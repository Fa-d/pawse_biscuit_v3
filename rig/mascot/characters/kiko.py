"""Kiko the koala -- character definition.

Built on Bruno's round head and Biscuit's body.  Soft grey fur, big round fluffy ears with pale insides, a large
dark spoon-shaped nose, a pale belly and no tail to speak of.
"""
from __future__ import annotations

import math

from ..geom import smooth
from ..lottie import el, fl, gr, rgb, sh
from .biscuit import mirror_half
from .bruno import Bruno


class Kiko(Bruno):
    name = "kiko"

    pal = dict(
        orange=rgb("#A9AFBA"),
        arm=rgb("#9AA1AD"),
        leg=rgb("#9AA1AD"),
        tail=rgb("#9AA1AD"),
        stripe=rgb("#7F8794"),
        cream=rgb("#EEF0F4"),
        tail_tip=rgb("#9AA1AD"),
        dark=rgb("#2C2C34"),
        iris=rgb("#4A4A56"),
        pink=rgb("#FFA4B0"),
        white=[1.0, 1.0, 1.0],
        blush_o=60,
    )
    HEAD_R = [(0, 118), (66, 122), (112, 150), (134, 196), (138, 238), (126, 272), (100, 298), (58, 314), (0, 320)]
    ear_pivot = {"R": (356.0, 162.0)}
    nose = (256.0, 252.0)
    mouth = (256.0, 282.0)
    tail = dict(Bruno.tail, length=20.0, profile=[(0.0, 28.0), (0.5, 32.0), (1.0, 24.0)], tip_r=12.0)
    dyn = {"ear.rot": 0.55, "ear.max": 16.0, "ear.damp": 0.3}

    def ear_shapes(self, side):
        pal = self.pal
        c = self.side(self.ear_pivot, side)
        k = 1 if side == "R" else -1
        cx, cy = c[0] + k * 34, c[1] - 26
        fluff = [el((cx + k * 18 * math.cos(a) + k * 6, cy + 18 * math.sin(a) + 4), (22, 22))
                 for a in (math.radians(d) for d in (-50, -15, 20, 55))]
        return [
            gr("fluff", fluff + [fl(pal["cream"])]),
            gr("inner ear", [el((cx + k * 6, cy + 4), (54, 54)), fl(pal["cream"], 90)]),
            gr("ear", [el((cx, cy), (104, 100)), fl(pal["orange"])]),
        ]

    def head_shapes(self):
        pal = self.pal
        return [
            gr("head shine", [el((0, 0), (84, 32)), fl(pal["white"], 22)], p=(204, 156), r=-16),
            gr("chin", [el((256, 296), (90, 48)), fl(pal["cream"])]),
            gr("head", [sh(self.head_outline()), fl(pal["orange"])]),
        ]

    def nose_shapes(self):
        pal = self.pal
        x, y = self.nose
        nose = smooth([(x - 20, y - 18), (x, y - 22), (x + 20, y - 18), (x + 24, y + 4), (x + 12, y + 20), (x, y + 23), (x - 12, y + 20),
                       (x - 24, y + 4)], closed=True, tension=0.38)
        return [
            gr("nose shine", [el((x - 9, y - 10), (10, 6)), fl(pal["white"], 50)], r=-20),
            gr("nose", [sh(nose), fl(pal["dark"])]),
        ]

    def body_shapes(self):
        pal = self.pal
        body = smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)
        return [
            gr("belly", [el((256, 366), (100, 90)), fl(pal["cream"])]),
            gr("body", [sh(body), fl(pal["orange"])]),
        ]
