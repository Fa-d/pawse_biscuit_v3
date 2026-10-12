"""Things to eat and drink.  Each is drawn upright around the point that rests in the paw (0, 0), negative y up,
and tilts with the paw (upright=False), so an 'eat' or 'sip' motion takes it to the mouth.

Category 'food' or 'drink': the eat and sip motions act with any prop of their category.
"""
from __future__ import annotations

from ..registry import prop
from .common import C, F, Layer, Path, acted, col, el, fl, gr, grip, heart_path, math, rc, sh, smooth, st


def held(x, items, pose="hold", upright=False, tilt=0.0, scale=1.3, nm="prop", grip_at=(0.0, 17.0)):
    """spec for items held in the paw x.side.  items: a list, or fn(char, T, n) -> list (for animated parts)."""
    side = x.side
    upright = upright or acted(x)

    def spec(char, T, n):
        its = items(char, T, n) if callable(items) else items
        return [(f"hand.{side}", grip(char, T, side, its, pose, upright=upright, tilt=tilt, scale=scale, nm=nm, grip_at=grip_at))]
    return spec


def flame(n, L, at=(0.0, 0.0), size=1.0, nm="flame"):
    """A small candle flame that flickers on a loop (period divides L)."""
    per = L / max(1, round(L / 12.0))
    shape = smooth([(0, -16), (7, -2), (4, 6), (-4, 6), (-7, -2)], closed=True, tension=0.42, sharp={0: 0.5})
    inner = smooth([(0, -8), (4, 0), (2, 5), (-2, 5), (-4, 0)], closed=True, tension=0.42, sharp={0: 0.5})
    return gr(nm, [gr("core", [sh(inner), fl(C["yellow"])]), gr("flame", [sh(shape), fl(C["flame"])])],
              a=(0.0, 6.0), p=(at[0], at[1] + 6),
              s=F(n, lambda f: (100 * size * (1 + 0.08 * math.sin(2 * math.pi * f / per)), 100 * size * (1 + 0.16 * math.sin(2 * math.pi * f / per + 1.3))),
                  tol=2.0),
              r=F(n, lambda f: 6 * math.sin(2 * math.pi * f / per * 2 + 0.4), tol=1.5))


# ------------------------------------------------------------------ food
@prop("pizza", "Pizza slice", "🍕", noun="a slice of pizza", category="food", tags=("food", "party"))
def pizza(x):
    slice_ = smooth([(-34, -14), (0, -104), (34, -14)], closed=True, tension=0.1, sharp={0: 0.9, 1: 0.9, 2: 0.9})
    drip = smooth([(16, -40), (24, -40), (22, -26), (19, -22), (16, -28)], closed=True, tension=0.4)
    return held(x, [
        gr("pepperoni", [el((-10, -42), (17, 17)), el((12, -58), (16, 16)), el((-1, -80), (13, 13)), fl(C["tomato"])]),
        gr("drip", [sh(drip), fl(C["cheese"])]),
        gr("slice", [sh(slice_), fl(C["cheese"])]),
        gr("crust", [rc((0, -12), (78, 18), 9), fl(C["crust"])]),
    ], nm="pizza")


@prop("burger", "Burger", "🍔", noun="a burger", category="food", tags=("food",))
def burger(x):
    top = smooth([(-42, -46), (-36, -70), (0, -84), (36, -70), (42, -46)], closed=True, tension=0.36, sharp={0: 0.3, 4: 0.3})
    lettuce = smooth([(-46, -44), (-34, -36), (-22, -44), (-10, -36), (2, -44), (14, -36), (26, -44), (38, -36), (46, -44), (46, -40), (-46, -40)],
                     closed=True, tension=0.3)
    cheese = smooth([(-40, -38), (40, -38), (30, -26), (20, -30), (-6, -30), (-20, -24), (-30, -30)], closed=True, tension=0.2)
    seeds = [el((sx, sy), (5, 7)) for sx, sy in ((-18, -70), (0, -76), (18, -70), (-8, -62), (10, -63))]
    return held(x, [
        gr("seeds", seeds + [fl(C["cream"])]),
        gr("bun top", [sh(top), fl(C["crust"])]),
        gr("lettuce", [sh(lettuce), fl(C["lettuce"])]),
        gr("cheese", [sh(cheese), fl(C["cheese"])]),
        gr("patty", [rc((0, -26), (86, 18), 9), fl(C["darkbrown"])]),
        gr("bun", [rc((0, -10), (82, 18), 9), fl(C["crust"])]),
    ], nm="burger")


@prop("donut", "Donut", "🍩", noun="a donut", category="food", tags=("food", "sweet"), tint=("gum", "coral", "lilac", "mint"))
def donut(x):
    icing = col(x.color or "gum")
    sprinkles = []
    for q, (a, cname) in enumerate(((10, "yellow"), (60, "teal"), (110, "white"), (160, "yellow"), (215, "teal"), (265, "white"), (320, "yellow"))):
        r = math.radians(a)
        cx, cy = 24 * math.cos(r), -46 + 24 * math.sin(r)
        sprinkles.append(gr(f"sprinkle {q}", [rc((0, 0), (9, 3.5), 1.7), fl(C[cname])], p=(cx, cy), r=a + 70))
    return held(x, sprinkles + [
        gr("icing", [el((0, -46), (50, 50)), st(icing, 20)]),
        gr("dough", [el((0, -44), (54, 54)), st(C["crust"], 28)]),
    ], nm="donut")


@prop("ice_cream", "Ice cream", "🍦", noun="an ice cream cone", category="food", tags=("food", "sweet", "summer"),
      tint=("gum", "mint", "lilac", "cream"))
def ice_cream(x):
    scoop = col(x.color or "gum")
    cone = Path([(-24, -54), (24, -54), (0, 2)], closed=True)
    waffle = [sh(Path([(-16, -50), (6, -6)], closed=False)), sh(Path([(0, -54), (13, -26)], closed=False)),
              sh(Path([(16, -50), (-6, -6)], closed=False)), sh(Path([(0, -54), (-13, -26)], closed=False))]
    drip = smooth([(-24, -60), (24, -60), (22, -50), (14, -46), (8, -38), (2, -48), (-10, -44), (-20, -50)], closed=True, tension=0.38)
    return held(x, [
        gr("cherry", [el((4, -112), (16, 16)), fl(C["red"])]),
        gr("stem", [sh(Path([(4, -118), (12, -130)], closed=False)), st(C["darkgreen"], 3)]),
        gr("scoop shine", [el((-12, -92), (12, 8)), fl(C["white"], 60)]),
        gr("top scoop", [el((0, -92), (46, 42)), fl(C["mint"])]),
        gr("drip", [sh(drip), fl(scoop)]),
        gr("scoop", [el((0, -68), (54, 46)), fl(scoop)]),
        gr("waffle", waffle + [st(C["tan"], 3)]),
        gr("cone", [sh(cone), fl(C["crust"])]),
    ], nm="ice cream", grip_at=(0.0, 12.0))


@prop("cupcake", "Cupcake", "🧁", noun="a cupcake", category="food", tags=("food", "sweet", "birthday"), tint=("gum", "lilac", "mint", "cream"))
def cupcake(x):
    frost = col(x.color or "gum")
    L = x.L

    def items(char, T, n):
        wrapper = Path([(-28, -34), (28, -34), (20, -2), (-20, -2)], closed=True)
        stripes = [sh(Path([(sx, -34), (sx * 0.72, -2)], closed=False)) for sx in (-16, -6, 4, 14)]
        return [
            flame(n, L, at=(0, -100), size=0.9),
            gr("candle", [rc((0, -84), (8, 26), 3), fl(C["sky2"])]),
            gr("sprinkles", [rc((-14, -54), (8, 3), 1.5), rc((10, -62), (8, 3), 1.5), rc((-2, -46), (8, 3), 1.5), fl(C["yellow"])]),
            gr("frosting top", [el((0, -64), (34, 22)), fl(frost)]),
            gr("frosting", [el((0, -46), (64, 30)), fl(frost)]),
            gr("wrapper lines", stripes + [st(C["white"], 2.5, 60)]),
            gr("wrapper", [sh(wrapper), fl(C["teal"])]),
        ]
    return held(x, items, nm="cupcake")


@prop("cookie", "Cookie", "🍪", noun="a cookie", category="food", tags=("food", "sweet"))
def cookie(x):
    pts = []
    for q in range(16):
        a = 2 * math.pi * q / 16
        r = 30 if q not in (2, 3) else 22
        pts.append((r * math.cos(a), -40 + r * math.sin(a)))
    body = smooth(pts, closed=True, tension=0.36)
    chips = [el((cx, cy), (8, 7)) for cx, cy in ((-12, -48), (8, -52), (-4, -34), (14, -36), (-16, -30), (2, -58))]
    return held(x, [
        gr("chips", chips + [fl(C["choco"])]),
        gr("cookie", [sh(body), fl(C["crust"])]),
    ], nm="cookie")


@prop("popcorn", "Popcorn", "🍿", noun="a bucket of popcorn", category="food", tags=("food", "movie"))
def popcorn(x):
    bucket = Path([(-30, -58), (30, -58), (22, 0), (-22, 0)], closed=True)
    stripes = [sh(Path([(-15, -58), (-11, 0)], closed=False)), sh(Path([(0, -58), (0, 0)], closed=False)), sh(Path([(15, -58), (11, 0)], closed=False))]
    puffs = [el((px, py), (18, 16)) for px, py in ((-20, -60), (-6, -66), (8, -64), (22, -60), (-12, -74), (4, -78), (16, -72), (-2, -86))]
    return held(x, [
        gr("puffs", puffs + [fl(C["cream"])]),
        gr("puff shade", [el((px, py + 3), (18, 14)) for px, py in ((-20, -60), (8, -64), (4, -78))] + [fl(C["cheese"], 70)]),
        gr("stripes", stripes + [st(C["white"], 8)]),
        gr("bucket", [sh(bucket), fl(C["tomato"])]),
    ], nm="popcorn")


@prop("apple", "Apple", "🍎", noun="an apple", category="food", tags=("food", "healthy", "school"), tint=("red", "lime", "gold2"))
def apple(x):
    c = col(x.color or "red")
    body = smooth([(0, -54), (14, -62), (30, -54), (32, -26), (16, -6), (0, -10), (-16, -6), (-32, -26), (-30, -54), (-14, -62)], closed=True,
                  tension=0.38, sharp={0: 0.6})
    return held(x, [
        gr("leaf", [el((0, 0), (20, 10)), fl(C["leaf"])], p=(12, -66), r=-30),
        gr("stem", [sh(Path([(0, -54), (4, -70)], closed=False)), st(C["darkbrown"], 4)]),
        gr("shine", [el((-14, -42), (10, 16)), fl(C["white"], 55)], r=20),
        gr("apple", [sh(body), fl(c)]),
    ], nm="apple")


@prop("banana", "Banana", "🍌", noun="a banana", category="food", tags=("food", "monkey"))
def banana(x):
    body = smooth([(-8, -4), (6, -30), (8, -62), (-2, -92), (6, -94), (22, -64), (20, -26), (4, -2)], closed=True, tension=0.36)
    return held(x, [
        gr("tip", [el((2, -94), (8, 6)), fl(C["darkbrown"])]),
        gr("line", [sh(smooth([(2, -12), (14, -40), (12, -72)], closed=False, tension=0.4)), st(C["gold2"], 3)]),
        gr("banana", [sh(body), fl(C["yellow"])]),
        gr("stem", [rc((-2, -4), (10, 10), 3), fl(C["darkbrown"])]),
    ], nm="banana", tilt=18)


@prop("watermelon", "Watermelon", "🍉", noun="a slice of watermelon", category="food", tags=("food", "summer"))
def watermelon(x):
    seeds = [el((sx, sy), (5, 8)) for sx, sy in ((-14, -30), (0, -38), (14, -30), (-6, -52), (6, -52))]
    return held(x, [
        gr("seeds", seeds + [fl(C["black"])]),
        gr("flesh", [sh(Path([(-38, -20), (38, -20), (0, -82)], closed=True)), fl(C["tomato"])]),
        gr("white", [sh(Path([(-42, -16), (42, -16), (0, -86)], closed=True)), fl(C["cream"])]),
        gr("rind", [rc((0, -12), (94, 14), 7), fl(C["leaf"])]),
    ], nm="watermelon")


@prop("sushi", "Sushi", "🍣", noun="a piece of sushi", category="food", tags=("food",))
def sushi(x):
    fish = smooth([(-36, -34), (-20, -46), (20, -48), (38, -38), (34, -28), (-34, -26)], closed=True, tension=0.38)
    return held(x, [
        gr("stripes", [sh(Path([(-14, -44), (-20, -28)], closed=False)), sh(Path([(4, -46), (-2, -28)], closed=False)),
                       sh(Path([(22, -44), (16, -28)], closed=False)), st(C["white"], 3.5, 80)]),
        gr("salmon", [sh(fish), fl(C["orange"])]),
        gr("rice", [rc((0, -16), (66, 26), 12), fl(C["white"])]),
        gr("rice edge", [rc((0, -16), (66, 26), 12), st(C["paper"], 3)]),
    ], nm="sushi")


@prop("lollipop", "Lollipop", "🍭", noun="a lollipop", category="food", tags=("sweet", "candy"), tint=("gum", "teal", "lilac", "yellow"))
def lollipop(x):
    c = col(x.color or "gum")

    def items(char, T, n):
        L = n - 1
        swirl = smooth([(0, -92), (8, -96), (6, -104), (-6, -104), (-14, -94), (-10, -80), (6, -76), (20, -86), (22, -100), (12, -114), (-8, -118),
                        (-26, -106)], closed=False, tension=0.4)
        return [gr("candy", [
            gr("swirl", [sh(swirl), st(C["white"], 6)]),
            gr("disc", [el((0, -96), (60, 60)), fl(c)]),
        ], a=(0, -96), p=(0, -96), r=F(n, lambda f: 360.0 * f / L, tol=1.0)),
            gr("stick", [rc((0, -36), (7, 74), 3), fl(C["paper"])])]
    return held(x, items, nm="lollipop")


@prop("candy_cane", "Candy cane", "🍬", noun="a candy cane", category="food", tags=("christmas", "sweet"))
def candy_cane(x):
    hook = smooth([(0, 0), (0, -70), (8, -92), (22, -96), (32, -84), (30, -72)], closed=False, tension=0.4)
    marks = [gr(f"stripe {q}", [rc((0, 0), (16, 6), 2), fl(C["red"])], p=(0, -10 - 15 * q), r=-30) for q in range(5)]
    return held(x, marks + [
        gr("hook stripes", [sh(smooth([(6, -94), (14, -98)], closed=False)), sh(smooth([(26, -94), (32, -88)], closed=False)), st(C["red"], 9)]),
        gr("cane", [sh(hook), st(C["white"], 14)]),
        gr("cane edge", [sh(hook), st(C["red"], 17, 35)]),
    ], nm="candy cane")


@prop("chocolate", "Chocolate", "🍫", noun="a chocolate bar", category="food", tags=("sweet", "love"))
def chocolate(x):
    grid = [sh(Path([(-20, -90 + 14 * q), (20, -90 + 14 * q)], closed=False)) for q in range(1, 3)] + [sh(Path([(0, -92), (0, -52)], closed=False))]
    return held(x, [
        gr("foil", [sh(Path([(-24, -54), (24, -54), (24, -46), (-24, -46)], closed=True)), fl(C["silver"])]),
        gr("wrapper", [rc((0, -26), (54, 50), 4), fl(C["red"])]),
        gr("band", [rc((0, -26), (54, 12), 0), fl(C["gold2"])]),
        gr("lines", grid + [st(C["darkbrown"], 3)]),
        gr("bar", [rc((0, -62), (46, 66), 4), fl(C["choco"])]),
    ], nm="chocolate")


@prop("taco", "Taco", "🌮", noun="a taco", category="food", tags=("food",))
def taco(x):
    shell = Path([(-40, -14), (40, -14)], i=[(0, 0), (0, -70)], o=[(0, -70), (0, 0)], closed=True)
    frills = smooth([(-34, -46), (-24, -60), (-12, -52), (0, -66), (12, -54), (24, -62), (34, -48), (0, -40)], closed=True, tension=0.38)
    return held(x, [
        gr("tomato", [el((-14, -54), (12, 10)), el((12, -58), (12, 10)), fl(C["tomato"])]),
        gr("lettuce", [sh(frills), fl(C["lettuce"])]),
        gr("meat", [el((0, -44), (64, 22)), fl(C["darkbrown"])]),
        gr("shell", [sh(shell), fl(C["cheese"])]),
    ], nm="taco")


@prop("hotdog", "Hot dog", "🌭", noun="a hot dog", category="food", tags=("food",))
def hotdog(x):
    zig = Path([(-30, -40), (-20, -48), (-10, -40), (0, -48), (10, -40), (20, -48), (30, -40)], closed=False)
    return held(x, [
        gr("mustard", [sh(zig), st(C["yellow"], 5)]),
        gr("sausage", [rc((0, -44), (96, 22), 11), fl(C["tomato"])]),
        gr("bun", [rc((0, -32), (84, 30), 15), fl(C["crust"])]),
    ], nm="hot dog")


@prop("carrot", "Carrot", "🥕", noun="a carrot", category="food", tags=("bunny", "healthy"))
def carrot(x):
    body = smooth([(-14, -76), (14, -76), (4, -6), (0, 0), (-4, -6)], closed=True, tension=0.3, sharp={3: 0.8})
    lines = [sh(Path([(-8, -56), (0, -54)], closed=False)), sh(Path([(2, -40), (8, -42)], closed=False)), sh(Path([(-6, -24), (0, -22)], closed=False))]
    leaves = [gr(f"leaf {q}", [el((0, -12), (10, 26)), fl(C["leaf"])], p=(0, -76), r=a) for q, a in enumerate((-28, 0, 26))]
    return held(x, leaves + [gr("lines", lines + [st(C["crust"], 3)]), gr("carrot", [sh(body), fl(C["orange"])])], nm="carrot", tilt=16)


@prop("fish", "Fish", "🐟", noun="a fish", category="food", tags=("cat", "food"))
def fish(x):
    body = smooth([(-44, -40), (-20, -56), (14, -54), (32, -40), (14, -26), (-20, -24)], closed=True, tension=0.4)
    tail = Path([(30, -40), (54, -56), (50, -40), (54, -24)], closed=True)
    return held(x, [
        gr("eye", [el((-28, -44), (8, 8)), fl(C["black"])]),
        gr("fin", [sh(Path([(-4, -54), (8, -66), (12, -52)], closed=True)), fl(C["blue"])]),
        gr("shine", [el((-6, -48), (24, 7)), fl(C["white"], 45)]),
        gr("body", [sh(body), fl(C["sky2"])]),
        gr("tail", [sh(tail), fl(C["blue"])]),
    ], nm="fish")


@prop("bone", "Bone", "🦴", noun="a bone", category="food", tags=("dog",))
def bone(x):
    ends = [el((ex, ey), (26, 26)) for ex, ey in ((-34, -50), (-34, -32), (34, -50), (34, -32))]
    return held(x, [gr("bone", ends + [rc((0, -41), (70, 22), 8), fl(C["paper"])]),
                    gr("edge", [el((ex, ey), (26, 26)) for ex, ey in ((-34, -50), (-34, -32), (34, -50), (34, -32))] + [st(C["sand"], 5)])],
                nm="bone", tilt=-20)


@prop("cheese", "Cheese", "🧀", noun="a wedge of cheese", category="food", tags=("mouse", "food"))
def cheese(x):
    wedge = Path([(-40, -14), (40, -14), (40, -52), (-28, -78)], closed=True)
    top = Path([(-40, -14), (-28, -78), (-40, -60)], closed=True)
    holes = [el((-6, -38), (16, 14)), el((22, -28), (12, 10)), el((18, -54), (10, 9)), el((-24, -24), (9, 8))]
    return held(x, [
        gr("holes", holes + [fl(C["gold2"])]),
        gr("side", [sh(top), fl(C["gold2"])]),
        gr("wedge", [sh(wedge), fl(C["cheese"])]),
        gr("edge", [sh(wedge), st(C["darkgold"], 3, 60)]),
    ], nm="cheese")


@prop("bamboo", "Bamboo", "🎋", noun="a bamboo stalk", category="food", tags=("panda",))
def bamboo(x):
    joints = [rc((0, -18 - 34 * q), (26, 6), 3) for q in range(4)]
    return held(x, [
        gr("leaf", [el((0, 0), (18, 52)), fl(C["leaf"])], p=(22, -114), r=40),
        gr("joints", joints + [fl(C["darkgreen"])]),
        gr("stalk", [rc((0, -64), (20, 136), 8), fl(C["lettuce"])]),
    ], nm="bamboo", tilt=8)


@prop("honey", "Honey pot", "🍯", noun="a pot of honey", category="food", tags=("bear", "sweet"))
def honey(x):
    pot = smooth([(-26, -54), (26, -54), (34, -30), (26, -4), (-26, -4), (-34, -30)], closed=True, tension=0.4)
    drip = smooth([(-22, -58), (22, -58), (20, -48), (8, -40), (4, -48), (-8, -42), (-18, -50)], closed=True, tension=0.38)
    return held(x, [
        gr("dipper", [rc((18, -78), (8, 40), 3), el((18, -96), (16, 12)), fl(C["wood"])], r=20, a=(18, -60), p=(18, -60)),
        gr("drip", [sh(drip), fl(C["gold"])]),
        gr("lid rim", [rc((0, -58), (60, 10), 5), fl(C["gold2"])]),
        gr("label", [rc((0, -30), (36, 18), 4), fl(C["paper"])]),
        gr("pot", [sh(pot), fl(C["gold2"])]),
    ], nm="honey")


# ------------------------------------------------------------------ the birthday cake: carried on both paws
@prop("cake", "Birthday cake", "🎂", noun="a birthday cake", paw="LR", pose="present", flexible=False, category="food",
      tags=("birthday", "celebrate"), tint=("gum", "lilac", "mint", "teal"), cost=1.2)
def cake(x):
    L = x.L
    icing = col(x.color or "gum")

    def spec(char, T, n):
        cx, base = 256.0, 386.0
        drips = smooth([(cx - 66, base - 64), (cx + 66, base - 64), (cx + 66, base - 50), (cx + 50, base - 44), (cx + 38, base - 54), (cx + 20, base - 40),
                        (cx + 6, base - 52), (cx - 12, base - 42), (cx - 28, base - 54), (cx - 44, base - 42), (cx - 58, base - 52), (cx - 66, base - 48)],
                       closed=True, tension=0.34)
        items = []
        for q, dx in enumerate((-30, 0, 30)):
            items.append(flame(n, L, at=(cx + dx, base - 100), size=0.9, nm=f"flame {q}"))
        items += [
            gr("candles", [rc((cx + dx, base - 80), (9, 24), 3) for dx in (-30, 0, 30)] + [fl(C["sky2"])]),
            gr("dots", [el((cx + dx, base - 26), (8, 8)) for dx in (-44, -22, 0, 22, 44)] + [fl(C["yellow"])]),
            gr("icing", [sh(drips), fl(icing)]),
            gr("top", [el((cx, base - 66), (134, 22)), fl(icing)]),
            gr("cake", [rc((cx, base - 34), (132, 64), 8), fl(C["paper"])]),
            gr("plate", [el((cx, base + 2), (176, 20)), fl(C["silver"])]),
        ]
        return [("front", Layer("cake", items, parent="body"))]
    return spec


# ------------------------------------------------------------------ drinks
@prop("boba", "Bubble tea", "🧋", noun="a bubble tea", category="drink", tags=("drink", "sweet"))
def boba(x):
    cup = Path([(-26, -76), (26, -76), (20, -2), (-20, -2)], closed=True)
    tea = Path([(-25, -60), (25, -60), (20, -2), (-20, -2)], closed=True)
    pearls = [el((px, py), (10, 10)) for px, py in ((-12, -10), (0, -12), (12, -10), (-6, -20), (6, -21), (-14, -26), (14, -24))]
    return held(x, [
        gr("straw", [rc((8, -100), (10, 64), 4), fl(C["gum"])], a=(8, -76), p=(8, -76), r=12),
        gr("lid", [el((0, -78), (58, 14)), fl(C["white"], 90)]),
        gr("cup shine", [rc((-14, -40), (5, 46), 2.5), fl(C["white"], 50)]),
        gr("pearls", pearls + [fl(C["choco"])]),
        gr("tea", [sh(tea), fl(C["tan"])]),
        gr("cup", [sh(cup), fl(C["ice"], 85)]),
    ], nm="boba")


@prop("soda", "Soda", "🥤", noun="a soda", category="drink", tags=("drink", "movie"), tint=("tomato", "teal", "blue", "lilac"))
def soda(x):
    c = col(x.color or "tomato")
    cup = Path([(-26, -76), (26, -76), (20, -2), (-20, -2)], closed=True)
    return held(x, [
        gr("straw", [rc((6, -96), (8, 44), 3), fl(C["white"])], a=(6, -78), p=(6, -78), r=14),
        gr("lid", [rc((0, -78), (60, 10), 5), fl(C["white"])]),
        gr("stripe", [sh(Path([(-23, -44), (23, -44), (22, -34), (-22, -34)], closed=True)), fl(C["white"])]),
        gr("cup", [sh(cup), fl(c)]),
    ], nm="soda")


@prop("glass", "Glass", "🥂", noun="a glass of something bubbly", category="drink", tags=("cheers", "celebrate"))
def glass(x):
    def items(char, T, n):
        L = n - 1
        per = L / max(1, round(L / 40.0))
        bubbles = []
        for q, bx in enumerate((-5, 3, -1)):
            u = lambda f, q=q: ((f / per) + q / 3.0) % 1.0
            bubbles.append(gr(f"bubble {q}", [el((0, 0), (5, 5)), fl(C["white"], 90)],
                              p=F(n, lambda f, u=u, bx=bx: (bx, -40 - 34 * u(f)), tol=0.5), o=F(n, lambda f, u=u: 100 * min(1.0, (1 - u(f)) * 4), tol=3.0)))
        bowl = Path([(-16, -84), (16, -84), (10, -40), (-10, -40)], closed=True)
        drink = Path([(-14, -72), (14, -72), (10, -42), (-10, -42)], closed=True)
        return bubbles + [
            gr("drink", [sh(drink), fl(C["gold"])]),
            gr("glass", [sh(bowl), fl(C["ice"], 60)]),
            gr("glass edge", [sh(bowl), st(C["white"], 3)]),
            gr("stem", [rc((0, -22), (5, 36), 2), fl(C["ice"])]),
            gr("foot", [el((0, -4), (30, 7)), fl(C["ice"])]),
        ]
    return held(x, items, nm="glass", pose="hold")


@prop("water_bottle", "Water bottle", "🧴", noun="a water bottle", category="drink", tags=("gym", "hot"), tint=("sky2", "teal", "lime", "gum"))
def water_bottle(x):
    c = col(x.color or "sky2")
    return held(x, [
        gr("cap", [rc((0, -96), (24, 14), 4), fl(C["steel"])]),
        gr("shine", [rc((-9, -52), (5, 52), 2.5), fl(C["white"], 55)]),
        gr("label", [rc((0, -46), (34, 20), 3), fl(C["white"], 85)]),
        gr("bottle", [rc((0, -48), (36, 88), 12), fl(c)]),
    ], nm="water bottle")


@prop("takeaway", "Coffee to go", "☕", noun="a coffee to go", category="drink", tags=("coffee", "work", "morning"))
def takeaway(x):
    cup = Path([(-24, -74), (24, -74), (18, -2), (-18, -2)], closed=True)
    return held(x, [
        gr("lid", [rc((0, -80), (58, 12), 5), rc((0, -88), (40, 8), 4), fl(C["white"])]),
        gr("heart", [sh(heart_path(9, 0, -40)), fl(C["white"])]),
        gr("sleeve", [sh(Path([(-23, -52), (23, -52), (21, -28), (-21, -28)], closed=True)), fl(C["tan"])]),
        gr("cup", [sh(cup), fl(C["paper"])]),
    ], nm="coffee to go")
