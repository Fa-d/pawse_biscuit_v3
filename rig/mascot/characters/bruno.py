"""Bruno the bear -- character definition.

Built on Biscuit's body and joints (same proportions, so every pose and clip fits).  A bear has round ears,
a broad round head with a big pale muzzle, no head tuft and a short stub of a tail.
"""
from __future__ import annotations

from ..geom import smooth
from ..lottie import el, fl, gr, rgb, sh
from .biscuit import Biscuit, mirror_half


class Bruno(Biscuit):
    name = "bruno"

    pal = dict(
        orange=rgb("#B07A4F"),
        arm=rgb("#A06B42"),
        leg=rgb("#A06B42"),
        tail=rgb("#A06B42"),
        stripe=rgb("#7E5333"),
        cream=rgb("#F3DFC6"),
        tail_tip=rgb("#A06B42"),
        dark=rgb("#3A2A22"),
        iris=rgb("#6A4632"),
        pink=rgb("#FF9AA2"),
        white=[1.0, 1.0, 1.0],
        blush_o=55,
    )

    HEAD_R = [(0, 116), (64, 120), (110, 148), (132, 194), (136, 236), (126, 270), (100, 296), (58, 312), (0, 318)]
    ear_pivot = {"R": (344.0, 146.0)}
    crown = (256.0, 116.0)
    tuft_pivot = (256.0, 118.0)
    nose = (256.0, 262.0)

    # a short round stub: same pose names as every other tail, it just barely shows
    tail = dict(
        Biscuit.tail,
        length=54.0,
        bones=4,
        profile=[(0.0, 44.0), (0.5, 54.0), (1.0, 40.0)],
        tip_from=1.5,
        tip_r=18.0,
        tip_ext=4.0,
        furry=False,
    )
    dyn = {"ear.rot": 0.45, "ear.max": 14.0, "tail.rot": 0.3}

    def head_outline(self):
        return smooth(mirror_half(self.HEAD_R), closed=True, tension=0.36)

    def head_shapes(self):
        pal = self.pal
        return [
            gr("head shine", [el((0, 0), (84, 32)), fl(pal["white"], 20)], p=(204, 152), r=-16),
            gr("muzzle", [el((256, 278), (118, 82)), fl(pal["cream"])]),
            gr("head", [sh(self.head_outline()), fl(pal["orange"])]),
        ]

    def tuft_shapes(self):
        return []

    def ear_shapes(self, side):
        pal = self.pal
        c = self.side(self.ear_pivot, side)
        cx, cy = c[0] + (14 if side == "R" else -14), c[1] - 26
        return [
            gr("inner ear", [el((cx, cy + 4), (38, 36)), fl(pal["cream"])]),
            gr("ear", [el((cx, cy), (66, 64)), fl(pal["orange"])]),
        ]

    def face_static(self):
        return []

    def body_shapes(self):
        pal = self.pal
        body = smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)
        return [
            gr("belly", [el((256, 364), (104, 92)), fl(pal["cream"])]),
            gr("body", [sh(body), fl(pal["orange"])]),
        ]


