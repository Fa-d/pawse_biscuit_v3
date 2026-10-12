"""The first fourteen sticker motions (from v3), unchanged in how they move.

A motion is fn(m) -> frame for the still image, where m is a registry.Act: m.c the clip, m.L its length, m.k the
intensity, m.hands the paws it may animate, m.per(n) a period near n frames that fits the loop (and follows the
tempo).  Every periodic movement uses m.per, so the loop has no seam.
"""
from __future__ import annotations

from mascot import props as P
from mascot.clips import moves as M

from ..registry import motion


@motion("idle", "Stand still", "🧍", doing="standing", sit="ok", wag=5, tags=("calm",))
def idle(m):
    c, L, k = m.c, m.L, m.k
    M.breathe(c, period=m.per(60), amp=0.02 * k)
    c.k("head.rot", (0, 0), (L // 2, 2.0 * k, "soft"), (L, 0, "soft"))
    c.blink(int(L * 0.62))
    return 0


@motion("bounce", "Bounce", "⤴️", doing="bouncing", wag=11, tags=("happy",))
def bounce(m):
    c = m.c
    M.bob(c, m.per(30), amp=4.5 * m.k, st=0.018)
    c.osc("head.rot", 3.0 * m.k, m.per(60))
    return 0


@motion("jump", "Jump", "🤸", doing="jumping", paws=2, wag=10, tags=("happy", "energy"))
def jump(m):
    c, L, k = m.c, m.L, m.k
    air = 30 if L >= 90 else 22
    t0 = max(2, int(L * 0.1))
    tl, ta, td = M.jump(c, t0, h=52 * k, air=air, anti=9, spread=9.0, settle=min(18, L - t0 - 9 - air - 5))
    c.prop(P.dust(td, 256, n_puffs=4))
    for s in m.hands:
        c.arm(s, (0, "relax"), (tl - 2, "lap", "out"), (tl + 8, "cheer", "back"), (td, "cheer"), (min(L - 2, td + 16), "relax", "io"), (L, "relax"))
    return int(ta)


@motion("cheer", "Cheer", "🙌", doing="cheering", paws=2, wag=12, tags=("happy", "celebrate"))
def cheer(m):
    c, k = m.c, m.k
    p = m.per(24)
    for q, s in enumerate(m.hands):
        c.arm(s, (0, "cheer"))
        c.osc(f"arm.{s}.sh", 13.0 * k, p, phase=0.06 * q)
        c.osc(f"arm.{s}.el", 9.0 * k, p, phase=0.06 * q + 0.12)
    M.bob(c, p, amp=5.0 * k, st=0.02)
    c.osc("head.rot", 3.0, m.per(48))
    return int(p / 4)


@motion("wave", "Wave", "👋", doing="waving", paws=1, sit="ok", wag=8, tags=("greeting",), face="smiley")
def wave(m):
    c, k = m.c, m.k
    p = m.per(30)
    side = m.side
    if side:
        M.wave(c, side, None, None, period=p, swing=24.0 * k)
        c.k("head.rot", (0, 3 if side == "R" else -3))
    M.bob(c, p, amp=3.0 * k, st=0.008)
    return int(p / 2)


@motion("dance", "Dance", "💃", doing="dancing", paws=2, wag=12, tags=("happy", "party", "music"))
def dance(m):
    c, L, k = m.c, m.L, m.k
    M.patter(c, 0, L, period=m.per(10), lift=6.0 * k)
    M.bob(c, m.per(20), amp=3.0 * k, st=0.012)
    c.osc("body.rot", 3.5 * k, m.per(40))
    c.osc("head.rot", -4.0 * k, m.per(40), phase=0.1)
    for q, s in enumerate(m.hands):
        c.arm(s, (0, "cheer_out"))
        c.osc(f"arm.{s}.sh", 10.0 * k, m.per(40), phase=0.5 * q)
    return int(m.per(40) / 4)


@motion("walk", "Walk", "🚶", doing="walking", wag=6, tags=("travel",))
def walk(m):
    p = m.per(60)
    M.walk(m.c, period=p, lift=15.0 * m.k)
    return int(p * 0.2)


@motion("nod", "Nod yes", "👍", doing="nodding", sit="ok", wag=6, tags=("yes",), face="smiley")
def nod(m):
    c, L = m.c, m.L
    p = m.per(40)
    t = 0.0
    while t + 16 <= L:
        M.nod(c, int(t), amp=6.0 * m.k)
        t += p
    return 6


@motion("no", "Shake no", "🙅", doing="shaking its head", sit="ok", wag=4, tags=("no",), face="focused")
def no(m):
    c, k = m.c, m.k
    p = m.per(30)
    c.osc("head.rot", 9.0 * k, p)
    c.osc("look.x", -0.4, p)
    c.osc("body.rot", 1.5 * k, p, phase=0.5)
    return int(p / 4)


@motion("shiver", "Shiver", "🥶", doing="shivering", paws=2, wag=2, tags=("cold", "scared"), face="worried")
def shiver(m):
    c, L, k = m.c, m.L, m.k
    c.set("hip.y", 6.0)
    for s in "LR":
        c.set(f"leg.{s}.bend", -1.0)
    c.osc("root.x", 1.6 * k, m.per(6))
    c.osc("body.rot", 1.0 * k, m.per(8))
    c.ears((0, 22))
    for s in m.hands:
        c.arm(s, (0, "belly"))
    return 0


@motion("sway", "Sway", "🎶", doing="swaying", sit="ok", wag=5, tags=("calm",), calm=True)
def sway(m):
    c, L, k = m.c, m.L, m.k
    c.osc("body.rot", 3.0 * k, L)
    c.osc("head.rot", -1.5 * k, L, phase=0.1)
    c.osc("hip.x", 4.0 * k, L)
    M.breathe(c, period=m.per(60), amp=0.02)
    return int(L / 4)


@motion("sleep", "Doze", "😴", doing="dozing", sit="ok", stance="sit", wag=3, blink=False, tags=("sleep",), face="sleep", calm=True)
def sleep(m):
    c, L, k = m.c, m.L, m.k
    M.breathe(c, period=m.per(120), amp=0.035 * k)
    c.osc("head.rot", 2.5, m.per(120))
    c.set("head.y", 4.0)
    c.ears((0, 10))
    return 0


@motion("think", "Think", "🤔", doing="thinking", paws=1, sit="ok", wag=4, blink=False, tags=("think",), face="curious")
def think(m):
    c, L, k = m.c, m.L, m.k
    if m.hands:
        c.arm(m.hands[0], (0, "chin"))
    c.osc("head.rot", 2.5 * k, L)
    c.set("look.x", 0.6)
    c.set("look.y", -0.6)
    M.breathe(c, period=m.per(60), amp=0.02)
    return 0


@motion("hide", "Hide eyes", "🙈", doing="hiding its eyes", paws=2, sit="ok", wag=3, blink=False, tags=("shy",), face="worried")
def hide(m):
    c, L, k = m.c, m.L, m.k
    hands = m.hands
    for s in hands:
        c.arm(s, (0, "cover_eyes"))
    if len(hands) == 2:                                        # one paw lifts to peek, then covers again
        s = hands[1]
        c.arm(s, (0, "cover_eyes"), (int(L * 0.3), "cover_eyes"), (int(L * 0.4), "peek", "out"), (int(L * 0.7), "peek"),
              (int(L * 0.8), "cover_eyes", "io"), (L, "cover_eyes"))
    c.osc("root.x", 0.8 * k, m.per(8))
    return int(L * 0.55)
