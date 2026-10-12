"""Library and skeleton tests.  Run from rig/:   python3 -m unittest studio.tests.test_library -v

The sweep at the bottom composes every item of the library; it checks one mascot by default.  Set STUDIO_FULL_QA=1
to check every mascot at every loop length (or run `python -m studio.qa`).
"""
from __future__ import annotations

import os
import tempfile
import unittest

import numpy as np

os.environ.setdefault("STUDIO_CACHE", tempfile.mkdtemp())

from mascot.lottie import Layer, document, el, fl, gr  # noqa: E402
from mascot.props import C  # noqa: E402
from mascot.rig import FACES  # noqa: E402
from studio import qa  # noqa: E402
from studio.compose import compose, plan_for  # noqa: E402
from studio.export import frame, frames  # noqa: E402
from studio.registry import EFFECT_ZONES, REG, SIT_RULES, WEAR_ZONES  # noqa: E402
from studio.rules import RULES, describe  # noqa: E402
from studio.spec import StickerSpec  # noqa: E402

FULL = bool(os.environ.get("STUDIO_FULL_QA"))


class Registry(unittest.TestCase):
    def test_every_item_is_described(self):
        for table in (REG.motions, REG.props, REG.effects, REG.wear, REG.faces, REG.bases):
            for name, it in table.items():
                with self.subTest(item=name):
                    self.assertTrue(it.label, "no label")
                    self.assertTrue(it.emoji, "no emoji")

    def test_metadata_is_valid(self):
        for name, m in REG.motions.items():
            self.assertIn(m.sit, SIT_RULES, name)
            self.assertIn(m.paws, (0, 1, 2), name)
            if m.face:
                self.assertIn(m.face, FACES, name)
        for name, p in REG.props.items():
            self.assertIn(p.paw, ("R", "L", "LR"), name)
            self.assertTrue(REG.bases["biscuit"].load()().has_pose(p.pose), f"{name}: unknown pose {p.pose}")
            for c in p.tint:
                self.assertIn(c, C, name)
        for name, e in REG.effects.items():
            self.assertIn(e.zone, EFFECT_ZONES, name)
            if e.peak is not None:
                self.assertTrue(0 <= e.peak < 1, name)
        for name, w in REG.wear.items():
            self.assertIn(w.zone, WEAR_ZONES + ("ears",), name)

    def test_every_face_has_a_label(self):
        self.assertEqual(set(FACES), set(REG.faces))

    def test_mascots_pass_their_data_check(self):
        for name, b in REG.bases.items():
            with self.subTest(base=name):
                self.assertEqual(b.load()().problems(), [])


class Rules(unittest.TestCase):
    def test_rules_have_unique_codes_and_text(self):
        codes = [fn.code for fn in RULES]
        self.assertEqual(len(codes), len(set(codes)))
        self.assertTrue(all(text for _, text in describe()))

    def test_paws_props_and_motions(self):
        p = plan_for(StickerSpec(motion="wave", props=["phone"]))
        self.assertEqual(p.arms["R"], "hold")
        self.assertEqual(p.hands, ["L"])
        p = plan_for(StickerSpec(motion="cheer", props=["mug", "phone"]))
        self.assertEqual(p.motion, "bounce")
        p = plan_for(StickerSpec(props=["mug"], sides={"mug": "L"}))
        self.assertEqual(p.props, [("mug", "L")])

    def test_sitting_and_gift(self):
        p = plan_for(StickerSpec(motion="jump", stance="sit"))
        self.assertEqual(p.motion, "sway")
        self.assertIn(p.tail, ("ground", "ground_up", "wrap"))
        p = plan_for(StickerSpec(props=["gift"], stance="sit"))
        self.assertEqual(p.stance, "wide")

    def test_one_thing_per_place(self):
        p = plan_for(StickerSpec(accessories=["glasses", "sunglasses", "crown"], effects=["zzz", "rain", "sparkles"]))
        self.assertEqual(p.wear, ["glasses", "crown"])
        self.assertEqual(p.effects, ["zzz", "sparkles"])

    def test_any_fur_colour(self):
        p = plan_for(StickerSpec(palette={"orange": "#2a9d8f"}))
        self.assertIn("arm", p.palette)
        self.assertIn("stripe", p.palette)
        p = plan_for(StickerSpec(palette={"orange": "#151515"}))
        self.assertIn("dark", p.palette)            # features kept readable on black fur

    def test_tints(self):
        p = plan_for(StickerSpec(accessories=["scarf"], tints={"scarf": "#ff0000"}))
        self.assertEqual([round(v, 3) for v in p.tints["scarf"]], [1.0, 0.0, 0.0])


class Spec(unittest.TestCase):
    def test_v3_specs_still_load(self):
        old = {"base": "mochi", "palette": {}, "face": "angry", "arm_L": None, "arm_R": None, "stance": "stand", "tail": None,
               "look": [0.0, 0.0], "props": [], "effects": ["anger"], "accessories": ["sunglasses"], "motion": "no", "intensity": 1.0,
               "caption": {"text": "no.", "style": "outline", "pos": "bottom"}, "seconds": 2.0}
        s = StickerSpec.from_dict(old)
        self.assertEqual(s.tempo, 1.0)
        self.assertEqual(StickerSpec.from_dict(s.to_dict()), s)

    def test_bad_values_are_refused(self):
        for bad in (dict(palette={"orange": "red"}), dict(palette={"orange": "#gggggg"}), dict(palette={"nope": "#112233"}),
                    dict(look=[1]), dict(look=[9, 0]), dict(tints={"scarf": "blue"}), dict(tints={"sword": "#ffffff"}),
                    dict(sides={"mug": "X"}), dict(tempo=5), dict(seconds=float("nan")), dict(props="mug"), dict(face="smirk"),
                    dict(caption={"text": "x" * 81}), dict(caption={"text": "hi", "pos": "middle"})):
            with self.subTest(spec=bad):
                with self.assertRaises((ValueError, TypeError)):
                    StickerSpec.from_dict(bad)

    def test_repeats_and_short_colours_are_cleaned(self):
        s = StickerSpec(effects=["hearts", "hearts"], palette={"orange": "#f0a"}).normalized()
        self.assertEqual(s.effects, ["hearts"])
        self.assertEqual(s.palette, {"orange": "#ff00aa"})
        compose(StickerSpec(effects=["hearts", "hearts"]))      # v3 crashed: duplicate layer names


class Pictures(unittest.TestCase):
    def test_exported_alpha_is_straight(self):
        doc = document("t", [Layer("a", [gr("g", [el((256, 256), (300, 300)), fl([1.0, 1.0, 1.0], 50)])])], op=10)
        r, g, b, a = frame(doc, 0).getpixel((256, 256))
        self.assertEqual((r, g, b), (255, 255, 255))
        self.assertAlmostEqual(a, 127, delta=2)

    def test_fading_effects_do_not_dim_the_mascot(self):
        doc, _ = compose(StickerSpec(effects=["confetti", "hearts"], motion="idle"))
        alphas = [np.asarray(im)[372, 256, 3] for im in frames(doc, size=512, step=6)]      # the belly
        self.assertEqual(min(alphas), 255)

    def test_frame_zero_is_the_best_frame(self):
        # the z's are at their fullest in the still (v3 showed none of them in the PNG)
        doc, info = compose(StickerSpec(face="sleep", stance="sit", motion="sleep", effects=["zzz"]))
        self.assertEqual(info["still"], 0)
        names = [L["nm"] for L in doc["layers"] if L["nm"].startswith("z ")]
        alone = dict(doc, layers=[L for L in doc["layers"] if L["nm"] in names or L["nm"] == "stage"])
        self.assertGreater(int((np.asarray(frame(alone, 0, size=256))[..., 3] > 0).sum()), 150)


class Sweep(unittest.TestCase):
    """Every item of the library: builds, loops without a seam, stays inside the canvas, fits Telegram."""

    def run_kind(self, kind):
        bases = None if FULL else ["biscuit"]
        for label, d in qa.cases(kind, bases):
            with self.subTest(item=label):
                problems, _ = qa.check(StickerSpec.from_dict(d))
                self.assertEqual(problems, [])

    def test_motions(self):
        self.run_kind("motions")

    def test_props(self):
        self.run_kind("props")

    def test_effects(self):
        self.run_kind("effects")

    def test_wear(self):
        self.run_kind("wear")

    def test_faces(self):
        if FULL:
            self.run_kind("faces")
        else:
            for name in REG.faces:
                with self.subTest(face=name):
                    compose(StickerSpec(face=name), frame=False)


if __name__ == "__main__":
    unittest.main()
