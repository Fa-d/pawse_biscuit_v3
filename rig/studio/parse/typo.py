"""Safe typo correction.

v3 matched every unknown word against the lexicon with a loose similarity score, which turned real words into wrong
ones: 'eating' -> 'sweating' (a scared fox), 'clapping' -> 'napping', 'orange' -> 'rage', 'what' -> 'hat'.  Now:

  * a real English word is never "corrected" (a list of about 64,000 common words, from SCOWL, guards it),
  * the fix must be within a small edit distance for the word's length (one edit up to 5 letters, two from 6, with
    letters swapped counting as one edit), and keep the first letter unless the word is long,
  * when two different lexicon words are equally close, nothing is guessed.
"""
from __future__ import annotations

import gzip
import os
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
WORDS_FILE = os.path.join(HERE, "data", "english-words.txt.gz")


@lru_cache(maxsize=1)
def english():
    """The guard list: lowercase common English words (empty if the file is missing)."""
    try:
        with gzip.open(WORDS_FILE, "rt", encoding="utf-8") as f:
            return frozenset(w.strip() for w in f if w.strip())
    except OSError:
        return frozenset()


def is_word(w):
    return w in english()


def distance(a, b, limit=3):
    """Damerau-Levenshtein distance (adjacent swaps count as one edit), giving up above `limit`."""
    la, lb = len(a), len(b)
    if abs(la - lb) > limit:
        return limit + 1
    prev2 = None
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        best = cur[0]
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            v = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if prev2 is not None and i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                v = min(v, prev2[j - 2] + 1)
            cur[j] = v
            best = min(best, v)
        if best > limit:
            return limit + 1
        prev2, prev = prev, cur
    return prev[lb]


def allowed(word):
    """Edits a word of this length may need to be fixed."""
    n = len(word)
    if n <= 3:
        return 0
    if n <= 5:
        return 1
    return 2


class Fixer:
    def __init__(self, vocab):
        """vocab: the single words the lexicon knows."""
        self.by_len = {}
        for w in vocab:
            if len(w) >= 3 and w.isalpha():
                self.by_len.setdefault(len(w), []).append(w)

    def fix(self, word, entry_of=lambda w: w):
        """The lexicon word `word` is a typo of, or None.  entry_of maps a word to the lexicon entry it belongs to
        (two candidates for the same entry are not a real ambiguity)."""
        if not word.isalpha() or is_word(word):
            return None
        k = allowed(word)
        if not k:
            return None
        best_d, cands = k + 1, []
        for n in range(len(word) - k, len(word) + k + 1):
            for cand in self.by_len.get(n, ()):
                if cand[0] != word[0] and (len(word) < 7 or cand[1:3] != word[1:3]):
                    continue                                   # people rarely mistype the first letter
                d = distance(word, cand, k)
                if cand[0] != word[0] and d > 1:
                    continue                                   # a different first letter and more: another word
                if d < best_d:
                    best_d, cands = d, [cand]
                elif d == best_d and d <= k:
                    cands.append(cand)
        if not cands or best_d > k:
            return None
        # equally close: the likelier slip wins (a doubled letter typed once, the last letter kept), and only if it
        # leaves one meaning ('slepy' is 'sleepy', not 'slept')
        likely = lambda c: (_undoubled(word, c), c[-1] == word[-1])
        top = max(likely(c) for c in cands)
        cands = [c for c in cands if likely(c) == top]
        if len({entry_of(c) for c in cands}) > 1:
            return None
        return cands[0]


def _undoubled(typed, cand):
    """typed is cand with one doubled letter typed once ('slepy' / 'sleepy'), or the other way round."""
    a, b = (typed, cand) if len(typed) < len(cand) else (cand, typed)
    if len(b) != len(a) + 1:
        return False
    for i in range(1, len(b)):
        if b[i] == b[i - 1] and b[:i] + b[i + 1:] == a:
            return True
    return False
