"""StickerSpec: the one structure every part of the studio agrees on.

The parser fills it from a prompt, the editor chips change it, the composer turns it into a clip.  Every value is a
*name* from the registry (studio/registry.py: motions, props, effects, worn items, faces, mascots) or the rig's
own vocabulary (stances, tail poses, arm poses), never a coordinate, so a spec plays on any mascot.

v4 added three optional fields, all with defaults, so every saved v3 spec still loads:
  tints   {item: '#rrggbb'}   the colour of one prop, effect or worn item ("a red scarf")
  sides   {prop: 'L' | 'R'}   which paw holds a prop ("coffee in the left paw")
  tempo   0.5 .. 2.0          how fast the motion goes (1 = normal)
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field, replace

from .registry import ensure_loaded

REG = ensure_loaded()

ARM_POSES = tuple(REG.arm_poses)
STANCES = tuple(REG.stances)
TAILS = tuple(REG.tails)
SIT_TAILS = ("ground", "ground_up", "wrap")
MOTIONS = tuple(REG.motions)
PROPS = tuple(REG.props)
EFFECTS = tuple(REG.effects)
ACCESSORIES = tuple(REG.wear)
FACE_NAMES = tuple(REG.faces)
CAPTION_STYLES = ("outline", "bubble")
CAPTION_POS = ("bottom", "top")
BASES = tuple(REG.bases)
MAX_PROPS, MAX_EFFECTS, MAX_WEAR = 2, 3, 3        # what a sticker uses (the composer keeps the first ones, with a note)
HARD_PROPS, HARD_EFFECTS, HARD_WEAR = 4, 6, 6     # what a spec may list at all
MAX_CAPTION = 80
HEX = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")

VOCAB = dict(face=FACE_NAMES, arm=ARM_POSES, stance=STANCES, tail=TAILS, motion=MOTIONS, props=PROPS, effects=EFFECTS,
             accessories=ACCESSORIES, base=BASES, caption_style=CAPTION_STYLES)

_PAL_KEYS = None


def palette_keys():
    """Colour slots a palette override may set: the colour keys every mascot's palette has."""
    global _PAL_KEYS
    if _PAL_KEYS is None:
        keys = None
        for b in REG.bases.values():
            ks = {k for k, v in b.load().pal.items() if isinstance(v, (list, tuple)) and len(v) == 3}
            keys = ks if keys is None else keys & ks
        _PAL_KEYS = frozenset((keys or set()) | {"tail_ring", "paw"})
    return _PAL_KEYS


def hex6(v):
    """'#abc' -> '#aabbcc'; anything else unchanged."""
    if isinstance(v, str) and len(v) == 4 and v.startswith("#"):
        return "#" + "".join(ch * 2 for ch in v[1:])
    return v


@dataclass
class Caption:
    text: str
    style: str = "outline"
    pos: str = "bottom"          # 'bottom' or 'top'


@dataclass
class StickerSpec:
    base: str = "biscuit"
    palette: dict = field(default_factory=dict)       # pal key -> '#rrggbb' overrides
    face: str = "smiley"
    arm_L: str | None = None                          # None: let the composer choose (rest, or what a motion / prop needs)
    arm_R: str | None = None
    stance: str = "stand"
    tail: str | None = None
    look: tuple = (0.0, 0.0)
    props: list = field(default_factory=list)
    effects: list = field(default_factory=list)
    accessories: list = field(default_factory=list)
    motion: str = "idle"
    intensity: float = 1.0                            # 0.5 subtle .. 1.5 big
    caption: Caption | None = None
    seconds: float = 2.0                              # loop length (Telegram allows up to 3 s)
    tints: dict = field(default_factory=dict)         # v4: item -> '#rrggbb'
    sides: dict = field(default_factory=dict)         # v4: prop -> 'L' or 'R'
    tempo: float = 1.0                                # v4: 0.5 slow .. 2 fast

    def validate(self):
        """Raise ValueError on any name the rig does not know or any value it cannot draw.  Returns self."""
        def need(kind, v, allowed):
            if not isinstance(v, str) or v not in allowed:
                raise ValueError(f"unknown {kind} {v!r}; expected one of {', '.join(allowed)}")

        def number(kind, v, lo, hi):
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError(f"{kind} must be a number")
            if not lo <= v <= hi:
                raise ValueError(f"{kind} must be between {lo} and {hi}")

        def names(kind, one, vs, allowed, most):
            if not isinstance(vs, (list, tuple)):
                raise ValueError(f"{kind} must be a list of names")
            for v in vs:
                need(one, v, allowed)
            if len(set(vs)) > most:
                raise ValueError(f"at most {most} {kind}; this has {len(set(vs))}")

        need("base", self.base, BASES)
        need("face", self.face, FACE_NAMES)
        for a in (self.arm_L, self.arm_R):
            if a is not None:
                need("arm pose", a, ARM_POSES)
        need("stance", self.stance, STANCES)
        if self.tail is not None:
            need("tail pose", self.tail, TAILS)
        need("motion", self.motion, MOTIONS)
        names("props", "prop", self.props, PROPS, HARD_PROPS)
        names("effects", "effect", self.effects, EFFECTS, HARD_EFFECTS)
        names("accessories", "accessory", self.accessories, ACCESSORIES, HARD_WEAR)
        if not isinstance(self.palette, dict):
            raise ValueError("palette must map colour slots to '#rrggbb' colours")
        for k, v in self.palette.items():
            if k not in palette_keys():
                raise ValueError(f"unknown palette key {k!r}; expected one of {', '.join(sorted(palette_keys()))}")
            if not isinstance(v, str) or not HEX.match(v):
                raise ValueError(f"palette colour for {k!r} must look like '#ff8a3d', not {v!r}")
        if not isinstance(self.tints, dict):
            raise ValueError("tints must map items to '#rrggbb' colours")
        for k, v in self.tints.items():
            if k not in PROPS and k not in EFFECTS and k not in ACCESSORIES:
                raise ValueError(f"tint for unknown item {k!r}")
            if not isinstance(v, str) or not HEX.match(v):
                raise ValueError(f"tint for {k!r} must look like '#ff8a3d', not {v!r}")
        if not isinstance(self.sides, dict):
            raise ValueError("sides must map props to 'L' or 'R'")
        for k, v in self.sides.items():
            need("prop", k, PROPS)
            if v not in ("L", "R"):
                raise ValueError(f"side for {k!r} must be 'L' or 'R'")
        look = tuple(self.look) if isinstance(self.look, (list, tuple)) else None
        if look is None or len(look) != 2:
            raise ValueError("look must be two numbers (x, y), each between -1.5 and 1.5")
        for v in look:
            number("look", v, -1.5, 1.5)
        if self.caption is not None:
            if not isinstance(self.caption, Caption) or not isinstance(self.caption.text, str):
                raise ValueError("caption must have a text")
            if len(self.caption.text) > MAX_CAPTION:
                raise ValueError(f"captions are at most {MAX_CAPTION} characters")
            need("caption style", self.caption.style, CAPTION_STYLES)
            need("caption position", self.caption.pos, CAPTION_POS)
        number("intensity", self.intensity, 0.2, 2.0)
        number("seconds", self.seconds, 1.0, 3.0)
        number("tempo", self.tempo, 0.5, 2.0)
        return self

    def normalized(self):
        """A validated copy with repeats removed, colours as '#rrggbb' and empty captions dropped."""
        self.validate()
        dedupe = lambda xs: list(dict.fromkeys(xs))
        cap = self.caption
        if cap is not None:
            text = " ".join("".join(ch for ch in cap.text if ch.isprintable()).split())
            cap = Caption(text, cap.style, cap.pos) if text else None
        return replace(self, props=dedupe(self.props), effects=dedupe(self.effects), accessories=dedupe(self.accessories),
                       palette={k: hex6(v).lower() for k, v in self.palette.items()},
                       tints={k: hex6(v).lower() for k, v in self.tints.items()}, sides=dict(self.sides),
                       look=(float(self.look[0]), float(self.look[1])), caption=cap)

    # ---- (de)serialisation
    def to_dict(self):
        return asdict(self)

    def to_json(self, **kw):
        return json.dumps(self.to_dict(), **kw)

    @classmethod
    def from_dict(cls, d):
        if not isinstance(d, dict):
            raise ValueError("a spec must be a JSON object")
        d = dict(d)
        cap = d.pop("caption", None)
        if isinstance(cap, str):
            cap = Caption(cap)
        elif isinstance(cap, dict):
            extra = set(cap) - {"text", "style", "pos"}
            if extra or "text" not in cap:
                raise ValueError(f"a caption has text, style and pos; got {sorted(cap)}")
            cap = Caption(**cap)
        elif cap is not None:
            raise ValueError("caption must be text or {text, style, pos}")
        if "look" in d:
            if not isinstance(d["look"], (list, tuple)):
                raise ValueError("look must be two numbers")
            d["look"] = tuple(d["look"])
        known = cls.__dataclass_fields__
        unknown = set(d) - set(known)
        if unknown:
            raise ValueError(f"unknown spec fields: {sorted(unknown)}")
        for k in ("props", "effects", "accessories"):
            if k in d and isinstance(d[k], tuple):
                d[k] = list(d[k])
        return cls(caption=cap, **d).validate()

    def key(self):
        """Stable hash of the spec, used to cache rendered files."""
        import hashlib
        return hashlib.blake2b(self.to_json(sort_keys=True).encode(), digest_size=10).hexdigest()
