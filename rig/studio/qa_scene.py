#!/usr/bin/env python3
"""Quality checks for scenes of two mascots (rule L12), and contact sheets to look at them.

    python -m studio.qa_scene                        # every ordered pair of the 14 mascots (196 scenes), idle
    python -m studio.qa_scene --motion wave --bases biscuit,mochi,bao
    python -m studio.qa_scene --sheet out/pairs.png --bases biscuit,mochi,pip,leo

What is checked for each scene, as studio.qa checks one mascot:
  builds      the scene composes without an error
  loop        the last frame of the loop equals the first (measured on the picture, before the loop is turned)
  canvas      nothing is drawn within 2 px of the canvas edge after framing, in any sampled frame
  telegram    the .tgs file is under 64 KB
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

from mascot.clip import FPS
from mascot.scene import Scene

from .compose import build_clip
from .export import TGS_MAX, tgs_bytes
from .qa import SEAM_MAX, _render, edge_alpha
from .registry import REG
from .scene_compose import compose_scene, resolve_scene
from .scene_spec import ActorSpec, SceneSpec


def scene_seam(spec: SceneSpec):
    """Difference between frame 0 and frame L of the scene as acted (not turned), in mean |d| of 0..255 values."""
    plan = resolve_scene(spec.normalized())
    L = int(round(spec.seconds * FPS))
    sc = Scene("seam", frames=L, roll=0, fade_safe=True)
    for ident, s, st in zip(plan.ids, plan.stickers, plan.stages):
        c, char, _ = build_clip(s)
        c.opts["fade_safe"] = True
        sc.add(ident, char, c, st)
    doc = sc.build()
    a, b = _render(doc, [0, doc["op"]], size=160)
    return float(np.abs(a - b).mean())


def check(spec: SceneSpec):
    """(problems, stats) for one scene."""
    t = time.time()
    try:
        doc, info = compose_scene(spec)
    except Exception as e:  # noqa: BLE001 - report it
        return [f"does not build: {type(e).__name__}: {e}"], {}
    dt = time.time() - t
    out = []
    s = scene_seam(spec)
    if s > SEAM_MAX:
        out.append(f"loop seam {s:.2f}")
    e = edge_alpha(doc)
    if e > 40:
        out.append(f"touches the canvas edge (alpha {e})")
    size = len(tgs_bytes(doc))
    if size > TGS_MAX:
        out.append(f"{size / 1024:.0f} KB is over Telegram's 64 KB")
    return out, dict(seconds=round(dt, 2), seam=round(s, 3), tgs_kb=round(size / 1024, 1), layers=len(doc["layers"]),
                     frame=info.get("frame", {}).get("scale"), notes=info.get("notes", []))


def pairs(bases=None, **kw):
    """(label, SceneSpec) for every ordered pair of mascots, the same mascot twice included."""
    bases = bases or list(REG.bases)
    for a in bases:
        for b in bases:
            yield f"{a}+{b}", SceneSpec(actors=[ActorSpec(base=a, **kw), ActorSpec(base=b, **kw)])


def _one(item):
    label, d = item
    problems, stats = check(SceneSpec.from_dict(d))
    return label, problems, stats


def sheet(specs, out, cols=4, size=200):
    from PIL import Image, ImageDraw
    from .export import frame
    rows = []
    for label, spec in specs:
        doc, info = compose_scene(spec)
        L = int(doc["op"])
        rows.append((label, [frame(doc, int(L * q / cols), size=size) for q in range(cols)]))
    img = Image.new("RGB", (cols * size, len(rows) * (size + 16)), (236, 238, 242))
    d = ImageDraw.Draw(img)
    for r, (label, ims) in enumerate(rows):
        y = r * (size + 16)
        d.text((3, y + 2), label, fill=(20, 20, 20))
        for k, im in enumerate(ims):
            tile = Image.new("RGBA", (size, size), (255, 255, 255, 255))
            tile.alpha_composite(im)
            img.paste(tile.convert("RGB"), (k * size, y + 16))
    img.save(out)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bases", default="", help="comma-separated mascots (default: all 14, so 196 pairs)")
    ap.add_argument("--motion", default="idle")
    ap.add_argument("--stance", default="stand")
    ap.add_argument("--sheet", default="", help="write a contact sheet instead of checking")
    ap.add_argument("--json", default="", help="write the results as JSON")
    ap.add_argument("--jobs", type=int, default=0, help="worker processes (0 = one per CPU)")
    a = ap.parse_args(argv)
    bases = [b for b in a.bases.split(",") if b] or None
    todo = list(pairs(bases, motion=a.motion, stance=a.stance))
    if a.sheet:
        print(sheet(todo, a.sheet))
        return 0
    t0 = time.time()
    items = [(label, spec.to_dict()) for label, spec in todo]
    jobs = a.jobs or os.cpu_count() or 1
    if jobs > 1:
        import multiprocessing as mp
        with mp.Pool(jobs) as pool:
            results = list(pool.imap(_one, items, chunksize=2))
    else:
        results = [_one(it) for it in items]
    bad = 0
    out = {}
    for label, problems, stats in results:
        out[label] = dict(problems=problems, **stats)
        if problems:
            bad += 1
            print(f"PROBLEM {label}: {'; '.join(problems)}", flush=True)
    kb = [s.get("tgs_kb", 0) for _, _, s in results if s]
    secs = [s.get("seconds", 0) for _, _, s in results if s]
    print(f"{len(todo) - bad}/{len(todo)} fine in {time.time() - t0:.0f} s; .tgs {min(kb):.1f} to {max(kb):.1f} KB; "
          f"composed in {min(secs):.2f} to {max(secs):.2f} s each")
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(out, fh, indent=1)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
