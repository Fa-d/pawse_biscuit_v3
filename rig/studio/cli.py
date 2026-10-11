#!/usr/bin/env python3
"""Make a sticker from a sentence.

    python3 -m studio.cli "sleepy fox with coffee saying 'monday'" --out out/
    python3 -m studio.cli "happy birthday" --set face=surprised --set effects=confetti,sparkles --formats png,tgs,awebp
    python3 -m studio.cli --spec spec.json --out out/          # skip the parser: render a saved spec
    python3 -m studio.cli "..." --dry                           # only show what was understood

--set changes one slot after parsing, the same way an editor chip would.  --llm lets the fallback ask Claude Haiku
when the rules do not understand the prompt (needs Anthropic credentials; answers are cached).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

from .compose import compose
from .export import save
from .parse.fallback import parse
from .spec import Caption, StickerSpec


def apply_set(spec: StickerSpec, items):
    for item in items:
        k, _, v = item.partition("=")
        k = k.strip().replace(".", "_")
        if k in ("props", "effects", "accessories"):
            setattr(spec, k, [x for x in v.split(",") if x])
        elif k == "caption":
            spec.caption = Caption(v) if v else None
        elif k == "caption_style":
            spec.caption = Caption(spec.caption.text if spec.caption else "", style=v)
        elif k == "caption_pos":
            spec.caption = Caption(spec.caption.text if spec.caption else "", style=spec.caption.style if spec.caption else "outline", pos=v)
        elif k in ("intensity", "seconds"):
            setattr(spec, k, float(v))
        elif k == "look":
            spec.look = tuple(float(x) for x in v.split(","))
        elif k in StickerSpec.__dataclass_fields__:
            setattr(spec, k, v or None)
        else:
            raise SystemExit(f"--set: unknown slot {k!r}")
    return spec.validate()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", nargs="?", default="")
    ap.add_argument("--spec", help="render this spec (JSON file) instead of parsing a prompt")
    ap.add_argument("--set", action="append", default=[], metavar="SLOT=VALUE")
    ap.add_argument("--out", default="out")
    ap.add_argument("--name", default=None)
    ap.add_argument("--formats", default="png,webp,tgs,json", help="png, webp, tgs, awebp (WhatsApp), gif, json")
    ap.add_argument("--llm", action="store_true", help="allow the LLM fallback for prompts the rules do not understand")
    ap.add_argument("--no-auto-caption", action="store_true")
    ap.add_argument("--watermark", action="store_true", help="free-tier watermark on raster exports")
    ap.add_argument("--dry", action="store_true", help="print the spec and stop")
    a = ap.parse_args(argv)

    if a.spec:
        with open(a.spec) as f:
            spec = StickerSpec.from_dict(json.load(f))
        print("spec from", a.spec)
    elif a.prompt:
        r = parse(a.prompt, llm=a.llm, auto_caption=not a.no_auto_caption)
        print(r.explain())
        spec = r.spec
        if not r.confident:
            print("  (not sure what this means; showing a friendly default. Try other words, or --llm)", file=sys.stderr)
    else:
        ap.error("give a prompt or --spec")
    apply_set(spec, a.set)
    print("spec:", spec.to_json())
    if a.dry:
        return 0

    t = time.time()
    doc, info = compose(spec)
    for n in info["notes"]:
        print("  note:", n)
    name = a.name or spec.key()
    res = save(doc, a.out, name, formats=tuple(f.strip() for f in a.formats.split(",")), still=info["still"], mark=a.watermark)
    for fmt, (path, size, warn) in res.items():
        print(f"  {fmt:<6} {size / 1024:7.1f} KB  {path}{'   ! ' + warn if warn else ''}")
    print(f"done in {time.time() - t:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
