"""Leo the lion -- character definition.

Built on Bruno's round head and Biscuit's body.  Golden fur, a big scalloped mane around the head (drawn with the
head, so it follows every turn; the small round ears sit on the mane and are drawn with it too), a pale muzzle and a
long thin tail ending in a dark tuft.
"""
from __future__ import annotations

import math

from ..geom import smooth
from ..lottie import el, fl, gr, rgb, sh
from .biscuit import Biscuit, mirror_half
from .bruno import Bruno


class Leo(Bruno):
    name = "leo"

    pal = dict(
        orange=rgb("#F4B64C"),
        arm=rgb("#E9A83D"),
        leg=rgb("#E9A83D"),
        tail=rgb("#E9A83D"),
        stripe=rgb("#C9862A"),
        cream=rgb("#FFF1D4"),
        tail_tip=rgb("#9A4E22"),
        dark=rgb("#3B2A20"),
        iris=rgb("#7A5230"),
        pink=rgb("#FF9AA2"),
        white=[1.0, 1.0, 1.0],
        mane=rgb("#C96E2A"),
        blush_o=55,
    )
    HEAD_R = [(0, 128), (62, 132), (104, 158), (124, 198), (128, 236), (118, 270), (96, 296), (56, 312), (0, 318)]
    crown = (256.0, 124.0)
    top = (256.0, 62.0)                       # the mane rises well above the skull
    collar = (256.0, 360.0)                   # and hides the neck: neck things hang below it
    ear_pivot = {"R": (344.0, 140.0)}

    tail = dict(
        Biscuit.tail,
        length=210.0,
        bones=10,
        profile=[(0.0, 18.0), (0.7, 14.0), (0.84, 16.0), (0.92, 30.0), (1.0, 26.0)],
        tip_from=0.84,
        tip_r=13.0,
        tip_ext=8.0,
        furry=True,
    )
    dyn = {"tail.rot": 0.6}

    def mane(self):
        pal = self.pal
        cx, cy, rx, ry = 256.0, 210.0, 150.0, 118.0
        n = 14
        lobes = [el((cx + rx * math.cos(2 * math.pi * q / n), cy + ry * math.sin(2 * math.pi * q / n)), (78, 78)) for q in range(n)]
        return [gr("mane", lobes + [el((cx, cy), (2 * rx, 2 * ry)), fl(pal["mane"])])]

    def head_shapes(self):
        pal = self.pal
        ears = []
        for sgn in (1, -1):
            cx, cy = 256 + sgn * 96, 136
            ears.append(gr("ear", [el((cx, cy + 4), (30, 28)), fl(pal["cream"])]))
            ears.append(gr("ear", [el((cx, cy), (58, 56)), fl(pal["orange"])]))
        return [
            gr("head shine", [el((0, 0), (80, 30)), fl(pal["white"], 22)], p=(206, 160), r=-16),
            gr("muzzle", [el((230, 282), (64, 48)), el((282, 282), (64, 48)), el((256, 300), (58, 30)), fl(pal["cream"])]),
            gr("head", [sh(self.head_outline()), fl(pal["orange"])]),
        ] + ears + self.mane()

    def ear_shapes(self, side):
        return []

    def body_shapes(self):
        pal = self.pal
        body = smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)
        return [
            gr("belly", [el((256, 366), (92, 86)), fl(pal["cream"])]),
            gr("body", [sh(body), fl(pal["orange"])]),
        ]
