#!/usr/bin/env python3
"""Design iteration: render several pose / parameter variants side by side.

Usage: variants.py out.png name1:'k=v;k=v' name2:...     keys: arm.L / arm.R / arms (pose tuple or name), tail, face,
       scale, any channel, or attr:<Character attribute path>=<python literal>
"""
import ast, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from PIL import Image, ImageDraw
import lr
from render_sheet import font
from mascot.clip import Clip
from mascot.rig import FACES
from mascot.characters.biscuit import Biscuit


def build(spec, name):
    class V(Biscuit):
        pass
    V.arm = dict(Biscuit.arm)
    V.tail = dict(Biscuit.tail); V.tail["poses"] = dict(Biscuit.tail["poses"])
    V.pal = dict(Biscuit.pal)
    V.leg = dict(Biscuit.leg); V.stances = dict(Biscuit.stances)
    V.hip = dict(Biscuit.hip); V.foot = dict(Biscuit.foot); V.shoulder = dict(Biscuit.shoulder)
    char = V()
    c = Clip(name, 2, loop=False, char=char)
    for item in [s for s in spec.split(";") if s.strip()]:
        k, v = item.split("=", 1)
        k = k.strip()
        if k == "face":
            for ck, cv in FACES[v].items():
                c.set(ck, cv)
        elif k in ("arm.L", "arm.R", "arms"):
            p = v if v in char.arm_poses else ast.literal_eval(v)
            c.arm("LR" if k == "arms" else k[-1], (0, p))
        elif k == "tail":
            c.tailpose((0, v if v in char.tail["poses"] else ast.literal_eval(v)))
        elif k == "stance":
            c.stance((0, v if v in char.stances else ast.literal_eval(v)))
        elif k == "scale":
            c.scale = float(v)
        elif k.startswith("attr:"):
            path = k[5:].split(".")
            obj = char
            for part in path[:-1]:
                obj = obj[part] if isinstance(obj, dict) else getattr(obj, part)
            val = ast.literal_eval(v)
            if isinstance(obj, dict):
                obj[path[-1]] = val
            else:
                setattr(type(char), path[-1], val)
        else:
            c.set(k, float(v))
    return char.build(c)


if __name__ == "__main__":
    out = sys.argv[1]
    size = 384
    jobs = []
    for arg in sys.argv[2:]:
        name, _, spec = arg.partition(":")
        jobs.append((name, build(spec, name), [0]))
    rows, errs = lr.render(jobs, size, "#f4efe9", 1.0)
    cols = min(4, len(rows))
    nrow = (len(rows) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * size, nrow * (size + 22)), "white")
    d = ImageDraw.Draw(sheet)
    for k, (name, total, imgs) in enumerate(rows):
        x, y = (k % cols) * size, (k // cols) * (size + 22)
        d.rectangle([x, y, x + size, y + 22], fill="#222")
        d.text((x + 6, y + 4), name, fill="white", font=font(13))
        sheet.paste(imgs[0][1], (x, y + 22))
    sheet.save(out)
    print("wrote", out, sheet.size)
