#!/usr/bin/env python3
"""Print how low / how far right each named tail pose reaches (rest coordinates), standing and sitting."""
import math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from mascot.characters.biscuit import Biscuit
from mascot.geom import pchip

c = Biscuit()
tl = c.tail
nb = tl["bones"]; Lb = tl["length"] / nb
xs, ys = zip(*tl["profile"])
radii = [0.5 * pchip(xs, ys, j / nb) for j in range(nb + 1)]
sit = c.stances["sit"][0]
for name, v in tl["poses"].items():
    v = list(v)
    nc = len(tl["poses"]["rest"])
    off = v[nc:] if len(v) > nc else [0, 0]
    heads = np.cumsum(v[:nc])
    xs_ = np.array([0.0] + [(k + 0.5) / nc for k in range(nc)] + [1.0])
    hs = np.concatenate([[heads[0]], heads, [heads[-1]]])
    us = np.array([(j + 0.5) / nb for j in range(nb)])
    hb = np.interp(us, xs_, hs)
    seated = name in ("ground", "ground_up", "wrap")
    x, y = tl["base"][0] + off[0], tl["base"][1] + off[1] + (sit if seated else 0.0)
    lo, hi, right, left = -1e9, 1e9, -1e9, 1e9
    for j in range(nb):
        r = radii[j]
        lo = max(lo, y + r); hi = min(hi, y - r); right = max(right, x + r); left = min(left, x - r)
        x += Lb * math.cos(math.radians(hb[j])); y -= Lb * math.sin(math.radians(hb[j]))
    r = tl.get("tip_r", 8) + 0
    ext = tl.get("tip_ext", 14)
    x += ext * math.cos(math.radians(hb[-1])); y -= ext * math.sin(math.radians(hb[-1]))
    lo = max(lo, y + r); hi = min(hi, y - r); right = max(right, x + r); left = min(left, x - r)
    print(f"{name:<10} {'sit ' if seated else 'stand'}  lowest y {lo:6.1f}   highest y {hi:6.1f}   x from {left:6.1f} to {right:6.1f}")
print("ground line 470; canvas right edge reached at x =", round(256 + (512 - 256) / 0.98, 1), "(scale 0.98)")
