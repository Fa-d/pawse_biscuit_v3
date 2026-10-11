"""What happens when the rules do not understand a prompt.

  1. typo fix: unknown words are matched against the lexicon's own words (difflib, no model).  'slepy wih cofee'
     -> 'sleepy with coffee'.
  2. small LLM (optional, only when ANTHROPIC credentials exist and llm=True): Claude Haiku maps the prompt onto the
     same vocabulary through a JSON schema whose fields are enums, so it can only answer with names the rig knows.
     Answers are cached by normalised prompt, and every prompt that reaches this step is logged to
     cache/misses.jsonl so its words can be added to lexicon.yaml (and the next user with that wording costs nothing).

The rules still have the last word: the LLM answer is a base layer under anything the rules did understand.
"""
from __future__ import annotations

import difflib
import json
import os
import time

from ..spec import VOCAB, StickerSpec
from .parser import Parser, ParseResult, normalize

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.environ.get("STUDIO_CACHE", os.path.join(HERE, "..", "cache"))
MODEL = "claude-haiku-5-5"


def fix_typos(parser: Parser, result: ParseResult, text):
    """Replace each unknown word with the closest single word the lexicon knows (or leave it).  Returns new text or None."""
    vocab = sorted({p for p in parser.index if " " not in p} | parser.stop)
    out, changed = normalize(text).split(), False
    for k, tok in enumerate(out):
        if tok in result.unknown and len(tok) >= 3:
            best = difflib.get_close_matches(tok, vocab, n=1, cutoff=0.78)
            if best and best[0] != tok:
                out[k] = best[0]
                changed = True
    return " ".join(out) if changed else None


# ------------------------------------------------------------------ LLM step
def _schema():
    enum = lambda xs: {"type": "string", "enum": list(xs)}
    return {
        "type": "object",
        "properties": {
            "face": enum(VOCAB["face"]),
            "motion": enum(VOCAB["motion"]),
            "stance": enum(VOCAB["stance"]),
            "props": {"type": "array", "items": enum(VOCAB["props"])},
            "effects": {"type": "array", "items": enum(VOCAB["effects"])},
            "accessories": {"type": "array", "items": enum(VOCAB["accessories"])},
            "unknown_concepts": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["face", "motion", "stance", "props", "effects", "accessories", "unknown_concepts"],
        "additionalProperties": False,
    }


SYSTEM = (
    "You turn a short description of a sticker into settings for an animated cartoon mascot. "
    "Choose the closest face, motion and stance, at most two props, three effects and three accessories (things worn), "
    "only from the allowed values. "
    "Prefer fewer props and effects over loosely related ones. "
    "List any part of the request the allowed values cannot show (for example an object or a second character) in unknown_concepts."
)


def _cache_path(name):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, name)


def _load_cache():
    try:
        with open(_cache_path("llm.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def log_miss(text, result: ParseResult, used_llm):
    with open(_cache_path("misses.jsonl"), "a") as f:
        f.write(json.dumps(dict(t=round(time.time()), prompt=text, unknown=result.unknown, llm=used_llm)) + "\n")


def llm_spec(text):
    """dict with face/motion/stance/props/effects (+unknown_concepts), or None when no API access."""
    key = normalize(text)
    cache = _load_cache()
    if key in cache:
        return cache[key]
    try:
        import anthropic
    except ImportError:
        return None
    try:
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM,
            messages=[{"role": "user", "content": text}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": _schema()}},
        )
    except anthropic.AuthenticationError:
        return None
    except anthropic.APIConnectionError:
        return None
    except anthropic.APIStatusError:
        return None
    if resp.stop_reason in ("refusal", "max_tokens"):
        return None
    data = json.loads(next(b.text for b in resp.content if b.type == "text"))
    cache[key] = data
    with open(_cache_path("llm.json"), "w") as f:
        json.dump(cache, f, indent=1)
    return data


def merge(llm: dict, rules: ParseResult) -> StickerSpec:
    """LLM answer as the base, then everything the rules understood on top."""
    spec = rules.spec
    understood = {m.section for m in rules.matches}
    if "moods" not in understood and "template" not in understood:
        spec.face = llm["face"]
    if not understood & {"moods", "actions", "template"}:
        spec.motion = llm["motion"]
    if "poses" not in understood and not ("moods" in understood and spec.stance != "stand"):
        spec.stance = llm["stance"]
    spec.props = (spec.props + [p for p in llm["props"] if p not in spec.props])[:2]
    spec.effects = (spec.effects + [e for e in llm["effects"] if e not in spec.effects])[:3]
    spec.accessories = (spec.accessories + [w for w in llm.get("accessories", []) if w not in spec.accessories])[:3]
    return spec.validate()


def parse(text, parser: Parser | None = None, llm=False, auto_caption=True) -> ParseResult:
    """Rules, then typo fixing, then (optionally) the LLM."""
    parser = parser or default_parser()
    r = parser.parse(text, auto_caption=auto_caption)
    if r.confident:
        return r
    fixed = fix_typos(parser, r, parser.extract_caption(text)[1])
    if fixed:
        r2 = parser.parse(fixed, auto_caption=auto_caption)
        cap = parser.extract_caption(text)[0]
        if cap:
            r2.spec.caption = r.spec.caption
        r2.source = "rules+typos"
        if r2.confident:
            return r2
        r = r2 if len(r2.matches) > len(r.matches) else r
    used = False
    if llm:
        data = llm_spec(text)
        if data:
            r.spec = merge(data, r)
            r.source = r.source + "+llm"
            r.confident = True
            r.unknown = list(data.get("unknown_concepts", []))
            used = True
    log_miss(text, r, used)
    return r


_DEFAULT = None


def default_parser():
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Parser()
    return _DEFAULT
