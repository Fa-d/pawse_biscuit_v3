#!/usr/bin/env python3
"""Render the rest pose (or any channel overrides) of a mascot to a PNG for design iteration.

Usage: still.py out.png [--size 512] [--set ch=value ...] [--arm L=pose R=pose] [--tail pose] [--face name] [--stance sit] [--grid]
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from PIL import ImageDraw
import lr
from mascot.clip import Clip
from mascot.rig import FACES
from mascot.characters.biscuit import Biscuit


def make(char, sets=(), arms=(), tail=None, face=None, scale=1.0, name="still", stance=None):
    c = Clip(name, 2, loop=False, scale=scale, char=char)
    if stance:
        c.stance((0, stance))
    if face:
        for k, v in FACES[face].items():
            c.set(k, v)
    for s in sets:
        k, v = s.split("=")
        c.set(k, float(v))
    for a in arms:
        side, pose = a.split("=")
        c.arm(side, (0, pose if pose in char.arm_poses else tuple(float(x) for x in pose.split(","))))
    if tail:
        c.tailpose((0, tail if tail in char.tail["poses"] else tuple(float(x) for x in tail.split(","))))
    return char.build(c)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--set", nargs="*", default=[])
    ap.add_argument("--arm", nargs="*", default=[])
    ap.add_argument("--tail", default=None)
    ap.add_argument("--face", default=None)
    ap.add_argument("--stance", default=None)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--grid", action="store_true")
    ap.add_argument("--bg", default="#f4efe9")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    doc = make(Biscuit(), a.set, a.arm, a.tail, a.face, a.scale, stance=a.stance)
    if a.json:
        json.dump(doc, open(a.json, "w"), separators=(",", ":"))
    rows, errs = lr.render([("still", doc, [0])], a.size, a.bg, 1.0)
    im = rows[0][2][0][1]
    if a.grid:
        d = ImageDraw.Draw(im)
        k = a.size / 512
        for g in range(0, 513, 64):
            d.line([(g * k, 0), (g * k, a.size)], fill="#cfc6ba", width=1)
            d.line([(0, g * k), (a.size, g * k)], fill="#cfc6ba", width=1)
            d.text((g * k + 2, 2), str(g), fill="#9a8f80")
            d.text((2, g * k + 2), str(g), fill="#9a8f80")
    im.save(a.out)
    print("wrote", a.out)
