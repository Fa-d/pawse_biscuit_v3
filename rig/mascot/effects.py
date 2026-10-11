"""The small non-character animations (flame, check burst, sparkle, star burst).

Shapes, colours, canvas sizes and frame counts are the originals'; only the motion is reworked:
overshoot and settle, staggered timing, a little secondary action.  `pawse_logo` is a brand mark and
is passed through untouched.

    python3 -m mascot.effects --out dist/effects [--logo raw/pawse_logo.json]
"""
from __future__ import annotations

import argparse
import json
import math
import os

from .lottie import Layer, Path, document, el, fl, gr, rgb, sh, st, tm
from .props import F, K, star4, star5


def flame():
    n = 61                                                     # frames 0..60, loops
    w = lambda k, ph=0.0: (lambda f: math.sin(2 * math.pi * (k * f / 60.0 + ph)))
    a1, a2, a3 = w(1), w(2, 0.15), w(3, 0.4)

    def outer(f):
        sway = 5.0 * a1(f) + 2.5 * a2(f)                       # the tip licks sideways and stretches
        lift = 5.0 * a2(f) + 2.0 * a3(f)
        tip = (64 + sway, 10 - lift)
        return Path([tip, (104 + 2.0 * a2(f), 82 + 1.5 * a3(f)), (64, 122), (24 - 2.0 * a2(f + 9), 82 - 1.5 * a3(f))],
                    i=[(0, 0), (-6 + sway * 0.5, -30), (22, 0), (0, 22)],
                    o=[(6 + sway * 0.25, 30), (0, 22), (-22, 0), (-6 + sway * 0.5, -30)], closed=True)

    def inner(f):
        g = f - 5                                              # the core follows a moment later
        sway = 3.0 * a1(g) + 1.5 * a2(g)
        lift = 4.0 * a2(g)
        return Path([(64 + sway, 52 - lift), (84 + 1.2 * a3(g), 92), (64, 116), (44 - 1.2 * a3(g), 92)],
                    i=[(0, 0), (-4 + sway * 0.4, -16), (11, 0), (0, 12)],
                    o=[(4 + sway * 0.2, 16), (0, 12), (-11, 0), (-4 + sway * 0.4, -16)], closed=True)

    layers = []
    for q, (x, t0) in enumerate(((72, 6), (55, 34))):          # two sparks drifting up from the tip
        u = lambda f, t0=t0: ((f - t0) % 60) / 26.0
        layers.append(Layer(f"spark {q}", [gr("spark", [el((0, 0), (6, 6)), fl(rgb("#FFC93C"))])],
                            p=F(n, lambda f, x=x, u=u: (x + 5 * math.sin(u(f) * 5), 30 - 26 * min(u(f), 1.0)), tol=0.5),
                            s=F(n, lambda f, u=u: ((100 * max(0.0, 1 - u(f)) ** 0.6,) * 2), tol=3.0),
                            o=F(n, lambda f, u=u: 0.0 if u(f) >= 1 else 95 * min(1.0, u(f) * 6) * (1 - u(f)), tol=3.0)))
    layers.append(Layer("inner", [gr("inner", [sh(F(n, inner, tol=0.25)), fl(rgb("#FFC93C"))])], a=(64, 118), p=(64, 118),
                        s=K(n, (0, (100, 100)), (20, (93, 110), "io"), (40, (104, 95), "io"), (60, (100, 100), "io"))))
    layers.append(Layer("outer", [gr("outer", [sh(F(n, outer, tol=0.25)), fl(rgb("#FF6B35"))])], a=(64, 120), p=(64, 120),
                        s=K(n, (0, (100, 100)), (15, (96, 107), "io"), (30, (103, 96), "io"), (45, (98, 104), "io"), (60, (100, 100), "io")),
                        r=K(n, (0, -3.0), (15, 3.0, "io"), (30, -2.0, "io"), (45, 2.0, "io"), (60, -3.0, "io"))))
    return document("flame", layers, op=60, w=128, h=128)


def check_burst():
    n = 61
    layers = []
    layers.append(Layer("tick", [gr("tick", [sh(Path([(72, 102), (92, 122), (130, 82)], closed=False)), st([1, 1, 1], 13),
                                             tm(0, K(n, (0, 0.0), (12, 0.0, "hold"), (27, 100.0, "out")))])],
                        a=(100, 100), p=(100, 100),
                        s=K(n, (0, (100, 100)), (24, (100, 100), "hold"), (30, (113, 113), "out"), (40, (100, 100), "back"))))
    layers.append(Layer("circle", [gr("circle", [el((100, 100), (104, 104)), fl(rgb("#4CAF50"))])], a=(100, 100), p=(100, 100),
                        s=K(n, (0, (0, 0)), (12, (118, 118), "out"), (20, (94, 94), "io"), (28, (102, 102), "io"), (36, (100, 100), "io"))))
    layers.append(Layer("pulse", [gr("pulse", [el((100, 100), (104, 104)), st(rgb("#4CAF50"), 6)])], a=(100, 100), p=(100, 100),
                        s=K(n, (0, (60, 60)), (10, (60, 60), "hold"), (34, (170, 170), "out")),
                        o=K(n, (0, 0.0), (10, 55.0, "hold"), (34, 0.0, "io"))))
    for q in range(8):                                         # rays ripple round the circle instead of firing all at once
        a = -q * math.pi / 4
        p0 = (100 + 62 * math.cos(a), 100 + 62 * math.sin(a))
        p1 = (100 + 92 * math.cos(a), 100 + 92 * math.sin(a))
        d = q                                                   # one frame later per ray
        layers.append(Layer(f"ray {q}", [gr("ray", [sh(Path([p0, p1], closed=False)), st(rgb("#FFC93C"), 8),
                                                    tm(K(n, (0, 0.0), (16 + d, 0.0, "hold"), (32 + d, 100.0, "io")),
                                                       K(n, (0, 0.0), (9 + d, 0.0, "hold"), (21 + d, 100.0, "out")))])],
                            a=(100, 100), p=(100, 100)))
    return document("check_burst", layers, op=60, w=200, h=200)


def sparkle():
    n = 91
    twinkle = K(n, (0, (60, 60)), (38, (108, 108), "io"), (50, (98, 98), "io"), (90, (60, 60), "io"))
    layers = []
    for q, (x, y, r, t0) in enumerate(((52, 12, 5.0, 30), (11, 50, 4.0, 52))):   # two tiny companions wink in and out
        layers.append(Layer(f"glint {q}", [gr("glint", [sh(star4((0, 0), r)), fl(rgb("#FFD93D"))])], p=(x, y),
                            s=K(n, (0, (0, 0)), (t0, (0, 0), "hold"), (t0 + 10, (115, 115), "back"), (t0 + 26, (0, 0), "io"), tol=2.0)))
    layers.append(Layer("sparkle", [gr("sparkle", [sh(star4((32, 32), 26, 0.3192)), fl(rgb("#FFD93D"))])], a=(32, 32), p=(32, 32),
                        s=twinkle, r=F(n, lambda f: 90.0 * f / 90.0), o=K(n, (0, 70.0), (40, 100.0, "io"), (90, 70.0, "io"))))
    return document("sparkle", layers, op=90, w=64, h=64)


def star_burst():
    n = 76
    cols = ["#FFD93D", "#FF6B6B", "#4ECDC4", "#FFD93D", "#AA96DA", "#FF8A3D"]
    layers = []
    for q in range(6):
        a = math.radians(-90 + 60 * q)
        d = q % 3                                              # slight stagger
        far = (150 + 104 * math.cos(a), 150 + 104 * math.sin(a))
        end = (150 + 120 * math.cos(a), 150 + 120 * math.sin(a) + 9)     # eases outwards, sinking a touch
        spin = 200.0 if q % 2 == 0 else -200.0
        layers.append(Layer(f"star {5 - q}", [gr("star", [sh(star5((0, 0), 22, 0.455)), fl(rgb(cols[q]))])],
                            p=K(n, (0, (150, 150)), (d, (150, 150), "hold"), (26 + d, far, "out"), (75, end, "io")),
                            s=K(n, (0, (0, 0)), (d, (0, 0), "hold"), (12 + d, (126, 126), "back"), (46, (92, 92), "io"), (75, (0, 0), "in")),
                            r=K(n, (0, 0.0), (d, 0.0, "hold"), (75, spin, "out"))))
    layers.append(Layer("ring", [gr("ring", [el((150, 150), (70, 70)), st(rgb("#FFD93D"), 5)])], a=(150, 150), p=(150, 150),
                        s=K(n, (0, (40, 40)), (4, (40, 40), "hold"), (30, (250, 250), "out")), o=K(n, (0, 0.0), (4, 60.0, "hold"), (30, 0.0, "io"))))
    layers.append(Layer("glow", [gr("glow", [el((150, 150), (70, 70)), fl(rgb("#FFD93D"), 60)])], a=(150, 150), p=(150, 150),
                        s=K(n, (0, (0, 0)), (10, (150, 150), "out"), (28, (0, 0), "io"))))
    return document("star_burst", layers[:6][::-1] + layers[6:], op=75, w=300, h=300)


EFFECTS = {"flame": flame, "check_burst": check_burst, "sparkle": sparkle, "star_burst": star_burst}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="dist/effects")
    ap.add_argument("--logo", default="raw/pawse_logo.json", help="original logo file, copied through unchanged")
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    for name, fn in EFFECTS.items():
        doc = fn()
        path = os.path.join(a.out, f"{name}.json")
        with open(path, "w") as f:
            json.dump(doc, f, separators=(",", ":"))
        print(f"{name:<14}{doc['op']:>4}f {doc['w']}x{doc['h']} {os.path.getsize(path) / 1024:>6.1f} KB")
    if a.logo and os.path.exists(a.logo):
        with open(a.logo) as f:
            logo = json.load(f)
        with open(os.path.join(a.out, "pawse_logo.json"), "w") as f:
            json.dump(logo, f, separators=(",", ":"))
        print("pawse_logo     copied unchanged (minified)")


if __name__ == "__main__":
    main()
