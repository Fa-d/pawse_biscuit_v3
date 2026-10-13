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


if __name__ == "__main__":
    unittest.main()
