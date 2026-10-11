"""StickerSpec -> Lottie document.  Pure rules, no AI.

Order of decisions (each one is written to `notes` so the editor can explain the result):
  1. props claim paws first (a phone needs a paw in the `hold` pose), on their preferred side if it is free
  2. the motion gets the paws that are left; a motion that needs a paw and gets none is swapped for `bounce`
  3. motions that need legs are swapped for `sway` when the mascot sits
  4. arm poses named in the spec fill the paws nobody claimed; the rest hang at `rest`
  5. the tail follows the stance (sitting mascots use the sitting tail poses)
  6. with a caption the whole character is shrunk and moved out of the way on a `stage` null layer
"""
from __future__ import annotations

from mascot import props as P
from mascot.clip import FPS, Clip
from mascot.lottie import rgb

from . import extras as X
from .accessories import ACCESSORIES, EXCLUSIVE
from .colour import PREFS, pick
from .caption import caption_layers
from .motions import MOTIONS, WAG, per
from .spec import SIT_TAILS, StickerSpec


def characters():
    from mascot.build import characters as reg
    return reg()


def make_character(spec):
    """Character instance for the spec's base, with its palette overrides applied."""
    base = characters()[spec.base]
    if not spec.palette:
        return base()
    pal = dict(base.pal)
    for k, v in spec.palette.items():
        if k not in pal:
            raise ValueError(f"unknown palette key {k!r}; expected one of {', '.join(sorted(pal))}")
        pal[k] = rgb(v)
    # slots that shared a colour in the design keep sharing it (Mochi's tail tip is its stripe colour, Bruno's its fur)
    for k in base.pal:
        if k in spec.palette:
            continue
        twin = next((o for o in spec.palette if o in base.pal and base.pal[o] == base.pal[k]), None)
        if twin:
            pal[k] = pal[twin]
    return type(f"{base.__name__}Custom", (base,), {"pal": pal})()


# prop -> (preferred paw, pose, may switch sides, factory(L, side, tint))   tint: item -> colour that shows on this fur
# SHOW_AT: first frame where the prop is fully visible (the still image is never taken before it)
SHOW_AT = {"badge": 34, "phone": 40, "clipboard": 0.5, "gift": 90}
PROPS = {
    "phone": ("R", "hold", True, lambda L, s, t: P.phone(s, "hold", t_bars=(4, 12, 20), t_out=L - 16, t_gone=L)),
    "bell": ("R", "ring", True, lambda L, s, t: P.bell(s, "ring", period=per(L, 24), scale=0.9)),
    "clipboard": ("L", "hold", True, lambda L, s, t: P.clipboard(s, "hold", t_draw=(0, int(L * 0.45)), t_out=L - 18, t_gone=L)),
    "badge": ("R", "hold_up", True, lambda L, s, t: P.badge(s, "hold_up", t_pop=6)),
    "cloud": ("R", "carry", True, lambda L, s, t: P.cloud_on_string(s, offset=(46, -238), scale=0.9, period=per(L, 60))),
    "mug": ("R", "hold", True, lambda L, s, t: X.mug(s, "hold", color=t["mug"])),
    "heart": ("R", "hold_up", True, lambda L, s, t: X.heart(s, "hold_up", color=t["heart"], beat=per(L, 60))),
    "gift": ("LR", "lid", False, lambda L, s, t: P.gift(k=0.84)),
}

EFFECTS = {      # name -> factory(L, tint)
    "sparkles": lambda L, t: P.sparkles([(84, 170, 22, "yellow", 0), (430, 120, 26, "teal", int(L * 0.25)), (456, 260, 18, "coral", int(L * 0.5)),
                                      (60, 300, 18, "lilac", int(L * 0.72))]),
    "confetti": lambda L, t: P.confetti(t0=4, origin=(256, 250), t_end=L),
    "zzz": lambda L, t: P.zzz([(134, 44, 20, 0), (158, 8, 26, int(L * 0.2)), (178, -28, 30, int(L * 0.4))], life=int(L * 0.55),
                           fade_in=int(L * 0.15), rel=True),
    "thought": lambda L, t: P.thought_dots([(162, 58, 20, 4), (188, 24, 28, 14), (216, -16, 40, 24)], t_out=L - 16, t_gone=L, rel=True),
    "tear": lambda L, t: P.tear(int(L * 0.2), life=int(L * 0.6)),
    "sweat": lambda L, t: P.sweat_drop(int(L * 0.15), life=int(L * 0.6)),
    "hearts": lambda L, t: X.hearts(t["hearts"]),
    "notes": lambda L, t: X.notes(),
    "aura": lambda L, t: P.aura("teal", period=L, size=336.0),
    "orbs": lambda L, t: P.orbs(3, period=L),
    "rain": lambda L, t: X.rain(),
    "anger": lambda L, t: X.anger(),
}

FIGURE = 440.0          # rough height of a mascot plus headroom for bounces, in canvas px at scale 1

STAND_TAIL = {"ground": "low", "ground_up": "up", "wrap": "rest"}
SIT_TAIL = {"up": "ground_up", "out": "ground_up", "flick_out": "ground_up", "curl": "ground_up"}


def resolve(spec: StickerSpec):
    """Work out who gets which paw, the final motion, tail and stance.  Returns (plan dict, notes list)."""
    notes = []
    free = ["R", "L"]
    claims = {}                                  # paw -> pose
    props = []                                   # (name, side)
    stance = spec.stance
    for name in spec.props:
        pref, pose, flexible, _ = PROPS[name]
        if pref == "LR":
            if len(free) < 2:
                notes.append(f"dropped {name}: it needs both paws")
                continue
            for s in "RL":
                claims[s] = pose
            free = []
            props.append((name, "LR"))
            if stance == "stand":
                stance = "wide"
                notes.append("gift: feet apart on either side of the box")
            continue
        side = pref if pref in free else (free[0] if flexible and free else None)
        if side is None:
            notes.append(f"dropped {name}: no free paw")
            continue
        if side != pref:
            notes.append(f"{name} moved to the {'left' if side == 'L' else 'right'} paw")
        claims[side] = pose
        free.remove(side)
        props.append((name, side))

    motion = spec.motion
    fn, wants, sit_ok = MOTIONS[motion]
    if stance in ("sit", "lotus") and not sit_ok:
        notes.append(f"{motion} needs legs; sitting, so it sways instead")
        motion = "sway"
        fn, wants, sit_ok = MOTIONS[motion]
    if wants and not free:
        if any(n == "gift" for n, _ in props):
            notes.append("the gift is the act: paws on the lid, it pops, then a cheer")
        else:
            notes.append(f"{motion} needs a free paw; both are busy, so it bounces instead")
        motion = "bounce"
        fn, wants, _ = MOTIONS[motion]
    if motion == "wave" and "R" not in free and "L" in free:
        notes.append("waves with the left paw (the right one is holding something)")
    hands = free[:wants]

    arms = {}
    for s, want in (("R", spec.arm_R), ("L", spec.arm_L)):
        if s in claims:
            arms[s] = claims[s]
        elif s in hands:
            arms[s] = None                       # the motion keys this paw itself
        else:
            arms[s] = want or ("knee" if stance == "lotus" else "rest")

    wear = []
    for w in spec.accessories:
        clash = next((x for x in wear for group in EXCLUSIVE if {w, x} <= group), None)
        if clash:
            notes.append(f"dropped {w}: it sits where the {clash} is")
        elif w not in wear:
            wear.append(w)

    tail = spec.tail
    if stance in ("sit", "lotus"):
        if tail not in SIT_TAILS:
            tail = SIT_TAIL.get(tail, "wrap" if stance == "lotus" else "ground")
    else:
        tail = STAND_TAIL.get(tail, tail) if tail else "rest"
    return dict(motion=motion, fn=fn, hands=hands, arms=arms, props=props, stance=stance, tail=tail, wear=wear), notes


def build_clip(spec: StickerSpec, char=None):
    """Spec -> (Clip, character, info).  info has the still frame and the notes."""
    spec.validate()
    char = char or make_character(spec)
    plan, notes = resolve(spec)
    L = int(round(spec.seconds * FPS))
    scale = 0.86 if plan["motion"] in ("jump", "cheer") or "cloud" in spec.props else 1.0
    if plan["stance"] in ("sit", "lotus"):
        scale = 1.06
    c = Clip(f"sticker_{spec.key()}", L, loop=True, scale=scale, char=char)
    c.calm = 0
    c.stance((0, plan["stance"]))
    c.face(0, spec.face, dur=0)
    if spec.look != (0.0, 0.0):
        c.set("look.x", float(spec.look[0]))
        c.set("look.y", float(spec.look[1]))
    for s, pose in plan["arms"].items():
        if pose is not None:
            c.arm(s, (0, pose))
    still = plan["fn"](c, spec.intensity, plan["hands"])
    if any(n == "gift" for n, _ in plan["props"]) and L >= 100:
        # as in clips/core.py gift: the lid pops at 40 (props.gift), the paws fly up and the face lights up
        c.arm("LR", (0, "lid"), (34, "lid"), (38, "lap", "in"), (48, "cheek", "back"), (62, "cheek"), (78, "cheer", "back"),
              (L - 8, "cheer"), (L, "lid", "io"))
        c.face(0, "curious", dur=0, look_x=0.0, look_y=0.85)
        c.face(34, "curious", dur=0, look_x=0.0, look_y=0.85)
        c.face(46, "surprised", dur=6)
        c.face(68, spec.face if spec.face in ("joy", "smiley") else "joy", dur=8)
        c.face(L - 8, spec.face if spec.face in ("joy", "smiley") else "joy", dur=0)
        c.face(L, "curious", dur=8, look_x=0.0, look_y=0.85)
        still = 90
    elif any(n == "gift" for n, _ in plan["props"]):
        c.set("look.y", 0.85)
    c.tailpose((0, plan["tail"]))
    if plan["tail"] == "wrap":
        c.set("tail.front", 1.0)                 # across the lap
    wag = WAG[plan["motion"]] * (0.5 if plan["stance"] in ("sit", "lotus") else 1.0) * spec.intensity
    c.wag(amp=wag, period=per(L, 30 if wag > 8 else 60), lag=0.14)
    if spec.face not in ("sleep", "calm", "joy", "wink") and plan["motion"] not in ("hide", "think"):
        c.blink(int(L * 0.8))
    tint = {item: pick(prefs, char.pal["orange"]) for item, prefs in PREFS.items()}
    for name, side in plan["props"]:
        c.prop(PROPS[name][3](L, side, tint))
        at = SHOW_AT.get(name, 0)
        still = max(still, min(L - 1, int(at * L) if isinstance(at, float) else at))
    for name in spec.effects:
        c.prop(EFFECTS[name](L, tint))
    for name in plan["wear"]:
        c.prop(ACCESSORIES[name](color=tint[name]) if name in tint else ACCESSORIES[name]())
    return c, char, dict(still=int(still), notes=notes, tint=tint, motion=plan["motion"], stance=plan["stance"], tail=plan["tail"], arms=plan["arms"])


def stage(doc, scale=1.0, dy=0.0, about=(256.0, 470.0)):
    """Parent every top-level layer to one null that scales the scene about `about` and moves it by dy."""
    layers = doc["layers"]
    ind = max(L["ind"] for L in layers) + 1
    for L in layers:
        if "parent" not in L:
            L["parent"] = ind
    null = {"ddd": 0, "ind": ind, "ty": 3, "nm": "stage", "sr": 1, "ao": 0, "ip": 0, "op": doc["op"], "st": 0, "bm": 0,
            "ks": {"o": {"a": 0, "k": 100}, "r": {"a": 0, "k": 0}, "p": {"a": 0, "k": [about[0], about[1] + dy, 0]},
                   "a": {"a": 0, "k": [about[0], about[1], 0]}, "s": {"a": 0, "k": [scale * 100, scale * 100, 100]}}}
    layers.append(null)
    return doc


def add_layers_on_top(doc, layers):
    """Append extra unparented Layers above everything (used for the caption)."""
    start = max(L["ind"] for L in doc["layers"]) + 1
    js = [L.json(start + k, {}, doc["op"]) for k, L in enumerate(layers)]
    doc["layers"] = js[::-1] + doc["layers"]
    return doc


def compose(spec: StickerSpec):
    """Spec -> (lottie dict, info)."""
    c, char, info = build_clip(spec)
    doc = char.build(c)
    doc["nm"] = f"sticker {spec.key()}"
    if spec.caption and spec.caption.text.strip():
        cap = spec.caption
        layers, (y0, y1) = caption_layers(cap.text.strip(), pos=cap.pos, style=cap.style)
        # fit the character (about FIGURE px tall) into the rows the caption leaves free
        if cap.pos == "bottom":
            ground, room = y0 - 6.0, y0 - 6.0 - 8.0
        else:
            ground, room = 496.0, 496.0 - (y1 + 6.0)
        k = min(0.9, room / FIGURE)
        stage(doc, scale=k, dy=ground - 470.0)
        add_layers_on_top(doc, layers)
    return doc, info
