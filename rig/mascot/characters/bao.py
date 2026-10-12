"""Bao the panda -- character definition.

Built on Bruno's round bear head and Biscuit's body.  White fur, black round ears, black eye patches (the upper
lids are painted in the patch colour so a sleepy panda's lids match), black arms, legs and a black band over the
shoulders, a short white tail.
"""
from __future__ import annotations

from ..geom import smooth
from ..lottie import el, fl, gr, rgb, sh
from .biscuit import mirror_half
from .bruno import Bruno


class Bao(Bruno):
    name = "bao"

    pal = dict(
        orange=rgb("#F7F6F2"),
        arm=rgb("#2E2D33"),
        leg=rgb("#2E2D33"),
        tail=rgb("#F7F6F2"),
        stripe=rgb("#2E2D33"),
        cream=rgb("#FFFFFF"),
        tail_tip=rgb("#F7F6F2"),
        dark=rgb("#1B1B20"),
        iris=rgb("#55515E"),
        pink=rgb("#FFB0C0"),
        white=[1.0, 1.0, 1.0],
        patch=rgb("#3A3842"),
        blush_o=60,
    )
    lid_color = "patch"

    def head_shapes(self):
        pal = self.pal
        patches = []
        for sgn in (1, -1):
            cx = 256 + sgn * 58
            patches.append(gr("patch", [el((0, 0), (78, 92)), fl(pal["patch"])], p=(cx, 232), r=sgn * -28))
        return patches + [
            gr("head shine", [el((0, 0), (84, 32)), fl(pal["white"], 60)], p=(204, 152), r=-16),
            gr("muzzle", [el((256, 280), (112, 76)), fl(pal["cream"])]),
            gr("head", [sh(self.head_outline()), fl(pal["orange"])]),
        ]

    def ear_shapes(self, side):
        pal = self.pal
        c = self.side(self.ear_pivot, side)
        cx, cy = c[0] + (14 if side == "R" else -14), c[1] - 26
        return [gr("ear", [el((cx, cy), (68, 66)), fl(pal["patch"])])]

    def body_shapes(self):
        pal = self.pal
        body = smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)
        band = smooth([(196, 300), (256, 292), (316, 300), (330, 336), (300, 330), (256, 326), (212, 330), (182, 336)], closed=True, tension=0.38)
        return [
            gr("belly", [el((256, 370), (100, 84)), fl(pal["cream"])]),
            gr("shoulder band", [sh(band), fl(pal["patch"])]),
            gr("body", [sh(body), fl(pal["orange"])]),
        ]
