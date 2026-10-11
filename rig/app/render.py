"""Spec -> Lottie (cached) -> preview or file bytes.

Composing is CPU work in Python (about 0.2-5 s), so results are kept in a small in-process LRU keyed by the spec
hash.  One lock serialises composing: the rig's keyframe fitter keeps module-level caches, and the GIL would
serialise the work anyway.  Run several worker processes to use several cores.
"""
from __future__ import annotations

import copy
import tempfile
import threading
from collections import OrderedDict

from mascot.lottie import Layer, fl, gr, rgb, sh, st
from studio.caption import glyph_paths
from studio.compose import add_layers_on_top, compose
from studio.export import save
from studio.spec import StickerSpec

from .plans import FORMATS

_lock = threading.Lock()
_cache: OrderedDict = OrderedDict()
CACHE_SIZE = 256
MARK = "pawse studio"


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
