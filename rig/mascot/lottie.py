"""Minimal Lottie (Bodymovin 5.7.4) writer with a keyframe fitter.

Everything animated in this project is *sampled* once per frame by the rig and then reduced
here to as few eased keyframes as the tolerance allows.  Only features that every Lottie
player supports are emitted: shape layers, null layers, parenting, groups with transforms,
paths / ellipses / rects, fills, strokes and trim paths.

Two switches change how samples become keyframes (both are off unless a caller turns them on):

  rolled(k)      every looping property starts k frames into its loop.  The sticker studio uses it so that
                 frame 0 of a loop is the frame worth showing as a still.
  fade_safe      a layer that fades is written with its opacity on a group inside the layer instead of on the
                 layer itself.  rlottie (Telegram's player, and the rasteriser used for PNG / WebP / GIF export)
                 blends a layer with fractional opacity through an off-screen surface, and that blend darkens
                 everything already drawn by one level out of 255 for each such layer.
"""
from __future__ import annotations

import hashlib
import math

import numpy as np

VERSION = "5.7.4"

# properties with a hard valid range: eased segments must not overshoot their keys (see _fit_ease)
BOUNDED = ("opacity", "pct")

# default tolerances (max abs error in the unit of the property)
TOL = dict(pos=0.3, rot=0.2, scale=0.25, opacity=0.8, path=0.35, size=0.3, pct=0.4, width=0.2, color=0.004)
# The fitter looks for the smallest PEAK error, so its curves use a tolerance to the full.  Fitting to this share
# of each tolerance keeps the pictures as close to the per-frame samples as they were with the old optimiser.
FIT_MARGIN = 0.65


# --------------------------------------------------------------------------- values
def num(x, nd=2):
    x = float(x)
    if not math.isfinite(x):
        raise ValueError(f"a Lottie value is {x}; every number written to a file must be finite")
    x = round(x, nd)
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


# --------------------------------------------------------------------------- loop rotation
_ROLL = 0


class rolled:
    """Context manager: every Anim turned into keyframes inside the block starts `k` frames into its loop.

        with rolled(36):
            doc = character.build(clip)      # frame 0 of doc is frame 36 of the clip; the loop is otherwise the same

    Only meaningful for looping animation (first sample == last sample).  A Layer remembers the roll that was in
    effect when it was made, so layers made under different rolls can share a document: the studio gives a
    decoration that does not follow the mascot (z's, sparkles, a chart drawing itself) its own roll, which puts the
    moment it is most complete on the frame used as the still."""

    def __init__(self, k):
        self.k = int(k)

    def __enter__(self):
        global _ROLL
        self.prev, _ROLL = _ROLL, self.k
        return self

    def __exit__(self, *exc):
        global _ROLL
        _ROLL = self.prev
        return False


def current_roll():
    return _ROLL


def _same(a, b):
    """Two samples of one property are equal (numbers, tuples of numbers or Paths)."""
    if isinstance(a, Path):
        return a.c == b.c and len(a.v) == len(b.v) and np.allclose(a.flat(), b.flat(), atol=1e-6)
    return bool(np.allclose(np.asarray(a, dtype=float), np.asarray(b, dtype=float), atol=1e-6))


def _roll(samples, k):
    """Rotate per-frame samples of a loop (index = frame, last == first) so they start at frame k."""
    n = len(samples) - 1
    if n <= 0 or k % n == 0:
        return samples
    k %= n
    body = list(samples[:n])
    out = body[k:] + body[:k]
    out.append(out[0])
    return out


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

# The easing of one segment has four numbers.  With the two x-handles fixed, the eased value is LINEAR in the two
# y-handles, so the best y-handles are a 2 x 2 solve.  The fitter therefore tries a grid of x-handle pairs at once
# (plain array arithmetic), keeps the pair with the smallest peak error and polishes around it.  This replaced a
# general-purpose optimiser that took over 95 % of the time of every build and found the same curves.
_GX = tuple(np.linspace(0.02, 0.98, 15))
_PAIRS = np.array([(a, b) for a in _GX for b in _GX])
_NT = 1024
LAWSON_WITHIN = 3.0          # reweight towards the peaks when the least-squares peak error is within this many tolerances
POLISH_WITHIN = 1.7          # then search between the grid points when it is within this many


def _bernstein(u):
    return 3 * (1 - u) ** 2 * u, 3 * (1 - u) * u ** 2, u ** 3


def _tabulate(pairs):
    """Weights of y1 and y2 and the constant term of the eased value, over a fine grid of tau, per x-handle pair."""
    uu = np.linspace(0.0, 1.0, 513)
    b1, b2, b3 = _bernstein(uu)
    tt = np.linspace(0.0, 1.0, _NT + 1)
    A = np.empty((len(pairs), _NT + 1))
    B, C = np.empty_like(A), np.empty_like(A)
    for g, (x1, x2) in enumerate(pairs):
        A[g], B[g], C[g] = _bernstein(np.interp(tt, b1 * x1 + b2 * x2 + b3, uu))
    return A, B, C


_TA, _TB, _TC = _tabulate(_PAIRS)


def _solve_y(A, B, R, lo, hi, W=None):
    """Least-squares y-handles for every row (rows = x-handle pairs), kept inside [lo, hi]."""
    WA, WB = (A, B) if W is None else (W * A, W * B)
    saa, sab, sbb = (WA * A).sum(1), (WA * B).sum(1), (WB * B).sum(1)
    ra, rb = (WA * R).sum(1), (WB * R).sum(1)
    det = saa * sbb - sab * sab
    det = np.where(np.abs(det) < 1e-14, 1e-14, det)
    return _inside(ra, rb, saa, sab, sbb, (ra * sbb - rb * sab) / det, (rb * saa - ra * sab) / det, lo, hi)


def _inside(ra, rb, saa, sab, sbb, y1, y2, lo, hi):
    """Keep both handles inside [lo, hi]; a handle that hit its limit changes the best value of the other one."""
    if float(y1.min()) >= lo and float(y1.max()) <= hi and float(y2.min()) >= lo and float(y2.max()) <= hi:
        return y1, y2
    c1, c2 = np.clip(y1, lo, hi), np.clip(y2, lo, hi)
    n2 = np.where(c1 != y1, (rb - sab * c1) / np.maximum(sbb, 1e-14), y2)
    n1 = np.where(c2 != y2, (ra - sab * c2) / np.maximum(saa, 1e-14), y1)
    return np.clip(n1, lo, hi), np.clip(n2, lo, hi)


def _minimax(A, B, R, lo, hi, rounds, y1=None, y2=None):
    """Per row: y-handles with a small PEAK error (least squares, then Lawson's reweighting towards the peaks).
    Returns (peak error, y1, y2) arrays."""
    if y1 is None:
        y1, y2 = _solve_y(A, B, R, lo, hi)
    E = np.abs(A * y1[:, None] + B * y2[:, None] - R)
    best = (E.max(1), y1, y2)
    W = np.ones_like(E)
    for _ in range(rounds):
        W = W * (E + 1e-12)
        W = W / W.sum(1, keepdims=True)
        y1, y2 = _solve_y(A, B, R, lo, hi, W)
        E = np.abs(A * y1[:, None] + B * y2[:, None] - R)
        e = E.max(1)
        better = e < best[0]
        best = (np.where(better, e, best[0]), np.where(better, y1, best[1]), np.where(better, y2, best[2]))
    return best


class _Span:
    """Everything about a span of n frames that does not depend on the samples: the tables of the grid at the
    span's own tau values and the solved normal equations.  Spans of the same length come up again and again."""

    __slots__ = ("tau", "A", "B", "C", "saa", "sab", "sbb", "i11", "i12", "i22", "ac", "bc", "SA", "SB", "SC")

    def __init__(self, n):
        self.tau = tau = np.arange(1, n) / float(n)
        pos = tau * _NT
        i0 = np.minimum(pos.astype(np.intp), _NT - 1)
        w = pos - i0
        self.A = A = _TA[:, i0] * (1 - w) + _TA[:, i0 + 1] * w
        self.B = B = _TB[:, i0] * (1 - w) + _TB[:, i0 + 1] * w
        self.C = C = _TC[:, i0] * (1 - w) + _TC[:, i0 + 1] * w
        self.saa, self.sab, self.sbb = saa, sab, sbb = (A * A).sum(1), (A * B).sum(1), (B * B).sum(1)
        det = saa * sbb - sab * sab
        det = np.where(np.abs(det) < 1e-14, 1e-14, det)
        self.i11, self.i12, self.i22 = sbb / det, -sab / det, saa / det
        self.ac, self.bc = (A * C).sum(1), (B * C).sum(1)
        self.SA = np.empty((len(_SX), n - 1))                 # the same tables for the standard candidates
        self.SB, self.SC = np.empty_like(self.SA), np.empty_like(self.SA)
        for g, (x1, x2) in enumerate(_SX):
            self.SA[g], self.SB[g], self.SC[g] = _bernstein(np.interp(tau, _B1 * x1 + _B2 * x2 + _B3, _U))


_SPANS = {}
_SPAN_BUDGET = 6_000_000        # numbers kept in span tables (about 50 MB); the least recently made are dropped beyond it
_span_load = 0


def _span(n):
    global _span_load
    sp = _SPANS.get(n)
    if sp is None:
        if _span_load > _SPAN_BUDGET:
            _SPANS.clear()
            _span_load = 0
        sp = _SPANS[n] = _Span(n)
        _span_load += 3 * sp.A.size
    return sp


def _grid_fit(sp, p, tolp, lo, hi):
    """Best easing on the grid of x-handle pairs for the samples p of a span: ((x1, y1, x2, y2), peak error)."""
    A, B = sp.A, sp.B
    R = p - sp.C
    ra, rb = A @ p - sp.ac, B @ p - sp.bc
    y1, y2 = _inside(ra, rb, sp.saa, sp.sab, sp.sbb, sp.i11 * ra + sp.i12 * rb, sp.i12 * ra + sp.i22 * rb, lo, hi)
    err = np.abs(A * y1[:, None] + B * y2[:, None] - R).max(1)
    g = int(np.argmin(err))
    if tolp < err[g] <= LAWSON_WITHIN * tolp:             # close: a least-squares fit is not the smallest-peak fit
        top = np.argpartition(err, 12)[:12]
        e2, a2, b2 = _minimax(A[top], B[top], R[top], lo, hi, 4, y1[top], y2[top])
        k = int(np.argmin(e2))
        if e2[k] < err[g]:
            return (float(_PAIRS[top[k], 0]), float(a2[k]), float(_PAIRS[top[k], 1]), float(b2[k])), float(e2[k])
    return (float(_PAIRS[g, 0]), float(y1[g]), float(_PAIRS[g, 1]), float(y2[g])), float(err[g])


def _polish(tau, p, c, e, tolp, lo, hi):
    """Pattern search on the x-handles between the grid points (the y-handles are re-solved at every probe)."""
    x1, x2 = c[0], c[2]
    best, best_e = c, e
    for step in (0.03, 0.012, 0.005):
        cand = [(min(0.99, max(0.01, x1 + dx)), min(0.99, max(0.01, x2 + dy)))
                for dx in (-step, 0.0, step) for dy in (-step, 0.0, step) if dx or dy]
        A = np.empty((len(cand), len(tau)))
        B, C = np.empty_like(A), np.empty_like(A)
        for g, (a, b) in enumerate(cand):
            A[g], B[g], C[g] = _bernstein(np.interp(tau, _B1 * a + _B2 * b + _B3, _U))
        err, y1, y2 = _minimax(A, B, p - C, lo, hi, 3)
        g = int(np.argmin(err))
        if err[g] < best_e:
            best, best_e = (cand[g][0], float(y1[g]), cand[g][1], float(y2[g])), float(err[g])
            x1, x2 = cand[g]
            if best_e <= tolp:
                break
    return best, best_e


# standard candidates tried before the grid: the cubic through the end slopes (x-handles 1/3 and 2/3), then the
# easings clips are usually keyed with
_SX = ((1 / 3, 2 / 3),) + tuple((c[0], c[2]) for c in _STD[1:])
_SY1 = np.array([0.0] + [c[1] for c in _STD[1:]])
_SY2 = np.array([0.0] + [c[3] for c in _STD[1:]])


def _fit_ease(tau, p, tolp, mono=False):
    """Find a cubic-bezier easing with max |E(tau) - p| <= tolp.  Returns coeffs or None.
    tau must be the evenly spaced times 1/n .. (n-1)/n of a span of n frames.

    mono=True keeps y1, y2 inside [0, 1] so the eased value can never leave the range spanned by its two keys.
    That is required for opacity and trim: some players wrap values above 100 % instead of clamping them.
    """
    if np.max(np.abs(tau - p)) <= tolp:
        return LINEAR
    ylo, yhi = (0.0, 1.0) if mono else (-4.0, 5.0)
    m = len(tau)
    sp = _span(m + 1)
    err = lambda c: float(np.max(np.abs(ease_eval(c, tau) - p)))
    if m <= 2:
        # one or two samples in between: with x1 = 1/3, x2 = 2/3 the easing is a plain cubic in tau, solve it exactly
        A_ = np.array([[3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2] for t in tau])
        b_ = np.array([q - t ** 3 for t, q in zip(tau, p)])
        if m == 2:
            y1, y2 = np.linalg.solve(A_, b_)
        else:
            sm = b_[0] / A_[0, 0]                      # y1 + y2 at tau = 0.5; keep the pair as close to linear as possible
            y1, y2 = sm / 2 - 1 / 6, sm / 2 + 1 / 6
        if ylo <= y1 <= yhi and ylo <= y2 <= yhi:
            c = (1 / 3, float(y1), 2 / 3, float(y2))
            if err(c) <= tolp:
                return c
    # cubic Hermite through the end slopes == bezier with x1 = 1/3, x2 = 2/3
    y1s, y2s = _SY1.copy(), _SY2.copy()
    y1s[0], y2s[0] = (p[0] / tau[0]) / 3.0, 1.0 - ((1.0 - p[-1]) / (1.0 - tau[-1])) / 3.0
    e = np.abs(sp.SA * y1s[:, None] + sp.SB * y2s[:, None] + sp.SC - p).max(1)
    if not (ylo <= y1s[0] <= yhi and ylo <= y2s[0] <= yhi):
        e[0] = 1e9
    if mono:
        e[-1] = 1e9                                    # the overshooting 'back' easing leaves the range of its keys
    g = int(np.argmin(e))
    if e[g] <= tolp:
        c = (_SX[g][0], float(y1s[g]), _SX[g][1], float(y2s[g]))
        if err(c) <= tolp:
            return c
    if e[g] > 80 * tolp:                               # hopeless, don't burn time
        return None
    STATS["fits"] += 1
    c, e = _grid_fit(sp, p, tolp, ylo, yhi)
    if e > POLISH_WITHIN * tolp:
        return None
    if e > tolp:
        STATS["polish"] = STATS.get("polish", 0) + 1
        c, e = _polish(tau, p, c, e, tolp, ylo, yhi)
        if e > tolp:
            return None
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

    samples, cut = value.s, None
    if _ROLL and len(samples) > 2:
        n_ = len(samples) - 1
        k_ = _ROLL % n_
        if k_:
            if not _same(samples[0], samples[-1]):
                # this property jumps at the loop point (a ray that turns by exactly one ray per loop).  Once the loop
                # is turned that jump lands inside the timeline, where it must stay a jump: a hold key, not a blend.
                cut = n_ - k_
            samples = _roll(samples, k_)
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

    if not np.isfinite(S).all():
        bad = int(np.argwhere(~np.isfinite(S).reshape(len(S), -1).all(axis=1))[0][0])
        raise ValueError(f"an animated {kind} is not a finite number at frame {bad}")
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

    hkey = hashlib.blake2b(S.tobytes() + repr((kind, t, nd, wrap, cut)).encode(), digest_size=12).digest()
    if hkey in _CACHE:
        STATS["cache"] += 1
        return _CACHE[hkey]
    if cut is None:
        keys = fit_keys(S, t * FIT_MARGIN, mono=kind in BOUNDED)
    else:
        # two runs: up to the frame before the jump (held there), then from the jump on
        a_ = fit_keys(S[:cut], t * FIT_MARGIN, mono=kind in BOUNDED) if cut > 1 else [(0, None)]
        b_ = fit_keys(S[cut:], t * FIT_MARGIN, mono=kind in BOUNDED) if len(S) - cut > 1 else [(0, None)]
        keys = a_[:-1] + [(a_[-1][0], "hold")] + [(f + cut, c) for f, c in b_]
    ks = []
    for f, c in keys:
        k = {"t": f, "s": wrapk(fmt(back(S[f])))}
        if c == "hold":
            k["h"] = 1
        elif c is not None:
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
def _fades(o):
    """True when an opacity is ever strictly between hidden and solid."""
    if is_anim(o):
        return any(0.0 < float(v) < 100.0 for v in o.s)
    return 0.0 < float(o) < 100.0


class Layer:
    def __init__(self, nm, shapes=None, parent=None, p=(0, 0), a=(0, 0), s=(100, 100), r=0, o=100, null=False):
        self.nm = nm
        self.shapes = shapes or []
        self.parent = parent
        self.p, self.a, self.s, self.r, self.o = p, a, s, r, o
        self.null = null
        self.roll = _ROLL            # see rolled(): the layer's own transform keys use the roll it was made under

    def json(self, ind, index_of, op, fade_safe=False):
        with rolled(self.roll):
            shapes, o = self.shapes, self.o
            if fade_safe and not self.null and shapes and _fades(o):
                # the fade goes on a group, not on the layer (see the module docstring)
                shapes, o = [gr("fade", shapes, o=o)], 100
            d = {
                "ddd": 0,
                "ind": ind,
                "ty": 3 if self.null else 4,
                "nm": self.nm,
                "sr": 1,
                "ks": {
                    "o": prop(o, "opacity"),
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
            d["shapes"] = shapes
        if self.parent is not None:
            d["parent"] = index_of[self.parent]
        return d


def document(name, layers, op, w=512, h=512, fr=60, fade_safe=False):
    """layers: list of Layer, top-most first.  fade_safe: see the module docstring."""
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
        "layers": [L.json(index_of[L.nm], index_of, op, fade_safe) for L in layers],
    }
