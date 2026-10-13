"""Things worn, seen from the side and from behind (v5).

A mascot turned to a drawn view (mascot/views.py) draws a worn item again with the view's copy of itself: the item's
own drawing function gets a mascot whose anchors are the view's (its near eye, the tip of its muzzle, its crown, its
outlines) and whose `view_name` says which view it is:

    'side'   facing screen-right, seen from its left: +x is forward, the near eye is ch.view_sides[0]
             (the mirrored side view, facing left, is this drawing mirrored by the rig)
    'back'   seen from behind: the mascot's right side is on screen-left

The functions here are those drawings; a factory in wear_core.py / wear_more.py calls them when view_of(char) is set
and registers the views it draws (@wear(..., views=("side", "back"))).  A view an item has no drawing for: a hat is
worn as drawn for the front, anything else is left out.  The front drawings are not touched, so a sticker that faces
the viewer is byte-identical to v4.

Everything is placed from the mascot's own data, as the front drawings are: eyes, nose, mouth, crown, ear pivots, the
neck, and the outlines of the head and the body (head_span, body_span), so a mascot that gets its own drawn views
wears the same things without new drawings.
"""
from __future__ import annotations

import numpy as np

from mascot.views import sample_path

from .common import C, F, Layer, Path, el, fl, gr, math, rc, sh, smooth, st, star5

SQUASH = 0.45            # a lens, a bow, a bow tie seen from the side: this much of its width shows
FRONT, BACK = "side", "back"


# ------------------------------------------------------------------ where things are in a drawn view
def view_of(ch):
    """'side', 'back', or None for the front."""
    return getattr(ch, "view_name", None)


def near_side(ch):
    sides = getattr(ch, "view_sides", ("R", "L"))
    return sides[0] if sides else "R"


def near_eye(ch):
    """The eye nearer the viewer, in the head drawing ((x, y), eye width, eye height)."""
    e = ch.side(ch.eye, near_side(ch))
    w, h = getattr(ch, "eye_size", (54.0, 66.0))
    return (float(e[0]), float(e[1])), float(w), float(h)


def _span(path, y):
    P = sample_path(path, 24)
    a, b = P, np.roll(P, -1, axis=0)
    lo, hi = np.minimum(a[:, 1], b[:, 1]), np.maximum(a[:, 1], b[:, 1])
    m = (lo <= y) & (y <= hi) & (hi - lo > 1e-9)
    if not m.any():
        c = P[np.argmin(np.abs(P[:, 1] - y))]
        return float(c[0]), float(c[0])
    xs = a[m, 0] + (y - a[m, 1]) / (b[m, 1] - a[m, 1]) * (b[m, 0] - a[m, 0])
    return float(xs.min()), float(xs.max())


def head_span(ch, y):
    """(back, front) of the head outline at height y (head drawing): from the side the face is at the front (+x)."""
    return _span(ch.head_outline(), y)


def body_span(ch, y):
    """(back, front) of the body outline at height y (body space)."""
    return _span(ch.body_outline(), y)


def squash(items, about, k, nm="seen from the side"):
    """Items narrowed to k of their width about a point (a flat thing seen nearly edge on)."""
    return gr(nm, items, a=about, p=about, s=(100.0 * k, 100.0))


def neck_point(ch):
    """Where things worn at the neck hang (body space): the collar, or just under the neck pivot."""
    if ch.collar:
        return tuple(map(float, ch.collar))
    sx, sy = ch.neck_at or ch.neck
    return float(sx), float(sy) + 14.0


def torso(ch, y0, y1, out=3.0, steps=9):
    """The body's outline between heights y0 and y1 seen from the side, as a closed path pushed out by `out` px:
    what a sweater or a T-shirt covers."""
    ys = np.linspace(y0, y1, steps)
    front, back = [], []
    for y in ys:
        b, f = body_span(ch, float(y))
        front.append((f + out, float(y)))
        back.append((b - out, float(y)))
    pts = front + back[::-1]
    return smooth(pts, closed=True, tension=0.3, sharp={0: 0.5, steps - 1: 0.4, steps: 0.4, 2 * steps - 1: 0.5})


def temple(ch, x0, y0, reach=0.5, rise=6.0, hook=8.0):
    """The arm of a pair of glasses seen from the side: from a lens's back edge along the side of the head, `reach`
    of the way to the back of it, hooking down at the end."""
    back, _ = head_span(ch, y0)
    x1 = x0 - reach * (x0 - back)
    return Path([(x0, y0), (x1, y0 - rise), (x1 - 6.0, y0 - rise + hook)], i=[(0, 0), (12, 0), (2, -4)],
                o=[(-12, 0), (-4, 0), (0, 0)], closed=False)


def on_top(ch, dx, dy, side="R"):
    """A place on top of the head as the front drawings find it: halfway between the crown and the ear of `side`, then
    dx further out (away from the crown), dy below the crown.  The same sum puts it where each drawn view has that
    ear: beside the far ear from the side, on the other side from behind."""
    ex = float(ch.side(ch.ear_pivot, side)[0])
    cx = float(ch.crown[0])
    k = 1.0 if ex >= cx else -1.0
    return (ex + cx) / 2.0 + k * dx, float(ch.crown[1]) + dy, k


# ------------------------------------------------------------------ glasses and masks
def glasses(ch, frame):
    if view_of(ch) == BACK:
        return []
    (ex, ey), w, h = near_eye(ch)
    d = max(w, h) * 1.25
    lw, lx = d * 0.5, ex + 6.0
    arm = temple(ch, lx - lw / 2.0 + 2.0, ey - d * 0.2)
    return [gr("glasses", [
        gr("frames", [el((lx, ey), (lw, d)), sh(arm), st(frame, 6)]),
        gr("lenses", [el((lx, ey), (lw, d)), fl(C["lightblue"], 22)]),
    ])]


def sunglasses(ch):
    if view_of(ch) == BACK:
        return []
    (ex, ey), w, h = near_eye(ch)
    gw, gh = w * 1.5 * SQUASH, h * 1.0
    lx = ex + 6.0
    glint = sh(Path([(lx - gw * 0.15, ey - gh * 0.1), (lx + gw * 0.1, ey - gh * 0.32)], closed=False))
    return [gr("sunglasses", [
        gr("glint", [glint, st(C["white"], 5, 70)]),
        gr("lenses", [rc((lx, ey + 2), (gw, gh), min(gw, gh) * 0.42), fl(C["dark"])]),
        gr("arm", [sh(temple(ch, lx - gw / 2.0 + 2.0, ey - gh * 0.22)), st(C["dark"], 7)]),
    ])]


def lenses(ch, shape_fn, fill, edge, glare=True):
    """Shaped glasses (hearts, stars) from the side: the near lens, narrowed, and its arm."""
    if view_of(ch) == BACK:
        return []
    (ex, ey), w, h = near_eye(ch)
    lens = shape_fn((ex, ey), w)
    out = []
    if glare:
        out.append(gr("glare", [sh(Path([(ex - w * 0.3, ey - h * 0.1), (ex - w * 0.05, ey - h * 0.32)], closed=False)), st(C["white"], 5, 70)]))
    out += [gr("lenses", [sh(lens), fl(fill)]), gr("frames", [sh(lens), st(edge, 6)])]
    half = w * 0.8 * SQUASH
    return [squash(out, (ex, ey), SQUASH, nm="lens"),
            gr("arm", [sh(temple(ch, ex + 4.0 - half, ey - h * 0.2)), st(edge, 6)])]


def goggles(ch, c):
    (ex, ey), w, h = near_eye(ch)
    if view_of(ch) == BACK:
        cx = float(ch.CX)
        back_l, back_r = head_span(ch, ey)
        strap = smooth([(back_l - 6, ey - 2), (cx, ey - 10), (back_r + 6, ey - 2)], closed=False, tension=0.4)
        return [gr("strap", [sh(strap), st(c, 12)])]
    lw, lh = w * 1.5 * SQUASH, h * 1.05
    lx = ex + 6.0
    back, _ = head_span(ch, ey)
    lens = rc((lx, ey), (lw, lh), lw * 0.45)
    strap = smooth([(lx - lw / 2.0, ey - 4), ((lx + back) / 2.0, ey - 12), (back - 4, ey - 8)], closed=False, tension=0.4)
    return [
        gr("glare", [sh(Path([(lx - lw * 0.2, ey - lh * 0.15), (lx + lw * 0.1, ey - lh * 0.35)], closed=False)), st(C["white"], 5, 80)]),
        gr("lenses", [lens, fl(C["sky2"], 70)]),
        gr("frames", [rc((lx, ey), (lw, lh), lw * 0.45), st(c, 9)]),
        gr("strap", [sh(strap), st(c, 12)]),
    ]


def glasses_3d(ch):
    if view_of(ch) == BACK:
        return []
    (ex, ey), w, h = near_eye(ch)
    lw, lh = w * 1.4 * SQUASH, h * 0.9
    lx = ex + 6.0
    red = near_side(ch) == "L"                      # the left lens is the red one
    return [
        gr("near lens", [rc((lx, ey + 2), (lw, lh), 6), fl(C["red"] if red else C["sky2"], 80 if red else 85)]),
        gr("frame", [rc((lx, ey + 2), (lw + 10, lh + 12), 8), fl(C["white"])]),
        gr("arm", [sh(temple(ch, lx - lw / 2.0, ey - lh * 0.3)), st(C["white"], 7)]),
    ]


def monocle(ch):
    if view_of(ch) == BACK:
        return []
    (ex, ey), w, h = near_eye(ch)
    d = max(w, h) * 1.25
    lw, lx = d * 0.5, ex + 6.0
    chain = smooth([(lx - lw * 0.35, ey + d * 0.42), (lx - lw * 0.6, ey + d * 0.85), (lx - 26, ey + 120)], closed=False, tension=0.4)
    return [gr("chain", [sh(chain), st(C["gold"], 3)]), gr("rim", [el((lx, ey), (lw, d)), st(C["gold"], 6)]),
            gr("lens", [el((lx, ey), (lw, d)), fl(C["lightblue"], 25)])]


def eye_patch(ch):
    (ex, ey), w, h = near_eye(ch)
    cx = float(ch.CX)
    if view_of(ch) == BACK:                         # the strap goes round the back of the head, high on the patch's side
        hi, lo = head_span(ch, ey - 66)[1], head_span(ch, ey + 56)[0]
        strap = smooth([(hi - 2, ey - 66), (cx, ey - 8), (lo + 2, ey + 56)], closed=False, tension=0.4)
        return [gr("strap", [sh(strap), st(C["black"], 5)])]
    back, front = head_span(ch, ey)
    mid = (back + front) / 2.0
    strap = smooth([(ex - w * 0.3, ey - h * 0.4), (mid - 20, ey - 70), (back + 2, ey - 8)], closed=False, tension=0.4)
    return [gr("patch", [el((ex + 2, ey), (w * 1.3 * 0.62, h * 1.15)), fl(C["black"])]), gr("strap", [sh(strap), st(C["black"], 5)])]


def sleep_mask(ch, c):
    (ex, ey), w, h = near_eye(ch)
    cx = float(ch.CX)
    if view_of(ch) == BACK:
        return [gr("strap", [sh(Path([(cx - 150, ey - 10), (cx + 150, ey - 10)], closed=False)), st(c, 8)])]
    back, front = head_span(ch, ey)
    mask = smooth([(front - 2, ey - h * 0.42), (ex, ey - h * 0.62), (ex - w * 0.85, ey - 6), (ex, ey + h * 0.6), (front - 4, ey + h * 0.34)],
                  closed=True, tension=0.38)
    lash = smooth([(ex - w * 0.2, ey), (ex + w * 0.05, ey + h * 0.2), (ex + w * 0.28, ey)], closed=False, tension=0.4)
    return [gr("drawn eye", [sh(lash), st(C["dark"], 5)]), gr("mask", [sh(mask), fl(c)]),
            gr("strap", [sh(smooth([(ex - w * 0.8, ey - 6), ((ex + back) / 2.0, ey - 14), (back - 2, ey - 10)], closed=False, tension=0.4)), st(c, 8)])]


# ------------------------------------------------------------------ nose and mouth
def mustache(ch, c):
    if view_of(ch) == BACK:
        return []
    nx, ny = map(float, ch.nose)
    half = smooth([(nx, ny + 10), (nx - 22, ny + 6), (nx - 40, ny + 12), (nx - 50, ny + 2), (nx - 46, ny + 18), (nx - 26, ny + 24), (nx - 6, ny + 18)],
                  closed=True, tension=0.36, sharp={3: 0.8})
    return [squash([gr("mustache", [sh(half), fl(c)])], (nx - 4, ny + 12), 0.7, nm="mustache")]


def face_mask(ch, c):
    if view_of(ch) == BACK:
        return []
    nx, ny = map(float, ch.nose)
    mx, my = map(float, ch.mouth)
    top, bot = ny - 12, my + 42
    mask = smooth([(nx - 96, top + 12), (nx - 30, top - 2), (nx + 8, top + 6), (nx + 12, (top + bot) / 2), (mx + 2, bot - 6),
                   (nx - 58, bot + 2), (nx - 98, bot - 14)], closed=True, tension=0.34, sharp={0: 0.4})
    pleats = [sh(Path([(nx - 86, top + 18 + 12 * q), (nx - 4, top + 18 + 12 * q)], closed=False)) for q in range(3)]
    loop = sh(smooth([(nx - 94, top + 24), (nx - 140, top + 20), (nx - 178, top + 4)], closed=False, tension=0.4))     # under the eye
    return [gr("pleats", pleats + [st(C["white"], 3, 60)]), gr("mask", [sh(mask), fl(c)]), gr("loops", [loop, st(C["white"], 4)])]


def clown_nose(ch):
    if view_of(ch) == BACK:
        return []
    nx, ny = map(float, ch.nose)
    return [gr("shine", [el((nx - 2, ny - 6), (8, 6)), fl(C["white"], 80)]), gr("nose", [el((nx + 2, ny), (34, 32)), fl(C["red"])])]


# ------------------------------------------------------------------ on the head: clips, flowers, headphones
def bow(ch, color):
    bx, by, k = on_top(ch, 22.0, 12.0)
    wing = lambda q: smooth([(bx, by), (bx + q * 30, by - 20), (bx + q * 36, by + 2), (bx + q * 28, by + 20)], closed=True, tension=0.35,  # noqa: E731
                            sharp={0: 0.9})
    items = [gr("knot", [el((bx, by), (16, 16)), fl(C["coral"])]), gr("wings", [sh(wing(1)), sh(wing(-1)), fl(color)])]
    narrow = 0.6 if view_of(ch) == FRONT else 1.0
    return [gr("bow", items, a=(bx, by), p=(bx, by), r=14 * k, s=(100.0 * narrow, 100.0))]


def star_clip(ch, color):
    sx, sy, _ = on_top(ch, 24.0, 16.0)
    narrow = 0.55 if view_of(ch) == FRONT else 1.0
    return [gr("star clip", [sh(star5((sx, sy), 17)), fl(color)], a=(sx, sy), p=(sx, sy), s=(100.0 * narrow, 100.0))]


def flower(ch, petal_c):
    fx, fy, _ = on_top(ch, 28.0, 16.0, side="L")
    petals = [el((fx + 15 * math.cos(a), fy + 15 * math.sin(a)), (20, 20)) for a in (k * 2 * math.pi / 5 - math.pi / 2 for k in range(5))]
    return [gr("flower", [gr("centre", [el((fx, fy), (14, 14)), fl(C["yellow"])]), gr("petals", petals + [fl(petal_c)])])]


def _ear_spot(ch, y):
    """Where an ear cup goes on the side of the head (side view): a little behind the middle of the head."""
    back, front = head_span(ch, y)
    return back + 0.42 * (front - back)


def headphones(ch, color):
    """Side view (the front drawing serves from behind): the near cup on the side of the head, the band over it."""
    (ex, ey), w, h = near_eye(ch)
    cy = ey + 6
    hx = _ear_spot(ch, cy)
    top = float(ch.crown[1]) - 12
    band = Path([(hx - 2, cy - 34), (hx + 8, top + 2)], i=[(0, 0), (-14, 30)], o=[(-6, -30), (0, 0)], closed=False)
    return [gr("headphones", [
        gr("cup", [rc((hx, cy), (54, 70), 24), fl(color)]),
        gr("cap", [rc((hx, cy), (30, 44), 14), fl(C["white"], 35)]),
        gr("band", [sh(band), st(C["dark"], 9)]),
    ])]


def earmuffs(ch, c):
    """Side view (the front drawing serves from behind): the near muff on the side of the head, the band over it."""
    (ex, ey), w, h = near_eye(ch)
    cy = ey - 10
    hx = _ear_spot(ch, cy)
    top = float(ch.crown[1]) - 10
    fluff = [el((hx + 16 * math.cos(a), cy + 16 * math.sin(a)), (34, 34)) for a in (k * math.pi / 3 for k in range(6))] + [el((hx, cy), (52, 56))]
    band = Path([(hx - 2, cy - 30), (hx + 8, top + 2)], i=[(0, 0), (-14, 26)], o=[(-6, -26), (0, 0)], closed=False)
    return [gr("earmuffs", [gr("muff", fluff + [fl(c)]), gr("band", [sh(band), st(C["silver"], 8)])])]


# ------------------------------------------------------------------ at the neck (body space)
def scarf(ch, color, stripe):
    sx, sy = neck_point(ch)
    sy -= 2
    if view_of(ch) == BACK:
        return [gr("scarf", [gr("stripes", [rc((sx - 40, sy), (8, 28), 2), rc((sx + 10, sy), (8, 28), 2), fl(stripe)]),
                             gr("loop", [rc((sx, sy), (150, 30), 15), fl(color)])])]
    back, front = body_span(ch, sy)
    mid = (back + front) / 2.0
    tail = smooth([(front - 22, sy + 4), (front + 2, sy + 6), (front + 10, sy + 62), (front - 14, sy + 66)], closed=True, tension=0.3)
    return [gr("scarf", [
        gr("stripes", [rc((front - 3, sy + 42), (24, 6), 2), rc((back + 26, sy), (8, 28), 2), rc((mid + 12, sy), (8, 28), 2), fl(stripe)]),
        gr("tail", [sh(tail), fl(color)]),
        gr("loop", [rc((mid, sy), (front - back + 12, 30), 15), fl(color)]),
    ])]


def bow_tie(ch, c):
    if view_of(ch) == BACK:
        return []
    sx, sy = neck_point(ch)
    _, front = body_span(ch, sy)
    x = front + 2
    wing = lambda k: Path([(x, sy), (x + k * 30, sy - 16), (x + k * 30, sy + 16)], closed=True)   # noqa: E731
    items = [gr("knot", [rc((x, sy), (14, 16), 4), fl(c)]), gr("wings", [sh(wing(1)), sh(wing(-1)), fl(c)]),
             gr("shade", [sh(wing(1)), sh(wing(-1)), st(C["black"], 3, 25)])]
    return [squash(items, (x, sy), 0.35, nm="bow tie")]


def necktie(ch, c):
    sx, sy = neck_point(ch)
    if view_of(ch) == BACK:
        return [gr("collar", [sh(smooth([(sx - 34, sy - 4), (sx, sy - 10), (sx + 34, sy - 4)], closed=False, tension=0.4)), st(C["white"], 10)])]
    back, front = body_span(ch, sy)
    f40, f74 = body_span(ch, sy + 40)[1], body_span(ch, sy + 74)[1]
    blade = smooth([(front - 4, sy + 10), (front + 6, sy + 10), (f40 + 8, sy + 42), (f74 + 6, sy + 80), (f74 - 2, sy + 84), (f40 - 4, sy + 44)],
                   closed=True, tension=0.32, sharp={0: 0.4, 1: 0.4})
    return [gr("tie", [
        gr("stripe", [sh(Path([(f40 - 2, sy + 34), (f40 + 8, sy + 28)], closed=False)), st(C["white"], 3, 60)]),
        gr("knot", [rc((front + 1, sy + 4), (12, 16), 4), fl(c)]),
        gr("blade", [sh(blade), fl(c)]),
        gr("collar", [sh(smooth([(back + 4, sy - 12), ((back + front) / 2, sy - 8), (front + 4, sy + 2)], closed=False, tension=0.4)), st(C["white"], 10)]),
    ])]


def lei(ch):
    sx, sy = neck_point(ch)
    out = []
    if view_of(ch) == BACK:                         # across the back of the neck: a shallow dip
        pts = [(sx + 74 * t, sy - 8 + 14 * (1.0 - t * t)) for t in (-1.0 + q / 4.0 for q in range(9))]
    else:                                           # from the back of the neck down to the front of the chest
        back, front = body_span(ch, sy)
        pts = []
        for q in range(6):
            t = q / 5.0
            y = sy - 8 + 46 * t * t
            b, f = body_span(ch, y)
            pts.append((b + 10 + (f - b - 10) * t, y))
    for q, (fx, fy) in enumerate(pts):
        c = ("coral", "yellow", "rose", "gum")[q % 4]
        petals = [el((fx + 7 * math.cos(b), fy + 7 * math.sin(b)), (11, 11)) for b in (k * 2 * math.pi / 5 for k in range(5))]
        out.append(gr(f"flower {q}", [gr("centre", [el((fx, fy), (7, 7)), fl(C["white"])]), gr("petals", petals + [fl(C[c])])]))
    return out


def bell_collar(ch, c):
    sx, sy = neck_point(ch)
    if view_of(ch) == BACK:
        return [gr("bell collar", [gr("band", [sh(smooth([(sx - 60, sy - 8), (sx, sy - 2), (sx + 60, sy - 8)], closed=False, tension=0.4)), st(c, 11)])])]
    back, front = body_span(ch, sy)
    band = smooth([(back + 2, sy - 10), ((back + front) / 2, sy - 6), (front + 2, sy + 2)], closed=False, tension=0.4)
    return [gr("bell collar", [
        gr("slot", [sh(Path([(front + 3, sy + 20), (front + 3, sy + 26)], closed=False)), st(C["darkgold"], 3)]),
        gr("bell", [el((front + 3, sy + 18), (22, 22)), fl(C["gold"])]),
        gr("band", [sh(band), st(c, 11)]),
    ])]


def bib(ch, c):
    sx, sy = neck_point(ch)
    if view_of(ch) == BACK:                         # tied at the back of the neck
        loop = lambda k: smooth([(sx, sy - 4), (sx + k * 14, sy - 12), (sx + k * 16, sy + 2)], closed=True, tension=0.36, sharp={0: 0.8})  # noqa: E731
        return [gr("bib tie", [gr("knot", [el((sx, sy - 4), (8, 8)), fl(c)]), gr("loops", [sh(loop(1)), sh(loop(-1)), fl(c)]),
                               gr("edge", [sh(loop(1)), sh(loop(-1)), st(C["ice"], 2)])])]
    back, front = body_span(ch, sy)
    f40 = body_span(ch, sy + 40)[1]
    shape = smooth([(front - 6, sy - 3), (front + 3, sy - 2), (f40 + 7, sy + 40), (f40 + 1, sy + 66), (f40 - 5, sy + 40)], closed=True, tension=0.36,
                   sharp={0: 0.4, 1: 0.4})
    return [gr("bib", [gr("bib", [sh(shape), fl(c)]), gr("edge", [sh(shape), st(C["ice"], 4)]),
                       gr("tie", [sh(smooth([(front - 8, sy - 4), ((back + front) / 2, sy - 8), (back + 4, sy - 8)], closed=False, tension=0.4)), st(C["ice"], 3)])])]


# ------------------------------------------------------------------ on the back
def hero_cape(ch, c, w, n):
    """[(slot, Layer)]: from behind the cape covers the back (over the body); from the side it hangs behind the body
    and flares out behind it, its band and clasp over the near shoulder.  w(f, phase) is the cape's wave."""
    sx, sy = ch.neck_at or ch.neck
    sx, sy = float(sx), float(sy)
    if view_of(ch) == BACK:
        def cape(f):
            return smooth([(sx - 64, sy + 4), (sx + 64, sy + 4), (sx + 100 + 4 * w(f, 0.3), sy + 90), (sx + 124 + 7 * w(f, 0.0), sy + 176),
                           (sx + 44, sy + 166 + 8 * w(f, 1.0)), (sx, sy + 178),
                           (sx - 44, sy + 166 + 8 * w(f, 2.0)), (sx - 124 + 7 * w(f, 0.5), sy + 176), (sx - 100 + 4 * w(f, 0.8), sy + 90)],
                          closed=True, tension=0.3, sharp={0: 0.4, 1: 0.4})
        folds = [sh(Path([(sx + dx, sy + 40), (sx + dx * 1.7, sy + 160)], closed=False)) for dx in (-40, 0, 40)]
        return [("mid", Layer("wear hero cape", [gr("folds", folds + [st(C["black"], 4, 12)]), gr("cape", [sh(F(n, cape, tol=0.6)), fl(c)])],
                              parent="body"))]
    back, front = body_span(ch, sy + 20)

    mid = (back + front) / 2.0

    def cape(f):                                    # (its front edge stays behind the middle of the body: it hangs at the back)
        return smooth([(mid - 6, sy + 6), (back + 8, sy + 6), (back - 40 + 4 * w(f, 0.3), sy + 90), (back - 66 + 7 * w(f, 0.0), sy + 176),
                       (back + 6, sy + 166 + 8 * w(f, 1.0)), (mid - 10, sy + 150)], closed=True, tension=0.3, sharp={0: 0.4, 1: 0.4, 5: 0.4})
    b8, f8 = body_span(ch, sy + 8)
    top = Layer("wear hero cape clasp", [gr("clasp", [el((f8 - 12, sy + 10), (16, 16)), fl(C["gold"])]),
                                         gr("cape top", [rc(((b8 + f8) / 2.0, sy + 9), (f8 - b8 - 4, 14), 7), fl(c)])], parent="body")
    return [("mid", top), ("back", Layer("wear hero cape", [gr("cape", [sh(F(n, cape, tol=0.6)), fl(c)])], parent="body"))]


def wing_spots(ch):
    """[(k, (sx, sy), turn, slot)] for the wings a view shows: k is the wing's side as drawn from the front (+1 the right
    wing), (sx, sy) the point the front's wing drawings are measured from (the neck), turn extra degrees.  From the
    side both wings spread backwards from the shoulder blades, the far one a little higher; from behind they are the
    front's, drawn over the body."""
    sx, sy = ch.neck_at or ch.neck
    sx, sy = float(sx), float(sy)
    if view_of(ch) == BACK:
        return [(1, (sx, sy), 0.0, "mid"), (-1, (sx, sy), 0.0, "mid")]
    back, _ = body_span(ch, sy + 36)
    return [(-1, (back + 34.0, sy - 4.0), 0.0, "back"), (-1, (back + 40.0, sy - 10.0), 14.0, "back")]


def backpack(ch, c):
    """[(slot, Layer)]: the bag on the back (behind the body from the side, over it from behind) and the straps."""
    sx, sy = ch.neck_at or ch.neck
    sx, sy = float(sx), float(sy)
    if view_of(ch) == BACK:
        flap = smooth([(sx - 74, sy + 22), (sx, sy + 8), (sx + 74, sy + 22), (sx + 70, sy + 44), (sx - 70, sy + 44)], closed=True, tension=0.3)
        return [("mid", Layer("wear backpack straps", [gr("straps", [sh(Path([(sx - 46, sy + 10), (sx - 40, sy - 4)], closed=False)),
                                                                     sh(Path([(sx + 46, sy + 10), (sx + 40, sy - 4)], closed=False)), st(c, 10)])],
                              parent="body")),
                ("mid", Layer("wear backpack", [
                    gr("handle", [sh(smooth([(sx - 20, sy + 4), (sx, sy - 8), (sx + 20, sy + 4)], closed=False, tension=0.4)), st(c, 7)]),
                    gr("pocket", [rc((sx, sy + 96), (96, 46), 14), fl(C["white"], 40)]),
                    gr("flap", [sh(flap), fl(C["black"], 14)]),
                    gr("bag", [rc((sx, sy + 66), (156, 128), 26), fl(c)])], parent="body"))]
    back, front = body_span(ch, sy + 60)
    strap = smooth([(back + 10, sy + 12), (sx - 4, sy + 2), (front - 14, sy + 30), (front - 22, sy + 74), (back + 18, sy + 100)], closed=False, tension=0.36)
    return [("mid", Layer("wear backpack straps", [gr("straps", [sh(strap), st(c, 10)])], parent="body")),
            ("back", Layer("wear backpack", [gr("pocket", [rc((back - 50, sy + 74), (18, 44), 6), fl(C["white"], 40)]),
                                             gr("bag", [rc((back - 18, sy + 62), (80, 128), 24), fl(c)])], parent="body"))]


# ------------------------------------------------------------------ on the body
def apron(ch, c):
    sx, sy = ch.neck_at or ch.neck
    sx, sy = float(sx), float(sy)
    if view_of(ch) == BACK:                         # the strap round the neck, the tie across the back with a bow
        loop = lambda k: smooth([(sx, sy + 70), (sx + k * 18, sy + 58), (sx + k * 20, sy + 78)], closed=True, tension=0.36, sharp={0: 0.8})  # noqa: E731
        return [gr("apron", [
            gr("bow", [el((sx, sy + 70), (10, 10)), sh(loop(1)), sh(loop(-1)), fl(c)]),
            gr("tie", [sh(Path([(sx - 74, sy + 70), (sx + 74, sy + 70)], closed=False)), st(c, 6)]),
            gr("strap", [sh(smooth([(sx - 30, sy + 8), (sx, sy + 2), (sx + 30, sy + 8)], closed=False, tension=0.4)), st(c, 6)]),
        ])]
    f28, f64, f100 = (body_span(ch, sy + d)[1] for d in (28, 64, 100))
    back70 = body_span(ch, sy + 70)[0]
    shape = smooth([(f28 - 12, sy + 28), (f28 + 3, sy + 28), (f64 + 5, sy + 64), (f100 + 8, sy + 112), (f100 - 10, sy + 118), (f64 - 12, sy + 66)],
                   closed=True, tension=0.32, sharp={0: 0.5, 1: 0.5})
    loop = lambda k: smooth([(back70 + 2, sy + 70), (back70 - 14, sy + 60 + k * 0), (back70 - 16, sy + 80)], closed=True, tension=0.36, sharp={0: 0.8})  # noqa: E731
    return [gr("apron", [
        gr("apron", [sh(shape), fl(c)]), gr("edge", [sh(shape), st(C["ice"], 3)]),
        gr("strap", [sh(smooth([(f28 - 6, sy + 30), (f28 - 16, sy + 6), (sx - 12, sy + 0)], closed=False, tension=0.4)), st(c, 6)]),
        gr("tie", [sh(Path([(f64 - 12, sy + 70), (back70 + 4, sy + 70)], closed=False)), sh(loop(1)), st(c, 6)]),
    ])]


def xmas_sweater(ch, c):
    sx, sy = ch.neck_at or ch.neck
    sx, sy = float(sx), float(sy)
    if view_of(ch) == BACK:
        body = smooth([(sx - 64, sy + 10), (sx + 64, sy + 10), (sx + 76, sy + 60), (sx + 78, sy + 104), (sx, sy + 112), (sx - 78, sy + 104), (sx - 76, sy + 60)],
                      closed=True, tension=0.34)
        zig = Path([(sx - 70 + 14 * q, sy + 60 + (8 if q % 2 else 0)) for q in range(11)], closed=False)
        snow = [el((sx + dx, sy + dy), (7, 7)) for dx, dy in ((-44, 36), (40, 30), (-30, 92), (44, 88), (0, 38))]
        return [gr("sweater", [gr("snow", snow + [fl(C["white"])]), gr("zigzag", [sh(zig), st(C["white"], 5)]),
                               gr("collar", [rc((sx, sy + 12), (100, 14), 7), fl(C["white"])]), gr("body", [sh(body), fl(c)])])]
    b60, f60 = body_span(ch, sy + 60)
    zig = Path([(b60 + 4 + (f60 - b60 - 8) * q / 8.0, sy + 60 + (8 if q % 2 else 0)) for q in range(9)], closed=False)
    b12, f12 = body_span(ch, sy + 12)
    snow = [el((b60 + (f60 - b60) * u, sy + dy), (7, 7)) for u, dy in ((0.3, 36), (0.6, 90), (0.25, 94))]
    return [gr("sweater", [gr("snow", snow + [fl(C["white"])]), gr("zigzag", [sh(zig), st(C["white"], 5)]),
                           gr("collar", [rc(((b12 + f12) / 2.0, sy + 12), (f12 - b12 + 6, 14), 7), fl(C["white"])]),
                           gr("body", [sh(torso(ch, sy + 10, sy + 112)), fl(c)])])]


def tshirt(ch, c):
    sx, sy = ch.neck_at or ch.neck
    sx, sy = float(sx), float(sy)
    if view_of(ch) == BACK:
        body = smooth([(sx - 62, sy + 8), (sx, sy + 4), (sx + 62, sy + 8), (sx + 74, sy + 52), (sx + 76, sy + 98), (sx, sy + 104), (sx - 76, sy + 98),
                       (sx - 74, sy + 52)], closed=True, tension=0.34)
        return [gr("tshirt", [gr("body", [sh(body), fl(c)])])]
    return [gr("tshirt", [gr("body", [sh(torso(ch, sy + 8, sy + 104)), fl(c)])])]


def tutu(ch, c):
    """Side view (the front drawing serves from behind): the same disc of frills, round the body's middle."""
    px, py = ch.pelvis
    py = float(py)
    b, f = body_span(ch, py - 20)
    px = (b + f) / 2.0
    frill = smooth([(px - 74, py - 20)] + [(px - 74 + 148 * q / 8, py + (14 if q % 2 else 2)) for q in range(9)] + [(px + 74, py - 20)], closed=True,
                   tension=0.34)
    return [gr("tutu", [gr("waist", [rc((px, py - 22), (f - b + 8, 12), 6), fl(C["white"], 85)]), gr("frill", [sh(frill), fl(c, 85)]),
                        gr("under", [el((px, py - 4), (176, 40)), fl(c, 55)])])]


# ------------------------------------------------------------------ hats with a front
def cap(ch, c):
    cx, y = map(float, ch.crown)
    y += 22
    dome = smooth([(cx - 78, y), (cx - 70, y - 40), (cx, y - 66), (cx + 70, y - 40), (cx + 78, y)], closed=True, tension=0.38, sharp={0: 0.5, 4: 0.5})
    if view_of(ch) == BACK:                         # the strap's opening at the back, no visor
        return [gr("cap", [
            gr("button", [el((cx, y - 66), (14, 10)), fl(c)]),
            gr("strap", [rc((cx, y - 6), (44, 7), 3), fl(C["black"], 35)]),
            gr("opening", [sh(smooth([(cx - 24, y), (cx, y - 18), (cx + 24, y)], closed=False, tension=0.4)), st(C["black"], 4, 45)]),
            gr("dome", [sh(dome), fl(c)]),
        ])]
    visor = smooth([(cx + 52, y - 8), (cx + 136, y + 2), (cx + 132, y + 12), (cx + 48, y + 6)], closed=True, tension=0.3)
    return [gr("cap", [
        gr("button", [el((cx, y - 66), (14, 10)), fl(c)]),
        gr("seams", [sh(smooth([(cx, y - 64), (cx + 8, y - 30), (cx + 2, y)], closed=False, tension=0.4)), st(C["black"], 2.5, 30)]),
        squash([gr("logo", [sh(star5((cx + 44, y - 30), 12)), fl(C["white"])])], (cx + 44, y - 30), 0.55, nm="logo"),
        gr("visor", [sh(visor), fl(C["black"], 75)]),
        gr("dome", [sh(dome), fl(c)]),
    ])]


def headband(ch, c):
    """Side view (the front drawing serves from behind): round the head at the same height."""
    cx, y = map(float, ch.crown)
    (ex, ey), w, h = near_eye(ch)
    by = (y + ey) / 2.0 - 6
    back, front = head_span(ch, by)
    band = smooth([(back - 4, by + 2), ((back + front) / 2.0, by - 4), (front + 2, by + 8)], closed=False, tension=0.4)
    return [gr("stripe", [sh(band), st(C["white"], 6)]), gr("band", [sh(band), st(c, 24)])]


