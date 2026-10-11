"""Things a mascot wears.  Each returns spec(char, T, n) -> [(slot, Layer)] like mascot/props.py.

Head items hang from the 'neck' null and are drawn in the head drawing's own coordinates, placed from the
mascot's data (crown, eyes, ear pivots), so they sit right on every mascot and follow every head turn, squash
and stance.  The scarf rides on the body.
"""
from __future__ import annotations

import math

from mascot.geom import smooth
from mascot.lottie import Layer, Path, el, fl, gr, rc, sh, st
from mascot.props import C, star5


def _head(name, items, slot="front"):
    def spec(char, T, n):
        return [(slot, Layer(f"wear {name}", items(char), parent="neck"))]
    return spec


def party_hat(color="coral", stripe="yellow"):
    def items(ch):
        x, y = ch.crown
        y += 10
        cone = Path([(x - 34, y), (x, y - 92), (x + 34, y)], closed=True)
        stripes = [sh(Path([(x - 34 + 8 * k, y - 18 * k), (x + 34 - 8 * k, y - 18 * k - 14)], closed=False)) for k in (1, 2, 3)]
        return [gr("party hat", [
            gr("pompom", [el((x, y - 94), (24, 24)), fl(C["white"])]),
            gr("stripes", stripes + [st(C[stripe], 7)]),
            gr("cone", [sh(cone), fl(C[color])]),
            gr("brim", [rc((x, y), (76, 10), 5), fl(C[stripe])]),
        ], a=(x, y), p=(x, y), r=-12, s=(130, 130))]
    return _head("party hat", items)


def crown():
    def items(ch):
        x, y = ch.crown
        y += 8
        pts = [(x - 44, y), (x - 48, y - 46), (x - 24, y - 24), (x, y - 58), (x + 24, y - 24), (x + 48, y - 46), (x + 44, y)]
        return [gr("crown", [
            gr("gems", [el((x, y - 14), (12, 12)), el((x - 26, y - 12), (9, 9)), el((x + 26, y - 12), (9, 9)), fl(C["coral"])]),
            gr("tips", [el(p, (11, 11)) for p in ((x - 48, y - 48), (x, y - 60), (x + 48, y - 48))] + [fl(C["gold"])]),
            gr("band", [sh(Path(pts, closed=True)), fl(C["gold"])]),
            gr("band edge", [sh(Path(pts, closed=True)), st(C["darkgold"], 5)]),
        ], a=(x, y), p=(x, y), r=6, s=(115, 115))]
    return _head("crown", items)


def _eyes(ch):
    r = ch.eye["R"]
    l = (2 * ch.CX - r[0], r[1])
    w, h = getattr(ch, "eye_size", (54.0, 66.0))
    return l, r, w, h


def glasses(color="dark"):
    def items(ch):
        l, r, w, h = _eyes(ch)
        d = max(w, h) * 1.25
        bridge = sh(Path([(l[0] + d / 2, l[1] - 4), (r[0] - d / 2, r[1] - 4)], i=[(0, 0), (-8, -8)], o=[(8, -8), (0, 0)], closed=False))
        return [gr("glasses", [
            gr("frames", [el(l, (d, d)), el(r, (d, d)), bridge, st(C[color], 6)]),
            gr("lenses", [el(l, (d, d)), el(r, (d, d)), fl(C["lightblue"], 22)]),
        ])]
    return _head("glasses", items)


def sunglasses():
    def items(ch):
        l, r, w, h = _eyes(ch)
        gw, gh = w * 1.5, h * 1.0
        lens = lambda c: rc((c[0], c[1] + 2), (gw, gh), gh * 0.42)
        glint = lambda c: sh(Path([(c[0] - gw * 0.3, c[1] - gh * 0.1), (c[0] - gw * 0.05, c[1] - gh * 0.32)], closed=False))
        return [gr("sunglasses", [
            gr("glint", [glint(l), glint(r), st(C["white"], 5, 70)]),
            gr("lenses", [lens(l), lens(r), fl(C["dark"])]),
            gr("bridge", [rc(((l[0] + r[0]) / 2, l[1] - gh * 0.22), (r[0] - l[0] - gw + 12, 9), 4), fl(C["dark"])]),
        ])]
    return _head("sunglasses", items)


def bow(color="pink"):
    def items(ch):
        ex, ey = ch.ear_pivot["R"]
        x, y = (ex + ch.crown[0]) / 2 + 22, ch.crown[1] + 12
        wing = lambda k: smooth([(x, y), (x + k * 30, y - 20), (x + k * 36, y + 2), (x + k * 28, y + 20)], closed=True, tension=0.35,
                                sharp={0: 0.9})
        return [gr("bow", [
            gr("knot", [el((x, y), (16, 16)), fl(C["coral"])]),
            gr("wings", [sh(wing(1)), sh(wing(-1)), fl(C[color])]),
        ], a=(x, y), p=(x, y), r=14)]
    return _head("bow", items)


def flower():
    def items(ch):
        ex, ey = ch.ear_pivot["R"]
        x, y = 2 * ch.CX - ((ex + ch.crown[0]) / 2 + 28), ch.crown[1] + 16
        petals = [el((x + 15 * math.cos(a), y + 15 * math.sin(a)), (20, 20)) for a in (k * 2 * math.pi / 5 - math.pi / 2 for k in range(5))]
        return [gr("flower", [gr("centre", [el((x, y), (14, 14)), fl(C["yellow"])]), gr("petals", petals + [fl(C["white"])])])]
    return _head("flower", items)


def headphones(color="teal"):
    def items(ch):
        l, r, w, h = _eyes(ch)
        cy = l[1] + 6
        half = (r[0] - l[0]) / 2 + 96
        x = ch.CX
        top = ch.crown[1] - 12
        band = Path([(x - half + 10, cy - 20), (x, top), (x + half - 10, cy - 20)], i=[(0, 0), (-half * 0.6, 0), (0, -half * 0.5)],
                    o=[(0, -half * 0.5), (half * 0.6, 0), (0, 0)], closed=False)
        cup = lambda cx: rc((cx, cy), (30, 62), 14)
        return [gr("headphones", [
            gr("cups", [cup(x - half), cup(x + half), fl(C[color])]),
            gr("pads", [rc((x - half + 10, cy), (16, 52), 8), rc((x + half - 10, cy), (16, 52), 8), fl(C["dark"])]),
            gr("band", [sh(band), st(C["dark"], 9)]),
        ])]
    return _head("headphones", items)


def scarf(color="coral", stripe="cream"):
    def spec(char, T, n):
        x, y = char.neck_at or char.neck
        y += 12
        loop = rc((x, y), (150, 30), 15)
        tail = smooth([(x + 30, y + 4), (x + 52, y + 4), (x + 60, y + 62), (x + 36, y + 64)], closed=True, tension=0.3)
        lay = Layer("wear scarf", [gr("scarf", [
            gr("stripes", [rc((x + 47, y + 40), (24, 6), 2), rc((x - 40, y), (8, 28), 2), rc((x + 10, y), (8, 28), 2), fl(C[stripe])]),
            gr("tail", [sh(tail), fl(C[color])]),
            gr("loop", [loop, fl(C[color])]),
        ])], parent="body")
        return [("mid", lay)]
    return spec


def star_clip():
    def items(ch):
        ex, _ = ch.ear_pivot["R"]
        x, y = (ex + ch.crown[0]) / 2 + 24, ch.crown[1] + 16
        return [gr("star clip", [sh(star5((x, y), 17)), fl(C["yellow"])])]
    return _head("star clip", items)


ACCESSORIES = {
    "party_hat": party_hat, "crown": crown, "glasses": glasses, "sunglasses": sunglasses, "bow": bow, "flower": flower,
    "headphones": headphones, "scarf": scarf, "star_clip": star_clip,
}
# items that cannot be worn together (they sit in the same place)
EXCLUSIVE = [{"party_hat", "crown"}, {"glasses", "sunglasses"}, {"bow", "star_clip"}]
