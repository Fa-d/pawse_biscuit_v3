"""Generic mascot builder.

A concrete mascot (see characters/biscuit.py) only supplies *data*: palette, joint positions,
part drawings, named arm / tail poses and spring settings.  Everything about how those parts
move, layer and bake into Lottie lives here and is shared by every mascot.

Skeleton written into every file (layer / group names are stable so an app can address them):

    shadow
    root (null)                      whole-character move, squash & stretch, flips
      hips (null)                    pelvis: sits down, bends the knees, shifts the weight
        tail                         bone chain: nested groups  tail 0 > tail 1 > ... (each rotates at its joint)
        body                         torso, pivot at the pelvis
          right arm / left arm       bone chain: upper arm > forearm > hand   (held props live inside 'hand')
          neck (null)                head pivot
            right ear / left ear, head (with 'tuft'), face, eyes, brows
      right leg / left leg           one bendy limb from the hip joint to the ankle, solved every frame
      right foot / left foot         stay where the clip plants them while the hips move
"""
from __future__ import annotations

import math

import numpy as np

from . import rig
from .geom import heading, pchip, rot as rot_pt, smooth
from .lottie import Anim, Layer, Path, document, el, fl, gr, sh, st


def mirror_pt(p, cx):
    return (2 * cx - p[0], p[1])


class Character:
    name = "mascot"
    CX = 256.0
    GROUND = 470.0
    base_scale = 1.0      # size of the drawing inside the canvas (about the ground point); leaves headroom for acting
    pal: dict = {}
    dyn: dict = {}
    head_lever = 150.0

    # ------------------------------------------------------------------ data a mascot must provide
    neck = (256.0, 316.0)            # head pivot, in the coordinates the head is drawn in
    neck_at = None                   # where that pivot sits on the body (default: the same point)
    head_scale = 1.0                 # size of the head drawing on the body
    crown = (256.0, 104.0)           # top of the skull in the head drawing (effects such as z's and thought dots start from it)
    ear_pivot = {"R": (336.0, 130.0)}
    tuft_pivot = (256.0, 108.0)
    eye = {"R": (314.0, 226.0)}
    eye_look = 5.0
    lid = dict(w=23.0, rise=15.0, dy=9.0, stroke=9.5)
    brow = dict(dy=-48.0, half=15.0, stroke=7.0)
    mouth = (256.0, 268.0)
    nose = (256.0, 256.0)
    shoulder = {"R": (316.0, 348.0)}
    arm = dict(L1=38.0, L2=34.0, w=30.0)
    arm_poses: dict = {}
    # lower body.  A mascot without legs sets leg = None: its feet then simply hang from the root.
    pelvis = (256.0, 470.0)          # pivot of the hips (and of the torso's lean and breathing)
    hip = {"R": (290.0, 410.0)}      # where a leg leaves the body
    foot = {"R": (304.0, 446.0)}     # ankle when standing at rest
    leg = None                       # dict(w=stroke width, knee=how far the knee bows when the leg shortens, slack, stretch)
    stances: dict = {}               # name -> numbers in rig.STANCE order ('stand' and 'sit' are required when leg is set)
    shadow = dict(c=(256.0, 474.0), size=(250.0, 24.0), o=14)
    # tail: dict(base, length, bones, profile [(u, width)], tip_from, tip_r, poses {name: (base heading, bends...)}) or None
    tail = None

    # part drawings (static shape items, top-most first, in canvas coordinates of the rest pose)
    def body_shapes(self): return []
    def head_shapes(self): return []
    def tuft_shapes(self): return []
    def ear_shapes(self, side): return []
    def eye_shapes(self, side): return []
    def nose_shapes(self): return []
    def face_static(self): return []
    def blush_shapes(self): return []
    def hand_shapes(self, side): return dict(pads=[], mitten=[], thumb=[], thumb_at=(0, 0, 0))   # wrist at (0,0), fingers to +y
    # foot: either a plain list of shapes in canvas coordinates (mascots without legs), or a dict drawn around
    # the ankle at (0, 0):  flat=((cx, cy), (w, h)) ellipse when standing, sole=((cx, cy), (w, h)) ellipse when the
    # sole faces the viewer, pads=[shapes around the sole centre], toes=[shapes on the flat foot], color
    def foot_shapes(self, side): return []

    # ------------------------------------------------------------------ helpers
    def side(self, d, s):
        """Look up a per-side value given for the right side only (mirrors for the left)."""
        if s in d:
            return d[s]
        return mirror_pt(d["R"], self.CX)

    def A(self, fn, hold=False, tol=None):
        return Anim([fn(f) for f in range(self.n)], hold=hold, tol=tol)

    def ch(self, name, k=1.0, off=0.0, tol=None):
        return Anim([float(v) * k + off for v in self.T[name]], tol=tol)

    def const(self, name):
        a = self.T[name]
        return bool(np.all(np.abs(a - a[0]) < 1e-9))

    # ------------------------------------------------------------------ named poses
    def ik(self, target, bend=1.0, ln=1.0, hand=None, wr=0.0, max_len=1.7):
        """(shoulder, elbow, wrist, length) so the RIGHT wrist reaches `target` (rest-pose canvas coordinates).

        bend=+1 puts the elbow outwards, -1 inwards.  `hand` = absolute heading of the paw (0 down, 90 out, 180 up).
        The arm stretches (cartoon style) when the target is out of reach.
        """
        S = self.shoulder["R"]
        vx, vy = target[0] - S[0], target[1] - S[1]
        dist = math.hypot(vx, vy)
        base = self.arm["L1"] + self.arm["L2"]
        if dist > base * ln * 0.985:
            ln = min(max_len, dist / (base * 0.985))
        L1, L2 = self.arm["L1"] * ln, self.arm["L2"] * ln
        d = min(max(dist, abs(L1 - L2) + 1e-3), L1 + L2 - 1e-3)
        phi = math.degrees(math.atan2(vx, vy))
        alpha = math.degrees(math.acos(max(-1.0, min(1.0, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d)))))
        beta = math.degrees(math.acos(max(-1.0, min(1.0, (L1 * L1 + L2 * L2 - d * d) / (2 * L1 * L2)))))
        shd = (phi + bend * alpha + 100.0) % 360.0 - 100.0    # raise arms through the outside, not across the body
        elb = -bend * (180.0 - beta)
        if hand is not None:
            wr = (hand - (shd + elb) + 180.0) % 360.0 - 180.0
        return (shd, elb, wr, ln)

    def pose(self, name):
        """Named arm pose -> dict(v=(sh, el, wr, len), front=True/False/None, palm=bool)."""
        p = self.arm_poses[name]
        if isinstance(p, dict):
            return p
        return dict(v=tuple(p), front=None, palm=False)

    def tail_ctrl(self):
        return len(self.tail["poses"]["rest"])

    def tailvec(self, name):
        """Named tail pose -> [base heading, bends..., base offset x, base offset y]."""
        v = list(self.tail["poses"][name]) if isinstance(name, str) else list(name)
        if len(v) == self.tail_ctrl():
            v += [0.0, 0.0]
        return np.array(v, dtype=float)

    def stancevec(self, name):
        """Named stance -> numbers in rig.STANCE order."""
        v = self.stances[name] if isinstance(name, str) else name
        if len(v) != len(rig.STANCE):
            raise ValueError(f"stance {name!r} needs {len(rig.STANCE)} numbers: {rig.STANCE}")
        return np.array(v, dtype=float)

    @property
    def leg_len(self):
        """Hip joint to ankle when standing at rest."""
        h, a = self.hip["R"], self.foot["R"]
        return math.hypot(a[0] - h[0], a[1] - h[1])

    # ------------------------------------------------------------------ rig solves (rest-pose "body space")
    def arm_solve(self, s, f):
        """Shoulder, elbow, wrist positions and the paw's heading, in body space."""
        T = self.T
        sgn = 1.0 if s == "R" else -1.0
        S = self.side(self.shoulder, s)
        shd, elb, wr = T[f"arm.{s}.sh"][f], T[f"arm.{s}.el"][f], T[f"arm.{s}.wr"][f]
        ln = max(0.3, T[f"arm.{s}.len"][f])
        L1, L2 = self.arm["L1"] * ln, self.arm["L2"] * ln
        d1, d2 = heading(shd), heading(shd + elb)
        E = (S[0] + sgn * d1[0] * L1, S[1] + d1[1] * L1)
        W = (E[0] + sgn * d2[0] * L2, E[1] + d2[1] * L2)
        return S, E, W, shd + elb + wr

    def hand_rot(self, s, f):
        """Total rotation (Lottie degrees) of the paw relative to the body."""
        ang = self.arm_solve(s, f)[3]
        return -ang if s == "R" else ang

    def root_pos(self, f):
        T, cx, gy = self.T, self.CX, self.GROUND
        sc = T["root.scale"][f]
        h = T["root.pivot"][f] * sc * T["root.sy"][f]
        r = math.radians(T["root.rot"][f])
        return (cx + T["root.x"][f] - math.sin(r) * h, gy + T["root.y"][f] - h + math.cos(r) * h)

    def root_to_world(self, f, p):
        T, cx, gy = self.T, self.CX, self.GROUND
        sc = T["root.scale"][f]
        q = ((p[0] - cx) * sc * T["root.sx"][f], (p[1] - gy) * sc * T["root.sy"][f])
        q = rot_pt(q, T["root.rot"][f])
        rp = self.root_pos(f)
        return (rp[0] + q[0], rp[1] + q[1])

    def hips_to_root(self, f, p):
        """A point riding on the pelvis (rest-pose coordinates) -> root space."""
        T, pv = self.T, self.pelvis
        q = rot_pt((p[0] - pv[0], p[1] - pv[1]), T["hip.rot"][f])
        return (pv[0] + T["hip.x"][f] + q[0], pv[1] + T["hip.y"][f] + q[1])

    def body_to_world(self, f, p):
        T, pv = self.T, self.pelvis
        q = ((p[0] - pv[0]) * T["body.sx"][f], (p[1] - pv[1]) * T["body.sy"][f])
        q = rot_pt(q, T["body.rot"][f])
        return self.root_to_world(f, self.hips_to_root(f, (pv[0] + T["body.x"][f] + q[0], pv[1] + T["body.y"][f] + q[1])))

    def head_pt(self, p):
        """A point of the head drawing -> rest-pose body space (use it to place paws on the face)."""
        nk, at, k = self.neck, self.neck_at or self.neck, self.head_scale
        return (at[0] + (p[0] - nk[0]) * k, at[1] + (p[1] - nk[1]) * k)

    def crown_world(self, f=0):
        """Top of the head on the canvas at frame f."""
        return self.head_to_world(f, self.crown)

    def middle_root(self, f=0):
        """Roughly the middle of the figure in root space (for halos and orbits), following the stance at frame f."""
        top = self.head_pt(self.crown)[1] + float(self.T["hip.y"][f])
        return (self.CX, (top + self.GROUND) / 2.0 - 6.0)

    def head_to_world(self, f, p):
        T, nk, at, k = self.T, self.neck, self.neck_at or self.neck, self.head_scale
        q = ((p[0] - nk[0]) * k * T["head.sx"][f] / T["body.sx"][f], (p[1] - nk[1]) * k * T["head.sy"][f] / T["body.sy"][f])
        q = rot_pt(q, T["head.rot"][f])
        return self.body_to_world(f, (at[0] + T["head.x"][f] + q[0], at[1] + T["head.y"][f] + q[1]))

    def world_to_body(self, f, p):
        """Inverse of body_to_world: a canvas point expressed in rest-pose body space."""
        T, cx, gy, pv = self.T, self.CX, self.GROUND, self.pelvis
        rp = self.root_pos(f)
        sc = max(T["root.scale"][f], 1e-3)
        q = rot_pt((p[0] - rp[0], p[1] - rp[1]), -T["root.rot"][f])
        q = (cx + q[0] / (sc * T["root.sx"][f]), gy + q[1] / (sc * T["root.sy"][f]))                      # root space
        q = rot_pt((q[0] - pv[0] - T["hip.x"][f], q[1] - pv[1] - T["hip.y"][f]), -T["hip.rot"][f])       # relative to the pelvis
        q = rot_pt((q[0] - T["body.x"][f], q[1] - T["body.y"][f]), -T["body.rot"][f])
        return (pv[0] + q[0] / T["body.sx"][f], pv[1] + q[1] / T["body.sy"][f])

    def apply_pins(self, clip):
        """Planted paws: replace the keyed arm pose by an IK solve towards a fixed scene point."""
        T = self.T
        for pin in clip.pins:
            s = pin["side"]
            for f in range(self.n):
                b = max(pin["blend"], 1)
                w = min(1.0, (f - pin["t0"] + b) / b, (pin["t1"] + b - f) / b)
                if w <= 0:
                    continue
                w = 0.5 - 0.5 * math.cos(math.pi * w)
                at = pin["at"](f) if callable(pin["at"]) else pin["at"]
                hand = pin["hand"](f) if callable(pin["hand"]) else pin["hand"]
                bp = self.world_to_body(f, at)
                if s == "L":
                    bp = mirror_pt(bp, self.CX)
                new = self.ik(bp, bend=pin["bend"], hand=hand)
                for key, val in zip(("sh", "el", "wr", "len"), new):
                    ch = f"arm.{s}.{key}"
                    old = T[ch][f]
                    if key != "len":
                        val = old + ((val - old + 180.0) % 360.0 - 180.0)     # blend the short way round
                    T[ch][f] = old + (val - old) * w

    def hand_to_world(self, s, f, local=(0.0, 0.0)):
        """A point given in paw coordinates (wrist at origin, fingers towards +y) -> canvas."""
        _, _, W, _ = self.arm_solve(s, f)
        k = self.T[f"hand.{s}.s"][f]
        q = rot_pt((local[0] * k, local[1] * k), self.hand_rot(s, f))
        return self.body_to_world(f, (W[0] + q[0], W[1] + q[1]))

    def tail_headings(self):
        """(frames, bones) array of bone headings, resampled from the few control values a pose is made of."""
        tl = self.tail
        nc, nb = self.tail_ctrl(), tl["bones"]
        P = self.T["tail"]
        heads = np.cumsum(P[:, :nc], axis=1)
        xs = np.array([0.0] + [(c + 0.5) / nc for c in range(nc)] + [1.0])
        us = np.array([(j + 0.5) / nb for j in range(nb)])
        out = np.zeros((self.n, nb))
        for f in range(self.n):
            hs = np.concatenate([[heads[f, 0]], heads[f], [heads[f, -1]]])
            out[f] = np.interp(us, xs, hs)
        return out

    # ------------------------------------------------------------------ layers
    def root_layer(self):
        T, cx, gy = self.T, self.CX, self.GROUND
        return Layer(
            "root", null=True, a=(cx, gy), p=self.A(self.root_pos), r=self.ch("root.rot", tol=0.12),
            s=self.A(lambda f: (T["root.scale"][f] * T["root.sx"][f] * 100, T["root.scale"][f] * T["root.sy"][f] * 100), tol=0.12),
        )

    def shadow_layer(self):
        T, sd = self.T, self.shadow
        c = sd["c"]
        return Layer(
            "shadow", [gr("shadow", [el(c, sd["size"]), fl(self.pal["dark"], sd["o"])])],
            a=c, p=self.A(lambda f: (c[0] + T["root.x"][f], c[1])),
            s=self.A(lambda f: (T["shadow.s"][f] * 100, T["shadow.s"][f] * 100), tol=0.6),
            o=self.ch("shadow.o", 100),
        )

    def hips_layer(self):
        T, pv = self.T, self.pelvis
        return Layer("hips", null=True, parent="root", a=pv, p=self.A(lambda f: (pv[0] + T["hip.x"][f], pv[1] + T["hip.y"][f])),
                     r=self.ch("hip.rot", tol=0.12))

    def body_layer(self):
        T, pv = self.T, self.pelvis
        return Layer(
            "body", self.body_shapes(), parent="hips", a=pv,
            p=self.A(lambda f: (pv[0] + T["body.x"][f], pv[1] + T["body.y"][f])), r=self.ch("body.rot", tol=0.12),
            s=self.A(lambda f: (T["body.sx"][f] * 100, T["body.sy"][f] * 100), tol=0.15),
        )

    def head_layers(self):
        """Top-most first: brows, eyes, face, head, ears.  All hang from the 'neck' null."""
        T, nk, at, hk = self.T, self.neck, self.neck_at or self.neck, self.head_scale * 100.0
        out = []
        out.append(Layer("brows", self.brow_groups(), parent="neck"))
        out.append(Layer("eyes", self.eye_groups(), parent="neck"))
        out.append(Layer("face", self.face_groups(), parent="neck"))
        tp = self.tuft_pivot
        head_items = [gr("tuft", self.tuft_shapes(), a=tp, p=tp, r=self.ch("tuft.rot", tol=0.6))] + self.head_shapes()
        out.append(Layer("head", head_items, parent="neck"))
        for s, nm in (("R", "right ear"), ("L", "left ear")):
            pv = self.side(self.ear_pivot, s)
            out.append(Layer(nm, self.ear_shapes(s), parent="neck", a=pv, p=pv, r=self.ch(f"ear.{s}.rot", tol=0.3),
                             s=self.A(lambda f, s=s: (100, T[f"ear.{s}.sy"][f] * 100))))
        out.append(Layer(
            "neck", null=True, parent="body", a=nk,
            p=self.A(lambda f: (at[0] + T["head.x"][f], at[1] + T["head.y"][f])), r=self.ch("head.rot", tol=0.12),
            # the chest swelling lifts the head but must not inflate it, so the body's own scale is cancelled here
            s=self.A(lambda f: (T["head.sx"][f] / T["body.sx"][f] * hk, T["head.sy"][f] / T["body.sy"][f] * hk), tol=0.15),
        ))
        return out

    # ---- face
    def eye_open(self, s, f):
        T = self.T
        return float(np.clip(T["eye.open"][f] * (1.0 - T[f"eye.{s}.blink"][f]), 0.0, 1.3))

    EYE_SWAP = 0.14

    def eye_groups(self):
        T, pal = self.T, self.pal
        groups = []
        lid = self.lid
        for s in ("R", "L"):
            c = self.side(self.eye, s)
            is_open = lambda f, s=s: self.eye_open(s, f) >= self.EYE_SWAP

            def lidpath(f, c=c):
                a = float(T["eye.arc"][f])
                w = lid["w"] * float(T["eye.w"][f])
                y0 = c[1] + lid["dy"] + (4.0 if a > 0 else 0.0) * abs(a)
                top = -a * lid["rise"]
                return Path(
                    [(c[0] - w, y0), (c[0], y0 + top), (c[0] + w, y0)],
                    i=[(0, 0), (-w * 0.55, 0), (-w * 0.28, top * 0.75)],
                    o=[(w * 0.28, top * 0.75), (w * 0.55, 0), (0, 0)],
                    closed=False,
                )

            groups.append(gr(
                f"lid {s}", [sh(self.A(lidpath)), st(pal["dark"], lid["stroke"])],
                o=self.A(lambda f, io=is_open: 0 if io(f) else 100, hold=True),
            ))
            groups.append(gr(
                f"eye {s}", self.eye_shapes(s), a=c,
                p=self.A(lambda f, c=c, s=s: (c[0] + (T["look.x"][f] + (-1.0 if s == "R" else 1.0) * 1.3 * T["eye.cross"][f]) * self.eye_look,
                                               c[1] + T["look.y"][f] * self.eye_look)),
                s=self.A(lambda f, s=s: (T["eye.w"][f] * 100, T["eye.h"][f] * max(self.eye_open(s, f), self.EYE_SWAP * 0.8) * 100), tol=0.5),
                o=self.A(lambda f, io=is_open: 100 if io(f) else 0, hold=True),
            ))
        return groups

    def brow_groups(self):
        T, pal, b = self.T, self.pal, self.brow
        groups = []
        for s, sgn in (("R", 1.0), ("L", -1.0)):
            c = self.side(self.eye, s)
            c = (c[0], c[1] + b["dy"])
            h = b["half"]
            groups.append(gr(
                f"brow {s}", [sh(Path([(c[0] - h, c[1]), (c[0] + h, c[1])], closed=False)), st(pal["dark"], b["stroke"])],
                a=c, p=self.A(lambda f, c=c: (c[0], c[1] - T["brow.y"][f])), r=self.ch("brow.tilt", sgn),
                o=self.A(lambda f: float(np.clip(T["brow.show"][f], 0, 1)) * 100),
            ))
        return groups

    LIPS = {
        1: ([(-28, 3), (-13.5, 12), (0, 0), (13.5, 12), (28, 3)],
            [(0, 0), (-7, 1.5), (-2, 8), (-7, -1.5), (-3.5, 5.5)],
            [(3.5, 5.5), (7, -1.5), (2, 8), (7, 1.5), (0, 0)]),
        0: ([(-20, 8), (-10, 8.6), (0, 8), (10, 8.6), (20, 8)],
            [(0, 0), (-3, 0), (-3, 0.3), (-3, 0), (-3, 0)],
            [(3, 0), (3, 0), (3, -0.3), (3, 0), (0, 0)]),
        -1: ([(-20, 16), (-10.5, 9), (0, 6.5), (10.5, 9), (20, 16)],
             [(0, 0), (-4, 2), (-4, 0), (-4, -1.5), (-3, -4)],
             [(3, -4), (4, -1.5), (4, 0), (4, 2), (0, 0)]),
    }
    BOWL = dict(top=6.5, half=15.5, depth=27.0)

    def lips_path(self, f):
        T = self.T
        m = self.mouth
        s = float(np.clip(T["mouth.smile"][f], -1.0, 1.25))
        w = float(T["mouth.w"][f])
        a, b, t = (self.LIPS[0], self.LIPS[1], s) if s >= 0 else (self.LIPS[0], self.LIPS[-1], -s)
        mix = lambda A_, B_: [((1 - t) * p[0] + t * q[0], (1 - t) * p[1] + t * q[1]) for p, q in zip(A_, B_)]
        v, i, o = mix(a[0], b[0]), mix(a[1], b[1]), mix(a[2], b[2])
        return Path([(m[0] + x * w, m[1] + y) for x, y in v], [(x * w, y) for x, y in i], [(x * w, y) for x, y in o], closed=False)

    def face_groups(self):
        T, pal, m = self.T, self.pal, self.mouth
        B = self.BOWL
        top, half, depth = B["top"], B["half"], B["depth"]
        bowl = smooth([(m[0] - half, m[1] + top), (m[0] + half, m[1] + top), (m[0] + half * 0.8, m[1] + top + depth * 0.6),
                       (m[0], m[1] + top + depth), (m[0] - half * 0.8, m[1] + top + depth * 0.6)],
                      closed=True, tension=0.38, sharp={0: 0.25, 1: 0.25})
        mo = lambda f: float(np.clip(T["mouth.o"][f], 0, 1.4))
        op = lambda f: float(np.clip(T["mouth.open"][f], 0, 1.3))
        groups = [
            gr("lips", [sh(self.A(self.lips_path)), st(pal["dark"], 6)],
               o=self.A(lambda f: float(np.clip(1.0 - mo(f) * 1.6, 0, 1)) * 100)),
            gr("mouth o", [el((m[0], m[1] + 13), (15, 18)), fl(pal["dark"])], a=(m[0], m[1] + 13), p=(m[0], m[1] + 13),
               s=self.A(lambda f: (mo(f) * 100, mo(f) * 100)), o=self.A(lambda f: 100 if mo(f) > 0.04 else 0, hold=True)),
            gr("mouth open", [
                gr("tongue", [el((m[0], m[1] + top + depth * 0.74), (half * 1.25, depth * 0.46)), fl(pal["pink"])]),
                gr("bowl", [sh(bowl), fl(pal["dark"])]),
            ], a=(m[0], m[1] + top), p=(m[0], m[1] + top),
               s=self.A(lambda f: ((0.72 + 0.28 * op(f)) * T["mouth.w"][f] * 100, op(f) * 100)),
               o=self.A(lambda f: 100 if op(f) > 0.04 else 0, hold=True)),
            gr("blep", [el((m[0] + 3, m[1] + 14), (12, 14)), fl(pal["pink"])], a=(m[0] + 3, m[1] + 7), p=(m[0] + 3, m[1] + 7),
               s=self.A(lambda f: (100, float(np.clip(T["tongue"][f], 0, 1.4)) * 100)),
               o=self.A(lambda f: 100 if T["tongue"][f] > 0.05 else 0, hold=True)),
            gr("nose", self.nose_shapes(), a=self.nose, p=self.A(lambda f: (self.nose[0], self.nose[1] + T["nose.y"][f])),
               s=self.A(lambda f: (T["nose.s"][f] * 100, T["nose.s"][f] * 100))),
            gr("blush", self.blush_shapes(), o=self.A(lambda f: float(np.clip(T["blush"][f], 0, 1.5)) * self.pal.get("blush_o", 62))),
        ]
        return groups + self.face_static()

    # ---- limbs: real bone chains (nested groups), so every joint is a plain rotation
    def arm_layer(self, s, front, held_under=(), held_over=(), only_hand=False, name=None):
        T, pal, arm = self.T, self.pal, self.arm
        sgn = 1.0 if s == "R" else -1.0
        side_nm = "right" if s == "R" else "left"
        both = not self.const(f"arm.{s}.front")
        o = self.A(lambda f: 100 if (T[f"arm.{s}.front"][f] > 0.5) == front else 0, hold=True) if both else 100
        if only_hand:
            o = self.A(lambda f: 100 if T[f"hand.{s}.over"][f] > 0.5 else 0, hold=True)
        ln = lambda f: max(0.3, float(T[f"arm.{s}.len"][f]))
        L1, L2, w = arm["L1"], arm["L2"], arm["w"]
        hs = self.hand_shapes(s)
        palm = lambda f: float(np.clip(T[f"hand.{s}.palm"][f], 0, 1))
        tx, ty, trot = hs["thumb_at"]
        # turning the paw over: the thumb slides behind the mitten to the opposite edge while the pads fade in
        thumb = gr("thumb", hs["thumb"], p=self.A(lambda f: (tx * (1 - 2 * palm(f)), ty), tol=0.5), r=self.A(lambda f: trot * (1 - 2 * palm(f)), tol=1.0))
        hand = gr(
            "hand",
            list(held_over) + [gr("pads", hs["pads"], o=self.A(lambda f: palm(f) * 100, tol=2.0)), thumb] + hs["mitten"] + list(held_under),
            p=self.A(lambda f: (0.0, L2 * ln(f))), r=self.ch(f"arm.{s}.wr", -sgn, tol=0.6),
            s=self.A(lambda f: (T[f"hand.{s}.s"][f] * 100, T[f"hand.{s}.s"][f] * 100)),
        )
        fore_items = [hand]
        if not only_hand:
            fore_items.append(gr("forearm skin", [sh(self.A(lambda f: Path([(0, 0), (0, L2 * ln(f))], closed=False))), st(pal["arm"], w)]))
        fore = gr("forearm", fore_items, p=self.A(lambda f: (0.0, L1 * ln(f))), r=self.ch(f"arm.{s}.el", -sgn, tol=0.4))
        upper_items = [fore]
        if not only_hand:
            upper_items.append(gr("upper arm skin", [sh(self.A(lambda f: Path([(0, 0), (0, L1 * ln(f))], closed=False))), st(pal["arm"], w)]))
        upper = gr("upper arm", upper_items, r=self.ch(f"arm.{s}.sh", -sgn, tol=0.35))
        nm = name or f"{side_nm} arm{' front' if (front and both) else ''}"
        return Layer(nm, [upper], parent="body", a=(0, 0), p=self.side(self.shoulder, s), o=o)

    # ---- legs: one bendy limb per side, solved from the hip joint to wherever the foot is planted
    def solve_legs(self):
        """Per-frame hip joint H, knee K and ankle A of both legs (root space), the leg's screen rotation and length."""
        T, lg = self.T, self.leg
        L0 = self.leg_len
        full = L0 / (1.0 - lg.get("slack", 0.04))             # a relaxed standing leg is not quite straight
        self.legs = {}
        for s in "RL":
            sgn = 1.0 if s == "R" else -1.0
            J, F0 = self.side(self.hip, s), self.side(self.foot, s)
            H, K, A = np.zeros((self.n, 2)), np.zeros((self.n, 2)), np.zeros((self.n, 2))
            phi, Ln = np.zeros(self.n), np.zeros(self.n)
            for f in range(self.n):
                h = self.hips_to_root(f, J)
                a = (F0[0] + sgn * T[f"foot.{s}.x"][f], F0[1] + T[f"foot.{s}.y"][f])
                dx, dy = a[0] - h[0], a[1] - h[1]
                L = math.hypot(dx, dy)
                mx = lg.get("stretch", 1.2) * L0
                if L > mx:                                     # out of reach: the foot comes along with the hip
                    a = (h[0] + dx * mx / L, h[1] + dy * mx / L)
                    dx, dy, L = a[0] - h[0], a[1] - h[1], mx
                u = (dx / L, dy / L) if L > 1e-6 else (0.0, 1.0)
                k = math.sqrt(max(0.0, (full * 0.5) ** 2 - (L * 0.5) ** 2)) * lg.get("knee", 0.9) * T[f"leg.{s}.bend"][f]
                H[f], A[f] = h, a
                K[f] = ((h[0] + a[0]) / 2 + u[1] * sgn * k, (h[1] + a[1]) / 2 - u[0] * sgn * k)   # knee bows away from the body
                phi[f] = math.degrees(math.atan2(-u[0], u[1]))
                Ln[f] = L
            self.legs[s] = dict(H=H, K=K, A=A, phi=phi, L=Ln)

    def leg_layers(self):
        pal, lg = self.pal, self.leg
        L0, w0 = self.leg_len, lg["w"]
        out = []
        for s, nm in (("R", "right leg"), ("L", "left leg")):
            G = self.legs[s]
            path = lambda f, G=G: smooth([tuple(G["H"][f]), tuple(G["K"][f]), tuple(G["A"][f])], closed=False, tension=0.36)
            # squash and stretch: a shortened leg gets chunkier, a stretched one thinner
            width = lambda f, G=G: w0 * (1.0 + lg.get("bulge", 0.22) * (1.0 - min(G["L"][f] / L0, 1.4)))
            out.append(Layer(nm, [gr("leg", [sh(self.A(path, tol=0.55)), st(pal.get("leg", pal["orange"]), self.A(width, tol=0.4))])], parent="root"))
        return out

    def foot_layers(self):
        T, pal = self.T, self.pal
        out = []
        if self.leg is None:                                    # feet only: they hang from the root
            for s, sgn, nm in (("R", 1.0, "right foot"), ("L", -1.0, "left foot")):
                c = self.side(self.foot, s)
                out.append(Layer(
                    nm, self.foot_shapes(s), parent="root", a=c,
                    p=self.A(lambda f, c=c, sgn=sgn, s=s: (c[0] + sgn * T[f"foot.{s}.x"][f], c[1] + T[f"foot.{s}.y"][f])),
                    r=self.ch(f"foot.{s}.rot", sgn, tol=0.5),
                ))
            return out
        mix = lambda a, b, t: (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        follow = self.leg.get("foot_follow", 0.8)
        for s, sgn, nm in (("R", 1.0, "right foot"), ("L", -1.0, "left foot")):
            fs, G = self.foot_shapes(s), self.legs[s]
            sole = lambda f, s=s: float(np.clip(T[f"foot.{s}.sole"][f], 0, 1))
            (fc, fz), (sc, sz) = fs["flat"], fs["sole"]
            items = []
            if fs.get("pads"):                                  # pads come into view as the foot tips up towards the viewer
                items.append(gr("pads", fs["pads"], a=(0, 0), p=sc, o=self.A(lambda f: min(1.0, sole(f) * 2.4) * 100, tol=2.0),
                                s=self.A(lambda f: (100, 45 + 55 * sole(f)), tol=1.5)))
            if fs.get("toes"):
                items.append(gr("toes", fs["toes"], o=self.A(lambda f: (1 - min(1.0, sole(f) * 2.5)) * 100, tol=2.0)))
            items.append(gr("foot", [el(self.A(lambda f: mix(fc, sc, sole(f))), self.A(lambda f: mix(fz, sz, sole(f)))), fl(fs.get("color", pal["dark"]))]))

            def rot(f, s=s, sgn=sgn, G=G):
                # a lifted foot turns with its leg; a planted one stays flat on the ground
                clear = float(np.clip((self.height[f] - T[f"foot.{s}.y"][f]) / 10.0, 0.0, 1.0))
                return sgn * T[f"foot.{s}.rot"][f] + G["phi"][f] * follow * clear * T["plant"][f]

            out.append(Layer(nm, items, parent="root", a=(0, 0), p=Anim([tuple(v) for v in G["A"]], tol=0.4),
                             r=self.A(rot, tol=0.8), s=self.A(lambda f, s=s: (T[f"foot.{s}.s"][f] * 100, T[f"foot.{s}.s"][f] * 100), tol=0.6)))
        return out

    TAIL_SLOTS = ("tail", "tail lap", "tail front")

    def tail_slot(self, f):
        v = self.T["tail.front"][f]
        return 0 if v <= 0.5 else (1 if v <= 1.5 else 2)

    def tail_layer(self, slot):
        """slot 0: behind the body, 1: in the lap (in front of the body, behind the feet), 2: in front of the feet."""
        T, tl, pal = self.T, self.tail, self.pal
        used = sorted({self.tail_slot(f) for f in range(self.n)})
        o = self.A(lambda f: 100 if self.tail_slot(f) == slot else 0, hold=True) if len(used) > 1 else 100
        nb = tl["bones"]
        Lb = tl["length"] / nb
        xs, ys = zip(*tl["profile"])
        radii = [0.5 * pchip(xs, ys, j / nb) for j in range(nb)]
        k = int(math.ceil(tl["tip_from"] * nb - 1e-9))        # first bone in the tip colour
        heads = self.tail_headings()

        # --- skin: every bone carries a disc at its joint and a wedge reaching the next joint, tangent to both
        # discs.  Together they form one smooth tapering tube in ANY pose (bones are short, so the straight
        # wedge edges stay within a fraction of a pixel of the ideal curve).
        tip_r, ext = tl.get("tip_r", 8.0), tl.get("tip_ext", 14.0)

        def wedge(r0, r1, L):
            sa = max(-0.95, min(0.95, (r0 - r1) / L))
            ca = math.sqrt(1 - sa * sa)
            return [(r0 * sa, -r0 * ca), (L + r1 * sa, -r1 * ca), (L + r1 * sa, r1 * ca), (r0 * sa, r0 * ca)]

        def skin(j):
            r0 = radii[j]
            last = j == nb - 1
            r1, L = (tip_r, Lb + ext) if last else (radii[j + 1], Lb)
            q = wedge(r0, r1, L)
            items = []
            if j == k and tl.get("furry", True):
                # furry edge where the colour changes: rim, spike, valley, spike, rim (spikes point at the base)
                z = [q[0], q[1], q[2], q[3], (0, r0), (-0.66 * r0, 0.47 * r0), (-0.12 * r0, 0.0), (-0.66 * r0, -0.47 * r0), (0, -r0)]
                items.append(sh(Path(z, closed=True)))
            else:
                items.append(sh(Path(q, closed=True)))
                items.append(el((0, 0), (2 * r0, 2 * r0)))
            if last:
                items.append(el((L, 0), (2 * r1, 2 * r1)))
            elif j == k - 1:                                   # fills the outside of the bend under the colour change
                items.append(el((Lb, 0), (1.94 * r1, 1.94 * r1)))
            return gr(f"skin {j}", items + [fl(pal["tail_tip"] if j >= k else pal["tail"])])

        node = None
        for j in reversed(range(nb)):
            items = ([node] if node is not None else []) + [skin(j)]
            if j == 0:
                node = gr("tail 0", items, r=Anim(list(-heads[:, 0]), tol=0.15))
            else:
                node = gr(f"tail {j}", items, p=(Lb, 0), r=Anim(list(-(heads[:, j] - heads[:, j - 1])), tol=0.12))
        base = tl["base"]
        nc = self.tail_ctrl()
        return Layer(
            self.TAIL_SLOTS[slot] if len(used) > 1 else "tail", [node], parent="hips", a=(0, 0),
            p=self.A(lambda f: (base[0] + T["tail"][f][nc], base[1] + T["tail"][f][nc + 1])),
            s=self.A(lambda f: (T["tail.len"][f] * T["tail.fluff"][f] * 100, T["tail.len"][f] * T["tail.fluff"][f] * 100)), o=o,
        )

    # ------------------------------------------------------------------ assembly
    SLOTS = ("top", "front", "mid", "back", "hand.R", "hand.L", "hand.R.over", "hand.L.over")

    def build(self, clip):
        """Bake one clip into a Lottie document."""
        self.clip = clip
        self.n = clip.frames + 1
        self.T = T = rig.evaluate(clip, self)
        self.height = np.clip(-T["root.y"], 0, None) / np.maximum(T["root.scale"] * T["root.sy"], 0.2)
        self.apply_pins(clip)
        if self.leg is not None:
            self.solve_legs()
        fx = {k: [] for k in self.SLOTS}
        for spec in clip.props:
            for slot, payload in spec(self, T, self.n):
                fx[slot].append(payload)

        def arms(front):
            out = []
            for s in "RL":
                used = bool(np.any((T[f"arm.{s}.front"] > 0.5) == front))
                if used:
                    out.append(self.arm_layer(s, front, held_under=fx[f"hand.{s}"], held_over=fx[f"hand.{s}.over"]))
            return out

        layers = []
        if clip.opts.get("hands_over_top"):                    # paws that must sit above a foreground prop
            for s in "RL":
                if np.any(T[f"arm.{s}.front"] > 0.5):
                    layers.append(self.arm_layer(s, True, only_hand=True, name=("right" if s == "R" else "left") + " paw"))
        layers += fx["top"]
        layers += arms(True)
        layers += fx["front"]
        layers += self.head_layers()
        layers += arms(False)
        layers += fx["mid"]
        slots = {self.tail_slot(f) for f in range(self.n)} if self.tail is not None else set()
        if 2 in slots:
            layers.append(self.tail_layer(2))
        layers += self.foot_layers()
        if 1 in slots:
            layers.append(self.tail_layer(1))
        layers.append(self.body_layer())
        if self.leg is not None:
            layers += self.leg_layers()
        if 0 in slots:
            layers.append(self.tail_layer(0))
        layers.append(self.hips_layer())
        layers.append(self.root_layer())
        layers += fx["back"]
        layers.append(self.shadow_layer())
        return document(clip.name, layers, op=clip.frames)
