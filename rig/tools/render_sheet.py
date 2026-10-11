#!/usr/bin/env python3
"""Render Lottie JSON files to a contact sheet (one row per file).

Usage:
  render_sheet.py --out sheet.png [--n 8 | --frames 0,10,20] [--size 200] [--bg '#f4efe9'] a.json b.json ...
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw, ImageFont
import lr


def font(sz, bold=False):
    names = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for d in ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu"):
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def sheet(rows, S, out, cols=0):
    lab = 18
    if cols:  # wrap long rows
        wrapped = []
        for name, total, imgs in rows:
            for k in range(0, len(imgs), cols):
                wrapped.append((name if k == 0 else "", total, imgs[k : k + cols]))
        rows = wrapped
    maxc = max(len(r[2]) for r in rows)
    W = maxc * S
    H = sum(S + (lab if r[0] else 0) for r in rows)
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    fnt = font(12)
    y = 0
    for name, total, imgs in rows:
        if name:
            d.rectangle([0, y, W, y + lab], fill="#222")
            d.text((4, y + 2), f"{name}  ({total}f)", fill="white", font=fnt)
            y += lab
        for ci, (fi, fr) in enumerate(imgs):
            im.paste(fr, (ci * S, y))
            d.text((ci * S + 4, y + 2), str(fi), fill="#888", font=fnt)
        y += S
    im.save(out)
    print("wrote", out, im.size)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--frames", default="")
    ap.add_argument("--size", type=int, default=200)
    ap.add_argument("--bg", default="#f4efe9")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--cols", type=int, default=0)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    fr = [int(x) for x in a.frames.split(",")] if a.frames else lr.even(a.n)
    jobs = [(os.path.basename(p), lr.load(p), fr) for p in a.files]
    rows, errs = lr.render(jobs, a.size, a.bg, a.scale)
    sheet(rows, int(a.size * a.scale), a.out, a.cols)
