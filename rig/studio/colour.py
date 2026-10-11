"""Keep worn and held things visible against the mascot's fur.

A pink bow on a pink cat disappears.  Each coloured item has a list of colours it likes, best first; the first one
that differs enough from the fur (CIE76 distance in Lab space) is used.
"""
from __future__ import annotations

from mascot.props import C

MIN_DELTA = 28.0          # below this two flat colours read as "the same" at sticker size


def _lab(rgb):
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(float(c)) for c in rgb[:3])
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta(a, b):
    la, lb = _lab(a), _lab(b)
    return sum((p - q) ** 2 for p, q in zip(la, lb)) ** 0.5


def pick(prefs, fur):
    """First colour name in `prefs` that stands out from `fur` (an RGB list); the most different one if none does."""
    for name in prefs:
        if delta(C[name], fur) >= MIN_DELTA:
            return name
    return max(prefs, key=lambda n: delta(C[n], fur))


# item -> colours it likes, best first (names from mascot.props.C)
PREFS = {
    "party_hat": ["coral", "teal", "lilac", "blue"],
    "bow": ["pink", "coral", "lilac", "teal", "yellow"],
    "scarf": ["coral", "teal", "lilac", "blue"],
    "headphones": ["teal", "coral", "lilac", "yellow"],
    "heart": ["coral", "pink", "lilac", "teal"],
    "hearts": ["coral", "pink", "lilac", "teal"],
    "mug": ["teal", "coral", "lilac", "blue"],
}
