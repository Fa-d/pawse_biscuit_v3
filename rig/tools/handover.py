#!/usr/bin/env python3
"""Check the hand-overs between clips: the frame one clip ends on must equal the frame the next one starts on.

  hop_in (last frame)  ->  idle (first frame)
  every *_alt_* take   ->  first AND last frame equal the first frame of its base clip

Channels that cannot be seen in that frame (hidden brows, the depth slot of an arm that hangs at rest) are ignored.
Usage: handover.py [character]
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from mascot import build as B, rig
from mascot.clip import Clip


def evaluate(char_key, key):
    char = B.characters()[char_key]()
    spec = B.registry()[key]
    c = Clip(key, spec["frames"], loop=spec.get("loop", True), scale=spec.get("scale", 1.0), char=char)
    c.settle, c.calm = bool(spec.get("settle", False)), int(spec.get("calm", 0))
    spec["fn"](c)
    return rig.evaluate(c, char)


def diff(a, fa, b, fb):
    out = []
    for k in b:
        if k.endswith(".front") and not k.startswith("tail"):
            continue
        if k.startswith("brow.") and k != "brow.show" and a["brow.show"][fa] == 0 and b["brow.show"][fb] == 0:
            continue
        d = float(np.max(np.abs(np.asarray(a[k][fa], dtype=float) - np.asarray(b[k][fb], dtype=float))))
        if d > 0.02:
            out.append((round(d, 3), k))
    return sorted(out, reverse=True)


if __name__ == "__main__":
    ck = sys.argv[1] if len(sys.argv) > 1 else "biscuit"
    cache = {}
    get = lambda k: cache.setdefault(k, evaluate(ck, k))
    pairs = [("hop_in", -1, "idle", 0)]
    for key in B.registry():
        if "_alt_" in key:
            base = key.split("_alt_")[0]
            pairs += [(key, 0, base, 0), (key, -1, base, 0)]
    bad = 0
    for a, fa, b, fb in pairs:
        d = diff(get(a), fa, get(b), fb)
        bad += bool(d)
        print(f"{a:<20} {'first' if fa == 0 else 'last '} frame  vs  {b:<7} first frame:  {'identical' if not d else d[:6]}")
    sys.exit(1 if bad else 0)


def pixels(dist, char="biscuit", size=256):
    """Render the frames themselves and compare the pictures (catches props, layer order, anything outside the rig)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import lr
    load = lambda k: lr.load(os.path.join(dist, f"{char}_{k}.json"))
    reg = B.registry()
    keys = ["idle", "sleepy", "hop_in"] + [k for k in reg if "_alt_" in k]
    jobs = [(k, load(k), [0, reg[k]["frames"] - 1]) for k in keys]
    rows, _ = lr.render(jobs, size, "#f4efe9", 1.0)
    img = {name: {fi: np.asarray(im, dtype=np.int16) for fi, im in imgs} for name, total, imgs in rows}
    def d(a, fa, b):
        x = np.abs(img[a][fa] - img[b][0])
        return float((x.max(axis=2) > 24).mean() * 100)
    worst = 0.0
    for k in keys[2:]:
        base = "idle" if k == "hop_in" else k.split("_alt_")[0]
        last = reg[k]["frames"] - 1
        parts = [] if k == "hop_in" else [("first", d(k, 0, base))]
        parts.append(("last ", d(k, last, base)))
        for nm, v in parts:
            worst = max(worst, v)
            print(f"{k:<20} {nm} frame vs {base:<7} first frame: {v:.3f} % of pixels differ")
    return worst
