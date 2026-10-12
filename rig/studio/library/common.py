"""Small helpers shared by the library's drawings.

Conventions (the same as mascot/props.py):
  * a factory gets a Make (frames, paw, colour, ...) and returns spec(char, T, n) -> [(slot, Layer or group)]
  * slots: 'top' over everything, 'front' in front of the head, 'mid' between arms and feet, 'back' behind the
    mascot, 'hand.R' / 'hand.L' inside a paw (drawn under the paw), 'hand.R.over' / 'hand.L.over' over it
  * held things are drawn upright around (0, 0) = the point that rests in the paw, negative y is up
  * everything must loop: every periodic movement uses a period that divides the loop (Make.per)
"""
from __future__ import annotations

import math

import numpy as np

from mascot.geom import heart_path, smooth, spiral_points, star_path
from mascot.lottie import Anim, Layer, Path, el, fl, gr, rc, rgb, sh, st, tm
from mascot.props import C, F, K, KH, star4, star5

__all__ = ["C", "F", "K", "KH", "Anim", "Layer", "Path", "el", "fl", "gr", "rc", "rgb", "sh", "st", "tm", "smooth", "star4",
           "star5", "heart_path", "star_path", "spiral_points", "col", "shade", "cycle", "env", "grip", "math", "np", "loop_pop", "acted"]

# extra named colours for the library (mascot.props.C keeps its own and is never changed)
C.update({k: rgb(v) for k, v in dict(
    red="#E84A5F", darkred="#B8283D", rose="#FF8FAB", peach="#FFC4A3", tan="#E3B583", brown="#9C6B43", darkbrown="#6B4428",
    choco="#5B3A29", cheese="#FFD25A", crust="#E9A64B", tomato="#E8503A", lettuce="#7BC86C", leaf="#5DAE5B", darkgreen="#2E7D4F",
    navy="#2F4A7A", purple="#8A6FDF", violet="#6C4FC4", silver="#C9D1DB", steel="#8C97A6", black="#2B2730", ink="#1F2A2E",
    paper="#FFFDF7", ice="#DDF3FF", sand="#F3D9A4", fire="#FF7A2F", flame="#FFB02E", snow="#F4F8FF", night="#3A3F6B",
    bubble="#BDE7FF", water="#56B4F0", gum="#FF7EB6", lime="#B6E35A", sky2="#A8DBFF", gold2="#F6B93B", wood="#B9824F",
).items()})


def col(x):
    """A colour given as a name of C or an [r, g, b] list -> [r, g, b]."""
    if isinstance(x, str):
        return C[x] if x in C else rgb(x)
    return list(x)


def shade(x, k):
    """Darker (k < 1) or lighter (k > 1) version of a colour."""
    r, g, b = col(x)
    if k <= 1:
        return [r * k, g * k, b * k]
    t = min(1.0, k - 1.0)
    return [r + (1 - r) * t, g + (1 - g) * t, b + (1 - b) * t]


def cycle(f, period, phase=0.0):
    """0..1 progress through a cycle of `period` frames."""
    return ((f / float(period)) + phase) % 1.0


def env(u, rise=0.15, fall=0.35):
    """0 -> 1 -> 0 over u in [0, 1]: quick rise, hold, soft fall (for things that appear and fade on a loop)."""
    if u <= 0 or u >= 1:
        return 0.0
    a = min(1.0, u / rise) if rise else 1.0
    b = min(1.0, (1 - u) / fall) if fall else 1.0
    return 0.5 - 0.5 * math.cos(math.pi * min(a, b))


def loop_pop(f, L, t0, life, peak=1.15):
    """Scale (0..peak..1..0) of something that pops in at t0, lives `life` frames and shrinks away, wrapping
    round the loop so the first and last frames always agree."""
    u = ((f - t0) % L) / float(life)
    if u >= 1.0:
        return 0.0
    if u < 0.25:
        x = u / 0.25
        return peak * (1 - (1 - x) ** 3)                       # out-ease up to the overshoot
    if u < 0.4:
        return peak + (1.0 - peak) * (u - 0.25) / 0.15
    if u < 0.75:
        return 1.0
    return max(0.0, 1.0 - ((u - 0.75) / 0.25) ** 2)


def acted(x):
    """Is the paw holding this prop moved by the motion (a snack taken to the mouth, a glass raised for a toast)?
    Then the prop is kept upright whatever the arm does on the way, so nothing is spilled or spun round."""
    plan = x.plan
    return plan is not None and any(s == x.side or s == "LR" for _, s in getattr(plan, "acts", ()))


def grip(char, T, side, items, pose="hold", upright=True, grip_at=(0.0, 17.0), tilt=0.0, scale=1.0, nm="prop", swing=None):
    """Put upright-drawn items into a paw.

    upright=True turns them against the arm every frame, so they stay upright whatever the arm does (waves,
    cheers).  upright=False keeps the classic behaviour of mascot.props.held: upright in `pose`, tilting with the
    paw when the arm moves (a mug that tips towards the mouth)."""
    sgn = 1.0 if side == "R" else -1.0
    n = char.n
    if upright:
        base = [sgn * float(T[f"arm.{side}.sh"][f] + T[f"arm.{side}.el"][f] + T[f"arm.{side}.wr"][f]) + tilt for f in range(n)]
    else:
        v = char.pose(pose)["v"]
        base = [sgn * (v[0] + v[1] + v[2]) + tilt] * n
    if swing is not None:
        base = [b + float(s) for b, s in zip(base, swing)]
    hs = [float(T[f"hand.{side}.s"][f]) for f in range(n)]
    # the paw's own scale is undone so a held thing keeps its size when the paw grows (pointing at the viewer)
    s = Anim([(scale * 100 / h, scale * 100 / h) for h in hs], tol=0.6) if max(hs) - min(hs) > 1e-6 or abs(hs[0] - 1) > 1e-6 \
        else (scale * 100, scale * 100)
    rot = Anim(base, tol=0.5) if max(base) - min(base) > 1e-6 else base[0]
    return gr(nm, items, p=grip_at, r=rot, s=s)
