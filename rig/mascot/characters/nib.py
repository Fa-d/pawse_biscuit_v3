"""Nib the mouse -- character definition.

Built on Biscuit's body and joints.  Soft grey fur, two big round ears with pink insides, a small pink nose with
long whiskers, a pale belly and a long thin pink tail.
"""
from __future__ import annotations

from ..geom import smooth
from ..lottie import Path, el, fl, gr, rgb, sh, st
from .biscuit import Biscuit, mirror_half


class Nib(Biscuit):
    name = "nib"

    pal = dict(
        orange=rgb("#B9B5C2"),
        arm=rgb("#ABA6B5"),
        leg=rgb("#ABA6B5"),
        tail=rgb("#F2A9B9"),
        stripe=rgb("#9893A3"),
        cream=rgb("#F6F3F8"),
        tail_tip=rgb("#F2A9B9"),
        dark=rgb("#34313D"),
        iris=rgb("#5A5468"),
        pink=rgb("#FF9AB4"),
        white=[1.0, 1.0, 1.0],
        blush_o=65,
    )
    HEAD_R = [(0, 122), (60, 126), (102, 152), (120, 192), (124, 230), (116, 264), (94, 292), (54, 310), (0, 316)]
    ear_pivot = {"R": (338.0, 150.0)}
    crown = (256.0, 122.0)
    tuft_pivot = (256.0, 124.0)
    nose = (256.0, 256.0)

    tail = dict(
        Biscuit.tail,
        length=250.0,
        bones=12,
        profile=[(0.0, 12.0), (0.5, 9.0), (1.0, 6.0)],
        tip_from=1.5,
        tip_r=3.0,
        tip_ext=2.0,
        furry=False,
    )
    dyn = {"ear.rot": 0.7, "ear.max": 22.0}

    def head_outline(self):
        return smooth(mirror_half(self.HEAD_R), closed=True, tension=0.36)

    def head_shapes(self):
        pal = self.pal
        return [
            gr("head shine", [el((0, 0), (76, 28)), fl(pal["white"], 26)], p=(208, 156), r=-16),
            gr("muzzle", [el((256, 278), (84, 56)), fl(pal["cream"])]),
            gr("head", [sh(self.head_outline()), fl(pal["orange"])]),
        ]

    def tuft_shapes(self):
        return []

    def ear_shapes(self, side):
        pal = self.pal
        c = self.side(self.ear_pivot, side)
        k = 1 if side == "R" else -1
        cx, cy = c[0] + k * 30, c[1] - 52
        return [
            gr("inner ear", [el((cx + k * 4, cy + 6), (70, 70)), fl(pal["pink"], 85)]),
            gr("ear", [el((cx, cy), (110, 108)), fl(pal["orange"])]),
        ]

    def nose_shapes(self):
        pal = self.pal
        x, y = self.nose
        return [
            gr("nose shine", [el((x - 3, y - 3), (5, 3)), fl(pal["white"], 70)]),
            gr("nose", [el((x, y), (20, 15)), fl(pal["pink"])]),
        ]

    def face_static(self):
        pal = self.pal
        w = []
        for sgn in (1, -1):
            for dy, tilt in ((-5, -8), (4, 2), (12, 10)):
                x0 = 256 + sgn * 34
                w.append(sh(Path([(x0, 266 + dy), (x0 + sgn * 62, 262 + dy + tilt)], i=[(0, 0), (-sgn * 20, -3)], o=[(sgn * 20, -3), (0, 0)],
                                 closed=False)))
        return [gr("whiskers", w + [st(pal["dark"], 2.6, 45)])]

    def body_shapes(self):
        pal = self.pal
        body = smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)
        return [
            gr("belly", [el((256, 364), (92, 86)), fl(pal["cream"])]),
            gr("body", [sh(body), fl(pal["orange"])]),
        ]
