"""The skeleton: channels every mascot understands, expression presets, and automatic secondary motion.

Angle conventions
  limb angles (arms):   0 = hanging straight down, positive = swinging OUTWARD/up, same number for both sides
  tail headings:        0 = pointing screen-right, positive = counter-clockwise (up)
  *.rot channels:       degrees, clockwise on screen (Lottie convention)
"""
from __future__ import annotations

import math

import numpy as np

from .clip import spring_follow

# ---------------------------------------------------------------- channels (name -> rest value)
CHANNELS = {
    # whole character (pivot on the ground between the feet)
    "root.x": 0.0, "root.y": 0.0, "root.rot": 0.0, "root.sx": 1.0, "root.sy": 1.0, "root.scale": 1.0,
    "root.pivot": 0.0,           # height above ground of the rotation pivot (use for flips)
    # pelvis: offset from where the stance puts it.  y > 0 = lower (bending the knees), rot tilts hips and torso together
    "hip.x": 0.0, "hip.y": 0.0, "hip.rot": 0.0,
    # torso (pivot at the pelvis)
    "body.x": 0.0, "body.y": 0.0, "body.rot": 0.0, "body.sx": 1.0, "body.sy": 1.0,
    # head (pivot at the neck)
    "head.x": 0.0, "head.y": 0.0, "head.rot": 0.0, "head.sx": 1.0, "head.sy": 1.0,
    "ear.L.rot": 0.0, "ear.R.rot": 0.0, "ear.L.sy": 1.0, "ear.R.sy": 1.0, "tuft.rot": 0.0,
    # face
    "eye.open": 1.0,             # 1 open .. 0 closed (a closed eye is drawn as an arc)
    "eye.arc": -0.45,            # closed-eye curve: +1 happy arch ^, 0 flat, -1 sleepy smile u
    "eye.w": 1.0, "eye.h": 1.0,  # eye size multipliers
    "eye.L.blink": 0.0, "eye.R.blink": 0.0,
    "look.x": 0.0, "look.y": 0.0,  # -1..1 gaze
    "eye.cross": 0.0,              # 0..1 eyes converge (looking at something on the nose)
    "brow.show": 0.0, "brow.y": 0.0, "brow.tilt": 0.0,  # tilt > 0 worried, < 0 determined
    "mouth.smile": 1.0,          # +1 cat smile, 0 flat, -1 frown
    "mouth.open": 0.0, "mouth.o": 0.0, "mouth.w": 1.0, "tongue": 0.0,
    "nose.y": 0.0, "nose.s": 1.0, "blush": 1.0,
    # arms: additive offsets on top of the named pose (arm.L / arm.R vector tracks)
    "arm.L.sh": 0.0, "arm.L.el": 0.0, "arm.L.wr": 0.0, "arm.L.len": 0.0,
    "arm.R.sh": 0.0, "arm.R.el": 0.0, "arm.R.wr": 0.0, "arm.R.len": 0.0,
    "hand.L.palm": 0.0, "hand.R.palm": 0.0,     # 1 = pads face the viewer
    "hand.L.s": 1.0, "hand.R.s": 1.0,
    "arm.L.front": 0.0, "arm.R.front": 0.0,     # 1 = drawn in front of the head
    "hand.L.over": 0.0, "hand.R.over": 0.0,     # 1 = paw also drawn above foreground props (clip option hands_over_top)
    # feet: offsets from where the stance puts them.  x > 0 = outwards, y > 0 = down (y < 0 lifts the foot),
    # rot > 0 = toes outwards, sole 1 = pads face the viewer, s = size (a foot coming towards the viewer grows)
    "foot.L.x": 0.0, "foot.L.y": 0.0, "foot.L.rot": 0.0, "foot.L.sole": 0.0, "foot.L.s": 1.0,
    "foot.R.x": 0.0, "foot.R.y": 0.0, "foot.R.rot": 0.0, "foot.R.sole": 0.0, "foot.R.s": 1.0,
    "leg.L.bend": 1.0, "leg.R.bend": 1.0,       # which way the knee goes: 1 outwards, -1 inwards (knock-kneed)
    # tail: additive on top of the named pose (tail vector track)
    "tail.len": 1.0, "tail.fluff": 1.0,
    "tail.front": 0.0,           # 0 behind the body, 1 in the lap (in front of the body, behind the feet), 2 in front of the feet
    # ground shadow
    "shadow.o": 1.0,
}

# ---------------------------------------------------------------- expressions
# Only face channels; any mascot with eyes, brows and a mouth can play them.
FACES = {
    "neutral":   {"eye.open": 1, "eye.arc": -0.45, "eye.w": 1, "eye.h": 1, "look.x": 0, "look.y": 0, "brow.show": 0, "brow.y": 0, "brow.tilt": 0,
                  "mouth.smile": 1, "mouth.open": 0, "mouth.o": 0, "tongue": 1, "blush": 1},
    "smiley":    {"eye.open": 1, "eye.arc": -0.45, "eye.w": 1, "eye.h": 1, "look.x": 0, "look.y": 0, "brow.show": 0, "brow.y": 0, "brow.tilt": 0,
                  "mouth.smile": 1, "mouth.open": 0.85, "mouth.o": 0, "tongue": 0, "blush": 1},
    "joy":       {"eye.open": 0, "eye.arc": 1.0, "eye.w": 1, "eye.h": 1, "look.x": 0, "look.y": 0, "brow.show": 0, "brow.y": 0, "brow.tilt": 0,
                  "mouth.smile": 1, "mouth.open": 1.0, "mouth.o": 0, "tongue": 0, "blush": 1.2},
    "worried":   {"eye.open": 1, "eye.arc": -0.45, "eye.w": 0.88, "eye.h": 0.84, "look.x": 0, "look.y": 0.25, "brow.show": 1, "brow.y": 0, "brow.tilt": 20,
                  "mouth.smile": -1, "mouth.open": 0, "mouth.o": 0, "tongue": 0, "blush": 0},
    "curious":   {"eye.open": 1, "eye.arc": -0.45, "eye.w": 1, "eye.h": 1, "look.x": 0.5, "look.y": -0.5, "brow.show": 0, "brow.y": 0, "brow.tilt": 0,
                  "mouth.smile": 0.3, "mouth.open": 0, "mouth.o": 1, "tongue": 0, "blush": 1},
    "sleep":     {"eye.open": 0, "eye.arc": -1.0, "eye.w": 1, "eye.h": 1, "look.x": 0, "look.y": 0, "brow.show": 0, "brow.y": 0, "brow.tilt": 0,
                  "mouth.smile": 0.15, "mouth.open": 0, "mouth.o": 0, "tongue": 0, "blush": 1},
    "calm":      {"eye.open": 0, "eye.arc": -1.0, "eye.w": 1, "eye.h": 1, "look.x": 0, "look.y": 0, "brow.show": 0, "brow.y": 0, "brow.tilt": 0,
                  "mouth.smile": 1, "mouth.open": 0, "mouth.o": 0, "tongue": 0, "blush": 1},
    "surprised": {"eye.open": 1, "eye.arc": -0.45, "eye.w": 1.14, "eye.h": 1.12, "look.x": 0, "look.y": 0, "brow.show": 1, "brow.y": 10, "brow.tilt": 6,
                  "mouth.smile": 0.3, "mouth.open": 0, "mouth.o": 1.15, "tongue": 0, "blush": 1},
    "focused":   {"eye.open": 0.6, "eye.arc": -0.45, "eye.w": 1, "eye.h": 1, "look.x": 0, "look.y": 0.35, "brow.show": 1, "brow.y": -4, "brow.tilt": -10,
                  "mouth.smile": 0.8, "mouth.open": 0, "mouth.o": 0, "tongue": 0, "blush": 0},
}
FACE_CHANNELS = sorted({k for f in FACES.values() for k in f})

# ---------------------------------------------------------------- stances
# A stance is how the lower body is arranged: 'stand', 'sit', ... .  Every mascot with legs defines the same names
# as one row of numbers in this order (right side; the left side mirrors):
STANCE = ("hip.y", "foot.x", "foot.y", "foot.rot", "foot.sole", "foot.s", "body.sy", "body.sx", "plant")
#   plant: 1 = feet stay on the ground while the body bounces above them, 0 = feet ride along with the body

# ---------------------------------------------------------------- secondary motion defaults
# Each mascot can override these numbers (floppy rabbit ears, stiff cat ears, no tail ...).
DYN = {
    "ear.freq": 2.6, "ear.damp": 0.28, "ear.rot": 0.9, "ear.x": 0.35, "ear.y": 0.42, "ear.max": 34.0,
    "tuft.freq": 2.0, "tuft.damp": 0.22, "tuft.rot": 1.2, "tuft.x": 0.6, "tuft.y": 0.0, "tuft.max": 40.0,
    "tail.freq": 1.7, "tail.damp": 0.30, "tail.y": 0.20, "tail.rot": 0.55, "tail.x": 0.16, "tail.max": 26.0,
    "wrist.freq": 3.0, "wrist.damp": 0.30, "wrist.gain": 0.8, "wrist.max": 28.0,
    "arm.freq": 2.4, "arm.damp": 0.35, "arm.y": 0.5, "arm.max": 30.0,
    "foot.freq": 3.0, "foot.damp": 0.35, "foot.drop": 12.0, "foot.rot": 12.0,      # mascots without legs: feet dangle
    "leg.freq": 4.2, "leg.damp": 0.42, "leg.reach": 0.16, "leg.kick": 0.5, "leg.rot": 9.0,   # mascots with legs
    "shadow.fade": 0.4,
}


def _clip(a, lim):
    return np.clip(a, -lim, lim)


def _soft(a, lim):
    """Soft limiter so big impulses saturate instead of clipping."""
    return lim * np.tanh(np.asarray(a) / lim)


def plant_feet(h, reach, freq, damp, loop, kick=0.55, fps=60, sub=4):
    """How far the feet reach below their stance position while the body rises `h` above the ground.

    While the legs can still reach, the feet stay planted and follow the ground exactly (ext == h).  When
    the body rises beyond `reach` the feet let go and spring back, overshooting into a tuck; on the way
    down they stretch towards the ground again, touch first and take the landing.
    """
    h = np.asarray(h, dtype=float)
    n = len(h)
    w = 2 * math.pi * freq / fps
    ext = np.zeros(n)
    m = n - 1 if loop else n
    if m <= 0:
        return ext
    planted, x, v = True, min(h[0], reach), 0.0
    for ps in range(3 if loop else 1):
        for f in range(m):
            hf = h[f]
            prev = h[(f - 1) % m] if loop else h[max(f - 1, 0)]
            nxt = h[(f + 1) % m] if loop else h[min(f + 1, n - 1)]
            if planted:
                if hf <= reach:
                    x, v = hf, 0.0
                else:                                      # out of reach: let go, still extending as fast as the body rose
                    planted = False
                    x, v = reach, min(max(hf - prev, 0.0), w * reach) * kick
            elif x >= hf and hf <= reach:                  # touched down
                planted, x, v = True, hf, 0.0
            x = min(x, hf)
            ext[f] = x
            if not planted:
                rising = nxt >= hf
                for q in range(sub):
                    hh = hf + (nxt - hf) * (q + 1) / sub
                    tgt = 0.0 if (rising or hh > 3.0 * reach) else min(hh, reach)
                    acc = w * w * (tgt - x) - 2 * damp * w * v
                    v += acc / sub
                    x += v / sub
    if loop:
        ext[n - 1] = ext[0]
    return ext


def evaluate(clip, char):
    """Sample every channel of a clip and layer the automatic follow-through on top."""
    n = clip.frames + 1
    # springs: a looping clip runs them round the loop; a clip that hands over to another one (clip.settle)
    # starts them at rest and eases them out, so its last frame is exactly the pose that was keyed
    loop = clip.loop and not getattr(clip, "settle", False)
    T = {ch: clip.sample(ch, d) for ch, d in CHANNELS.items()}
    T["root.scale"] = T["root.scale"] * clip.scale * getattr(char, "base_scale", 1.0)
    g = dict(DYN)
    g.update(getattr(char, "dyn", {}))
    g.update(clip.auto)
    legs = getattr(char, "leg", None) is not None

    # ---- named poses
    for side in "LR":
        arr = clip.sample(f"arm.{side}", np.array(char.pose("rest")["v"], dtype=float))
        T[f"arm.{side}.sh"] = T[f"arm.{side}.sh"] + arr[:, 0]
        T[f"arm.{side}.el"] = T[f"arm.{side}.el"] + arr[:, 1]
        T[f"arm.{side}.wr"] = T[f"arm.{side}.wr"] + arr[:, 2]
        T[f"arm.{side}.len"] = T[f"arm.{side}.len"] + arr[:, 3]
    if char.tail is not None:
        T["tail"] = clip.sample("tail", char.tailvec("rest"))
    T["plant"] = np.zeros(n)
    if legs:
        st = clip.sample("stance", char.stancevec("stand"))
        T["hip.y"] = T["hip.y"] + st[:, 0]
        for side in "LR":
            T[f"foot.{side}.x"] = T[f"foot.{side}.x"] + st[:, 1]
            T[f"foot.{side}.y"] = T[f"foot.{side}.y"] + st[:, 2]
            T[f"foot.{side}.rot"] = T[f"foot.{side}.rot"] + st[:, 3]
            T[f"foot.{side}.sole"] = T[f"foot.{side}.sole"] + st[:, 4]
            T[f"foot.{side}.s"] = T[f"foot.{side}.s"] * st[:, 5]
        T["body.sy"] = T["body.sy"] * st[:, 6]
        T["body.sx"] = T["body.sx"] * st[:, 7]
        T["plant"] = st[:, 8]

    # ---- driving signals (approximate world motion of the head top and of the hips)
    lever = float(getattr(char, "head_lever", 150.0))
    sc = np.maximum(T["root.scale"], 0.2)
    hrot = T["root.rot"] + T["hip.rot"] + T["body.rot"] + T["head.rot"]
    hy = T["root.y"] / sc + T["hip.y"] + T["body.y"] + T["head.y"]
    hy = hy - (T["root.sy"] - 1.0) * 330.0 - (T["head.sy"] - 1.0) * 120.0   # squash moves the head too
    hx = T["root.x"] + T["hip.x"] + T["body.x"] + T["head.x"] + lever * np.sin(np.radians(hrot))
    ry = T["root.y"] / sc + T["hip.y"] - (T["root.sy"] - 1.0) * 60.0
    rrot = T["root.rot"] + T["hip.rot"] + T["body.rot"]
    rx = T["root.x"] + T["hip.x"] + T["body.x"]

    # window that takes the follow-through to zero at the ends that have to match another clip's first frame
    win = np.ones(n)
    n_in = int(getattr(clip, "calm", 0))
    n_out = max(n_in, 14 if getattr(clip, "settle", False) else 0)
    for q in range(n):
        w = 1.0
        if n_in:
            w = min(w, q / float(n_in))
        if n_out:
            w = min(w, (n - 1 - q) / float(n_out))
        win[q] = 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, w)))

    def lag(sig, freq, damp):
        d = sig - spring_follow(sig, freq, damp, loop=loop)
        return d * (win if d.ndim == 1 else win[:, None])

    # ---- ears and tuft
    for part, chans in (("ear", ["ear.L.rot", "ear.R.rot"]), ("tuft", ["tuft.rot"])):
        f, d = g[part + ".freq"], g[part + ".damp"]
        lr, lx, ly = lag(hrot, f, d), lag(hx, f, d), lag(hy, f, d)
        common = -lr * g[part + ".rot"] - lx * g[part + ".x"]
        flop = -ly * g[part + ".y"]          # moving up -> ears pushed down/outwards
        for ch in chans:
            sgn = 1.0 if ".R." in ch else (-1.0 if ".L." in ch else 0.0)
            T[ch] = T[ch] + _soft(common + sgn * flop, g[part + ".max"])

    # ---- arms swing with vertical motion; wrists flop behind the forearm
    for side in "LR":
        ly = lag(hy, g["arm.freq"], g["arm.damp"])
        T[f"arm.{side}.sh"] = T[f"arm.{side}.sh"] + _soft(ly * g["arm.y"], g["arm.max"])
        fore = T[f"arm.{side}.sh"] + T[f"arm.{side}.el"]
        lw = lag(fore, g["wrist.freq"], g["wrist.damp"])
        T[f"arm.{side}.wr"] = T[f"arm.{side}.wr"] - _soft(lw * g["wrist.gain"], g["wrist.max"])

    # ---- legs and feet
    height = np.clip(-T["root.y"], 0, None) / np.maximum(T["root.scale"] * T["root.sy"], 0.2)   # body above the ground, in root units
    if legs:
        # planted feet stay on the ground while the body bounces; beyond the legs' reach they let go, tuck and reach back
        reach = g["leg.reach"] * char.leg_len
        ext = plant_feet(height, reach, g["leg.freq"], g["leg.damp"], loop, kick=g["leg.kick"])
        ext = np.where(height > 1e-6, ext, ext * win)      # nothing left over once the clip has settled on the ground
        off = np.clip((height - ext) / max(reach, 1e-6), 0.0, 1.0)          # 0 on the ground .. 1 clearly airborne
        T["air"] = off
        for side in "LR":   # toes turn in a little while the feet hang
            T[f"foot.{side}.y"] = T[f"foot.{side}.y"] + ext * T["plant"]
            T[f"foot.{side}.rot"] = T[f"foot.{side}.rot"] - off * T["plant"] * g["leg.rot"]
            T[f"foot.{side}.y"] = np.minimum(T[f"foot.{side}.y"], height)     # never through the floor
    else:
        air = np.clip(-ry / 36.0, 0.0, 1.0)
        airf = spring_follow(air, g["foot.freq"], g["foot.damp"], loop=loop)
        T["air"] = airf
        for side in "LR":   # foot.rot > 0 means toes splay outwards on either side
            T[f"foot.{side}.y"] = T[f"foot.{side}.y"] + airf * g["foot.drop"]
            T[f"foot.{side}.rot"] = T[f"foot.{side}.rot"] - airf * g["foot.rot"]

    # ---- tail: every joint trails the hips, softer and later towards the tip
    if char.tail is not None:
        nj = char.tail_ctrl()                    # the two extra numbers are the base offset
        dyn = np.zeros((n, T["tail"].shape[1]))
        for j in range(nj):
            u = j / max(nj - 1, 1)
            f = g["tail.freq"] * (1.0 - 0.45 * u)
            d = g["tail.damp"]
            w = 0.55 + 0.45 * u
            dyn[:, j] = w * (lag(ry, f, d) * g["tail.y"] + lag(rrot, f, d) * g["tail.rot"] + lag(rx, f, d) * g["tail.x"])
        T["tail"] = T["tail"] + _soft(dyn, g["tail.max"])

    # ---- shadow shrinks as the character leaves the ground
    rise = np.clip(-T["root.y"], 0, None)
    T["shadow.s"] = T["root.scale"] * (1.0 - g["shadow.fade"] * np.clip(rise / 150.0, 0, 1)) * (0.6 + 0.4 * T["root.sx"])
    T["shadow.s"] = np.where(T["root.scale"] < 0.02, 0.0, T["shadow.s"])
    return T
