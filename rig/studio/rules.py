"""Composer rules: how a spec becomes a plan the rig can perform.

Each rule is a small function, registered in order with @rule.  A rule reads and changes the Plan and explains
every change in plain words (plan.notes), which the editor shows under the sticker.  `python -m studio.cli --rules`
lists them.  The order matters: a motion's own prop is added before paws are handed out, paws are handed out
before motions pick theirs, colours are settled before the items that are coloured, and so on.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .colour import delta, fur_palette, pick, prefs_for, readable, to_rgb
from .registry import ONE_PER_ZONE, REG
from .spec import MAX_EFFECTS, MAX_PROPS, MAX_WEAR, SIT_TAILS, StickerSpec

SITTING = ("sit", "lotus")
STAND_TAIL = {"ground": "low", "ground_up": "up", "wrap": "rest"}
SIT_TAIL = {"up": "ground_up", "out": "ground_up", "flick_out": "ground_up", "curl": "ground_up", "alert": "ground_up", "tucked": "wrap"}
# motions that cannot be played sitting, and what a sitting mascot does instead (a motion may name its own: sit_alt)
SIT_ALT = {"jump": "sway", "bounce": "sway", "cheer": "sway", "dance": "sway", "walk": "sway", "shiver": "sway"}
CALM_TEMPO = 1.2             # the fastest a calm motion (dozing, meditating) is played
BUDGET = 4.6                 # rough cost units a sticker may carry and stay under Telegram's 64 KB


@dataclass
class Plan:
    spec: StickerSpec
    base_pal: dict
    face: str = "smiley"
    motion: str = "idle"
    stance: str = "stand"
    tail: str = "rest"
    tempo: float = 1.0
    props: list = field(default_factory=list)        # [(name, side)]
    effects: list = field(default_factory=list)
    wear: list = field(default_factory=list)
    claims: dict = field(default_factory=dict)       # paw -> arm pose a prop needs
    free: list = field(default_factory=lambda: ["R", "L"])
    hands: list = field(default_factory=list)        # paws the motion animates
    acts: list = field(default_factory=list)         # [(prop, side)] held props the motion acts with (it moves their paw)
    arms: dict = field(default_factory=dict)         # paw -> pose, or None (the motion keys it)
    palette: dict = field(default_factory=dict)      # palette overrides as RGB lists
    tints: dict = field(default_factory=dict)        # item -> colour name or RGB list
    covered: set = field(default_factory=set)        # face parts something worn hides ("eyes", "mouth")
    sign_text: str | None = None                     # the caption, when a held sign carries it
    gift_act: bool = False
    notes: list = field(default_factory=list)
    fired: list = field(default_factory=list)

    def note(self, text):
        if text not in self.notes:
            self.notes.append(text)

    @property
    def sitting(self):
        return self.stance in SITTING

    @property
    def fur(self):
        return self.palette.get("orange", self.base_pal["orange"])


RULES = []


def the(label):
    """'the glasses are' / 'the crown is'."""
    lab = label.lower()
    plural = lab.endswith("s") and not lab.endswith("ss") or lab in ("headphones", "sunglasses", "glasses")
    return f"the {lab} {'are' if plural else 'is'}"


def doing(name):
    m = REG.motions[name]
    return m.doing or name.replace("_", " ")


def rule(code, text):
    """Register a composer rule.  code: short id (R01 ...); text: what it decides, in one sentence."""
    def deco(fn):
        fn.code, fn.text = code, text
        RULES.append(fn)
        return fn
    return deco


def resolve(spec: StickerSpec, base_pal: dict) -> Plan:
    """Run every rule in order.  `spec` must be normalized (StickerSpec.normalized)."""
    plan = Plan(spec=spec, base_pal=dict(base_pal), face=spec.face, motion=spec.motion, stance=spec.stance,
                tail=spec.tail or "rest", tempo=spec.tempo)
    for fn in RULES:
        before = len(plan.notes)
        fn(plan)
        if len(plan.notes) > before:
            plan.fired.append(fn.code)
    return plan


def describe():
    """The rules, in order, as (code, text)."""
    return [(fn.code, fn.text) for fn in RULES]


def _uses(mv, name):
    """Does motion mv act with the prop `name` (named, or by its category)?"""
    pr = REG.props.get(name)
    return bool(mv.uses) and (name in mv.uses or (pr is not None and pr.category in mv.uses))


# ------------------------------------------------------------------ 1. what is in the sticker
@rule("R01", "A sticker uses at most 2 props, 3 effects and 3 worn items, the first ones listed; repeats were removed when "
             "the spec was normalised.")
def caps(p):
    s = p.spec
    for kind, items, most in (("props", s.props, MAX_PROPS), ("effects", s.effects, MAX_EFFECTS), ("worn items", s.accessories, MAX_WEAR)):
        if len(items) > most:
            p.note(f"kept the first {most} {kind}: {', '.join(x.replace('_', ' ') for x in items[most:])} left out")
    p.props_wanted = list(s.props)[:MAX_PROPS]
    p.effects = list(s.effects)[:MAX_EFFECTS]
    p.wear_wanted = list(s.accessories)[:MAX_WEAR]


@rule("R02", "A motion that acts with something brings it when the spec holds nothing it can use: typing brings a laptop, "
             "singing a microphone, eating the mascot's favourite snack (a bone for the dog, a carrot for the bunny).")
def brings(p):
    mv = REG.motions[p.motion]
    if not mv.brings or any(_uses(mv, n) for n in p.props_wanted):
        return
    want = REG.bases[p.spec.base].snack if mv.brings == "snack" else mv.brings
    noun = REG.props[want].noun or want.replace("_", " ")
    if len(p.props_wanted) >= MAX_PROPS:
        p.note(f"{doing(p.motion)} without {noun}: the paws already hold two things")
        return
    p.props_wanted.insert(0, want)
    p.note(f"{doing(p.motion)}, so it holds {noun}")


@rule("R03", "A sitting-only motion (dozing, kicking its feet) sits the mascot down if the spec has it standing.")
def sit_for_sitting_motion(p):
    mv = REG.motions[p.motion]
    if mv.sit == "only" and not p.sitting:
        p.stance = mv.stance or "sit"
        p.note(f"{doing(p.motion)} is done sitting, so it sits down")


# ------------------------------------------------------------------ 2. paws
@rule("R04", "Held props claim paws first: the paw named in the spec, else the prop's preferred paw, else the other one; "
             "a prop that needs both paws needs both free.")
def props_claim_paws(p):
    sides = p.spec.sides
    for name in p.props_wanted:
        pr = REG.props[name]
        if pr.paw == "LR":
            if len(p.free) < 2:
                p.note(f"dropped the {pr.label.lower()}: it needs both paws")
                continue
            for s in "RL":
                p.claims[s] = pr.pose
            p.free = []
            p.props.append((name, "LR"))
            continue
        want = sides.get(name, pr.paw)
        side = want if want in p.free else (p.free[0] if (pr.flexible or name in sides) and p.free else None)
        if side is None:
            p.note(f"dropped the {pr.label.lower()}: no free paw")
            continue
        if side != want:
            p.note(f"the {pr.label.lower()} moved to the {'left' if side == 'L' else 'right'} paw")
        p.claims[side] = pr.pose
        p.free.remove(side)
        p.props.append((name, side))


# a motion and a held thing that together mean another motion: (motion, prop) -> motion
WITH_PROP = {("wave", "flag"): "wave_flag", ("wave_both", "flag"): "wave_flag", ("cheer", "flag"): "wave_flag",
             ("cheer", "glass"): "toast", ("bounce", "glass"): "toast", ("dance", "microphone"): "sing", ("sway", "microphone"): "sing",
             ("dance", "guitar"): "strum", ("sway", "guitar"): "strum", ("bounce", "guitar"): "strum", ("headbang", "guitar"): "strum",
             ("hug", "plushie"): "cuddle", ("nod", "laptop"): "typing", ("think", "pencil"): "write", ("think", "book"): "read"}


@rule("R05", "A motion done with a thing that has its own way of being used becomes that: waving with a flag waves the flag, "
             "cheering with a glass raises a toast, dancing with a microphone sings, with a guitar strums.")
def motion_with_prop(p):
    for name, _ in p.props:
        alt = WITH_PROP.get((p.motion, name))
        if alt:
            p.note(f"{doing(p.motion)} with {REG.props[name].noun or name}, so it's {doing(alt)}")
            p.motion = alt
            return


@rule("R06", "A prop that needs a stance gets it (feet apart either side of a gift box); a sitting mascot stands up for it.")
def prop_stance(p):
    for name, _ in p.props:
        need = REG.props[name].stance
        if need and p.stance != need:
            if p.sitting:
                p.note(f"stands up with its feet apart for the {REG.props[name].label.lower()}")
            elif need == "wide":
                p.note(f"{REG.props[name].label.lower()}: feet apart on either side of it")
            p.stance = need


@rule("R07", "A motion that needs legs is swapped for one that works sitting when the mascot sits.")
def sitting_swaps(p):
    mv = REG.motions[p.motion]
    if p.sitting and mv.sit == "no":
        alt = mv.sit_alt or SIT_ALT.get(p.motion, "sway")
        p.note(f"{doing(p.motion)} needs legs; sitting, so it's {doing(alt)} instead")
        p.motion = alt


@rule("R24", "A turned mascot (a yaw, or a motion that turns) shows the drawn side and back views it has; without them it turns "
             "as far as three-quarter and shows its front past that, and looking back over its shoulder (which needs a back "
             "view) becomes looking around.")
def views(p):
    s = p.spec
    mv = REG.motions[p.motion]
    if not s.yaw and "turn" not in mv.tags:
        return
    ch = REG.bases[s.base].load()()
    side, back = ch.view_data("side") is not None, ch.view_data("back") is not None
    animal = REG.bases[s.base].animal
    if p.motion == "look_back" and not back:
        p.note(f"the {animal} has no back view drawn yet, so it looks around instead of looking back over its shoulder")
        p.motion = "look_around"
        return
    if not side:
        p.note(f"the {animal} has no side or back view drawn yet, so it turns as far as three-quarter")
    elif not back and (abs(s.yaw) >= 135.0 or "turn" in mv.tags):
        p.note(f"the {animal} has no back view drawn yet, so it shows its side instead")


@rule("R08", "A held prop the motion acts with is given to the motion: its paw follows the motion and the prop moves with it "
             "(a snack goes to the mouth, a mug is sipped).")
def acts_with(p):
    mv = REG.motions[p.motion]
    for name, side in p.props:
        if side != "LR" and _uses(mv, name) and not p.acts:
            p.acts.append((name, side))
        elif side == "LR" and _uses(mv, name) and not p.acts:
            p.acts.append((name, "LR"))


@rule("R09", "The motion gets the paws that are left (and the paw of a prop it acts with); with too few it becomes the "
             "version it names for fewer paws, else a bounce.")
def motion_paws(p):
    mv = REG.motions[p.motion]
    acting = [s for _, side in p.acts for s in ("RL" if side == "LR" else side)]
    avail = acting + [s for s in p.free if s not in acting]
    if mv.least_paws > len(avail):
        has_gift = any(n == "gift" for n, _ in p.props)
        alt = mv.paw_alt
        if alt and REG.motions[alt].least_paws <= len(p.free):
            p.note(f"{doing(p.motion)} needs {mv.least_paws} free paws, so it's {doing(alt)} instead")
            p.motion = alt
        elif has_gift:
            p.note("the gift is the act: paws on the lid, it pops, then a cheer")
            p.motion = "bounce" if not p.sitting else "sway"
        else:
            fallback = "sway" if p.sitting else "bounce"
            busy = "both are busy" if not p.free else "the other one is busy"
            p.note(f"{doing(p.motion)} needs {'both paws' if mv.least_paws == 2 else 'a free paw'}; {busy}, so it's {doing(fallback)} instead")
            p.motion = fallback
        mv = REG.motions[p.motion]
        p.acts = [(n, s) for n, s in p.acts if _uses(mv, n)]
        acting = [s for _, side in p.acts for s in ("RL" if side == "LR" else side)]
        avail = acting + [s for s in p.free if s not in acting]
    p.hands = avail[:max(mv.paws, len(acting))]
    if mv.paws == 1 and p.hands == ["L"] and not acting and p.motion != "think":
        p.note(f"{doing(p.motion)} with the left paw (the right one is holding something)")


@rule("R10", "Paws nobody claimed take the pose the spec asks for, else rest on the knees when cross-legged, else hang.")
def arm_poses(p):
    s = p.spec
    for side, want in (("R", s.arm_R), ("L", s.arm_L)):
        if side in p.hands:
            p.arms[side] = None
        elif side in p.claims:
            p.arms[side] = p.claims[side]
        else:
            p.arms[side] = want or ("knee" if p.stance == "lotus" else "rest")


# ------------------------------------------------------------------ 3. worn things and effects
OWN_FEATURE = {"bunny_ears": "bunny"}         # costume -> the animal that has the real thing


@rule("R11", "A costume of what the mascot already has is left out: bunny ears on the bunny.")
def own_costume(p):
    animal = REG.bases[p.spec.base].animal if p.spec.base in REG.bases else ""
    for name in [n for n in p.wear_wanted if OWN_FEATURE.get(n) == animal]:
        p.wear_wanted.remove(name)
        p.note(f"left out the {REG.wear[name].label.lower()}: the {animal} has its own")


@rule("R12", "One worn item per place on the body (hat, eyes, ears, neck, back ...); a later one that needs a taken place is dropped.")
def wear_zones(p):
    taken = {}
    for name in p.wear_wanted:
        w = REG.wear[name]
        zones = (w.zone,) + tuple(w.also)
        clash = next((taken[z] for z in zones if z in taken), None)
        if clash:
            p.note(f"dropped the {w.label.lower()}: it goes where {the(REG.wear[clash].label)}")
            continue
        for z in zones:
            taken[z] = name
        p.wear.append(name)


MOUTH_MOTIONS = ("eat", "sip", "sing", "blow_kiss", "brush_teeth", "toast", "blow_nose", "yawn")
SIGHT_MOTIONS = ("read", "typing", "texting", "photo", "selfie", "paint", "gaming", "write", "juggle", "look_around", "magic", "knock")


@rule("R13", "Something worn over the mouth comes off for a motion that uses the mouth (eating, sipping, singing, a kiss, "
             "brushing teeth); a sleep mask comes off for one that needs to see (reading, typing, taking photos).")
def busy_face(p):
    for name in list(p.wear):
        w = REG.wear[name]
        if "mouth" in w.covers and p.motion in MOUTH_MOTIONS:
            p.wear.remove(name)
            p.note(f"takes off the {w.label.lower()} for {doing(p.motion)}")
        elif name == "sleep_mask" and p.motion in SIGHT_MOTIONS:
            p.wear.remove(name)
            p.note(f"pushes the sleep mask off for {doing(p.motion)}")


@rule("R14", "Something worn over the eyes hides special eyes (hearts, stars, spirals), and a mask hides the mouth; the face "
             "is kept and the note says what doesn't show.")
def covered_face(p):
    from mascot.rig import FACES
    for name in p.wear:
        p.covered.update(REG.wear[name].covers)
    face = FACES.get(p.face, {})
    style = face.get("eye.style", 0)
    if "eyes" in p.covered and style and style != 6:
        hider = next(REG.wear[n].label.lower() for n in p.wear if "eyes" in REG.wear[n].covers)
        p.note(f"{the(hider).rsplit(' ', 1)[0]} hide{'' if hider.endswith('s') else 's'} its eyes")
    mouthy = face.get("mouth.kiss", 0) or face.get("tongue", 0) > 1.2 or face.get("mouth.wail", 0) or face.get("mouth.open", 0) > 1.1
    if "mouth" in p.covered and mouthy:
        hider = next(REG.wear[n].label.lower() for n in p.wear if "mouth" in REG.wear[n].covers)
        p.note(f"the {hider} covers its mouth")


@rule("R15", "An effect the motion already draws is not drawn twice: sobbing makes its own waterfall tears and soaring "
             "its own speed lines.")
def drawn_by_motion(p):
    own = REG.motions[p.motion].draws if p.motion in REG.motions else ()
    for name in [n for n in p.effects if n in own]:
        p.effects.remove(name)
        p.note(f"{doing(p.motion)} already makes its own {REG.effects[name].label.lower()}")


@rule("R16", "Only one effect floats over the head (rain cloud, z's, thought dots ...) and one glows behind the mascot (glow "
             "ring, rainbow, sun rays ...); later ones that would pile up there are dropped.")
def one_per_zone(p):
    seen = {}
    keep = []
    for name in p.effects:
        e = REG.effects[name]
        if e.zone in ONE_PER_ZONE:
            if e.zone in seen:
                where = "over its head" if e.zone == "overhead" else "behind it"
                p.note(f"dropped the {e.label.lower()}: {the(REG.effects[seen[e.zone]].label)} already {where}")
                continue
            seen[e.zone] = name
        keep.append(name)
    p.effects = keep


@rule("R17", "A sticker stays under Telegram's size limit: when props and effects add up to too much, the costliest effect goes.")
def budget(p):
    def cost():
        return sum(REG.props[n].cost for n, _ in p.props) + sum(REG.effects[n].cost for n in p.effects) + 0.25 * len(p.wear)
    while p.effects and cost() > BUDGET:
        drop = max(p.effects, key=lambda n: REG.effects[n].cost)
        p.effects.remove(drop)
        p.note(f"dropped the {REG.effects[drop].label.lower()} to stay within Telegram's 64 KB")


# ------------------------------------------------------------------ 4. body and tempo
@rule("R18", "The tail follows the stance: sitting mascots use the sitting tail poses, standing ones the standing poses.")
def tail(p):
    t = p.spec.tail
    if p.sitting:
        if t not in SIT_TAILS:
            p.tail = SIT_TAIL.get(t, "wrap" if p.stance == "lotus" else "ground")
    else:
        p.tail = STAND_TAIL.get(t, t) if t else "rest"


@rule("R19", "A calm motion keeps a calm tempo: dozing, meditating or swaying is never played faster than 1.2 times.")
def calm_tempo(p):
    mv = REG.motions[p.motion]
    if mv.calm and p.tempo > CALM_TEMPO:
        p.note(f"{doing(p.motion)} stays slow")
        p.tempo = CALM_TEMPO


# ------------------------------------------------------------------ 5. colours
@rule("R20", "A colour for the fur repaints every shade of it (arms, legs, tail, stripes) and keeps eyes and paws readable.")
def palette(p):
    pal = dict(p.spec.palette)
    if not pal:
        return
    base = p.base_pal
    out = {k: to_rgb(v) for k, v in pal.items()}
    if set(pal) == {"orange"}:                          # one colour: shade the rest from it
        out.update({k: to_rgb(v) for k, v in fur_palette(pal["orange"], base).items() if k not in pal})
    # slots that shared a colour in the design keep sharing it (the cat's tail tip is its stripe colour)
    for k in base:
        if k in out or not isinstance(base[k], (list, tuple)):
            continue
        twin = next((o for o in pal if o in base and base[o] == base[k]), None)
        if twin:
            out[k] = out[twin]
    merged = dict(base)
    merged.update(out)
    fix = readable(merged)
    if fix and "dark" not in pal:
        out.update(fix)
        p.note("eyes and paws drawn darker so they show on the dark fur")
    p.palette = out


@rule("R21", "A worn or held thing takes the colour the spec gives it, else the first colour it likes that stands out from the fur.")
def tints(p):
    fur = p.fur
    for name in [n for n, _ in p.props] + p.effects + p.wear:
        if name in p.spec.tints:
            p.tints[name] = to_rgb(p.spec.tints[name])
            if delta(p.tints[name], fur) < 12:
                p.note(f"the {name.replace('_', ' ')} is nearly the colour of the fur")
            continue
        prefs = prefs_for(name)
        if prefs:
            p.tints[name] = pick(prefs, fur)


# ------------------------------------------------------------------ 6. acting
@rule("R22", "With a gift box and a loop of at least 100 frames the gift is the act: paws on the lid, it pops, a cheer, the lid drops back.")
def gift_act(p):
    if any(n == "gift" for n, _ in p.props):
        p.gift_act = round(p.spec.seconds * 60) >= 100
        if not p.gift_act:
            p.note("too short for the gift to pop open; it just wiggles")


SIGN_MAX = 40                # longest caption written on a sign (longer ones stay under the sticker)


@rule("R23", "A sign carries the caption: with a sign in its paw, the caption is written on the sign instead of under the sticker "
             "(if it is short enough to read there).")
def sign_caption(p):
    cap = p.spec.caption
    if not any(n == "sign" for n, _ in p.props) or cap is None or not cap.text.strip():
        return
    if len(cap.text.strip()) <= SIGN_MAX:
        p.sign_text = cap.text.strip()
        p.note("the caption is written on the sign")
    else:
        p.note("the caption is too long for the sign, so it stays under the sticker")
