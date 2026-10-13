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
        "crouch": (20.0, 8.0,    0.0,    8.0,     0.0,  1.0,  0.97,    1.02,    1.0),   # knees bent, ready to spring (or to hide)
        "tiptoe": (-7.0, -2.0,  -4.0,   -4.0,     0.25, 0.96, 1.02,    0.99,    1.0),   # up on its toes
    }
    shadow = dict(c=(256.0, 472.0), size=(236.0, 22.0), o=14)

    # places the paws can go (right side; the left side mirrors).  Clips only use the pose names below.
    # Points on the face are given in the head drawing's coordinates and placed with head_pt().
    face_anchors = dict(chin=(277.0, 324.0), mouth=(272.0, 305.0), cheek=(338.0, 302.0), hold=(392.0, 322.0), hold_up=(404.0, 290.0),
                        carry=(386.0, 318.0), ring=(408.0, 272.0), eye_cover=(315.0, 244.0), eye_peek=(356.0, 266.0),
                        # v4
                        salute=(352.0, 236.0), facepalm=(282.0, 238.0), ear=(374.0, 262.0), thumbs=(408.0, 336.0),
                        # acting with things: a bite at the corner of the mouth, a phone against the cheek
                        bite=(310.0, 346.0), phone_ear=(350.0, 280.0))
    body_anchors = dict(belly=(286.0, 372.0), hip=(330.0, 384.0), edge=(356.0, 380.0), lap=(294.0, 404.0), lid=(301.0, 374.0),
                        # v4
                        chest=(274.0, 342.0), cross=(226.0, 346.0), hug=(222.0, 362.0), pray=(262.0, 334.0), clap_open=(304.0, 334.0),
                        point_fwd=(336.0, 318.0), thumbs_down=(398.0, 352.0), tray=(330.0, 372.0),
                        text=(298.0, 366.0))         # a phone held in front of the chest
    cheek = {"R": (352.0, 266.0)}           # centre of the blush on the right cheek (head drawing)

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
            # ---- v4 poses (the paw shapes - fist, thumb, finger - are separate channels; see Character.hand_variant)
            "salute": P(ik(A["salute"], bend=-1, hand=212), front=True),
            "facepalm": P(ik(A["facepalm"], bend=-1, hand=196), front=True),
            "ear": P(ik(A["ear"], bend=-1, hand=168), front=True),
            "chest": P(ik(A["chest"], bend=1, hand=-74)),
            "cross": P(ik(A["cross"], bend=1, hand=-92)),
            "hug": P(ik(A["hug"], bend=1, hand=-80)),
            "wide": P((106, 4, 0, 1.4), palm=True),
            "shrug": P((34, 70, 12, 1.15), palm=True),
            "flex": P((90, 92, 0, 1.25), front=True),
            "pray": P(ik(A["pray"], bend=1, hand=178)),
            "clap": P(ik(A["pray"], bend=1, hand=160)),
            "clap_open": P(ik(A["clap_open"], bend=1, hand=150), palm=True),
            "point_out": P((90, 2, 0, 1.45)),
            "point_up": P((146, 10, 4, 1.4), front=True),
            "point_fwd": P(ik(A["point_fwd"], bend=-1, hand=128), front=True),
            "thumbs_up": P(ik(A["thumbs"], bend=-1, hand=90)),
            "thumbs_down": P(ik(A["thumbs_down"], bend=-1, hand=-90)),
            "tray": P(ik(A["tray"], bend=1, hand=-8)),
            "present": P(ik(A["tray"], bend=1, hand=-8), front=True),     # carrying something in front (a cake)
            "lift": P((152, 18, 0, 1.5), front=True, palm=True),
            "fist_pump": P((128, 44, 0, 1.3), front=True),
            "reach": P((132, 0, 0, 1.55), front=True, palm=True),
            "dab": P((128, 0, 0, 1.55), front=True),
            "dab_in": P((160, -128, -10, 1.6), front=True),
            "behind": P((22, -32, 0, 0.9)),
            "fly": P((165, 0, 0, 1.55), front=True),
            # ---- acting with things (studio library)
            "bite": P(ik(A["bite"], bend=-1, hand=186), front=True),
            "phone_ear": P(ik(A["phone_ear"], bend=-1, hand=172), front=True),
            "text": P(ik(A["text"], bend=1, hand=-12), front=True),
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
            "alert": (2, 38, 36, 12, -12),          # straight up and bristling
            "tucked": (-48, 56, 64, 60, 34),          # curled up tight behind the body (scared)
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

    def body_outline(self):
        return smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)

    def body_shapes(self):
        pal = self.pal
        body = smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)
        return [
            gr("belly", [el((256, 362), (96, 90)), fl(pal["cream"])]),
            gr("body", [sh(body), fl(pal["orange"])]),
        ]

    # ------------------------------------------------------------------ drawn views (v5): seen from the side and from behind
    # The side view faces screen-right and is seen from the fox's left: 'L' is the near side (its eye, brow, cheek, ear,
    # arm and leg are in front), 'R' the far side.  The back view is seen from behind, so the fox's right side ('R') is on
    # screen-left.  Every point is in the same coordinates as the front drawing (head drawing for the head, canvas for the
    # body), so crown, eye line, shoulders and ground stay where the turnaround sheet's guides are.
    HEAD_SIDE = [(252, 104), (304, 108), (342, 128), (364, 160), (370, 196), (366, 222), (382, 232), (402, 236), (418, 243), (425, 254),
                 (416, 268), (392, 277), (362, 286), (330, 300), (290, 312), (252, 315), (206, 310), (170, 294), (146, 266), (138, 226),
                 (144, 182), (164, 144), (196, 116), (224, 106)]
    BODY_SIDE = [(254, 284), (290, 288), (314, 308), (326, 340), (330, 376), (318, 402), (288, 414), (250, 416), (214, 410), (196, 390),
                 (192, 356), (198, 320), (218, 294)]
    EAR_SIDE = [(-28, 12), (-31, -30), (-23, -70), (-13, -98), (-4, -110), (7, -100), (17, -64), (26, -22), (30, 8)]    # around the pivot

    def view_data(self, name):
        if self.name != "biscuit":                    # the fox's drawings: a mascot built on Biscuit draws its own views
            return super().view_data(name)
        if name == "side":
            return dict(
                head_shapes="side_head_shapes", tuft_shapes="side_tuft_shapes", ear_shapes="side_ear_shapes", nose_shapes="side_nose_shapes",
                blush_shapes="side_blush_shapes", face_static="side_face_static", body_shapes="side_body_shapes", foot_shapes="side_foot_shapes",
                head_outline="side_head_outline", body_outline="side_body_outline",
                eye={"L": (324.0, 225.0), "R": (324.0, 225.0)}, mouth=(398.0, 268.0), nose=(414.0, 251.0), cheek={"L": (300.0, 262.0), "R": (300.0, 262.0)},
                ear_pivot={"L": (232.0, 138.0), "R": (268.0, 126.0)}, tuft_pivot=(266.0, 110.0), crown=(256.0, 104.0),
                shoulder={"L": (258.0, 326.0), "R": (268.0, 322.0)}, hip={"L": (252.0, 400.0), "R": (264.0, 398.0)},
                foot={"L": (246.0, 446.0), "R": (268.0, 442.0)},
                tail=dict(self.tail, base=(206.0, 392.0)),
                dirs={"R": 1.0, "L": 1.0}, view_sides=("L",),
                squash={"eyes": 0.74, "brows": 0.8, "face": 0.6}, tail_slot=0, tail_flip=True, arms_behind="far", arm_turn=-16.0,
            )
        if name == "back":
            m = lambda p: (2 * CX - p[0], p[1])
            return dict(
                head_shapes="back_head_shapes", tuft_shapes="back_tuft_shapes", ear_shapes="back_ear_shapes", body_shapes="back_body_shapes",
                foot_shapes="back_foot_shapes",
                ear_pivot={"R": m(self.ear_pivot["R"]), "L": self.ear_pivot["R"]}, tuft_pivot=m(self.tuft_pivot),
                shoulder={"R": m(self.shoulder["R"]), "L": self.shoulder["R"]}, hip={"R": m(self.hip["R"]), "L": self.hip["R"]},
                foot={"R": m(self.foot["R"]), "L": self.foot["R"]},
                tail=dict(self.tail, base=(262.0, 400.0)),
                dirs={"R": -1.0, "L": 1.0}, view_sides=(),
                face=False, tail_slot=1, tail_flip=True, tail_rot=22.0, arms_behind="both",
            )
        return None

    def side_head_outline(self):
        return smooth(self.HEAD_SIDE, closed=True, tension=0.34, sharp={5: 0.45, 8: 0.6, 9: 0.6, 11: 0.5})

    def side_head_shapes(self):
        pal = self.pal
        head = self.side_head_outline()
        # the cream of the muzzle and the lower cheek: the outline from just behind the nose round the snout and the jaw
        # (pushed out a hair, keeping the outline's own curve), the fluff sticking out behind the cheek, and a line under
        # the eye back to the nose
        idx = list(range(8, 17))
        rim = [pushed(head.v[k], (300.0, 240.0)) for k in idx]
        # the white cheek reaches up behind the eye, with the fluff sticking out at its back edge
        fluff = [(176, 314), (192, 300), (152, 292), (180, 282), (148, 266), (182, 260), (166, 244), (204, 236)]
        inner = [(240, 236), (270, 250), (302, 262), (338, 262), (370, 252), (396, 243)]
        pts = rim + fluff + inner
        n_rim = len(rim)
        sharp = {0: 0.3, n_rim - 1: 0.4, len(pts) - 1: 0.5}
        sharp.update({n_rim + q: (0.0 if q % 2 == 0 else 0.4) for q in range(0, 7)})
        mask = smooth(pts, closed=True, tension=0.34, sharp=sharp)
        for q, k in enumerate(idx):
            if 0 < q < n_rim - 1:
                mask.i[q], mask.o[q] = head.i[k], head.o[k]
        line = lambda a_, b_: sh(Path([a_, b_], closed=False))
        stripes = [line((300, 112), (296, 134)), line((322, 118), (314, 140)), line((278, 110), (278, 132)),
                   line((228, 192), (206, 188)), line((230, 209), (208, 207))]
        return [
            gr("stripes", stripes + [st(pal["stripe"], 9)]),
            gr("head shine", [el((0, 0), (80, 28)), fl(pal["white"], 20)], p=(268, 136), r=-6),
            gr("muzzle", [el((404, 262), (30, 18)), fl(pal["white"], 55)]),
            gr("cream mask", [sh(mask), fl(pal["cream"])]),
            gr("head", [sh(head), fl(pal["orange"])]),
        ]

    def side_tuft_shapes(self):
        """The tuft, swept back."""
        pal = self.pal
        pts = [(2 * 262 - x, y) for x, y in [(236, 118), (238, 96), (254, 80), (280, 72), (272, 90), (290, 96), (278, 118)]]
        return [sh(smooth(pts, closed=True, tension=0.36, sharp={3: 0.55, 5: 0.55, 0: 0.4, 6: 0.4})), fl(pal["orange"])]

    def side_ear_shapes(self, side):
        """Ears seen from the side: narrow, standing on top of the head; the near ear shows the cream of its front
        edge, the far one peeks out behind it, a shade darker."""
        pal = self.pal
        pv = self.side({"L": (232.0, 138.0), "R": (268.0, 126.0)}, side)
        k = 1.0 if side == "L" else 0.9
        pts = [(pv[0] + x * k, pv[1] + y * k) for x, y in self.EAR_SIDE]
        ear = smooth(pts, closed=True, tension=0.33, sharp={4: 0.6, 0: 0.0, 8: 0.0})
        tip = [pushed(ear.v[q], (pv[0], pv[1] - 60.0)) for q in (2, 3, 4, 5, 6)] + [(pv[0] - 4.0, pv[1] - 70.0)]
        cap = smooth(tip, closed=True, tension=0.3, sharp={0: 0.0, 4: 0.0, 5: 0.5})
        for q in (1, 2, 3):
            cap.i[q], cap.o[q] = ear.i[q + 2], ear.o[q + 2]
        out = [gr("ear tip", [sh(cap), fl(pal["dark"])])]
        if side == "L":
            inner = smooth([(pv[0] + x, pv[1] + y) for x, y in [(4, -78), (14, -54), (21, -20), (23, 4), (11, 2), (7, -36)]], closed=True,
                           tension=0.35, sharp={0: 0.2, 3: 0.2})
            out.append(gr("inner ear", [sh(inner), fl(pal["cream"])]))
        out.append(gr("ear", [sh(ear), fl(pal["orange"] if side == "L" else pal["arm"])]))
        return out

    def side_nose_shapes(self):
        pal = self.pal
        x, y = (414.0, 251.0)
        nose = smooth([(x - 8, y - 6), (x + 5, y - 7), (x + 11, y - 1), (x + 6, y + 6), (x - 5, y + 5)], closed=True, tension=0.38)
        return [
            gr("nose shine", [el((x + 1, y - 3), (6, 3)), fl(pal["white"], 55)]),
            gr("nose", [sh(nose), fl(pal["dark"])]),
        ]

    def side_blush_shapes(self):
        pal = self.pal
        return [el((300, 264), (44, 24)), fl(pal["pink"])]

    def side_face_static(self):
        pal = self.pal
        dots = [el((x, y), (5, 5)) for x, y in ((376, 270), (384, 279), (368, 281))]
        return [gr("whisker dots", dots + [fl(pal["dark"], 32)])]

    def side_body_outline(self):
        return smooth(self.BODY_SIDE, closed=True, tension=0.36)

    def side_body_shapes(self):
        pal = self.pal
        return [
            gr("belly", [el((298, 362), (58, 86)), fl(pal["cream"])]),
            gr("body", [sh(self.side_body_outline()), fl(pal["orange"])]),
        ]

    def side_foot_shapes(self, side):
        """A foot seen from the side: long, toes pointing the way the fox faces; tipping up shows the sole."""
        pal = self.pal
        beans = [el((-4, -10), (8, 10)), el((-4, 2), (8, 10)), el((-2, 14), (10, 16)), fl(pal["pink"])]
        line = lambda x: sh(Path([(x, 14.0), (x + 2, 21.0)], closed=False))
        return dict(
            pads=beans,
            toes=[line(26.0), line(16.0), st(pal["iris"], 3.2, 70)],
            flat=((12.0, 10.0), (76.0, 28.0)),
            sole=((4.0, 2.0), (30.0, 50.0)),
            color=pal["dark"],
        )

    def back_head_shapes(self):
        """The back of the head: the same outline, the cheek fluff showing at the sides, no face."""
        pal = self.pal
        head = self.head_outline()
        n = len(head.v)
        fluff = []
        for k0 in (4, n - 8):                           # the fluff points of each cheek, pushed out, closed under them
            ks = list(range(k0, k0 + 5))
            v = [pushed(head.v[k], (256.0, 212.0)) for k in ks]
            c = (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v))
            inner = (c[0] + (256.0 - c[0]) * 0.28, c[1] + 4.0)
            fluff.append(smooth(v + [inner], closed=True, tension=0.3, sharp={0: 0.2, len(v) - 1: 0.2, 2: 0.6}))
        line = lambda a_, b_: sh(Path([a_, b_], closed=False))
        marks = [line((256, 124), (256, 150)), line((232, 128), (238, 150)), line((280, 128), (274, 150))]
        return [
            gr("stripes", marks + [st(pal["stripe"], 9)]),
            gr("head shine", [el((0, 0), (90, 30)), fl(pal["white"], 16)], p=(296, 142), r=16),
            gr("cheek fluff", [sh(f) for f in fluff] + [fl(pal["cream"])]),
            gr("head", [sh(head), fl(pal["orange"])]),
        ]

    def back_tuft_shapes(self):
        pts = [(2 * CX - x, y) for x, y in [(236, 118), (238, 96), (254, 80), (280, 72), (272, 90), (290, 96), (278, 118)]]
        return [sh(smooth(pts, closed=True, tension=0.36, sharp={3: 0.55, 5: 0.55, 0: 0.4, 6: 0.4})), fl(self.pal["orange"])]

    def back_ear_shapes(self, side):
        """Ears from behind: the back of the ear, orange with the dark tip, no cream inside."""
        pal = self.pal
        ear = smooth(self.EAR_R, closed=True, tension=0.33, sharp={3: 0.8, 4: 0.8, 0: 0.0, 7: 0.0})
        cap_v = [pushed(ear.v[q], (350.0, 110.0)) for q in (2, 3, 4, 5)] + [(366, 64)]
        cap = Path(cap_v, [(0, 0), ear.i[3], ear.i[4], ear.i[5], (6, 4)], [ear.o[2], ear.o[3], ear.o[4], (0, 0), (-6, -4)], True)
        if side == "R":                                 # the right ear is on screen-left from behind
            ear, cap = ear.mirrored(CX), cap.mirrored(CX)
        return [
            gr("ear tip", [sh(cap), fl(pal["dark"])]),
            gr("ear", [sh(ear), fl(pal["orange"])]),
        ]

    def back_body_shapes(self):
        pal = self.pal
        return [gr("body", [sh(smooth(mirror_half(self.BODY_R), closed=True, tension=0.36)), fl(pal["orange"])])]

    def back_foot_shapes(self, side):
        """Feet from behind: the heel; tipping up shows the sole and its pads."""
        pal = self.pal
        beans = [el((-15, -8), (10, 11)), el((0, -14), (10, 11)), el((15, -8), (10, 11)), el((0, 7), (28, 19)), fl(pal["pink"])]
        return dict(
            pads=beans,
            toes=[],
            flat=((0.0, 9.0), (56.0, 28.0)),
            sole=((0.0, 2.0), (62.0, 46.0)),
            color=pal["dark"],
        )

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
