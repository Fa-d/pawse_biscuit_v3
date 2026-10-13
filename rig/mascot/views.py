"""The view rig: a mascot turned away from the viewer.

Two channels (rig.CHANNELS), in degrees: body.yaw turns the whole mascot (0 faces the viewer, + turns the face
towards screen-right) and head.yaw turns the head further on top of the body's turn.  While both stay 0 nothing in
this module runs (Character.prepare() only makes a ViewState when one of them moves), so every file without a turn is
byte-identical to what v4 wrote.

The front drawing turns by itself up to `Character.view_warp_max` degrees (the smooth part of the hybrid turn):

  * every part (the head, the body) is a surface: its outline puffed up into a dome as deep as `depth` times its half
    width, plus a snout bump on the head.  A point of the drawing is a point on that surface, so turning the part
    moves it in x by  dx cos(yaw) + z sin(yaw):  the eyes, nose and muzzle slide towards the side the face turns to,
    the far eye narrows and the near one widens.
  * the outline itself, and whatever is drawn behind it (a mane), follow the silhouette instead: a dome seen from
    the side is a little narrower, so the outline only narrows by  sqrt(cos^2 + (depth/width)^2 sin^2).
  * edge rules: a point that turns round behind the silhouette rides the silhouette's edge instead of drawing past
    it (stripes and whiskers on the far cheek pile up at the edge), and a whole feature fades out as it turns away
    (the far blush, the far eye at a sharp turn).  Thin marks and patches near the outline blend between the two.
  * small groups (an eye, a brow, the nose, the mouth, a shine) move as one piece: a group around them gets the
    position, the narrowing and the fade; bigger groups (the outline, a mask, stripes across the head) move point by
    point.  Ears turn with the head and narrow like plates; shoulders, hips, feet and the root of the tail turn with
    the body, the arm on the far side goes behind the body past FAR_ARM_BEHIND degrees, and the tail swings round.

Drawn views (three-quarter targets, side and back) come on top of this in the same module.
"""
from __future__ import annotations

import copy
import math
from functools import lru_cache

import numpy as np

from .lottie import Anim, Layer, Path, gr, prop

WARP_MAX = 45.0           # degrees the front drawing turns at most (Character.view_warp_max)
FAR_ARM_BEHIND = 12.0     # degrees of body turn past which the arm on the far side is drawn behind the body
COMPACT = 0.5             # a group no wider than this share of its part (and no taller than COMPACT_H) moves as one piece
COMPACT_H = 0.6
EDGE_IN = 0.86            # how far out (0 centre, 1 outline) points start to follow the silhouette instead of the surface
OUTLINE_AT = 0.97         # a feature anchored this far out sits on the outline (a tuft, a hat): it follows the silhouette
FADE = 0.25               # a feature fades out over this much loss of facing (the cosine between its normal and the viewer)
FACING_FULL = 0.3         # ... starting when it faces the viewer less than this (or less than it did at rest)
ARM_BANDS = ("paws_over", "arms_front", "arms", "arms_back")
SIDE_FROM = 67.5          # degrees of turn from which a part is drawn from the side (mirrored for a negative turn)...
BACK_FROM = 135.0         # ... and from which it is drawn from behind (the hybrid's snaps)
SMEAR = {-1: 0.06, 0: 0.14, 1: 0.06}     # how much a part squashes in x on the frames around a snap
HEAD_SET = ("brows", "eyes", "face", "head", "right ear", "left ear")
WEAR_EVERY_VIEW = ("hat",)                 # worn things that look right from every side (the crown is in the same place)
PROXY_METHODS = ("head_shapes", "tuft_shapes", "ear_shapes", "eye_shapes", "nose_shapes", "blush_shapes", "face_static",
                 "body_shapes", "foot_shapes", "hand_shapes", "head_outline", "body_outline")
VIEW_OPTIONS = ("squash", "face", "tail_slot", "tail_flip", "tail_rot", "arms_behind", "arm_turn")


def smoothstep(a, b, x):
    """0 at a, 1 at b (either way round), smooth in between."""
    t = np.clip((np.asarray(x, dtype=float) - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# ------------------------------------------------------------------ geometry of a part
def sample_path(path, per=16):
    """Points along a bezier Path (per points per segment), as an (n, 2) array."""
    v, i, o = (np.array(a, dtype=float).reshape(-1, 2) for a in (path.v, path.i, path.o))
    n = len(v)
    segs = n if path.c else n - 1
    t = np.linspace(0.0, 1.0, per, endpoint=False)[:, None]
    out = []
    for k in range(segs):
        p0, p3 = v[k], v[(k + 1) % n]
        p1, p2 = p0 + o[k], p3 + i[(k + 1) % n]
        out.append((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)
    pts = np.concatenate(out) if out else v
    if not path.c:
        pts = np.vstack([pts, v[-1:]])
    return pts


class Surface:
    """A part of the drawing as a surface facing the viewer: the outline puffed up into a dome.

    outline : the part's outline Path (the head's or the body's), in the part's drawing coordinates
    depth   : how deep the dome is, as a share of the outline's half width
    snout   : (x, y, extra depth, radius): a muzzle that sticks out further than the dome
    """

    def __init__(self, outline, depth=0.85, snout=None):
        P = sample_path(outline, 24)
        self.poly = P
        (x0, y0), (x1, y1) = P.min(0), P.max(0)
        self.box = (float(x0), float(y0), float(x1), float(y1))
        self.cx, self.cy = float(x0 + x1) / 2.0, float(y0 + y1) / 2.0
        self.R = float(x1 - x0) / 2.0
        self.width, self.height = float(x1 - x0), float(y1 - y0)
        self.rz = depth * self.R
        self.snout = snout
        # radius of the outline in every direction from the centre, and its reach left and right at every height
        self.phi = np.linspace(-math.pi, math.pi, 1441)
        self.rad = self._rays(P)
        self.ytab = np.linspace(y0, y1, 241)
        self.half = self._halves(P)
        self.btab = np.array([self.z_dome(np.array([self.cx]), np.array([y]))[0] for y in self.ytab])

    def _rays(self, P):
        A = P - (self.cx, self.cy)
        D = np.roll(P, -1, axis=0) - P
        u = np.stack([np.cos(self.phi), np.sin(self.phi)], axis=1)
        den = u[:, :1] * D[None, :, 1] - u[:, 1:] * D[None, :, 0]                     # cross(u, d)
        num_t = A[:, 0] * D[:, 1] - A[:, 1] * D[:, 0]                                  # cross(a - c, d)
        num_s = A[None, :, 0] * u[:, 1:] - A[None, :, 1] * u[:, :1]                     # cross(a - c, u)
        ok = np.abs(den) > 1e-12
        den = np.where(ok, den, 1.0)
        t, s = num_t[None, :] / den, num_s / den
        hit = ok & (s >= -1e-9) & (s <= 1 + 1e-9) & (t > 0)
        r = np.where(hit, t, 0.0).max(axis=1)
        return np.maximum(r, 1.0)

    def _halves(self, P):
        a, b = P, np.roll(P, -1, axis=0)
        out = np.zeros((len(self.ytab), 2))
        for q, y in enumerate(self.ytab):
            lo, hi = np.minimum(a[:, 1], b[:, 1]), np.maximum(a[:, 1], b[:, 1])
            m = (lo <= y) & (y <= hi) & (hi - lo > 1e-9)
            if not m.any():
                out[q] = (1.0, 1.0)
                continue
            xs = a[m, 0] + (y - a[m, 1]) / (b[m, 1] - a[m, 1]) * (b[m, 0] - a[m, 0])
            out[q] = (max(1.0, xs.max() - self.cx), max(1.0, self.cx - xs.min()))
        return out

    # ---- per point
    def rho(self, x, y):
        dx, dy = x - self.cx, y - self.cy
        return np.hypot(dx, dy) / np.interp(np.arctan2(dy, dx), self.phi, self.rad)

    def z_dome(self, x, y):
        r = self.rho(x, y)
        return self.rz * np.sqrt(np.clip(1.0 - r * r, 0.0, None))

    def z(self, x, y):
        z = self.z_dome(x, y)
        if self.snout:
            sx, sy, dz, rr = self.snout
            z = z + dz * np.exp(-((x - sx) ** 2 + (y - sy) ** 2) / (2.0 * rr * rr)) * smoothstep(1.0, 0.8, self.rho(x, y))
        return z

    def info(self, P):
        """Everything about points P ((k, 2)) that does not depend on the angle."""
        P = np.asarray(P, dtype=float).reshape(-1, 2)
        x, y = P[:, 0], P[:, 1]
        h = 1.0
        z = self.z(x, y)
        gx = (self.z(x + h, y) - self.z(x - h, y)) / (2 * h)
        gy = (self.z(x, y + h) - self.z(x, y - h)) / (2 * h)
        nl = np.sqrt(gx * gx + gy * gy + 1.0)
        yc = np.clip(y, self.ytab[0], self.ytab[-1])
        aR, aL = np.interp(yc, self.ytab, self.half[:, 0]), np.interp(yc, self.ytab, self.half[:, 1])
        dx = x - self.cx
        return dict(x=x, y=y, dx=dx, z=z, nx=-gx / nl, nz=1.0 / nl, rho=self.rho(x, y), aR=aR, aL=aL,
                    a=np.where(dx >= 0, aR, aL), b=np.interp(yc, self.ytab, self.btab))

    # ---- turning (th: angles in radians, one per frame; results are (points, frames))
    @staticmethod
    def _sil(b, a, c, s):
        k = np.minimum(b / np.maximum(a, 1.0), 1.5)
        return np.sqrt(c * c + (k * k)[:, None] * s * s)

    def outline_x(self, I, th):
        """The silhouette rule: the outline (and what lies behind it) narrows like a turned dome."""
        c, s = np.cos(th)[None, :], np.sin(th)[None, :]
        return self.cx + I["dx"][:, None] * self._sil(I["b"], I["a"], c, s)

    def turn_x(self, I, th):
        """A point of the surface turned round the part's vertical axis: (x, depth towards the viewer)."""
        c, s = np.cos(th)[None, :], np.sin(th)[None, :]
        dx, z = I["dx"][:, None], I["z"][:, None]
        return self.cx + dx * c + z * s, -dx * s + z * c

    def facing(self, I, th):
        """How squarely each point faces the viewer once turned (1 head on, 0 edge on, < 0 turned away)."""
        return -I["nx"][:, None] * np.sin(th)[None, :] + I["nz"][:, None] * np.cos(th)[None, :]

    def surface_x(self, I, th):
        """The surface rule with the edge rules: points turn with the surface; one that turns round behind the
        silhouette rides its edge; near the outline (rho EDGE_IN .. 1) points blend into the silhouette rule."""
        c, s = np.cos(th)[None, :], np.sin(th)[None, :]
        xr, _ = self.turn_x(I, th)
        xo = self.outline_x(I, th)
        nz0 = I["nz"][:, None]
        h0 = np.minimum(0.06, nz0 - 0.02)
        hidden = smoothstep(h0, h0 - 0.12, self.facing(I, th))
        far = np.sign(th)[None, :]
        a_far = np.where(far >= 0, I["aR"][:, None], I["aL"][:, None])
        edge = self.cx + far * a_far * np.sqrt(c * c + (np.minimum(I["b"][:, None] / np.maximum(a_far, 1.0), 1.5)) ** 2 * s * s)
        xi = xr + (edge - xr) * hidden
        k = smoothstep(EDGE_IN, 1.0, I["rho"])[:, None]
        return xi + (xo - xi) * k

    def back_x(self, I, th):
        """A point on the back of the part (a backpack, wings): it turns the other way round."""
        c, s = np.cos(th)[None, :], np.sin(th)[None, :]
        return self.cx + I["dx"][:, None] * c - I["z"][:, None] * s

    def map_x(self, I, th, mode="surface"):
        if mode == "outline":
            return self.outline_x(I, th)
        if mode == "back":
            return self.back_x(I, th)
        return self.surface_x(I, th)

    def span(self, l, r, th, mode="surface"):
        """Where the two ends (l, r) of something drawn across the surface land: (x of l, x of r) per frame.  Mapping
        the ends rather than the middle keeps a feature inside the silhouette: near the edge it squashes against it."""
        X = self.map_x(self.info([l, r]), th, mode)
        return X[0], X[1]

    def visible(self, I, th):
        """1 while a feature faces the viewer, fading to 0 as it turns away (always 1 at rest)."""
        hi = np.minimum(FACING_FULL, I["nz"])[:, None]
        return smoothstep(hi - FADE, hi, self.facing(I, th))


def _outline_key(path):
    return tuple(round(v, 2) for v in path.flat()) + (path.c,)


@lru_cache(maxsize=256)
def _surface(key, depth, snout):
    flat, closed = key[:-1], key[-1]
    n = len(flat) // 6
    return Surface(Path.unflat(flat, n, closed), depth=depth, snout=snout)


def head_surface(ch):
    vh = dict(VIEW_HEAD, **getattr(ch, "view_head", {}))
    snout = None
    if vh.get("snout"):
        dz, r = vh["snout"]
        snout = (float(ch.nose[0]), float(ch.nose[1]) + 8.0, float(dz), float(r))
    return _surface(_outline_key(ch.head_outline()), float(vh["depth"]), snout)


def body_surface(ch):
    vb = dict(VIEW_BODY, **getattr(ch, "view_body", {}))
    return _surface(_outline_key(ch.body_outline()), float(vb["depth"]), None)


VIEW_HEAD = dict(depth=0.85, snout=(14.0, 34.0))      # defaults of Character.view_head: dome depth, snout (extra depth, radius)
VIEW_BODY = dict(depth=0.8)


# ------------------------------------------------------------------ reading the Lottie a drawing was written as
def static_value(p):
    """The value of a property at rest (a constant, or the first key of an animated one)."""
    if p.get("a", 0) == 0:
        return p["k"]
    s = p["k"][0]["s"]
    return s[0] if isinstance(s, list) and len(s) == 1 else s


def animated(p):
    return p.get("a", 0) == 1


def prop_at(p, t):
    """Value of a property at frame t of the file (eased between keys, held on hold keys)."""
    if not animated(p):
        return p["k"]
    ks = p["k"]

    def val(k):
        s = k["s"]
        return s[0] if isinstance(s, list) and len(s) == 1 else s

    if t <= ks[0]["t"]:
        return val(ks[0])
    for a, b in zip(ks, ks[1:]):
        if a["t"] <= t < b["t"]:
            va, vb = val(a), val(b)
            if a.get("h"):
                return va
            u = (t - a["t"]) / float(b["t"] - a["t"])
            if "o" in a:
                ox, oy, ix, iy = (a["o"]["x"], a["o"]["y"], a["i"]["x"], a["i"]["y"])
                ox, oy, ix, iy = (q[0] if isinstance(q, list) else q for q in (ox, oy, ix, iy))
                from .lottie import ease_eval
                u = float(ease_eval((ox, oy, ix, iy), u))
            if isinstance(va, dict):
                return {"c": va["c"], **{key: [[pa[0] + (pb[0] - pa[0]) * u, pa[1] + (pb[1] - pa[1]) * u] for pa, pb in zip(va[key], vb[key])]
                                        for key in ("v", "i", "o")}}
            if isinstance(va, list):
                return [x + (y - x) * u for x, y in zip(va, vb)]
            return va + (vb - va) * u
    return val(ks[-1])


def matrix(trn):
    """3 x 3 matrix of a group transform ('tr' item) at rest: T(p) R(r) S(s) T(-a)."""
    p, a, s, r = (static_value(trn[k]) for k in ("p", "a", "s", "r"))
    rr = math.radians(float(r))
    c, sn = math.cos(rr), math.sin(rr)
    T = np.array([[1, 0, p[0]], [0, 1, p[1]], [0, 0, 1.0]])
    R = np.array([[c, -sn, 0], [sn, c, 0], [0, 0, 1.0]])
    S = np.diag([float(s[0]) / 100.0, float(s[1]) / 100.0, 1.0])
    A = np.array([[1, 0, -a[0]], [0, 1, -a[1]], [0, 0, 1.0]])
    return T @ R @ S @ A


def apply(M, P):
    P = np.asarray(P, dtype=float).reshape(-1, 2)
    return P @ M[:2, :2].T + M[:2, 2]


def geometry_points(it):
    """Points that bound one shape item (path vertices and handles, an ellipse's or a rectangle's corners) at rest."""
    ty = it.get("ty")
    if ty == "sh":
        k = static_value(it["ks"])
        v = np.array(k["v"], dtype=float).reshape(-1, 2)
        if not len(v):
            return np.zeros((0, 2))
        return np.vstack([v, v + np.array(k["i"], dtype=float).reshape(-1, 2), v + np.array(k["o"], dtype=float).reshape(-1, 2)])
    if ty in ("el", "rc"):
        c, s = np.array(static_value(it["p"]), dtype=float), np.array(static_value(it["s"]), dtype=float)
        return np.array([c - s / 2, c + s / 2, (c[0] - s[0] / 2, c[1] + s[1] / 2), (c[0] + s[0] / 2, c[1] - s[1] / 2)])
    return np.zeros((0, 2))


def tree_points(items, M=np.eye(3)):
    out = []
    for it in items:
        if it.get("ty") == "gr":
            G = M @ matrix(it["it"][-1])
            if abs(np.linalg.det(G[:2, :2])) < 1e-9:
                continue
            out.append(tree_points(it["it"][:-1], G))
        else:
            P = geometry_points(it)
            if len(P):
                out.append(apply(M, P))
    return np.vstack(out) if out else np.zeros((0, 2))


def is_leaf(g):
    return g.get("ty") == "gr" and not any(it.get("ty") == "gr" for it in g["it"][:-1])


GEOMETRY = ("sh", "el", "rc", "sr")


# ------------------------------------------------------------------ the turn of one mascot through one clip
def norm_deg(d):
    """Degrees in (-180, 180]."""
    return (np.asarray(d, dtype=float) + 180.0) % 360.0 - 180.0


def bucket_of(d, has_side, has_back):
    """Which drawing a part turned by d degrees (normalised) shows: 'front' (warped), 'side' (facing right), 'side-'
    (the side view mirrored, facing left) or 'back'.  A view the mascot has not got falls back to the nearest one."""
    a = abs(d)
    side = "side" if d > 0 else "side-"
    if a < SIDE_FROM:
        return "front"
    if a < BACK_FROM:
        return side if has_side else "front"
    if has_back:
        return "back"
    return side if has_side else "front"


class ViewState:
    """Per-frame turn of a prepared Character: which way each part faces and how the front drawing follows."""

    def __init__(self, ch):
        T = ch.T
        self.ch = ch
        self.n = ch.n
        self.body_deg = np.asarray(T["body.yaw"], dtype=float).copy()
        self.head_deg = self.body_deg + np.asarray(T["head.yaw"], dtype=float)
        self.warp_max = float(getattr(ch, "view_warp_max", WARP_MAX))
        self.has_side = ch.view_data("side") is not None
        self.has_back = ch.view_data("back") is not None
        self.head_bucket = [bucket_of(d, self.has_side, self.has_back) for d in norm_deg(self.head_deg)]
        self.body_bucket = [bucket_of(d, self.has_side, self.has_back) for d in norm_deg(self.body_deg)]
        self.body_th = np.radians(self._front_angles(self.body_deg, self.body_bucket))
        self.head_th = np.radians(self._front_angles(self.head_deg, self.head_bucket))
        self.head = head_surface(ch)
        self.body = body_surface(ch)
        self._pts = {}
        self.proxies = {}

    def _front_angles(self, deg, buckets):
        """The angle the front drawing is warped to on every frame.  While a part is drawn from another side its front
        drawing is hidden: it holds the angle it had when it was last shown (fewer keys)."""
        a = self.warp_angle(deg)
        shown = np.array([b == "front" for b in buckets])
        if shown.all():
            return a
        if not shown.any():
            return np.full(len(a), float(np.sign(norm_deg(deg[0])) or 1.0) * self.warp_max)
        idx = np.where(shown, np.arange(len(a)), -1)
        idx = np.maximum.accumulate(idx)
        first = int(np.argmax(shown))
        idx = np.where(idx < 0, first, idx)
        return a[idx]

    def smear(self, T, loop=True):
        """A quick squash where a part snaps from one drawing to another: the body squashes the whole mascot
        (root.sx), a head turning on its own squashes the head (head.sx)."""
        n = self.n
        snaps = lambda b: [f for f in range(1, n) if b[f] != b[f - 1]]
        body = snaps(self.body_bucket)
        head = [f for f in snaps(self.head_bucket) if f not in body]
        L = n - 1
        for chn, fs in (("root.sx", body), ("head.sx", head)):
            if not fs:
                continue
            k = np.ones(n)
            for f0 in fs:
                for d, q in SMEAR.items():
                    f = f0 + d
                    f = f % L if (loop and L > 0) else min(max(f, 0), n - 1)
                    k[f] *= 1.0 - q
            if loop and L > 0:
                k[n - 1] = k[0]
            T[chn] = np.asarray(T[chn], dtype=float) * k

    def warp_angle(self, deg):
        """The angle the front drawing is warped to: the turn itself up to view_warp_max, held there beyond it, and on
        the way round the back the same angles again (a mascot without a back view shows its front, as v4's spin)."""
        d = (np.asarray(deg, dtype=float) + 180.0) % 360.0 - 180.0
        d = np.where(np.abs(d) > 90.0, np.sign(d) * (180.0 - np.abs(d)), d)
        return np.clip(d, -self.warp_max, self.warp_max)

    # ---- single points through every frame (cached), for the rig's solves and for props
    def _point(self, part, mode, p):
        key = (part, mode, round(float(p[0]), 3), round(float(p[1]), 3))
        got = self._pts.get(key)
        if got is None:
            S, th = (self.head, self.head_th) if part == "head" else (self.body, self.body_th)
            I = S.info([p])
            if mode == "surface":
                got = S.surface_x(I, th)[0]
            elif mode == "outline":
                got = S.outline_x(I, th)[0]
            else:
                got = S.turn_x(I, th)[0][0]
            self._pts[key] = got
        return got

    def head_point(self, p, f):
        """A point of the head drawing at frame f (eyes, mouth, cheeks slide with the turn; the outline narrows)."""
        if self.head.rho(np.array([p[0]]), np.array([p[1]]))[0] >= OUTLINE_AT:
            return (float(self._point("head", "outline", p)[f]), p[1])
        return (float(self._point("head", "surface", p)[f]), p[1])

    def body_point(self, p, f):
        """A point riding on the body's surface (shoulders, hips) at frame f."""
        return (float(self._point("body", "turn", p)[f]), p[1])

    def ground_point(self, p, f, lift=0.25):
        """A point on the ground under the body (an ankle): turned round the body's axis; the far one sits a little
        higher, as the ground goes away from the viewer."""
        cx = self.body.cx
        th = float(self.body_th[f])
        dx = p[0] - cx
        return (cx + dx * math.cos(th), p[1] - lift * dx * math.sin(th))

    def tail_root(self, p, f):
        vt = dict(TAIL, **getattr(self.ch, "view_tail", {}))
        cx = self.body.cx
        I = self.body.info([(cx, p[1])])
        z = -vt["depth"] * float(I["b"][0])                     # the tail leaves the back of the body
        th = float(self.body_th[f])
        return (cx + (p[0] - cx) * math.cos(th) + z * math.sin(th), p[1])

    def tail_squash(self, f):
        """x scale of the tail.  It points out to the side and back (`angle` degrees from the picture plane), so it
        swings round behind the body as the mascot turns its face to the tail's side: it narrows (never below `min`)
        until it points straight away, then flips over to the other side, where it shows at least `flip` wide."""
        vt = dict(TAIL, **getattr(self.ch, "view_tail", {}))
        a = math.radians(vt["angle"])
        th = float(self.body_th[f])
        m = math.cos(th + a) / math.cos(a)
        if m >= 0.0:
            return float(np.clip(m, vt["min"], 1.3))
        return float(-np.clip(-m, vt["flip"], 1.3))

    def arm_behind(self, s, f):
        """Is arm s drawn behind the body at frame f?  The arm on the far side is, once the body has turned past
        FAR_ARM_BEHIND degrees, while its paw hangs at the side; a paw raised (to the face, holding something up) or
        resting on the front of the body stays where its pose puts it."""
        if self.far(f) != s or abs(float(norm_deg(self.body_deg[f]))) <= FAR_ARM_BEHIND:
            return False
        S, _, W, _ = self.ch.arm_solve(s, f)
        if W[1] < S[1] + 12.0:
            return False
        I = self.body.info([(self.body.cx, W[1])])
        half = float(I["aR"][0] if s == "R" else I["aL"][0])
        return abs(W[0] - self.body.cx) > 0.75 * half

    def far(self, f):
        """The side of the body turned away from the viewer at frame f ('R' when the face turns right), or None."""
        d = float(norm_deg(self.body_deg[f]))
        return None if abs(d) < 1e-9 else ("R" if d > 0 else "L")

    # ---- the rig's attachment points
    def shoulder(self, s, f):
        return self.body_point(self.ch.side(self.ch.shoulder, s), f)

    def hip(self, s, f):
        return self.body_point(self.ch.side(self.ch.hip, s), f)

    def foot(self, s, f):
        return self.ground_point(self.ch.side(self.ch.foot, s), f)

    # ---- the baked layers
    def apply(self, out):
        """(band, Layer) pairs from Character.bake() -> the same with the turn applied."""
        res = []
        for band, L in out:
            if L.null:
                res.append((band, L))
            elif band in ARM_BANDS:
                res.extend(self._arm(band, L))
            elif L.nm in ("right ear", "left ear"):
                self._ear(L)
                res.append((band, L))
            elif L.parent == "neck":
                self._layer(L, "head", outline="head" if L.nm == "head" else None)
                res.append((band, L))
            elif L.nm == "body" or L.parent == "body":
                self._layer(L, "body", outline="body" if L.nm == "body" else None, back=band == "back")
                res.append((band, L))
            elif band in ("tail", "tail_lap", "tail_front"):
                self._tail(L)
                res.append((band, L))
            elif band == "feet":
                self._foot(L)
                res.append((band, L))
            else:
                res.append((band, L))
        res = self._near_first(res)
        if any(b != "front" for b in self.head_bucket + self.body_bucket):
            res = self._drawn(res)
        depth = list(type(self.ch).DEPTH)
        order = sorted(range(len(res)), key=lambda q: (depth.index(res[q][0]) if res[q][0] in depth else len(depth), q))
        return [res[q] for q in order]

    # ---- drawn views (side, back)
    def _kind(self, band, L):
        """Which part a layer of the mascot's own belongs to: 'head', 'body', or None (props, effects, nulls)."""
        if L.null:
            return None
        if L.nm in HEAD_SET:
            return "head"
        if band in ARM_BANDS or band in ("legs", "feet", "tail", "tail_lap", "tail_front") or (band == "body" and L.nm == "body"):
            return "body"
        return None

    def proxy(self, view):
        """The mascot as drawn from `view` ('side', 'side-', 'back'): a copy whose drawings and anchors are the view's
        (Character.view_data); 'side-' is the side view with left and right swapped, drawn under mirror nulls."""
        if view not in self.proxies:
            self.proxies[view] = view_proxy(self.ch, view)
        return self.proxies[view]

    def _drawn(self, res):
        head_on = {v: np.array([b == v for b in self.head_bucket]) for v in set(self.head_bucket)}
        body_on = {v: np.array([b == v for b in self.body_bucket]) for v in set(self.body_bucket)}
        out = []
        for band, L in res:
            kind = self._kind(band, L)
            zone = getattr(L, "view_zone", None)
            if kind is None and zone is not None and zone not in WEAR_EVERY_VIEW:
                kind = "head" if L.parent == "neck" else "body"         # worn things drawn for the front only
            on = head_on if kind == "head" else (body_on if kind == "body" else None)
            front = on.get("front", np.zeros(self.n, bool)) if on is not None else None
            if front is not None and not front.any():           # never seen from the front: not written at all...
                if kind == "body" and L.nm == "body":           # ... but the body still carries the neck and the arms
                    L.null, L.shapes = True, []
                    out.append((band, L))
                continue
            if front is not None and not front.all():
                L.o = _mask(L.o, front, self.n)
            out.append((band, L))
        for v in sorted(head_on):
            if v != "front":
                out.extend(self._head_set(v, head_on[v]))
        for v in sorted(body_on):
            if v != "front":
                out.extend(self._body_set(v, body_on[v]))
        return out

    def _mirror_null(self, v, parent):
        return Layer(f"{parent} mirror [{v}]", null=True, parent=parent, a=(self.ch.CX, 0.0), p=(self.ch.CX, 0.0), s=(-100.0, 100.0))

    def _head_set(self, v, on):
        p = self.proxy(v)
        opt = p.view_options
        out = []
        parent = "neck"
        if v == "side-":
            out.append(("nulls", self._mirror_null(v, "neck")))
            parent = f"neck mirror [{v}]"
        layers = [L for L in p.head_layers() if not L.null]
        if not opt.get("face", True):
            layers = [L for L in layers if L.nm != "face"]
        layers = [L for L in layers if L.shapes or L.nm in ("head",)]
        ears = [L for L in layers if L.nm.endswith(" ear")]
        if len(ears) == 2 and p.view_sides and p.view_sides[0] == "L":       # the near ear over the far one
            a, b = layers.index(ears[0]), layers.index(ears[1])
            layers[a], layers[b] = layers[b], layers[a]
        hints = head_hints(p)
        for L in layers:
            k = opt.get("squash", {}).get(L.nm)
            if k:
                L.shapes = [squashed(g, k, hints) if g.get("ty") == "gr" else g for g in L.shapes]
            L.nm = f"{L.nm} [{v}]"
            L.parent = parent
            L.o = _mask(L.o, on, self.n)
            out.append(("head", L))
        return out

    def _body_set(self, v, on):
        p = self.proxy(v)
        opt = p.view_options
        fx = getattr(self.ch, "_fx", None) or {}
        swap = (lambda s: "L" if s == "R" else "R") if v == "side-" else (lambda s: s)
        out = []
        hips, root = "hips", "root"
        if v == "side-":
            out += [("nulls", self._mirror_null(v, "hips")), ("nulls", self._mirror_null(v, "root"))]
            hips, root = f"hips mirror [{v}]", f"root mirror [{v}]"
        if p.leg is not None:
            p.solve_legs()
        body = p.body_layer()
        body.nm, body.parent = f"body [{v}]", hips
        out.append(("body", body))
        behind = opt.get("arms_behind", "far")
        near = p.view_sides[0] if p.view_sides else None
        for s in "RL":
            held_u, held_o = fx.get(f"hand.{swap(s)}", []), fx.get(f"hand.{swap(s)}.over", [])
            back = behind == "both" or (behind == "far" and s != near)
            side_nm = "right" if s == "R" else "left"
            if back:
                L = p.arm_layer(s, False, held_under=copy.deepcopy(held_u), held_over=copy.deepcopy(held_o), name=f"{side_nm} arm [{v}]")
                L.o = 100
                out.append(("arms_back", L))
                continue
            fr = np.asarray(p.T[f"arm.{s}.front"]) > 0.5
            for front, band in ((True, "arms_front"), (False, "arms")):
                if (fr == front).any():
                    L = p.arm_layer(s, front, held_under=copy.deepcopy(held_u), held_over=copy.deepcopy(held_o))
                    L.nm = f"{L.nm} [{v}]"
                    out.append((band, L))
        for L in out:
            if L[0] in ARM_BANDS:
                L[1].parent = f"body [{v}]"
        if p.leg is not None:
            legs = p.leg_layers()
            if near == "L":
                legs = legs[::-1]
            for L in legs:
                L.nm, L.parent = f"{L.nm} [{v}]", root
                out.append(("legs", L))
        feet = p.foot_layers()
        if near == "L":
            feet = feet[::-1]
        for L in feet:
            L.nm, L.parent = f"{L.nm} [{v}]", root
            out.append(("feet", L))
        if p.tail is not None:
            slot = int(opt.get("tail_slot", 0))
            p.tail_slot = lambda f, slot=slot: slot
            L = p.tail_layer(slot)
            L.nm, L.parent = f"tail [{v}]", hips
            if opt.get("tail_flip"):
                ss = L.s.s if isinstance(L.s, Anim) else [tuple(L.s)] * self.n
                L.s = Anim([(-float(q[0]), float(q[1])) for q in ss], tol=0.4)
            if opt.get("tail_rot"):
                L.r = float(opt["tail_rot"])
            out.append((("tail", "tail_lap", "tail_front")[slot], L))
        for band, L in out:
            if not L.null:
                L.o = _mask(L.o, on, self.n)
        return out

    def _near_first(self, res):
        """Of the two legs and the two feet, the one nearer the viewer is drawn over the other."""
        d = norm_deg(self.body_deg)
        lean = float(np.mean(np.sign(d) * (np.abs(d) > 2.0)))
        if lean <= 0.0:                     # facing left (or not turned): the right side is nearer, as drawn
            return res
        out = list(res)
        for a, b in (("right leg", "left leg"), ("right foot", "left foot")):
            ia = next((q for q, (_, L) in enumerate(out) if L.nm == a), None)
            ib = next((q for q, (_, L) in enumerate(out) if L.nm == b), None)
            if ia is not None and ib is not None and ia < ib:
                out[ia], out[ib] = out[ib], out[ia]
        return out

    # ---- layers of one part
    def _surface(self, part):
        return (self.head, self.head_th) if part == "head" else (self.body, self.body_th)

    def _layer(self, L, part, outline=None, back=False):
        S, th = self._surface(part)
        own = outline is None and (isinstance(L.p, Anim) or isinstance(L.a, Anim) or tuple(L.p) != (0, 0) or tuple(L.a) != (0, 0))
        if own:                                                  # a thing with a place of its own (a tear, a puff): moves as one
            self._move_layer(L, S, th)
        else:
            hints = head_hints(self.ch) if part == "head" else None
            L.shapes = Warp(S, th, self.n, L.roll, hints).items(L.shapes, outline=outline, mode="back" if back else None)

    def _move_layer(self, L, S, th):
        n = self.n
        ps = L.p.s if isinstance(L.p, Anim) else [tuple(L.p)] * n
        P = np.array([tuple(q)[:2] for q in ps], dtype=float)
        I = S.info(P)
        outline = I["rho"] >= OUTLINE_AT
        xs = np.empty(n)
        jx = np.empty(n)
        vis = np.ones(n)
        for f in range(n):                                       # each frame at its own place
            one = {k: v[f:f + 1] for k, v in I.items()}
            t = th[f:f + 1]
            if outline[f]:
                xs[f] = S.outline_x(one, t)[0, 0]
                jx[f] = S._sil(one["b"], one["a"], np.cos(t)[None, :], np.sin(t)[None, :])[0, 0]
            else:
                xs[f] = S.surface_x(one, t)[0, 0]
                jx[f] = _jx(S, P[f], t)[0]
                vis[f] = S.visible(one, t)[0, 0]
        L.p = Anim([(float(x), float(q[1])) for x, q in zip(xs, P)], tol=getattr(L.p, "tol", None) if isinstance(L.p, Anim) else None)
        ss = L.s.s if isinstance(L.s, Anim) else [tuple(L.s)] * n
        L.s = Anim([(float(q[0]) * float(j), float(q[1])) for q, j in zip(ss, np.clip(jx, 0.25, 1.3))], tol=0.4)
        if float(vis.min()) < 0.999:
            os_ = L.o.s if isinstance(L.o, Anim) else [float(L.o)] * n
            L.o = Anim([float(o) * float(v) for o, v in zip(os_, vis)], tol=1.0)

    def _ear(self, L):
        """Ears turn with the head like plates standing on it: the root rides the head, the ear narrows."""
        S, th = self.head, self.head_th
        piv = tuple(L.p)[:2]
        x, _ = S.turn_x(S.info([piv]), th)
        k = np.clip(np.cos(th), 0.45, 1.0)
        L.p = Anim([(float(v), piv[1]) for v in x[0]])
        ss = L.s.s if isinstance(L.s, Anim) else [tuple(L.s)] * self.n
        L.s = Anim([(float(q[0]) * float(j), float(q[1])) for q, j in zip(ss, k)], tol=0.4)

    def _tail(self, L):
        ps = L.p.s if isinstance(L.p, Anim) else [tuple(L.p)] * self.n
        L.p = Anim([self.tail_root(q, f) for f, q in enumerate(ps)], tol=0.4)
        ss = L.s.s if isinstance(L.s, Anim) else [tuple(L.s)] * self.n
        L.s = Anim([(float(q[0]) * self.tail_squash(f), float(q[1])) for f, q in enumerate(ss)], tol=0.4)

    def _foot(self, L):
        """A foot seen at an angle shows more of its length."""
        th = self.body_th
        k = np.sqrt(np.cos(th) ** 2 + 1.6 * np.sin(th) ** 2)
        ss = L.s.s if isinstance(L.s, Anim) else [tuple(L.s)] * self.n
        L.s = Anim([(float(q[0]) * float(j), float(q[1])) for q, j in zip(ss, k)], tol=0.6)

    def _arm(self, band, L):
        """The shoulder rides the body; the far arm goes behind the body once the body has turned far enough."""
        s = "R" if L.nm.startswith("right") else "L"
        L.p = Anim([self.shoulder(s, f) for f in range(self.n)], tol=0.3)
        behind = np.array([self.arm_behind(s, f) for f in range(self.n)])
        if not behind.any() or band == "arms_back":
            return [(band, L)]
        if band == "paws_over":                                  # the paw drawn over props: not while it is behind
            L.o = _times(L.o, ~behind, self.n)
            return [(band, L)]
        if behind.all():
            return [("arms_back", L)]
        back = copy.deepcopy(L)
        back.nm = L.nm + " behind"
        L.o = _times(L.o, ~behind, self.n)
        back.o = _times(back.o, behind, self.n)
        return [(band, L), ("arms_back", back)]


TAIL = dict(angle=60.0, depth=0.8, min=0.5, flip=0.85)


def _times(o, mask, n):
    """Opacity o (constant or Anim) shown only on the frames where mask is True (hold keys)."""
    os_ = o.s if isinstance(o, Anim) else [float(o)] * n
    return Anim([float(v) if m else 0.0 for v, m in zip(os_, mask)], hold=True)


def _mask(o, mask, n):
    """Opacity o shown only on the frames where mask is True: hold keys, unless o fades smoothly by itself."""
    mask = np.asarray(mask, dtype=bool)
    if mask.all():
        return o
    if isinstance(o, Anim) and not o.hold:
        return Anim([float(v) if m else 0.0 for v, m in zip(o.s, mask)], tol=o.tol)
    return _times(o, mask, n)


class ViewT(dict):
    """A clip's channels as a drawn view reads them: with left and right swapped (the mirrored side view draws its
    near, left side from the right side's channels, so the paw nearer the viewer is still the one that moves) and with
    offsets added (arm_turn: arms hang a little more forward... or back, seen from the side)."""

    def __init__(self, T, swap=False, add=None):
        super().__init__()
        self.T = T
        self.sw = swap
        self.add = {k: v for k, v in (add or {}).items() if v}
        self._got = {}

    def swap(self, k):
        if not self.sw:
            return k
        if ".R." in k:
            return k.replace(".R.", ".L.")
        if ".L." in k:
            return k.replace(".L.", ".R.")
        return k

    def __getitem__(self, k):
        if k in self.add:
            if k not in self._got:
                self._got[k] = np.asarray(self.T[self.swap(k)], dtype=float) + self.add[k]
            return self._got[k]
        return self.T[self.swap(k)]

    def __contains__(self, k):
        return self.swap(k) in self.T

    def get(self, k, d=None):
        return self.T.get(self.swap(k), d)

    def keys(self):
        return self.T.keys()


def view_proxy(ch, view):
    """A copy of the character that draws itself as seen from `view` (see ViewState.proxy)."""
    data = ch.view_data("side" if view.startswith("side") else view)
    if data is None:
        raise ValueError(f"{ch.name} has no {view} view")
    p = copy.copy(ch)
    p.view = None
    opts = {}
    for k, v in data.items():
        if k in VIEW_OPTIONS:
            opts[k] = v
        elif k in PROXY_METHODS:
            setattr(p, k, getattr(p, v) if isinstance(v, str) else v)
        else:
            setattr(p, k, v)
    p.view_options = opts
    turn = float(opts.get("arm_turn", 0.0))
    if (view == "side-" or turn) and getattr(ch, "T", None) is not None:      # (no clip yet: the drawings alone)
        p.T = ViewT(ch.T, swap=view == "side-", add={"arm.R.sh": turn, "arm.L.sh": turn})
    return p


VIEW_ANCHORS = ("eye", "eye_size", "lid", "brow", "mouth", "nose", "cheek", "ear_pivot", "tuft_pivot", "shoulder", "hip", "foot", "tail",
                "dirs", "view_sides")
BOTH_SIDES = ("ear_pivot", "shoulder", "hip", "foot")


def view_problems(ch):
    """What is wrong with a mascot's drawn views (Character.view_data), as sentences."""
    out = []
    for name in ("side", "back"):
        try:
            d = ch.view_data(name)
        except Exception as e:  # noqa: BLE001 - reported as a problem
            out.append(f"{name} view: view_data raised {type(e).__name__}: {e}")
            continue
        if d is None:
            continue
        if not isinstance(d, dict):
            out.append(f"{name} view: view_data must return a dict or None")
            continue
        for k, v in d.items():
            if k in PROXY_METHODS:
                if isinstance(v, str) and not callable(getattr(ch, v, None)):
                    out.append(f"{name} view: {k} names {v!r}, which is not a method of {type(ch).__name__}")
            elif k not in VIEW_OPTIONS and k not in VIEW_ANCHORS:
                out.append(f"{name} view: unknown key {k!r}")
        for k in BOTH_SIDES:
            if k in d and not (isinstance(d[k], dict) and "R" in d[k] and "L" in d[k]):
                out.append(f"{name} view: {k} must give both sides ('R' and 'L'): nothing is mirrored in a drawn view")
        dirs = d.get("dirs", {"R": 1.0, "L": -1.0})
        if set(dirs) != {"R", "L"} or any(abs(abs(float(v)) - 1.0) > 1e-9 for v in dirs.values()):
            out.append(f"{name} view: dirs must be {{'R': +1 or -1, 'L': +1 or -1}}")
        if not set(d.get("view_sides", ())) <= {"R", "L"}:
            out.append(f"{name} view: view_sides lists 'R' and / or 'L'")
        for k, v in (d.get("squash") or {}).items():
            if k not in ("brows", "eyes", "face") or not 0.0 < float(v) <= 1.5:
                out.append(f"{name} view: squash {k!r} must be one of brows, eyes, face with a scale in (0, 1.5]")
        if d.get("tail_slot", 0) not in (0, 1, 2):
            out.append(f"{name} view: tail_slot is 0 (behind the body), 1 (in the lap) or 2 (in front of the feet)")
        if d.get("arms_behind", "far") not in ("far", "both", "none"):
            out.append(f"{name} view: arms_behind is 'far', 'both' or 'none'")
    return out


def squashed(g, k, hints):
    """A feature narrowed to k of its width about its own centre (an eye or a mouth seen from the side)."""
    P = tree_points(g["it"][:-1], matrix(g["it"][-1]))
    if not len(P):
        return g
    c = anchor_of(g, P, hints)
    return gr(f"{g.get('nm', 'group')} view", [g], a=c, p=c, s=(100.0 * k, 100.0))


def _jx(S, p, th, h=1.0):
    """How much the surface rule stretches x at point p, per frame."""
    I = S.info([(p[0] - h, p[1]), (p[0] + h, p[1])])
    X = S.surface_x(I, th)
    return (X[1] - X[0]) / (2.0 * h)


# ------------------------------------------------------------------ turning a drawing (Lottie shape items)
class Warp:
    """Turns the shape items of one layer by a part's surface, frame by frame.

    S   : the part's Surface;  th : the angle per frame (radians);  n : frames;  roll : the loop roll the items were
    written under (their animated values are read back at the right frames)."""

    def __init__(self, S, th, n, roll=0, hints=None):
        self.S, self.th, self.n, self.roll = S, np.asarray(th, dtype=float), n, int(roll)
        self.still = bool(np.all(np.abs(self.th - self.th[0]) < 1e-12))
        self.hints = hints or {}

    # ---- time
    def file_frame(self, f):
        """Frame of the written file that shows frame f of the clip (the loop may have been turned)."""
        L = self.n - 1
        return (f - self.roll) % L if (self.roll and L > 0) else f

    def frames(self):
        return [0] if self.still else list(range(self.n))

    def values(self, vals, kind, tol=None):
        """Per-frame values -> an animated property (or a constant one when the turn is held)."""
        if self.still:
            return vals[0]
        return Anim(vals, tol=tol)

    # ---- items
    def items(self, items, outline=None, M=np.eye(3), mode=None):
        """outline: name of the group holding the part's outline: it and everything drawn behind it follow the
        silhouette; mode forces a rule for everything ('outline')."""
        out = []
        if mode == "back":
            for it in items:
                ty = it.get("ty")
                out.append(self.group(it, M, "back") if ty == "gr" else (self.geometry(it, M, "back") if ty in GEOMETRY else it))
            return out
        behind = mode == "outline"
        for it in items:
            ty = it.get("ty")
            if ty == "gr":
                if behind or (outline is not None and it.get("nm") == outline):
                    out.append(self.group(it, M, "outline"))
                    behind = True if outline is not None else behind
                else:
                    out.extend(self.feature_or_surface(it, M))
            elif ty in GEOMETRY:
                out.append(self.geometry(it, M, "outline" if behind else "surface"))
            else:
                out.append(it)
        return out

    def size_of(self, P):
        if not len(P):
            return 0.0, 0.0
        return float(P[:, 0].max() - P[:, 0].min()), float(P[:, 1].max() - P[:, 1].min())

    def feature_or_surface(self, g, M):
        tr_ = g["it"][-1]
        G = M @ matrix(tr_)
        P = tree_points(g["it"][:-1], G)
        if not len(P):
            return [g]
        w, h = self.size_of(P)
        moving = any(animated(tr_[k]) for k in ("p", "a", "s", "r"))
        if moving or (w <= COMPACT * self.S.width and h <= COMPACT_H * self.S.height):
            return [self.rigid(g, M, P)]
        return [self.group(g, M, "surface")]

    def rigid(self, g, M, P):
        """A small group (an eye, the nose, a shine) moves, narrows and fades as one piece."""
        S = self.S
        c = anchor_of(g, P, self.hints)
        I = S.info([c])
        th = self.th
        mode = "outline" if I["rho"][0] >= OUTLINE_AT else "surface"
        x0, x1 = float(P[:, 0].min()), float(P[:, 0].max())
        if x1 - x0 < 1.0:
            x0, x1 = c[0] - 0.5, c[0] + 0.5
        l, r = S.span((x0, c[1]), (x1, c[1]), th, mode)
        jx = np.clip((r - l) / (x1 - x0), 0.15, 1.3)
        x = l + (c[0] - x0) * jx
        vis = np.ones(self.n) if mode == "outline" else S.visible(I, th)[0]
        inv = np.linalg.inv(M)
        a = apply(inv, [c])[0]
        pos = [tuple(apply(inv, [(x[f], c[1])])[0]) for f in range(self.n)]
        kw = dict(a=tuple(a), p=self.values(pos, "pos", 0.3), s=self.values([(100.0 * j, 100.0) for j in jx], "scale", 0.4))
        if float(vis.min()) < 0.999:
            kw["o"] = self.values([100.0 * v for v in vis], "opacity", 1.0)
        return gr(f"{g.get('nm', 'group')} view", [g], **kw)

    def group(self, g, M, mode):
        """A big group: its items move point by point (mode 'surface' or 'outline')."""
        tr_ = g["it"][-1]
        if any(animated(tr_[k]) for k in ("p", "a", "s", "r")):
            P = tree_points(g["it"][:-1], M @ matrix(tr_))
            return self.rigid(g, M, P) if len(P) else g
        G = M @ matrix(tr_)
        if abs(np.linalg.det(G[:2, :2])) < 1e-9:
            return g
        body = g["it"][:-1]
        if mode in ("outline", "back"):
            new = self.items(body, M=G, mode=mode)
        else:
            new = []
            for it in body:
                if it.get("ty") == "gr":
                    new.extend(self.feature_or_surface(it, G))
                elif it.get("ty") in GEOMETRY:
                    new.append(self.geometry(it, G, "surface"))
                else:
                    new.append(it)
            if is_leaf(g):
                split = self.split(g, new, body, G)
                if split is not None:
                    new = split
        out = dict(g)
        out["it"] = new + [tr_]
        return out

    def split(self, g, new, body, G):
        """A leaf group whose pieces fade at different times (the far blush, whiskers on the far cheek) becomes one
        group per piece, each with its own copy of the fill or stroke and its own fade."""
        S = self.S
        geo = [q for q, it in enumerate(body) if it.get("ty") in GEOMETRY]
        if not geo:
            return None
        style = [it for it in new if it.get("ty") not in GEOMETRY]
        fades = []
        for q in geo:
            P = apply(G, geometry_points(body[q]))
            if not len(P):
                fades.append(None)
                continue
            if float(S.rho(P[:, 0], P[:, 1]).max()) > 1.02:          # part of the silhouette (a bump on the outline): stays
                fades.append(None)
                continue
            c = P.mean(axis=0)
            vis = S.visible(S.info([c]), self.th)[0]
            fades.append(vis if float(vis.min()) < 0.995 else None)
        if all(v is None for v in fades):
            return None
        out = []
        for q, vis in zip(geo, fades):
            kw = {} if vis is None else dict(o=self.values([100.0 * v for v in vis], "opacity", 1.0))
            out.append(gr(f"{g.get('nm', 'group')} {len(out)}", [new[q]] + [copy.deepcopy(it) for it in style], **kw))
        return out

    # ---- geometry
    def geometry(self, it, M, mode):
        ty = it["ty"]
        if ty == "sh":
            return self.path(it, M, mode)
        if ty in ("el", "rc"):
            return self.blob(it, M, mode)
        return it

    def _xs(self, P, mode):
        return self.S.map_x(self.S.info(P), self.th, mode)

    def path(self, it, M, mode):
        ks = it["ks"]
        inv = np.linalg.inv(M)
        if animated(ks):
            frames_k = [prop_at(ks, self.file_frame(f)) for f in range(self.n)]
        else:
            frames_k = None
        base = static_value(ks)
        nv = len(base["v"])
        if nv == 0:
            return it

        def triple(k):
            v = np.array(k["v"], dtype=float).reshape(-1, 2)
            return v, v + np.array(k["i"], dtype=float).reshape(-1, 2), v + np.array(k["o"], dtype=float).reshape(-1, 2)

        if frames_k is None:
            v, vi, vo = triple(base)
            P = apply(M, np.vstack([v, vi, vo]))
            X = self._xs(P, mode)                                 # (3 nv, frames)
            paths = []
            for f in self.frames():
                Q = np.column_stack([X[:, f], P[:, 1]])
                Q = apply(inv, Q)
                nv_, ni, no = Q[:nv], Q[nv:2 * nv], Q[2 * nv:]
                paths.append(Path([tuple(p) for p in nv_], [tuple(p) for p in ni - nv_], [tuple(p) for p in no - nv_], base["c"]))
        else:
            paths = []
            for f in range(self.n):
                v, vi, vo = triple(frames_k[f])
                P = apply(M, np.vstack([v, vi, vo]))
                x = self.S.map_x(self.S.info(P), self.th[f:f + 1], mode)[:, 0]
                Q = apply(inv, np.column_stack([x, P[:, 1]]))
                nv_, ni, no = Q[:nv], Q[nv:2 * nv], Q[2 * nv:]
                paths.append(Path([tuple(p) for p in nv_], [tuple(p) for p in ni - nv_], [tuple(p) for p in no - nv_], frames_k[f]["c"]))
        out = dict(it)
        out["ks"] = prop(paths[0] if (self.still and frames_k is None) else Anim(paths), "path")
        return out

    def blob(self, it, M, mode):
        """An ellipse or a rectangle: its centre moves, its width narrows."""
        if animated(it["p"]) or animated(it["s"]):
            return it                                             # (none in the drawings; left as drawn)
        c = np.array(static_value(it["p"]), dtype=float)
        s = np.array(static_value(it["s"]), dtype=float)
        inv = np.linalg.inv(M)
        cw = apply(M, [c])[0]
        ends = apply(M, [(c[0] - s[0] / 2.0, c[1]), (c[0] + s[0] / 2.0, c[1])])
        w0 = float(np.hypot(*(ends[1] - ends[0])))
        l, r = self.S.span(tuple(ends[0]), tuple(ends[1]), self.th, mode)
        jx = np.clip((r - l) / max(abs(ends[1][0] - ends[0][0]), 1e-6), 0.15, 1.3) if w0 > 1e-6 else np.ones(self.n)
        x = (l + r) / 2.0 + (cw[0] - (ends[0][0] + ends[1][0]) / 2.0) * jx
        if mode == "back":                                       # on the back nothing clamps it: the middle goes round with the body
            x = self.S.back_x(self.S.info([cw]), self.th)[0]
        cs = [tuple(apply(inv, [(x[f], cw[1])])[0]) for f in range(self.n)]
        out = dict(it)
        out["p"] = prop(self.values(cs, "pos", 0.3), "pos")
        out["s"] = prop(self.values([(float(s[0]) * float(j), float(s[1])) for j in jx], "size", 0.3), "size")
        return out


def anchor_of(g, P, hints=None):
    """Where a small group is pinned to the surface: a named place (every part of an eye pins to the eye's centre, so
    the lid, the closed-eye arc and the eye move together), else the centre of what it draws."""
    nm = g.get("nm", "")
    if hints:
        if nm in hints:
            return hints[nm]
        if nm.startswith("eye style ") and f"eye {nm[-1]}" in hints:
            return hints[f"eye {nm[-1]}"]
    return (float((P[:, 0].min() + P[:, 0].max()) / 2.0), float((P[:, 1].min() + P[:, 1].max()) / 2.0))


def head_hints(ch):
    """Named anchors of the head's features: the eyes and the brows."""
    out = {}
    for s in "RL":
        e = tuple(map(float, ch.side(ch.eye, s)))
        for nm in ("eye", "lid", "upper lid"):
            out[f"{nm} {s}"] = e
        out[f"brow {s}"] = (e[0], e[1] + float(ch.brow["dy"]))
    return out
