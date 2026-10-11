#!/usr/bin/env python3
"""Rig test: build every clip for two throwaway mascots that differ from Biscuit in the ways a new mascot might.

  bun   - no tail, long floppy ears, other colours, wider stance, longer legs
  blob  - no legs at all (leg = None): feet hang from the body, no tail

Neither is a design.  The point is that all clips build and play without touching a single clip.

Usage: smoke_test.py [outdir]   (writes Lottie files and a contact sheet)
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from mascot import build as B
from mascot.characters.biscuit import Biscuit
from mascot.geom import smooth
from mascot.lottie import el, fl, gr, rgb, sh


class Bun(Biscuit):
    name = "bun"
    tail = None
    pal = dict(Biscuit.pal, orange=rgb("#B7A6E8"), arm=rgb("#A391DC"), leg=rgb("#A391DC"), stripe=rgb("#8A76CC"), dark=rgb("#4A3F6B"),
               iris=rgb("#6B5BA8"), cream=rgb("#FBF7FF"))
    hip = {"R": (298.0, 396.0)}
    foot = {"R": (306.0, 444.0)}
    leg = dict(Biscuit.leg, w=34.0)
    dyn = {"ear.freq": 1.5, "ear.damp": 0.2, "ear.rot": 1.3, "ear.y": 0.9, "ear.max": 48.0}
    EAR_R = [(300, 150), (318, 60), (338, -4), (360, -30), (378, -22), (388, 30), (384, 110), (366, 184)]


class Blob(Biscuit):
    name = "blob"
    tail = None
    leg = None
    pelvis = (256.0, 470.0)
    pal = dict(Biscuit.pal, orange=rgb("#58C4A7"), arm=rgb("#46B294"), stripe=rgb("#2F9C7E"), cream=rgb("#F1FFF9"))
    BODY_R = [(0, 284), (50, 290), (74, 326), (86, 384), (88, 430), (72, 462), (30, 470), (0, 470)]
    foot = {"R": (300.0, 452.0)}

    def body_shapes(self):
        body = smooth([(256 + dx, y) for dx, y in self.BODY_R] + [(256 - dx, y) for dx, y in reversed(self.BODY_R[1:-1])], closed=True, tension=0.36)
        return [gr("belly", [el((256, 400), (100, 110)), fl(self.pal["cream"])]), gr("body", [sh(body), fl(self.pal["orange"])])]

    def foot_shapes(self, side):
        c = self.side(self.foot, side)
        k = 1.0 if side == "R" else -1.0
        beans = [el((-15, -8), (10, 11)), el((0, -14), (10, 11)), el((15, -8), (10, 11)), el((0, 7), (28, 19)), fl(self.pal["pink"])]
        return [gr("pads", beans, p=c, r=k * 10), gr("foot", [el((0, 0), (62, 46)), fl(self.pal["dark"])], p=c, r=k * 10)]


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "out/smoke"
    os.makedirs(out, exist_ok=True)
    reg = B.registry()
    bad = 0
    for cls in (Bun, Blob):
        for key in reg:
            try:
                doc = B.build_clip(cls(), key)
                json.dump(doc, open(os.path.join(out, f"{doc['nm']}.json"), "w"), separators=(",", ":"))
            except Exception as e:   # noqa: BLE001 - report every failure, then exit non-zero
                bad += 1
                print(f"FAILED {cls.name} {key}: {type(e).__name__}: {e}")
        print(f"{cls.name}: built {len(reg)} clips")
    print("all clips built" if not bad else f"{bad} clips failed")
    sys.exit(1 if bad else 0)
