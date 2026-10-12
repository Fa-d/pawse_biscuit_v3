"""Word forms: 'clapping', 'waved', 'cries', 'happier', 'hugs' find the lexicon's 'clap', 'wave', 'cry', 'happy', 'hug'.

Only used for a word the lexicon does not list itself.  The spelling rules of English decide which base a form can
come from, so 'caring' finds 'care' and never 'car', 'hoping' finds 'hope' and 'hopping' finds 'hop'.
"""
from __future__ import annotations

import re

VOWELS = set("aeiou")
# forms that look like an inflection of a lexicon word but are a different word
FALSE_FRIENDS = {
    "sweater", "power", "tower", "corner", "shower", "butter", "better", "letter", "matter", "number", "paper", "water", "later",
    "dinner", "summer", "winter", "after", "over", "under", "never", "ever", "every", "flower", "flowers", "bowling", "bowler",
    "ringer", "string", "spring", "thing", "things", "nothing", "something", "everything", "king", "wing", "wings", "ceiling",
    "morning", "evening", "pudding", "wedding", "building", "being", "ring", "bring", "sing", "during", "boring", "bored", "news",
    "lens", "bus", "gas", "yes", "this", "his", "has", "was", "is", "us", "plus", "series", "species", "always", "sometimes",
    "lately", "only", "early", "family", "belly", "jelly", "silly", "lovely", "ugly", "holly", "bully", "fly", "reply", "supply",
    "happy", "sorry", "worry", "hurry", "jury", "bury", "angry", "hungry", "ready", "steady", "candy", "dandy", "handy", "windy",
    "corny", "horny", "sunny", "funny", "bunny", "puppy", "kitty", "party", "pretty", "ditty", "petty", "witty", "berry", "cherry",
    "ice", "nice", "rice", "dice", "mice", "price", "spice", "slice", "twice", "police", "office", "notice", "juice", "voice",
    "tired", "scared", "excited", "red", "bed", "wed", "fed", "led", "shed", "sled", "need", "speed", "seed", "feed", "weed",
    "hundred", "sacred", "kindred", "naked", "wicked", "rugged", "jagged", "crooked", "beloved", "learned", "aged", "dogged",
    "hater", "later", "eater", "cater", "crater", "skater",
}


def _cvc(stem):
    """Ends consonant-vowel-consonant (not w, x or y) in a one-syllable stem: 'hop', 'clap', 'car'."""
    if len(stem) < 3:
        return False
    a, b, c = stem[-3], stem[-2], stem[-1]
    groups = len(re.findall(r"[aeiouy]+", stem))
    return a not in VOWELS and b in VOWELS and c not in VOWELS and c not in "wxy" and groups == 1


def candidates(word):
    """Possible base words for an inflected form, most likely first."""
    w = word
    out = []
    if len(w) < 4 or w in FALSE_FRIENDS:
        return out

    def add(x):
        if len(x) >= 2 and x not in out:
            out.append(x)

    if w.endswith("ies") and len(w) > 4:                      # cries -> cry
        add(w[:-3] + "y")
    if w.endswith("ied") and len(w) > 4:                      # cried -> cry
        add(w[:-3] + "y")
    if w.endswith("ing") and len(w) > 5:
        stem = w[:-3]
        if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] not in "ls":
            add(stem[:-1])                                     # hopping -> hop, clapping -> clap
        elif stem.endswith("y") and len(stem) > 2 and stem[-2] not in VOWELS and w[:-4] + "ie" != stem:
            add(stem)                                          # crying -> cry
            add(stem[:-1] + "ie")                              # lying -> lie
        elif _cvc(stem):
            add(stem + "e")                                    # caring -> care (a CVC stem would have doubled: car -> carring)
        else:
            add(stem)                                          # walking -> walk, eating -> eat
            add(stem + "e")                                    # dancing -> dance, waving -> wave
        if stem.endswith("ll"):
            add(stem)                                          # falling -> fall
    if w.endswith("ed") and len(w) > 4:
        stem = w[:-2]
        if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] not in "ls":
            add(stem[:-1])                                     # hopped -> hop
        if not _cvc(stem):
            add(stem)                                          # jumped -> jump
        add(w[:-1])                                            # waved -> wave
    if w.endswith("es") and len(w) > 4 and w[-3] in "sxzh":
        add(w[:-2])                                            # kisses -> kiss, boxes -> box, wishes -> wish
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        add(w[:-1])                                            # hugs -> hug, waves -> wave
    if w.endswith("er") and len(w) > 4:                        # happier -> happy, sadder -> sad, dancer -> dance
        stem = w[:-2]
        if stem.endswith("i"):
            add(stem[:-1] + "y")
        elif len(stem) >= 2 and stem[-1] == stem[-2]:
            add(stem[:-1])
        else:
            add(stem)
            add(stem + "e")
    if w.endswith("est") and len(w) > 5:
        stem = w[:-3]
        if stem.endswith("i"):
            add(stem[:-1] + "y")
        elif len(stem) >= 2 and stem[-1] == stem[-2]:
            add(stem[:-1])
        else:
            add(stem)
            add(stem + "e")
    if w.endswith("ily") and len(w) > 5:                       # happily -> happy
        add(w[:-3] + "y")
    elif w.endswith("ly") and len(w) > 4:                      # sadly -> sad, sleepily handled above
        add(w[:-2])
    if w.endswith("iness"):                                    # happiness -> happy
        add(w[:-5] + "y")
    elif w.endswith("ness") and len(w) > 6:                    # sadness -> sad
        add(w[:-4])
    if w.endswith("ful") and len(w) > 5:                       # cheerful -> cheer
        add(w[:-3])
    if w.endswith("y") and len(w) > 4 and w[-2] not in VOWELS:  # sleepy is listed; rainy -> rain, snowy -> snow
        stem = w[:-1]
        add(stem[:-1] if len(stem) >= 2 and stem[-1] == stem[-2] else stem)
    return out


def base_of(word, known):
    """The lexicon word `word` is a form of, or None."""
    for c in candidates(word):
        if c in known:
            return c
    return None
