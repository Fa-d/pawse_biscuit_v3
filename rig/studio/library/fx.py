"""Effect builders shared by motions and effects: bursts, streams, speed lines, dust.

Each returns a spec(char, T, n) -> [(slot, Layer)].  One-shot things (a burst at frame t0) are invisible before t0
and after their life, so they never show at the loop point unless they are meant to; looping things use periods that
divide the loop.
"""
from __future__ import annotations

import math

import numpy as np

from mascot import props as P
from mascot.clip import ease

from .common import F, Layer, Path, col, el, fl, gr, sh, smooth, st, star4

DROP = smooth([(0, -9), (5, 0), (0, 6), (-5, 0)], closed=True, tension=0.42, sharp={0: 0.35})


def _drop(color, scale=1.0):
    return [gr("drop", [sh(DROP), fl(col(color))], s=(scale * 100, scale * 100))]


def burst(t0, at, count=6, colours=("yellow",), reach=70.0, life=18, kind="star", size=14.0, slot="top", spread=(0.0, 360.0),
          gravity=0.0, seed=5, nm="burst"):
    """A one-shot burst at frame t0 from `at` (canvas point, or fn(char, T) -> point): stars, drops or dots fly out
    and fade.  spread: the arc of directions in degrees (0 = right, 90 = up)."""
    def spec(char, T, n):
        o = at(char, T) if callable(at) else at
        rng = np.random.RandomState(seed)
        out = []
        for q in range(count):
            a = math.radians(spread[0] + (spread[1] - spread[0]) * (q + 0.5) / count + rng.uniform(-8, 8))
            d = reach * (0.75 + 0.4 * rng.rand())
            tx, ty = o[0] + d * math.cos(a), o[1] - d * math.sin(a)
            u = lambda f: min(max((f - t0) / float(life), 0.0), 1.0)
            pos = F(n, lambda f, tx=tx, ty=ty: (o[0] + (tx - o[0]) * ease("out", u(f)), o[1] + (ty - o[1]) * ease("out", u(f)) + gravity * u(f) ** 2),
                    tol=0.8)
            sc = F(n, lambda f: (0.0, 0.0) if (f < t0 or f > t0 + life) else (100 * math.sin(math.pi * min(1.0, u(f) * 1.3 + 0.1)),) * 2, tol=2.0)
            colour = col(colours[q % len(colours)])
            if kind == "star":
                shapes = [gr("star", [sh(star4((0, 0), size)), fl(colour)])]
            elif kind == "drop":
                shapes = [gr("drop", [sh(DROP), fl(colour)], r=-math.degrees(a) + 90)]
            else:
                shapes = [gr("dot", [el((0, 0), (size, size)), fl(colour)])]
            out.append((slot, Layer(f"{nm} {t0} {q}", shapes, p=pos, s=sc)))
        return out
    return spec


def streams(L, count=4, color="sky", reach=70.0, drop=110.0, nm="tear stream"):
    """Cartoon crying: drops arc out of the corner of each eye and fall, all through the loop (head coordinates)."""
    def spec(char, T, n):
        out = []
        er = char.eye["R"]
        w, h = getattr(char, "eye_size", (54.0, 66.0))
        period = L / max(1, round(L / 36.0))
        for s, sgn in (("R", 1.0), ("L", -1.0)):
            ex = er[0] if s == "R" else 2 * char.CX - er[0]
            x0, y0 = ex + sgn * w * 0.36, er[1] + h * 0.3
            for q in range(count):
                ph = q / float(count)

                def u(f, ph=ph):
                    return ((f / period) + ph) % 1.0

                pos = F(n, lambda f, u=u, sgn=sgn: (x0 + sgn * reach * u(f), y0 - 26 * math.sin(math.pi * min(1.0, u(f) * 1.6)) + drop * u(f) ** 2),
                        tol=0.6)
                op = F(n, lambda f, u=u: 100 * min(1.0, u(f) * 8) * min(1.0, (1 - u(f)) * 3), tol=3.0)
                out.append(("front", Layer(f"{nm} {s} {q}", _drop(color, 1.1), parent="neck", p=pos, o=op)))
        return out
    return spec


def speed_lines(L, count=5, direction=-1, slot="back", color="grey", length=70.0, nm="speed line"):
    """Streaks rushing past the mascot on a loop (direction -1: towards the left, the mascot going right)."""
    def spec(char, T, n):
        cx, cy = char.middle_root(0)
        out = []
        period = L / max(1, round(L / 24.0))
        for q in range(count):
            y = cy - 150 + q * 300.0 / max(1, count - 1)
            ph = (q * 0.37) % 1.0
            x_from = cx - direction * 170.0
            u = lambda f, ph=ph: ((f / period) + ph) % 1.0
            pos = F(n, lambda f, u=u, y=y: (x_from + direction * 260.0 * u(f), y), tol=0.8)
            op = F(n, lambda f, u=u: 70 * math.sin(math.pi * u(f)), tol=3.0)
            line = sh(Path([(0, 0), (-direction * length, 0)], closed=False))
            out.append((slot, Layer(f"{nm} {q}", [gr("line", [line, st(col(color), 6, 80)])], p=pos, o=op)))
        return out
    return spec


def dust_at(times, L=None, side=0, n_puffs=3, size=18.0):
    """Dust puffs at the feet at each frame in `times` (one-shot each).  With L, puffs that would still be in the
    air at the end of the loop are left out (they would not be there at its start)."""
    specs = [P.dust(int(t), 256.0, side=side, n_puffs=n_puffs, size=size) for t in times if L is None or int(t) + 23 <= L]

    def spec(char, T, n):
        out = []
        for s in specs:
            out += s(char, T, n)
        return out
    return spec


def flung_drops(t0, t1, every, L, color="sky", count=6, reach=110.0, nm="flung drop"):
    """Drops thrown off the body (a wet dog shake) every `every` frames between t0 and t1."""
    bursts = []
    for q, t in enumerate(range(int(t0), int(t1), max(1, int(every)))):
        side = 1 if q % 2 == 0 else -1
        bursts.append(burst(t, lambda char, T, side=side: (char.CX + side * 70.0, char.GROUND - 220.0), count=count, colours=(color, "white"),
                            reach=reach, life=20, kind="drop", spread=((-30, 60) if side > 0 else (120, 210)), gravity=40.0, seed=11 + q,
                            nm=f"{nm} {q}"))

    def spec(char, T, n):
        out = []
        for b in bursts:
            out += b(char, T, n)
        return out
    return spec
