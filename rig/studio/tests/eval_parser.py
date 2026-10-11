#!/usr/bin/env python3
"""How often the rules (no LLM) give the sticker a person meant.  Reads golden.yaml, prints misses and the hit rate.

    python3 -m studio.tests.eval_parser [--min 0.9]
"""
from __future__ import annotations

import argparse
import os
import sys

from ..parse.fallback import parse
from ..parse.parser import Parser, load_yaml

HERE = os.path.dirname(os.path.abspath(__file__))


def check(spec, expect):
    bad = []
    for slot, want in expect.items():
        have = getattr(spec, slot)
        if slot in ("props", "effects"):
            missing = [w for w in want if w not in have]
            if missing:
                bad.append(f"{slot} lacks {missing} (has {have})")
        elif slot == "palette":
            if bool(have) != bool(want):
                bad.append(f"palette {'missing' if want else 'unexpected'}")
        elif have != want:
            bad.append(f"{slot}={have!r}, wanted {want!r}")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=float, default=0.0, help="exit 1 below this hit rate")
    a = ap.parse_args(argv)
    os.environ.setdefault("STUDIO_CACHE", os.path.join(HERE, ".cache"))
    p = Parser()
    cases = load_yaml(os.path.join(HERE, "golden.yaml"))
    hits = 0
    for case in cases:
        r = parse(case["prompt"], p, llm=False)
        bad = check(r.spec, case["expect"])
        if bad:
            print(f"MISS {case['prompt']!r:<34} {'; '.join(bad)}   [{r.source}, template={r.template}]")
        else:
            hits += 1
    rate = hits / len(cases)
    print(f"\n{hits}/{len(cases)} prompts right without the LLM: {rate:.0%}")
    return 0 if rate >= a.min else 1


if __name__ == "__main__":
    sys.exit(main())
