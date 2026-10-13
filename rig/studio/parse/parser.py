"""Prompt -> StickerSpec with rules only (the lexicon and the scenario templates).

    "a super sleepy purple fox with coffee saying 'monday again'"
      caption    'monday again'                      quoted text, or what follows 'saying', is never read as words
      words      super sleepy purple fox with coffee
      matches    super (stronger) · sleepy (mood) · purple (colour) · fox (mascot) · coffee (prop)
      spec       face sleep (what 'sleepy' MEANS), stance sit and motion sleep (what it SUGGESTS), mug, purple fur

How words are read (each step in its own module):
  text.py    accents, emoji and emoticons, stretched words, laughter, chat shorthand, clause breaks
  morph.py   word forms the lexicon does not list ('clapping' -> clap, 'happier' -> happy)
  typo.py    real typos only ('slepy' -> sleepy), never real words ('eating' stays eating)

How a spec is decided:
  * Every lexicon entry says what its word MEANS (the slot its section owns: a mood's face, an action's motion, a
    prop) and what it only SUGGESTS (a mood's usual motion, an action's usual face).  What a word means beats a
    scenario template; a template beats what a word merely suggests.  "sad fox waving" waves (waving means it) with
    a sad face (sad means it); "tired fox jumping" jumps instead of sitting down as 'tired' alone would suggest.
  * 'not', 'no', 'without' ... negate the next thing said in the same clause: a negated mood with a `not:` partner
    flips ("not happy" -> sad), a negated prop, effect or worn item is kept out even if a template brings it
    ("birthday without the hat").  Phrases with a negator in them win first ("no way", "can't wait", "not bad").
  * A colour sticks to the item right after it ("a red scarf", "pink bow") or else colours the fur ("blue fox").
  * "in its left paw", "looking up", "fast" / "slowly" set which paw, the gaze and the tempo; "from behind", "side view",
    "facing left" which way the mascot faces (v5: a yaw; turning words such as "turn around" are motions).
"""
from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field

import yaml

from ..registry import REG
from ..spec import MAX_EFFECTS, MAX_PROPS, MAX_WEAR, VOCAB, Caption, StickerSpec, hex6
from .morph import base_of
from .text import BREAK, Token, fold, normalize, tokenize  # noqa: F401  (normalize is part of this module's interface)
from .typo import Fixer, is_word

HERE = os.path.dirname(os.path.abspath(__file__))
LIST_SLOTS = ("props", "effects", "accessories")
SCALAR_SLOTS = ("face", "stance", "tail", "motion", "arm_L", "arm_R", "base")
SECTIONS = ("moods", "actions", "props", "effects", "accessories", "poses", "bases")
# the slots each section's words MEAN; everything else an entry sets is only suggested
OWNS = dict(moods=("face",), actions=("motion",), props=("props",), effects=("effects",), accessories=("accessories",),
            poses=("stance", "arm_L", "arm_R", "tail"), bases=("base",))
# weight of a vote: what a word means (by section), a template, what a word suggests (by section)
MEANS = dict(poses=6, bases=6, actions=5, moods=5, props=5, effects=5, accessories=5)
TEMPLATE = 3
SUGGESTS = dict(actions=2.2, props=2.0, effects=2.0, accessories=2.0, poses=2.0, bases=2.0, moods=1.5)
HINT = 0.7                                   # read from the caption text, when the rest of the prompt says nothing
WEIGHT = dict(template=TEMPLATE, **MEANS)    # v3 name, still used by tools

# How a prompt is read, in order (python -m studio.cli --rules lists these with the composer's rules)
PARSER_RULES = [
    ("P01", "Quoted text is the caption, word for word; so is what follows 'saying', 'that says', 'with text' (a sign 'reading' too)."),
    ("P02", "'no caption' / 'without text' turns the suggested caption off."),
    ("P03", "A colour code ('#ff6699') is a colour like any colour word."),
    ("P04", "Emoji and emoticons are read as the words they stand for (😴 sleepy, :D laughing, ¯\\_(ツ)_/¯ shrug)."),
    ("P05", "Laughter in any spelling (hahaha, lolol, jajaja, kkkk, 555, xD) is one word: haha."),
    ("P06", "Stretched words are shrunk to a word the lexicon knows (heyyyy -> hey, sooo -> so)."),
    ("P07", "Chat shorthand is spelt out (omw, brb, ty, ily, idk, hbd ...), contractions too (can't -> can not)."),
    ("P08", "A word the lexicon lists exactly is read as written, never shrunk or spelt out."),
    ("P09", "Whole phrases in other languages are read as English (feliz cumpleaños, eid mubarak, শুভ জন্মদিন ...); "
            "a one-word phrase is matched as typed first."),
    ("P10", "Word forms the lexicon does not list are read as their base word (clapping -> clap, happier -> happy)."),
    ("P11", "Real typos are fixed (slepy -> sleepy), real words never are (eating stays eating)."),
    ("P12", "The longest phrase wins ('ice cream' before 'ice'); a phrase belongs to one entry only."),
    ("P13", "Little words ('a', 'the', 'my') and fillers ('ngl', 'pov', 'all night') carry no meaning."),
    ("P14", "Some words mean something only as the whole prompt ('nice' alone is a thumbs up)."),
    ("P15", "'No!' on its own is a head shake."),
    ("P16", "'not', 'no', 'without' negate the next thing said in the same clause; in a list after a negator every item is negated."),
    ("P17", "A negated feeling turns into its opposite ('not happy' is sad, 'not scared' is determined)."),
    ("P18", "A negated prop, effect or worn item is kept out, even when a scenario would bring it ('birthday without the hat')."),
    ("P19", "What a word means (weight 5, poses and mascots 6) beats a scenario (3), which beats what a word only suggests (2)."),
    ("P20", "Between two words of the same weight, the later one wins ('tired but dancing' dances)."),
    ("P21", "Vague words count less (please, maybe; yes and no 0.9) so the rest of the prompt decides when it says anything."),
    ("P22", "A colour paints the item right after it ('a red scarf'); after the item with 'in' ('a scarf in red'); else the fur."),
    ("P23", "A colour before 'eyes' colours the eyes."),
    ("P24", "A shade word changes the colour after it (light blue, dark red, pastel pink, neon green)."),
    ("P25", "Some mascot words bring a fur colour (polar bear is white, golden retriever golden) unless a colour is named."),
    ("P26", "'left paw' / 'right hand' puts the nearest held thing in that paw."),
    ("P27", "Gaze words set where it looks (looking up, side eye); tempo words set the speed (fast, slowly)."),
    ("P28", "Intensity words, '!!!' and CAPITALS make it stronger; 'a bit', 'kinda' make it softer."),
    ("P29", "One scenario at most: the one whose phrases cover the most words, then the one said first."),
    ("P30", "A scenario suggests its caption when the prompt has none (and auto captions are on)."),
    ("P31", "When only the caption says anything, its words hint at the scenario and the mood (lightly)."),
    ("P32", "A motion suggests its own face when nothing else sets one (eating looks happy, sobbing cries)."),
    ("P33", "A prompt is understood when something in it means a sticker part and few words are left unknown; unknown words get "
            "a 'did you mean' suggestion."),
    ("P34", "One mascot is drawn per sticker for now: a second animal named ('a cat hugging a dog'), or two of one ('two foxes'), "
            "is left out with a note that says so, and counts as not understood."),
    ("P35", "View words turn the mascot ('from behind', 'side view', 'in profile', 'facing left', 'three-quarter view'): the last "
            "one said wins.  Turning is a motion ('turn around', 'looking back over its shoulder', 'do a 360')."),
]
# words before a mascot that mean more than one of it ("two foxes", "a pair of cats")
PLURAL_WORDS = {"two", "2", "both", "pair", "couple", "twins", "twin", "duo", "three", "3", "few", "several", "many"}
FILLERS = {"a", "an", "the", "my", "your", "his", "her", "its", "their", "our", "some"}   # dropped from phrases and prompts alike

QUOTES = "\"“”‘’'«»„‚「」『』"
HEX_COLOUR = re.compile(r"(?<![\w#])#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-zA-Z])")
HEX_TOKEN = re.compile(r"^hexcolour([0-9a-f]{6})$")
COLOUR_STOP = {"with", "holding", "wearing", "in", "on", "and", "plus", "carrying", "has", "having", "while", "but"}
QUOTED = re.compile(r"(?:^|(?<=[\s:(\[]))[\"“”‘’'«„‚「『]([^\"“”«»„「」『』]{1,80}?)[\"“”’'»」』](?=$|[\s.,!?;:)\]])")
# 'reading' starts a caption only after a thing with writing on it ("a sign reading open"); "reading a book" is reading
SAYING = re.compile(r"\b(?:saying|says|that says|which says|that reads|(?:(?<=sign )|(?<=board )|(?<=banner )|(?<=poster )|(?<=card )|"
                    r"(?<=shirt )|(?<=note ))reading|with (?:the )?(?:text|caption|words?|message)|captioned|"
                    r"titled|labell?ed|(?:caption|text|message)\s*[:\-])\s*[:\-]?\s+(.{1,80}?)\s*$", re.I)
LEAD_IN = re.compile(r"\b(?:saying|says|that says|which says|that reads|which reads|reads|reading|with (?:the )?(?:text|caption|words?|message)|"
                     r"captioned|titled|labell?ed|caption|text|message)\s*[:\-]?\s*$", re.I)
NO_CAPTION = re.compile(r"\b(?:no|without)\s+(?:a\s+|any\s+)?(?:caption|text|words|title|message)\b", re.I)


class _Loader(yaml.SafeLoader):
    """YAML without the 1.1 booleans: 'yes', 'no', 'on' and 'off' are words here."""


_Loader.yaml_implicit_resolvers = {k: [r for r in v if r[0] != "tag:yaml.org,2002:bool"]
                                   for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()}


def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.load(f, Loader=_Loader)


def _merge_dir(single, folder):
    """A YAML file and/or every YAML file in a folder, merged (sections merge one level deep)."""
    out = {}
    paths = ([single] if single and os.path.exists(single) else []) + sorted(glob.glob(os.path.join(folder, "*.yaml")) if folder else [])
    for p in paths:
        data = load_yaml(p) or {}
        for k, v in data.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                dup = set(v) & set(out[k])
                if dup:
                    raise ValueError(f"{os.path.basename(p)}: {k}: {sorted(dup)} defined twice")
                out[k].update(v)
            elif isinstance(v, list) and isinstance(out.get(k), list):
                out[k] = out[k] + [x for x in v if x not in out[k]]
            elif k in out and k not in ("stopwords", "negators"):
                raise ValueError(f"{os.path.basename(p)}: {k!r} defined twice")
            else:
                out[k] = v
    return out


@dataclass
class Match:
    phrase: str
    section: str            # template, moods, actions, props, effects, accessories, poses, bases, colours, strong, weak, side, look, tempo,
                            # view
    name: str
    pos: int                # token index where the phrase starts
    negated: bool = False
    typed: str = ""         # what was typed when it differs ('clapping', 'slepy')
    end: int = 0
    dropped: bool = False   # understood, but left out of the sticker (a second mascot, P34)


@dataclass
class ParseResult:
    spec: StickerSpec
    matches: list = field(default_factory=list)
    unknown: list = field(default_factory=list)          # content words nothing understood
    template: str | None = None
    confident: bool = True
    source: str = "rules"                                 # rules, rules+llm
    score: float = 1.0                                    # share of the meaningful words that were understood
    suggestions: dict = field(default_factory=dict)       # unknown word -> a lexicon word it resembles
    fixed: dict = field(default_factory=dict)             # typed word -> word read (typos and word forms)
    notes: list = field(default_factory=list)             # what was understood but could not be used, in plain words (P34)

    def explain(self):
        lines = [f"source: {self.source}   confident: {self.confident}   understood: {self.score:.0%}   template: {self.template or '-'}"]
        for m in self.matches:
            typed = f"  (typed {m.typed!r})" if m.typed else ""
            flags = ("  (negated)" if m.negated else "") + ("  (left out)" if m.dropped else "")
            lines.append(f"  {m.phrase!r:<22} -> {m.section}:{m.name}{flags}{typed}")
        if self.unknown:
            lines.append(f"  not understood: {', '.join(self.unknown)}")
        if self.suggestions:
            lines.append("  did you mean: " + ", ".join(f"{k} -> {v}" for k, v in self.suggestions.items()))
        for n in self.notes:
            lines.append(f"  note: {n}")
        return "\n".join(lines)


class Parser:
    def __init__(self, lexicon=os.path.join(HERE, "lexicon.yaml"), templates=os.path.join(HERE, "templates.yaml"),
                 lexicon_dir=os.path.join(HERE, "lexicon"), templates_dir=os.path.join(HERE, "templates")):
        self.lex = _merge_dir(lexicon, lexicon_dir)
        self.tpl = _merge_dir(templates, templates_dir)
        for sec in SECTIONS + ("colours",):
            self.lex.setdefault(sec, {})
        self.lex.setdefault("intensity", {"strong": [], "weak": []})
        self.lex.setdefault("tempo", {"fast": [], "slow": []})
        self.lex.setdefault("sides", {"L": [], "R": []})
        self.lex.setdefault("look", {})
        self.lex.setdefault("view", {})
        self.lex.setdefault("colour_modifiers", {})
        self.lex.setdefault("translations", {})
        self.lex.setdefault("fillers", [])
        self.lex.setdefault("alone", {})
        self.stop = {w for w in (self._norm(x) for x in self.lex.get("stopwords", [])) if w}
        self.neg = {w for w in (self._norm(x) for x in self.lex.get("negators", [])) if w}
        self.index = {}                                       # phrase -> [(section, name)]

        self._written = set()                                  # phrases as written, before 'a', 'the', 'my' ... are dropped

        def add(phrase, section, name):
            self._written.add(" ".join(t.text for t in tokenize(str(phrase), chat=False)[0]))
            p = self._norm(str(phrase))
            if p and (section, name) not in self.index.get(p, ()):
                self.index.setdefault(p, []).append((section, name))

        for name, t in self.tpl.items():
            for w in t["words"]:
                add(w, "template", name)
        for section in SECTIONS:
            for name, e in self.lex[section].items():
                for w in e["words"]:
                    add(w, section, name)
        for name, e in self.lex["colours"].items():
            for w in [name] + list(e.get("words", []) if isinstance(e, dict) and "words" in e else []):
                add(w, "colours", name)
        for kind in ("strong", "weak"):
            for w in self.lex["intensity"].get(kind, []):
                add(w, kind, kind)
        for kind in ("fast", "slow"):
            for w in self.lex["tempo"].get(kind, []):
                add(w, "tempo", kind)
        for side, words in self.lex["sides"].items():
            for w in words:
                add(w, "side", side)
        for name, e in self.lex["look"].items():
            for w in e["words"]:
                add(w, "look", name)
        for name, e in self.lex["view"].items():
            for w in e["words"]:
                add(w, "view", name)
        for name, words in self.lex["colour_modifiers"].items():
            for w in words:
                add(w, "shade", name)
        for w in self.lex["fillers"]:
            add(w, "filler", "filler")
        self.longest = max(len(p.split()) for p in self.index)
        self.known = set()
        for p in self.index:
            self.known.update(p.split())
        self.known |= self.stop | self.neg | FILLERS
        self._known = frozenset(self.known)
        self.singles = {p for p in self.index if " " not in p}
        self._listed = frozenset(self.singles)
        self.fixer = Fixer(self.singles)
        self.entry_of = {}
        for p, hits in self.index.items():
            if " " not in p:
                lexical = [h for h in hits if h[0] != "template"]
                self.entry_of[p] = lexical[0] if lexical else hits[0]
        # translations: whole phrases in other languages -> English words (read before matching)
        self.translations = {}
        self.translations_raw = {}                     # one-word keys as typed ('555', 'kkkk'), looked up before anything else
        for src, dst in (self.lex.get("translations") or {}).items():
            # keys are read the way prompts are (stretched letters shrunk), so 'ㅋㅋㅋ' and 'hahahaha' match as typed ...
            k = " ".join(t.text for t in tokenize(str(src), self._known, listed=self._listed)[0] if t.text not in FILLERS)
            raw = " ".join(fold(str(src)).lower().split())
            if " " not in raw:
                self.translations_raw[raw] = str(dst)
                # ... unless reading it that way turns it into another word ('555' -> '5', 'kkkk' -> 'kk' -> 'ok')
                if k != raw and k in self.known:
                    continue
            if k:
                self.translations[k] = str(dst)
        self.max_tr = max((len(k.split()) for k in self.translations), default=0)

    # ---------------------------------------------------------------- pieces
    @staticmethod
    def _norm(text):
        toks, _ = tokenize(text, chat=False)
        words = [t.text for t in toks if t.text not in FILLERS]
        while words and words[0] == BREAK:
            words.pop(0)
        return " ".join(words)

    @staticmethod
    def extract_caption(text):
        """Pull out the caption the user wants printed: quoted text, or what follows 'saying' / 'with text'.
        Returns (caption or None, the rest of the prompt)."""
        m = QUOTED.search(text)
        if m and m.group(1).strip():
            before = LEAD_IN.sub("", text[:m.start()])        # 'a sign reading "open"': 'reading' only led to the text
            return m.group(1).strip(), (before + " " + text[m.end():]).strip()
        m = SAYING.search(text)
        if m:
            cap = m.group(1).strip().strip(QUOTES).rstrip(".").strip()
            if cap:
                return cap, text[:m.start()].strip()
        return None, text

    def _tokens(self, text):
        text = HEX_COLOUR.sub(lambda m: f" hexcolour{hex6('#' + m.group(1))[1:].lower()} ", text)
        toks, bangs = tokenize(text, self._known, listed=self._listed)
        if self.translations:                                  # other languages: whole phrases to English
            out, k = [], 0
            while k < len(toks):
                hit = None
                for n in range(min(self.max_tr, len(toks) - k), 0, -1):
                    if n == 1:                         # a one-word key as typed comes before the word as read
                        raw = fold(toks[k].raw or "").lower()
                        if raw in self.translations_raw and toks[k].source != "emoji":
                            hit = (1, self.translations_raw[raw])
                            break
                    key = " ".join(t.text for t in toks[k:k + n])
                    if key in self.translations:
                        hit = (n, self.translations[key])
                        break
                if hit:
                    for w in hit[1].split():
                        out.append(Token(w, " ".join(t.raw for t in toks[k:k + hit[0]]), toks[k].emph, "translation"))
                    k += hit[0]
                else:
                    out.append(toks[k])
                    k += 1
            toks = out
        return toks, bangs

    def _repair(self, toks):
        """Word forms and typos the lexicon does not list, read as the word they stand for."""
        fixed = {}
        for t in toks:
            w = t.text
            if w == BREAK or w in self.known or not w.isalpha() or len(w) < 3 or HEX_TOKEN.match(w):
                continue
            base = base_of(w, self.singles)
            if base is None and not is_word(w):
                base = self.fixer.fix(w, lambda c: self.entry_of.get(c, c))
            if base and base != w:
                fixed[t.raw if t.raw else w] = base
                t.text = base
        return fixed

    def match(self, toks):
        """Longest phrases first; returns (matches, taken flags, filtered tokens)."""
        words = [t for t in toks if t.text not in FILLERS]
        n = len(words)
        taken = [False] * n
        out = []
        for i, t in enumerate(words):                          # colour codes: "#ff6699 cat"
            h = HEX_TOKEN.match(t.text)
            if h:
                taken[i] = True
                out.append(Match(t.raw, "colours", "#" + h.group(1), i, end=i + 1))
        for size in range(min(self.longest, n), 0, -1):
            for i in range(n - size + 1):
                if any(taken[i:i + size]):
                    continue
                seq = words[i:i + size]
                if any(t.text == BREAK for t in seq):
                    continue
                phrase = " ".join(t.text for t in seq)
                hits = self.index.get(phrase)
                if not hits:
                    continue
                for k in range(i, i + size):
                    taken[k] = True
                typed = " ".join(t.raw for t in seq)
                for section, name in hits:
                    out.append(Match(phrase, section, name, i, typed=typed if typed.lower() != phrase else "", end=i + size))
        # a word that only means something as the whole prompt ("nice", "what?!")
        if self.lex["alone"] and not any(m.section not in ("strong", "weak", "filler") for m in out):
            free = [i for i in range(n) if not taken[i] and words[i].text != BREAK]
            if len(free) == 1 and words[free[0]].text in self.lex["alone"]:
                i = free[0]
                section, name = self.lex["alone"][words[i].text].split(".")
                taken[i] = True
                out.append(Match(words[i].text, section, name, i, end=i + 1))
        # "No!" on its own (nothing after it to negate) is a head shake
        if "no" in self.lex["actions"]:
            for i, t in enumerate(words):
                alone = (i == 0 or words[i - 1].text == BREAK) and (i == n - 1 or words[i + 1].text == BREAK)
                if t.text == "no" and not taken[i] and alone:
                    taken[i] = True
                    out.append(Match("no", "actions", "no", i, end=i + 1))
        out.sort(key=lambda m: (m.pos, m.section != "template"))
        return out, taken, words

    NEGATABLE = ("template", "moods", "actions", "props", "effects", "accessories", "poses")
    LISTED = ("props", "effects", "accessories")
    PASS = ("strong", "weak", "shade", "colours", "side")   # 'not very happy', 'no red hat': the negator reaches past these

    def _negate(self, matches, taken, words):
        """'not', 'no', 'without' ... negate the next thing said in the same clause.  In a list after a negator
        ('without the hat or the scarf') every item is negated.  A negator inside a matched phrase ('no way',
        "can't wait") belongs to that phrase and negates nothing."""
        covered = {}
        for m in matches:
            for k in range(m.pos, m.end):
                covered.setdefault(k, m)
        for m in sorted(matches, key=lambda x: x.pos):
            if m.section not in self.NEGATABLE:
                continue
            k, gap, joined = m.pos - 1, 0, False
            while k >= 0 and gap <= 3:
                w = words[k].text
                if w == BREAK:
                    break
                other = covered.get(k)
                if other is not None and other is not m:
                    if other.section in self.PASS:
                        k = other.pos - 1
                        continue
                    if joined and other.negated and other.section in self.LISTED and m.section in self.LISTED:
                        m.negated = True
                    break
                if w in self.neg:
                    m.negated = True
                    break
                if w in ("and", "or", "nor"):
                    joined = True
                elif w not in self.stop and w not in FILLERS:
                    gap += 1
                k -= 1

    # ---------------------------------------------------------------- main
    def parse(self, text, auto_caption=True):
        caption, rest = self.extract_caption(text)
        if NO_CAPTION.search(rest):
            auto_caption = False
            rest = NO_CAPTION.sub(" ", rest)
        toks, bangs = self._tokens(rest)
        fixed = self._repair(toks)
        matches, taken, words = self.match(toks)
        self._negate(matches, taken, words)

        votes = {s: [] for s in SCALAR_SLOTS}                 # slot -> [(weight, pos, value)]
        lists = {s: [] for s in LIST_SLOTS}                   # slot -> [(weight, pos, item)]
        banned = {s: set() for s in LIST_SLOTS}
        palette, tints, sides, look, tempo, yaw = {}, {}, {}, None, None, None
        intensity = 1.0
        hint_mode = False

        def apply(values, weight, pos):
            for slot, v in values.items():
                if slot in LIST_SLOTS:
                    for item in v:
                        lists[slot].append((weight, pos, item))
                elif slot in votes:
                    votes[slot].append((weight, pos, v))

        def entry_votes(section, entry, pos, scale=1.0):
            scale *= float(entry.get("weight", 1.0))
            means, suggests = self._split(section, entry)
            apply(means, MEANS[section] * scale, pos)
            apply(suggests, SUGGESTS[section] * scale, pos)

        # one template: the one whose phrases cover the most words, then the one mentioned first
        score = {}
        for m in matches:
            if m.section == "template" and not m.negated:
                cnt, first = score.get(m.name, (0, m.pos))
                score[m.name] = (cnt + len(m.phrase.split()), min(first, m.pos))
        template = max(score, key=lambda k: (score[k][0], -score[k][1])) if score else None
        if template:
            apply(self.tpl[template]["spec"], TEMPLATE, -1)

        used = []
        items_at = []                                         # (pos, end, section, name) of things that can take a colour or side
        default_colour = None                                 # fur colour an entry implies ("polar bear")
        for m in matches:
            if m.section == "template":
                if m.name == template:
                    used.append(m)
                continue
            if m.section in ("strong", "weak"):
                intensity *= 1.35 if m.section == "strong" else 0.65
                used.append(m)
                continue
            if m.section in ("colours", "side", "shade"):
                used.append(m)
                continue
            if m.section == "filler":
                continue
            if m.section == "tempo":
                tempo = 1.4 if m.name == "fast" else 0.7
                used.append(m)
                continue
            if m.section == "look":
                e = self.lex["look"][m.name]
                look = tuple(e["at"])
                if e.get("face"):
                    votes["face"].append((MEANS["poses"] - 1, m.pos, e["face"]))
                used.append(m)
                continue
            if m.section == "view":                           # P35: which way it faces, the last view word said
                yaw = float(self.lex["view"][m.name]["yaw"])
                used.append(m)
                continue
            entry = self.lex[m.section][m.name]
            if m.negated:
                means, _ = self._split(m.section, entry)
                for slot in LIST_SLOTS:
                    for item in means.get(slot, []):
                        banned[slot].add(item)
                flip = entry.get("not")
                if flip:
                    entry_votes("moods", self.lex["moods"][flip], m.pos)
                used.append(m)
                continue
            entry_votes(m.section, entry, m.pos)
            if entry.get("colour") and default_colour is None:
                default_colour = entry["colour"]
            if m.section in ("props", "accessories", "effects", "bases"):
                items_at.append((m.pos, m.end, m.section, m.name))
            used.append(m)

        # colours: the item right after a colour takes it; otherwise the fur
        tinted = {i for m in used if m.section in ("colours", "shade") for i in range(m.pos, m.end)}
        for m in used:
            if m.section != "colours":
                continue
            value = self._colour(m, used)
            # the first thing after the colour takes it, unless that is the mascot ("purple kitty with coffee"
            # colours the cat) or a word like 'with' stands between them ("blue with a hat" is a blue fox)
            ahead = sorted(it for it in items_at if 0 <= it[0] - m.end <= 2)
            target = ahead[0] if ahead and ahead[0][2] != "bases" else None
            between = [i for i in range(m.end, target[0]) if i not in tinted] if target is not None else []
            if between and any(words[i].text in COLOUR_STOP for i in between) and \
                    not all(words[i].text in ("and", "or") for i in between):      # "red and white scarf" is a scarf
                target = None
            before = m.pos >= 1 and words[m.pos - 1].text == "in"
            if before and target is None:
                target = next((it for it in reversed(items_at) if 0 <= m.pos - it[1] <= 2 and it[2] != "bases"), None)
            nxt = words[m.end].text if m.end < len(words) else ""
            if nxt in ("eyes", "eye", "eyed"):
                palette["iris"] = value if isinstance(value, str) else value.get("orange")
            elif target is not None:
                item = self._item_of(target)
                if item:
                    tints[item] = value if isinstance(value, str) else value.get("orange")
            else:
                palette = dict(value) if isinstance(value, dict) else {"orange": value}
        if not palette and default_colour:
            palette = {"orange": self._hex(default_colour)}
        # which paw: the side words stick to the nearest prop in the same clause
        for m in used:
            if m.section != "side":
                continue
            props = [it for it in items_at if it[2] == "props"]
            if props:
                near = min(props, key=lambda it: min(abs(it[0] - m.pos), abs(it[1] - m.pos)))
                item = self._item_of(near)
                if item:
                    sides[item] = m.name

        # nothing said about the sticker itself: the caption's own words hint at a scenario or a mood
        core = any(m.section in ("template", "moods", "actions", "props", "poses", "accessories", "effects") for m in used)
        if caption and not core:
            ctoks, _ = self._tokens(caption)
            self._repair(ctoks)
            cm, _, _ = self.match(ctoks)
            cscore = {}
            for m in cm:
                if m.section == "template":
                    cnt, first = cscore.get(m.name, (0, m.pos))
                    cscore[m.name] = (cnt + len(m.phrase.split()), min(first, m.pos))
            if cscore:
                ct = max(cscore, key=lambda k: (cscore[k][0], -cscore[k][1]))
                apply(self.tpl[ct]["spec"], HINT, -2)
                hint_mode = True
            for m in cm:
                if m.section in ("moods", "actions"):
                    entry_votes(m.section, self.lex[m.section][m.name], -2, scale=HINT / MEANS[m.section])
                    hint_mode = True

        emph = sum(t.emph for t in toks)
        intensity *= 1.0 + min(bangs, 3) * 0.08 + min(emph, 1.5) * 0.12

        spec = StickerSpec()
        chosen = {}
        for slot, vs in votes.items():
            if vs:
                best = max(vs, key=lambda x: (x[0], x[1]))
                chosen[slot] = best
                setattr(spec, slot, best[2])
        self._settle(spec, chosen, votes)
        if "face" not in chosen and "motion" in chosen:       # a motion's own face when nothing else set one ("clapping" smiles)
            own = REG.motions[spec.motion].face
            if own:
                spec.face = own
        for slot, most, attr in (("props", MAX_PROPS, "props"), ("effects", MAX_EFFECTS, "effects"), ("accessories", MAX_WEAR, "accessories")):
            ranked = sorted(lists[slot], key=lambda x: (-x[0], x[1]))
            items = []
            for _, _, item in ranked:
                if item not in items and item not in banned[slot]:
                    items.append(item)
            setattr(spec, attr, items[:most])
        spec.palette = palette
        spec.tints = {k: v for k, v in tints.items() if k in spec.props or k in spec.accessories or k in spec.effects}
        spec.sides = {k: v for k, v in sides.items() if k in spec.props}
        if look is not None:
            spec.look = look
        if yaw is not None:
            spec.yaw = yaw
        if tempo is not None:
            spec.tempo = tempo
        spec.intensity = round(min(1.6, max(0.5, intensity)), 2)
        if caption:
            spec.caption = Caption(caption[:80])
        elif auto_caption and template and self.tpl[template].get("caption"):
            spec.caption = Caption(self.tpl[template]["caption"])
        spec.validate()
        notes, dropped_words = self._one_mascot(spec, used, words)

        # how much was understood
        content = [t.text for t in words if t.text not in self.stop and t.text not in self.neg and t.text != BREAK and not t.text.isdigit()
                   and len(t.text) > 1]
        unknown = [w for w, tk in zip([t.text for t in words], taken) if not tk and w in content]
        understood = sum(len(m.phrase.split()) for m in used if m.section not in ("strong", "weak") and not m.dropped)
        has_core = core or hint_mode or any(m.section in ("bases", "colours", "look", "view") for m in used) or bool(caption)
        confident = has_core and (len(unknown) <= max(1.0, 1.5 * understood) if (core or hint_mode) else not unknown)
        score_ = understood / max(1, understood + len(unknown) + dropped_words)
        suggestions = {}
        for w in unknown:
            if not is_word(w):
                near = self._near(w)
                if near:
                    suggestions[w] = near
        res = ParseResult(spec, used, unknown, template, confident, score=round(score_, 2), suggestions=suggestions, fixed=fixed,
                          notes=notes)
        return res

    # ---------------------------------------------------------------- helpers
    def _one_mascot(self, spec, used, words):
        """P34: a sticker draws one mascot for now.  Every other mascot named is marked as left out, and a note says what was
        kept; 'two foxes' or 'foxes' draws one fox and says so.  Returns (notes, number of words left out)."""
        kept = spec.base
        kept_as, others, plural, dropped_words = None, [], False, 0
        for m in used:
            if m.section != "bases" or m.negated:
                continue
            entry = self.lex["bases"][m.name]
            if self._split("bases", entry)[0].get("base", m.name) != kept:
                m.dropped = True
                dropped_words += len(m.phrase.split())
                singular = self._singular(m.phrase, entry)
                if singular not in others:
                    others.append(singular)
                continue
            kept_as = kept_as or self._singular(m.phrase, entry)
            before = {words[k].text for k in range(max(0, m.pos - 2), m.pos)}
            if before & PLURAL_WORDS or self._singular(m.phrase, entry) != m.phrase:
                plural = True

        animal = kept_as or (REG.bases[kept].animal if kept in REG.bases else kept)
        notes = []
        if others:
            left = others[0] if len(others) == 1 else ", ".join(others[:-1]) + " and " + others[-1]
            notes.append(f"one mascot fits in a sticker for now, so it's the {animal}; the {left} "
                         f"{'is' if len(others) == 1 else 'are'} left out")
        elif plural:
            notes.append(f"one mascot fits in a sticker for now, so there's one {animal}")
        return notes, dropped_words

    @staticmethod
    def _singular(phrase, entry):
        """'foxes' -> 'fox', 'polar bears' -> 'polar bear', 'kitties' -> 'kitty' when the singular is one of the entry's first
        three words (its plain nouns; later words include sounds such as 'meows'); anything else as it is."""
        nouns = [str(w) for w in entry.get("words", [])[:3]]
        for w in nouns:
            if phrase in (w + "s", w + "es") or (w.endswith("y") and phrase == w[:-1] + "ies"):
                return w
        return phrase
    def _split(self, section, entry):
        """(means, suggests) of a lexicon entry.  v3 entries have one `set:`: the slots the section owns are meant,
        the rest suggested.  v4 entries may say `means:` and `suggests:` themselves."""
        if "means" in entry or "suggests" in entry:
            return dict(entry.get("means", {})), dict(entry.get("suggests", {}))
        owns = OWNS[section]
        s = entry.get("set", {})
        strong = set(owns) | set(entry.get("strong", ()))
        return {k: v for k, v in s.items() if k in strong}, {k: v for k, v in s.items() if k not in strong}

    def _settle(self, spec, chosen, votes):
        """Make the scalar choices fit together: a motion that needs legs beats a stance that was only suggested."""
        m = REG.motions.get(spec.motion)
        st = chosen.get("stance")
        mo = chosen.get("motion")
        if m is None or st is None or spec.stance not in ("sit", "lotus"):
            return
        if m.sit == "no":
            if mo is not None and mo[0] >= st[0]:
                alts = [v for v in votes["stance"] if v[2] not in ("sit", "lotus")]
                spec.stance = max(alts, key=lambda x: (x[0], x[1]))[2] if alts else "stand"
            else:
                alts = [v for v in votes["motion"] if REG.motions[v[2]].sit != "no"]
                spec.motion = max(alts, key=lambda x: (x[0], x[1]))[2] if alts else "sway"

    def _colour(self, m, used):
        """The colour a colour match names, shifted by a modifier just before it ('light blue', 'dark red')."""
        value = m.name if m.name.startswith("#") else self._hex(m.name)
        shade = next((x for x in used if x.section == "shade" and x.end == m.pos), None)
        if shade and isinstance(value, str):
            from ..colour import _from_hls, _hls, to_hex, to_rgb
            h, l, s = _hls(to_rgb(value))
            l, s = {"light": (l + (1 - l) * 0.45, s * 0.9), "dark": (l * 0.6, s), "pastel": (l + (1 - l) * 0.55, s * 0.7),
                    "bright": (l, min(1.0, s * 1.25 + 0.1)), "pale": (l + (1 - l) * 0.6, s * 0.6), "deep": (l * 0.72, min(1.0, s * 1.1))
                    }.get(shade.name, (l, s))
            value = to_hex(_from_hls(h, l, s))
        return value.lower() if isinstance(value, str) else value

    def _hex(self, name):
        """'#rrggbb' of a colour name in the lexicon (v3 palettes: their main colour)."""
        value = self.lex["colours"][name]
        if isinstance(value, dict):
            value = value.get("hex") or value.get("orange")
        return hex6(value).lower()

    def _item_of(self, it):
        """Registry item named by a matched lexicon entry."""
        pos, end, section, name = it
        e = self.lex[section][name]
        means, _ = self._split(section, e)
        for slot in LIST_SLOTS:
            if means.get(slot):
                return means[slot][0]
        return None

    def _near(self, w):
        best, bd = None, 3
        from .typo import distance
        for cand in self.singles:
            if abs(len(cand) - len(w)) > 2 or cand[0] != w[0]:
                continue
            d = distance(w, cand, 2)
            if d < bd:
                best, bd = cand, d
        return best

    # ---------------------------------------------------------------- checks
    def problems(self):
        """Names in the YAML files that the registry does not know, and phrases that belong to two entries."""
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
            if not t.get("words"):
                bad.append(f"template {name}: no words")
        for section in SECTIONS:
            for name, e in self.lex[section].items():
                means, suggests = self._split(section, e)
                check(f"{section}.{name}", {**means, **suggests})
                if e.get("not") and e["not"] not in self.lex["moods"]:
                    bad.append(f"{section}.{name}: not -> unknown mood {e['not']!r}")
                if not e.get("words"):
                    bad.append(f"{section}.{name}: no words")
                w = e.get("weight", 1.0)
                if not isinstance(w, (int, float)) or not 0 < w <= 3:
                    bad.append(f"{section}.{name}: weight must be a number in (0, 3]")
                if e.get("colour") and e["colour"] not in self.lex["colours"]:
                    bad.append(f"{section}.{name}: colour {e['colour']!r} is not in colours")
                for w in e.get("words", ()):
                    if re.search(r"[a-z]_[a-z]|[a-z]_$", str(w)):
                        bad.append(f"{section}.{name}: {w!r} has an underscore (words are written as typed)")
        for src, dst in self.translations.items():
            missing = [w for w in self._norm(dst).split() if w not in self.known]
            if missing:
                bad.append(f"translations.{src}: {dst!r} has words the lexicon does not know: {missing}")
        for w, target in self.lex["alone"].items():
            sec, _, name = str(target).partition(".")
            if sec not in SECTIONS or name not in self.lex[sec]:
                bad.append(f"alone.{w}: {target!r} is not a lexicon entry (section.name)")
        small = self.stop | self.neg | FILLERS
        loose = ("strong", "weak", "filler", "shade", "side", "look", "view")
        for p, h in self.index.items():
            if h[0][0] in loose or not all(w in small for w in p.split()):
                continue
            if " " not in p:
                why = "is" if p in self._written else "becomes, once 'a', 'the', 'my' ... are dropped,"
                bad.append(f"phrase {p!r} ({h[0][0]}.{h[0][1]}) {why} a stopword: it would fire on every prompt that uses it")
        for name, e in self.lex["look"].items():
            if len(e.get("at", ())) != 2:
                bad.append(f"look.{name}: 'at' must be two numbers")
            if e.get("face") and e["face"] not in VOCAB["face"]:
                bad.append(f"look.{name}: unknown face {e['face']!r}")
        for name, e in self.lex["view"].items():
            y = e.get("yaw")
            if not isinstance(y, (int, float)) or not -180 <= y <= 180:
                bad.append(f"view.{name}: 'yaw' must be a number of degrees from -180 to 180")
            if not e.get("words"):
                bad.append(f"view.{name}: no words")
        for name, e in self.lex["colours"].items():
            v = e["hex"] if isinstance(e, dict) and "hex" in e else e
            if isinstance(v, str) and not re.fullmatch(r"#[0-9a-fA-F]{6}", v):
                bad.append(f"colours.{name}: {v!r} is not '#rrggbb'")
        lexical = ("moods", "actions", "props", "effects", "accessories", "poses", "bases", "colours", "strong", "weak", "tempo",
                   "side", "look", "view", "shade", "filler")
        for p, h in self.index.items():
            if BREAK in p.split():
                bad.append(f"phrase {p!r} ({h[0][0]}.{h[0][1]}) has a clause break in it ('but', 'though', punctuation) and can never match")
            secs = [s for s, _ in h if s in lexical]
            if len(secs) > 1:
                bad.append(f"phrase {p!r} is in several lexicon entries: {h}")
        return bad
