"""v5 tests: the scene layer and what leads up to it.  Run from rig/:   python3 -m unittest studio.tests.test_v5 -v"""
from __future__ import annotations

import os
import tempfile
import unittest

from studio.parse.parser import Parser

os.environ.setdefault("STUDIO_CACHE", tempfile.mkdtemp())


class OneMascotForNow(unittest.TestCase):
    """P34: a second mascot is left out with a note instead of vanishing silently."""

    @classmethod
    def setUpClass(cls):
        cls.p = Parser()

    def read(self, text):
        return self.p.parse(text)

    def test_second_animal_is_noted_and_struck(self):
        r = self.read("a cat hugging a dog")
        self.assertEqual(r.spec.base, "pip")
        self.assertEqual([m.phrase for m in r.matches if m.dropped], ["cat"])
        self.assertEqual(r.notes, ["one mascot fits in a sticker for now, so it's the dog; the cat is left out"])
        self.assertLess(r.score, 1.0)

    def test_three_animals_name_both_left_out(self):
        r = self.read("a cat, a dog and a mouse")
        self.assertEqual(r.spec.base, "nib")
        self.assertIn("the cat and dog are left out", r.notes[0])

    def test_two_of_one_mascot(self):
        for text, animal in (("two foxes high five", "fox"), ("a pair of cats dancing", "cat"), ("foxes dancing", "fox"),
                             ("kitties playing", "kitty")):
            with self.subTest(text=text):
                self.assertEqual(self.read(text).notes, [f"one mascot fits in a sticker for now, so there's one {animal}"])

    def test_one_mascot_has_no_note(self):
        for text in ("a polar bear waving", "golden retriever with a ball", "a cat meows", "sleepy kitty with coffee",
                     "happy fox", "omg no way"):
            with self.subTest(text=text):
                r = self.read(text)
                self.assertEqual(r.notes, [])
                self.assertFalse(any(m.dropped for m in r.matches))

    def test_slots_do_not_change(self):
        """The note changes nothing the sticker is made from (the golden prompts check the rest)."""
        r = self.read("bear and panda celebrating together")
        self.assertEqual((r.spec.base, r.spec.motion), ("bao", "cheer"))



# ---------------------------------------------------------------- phase 1: the scene layer
import json  # noqa: E402
import math  # noqa: E402

from mascot.build import characters, registry  # noqa: E402
from mascot.clip import Clip  # noqa: E402
from mascot.clips import moves as M  # noqa: E402
from mascot.scene import Scene, Stage  # noqa: E402
from studio import scene_compose  # noqa: E402
from studio.compose import _character, build_clip, compose  # noqa: E402
from studio.export import TGS_MAX, tgs_bytes  # noqa: E402
from studio.scene_compose import compose_scene, duo  # noqa: E402
from studio.scene_spec import ActorSpec, SceneSpec  # noqa: E402
from studio.spec import Caption, StickerSpec  # noqa: E402


def app_clip(mascot, key):
    """(character, clip) of one of the app's clips, made the way mascot.build makes it."""
    spec = registry()[key]
    ch = characters()[mascot]()
    c = Clip(f"{ch.name}_{key}", spec["frames"], loop=spec.get("loop", True), scale=spec.get("scale", 1.0), char=ch)
    c.settle = bool(spec.get("settle", False))
    c.calm = int(spec.get("calm", 0))
    spec["fn"](c)
    return ch, c


def dumps(doc):
    return json.dumps(doc, separators=(",", ":"))


class SceneOfOne(unittest.TestCase):
    """A scene of one mascot on a plain stage writes the file Character.build() writes."""

    def test_app_clips(self):
        for mascot, key in (("biscuit", "idle"), ("biscuit", "gift"), ("mochi", "wave"), ("leo", "sleepy"), ("fern", "hop_in")):
            with self.subTest(clip=f"{mascot}_{key}"):
                ch, c = app_clip(mascot, key)
                want = dumps(ch.build(c))
                ch2, c2 = app_clip(mascot, key)
                sc = Scene(c2.name, frames=c2.frames)
                sc.add("a", ch2, c2)
                self.assertEqual(dumps(sc.build()), want)

    def test_sticker_clip_with_props_and_roll(self):
        spec = StickerSpec(base="clover", motion="eat", props=["donut"], accessories=["party_hat"], effects=["sparkles"])
        c, ch, info = build_clip(spec)
        c.roll, c.opts["fade_safe"] = info["still"], True
        want = dumps(ch.build(c))
        c2, ch2, _ = build_clip(spec)
        c2.opts["fade_safe"] = True
        sc = Scene(c2.name, frames=c2.frames, roll=info["still"])
        sc.add("a", ch2, c2)
        self.assertEqual(dumps(sc.build()), want)


class SceneSpecs(unittest.TestCase):
    def test_v4_specs_load_as_one_mascot(self):
        s = StickerSpec(base="mochi", face="joy", props=["mug"], caption=Caption("hi"), palette={"orange": "#8a6fdf"}, tempo=1.4)
        scene = SceneSpec.from_dict(s.to_dict())
        self.assertTrue(scene.solo)
        self.assertEqual(scene.to_dict(), s.to_dict())
        self.assertEqual(scene.key(), s.key())

    def test_two_mascots_round_trip(self):
        scene = SceneSpec(actors=[ActorSpec(base="mochi", props=["mug"]), ActorSpec(base="pip", motion="dance")],
                          effects=["confetti"], caption=Caption("besties", style="bubble"), seconds=2.5)
        back = SceneSpec.from_dict(json.loads(scene.to_json()))
        self.assertEqual(back, scene.normalized())
        self.assertNotEqual(scene.key(), scene.actors[0].sticker().key())

    def test_what_a_scene_refuses(self):
        for bad in (dict(actors=[{}, {}, {}]), dict(actors=[{"base": "dragon"}]), dict(actors=[{"caption": "hi"}]),
                    dict(actors=[{}], duet="tango"), dict(actors=[{}], effects=["glitter"]), dict(actors=[{}], seconds=9),
                    dict(actors=[], seconds=2), dict(actors=[{}], scenery="beach")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                SceneSpec.from_dict(bad)

    def test_one_mascot_composes_as_v4(self):
        s = StickerSpec(base="leo", motion="dance", props=["mug"], caption=Caption("hey"))
        self.assertEqual(dumps(compose_scene(SceneSpec.from_sticker(s))[0]), dumps(compose(s)[0]))
        self.assertEqual(dumps(compose_scene(s.to_dict())[0]), dumps(compose(s)[0]))


L_PAT, PATS, T0, T1 = 120, (36, 54, 72), 26, 88


def comfort_scene():
    """The phase 1 gate's duet: a cat on tiptoe pats a sad, sitting bunny on the head, and the bunny calms down."""
    A, B = _character("mochi", {}), _character("clover", {})
    cb = Clip("bunny", L_PAT, loop=True, char=B)
    cb.stance((0, "sit"))
    cb.face(0, "sad", dur=0)
    cb.face(60, "relieved", dur=14)
    cb.face(98, "relieved", dur=0)
    cb.face(118, "sad", dur=16)
    cb.face(L_PAT, "sad", dur=0)
    cb.tailpose((0, "ground"))
    cb.k("head.rot", (0, 0.0), (T0, -7.0, "io"), (T1, -7.0, "hold"), (L_PAT, 0.0, "io"))
    for t in PATS:
        cb.pulse("head.y", t - 1, 5.0, up=3, down=11)
    cb.arm("LR", (0, "lap"))
    M.breathe(cb, period=60, amp=0.02)
    ca = Clip("cat", L_PAT, loop=True, char=A)
    ca.stance((0, "stand"), (T0 - 6, "tiptoe", "io"), (T1 + 4, "tiptoe", "hold"), (L_PAT, "stand", "io"))
    ca.face(0, "smiley", dur=0)
    ca.face(T0, "calm", dur=10)
    ca.face(T1 + 10, "smiley", dur=10)
    ca.face(L_PAT, "smiley", dur=0)
    ca.k("body.rot", (0, 0.0), (T0, 7.0, "io"), (T1, 7.0, "hold"), (L_PAT, 0.0, "io"))
    ca.k("hip.x", (0, 0.0), (T0, 6.0, "io"), (T1, 6.0, "hold"), (L_PAT, 0.0, "io"))
    ca.arm("L", (0, "relax"))
    ca.arm("R", (0, "rest"), (T0, "hold", "io"), (T1, "hold", "hold"), (L_PAT, "rest", "io"))
    ca.set("arm.R.front", 1.0)
    ca.tailpose((0, "rest"))
    sc = Scene("comfort", frames=L_PAT)
    sc.add("a", A, ca, Stage(x=-58.0, y=-4.0, scale=0.74))
    sc.add("b", B, cb, Stage(x=64.0, y=10.0, scale=0.74))

    def lift(f):
        d = min(abs(f - t) for t in PATS)
        return (0.0, -9.0 * min(1.0, d / 9.0) ** 1.4)
    sc.pin("a", "R", T0, T1, ("b", "head_side", "L"), hand=118.0, bend=-1.0, blend=8, offset=lift)
    sc.lift("a", "right arm", over="b", t0=T0 - 8, t1=T1 + 8)
    return sc


class SceneBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sc = comfort_scene()
        cls.doc = cls.sc.build()
        cls.names = [L["nm"] for L in cls.doc["layers"]]

    def test_names_and_stages(self):
        for nm in self.names:
            self.assertTrue(nm.startswith(("a/", "b/")), nm)
        self.assertIn("a/stage", self.names)
        self.assertIn("b/stage", self.names)
        ind = {L["ind"]: L for L in self.doc["layers"]}
        for L in self.doc["layers"]:
            if "parent" in L:
                self.assertEqual(ind[L["parent"]]["nm"].split("/")[0], L["nm"].split("/")[0], "a parent belongs to the same mascot")

    def test_depth_order(self):
        pos = {nm: q for q, nm in enumerate(self.names)}
        self.assertLess(pos["a/right arm lifted"], pos["b/head"], "the lifted paw is over the bunny's head")
        self.assertLess(pos["b/body"], pos["a/body"], "the bunny, nearer the viewer, is in front of the cat")
        self.assertGreater(pos["a/shadow"], pos["a/body"])
        self.assertEqual(sorted(self.names[-4:-2]), ["a/shadow", "b/shadow"], "the shadows come last, then the stages")

    def test_timed_lift_swaps_by_hold_keys(self):
        ly = {L["nm"]: L for L in self.doc["layers"]}
        up, down = ly["a/right arm lifted"]["ks"]["o"], ly["a/right arm"]["ks"]["o"]
        self.assertEqual([(k["t"], k["s"][0]) for k in up["k"]], [(0, 0), (T0 - 8, 100), (T1 + 9, 0)])
        self.assertTrue(all(k.get("h") == 1 for k in up["k"] + down["k"]))

    def test_paw_holds_the_contact(self):
        tg = self.sc.target(self.sc.pins[0])
        errs = [math.dist(self.sc.point("a", "wrist", f, "R"), tg(f)) for f in range(T0 + 8, T1 - 7)]
        self.assertLessEqual(max(errs), 4.0)
        self.assertLessEqual(self.sc.reach(self.sc.pins[0]), 1.7)

    def test_fits_telegram(self):
        self.assertLess(len(tgs_bytes(self.doc)), TGS_MAX)

    def test_points_need_a_prepared_scene(self):
        fresh = comfort_scene()
        with self.assertRaises(RuntimeError):
            fresh.point("b", "crown", 0)
        with self.assertRaises(ValueError):
            fresh.prepare().point("b", "paw", 0)          # a sided part needs its side

    def test_stage_coordinates_invert(self):
        sc = Scene("x", frames=2)
        ch = _character("pip", {})
        sc.add("m", ch, Clip("x", 2, char=ch), Stage(x=40.0, y=-12.0, scale=0.6, mirror=True))
        for p in ((256.0, 470.0), (100.0, 200.0), (400.0, 90.0)):
            back = sc.to_local("m", sc.to_scene("m", p))
            self.assertAlmostEqual(back[0], p[0])
            self.assertAlmostEqual(back[1], p[1])


class SceneCompose(unittest.TestCase):
    def test_a_duo_builds_with_notes(self):
        doc, info = compose_scene(duo("mochi", "pip"))
        self.assertLess(len(tgs_bytes(doc)), TGS_MAX)
        self.assertIn("the cat stands on the left, the dog on the right", info["notes"])
        self.assertEqual([a["base"] for a in info["actors"]], ["mochi", "pip"])

    def test_two_of_the_same_mascot_are_told_apart(self):
        plan = scene_compose.resolve_scene(duo("biscuit", "biscuit").normalized())
        self.assertEqual(plan.stickers[0].palette, {})
        self.assertTrue(plan.stickers[1].palette.get("orange"))
        self.assertIn("S06", plan.fired)

    def test_scene_effects_go_to_the_mascot_in_front(self):
        spec = SceneSpec(actors=[ActorSpec(base="bruno"), ActorSpec(base="bao")], effects=["confetti"]).normalized()
        plan = scene_compose.resolve_scene(spec)
        self.assertEqual([s.effects for s in plan.stickers], [[], ["confetti"]])

    def test_over_budget_drops_the_costliest_effect(self):
        spec = SceneSpec(actors=[ActorSpec(base="bruno", effects=["sparkles"]), ActorSpec(base="bao", effects=["confetti"])])
        old = scene_compose.TGS_MAX
        try:
            scene_compose.TGS_MAX = 6 * 1024                 # a small limit (the scene is 8 KB), so the rule has to act
            doc, info = compose_scene(spec)
        finally:
            scene_compose.TGS_MAX = old
        self.assertIn("dropped the confetti to stay within Telegram's 64 KB", info["notes"])
        self.assertNotIn("dropped the sparkles to stay within Telegram's 64 KB", info["notes"], "it stops once the file fits")
        self.assertLessEqual(len(tgs_bytes(doc)), 6 * 1024)


if __name__ == "__main__":
    unittest.main()
