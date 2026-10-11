"""Clips: channel tracks, easing and springs.

A clip never contains character coordinates.  It keys *channels* (numbers such as ``head.rot``)
and *named poses* (``arm.R -> 'wave_hi'``, ``tail -> 'rest'``); the character resolves those names.
"""
from __future__ import annotations

import math

import numpy as np

from .lottie import ease_eval

FPS = 60

# cubic-bezier easings (x1, y1, x2, y2)
BEZ = {
    "lin": None,
    "io": (0.42, 0.0, 0.58, 1.0),      # ease in-out
    "soft": (0.37, 0.0, 0.63, 1.0),    # sine-like
    "out": (0.2, 0.0, 0.2, 1.0),       # fast start, soft landing
    "in": (0.6, 0.0, 0.9, 1.0),        # slow start, fast end (falling)
    "back": (0.3, 0.0, 0.35, 1.45),    # overshoot then settle
    "bigback": (0.3, 0.0, 0.3, 1.8),
    "snap": (0.15, 0.0, 0.0, 1.0),     # very snappy
    "anti": (0.45, -0.45, 0.55, 1.0),  # wind up first
    "antiback": (0.5, -0.4, 0.3, 1.4),
    "inback": (0.6, -0.3, 0.75, 0.6),
}


def ease(name, x):
    """Evaluate a named easing at x in [0, 1]."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    if name == "hold":
        return 0.0
    if name == "sine":
        return 0.5 - 0.5 * math.cos(math.pi * x)
    if name == "elastic":  # overshoot and ring out
        return 1.0 - math.exp(-6.5 * x) * math.cos(2 * math.pi * 1.75 * x) * (1 - x) ** 0.5
    if name == "spring":   # softer ring
        return 1.0 - math.exp(-5.0 * x) * math.cos(2 * math.pi * 1.25 * x) * (1 - x) ** 0.5
    if name == "bounce":
        n1, d1 = 7.5625, 2.75
        if x < 1 / d1:
            return n1 * x * x
        if x < 2 / d1:
            x -= 1.5 / d1
            return n1 * x * x + 0.75
        if x < 2.5 / d1:
            x -= 2.25 / d1
            return n1 * x * x + 0.9375
        x -= 2.625 / d1
        return n1 * x * x + 0.984375
    b = BEZ[name]
    if b is None:
        return x
    return float(ease_eval(b, x))


class Track:
    """Keyframes (t, value, ease) where `ease` shapes the segment arriving at that key."""

    def __init__(self, default):
        self.default = default
        self.keys = []

    def key(self, t, v, e="io"):
        if isinstance(v, (list, tuple)):
            v = np.array(v, dtype=float)
        self.keys = [k for k in self.keys if k[0] != t] + [(t, v, e)]
        self.keys.sort(key=lambda k: k[0])
        return self

    def at(self, t):
        ks = self.keys
        if not ks:
            return self.default
        if t <= ks[0][0]:
            return ks[0][1]
        if t >= ks[-1][0]:
            return ks[-1][1]
        for a, b in zip(ks, ks[1:]):
            if a[0] <= t <= b[0]:
                if b[0] == a[0]:
                    return b[1]
                x = (t - a[0]) / (b[0] - a[0])
                return a[1] + (b[1] - a[1]) * ease(b[2], x)
        return ks[-1][1]


def spring_follow(target, freq=2.0, damp=0.35, loop=False, fps=FPS, sub=4):
    """Second-order follower: returns x(t) chasing target(t) with overshoot.

    freq in Hz (natural frequency), damp = damping ratio (<1 rings, 1 = no overshoot).
    """
    target = np.asarray(target, dtype=float)
    n = len(target)
    w = 2 * math.pi * freq / fps
    x = np.array(target[0], dtype=float)
    v = np.zeros_like(x)
    out = np.zeros_like(target)
    passes = 4 if loop else 1
    m = n - 1 if loop else n   # in a loop the last sample repeats the first
    for ps in range(passes):
        for f in range(m):
            a = target[f]
            b = target[(f + 1) % m] if loop else target[min(f + 1, n - 1)]
            out[f] = x
            for s in range(sub):
                tg = a + (b - a) * (s + 1) / sub
                acc = w * w * (tg - x) - 2 * damp * w * v
                v = v + acc / sub
                x = x + v / sub
    if loop:
        out[n - 1] = out[0]
    return out


def deriv(a, loop=False):
    """Per-frame central difference."""
    a = np.asarray(a, dtype=float)
    n = len(a)
    d = np.zeros_like(a)
    if loop:
        m = n - 1
        for f in range(m):
            d[f] = (a[(f + 1) % m] - a[(f - 1) % m]) / 2.0
        d[n - 1] = d[0]
    else:
        d[1:-1] = (a[2:] - a[:-2]) / 2.0
        d[0] = a[1] - a[0] if n > 1 else 0
        d[-1] = a[-1] - a[-2] if n > 1 else 0
    return d


class Clip:
    """Animation description, independent of any character."""

    def __init__(self, name, frames, loop=True, scale=1.0, char=None):
        self.char = char
        self.name = name
        self.frames = frames
        self.loop = loop
        self.scale = scale          # base size of the character inside the canvas
        self.tracks = {}            # channel -> Track
        self.adds = {}              # channel -> [fn(t)]
        self.props = []             # prop/fx specs (see props.py)
        self.opts = {}              # per-clip rig options (z order etc.)
        self.auto = {}              # overrides for automatic secondary motion gains
        self.pins = []              # paws planted on a fixed point of the scene (solved with IK per frame)
        self.settle = False         # True: ends exactly on its keyed pose (it hands over to another clip instead of looping)
        self.calm = 0               # frames over which follow-through is eased away around the loop point (base clips)

    # ---- keys
    def k(self, ch, *keys):
        """c.k('head.rot', (0, 0), (12, 8, 'back'), ...)"""
        tr = self.tracks.setdefault(ch, Track(None))
        for key in keys:
            t, v = key[0], key[1]
            e = key[2] if len(key) > 2 else "io"
            tr.key(t, v, e)
        return self

    def set(self, ch, v):
        self.tracks[ch] = Track(None).key(0, v)
        return self

    # ---- named poses (resolved by the character, so clips stay character independent)
    def arm(self, side, *keys):
        """c.arm('R', (0, 'rest'), (12, 'wave_hi', 'back'), ...)   side: 'L', 'R' or 'LR'.

        Also switches the depth slot (in front of / behind the head) and palm visibility that belong to the pose.
        """
        poses = []
        for key in keys:
            name = key[1]
            poses.append(self.char.pose(name) if isinstance(name, str) else dict(v=tuple(name), front=None, palm=None))
        for s in side:
            for q, key in enumerate(keys):
                t = key[0]
                e = key[2] if len(key) > 2 else "io"
                p = poses[q]
                self.k(f"arm.{s}", (t, np.array(p["v"], dtype=float), e))
                if p.get("front"):
                    # a paw that ever has to pass in front of the head stays in that slot for the whole clip
                    # (rest-like poses look the same in either slot, and one copy of the arm keeps files small)
                    self.set(f"arm.{s}.front", 1.0)
                if p.get("palm") is not None:
                    self.k(f"hand.{s}.palm", (t, 1.0 if p["palm"] else 0.0, e if e != "hold" else "hold"))
        return self

    def pin(self, side, t0, t1, at, hand=None, bend=1.0, blend=6):
        """Keep a paw's wrist on a canvas point (or fn(frame) -> point) from t0 to t1, easing in and out over `blend` frames."""
        for s in side:
            self.pins.append(dict(side=s, t0=t0, t1=t1, at=at, hand=hand, bend=bend, blend=blend))
        return self

    def tailpose(self, *keys):
        """c.tailpose((0, 'rest'), (20, 'up', 'back'))"""
        if self.char.tail is None:
            return self
        for key in keys:
            t, name = key[0], key[1]
            e = key[2] if len(key) > 2 else "io"
            self.k("tail", (t, self.char.tailvec(name), e))
        return self

    def stance(self, *keys):
        """c.stance((0, 'sit'))   How the lower body is arranged: 'stand' (default), 'sit', ... (resolved by the character)."""
        if getattr(self.char, "leg", None) is None:
            return self
        for key in keys:
            t, name = key[0], key[1]
            e = key[2] if len(key) > 2 else "io"
            self.k("stance", (t, self.char.stancevec(name), e))
        return self

    def wag(self, amp, period, lag=0.12, t0=0, t1=None, phase=0.0, taper=(0.5, 1.0), fade=0, fade_out=None):
        """Travelling wave down the tail.  amp in degrees per joint, lag in cycles per joint.
        fade = frames to ease in (and out, unless fade_out says otherwise; fade_out=0 keeps it going to the last frame)."""
        if self.char.tail is None:
            return self
        nj = self.char.tail_ctrl()
        t1 = self.frames if t1 is None else t1
        f_out = fade if fade_out is None else fade_out

        def fn(t):
            out = np.zeros(nj + 2)
            if t < t0 or t > t1:
                return out
            g = 1.0
            if fade:
                g = min(g, (t - t0) / fade)
            if f_out:
                g = min(g, (t1 - t) / f_out)
            g = 0.5 - 0.5 * math.cos(math.pi * max(g, 0.0))
            for j in range(nj):
                u = j / (nj - 1)
                a = amp * (taper[0] + (taper[1] - taper[0]) * u)
                out[j] = g * a * math.sin(2 * math.pi * ((t - t0) / period + phase - lag * j))
            return out

        return self.add("tail", fn)

    def face(self, t, name, dur=8, e="io", **over):
        """Blend every face channel to the named expression, arriving at frame t (starting dur frames earlier)."""
        from .rig import FACES
        vals = dict(FACES[name])
        vals.update({k.replace("_", "."): v for k, v in over.items()})
        from .rig import CHANNELS
        for ch, v in vals.items():
            tr = self.tracks.get(ch)
            if dur > 0 and t - dur >= 0:
                if tr and tr.keys:
                    earlier = [k[0] for k in tr.keys if k[0] <= t]
                    if earlier and max(earlier) <= t - dur:      # start the blend late, not from the previous key
                        self.k(ch, (t - dur, tr.at(t - dur), "hold"))
                else:
                    self.k(ch, (t - dur, CHANNELS[ch], "hold"))
            self.k(ch, (t, v, e))
        return self

    def blink(self, t, dur=9, side="LR"):
        """Quick blink that works on top of any expression."""
        for s in side:
            self.pulse(f"eye.{s}.blink", t, 1.0, up=max(2, dur * 4 // 9), down=max(3, dur - dur * 4 // 9), e_up="io", e_down="io")
        return self

    def ears(self, *keys):
        """Symmetric ear droop: positive = outwards / down."""
        for key in keys:
            t, v = key[0], key[1]
            e = key[2] if len(key) > 2 else "io"
            self.k("ear.R.rot", (t, v, e))
            self.k("ear.L.rot", (t, -v, e))
        return self

    def add(self, ch, fn):
        self.adds.setdefault(ch, []).append(fn)
        return self

    def osc(self, ch, amp, period, phase=0.0, t0=0, t1=None, shape="sin"):
        """Additive oscillation.  phase in cycles.  Fades are not applied: use full periods in loops."""
        t1 = self.frames if t1 is None else t1

        def fn(t, amp=amp, period=period, phase=phase):
            if t < t0 or t > t1:
                return 0.0
            x = (t - t0) / period + phase
            return amp * math.sin(2 * math.pi * x)

        return self.add(ch, fn)

    def pulse(self, ch, t0, amp, up=6, down=14, e_up="out", e_down="io"):
        """Additive bump: 0 -> amp over `up` frames, back to 0 over `down` frames."""

        def fn(t):
            if t <= t0 or t >= t0 + up + down:
                return 0.0
            if t <= t0 + up:
                return amp * ease(e_up, (t - t0) / up)
            return amp * (1 - ease(e_down, (t - t0 - up) / down))

        return self.add(ch, fn)

    def env(self, ch, fn):
        return self.add(ch, fn)

    def opt(self, **kw):
        self.opts.update(kw)
        return self

    def prop(self, spec):
        self.props.append(spec)
        return spec

    # ---- evaluation
    def sample(self, ch, default):
        """Array over frames 0..frames inclusive."""
        n = self.frames + 1
        tr = self.tracks.get(ch)
        adds = self.adds.get(ch, [])
        first = tr.at(0) if tr and tr.keys else default
        vec = isinstance(first, np.ndarray)
        out = np.zeros((n, len(first))) if vec else np.zeros(n)
        for f in range(n):
            v = tr.at(f) if tr and tr.keys else default
            for fn in adds:
                v = v + fn(f)
            out[f] = v
        return out
