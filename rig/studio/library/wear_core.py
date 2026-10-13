"""The first nine things to wear (from v3).

Head items hang from the 'neck' null and are drawn in the head drawing's own coordinates, placed from the
mascot's data (crown, eyes, ear pivots), so they sit right on every mascot and follow every head turn, squash and
stance.  Neck items ride on the body.  Seen from the side or from behind (v5), an item with `views` is drawn by
wear_views.py instead (the drawing function is handed the view's copy of the mascot: V.view_of(char) says which).
"""
from __future__ import annotations

from ..registry import wear
from . import wear_views as V
from .common import C, Layer, Path, col, el, fl, gr, math, rc, sh, smooth, st, star5


def on_head(name, items, slot="front"):
    """spec for shapes drawn in the head drawing's coordinates (they follow every head movement)."""
    def spec(char, T, n):
        return [(slot, Layer(f"wear {name}", items(char), parent="neck"))]
    return spec


def on_body(name, items, slot="mid"):
    def spec(char, T, n):
        return [(slot, Layer(f"wear {name}", items(char), parent="body"))]
    return spec


def eyes_of(ch):
    """(left eye, right eye, eye width, eye height) in the head drawing."""
    r = ch.eye["R"]
    l = (2 * ch.CX - r[0], r[1])
    w, h = getattr(ch, "eye_size", (54.0, 66.0))
    return l, r, w, h


@wear("party_hat", "Party hat", "🥳", zone="hat", noun="a party hat", tint=("coral", "teal", "lilac", "blue"))
def party_hat(x):
    color, stripe = col(x.color or "coral"), C["yellow"]

    def items(ch):
        cx, y = ch.crown
        y += 10
        cone = Path([(cx - 34, y), (cx, y - 92), (cx + 34, y)], closed=True)
        stripes = [sh(Path([(cx - 34 + 8 * k, y - 18 * k), (cx + 34 - 8 * k, y - 18 * k - 14)], closed=False)) for k in (1, 2, 3)]
        return [gr("party hat", [
            gr("pompom", [el((cx, y - 94), (24, 24)), fl(C["white"])]),
            gr("stripes", stripes + [st(stripe, 7)]),
            gr("cone", [sh(cone), fl(color)]),
            gr("brim", [rc((cx, y), (76, 10), 5), fl(stripe)]),
        ], a=(cx, y), p=(cx, y), r=-12, s=(130, 130))]
    return on_head("party hat", items)


@wear("crown", "Crown", "👑", zone="hat", noun="a crown")
def crown(x):
    def items(ch):
        cx, y = ch.crown
        y += 8
        pts = [(cx - 44, y), (cx - 48, y - 46), (cx - 24, y - 24), (cx, y - 58), (cx + 24, y - 24), (cx + 48, y - 46), (cx + 44, y)]
        return [gr("crown", [
            gr("gems", [el((cx, y - 14), (12, 12)), el((cx - 26, y - 12), (9, 9)), el((cx + 26, y - 12), (9, 9)), fl(C["coral"])]),
            gr("tips", [el(p, (11, 11)) for p in ((cx - 48, y - 48), (cx, y - 60), (cx + 48, y - 48))] + [fl(C["gold"])]),
            gr("band", [sh(Path(pts, closed=True)), fl(C["gold"])]),
            gr("band edge", [sh(Path(pts, closed=True)), st(C["darkgold"], 5)]),
        ], a=(cx, y), p=(cx, y), r=6, s=(115, 115))]
    return on_head("crown", items)


@wear("glasses", "Glasses", "👓", zone="eyes", noun="glasses", views=("side", "back"))
def glasses(x):
    frame = col(x.color or "dark")

    def items(ch):
        if V.view_of(ch):
            return V.glasses(ch, frame)
        l, r, w, h = eyes_of(ch)
        d = max(w, h) * 1.25
        bridge = sh(Path([(l[0] + d / 2, l[1] - 4), (r[0] - d / 2, r[1] - 4)], i=[(0, 0), (-8, -8)], o=[(8, -8), (0, 0)], closed=False))
        return [gr("glasses", [
            gr("frames", [el(l, (d, d)), el(r, (d, d)), bridge, st(frame, 6)]),
            gr("lenses", [el(l, (d, d)), el(r, (d, d)), fl(C["lightblue"], 22)]),
        ])]
    return on_head("glasses", items)


@wear("sunglasses", "Sunglasses", "😎", zone="eyes", noun="sunglasses", covers=("eyes",), views=("side", "back"))
def sunglasses(x):
    def items(ch):
        if V.view_of(ch):
            return V.sunglasses(ch)
        l, r, w, h = eyes_of(ch)
        gw, gh = w * 1.5, h * 1.0
        lens = lambda c: rc((c[0], c[1] + 2), (gw, gh), gh * 0.42)
        glint = lambda c: sh(Path([(c[0] - gw * 0.3, c[1] - gh * 0.1), (c[0] - gw * 0.05, c[1] - gh * 0.32)], closed=False))
        return [gr("sunglasses", [
            gr("glint", [glint(l), glint(r), st(C["white"], 5, 70)]),
            gr("lenses", [lens(l), lens(r), fl(C["dark"])]),
            gr("bridge", [rc(((l[0] + r[0]) / 2, l[1] - gh * 0.22), (r[0] - l[0] - gw + 12, 9), 4), fl(C["dark"])]),
        ])]
    return on_head("sunglasses", items)


@wear("bow", "Bow", "🎀", zone="ear", noun="a bow", tint=("pink", "coral", "lilac", "teal", "yellow"), views=("side", "back"))
def bow(x):
    color = col(x.color or "pink")

    def items(ch):
        if V.view_of(ch):
            return V.bow(ch, color)
        ex, ey = ch.ear_pivot["R"]
        bx, by = (ex + ch.crown[0]) / 2 + 22, ch.crown[1] + 12
        wing = lambda k: smooth([(bx, by), (bx + k * 30, by - 20), (bx + k * 36, by + 2), (bx + k * 28, by + 20)], closed=True, tension=0.35,
                                sharp={0: 0.9})
        return [gr("bow", [
            gr("knot", [el((bx, by), (16, 16)), fl(C["coral"])]),
            gr("wings", [sh(wing(1)), sh(wing(-1)), fl(color)]),
        ], a=(bx, by), p=(bx, by), r=14)]
    return on_head("bow", items)


@wear("flower", "Flower", "🌼", zone="head_side", noun="a flower", views=("side", "back"))
def flower(x):
    petal_c = col(x.color or "white")

    def items(ch):
        if V.view_of(ch):
            return V.flower(ch, petal_c)
        ex, ey = ch.ear_pivot["R"]
        fx, fy = 2 * ch.CX - ((ex + ch.crown[0]) / 2 + 28), ch.crown[1] + 16
        petals = [el((fx + 15 * math.cos(a), fy + 15 * math.sin(a)), (20, 20)) for a in (k * 2 * math.pi / 5 - math.pi / 2 for k in range(5))]
        return [gr("flower", [gr("centre", [el((fx, fy), (14, 14)), fl(C["yellow"])]), gr("petals", petals + [fl(petal_c)])])]
    return on_head("flower", items)


@wear("headphones", "Headphones", "🎧", zone="ears", noun="headphones", tint=("teal", "coral", "lilac", "yellow"), views=("side", "back"))
def headphones(x):
    color = col(x.color or "teal")

    def items(ch):
        if V.view_of(ch) == "side":                 # (from behind the front drawing serves: cups both sides, the band over)
            return V.headphones(ch, color)
        l, r, w, h = eyes_of(ch)
        cy = l[1] + 6
        half = (r[0] - l[0]) / 2 + 96
        cx = ch.CX
        top = ch.crown[1] - 12
        band = Path([(cx - half + 10, cy - 20), (cx, top), (cx + half - 10, cy - 20)], i=[(0, 0), (-half * 0.6, 0), (0, -half * 0.5)],
                    o=[(0, -half * 0.5), (half * 0.6, 0), (0, 0)], closed=False)
        cup = lambda px: rc((px, cy), (30, 62), 14)
        return [gr("headphones", [
            gr("cups", [cup(cx - half), cup(cx + half), fl(color)]),
            gr("pads", [rc((cx - half + 10, cy), (16, 52), 8), rc((cx + half - 10, cy), (16, 52), 8), fl(C["dark"])]),
            gr("band", [sh(band), st(C["dark"], 9)]),
        ])]
    return on_head("headphones", items)


@wear("scarf", "Scarf", "🧣", zone="neck", noun="a scarf", tint=("coral", "teal", "lilac", "blue"), views=("side", "back"))
def scarf(x):
    color, stripe = col(x.color or "coral"), C["cream"]

    def items(ch):
        if V.view_of(ch):
            return V.scarf(ch, color, stripe)
        if ch.collar:                      # a mane hides the neck: wrap it lower
            sx, sy = ch.collar[0], ch.collar[1] - 2
        else:
            sx, sy = ch.neck_at or ch.neck
            sy += 12
        loop = rc((sx, sy), (150, 30), 15)
        tail = smooth([(sx + 30, sy + 4), (sx + 52, sy + 4), (sx + 60, sy + 62), (sx + 36, sy + 64)], closed=True, tension=0.3)
        return [gr("scarf", [
            gr("stripes", [rc((sx + 47, sy + 40), (24, 6), 2), rc((sx - 40, sy), (8, 28), 2), rc((sx + 10, sy), (8, 28), 2), fl(stripe)]),
            gr("tail", [sh(tail), fl(color)]),
            gr("loop", [loop, fl(color)]),
        ])]
    return on_body("scarf", items)


@wear("star_clip", "Star clip", "⭐", zone="ear", noun="a star clip", views=("side", "back"))
def star_clip(x):
    color = col(x.color or "yellow")

    def items(ch):
        if V.view_of(ch):
            return V.star_clip(ch, color)
        ex, _ = ch.ear_pivot["R"]
        sx, sy = (ex + ch.crown[0]) / 2 + 24, ch.crown[1] + 16
        return [gr("star clip", [sh(star5((sx, sy), 17)), fl(color)])]
    return on_head("star clip", items)
