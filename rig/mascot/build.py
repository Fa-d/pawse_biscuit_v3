#!/usr/bin/env python3
"""Build Lottie files for a mascot.

    python3 -m mascot.build --char biscuit [--only idle,wave] [--out dist]

Every clip in mascot/clips is character independent, so a new mascot only needs a new file in
mascot/characters/ and its name in MASCOTS below.
"""
from __future__ import annotations

import argparse
import json
import os
import time

from . import lottie
from .clip import Clip


MASCOTS = ("biscuit", "mochi", "bruno", "pip", "clover", "bao", "tora", "kiko", "rocco", "truffle", "fern", "pebble", "nib", "leo")


def characters():
    """name -> Character class, for every mascot (each lives in mascot/characters/<name>.py as its capitalised name)."""
    import importlib
    return {name: getattr(importlib.import_module(f".characters.{name}", __package__), name.capitalize()) for name in MASCOTS}


def registry():
    from .clips import core
    reg = dict(core.CLIPS)
    try:
        from .clips import alts
        reg.update(alts.CLIPS)
    except ImportError:
        pass
    return reg


def build_clip(char, key, spec=None):
    spec = spec or registry()[key]
    c = Clip(f"{char.name}_{key}", spec["frames"], loop=spec.get("loop", True), scale=spec.get("scale", 1.0), char=char)
    c.settle = bool(spec.get("settle", False))
    c.calm = int(spec.get("calm", 0))
    spec["fn"](c)
    if c.loop:
        check_loop(c)
    return char.build(c)


def check_loop(c):
    """A looping clip must end exactly where it starts."""
    import numpy as np
    bad = []
    for ch in set(c.tracks) | set(c.adds):
        tr = c.tracks.get(ch)
        a = tr.at(0) if tr and tr.keys else 0.0
        b = tr.at(c.frames) if tr and tr.keys else 0.0
        for fn in c.adds.get(ch, []):
            a = a + fn(0)
            b = b + fn(c.frames)
        if float(np.max(np.abs(np.asarray(a, dtype=float) - np.asarray(b, dtype=float)))) > 1e-6:
            bad.append(ch)
    if bad:
        raise ValueError(f"{c.name}: looping clip does not return to its start on {sorted(bad)}")


def _one(args):
    char_key, key, out = args
    t0 = time.time()
    char = characters()[char_key]()
    lottie.STATS.update(props=0, keys=0, fits=0, cache=0)
    doc = build_clip(char, key)
    path = os.path.join(out, f"{doc['nm']}.json")
    with open(path, "w") as f:
        json.dump(doc, f, separators=(",", ":"))
    st = lottie.STATS
    return (f"{doc['nm']:<34}{doc['op']:>4}f {len(doc['layers']):>3} layers {st['props']:>4} animated props {st['keys']:>5} keys"
            f" {os.path.getsize(path) / 1024:>7.1f} KB  {time.time() - t0:>5.1f}s", os.path.getsize(path))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--char", default="biscuit")
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default="dist")
    ap.add_argument("--jobs", type=int, default=0, help="parallel workers (0 = one per CPU)")
    a = ap.parse_args(argv)
    reg = registry()
    keys = [k for k in a.only.split(",") if k] or list(reg)
    out = os.path.join(a.out, a.char)
    os.makedirs(out, exist_ok=True)
    jobs = [(a.char, k, out) for k in keys]
    workers = a.jobs or os.cpu_count() or 1
    total = 0
    if workers > 1 and len(jobs) > 1:
        import multiprocessing as mp
        with mp.Pool(min(workers, len(jobs))) as pool:
            for line, size in pool.imap(_one, jobs):
                print(line, flush=True)
                total += size
    else:
        for j in jobs:
            line, size = _one(j)
            print(line, flush=True)
            total += size
    print(f"total {total / 1024:.1f} KB in {len(keys)} files -> {out}")


if __name__ == "__main__":
    main()
