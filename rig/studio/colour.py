"""Colours: a full fur palette from one colour, and worn and held things that stay visible against the fur.

A pink bow on a pink cat disappears.  Each coloured item has a list of colours it likes, best first; the first one
that differs enough from the fur (CIE76 distance in Lab space) is used.

`fur_palette` turns ONE colour into every shade the mascot is drawn with (body, arms and legs a touch darker, tail
darker still, stripes darkest), copying the proportions of the mascot's own palette, so any colour works: "a teal
fox", "#ff00aa cat".  `readable` keeps the features (eyes, nose, paws) visible on very dark fur.
"""
from __future__ import annotations

import colorsys

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


def lightness(rgb):
    return _lab(rgb)[0]


def to_rgb(c):
    """'#rrggbb' / '#rgb' / a name of mascot.props.C / an [r, g, b] list -> [r, g, b] in 0..1."""
    if isinstance(c, str):
        if c in C:
            return list(C[c])
        h = c.lstrip("#")
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        return [int(h[k:k + 2], 16) / 255.0 for k in (0, 2, 4)]
    return [float(v) for v in c[:3]]


def to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(v * 255))):02x}" for v in rgb[:3])


def pick(prefs, fur):
    """First colour name in `prefs` that stands out from `fur` (an RGB list); the most different one if none does."""
    for name in prefs:
        if delta(C[name], fur) >= MIN_DELTA:
            return name
    return max(prefs, key=lambda n: delta(C[n], fur))


# item -> colours it likes, best first (names from mascot.props.C).  Items registered with `tint=` add themselves.
PREFS = {
    "party_hat": ["coral", "teal", "lilac", "blue"],
    "bow": ["pink", "coral", "lilac", "teal", "yellow"],
    "scarf": ["coral", "teal", "lilac", "blue"],
    "headphones": ["teal", "coral", "lilac", "yellow"],
    "heart": ["coral", "pink", "lilac", "teal"],
    "hearts": ["coral", "pink", "lilac", "teal"],
    "mug": ["teal", "coral", "lilac", "blue"],
}


def prefs_for(name):
    """The colour preferences of an item, from the registry (falls back to the table above)."""
    from .registry import REG
    for table in (REG.props, REG.effects, REG.wear):
        it = table.get(name)
        if it is not None and it.tint:
            return list(it.tint)
    return PREFS.get(name)


# ------------------------------------------------------------------ fur from one colour
def _hls(rgb):
    return colorsys.rgb_to_hls(*rgb[:3])


def _from_hls(h, l, s):
    return list(colorsys.hls_to_rgb(h % 1.0, max(0.0, min(1.0, l)), max(0.0, min(1.0, s))))


def fur_palette(colour, base_pal):
    """Palette overrides for fur of `colour`, shaded like the mascot's own palette.
    base_pal: the mascot's palette (its 'orange' slot is the main fur; every slot that was a shade of it follows)."""
    main = to_rgb(colour)
    h0, l0, s0 = _hls(base_pal["orange"])
    h, l, s = _hls(main)
    out = {"orange": to_hex(main)}
    for key in ("arm", "leg", "tail", "stripe", "tail_tip", "tail_ring"):
        ref = base_pal.get(key)
        if ref is None or not isinstance(ref, (list, tuple)):
            continue
        hr, lr, sr = _hls(ref)
        if delta(ref, base_pal["orange"]) > 45 and key == "tail_tip":
            continue                                    # a tip in another colour (the fox's cream tip) stays as it is
        dl = lr - l0                                    # how much darker / lighter this slot is than the main fur
        ds = (sr - s0) if s0 > 0.05 else 0.0
        if l < 0.18:                                    # on very dark fur, shade towards lighter instead of black
            dl = abs(dl) * 0.8
        out[key] = to_hex(_from_hls(h, l + dl, s + ds * (s / max(s0, 1e-6)) if s0 > 0.05 else s))
    return out


def readable(pal):
    """Keep the features readable: on very dark fur the dark eye and paw colour would vanish, so the features get
    darker still and the eye colour lighter.  Returns palette changes (possibly none)."""
    fur = pal["orange"]
    dark = pal.get("dark")
    if dark is None or delta(fur, dark) >= 24:
        return {}
    h, l, s = _hls(fur)
    out = {"dark": _from_hls(h, min(l * 0.38, 0.08), min(s, 0.25))}
    if "iris" in pal:
        out["iris"] = _from_hls(_hls(pal["iris"])[0], 0.62, 0.45)
    return out
