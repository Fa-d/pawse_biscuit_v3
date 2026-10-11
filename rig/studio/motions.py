"""Short looping motions for stickers, built only from mascot/clips/moves.py and rig channels.

Each motion is fn(c, k, hands) -> frame to use for the still image.  `k` is the intensity (1 = normal), `hands`
the paws the motion may use (the composer gives a paw to a held prop first).  Every period divides the clip
length, so each motion loops without a seam.
"""
from __future__ import annotations

from mascot.clips import moves as M
from mascot import props as P


def per(L, approx):
    """The period closest to `approx` that fits a whole number of times into L frames."""
    return L / max(1, round(L / approx))


def idle(c, k, hands):
    L = c.frames
    M.breathe(c, period=per(L, 60), amp=0.02 * k)
    c.k("head.rot", (0, 0), (L // 2, 2.0 * k, "soft"), (L, 0, "soft"))
    c.blink(int(L * 0.62))
    return 0


def bounce(c, k, hands):
    L = c.frames
    M.bob(c, per(L, 30), amp=4.5 * k, st=0.018)
    c.osc("head.rot", 3.0 * k, per(L, 60))
    return 0


def jump(c, k, hands):
    L = c.frames
    air = 30 if L >= 90 else 22
    t0 = max(2, int(L * 0.1))
    tl, ta, td = M.jump(c, t0, h=52 * k, air=air, anti=9, spread=9.0, settle=min(18, L - t0 - 9 - air - 5))
    c.prop(P.dust(td, 256, n_puffs=4))
    for s in hands:
        c.arm(s, (0, "relax"), (tl - 2, "lap", "out"), (tl + 8, "cheer", "back"), (td, "cheer"), (min(L - 2, td + 16), "relax", "io"), (L, "relax"))
    return int(ta)


def cheer(c, k, hands):
    L = c.frames
    p = per(L, 24)
    for q, s in enumerate(hands):
        c.arm(s, (0, "cheer"))
        c.osc(f"arm.{s}.sh", 13.0 * k, p, phase=0.06 * q)
        c.osc(f"arm.{s}.el", 9.0 * k, p, phase=0.06 * q + 0.12)
    M.bob(c, p, amp=5.0 * k, st=0.02)
    c.osc("head.rot", 3.0, 2 * p)
    return int(p / 4)


def wave(c, k, hands):
    L = c.frames
    p = per(L, 30)
    side = hands[0] if hands else None
    if side:
        M.wave(c, side, None, None, period=p, swing=24.0 * k)
        c.k("head.rot", (0, 3 if side == "R" else -3))
    M.bob(c, p, amp=3.0 * k, st=0.008)
    return int(p / 2)


def dance(c, k, hands):
    L = c.frames
    M.patter(c, 0, L, period=per(L, 10), lift=6.0 * k)
    M.bob(c, per(L, 20), amp=3.0 * k, st=0.012)
    c.osc("body.rot", 3.5 * k, per(L, 40))
    c.osc("head.rot", -4.0 * k, per(L, 40), phase=0.1)
    for q, s in enumerate(hands):
        c.arm(s, (0, "cheer_out"))
        c.osc(f"arm.{s}.sh", 10.0 * k, per(L, 40), phase=0.5 * q)
    return int(per(L, 40) / 4)


def walk(c, k, hands):
    L = c.frames
    p = per(L, 60)
    M.walk(c, period=p, lift=15.0 * k)
    return int(p * 0.2)


def nod(c, k, hands):
    L = c.frames
    p = per(L, 40)
    t = 0.0
    while t + 16 <= L:
        M.nod(c, int(t), amp=6.0 * k)
        t += p
    return 6


def no(c, k, hands):
    L = c.frames
    p = per(L, 30)
    c.osc("head.rot", 9.0 * k, p)
    c.osc("look.x", -0.4, p)
    c.osc("body.rot", 1.5 * k, p, phase=0.5)
    return int(p / 4)


def shiver(c, k, hands):
    L = c.frames
    c.set("hip.y", 6.0)
    for s in "LR":
        c.set(f"leg.{s}.bend", -1.0)
    c.osc("root.x", 1.6 * k, per(L, 6))
    c.osc("body.rot", 1.0 * k, per(L, 8))
    c.ears((0, 22))
    for s in hands:
        c.arm(s, (0, "belly"))
    return 0


def sway(c, k, hands):
    L = c.frames
    c.osc("body.rot", 3.0 * k, L)
    c.osc("head.rot", -1.5 * k, L, phase=0.1)
    c.osc("hip.x", 4.0 * k, L)
    M.breathe(c, period=per(L, 60), amp=0.02)
    return int(L / 4)


def sleep(c, k, hands):
    L = c.frames
    M.breathe(c, period=per(L, 120), amp=0.035 * k)
    c.osc("head.rot", 2.5, per(L, 120))
    c.set("head.y", 4.0)
    c.ears((0, 10))
    return 0


def think(c, k, hands):
    L = c.frames
    if hands:
        c.arm(hands[0], (0, "chin"))
    c.osc("head.rot", 2.5 * k, L)
    c.set("look.x", 0.6)
    c.set("look.y", -0.6)
    M.breathe(c, period=per(L, 60), amp=0.02)
    return 0


def hide(c, k, hands):
    L = c.frames
    for s in hands:
        c.arm(s, (0, "cover_eyes"))
    if len(hands) == 2:                                        # one paw lifts to peek, then covers again
        s = hands[1]
        c.arm(s, (0, "cover_eyes"), (int(L * 0.3), "cover_eyes"), (int(L * 0.4), "peek", "out"), (int(L * 0.7), "peek"), (int(L * 0.8), "cover_eyes", "io"), (L, "cover_eyes"))
    c.osc("root.x", 0.8 * k, per(L, 8))
    return int(L * 0.55)


# name -> (fn, paws it wants, ok while sitting)
MOTIONS = {
    "idle": (idle, 0, True),
    "bounce": (bounce, 0, False),
    "jump": (jump, 2, False),
    "cheer": (cheer, 2, False),
    "wave": (wave, 1, True),
    "dance": (dance, 2, False),
    "walk": (walk, 0, False),
    "nod": (nod, 0, True),
    "no": (no, 0, True),
    "shiver": (shiver, 2, False),
    "sway": (sway, 0, True),
    "sleep": (sleep, 0, True),
    "think": (think, 1, True),
    "hide": (hide, 2, True),
}
# how much the tail wags with each motion (degrees per joint)
WAG = {"idle": 5, "bounce": 11, "jump": 10, "cheer": 12, "wave": 8, "dance": 12, "walk": 6, "nod": 6, "no": 4,
       "shiver": 2, "sway": 5, "sleep": 3, "think": 4, "hide": 3}
