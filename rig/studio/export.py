"""Lottie -> files: PNG / WebP still, Telegram .tgs, WhatsApp animated WebP, GIF, raw JSON.

Rasterising uses rlottie (no browser needed).  Limits that the messengers enforce are checked and reported.
"""
from __future__ import annotations

import gzip
import json
import os

from PIL import Image, ImageChops, ImageFilter

TGS_MAX = 64 * 1024            # Telegram animated sticker: gzipped Lottie, 512x512, 60 fps, up to 3 s
WA_ANIM_MAX = 500 * 1024       # WhatsApp animated sticker: WebP 512x512, up to 500 KB
WA_STILL_MAX = 100 * 1024      # WhatsApp static sticker: WebP 512x512, up to 100 KB


def _anim(doc):
    from rlottie_python import LottieAnimation
    return LottieAnimation.from_data(json.dumps(doc, separators=(",", ":")))


def frame(doc, f, size=512):
    """One frame as an RGBA image."""
    a = _anim(doc)
    try:
        return a.render_pillow_frame(frame_num=int(f), width=size, height=size).convert("RGBA")
    finally:
        a.lottie_animation_destroy()


def frames(doc, size=512, step=1):
    """Frames ip .. op-1.  The frame at op equals frame ip in a loop, so it is left out (playing it would show the
    first pose twice at every loop, a small stutter)."""
    a = _anim(doc)
    try:
        total = min(a.lottie_animation_get_totalframe(), int(doc["op"] - doc["ip"]))
        return [a.render_pillow_frame(frame_num=f, width=size, height=size).convert("RGBA") for f in range(0, total, step)]
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
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    w = img.width
    d.text((w - 8, img.height - 8), text, fill=(59, 42, 32, 110), anchor="rd")
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
            put("webp", p, f"over WhatsApp's 100 KB static limit" if os.path.getsize(p) > WA_STILL_MAX else None)
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
