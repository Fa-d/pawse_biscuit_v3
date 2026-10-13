"""L17: one-mascot output stays byte-identical to v4.  Run from rig/:   python3 -m unittest studio.tests.test_snapshots

Builds the snapshot corpus (about 380 items, roughly a minute on two cores) and compares it with the hashes recorded
from the v4 code in studio/tests/snapshots.json.  `python -m studio.snapshots --check` lists every difference.
"""
from __future__ import annotations

import contextlib
import io
import unittest

from studio import snapshots


class ByteIdentical(unittest.TestCase):
    def test_corpus_matches_v4(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = snapshots.main(["--check"])
        self.assertEqual(code, 0, "one-mascot output changed:\n" + out.getvalue())


if __name__ == "__main__":
    unittest.main()
