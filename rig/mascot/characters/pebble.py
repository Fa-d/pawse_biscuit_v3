"""Pebble the penguin -- character definition.

Built on Biscuit's body and joints.  A dark round head with a white face, an orange beak instead of a nose, no
ears, flippers for arms (no fingers: a fist or a thumb is still just a flipper), a big white belly, short dark
legs, orange webbed feet and a short tail.
"""
from __future__ import annotations

from ..geom import smooth
from ..lottie import Path, el, fl, gr, rgb, sh, st
from .biscuit import Biscuit, mirror_half
from .bruno import Bruno


class Pebble(Biscuit):
    name = "pebble"

    pal = dict(
        orange=rgb("#39414F"),
        arm=rgb("#323A47"),
        leg=rgb("#323A47"),
        tail=rgb("#323A47"),
        stripe=rgb("#2A313C"),
        cream=rgb("#FFFFFF"),
        tail_tip=rgb("#323A47"),
        dark=rgb("#171A20"),
        iris=rgb("#3D4B66"),
        pink=rgb("#FF9AAE"),
        white=[1.0, 1.0, 1.0],
        beak=rgb("#FFB13B"),
        blush_o=70,
    )
    lid_color = "cream"
    paw_color = "arm"
    HEAD_R = Bruno.HEAD_R
    ear_pivot = {"R": (344.0, 150.0)}
    crown = (256.0, 116.0)
    tuft_pivot = (256.0, 118.0)
    nose = (256.0, 262.0)
    mouth = (256.0, 280.0)
    tail = dict(Bruno.tail, length=34.0, profile=[(0.0, 40.0), (0.5, 40.0), (1.0, 20.0)], tip_r=10.0)
    dyn = {"tail.rot": 0.5}

    def head_outline(self):
        return smooth(mirror_half(self.HEAD_R), closed=True, tension=0.36)

    def head_shapes(self):
        pal = self.pal
        face = smooth([(256, 196), (290, 162), (338, 160), (370, 196), (372, 252), (346, 296), (300, 312), (256, 314), (212, 312), (166, 296),
                       (140, 252), (142, 196), (174, 160), (222, 162)], closed=True, tension=0.38, sharp={0: 0.6})
        return [
            gr("head shine", [el((0, 0), (80, 28)), fl(pal["white"], 22)], p=(206, 148), r=-16),
            gr("face", [sh(face), fl(pal["cream"])]),
            gr("head", [sh(self.head_outline()), fl(pal["orange"])]),
        ]

    def tuft_shapes(self):
        pal = self.pal
        pts = [(244, 122), (250, 98), (262, 90), (266, 104), (272, 122)]
        return [sh(smooth(pts, closed=True, tension=0.4)), fl(pal["orange"])]

    def ear_shapes(self, side):
        return []

    def nose_shapes(self):
        pal = self.pal
        x, y = self.nose
        top = smooth([(x - 20, y - 2), (x, y - 12), (x + 20, y - 2), (x, y + 6)], closed=True, tension=0.3, sharp={0: 0.7, 2: 0.7})
        low = smooth([(x - 15, y + 2), (x + 15, y + 2), (x, y + 14)], closed=True, tension=0.3)
        return [
            gr("beak shine", [el((x - 6, y - 5), (10, 4)), fl(pal["white"], 60)]),
            gr("beak top", [sh(top), fl(pal["beak"])]),
            gr("beak low", [sh(low), fl(rgb("#F0962A"))]),
        ]

    def face_static(self):
        return []

    def body_shapes(self):
        pal = self.pal
        body = smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)
        return [
            gr("belly", [el((256, 360), (112, 104)), fl(pal["cream"])]),
            gr("body", [sh(body), fl(pal["orange"])]),
        ]

    def hand_shapes(self, side):
        pal = self.pal
        k = -1.0 if side == "R" else 1.0
        col = pal["arm"]
        return dict(
            pads=[],
            mitten=[gr("flipper", [el((0, 20), (34, 52)), fl(col)])],
            thumb=[el((0, 0), (1, 1)), fl(col, 0)],
            thumb_at=(k * 1.0, 0.0, 0.0),
        )

    def hand_variant(self, k, side):
        """A flipper has no fingers: every paw shape is the flipper."""
        return self.hand_shapes(side)["mitten"]

    def foot_shapes(self, side):
        pal = self.pal
        k = 1.0 if side == "R" else -1.0
        toes = [sh(Path([(k * 3.0 + x, 12.0), (k * 3.0 + x * 1.3, 22.0)], closed=False)) for x in (-12, 0, 12)]
        return dict(
            pads=[el((0, 0), (40, 24)), fl(rgb("#F0962A"))],
            toes=toes + [st(rgb("#E07F1F"), 3.2, 80)],
            flat=((k * 3.0, 10.0), (66.0, 28.0)),
            sole=((k * 2.0, 2.0), (62.0, 44.0)),
            color=pal["beak"],
        )
