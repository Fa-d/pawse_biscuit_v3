"""Reusable bits of acting, built only from rig channels (so they work for every mascot)."""
from __future__ import annotations

import math

from ..clip import Track, ease


def addkeys(c, ch, *keys):
    """Additive keyed bump on a channel: [(t, value, ease), ...]; contributes 0 outside its keys."""
    tr = Track(None)
    for k in keys:
        tr.key(*k)
    t0, t1 = tr.keys[0][0], tr.keys[-1][0]
    c.add(ch, lambda t: tr.at(t) if t0 <= t <= t1 else 0.0)
    return c


def breathe(c, period, amp=0.03, t0=0, phase=0.0):
    """Chest rises and falls; shoulders follow.  Use whole periods in looping clips."""
    def up(t):
        return 0.5 - 0.5 * math.cos(2 * math.pi * ((t - t0) / period + phase))
    c.add("body.sy", lambda t: amp * up(t))
    c.add("body.sx", lambda t: amp * 0.4 * up(t))
    c.add("arm.L.sh", lambda t: 2.5 * amp / 0.03 * up(t))
    c.add("arm.R.sh", lambda t: 2.5 * amp / 0.03 * up(t))


def ear_flick(c, side, t, amp=13.0, dur=14):
    """One ear snaps out and springs back."""
    sgn = 1.0 if side == "R" else -1.0
    c.pulse(f"ear.{side}.rot", t, sgn * amp, up=max(3, dur // 3), down=dur - max(3, dur // 3), e_up="out", e_down="back")


def squash(c, t, amount=0.08, pre=5, post=14, body=0.0, head=0.0, knees=1.0):
    """A squash hit at frame t (landing, plop, impact) followed by a springy recovery.  The knees give too."""
    def sy(a):
        return ((t - pre, 0.0), (t, -a, "out"), (t + post * 0.45, a * 0.42, "io"), (t + post, 0.0, "io"))
    def sx(a):
        return ((t - pre, 0.0), (t, a * 0.75, "out"), (t + post * 0.45, -a * 0.3, "io"), (t + post, 0.0, "io"))
    addkeys(c, "root.sy", *sy(amount))
    addkeys(c, "root.sx", *sx(amount))
    if knees:
        d = amount * 110.0 * knees
        addkeys(c, "hip.y", (t - pre, 0.0), (t, d, "out"), (t + post * 0.45, -d * 0.25, "io"), (t + post, 0.0, "io"))
    if body:
        addkeys(c, "body.sy", *sy(body))
        addkeys(c, "body.sx", *sx(body))
    if head:
        addkeys(c, "head.sy", *sy(head))
        addkeys(c, "head.sx", *sx(head))


def jump(c, t0, h=56.0, air=30, anti=10, sq=0.08, st=0.07, settle=18, body=0.07, head=0.045, crouch=None, tuck=None, spread=5.0):
    """Hop with anticipation, stretch, and a squashy landing.  Returns (launch, apex, land) frames.

    The legs do the work: the hips sink to load them (`crouch`), they snap straight on the push-off, tuck up
    in the air (`tuck`, feet `spread` apart) and take the landing.  Leaving the ground, hanging and reaching
    back for it are automatic (see rig.plant_feet).  sq / st are whole-character squash and stretch; `body`
    and `head` add local squash so the impact reads without making the mascot look like rubber.
    """
    tl = t0 + anti
    td = tl + air
    ta = (tl + td) / 2.0
    crouch = min(20.0, max(6.0, h * 0.26)) if crouch is None else crouch
    tuck = min(15.0, max(5.0, h * 0.2)) if tuck is None else tuck
    aq = sq * 0.7                                            # the knees take part of the wind-up

    def y(t):
        if t <= tl or t >= td:
            return 0.0
        u = (t - tl) / float(air)
        return -h * 4.0 * u * (1.0 - u)

    c.add("root.y", y)
    addkeys(c, "hip.y", (t0, 0.0), (tl - 3, crouch, "out"), (tl, 0.0, "in"), (tl + 3, -crouch * 0.2, "out"), (tl + 8, 0.0, "io"), (td - 1, 0.0, "hold"),
            (td + 4, crouch * 1.15, "out"), (td + 11, -crouch * 0.22, "io"), (td + settle, 0.0, "io"))
    for s in "LR":
        addkeys(c, f"foot.{s}.y", (tl + 2, 0.0), (ta, -tuck, "out"), (td - 4, 0.0, "in"))
        addkeys(c, f"foot.{s}.x", (tl + 2, 0.0), (ta, spread, "out"), (td - 3, 0.0, "io"))
    addkeys(c, "root.sy", (t0, 0.0), (tl - 2, -aq, "out"), (tl + 3, st, "io"), (ta, 0.015, "io"), (td - 1, st * 0.75, "io"),
            (td + 3, -sq * 1.0, "out"), (td + 10, sq * 0.34, "io"), (td + settle, 0.0, "io"))
    addkeys(c, "root.sx", (t0, 0.0), (tl - 2, aq * 0.8, "out"), (tl + 3, -st * 0.7, "io"), (ta, -0.01, "io"), (td - 1, -st * 0.5, "io"),
            (td + 3, sq * 0.85, "out"), (td + 10, -sq * 0.25, "io"), (td + settle, 0.0, "io"))
    if body:
        addkeys(c, "body.sy", (t0, 0.0), (tl - 2, -body, "out"), (tl + 4, body * 0.5, "io"), (ta, 0.0, "io"), (td, 0.0, "hold"),
                (td + 4, -body * 1.2, "out"), (td + 11, body * 0.45, "io"), (td + settle + 2, 0.0, "io"))
        addkeys(c, "body.sx", (t0, 0.0), (tl - 2, body * 0.6, "out"), (tl + 4, -body * 0.3, "io"), (ta, 0.0, "io"), (td, 0.0, "hold"),
                (td + 4, body * 0.8, "out"), (td + 11, -body * 0.3, "io"), (td + settle + 2, 0.0, "io"))
    if head:
        addkeys(c, "head.sy", (td - 1, 0.0), (td + 4, -head, "out"), (td + 12, head * 0.5, "io"), (td + settle + 4, 0.0, "io"))
        addkeys(c, "head.sx", (td - 1, 0.0), (td + 4, head * 0.8, "out"), (td + 12, -head * 0.35, "io"), (td + settle + 4, 0.0, "io"))
        addkeys(c, "head.y", (t0, 0.0), (tl - 2, 4.0, "out"), (tl + 4, -3.0, "io"), (ta, 0.0, "io"), (td, 0.0, "hold"),
                (td + 4, 6.0, "out"), (td + 12, -2.0, "io"), (td + settle + 4, 0.0, "io"))
    return tl, ta, td


def bob(c, period, amp=4.0, t0=0, t1=None, st=0.02, phase=0.0):
    """Rhythmic bounce on the spot (dancing, keeping the beat): the knees dip once per period while the feet
    stay put.  Starts and ends standing tall."""
    t1 = c.frames if t1 is None else t1

    def dip(t):
        if t < t0 or t > t1:
            return 0.0
        return 0.5 - 0.5 * math.cos(2 * math.pi * ((t - t0) / period + phase))

    c.add("hip.y", lambda t: amp * dip(t))
    if st:
        c.add("body.sy", lambda t: -st * dip(t))
        c.add("body.sx", lambda t: st * 0.7 * dip(t))


def _edge(t, t0, t1, period, frames):
    """1 inside [t0, t1], easing to 0 over a quarter period at ends that fall inside the clip."""
    if t0 <= 0 and t1 >= frames:
        return 1.0
    q = period / 4.0
    return ease("io", max(0.0, min(1.0, (t - t0) / q, (t1 - t) / q)))


# ---------------------------------------------------------------- legs
def weight(c, *keys, tilt=0.35, sink=0.18):
    """Shift the weight from foot to foot: (t, x[, ease]) with x in pixels, + = towards the right foot.

    The hips swing over the supporting foot and tip a little; planted feet stay where they are.
    """
    for key in keys:
        t, x = key[0], key[1]
        e = key[2] if len(key) > 2 else "soft"
        c.k("hip.x", (t, x, e))
        c.k("hip.rot", (t, x * tilt, e))
    c.add("hip.y", lambda t: abs(c.tracks["hip.x"].at(t)) * sink)


def step(c, side, t, lift=12.0, dur=14, sole=0.7, grow=0.08, inward=0.0, e_up="out", e_down="in"):
    """Pick one foot up and put it down again.  Seen from the front the lifted foot comes towards the viewer:
    it tips up to show its pads and grows a touch."""
    for s in side:
        a, b = t + dur * 0.45, t + dur
        addkeys(c, f"foot.{s}.y", (t, 0.0), (a, -lift, e_up), (b, 0.0, e_down))
        if sole:
            addkeys(c, f"foot.{s}.sole", (t, 0.0), (a, sole, e_up), (b - 1, 0.0, e_down))
        if grow:
            addkeys(c, f"foot.{s}.s", (t, 0.0), (a, grow, e_up), (b, 0.0, e_down))
        if inward:
            addkeys(c, f"foot.{s}.x", (t, 0.0), (a, -inward, e_up), (b, 0.0, e_down))


def tap(c, side, t, n=1, gap=11, up=0.5, lift=2.5):
    """Toe taps: the front of the foot lifts and slaps back down."""
    for q in range(n):
        t0 = t + q * gap
        for s in side:
            addkeys(c, f"foot.{s}.sole", (t0, 0.0), (t0 + 4, up, "out"), (t0 + 7, 0.0, "in"))
            addkeys(c, f"foot.{s}.y", (t0, 0.0), (t0 + 4, -lift, "out"), (t0 + 7, 0.0, "in"))


def kick(c, side, t, out=22.0, up=16.0, dur=18, hold=0):
    """A little sideways kick: the leg swings out and back."""
    for s in side:
        a = t + dur * 0.4
        addkeys(c, f"foot.{s}.x", (t, 0.0), (a, out, "out"), (a + hold, out, "hold"), (t + dur + hold, 0.0, "io"))
        addkeys(c, f"foot.{s}.y", (t, 0.0), (a, -up, "out"), (a + hold, -up, "hold"), (t + dur + hold, 0.0, "in"))


def patter(c, t0, t1, period=10, lift=6.0, first="R"):
    """Happy feet: quick little alternating steps on the spot."""
    other = "L" if first == "R" else "R"
    t, q = t0, 0
    while t + period <= t1 + 1e-6:
        step(c, first if q % 2 == 0 else other, t, lift=lift, dur=period, sole=0.35, grow=0.03)
        t += period
        q += 1


def walk(c, period=60, t0=0, t1=None, lift=15.0, sway=6.0, lean=2.2, dip=3.0, first="R"):
    """Walking towards the viewer on the spot.  One full cycle (two steps) per `period`.

    Each foot in turn comes up and forward (pads flash, the foot grows), the hips swing over the supporting
    foot, the body leans with them and dips as each foot lands.
    """
    t1 = c.frames if t1 is None else t1
    sgn = 1.0 if first == "R" else -1.0

    def ph(t):
        return (t - t0) / float(period)

    def on(t):
        return _edge(t, t0, t1, period, c.frames) if t0 <= t <= t1 else 0.0

    def up(t, off):                                           # 0..1 while this foot is in the air (40 % of the cycle)
        x = (ph(t) + off) % 1.0
        return math.sin(math.pi * x / 0.4) ** 1.3 if x < 0.4 else 0.0

    for s, off in ((first, 0.0), ("L" if first == "R" else "R", 0.5)):
        c.add(f"foot.{s}.y", lambda t, off=off: -lift * up(t, off) * on(t))
        c.add(f"foot.{s}.sole", lambda t, off=off: 0.75 * up(t, off) ** 0.8 * on(t))
        c.add(f"foot.{s}.s", lambda t, off=off: 0.10 * up(t, off) * on(t))
        c.add(f"foot.{s}.x", lambda t, off=off: -3.0 * up(t, off) * on(t))
    # weight over the foot that is on the ground (the first foot is in the air during the first 40 %)
    swing = lambda t: -sgn * math.cos(2 * math.pi * (ph(t) - 0.2)) * on(t)      # -1 = weight on the left foot, +1 = on the right
    c.add("hip.x", lambda t: sway * swing(t))
    c.add("hip.rot", lambda t: lean * 0.6 * swing(t))
    c.add("body.rot", lambda t: lean * swing(t))                                # the body leans over the supporting leg...
    c.add("head.rot", lambda t: -lean * 0.9 * swing(t))                         # ...and the head stays level
    c.add("hip.y", lambda t: dip * (0.5 + 0.5 * math.cos(4 * math.pi * (ph(t) - 0.45))) * on(t))   # lowest as each foot lands


def wave(c, side, t_up, t_down=None, period=30, swing=24.0, lo="wave_lo", hi="wave_hi", rest="rest", up=10, down=14):
    """Raise a paw, wave it (forearm swings about the elbow, wrist flops behind), and put it back.

    If t_down is None the paw stays up (for looping waves start with the paw already up: t_up=None).
    """
    if t_up is not None:
        c.arm(side, (t_up, rest), (t_up + 3, (c.char.pose(rest)["v"][0] - 6, c.char.pose(rest)["v"][1] - 6, 0, 1.0), "out"),
              (t_up + up + 3, lo, "back"))
        t_start = t_up + up + 3
    else:
        c.arm(side, (0, lo))
        t_start = 0
    t_end = c.frames if t_down is None else t_down
    a = c.char.pose(lo)["v"]
    b = c.char.pose(hi)["v"]
    mid_d = (b[1] - a[1]) / 2.0

    def el(t):
        if t < t_start or t > t_end:
            return 0.0
        return mid_d * (1.0 - math.cos(2 * math.pi * (t - t_start) / period))

    for s in side:
        c.add(f"arm.{s}.el", el)
    if t_down is not None:
        c.arm(side, (t_down, lo), (t_down + down, rest, "back"))
    return t_start


def look(c, *keys):
    """Gaze keys: (t, x, y[, ease])  with x, y in -1..1."""
    for key in keys:
        t, x, y = key[0], key[1], key[2]
        e = key[3] if len(key) > 3 else "out"
        c.k("look.x", (t, x, e))
        c.k("look.y", (t, y, e))


def nod(c, t, amp=6.0, dur=16):
    """Small yes-nod: dip, overshoot back."""
    addkeys(c, "head.rot", (t, 0.0), (t + dur * 0.4, amp * 0.25, "out"), (t + dur, 0.0, "back"))
    addkeys(c, "head.y", (t, 0.0), (t + dur * 0.4, amp, "out"), (t + dur, 0.0, "back"))


def happy_squint(c, t0, t1, dur=6):
    """Eyes close into happy arches for a moment, then pop open again."""
    c.k("eye.open", (t0 - dur, 1.0, "hold"), (t0, 0.0, "io"), (t1, 0.0, "hold"), (t1 + dur, 1.0, "back"))
    c.k("eye.arc", (t0 - dur, -0.45, "hold"), (t0 - 2, 0.2, "io"), (t0 + 4, 1.0, "back"), (t1, 1.0, "hold"), (t1 + dur, -0.45, "io"))
