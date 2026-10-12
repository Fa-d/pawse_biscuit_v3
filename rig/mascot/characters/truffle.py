"""Truffle the pig -- character definition.

Built on Bruno's round head and Biscuit's body.  Pink skin, a big round snout with two nostrils (the mouth sits
lower, under the snout), floppy ears that fold forward and a short curly tail.
"""
from __future__ import annotations

from ..geom import smooth
from ..lottie import el, fl, gr, rgb, sh, st
from .biscuit import CX, Biscuit, mirror_half
from .bruno import Bruno


class Truffle(Bruno):
    name = "truffle"

    pal = dict(
        orange=rgb("#FFB8C6"),
        arm=rgb("#F7A6B7"),
        leg=rgb("#F7A6B7"),
        tail=rgb("#F7A6B7"),
        stripe=rgb("#E98CA0"),
        cream=rgb("#FFD6DE"),
        tail_tip=rgb("#F7A6B7"),
        dark=rgb("#4A2C35"),
        iris=rgb("#6A3E4A"),
        pink=rgb("#FF7F9A"),
        white=[1.0, 1.0, 1.0],
        snout=rgb("#FF9DB1"),
        blush_o=55,
    )
    HEAD_R = [(0, 118), (66, 122), (112, 150), (134, 196), (138, 238), (128, 272), (102, 298), (58, 314), (0, 320)]
    ear_pivot = {"R": (338.0, 140.0)}
    nose = (256.0, 254.0)
    mouth = (256.0, 286.0)
    cheek = {"R": (360.0, 270.0)}

    # a thin tail that curls round on itself
    tail = dict(
        Biscuit.tail,
        base=(282.0, 392.0),
        length=86.0,
        bones=8,
        profile=[(0.0, 14.0), (1.0, 10.0)],
        tip_from=1.5,
        tip_r=5.0,
        tip_ext=2.0,
        furry=False,
        poses={**{k: (v[0], 70, 80, 80, 70) + tuple(v[5:]) for k, v in Biscuit.tail["poses"].items()},
               "rest": (-10, 70, 80, 80, 70), "up": (10, 70, 80, 80, 70), "low": (-40, 60, 70, 70, 60)},
    )
    dyn = {"ear.rot": 0.9, "ear.max": 22.0, "tail.rot": 0.4}

    def head_shapes(self):
        pal = self.pal
        return [
            gr("head shine", [el((0, 0), (84, 32)), fl(pal["white"], 26)], p=(204, 154), r=-16),
            gr("head", [sh(self.head_outline()), fl(pal["orange"])]),
        ]

    # floppy ears: they rise from the top of the head and fold over, tips pointing out and down
    EAR_R = [(300, 134), (318, 104), (350, 92), (388, 110), (414, 150), (404, 176), (378, 168), (344, 152)]

    def ear_shapes(self, side):
        pal = self.pal
        ear = smooth(self.EAR_R, closed=True, tension=0.34, sharp={4: 0.7})
        inner = smooth([(326, 128), (350, 108), (382, 120), (402, 156), (380, 154), (348, 140)], closed=True, tension=0.34, sharp={3: 0.6})
        if side == "L":
            ear, inner = ear.mirrored(CX), inner.mirrored(CX)
        return [
            gr("inner ear", [sh(inner), fl(pal["stripe"])]),
            gr("ear", [sh(ear), fl(pal["orange"])]),
        ]

    def nose_shapes(self):
        pal = self.pal
        x, y = self.nose
        return [
            gr("nostrils", [el((x - 11, y + 2), (9, 15)), el((x + 11, y + 2), (9, 15)), fl(pal["dark"], 70)]),
            gr("snout shine", [el((x - 14, y - 12), (16, 6)), fl(pal["white"], 50)], r=-10),
            gr("snout", [el((x, y), (64, 46)), fl(pal["snout"])]),
            gr("snout edge", [el((x, y), (64, 46)), st(pal["stripe"], 4)]),
        ]

    def body_shapes(self):
        pal = self.pal
        body = smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)
        return [
            gr("belly", [el((256, 366), (98, 88)), fl(pal["cream"])]),
            gr("body", [sh(body), fl(pal["orange"])]),
        ]
