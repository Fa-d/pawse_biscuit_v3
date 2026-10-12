"""What happens when the rules do not understand a prompt.

Word forms and typos are already handled inside the parser (morph.py, typo.py).  This module adds:

  1. an optional small model (only with llm=True and Anthropic credentials): Claude Haiku maps the prompt onto the
     registry's names through a JSON schema whose fields are enums, so it can only answer with names the rig knows.
     Answers are cached by prompt.  The rules still have the last word: the model's answer only fills what the rules
     left empty.
  2. a log of every prompt the rules did not understand (cache/misses.jsonl, capped), so its words can be added to
     the lexicon and the next person with that wording is understood without a model.

Nothing here can raise: a missing SDK, no credentials, an API or network error, a refusal, a cut-off or malformed
answer all mean "no answer".
"""
from __future__ import annotations

import json
import os
import threading
import time

from ..registry import REG
from ..spec import MAX_EFFECTS, MAX_PROPS, MAX_WEAR, VOCAB, StickerSpec
from .parser import Parser, ParseResult, normalize

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.environ.get("STUDIO_CACHE", os.path.join(HERE, "..", "cache"))
MODEL = os.environ.get("STUDIO_LLM_MODEL", "claude-haiku-5-5")
CACHE_MAX = 5000            # answers kept
MISSES_MAX = 2_000_000      # bytes of miss log kept (the older half is dropped beyond it)
_lock = threading.Lock()


# ------------------------------------------------------------------ LLM step
def _schema():
    enum = lambda xs: {"type": "string", "enum": list(xs)}
    return {
        "type": "object",
        "properties": {
            "base": enum(VOCAB["base"]),
            "face": enum(VOCAB["face"]),
            "motion": enum(VOCAB["motion"]),
            "stance": enum(VOCAB["stance"]),
            "props": {"type": "array", "items": enum(VOCAB["props"])},
            "effects": {"type": "array", "items": enum(VOCAB["effects"])},
            "accessories": {"type": "array", "items": enum(VOCAB["accessories"])},
            "unknown_concepts": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["base", "face", "motion", "stance", "props", "effects", "accessories", "unknown_concepts"],
        "additionalProperties": False,
    }


def _system():
    m = ", ".join(f"{k} ({v.doing or v.label.lower()})" for k, v in REG.motions.items())
    return (
        "You turn a short description of a sticker into settings for an animated cartoon mascot. "
        "Choose the closest mascot, face, motion and stance, at most two props held in the paws, three effects around it "
        "and three things worn, only from the allowed values. Keep the mascot 'biscuit' (a fox) unless another animal is asked for. "
        "Prefer fewer props and effects over loosely related ones. "
        f"Motions: {m}. "
        "List any part of the request the allowed values cannot show (for example an object or a second character) in unknown_concepts."
    )


def _cache_path(name):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, name)


def _load_cache():
    try:
        with open(_cache_path("llm.json"), encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_cache(cache):
    if len(cache) > CACHE_MAX:
        for k in list(cache)[: len(cache) - CACHE_MAX]:
            del cache[k]
    path = _cache_path("llm.json")
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)                                   # atomic: a reader never sees half a file


def log_miss(text, result: ParseResult, used_llm):
    try:
        with _lock:
            path = _cache_path("misses.jsonl")
            if os.path.exists(path) and os.path.getsize(path) > MISSES_MAX:
                with open(path, encoding="utf-8") as f:
                    lines = f.readlines()
                with open(path, "w", encoding="utf-8") as f:
                    f.writelines(lines[len(lines) // 2:])
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(dict(t=round(time.time()), prompt=text[:300], unknown=result.unknown, llm=used_llm), ensure_ascii=False) + "\n")
    except OSError:
        pass


def _clean(data):
    """Keep only allowed names (compared without case, as the API may change it); None if the answer is unusable."""
    if not isinstance(data, dict):
        return None
    out = {}
    for slot in ("base", "face", "motion", "stance"):
        allowed = {v.lower(): v for v in VOCAB[slot]}
        v = data.get(slot)
        out[slot] = allowed.get(v.lower()) if isinstance(v, str) else None
    for slot in ("props", "effects", "accessories"):
        allowed = {v.lower(): v for v in VOCAB[slot]}
        vs = data.get(slot) if isinstance(data.get(slot), list) else []
        out[slot] = [allowed[v.lower()] for v in vs if isinstance(v, str) and v.lower() in allowed]
    out["unknown_concepts"] = [str(x)[:40] for x in (data.get("unknown_concepts") or []) if isinstance(x, (str, int, float))][:8]
    return out


def llm_spec(text):
    """dict of registry names (+ unknown_concepts), or None when there is no usable answer."""
    key = normalize(text)
    with _lock:
        cache = _load_cache()
    if key in cache:
        return _clean(cache[key])
    try:
        import anthropic
    except ImportError:
        return None
    try:
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=_system(),
            messages=[{"role": "user", "content": text[:300]}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": _schema()}},
        )
        if resp.stop_reason in ("refusal", "max_tokens"):
            return None
        raw = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), None)
        data = _clean(json.loads(raw)) if raw else None
    except Exception:  # noqa: BLE001 - auth, network, API, SDK too old for output_config, malformed JSON: no answer
        return None
    if data is None:
        return None
    with _lock:
        cache = _load_cache()
        cache[key] = data
        try:
            _save_cache(cache)
        except OSError:
            pass
    return data


def merge(llm: dict, rules: ParseResult) -> StickerSpec:
    """The model's answer fills what the rules left empty; everything the rules understood stays."""
    spec = rules.spec
    understood = {m.section for m in rules.matches}
    if llm.get("base") and "bases" not in understood:
        spec.base = llm["base"]
    if llm.get("face") and not understood & {"moods", "template"}:
        spec.face = llm["face"]
    if llm.get("motion") and not understood & {"moods", "actions", "template"}:
        spec.motion = llm["motion"]
    if llm.get("stance") and "poses" not in understood and not ("moods" in understood and spec.stance != "stand"):
        spec.stance = llm["stance"]
    spec.props = (spec.props + [p for p in llm.get("props", []) if p not in spec.props])[:MAX_PROPS]
    spec.effects = (spec.effects + [e for e in llm.get("effects", []) if e not in spec.effects])[:MAX_EFFECTS]
    spec.accessories = (spec.accessories + [w for w in llm.get("accessories", []) if w not in spec.accessories])[:MAX_WEAR]
    if spec.stance in ("sit", "lotus") and REG.motions[spec.motion].sit == "no":
        spec.stance = "stand"
    return spec.validate()


def parse(text, parser: Parser | None = None, llm=False, auto_caption=True) -> ParseResult:
    """Rules (with word forms and typo fixes), then, if they did not understand and llm=True, the model."""
    parser = parser or default_parser()
    r = parser.parse(text, auto_caption=auto_caption)
    if r.fixed:
        r.source = "rules+typos" if any(k != v for k, v in r.fixed.items()) else r.source
    if r.confident:
        return r
    used = False
    if llm:
        data = llm_spec(text)
        if data:
            try:
                r.spec = merge(data, r)
                r.source = r.source + "+llm"
                r.confident = True
                r.unknown = list(data.get("unknown_concepts", []))
                used = True
            except ValueError:
                pass
    log_miss(text, r, used)
    return r


def fix_typos(parser: Parser, result: ParseResult, text):
    """v3 interface, kept for old scripts: typos are now fixed inside Parser.parse.  Returns None."""
    return None


_DEFAULT = None


def default_parser():
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Parser()
    return _DEFAULT
