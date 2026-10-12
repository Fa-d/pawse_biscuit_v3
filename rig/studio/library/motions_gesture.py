"""Gestures: what the paws and the head say (clap, shrug, facepalm, salute, thumbs up, point, peace sign ...).

Each motion takes the paws the composer gives it (m.hands: free paws, right first) and works with fewer when it can
(min_paws), so "clapping with a mug in one paw" becomes a one-paw version or the motion it names in paw_alt.
"""
from __future__ import annotations

from mascot import props as P

from ..registry import motion
from .acting import M, alternate, beat, bump, frames_of, hold_pose, math, shake, shape, sway_hips
from .common import C, F, Layer, gr, heart_path, sh, fl, star4


def _both(m):
    return list(m.hands)


@motion("clap", "Clap", "👏", doing="clapping", paws=2, sit="ok", wag=10, tags=("happy", "celebrate"), face="joy", paw_alt="thumbs_up")
def clap(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(18)
    for s in _both(m):
        alternate(c, s, "clap_open", "clap", p, L, at_b=0.45, e_ab="in", e_ba="out")
    M.bob(c, m.per(36), amp=2.5 * k, st=0.01)
    c.osc("head.rot", 2.0 * k, m.per(36))
    beat(c, "body.sx", 0.012 * k, p, L, phase=0.55, sharp=3.0)
    return int(p * 0.45)


@motion("shrug", "Shrug", "🤷", doing="shrugging", paws=2, min_paws=0, sit="ok", wag=4, tags=("unsure",), face="confused")
def shrug(m):
    c, L, k = m.c, m.L, m.k
    t_up, t_hold, t_down = frames_of(L, 0.14, 0.62, 0.86)
    for s in m.hands:
        c.arm(s, (0, "relax"), (t_up, "shrug", "back"), (t_hold, "shrug", "hold"), (t_down, "relax", "io"), (L, "relax"))
    bump(c, "head.y", 0, t_down, 7.0 * k, rise=t_up, fall=t_down - t_hold, e_in="back")
    bump(c, "head.rot", 0, t_down, 8.0 * k, rise=t_up, fall=t_down - t_hold, e_in="back")
    bump(c, "brow.y", 0, t_down, 6.0, rise=t_up, fall=t_down - t_hold)
    bump(c, "body.sy", 0, t_down, 0.025 * k, rise=t_up, fall=t_down - t_hold)
    return (t_up + t_hold) // 2


@motion("facepalm", "Facepalm", "🤦", doing="facepalming", paws=1, min_paws=0, sit="ok", wag=3, tags=("annoyed",), face="unamused")
def facepalm(m):
    c, L, k = m.c, m.L, m.k
    t_in, t_out = frames_of(L, 0.12, 0.84)
    if m.side:
        hold_pose(c, m.side, "facepalm", t_in, t_out, L, e_in="in")
    bump(c, "head.y", t_in - 2, L, 6.0 * k, rise=10, fall=L - t_out)
    shake(c, "head.rot", 3.0 * k, t_in + 8, t_out, 3)
    M.addkeys(c, "head.rot", (t_in - 2, 0.0), (t_in + 2, -5.0 * k, "out"), (t_in + 10, 0.0, "io"))
    return (t_in + t_out) // 2


@motion("salute", "Salute", "🫡", doing="saluting", paws=1, min_paws=1, sit="ok", wag=4, tags=("respect",), face="determined",
        paw_alt="nod")
def salute(m):
    c, L, k = m.c, m.L, m.k
    t_in, t_out = frames_of(L, 0.12, 0.84)
    hold_pose(c, m.side, "salute", t_in, t_out, L, e_in="snap")
    M.addkeys(c, "head.y", (t_in - 4, 0.0), (t_in + 2, -3.0 * k, "out"), (t_in + 12, 0.0, "back"))
    bump(c, "body.sy", t_in - 4, t_out, 0.02 * k, rise=8, fall=10)
    bump(c, "hip.y", t_in - 4, t_out, -2.0 * k, rise=8, fall=10)
    return (t_in + t_out) // 2


@motion("flex", "Flex", "💪", doing="flexing", paws=2, min_paws=1, sit="ok", wag=8, tags=("strong",), face="determined")
def flex(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(30)
    shape(c, "".join(m.hands), 1)
    for q, s in enumerate(m.hands):
        c.arm(s, (0, "flex"))
        c.osc(f"arm.{s}.el", 12.0 * k, p, phase=0.5 * q)
        c.osc(f"arm.{s}.sh", -5.0 * k, p, phase=0.5 * q)
    beat(c, "body.sx", 0.03 * k, p / 2.0, L)
    M.bob(c, p, amp=2.0 * k, st=0.0)
    return int(p / 4)


@motion("pray", "Paws together", "🙏", doing="with its paws together", paws=2, min_paws=1, sit="ok", wag=3, tags=("calm", "please"),
        face="calm", calm=True)
def pray(m):
    c, L, k = m.c, m.L, m.k
    for s in m.hands:
        c.arm(s, (0, "pray"))
    p = m.per(90)
    c.osc("head.y", 2.5 * k, p)
    c.osc("head.rot", 1.5 * k, p, phase=0.25)
    M.breathe(c, period=p, amp=0.02)
    return 0


@motion("plead", "Pretty please", "🥺", doing="pleading", paws=2, min_paws=1, sit="ok", wag=6, tags=("please",), face="pleading")
def plead(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(12)
    for q, s in enumerate(m.hands):
        c.arm(s, (0, "pray"))
        c.osc(f"arm.{s}.sh", 4.0 * k, p, phase=0.5 * q)
        c.osc(f"arm.{s}.el", -4.0 * k, p, phase=0.5 * q)
    c.k("head.rot", (0, 6.0))
    M.bob(c, m.per(40), amp=2.0 * k, st=0.01)
    return 0


def _thumbs(m, pose, k_shape=2, shake_no=False):
    c, L, k = m.c, m.L, m.k
    p = m.per(30)
    sides = m.hands or []
    shape(c, "".join(sides), k_shape)
    t_in = frames_of(L, 0.1)[0]
    for q, s in enumerate(sides):
        c.arm(s, (0, pose))
        c.osc(f"arm.{s}.sh", 5.0 * k, p, phase=0.25 * q)
    if shake_no:
        c.osc("head.rot", 6.0 * k, p)
    else:
        M.bob(c, p, amp=2.5 * k, st=0.012)
        c.osc("head.rot", 2.0 * k, m.per(60))
    return t_in


@motion("thumbs_up", "Thumbs up", "👍", doing="giving a thumbs up", paws=2, min_paws=1, sit="ok", wag=9, tags=("yes", "good"),
        face="grin", paw_alt="nod")
def thumbs_up(m):
    return _thumbs(m, "thumbs_up")


@motion("thumbs_down", "Thumbs down", "👎", doing="giving a thumbs down", paws=1, min_paws=1, sit="ok", wag=3, tags=("no", "bad"),
        face="unamused", paw_alt="no")
def thumbs_down(m):
    return _thumbs(m, "thumbs_down", shake_no=True)


@motion("point", "Point at you", "🫵", doing="pointing at you", paws=1, min_paws=1, sit="ok", wag=7, tags=("you",), face="grin",
        paw_alt="nod")
def point(m):
    c, L, k = m.c, m.L, m.k
    s = m.side
    shape(c, s, 3)
    c.arm(s, (0, "point_fwd"))
    p = m.per(L / 2.0)
    for q in range(max(1, round(L / p))):
        t = int(q * p)
        c.pulse(f"hand.{s}.s", t + 2, 0.22 * k, up=5, down=12, e_up="out", e_down="io")
        c.pulse(f"arm.{s}.len", t + 2, 0.12 * k, up=5, down=12, e_up="out", e_down="io")
        c.pulse("head.y", t + 2, -3.0 * k, up=5, down=12)
    return 7


@motion("eureka", "Idea!", "☝️", doing="having an idea", paws=1, min_paws=1, sit="ok", wag=10, tags=("idea",), face="excited",
        paw_alt="jump")
def eureka(m):
    c, L, k = m.c, m.L, m.k
    s = m.side
    shape(c, s, 3)
    t_up, t_out = frames_of(L, 0.16, 0.86)
    hold_pose(c, s, "point_up", t_up, t_out, L, rest="relax", e_in="back")
    if not m.sitting and L >= 60:
        M.jump(c, max(2, t_up - 12), h=26 * k, air=16, anti=6, settle=12)
    bump(c, "brow.y", t_up - 6, t_out, 8.0, rise=6, fall=10)
    shake(c, f"arm.{s}.wr", 7.0 * k, t_up, t_out, max(1, round((t_out - t_up) / 22.0)))
    return t_up + 10


@motion("peace", "Peace sign", "✌️", doing="making a peace sign", paws=1, min_paws=1, sit="ok", wag=9, tags=("cool", "fun"),
        face="wink", paw_alt="nod")
def peace(m):
    c, L, k = m.c, m.L, m.k
    s = m.side
    shape(c, s, 4)
    p = m.per(40)
    c.arm(s, (0, "wave_hi"))
    c.osc(f"arm.{s}.el", 6.0 * k, p)
    c.k("head.rot", (0, 5.0 if s == "R" else -5.0))
    M.bob(c, p, amp=3.0 * k, st=0.012)
    return int(p / 4)


@motion("fist_pump", "Fist pump", "✊", doing="pumping its fist", paws=1, min_paws=1, sit="ok", wag=12, tags=("win", "yes"),
        face="excited", paw_alt="bounce")
def fist_pump(m):
    c, L, k = m.c, m.L, m.k
    s = m.side
    shape(c, s, 1)
    p = m.per(22)
    alternate(c, s, "fist_pump", (62, 118, 0, 1.15), p, L, at_b=0.5, e_ab="in", e_ba="out")
    M.bob(c, p, amp=4.0 * k, st=0.02)
    return 0


@motion("dab", "Dab", "😎", doing="dabbing", paws=2, min_paws=2, sit="ok", wag=6, tags=("cool", "dance"), face="cool",
        paw_alt="fist_pump")
def dab(m):
    c, L, k = m.c, m.L, m.k
    t_in, t_out = frames_of(L, 0.14, 0.8)
    a, b = ("R", "L") if m.hands[0] == "R" else ("L", "R")
    hold_pose(c, a, "dab", t_in, t_out, L, e_in="snap")
    hold_pose(c, b, "dab_in", t_in, t_out, L, e_in="snap")
    sgn = 1.0 if a == "R" else -1.0
    bump(c, "head.rot", t_in - 6, L, -sgn * 12.0 * k, rise=8, fall=L - t_out)
    bump(c, "head.y", t_in - 6, L, 8.0 * k, rise=8, fall=L - t_out)
    bump(c, "hip.x", t_in - 6, L, -sgn * 6.0 * k, rise=8, fall=L - t_out)
    return (t_in + t_out) // 2


@motion("hug", "Hug", "🤗", doing="hugging", paws=2, min_paws=1, sit="ok", wag=8, tags=("love",), face="joy")
def hug(m):
    c, L, k = m.c, m.L, m.k
    t_in, t_out = frames_of(L, 0.3, 0.84)
    for s in m.hands:
        c.arm(s, (0, "wide"), (t_in, "hug", "out"), (t_out, "hug", "hold"), (L, "wide", "io"))
    bump(c, "body.sx", t_in - 4, t_out + 6, -0.04 * k, rise=8, fall=12)
    bump(c, "body.sy", t_in - 4, t_out + 6, 0.03 * k, rise=8, fall=12)
    shake(c, "body.rot", 3.0 * k, t_in, t_out, 1)
    bump(c, "head.rot", t_in - 4, t_out + 6, 6.0 * k, rise=10, fall=12)
    return (t_in + t_out) // 2


@motion("ta_da", "Ta-da!", "👐", doing="presenting itself", paws=2, min_paws=1, wag=12, tags=("show", "happy"), face="joy",
        sit_alt="wave_both")
def ta_da(m):
    c, L, k = m.c, m.L, m.k
    t_dip, t_pop, t_hold = frames_of(L, 0.12, 0.24, 0.8)
    for s in m.hands:
        c.arm(s, (0, "wide"), (t_dip, "lap", "io"), (t_pop, "wide", "back"), (t_hold, "wide", "hold"), (L, "wide"))
    c.stance((0, m.stance), (t_dip, "crouch", "io"), (t_pop, "tiptoe", "back"), (t_hold, "tiptoe", "hold"), (L, m.stance, "io"))
    bump(c, "body.sy", t_pop - 4, t_hold, 0.035 * k, rise=6, fall=10, e_in="back")
    return (t_pop + t_hold) // 2


@motion("blow_kiss", "Blow a kiss", "😘", doing="blowing a kiss", paws=1, min_paws=1, sit="ok", wag=8, tags=("love",), face="kiss",
        paw_alt="sway")
def blow_kiss(m):
    c, L, k = m.c, m.L, m.k
    s = m.side
    t_lips, t_throw, t_back = frames_of(L, 0.2, 0.42, 0.8)
    c.arm(s, (0, "rest"), (t_lips, "mouth", "out"), (t_lips + 6, "mouth", "hold"), (t_throw, "cheer_out", "out"), (t_back, "cheer_out", "hold"),
          (L, "rest", "io"))
    bump(c, "head.rot", t_lips - 6, t_back, (5.0 if s == "R" else -5.0) * k, rise=8, fall=10)

    def heart(char, T, n):
        sgn = 1.0 if s == "R" else -1.0
        x0, y0 = char.head_to_world(0, char.mouth)
        x1, y1 = x0 + sgn * 130.0, y0 - 120.0
        tt = t_throw - 2

        def u(f):
            return max(0.0, min(1.0, (f - tt) / float(max(1, t_back - tt))))
        pos = F(n, lambda f: (x0 + (x1 - x0) * (1 - (1 - u(f)) ** 2), y0 + (y1 - y0) * u(f) - 18 * math.sin(math.pi * u(f))), tol=0.6)
        scl = F(n, lambda f: (0.0, 0.0) if f < tt else (30 + 90 * min(1.0, u(f) * 3),) * 2, tol=1.5)
        op = F(n, lambda f: 0.0 if f < tt else 100 * min(1.0, (1 - u(f)) * 4), tol=2.5)
        return [("top", Layer("kiss heart", [gr("heart", [sh(heart_path(34)), fl(C["coral"])])], p=pos, s=scl, o=op))]
    c.prop(heart)
    return t_throw + 6


@motion("high_five", "High five", "✋", doing="giving a high five", paws=1, min_paws=1, sit="ok", wag=10, tags=("friends", "yes"),
        face="excited", paw_alt="bounce")
def high_five(m):
    c, L, k = m.c, m.L, m.k
    s = m.side
    t_up, t_hit, t_out = frames_of(L, 0.18, 0.4, 0.84)
    c.arm(s, (0, "rest"), (t_up, "reach", "back"), (t_out, "reach", "hold"), (L, "rest", "io"))
    c.pulse(f"hand.{s}.s", t_hit - 6, 0.38 * k, up=6, down=16, e_up="in", e_down="back")
    M.squash(c, t_hit, amount=0.05 * k, pre=4, post=14)

    def burst(char, T, n):
        out = []
        for q in range(4):
            a = math.radians(-60 + q * 40 + (0 if s == "R" else 180))
            def scl(f, q=q):
                x = (f - t_hit) / 14.0
                return (0.0, 0.0) if x < 0 or x > 1 else (100 * math.sin(math.pi * x),) * 2
            px, py = char.hand_to_world(s, t_hit, (0.0, 20.0))
            out.append(("top", Layer(f"clap star {q}", [gr("star", [sh(star4((0, 0), 16)), fl(C["yellow"])])],
                                     p=(px + 60 * math.cos(a), py - 60 * math.sin(a)), s=F(n, scl, tol=2.0))))
        return out
    c.prop(burst)
    return t_hit + 2


@motion("wave_both", "Wave both paws", "🙌", doing="waving both paws", paws=2, min_paws=2, sit="ok", wag=10, tags=("greeting",),
        face="joy", paw_alt="wave")
def wave_both(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(30)
    for s in m.hands:
        M.wave(c, s, None, None, period=p, swing=24.0 * k)
    M.bob(c, p, amp=3.5 * k, st=0.012)
    return int(p / 2)


@motion("bow", "Bow", "🙇", doing="bowing", paws=2, min_paws=0, sit="ok", wag=3, blink=False, tags=("thanks", "sorry"), face="calm")
def bow(m):
    c, L, k = m.c, m.L, m.k
    t_down, t_up = frames_of(L, 0.3, 0.78)
    if m.hands:
        hold_pose(c, m.hands[0], "chest", int(L * 0.15), t_up + 6, L)
    if len(m.hands) > 1:
        c.arm(m.hands[1], (0, "behind"))
        c.set(f"arm.{m.hands[1]}.back", 1.0)
    for ch, amp in (("head.y", 30.0), ("hip.y", 8.0)):
        bump(c, ch, int(L * 0.1), L, amp * k, rise=t_down - int(L * 0.1), fall=L - t_up, e_in="io")
    bump(c, "head.sy", int(L * 0.1), L, -0.08 * k, rise=t_down - int(L * 0.1), fall=L - t_up, e_in="io")
    bump(c, "body.sy", int(L * 0.1), L, -0.08 * k, rise=t_down - int(L * 0.1), fall=L - t_up, e_in="io")
    bump(c, "look.y", int(L * 0.1), L, 0.8, rise=t_down - int(L * 0.1), fall=L - t_up, e_in="io")
    c.ears((0, 0), (t_down, 14), (t_up, 14, "hold"), (L, 0))
    return (t_down + t_up) // 2


@motion("stretch", "Stretch", "🙆", doing="stretching", paws=2, min_paws=0, wag=4, tags=("morning", "tired"), face="yawn",
        sit_alt="yawn")
def stretch(m):
    c, L, k = m.c, m.L, m.k
    t_up, t_hold, t_down = frames_of(L, 0.25, 0.62, 0.86)
    for s in m.hands:
        c.arm(s, (0, "rest"), (t_up, "stretch", "io"), (t_hold, "stretch", "hold"), (t_down, "rest", "io"), (L, "rest"))
    c.stance((0, m.stance), (t_up, "tiptoe", "io"), (t_hold, "tiptoe", "hold"), (t_down, m.stance, "io"), (L, m.stance))
    bump(c, "body.sy", 0, t_down, 0.05 * k, rise=t_up, fall=t_down - t_hold, e_in="io")
    shake(c, "body.rot", 2.0 * k, t_up, t_hold, 1)
    return (t_up + t_hold) // 2


@motion("yawn", "Yawn", "🥱", doing="yawning", paws=1, min_paws=0, sit="ok", wag=3, blink=False, tags=("tired", "morning"),
        face="yawn", calm=True)
def yawn(m):
    c, L, k = m.c, m.L, m.k
    t_in, t_out = frames_of(L, 0.25, 0.8)
    if m.side:
        hold_pose(c, m.side, "mouth", t_in, t_out, L, e_in="io")
    bump(c, "head.rot", 0, L, -6.0 * k, rise=t_in, fall=L - t_out, e_in="io")
    bump(c, "head.y", 0, L, -4.0 * k, rise=t_in, fall=L - t_out, e_in="io")
    bump(c, "body.sy", 0, L, 0.03 * k, rise=t_in, fall=L - t_out, e_in="io")
    c.ears((0, 0), (t_in, 10), (t_out, 10, "hold"), (L, 0))
    return (t_in + t_out) // 2


@motion("giggle", "Giggle", "🤭", doing="giggling", paws=1, min_paws=0, sit="ok", wag=9, tags=("funny",), face="laugh")
def giggle(m):
    c, L, k = m.c, m.L, m.k
    if m.side:
        c.arm(m.side, (0, "mouth"))
    p = m.per(10)
    c.osc("body.rot", 2.0 * k, p)
    c.osc("head.rot", -2.5 * k, p, phase=0.15)
    M.bob(c, m.per(30), amp=2.5 * k, st=0.012)
    return 0


@motion("shush", "Shh", "🤫", doing="shushing", paws=1, min_paws=1, sit="ok", wag=4, tags=("secret",), face="wink", paw_alt="idle")
def shush(m):
    c, L, k = m.c, m.L, m.k
    s = m.side
    shape(c, s, 3)
    t_in, t_out = frames_of(L, 0.12, 0.86)
    hold_pose(c, s, "mouth", t_in, t_out, L, e_in="out")
    bump(c, "head.y", t_in - 6, L, 4.0 * k, rise=8, fall=L - t_out)
    shake(c, "head.rot", 2.0 * k, t_in, t_out, 2)
    return (t_in + t_out) // 2


@motion("scratch_head", "Scratch head", "🤔", doing="scratching its head", paws=1, min_paws=1, sit="ok", wag=4, tags=("unsure",),
        face="confused", paw_alt="think")
def scratch_head(m):
    c, L, k = m.c, m.L, m.k
    s = m.side
    ch = m.char
    target = ch.head_pt((ch.CX + 58.0, ch.crown[1] + 6.0))
    v = ch.ik(target, bend=-1, hand=206)
    t_in, t_out = frames_of(L, 0.14, 0.84)
    c.arm(s, (0, "relax"), (t_in, v, "out"), (t_out, v, "hold"), (L, "relax", "io"))
    c.set(f"arm.{s}.front", 1.0)
    shake(c, f"arm.{s}.el", 9.0 * k, t_in, t_out, 6)
    bump(c, "head.rot", 0, L, (-6.0 if s == "R" else 6.0) * k, rise=t_in, fall=L - t_out)
    return (t_in + t_out) // 2


@motion("scheme", "Scheme", "😈", doing="scheming", paws=2, min_paws=2, sit="ok", wag=5, tags=("evil", "plan"), face="mischief",
        paw_alt="idle")
def scheme(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(14)
    for q, s in enumerate(m.hands):
        c.arm(s, (0, "pray"))
        c.osc(f"arm.{s}.sh", 5.0 * k, p, phase=0.5 * q)
        c.osc(f"arm.{s}.wr", 8.0 * k, p, phase=0.5 * q + 0.25)
    c.k("head.y", (0, 4.0))
    c.osc("head.rot", 2.0 * k, m.per(60))
    return 0


@motion("look_around", "Look around", "👀", doing="looking around", sit="ok", wag=5, tags=("curious",), face="curious")
def look_around(m):
    c, L, k = m.c, m.L, m.k
    a, b, d, e = frames_of(L, 0.08, 0.38, 0.58, 0.88)
    M.addkeys(c, "look.x", (0, 0.0), (a, -0.9, "out"), (b, -0.9, "hold"), (d, 0.9, "io"), (e, 0.9, "hold"), (L, 0.0, "io"))
    M.addkeys(c, "head.rot", (0, 0.0), (a, -6.0 * k, "out"), (b, -6.0 * k, "hold"), (d, 6.0 * k, "io"), (e, 6.0 * k, "hold"), (L, 0.0, "io"))
    M.addkeys(c, "head.x", (0, 0.0), (a, -4.0 * k, "out"), (b, -4.0 * k, "hold"), (d, 4.0 * k, "io"), (e, 4.0 * k, "hold"), (L, 0.0, "io"))
    c.blink((b + d) // 2)
    return a + 6


@motion("impatient", "Tap foot", "😒", doing="tapping its foot", paws=2, min_paws=0, wag=3, tags=("waiting", "annoyed"),
        face="unamused", sit_alt="idle")
def impatient(m):
    c, L, k = m.c, m.L, m.k
    for s in m.hands:
        c.arm(s, (0, "cross"))
    p = m.per(16)
    t = 0.0
    while t + p <= L + 1e-6:
        M.tap(c, "R", int(round(t)), n=1, up=0.55, lift=3.0)
        t += p
    c.k("head.rot", (0, -4.0))
    c.osc("hip.x", 1.5 * k, m.per(32))
    return 4


@motion("sulk", "Sulk", "😤", doing="sulking", paws=2, min_paws=0, sit="ok", wag=2, tags=("pout",), face="pout")
def sulk(m):
    c, L, k = m.c, m.L, m.k
    for s in m.hands:
        c.arm(s, (0, "cross"))
    t_huff = frames_of(L, 0.15)[0]
    M.addkeys(c, "head.rot", (0, -9.0 * k), (t_huff, -12.0 * k, "out"), (t_huff + 12, -9.0 * k, "io"), (L, -9.0 * k))
    c.set("look.x", -0.9)
    c.pulse("body.sy", t_huff - 4, 0.03 * k, up=5, down=12)
    c.pulse("hip.y", t_huff - 4, -3.0 * k, up=5, down=12)
    M.breathe(c, period=m.per(60), amp=0.02)
    return 0


@motion("sigh", "Sigh", "😮‍💨", doing="sighing", sit="ok", wag=2, blink=False, tags=("tired", "relief"), face="relieved", calm=True)
def sigh(m):
    c, L, k = m.c, m.L, m.k
    t_in, t_out = frames_of(L, 0.35, 0.55)
    M.addkeys(c, "body.sy", (0, 0.0), (t_in, 0.05 * k, "io"), (t_out, -0.03 * k, "out"), (L, 0.0, "io"))
    M.addkeys(c, "arm.R.sh", (0, 0.0), (t_in, 8.0 * k, "io"), (t_out, -4.0 * k, "out"), (L, 0.0, "io"))
    M.addkeys(c, "arm.L.sh", (0, 0.0), (t_in, 8.0 * k, "io"), (t_out, -4.0 * k, "out"), (L, 0.0, "io"))
    M.addkeys(c, "head.y", (0, 0.0), (t_in, -3.0 * k, "io"), (t_out, 5.0 * k, "out"), (L, 0.0, "io"))
    c.prop(P.breath_puff(t_out - 6, life=min(70, L - t_out + 6), count=3))
    return t_out + 4


@motion("bashful", "Aw shucks", "☺️", doing="being bashful", paws=2, min_paws=0, wag=5, tags=("shy",), face="flustered",
        sit_alt="sway")
def bashful(m):
    c, L, k = m.c, m.L, m.k
    for s in m.hands:
        c.arm(s, (0, "behind"))
        c.set(f"arm.{s}.back", 1.0)
    p = m.per(40)
    c.osc("foot.R.rot", 14.0 * k, p)
    beat(c, "foot.R.sole", 0.3, p, L)
    c.k("head.rot", (0, 7.0))
    sway_hips(c, 3.0 * k, p, tilt=0.5)
    return 0
