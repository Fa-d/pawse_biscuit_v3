"""Studio tests.  Run from rig/:   python3 -m unittest studio.tests.test_studio -v"""
from __future__ import annotations

import os
import tempfile
import unittest

import numpy as np

from studio.caption import caption_layers
from studio.compose import compose, resolve
from studio.export import TGS_MAX, frame, save, tgs_bytes
from studio.motions import MOTIONS
from studio.parse.parser import Parser
from studio.spec import Caption, StickerSpec

os.environ.setdefault("STUDIO_CACHE", tempfile.mkdtemp())


class Vocabulary(unittest.TestCase):
    def test_yaml_names_exist_in_the_rig(self):
        self.assertEqual(Parser().problems(), [])

    def test_spec_round_trip(self):
        s = StickerSpec(face="joy", props=["mug"], caption=Caption("hi", style="bubble"), palette={"orange": "#123456"})
        self.assertEqual(StickerSpec.from_dict(s.to_dict()), s)

    def test_unknown_names_are_rejected(self):
        for bad in (dict(face="smirk"), dict(motion="fly"), dict(props=["sword"]), dict(accessories=["cape"]), dict(base="dragon"), dict(seconds=5)):
            with self.assertRaises(ValueError):
                StickerSpec(**bad).validate()


class Rules(unittest.TestCase):
    def test_prop_takes_the_paw_and_the_wave_moves_over(self):
        plan, notes = resolve(StickerSpec(motion="wave", props=["phone"]))
        self.assertEqual(plan["arms"]["R"], "hold")
        self.assertEqual(plan["hands"], ["L"])

    def test_sitting_mascot_does_not_jump(self):
        plan, _ = resolve(StickerSpec(motion="jump", stance="sit"))
        self.assertEqual(plan["motion"], "sway")
        self.assertIn(plan["tail"], ("ground", "ground_up", "wrap"))

    def test_two_props_and_a_cheer(self):
        plan, notes = resolve(StickerSpec(motion="cheer", props=["mug", "phone"]))
        self.assertEqual(plan["motion"], "bounce")
        self.assertEqual(sorted(plan["arms"].values()), ["hold", "hold"])

    def test_gift_needs_both_paws(self):
        plan, notes = resolve(StickerSpec(props=["mug", "gift"]))
        self.assertEqual([n for n, _ in plan["props"]], ["mug"])
        self.assertTrue(any("gift" in n for n in notes))


class Output(unittest.TestCase):
    def test_every_motion_loops_without_a_seam(self):
        for motion, (_, _, sit_ok) in MOTIONS.items():
            for stance in ("stand", "sit") if sit_ok else ("stand",):
                with self.subTest(motion=motion, stance=stance):
                    doc, _ = compose(StickerSpec(motion=motion, stance=stance))
                    a = np.asarray(frame(doc, 0, size=256)).astype(int)
                    b = np.asarray(frame(doc, doc["op"], size=256)).astype(int)
                    self.assertLess(np.abs(a - b).mean(), 0.05)

    def test_every_template_fits_telegram(self):
        p = Parser()
        for name, t in p.tpl.items():
            with self.subTest(template=name):
                r = p.parse(t["words"][0])
                self.assertEqual(r.template, name)
                doc, _ = compose(r.spec)
                self.assertEqual((doc["w"], doc["h"], doc["fr"]), (512, 512, 60))
                self.assertLessEqual((doc["op"] - doc["ip"]) / doc["fr"], 3.0)
                self.assertLess(len(tgs_bytes(doc)), TGS_MAX)

    def test_every_accessory_on_every_mascot(self):
        from studio.spec import ACCESSORIES, BASES
        for base in BASES:
            for w in ACCESSORIES:
                with self.subTest(base=base, accessory=w):
                    doc, info = compose(StickerSpec(base=base, accessories=[w], motion="bounce"))
                    if any("has its own" in n for n in info["notes"]):
                        continue                    # a costume of what it already has (bunny ears on the bunny)
                    self.assertTrue(any(L["nm"] == f"wear {w.replace('_', ' ')}" for L in doc["layers"]))

    def test_clashing_accessories(self):
        plan, notes = resolve(StickerSpec(accessories=["glasses", "sunglasses", "crown", "party_hat"]))
        self.assertEqual(plan["wear"], ["glasses", "crown"])
        self.assertEqual(len(notes), 2)

    def test_worn_things_stand_out_from_the_fur(self):
        from studio.colour import MIN_DELTA, delta
        from mascot.props import C
        p = Parser()
        for base in ("biscuit", "mochi", "bruno"):
            for colour in p.lex["colours"]:
                with self.subTest(base=base, colour=colour):
                    _, char, info = __import__("studio.compose", fromlist=["build_clip"]).build_clip(
                        StickerSpec(base=base, palette={"orange": p._hex(colour)}, accessories=["bow"]))
                    for item, name in info["tint"].items():
                        if delta(C[name], char.pal["orange"]) < MIN_DELTA:
                            # allowed only when none of the item's colours would do
                            from studio.colour import PREFS
                            self.assertTrue(all(delta(C[n], char.pal["orange"]) < MIN_DELTA for n in PREFS[item]), item)

    def test_new_faces_on_every_mascot(self):
        from studio.spec import BASES
        for base in BASES:
            for face in ("angry", "wink"):
                with self.subTest(base=base, face=face):
                    compose(StickerSpec(base=base, face=face, effects=["anger"]))

    def test_caption_stays_on_the_canvas(self):
        for text in ("OK", "Happy birthday!", "This is a rather long caption for a sticker"):
            for pos in ("top", "bottom"):
                _, (y0, y1) = caption_layers(text, pos=pos)
                self.assertGreaterEqual(y0, 0)
                self.assertLessEqual(y1, 512)

    def test_files_are_written(self):
        with tempfile.TemporaryDirectory() as d:
            doc, info = compose(StickerSpec(motion="bounce", caption=Caption("Hi")))
            res = save(doc, d, "t", formats=("png", "webp", "tgs", "json"), still=info["still"])
            for fmt, (path, size, warn) in res.items():
                self.assertTrue(os.path.getsize(path) > 0, fmt)
                self.assertIsNone(warn, fmt)


if __name__ == "__main__":
    unittest.main()
