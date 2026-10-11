#!/usr/bin/env python3
"""Where do the bytes go?  Usage: sizes.py file.json"""
import json, sys
d = json.load(open(sys.argv[1]))
def sz(o): return len(json.dumps(o, separators=(",", ":")))
def walk(o, path, out):
    if isinstance(o, dict):
        if o.get("a") == 1 and isinstance(o.get("k"), list):
            out.append((sz(o), len(o["k"]), path))
            return
        for k, v in o.items():
            nm = o.get("nm") if k in ("it", "shapes", "ks") else None
            walk(v, path + ([f"{k}"] if not isinstance(v, list) else [k]), out)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            nm = v.get("nm") if isinstance(v, dict) and "nm" in v else str(i)
            walk(v, path + [nm], out)
print("total", sz(d))
rows = []
for L in d["layers"]:
    out = []
    walk(L, [], out)
    rows.append((sz(L), L["nm"], sum(o[0] for o in out), out))
for s, nm, an, out in sorted(rows, reverse=True):
    print(f"{s:>7} {nm:<18} animated {an:>6}")
    for o in sorted(out, reverse=True)[:6]:
        print(f"         {o[0]:>6}B {o[1]:>3} keys  {'/'.join(o[2])}")
