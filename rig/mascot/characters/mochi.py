"""Mochi the cat -- character definition.

Built on Biscuit's body and joints (same proportions, so every pose and clip fits); only the drawings and the
data that make a cat differ: shorter, wider ears with pink insides, a round head without the fox cheek fluff,
whiskers, a small pink nose, green eyes and a long slim tail with a dark tip.
"""
from __future__ import annotations

from ..geom import smooth
from ..lottie import Path, el, fl, gr, rgb, sh, st
from .biscuit import CX, Biscuit, mirror_half, scaled


class Mochi(Biscuit):
    name = "mochi"

    pal = dict(
        orange=rgb("#A7B0C2"),          # main fur (keys keep Biscuit's names so palettes work on every mascot)
        arm=rgb("#97A1B5"),
        leg=rgb("#97A1B5"),
        tail=rgb("#97A1B5"),
        stripe=rgb("#6E7890"),
        cream=rgb("#FBF8F4"),
        tail_tip=rgb("#6E7890"),
        dark=rgb("#3A3644"),
        iris=rgb("#5FA36B"),
        pink=rgb("#FF9AAE"),
        white=[1.0, 1.0, 1.0],
        blush_o=62,
    )

    # a rounder skull: no cheek fluff points
    HEAD_R = [(0, 112), (60, 116), (104, 144), (124, 188), (128, 228), (122, 262), (100, 290), (60, 309), (0, 316)]
    EAR_R = [(286, 136), (304, 92), (330, 60), (352, 46), (364, 52), (372, 86), (376, 132), (366, 176)]
    ear_pivot = {"R": (340.0, 150.0)}
    crown = (256.0, 112.0)
    tuft_pivot = (256.0, 116.0)
    nose = (256.0, 258.0)

    tail = dict(
        Biscuit.tail,
        length=250.0,
        profile=[(0.0, 30.0), (0.3, 30.0), (0.7, 28.0), (0.9, 26.0), (1.0, 18.0)],
        tip_from=0.86,
        tip_r=9.0,
        tip_ext=10.0,
        furry=False,
    )
    dyn = {"ear.rot": 0.6, "ear.max": 22.0}       # cat ears are stiffer than fox ears

    def head_outline(self):
        return smooth(mirror_half(self.HEAD_R), closed=True, tension=0.36)

    def head_shapes(self):
        pal = self.pal
        head = self.head_outline()
        line = lambda a, b: sh(Path([a, b], closed=False))
        stripes = [line((256, 126), (256, 156)), line((282, 130), (276, 154)), line((230, 130), (236, 154)),
                   line((376, 196), (356, 200)), line((378, 214), (358, 216)), line((136, 196), (156, 200)), line((134, 214), (154, 216))]
        return [
            gr("stripes", stripes + [st(pal["stripe"], 8)]),
            gr("head shine", [el((0, 0), (78, 30)), fl(pal["white"], 22)], p=(206, 148), r=-16),
            gr("muzzle", [el((236, 276), (60, 46)), el((276, 276), (60, 46)), fl(pal["cream"])]),
            gr("chin", [el((256, 296), (70, 34)), fl(pal["cream"])]),
            gr("head", [sh(head), fl(pal["orange"])]),
        ]

    def tuft_shapes(self):
        return []

    def ear_shapes(self, side):
        pal = self.pal
        ear = smooth(self.EAR_R, closed=True, tension=0.3, sharp={3: 0.7, 4: 0.7, 0: 0.0, 7: 0.0})
        inner = smooth(scaled(self.EAR_R, (340, 128), 0.58, (2, 10)), closed=True, tension=0.3, sharp={3: 0.7, 4: 0.7})
        if side == "L":
            ear, inner = ear.mirrored(CX), inner.mirrored(CX)
        return [
            gr("inner ear", [sh(inner), fl(pal["pink"], 85)]),
            gr("ear", [sh(ear), fl(pal["orange"])]),
        ]

    def nose_shapes(self):
        pal = self.pal
        x, y = self.nose
        nose = smooth([(x - 10, y - 5), (x + 10, y - 5), (x, y + 6)], closed=True, tension=0.3)
        return [
            gr("nose shine", [el((x - 3, y - 3), (6, 3)), fl(pal["white"], 60)]),
            gr("nose", [sh(nose), fl(pal["pink"])]),
            gr("nose edge", [sh(nose), st(pal["dark"], 3, 40)]),
        ]

    def face_static(self):
        pal = self.pal
        w = []
        for sgn in (1, -1):
            for dy, tilt in ((-4, -6), (6, 4)):
                x0 = 256 + sgn * 46
                w.append(sh(Path([(x0, 272 + dy), (x0 + sgn * 54, 266 + dy + tilt)], i=[(0, 0), (-sgn * 18, -3)], o=[(sgn * 18, -3), (0, 0)],
                                 closed=False)))
        return [gr("whiskers", w + [st(pal["dark"], 3, 45)])]

    def body_shapes(self):
        pal = self.pal
        body = smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)
        return [
            gr("belly", [el((256, 364), (88, 86)), fl(pal["cream"])]),
            gr("body stripes", [sh(Path([(312, 312), (328, 318)], closed=False)), sh(Path([(200, 312), (184, 318)], closed=False)),
                                st(pal["stripe"], 7)]),
            gr("body", [sh(body), fl(pal["orange"])]),
        ]
