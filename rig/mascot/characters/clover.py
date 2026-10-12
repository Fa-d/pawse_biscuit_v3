"""Clover the bunny -- character definition.

Built on Biscuit's body and joints.  A bunny has two tall ears with pink insides that wobble with every hop, a
round soft head with puffy cheeks, a tiny pink nose with whiskers and a round cotton tail.
"""
from __future__ import annotations

from ..geom import smooth
from ..lottie import Path, el, fl, gr, rgb, sh, st
from .biscuit import CX, Biscuit, mirror_half


class Clover(Biscuit):
    name = "clover"

    pal = dict(
        orange=rgb("#EEEAF2"),
        arm=rgb("#E2DCE9"),
        leg=rgb("#E2DCE9"),
        tail=rgb("#FFFFFF"),
        stripe=rgb("#C9BFD6"),
        cream=rgb("#FFFFFF"),
        tail_tip=rgb("#FFFFFF"),
        dark=rgb("#3A3644"),
        iris=rgb("#7E6A9E"),
        pink=rgb("#FF9AB8"),
        white=[1.0, 1.0, 1.0],
        blush_o=70,
    )

    HEAD_R = [(0, 120), (60, 124), (104, 150), (124, 192), (130, 232), (124, 266), (102, 294), (60, 312), (0, 318)]
    ear_pivot = {"R": (298.0, 132.0)}
    crown = (256.0, 120.0)
    tuft_pivot = (256.0, 122.0)
    nose = (256.0, 258.0)

    # a round puff: the stub tail of the bear, white and fluffy
    tail = dict(
        Biscuit.tail,
        base=(286.0, 396.0),
        length=26.0,
        bones=3,
        profile=[(0.0, 46.0), (0.5, 58.0), (1.0, 46.0)],
        tip_from=1.5,
        tip_r=26.0,
        tip_ext=2.0,
        furry=False,
    )
    dyn = {"ear.rot": 0.8, "ear.damp": 0.24, "ear.max": 26.0, "ear.freq": 2.2, "tail.rot": 0.3}

    def head_outline(self):
        return smooth(mirror_half(self.HEAD_R), closed=True, tension=0.36)

    def head_shapes(self):
        pal = self.pal
        return [
            gr("head shine", [el((0, 0), (78, 30)), fl(pal["white"], 30)], p=(206, 156), r=-16),
            gr("cheeks", [el((224, 280), (66, 50)), el((288, 280), (66, 50)), fl(pal["cream"])]),
            gr("head", [sh(self.head_outline()), fl(pal["orange"])]),
        ]

    def tuft_shapes(self):
        pal = self.pal
        pts = [(244, 128), (248, 108), (258, 100), (266, 110), (270, 128)]
        return [sh(smooth(pts, closed=True, tension=0.4)), fl(pal["orange"])]

    # a tall ear standing on the pivot, leaning out a little
    EAR_R = [(282, 140), (276, 92), (280, 40), (296, 4), (316, 0), (330, 30), (330, 88), (318, 142)]

    def ear_shapes(self, side):
        pal = self.pal
        ear = smooth(self.EAR_R, closed=True, tension=0.38, sharp={0: 0.2, 7: 0.2})
        inner = smooth([(292, 126), (290, 84), (294, 42), (304, 20), (314, 20), (320, 50), (318, 96), (310, 128)], closed=True, tension=0.38)
        if side == "L":
            ear, inner = ear.mirrored(CX), inner.mirrored(CX)
        k = 1 if side == "R" else -1
        return [gr("ear", [
            gr("inner ear", [sh(inner), fl(pal["pink"], 80)]),
            gr("ear", [sh(ear), fl(pal["orange"])]),
        ], a=self.side(self.ear_pivot, side), p=self.side(self.ear_pivot, side), r=k * 10)]

    def nose_shapes(self):
        pal = self.pal
        x, y = self.nose
        nose = smooth([(x - 9, y - 4), (x + 9, y - 4), (x, y + 6)], closed=True, tension=0.32)
        return [
            gr("nose shine", [el((x - 3, y - 3), (5, 2.5)), fl(pal["white"], 70)]),
            gr("nose", [sh(nose), fl(pal["pink"])]),
        ]

    def face_static(self):
        pal = self.pal
        w = []
        for sgn in (1, -1):
            for dy, tilt in ((-3, -5), (6, 4)):
                x0 = 256 + sgn * 40
                w.append(sh(Path([(x0, 270 + dy), (x0 + sgn * 46, 264 + dy + tilt)], i=[(0, 0), (-sgn * 16, -3)], o=[(sgn * 16, -3), (0, 0)],
                                 closed=False)))
        return [gr("whiskers", w + [st(pal["stripe"], 3, 80)])]

    def body_shapes(self):
        pal = self.pal
        body = smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)
        return [
            gr("belly", [el((256, 364), (96, 90)), fl(pal["cream"])]),
            gr("body", [sh(body), fl(pal["orange"])]),
        ]
