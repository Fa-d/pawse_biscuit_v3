#!/usr/bin/env python3
"""How often the rules (no LLM) give the sticker a person meant.  Reads golden.yaml, prints misses and hit rates.

    python3 -m studio.tests.eval_parser [--min 0.9] [--tag misfire] [--quiet]

A case:
    - prompt: "sleepy fox with coffee"
      expect: {face: [sleep, drowsy], props: [mug]}       # scalar: the value, or a list of acceptable values
                                                           # props/effects/accessories: must include these
      not: {face: [scared], effects: [sweat]}              # must not be / must not include
      tag: misfire                                         # optional group for the report

Expectations understood: face, motion, stance, tail, arm_L, arm_R, base (scalars), props, effects, accessories (lists),
palette (true/false: fur recoloured), tints ({item: true or '#rrggbb'}), sides ({prop: L/R}), look ([x, y]),
tempo ('fast' / 'slow' / 'normal'), intensity ('strong' / 'weak' / 'normal'), caption (text, or false for none),
template (name or null), confident (true/false), fur (true/false: the fur itself recoloured, not only the eyes).
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

from ..parse.fallback import parse
from ..parse.parser import Parser, load_yaml

HERE = os.path.dirname(os.path.abspath(__file__))
LISTS = ("props", "effects", "accessories")


def _flag(v):
    """golden.yaml is read without YAML booleans ('no' is a motion), so true/false arrive as text."""
    return {"true": True, "false": False}.get(v, v) if isinstance(v, str) else v


def check(result, expect, forbid=None):
    spec = result.spec
    bad = []
    for slot, want in (expect or {}).items():
        want = _flag(want)
        if slot in LISTS:
            have = getattr(spec, slot)
            missing = [w for w in want if w not in have]
            if missing:
                bad.append(f"{slot} lacks {missing} (has {have})")
        elif slot == "palette":
            if bool(spec.palette) != bool(want):
                bad.append(f"palette {'missing' if want else 'unexpected: ' + str(spec.palette)}")
        elif slot == "fur":
            if ("orange" in spec.palette) != bool(want):
                bad.append(f"fur colour {'missing' if want else 'unexpected: ' + str(spec.palette)}")
        elif slot == "tints":
            for item, v in want.items():
                v = _flag(v)
                got = spec.tints.get(item)
                if not got or (isinstance(v, str) and got.lower() != v.lower()):
                    bad.append(f"tint of {item}: {got!r}, wanted {v!r}")
        elif slot == "sides":
            for item, v in want.items():
                if spec.sides.get(item) != v:
                    bad.append(f"side of {item}: {spec.sides.get(item)!r}, wanted {v!r}")
        elif slot == "look":
            if tuple(round(x, 2) for x in spec.look) != tuple(float(x) for x in want):
                bad.append(f"look {spec.look}, wanted {tuple(want)}")
        elif slot == "tempo":
            have = "fast" if spec.tempo > 1.01 else "slow" if spec.tempo < 0.99 else "normal"
            if have != want:
                bad.append(f"tempo {spec.tempo} ({have}), wanted {want}")
        elif slot == "intensity":
            have = "strong" if spec.intensity > 1.01 else "weak" if spec.intensity < 0.99 else "normal"
            if have != want:
                bad.append(f"intensity {spec.intensity} ({have}), wanted {want}")
        elif slot == "caption":
            have = spec.caption.text if spec.caption else False
            if have != want:
                bad.append(f"caption {have!r}, wanted {want!r}")
        elif slot == "template":
            if result.template != want:
                bad.append(f"template {result.template!r}, wanted {want!r}")
        elif slot == "confident":
            if result.confident != want:
                bad.append(f"confident={result.confident}, wanted {want}")
        else:
            have = getattr(spec, slot)
            ok = have in want if isinstance(want, list) else have == want
            if not ok:
                bad.append(f"{slot}={have!r}, wanted {want!r}")
    for slot, never in (forbid or {}).items():
        never = never if isinstance(never, list) else [never]
        if slot in LISTS:
            hit = [x for x in getattr(spec, slot) if x in never]
            if hit:
                bad.append(f"{slot} must not have {hit}")
        elif slot == "palette":
            if spec.palette:
                bad.append(f"palette must stay as it is (got {spec.palette})")
        elif slot == "tints":
            for item in (never[0] if never and isinstance(never[0], dict) else {}):
                if spec.tints.get(item):
                    bad.append(f"{item} must keep its own colour (got {spec.tints[item]})")
        elif slot == "template":
            if result.template in never:
                bad.append(f"template must not be {result.template!r}")
        else:
            if getattr(spec, slot) in never:
                bad.append(f"{slot} must not be {getattr(spec, slot)!r}")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=float, default=0.0, help="exit 1 below this hit rate")
    ap.add_argument("--tag", default=None, help="only cases with this tag")
    ap.add_argument("--quiet", action="store_true", help="only the summary")
    a = ap.parse_args(argv)
    os.environ.setdefault("STUDIO_CACHE", os.path.join(HERE, ".cache"))
    p = Parser()
    cases = load_yaml(os.path.join(HERE, "golden.yaml"))
    if a.tag:
        cases = [c for c in cases if c.get("tag") == a.tag]
    hits = 0
    by_tag = defaultdict(lambda: [0, 0])
    for case in cases:
        r = parse(case["prompt"], p, llm=False)
        bad = check(r, case.get("expect"), case.get("not"))
        tag = case.get("tag", "-")
        by_tag[tag][1] += 1
        if bad:
            if not a.quiet:
                print(f"MISS {case['prompt']!r:<40} {'; '.join(bad)}   [{r.source}, template={r.template}]")
        else:
            hits += 1
            by_tag[tag][0] += 1
    rate = hits / max(1, len(cases))
    print()
    for tag, (h, n) in sorted(by_tag.items()):
        print(f"  {tag:<14} {h:>4}/{n:<4} {h / n:.0%}")
    print(f"\n{hits}/{len(cases)} prompts right without the LLM: {rate:.1%}")
    return 0 if rate >= a.min else 1


if __name__ == "__main__":
    sys.exit(main())
