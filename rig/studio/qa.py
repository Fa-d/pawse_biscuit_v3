#!/usr/bin/env python3
"""Quality checks for everything in the library, and contact sheets to look at it.

    python -m studio.qa                       # check every item on every mascot, print problems
    python -m studio.qa --kind motions        # only motions (props, effects, wear, faces, bases)
    python -m studio.qa --sheet out/sheet.png --kind effects     # contact sheet: one row per item, frames across

What is checked for each item:
  builds      the sticker composes without an error
  loop        the last frame of the loop equals the first (measured on the picture, before the loop is turned)
  canvas      nothing is drawn within 4 px of the canvas edge after framing
  telegram    the .tgs file is under 64 KB
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import numpy as np

from .compose import build_clip, compose
from .export import TGS_MAX, _anim, straight, tgs_bytes
from .registry import REG
from .spec import StickerSpec

# what the library guarantees (checked here, listed by python -m studio.cli --rules)
GUARANTEES = [
    ("L01", "Every motion, prop, effect and worn item loops seamlessly: the last frame matches the first (checked on the picture)."),
    ("L02", "Everything that repeats uses a period that divides the loop, so any length or tempo still loops."),
    ("L03", "One-shot things (a burst of stars, a camera flash, crumbs) are over before the loop ends."),
    ("L04", "Nothing touches the canvas edge after auto-framing (4 px margin), whatever the mascot holds or wears."),
    ("L05", "Every sticker fits Telegram's 64 KB .tgs limit."),
    ("L06", "Head-worn things are placed from each mascot's own data (crown, eyes, ears, nose, mouth) and follow every head turn."),
    ("L07", "A held thing the motion acts with stays upright whatever the arm does on the way (nothing is spilled or spun)."),
    ("L08", "Things floating over the head clear a mane (the mascot's top); neck things hang below it (its collar)."),
    ("L09", "Every item is checked on every mascot, standing and (when it can) sitting."),
    ("L10", "Every motion is checked at 1, 1.5 and 3 seconds."),
    ("L11", "The original app's 23 clips are drawn exactly as before (byte-identical files)."),
    ("L12", "Every pair of mascots builds as a scene of two that loops, stays off the canvas edge and fits 64 KB "
            "(python -m studio.qa_scene; duets join the check in phase 3)."),
    ("L13", "A paw held on another mascot stays within 4 px of its target (studio/tests/test_v5.py)."),
    ("L15", "A turned mascot builds, loops and fits on every mascot (front drawing turned, or its drawn side and back views), "
            "and a drawn view keeps the front's proportions: crown within 4 px, eye line within 3 px, the near foot on the "
            "ground (python -m studio.qa --kind views)."),
    ("L16", "Turned mascots look the same in lottie-web as in rlottie (python3 tools/cross_render.py on turned stickers)."),
    ("L17", "One-mascot stickers, the app's clips and the small effects stay byte-identical to v4 (python -m studio.snapshots --check)."),
    ("L18", "Seen from the side or from behind, a mascot with drawn views plays every motion, wears every worn thing (each "
            "drawn for that view, or left out where it cannot be seen) and shows the effects on its face where that view has "
            "its face; each builds, loops and fits (python -m studio.qa --kind turned).  A paw pinned in a drawn view lands "
            "within 1 px of its target in the written file (studio/tests/test_views.py)."),
]

SEAM_MAX = 0.08          # mean absolute difference (0..255) allowed between the first and the last frame


def _render(doc, frames, size=128):
    a = _anim(doc)
    try:
        return [np.asarray(straight(a.render_pillow_frame(frame_num=int(f), width=size, height=size).convert("RGBA"))).astype(np.int16)
                for f in frames]
    finally:
        a.lottie_animation_destroy()


def seam(spec):
    """Difference between frame 0 and frame L of the loop as acted (not turned), in mean |d| of 0..255 values."""
    c, char, info = build_clip(spec)
    c.opts["fade_safe"] = True
    doc = char.build(c)
    a, b = _render(doc, [0, doc["op"]], size=160)
    return float(np.abs(a - b).mean())


def edge_alpha(doc, size=128, every=4):
    L = int(doc["op"])
    worst = 0
    for im in _render(doc, range(0, L, every), size):
        al = im[..., 3]
        worst = max(worst, int(al[:2].max()), int(al[-2:].max()), int(al[:, :2].max()), int(al[:, -2:].max()))
    return worst


def check(spec):
    """Problems (list of sentences) for one spec."""
    out = []
    t = time.time()
    try:
        doc, info = compose(spec)
    except Exception as e:  # noqa: BLE001 - report it
        return [f"does not build: {type(e).__name__}: {e}"], {}
    dt = time.time() - t
    s = seam(spec)
    if s > SEAM_MAX:
        out.append(f"loop seam {s:.2f}")
    e = edge_alpha(doc)
    if e > 40:
        out.append(f"touches the canvas edge (alpha {e})")
    size = len(tgs_bytes(doc))
    if size > TGS_MAX:
        out.append(f"{size / 1024:.0f} KB is over Telegram's 64 KB")
    return out, dict(seconds=round(dt, 2), seam=round(s, 3), tgs_kb=round(size / 1024, 1), notes=info.get("notes", []))


def cases(kind, bases=None):
    """(label, spec dict) pairs that exercise every item of a kind."""
    bases = bases or list(REG.bases)
    if kind == "motions":
        for name, m in REG.motions.items():
            for b in bases:
                yield f"{name} on {b}", dict(base=b, motion=name, stance="sit" if m.sit == "only" else "stand")
                if m.sit == "ok":
                    yield f"{name} sitting on {b}", dict(base=b, motion=name, stance="sit")
    elif kind == "props":
        for name in REG.props:
            for b in bases:
                yield f"{name} on {b}", dict(base=b, props=[name], motion="bounce")
    elif kind == "effects":
        for name in REG.effects:
            for b in bases:
                yield f"{name} on {b}", dict(base=b, effects=[name], motion="bounce")
    elif kind == "wear":
        for name in REG.wear:
            for b in bases:
                yield f"{name} on {b}", dict(base=b, accessories=[name], motion="jump")
    elif kind == "faces":
        for name in REG.faces:
            for b in bases:
                yield f"{name} on {b}", dict(base=b, face=name, motion="idle")
    elif kind == "seconds":
        for name in REG.motions:
            for secs in (1.0, 1.5, 3.0):
                yield f"{name} {secs}s", dict(motion=name, seconds=secs)
    elif kind == "views":
        for b in bases:
            for yaw in VIEW_YAWS:
                yield f"yaw {yaw:+.0f} on {b}", dict(base=b, yaw=yaw, motion="wave")
    elif kind == "turned":                          # L18: everything again in the drawn views of the mascots that have them
        for b in bases:
            if REG.bases[b].load()().view_data("side") is None:
                continue
            for yaw in TURNED_YAWS:
                for name, m in REG.motions.items():
                    yield f"{name} at yaw {yaw:+.0f} on {b}", dict(base=b, motion=name, yaw=yaw, stance="sit" if m.sit == "only" else "stand")
                for name in REG.wear:
                    yield f"{name} worn at yaw {yaw:+.0f} on {b}", dict(base=b, accessories=[name], motion="jump", yaw=yaw)
                for name, e in REG.effects.items():
                    if e.zone == "face":
                        yield f"{name} at yaw {yaw:+.0f} on {b}", dict(base=b, effects=[name], motion="idle", yaw=yaw)


VIEW_YAWS = (20.0, 45.0, 90.0, 180.0, -90.0)
TURNED_YAWS = (90.0, -90.0, 180.0)


def view_proportions(base):
    """L15 for one mascot's drawn views: problems (sentences) where a view leaves the front's guide lines."""
    from mascot.views import view_proxy
    ch = REG.bases[base].load()()
    out = []
    for view in ("side", "back"):
        if ch.view_data(view) is None:
            continue
        p = view_proxy(ch, view)
        top = min(y for _, y in p.head_outline().v)
        if abs(top - ch.crown[1]) > 4.0:
            out.append(f"{view} view: the head's top is at {top:.0f}, the front's crown at {ch.crown[1]:.0f} (more than 4 px)")
        for s in p.view_sides:
            ey, fy = p.side(p.eye, s)[1], ch.side(ch.eye, s)[1]
            if abs(ey - fy) > 3.0:
                out.append(f"{view} view: the eye line is at {ey:.0f}, the front's at {fy:.0f} (more than 3 px)")
        near = p.view_sides[0] if p.view_sides else "R"
        if p.leg is not None and abs(p.side(p.foot, near)[1] - ch.side(ch.foot, "R")[1]) > 1e-6:
            out.append(f"{view} view: the near foot is not on the ground the front stands on")
    return out


def sheet(specs, out, cols=6, size=170):
    from PIL import Image, ImageDraw
    rows = []
    for label, d in specs:
        try:
            doc, info = compose(StickerSpec.from_dict(d))
            L = int(doc["op"])
            ims = _render(doc, [int(L * q / cols) for q in range(cols)], size)
            rows.append((label, ims, info.get("notes", [])))
        except Exception as e:  # noqa: BLE001
            rows.append((f"{label}: {type(e).__name__}: {e}", [], []))
    img = Image.new("RGB", (cols * size, len(rows) * (size + 16)), (236, 238, 242))
    d = ImageDraw.Draw(img)
    for r, (label, ims, notes) in enumerate(rows):
        y = r * (size + 16)
        d.text((3, y + 2), (label + ("  - " + "; ".join(notes) if notes else ""))[:150], fill=(20, 20, 20))
        for k, im in enumerate(ims):
            tile = Image.new("RGBA", (size, size), (255, 255, 255, 255))
            tile.alpha_composite(Image.fromarray(im.astype(np.uint8), "RGBA"))
            img.paste(tile.convert("RGB"), (k * size, y + 16))
    img.save(out)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kind", default="all", help="motions, props, effects, wear, faces, views, turned, seconds or all")
    ap.add_argument("--bases", default="", help="comma-separated mascots (default: all)")
    ap.add_argument("--only", default="", help="comma-separated item names")
    ap.add_argument("--sheet", default="", help="write a contact sheet instead of checking")
    ap.add_argument("--json", default="", help="write the results as JSON")
    a = ap.parse_args(argv)
    kinds = ["motions", "props", "effects", "wear", "faces", "views", "turned"] if a.kind == "all" else a.kind.split(",")
    bases = [b for b in a.bases.split(",") if b] or None
    only = {x for x in a.only.split(",") if x}
    todo = [(lab, d) for k in kinds for lab, d in cases(k, bases) if not only or lab.split(" ")[0] in only]
    if a.sheet:
        print(sheet(todo, a.sheet))
        return 0
    bad, results = 0, {}
    t0 = time.time()
    drawn = 0
    if "views" in kinds:                               # L15: the drawn views keep the front's guide lines
        for b in bases or list(REG.bases):
            for problem in view_proportions(b):
                drawn += 1
                print(f"PROBLEM {b}: {problem}", flush=True)
    for label, d in todo:
        problems, stats = check(StickerSpec.from_dict(d))
        results[label] = dict(problems=problems, **stats)
        if problems:
            bad += 1
            print(f"PROBLEM {label}: {'; '.join(problems)}", flush=True)
    print(f"{len(todo) - bad}/{len(todo)} fine in {time.time() - t0:.0f} s" + (f"; {drawn} drawn-view proportion problems" if drawn else ""))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(results, f, indent=1)
    return 1 if bad or drawn else 0


if __name__ == "__main__":
    sys.exit(main())
