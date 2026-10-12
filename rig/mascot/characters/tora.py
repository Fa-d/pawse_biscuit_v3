"""Tora the tiger -- character definition.

Built on Biscuit's body and joints.  Bright orange fur with dark stripes on the forehead, cheeks, body and tail,
a white muzzle and cheek ruffs, small round ears with dark backs and a long striped tail with a dark tip.
"""
from __future__ import annotations

from ..geom import smooth
from ..lottie import el, fl, gr, rgb, sh, st
from .biscuit import Biscuit, mirror_half


class Tora(Biscuit):
    name = "tora"

    pal = dict(
        orange=rgb("#FF9C3A"),
        arm=rgb("#F28C2C"),
        leg=rgb("#F28C2C"),
        tail=rgb("#F28C2C"),
        stripe=rgb("#33231B"),
        cream=rgb("#FFF6EA"),
        tail_tip=rgb("#33231B"),
        tail_ring=rgb("#33231B"),
        dark=rgb("#33231B"),
        iris=rgb("#9A7420"),
        pink=rgb("#FF9AA2"),
        white=[1.0, 1.0, 1.0],
        blush_o=55,
    )

    HEAD_R = [(0, 112), (62, 116), (106, 144), (126, 188), (132, 226), (146, 244), (124, 256), (124, 274), (92, 298), (48, 312), (0, 316)]
    ear_pivot = {"R": (344.0, 150.0)}
    crown = (256.0, 112.0)
    tuft_pivot = (256.0, 114.0)
    nose = (256.0, 258.0)

    tail = dict(
        Biscuit.tail,
        length=230.0,
        bones=12,
        profile=[(0.0, 30.0), (0.3, 32.0), (0.7, 30.0), (1.0, 24.0)],
        tip_from=0.88,
        tip_r=12.0,
        tip_ext=8.0,
        furry=False,
        rings=[(0.18, 0.26), (0.38, 0.46), (0.58, 0.66), (0.76, 0.82)],
    )
    dyn = {"ear.rot": 0.5, "ear.max": 16.0}

    def head_outline(self):
        pts = mirror_half(self.HEAD_R)
        n = len(pts)
        sharp = {5: 0.6, n - 5: 0.6}
        return smooth(pts, closed=True, tension=0.36, sharp=sharp)

    def head_shapes(self):
        pal = self.pal
        line = lambda pts, w: sh(smooth(pts, closed=False, tension=0.4))
        stripes = [
            line([(256, 122), (256, 160)], 9), line([(232, 126), (238, 152)], 8), line([(280, 126), (274, 152)], 8),
            line([(380, 196), (352, 202), (336, 214)], 8), line([(384, 220), (358, 224)], 8),
            line([(132, 196), (160, 202), (176, 214)], 8), line([(128, 220), (154, 224)], 8),
        ]
        return [
            gr("stripes", stripes + [st(pal["stripe"], 9)]),
            gr("head shine", [el((0, 0), (80, 30)), fl(pal["white"], 22)], p=(206, 148), r=-16),
            gr("muzzle", [el((230, 280), (68, 54)), el((282, 280), (68, 54)), el((256, 300), (64, 34)), fl(pal["cream"])]),
            gr("brows", [el((288, 178), (26, 14)), el((224, 178), (26, 14)), fl(pal["cream"], 85)]),
            gr("head", [sh(self.head_outline()), fl(pal["orange"])]),
        ]

    def tuft_shapes(self):
        return []

    def ear_shapes(self, side):
        pal = self.pal
        c = self.side(self.ear_pivot, side)
        k = 1 if side == "R" else -1
        cx, cy = c[0] + k * 12, c[1] - 30
        return [
            gr("inner ear", [el((cx, cy + 6), (30, 28)), fl(pal["cream"])]),
            gr("ear rim", [el((cx, cy), (58, 54)), fl(pal["stripe"])]),
            gr("ear", [el((cx, cy + 3), (62, 58)), fl(pal["orange"])]),
        ]

    def nose_shapes(self):
        pal = self.pal
        x, y = self.nose
        nose = smooth([(x - 12, y - 5), (x + 12, y - 5), (x, y + 7)], closed=True, tension=0.3)
        return [
            gr("nose shine", [el((x - 3, y - 3), (6, 3)), fl(pal["white"], 60)]),
            gr("nose", [sh(nose), fl(rgb("#E8858F"))]),
        ]

    def face_static(self):
        pal = self.pal
        dots = [el((x, y), (5, 5)) for x, y in ((284, 280), (293, 289), (228, 280), (219, 289))]
        return [gr("whisker dots", dots + [fl(pal["dark"], 40)])]

    def body_shapes(self):
        pal = self.pal
        body = smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)
        stripe = lambda pts: sh(smooth(pts, closed=False, tension=0.4))
        return [
            gr("belly", [el((256, 364), (92, 86)), fl(pal["cream"])]),
            gr("body stripes", [stripe([(326, 330), (304, 338), (296, 350)]), stripe([(330, 362), (310, 368)]),
                                stripe([(186, 330), (208, 338), (216, 350)]), stripe([(182, 362), (202, 368)]), st(pal["stripe"], 8)]),
            gr("body", [sh(body), fl(pal["orange"])]),
        ]
