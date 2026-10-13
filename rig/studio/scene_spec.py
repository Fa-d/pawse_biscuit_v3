"""SceneSpec: one or two mascots in a sticker, plus what they share.

    SceneSpec(actors=[ActorSpec(base="mochi", motion="wave"), ActorSpec(base="pip", motion="dance")],
              caption=Caption("besties"), seconds=2.0)

An ActorSpec holds everything a StickerSpec says about its one mascot (base, colours, face, arms, stance, tail,
gaze, props, effects, worn things, motion, intensity, tints, sides and, from v5, the yaw it is turned by).  The scene holds what the mascots share: the
caption, the loop length, the tempo, scene-wide effects and, from phase 3 on, the duet they play.

Old specs keep working: a v3 or v4 StickerSpec loads as a scene of one mascot, and a scene of one mascot writes back
in the v4 shape with the same key(), so saved stickers and cached files stay as they are.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, fields

from .registry import ensure_loaded
from .spec import EFFECTS, HARD_EFFECTS, Caption, StickerSpec

REG = ensure_loaded()

MAX_ACTORS = 2
SHARED = ("caption", "seconds", "tempo")
ACTOR_FIELDS = tuple(f.name for f in fields(StickerSpec) if f.name not in SHARED)


@dataclass
class ActorSpec:
    """One mascot of a scene: the per-mascot fields of a StickerSpec, with the same names and defaults."""
    base: str = "biscuit"
    palette: dict = field(default_factory=dict)
    face: str = "smiley"
    arm_L: str | None = None
    arm_R: str | None = None
    stance: str = "stand"
    tail: str | None = None
    look: tuple = (0.0, 0.0)
    props: list = field(default_factory=list)
    effects: list = field(default_factory=list)
    accessories: list = field(default_factory=list)
    motion: str = "idle"
    intensity: float = 1.0
    tints: dict = field(default_factory=dict)
    sides: dict = field(default_factory=dict)
    yaw: float = 0.0

    def sticker(self, caption=None, seconds=2.0, tempo=1.0) -> StickerSpec:
        """This mascot as a v4 StickerSpec, with the scene's shared values."""
        return StickerSpec(caption=caption, seconds=seconds, tempo=tempo, **{k: getattr(self, k) for k in ACTOR_FIELDS})

    @classmethod
    def of(cls, s: StickerSpec):
        return cls(**{k: getattr(s, k) for k in ACTOR_FIELDS})


assert set(ACTOR_FIELDS) == {f.name for f in fields(ActorSpec)}, "ActorSpec must have exactly the per-mascot fields of StickerSpec"


@dataclass
class SceneSpec:
    actors: list = field(default_factory=lambda: [ActorSpec()])
    duet: str | None = None                           # a registered duet (phase 3); None: each mascot plays its own motion
    effects: list = field(default_factory=list)       # scene-wide effects (phase 1: drawn by the mascot in front, rule S07)
    caption: Caption | None = None
    seconds: float = 2.0
    tempo: float = 1.0

    # ---- one mascot: exactly a v4 sticker
    @classmethod
    def from_sticker(cls, s: StickerSpec):
        return cls(actors=[ActorSpec.of(s)], caption=s.caption, seconds=s.seconds, tempo=s.tempo)

    @property
    def solo(self):
        return len(self.actors) == 1 and self.duet is None

    def sticker(self) -> StickerSpec:
        """A scene of one mascot as the v4 StickerSpec it is (scene-wide effects join the mascot's own)."""
        if not self.solo:
            raise ValueError("only a scene of one mascot without a duet is a v4 sticker")
        a = self.actors[0]
        s = a.sticker(self.caption, self.seconds, self.tempo)
        s.effects = list(dict.fromkeys(list(a.effects) + list(self.effects)))
        return s

    def stickers(self):
        """One v4 StickerSpec per mascot, each carrying the scene's loop length and tempo but no caption (the scene has it)."""
        return [a.sticker(None, self.seconds, self.tempo) for a in self.actors]

    # ---- checks
    def validate(self):
        if not isinstance(self.actors, list) or not self.actors:
            raise ValueError("a scene needs one or two mascots")
        if len(self.actors) > MAX_ACTORS:
            raise ValueError(f"at most {MAX_ACTORS} mascots in a sticker; this has {len(self.actors)}")
        for q, a in enumerate(self.actors):
            if not isinstance(a, ActorSpec):
                raise ValueError(f"mascot {q + 1} must be an ActorSpec")
            try:
                a.sticker(self.caption, self.seconds, self.tempo).validate()
            except ValueError as e:
                raise ValueError(f"mascot {q + 1}: {e}") from None
        duets = getattr(REG, "duets", {})
        if self.duet is not None and self.duet not in duets:
            raise ValueError(f"unknown duet {self.duet!r}; expected one of {', '.join(duets) or '(none yet)'}")
        if not isinstance(self.effects, (list, tuple)):
            raise ValueError("effects must be a list of names")
        for e in self.effects:
            if e not in EFFECTS:
                raise ValueError(f"unknown effect {e!r}; expected one of {', '.join(EFFECTS)}")
        if len(set(self.effects)) > HARD_EFFECTS:
            raise ValueError(f"at most {HARD_EFFECTS} scene-wide effects")
        StickerSpec(caption=self.caption, seconds=self.seconds, tempo=self.tempo).validate()     # caption, loop length, tempo
        return self

    def normalized(self):
        """A validated copy; each mascot normalised as a StickerSpec is (repeats removed, colours as '#rrggbb')."""
        self.validate()
        acts = [ActorSpec.of(a.sticker(None, self.seconds, self.tempo).normalized()) for a in self.actors]
        cap = StickerSpec(caption=self.caption).normalized().caption
        return SceneSpec(actors=acts, duet=self.duet, effects=list(dict.fromkeys(self.effects)), caption=cap, seconds=self.seconds,
                         tempo=self.tempo)

    # ---- (de)serialisation
    def to_dict(self):
        if self.solo:
            return self.sticker().to_dict()
        actors = [{k: v for k, v in asdict(a).items() if k != "yaw" or v} for a in self.actors]    # yaw only when turned
        return dict(actors=actors, duet=self.duet, effects=list(self.effects),
                    caption=asdict(self.caption) if self.caption is not None else None, seconds=self.seconds, tempo=self.tempo)

    def to_json(self, **kw):
        return json.dumps(self.to_dict(), **kw)

    @classmethod
    def from_dict(cls, d):
        """A scene dict ({'actors': [...], ...}) or any v3 / v4 sticker dict."""
        if not isinstance(d, dict):
            raise ValueError("a spec must be a JSON object")
        if "actors" not in d:
            return cls.from_sticker(StickerSpec.from_dict(d))
        d = dict(d)
        unknown = set(d) - {"actors", "duet", "effects", "caption", "seconds", "tempo"}
        if unknown:
            raise ValueError(f"unknown scene fields: {sorted(unknown)}")
        raw = d.pop("actors")
        if not isinstance(raw, list):
            raise ValueError("actors must be a list of mascots")
        acts = []
        for q, a in enumerate(raw):
            if not isinstance(a, dict):
                raise ValueError(f"mascot {q + 1} must be a JSON object")
            extra = set(a) - set(ACTOR_FIELDS)
            if extra:
                raise ValueError(f"mascot {q + 1}: unknown fields {sorted(extra)} (caption, seconds and tempo belong to the scene)")
            s = StickerSpec.from_dict(dict(a))                 # the v4 checks and conversions (look as a tuple, lists ...)
            acts.append(ActorSpec.of(s))
        cap = d.pop("caption", None)
        shared = StickerSpec.from_dict({"caption": cap, **{k: d[k] for k in ("seconds", "tempo") if k in d}})
        effects = d.get("effects", [])
        if isinstance(effects, tuple):
            effects = list(effects)
        return cls(actors=acts, duet=d.get("duet"), effects=effects, caption=shared.caption, seconds=shared.seconds,
                   tempo=shared.tempo).validate()

    def key(self):
        """Stable hash: a scene of one mascot has its v4 StickerSpec's key, so cached and saved stickers keep theirs."""
        if self.solo:
            return self.sticker().key()
        return hashlib.blake2b(self.to_json(sort_keys=True).encode(), digest_size=10).hexdigest()
