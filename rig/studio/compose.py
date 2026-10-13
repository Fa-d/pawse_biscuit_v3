"""StickerSpec -> Lottie document.  Pure rules, no AI.

  1. the spec is normalised and checked                              (spec.py)
  2. the composer rules turn it into a plan, each change noted       (rules.py)
  3. the plan is acted out on a clip: stance, face, arms, the motion, props, effects, things worn
  4. the loop is turned so that frame 0 is the best frame: the motion's key pose, with every effect at the moment it
     looks most complete (the PNG still, Telegram's first frame and WhatsApp's resting frame are all frame 0)
  5. the rig bakes it; fades are written so rlottie (Telegram) does not dim the mascot behind them
  6. auto-framing: what the animation covers is measured and the scene fitted to the canvas, above or below a caption
"""
from __future__ import annotations

from mascot.clip import FPS, Clip
from mascot.lottie import rgb

from .caption import caption_layers
from .framing import CANVAS, MARGIN, fit, measure
from .registry import REG, Act, Make
from .rules import Plan, resolve as _resolve
from .spec import StickerSpec

FIGURE = 440.0          # rough height of a mascot plus headroom for bounces, in canvas px at scale 1 (used without a rasteriser)


def characters():
    return {name: b.load() for name, b in REG.bases.items()}


def _character(base, pal_over):
    cls = REG.bases[base].load()
    if not pal_over:
        return cls()
    pal = dict(cls.pal)
    for k, v in pal_over.items():
        pal[k] = list(v) if isinstance(v, (list, tuple)) else rgb(v)
    return type(f"{cls.__name__}Custom", (cls,), {"pal": pal})()


def plan_for(spec: StickerSpec) -> Plan:
    spec = spec.normalized()
    return _resolve(spec, REG.bases[spec.base].load().pal)


def make_character(spec, plan=None):
    """Character instance for the spec's base, with its palette overrides applied."""
    plan = plan or plan_for(spec)
    return _character(spec.base, plan.palette)


def resolve(spec: StickerSpec):
    """Compatibility view of the plan: (dict, notes) as v3 returned it."""
    p = plan_for(spec)
    fn = REG.motions[p.motion].fn
    m = REG.motions[p.motion]
    return dict(motion=p.motion, fn=fn, hands=p.hands, arms=p.arms, props=p.props, stance=p.stance, tail=p.tail, wear=p.wear,
                effects=p.effects, tints=p.tints, wants=m.paws), p.notes


def _make(plan, L, name, side="R"):
    return Make(L=L, side=side, color=plan.tints.get(name), spec=plan.spec, plan=plan, k=plan.spec.intensity)


def _peak_roll(peak, L):
    return None if peak is None else int(round(peak * L)) % L


def build_clip(spec: StickerSpec, char=None, plan=None):
    """Spec -> (Clip, character, info).  info has the still frame (before the loop is turned), the notes and the plan."""
    spec = spec.normalized()
    plan = plan or _resolve(spec, REG.bases[spec.base].load().pal)
    char = char or _character(spec.base, plan.palette)
    L = int(round(spec.seconds * FPS))
    c = Clip(f"sticker_{spec.key()}", L, loop=True, scale=1.0, char=char)
    c.calm = 0
    c.stance((0, plan.stance))
    c.face(0, plan.face, dur=0)
    if tuple(spec.look) != (0.0, 0.0):
        c.set("look.x", float(spec.look[0]))
        c.set("look.y", float(spec.look[1]))
    for s, pose in plan.arms.items():
        if pose is not None:
            c.arm(s, (0, pose))
    mv = REG.motions[plan.motion]
    act = Act(c=c, L=L, k=spec.intensity, tempo=plan.tempo, hands=list(plan.hands), stance=plan.stance, char=char, spec=spec,
              data=dict(props=list(plan.props), acts=list(plan.acts), face=plan.face))
    still = mv.fn(act)
    if spec.yaw:                                    # v5: turned away from the viewer, on top of any turn the motion makes
        c.add("body.yaw", lambda t, y=float(spec.yaw): y)
    if plan.gift_act:
        # the lid pops at 31 % of the loop: paws on the lid, to the cheeks, up in a cheer, back on the lid as it lands
        f = lambda u: int(round(u * L))
        happy = plan.face if plan.face in ("joy", "smiley", "laugh", "excited", "starry", "love", "grin") else "joy"
        c.arm("LR", (0, "lid"), (f(0.27), "lid"), (f(0.31), "lap", "in"), (f(0.38), "cheek", "back"), (f(0.48), "cheek"),
              (f(0.6), "cheer", "back"), (f(0.74), "cheer"), (f(0.86), "lid", "io"), (L, "lid"))
        c.face(0, "curious", dur=0, look_x=0.0, look_y=0.85)
        c.face(f(0.27), "curious", dur=0, look_x=0.0, look_y=0.85)
        c.face(f(0.36), "surprised", dur=6)
        c.face(f(0.55), happy, dur=8)
        c.face(f(0.8), happy, dur=0)
        c.face(f(0.92), "curious", dur=8, look_x=0.0, look_y=0.85)
        c.face(L, "curious", dur=0, look_x=0.0, look_y=0.85)
        still = f(0.62)
    elif any(n == "gift" for n, _ in plan.props):
        c.set("look.y", 0.85)
    c.tailpose((0, plan.tail))
    if plan.tail == "wrap":
        c.set("tail.front", 1.0)                 # across the lap
    wag = mv.wag * (0.5 if plan.sitting else 1.0) * spec.intensity
    c.wag(amp=wag, period=act.per(30 if wag > 8 else 60), lag=0.14)
    fc = REG.faces[plan.face]
    if fc.blink and mv.blink and not plan.gift_act:
        c.blink(int(L * 0.8))
    still = int(still) % L
    for name, side in plan.props:
        pr = REG.props[name]
        spec_fn = pr.factory(_make(plan, L, name, side))
        spec_fn.roll = _peak_roll(pr.peak, L)
        c.prop(spec_fn)
    for name in plan.effects:
        e = REG.effects[name]
        spec_fn = e.factory(_make(plan, L, name))
        spec_fn.roll = None if e.follows else _peak_roll(e.peak, L)
        c.prop(_on_face(spec_fn) if e.zone == "face" else spec_fn)
    for name in plan.wear:
        w = REG.wear[name]
        c.prop(_zoned(w.factory(_make(plan, L, name)), w.zone, w.views))
    info = dict(still=still, notes=list(plan.notes), tint=dict(plan.tints), motion=plan.motion, stance=plan.stance, tail=plan.tail,
                arms=dict(plan.arms), plan=plan)
    return c, char, info


def _zoned(spec_fn, zone, views=()):
    """A worn item's layers carry its zone, the drawn views it draws itself (Wear.views) and the spec that drew them,
    so a mascot turned to a drawn view (side, back) draws it again from there (mascot/views.py); a hat drawn for the
    front only is worn as it is, anything else drawn for the front only is left out.  Nothing is written for it."""
    def spec(char, T, n):
        out = spec_fn(char, T, n)
        for _, L in out:
            if hasattr(L, "nm"):
                L.view_zone, L.view_draws, L.view_spec = zone, tuple(views), spec
        return out
    for k, v in vars(spec_fn).items():
        setattr(spec, k, v)
    return spec


def _on_face(spec_fn):
    """An effect on the face (a tear, steam from the ears): its layers are marked, so a mascot turned to a drawn view
    moves them to the same place on the drawn head (mascot/views.py).  Nothing is written for it."""
    def spec(char, T, n):
        out = spec_fn(char, T, n)
        for _, L in out:
            if hasattr(L, "nm"):
                L.view_place, L.view_spec = "face", spec
        return out
    for k, v in vars(spec_fn).items():
        setattr(spec, k, v)
    return spec


# ------------------------------------------------------------------ staging
def stage(doc, scale=1.0, dy=0.0, about=(256.0, 470.0), dx=0.0):
    """Parent every top-level layer to one null that scales the scene about `about` and moves it by (dx, dy)."""
    layers = doc["layers"]
    ind = max(L["ind"] for L in layers) + 1
    for L in layers:
        if "parent" not in L:
            L["parent"] = ind
    null = {"ddd": 0, "ind": ind, "ty": 3, "nm": "stage", "sr": 1, "ao": 0, "ip": 0, "op": doc["op"], "st": 0, "bm": 0,
            "ks": {"o": {"a": 0, "k": 100}, "r": {"a": 0, "k": 0}, "p": {"a": 0, "k": [round(about[0] + dx, 2), round(about[1] + dy, 2), 0]},
                   "a": {"a": 0, "k": [round(about[0], 2), round(about[1], 2), 0]},
                   "s": {"a": 0, "k": [round(scale * 100, 3), round(scale * 100, 3), 100]}}}
    layers.append(null)
    return doc


def add_layers_on_top(doc, layers):
    """Append extra unparented Layers above everything (used for the caption)."""
    start = max(L["ind"] for L in doc["layers"]) + 1
    js = [L.json(start + k, {}, doc["op"]) for k, L in enumerate(layers)]
    doc["layers"] = js[::-1] + doc["layers"]
    return doc


def compose(spec: StickerSpec, frame=True):
    """Spec -> (lottie dict, info).  frame=False skips auto-framing (the v3 fixed sizes are used instead)."""
    c, char, info = build_clip(spec)
    plan = info.pop("plan")
    still = info["still"]
    c.roll = still                                  # frame 0 becomes the best frame
    c.opts["fade_safe"] = True
    doc = char.build(c)
    doc["nm"] = f"sticker {spec.key()}"
    info["still"] = 0
    info["rig_still"] = still
    cap = plan.spec.caption
    free = (0.0, CANVAS)
    layers = span = None
    if cap is not None and cap.text.strip() and not plan.sign_text:
        layers, span = caption_layers(cap.text.strip(), pos=cap.pos, style=cap.style)
        free = (0.0, span[0] + MARGIN - 6.0) if cap.pos == "bottom" else (span[1] - MARGIN + 6.0, CANVAS)
    box = measure(doc) if frame else None
    if box is not None:
        k, dx, dy, about = fit(box, free)
        stage(doc, scale=k, dx=dx, dy=dy, about=about)
        info["frame"] = dict(scale=round(float(k), 3), box=[round(float(v), 1) for v in box])
    else:                                           # no rasteriser: the v3 rule of thumb
        k = 0.86 if plan.motion in ("jump", "cheer") or any(n == "cloud" for n, _ in plan.props) else 1.0
        if plan.sitting:
            k = 1.06
        if layers is not None:
            y0, y1 = span
            ground, room = (y0 - 6.0, y0 - 14.0) if cap.pos == "bottom" else (496.0, 496.0 - (y1 + 6.0))
            k = min(0.9, room / FIGURE)
            stage(doc, scale=k, dy=ground - 470.0)
        elif abs(k - 1.0) > 1e-9:
            stage(doc, scale=k)
    if layers is not None:
        add_layers_on_top(doc, layers)
    return doc, info
