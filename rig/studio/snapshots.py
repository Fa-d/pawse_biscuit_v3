#!/usr/bin/env python3
"""Snapshot corpus: proof that one-mascot output does not change while v5 is built (rule L17).

A fixed corpus of about 300 one-mascot stickers (every motion, prop, effect and worn item, every mascot, captions,
colours), the app's 23 clips on Biscuit, three clips on every other mascot and the 4 small effects is built, and a
hash of each Lottie document is compared with the hashes recorded from the v4 code.

    python -m studio.snapshots --check           # build everything, compare, list each difference (exit 1 on any)
    python -m studio.snapshots --check --only clips
    python -m studio.snapshots --record          # write studio/tests/snapshots.json from the current code

Record only from code whose output is known to be right (the v4 code at ea22b21 for the corpus in the repo).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, "tests", "snapshots.json")
APP_CLIP_SAMPLE = ("idle", "wave", "sleepy")          # clips built on every mascot other than Biscuit


def digest(doc):
    """Stable hash of a Lottie document (the JSON as the exporters write it; .tgs adds a gzip header with a time)."""
    return hashlib.sha256(json.dumps(doc, separators=(",", ":")).encode()).hexdigest()


def corpus():
    """[(id, kind, payload)] in a fixed order.  kind: 'sticker' (a StickerSpec dict), 'clip' ((mascot, clip)), 'effect'."""
    from mascot.build import MASCOTS, registry
    from mascot.effects import EFFECTS
    from studio.registry import ensure_loaded

    reg = ensure_loaded()
    bases = list(reg.bases)
    items = []

    def sticker(name, **kw):
        items.append((f"sticker:{name}", "sticker", kw))

    for m in reg.motions:                                           # every motion on the fox, standing
        sticker(f"motion:{m}", motion=m)
    for q, b in enumerate(bases):                                   # every mascot, waving and sitting
        sticker(f"base:{b}:wave", base=b, motion="wave")
        sticker(f"base:{b}:sit", base=b, stance="sit", motion="sway", face="calm")
    for q, p in enumerate(reg.props):                               # every held prop, on a rotating mascot
        sticker(f"prop:{p}", base=bases[q % len(bases)], props=[p])
    for q, e in enumerate(reg.effects):
        sticker(f"effect:{e}", base=bases[(q + 3) % len(bases)], effects=[e])
    for q, w in enumerate(reg.wear):
        sticker(f"wear:{w}", base=bases[(q + 7) % len(bases)], accessories=[w])
    for style in ("outline", "bubble"):
        for pos in ("bottom", "top"):
            sticker(f"caption:{style}:{pos}", motion="cheer", caption={"text": "good morning!", "style": style, "pos": pos})
    sticker("colour:purple-cat", base="mochi", palette={"orange": "#8a6fdf"}, props=["mug"], tints={"mug": "#4ecdc4"})
    sticker("colour:black-dog", base="pip", palette={"orange": "#2b2730"}, motion="dance")
    sticker("sides:left-paw", props=["phone"], sides={"phone": "L"}, motion="wave")
    sticker("busy:monday", base="mochi", motion="nod_off", stance="sit", face="drowsy", props=["mug"], accessories=["scarf"],
            effects=["zzz"], caption={"text": "monday again"})
    sticker("gift:3s", props=["gift"], effects=["confetti"], seconds=3.0)
    sticker("tempo:fast-dance", base="leo", motion="dance", tempo=1.8, intensity=1.5)
    sticker("short:1s-jump", base="clover", motion="jump", seconds=1.0)

    for clip in registry():                                         # the app's clips
        items.append((f"clip:biscuit:{clip}", "clip", ("biscuit", clip)))
    for m in MASCOTS:
        if m != "biscuit":
            for clip in APP_CLIP_SAMPLE:
                items.append((f"clip:{m}:{clip}", "clip", (m, clip)))
    for name in EFFECTS:
        items.append((f"effect-file:{name}", "effect", name))
    return items


def build(item):
    """(id, digest, size of the .tgs or json in bytes, seconds)."""
    ident, kind, payload = item
    t0 = time.time()
    if kind == "sticker":
        from studio.compose import compose
        from studio.export import tgs_bytes
        from studio.spec import StickerSpec
        doc, _ = compose(StickerSpec.from_dict(payload))
        size = len(tgs_bytes(doc))
    elif kind == "clip":
        from mascot.build import build_clip, characters
        mascot, clip = payload
        doc = build_clip(characters()[mascot](), clip)
        size = len(json.dumps(doc, separators=(",", ":")))
    else:
        from mascot.effects import EFFECTS
        doc = EFFECTS[payload]()
        size = len(json.dumps(doc, separators=(",", ":")))
    return ident, digest(doc), size, time.time() - t0


def run(items, jobs):
    if jobs > 1 and len(items) > 1:
        import multiprocessing as mp
        with mp.Pool(jobs) as pool:
            return list(pool.imap(build, items, chunksize=4))
    return [build(it) for it in items]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    act = ap.add_mutually_exclusive_group(required=True)
    act.add_argument("--check", action="store_true")
    act.add_argument("--record", action="store_true")
    ap.add_argument("--only", choices=("stickers", "clips", "effects"), default=None)
    ap.add_argument("--jobs", type=int, default=0, help="worker processes (0 = one per CPU)")
    a = ap.parse_args(argv)
    os.environ.setdefault("STUDIO_CACHE", os.path.join(HERE, "cache"))
    items = corpus()
    if a.only:
        kind = {"stickers": "sticker", "clips": "clip", "effects": "effect"}[a.only]
        items = [it for it in items if it[1] == kind]
    t0 = time.time()
    results = run(items, a.jobs or os.cpu_count() or 1)
    took = time.time() - t0
    if a.record:
        if a.only:
            sys.exit("record the whole corpus at once (no --only), so the store never mixes code versions")
        store = {ident: {"sha256": h, "bytes": size} for ident, h, size, _ in results}
        with open(STORE, "w") as fh:
            json.dump(dict(note="hashes of the v4 output; python -m studio.snapshots --check compares", items=store), fh, indent=1,
                      sort_keys=True)
        print(f"recorded {len(store)} items in {took:.0f} s -> {os.path.relpath(STORE)}")
        return 0
    with open(STORE) as fh:
        known = json.load(fh)["items"]
    changed = [(ident, size) for ident, h, size, _ in results if ident in known and known[ident]["sha256"] != h]
    unknown = [ident for ident, *_ in results if ident not in known]
    missing = [ident for ident in known if (not a.only or ident.startswith({"stickers": "sticker:", "clips": "clip:",
                                                                                  "effects": "effect-file:"}[a.only]))
               and ident not in {r[0] for r in results}]
    for ident, size in changed:
        print(f"CHANGED  {ident}  (now {size} bytes, was {known[ident]['bytes']})")
    for ident in unknown:
        print(f"NEW      {ident}  (not in the store)")
    for ident in missing:
        print(f"MISSING  {ident}  (in the store, not built)")
    ok = not changed and not missing
    print(f"{len(results) - len(changed) - len(unknown)} of {len(results)} identical, {len(changed)} changed, {len(unknown)} new, "
          f"{len(missing)} missing; {took:.0f} s")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
