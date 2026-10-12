"""Fern the frog -- character definition.

Built on Biscuit's body and joints.  A wide green head with the eyes up on two bumps, no ears and no tail, a pale
throat and belly, freckle spots, green paws and webbed green feet.
"""
from __future__ import annotations

from ..geom import smooth
from ..lottie import el, fl, gr, rgb, sh
from .biscuit import Biscuit, mirror_half


class Fern(Biscuit):
    name = "fern"

    pal = dict(
        orange=rgb("#7BC96F"),
        arm=rgb("#6CB960"),
        leg=rgb("#6CB960"),
        tail=rgb("#6CB960"),
        stripe=rgb("#56A04B"),
        cream=rgb("#E9F7C9"),
        tail_tip=rgb("#6CB960"),
        dark=rgb("#22301D"),
        iris=rgb("#6A5A20"),
        pink=rgb("#FF9AA2"),
        white=[1.0, 1.0, 1.0],
        blush_o=60,
    )
    paw_color = "stripe"
    eye = {"R": (322.0, 196.0)}
    eye_size = (52.0, 60.0)
    brow = dict(dy=-46.0, half=14.0, stroke=7.0)
    ear_pivot = {"R": (322.0, 150.0)}         # no ears: worn things placed by the ear go next to the eye bump
    crown = (256.0, 156.0)
    tuft_pivot = (256.0, 158.0)
    nose = (256.0, 246.0)
    mouth = (256.0, 264.0)
    cheek = {"R": (362.0, 258.0)}
    tail = None
    dyn = {}
    # the eyes sit higher on a frog: paws that cover, peek or salute go there
    face_anchors = dict(Biscuit.face_anchors, eye_cover=(322.0, 212.0), eye_peek=(366.0, 232.0), salute=(358.0, 204.0),
                        facepalm=(290.0, 206.0))

    HEAD_R = [(0, 160), (60, 162), (104, 180), (128, 212), (136, 244), (126, 272), (104, 294), (62, 310), (0, 314)]

    def head_outline(self):
        pts = mirror_half(self.HEAD_R)
        return smooth(pts, closed=True, tension=0.36)

    def head_shapes(self):
        pal = self.pal
        bumps = [el((322, 188), (100, 96)), el((190, 188), (100, 96))]
        spots = [el((256, 172), (14, 12)), el((236, 188), (9, 8)), el((280, 186), (10, 9)), el((372, 236), (10, 9)), el((140, 236), (10, 9))]
        return [
            gr("spots", spots + [fl(pal["stripe"])]),
            gr("head shine", [el((0, 0), (70, 26)), fl(pal["white"], 26)], p=(200, 156), r=-20),
            gr("throat", [el((256, 292), (130, 44)), fl(pal["cream"])]),
            gr("eye bumps", bumps + [fl(pal["orange"])]),
            gr("head", [sh(self.head_outline()), fl(pal["orange"])]),
        ]

    def tuft_shapes(self):
        return []

    def ear_shapes(self, side):
        return []

    def nose_shapes(self):
        pal = self.pal
        x, y = self.nose
        return [gr("nostrils", [el((x - 9, y), (6, 4)), el((x + 9, y), (6, 4)), fl(pal["dark"], 70)])]

    def face_static(self):
        return []

    def body_shapes(self):
        pal = self.pal
        body = smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)
        return [
            gr("belly", [el((256, 366), (104, 92)), fl(pal["cream"])]),
            gr("body spots", [el((318, 330), (12, 10)), el((196, 330), (12, 10)), el((330, 380), (9, 8)), fl(pal["stripe"])]),
            gr("body", [sh(body), fl(pal["orange"])]),
        ]

    def hand_shapes(self, side):
        pal = self.pal
        k = -1.0 if side == "R" else 1.0
        col = pal[self.paw_color]
        return dict(
            pads=[el((-13, 28), (10, 10)), el((0, 32), (10, 10)), el((13, 28), (10, 10)), fl(pal["cream"])],
            mitten=[gr("mitten", [el((0, 17), (45, 43)), fl(col)])],
            thumb=[el((0, 0), (18, 22)), fl(col)],
            thumb_at=(k * 18.0, 7.0, k * 28.0),
        )

    def foot_shapes(self, side):
        pal = self.pal
        k = 1.0 if side == "R" else -1.0
        toes = [el((k * 3.0 + x, 20.0), (14, 10)) for x in (-18, 0, 18)]
        return dict(
            pads=[el((-16, -8), (10, 10)), el((0, -14), (10, 10)), el((16, -8), (10, 10)), fl(pal["cream"])],
            toes=toes + [fl(pal["stripe"])],
            flat=((k * 3.0, 9.0), (66.0, 30.0)),
            sole=((k * 2.0, 2.0), (66.0, 46.0)),
            color=pal["stripe"],
        )
