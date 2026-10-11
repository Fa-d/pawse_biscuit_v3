"""StickerSpec: the one structure every part of the studio agrees on.

The parser fills it from a prompt, the editor chips change it, the composer turns it into a clip.  Every value is a
*name* from the rig's vocabulary (expressions, arm poses, stances, tail poses) or from the studio's own lists
(motions, props, effects), never a coordinate, so a spec plays on any mascot.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from mascot.rig import FACES

ARM_POSES = ("rest", "relax", "wave_lo", "wave_hi", "cheer", "cheer_hi", "cheer_out", "chin", "mouth", "cheek", "belly", "lap",
             "hip", "hold", "hold_up", "carry", "edge", "ring", "knee", "lid", "cover_eyes", "peek", "stretch")
STANCES = ("stand", "wide", "sit", "lotus")
TAILS = ("rest", "out", "in", "up", "low", "floor", "flick_out", "flick_in", "curl", "ground", "ground_up", "wrap")
SIT_TAILS = ("ground", "ground_up", "wrap")
MOTIONS = ("idle", "bounce", "jump", "cheer", "wave", "dance", "walk", "nod", "no", "shiver", "sway", "sleep", "think", "hide")
PROPS = ("phone", "bell", "clipboard", "badge", "cloud", "gift", "mug", "heart")
EFFECTS = ("sparkles", "confetti", "zzz", "thought", "tear", "sweat", "hearts", "notes", "aura", "orbs", "rain", "anger")
ACCESSORIES = ("party_hat", "crown", "glasses", "sunglasses", "bow", "flower", "headphones", "scarf", "star_clip")
CAPTION_STYLES = ("outline", "bubble")
BASES = ("biscuit", "mochi", "bruno")          # fox, cat, bear (mascot/characters/)

VOCAB = dict(face=tuple(FACES), arm=ARM_POSES, stance=STANCES, tail=TAILS, motion=MOTIONS, props=PROPS, effects=EFFECTS,
             accessories=ACCESSORIES, base=BASES, caption_style=CAPTION_STYLES)


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

    def validate(self):
        """Raise ValueError on any name the rig does not know.  Returns self."""
        def need(kind, v, allowed):
            if v not in allowed:
                raise ValueError(f"unknown {kind} {v!r}; expected one of {', '.join(allowed)}")
        need("base", self.base, BASES)
        need("face", self.face, tuple(FACES))
        for a in (self.arm_L, self.arm_R):
            if a is not None:
                need("arm pose", a, ARM_POSES)
        need("stance", self.stance, STANCES)
        if self.tail is not None:
            need("tail pose", self.tail, TAILS)
        need("motion", self.motion, MOTIONS)
        for p in self.props:
            need("prop", p, PROPS)
        for e in self.effects:
            need("effect", e, EFFECTS)
        for w in self.accessories:
            need("accessory", w, ACCESSORIES)
        if self.caption is not None:
            need("caption style", self.caption.style, CAPTION_STYLES)
        if not 0.2 <= self.intensity <= 2.0:
            raise ValueError("intensity must be between 0.2 and 2.0")
        if not 1.0 <= self.seconds <= 3.0:
            raise ValueError("seconds must be between 1 and 3")
        return self

    # ---- (de)serialisation
    def to_dict(self):
        return asdict(self)

    def to_json(self, **kw):
        return json.dumps(self.to_dict(), **kw)

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        cap = d.pop("caption", None)
        if isinstance(cap, str):
            cap = Caption(cap)
        elif isinstance(cap, dict):
            cap = Caption(**cap)
        if "look" in d:
            d["look"] = tuple(d["look"])
        known = cls.__dataclass_fields__
        unknown = set(d) - set(known)
        if unknown:
            raise ValueError(f"unknown spec fields: {sorted(unknown)}")
        return cls(caption=cap, **d).validate()

    def key(self):
        """Stable hash of the spec, used to cache rendered files."""
        import hashlib
        return hashlib.blake2b(self.to_json(sort_keys=True).encode(), digest_size=10).hexdigest()
