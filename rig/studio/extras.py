"""Extra props and effects for stickers, written like mascot/props.py (each returns spec(char, T, n) -> [(slot, Layer)]).

Everything here loops: periodic motion uses periods that divide the clip length, so the last frame matches the first.
"""
from __future__ import annotations

import math

from mascot.geom import smooth
from mascot.lottie import Path, Layer, el, fl, gr, rc, sh, st
from mascot.props import C, F, held


def heart_path(R, cx=0.0, cy=0.0):
    """A heart about R wide on each side, tip at the bottom."""
    v = [(0, R), (-R, -0.25 * R), (0, -0.55 * R), (R, -0.25 * R)]
    i = [(0.5 * R, -0.5 * R), (0, 0.45 * R), (-0.3 * R, -0.5 * R), (0, -0.6 * R)]
    o = [(-0.5 * R, -0.5 * R), (0, -0.6 * R), (0.3 * R, -0.5 * R), (0, 0.45 * R)]
    return Path([(x + cx, y + cy) for x, y in v], i, o, closed=True)


def _cycle(f, L, phase=0.0):
    """0..1 progress through a loop of L frames."""
    return ((f / float(L)) + phase) % 1.0


# ------------------------------------------------------------------ held in a paw
def mug(side="R", pose="hold", tilt=0.0, color="teal"):
    """A mug of something hot, with two curls of steam that rise on a loop."""
    def spec(char, T, n):
        L = n - 1
        steam = []
        for q, dx in enumerate((-9, 9)):
            curl = Path([(dx, -66), (dx + 5, -82), (dx - 3, -98)], i=[(0, 0), (-6, 6), (5, 5)], o=[(6, -6), (-5, -5), (0, 0)], closed=False)
            u = lambda f, q=q: _cycle(f, L / 2.0, 0.5 * q)
            steam.append(gr(f"steam {q}", [sh(curl), st(C["white"], 5)], a=(dx, -66), p=F(n, lambda f, dx=dx, u=u: (dx, -66 - 14 * u(f)), tol=0.5),
                            o=F(n, lambda f, u=u: 85 * math.sin(math.pi * u(f)), tol=2.0)))
        items = steam + [
            gr("coffee", [el((0, -58), (40, 9)), fl(C["board"])]),
            gr("rim", [el((0, -58), (48, 13)), fl(C["cream"])]),
            gr("shine", [rc((-14, -34), (6, 30), 3), fl(C["white"], 45)]),
            gr("mug", [rc((0, -32), (48, 54), 10), fl(C[color])]),
            gr("handle", [el((27, -32), (24, 26)), st(C[color], 7)]),
        ]
        return [(f"hand.{side}", held(char, T, side, items, pose, tilt=tilt, nm="mug"))]
    return spec


def heart(side="R", pose="hold_up", color="coral", beat=60):
    """A big heart held up in the paw that beats."""
    def spec(char, T, n):
        L = n - 1
        per = L / max(1, round(L / beat))
        def s(f):
            u = (f % per) / per
            k = 100 + 12 * math.exp(-((u - 0.12) / 0.05) ** 2) + 7 * math.exp(-((u - 0.3) / 0.05) ** 2)
            return (k, k)
        items = [gr("heart", [gr("shine", [el((-17, -62), (14, 9)), fl(C["white"], 60)]), sh(heart_path(40, 0, -44)), fl(C[color])],
                    a=(0, -44), p=(0, -44), s=F(n, s, tol=1.5))]
        return [(f"hand.{side}", held(char, T, side, items, pose, nm="heart"))]
    return spec


# ------------------------------------------------------------------ floating effects (positions relative to the top of the head)
def _floaters(name, shapes_fn, offsets, rise=90.0, life=0.6, sway=8.0, size=1.0, slot="top"):
    """Shapes that float up from around the head and fade, each on its own phase of the loop."""
    def spec(char, T, n):
        L = n - 1
        cx, cy = char.crown_world(0)
        out = []
        for q, (dx, dy, ph, k) in enumerate(offsets):
            def u(f, ph=ph):
                x = _cycle(f, L, ph)
                return x / life if x < life else None
            def pos(f, dx=dx, dy=dy, q=q):
                x = u(f)
                x = 0.0 if x is None else x
                return (cx + dx + sway * math.sin(2 * math.pi * x + q), cy + dy - rise * x)
            def op(f):
                x = u(f)
                return 0.0 if x is None else 100 * min(1.0, x * 6) * min(1.0, (1 - x) * 3)
            def scl(f, k=k):
                x = u(f)
                x = 0.0 if x is None else x
                v = 100 * size * k * (0.5 + 0.5 * min(1.0, x * 4))
                return (v, v)
            out.append((slot, Layer(f"{name} {q}", shapes_fn(q), p=F(n, pos, tol=0.6), o=F(n, op, tol=2.5), s=F(n, scl, tol=1.5))))
        return out
    return spec


def hearts(color="coral"):
    cols = [color, color, color]
    return _floaters("heart", lambda q: [gr("heart", [sh(heart_path(22)), fl(C[cols[q % 3]])])],
                     [(-110, 90, 0.0, 1.0), (115, 70, 0.33, 0.85), (-70, 20, 0.66, 0.75)])


def notes():
    def note(q):
        col = C[("teal", "lilac", "coral")[q % 3]]
        return [gr("note", [el((-7, 10), (16, 12)), rc((0, -8), (4, 36), 1), sh(Path([(2, -26), (14, -18), (14, -10), (2, -18)], closed=True)), fl(col)])]
    return _floaters("note", note, [(-130, 80, 0.0, 1.0), (130, 50, 0.3, 0.9), (-90, 10, 0.55, 0.8), (110, -10, 0.8, 0.85)], rise=80, sway=12)


def rain(drops=6):
    """A little grey cloud over the head with falling drops (sad / gloomy)."""
    def spec(char, T, n):
        L = n - 1
        cx, cy = char.crown_world(0)
        cy -= 96
        cloud = Layer("rain cloud", [gr("cloud", [el((-34, 4), (60, 46)), el((4, -10), (70, 58)), el((40, 4), (58, 44)), rc((0, 16), (124, 32), 16),
                                                   fl(C["grey"])])],
                      p=F(n, lambda f: (cx, cy + 3 * math.sin(2 * math.pi * f / L)), tol=0.5))
        out = [("top", cloud)]
        for q in range(drops):
            x0 = cx - 45 + 18 * q
            ph = (q * 0.37) % 1.0
            def pos(f, x0=x0, ph=ph):
                u = _cycle(f, L / 3.0, ph)
                return (x0, cy + 30 + 110 * u)
            def op(f, ph=ph):
                u = _cycle(f, L / 3.0, ph)
                return 90 * min(1.0, u * 8) * min(1.0, (1 - u) * 4)
            drop = smooth([(0, -9), (5, 0), (0, 6), (-5, 0)], closed=True, tension=0.42, sharp={0: 0.35})
            out.append(("top", Layer(f"rain {q}", [gr("drop", [sh(drop), fl(C["sky"])])], p=F(n, pos, tol=0.5), o=F(n, op, tol=3.0))))
        return out
    return spec


def anger(color="coral"):
    """The cartoon 'vein' mark that throbs at the top corner of the head (head rest-pose coordinates)."""
    def spec(char, T, n):
        L = n - 1
        x, y = char.crown[0] + 92, char.crown[1] + 58
        arcs = []
        for a in (45, 135, 225, 315):
            r = math.radians(a)
            cx, cy = 11 * math.cos(r), 11 * math.sin(r)
            arcs.append(sh(Path([(cx - 9 * math.sin(r), cy + 9 * math.cos(r)), (cx + 9 * math.sin(r), cy - 9 * math.cos(r))],
                                i=[(0, 0), (-5 * math.cos(r), -5 * math.sin(r))], o=[(-5 * math.cos(r), -5 * math.sin(r)), (0, 0)], closed=False)))
        per = L / max(1, round(L / 30))
        s = F(n, lambda f: (100 + 18 * max(0.0, math.sin(2 * math.pi * f / per)),) * 2, tol=1.5)
        return [("front", Layer("anger", [gr("mark", arcs + [st(C[color], 7)], s=(150, 150))], parent="neck", p=(x, y), s=s))]
    return spec
