"""Small 2D helpers: vectors, smooth paths through points, FK chains."""
from __future__ import annotations

import math

from .lottie import Path


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def mul(a, k):
    return (a[0] * k, a[1] * k)


def length(a):
    return math.hypot(a[0], a[1])


def norm(a):
    L = length(a)
    return (a[0] / L, a[1] / L) if L > 1e-9 else (0.0, 0.0)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp2(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def rot(p, deg, about=(0.0, 0.0)):
    """Rotate p clockwise on screen (same sense as Lottie's rotation) by deg about a point."""
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    x, y = p[0] - about[0], p[1] - about[1]
    return (about[0] + x * c - y * s, about[1] + x * s + y * c)


def heading(deg, L=1.0):
    """Unit vector for a limb angle: 0 = straight down, +90 = towards +x (screen right), 180 = up."""
    r = math.radians(deg)
    return (math.sin(r) * L, math.cos(r) * L)


def smooth(points, closed=True, tension=0.36, sharp=None, ends=None):
    """Bezier path through `points` with chord-proportional (Catmull-Rom like) tangents.

    sharp : dict {index: factor}  -- 0 makes a hard corner, 0.5 a tight curve, 1 = fully smooth (default)
    """
    n = len(points)
    sharp = sharp or {}
    vi, vo = [], []
    for k in range(n):
        p = points[k]
        if closed:
            a, b = points[(k - 1) % n], points[(k + 1) % n]
        else:
            a = points[k - 1] if k > 0 else None
            b = points[k + 1] if k < n - 1 else None
        if a is None or b is None:
            # open end: aim at the neighbour
            q = b if a is None else a
            d = norm(sub(q, p))
            L = length(sub(q, p)) * tension * 0.6
            if a is None:
                vi.append((0.0, 0.0)); vo.append(mul(d, L))
            else:
                vi.append(mul(d, L)); vo.append((0.0, 0.0))
            continue
        d = norm(sub(b, a))
        f = sharp.get(k, 1.0)
        li = length(sub(p, a)) * tension * f
        lo = length(sub(b, p)) * tension * f
        vi.append(mul(d, -li))
        vo.append(mul(d, lo))
    return Path(points, vi, vo, closed)


def poly(points, closed=False):
    return Path(points, None, None, closed)


def circle_pts(c, r, n=8, start=0.0):
    return [(c[0] + r * math.cos(start + 2 * math.pi * k / n), c[1] + r * math.sin(start + 2 * math.pi * k / n)) for k in range(n)]


def pchip(xs, ys, x):
    """Monotone-ish smooth interpolation of a small table (Catmull-Rom with clamped ends)."""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    k = max(i for i in range(len(xs) - 1) if xs[i] <= x)
    x0, x1 = xs[k], xs[k + 1]
    y0, y1 = ys[k], ys[k + 1]
    h = x1 - x0
    def slope(i):
        if i <= 0:
            return (ys[1] - ys[0]) / (xs[1] - xs[0])
        if i >= len(xs) - 1:
            return (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
        return (ys[i + 1] - ys[i - 1]) / (xs[i + 1] - xs[i - 1])
    m0, m1 = slope(k), slope(k + 1)
    t = (x - x0) / h
    h00 = 2 * t ** 3 - 3 * t ** 2 + 1
    h10 = t ** 3 - 2 * t ** 2 + t
    h01 = -2 * t ** 3 + 3 * t ** 2
    h11 = t ** 3 - t ** 2
    return h00 * y0 + h10 * h * m0 + h01 * y1 + h11 * h * m1
