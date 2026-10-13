"""SceneSpec -> Lottie document, for one or two mascots.  Pure rules, no AI.

    doc, info = compose_scene(SceneSpec(actors=[ActorSpec(base="mochi", motion="wave"), ActorSpec(base="pip")]))

  1. a scene of one mascot is a v4 sticker: compose() makes it, byte for byte as before
  2. the scene rules (S01 ...) settle what the mascots share and where they stand, each change noted
  3. every mascot is planned by the v4 composer rules (R01-R23) and acted out on its own clip
  4. the mascots are baked into one document by mascot.scene.Scene (names, stages, depth bands)
  5. the caption and auto-framing work on the whole scene, as compose() does for one mascot
  6. a scene over Telegram's 64 KB loses its costliest effect and is built again (S08)

Rules still to come with duets (phase 3): S02 roles, S03 paws claimed by a duet, S05 facing each other, and S10
(phase 2) views a mascot lacks.  Until then two mascots stand side by side and each plays its own motion.
"""
from __future__ import annotations

import colorsys
from dataclasses import dataclass, field
from functools import lru_cache

from mascot.clip import FPS
from mascot.scene import Scene, Stage

from .caption import caption_layers
from .colour import to_hex, to_rgb
from .compose import add_layers_on_top, build_clip, compose, stage
from .export import TGS_MAX, tgs_bytes
from .framing import CANVAS, MARGIN, fit, measure
from .registry import REG
from .scene_spec import MAX_ACTORS, ActorSpec, SceneSpec

IDS = ("a", "b")
DUO_SCALE = 0.74            # each mascot's size in a scene of two, before auto-framing fits the scene to the canvas
DUO_OVERLAP = 0.06          # how much the two bodies overlap, as a share of their widths (they stand close, as friends do)
DUO_DEPTH = 5.0             # px: the mascot on the left stands a little behind, the one on the right a little in front


@dataclass
class ScenePlan:
    spec: SceneSpec
    stickers: list = field(default_factory=list)      # one v4 StickerSpec per mascot
    stages: list = field(default_factory=list)        # one mascot.scene.Stage per mascot
    ids: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    fired: list = field(default_factory=list)

    def note(self, text):
        if text not in self.notes:
            self.notes.append(text)


SCENE_RULES = []


def scene_rule(code, text):
    def deco(fn):
        fn.code, fn.text = code, text
        SCENE_RULES.append(fn)
        return fn
    return deco


def describe():
    """The scene rules, in order, as (code, text)."""
    return [(fn.code, fn.text) for fn in SCENE_RULES]


def animal(base):
    return REG.bases[base].animal if base in REG.bases else base


def resolve_scene(spec: SceneSpec) -> ScenePlan:
    """Run every scene rule in order.  `spec` must be normalized (SceneSpec.normalized)."""
    plan = ScenePlan(spec=spec, stickers=spec.stickers(), ids=list(IDS[:len(spec.actors)]))
    for fn in SCENE_RULES:
        before = len(plan.notes)
        fn(plan)
        if len(plan.notes) > before:
            plan.fired.append(fn.code)
    return plan


# ------------------------------------------------------------------ the rules
@scene_rule("S01", "A sticker holds at most two mascots; the spec is refused with more (the parser leaves a third one out, "
                   "with a note).")
def cast(p):
    if len(p.stickers) > MAX_ACTORS:                        # SceneSpec.validate() refuses this already; kept as the rule's record
        raise ValueError(f"at most {MAX_ACTORS} mascots in a sticker")


@scene_rule("S04", "Without a duet the two mascots stand side by side, close enough to overlap a little: the first one named on "
                   "the left and a little behind, the second on the right and a little in front, so the left one's tail "
                   "tucks behind its friend.")
def side_by_side(p):
    if len(p.stickers) == 1:
        p.stages = [Stage()]
        return
    a, b = p.stickers
    p.stages = list(duo_stages(a.base, b.base))
    p.note(f"the {animal(a.base)} stands on the left, the {animal(b.base)} on the right")


@scene_rule("S06", "Two of the same mascot are told apart: when neither has a fur colour, the second one takes the mascot's best "
                   "known fur variant (an arctic fox, a ginger cat, a polar bear), or a lighter shade of its own fur.")
def tell_apart(p):
    if len(p.stickers) < 2:
        return
    a, b = p.stickers
    if a.base != b.base or a.palette or b.palette:
        return
    name, hexc = fur_variant(b.base)
    b.palette = {"orange": hexc}
    p.note(f"the second {animal(b.base)} is {name} so the two can be told apart")


@scene_rule("S07", "An effect belongs to one mascot.  Scene-wide effects are drawn around the mascot in front until duets bring "
                   "effects that span both (phase 3).")
def effect_owner(p):
    extra = [e for e in p.spec.effects]
    if not extra:
        return
    front = max(range(len(p.stickers)), key=lambda q: (p.stages[q].y if p.stages else 0.0, -q))
    s = p.stickers[front]
    s.effects = list(dict.fromkeys(list(s.effects) + extra))
    labels = ", ".join(REG.effects[e].label.lower() for e in extra)
    if len(p.stickers) > 1:
        p.note(f"the {labels} {'is' if len(extra) == 1 else 'are'} drawn around the {animal(s.base)} for now")


@scene_rule("S08", "A scene stays under Telegram's 64 KB: when the built file is over, the costliest effect of either mascot is "
                   "left out and the scene is built again.")
def budget(p):
    pass                                                    # applied after building (compose_scene), where the size is known


@scene_rule("S09", "One tempo for the scene: both mascots play at the scene's tempo, and a calm motion still stays calm (R19).")
def one_tempo(p):
    for s in p.stickers:
        s.tempo = p.spec.tempo


# ------------------------------------------------------------------ staging and colours
@lru_cache(maxsize=None)
def body_extent(base):
    """(left, right) reach of a mascot's head, ears, body and feet from its centre line, in its own canvas px, without the
    tail (which tucks behind a friend).  Measured once per mascot on its rest pose; a fixed guess without a rasteriser."""
    from mascot.clip import Clip
    ch = REG.bases[base].load()()
    c = Clip(f"extent_{base}", 2, loop=True, char=ch)
    c.face(0, "smiley", dur=0)
    c.arm("LR", (0, "rest"))
    c.tailpose((0, "rest"))
    doc = ch.build(c)
    doc["layers"] = [L for L in doc["layers"] if L["nm"] not in ("tail", "tail lap", "tail front", "shadow")]
    box = measure(doc)
    if box is None:
        return (140.0, 140.0)
    return (ch.CX - box[0], box[2] - ch.CX)


def duo_stages(base_a, base_b, scale=DUO_SCALE, overlap=DUO_OVERLAP, depth=DUO_DEPTH):
    """Stages that put two mascots side by side, a little overlapped, the pair centred on the canvas."""
    la, ra = body_extent(base_a)
    lb, rb = body_extent(base_b)
    d = (ra + lb) * scale * (1.0 - overlap)                 # from a's ground point to b's
    xa = -(d + (rb - la) * scale) / 2.0
    return Stage(x=round(xa, 2), y=-depth, scale=scale), Stage(x=round(xa + d, 2), y=depth, scale=scale)


def fur_variant(base):
    """(words for it, '#rrggbb') of the first fur variant the lexicon lists for a mascot ('an arctic fox'), else a lighter
    shade of its own fur ('a lighter bao')."""
    from .parse.fallback import default_parser
    p = default_parser()
    for name, entry in p.lex["bases"].items():
        means = entry.get("means", {}) or entry.get("set", {})
        if means.get("base") == base and entry.get("colour"):
            word = str(entry["words"][0])
            art = "an" if word[:1] in "aeiou" else "a"
            return f"{art} {word}", p._hex(entry["colour"])
    h, l, s = colorsys.rgb_to_hls(*to_rgb(REG.bases[base].load().pal["orange"]))
    return f"a lighter {animal(base)}", to_hex(colorsys.hls_to_rgb(h, min(0.92, l + 0.14), s * 0.85))


# ------------------------------------------------------------------ composing
def _drop_costliest(plan):
    """S08: leave out the costliest effect of any mascot.  False when there is none left to drop."""
    best = None
    for q, s in enumerate(plan.stickers):
        for e in s.effects:
            cost = REG.effects[e].cost
            if best is None or cost > best[0]:
                best = (cost, q, e)
    if best is None:
        return False
    _, q, e = best
    plan.stickers[q].effects = [x for x in plan.stickers[q].effects if x != e]
    plan.note(f"dropped the {REG.effects[e].label.lower()} to stay within Telegram's 64 KB")
    if "S08" not in plan.fired:
        plan.fired.append("S08")
    return True


def _build(plan, frame=True):
    spec = plan.spec
    L = int(round(spec.seconds * FPS))
    built = [build_clip(s) for s in plan.stickers]
    lead_still = int(built[0][2]["still"]) % L
    sc = Scene(f"scene {spec.key()}", frames=L, roll=lead_still, fade_safe=True)
    for ident, (clip, char, _), st in zip(plan.ids, built, plan.stages):
        clip.opts["fade_safe"] = True
        sc.add(ident, char, clip, st)
    doc = sc.build()
    doc["nm"] = f"sticker {spec.key()}"
    actors = []
    notes = list(plan.notes)
    for s, (_, _, info) in zip(plan.stickers, built):
        mine = [n for n in info["notes"]]
        actors.append(dict(base=s.base, motion=info["motion"], stance=info["stance"], tail=info["tail"], arms=info["arms"], notes=mine))
        notes += [f"{animal(s.base)}: {n}" for n in mine]
    info = dict(still=0, rig_still=lead_still, notes=notes, scene_rules=list(plan.fired), actors=actors,
                stages=[dict(x=st.x, y=st.y, scale=st.scale, mirror=st.mirror) for st in plan.stages])
    cap = spec.caption
    free = (0.0, CANVAS)
    layers = span = None
    if cap is not None and cap.text.strip():
        layers, span = caption_layers(cap.text.strip(), pos=cap.pos, style=cap.style)
        free = (0.0, span[0] + MARGIN - 6.0) if cap.pos == "bottom" else (span[1] - MARGIN + 6.0, CANVAS)
    box = measure(doc) if frame else None
    if box is not None:
        k, dx, dy, about = fit(box, free)
        stage(doc, scale=k, dx=dx, dy=dy, about=about)
        info["frame"] = dict(scale=round(float(k), 3), box=[round(float(v), 1) for v in box])
    elif layers is not None:
        y0, y1 = span
        ground = y0 - 6.0 if cap.pos == "bottom" else 496.0
        stage(doc, scale=0.86, dy=ground - 470.0)
    if layers is not None:
        add_layers_on_top(doc, layers)
    return doc, info


def compose_scene(scene, frame=True):
    """SceneSpec (or a v3 / v4 StickerSpec, or either as a dict) -> (lottie dict, info)."""
    if isinstance(scene, dict):
        scene = SceneSpec.from_dict(scene)
    elif not isinstance(scene, SceneSpec):
        scene = SceneSpec.from_sticker(scene)
    scene = scene.normalized()
    if scene.solo:
        return compose(scene.sticker(), frame=frame)
    plan = resolve_scene(scene)
    while True:
        doc, info = _build(plan, frame)
        if len(tgs_bytes(doc)) <= TGS_MAX or not _drop_costliest(plan):
            return doc, info


def duo(base_a, base_b, **kw):
    """A quick scene of two mascots (handy in tests and the CLI): duo('mochi', 'pip', motion='wave')."""
    return SceneSpec(actors=[ActorSpec(base=base_a, **kw), ActorSpec(base=base_b, **kw)])
