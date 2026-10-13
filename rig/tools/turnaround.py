#!/usr/bin/env python3
"""Turnaround sheet: every mascot in its rest pose, with the guide lines its other views must keep.

    python3 tools/turnaround.py                          # all 14 mascots, front view, in a grid -> out/turnaround.png
    python3 tools/turnaround.py biscuit                  # one mascot, one cell per view: front, 20 deg, three-quarter, side, back
    python3 tools/turnaround.py --views front,side mochi bruno --size 300 --out out/cats.png

Guide lines, measured on the front view in canvas pixels (512 x 512) and drawn across the mascot's whole row:
  ground (solid), crown (the top of the skull), eye line (the centre of the eyes), shoulders.
A view the mascot does not have yet is drawn as a faint onion skin of the front view, the space its art will fill.
v1 (phase 0) draws the front view only; the rig's views arrive in phase 2 and appear here by themselves.
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

VIEWS = {"front": "front", "y20": "20 deg", "q": "three-quarter", "side": "side", "back": "back"}
INK, QUIET, BG, CELL = (40, 36, 44), (120, 116, 124), (246, 244, 240), (255, 255, 255)
# guide line: (colour, dash length, gap); dash 0 = solid
GUIDES = {"crown": ((232, 112, 42), 6, 4), "eyes": ((74, 144, 226), 6, 4), "shoulders": ((76, 175, 80), 2, 3),
          "ground": ((40, 36, 44), 0, 0)}


def font(size):
    path = os.path.join(ROOT, "studio", "assets", "font.ttf")
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def rest_pose(name, view="front"):
    """(document, character) of the mascot standing at rest, smiling, frame 0.  Only the front view exists in v1."""
    from mascot.build import characters
    from mascot.clip import Clip

    if view != "front":
        return None, None
    ch = characters()[name]()
    c = Clip(f"turnaround_{name}_{view}", 2, loop=True, char=ch)
    c.face(0, "smiley", dur=0)
    c.arm("LR", (0, "rest"))
    c.tailpose((0, "rest"))
    return ch.build(c), ch


def guides(ch):
    """Guide heights on the canvas (y in px) from a built rest pose."""
    return dict(
        crown=ch.crown_world(0)[1],
        eyes=ch.head_to_world(0, ch.side(ch.eye, "R"))[1],
        shoulders=ch.body_to_world(0, ch.side(ch.shoulder, "R"))[1],
        ground=ch.GROUND,
    )


def dashed(d, y, x0, x1, fill, dash=6, gap=5, width=1):
    x = x0
    while x < x1:
        d.line([(x, y), (min(x + dash, x1), y)], fill=fill, width=width)
        x += dash + gap


def main(argv=None):
    from mascot.build import MASCOTS
    from studio.export import frame

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("mascots", nargs="*", help=f"default: all ({', '.join(MASCOTS)})")
    ap.add_argument("--views", default=None, help=f"comma list of {', '.join(VIEWS)} (default: front for many mascots, all for one)")
    ap.add_argument("--size", type=int, default=0, help="cell size in px (default 240, or 300 for one mascot)")
    ap.add_argument("--cols", type=int, default=7, help="mascots per row when only the front view is drawn")
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "turnaround.png"))
    a = ap.parse_args(argv)
    names = a.mascots or list(MASCOTS)
    bad = [n for n in names if n not in MASCOTS]
    if bad:
        ap.error(f"unknown mascot {bad[0]!r}; expected one of {', '.join(MASCOTS)}")
    views = (a.views.split(",") if a.views else (list(VIEWS) if len(names) == 1 else ["front"]))
    bad = [v for v in views if v not in VIEWS]
    if bad:
        ap.error(f"unknown view {bad[0]!r}; expected one of {', '.join(VIEWS)}")
    S = a.size or (300 if len(names) == 1 else 240)
    k = S / 512.0
    label_h, side = 60, 16
    grid = views == ["front"]
    cols = min(a.cols, len(names)) if grid else len(views)
    rows = (len(names) + cols - 1) // cols if grid else len(names)
    W = side + cols * S + 16
    H = rows * (S + label_h) + 64
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    f_title, f_label, f_small = font(18), font(14), font(12)
    d.text((side, 10), "Turnaround sheet: guide lines from the front view (canvas px)", fill=INK, font=f_title)
    x = side
    for key, (col, dash, gap) in GUIDES.items():                 # the legend
        if dash:
            dashed(d, 46, x, x + 28, col, dash, gap, width=2)
        else:
            d.line([(x, 46), (x + 28, 46)], fill=col, width=2)
        d.text((x + 34, 38), key, fill=INK, font=f_small)
        x += 34 + int(d.textlength(key, font=f_small)) + 24

    measured = {}
    for q, (name, view) in enumerate((n, v) for n in names for v in views):
        r, c = (q // cols, q % cols) if grid else (names.index(name), views.index(view))
        x0, y0 = side + c * S, 64 + r * (S + label_h)
        if name not in measured:
            front_doc, ch = rest_pose(name, "front")
            measured[name] = (front_doc, guides(ch))
        front_doc, g = measured[name]
        doc, _ = rest_pose(name, view)
        top = y0 + label_h
        d.rectangle([x0 + 2, top, x0 + S - 2, top + S - 4], fill=CELL)
        if doc is not None:
            img = frame(doc, 0, size=S)
        else:                                                # not drawn yet: an onion skin of the front view
            img = frame(front_doc, 0, size=S)
            img.putalpha(img.getchannel("A").point(lambda v: v * 22 // 100))
        sheet.paste(img, (x0, top), img)
        if doc is None:
            d.text((x0 + 10, top + 8), "not drawn yet", fill=QUIET, font=f_small)
        d.text((x0 + 8, y0 + 4), f"{name}  {VIEWS[view]}" if grid or c == 0 else VIEWS[view], fill=INK, font=f_label)
        if view == "front":                                  # the measured heights, under the name, two to a line
            keys = list(GUIDES)
            for line in range(2):
                text = "  ".join(f"{key} {g[key]:.0f}" for key in keys[2 * line:2 * line + 2])
                d.text((x0 + 8, y0 + 23 + 15 * line), text, fill=QUIET, font=f_small)
        for key, (col, dash, gap) in GUIDES.items():
            y = top + g[key] * k
            if dash:
                dashed(d, y, x0 + 4, x0 + S - 4, col, dash, gap, width=2)
            else:
                d.line([(x0 + 4, y), (x0 + S - 4, y)], fill=col, width=2)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    sheet.save(a.out)
    print(f"{len(names)} mascots x {len(views)} views -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
