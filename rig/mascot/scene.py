"""Scenes: one or two mascots in one Lottie document.

    from mascot.scene import Scene, Stage
    sc = Scene("comfort", frames=120)
    sc.add("a", Mochi(), clip_a, Stage(x=-66, y=-4, scale=0.74))           # the cat, a little behind
    sc.add("b", Clover(), clip_b, Stage(x=72, y=10, scale=0.74))           # the bunny, nearer the viewer
    sc.pin("a", "R", 26, 88, ("b", "head_side", "L"), hand=118, bend=-1, blend=8)   # the cat's paw on the bunny's head
    sc.lift("a", "right arm", over="b", t0=20, t1=94)                    # drawn over the bunny only around the pat
    doc = sc.build()

Every mascot is baked by its own Character, exactly as Character.build() does it, in three stages (prepare, finish,
bake).  The scene adds what one mascot never needed:

  * names: every layer of a mascot is prefixed with its id ('a/neck', 'b/neck') and its parents follow;
  * stages: each mascot hangs from its own null ('a/stage'), which places, scales and may mirror it;
  * depth: layers are ordered band by band (Character.DEPTH).  Effects over the head and paws that must sit on top
    come first for every mascot, then each mascot's own layers from the front one back, then effects behind the
    mascots, then the shadows.  A lift draws one layer of a mascot over another mascot, for the whole clip or only
    between two frames (two copies of the layer, swapped by hold keys);
  * pins across mascots: after every mascot is prepared, a paw can be solved towards a point on the other mascot
    (Scene.point), which moves with it frame by frame.

A scene of one mascot on a plain stage writes exactly the file Character.build() writes.
"""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass

import numpy as np

from .lottie import Anim, Layer, document, rolled

FRONT = ("paws_over", "top")              # bands drawn over every mascot (front mascot first)
UNDER = ("back",)                         # bands drawn under every mascot
LAST = ("shadow",)                        # the shadows, under everything


@dataclass(frozen=True)
class Stage:
    """Where a mascot stands in the scene: its ground point (CX, GROUND) moves by (x, y) canvas px, and the mascot is
    scaled about it.  y > 0 is lower on the canvas, nearer the viewer.  mirror draws it flipped left to right."""
    x: float = 0.0
    y: float = 0.0
    scale: float = 1.0
    mirror: bool = False

    @property
    def plain(self):
        return self == Stage()


@dataclass
class Actor:
    id: str
    char: object                          # a Character instance of its own (two mascots never share one)
    clip: object                          # mascot.clip.Clip made for that character
    stage: Stage
    order: int                            # added order; breaks depth ties


class Scene:
    def __init__(self, name="scene", frames=None, roll=0, fade_safe=None):
        self.name = name
        self.frames = frames
        self.roll = int(roll or 0)
        self.fade_safe = fade_safe
        self.actors = {}
        self.pins = []
        self.lifts = []
        self.extra = {"over": [], "under": []}      # scene-wide layers in scene coordinates
        self._prepared = False

    # ---------------------------------------------------------------- cast
    def add(self, id, char, clip, stage=Stage()):
        if id in self.actors:
            raise ValueError(f"a mascot called {id!r} is already in the scene")
        if not id or "/" in id:
            raise ValueError("a mascot's id is a short name without '/' (it prefixes its layer names)")
        if self.frames is None:
            self.frames = clip.frames
        if clip.frames != self.frames:
            raise ValueError(f"{id!r}: its clip has {clip.frames} frames, the scene {self.frames}")
        if any(a.char is char for a in self.actors.values()):
            raise ValueError(f"{id!r}: each mascot needs a Character instance of its own")
        self.actors[id] = a = Actor(id, char, clip, stage, len(self.actors))
        self._prepared = False
        return a

    def actor(self, id):
        if id not in self.actors:
            raise KeyError(f"no mascot {id!r} in the scene; it has {', '.join(self.actors) or 'none'}")
        return self.actors[id]

    def depth_order(self):
        """Mascots from the front back: lower on the canvas is nearer; a tie goes to the one added first."""
        return sorted(self.actors.values(), key=lambda a: (-a.stage.y, a.order))

    # ---------------------------------------------------------------- coordinates
    def to_scene(self, id, p):
        """A point in the mascot's own canvas coordinates -> scene (canvas) coordinates."""
        a = self.actor(id)
        st, cx, gy = a.stage, a.char.CX, a.char.GROUND
        k = -st.scale if st.mirror else st.scale
        return (cx + st.x + (p[0] - cx) * k, gy + st.y + (p[1] - gy) * st.scale)

    def to_local(self, id, p):
        """Scene coordinates -> the mascot's own canvas coordinates (inverse of to_scene)."""
        a = self.actor(id)
        st, cx, gy = a.stage, a.char.CX, a.char.GROUND
        k = -st.scale if st.mirror else st.scale
        return (cx + (p[0] - cx - st.x) / k, gy + (p[1] - gy - st.y) / st.scale)

    PARTS = ("crown", "top", "nose", "mouth", "chin", "eye", "cheek", "ear", "head_side", "collar", "chest", "belly", "back",
             "shoulder", "hip", "paw", "wrist", "foot", "ground")
    SIDED = ("eye", "cheek", "ear", "head_side", "back", "shoulder", "hip", "paw", "wrist", "foot")

    def point(self, id, part, f, side=None):
        """A named part of a mascot at frame f, in scene coordinates.  Sided parts ('paw', 'eye', ...) take side 'L' or
        'R' (the mascot's own left and right, as in the rig: 'R' is on screen right on an unmirrored stage).  Valid
        once the scene is prepared (and 'foot' once it is finished)."""
        a = self.actor(id)
        ch = a.char
        if getattr(ch, "T", None) is None or getattr(ch, "clip", None) is not a.clip:
            raise RuntimeError("Scene.point() needs the scene prepared first (Scene.prepare() or Scene.build())")
        if part not in self.PARTS:
            raise ValueError(f"unknown part {part!r}; expected one of {', '.join(self.PARTS)}")
        if part in self.SIDED and side not in ("L", "R"):
            raise ValueError(f"part {part!r} needs side='L' or 'R'")
        return self.to_scene(id, self._local_point(ch, part, f, side))

    @staticmethod
    def _local_point(ch, part, f, side):
        sgn = 1.0 if side == "R" else -1.0
        cx = ch.CX
        eye_r = ch.eye["R"]
        if part == "crown":
            return ch.head_to_world(f, ch.crown)
        if part == "top":
            return ch.top_world(f)
        if part == "nose":
            return ch.head_to_world(f, ch.nose)
        if part == "mouth":
            return ch.head_to_world(f, ch.mouth)
        if part == "chin":
            return ch.head_to_world(f, ch.neck)
        if part == "eye":
            return ch.head_to_world(f, ch.side(ch.eye, side))
        if part == "cheek":
            cheek = getattr(ch, "cheek", None) or {"R": (eye_r[0] + 38.0, eye_r[1] + 40.0)}
            return ch.head_to_world(f, ch.side(cheek, side))
        if part == "ear":
            return ch.head_to_world(f, ch.side(ch.ear_pivot, side))
        if part == "head_side":                         # the side of the skull above the eye, where a paw pats
            dx = 0.95 * (eye_r[0] - cx)
            y = ch.crown[1] + 0.4 * (eye_r[1] - ch.crown[1])
            return ch.head_to_world(f, (cx + sgn * dx, y))
        neck = ch.neck_at or ch.neck
        chest_y = (getattr(ch, "body_anchors", {}) or {}).get("chest", (cx, neck[1] + 40.0))[1]
        if part == "collar":
            return ch.body_to_world(f, ch.body_pt(f, ch.collar or (neck[0], neck[1] + 14.0)))
        if part == "chest":
            return ch.body_to_world(f, ch.body_pt(f, (cx, chest_y)))
        if part == "belly":
            belly_y = (getattr(ch, "body_anchors", {}) or {}).get("belly", (cx, ch.pelvis[1] - 30.0))[1]
            return ch.body_to_world(f, ch.body_pt(f, (cx, belly_y)))
        if part == "back":                              # the edge of the body at chest height (where a hug's paws go)
            half = max((dx for dx, _ in getattr(ch, "BODY_R", ())), default=70.0)
            return ch.body_to_world(f, ch.body_pt(f, (cx + sgn * half * 0.9, chest_y + 10.0)))
        if part == "shoulder":
            return ch.shoulder_world(side, f)
        if part == "hip":
            return ch.hip_world(side, f)
        if part == "paw":
            return ch.hand_to_world(side, f, tuple(ch.paw["c"]))
        if part == "wrist":
            return ch.hand_to_world(side, f, (0.0, 0.0))
        if part == "foot":
            if ch.leg is not None and not getattr(ch, "legs", None):
                raise RuntimeError("'foot' is known once the scene is finished (legs are solved after the pins)")
            return ch.foot_world(side, f)
        if part == "ground":
            return ch.root_to_world(f, (cx, ch.GROUND))
        raise AssertionError(part)

    # ---------------------------------------------------------------- what the scene adds
    def pin(self, id, side, t0, t1, target, hand=None, bend=1.0, blend=6, offset=None):
        """Keep a paw of mascot `id` on a target from frame t0 to t1 (easing in and out over `blend` frames).
        target: (other id, part[, side]) on any mascot of the scene, fn(frame) -> scene point, or a fixed scene point.
        offset: (dx, dy) or fn(frame) -> (dx, dy) in scene px, added to the target (a pat lifts the paw between taps).
        hand: the paw's heading in the mascot's own body space, as in Clip.pin."""
        self.actor(id)
        if isinstance(target, tuple) and target and isinstance(target[0], str):
            self.actor(target[0])
            if target[1] not in self.PARTS:
                raise ValueError(f"unknown part {target[1]!r}; expected one of {', '.join(self.PARTS)}")
        for s in side:
            self.pins.append(dict(id=id, side=s, t0=t0, t1=t1, target=target, hand=hand, bend=bend, blend=blend, offset=offset))
        return self

    def target(self, pin):
        """fn(frame) -> scene point of a pin's target, offset included."""
        tg, off = pin["target"], pin["offset"]
        if callable(tg):
            base = tg
        elif isinstance(tg, tuple) and tg and isinstance(tg[0], str):
            other, part = tg[0], tg[1]
            side = tg[2] if len(tg) > 2 else None
            base = lambda f, other=other, part=part, side=side: self.point(other, part, f, side)   # noqa: E731
        else:
            fixed = (float(tg[0]), float(tg[1]))
            base = lambda f: fixed                                                               # noqa: E731
        if off is None:
            return base
        return lambda f: (lambda p, d: (p[0] + d[0], p[1] + d[1]))(base(f), off(f) if callable(off) else off)

    def reach(self, pin, frames=None):
        """How far the paw must stretch for a pin, as a multiple of its rest length, at the worst frame (the rig's own
        poses go up to about 1.6; the IK caps at 1.7, beyond which the paw stops short).  Needs the scene prepared."""
        a = self.actor(pin["id"])
        ch, s = a.char, pin["side"]
        tg = self.target(pin)
        rest = ch.arm["L1"] + ch.arm["L2"]
        worst = 0.0
        for f in frames if frames is not None else range(pin["t0"], pin["t1"] + 1):
            bp = ch.world_to_body(f, self.to_local(a.id, tg(f)))
            sh = ch.shoulder_shown(s, f)                        # a drawn view's arm leaves its own shoulder
            worst = max(worst, math.hypot(bp[0] - sh[0], bp[1] - sh[1]) / rest)
        return worst

    def lift(self, id, layer, over, t0=None, t1=None):
        """Draw `layer` of mascot `id` over every layer of mascot `over`: always, or only from frame t0 to t1."""
        self.actor(id)
        self.actor(over)
        if (t0 is None) != (t1 is None):
            raise ValueError("a timed lift needs both t0 and t1")
        self.lifts.append(dict(id=id, layer=layer, over=over, t0=t0, t1=t1))
        return self

    def add_layers(self, region, layers):
        """Scene-wide layers in scene coordinates: region 'over' (above every mascot) or 'under' (below them)."""
        if region not in self.extra:
            raise ValueError("region is 'over' or 'under'")
        self.extra[region].extend(layers)
        return self

    # ---------------------------------------------------------------- building
    def prepare(self):
        """Stage 1 for every mascot, then the pins across mascots, in the order they were added."""
        if not self.actors:
            raise ValueError("an empty scene")
        with rolled(self.roll):
            for a in self.actors.values():
                a.char.prepare(a.clip)
            for pin in self.pins:
                a = self.actor(pin["id"])
                tg = self.target(pin)
                at = lambda f, a=a, tg=tg: self.to_local(a.id, tg(f))          # noqa: E731
                a.char.apply_pin_list([dict(side=pin["side"], t0=pin["t0"], t1=pin["t1"], at=at, hand=pin["hand"],
                                            bend=pin["bend"], blend=pin["blend"])])
        self._prepared = True
        return self

    def solo(self):
        """True when the scene is one mascot on a plain stage, with nothing added: it writes Character.build()'s file."""
        return len(self.actors) == 1 and next(iter(self.actors.values())).stage.plain and not self.lifts \
            and not self.extra["over"] and not self.extra["under"]

    def build(self):
        """The scene as one Lottie document."""
        self.prepare()
        solo = self.solo()
        with rolled(self.roll):
            baked = {}
            for a in self.actors.values():
                a.char.finish()
                baked[a.id] = a.char.bake(a.clip, self.roll)
            if not solo:
                for a in self.actors.values():
                    self._name(a, baked[a.id])
            lifted = self._lift(baked)
            layers = self._order(baked, lifted)
            if not solo:
                for a in self.actors.values():
                    st = a.stage
                    k = st.scale * 100.0
                    layers.append(Layer(f"{a.id}/stage", null=True, a=(a.char.CX, a.char.GROUND),
                                        p=(a.char.CX + st.x, a.char.GROUND + st.y), s=(-k if st.mirror else k, k)))
        fade = self.fade_safe if self.fade_safe is not None else any(a.clip.opts.get("fade_safe") for a in self.actors.values())
        return document(self.name, layers, op=self.frames, fade_safe=bool(fade))

    def _name(self, a, banded):
        """Prefix every layer of a mascot with its id; a layer without a parent hangs from the mascot's stage."""
        for _, L in banded:
            L.nm = f"{a.id}/{L.nm}"
            L.parent = f"{a.id}/{L.parent}" if L.parent is not None else f"{a.id}/stage"

    def _lift(self, baked):
        """Apply the lifts: {over id: [layers drawn above that mascot]}."""
        out = {}
        for lift in self.lifts:
            want = lift["layer"]
            banded = baked[lift["id"]]
            names = [L.nm for _, L in banded]
            full = want if want in names else f"{lift['id']}/{want}"
            hit = [q for q, (_, L) in enumerate(banded) if L.nm == full]
            if not hit:
                raise ValueError(f"mascot {lift['id']!r} has no layer {want!r}; it has {', '.join(n.split('/', 1)[-1] for n in names)}")
            band, L = banded[hit[0]]
            if lift["t0"] is None:                               # the whole clip: the layer simply moves
                del banded[hit[0]]
                out.setdefault(lift["over"], []).append(L)
                continue
            n = self.frames + 1
            inside = np.array([1.0 if lift["t0"] <= f <= lift["t1"] else 0.0 for f in range(n)])
            if inside[0] or inside[-1]:
                raise ValueError("a timed lift must start after frame 0 and end before the last frame (it cannot cross the loop point)")
            up = copy.copy(L)
            up.shapes = copy.deepcopy(L.shapes)                  # the two copies never share shape items
            up.nm = f"{L.nm} lifted"
            up.o = self._opacity(L.o, inside)
            L.o = self._opacity(L.o, 1.0 - inside)
            out.setdefault(lift["over"], []).append(up)
        return out

    def _opacity(self, o, mask):
        """A layer opacity (number or Anim) times a 0/1 mask, as hold keys (the swap must not blend)."""
        n = len(mask)
        if isinstance(o, Anim):
            if not o.hold and any(abs(float(v) - float(o.s[0])) > 1e-9 for v in o.s):
                raise ValueError("a timed lift cannot swap a layer that fades; lift it for the whole clip instead")
            base = o.s
        else:
            base = [float(o)] * n
        return Anim([float(v) * float(m) for v, m in zip(base, mask)], hold=True)

    def _order(self, baked, lifted):
        """Top-most first: over-everything bands of every mascot (front first), then each mascot from the front back with
        whatever is lifted over it on top, then the bands under every mascot, then the shadows."""
        front = self.depth_order()
        out = list(self.extra["over"])
        for a in front:
            out += [L for band, L in baked[a.id] if band in FRONT]
        for a in front:
            out += lifted.get(a.id, [])
            out += [L for band, L in baked[a.id] if band not in FRONT + UNDER + LAST]
        for a in front:
            out += [L for band, L in baked[a.id] if band in UNDER]
        out += list(self.extra["under"])
        for a in front:
            out += [L for band, L in baked[a.id] if band in LAST]
        return out
