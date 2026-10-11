"""What the editor's chips say.  Internal names stay in the spec; people see these words."""
from __future__ import annotations

from studio.parse.parser import Parser
from studio.spec import ACCESSORIES, BASES, EFFECTS, MOTIONS, PROPS, STANCES, VOCAB

BASE = {"biscuit": "Fox", "mochi": "Cat", "bruno": "Bear"}
FACE = {"neutral": "Neutral", "smiley": "Smiley", "joy": "Joyful", "worried": "Worried", "curious": "Curious",
        "sleep": "Sleepy", "calm": "Calm", "surprised": "Surprised", "focused": "Focused", "angry": "Angry", "wink": "Wink"}
MOTION = {"idle": "Stand still", "bounce": "Bounce", "jump": "Jump", "cheer": "Cheer", "wave": "Wave", "dance": "Dance",
          "walk": "Walk", "nod": "Nod yes", "no": "Shake no", "shiver": "Shiver", "sway": "Sway", "sleep": "Doze",
          "think": "Think", "hide": "Hide eyes"}
STANCE = {"stand": "Standing", "wide": "Feet apart", "sit": "Sitting", "lotus": "Cross-legged"}
PROP = {"phone": "Phone", "bell": "Bell", "clipboard": "Clipboard", "badge": "Medal", "cloud": "Cloud balloon",
        "gift": "Gift box", "mug": "Mug", "heart": "Heart"}
EFFECT = {"sparkles": "Sparkles", "confetti": "Confetti", "zzz": "Zzz", "thought": "Thought dots", "tear": "Tear",
          "sweat": "Sweat drop", "hearts": "Floating hearts", "notes": "Music notes", "aura": "Glow ring", "orbs": "Orbs",
          "rain": "Rain cloud", "anger": "Anger mark"}
WEAR = {"party_hat": "Party hat", "crown": "Crown", "glasses": "Glasses", "sunglasses": "Sunglasses", "bow": "Bow",
        "flower": "Flower", "headphones": "Headphones", "scarf": "Scarf", "star_clip": "Star clip"}

# sanity: every name the rig knows has a label
for _names, _labels in ((BASES, BASE), (VOCAB["face"], FACE), (MOTIONS, MOTION), (STANCES, STANCE), (PROPS, PROP),
                        (EFFECTS, EFFECT), (ACCESSORIES, WEAR)):
    assert set(_names) == set(_labels), set(_names) ^ set(_labels)


def vocab():
    p = Parser()
    pick = lambda labels: [{"id": k, "label": v} for k, v in labels.items()]
    colours = [{"id": "", "label": "Original", "hex": None}] + [
        {"id": name, "label": name.capitalize(), "hex": pal["orange"], "palette": pal}
        for name, pal in p.lex["colours"].items() if name not in ("violet", "gray")]
    ideas = [{"prompt": t["words"][0], "caption": t.get("caption")} for t in p.tpl.values()]
    return dict(base=pick(BASE), face=pick(FACE), motion=pick(MOTION), stance=pick(STANCE), props=pick(PROP),
                effects=pick(EFFECT), accessories=pick(WEAR), colours=colours, ideas=ideas,
                caption_style=[{"id": "outline", "label": "Outline"}, {"id": "bubble", "label": "Bubble"}],
                caption_pos=[{"id": "bottom", "label": "Bottom"}, {"id": "top", "label": "Top"}])
