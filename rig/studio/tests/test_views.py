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
from mascot.views import bucket_of, norm_deg  # noqa: E402
from studio.compose import compose  # noqa: E402
from studio.export import TGS_MAX, tgs_bytes  # noqa: E402
from studio.qa import view_proportions  # noqa: E402
from studio.registry import REG  # noqa: E402
from studio.spec import StickerSpec  # noqa: E402


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

    def test_mirrored_side_moves_the_near_paw_from_the_right_arm(self):
        ch, c = standing("biscuit", body=-90.0, R="wave_hi")
        doc = ch.build(c)
        ly = {L["nm"]: L for L in doc["layers"]}
        upper = ly["left arm front [side-]"]["shapes"][0] if "left arm front [side-]" in ly else ly["left arm [side-]"]["shapes"][0]
        rot = upper["it"][-1]["r"]
        val = rot["k"] if rot["a"] == 0 else rot["k"][0]["s"][0]
        turn = ch.view_data("side").get("arm_turn", 0.0)          # seen from the side the arms hang a little further forward
        self.assertAlmostEqual(abs(val), abs(ch.T["arm.R.sh"][0] + turn), delta=0.6)

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

    def test_turning_motions_and_fallback_notes(self):
        doc, info = compose(StickerSpec(base="biscuit", motion="turn_around"))
        self.assertEqual(info["notes"], [])
        self.assertTrue(any(n.endswith("[back]") for n in names(doc)))
        _, info = compose(StickerSpec(base="mochi", motion="look_back"))
        self.assertIn("looks around instead", " ".join(info["notes"]))
        _, info = compose(StickerSpec(base="pip", yaw=60.0))
        self.assertIn("as far as three-quarter", " ".join(info["notes"]))

    def test_front_only_wear_is_left_out_of_drawn_views(self):
        doc, _ = compose(StickerSpec(base="biscuit", yaw=90.0, accessories=["glasses", "crown"]))
        ly = {L["nm"]: L for L in doc["layers"]}
        self.assertNotIn("wear glasses", ly)
        self.assertIn("wear crown", ly)


if __name__ == "__main__":
    unittest.main()
