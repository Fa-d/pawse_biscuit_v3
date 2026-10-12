"""Rocco the raccoon -- character definition.

Built on Biscuit (the fox's pointed cheeks suit a raccoon).  Grey fur, a dark bandit mask over the eyes (the upper
lids are painted in the mask colour), pale brows and muzzle, small ears with pale rims and a bushy tail with dark
rings and a dark tip.
"""
from __future__ import annotations

from ..geom import smooth
from ..lottie import el, fl, gr, rgb, sh, st
from .biscuit import CX, Biscuit, mirror_half, scaled


class Rocco(Biscuit):
    name = "rocco"

    pal = dict(
        orange=rgb("#9C9BA8"),
        arm=rgb("#8D8C99"),
        leg=rgb("#8D8C99"),
        tail=rgb("#9C9BA8"),
        stripe=rgb("#3B3A45"),
        cream=rgb("#F3F2F5"),
        tail_tip=rgb("#3B3A45"),
        tail_ring=rgb("#3B3A45"),
        dark=rgb("#1F1E25"),
        iris=rgb("#5A4636"),
        pink=rgb("#FFA4B0"),
        white=[1.0, 1.0, 1.0],
        patch=rgb("#3B3A45"),
        blush_o=55,
    )
    lid_color = "patch"
    ear_pivot = {"R": (334.0, 146.0)}

    tail = dict(
        Biscuit.tail,
        profile=[(0.0, 34.0), (0.22, 54.0), (0.46, 66.0), (0.7, 66.0), (0.88, 54.0), (1.0, 30.0)],
        tip_from=0.86,
        furry=True,
        rings=[(0.14, 0.24), (0.34, 0.44), (0.54, 0.64), (0.72, 0.8)],
    )

    def head_shapes(self):
        pal = self.pal
        head = self.head_outline()
        mask = smooth([(150, 228), (176, 196), (220, 194), (256, 214), (292, 194), (336, 196), (362, 228), (348, 262), (306, 270), (256, 246),
                       (206, 270), (164, 262)], closed=True, tension=0.36, sharp={3: 0.5, 9: 0.5})
        return [
            gr("brows", [el((290, 176), (58, 20)), el((222, 176), (58, 20)), fl(pal["cream"])]),
            gr("mask", [sh(mask), fl(pal["patch"])]),
            gr("muzzle", [el((256, 282), (96, 60)), fl(pal["cream"])]),
            gr("cheeks", [el((340, 268), (70, 50)), el((172, 268), (70, 50)), fl(pal["cream"], 90)]),
            gr("head shine", [el((0, 0), (78, 30)), fl(pal["white"], 18)], p=(208, 140), r=-16),
            gr("head", [sh(head), fl(pal["orange"])]),
        ]

    def tuft_shapes(self):
        return []

    EAR_R = [(296, 132), (316, 92), (340, 70), (360, 66), (370, 82), (370, 118), (360, 160)]

    def ear_shapes(self, side):
        pal = self.pal
        ear = smooth(self.EAR_R, closed=True, tension=0.36, sharp={0: 0.0, 6: 0.0})
        inner = smooth(scaled(self.EAR_R, (346, 116), 0.62, (2, 6)), closed=True, tension=0.36)
        if side == "L":
            ear, inner = ear.mirrored(CX), inner.mirrored(CX)
        return [
            gr("inner ear", [sh(inner), fl(pal["patch"])]),
            gr("ear rim", [sh(ear), st(pal["cream"], 6)]),
            gr("ear", [sh(ear), fl(pal["orange"])]),
        ]

    def body_shapes(self):
        pal = self.pal
        body = smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)
        return [
            gr("belly", [el((256, 364), (90, 84)), fl(pal["cream"])]),
            gr("body", [sh(body), fl(pal["orange"])]),
        ]
