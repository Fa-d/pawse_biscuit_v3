"""Auto-framing: measure where the sticker actually draws, then scale and move it to fill the canvas.

v3 guessed a size per motion (0.86 for jumps, 1.06 when sitting).  Guesses fail for combinations: a balloon on a
string while sitting left the canvas at the top, rain clouds and party hats were cut off under captions.  Now the
finished animation is drawn small (rlottie) on a sample of its frames, the area anything ever covers is measured,
and the whole scene is fitted into the free part of the canvas with a margin for the white sticker edge.
"""
from __future__ import annotations

import json

import numpy as np

CANVAS = 512.0
MARGIN = 18.0          # empty border kept free: the white die-cut edge is about 8 px wide, plus a little air
MAX_GROW = 1.12        # a small scene is enlarged at most this much
MIN_SCALE = 0.42
PROBE = 128            # size the frames are measured at


ZOOM = 0.5             # the scene is measured shrunk to half size, so whatever reaches up to half a canvas past an edge still counts


def _shrunk(doc, k):
    """A copy of the document with every top-level layer scaled by k about the canvas centre."""
    layers = [dict(L) for L in doc["layers"]]
    ind = max(L["ind"] for L in layers) + 1
    for L in layers:
        if "parent" not in L:
            L["parent"] = ind
    c = CANVAS / 2.0
    layers.append({"ddd": 0, "ind": ind, "ty": 3, "nm": "measure", "sr": 1, "ao": 0, "ip": 0, "op": doc["op"], "st": 0, "bm": 0,
                   "ks": {"o": {"a": 0, "k": 100}, "r": {"a": 0, "k": 0}, "p": {"a": 0, "k": [c, c, 0]}, "a": {"a": 0, "k": [c, c, 0]},
                          "s": {"a": 0, "k": [k * 100, k * 100, 100]}}})
    return dict(doc, layers=layers)


def measure(doc, step=None, size=PROBE * 2, threshold=6, zoom=ZOOM):
    """(x0, y0, x1, y1) in canvas pixels covering everything drawn in any sampled frame - also what lies outside the
    canvas - or None (no rasteriser, or nothing drawn)."""
    try:
        from rlottie_python import LottieAnimation
    except ImportError:
        return None
    a = LottieAnimation.from_data(json.dumps(_shrunk(doc, zoom), separators=(",", ":")))
    try:
        total = int(a.lottie_animation_get_totalframe())
        step = step or max(1, total // 48)
        acc = np.zeros((size, size), dtype=bool)
        for f in list(range(0, total, step)) + [total - 1]:
            buf = np.frombuffer(a.lottie_animation_render(frame_num=f, width=size, height=size), dtype=np.uint8)
            acc |= buf.reshape(size, size, 4)[..., 3] > threshold
    finally:
        a.lottie_animation_destroy()
    ys, xs = np.nonzero(acc)
    if not len(xs):
        return None
    k = CANVAS / size
    pad = 1.0                                           # one probe pixel of slack on every side
    c = CANVAS / 2.0
    back = lambda v: c + (v * k - c) / zoom             # probe pixels -> canvas pixels of the unshrunk scene
    return (back(xs.min() - pad), back(ys.min() - pad), back(xs.max() + 1 + pad), back(ys.max() + 1 + pad))


def fit(box, free=(0.0, CANVAS), margin=MARGIN, grow=MAX_GROW):
    """Scale and offset that put `box` inside the canvas rows `free` = (top, bottom), centred, with `margin` free.
    Returns (scale, dx, dy, about): the scene is scaled by `scale` about `about`, then moved by (dx, dy)."""
    x0, y0, x1, y1 = box
    top, bottom = free
    avail_w = CANVAS - 2 * margin
    avail_h = (bottom - top) - 2 * margin
    w, h = max(x1 - x0, 1.0), max(y1 - y0, 1.0)
    k = max(MIN_SCALE, min(grow, avail_w / w, avail_h / h))
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    tx = CANVAS / 2.0
    # vertically: centred in the free rows, but a scene that fits with room to spare sits a little low (it stands)
    room = avail_h - h * k
    ty = top + margin + h * k / 2.0 + max(0.0, room) * 0.62
    return k, tx - cx, ty - cy, (cx, cy)
