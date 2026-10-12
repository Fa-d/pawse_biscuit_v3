"""Pip the dog -- character definition.

Built on Biscuit's body and joints (same proportions, so every pose, clip and worn item fits).  A puppy has long
floppy ears that swing with every move, a round head with a pale muzzle and a big nose, a spot on one ear and a
waggy tail that curves up.
"""
from __future__ import annotations

from ..geom import smooth
from ..lottie import Path, el, fl, gr, rgb, sh, st
from .biscuit import CX, Biscuit, mirror_half


class Pip(Biscuit):
    name = "pip"

    pal = dict(
        orange=rgb("#E3B47C"),          # main fur (keys keep Biscuit's names so palettes work on every mascot)
        arm=rgb("#D6A46B"),
        leg=rgb("#D6A46B"),
        tail=rgb("#D6A46B"),
        stripe=rgb("#9C6B43"),          # the ears and the spot
        cream=rgb("#FFF6E8"),
        tail_tip=rgb("#D6A46B"),
        dark=rgb("#3B2A20"),
        iris=rgb("#6A4632"),
        pink=rgb("#FF9AA2"),
        white=[1.0, 1.0, 1.0],
        blush_o=55,
    )

    HEAD_R = [(0, 114), (62, 118), (106, 146), (126, 190), (128, 232), (120, 266), (98, 294), (58, 312), (0, 318)]
    ear_pivot = {"R": (352.0, 160.0)}
    crown = (256.0, 114.0)
    tuft_pivot = (256.0, 116.0)
    nose = (256.0, 256.0)

    tail = dict(
        Biscuit.tail,
        length=150.0,
        bones=8,
        profile=[(0.0, 26.0), (0.35, 30.0), (0.75, 26.0), (1.0, 16.0)],
        tip_from=1.5,
        tip_r=8.0,
        tip_ext=6.0,
        furry=False,
        poses=dict(Biscuit.tail["poses"], rest=(-10, 30, 26, 18, 8), up=(4, 30, 22, 14, 4), low=(-34, 6, 10, 18, 24)),
    )
    dyn = {"ear.rot": 1.25, "ear.damp": 0.2, "ear.max": 40.0, "ear.freq": 2.0}

    def head_outline(self):
        return smooth(mirror_half(self.HEAD_R), closed=True, tension=0.36)

    def head_shapes(self):
        pal = self.pal
        return [
            gr("spot", [el((0, 0), (54, 40)), fl(pal["stripe"], 85)], p=(300, 150), r=-18),
            gr("head shine", [el((0, 0), (80, 30)), fl(pal["white"], 22)], p=(206, 150), r=-16),
            gr("muzzle", [el((256, 276), (104, 70)), fl(pal["cream"])]),
            gr("head", [sh(self.head_outline()), fl(pal["orange"])]),
        ]

    def tuft_shapes(self):
        return []

    # long floppy ears hanging from the top of the head, outside the cheeks
    EAR_R = [(334, 142), (366, 146), (394, 172), (406, 222), (398, 270), (376, 290), (356, 276), (346, 230), (338, 180)]

    def ear_shapes(self, side):
        pal = self.pal
        ear = smooth(self.EAR_R, closed=True, tension=0.36)
        inner = smooth([(354, 168), (378, 178), (390, 222), (382, 262), (366, 268), (358, 230)], closed=True, tension=0.36)
        if side == "L":
            ear, inner = ear.mirrored(CX), inner.mirrored(CX)
        return [
            gr("inner ear", [sh(inner), fl(pal["dark"], 18)]),
            gr("ear", [sh(ear), fl(pal["stripe"])]),
        ]

    def nose_shapes(self):
        pal = self.pal
        x, y = self.nose
        nose = smooth([(x - 17, y - 7), (x, y - 9), (x + 17, y - 7), (x + 8, y + 7), (x, y + 10), (x - 8, y + 7)], closed=True, tension=0.38,
                      sharp={0: 0.6, 2: 0.6})
        return [
            gr("nose shine", [el((x - 5, y - 4), (10, 4.5)), fl(pal["white"], 60)]),
            gr("nose", [sh(nose), fl(pal["dark"])]),
        ]

    def face_static(self):
        return []

    def body_shapes(self):
        pal = self.pal
        body = smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)
        return [
            gr("belly", [el((256, 364), (96, 88)), fl(pal["cream"])]),
            gr("collar", [sh(Path([(214, 300), (256, 312), (298, 300)], i=[(0, 0), (-16, 0), (0, 0)], o=[(0, 0), (16, 0), (0, 0)], closed=False)),
                          st(rgb("#E8574A"), 9)]),
            gr("tag", [el((256, 320), (14, 14)), fl(rgb("#FFC93C"))]),
            gr("body", [sh(body), fl(pal["orange"])]),
        ]
