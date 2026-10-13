"""Everything the studio can put in a sticker, in one place.

Each motion, held prop, effect, worn item, face and mascot is registered once, with the facts every other part
needs: its label and emoji, which paws it takes, where it sits, what it clashes with, how its colour is chosen and
when in the loop it looks its best.  The spec's allowed names, the composer's rules, the parser's checks, the LLM
schema, the pack emoji and the web editor's chips are all read from here, so adding an item is one call:

    @motion("clap", "Clap", "👏", doing="clapping", paws=2, sit="ok")
    def clap(m):
        ...
        return still_frame

Nothing in here draws.  Drawings live in studio/library/, registered with the decorators below.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# ------------------------------------------------------------------ what an item is
SIT_RULES = ("no", "ok", "only")           # can the motion be played sitting?  'only' = it is a sitting motion
WEAR_ZONES = ("hat", "eyes", "face", "nose", "mouth", "ear", "ears", "neck", "back", "body", "waist", "head_side")
EFFECT_ZONES = ("overhead", "around", "face", "back", "ground", "front")
ONE_PER_ZONE = ("overhead", "back")       # effect zones that hold one effect (a rain cloud and z's would pile up)


@dataclass(frozen=True)
class Motion:
    name: str
    fn: Callable                      # fn(m: Act) -> the frame that makes the best still (before the loop is rotated)
    label: str
    emoji: str = ""
    doing: str = ""                   # "waving": accessibility text says "A fox waving"
    paws: int = 0                     # free paws it wants (a held prop takes its paw first)
    sit: str = "no"                   # see SIT_RULES
    stance: str | None = None         # the stance it brings when the spec does not ask for one ("sleep" sits down)
    wag: float = 6.0                  # tail wag, degrees per joint
    blink: bool = True                # an extra blink is fine (False for motions with closed or hidden eyes)
    tags: tuple = ()
    uses: tuple = ()                  # props (names or categories) it acts with: their paw is handed to the motion
    face: str | None = None           # the face it suggests when nothing else sets one
    brings: str | None = None         # the prop it brings when the spec holds nothing it uses ("typing" brings a laptop)
    min_paws: int | None = None       # fewest free paws it can still be played with (default: paws)
    sit_alt: str | None = None        # what it becomes when the mascot sits and it cannot be played sitting
    paw_alt: str | None = None        # what it becomes when too few paws are free
    calm: bool = False                # a calm motion keeps a calm tempo (dozing never goes fast)
    draws: tuple = ()                 # effects it already draws itself ("sob" makes its own waterfall tears)

    @property
    def least_paws(self):
        return self.paws if self.min_paws is None else self.min_paws


@dataclass(frozen=True)
class Prop:
    name: str
    factory: Callable                 # factory(x: Make) -> spec(char, T, n)
    label: str
    emoji: str = ""
    noun: str = ""                    # "a mug of coffee"
    paw: str = "R"                    # preferred paw; "LR" = needs both
    pose: str = "hold"                # arm pose of the paw that holds it
    flexible: bool = True             # may move to the other paw
    tint: tuple = ()                  # colour names it likes, best first (contrast with the fur decides); () = fixed colours
    category: str = ""
    peak: float | None = None         # phase (0..1) where it is most complete; None = complete all the time / follows the paw
    stance: str | None = None         # a stance it needs (the gift box: feet apart)
    cost: float = 1.0                 # rough share of the Telegram size budget
    tags: tuple = ()


@dataclass(frozen=True)
class Effect:
    name: str
    factory: Callable                 # factory(x: Make) -> spec(char, T, n)
    label: str
    emoji: str = ""
    zone: str = "around"              # see EFFECT_ZONES; two effects in the 'overhead' zone fight for the same spot
    peak: float | None = None         # phase where it is most visible; the loop is turned so that it shows in the still
    follows: bool = False             # reads the mascot's motion frame by frame (must turn with it)
    tint: tuple = ()
    cost: float = 1.0
    tags: tuple = ()


@dataclass(frozen=True)
class Wear:
    name: str
    factory: Callable                 # factory(x: Make) -> spec(char, T, n)
    label: str
    emoji: str = ""
    zone: str = "hat"                 # see WEAR_ZONES; one item per zone
    noun: str = ""
    tint: tuple = ()
    tags: tuple = ()
    also: tuple = ()                  # other zones it covers (a hood covers hat and ear)
    covers: tuple = ()                # face parts it hides: "eyes" (sunglasses, a sleep mask), "mouth" (a face mask)
    views: tuple = ()                 # drawn views it draws itself ("side", "back"): its items get the view's copy of the
                                      # mascot (char.view_name says which); else a hat is worn as drawn for the front
                                      # and anything else is left out of drawn views


@dataclass(frozen=True)
class Face:
    name: str                         # a key of mascot.rig.FACES
    label: str
    emoji: str = ""
    mood: str = ""                    # word for accessibility text ("joyful")
    blink: bool = True                # eyes are open, so an occasional blink looks alive


@dataclass(frozen=True)
class Base:
    name: str
    label: str                        # "Fox"
    animal: str                       # "fox"
    load: Callable                    # () -> Character class
    emoji: str = ""
    snack: str = "cookie"             # what it eats when a sticker says "eating" and names no food


# ------------------------------------------------------------------ the registry
class Registry:
    def __init__(self):
        self.motions: dict[str, Motion] = {}
        self.props: dict[str, Prop] = {}
        self.effects: dict[str, Effect] = {}
        self.wear: dict[str, Wear] = {}
        self.faces: dict[str, Face] = {}
        self.bases: dict[str, Base] = {}
        self.stances: dict[str, str] = {}          # name -> label
        self.tails: dict[str, str] = {}
        self.arm_poses: dict[str, str] = {}

    def _add(self, table, item, kind):
        if item.name in table:
            raise ValueError(f"{kind} {item.name!r} is registered twice")
        if not item.name.replace("_", "").isalnum() or item.name != item.name.lower():
            raise ValueError(f"{kind} name {item.name!r} must be lowercase letters, digits and underscores")
        table[item.name] = item
        return item

    def names(self, kind):
        return tuple(getattr(self, kind))


REG = Registry()


def motion(name, label, emoji="", **kw):
    """Decorator: register fn(m) as a motion."""
    def deco(fn):
        REG._add(REG.motions, Motion(name, fn, label, emoji, **kw), "motion")
        return fn
    return deco


def prop(name, label, emoji="", **kw):
    def deco(factory):
        REG._add(REG.props, Prop(name, factory, label, emoji, **kw), "prop")
        return factory
    return deco


def effect(name, label, emoji="", **kw):
    def deco(factory):
        REG._add(REG.effects, Effect(name, factory, label, emoji, **kw), "effect")
        return factory
    return deco


def wear(name, label, emoji="", **kw):
    def deco(factory):
        REG._add(REG.wear, Wear(name, factory, label, emoji, **kw), "worn item")
        return factory
    return deco


def face(name, label, emoji="", **kw):
    REG._add(REG.faces, Face(name, label, emoji, **kw), "face")


def base(name, label, animal, load, emoji="", snack="cookie"):
    REG._add(REG.bases, Base(name, label, animal, load, emoji, snack), "mascot")


# ------------------------------------------------------------------ what a motion and a factory are given
@dataclass
class Act:
    """What a motion function works with."""
    c: object                         # mascot.clip.Clip
    L: int                            # frames in the loop
    k: float                          # intensity (1 = normal)
    tempo: float                      # 1 = normal speed
    hands: list                       # paws the motion may animate (a held prop took its paw first)
    stance: str
    char: object
    spec: object
    data: dict = field(default_factory=dict)       # extra hints from the composer (e.g. the prop in the hand)

    @property
    def sitting(self):
        return self.stance in ("sit", "lotus")

    def per(self, approx):
        """The period nearest to approx / tempo that fits a whole number of times into the loop."""
        return self.L / max(1, round(self.L * self.tempo / float(approx)))

    def per_n(self, approx, multiple=1):
        """Like per(), but the loop holds a multiple of `multiple` periods, so 1/multiple-sized parts of it loop too
        (three juggled balls every 1.5 tosses need an even number of ball cycles)."""
        n = round(self.L * self.tempo / float(approx) / multiple) * multiple
        return self.L / max(multiple, n)

    @property
    def side(self):
        """The paw a one-paw gesture uses: the first free one (right if both are free)."""
        return self.hands[0] if self.hands else None

    def prop_side(self, *wanted):
        """The paw holding a prop with one of these names or categories (one the motion acts with), else None."""
        for name, side in self.data.get("props", ()):
            pr = REG.props.get(name)
            if name in wanted or (pr is not None and pr.category in wanted):
                return side
        return None

    def other(self, side):
        """The other paw, if the motion may use it."""
        o = "L" if side == "R" else "R"
        return o if o in self.hands else None


@dataclass
class Make:
    """What a prop / effect / worn-item factory works with."""
    L: int                            # frames in the loop
    side: str = "R"                   # the paw a held prop sits in ("LR" for both)
    color: object = None              # chosen colour: a name of mascot.props.C or an [r, g, b] list
    spec: object = None
    plan: object = None
    k: float = 1.0                    # intensity

    def per(self, approx):
        return self.L / max(1, round(self.L / float(approx)))


def ensure_loaded():
    """Import the library (it registers itself).  Safe to call many times."""
    from . import library  # noqa: F401
    return REG
