"""Biscuit the fox -- character definition (data only; all mechanics live in character.py)."""
from __future__ import annotations

from ..character import Character
from ..geom import smooth
from ..lottie import Path, el, fl, gr, rgb, sh, st

CX = 256.0


def mirror_half(right_half):
    """right_half: points from top-centre clockwise to bottom-centre as (dx, y). Returns the closed outline."""
    pts = [(CX + dx, y) for dx, y in right_half]
    pts += [(CX - dx, y) for dx, y in reversed(right_half[1:-1])]
    return pts


def scaled(pts, about, k, shift=(0.0, 0.0)):
    return [(about[0] + (x - about[0]) * k + shift[0], about[1] + (y - about[1]) * k + shift[1]) for x, y in pts]


def pushed(p, centre, d=0.9):
    """Move a point d pixels away from `centre`.

    A patch that shares part of an outline with the shape underneath (cream cheeks on the head, dark tips on
    the ears) is pushed out by a hair, so the colour underneath cannot show as a fringe along that edge.
    """
    vx, vy = p[0] - centre[0], p[1] - centre[1]
    n = (vx * vx + vy * vy) ** 0.5 or 1.0
    return (p[0] + vx / n * d, p[1] + vy / n * d)


class Biscuit(Character):
    name = "biscuit"
    GROUND = 470.0
    base_scale = 0.98

    pal = dict(
        orange=rgb("#FF8A3D"),
        arm=rgb("#F27A2E"),
        leg=rgb("#F27A2E"),
        tail=rgb("#E8702A"),
        stripe=rgb("#C95A1D"),
        cream=rgb("#FFF4E6"),
        tail_tip=rgb("#FFF4E6"),
        dark=rgb("#3B2A20"),
        iris=rgb("#6A4632"),
        pink=rgb("#FF9AA2"),
        white=[1.0, 1.0, 1.0],
        blush_o=62,
    )

    # ------------------------------------------------------------------ joints (rest pose, canvas coordinates)
    neck = (256.0, 314.0)
    neck_at = (256.0, 302.0)                # the head sits a little higher and smaller than it is drawn,
    head_scale = 0.93                       # which leaves room for a body that stands on its own legs
    head_lever = 158.0
    ear_pivot = {"R": (338.0, 142.0)}
    tuft_pivot = (256.0, 110.0)
    eye = {"R": (314.0, 226.0)}
    eye_size = (54.0, 66.0)
    eye_look = 5.5
    lid = dict(w=23.0, rise=15.0, dy=9.0, stroke=9.5)
    brow = dict(dy=-50.0, half=15.0, stroke=7.0)
    nose = (256.0, 257.0)
    mouth = (256.0, 268.0)
    shoulder = {"R": (314.0, 328.0)}
    arm = dict(L1=32.0, L2=28.0, w=28.0)

    # lower body: a short torso on stubby legs (about one paw long), big flat feet
    pelvis = (256.0, 400.0)
    hip = {"R": (292.0, 400.0)}
    foot = {"R": (296.0, 446.0)}            # ankle; the foot is drawn around it
    leg = dict(w=38.0, knee=0.9, slack=0.04, stretch=1.18, bulge=0.2, foot_follow=0.8)
    stances = {
        #        hip.y  foot.x  foot.y  foot.rot  sole  size  body.sy  body.sx  plant
        "stand": (0.0,   0.0,    0.0,    0.0,     0.0,  1.0,  1.0,     1.0,     1.0),
        "wide":  (3.0,  12.0,    0.0,    6.0,     0.0,  1.0,  1.0,     1.0,     1.0),
        "sit":   (54.0, 24.0,    0.0,   12.0,     1.0,  1.06, 0.95,    1.08,    0.0),   # on its bottom, soles towards the viewer
        "lotus": (54.0, -24.0, -10.0,  -40.0,     1.0,  0.92, 0.95,    1.08,    0.0),   # cross-legged
    }
    shadow = dict(c=(256.0, 472.0), size=(236.0, 22.0), o=14)

    # places the paws can go (right side; the left side mirrors).  Clips only use the pose names below.
    # Points on the face are given in the head drawing's coordinates and placed with head_pt().
    face_anchors = dict(chin=(277.0, 324.0), mouth=(272.0, 305.0), cheek=(338.0, 302.0), hold=(392.0, 322.0), hold_up=(404.0, 290.0),
                        carry=(386.0, 318.0), ring=(408.0, 272.0), eye_cover=(315.0, 244.0), eye_peek=(356.0, 266.0))
    body_anchors = dict(belly=(286.0, 372.0), hip=(330.0, 384.0), edge=(356.0, 380.0), lap=(294.0, 404.0), lid=(301.0, 374.0))

    def __init__(self):
        self.anchors = A = dict(self.body_anchors)
        A.update({k: self.head_pt(v) for k, v in self.face_anchors.items()})
        ik = self.ik
        # front: True = must be drawn in front of the head, False = must be behind it, None = does not matter
        P = lambda v, front=None, palm=False: dict(v=tuple(v), front=front, palm=palm)
        # (shoulder, elbow, wrist, length): 0 = hanging down, + = outwards / up
        self.arm_poses = {
            "rest": P((30, -8, -4, 1.0)),
            "relax": P((38, -16, -6, 1.0)),
            "wave_lo": P((100, 26, 4, 1.38), front=True, palm=True),
            "wave_hi": P((100, 74, -4, 1.38), front=True, palm=True),
            "cheer": P((124, 20, 0, 1.42), front=True, palm=True),
            "cheer_hi": P((140, 12, 0, 1.46), front=True, palm=True),
            "cheer_out": P((106, 12, 0, 1.4), front=True, palm=True),
            "chin": P(ik(A["chin"], bend=1, hand=202), front=True),
            "mouth": P(ik(A["mouth"], bend=1, hand=192), front=True),
            "cheek": P(ik(A["cheek"], bend=-1, hand=176), front=True),
            "belly": P(ik(A["belly"], bend=1, hand=-62)),
            "lap": P(ik(A["lap"], bend=1, hand=-30)),
            "hip": P(ik(A["hip"], bend=1, hand=-40)),
            "hold": P(ik(A["hold"], bend=-1, hand=172), front=True),
            "hold_up": P(ik(A["hold_up"], bend=-1, hand=176), front=True),
            "carry": P(ik(A["carry"], bend=-1, hand=178), front=True),
            "edge": P(ik(A["edge"], bend=1, hand=10), front=True),
            "ring": P(ik(A["ring"], bend=-1, hand=180), front=True),
            "knee": P((52, -40, -10, 1.0), palm=True),           # resting on the knees when cross-legged, palms up
            "lid": P(ik(A["lid"], bend=1, hand=-20)),
            "cover_eyes": P(ik(A["eye_cover"], bend=-1, hand=184), front=True),
            "peek": P(ik(A["eye_peek"], bend=-1, hand=160), front=True),
            "stretch": P((112, 6, 0, 1.5), front=True, palm=True),
        }

    tail = dict(
        base=(280.0, 398.0),
        length=226.0,              # along the bones
        bones=12,
        profile=[(0.0, 36.0), (0.22, 62.0), (0.46, 84.0), (0.68, 86.0), (0.85, 70.0), (0.93, 50.0), (1.0, 24.0)],   # (position, width)
        tip_from=0.68,             # where the cream tip starts
        tip_r=8.0,
        tip_ext=14.0,
        poses={
            # base heading (0 = right, + = up), then the bend at each following joint
            # --- standing: the tail leaves the hips low, rests near the ground and sweeps up at the end
            "rest": (-25, 25, 30, 30, -10),
            "out": (-26, 22, 30, 30, -4),          # leaning away from the body
            "in": (-14, 28, 32, 30, -16),          # leaning towards the body
            "up": (-8, 26, 32, 28, -20),           # perky
            "low": (-22, 8, 18, 28, 36),           # droopy
            "floor": (-24, 10, 24, 38, 50),        # lying beside the feet, tip curled up (keeps clear of a raised paw)
            "flick_out": (-25, 25, 32, 20, -36),   # tip flops outwards
            "flick_in": (-25, 25, 30, 40, 44),     # tip curls inwards
            "curl": (-20, 30, 42, 52, 60),
            # --- sitting: the hips are on the ground, so the tail lies along it
            "ground": (10, 6, 28, 46, -4, 0, -6),
            "ground_up": (10, 24, 34, 26, -14, 0, -5),
            # across the lap (use with tail.front = 1); the last two numbers move the root to the hip so it seems to come from behind
            "wrap": (-178, -4, -6, -12, -26, 54, -20),
        },
    )

    dyn = {}

    # ------------------------------------------------------------------ drawings
    HEAD_R = [(0, 104), (58, 108), (102, 138), (122, 186), (124, 222), (140, 242), (119, 253), (122, 273), (88, 296), (44, 311), (0, 315)]
    BODY_R = [(0, 284), (48, 288), (66, 310), (74, 344), (80, 376), (74, 399), (50, 412), (0, 415)]

    def head_outline(self):
        pts = mirror_half(self.HEAD_R)
        n = len(pts)
        sharp = {5: 0.55, 7: 0.55, 6: 0.8, n - 5: 0.55, n - 7: 0.55, n - 6: 0.8}
        return smooth(pts, closed=True, tension=0.35, sharp=sharp)

    def head_shapes(self):
        pal = self.pal
        head = self.head_outline()
        n = len(head.v)
        a, b = 4, n - 4                      # cheek-top vertices on the right and on the left
        idx = list(range(a, b + 1))
        inner_pts = [head.v[b], (166, 254), (204, 265), (237, 243), (256, 204), (275, 243), (308, 265), (346, 254), head.v[a]]
        inner = smooth(inner_pts, closed=False, tension=0.34, sharp={4: 0.45})
        v = [pushed(head.v[k], (256.0, 212.0)) for k in idx] + inner.v[1:-1]
        i = [head.i[k] for k in idx] + inner.i[1:-1]
        o = [head.o[k] for k in idx] + inner.o[1:-1]
        o[len(idx) - 1] = inner.o[0]
        i[0] = inner.i[-1]
        mask = Path(v, i, o, True)
        line = lambda a_, b_: sh(Path([a_, b_], closed=False))
        stripes = [
            line((256, 120), (256, 148)), line((280, 123), (273, 147)), line((232, 123), (239, 147)),
            line((350, 190), (370, 185)), line((352, 207), (372, 205)),
            line((162, 190), (142, 185)), line((160, 207), (140, 205)),
        ]
        return [
            gr("stripes", stripes + [st(pal["stripe"], 9)]),
            gr("head shine", [el((0, 0), (78, 30)), fl(pal["white"], 20)], p=(208, 140), r=-16),
            gr("muzzle", [el((256, 278), (92, 52)), fl(pal["white"], 55)]),
            gr("cream mask", [sh(mask), fl(pal["cream"])]),
            gr("head", [sh(head), fl(pal["orange"])]),
        ]

    def tuft_shapes(self):
        pal = self.pal
        pts = [(236, 118), (238, 96), (254, 80), (280, 72), (272, 90), (290, 96), (278, 118)]
        return [sh(smooth(pts, closed=True, tension=0.36, sharp={3: 0.55, 5: 0.55, 0: 0.4, 6: 0.4})), fl(pal["orange"])]

    EAR_R = [(292, 126), (322, 72), (348, 44), (368, 30), (380, 34), (386, 62), (388, 112), (372, 180)]

    def ear_shapes(self, side):
        pal = self.pal
        ear = smooth(self.EAR_R, closed=True, tension=0.33, sharp={3: 0.8, 4: 0.8, 0: 0.0, 7: 0.0})
        cap_v = [pushed(ear.v[q], (350.0, 110.0)) for q in (2, 3, 4, 5)] + [(366, 64)]
        cap = Path(cap_v, [(0, 0), ear.i[3], ear.i[4], ear.i[5], (6, 4)], [ear.o[2], ear.o[3], ear.o[4], (0, 0), (-6, -4)], True)
        inner = smooth(scaled(self.EAR_R, (350, 120), 0.62, (2, 8)), closed=True, tension=0.33, sharp={3: 0.8, 4: 0.8})
        if side == "L":
            ear, cap, inner = ear.mirrored(CX), cap.mirrored(CX), inner.mirrored(CX)
        return [
            gr("ear tip", [sh(cap), fl(pal["dark"])]),
            gr("inner ear", [sh(inner), fl(pal["cream"])]),
            gr("ear", [sh(ear), fl(pal["orange"])]),
        ]

    def eye_shapes(self, side):
        pal = self.pal
        c = self.side(self.eye, side)
        w, h = self.eye_size
        return [
            gr("glint", [el((c[0] - 10, c[1] + 15), (8, 8)), fl(pal["white"], 90)]),
            gr("shine", [el((c[0] + 9, c[1] - 14), (20, 20)), fl(pal["white"])]),
            gr("iris", [el((c[0], c[1] + 17), (36, 24)), fl(pal["iris"], 80)]),
            gr("eye", [el(c, (w, h)), fl(pal["dark"])]),
        ]

    def nose_shapes(self):
        pal = self.pal
        x, y = self.nose
        nose = smooth([(x - 13, y - 5), (x, y - 7), (x + 13, y - 5), (x + 5, y + 4), (x, y + 8), (x - 5, y + 4)], closed=True, tension=0.36,
                      sharp={0: 0.7, 2: 0.7})
        return [
            gr("nose shine", [el((x - 3, y - 3), (8, 3.5)), fl(pal["white"], 55)]),
            gr("nose", [sh(nose), fl(pal["dark"])]),
        ]

    def blush_shapes(self):
        pal = self.pal
        return [el((352, 266), (42, 24)), el((160, 266), (42, 24)), fl(pal["pink"])]

    def face_static(self):
        pal = self.pal
        dots = [el((x, y), (5, 5)) for x, y in ((289, 278), (298, 287), (223, 278), (214, 287))]
        return [gr("whisker dots", dots + [fl(pal["dark"], 32)])]

    def body_shapes(self):
        pal = self.pal
        body = smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)
        return [
            gr("belly", [el((256, 362), (96, 90)), fl(pal["cream"])]),
            gr("body", [sh(body), fl(pal["orange"])]),
        ]

    def hand_shapes(self, side):
        """Paw drawn with the wrist at (0, 0) and the fingertips towards +y.

        Like a paw print, the three toe beans sit at the fingertip end and the big pad nearer the wrist.
        `thumb_at` is where the thumb sits when the BACK of the paw faces the viewer; the rig slides it to
        the other edge as the paw turns palm-out, so the thumb always ends up on the anatomically right side.
        """
        pal = self.pal
        k = -1.0 if side == "R" else 1.0     # thumb points to the body's centre line when the arm hangs
        return dict(
            pads=[el((-12, 26), (9, 10)), el((0, 30.5), (9, 10)), el((12, 26), (9, 10)), el((0, 13), (22, 16)), fl(pal["pink"])],
            mitten=[gr("mitten", [el((0, 17), (45, 43)), fl(pal["dark"])])],
            thumb=[el((0, 0), (18, 22)), fl(pal["dark"])],
            thumb_at=(k * 18.0, 7.0, k * 28.0),
        )

    def foot_shapes(self, side):
        """Foot drawn around the ankle at (0, 0).  Standing it is a flat paw seen from the front; as it tips up
        towards the viewer it rounds into the sole and the pads come into view (toe beans on top)."""
        pal = self.pal
        k = 1.0 if side == "R" else -1.0
        beans = [el((-15, -8), (10, 11)), el((0, -14), (10, 11)), el((15, -8), (10, 11)), el((0, 7), (28, 19)), fl(pal["pink"])]
        line = lambda x: sh(Path([(k * 3.0 + x, 16.0), (k * 3.0 + x, 22.0)], closed=False))
        return dict(
            pads=beans,
            toes=[line(-10.0), line(10.0), st(pal["iris"], 3.2, 70)],
            flat=((k * 3.0, 9.0), (60.0, 30.0)),
            sole=((k * 2.0, 2.0), (62.0, 46.0)),
            color=pal["dark"],
        )
