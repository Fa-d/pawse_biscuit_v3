"""Prompt -> StickerSpec with rules only (lexicon.yaml + templates.yaml).

    "a super sleepy purple fox with coffee saying 'monday again'"
      caption   'monday again'              (quoted text or 'saying ...' is never interpreted)
      template  monday? no -> none matched
      moods     sleepy (weight 2)           -> face sleep, stance sit, motion sleep
      props     coffee (weight 3)           -> mug
      colours   purple                      -> palette
      intensity super                       -> 1.35

Matching is on whole words, longest phrase first; a matched phrase hides the shorter phrases inside it, so
"good night" never also counts as "good".  For each slot the highest weight wins, and on a tie the word that
comes later in the prompt.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import yaml

from ..spec import Caption, StickerSpec, VOCAB

HERE = os.path.dirname(os.path.abspath(__file__))
WEIGHT = dict(template=1, moods=2, actions=3, props=3, effects=3, accessories=3, poses=4, colours=4, bases=4)
LIST_SLOTS = ("props", "effects", "accessories")
SCALAR_SLOTS = ("face", "stance", "tail", "motion", "arm_L", "arm_R", "base")
SECTIONS = ("moods", "actions", "props", "effects", "accessories", "poses", "bases")
MAX_PROPS, MAX_EFFECTS, MAX_WEAR = 2, 3, 3

QUOTED = re.compile(r"(?:^|(?<=[\s:(]))[\"“”‘’'«]([^\"“”«»]{1,60}?)[\"“”’'»](?=$|[\s.,!?;:)])")
SAYING = re.compile(r"\b(?:saying|says|that says|with (?:the )?(?:text|caption|words?)|captioned|(?:caption|text)\s*[:\-])\s*[:\-]?\s+(.{1,60}?)\s*$", re.I)


class _Loader(yaml.SafeLoader):
    """YAML without the 1.1 booleans: 'yes', 'no', 'on' and 'off' are words here."""


_Loader.yaml_implicit_resolvers = {k: [r for r in v if r[0] != "tag:yaml.org,2002:bool"]
                                   for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()}


def load_yaml(path):
    with open(path) as f:
        return yaml.load(f, Loader=_Loader)


def normalize(text):
    t = text.lower().replace("’", "'").replace("‘", "'")
    t = re.sub(r"[,.;!?]+", " | ", t)                              # clause breaks end the reach of a 'not'
    t = re.sub(r"[^a-z0-9'| ]+", " ", t)
    t = re.sub(r"(?<![a-z])'|'(?![a-z])", " ", t)                 # keep apostrophes only inside words
    return " ".join(t.split())


@dataclass
class Match:
    phrase: str
    section: str            # template, moods, actions, props, effects, poses, colours, strong, weak
    name: str
    pos: int                # token index where the phrase starts
    negated: bool = False


@dataclass
class ParseResult:
    spec: StickerSpec
    matches: list = field(default_factory=list)
    unknown: list = field(default_factory=list)          # content words nothing understood
    template: str | None = None
    confident: bool = True
    source: str = "rules"                                 # rules, rules+fuzzy, rules+llm

    def explain(self):
        lines = [f"source: {self.source}   confident: {self.confident}   template: {self.template or '-'}"]
        for m in self.matches:
            lines.append(f"  {m.phrase!r:<22} -> {m.section}:{m.name}{'  (negated)' if m.negated else ''}")
        if self.unknown:
            lines.append(f"  not understood: {', '.join(self.unknown)}")
        return "\n".join(lines)


class Parser:
    def __init__(self, lexicon=os.path.join(HERE, "lexicon.yaml"), templates=os.path.join(HERE, "templates.yaml")):
        self.lex = load_yaml(lexicon)
        self.tpl = load_yaml(templates)
        self.stop = {normalize(w) for w in self.lex["stopwords"]}
        self.neg = {normalize(w) for w in self.lex["negators"]}
        self.index = {}                                       # phrase -> [(section, name)]

        def add(phrase, section, name):
            p = normalize(str(phrase))
            if p:
                self.index.setdefault(p, []).append((section, name))

        for name, t in self.tpl.items():
            for w in t["words"]:
                add(w, "template", name)
        for section in SECTIONS:
            for name, e in self.lex[section].items():
                for w in e["words"]:
                    add(w, section, name)
        for name in self.lex["colours"]:
            add(name, "colours", name)
        for kind in ("strong", "weak"):
            for w in self.lex["intensity"][kind]:
                add(w, kind, kind)
        self.longest = max(len(p.split()) for p in self.index)

    # ---------------------------------------------------------------- pieces
    @staticmethod
    def extract_caption(text):
        """Pull out the caption the user wants printed: quoted text, or what follows 'saying' / 'with text'."""
        m = QUOTED.search(text)
        if m:
            return m.group(1).strip(), (text[:m.start()] + " " + text[m.end():]).strip()
        m = SAYING.search(text)
        if m:
            cap = m.group(1).strip().strip("\"'“”").rstrip(".")
            return cap, text[:m.start()].strip()
        return None, text

    def match(self, norm):
        toks = norm.split()
        taken = [False] * len(toks)
        out = []
        for n in range(min(self.longest, len(toks)), 0, -1):
            for i in range(len(toks) - n + 1):
                if any(taken[i:i + n]):
                    continue
                phrase = " ".join(toks[i:i + n])
                hits = self.index.get(phrase)
                if not hits:
                    continue
                for k in range(i, i + n):
                    taken[k] = True
                for section, name in hits:
                    out.append(Match(phrase, section, name, i))
        for m in out:
            # 'not' reaches back at most 3 words, and never past a clause break or another matched phrase
            for k in range(m.pos - 1, max(-1, m.pos - 4), -1):
                if toks[k] == "|" or taken[k]:
                    break
                if toks[k] in self.neg:
                    m.negated = True
                    break
        out.sort(key=lambda m: m.pos)
        unknown = [t for t, used in zip(toks, taken) if not used and t not in self.stop and t not in self.neg
                   and t != "|" and len(t) > 1 and not t.isdigit()]
        return out, unknown, toks

    # ---------------------------------------------------------------- main
    def parse(self, text, auto_caption=True):
        caption, rest = self.extract_caption(text)
        norm = normalize(rest)
        matches, unknown, toks = self.match(norm)

        votes = {s: [] for s in SCALAR_SLOTS}                 # slot -> [(weight, pos, value)]
        lists = {s: [] for s in LIST_SLOTS}
        palette, intensity = {}, 1.0

        def apply(values, weight, pos):
            for slot, v in values.items():
                if slot in LIST_SLOTS:
                    for item in v:
                        if item not in lists[slot]:
                            lists[slot].append(item)
                elif slot in votes:
                    votes[slot].append((weight, pos, v))

        # one template: the one whose phrases cover the most words, then the one mentioned first
        score = {}
        for m in matches:
            if m.section == "template" and not m.negated:
                n, first = score.get(m.name, (0, m.pos))
                score[m.name] = (n + len(m.phrase.split()), min(first, m.pos))
        template = None
        if score:
            template = max(score, key=lambda k: (score[k][0], -score[k][1]))
            apply(self.tpl[template]["spec"], WEIGHT["template"], -1)

        used = []
        for m in matches:
            if m.section == "template":
                if m.name == template:
                    used.append(m)
                continue
            if m.section in ("strong", "weak"):
                intensity *= 1.35 if m.section == "strong" else 0.65
                used.append(m)
                continue
            if m.section == "colours":
                palette = dict(self.lex["colours"][m.name])
                used.append(m)
                continue
            entry = self.lex[m.section][m.name]
            if m.negated:
                flip = entry.get("not")
                if not flip:
                    continue                                   # "not waving": just ignore the word
                entry = self.lex["moods"][flip]
            apply(entry["set"], WEIGHT[m.section], m.pos)
            used.append(m)

        bangs = text.count("!")
        if bangs:
            intensity *= 1.0 + min(bangs, 3) * 0.08

        spec = StickerSpec()
        for slot, vs in votes.items():
            if vs:
                setattr(spec, slot, max(vs, key=lambda x: (x[0], x[1]))[2])
        spec.props = lists["props"][:MAX_PROPS]
        spec.effects = lists["effects"][:MAX_EFFECTS]
        spec.accessories = lists["accessories"][:MAX_WEAR]
        spec.palette = palette
        spec.intensity = round(min(1.6, max(0.5, intensity)), 2)
        if caption:
            spec.caption = Caption(caption)
        elif auto_caption and template and self.tpl[template].get("caption"):
            spec.caption = Caption(self.tpl[template]["caption"])
        spec.validate()

        core = any(m.section in ("template", "moods", "actions", "props", "poses", "accessories") for m in used)
        content = [t for t in toks if t not in self.stop and t not in self.neg and t != "|"]
        confident = core and len(unknown) <= max(1, len(content) // 2)
        return ParseResult(spec, used, unknown, template, confident)

    # ---------------------------------------------------------------- checks
    def problems(self):
        """Names in the YAML files that the rig does not know (run by the tests)."""
        bad = []

        def check(where, values):
            for slot, v in values.items():
                if slot in LIST_SLOTS:
                    for item in v:
                        if item not in VOCAB[slot]:
                            bad.append(f"{where}: {slot} {item!r}")
                elif slot in ("arm_L", "arm_R"):
                    if v not in VOCAB["arm"]:
                        bad.append(f"{where}: {slot} {v!r}")
                elif slot in VOCAB and v not in VOCAB[slot]:
                    bad.append(f"{where}: {slot} {v!r}")
                elif slot not in VOCAB and slot not in SCALAR_SLOTS:
                    bad.append(f"{where}: unknown slot {slot!r}")
        for name, t in self.tpl.items():
            check(f"template {name}", t["spec"])
        for section in SECTIONS:
            for name, e in self.lex[section].items():
                check(f"{section}.{name}", e["set"])
                if e.get("not") and e["not"] not in self.lex["moods"]:
                    bad.append(f"{section}.{name}: not -> unknown mood {e['not']!r}")
        dup = {p: h for p, h in self.index.items() if len({s for s, _ in h if s != "template"}) > 1
               or len([1 for s, _ in h if s != "template"]) > 1}
        for p, h in dup.items():
            bad.append(f"phrase {p!r} is in several lexicon entries: {h}")
        return bad
