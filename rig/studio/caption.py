"""Captions drawn as plain Lottie paths (no text layers, so every player shows them the same).

Glyph outlines come from a TTF/OTF through fontTools.  Text is wrapped to at most two lines and shrunk until it fits.
"""
from __future__ import annotations

import os

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont

from mascot.lottie import Layer, Path, fl, gr, rc, sh, st, rgb

HERE = os.path.dirname(os.path.abspath(__file__))
# studio/assets/font.ttf is Fredoka SemiBold (SIL OFL, see FONT-LICENSE-OFL.txt); set STUDIO_FONT to use another font.
FONT_CANDIDATES = [
    os.environ.get("STUDIO_FONT", ""),
    os.path.join(HERE, "assets", "font.ttf"),
    "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

_FONT = None


def font():
    global _FONT
    if _FONT is None:
        for p in FONT_CANDIDATES:
            if p and os.path.exists(p):
                _FONT = TTFont(p, fontNumber=0)
                break
        else:
            raise FileNotFoundError("no caption font found; set STUDIO_FONT to a .ttf file")
    return _FONT


class _LottiePen(BasePen):
    """Collects glyph contours as Lottie paths (cubic; quadratic TrueType curves are converted by BasePen)."""

    def __init__(self, glyphset, k, ox, oy):
        super().__init__(glyphset)
        self.k, self.ox, self.oy = k, ox, oy
        self.paths = []
        self._pts = None

    def _xy(self, p):
        return (self.ox + p[0] * self.k, self.oy - p[1] * self.k)       # font units, y up -> canvas, y down

    def _moveTo(self, p):
        self._pts = [[self._xy(p), (0.0, 0.0), (0.0, 0.0)]]

    def _lineTo(self, p):
        self._pts.append([self._xy(p), (0.0, 0.0), (0.0, 0.0)])

    def _curveToOne(self, p1, p2, p3):
        a = self._pts[-1]
        c1, c2, b = self._xy(p1), self._xy(p2), self._xy(p3)
        a[2] = (c1[0] - a[0][0], c1[1] - a[0][1])
        self._pts.append([b, (c2[0] - b[0], c2[1] - b[1]), (0.0, 0.0)])

    def _closePath(self):
        pts = self._pts
        if len(pts) > 1 and abs(pts[-1][0][0] - pts[0][0][0]) < 1e-6 and abs(pts[-1][0][1] - pts[0][0][1]) < 1e-6:
            pts[0][1] = pts[-1][1]                  # the closing point repeats the start: keep its in-tangent only
            pts.pop()
        if len(pts) > 2:
            self.paths.append(Path([p[0] for p in pts], [p[1] for p in pts], [p[2] for p in pts], closed=True))
        self._pts = None

    _endPath = _closePath


def _advance(text, k):
    f = font()
    cmap, hmtx = f.getBestCmap(), f["hmtx"]
    w = 0.0
    for ch in text:
        g = cmap.get(ord(ch)) or cmap.get(ord("?"))
        w += hmtx[g][0] * k
    return w


def _wrap(text, k, width):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if cur and _advance(trial, k) > width:
            lines.append(cur)
            cur = wd
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def layout(text, width=460.0, max_size=76.0, min_size=30.0, max_lines=2):
    """Pick a font size and line breaks so the text fits in `width` on at most `max_lines` lines."""
    f = font()
    upm = f["head"].unitsPerEm
    for size in range(int(max_size), 51, -2):                 # one line, as long as the text can stay big
        if _advance(text, size / upm) <= width:
            return float(size), [text]
    size = max_size
    while True:
        k = size / upm
        lines = _wrap(text, k, width)
        if (len(lines) <= max_lines and all(_advance(ln, k) <= width for ln in lines)) or size <= min_size:
            return size, lines
        size -= 2.0


def glyph_paths(text, cx, baseline, size):
    """Paths for one centred line of text."""
    f = font()
    k = size / f["head"].unitsPerEm
    gs, cmap, hmtx = f.getGlyphSet(), f.getBestCmap(), f["hmtx"]
    x = cx - _advance(text, k) / 2.0
    out = []
    for ch in text:
        g = cmap.get(ord(ch)) or cmap.get(ord("?"))
        pen = _LottiePen(gs, k, x, baseline)
        gs[g].draw(pen)
        out += pen.paths
        x += hmtx[g][0] * k
    return out


def caption_layers(text, pos="bottom", style="outline", ink="#3B2A20", halo="#FFFFFF", accent="#FFD93D"):
    """Lottie layers (top-most first) for a caption at the bottom or top of the 512 canvas, and the (top, bottom)
    canvas rows it covers."""
    size, lines = layout(text)
    lh = size * 1.08
    block = lh * len(lines)
    top = (500.0 - block) if pos == "bottom" else 14.0
    paths = []
    for q, ln in enumerate(lines):
        baseline = top + lh * q + size * 0.82
        paths += glyph_paths(ln, 256.0, baseline, size)
    shapes = [sh(p) for p in paths]
    items = [gr("text", shapes + [fl(rgb(ink))])]
    if style == "outline":
        items.append(gr("halo", [sh(p) for p in paths] + [st(rgb(halo), max(8.0, size * 0.2))]))
    elif style == "bubble":
        wmax = max(_advance(ln, size / font()["head"].unitsPerEm) for ln in lines)
        items.append(gr("bubble", [rc((256.0, top + block / 2.0 + 2), (wmax + size * 0.9, block + size * 0.45), size * 0.45),
                                   fl(rgb(accent))]))
    if style == "bubble":
        span = (top - size * 0.22, top + block + size * 0.22)
    else:
        span = (top - size * 0.1, top + block + size * 0.1)
    return [Layer("caption", items)], span
