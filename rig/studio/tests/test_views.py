"""v5 phase 2 tests: the view rig (turning away from the viewer).  Run from rig/:   python3 -m unittest studio.tests.test_views -v"""
from __future__ import annotations

import json
import math
import os
import tempfile
import unittest

import numpy as np

os.environ.setdefault("STUDIO_CACHE", tempfile.mkdtemp())

from mascot.build import characters  # noqa: E402
from mascot.clip import Clip  # noqa: E402
from mascot.scene import Scene, Stage  # noqa: E402
from mascot.views import bucket_of, norm_deg, prop_at  # noqa: E402
from studio.compose import compose  # noqa: E402
from studio.export import TGS_MAX, tgs_bytes  # noqa: E402
from studio.qa import view_proportions  # noqa: E402
from studio.registry import REG  # noqa: E402
from studio.spec import StickerSpec  # noqa: E402
from studio.tests.lottie_points import group_matrix, layer_matrix, point, turn_of  # noqa: E402


def standing(name, body=None, head=None, frames=2, **arms):
    """(character, clip) of a mascot standing at rest; body / head: a yaw in degrees or a list of keys."""
    ch = characters()[name]()
    c = Clip(f"views_{name}", frames, loop=True, char=ch)
    c.face(0, "smiley", dur=0)
    c.arm("LR", (0, "rest"))
    for s, pose in arms.items():
        c.arm(s, (0, pose))
    c.tailpose((0, "rest"))
    for chn, v in (("body.yaw", body), ("head.yaw", head)):
        if isinstance(v, (int, float)):
            c.set(chn, float(v))
        elif v:
            c.k(chn, *v)
    return ch, c


def names(doc):
    return [L["nm"] for L in doc["layers"]]


def shown(doc, L, t):
    return L.get("ty") == 4 and float(np.ravel(prop_at(L["ks"]["o"], t))[0]) > 0.0


def shown_group(doc, group, t, layer_start=""):
    """(layer name, world matrix) of the first layer shown at frame t that draws a group called `group`."""
    for L in doc["layers"]:
        if not L["nm"].startswith(layer_start) or not shown(doc, L, t):
            continue
        try:
            return L["nm"], group_matrix(doc, L["nm"], group, t)
        except KeyError:
            continue
    raise KeyError(f"no layer shown at frame {t} draws {group!r}")


def sway(c, frames):
    """Lean the body and shift the hips back and forth (the moves a mirrored drawing must not mirror)."""
    c.k("body.rot", (0, 0.0), (frames // 4, 6.0, "io"), (frames * 3 // 4, -6.0, "io"), (frames, 0.0, "io"))
    c.k("body.x", (0, 0.0), (frames // 3, 6.0, "io"), (frames * 2 // 3, -6.0, "io"), (frames, 0.0, "io"))
    c.k("hip.x", (0, 0.0), (frames // 3, 5.0, "io"), (frames * 2 // 3, -5.0, "io"), (frames, 0.0, "io"))
    c.k("hip.rot", (0, 0.0), (frames // 4, 4.0, "io"), (frames * 3 // 4, -4.0, "io"), (frames, 0.0, "io"))


class AtRest(unittest.TestCase):
    def test_a_turn_of_zero_writes_the_v4_file(self):
        ch, c = standing("biscuit")
        a = json.dumps(ch.build(c))
        ch, c = standing("biscuit", body=0.0, head=0.0)
        self.assertEqual(json.dumps(ch.build(c)), a)

    def test_buckets(self):
        self.assertEqual(bucket_of(30.0, True, True), "front")
        self.assertEqual(bucket_of(90.0, True, True), "side")
        self.assertEqual(bucket_of(-90.0, True, True), "side-")
        self.assertEqual(bucket_of(180.0, True, True), "back")
        self.assertEqual(bucket_of(90.0, False, False), "front")          # no side view: the three-quarter turn holds
        self.assertEqual(bucket_of(170.0, True, False), "side")           # no back view: the side shows
        self.assertEqual(float(norm_deg(360.0)), 0.0)


class Warp(unittest.TestCase):
    def test_the_face_slides_and_the_far_arm_goes_behind(self):
        ch, c = standing("mochi", body=35.0)
        doc = ch.build(c)
        order = names(doc)
        self.assertGreater(order.index("right arm"), order.index("body"), "the far arm is drawn behind the body")
        self.assertLess(order.index("left arm"), order.index("body"), "the near arm stays in front")
        nose0 = characters()["mochi"]().nose
        moved = ch.head_to_world(0, nose0)
        ch2, c2 = standing("mochi")
        ch2.build(c2)
        rest = ch2.head_to_world(0, nose0)
        self.assertGreater(moved[0] - rest[0], 15.0, "the nose slides towards the side the face turns to")
        self.assertAlmostEqual(moved[1], rest[1], places=6)

    def test_every_mascot_turns_within_telegram(self):
        for name in REG.bases:
            with self.subTest(mascot=name):
                doc, _ = compose(StickerSpec(base=name, yaw=40.0, motion="wave"))
                self.assertLess(len(tgs_bytes(doc)), TGS_MAX)

    def test_a_head_turns_on_its_own(self):
        ch, c = standing("biscuit", head=30.0)
        doc = ch.build(c)
        self.assertNotIn("head [side]", names(doc))
        self.assertIsNone(ch.view.far(0), "the body still faces the viewer")


class DrawnViews(unittest.TestCase):
    def test_side_back_and_mirrored_side(self):
        for yaw, tag, mirror in ((90.0, "[side]", False), (-90.0, "[side-]", True), (180.0, "[back]", False)):
            with self.subTest(yaw=yaw):
                ch, c = standing("biscuit", body=yaw)
                order = names(ch.build(c))
                self.assertIn(f"head {tag}", order)
                self.assertIn(f"body {tag}", order)
                self.assertNotIn("head", order, "a view never seen from the front is not written")
                self.assertEqual(any("mirror" in n for n in order), mirror)

    def test_seen_from_the_side_the_near_paw_moves_with_the_right_arm(self):
        for yaw, tag in ((90.0, "[side]"), (-90.0, "[side-]")):
            with self.subTest(yaw=yaw):
                ch, c = standing("biscuit", body=yaw, R="wave_hi")
                doc = ch.build(c)
                ly = {L["nm"]: L for L in doc["layers"]}
                upper = (ly.get(f"left arm front {tag}") or ly[f"left arm {tag}"])["shapes"][0]
                rot = upper["it"][-1]["r"]
                val = rot["k"] if rot["a"] == 0 else rot["k"][0]["s"][0]
                turn = ch.view_data("side").get("arm_turn", 0.0)          # seen from the side the arms hang a little nearer the body
                self.assertAlmostEqual(abs(val), abs(ch.T["arm.R.sh"][0] + turn), delta=0.6)

    def test_seen_from_the_side_a_paw_reaching_in_reaches_forward(self):
        for pose in ("hug", "mouth", "belly", "clap"):
            for yaw, ahead in ((90.0, 1.0), (-90.0, -1.0)):
                with self.subTest(pose=pose, yaw=yaw):
                    ch, c = standing("biscuit", body=yaw, R=pose, L=pose)
                    ch.build(c)
                    for s in "RL":
                        w, sh = ch.view.hand_at(s, 0), ch.view.shoulder_at(s, 0)
                        self.assertGreater((w[0] - sh[0]) * ahead, 10.0, f"the {s} paw reaches forward, the way the fox faces")

    def test_a_snap_squashes_for_a_moment(self):
        ch, c = standing("biscuit", body=[(0, 0.0), (60, 180.0, "lin"), (120, 360.0, "lin")], frames=120)
        doc = ch.build(c)
        sx = np.asarray(ch.T["root.sx"])
        snaps = [f for f in range(1, ch.n) if ch.view.body_bucket[f] != ch.view.body_bucket[f - 1]]
        self.assertEqual(len(snaps), 4)                    # front > side > back > side- > front
        for f in snaps:
            self.assertLess(sx[f], 0.9)
        self.assertLess(len(tgs_bytes(doc)), TGS_MAX)

    def test_without_drawn_views_the_three_quarter_holds(self):
        ch, c = standing("mochi", body=90.0)
        order = names(ch.build(c))
        self.assertFalse(any("[" in n for n in order))
        self.assertTrue(all(abs(math.degrees(t) - 45.0) < 1e-6 for t in ch.view.body_th))

    def test_drawn_views_keep_the_guides(self):
        for name in REG.bases:
            with self.subTest(mascot=name):
                self.assertEqual(view_proportions(name), [])


class DrawnPins(unittest.TestCase):
    """Paws pinned to a point, the points a scene pins to and things held in a paw, as a drawn view draws them: checked
    in the written file (the transforms a player applies), not in the rig's own sums."""

    def test_a_pinned_paw_lands_on_its_target_as_drawn(self):
        cases = ((90.0, "R", "[side]", (330.0, 300.0)), (90.0, "L", "[side]", (330.0, 300.0)),
                 (-90.0, "R", "[side-]", (180.0, 300.0)), (-90.0, "R", "[side-]", (320.0, 330.0)),     # ... and behind it
                 (180.0, "R", "[back]", (200.0, 300.0)))
        for yaw, s, tag, target in cases:
            for swaying in (False, True):
                with self.subTest(yaw=yaw, side=s, target=target, sway=swaying):
                    ch, c = standing("biscuit", body=yaw, frames=60)
                    if swaying:
                        sway(c, 60)
                    c.pin(s, 10, 50, target, hand=120.0)
                    doc = ch.build(c)
                    drawn = "left" if ch.view.drawn_side(ch.view.body_view(30), s) == "L" else "right"
                    for f in (20, 30, 40):
                        nm, M = shown_group(doc, "hand", f, layer_start=f"{drawn} arm")
                        self.assertTrue(nm.endswith(tag), nm)
                        self.assertLess(math.dist(point(M), target), 1.0, f"frame {f}: {nm}")
                        self.assertLess(math.dist(ch.hand_to_world(s, f), target), 1.0)

    def test_the_mirrored_side_view_stays_joined_under_a_sway(self):
        for yaw, tag in ((90.0, "[side]"), (-90.0, "[side-]"), (180.0, "[back]")):
            with self.subTest(yaw=yaw):
                ch, c = standing("biscuit", body=yaw, frames=60)
                sway(c, 60)
                doc = ch.build(c)
                hips = f"hips mirror {tag}" if tag == "[side-]" else "hips"
                for f in range(0, 61, 6):
                    head_neck = point(layer_matrix(doc, f"head {tag}", f), ch.neck)
                    body_neck = point(layer_matrix(doc, f"body {tag}", f), ch.neck_at or ch.neck)
                    self.assertLess(math.dist(head_neck, body_neck), 0.5, f"the head sits on the body's neck (frame {f})")
                    p = ch.view.proxy(ch.view.body_bucket[f])
                    for s, nm in (("R", "right leg"), ("L", "left leg")):
                        L = next(x for x in doc["layers"] if x["nm"] == f"{nm} {tag}")
                        top = point(layer_matrix(doc, L["nm"], f), prop_at(L["shapes"][0]["it"][0]["ks"], f)["v"][0])
                        joint = point(layer_matrix(doc, hips, f), p.side(p.hip, s))
                        self.assertLess(math.dist(top, joint), 1.0, f"the {nm} leaves the hip (frame {f})")

    def test_scene_points_are_where_the_drawn_view_draws_them(self):
        a, b = characters()["biscuit"](), characters()["biscuit"]()
        sc = Scene("profiles", frames=60)
        for ident, ch, yaw, st in (("a", a, 90.0, Stage(x=-60, y=-4, scale=0.74)), ("b", b, -90.0, Stage(x=60, y=4, scale=0.74))):
            c = Clip(f"profile {ident}", 60, loop=True, char=ch)
            c.face(0, "smiley", dur=0)
            c.arm("LR", (0, "rest"))
            if ident == "b":
                c.arm("R", (0, "rest"), (12, "hold_up", "io"), (48, "hold_up"), (58, "rest", "io"))
            c.tailpose((0, "rest"))
            c.set("body.yaw", yaw)
            sc.add(ident, ch, c, st)
        sc.pin("a", "R", 16, 44, ("b", "paw", "R"), hand=150.0, bend=-1.0, blend=6)       # a high five, face to face
        doc = sc.build()
        for f in (24, 30, 36):
            self.assertLess(sc.reach(sc.pins[0], frames=[f]), 1.65)
            _, Ma = shown_group(doc, "hand", f, layer_start="a/left arm")
            _, Mb = shown_group(doc, "hand", f, layer_start="b/left arm")
            self.assertLess(math.dist(point(Ma), point(Mb, tuple(b.paw["c"]))), 1.0, f"paw meets paw (frame {f})")
            nose = point(group_matrix(doc, "b/face [side-]", "nose", f), b.view.proxy("side-").nose)
            self.assertLess(math.dist(sc.point("b", "nose", f), nose), 1.0, "the nose a scene pins to is the nose drawn")

    def test_a_held_thing_turns_as_it_does_from_the_front(self):
        docs = {yaw: compose(StickerSpec(base="biscuit", motion="sip", yaw=yaw), frame=False)[0] for yaw in (0.0, 90.0, -90.0)}
        for f in (0, 30, 60, 90):
            front = turn_of(shown_group(docs[0.0], "mug", f)[1])
            lean = turn_of(layer_matrix(docs[0.0], "body", f))
            self.assertAlmostEqual(turn_of(shown_group(docs[90.0], "mug", f)[1]), front, delta=1.5)
            self.assertAlmostEqual(turn_of(shown_group(docs[-90.0], "mug", f)[1]), 2.0 * lean - front, delta=1.5,
                                   msg="mirrored: the same tilt the other way")


class Studio(unittest.TestCase):
    def test_yaw_is_only_written_when_turned(self):
        s = StickerSpec(motion="wave")
        self.assertNotIn("yaw", s.to_dict())
        turned = StickerSpec(motion="wave", yaw=90.0)
        self.assertEqual(turned.to_dict()["yaw"], 90.0)
        self.assertEqual(StickerSpec.from_dict(turned.to_dict()), turned)
        self.assertNotEqual(turned.key(), s.key())
        with self.assertRaises(ValueError):
            StickerSpec.from_dict(dict(yaw=200))

    def test_view_words_turn_the_mascot(self):
        from studio.parse.fallback import default_parser
        p = default_parser()
        for prompt, yaw in (("a fox from behind", 180.0), ("fox in profile", 90.0), ("cat facing left", -90.0),
                            ("three quarter view of a bunny", 40.0), ("fox facing the camera", 0.0),
                            ("side view, then from behind", 180.0)):           # the last view word said wins
            with self.subTest(prompt=prompt):
                r = p.parse(prompt)
                self.assertEqual(r.spec.yaw, yaw)
                self.assertTrue(r.confident)
        r = p.parse("fox looking left")
        self.assertEqual((r.spec.yaw, tuple(r.spec.look)), (0.0, (-1.0, 0.0)), "looking is still the gaze")
        for prompt, motion in (("turning around", "turn_around"), ("looking back over its shoulder", "look_back"),
                               ("do a 360", "full_spin"), ("spinning around", "spin")):
            with self.subTest(prompt=prompt):
                self.assertEqual(p.parse(prompt).spec.motion, motion)
        self.assertEqual(p.problems(), [])

    def test_the_editor_has_a_facing_row(self):
        from app.vocab import vocab
        ids = [c["id"] for c in vocab()["yaw"]]
        self.assertEqual(ids[0], 0.0, "front first")
        self.assertTrue({90.0, -90.0, 180.0} <= set(ids))

    def test_turning_motions_and_fallback_notes(self):
        doc, info = compose(StickerSpec(base="biscuit", motion="turn_around"))
        self.assertEqual(info["notes"], [])
        self.assertTrue(any(n.endswith("[back]") for n in names(doc)))
        _, info = compose(StickerSpec(base="mochi", motion="look_back"))
        self.assertIn("looks around instead", " ".join(info["notes"]))
        _, info = compose(StickerSpec(base="pip", yaw=60.0))
        self.assertIn("as far as three-quarter", " ".join(info["notes"]))

    def test_worn_things_have_their_own_side_and_back_drawings(self):
        side = names(compose(StickerSpec(base="biscuit", yaw=90.0, accessories=["glasses", "crown"]))[0])
        self.assertIn("wear glasses [side]", side)
        self.assertNotIn("wear glasses", side, "the front's glasses are not written when the front never shows")
        self.assertIn("wear crown", side, "a hat without drawn views is worn as drawn for the front")
        back = names(compose(StickerSpec(base="biscuit", yaw=180.0, accessories=["glasses"]))[0])
        self.assertFalse(any("glasses" in n for n in back), "glasses are not seen from behind")
        back = names(compose(StickerSpec(base="biscuit", yaw=180.0, accessories=["goggles"]))[0])
        self.assertIn("wear goggles [back]", back, "... but a goggles strap is")
        turning = names(compose(StickerSpec(base="biscuit", motion="turn_around", accessories=["backpack"]))[0])
        for v in ("", " [side]", " [back]"):
            self.assertIn(f"wear backpack{v}", turning)
        pirate = names(compose(StickerSpec(base="biscuit", yaw=90.0, accessories=["pirate_hat"]))[0])
        self.assertIn("wear pirate hat", pirate, "a hat drawn only from behind is worn as drawn for the front from the side")
        self.assertNotIn("wear pirate hat [side]", pirate)

    def test_every_worn_thing_builds_in_every_drawn_view(self):
        for name, w in REG.wear.items():
            for yaw in (90.0, -90.0, 180.0):
                with self.subTest(item=name, yaw=yaw):
                    doc, _ = compose(StickerSpec(base="biscuit", yaw=yaw, accessories=[name], seconds=1.0), frame=False)
                    self.assertLess(len(tgs_bytes(doc)), TGS_MAX)
                    view = {90.0: "side", -90.0: "side-", 180.0: "back"}[yaw]
                    drawn = [n for n in names(doc) if n.startswith("wear ") and n.endswith(f"[{view}]")]
                    if ("side" if yaw != 180.0 else "back") in w.views:
                        continue                                    # (an item may have nothing to show from there)
                    self.assertEqual(drawn, [], "an item without that view is not drawn again")

    def test_a_tear_moves_to_the_eye_the_side_view_shows(self):
        for yaw in (90.0, -90.0):
            with self.subTest(yaw=yaw):
                spec = StickerSpec(base="biscuit", effects=["tear"], yaw=yaw)
                doc, _ = compose(spec, frame=False)
                L = next(x for x in doc["layers"] if x["nm"].startswith("tear"))
                ch = characters()["biscuit"]()
                p = ch.view_data("side")["eye"]["L"]
                eye = (2.0 * ch.CX - p[0], p[1]) if yaw < 0 else p
                f = next(t for t in range(int(doc["op"])) if float(np.ravel(prop_at(L["ks"]["o"], t))[0]) > 50.0)
                at = prop_at(L["ks"]["p"], f)
                self.assertLess(math.dist(at[:2], eye), 40.0, f"the tear is at the near eye ({at[:2]} vs {eye})")


if __name__ == "__main__":
    unittest.main()
