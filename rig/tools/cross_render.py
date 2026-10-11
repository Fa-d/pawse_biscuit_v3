#!/usr/bin/env python3
"""Cross-check: render the same frames with lottie-web (browser) and rlottie (the C++ engine used on many
mobile / embedded players) and report how different the pictures are.

Usage: cross_render.py [--frames 6] [--size 256] [--sheet out.png] file.json ...
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image, ImageDraw
import lr
from render_sheet import font
import rlottie_python as rl

BG = (244, 239, 233)


def rl_frame(anim, f, size):
    """rlottie returns premultiplied RGBA; composite it over the preview background correctly."""
    a = np.asarray(anim.render_pillow_frame(frame_num=f, width=size, height=size).convert("RGBA"), dtype=np.float32)
    alpha = a[..., 3:4] / 255.0
    out = a[..., :3] + np.array(BG, dtype=np.float32) * (1.0 - alpha)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=6)
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--sheet", default=None)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    jobs = [(os.path.basename(p), lr.load(p), lr.even(a.frames)) for p in a.files]
    web, _ = lr.render(jobs, a.size, "#f4efe9", 1.0)
    rows = []
    worst_all = 0.0
    for fp, (name, total, imgs) in zip(a.files, web):
        anim = rl.LottieAnimation.from_file(fp)
        nfr = anim.lottie_animation_get_totalframe()
        diffs = []
        pair = []
        for fi, wim in imgs:
            rim = rl_frame(anim, fi, a.size)
            d = np.abs(np.asarray(wim, dtype=np.int16) - np.asarray(rim, dtype=np.int16))
            # ignore 1px anti-aliasing differences: fraction of pixels that differ strongly
            strong = float((d.max(axis=2) > 60).mean()) * 100
            diffs.append(strong)
            pair.append((fi, wim, rim))
        worst = max(diffs)
        worst_all = max(worst_all, worst)
        print(f"{name:<36} frames lottie-web {total} / rlottie {nfr}   strongly different pixels: mean {np.mean(diffs):.2f}%  worst {worst:.2f}%")
        rows.append((name, pair))
    if a.sheet:
        S = a.size
        W = S * a.frames
        H = len(rows) * (2 * S + 20)
        sheet = Image.new("RGB", (W, H), "white")
        dr = ImageDraw.Draw(sheet)
        y = 0
        for name, pair in rows:
            dr.rectangle([0, y, W, y + 20], fill="#222")
            dr.text((4, y + 3), f"{name}   top: lottie-web   bottom: rlottie", fill="white", font=font(12))
            y += 20
            for k, (fi, wim, rim) in enumerate(pair):
                sheet.paste(wim, (k * S, y))
                sheet.paste(rim, (k * S, y + S))
            y += 2 * S
        sheet.save(a.sheet)
        print("wrote", a.sheet)
    print(f"worst overall: {worst_all:.2f}%")
