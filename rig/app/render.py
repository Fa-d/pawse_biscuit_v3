"""Spec -> Lottie (cached) -> preview pictures or file bytes.

The browser never receives Lottie: previews are pictures drawn here (an animated WebP, or a PNG still), and an
unpaid preview has its mark drawn into the pixels.  The vector source leaves only as a paid download.

Composing is CPU work in Python (about 0.2-5 s), so results are kept in a small in-process LRU keyed by the spec
hash.  One lock serialises composing: the rig's keyframe fitter keeps module-level caches, and the GIL would
serialise the work anyway.  Run several worker processes to use several cores.
"""
from __future__ import annotations

import copy
import io
import os
import tempfile
import threading
from collections import OrderedDict
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFont

from mascot.lottie import Layer, fl, gr, rgb, sh, st
from studio.caption import FONT_CANDIDATES, glyph_paths
from studio.compose import add_layers_on_top, compose
from studio.export import frame, frames, save
from studio.spec import StickerSpec

from .plans import FORMATS

_lock = threading.Lock()
_cache: OrderedDict = OrderedDict()
CACHE_SIZE = 256
MARK = "pawse studio"
PREVIEW_SIZE = 400          # the studio shows the sticker at up to 460 px; downloads are 512
THUMB_SIZE = 200
PREVIEW_FPS = 15
_img_lock = threading.Lock()
_img_cache: OrderedDict = OrderedDict()
IMG_CACHE_SIZE = 192


def composed(spec: StickerSpec):
    """(lottie dict, info) for a spec, from the cache when possible.  Callers must not change the result."""
    key = spec.key()
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
        doc, info = compose(spec)
        info = {k: v for k, v in info.items() if k != "tint"} | {"key": key}
        _cache[key] = (doc, info)
        if len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
        return doc, info


def watermarked(doc, corner="bottom"):
    """A copy of the document with a small 'pawse studio' mark in the right-hand corner at `corner` (top or bottom).
    Callers put it on the side away from the caption."""
    out = copy.deepcopy(doc)
    paths = glyph_paths(MARK, 0, 0, 20)
    width = max(max(x for x, _ in p.v) for p in paths) - min(min(x for x, _ in p.v) for p in paths)
    shift = (500 - width / 2 - 6, 502 if corner == "bottom" else 28)
    mark = Layer("watermark", [gr("mark", [gr("ink", [sh(p) for p in paths] + [fl(rgb("#1F2A2E"), 55)]),
                                           gr("halo", [sh(p) for p in paths] + [st([1, 1, 1], 4, 70)])], p=shift)])
    return add_layers_on_top(out, [mark])


def mark_corner(spec: StickerSpec):
    return "top" if spec.caption and spec.caption.text.strip() and spec.caption.pos == "bottom" else "bottom"


def preview(spec: StickerSpec, mark: bool):
    doc, info = composed(spec)
    return (watermarked(doc, mark_corner(spec)) if mark else doc), info


@lru_cache(maxsize=4)
def _tile(size):
    """A faint diagonal repeat of the mark, size x size.  Laid over the sticker's own pixels only (see _burn), so the
    transparent background stays clean and the die-cut outline in the page still fits."""
    path = next((p for p in FONT_CANDIDATES if p and os.path.exists(p)), None)
    fnt = ImageFont.truetype(path, max(10, size // 22)) if path else ImageFont.load_default()
    big = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    w = d.textlength(MARK, font=fnt)
    gap_x, gap_y = int(w + size * 0.12), max(14, size // 7)
    for row, y in enumerate(range(0, size * 2, gap_y)):
        for x in range(-int(w) + (row % 2) * gap_x // 2, size * 2, gap_x):
            d.text((x, y), MARK, font=fnt, fill=(120, 120, 120, 64))
    big = big.rotate(28, resample=Image.BICUBIC)
    o = size // 2
    return big.crop((o, o, o + size, o + size))


def _burn(img):
    """Draw the faint mark into an RGBA frame wherever the sticker is (straight alpha in, straight alpha out)."""
    tile = _tile(img.width)
    over = tile.copy()
    over.putalpha(ImageChops.multiply(tile.getchannel("A"), img.getchannel("A")))
    img.alpha_composite(over)
    return img


def preview_image(spec: StickerSpec, mark: bool, kind: str = "anim", tile: bool = True):
    """(bytes, media type, info) for what the studio shows.  kind: anim (animated WebP), still (PNG) or thumb (small PNG).
    mark: the corner mark, plus (with tile) the faint repeat burned into the sticker, as unpaid previews get."""
    ck = (spec.key(), mark, kind, tile)
    with _img_lock:
        if ck in _img_cache:
            _img_cache.move_to_end(ck)
            return _img_cache[ck]
    doc, info = composed(spec)
    if mark:
        doc = watermarked(doc, mark_corner(spec))
    burn = _burn if mark and tile else (lambda im: im)
    buf = io.BytesIO()
    if kind == "anim":
        step = max(1, round(doc["fr"] / PREVIEW_FPS))
        imgs = [burn(im) for im in frames(doc, PREVIEW_SIZE, step)]
        imgs[0].save(buf, "WEBP", save_all=True, append_images=imgs[1:], duration=int(round(1000 * step / doc["fr"])),
                     loop=0, quality=65, method=2)   # method 2: half the encode time of 4
        mime = "image/webp"
    else:
        im = burn(frame(doc, info["still"], PREVIEW_SIZE if kind == "still" else THUMB_SIZE))
        im.save(buf, "PNG", optimize=True)
        mime = "image/png"
    out = (buf.getvalue(), mime, info)
    with _img_lock:
        _img_cache[ck] = out
        if len(_img_cache) > IMG_CACHE_SIZE:
            _img_cache.popitem(last=False)
    return out


def export_bytes(spec: StickerSpec, fmt: str, mark: bool):
    """(bytes, filename, media type, warning or None)."""
    doc, info = composed(spec)
    if mark:
        doc = watermarked(doc, mark_corner(spec))
    ext, mime, _ = FORMATS[fmt]
    with tempfile.TemporaryDirectory() as d:
        res = save(doc, d, "sticker", formats=(fmt,), still=info["still"])
        path, _, warn = res[fmt]
        with open(path, "rb") as f:
            data = f.read()
    return data, f"sticker-{info['key'][:8]}.{ext}", mime, warn


def clear_cache():
    with _lock:
        _cache.clear()
    with _img_lock:
        _img_cache.clear()
