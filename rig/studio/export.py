"""Lottie -> files: PNG / WebP still, Telegram .tgs, WhatsApp animated WebP, GIF, raw JSON.

Rasterising uses rlottie (no browser needed).  Limits that the messengers enforce are checked and reported.
"""
from __future__ import annotations

import gzip
import json
import os

import numpy as np
from PIL import Image, ImageChops, ImageFilter

TGS_MAX = 64 * 1024            # Telegram animated sticker: gzipped Lottie, 512x512, 60 fps, up to 3 s
WA_ANIM_MAX = 500 * 1024       # WhatsApp animated sticker: WebP 512x512, up to 500 KB
WA_STILL_MAX = 100 * 1024      # WhatsApp static sticker: WebP 512x512, up to 100 KB


def _anim(doc):
    from rlottie_python import LottieAnimation
    return LottieAnimation.from_data(json.dumps(doc, separators=(",", ":")))


_PREMULTIPLIED = None


def _premultiplied():
    """Does the rasteriser hand back premultiplied pixels?  rlottie draws into a premultiplied surface and
    rlottie-python passes it on as if it were plain RGBA, so a white pixel at 50 % comes back as (127, 127, 127, 127).
    Checked once with a test drawing, so a future version that converts by itself is not converted twice."""
    global _PREMULTIPLIED
    if _PREMULTIPLIED is None:
        from mascot.lottie import Layer, document, el, fl, gr
        probe = document("probe", [Layer("probe", [gr("g", [el((8, 8), (40, 40)), fl([1.0, 1.0, 1.0], 50)])])], op=1, w=16, h=16)
        a = _anim(probe)
        try:
            r, g, b, al = a.render_pillow_frame(frame_num=0, width=16, height=16).getpixel((8, 8))
        finally:
            a.lottie_animation_destroy()
        _PREMULTIPLIED = 0 < al < 255 and r <= al + 1
    return _PREMULTIPLIED


def straight(img):
    """A rendered RGBA image with straight (not premultiplied) alpha, which is what PNG, WebP and GIF store.
    Without this every soft edge gets a dark fringe and every translucent glow turns grey."""
    if not _premultiplied():
        return img
    a = np.asarray(img, dtype=np.uint16)
    al = a[..., 3:4]
    rgb = np.where(al > 0, np.minimum(255, (a[..., :3] * 255 + al // 2) // np.maximum(al, 1)), 0)
    return Image.fromarray(np.concatenate([rgb, al], axis=2).astype(np.uint8), "RGBA")


def _render(a, f, size):
    return straight(a.render_pillow_frame(frame_num=int(f), width=size, height=size).convert("RGBA"))


def frame(doc, f, size=512):
    """One frame as an RGBA image (straight alpha)."""
    a = _anim(doc)
    try:
        return _render(a, f, size)
    finally:
        a.lottie_animation_destroy()


def frames(doc, size=512, step=1):
    """Frames ip .. op-1 (straight alpha).  The frame at op equals frame ip in a loop, so it is left out (playing it
    would show the first pose twice at every loop, a small stutter)."""
    a = _anim(doc)
    try:
        total = min(a.lottie_animation_get_totalframe(), int(doc["op"] - doc["ip"]))
        return [_render(a, f, size) for f in range(0, total, step)]
    finally:
        a.lottie_animation_destroy()


def die_cut(img, r=8):
    """The sticker look messengers expect: grow the silhouette by about r px with round corners, fill it white and
    lay it under the image (WhatsApp recommends an 8 px white outline)."""
    a = img.getchannel("A")
    grown = a.point(lambda v: 255 if v > 24 else 0).filter(ImageFilter.GaussianBlur(r * 0.75))
    grown = grown.point(lambda v: 255 if v > 18 else 0).filter(ImageFilter.GaussianBlur(0.8))   # threshold, then soften the edge
    base = Image.new("RGBA", img.size, (255, 255, 255, 0))
    base.putalpha(ImageChops.lighter(grown, a))
    base.alpha_composite(img)
    return base


def watermark(img, text="pawse studio"):
    """Small mark in the bottom-right corner, in the caption font (any Pillow build can draw it)."""
    from PIL import ImageDraw, ImageFont
    d = ImageDraw.Draw(img)
    try:
        from .caption import FONT_CANDIDATES
        path = next(p for p in FONT_CANDIDATES if p and os.path.exists(p))
        font = ImageFont.truetype(path, max(10, img.width // 32))
        d.text((img.width - 8, img.height - 8), text, fill=(59, 42, 32, 110), anchor="rd", font=font)
    except (StopIteration, OSError, ValueError):
        font = ImageFont.load_default()
        w = d.textlength(text, font=font)
        d.text((img.width - 8 - w, img.height - 20), text, fill=(59, 42, 32, 110), font=font)
    return img


def webp_durations(data: bytes):
    """Frame durations (ms) of an animated WebP, read from its ANMF chunks."""
    out, i = [], 12
    while i + 8 <= len(data):
        tag, size = data[i:i + 4], int.from_bytes(data[i + 4:i + 8], "little")
        if tag == b"ANMF":
            out.append(int.from_bytes(data[i + 20:i + 23], "little"))
        i += 8 + size + (size & 1)
    return out


def tgs_bytes(doc):
    return gzip.compress(json.dumps(doc, separators=(",", ":")).encode(), compresslevel=9)


def save(doc, out_dir, name, formats=("png", "webp", "tgs", "json"), still=0, mark=False, outline=True):
    """Write the requested formats.  Returns {format: (path, size_bytes, warning or None)}.
    outline: give raster formats (PNG, WebP, animated WebP, GIF) the white die-cut border.  Telegram draws .tgs files
    as they are, so the vector formats never get one."""
    os.makedirs(out_dir, exist_ok=True)
    res = {}

    def put(fmt, path, warn=None):
        res[fmt] = (path, os.path.getsize(path), warn)

    if "json" in formats:
        p = os.path.join(out_dir, f"{name}.json")
        with open(p, "w") as f:
            json.dump(doc, f, separators=(",", ":"))
        put("json", p)
    if "tgs" in formats:
        p = os.path.join(out_dir, f"{name}.tgs")
        data = tgs_bytes(doc)
        with open(p, "wb") as f:
            f.write(data)
        warn = None
        if len(data) > TGS_MAX:
            warn = f"over Telegram's 64 KB limit ({len(data) / 1024:.0f} KB)"
        if (doc["op"] - doc["ip"]) / doc["fr"] > 3.0:
            warn = "longer than Telegram's 3 s limit"
        put("tgs", p, warn)
    if "png" in formats or "webp" in formats:
        img = frame(doc, still)
        if outline:
            img = die_cut(img)
        if mark:
            watermark(img)
        if "png" in formats:
            p = os.path.join(out_dir, f"{name}.png")
            img.save(p, optimize=True)
            put("png", p)
        if "webp" in formats:
            p = os.path.join(out_dir, f"{name}.webp")
            img.save(p, "WEBP", quality=90, method=6)
            put("webp", p, "over WhatsApp's 100 KB static limit" if os.path.getsize(p) > WA_STILL_MAX else None)
    if "awebp" in formats or "gif" in formats:
        allf = frames(doc)
        if outline:
            allf = [die_cut(im) for im in allf]
        if mark:
            allf = [watermark(im) for im in allf]
        if "awebp" in formats:
            # A 512 px transparent frame costs ~13 KB whatever the quality, so the frame rate is what gets a sticker
            # under WhatsApp's limit: try 30, 20, then 15 fps.
            p = os.path.join(out_dir, f"{name}.anim.webp")
            for step, q in ((2, 75), (3, 70), (4, 60), (4, 45)):
                fr = allf[::step]
                fr[0].save(p, "WEBP", save_all=True, append_images=fr[1:], duration=int(round(1000 * step / doc["fr"])), loop=0,
                           quality=q, alpha_quality=60, method=4, kmin=9, kmax=10)
                if os.path.getsize(p) <= WA_ANIM_MAX:
                    break
            put("awebp", p, "over WhatsApp's 500 KB animated limit" if os.path.getsize(p) > WA_ANIM_MAX else None)
        if "gif" in formats:
            p = os.path.join(out_dir, f"{name}.gif")
            fr = allf[::3]                                   # 20 fps; GIF has no partial transparency anyway
            fr[0].save(p, save_all=True, append_images=fr[1:], duration=int(round(3000 / doc["fr"])), loop=0, disposal=2, optimize=True)
            put("gif", p)
    return res
