"""Minimal Lottie (Bodymovin 5.7.4) writer with a keyframe fitter.

Everything animated in this project is *sampled* once per frame by the rig and then reduced
here to as few eased keyframes as the tolerance allows.  Only features that every Lottie
player supports are emitted: shape layers, null layers, parenting, groups with transforms,
paths / ellipses / rects, fills, strokes and trim paths.
"""
from __future__ import annotations

import hashlib

import numpy as np

try:  # scipy is optional; without it we fall back to cubic-Hermite + linear segments
    from scipy.optimize import least_squares
except Exception:  # pragma: no cover
    least_squares = None

VERSION = "5.7.4"

# properties with a hard valid range: eased segments must not overshoot their keys (see _fit_ease)
BOUNDED = ("opacity", "pct")

# default tolerances (max abs error in the unit of the property)
TOL = dict(pos=0.3, rot=0.2, scale=0.25, opacity=0.8, path=0.35, size=0.3, pct=0.4, width=0.2, color=0.004)


# --------------------------------------------------------------------------- values
def num(x, nd=2):
    x = round(float(x), nd)
    if x == int(x):
        return int(x)
    return x


def nums(xs, nd=2):
    return [num(x, nd) for x in xs]


class Path:
    """A bezier path: vertices plus in/out tangents (relative to the vertex)."""

    __slots__ = ("v", "i", "o", "c")

    def __init__(self, v, i=None, o=None, closed=True):
        self.v = [tuple(map(float, p)) for p in v]
        n = len(self.v)
        self.i = [tuple(map(float, p)) for p in i] if i is not None else [(0.0, 0.0)] * n
        self.o = [tuple(map(float, p)) for p in o] if o is not None else [(0.0, 0.0)] * n
        self.c = closed

    def flat(self):
        out = []
        for arr in (self.v, self.i, self.o):
            for p in arr:
                out.extend(p)
        return out

    @staticmethod
    def unflat(a, n, closed):
        a = list(a)
        v = [(a[2 * k], a[2 * k + 1]) for k in range(n)]
        i = [(a[2 * n + 2 * k], a[2 * n + 2 * k + 1]) for k in range(n)]
        o = [(a[4 * n + 2 * k], a[4 * n + 2 * k + 1]) for k in range(n)]
        return Path(v, i, o, closed)

    def json(self, nd=1):
        return {
            "c": self.c,
            "v": [nums(p, nd) for p in self.v],
            "i": [nums(p, nd) for p in self.i],
            "o": [nums(p, nd) for p in self.o],
        }

    def moved(self, dx=0.0, dy=0.0):
        return Path([(x + dx, y + dy) for x, y in self.v], self.i, self.o, self.c)

    def mirrored(self, cx):
        """Mirror about the vertical line x = cx (keeps winding by reversing)."""
        v = [(2 * cx - x, y) for x, y in self.v]
        i = [(-x, y) for x, y in self.i]
        o = [(-x, y) for x, y in self.o]
        return Path(v, i, o, self.c)


class Anim:
    """Per-frame samples of one property (index = frame, inclusive of the last frame)."""

    __slots__ = ("s", "hold", "tol")

    def __init__(self, samples, hold=False, tol=None):
        self.s = list(samples)
        self.hold = hold
        self.tol = tol


def is_anim(x):
    return isinstance(x, Anim)


# --------------------------------------------------------------------------- easing fit
_U = np.linspace(0.0, 1.0, 129)
_B1 = 3 * (1 - _U) ** 2 * _U
_B2 = 3 * (1 - _U) * _U ** 2
_B3 = _U ** 3


def ease_eval(c, tau):
    """Lottie / CSS cubic-bezier easing with control points (x1,y1),(x2,y2)."""
    x1, y1, x2, y2 = c
    bx = _B1 * x1 + _B2 * x2 + _B3
    by = _B1 * y1 + _B2 * y2 + _B3
    return np.interp(tau, bx, by)


LINEAR = (0.167, 0.167, 0.833, 0.833)
_STD = [LINEAR, (0.42, 0.0, 0.58, 1.0), (0.333, 0.0, 0.667, 1.0), (0.2, 0.0, 0.2, 1.0), (0.6, 0.0, 0.9, 1.0), (0.3, 0.0, 0.35, 1.45)]

STATS = dict(props=0, keys=0, fits=0, cache=0)
_CACHE = {}


def _fit_ease(tau, p, tolp, mono=False):
    """Find a cubic-bezier easing with max |E(tau) - p| <= tolp.  Returns coeffs or None.

    mono=True keeps y1, y2 inside [0, 1] so the eased value can never leave the range spanned by its two keys.
    That is required for opacity and trim: some players wrap values above 100 % instead of clamping them.
    """
    if np.max(np.abs(tau - p)) <= tolp:
        return LINEAR
    ylo, yhi = (0.0, 1.0) if mono else (-4.0, 5.0)
    inside = lambda c: ylo <= c[1] <= yhi and ylo <= c[3] <= yhi
    err = lambda c: float(np.max(np.abs(ease_eval(c, tau) - p)))
    # cubic Hermite through the end slopes == bezier with x1 = 1/3, x2 = 2/3
    s0 = p[0] / tau[0]
    s1 = (1.0 - p[-1]) / (1.0 - tau[-1])
    cands = [(1 / 3, s0 / 3, 2 / 3, 1 - s1 / 3)] + _STD[1:]
    m = len(tau)
    if m <= 2:
        # one or two samples in between: with x1 = 1/3, x2 = 2/3 the easing is a plain cubic in tau, solve it exactly
        A_ = np.array([[3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2] for t in tau])
        b_ = np.array([q - t ** 3 for t, q in zip(tau, p)])
        if m == 2:
            y1, y2 = np.linalg.solve(A_, b_)
        else:
            sm = b_[0] / A_[0, 0]                      # y1 + y2 at tau = 0.5; keep the pair as close to linear as possible
            y1, y2 = sm / 2 - 1 / 6, sm / 2 + 1 / 6
        cands.insert(0, (1 / 3, float(y1), 2 / 3, float(y2)))
    cands = [c for c in cands if inside(c)]
    best, best_err = None, 1e9
    for c in cands:
        e = err(c)
        if e < best_err:
            best, best_err = c, e
    if best is not None and best_err <= tolp:
        return best
    if best is None:
        best, best_err = (0.333, 0.333, 0.667, 0.667), err((0.333, 0.333, 0.667, 0.667))
    if least_squares is None or best_err > 80 * tolp:  # hopeless, don't burn time
        return None
    STATS["fits"] += 1
    fun = lambda c: ease_eval(c, tau) - p
    lo, hi = np.array([0.02, ylo, 0.02, ylo]), np.array([0.98, yhi, 0.98, yhi])
    x0 = np.clip(best, lo + 1e-3, hi - 1e-3)
    try:
        res = least_squares(fun, x0, bounds=(lo, hi), max_nfev=40, xtol=1e-6, ftol=1e-9)
    except Exception:
        return None
    c = tuple(float(x) for x in res.x)
    return c if err(c) <= tolp else None


def _try_segment(S, i, j, tol, mono=False):
    if j == i + 1:
        return LINEAR
    D = S[j] - S[i]
    seg = S[i + 1 : j]
    K = seg - S[i]
    zero = seg == 0.0                                   # "off" values (hidden, zero size, untrimmed) must stay off
    ztol = min(tol, 0.01)
    scale = float(np.max(np.abs(D)))
    if scale < 1e-9:
        if float(np.max(np.abs(K))) > tol:
            return None
        return LINEAR if (not zero.any() or float(np.max(np.abs(K[zero]))) <= ztol) else None
    den = float(D @ D)
    p = (K @ D) / den
    resid = float(np.max(np.abs(K - np.outer(p, D))))
    if resid > tol:
        return None
    tau = (np.arange(i + 1, j) - i) / float(j - i)
    c = _fit_ease(tau, p, (tol - resid) / scale, mono)
    if c is not None and zero.any():
        pred = S[i] + np.outer(ease_eval(c, tau), D)
        if float(np.max(np.abs(pred[zero]))) > ztol:
            return None
    return c


def fit_keys(S, tol, mono=False):
    """S: (n, d) array of per-frame samples.  Returns list of (frame, ease-or-None).

    Greedy: from each key, look for the longest span that one eased segment reproduces within `tol`.
    Feasibility is not monotone in the span length, so the search keeps probing past a few failures.
    """
    n = len(S)
    keys = []
    i = 0
    while i < n - 1:
        best_j, best_c = i + 1, LINEAR
        fails, first_bad = 0, None
        j = min(i + 2, n - 1)
        while j > best_j:
            c = _try_segment(S, i, j, tol, mono)
            if c is not None:
                best_j, best_c, fails, first_bad = j, c, 0, None
            else:
                fails += 1
                if first_bad is None:
                    first_bad = j
                if fails >= 3:
                    break
            if j == n - 1:
                break
            j = min(n - 1, max(j + 1, i + int(round((j - i) * 1.45))))
        if first_bad is not None and first_bad > best_j + 1:
            lo, hi = best_j, first_bad
            while hi - lo > 1:
                mid = (lo + hi) // 2
                c = _try_segment(S, i, mid, tol, mono)
                if c is None:
                    hi = mid
                else:
                    lo, best_j, best_c = mid, mid, c
        keys.append((i, best_c))
        i = best_j
    keys.append((n - 1, None))
    return keys


def _ease_json(c, arr):
    x1, y1, x2, y2 = (num(v, 3) for v in c)
    if arr:
        return {"o": {"x": [x1], "y": [y1]}, "i": {"x": [x2], "y": [y2]}}
    return {"o": {"x": x1, "y": y1}, "i": {"x": x2, "y": y2}}


def prop(value, kind="pos", nd=None, tol=None, wrap=None):
    """Build a Lottie animatable property.

    value : constant, or Anim of per-frame samples.  kind selects tolerance and formatting:
      'pos' [x,y] -> [x,y,0] for layers (wrap='layer') ; 'scale' [sx,sy] in percent ; 'rot' ; 'opacity' ;
      'path' (Path) ; 'size' [w,h] ; 'pct' ; 'width' ; 'color' [r,g,b] (0..1)
    """
    if nd is None:
        nd = {"path": 1, "pos": 2, "rot": 2, "scale": 2, "opacity": 1, "size": 2, "pct": 2, "width": 2, "color": 4}[kind]

    def fmt(v):
        if kind == "path":
            return v.json(nd)
        if kind in ("rot", "opacity", "pct", "width"):
            return num(v, nd)
        if kind == "color":
            return nums(v, nd) + [1]
        out = nums(v, nd)
        if wrap == "layer":
            out = out + ([0] if kind == "pos" else [100])
        return out

    if not is_anim(value):
        return {"a": 0, "k": fmt(value)}

    samples = value.s
    scalar = kind in ("rot", "opacity", "pct", "width")
    if kind == "path":
        nv, closed = len(samples[0].v), samples[0].c
        S = np.array([q.flat() for q in samples], dtype=float)
        back = lambda row: Path.unflat(row, nv, closed)
    elif scalar:
        S = np.array(samples, dtype=float).reshape(-1, 1)
        back = lambda row: float(row[0])
    else:
        S = np.array(samples, dtype=float)
        back = lambda row: list(row)

    t = tol if tol is not None else (value.tol if value.tol is not None else TOL[kind])
    if float(np.max(np.abs(S - S[0]))) <= (1e-9 if value.hold else t * 0.5):
        return {"a": 0, "k": fmt(back(S[0]))}

    STATS["props"] += 1
    wrapk = (lambda v: [v]) if (scalar or kind == "path") else (lambda v: v)
    if value.hold:
        ks = []
        for f in range(len(S)):
            if f == 0 or float(np.max(np.abs(S[f] - S[f - 1]))) > 1e-9:
                ks.append({"t": f, "s": wrapk(fmt(back(S[f]))), "h": 1})
        STATS["keys"] += len(ks)
        return {"a": 1, "k": ks}

    hkey = hashlib.blake2b(S.tobytes() + repr((kind, t, nd, wrap)).encode(), digest_size=12).digest()
    if hkey in _CACHE:
        STATS["cache"] += 1
        return _CACHE[hkey]
    keys = fit_keys(S, t, mono=kind in BOUNDED)
    ks = []
    for f, c in keys:
        k = {"t": f, "s": wrapk(fmt(back(S[f])))}
        if c is not None:
            k.update(_ease_json(c, arr=(kind != "path")))
        ks.append(k)
    STATS["keys"] += len(ks)
    out = {"a": 1, "k": ks}
    _CACHE[hkey] = out
    return out


# --------------------------------------------------------------------------- shapes
def rgb(hexstr):
    h = hexstr.lstrip("#")
    return [int(h[k : k + 2], 16) / 255.0 for k in (0, 2, 4)]


def sh(path, nm=None):
    d = {"ty": "sh", "ks": prop(path, "path")}
    if nm:
        d["nm"] = nm
    return d


def el(p, s, nm=None):
    d = {"ty": "el", "d": 1, "p": prop(p, "pos"), "s": prop(s, "size")}
    if nm:
        d["nm"] = nm
    return d


def rc(p, s, r=0, nm=None):
    d = {"ty": "rc", "d": 1, "p": prop(p, "pos"), "s": prop(s, "size"), "r": prop(r, "width")}
    if nm:
        d["nm"] = nm
    return d


def fl(color, o=100):
    return {"ty": "fl", "c": prop(color, "color"), "o": prop(o, "opacity"), "r": 1}


def st(color, w, o=100, cap=2, join=2):
    return {"ty": "st", "c": prop(color, "color"), "o": prop(o, "opacity"), "w": prop(w, "width"), "lc": cap, "lj": join, "ml": 4}


def tm(s=0, e=100, o=0):
    return {"ty": "tm", "s": prop(s, "pct"), "e": prop(e, "pct"), "o": prop(o, "rot"), "m": 1}


def tr(p=(0, 0), a=(0, 0), s=(100, 100), r=0, o=100):
    return {
        "ty": "tr",
        "p": prop(p, "pos"),
        "a": prop(a, "pos"),
        "s": prop(s, "scale"),
        "r": prop(r, "rot"),
        "o": prop(o, "opacity"),
        "sk": {"a": 0, "k": 0},
        "sa": {"a": 0, "k": 0},
    }


def gr(nm, items, **xf):
    """Group.  items are drawn top-first (Lottie order); transform kwargs: p, a, s, r, o."""
    return {"ty": "gr", "nm": nm, "it": list(items) + [tr(**xf)]}


# --------------------------------------------------------------------------- layers
class Layer:
    def __init__(self, nm, shapes=None, parent=None, p=(0, 0), a=(0, 0), s=(100, 100), r=0, o=100, null=False):
        self.nm = nm
        self.shapes = shapes or []
        self.parent = parent
        self.p, self.a, self.s, self.r, self.o = p, a, s, r, o
        self.null = null

    def json(self, ind, index_of, op):
        d = {
            "ddd": 0,
            "ind": ind,
            "ty": 3 if self.null else 4,
            "nm": self.nm,
            "sr": 1,
            "ks": {
                "o": prop(self.o, "opacity"),
                "r": prop(self.r, "rot"),
                "p": prop(self.p, "pos", wrap="layer"),
                "a": prop(self.a, "pos", wrap="layer"),
                "s": prop(self.s, "scale", wrap="layer"),
            },
            "ao": 0,
            "ip": 0,
            "op": op,
            "st": 0,
            "bm": 0,
        }
        if not self.null:
            d["shapes"] = self.shapes
        if self.parent is not None:
            d["parent"] = index_of[self.parent]
        return d


def document(name, layers, op, w=512, h=512, fr=60):
    """layers: list of Layer, top-most first."""
    names = [L.nm for L in layers]
    dup = {n for n in names if names.count(n) > 1}
    if dup:
        raise ValueError(f"duplicate layer names: {sorted(dup)}")
    n = len(layers)
    index_of = {L.nm: n - k for k, L in enumerate(layers)}  # bottom layer gets ind 1, like the originals
    for L in layers:
        if L.parent is not None and L.parent not in index_of:
            raise ValueError(f"layer {L.nm!r} has unknown parent {L.parent!r}")
    return {
        "v": VERSION,
        "fr": fr,
        "ip": 0,
        "op": op,
        "w": w,
        "h": h,
        "nm": name,
        "ddd": 0,
        "assets": [],
        "layers": [L.json(index_of[L.nm], index_of, op) for L in layers],
    }
