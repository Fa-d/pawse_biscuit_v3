"""Acting with things: eating, sipping, typing, reading, calls and selfies, singing into a microphone, a toast,
painting, gaming, photos, brushing teeth, lifting weights, juggling, cuddling a plushie, magic with a wand ...

Each of these motions names what it acts with (`uses`: prop names or categories) and what it brings when the
sticker holds nothing it can use (`brings`; "snack" means the mascot's own favourite).  The composer hands the
paw that holds the thing to the motion (rule R07), so the prop goes where the paw goes: a cookie to the mouth, a
glass up for a toast.  When the paws are needed elsewhere the motion falls back to the one named in `paw_alt`.

Loop safety: every keyed channel ends on the value it starts with, periods come from m.per() so they divide the
loop, and one-shot bursts finish before the loop ends.
"""
from __future__ import annotations

import random

from mascot.geom import rot as rot_pt

from ..registry import motion
from .acting import M, alternate, beat, bump, frames_of, math, shake, shape, sway_hips
from .common import C, F, K, Layer, Path, el, fl, gr, rc, sh, smooth, st, tm
from .fx import burst


# ------------------------------------------------------------------ helpers
def _start(c, ch, default=0.0):
    """The value a channel starts the loop with (the face sets the mouth before the motion runs)."""
    tr = c.tracks.get(ch)
    return float(tr.at(0)) if tr is not None and tr.keys else default


def mouth_keys(c, L, keys, ch="mouth.open"):
    """Key the mouth over the loop: [(t, value, ease)], starting and ending on the face's own value."""
    base = _start(c, ch)
    out = [(0, base)]
    for t, v, e in keys:
        t = int(round(t))
        if 0 < t < L and t > out[-1][0]:
            out.append((t, float(v), e))
    out.append((L, base, "io"))
    c.k(ch, *out)


def chew(t0, t1, period, lo=0.12, hi=0.6):
    """Mouth keys for chewing between t0 and t1."""
    out, t = [], float(t0)
    while t + period <= t1 + 1e-6:
        out += [(t + period * 0.5, hi, "io"), (t + period, lo, "io")]
        t += period
    return out


def talk(t0, t1, seed=3, lo=0.1, hi=0.95):
    """Mouth keys for talking (or singing short notes): syllables of uneven length between t0 and t1."""
    rng = random.Random(seed)
    out, t, q = [], float(t0), 0
    while t < t1 - 7:
        t += rng.choice((5, 6, 7, 8, 9))
        out.append((min(t, t1 - 2), rng.uniform(0.45, hi) if q % 2 == 0 else lo, "io"))
        q += 1
    return out


def prop_point(char, side, f, pt, pose="hold", upright=False, tilt=0.0, scale=1.0, grip_at=(0.0, 17.0)):
    """Canvas position at frame f of a point `pt` drawn on a held prop (in the prop's own upright coordinates)."""
    sgn = 1.0 if side == "R" else -1.0
    T = char.T
    if upright:
        rot = sgn * float(T[f"arm.{side}.sh"][f] + T[f"arm.{side}.el"][f] + T[f"arm.{side}.wr"][f]) + tilt
    else:
        v = char.pose(pose)["v"]
        rot = sgn * (v[0] + v[1] + v[2]) + tilt
    k = float(T[f"hand.{side}.s"][f])
    q = rot_pt((pt[0] * scale / k, pt[1] * scale / k), rot)
    return char.hand_to_world(side, f, (grip_at[0] + q[0], grip_at[1] + q[1]))


def mouth_at(t, dy=8.0):
    """fn(char, T) -> the mouth on the canvas at frame t (for crumbs, bubbles)."""
    return lambda char, T: char.head_to_world(t, (char.mouth[0], char.mouth[1] + dy))


def paw_at(side, t, local=(0.0, 0.0)):
    return lambda char, T: char.hand_to_world(side, t, local)


def _side(m, *wanted):
    """The paw holding the thing the motion acts with, else the first free paw."""
    return m.prop_side(*wanted) or m.side


# ------------------------------------------------------------------ food and drink
@motion("eat", "Eating", "😋", doing="eating", paws=2, min_paws=1, sit="ok", wag=9, tags=("food", "hungry", "yum"), face="joy",
        uses=("food",), brings="snack", paw_alt="bounce")
def eat(m):
    """Bite, chew-chew-chew, bite again: the snack goes to the mouth, crumbs fly, the free paw rubs the tummy."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "food")
    p = m.per(60)
    keys, mouth, t = [(0, "hold")], [], 0.0
    while t + p <= L + 1e-6:
        t_up, t_bite, t_down = t + 0.22 * p, t + 0.32 * p, t + 0.46 * p
        keys += [(int(t_up), "bite", "back"), (int(t_bite), "bite", "hold"), (int(t_down), "hold", "io"), (int(t + p), "hold", "hold")]
        mouth += [(t_up - 3, 1.1, "out"), (t_bite, 0.05, "in")] + chew(t_bite + 3, t + p - 3, max(6.0, (p * 0.5) / 3.0))
        bump(c, "head.y", int(t_up - 4), int(t_down + 2), 4.0 * k, rise=6, fall=8)
        bump(c, "head.rot", int(t_bite - 1), int(t_bite + 10), -3.0 * k, rise=3, fall=7)
        c.prop(burst(int(t_bite), mouth_at(int(t_bite)), count=5, colours=("crust", "choco", "cheese"), reach=46, life=16, kind="dot",
                     size=7.0, gravity=34.0, spread=(195.0, 345.0), seed=int(t_bite)))
        t += p
    c.arm(s, *keys[:-1], (L, "hold"))
    mouth_keys(c, L, mouth)
    o = m.other(s)
    if o:                                   # the other paw rubs the tummy
        c.arm(o, (0, "belly"))
        c.osc(f"arm.{o}.sh", 4.0 * k, m.per(30))
    beat(c, "body.sx", 0.012 * k, m.per(15), L)
    return int(0.3 * p)


@motion("sip", "Sipping", "☕", doing="sipping", paws=2, min_paws=1, sit="ok", wag=3, tags=("drink", "coffee", "tea", "calm"), face="calm",
        uses=("drink",), brings="mug", paw_alt="sway", calm=True)
def sip(m):
    """A slow sip with the eyes closed, then a happy sigh."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "drink")
    t_up, t_sip, t_down, t_ahh = frames_of(L, 0.2, 0.3, 0.62, 0.74)
    c.arm(s, (0, "hold"), (t_up, "bite", "io"), (t_down, "bite", "hold"), (t_ahh, "hold", "io"), (L, "hold", "hold"))
    bump(c, "head.rot", t_up - 6, t_ahh, -5.0 * k, rise=12, fall=12)
    bump(c, "head.y", t_up - 6, t_ahh, -3.0 * k, rise=12, fall=12)
    mouth_keys(c, L, [(t_sip - 4, 0.0, "io"), (t_down, 0.0, "hold"), (t_ahh, 0.9, "out"), (t_ahh + 14, 0.3, "io")])
    bump(c, "body.sy", t_down, L - 4, -0.03 * k, rise=10, fall=18)
    bump(c, "hip.y", t_down, L - 4, 3.0 * k, rise=10, fall=18)
    o = m.other(s)
    if o:
        c.arm(o, (0, "belly"))
    M.breathe(c, period=m.per(60), amp=0.015)
    return (t_sip + t_down) // 2


# ------------------------------------------------------------------ screens and pages
@motion("typing", "Typing", "💻", doing="typing", paws=2, min_paws=2, sit="ok", wag=4, tags=("work", "busy", "computer"), face="focused",
        uses=("laptop",), brings="laptop", paw_alt="nod")
def typing(m):
    """Tap-tap-tap on the keys, the head following the lines, one big press of Enter."""
    c, L, k = m.c, m.L, m.k
    p = m.per(8)
    for q, s in enumerate(m.hands):
        c.arm(s, (0, "lap"))
        c.osc(f"arm.{s}.sh", 5.0 * k, p, phase=0.5 * q)
        c.osc(f"arm.{s}.el", -4.0 * k, p, phase=0.5 * q + 0.1)
    t_enter = frames_of(L, 0.72)[0]
    s0 = m.hands[0]
    M.addkeys(c, f"arm.{s0}.sh", (t_enter - 10, 0.0), (t_enter - 3, 16.0 * k, "out"), (t_enter, -6.0 * k, "in"), (t_enter + 10, 0.0, "io"))
    c.set("look.y", 0.55)
    c.k("head.y", (0, 3.0))
    c.osc("head.rot", 2.0 * k, m.per(60))
    c.osc("look.x", 0.25, m.per(60), phase=0.25)
    bump(c, "body.sy", t_enter - 2, t_enter + 10, -0.02 * k, rise=3, fall=7)
    return frames_of(L, 0.3)[0]


@motion("read", "Reading", "📖", doing="reading", paws=2, min_paws=2, sit="ok", wag=3, tags=("study", "book", "calm"), face="curious",
        uses=("book",), brings="book", paw_alt="think", calm=True)
def read(m):
    """Eyes run along the lines, the head nods a little at the end of each one; a page turns."""
    c, L, k = m.c, m.L, m.k
    for s in m.hands:
        c.arm(s, (0, "clap_open"))
    p = m.per(40)
    lines = []
    t = 0.0
    while t + p <= L + 1e-6:                  # gaze sweeps left to right, then darts back to the next line
        lines += [(int(t + 0.8 * p), 0.35, "io"), (int(t + p), -0.35, "out")]
        t += p
    c.k("look.x", (0, -0.35), *lines)
    c.set("look.y", 0.6)
    c.osc("head.rot", 2.0 * k, p, phase=0.75)
    t_page = frames_of(L, 0.55)[0]
    s0 = m.hands[0]
    M.addkeys(c, f"arm.{s0}.sh", (t_page, 0.0), (t_page + 8, 22.0 * k, "out"), (t_page + 20, 0.0, "io"))
    M.addkeys(c, f"arm.{s0}.el", (t_page, 0.0), (t_page + 8, -18.0 * k, "out"), (t_page + 20, 0.0, "io"))
    M.breathe(c, period=m.per(60), amp=0.015)
    return int(0.4 * p)


@motion("phone_call", "On the phone", "📞", doing="on the phone", paws=2, min_paws=1, sit="ok", wag=5, tags=("call", "talk", "busy"),
        face="smiley", uses=("phone",), brings="phone", paw_alt="nod")
def phone_call(m):
    """Phone to the ear, chatting away with the free paw talking too; a pause to listen and nod."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "phone")
    c.arm(s, (0, "phone_ear"))
    t_listen, t_back = frames_of(L, 0.5, 0.68)
    mouth_keys(c, L, talk(4, t_listen, seed=7) + [(t_listen + 3, 0.0, "io"), (t_back, 0.0, "hold")] + talk(t_back, L - 6, seed=11))
    M.nod(c, t_listen + 2, amp=5.0 * k, dur=14)
    sgn = 1.0 if s == "R" else -1.0
    c.k("head.rot", (0, 6.0 * sgn))
    c.osc("head.rot", 2.0 * k, m.per(40))
    o = m.other(s)
    if o:                                   # the free paw talks too
        c.arm(o, (0, "relax"), (frames_of(L, 0.14)[0], "shrug", "back"), (frames_of(L, 0.36)[0], "shrug", "hold"),
              (t_listen, "hip", "io"), (frames_of(L, 0.86)[0], "hip", "hold"), (L, "relax", "io"))
    sway_hips(c, 3.0 * k, m.per(120), tilt=0.3)
    return frames_of(L, 0.25)[0]


@motion("selfie", "Selfie", "🤳", doing="taking a selfie", paws=2, min_paws=1, sit="ok", wag=8, tags=("photo", "cute", "fun"), face="grin",
        uses=("phone",), brings="phone", paw_alt="peace")
def selfie(m):
    """Phone up, head tilted into the shot, click (flash); a second pose, click again."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "phone")
    sgn = 1.0 if s == "R" else -1.0
    c.arm(s, (0, "reach"))
    c.osc(f"arm.{s}.sh", 2.0 * k, m.per(60))
    t1, t2 = frames_of(L, 0.32, 0.78)
    c.k("head.rot", (0, 9.0 * sgn), (t1 + 8, 9.0 * sgn, "hold"), (t1 + 18, 3.0 * sgn, "io"), (t2 - 8, 3.0 * sgn, "hold"),
        (t2 + 10, 3.0 * sgn, "hold"), (L, 9.0 * sgn, "io"))
    for t in (t1, t2):
        c.prop(burst(t, lambda char, T, t=t: prop_point(char, s, t, (0.0, -46.0), upright=True, tilt=-8.0), count=8,
                     colours=("white", "yellow"), reach=42, life=12, kind="star", size=12.0, seed=t))
        bump(c, "body.sy", t - 4, t + 10, -0.025 * k, rise=4, fall=8)
        c.blink(t + 1, dur=7)
    o = m.other(s)
    if o:                                   # a peace sign for the second shot
        shape(c, o, 4)
        c.arm(o, (0, "rest"), (t1 + 16, "rest", "hold"), (t1 + 26, "wave_hi", "back"), (t2 + 12, "wave_hi", "hold"), (L, "rest", "io"))
    M.bob(c, m.per(60), amp=2.0 * k, st=0.01)
    return t1 + 3


@motion("texting", "Texting", "📱", doing="texting", paws=2, min_paws=1, sit="ok", wag=4, tags=("chat", "message", "busy"), face="focused",
        uses=("phone",), brings="phone", paw_alt="nod")
def texting(m):
    """Thumbs tapping, head down; each new message on the screen gets a little reaction."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "phone")
    c.arm(s, (0, "text"))
    c.osc(f"arm.{s}.wr", 5.0 * k, m.per(8))
    c.osc(f"arm.{s}.el", 2.0 * k, m.per(8), phase=0.25)
    o = m.other(s)
    if o:
        c.arm(o, (0, "text"))
        c.osc(f"arm.{o}.wr", 5.0 * k, m.per(8), phase=0.5)
    c.set("look.y", 0.6)
    c.k("head.y", (0, 3.0))
    for u in (0.32, 0.58):                  # the reply pops up: a tiny start
        t = frames_of(L, u)[0] + 4
        bump(c, "head.y", t, t + 14, -4.0 * k, rise=4, fall=10)
        bump(c, "body.sy", t, t + 14, 0.02 * k, rise=4, fall=10)
    c.osc("head.rot", 2.0 * k, m.per(60))
    return frames_of(L, 0.66)[0]


# ------------------------------------------------------------------ performing
@motion("sing", "Singing", "🎤", doing="singing", paws=2, min_paws=1, sit="ok", wag=8, tags=("music", "karaoke", "happy"), face="joy",
        uses=("microphone", "music"), brings="microphone", paw_alt="sway")
def sing(m):
    """Into the microphone: short notes, then one long big note with the free paw out wide."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "microphone", "music")
    c.arm(s, (0, "bite"))
    t_big, t_end = frames_of(L, 0.55, 0.9)
    mouth_keys(c, L, talk(3, t_big - 4, seed=5, lo=0.25, hi=0.9) + [(t_big + 4, 1.25, "out"), (t_end, 1.15, "hold"), (t_end + 6, 0.4, "io")])
    shake(c, "head.rot", 1.5 * k, t_big + 4, t_end, 6)
    bump(c, "head.rot", t_big - 4, t_end + 6, -6.0 * k, rise=8, fall=10)
    bump(c, "head.y", t_big - 4, t_end + 6, -4.0 * k, rise=8, fall=10)
    bump(c, "body.sy", t_big - 4, t_end + 6, 0.03 * k, rise=8, fall=10)
    o = m.other(s)
    if o:
        c.arm(o, (0, "relax"), (t_big - 6, "relax", "hold"), (t_big + 6, "cheer_out", "back"), (t_end, "cheer_out", "hold"), (L, "relax", "io"))
    sway_hips(c, 4.0 * k, m.per(60), tilt=0.4)
    return (t_big + t_end) // 2


@motion("toast", "Cheers", "🥂", doing="raising a glass", paws=2, min_paws=1, sit="ok", wag=9, tags=("celebrate", "party", "cheers"),
        face="joy", uses=("glass", "drink"), brings="glass", paw_alt="cheer")
def toast(m):
    """Glass up, clink (sparkle), a sip, glass down."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "glass", "drink")
    t_up, t_clink, t_sip, t_down = frames_of(L, 0.16, 0.28, 0.6, 0.82)
    c.arm(s, (0, "hold"), (t_up, "hold_up", "back"), (t_clink + 10, "hold_up", "hold"), (t_sip, "bite", "io"), (t_sip + 12, "bite", "hold"),
          (t_down, "hold", "io"), (L, "hold", "hold"))
    M.addkeys(c, f"arm.{s}.sh", (t_clink - 4, 0.0), (t_clink, 8.0 * k, "out"), (t_clink + 8, 0.0, "back"))
    c.prop(burst(t_clink, lambda char, T: prop_point(char, s, t_clink, (0.0, -70.0), upright=True, scale=1.3), count=7,
                 colours=("yellow", "white", "gold2"), reach=50, life=16, kind="star", size=12.0, seed=11))
    bump(c, "body.sy", t_clink - 4, t_clink + 14, -0.03 * k, rise=4, fall=10)
    bump(c, "hip.y", t_clink - 4, t_clink + 14, 3.0 * k, rise=4, fall=10)
    bump(c, "head.rot", t_sip - 4, t_down, -4.0 * k, rise=8, fall=10)
    o = m.other(s)
    if o:
        c.arm(o, (0, "relax"), (t_up, "cheer_out", "back"), (t_sip - 6, "cheer_out", "hold"), (t_down, "relax", "io"))
    return t_clink + 4


@motion("paint", "Painting", "🎨", doing="painting", paws=2, min_paws=1, sit="ok", wag=6, tags=("art", "creative"), face="smiley",
        uses=("paintbrush", "art"), brings="paintbrush", paw_alt="sway")
def paint(m):
    """One big sweep of the brush paints a rainbow in the air (it follows the bristles exactly), a few proud dabs,
    and the rainbow fades before the loop ends."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "paintbrush", "art")
    t_a, t_b, t_c, t_d = frames_of(L, 0.12, 0.42, 0.55, 0.85)
    c.arm(s, (0, "hold"), (t_a, "cheer_out", "io"), (t_b, "point_up", "io"), (t_c, "hold_up", "io"), (t_d, "hold", "io"), (L, "hold", "hold"))
    for q in range(3):                      # dab, dab, dab
        t = t_c + 6 + 7 * q
        M.addkeys(c, f"arm.{s}.el", (t, 0.0), (t + 3, -10.0 * k, "out"), (t + 7, 0.0, "in"))
    sgn = 1.0 if s == "R" else -1.0
    c.k("head.rot", (0, 0.0), (t_b, 6.0 * sgn, "io"), (t_d, 0.0, "io"))
    c.k("look.x", (0, 0.0), (t_a, 0.5 * sgn, "io"), (t_b, 0.6 * sgn, "io"), (t_d, 0.0, "io"))
    c.k("look.y", (0, 0.0), (t_b, -0.5, "io"), (t_d, 0.0, "io"))
    o = m.other(s)
    if o:
        c.arm(o, (0, "hip"))

    def spec(char, T, n):
        span = max(2, t_b - t_a)
        pts = [prop_point(char, s, t_a + int(round(span * q / 8.0)), (0.0, -100.0), upright=True, tilt=22.0, scale=1.3) for q in range(9)]
        out = []
        for band, (colour, off) in enumerate((("coral", -13.0), ("yellow", 0.0), ("teal", 13.0))):
            shifted = []
            for q, (x, y) in enumerate(pts):          # offset along the normal of the brush path
                ax, ay = pts[max(0, q - 1)]
                bx, by = pts[min(len(pts) - 1, q + 1)]
                dx, dy = bx - ax, by - ay
                d = math.hypot(dx, dy) or 1.0
                shifted.append((x - dy / d * off, y + dx / d * off))
            path = smooth(shifted, closed=False, tension=0.4)
            end = K(n, (0, 0.0), (t_a, 0.0, "hold"), (t_b, 100.0, "io"), (L - 1, 100.0, "hold"))
            op = K(n, (0, 0.0), (t_a, 0.0, "hold"), (t_a + 2, 100.0, "io"), (t_d, 100.0, "hold"), (L - 1, 0.0, "io"))
            out.append(("back", Layer(f"paint stroke {band}", [gr("stroke", [sh(path), tm(0, end), st(C[colour], 12)])], o=op)))
        return out
    c.prop(spec)
    return t_b + 4


@motion("gaming", "Gaming", "🎮", doing="gaming", paws=2, min_paws=2, sit="ok", wag=6, tags=("game", "fun", "play"), face="determined",
        uses=("controller",), brings="controller", paw_alt="nod")
def gaming(m):
    """Buttons mashed, leaning into the turns, a little victory hop."""
    c, L, k = m.c, m.L, m.k
    for q, s in enumerate(m.hands):
        c.arm(s, (0, "clap_open"))
        c.osc(f"arm.{s}.wr", 6.0 * k, m.per(6), phase=0.37 * q)
        c.osc(f"arm.{s}.sh", 2.0 * k, m.per(6), phase=0.5 * q)
    p = m.per(60)
    c.osc("body.rot", 4.0 * k, p)
    c.osc("head.rot", 6.0 * k, p, phase=0.05)
    c.osc("look.x", 0.3, p, phase=0.5)
    t_win = frames_of(L, 0.8)[0]
    for s in m.hands:
        M.addkeys(c, f"arm.{s}.sh", (t_win - 8, 0.0), (t_win, 24.0 * k, "back"), (t_win + 12, 24.0 * k, "hold"), (min(L, t_win + 22), 0.0, "io"))
    bump(c, "hip.y", t_win - 8, min(L, t_win + 22), -6.0 * k, rise=8, fall=12)
    return int(0.25 * p)


@motion("photo", "Taking a photo", "📸", doing="taking a photo", paws=2, min_paws=1, sit="ok", wag=5, tags=("photo", "travel"),
        face="focused", uses=("camera",), brings="camera", paw_alt="look_around")
def photo(m):
    """Camera up, one eye shut to aim, click (the camera flashes at half way), camera down."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "camera")
    t_up, t_click, t_down = frames_of(L, 0.2, 0.5, 0.8)
    c.arm(s, (0, "hold"), (t_up, "chin", "io"), (t_down - 6, "chin", "hold"), (t_down + 8, "hold", "io"), (L, "hold", "hold"))
    o = m.other(s)
    if o:
        c.arm(o, (0, "relax"), (t_up, "chin", "io"), (t_down - 6, "chin", "hold"), (t_down + 8, "relax", "io"), (L, "relax", "hold"))
    wink = "L" if s == "R" else "R"
    c.k(f"eye.{wink}.blink", (0, 0.0), (t_up + 2, 0.0, "hold"), (t_up + 8, 1.0, "io"), (t_click + 10, 1.0, "hold"), (t_click + 16, 0.0, "io"))
    bump(c, "body.sy", t_click - 3, t_click + 10, -0.025 * k, rise=3, fall=7)
    shake(c, "head.rot", 1.5 * k, t_click, t_click + 12, 2)
    return t_click + 3


@motion("brush_teeth", "Brushing teeth", "🪥", doing="brushing its teeth", paws=2, min_paws=1, sit="ok", wag=4,
        tags=("morning", "night", "routine"), face="grin", uses=("toothbrush",), brings="toothbrush", paw_alt="sway")
def brush_teeth(m):
    """Scrub-scrub at the mouth, foam bubbles floating up."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "toothbrush")
    c.arm(s, (0, "bite"))
    c.osc(f"arm.{s}.sh", 6.0 * k, m.per(8))
    c.osc(f"arm.{s}.el", -5.0 * k, m.per(8), phase=0.15)
    c.osc("head.rot", 1.5 * k, m.per(8), phase=0.5)
    c.set("mouth.teeth", 1.0)
    o = m.other(s)
    if o:
        c.arm(o, (0, "hip"))

    def spec(char, T, n):
        out = []
        for q in range(5):
            t0 = int(L * q / 5.0)
            life = 34

            def pos(f, q=q, t0=t0):
                u = ((f - t0) % L) / float(life)
                mx, my = char.head_to_world(f, (char.mouth[0], char.mouth[1] + 4))
                return (mx + (q - 2) * 14 + 6 * math.sin(6 * u + q), my - 10 - 60 * min(u, 1.0))

            def sc(f, t0=t0):
                u = ((f - t0) % L) / float(life)
                return (0.0, 0.0) if u >= 1 else ((100 * math.sin(math.pi * u),) * 2)
            out.append(("top", Layer(f"foam {q}", [gr("bubble", [el((0, 0), (12 + 3 * (q % 3), 12 + 3 * (q % 3))), fl(C["white"]), st(C["sky2"], 2)])],
                                     p=F(n, pos, tol=0.8), s=F(n, sc, tol=2.0))))
        return out
    c.prop(spec)
    return 0


@motion("lift", "Lifting weights", "🏋️", doing="lifting weights", paws=2, min_paws=1, sit="ok", wag=4, tags=("gym", "strong", "workout"),
        face="determined", uses=("dumbbell", "gym"), brings="dumbbell", paw_alt="flex")
def lift(m):
    """Curls: up (squeeze), down, up; the free paw on the hip."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "dumbbell", "gym")
    p = m.per(40)
    # a hammer curl: the upper arm stays out at the side and the forearm swings up, so the weight passes beside the
    # head instead of over the face
    alternate(c, s, (40, 50, 0, 1.1), (74, 100, 0, 1.15), p, L, at_b=0.45, e_ab="io", e_ba="io")
    c.set(f"arm.{s}.front", 1.0)
    beat(c, "body.sy", -0.02 * k, p, L, phase=0.7)
    beat(c, "hip.y", 3.0 * k, p, L, phase=0.7)
    c.osc("head.rot", 2.0 * k, p, phase=0.2)
    o = m.other(s)
    if o:
        c.arm(o, (0, "hip"))
    return int(0.45 * p)


@motion("strum", "Playing guitar", "🎸", doing="playing the guitar", paws=2, min_paws=2, sit="ok", wag=8, tags=("music", "song", "band"),
        face="joy", uses=("guitar",), brings="guitar", paw_alt="sway")
def strum(m):
    """Strum-strum at the sound hole, the other paw changing chords along the neck, swaying with the song."""
    c, L, k = m.c, m.L, m.k
    p = m.per(10)
    c.arm("R", (0, "belly"))
    c.osc("arm.R.el", 12.0 * k, p)
    c.osc("arm.R.sh", 4.0 * k, p, phase=0.25)
    c.arm("L", (0, "hold"))
    beat(c, "arm.L.wr", 6.0 * k, m.per(40), L, sharp=2.0)
    beat(c, "arm.L.sh", -3.0 * k, m.per(40), L, phase=0.5, sharp=2.0)
    sway_hips(c, 3.0 * k, m.per(60), tilt=0.4)
    c.osc("head.rot", 4.0 * k, m.per(30), phase=0.1)
    M.bob(c, m.per(30), amp=2.0 * k, st=0.008)
    return 0


@motion("juggle", "Juggling", "🤹", doing="juggling", paws=2, min_paws=2, sit="ok", wag=7, tags=("fun", "talent", "busy"), face="focused",
        paw_alt="bounce")
def juggle(m):
    """Three balls in a shower over the head: up from one paw, over the top, down into the other, and quickly back
    along the bottom; the paws toss in turn."""
    c, L, k = m.c, m.L, m.k
    per = m.per_n(60, 2)                     # one round of the three balls; an even number of rounds per loop ...
    p = per / 1.5                            # ... so the tosses (three balls per two tosses) fit the loop too
    for q, s in enumerate(m.hands):
        if q == 0:
            alternate(c, s, "hold", "hold_up", p, L, at_b=0.5, e_ab="out", e_ba="in")
        else:
            alternate(c, s, "hold_up", "hold", p, L, at_b=0.5, e_ab="in", e_ba="out")
    c.set("look.y", -0.7)
    c.osc("look.x", 0.5, per)
    c.osc("head.rot", 3.0 * k, per, phase=0.05)
    M.bob(c, p, amp=2.0 * k, st=0.008)

    def spec(char, T, n):
        (rx, ry), (lx, ly) = char.hand_to_world("R", 0, (0.0, 20.0)), char.hand_to_world("L", 0, (0.0, 20.0))
        top = char.top_world(0)[1] - 50.0
        out = []
        for q, colour in enumerate(("coral", "teal", "yellow")):
            def pos(f, q=q):
                u = (f / per + q / 3.0) % 1.0
                if u < 0.75:                     # over the head, right paw to left paw
                    v = u / 0.75
                    x, y = rx + (lx - rx) * v, ry + (ly - ry) * v
                    return (x, y - 4.0 * v * (1.0 - v) * (min(ry, ly) - top))
                w = (u - 0.75) / 0.25                # and quickly back along the bottom
                return (lx + (rx - lx) * w, ly + (ry - ly) * w + 14.0 * math.sin(math.pi * w))
            out.append(("top", Layer(f"juggling ball {q}", [gr("shine", [el((-7, -7), (10, 10)), fl(C["white"], 70)]),
                                                             gr("ball", [el((0, 0), (36, 36)), fl(C[colour])])], p=F(n, pos, tol=0.8))))
        return out
    c.prop(spec)
    return 0


@motion("cuddle", "Cuddling", "🧸", doing="cuddling", paws=2, min_paws=1, sit="ok", wag=6, tags=("love", "cute", "cozy"), face="joy",
        uses=("plushie", "toy", "pillow"), brings="plushie", paw_alt="hug")
def cuddle(m):
    """Hugging the plushie tight and rocking side to side, a squeeze at each end of the rock."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "plushie", "toy", "pillow")
    c.arm(s, (0, "present"))
    if m.other(s):
        c.arm(m.other(s), (0, "hug"))
    p = m.per(60)
    c.osc("body.rot", 4.0 * k, p)
    c.osc("head.rot", 7.0 * k, p, phase=0.05)
    beat(c, "body.sx", 0.02 * k, p / 2.0, L, phase=0.75, sharp=2.0)
    beat(c, "body.sy", -0.015 * k, p / 2.0, L, phase=0.75, sharp=2.0)
    return int(0.25 * p)


@motion("write", "Writing", "✍️", doing="writing", paws=2, min_paws=1, sit="ok", wag=3, tags=("study", "work", "note"), face="focused",
        uses=("pencil", "study"), brings="pencil", paw_alt="think")
def write(m):
    """Scribbling on a little notepad: line after line appears under the pencil, then the page clears."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "pencil", "study")
    c.arm(s, (0, "text"))
    p = m.per(10)
    c.osc(f"arm.{s}.sh", 3.0 * k, p)
    c.osc(f"arm.{s}.el", 3.0 * k, p, phase=0.25)
    c.osc("look.x", 0.25, m.per(60))
    c.set("look.y", 0.7)
    c.k("head.y", (0, 3.0))
    c.osc("head.rot", 2.0 * k, m.per(60), phase=0.05)
    o = m.other(s)
    if o:
        c.arm(o, (0, "belly"))
    sgn = 1.0 if s == "R" else -1.0

    def spec(char, T, n):
        tip = char.hand_to_world(s, 0, (0.0, 17.0 + 30.0))
        cx, cy = tip[0] - sgn * 18.0, tip[1] + 6.0
        lines = []
        for q in range(3):
            y = cy - 22.0 + 16.0 * q
            path = smooth([(cx - 26 + 13 * j, y + (3 if j % 2 else -3)) for j in range(5)], closed=False, tension=0.4)
            t0, t1 = frames_of(L, 0.05 + 0.27 * q, 0.27 + 0.27 * q)
            end = K(n, (0, 0.0), (t0, 0.0, "hold"), (t1, 100.0, "io"), (L - 1, 100.0, "hold"))
            lines.append(gr(f"line {q}", [sh(path), tm(0, end), st(C["ink"], 4)]))
        op = K(n, (0, 100.0), (frames_of(L, 0.9)[0], 100.0, "hold"), (L - 1, 0.0, "io"))
        paper = [gr("ink", lines, o=op), gr("rule", [sh(Path([(cx - 34, cy - 30 + 16 * q), (cx + 34, cy - 30 + 16 * q)], closed=False))
                                                     for q in range(4)] + [st(C["sky2"], 2)]),
                 gr("page", [rc((cx, cy - 6), (84, 68), 6), fl(C["paper"])]), gr("edge", [rc((cx, cy - 6), (84, 68), 6), st(C["sand"], 3)]),
                 gr("cover", [rc((cx + 4, cy - 2), (84, 68), 6), fl(C["coral"])])]
        return [("front", Layer("notepad", paper))]
    c.prop(spec)
    return frames_of(L, 0.7)[0]


@motion("magic", "Casting a spell", "🪄", doing="casting a spell", paws=2, min_paws=1, sit="ok", wag=9, tags=("magic", "wizard", "fairy"),
        face="excited", uses=("wand", "magic"), brings="wand", paw_alt="ta_da")
def magic(m):
    """Wand up, a flick, and a burst of sparkles from the star."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "wand", "magic")
    t_up, t_flick, t_down = frames_of(L, 0.18, 0.3, 0.7)
    c.arm(s, (0, "hold_up"), (t_up, "cheer", "io"), (t_flick, "point_fwd", "in"), (t_down, "point_fwd", "hold"), (L, "hold_up", "io"))
    c.prop(burst(t_flick, lambda char, T: prop_point(char, s, t_flick, (0.0, -118.0), upright=True, tilt=18.0), count=9,
                 colours=("yellow", "gum", "lilac", "white"), reach=70, life=22, kind="star", size=13.0, seed=21))
    bump(c, "body.sy", t_flick - 4, t_flick + 14, -0.03 * k, rise=4, fall=10)
    bump(c, "hip.y", t_up - 6, t_flick + 6, -4.0 * k, rise=8, fall=6)
    o = m.other(s)
    if o:
        c.arm(o, (0, "relax"), (t_flick, "cheer_out", "back"), (t_down, "cheer_out", "hold"), (L, "relax", "io"))
    return t_flick + 5


@motion("fan_self", "Fanning", "🪭", doing="fanning itself", paws=2, min_paws=1, sit="ok", wag=3, tags=("hot", "summer", "flustered"),
        face="flustered", uses=("fan",), brings="fan", paw_alt="sway")
def fan_self(m):
    """Flap-flap-flap at the face: it's hot."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "fan")
    c.arm(s, (0, "cheek"))
    p = m.per(10)
    c.osc(f"arm.{s}.wr", 14.0 * k, p)
    c.osc(f"arm.{s}.el", 6.0 * k, p, phase=0.1)
    c.k("head.y", (0, 3.0))
    sgn = 1.0 if s == "R" else -1.0
    c.k("head.rot", (0, -5.0 * sgn))
    o = m.other(s)
    if o:
        c.arm(o, (0, "hip"))
    M.breathe(c, period=m.per(30), amp=0.025)
    return 0


@motion("blow_nose", "Blowing its nose", "🤧", doing="blowing its nose", paws=2, min_paws=1, sit="ok", wag=2, tags=("sick", "cold", "flu"),
        face="sick", uses=("tissue",), brings="tissue", paw_alt="shiver")
def blow_nose(m):
    """Tissue to the nose, two big honks, tissue down."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "tissue")
    t_up, t_down = frames_of(L, 0.15, 0.8)
    c.arm(s, (0, "hold"), (t_up, "mouth", "io"), (t_down, "mouth", "hold"), (L, "hold", "io"))
    for u in (0.36, 0.56):
        t = frames_of(L, u)[0]
        bump(c, "head.y", t - 6, t + 10, -5.0 * k, rise=6, fall=10, e_in="in")
        bump(c, "body.sy", t - 6, t + 10, 0.04 * k, rise=6, fall=10, e_in="in")
        M.ear_flick(c, "R", t, amp=12.0)
        M.ear_flick(c, "L", t, amp=-12.0)
    o = m.other(s)
    if o:
        c.arm(o, (0, "belly"))
    return frames_of(L, 0.4)[0]


@motion("show_off", "Showing off", "🤩", doing="showing off", paws=2, min_paws=1, sit="ok", wag=10, tags=("proud", "look", "new"),
        face="proud", uses=("award", "love", "study", "money", "shopping", "food", "drink", "tech", "festival", "toy", "celebrate", "message",
                            "music", "art", "magic", "sport", "travel"),
        brings="trophy", paw_alt="ta_da")
def show_off(m):
    """Up it goes for everyone to see, with a sparkle and a proud little hop; the free paw on the hip."""
    c, L, k = m.c, m.L, m.k
    s = (m.data.get("acts") or [(None, None)])[0][1] or m.side
    if s == "LR":
        s = m.hands[0]
    t_up, t_down = frames_of(L, 0.16, 0.84)
    c.arm(s, (0, "hold"), (t_up, "hold_up", "back"), (t_down, "hold_up", "hold"), (L, "hold", "io"))
    c.osc(f"arm.{s}.sh", 4.0 * k, m.per(30))
    c.prop(burst(t_up + 2, paw_at(s, t_up + 2, (0.0, -40.0)), count=7, colours=("yellow", "white"), reach=60, life=18, kind="star",
                 size=12.0, seed=31))
    M.jump(c, t_up - 8, h=22.0 * k, air=14, anti=6, sq=0.05, st=0.05, settle=12)
    o = m.other(s)
    if o:
        c.arm(o, (0, "hip"))
    return t_up + 10


@motion("wave_flag", "Waving a flag", "🚩", doing="waving a flag", paws=2, min_paws=1, sit="ok", wag=10, tags=("cheer", "team", "sport"),
        face="excited", uses=("flag",), brings="flag", paw_alt="cheer")
def wave_flag(m):
    """The flag swings from side to side over the head."""
    c, L, k = m.c, m.L, m.k
    s = _side(m, "flag")
    p = m.per(40)
    alternate(c, s, "hold_up", "cheer", p, L, at_b=0.5, e_ab="io", e_ba="io")
    o = m.other(s)
    if o:
        c.arm(o, (0, "cheer_out"))
        c.osc(f"arm.{o}.sh", 6.0 * k, p, phase=0.5)
    M.bob(c, p / 2.0, amp=3.0 * k, st=0.012)
    c.osc("head.rot", 3.0 * k, p)
    return int(0.5 * p)


@motion("knock", "Knock knock", "🚪", doing="knocking", paws=1, min_paws=1, sit="ok", wag=4, tags=("hello", "anyone there"), face="curious",
        paw_alt="look_around")
def knock(m):
    """Knock, knock, knock on the screen (the fist comes at the viewer, little impact lines), then a listen."""
    c, L, k = m.c, m.L, m.k
    s = m.side
    shape(c, s, 1)
    t_in = frames_of(L, 0.1)[0]
    knocks = [frames_of(L, u)[0] for u in (0.2, 0.3, 0.4)]
    t_out = frames_of(L, 0.82)[0]
    c.arm(s, (0, "rest"), (t_in, "hold", "back"), (t_out, "hold", "hold"), (L, "rest", "io"))
    sgn = 1.0 if s == "R" else -1.0
    for t in knocks:
        M.addkeys(c, f"hand.{s}.s", (t - 4, 0.0), (t, 0.4 * k, "in"), (t + 6, 0.0, "out"))
        M.addkeys(c, f"arm.{s}.el", (t - 4, 0.0), (t, -10.0 * k, "in"), (t + 6, 0.0, "out"))

        def lines(char, T, n, t=t):
            x, y = char.hand_to_world(s, t, (0.0, 22.0))
            out = []
            for q, a in enumerate((20, 60, 110, 160)):
                d = (math.cos(math.radians(a)), -math.sin(math.radians(a)))
                seg = Path([(x + d[0] * 40, y + d[1] * 40), (x + d[0] * 60, y + d[1] * 60)], closed=False)
                op = K(n, (0, 0.0), (t, 0.0, "hold"), (t + 2, 100.0, "out"), (t + 9, 0.0, "in"))
                out.append(("top", Layer(f"knock {t} {q}", [gr("line", [sh(seg), st(C["dark"], 6)])], o=op)))
            return out
        c.prop(lines)
    t_listen = frames_of(L, 0.55)[0]
    c.k("head.rot", (0, 0.0), (t_listen, 8.0 * sgn, "io"), (t_out, 8.0 * sgn, "hold"), (L, 0.0, "io"))
    c.k("look.x", (0, 0.0), (t_listen, 0.6 * sgn, "io"), (t_out, 0.6 * sgn, "hold"), (L, 0.0, "io"))
    c.ears((0, 0), (t_listen, -8), (t_out, -8, "hold"), (L, 0))
    return knocks[1] + 1
