"""Faces, mascots, stances, tail poses and arm poses: their labels, emoji and words for accessibility text.
(The drawings themselves are the rig's: mascot/rig.py FACES and mascot/characters/.)"""
from __future__ import annotations

from mascot.rig import FACES

from ..registry import REG, base, face

# name: (label, emoji, mood word for "A <mood> fox ...", blink)
_FACES = {
    "neutral": ("Neutral", "😐", "calm-looking", True),
    "smiley": ("Smiley", "🙂", "smiling", True),
    "joy": ("Joyful", "😄", "joyful", False),
    "worried": ("Worried", "😟", "worried", True),
    "curious": ("Curious", "🤔", "curious", True),
    "sleep": ("Sleepy", "😴", "sleepy", False),
    "calm": ("Calm", "😌", "calm", False),
    "surprised": ("Surprised", "😮", "surprised", True),
    "focused": ("Focused", "🧐", "focused", True),
    "angry": ("Angry", "😠", "angry", True),
    "wink": ("Wink", "😉", "winking", False),
    "laugh": ("Laughing", "😆", "laughing", False),
    "grin": ("Grin", "😁", "grinning", True),
    "sad": ("Sad", "😢", "sad", True),
    "cry": ("Crying", "😭", "crying", False),
    "pleading": ("Puppy eyes", "🥺", "pleading", True),
    "love": ("Heart eyes", "😍", "love-struck", False),
    "starry": ("Star eyes", "🤩", "star-struck", False),
    "dizzy": ("Dizzy", "😵‍💫", "dizzy", False),
    "dead": ("Knocked out", "😵", "knocked-out", False),
    "shocked": ("Shocked", "😳", "shocked", True),
    "smug": ("Smug", "😏", "smug", False),
    "unamused": ("Unamused", "😒", "unamused", False),
    "pout": ("Pouting", "😤", "pouting", True),
    "nervous": ("Nervous", "😬", "nervous", True),
    "kiss": ("Kiss", "😘", "kissing", False),
    "silly": ("Silly", "😜", "silly", False),
    "yawn": ("Yawning", "🥱", "yawning", False),
    "drowsy": ("Drowsy", "😪", "drowsy", False),
    "determined": ("Determined", "😤", "determined", True),
    "mischief": ("Mischief", "😈", "mischievous", False),
    "sick": ("Sick", "🤢", "queasy", False),
    "confused": ("Confused", "😕", "confused", True),
    "flustered": ("Flustered", "😖", "flustered", False),
    "relieved": ("Relieved", "😌", "relieved", False),
    "proud": ("Proud", "😊", "proud", False),
    "scared": ("Scared", "😨", "scared", True),
    "hungry": ("Hungry", "😋", "hungry", True),
    "cool": ("Cool", "😎", "cool", False),
    "furious": ("Furious", "🤬", "furious", True),
    "excited": ("Excited", "🤩", "excited", True),
}
for _name, (_label, _emoji, _mood, _blink) in _FACES.items():
    face(_name, _label, _emoji, mood=_mood, blink=_blink)
_missing = set(FACES) - set(REG.faces)
if _missing:
    raise RuntimeError(f"faces without a label: {sorted(_missing)}")


def _loader(module, cls):
    def load():
        import importlib
        return getattr(importlib.import_module(f"mascot.characters.{module}"), cls)
    return load


base("biscuit", "Fox", "fox", _loader("biscuit", "Biscuit"), "🦊", snack="cookie")
base("mochi", "Cat", "cat", _loader("mochi", "Mochi"), "🐱", snack="fish")
base("bruno", "Bear", "bear", _loader("bruno", "Bruno"), "🐻", snack="honey")
base("pip", "Dog", "dog", _loader("pip", "Pip"), "🐶", snack="bone")
base("clover", "Bunny", "bunny", _loader("clover", "Clover"), "🐰", snack="carrot")
base("bao", "Panda", "panda", _loader("bao", "Bao"), "🐼", snack="bamboo")
base("tora", "Tiger", "tiger", _loader("tora", "Tora"), "🐯", snack="sushi")
base("kiko", "Koala", "koala", _loader("kiko", "Kiko"), "🐨", snack="cupcake")
base("rocco", "Raccoon", "raccoon", _loader("rocco", "Rocco"), "🦝", snack="pizza")
base("truffle", "Pig", "pig", _loader("truffle", "Truffle"), "🐷", snack="apple")
base("fern", "Frog", "frog", _loader("fern", "Fern"), "🐸", snack="lollipop")
base("pebble", "Penguin", "penguin", _loader("pebble", "Pebble"), "🐧", snack="fish")
base("nib", "Mouse", "mouse", _loader("nib", "Nib"), "🐭", snack="cheese")
base("leo", "Lion", "lion", _loader("leo", "Leo"), "🦁", snack="burger")

REG.stances.update({"stand": "Standing", "wide": "Feet apart", "sit": "Sitting", "lotus": "Cross-legged", "crouch": "Crouching",
                    "tiptoe": "On tiptoe"})
REG.tails.update({"rest": "Resting", "out": "Out", "in": "In", "up": "Up", "low": "Low", "floor": "On the floor", "flick_out": "Flick out",
                  "flick_in": "Flick in", "curl": "Curled", "ground": "On the ground", "ground_up": "Ground, tip up", "wrap": "Wrapped",
                  "alert": "Straight up", "tucked": "Tucked away"})
REG.arm_poses.update({
    "rest": "At its sides", "relax": "Relaxed", "wave_lo": "Waving (low)", "wave_hi": "Waving (high)", "cheer": "Arms up",
    "cheer_hi": "Arms high", "cheer_out": "Arms out and up", "chin": "Paw on chin", "mouth": "Paw at mouth", "cheek": "Paw on cheek",
    "belly": "Paws on tummy", "lap": "Paws in lap", "hip": "Hands on hips", "hold": "Holding", "hold_up": "Holding up",
    "carry": "Carrying", "edge": "On an edge", "ring": "Ringing", "knee": "Paws on knees", "lid": "On a lid", "cover_eyes": "Covering eyes",
    "peek": "Peeking", "stretch": "Stretching", "salute": "Saluting", "facepalm": "Facepalm", "ear": "Paw at ear", "chest": "Paw on heart",
    "cross": "Arms crossed", "hug": "Hugging itself", "wide": "Arms wide open", "shrug": "Shrugging", "flex": "Flexing", "pray": "Paws together",
    "clap": "Clapping", "clap_open": "Paws apart", "point_out": "Pointing out", "point_up": "Pointing up", "point_fwd": "Pointing at you",
    "thumbs_up": "Thumb up", "thumbs_down": "Thumb down", "tray": "Holding a tray", "present": "Carrying in front", "lift": "Lifting up", "fist_pump": "Fist pump",
    "reach": "Reaching", "dab": "Dab", "dab_in": "Dab (bent)", "behind": "Paws behind its back", "fly": "Arms forward",
})
