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
    # ---- added in v4.  At these rest values every file draws exactly what it drew before they existed.
    # brows, one at a time: offsets on top of brow.y / brow.tilt (a raised eyebrow, a skeptical look)
    "brow.L.y": 0.0, "brow.R.y": 0.0, "brow.L.tilt": 0.0, "brow.R.tilt": 0.0,
    # eye shape, held (not blended): 0 normal, 1 heart, 2 star, 3 spiral, 4 cross (x x), 5 squeezed shut (> <),
    # 6 sparkling (extra highlights on the normal eye)
    "eye.style": 0.0,
    "eye.spin": 0.0,             # degrees: turns spiral and star eyes
    "eye.L.s": 1.0, "eye.R.s": 1.0,   # size of one eye (a confused face has one eye bigger than the other)
    "eye.wet": 0.0,              # 0..1 teary: a water line along the bottom of the eye
    "lid.top": 0.0, "lid.L.top": 0.0, "lid.R.top": 0.0,   # 0..1 upper lids come down over open eyes (bored, smug, sleepy)
    # mouth shapes, each 0 at rest
    "mouth.teeth": 0.0,          # a row of teeth in the open mouth (grin)
    "mouth.grit": 0.0,           # clenched teeth instead of lips (nervous, straining)
    "mouth.wave": 0.0,           # wobbly line (queasy, nervous, about to cry)
    "mouth.kiss": 0.0,           # pursed lips
    "mouth.smirk": 0.0,          # -1..1 one corner of the mouth up
    "mouth.wail": 0.0,           # open frown (crying out loud)
    "blush.lines": 0.0,          # 0..1 hatch marks on the cheeks (flustered)
    # paws, held: 0 open paw, 1 fist, 2 thumb up, 3 pointing finger, 4 peace sign
    "hand.L.shape": 0.0, "hand.R.shape": 0.0,
    "arm.L.back": 0.0, "arm.R.back": 0.0,   # 1 = the arm is drawn behind the body (paws behind the back)
    # ---- added in v5: turning away from the viewer (mascot/views.py).  Degrees; 0 faces the viewer, + turns the face
    # towards screen-right.  body.yaw turns the whole mascot, head.yaw turns the head further on top of it.
    "body.yaw": 0.0, "head.yaw": 0.0,
}

# channels added in v4 that expressions may set; a face that does not mention one puts it back to rest, so going
# from a heart-eyed face to a smile clears the hearts
FACE_V4 = ("brow.L.y", "brow.R.y", "brow.L.tilt", "brow.R.tilt", "eye.style", "eye.L.s", "eye.R.s", "eye.wet", "lid.top",
           "lid.L.top", "lid.R.top", "mouth.teeth", "mouth.grit", "mouth.wave", "mouth.kiss", "mouth.smirk", "mouth.wail",
           "blush.lines", "mouth.w")
HELD = ("eye.style", "hand.L.shape", "hand.R.shape")      # channels whose values are names, so they jump instead of blending

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
    "angry":     {"eye.open": 1, "eye.arc": -0.45, "eye.w": 0.96, "eye.h": 0.76, "look.x": 0, "look.y": 0.1, "brow.show": 1, "brow.y": -6, "brow.tilt": -24,
                  "mouth.smile": -1, "mouth.open": 0, "mouth.o": 0, "tongue": 0, "blush": 0},
    "wink":      {"eye.open": 1, "eye.arc": 1.0, "eye.w": 1, "eye.h": 1, "look.x": 0, "look.y": 0, "brow.show": 0, "brow.y": 0, "brow.tilt": 0,
                  "mouth.smile": 1, "mouth.open": 0.85, "mouth.o": 0, "tongue": 0, "blush": 1.1, "eye.L.blink": 1},
    "focused":   {"eye.open": 0.6, "eye.arc": -0.45, "eye.w": 1, "eye.h": 1, "look.x": 0, "look.y": 0.35, "brow.show": 1, "brow.y": -4, "brow.tilt": -10,
                  "mouth.smile": 0.8, "mouth.open": 0, "mouth.o": 0, "tongue": 0, "blush": 0},
}


def _face(base, **kw):
    """An expression written as changes to another one (keyword names use _ for the dots)."""
    out = dict(FACES[base])
    out.pop("eye.L.blink", None)
    out.update({k.replace("__", ".").replace("_", "."): v for k, v in kw.items()})
    return out


# ---- v4 expressions.  Built from the channels above, so every mascot with eyes, brows and a mouth can play them.
FACES.update({
    "laugh":       _face("joy", eye_style=5, eye_open=1, mouth_open=1.25, blush=1.3),
    "grin":        _face("smiley", eye_h=0.95, mouth_smile=1.2, mouth_open=0.9, mouth_teeth=1, blush=1.1),
    "sad":         _face("worried", eye_w=0.92, eye_h=0.9, look_y=0.45, brow_y=2, brow_tilt=22, mouth_smile=-0.8, lid_top=0.22,
                         blush=0.4, eye_wet=0.35),
    "cry":         _face("worried", eye_open=0, eye_arc=0.35, brow_tilt=24, brow_y=3, mouth_smile=-1, mouth_wail=1, blush=1.2),
    "pleading":    _face("worried", eye_w=1.14, eye_h=1.16, look_y=-0.15, eye_style=6, eye_wet=1, brow_tilt=18, brow_y=4,
                         mouth_smile=-0.3, mouth_wave=0.5, blush=1.25),
    "love":        _face("smiley", eye_style=1, eye_w=1.06, eye_h=1.06, mouth_open=0.9, blush=1.4),
    "starry":      _face("smiley", eye_style=2, eye_w=1.06, eye_h=1.06, mouth_open=1.0, blush=1.2),
    "dizzy":       _face("neutral", eye_style=3, mouth_smile=0.2, mouth_wave=0.8, tongue=0.6, blush=0.6),
    "dead":        _face("neutral", eye_style=4, mouth_smile=0, tongue=1.7, blush=0),
    "shocked":     _face("surprised", eye_w=0.55, eye_h=0.6, brow_y=14, brow_tilt=8, mouth_o=1.35, blush=0.2),
    "smug":        _face("smiley", lid_top=0.45, look_x=0.35, brow_show=1, brow_R_y=7, brow_tilt=-6, mouth_open=0, mouth_smirk=0.9,
                         mouth_smile=0.6, blush=0.8),
    "unamused":    _face("neutral", lid_top=0.55, look_x=-0.5, brow_show=1, brow_y=-2, brow_tilt=-4, mouth_smile=0, tongue=0, blush=0.3),
    "pout":        _face("neutral", eye_h=0.92, lid_top=0.15, look_x=0.5, brow_show=1, brow_tilt=-16, brow_y=-3, mouth_smile=-0.6,
                         mouth_w=0.7, tongue=0, blush=1.35, blush_lines=0.6),
    "nervous":     _face("worried", eye_w=0.95, eye_h=1.0, brow_tilt=16, brow_y=4, look_x=-0.3, mouth_grit=1, blush=0.5),
    "kiss":        _face("joy", mouth_open=0, mouth_kiss=1, blush=1.4),
    "silly":       _face("wink", eye_L_blink=1, tongue=1.8, mouth_open=0, blush=1.2),
    "yawn":        _face("sleep", eye_style=5, eye_open=1, brow_show=1, brow_tilt=10, mouth_open=1.25, mouth_w=0.72, blush=0.8),
    "drowsy":      _face("neutral", lid_top=0.62, eye_h=0.95, look_y=0.2, mouth_smile=0.2, tongue=0, blush=0.9, eye_wet=0.3),
    "determined":  _face("focused", eye_open=1, lid_top=0.3, brow_y=-5, brow_tilt=-22, mouth_smile=0.8, look_y=0.1),
    "mischief":    _face("smiley", lid_top=0.4, look_x=0.4, brow_show=1, brow_tilt=-20, mouth_smile=1.2, mouth_open=0.7, mouth_teeth=1,
                         blush=0.6),
    "sick":        _face("worried", lid_top=0.5, eye_h=0.9, brow_tilt=14, mouth_smile=-0.2, mouth_wave=1, blush=0, eye_wet=0.4),
    "confused":    _face("curious", eye_L_s=0.82, eye_R_s=1.1, brow_show=1, brow_L_y=-4, brow_R_y=8, mouth_o=0, mouth_smile=0.1,
                         mouth_wave=0.6, look_x=0.3, look_y=-0.3),
    "flustered":   _face("worried", eye_style=5, eye_open=1, brow_tilt=14, mouth_smile=0.2, mouth_wave=0.7, blush=1.5, blush_lines=1),
    "relieved":    _face("calm", brow_show=1, brow_tilt=10, mouth_smile=0.8, blush=0.9),
    "proud":       _face("joy", mouth_open=0, blush=1.2),
    "scared":      _face("worried", eye_w=0.72, eye_h=0.76, eye_wet=0.5, brow_y=10, brow_tilt=24, mouth_smile=-0.6, mouth_wave=0.5,
                         blush=0),
    "hungry":      _face("smiley", eye_style=6, eye_w=1.1, eye_h=1.1, mouth_open=0.6, tongue=1.2, blush=1.1),
    "cool":        _face("smiley", lid_top=0.35, mouth_open=0, mouth_smirk=0.6, mouth_smile=0.8, blush=0.5),
    "furious":     _face("angry", eye_w=0.9, eye_h=0.7, brow_y=-8, brow_tilt=-28, mouth_grit=1, blush=0),
    "excited":     _face("joy", eye_style=6, eye_open=1, eye_w=1.1, eye_h=1.12, mouth_open=1.15, blush=1.3),
})
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
    # a clip that turns the whole mascot right round (a flip) ends a full turn away from where it began: the same
    # picture, but the springs would see the turn snap back at the loop point, so they follow the body without it
    turn = float(T["root.rot"][-1] - T["root.rot"][0])
    whole = loop and abs(turn) > 1.0 and abs(turn / 360.0 - round(turn / 360.0)) < 1e-6
    hrot = (0.0 if whole else T["root.rot"]) + T["hip.rot"] + T["body.rot"] + T["head.rot"]
    hy = T["root.y"] / sc + T["hip.y"] + T["body.y"] + T["head.y"]
    hy = hy - (T["root.sy"] - 1.0) * 330.0 - (T["head.sy"] - 1.0) * 120.0   # squash moves the head too
    hx = T["root.x"] + T["hip.x"] + T["body.x"] + T["head.x"] + lever * np.sin(np.radians(hrot))
    ry = T["root.y"] / sc + T["hip.y"] - (T["root.sy"] - 1.0) * 60.0
    rrot = (0.0 if whole else T["root.rot"]) + T["hip.rot"] + T["body.rot"]
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
