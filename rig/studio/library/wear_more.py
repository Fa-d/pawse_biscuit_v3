"""More things to wear: hats for every occasion, glasses and masks, things for the nose, mouth and neck, capes,
wings and backpacks, aprons, sweaters and a tutu.

Head items are drawn in the head drawing's coordinates from the mascot's own data (crown, eyes, ears, nose,
mouth), so they sit right on every mascot and follow every head turn.  Body items ride on the body.  Animated
items (a propeller, a halo, a cape) loop with periods that divide the loop.
"""
from __future__ import annotations

from ..registry import wear
from .common import C, F, Layer, Path, col, el, fl, gr, heart_path, math, rc, sh, smooth, st, star4, star5
from .wear_core import eyes_of, on_body, on_head


def _eye_top(ch):
    """Top of the eyes in the head drawing (a frog's eyes sit up on top of its head)."""
    l, r, w, h = eyes_of(ch)
    return r[1] - h / 2.0


def on_head_anim(name, items, slot="front"):
    """Like on_head, for drawings that move: items(char, T, n)."""
    def spec(char, T, n):
        return [(slot, Layer(f"wear {name}", items(char, T, n), parent="neck"))]
    return spec


def on_body_anim(name, items, slot="mid", parent="body"):
    def spec(char, T, n):
        return [(slot, Layer(f"wear {name}", items(char, T, n), parent=parent))]
    return spec


def cone(cx, y, w, h, tip_dx=0.0, droop=0.0):
    """A soft cone standing on (cx, y), w wide, h tall; the tip leans by tip_dx and droops by droop."""
    tip = (cx + tip_dx, y - h + droop)
    return smooth([(cx - w / 2, y), (cx - w * 0.28 + tip_dx * 0.4, y - h * 0.55), tip, (cx + w * 0.3 + tip_dx * 0.5, y - h * 0.5), (cx + w / 2, y)],
                  closed=True, tension=0.32, sharp={0: 0.4, 2: 0.7, 4: 0.4})


# ------------------------------------------------------------------ hats
@wear("santa_hat", "Santa hat", "🎅", zone="hat", noun="a Santa hat", tags=("christmas", "winter"))
def santa_hat(x):
    def items(ch):
        cx, y = ch.crown
        y += 14
        body = cone(cx, y, 134, 120, tip_dx=70, droop=50)
        return [gr("santa hat", [
            gr("pompom", [el((cx + 72, y - 68), (34, 34)), fl(C["white"])]),
            gr("trim", [rc((cx, y), (148, 30), 15), fl(C["white"])]),
            gr("shade", [sh(cone(cx + 22, y, 90, 96, tip_dx=58, droop=46)), fl(C["darkred"], 30)]),
            gr("hat", [sh(body), fl(C["red"])]),
        ], a=(cx, y), p=(cx, y), r=-6)]
    return on_head("santa hat", items)


@wear("witch_hat", "Witch hat", "🧙‍♀️", zone="hat", noun="a witch hat", tags=("halloween", "magic"), tint=("violet", "night", "black"))
def witch_hat(x):
    c = col(x.color or "violet")

    def items(ch):
        cx, y = ch.crown
        y += 12
        return [gr("witch hat", [
            gr("buckle", [rc((cx, y - 14), (20, 16), 3), st(C["gold"], 4)]),
            gr("band", [rc((cx, y - 14), (92, 16), 4), fl(C["lime"])]),
            gr("cone", [sh(cone(cx, y - 6, 96, 150, tip_dx=-34, droop=24)), fl(c)]),
            gr("brim", [el((cx, y - 4), (196, 34)), fl(c)]),
            gr("brim shade", [el((cx, y), (196, 34)), fl(C["black"], 35)]),
        ], a=(cx, y), p=(cx, y), r=8)]
    return on_head("witch hat", items)


@wear("wizard_hat", "Wizard hat", "🧙", zone="hat", noun="a wizard hat", tags=("magic", "wizard"), tint=("navy", "violet", "teal"))
def wizard_hat(x):
    c = col(x.color or "navy")

    def items(ch):
        cx, y = ch.crown
        y += 12
        return [gr("wizard hat", [
            gr("stars", [sh(star5((cx - 18, y - 46), 10)), sh(star5((cx + 16, y - 80), 8)), sh(star5((cx - 4, y - 110), 7)), fl(C["yellow"])]),
            gr("moon", [sh(smooth([(cx + 22, y - 30), (cx + 8, y - 36), (cx + 4, y - 50), (cx + 14, y - 62), (cx + 8, y - 48), (cx + 12, y - 38)],
                                  closed=True, tension=0.4)), fl(C["yellow"])]),
            gr("cone", [sh(cone(cx, y, 120, 168, tip_dx=30, droop=10)), fl(c)]),
            gr("brim", [el((cx, y), (160, 26)), fl(c)]),
        ], a=(cx, y), p=(cx, y), r=-4)]
    return on_head("wizard hat", items)


@wear("cowboy_hat", "Cowboy hat", "🤠", zone="hat", noun="a cowboy hat", tags=("western", "cool"))
def cowboy_hat(x):
    def items(ch):
        cx, y = ch.crown
        y += 16
        crown_ = smooth([(cx - 50, y - 6), (cx - 46, y - 52), (cx - 18, y - 66), (cx, y - 54), (cx + 18, y - 66), (cx + 46, y - 52), (cx + 50, y - 6)],
                        closed=True, tension=0.34, sharp={0: 0.4, 6: 0.4})
        brim = smooth([(cx - 120, y - 30), (cx - 70, y + 4), (cx, y + 10), (cx + 70, y + 4), (cx + 120, y - 30), (cx + 80, y - 6), (cx, y - 2),
                       (cx - 80, y - 6)], closed=True, tension=0.36, sharp={0: 0.6, 4: 0.6})
        return [gr("cowboy hat", [
            gr("band", [rc((cx, y - 14), (100, 12), 3), fl(C["darkbrown"])]),
            gr("crown", [sh(crown_), fl(C["brown"])]),
            gr("brim", [sh(brim), fl(C["brown"])]),
        ], a=(cx, y), p=(cx, y), r=-5)]
    return on_head("cowboy hat", items)


@wear("top_hat", "Top hat", "🎩", zone="hat", noun="a top hat", tags=("fancy", "magic", "classy"))
def top_hat(x):
    def items(ch):
        cx, y = ch.crown
        y += 14
        return [gr("top hat", [
            gr("shine", [rc((cx - 26, y - 62), (8, 70), 4), fl(C["white"], 25)]),
            gr("band", [rc((cx, y - 18), (84, 16), 2), fl(C["red"])]),
            gr("crown", [rc((cx, y - 54), (84, 100), 6), fl(C["black"])]),
            gr("brim", [rc((cx, y), (138, 16), 8), fl(C["black"])]),
        ], a=(cx, y), p=(cx, y), r=-7)]
    return on_head("top hat", items)


@wear("cap", "Cap", "🧢", zone="hat", noun="a cap", tags=("sport", "casual", "cool"), tint=("blue", "red", "teal", "black"))
def cap(x):
    c = col(x.color or "blue")

    def items(ch):
        cx, y = ch.crown
        y += 22
        dome = smooth([(cx - 78, y), (cx - 70, y - 40), (cx, y - 66), (cx + 70, y - 40), (cx + 78, y)], closed=True, tension=0.38, sharp={0: 0.5, 4: 0.5})
        return [gr("cap", [
            gr("button", [el((cx, y - 66), (14, 10)), fl(c)]),
            gr("seams", [sh(smooth([(cx, y - 64), (cx - 6, y - 30), (cx, y)], closed=False, tension=0.4)), st(C["black"], 2.5, 30)]),
            gr("logo", [sh(star5((cx + 30, y - 30), 12)), fl(C["white"])]),
            gr("dome", [sh(dome), fl(c)]),
            gr("visor", [sh(smooth([(cx - 70, y - 4), (cx, y + 14), (cx + 70, y - 4), (cx, y + 4)], closed=True, tension=0.36)), fl(C["black"], 75)]),
        ])]
    return on_head("cap", items)


@wear("beanie", "Beanie", "🧶", zone="hat", noun="a beanie", tags=("winter", "cold", "cozy"), tint=("teal", "coral", "lilac", "yellow"))
def beanie(x):
    c = col(x.color or "teal")

    def items(ch):
        cx, y = ch.crown
        y += 26
        dome = smooth([(cx - 86, y - 10), (cx - 76, y - 56), (cx, y - 86), (cx + 76, y - 56), (cx + 86, y - 10)], closed=True, tension=0.38,
                      sharp={0: 0.5, 4: 0.5})
        ribs = [sh(Path([(cx + dx, y - 22), (cx + dx, y + 2)], closed=False)) for dx in range(-70, 80, 14)]
        return [gr("beanie", [
            gr("pompom", [el((cx, y - 92), (40, 38)), fl(C["white"])]),
            gr("ribs", ribs + [st(C["dark"], 2.5, 20)]),
            gr("band", [rc((cx, y - 10), (176, 26), 12), fl(c)]),
            gr("dome", [sh(dome), fl(c)]),
            gr("knit", [sh(smooth([(cx - 50, y - 50), (cx, y - 64), (cx + 50, y - 50)], closed=False, tension=0.4)), st(C["white"], 5, 50)]),
        ])]
    return on_head("beanie", items)


@wear("chef_hat", "Chef hat", "👨‍🍳", zone="hat", noun="a chef's hat", tags=("cooking", "food", "chef"))
def chef_hat(x):
    def items(ch):
        cx, y = ch.crown
        y += 14
        puffs = [el((cx + dx, y - dy), (d, d)) for dx, dy, d in ((-38, 70, 64), (0, 88, 72), (38, 70, 64), (-20, 54, 60), (20, 54, 60))]
        return [gr("chef hat", [
            gr("fold", [sh(Path([(cx - 20, y - 50), (cx - 16, y - 20)], closed=False)), sh(Path([(cx + 18, y - 50), (cx + 14, y - 20)], closed=False)),
                        st(C["ice"], 3)]),
            gr("puffs", puffs + [fl(C["white"])]),
            gr("puff edge", [el((cx + dx, y - dy), (d, d)) for dx, dy, d in ((-38, 70, 64), (0, 88, 72), (38, 70, 64))] + [st(C["ice"], 3)]),
            gr("band", [rc((cx, y - 14), (110, 34), 6), fl(C["white"])]),
            gr("band edge", [rc((cx, y - 14), (110, 34), 6), st(C["ice"], 3)]),
        ])]
    return on_head("chef hat", items)


@wear("grad_cap", "Graduation cap", "🎓", zone="hat", noun="a graduation cap", tags=("graduation", "school", "smart"))
def grad_cap(x):
    L = x.L

    def items(ch, T, n):
        cx, y = ch.crown
        y += 8
        per = L / max(1, round(L / 60.0))
        board = Path([(cx, y - 52), (cx + 96, y - 30), (cx, y - 8), (cx - 96, y - 30)], closed=True)
        tassel = gr("tassel", [rc((cx + 56, y - 4), (5, 40), 2), el((cx + 56, y + 18), (14, 14)), fl(C["gold"])], a=(cx + 56, y - 24), p=(cx + 56, y - 24),
                    r=F(n, lambda f: 10 * math.sin(2 * math.pi * f / per), tol=1.0))
        return [gr("grad cap", [
            tassel,
            gr("cord", [sh(Path([(cx, y - 30), (cx + 56, y - 24)], closed=False)), st(C["gold"], 3)]),
            gr("button", [el((cx, y - 30), (10, 6)), fl(C["gold"])]),
            gr("board", [sh(board), fl(C["black"])]),
            gr("skull cap", [rc((cx, y - 4), (110, 34), 12), fl(C["ink"])]),
        ])]
    return on_head_anim("grad cap", items)


@wear("pirate_hat", "Pirate hat", "🏴‍☠️", zone="hat", noun="a pirate hat", tags=("pirate", "adventure"))
def pirate_hat(x):
    def items(ch):
        cx, y = ch.crown
        y += 16
        hat = smooth([(cx - 110, y - 20), (cx - 60, y - 40), (cx - 30, y - 80), (cx, y - 70), (cx + 30, y - 80), (cx + 60, y - 40), (cx + 110, y - 20),
                      (cx + 40, y), (cx - 40, y)], closed=True, tension=0.34, sharp={0: 0.8, 6: 0.8})
        return [gr("pirate hat", [
            gr("bones", [sh(Path([(cx - 14, y - 20), (cx + 14, y - 40)], closed=False)), sh(Path([(cx - 14, y - 40), (cx + 14, y - 20)], closed=False)),
                         st(C["white"], 5)]),
            gr("skull", [el((cx, y - 48), (22, 20)), fl(C["white"])]),
            gr("trim", [sh(hat), st(C["gold"], 5)]),
            gr("hat", [sh(hat), fl(C["black"])]),
        ])]
    return on_head("pirate hat", items)


@wear("flower_crown", "Flower crown", "🌸", zone="hat", noun="a flower crown", tags=("spring", "pretty", "festival"))
def flower_crown(x):
    def items(ch):
        cx, y = ch.crown
        y += 26
        flowers = ((-72, "rose"), (-38, "yellow"), (0, "pink"), (38, "lilac"), (72, "rose"))
        if y > _eye_top(ch) - 12:          # the eyes sit up on top of the head (a frog): a little crown between them
            y = ch.crown[1] + 10
            flowers = ((-28, "rose"), (0, "yellow"), (28, "lilac"))
        out = []
        for q, (dx, c) in enumerate(flowers):
            fx, fy = cx + dx, y - 8 + 0.004 * dx * dx
            petals = [el((fx + 9 * math.cos(a), fy + 9 * math.sin(a)), (13, 13)) for a in (k * 2 * math.pi / 5 for k in range(5))]
            out.append(gr(f"flower {q}", [gr("centre", [el((fx, fy), (9, 9)), fl(C["gold2"])]), gr("petals", petals + [fl(C[c])])]))
        spots = (-55, -20, 20, 55) if len(flowers) > 3 else (-14, 14)
        leaves = [gr("leaf", [el((0, 0), (10, 22)), fl(C["leaf"])], p=(cx + dx, y + 2 + 0.004 * dx * dx), r=dx) for dx in spots]
        return out + leaves
    return on_head("flower crown", items)


@wear("halo", "Halo", "😇", zone="hat", noun="a halo", tags=("angel", "innocent", "good"))
def halo(x):
    L = x.L

    def items(ch, T, n):
        cx, y = ch.crown
        y = min(y, (ch.top or ch.crown)[1] + 4) - 30      # clear a mane
        per = L / max(1, round(L / 60.0))
        return [gr("halo", [gr("ring", [el((cx, y), (130, 30)), st(C["gold"], 10)]), gr("glow", [el((cx, y), (150, 46)), st(C["yellow"], 6, 40)])],
                   a=(cx, y), p=F(n, lambda f: (cx, y - 5 * math.sin(2 * math.pi * f / per)), tol=0.5))]
    return on_head_anim("halo", items)


@wear("devil_horns", "Devil horns", "😈", zone="hat", noun="devil horns", tags=("evil", "mischief", "halloween"))
def devil_horns(x):
    def items(ch):
        cx, y = ch.crown
        horn = lambda k: smooth([(cx + k * 26, y + 18), (cx + k * 44, y - 8), (cx + k * 50, y - 36), (cx + k * 60, y + 6), (cx + k * 52, y + 22)],
                               closed=True, tension=0.36, sharp={2: 0.9})
        return [gr("horns", [sh(horn(1)), sh(horn(-1)), fl(C["red"])]), gr("horn edge", [sh(horn(1)), sh(horn(-1)), st(C["darkred"], 3)])]
    return on_head("devil horns", items)


@wear("bunny_ears", "Bunny ears", "🐰", zone="hat", noun="bunny ears", tags=("easter", "cute", "costume"))
def bunny_ears(x):
    def items(ch):
        cx, y = ch.crown
        y += 20
        ear = lambda k: gr(f"ear {k}", [
            gr("inner", [el((0, -50), (18, 66)), fl(C["rose"])]),
            gr("ear", [el((0, -52), (34, 96)), fl(C["white"])]),
            gr("edge", [el((0, -52), (34, 96)), st(C["ice"], 3)]),
        ], p=(cx + k * 30, y - 4), r=k * 14)
        return [ear(1), ear(-1), gr("band", [sh(smooth([(cx - 90, y + 10), (cx, y - 14), (cx + 90, y + 10)], closed=False, tension=0.4)), st(C["gum"], 9)])]
    return on_head("bunny ears", items)


@wear("unicorn_horn", "Unicorn horn", "🦄", zone="hat", noun="a unicorn horn", tags=("magic", "unicorn", "cute"))
def unicorn_horn(x):
    def items(ch):
        cx, y = ch.crown
        y += 22
        horn = Path([(cx - 18, y), (cx + 18, y), (cx + 4, y - 96)], closed=True)
        rings = [sh(Path([(cx - 15 + 3 * q, y - 18 - 22 * q), (cx + 15 - 3 * q, y - 10 - 22 * q)], closed=False)) for q in range(3)]
        return [gr("unicorn horn", [gr("rings", rings + [st(C["darkgold"], 3)]), gr("horn", [sh(horn), fl(C["gold"])]),
                                    gr("flowers", [el((cx - 30, y + 4), (18, 18)), el((cx + 30, y + 4), (18, 18)), fl(C["rose"])])])]
    return on_head("unicorn horn", items)


@wear("hard_hat", "Hard hat", "👷", zone="hat", noun="a hard hat", tags=("work", "building", "safety"))
def hard_hat(x):
    def items(ch):
        cx, y = ch.crown
        y += 22
        dome = smooth([(cx - 82, y), (cx - 72, y - 46), (cx, y - 74), (cx + 72, y - 46), (cx + 82, y)], closed=True, tension=0.38, sharp={0: 0.5, 4: 0.5})
        return [gr("hard hat", [gr("ridge", [rc((cx, y - 40), (18, 66), 8), fl(C["gold2"])]), gr("dome", [sh(dome), fl(C["yellow"])]),
                                gr("brim", [rc((cx, y), (186, 16), 8), fl(C["gold2"])])])]
    return on_head("hard hat", items)


@wear("beret", "Beret", "🎨", zone="hat", noun="a beret", tags=("art", "french", "artist"), tint=("red", "black", "navy"))
def beret(x):
    c = col(x.color or "red")

    def items(ch):
        cx, y = ch.crown
        y += 18
        return [gr("beret", [gr("stalk", [rc((cx + 10, y - 40), (6, 12), 2), fl(c)]),
                             gr("shade", [el((cx + 14, y - 4), (146, 26)), fl(C["black"], 18)]),
                             gr("beret", [el((cx + 14, y - 16), (156, 52)), fl(c)])], a=(cx, y), p=(cx, y), r=-12)]
    return on_head("beret", items)


@wear("sun_hat", "Sun hat", "👒", zone="hat", noun="a sun hat", tags=("summer", "beach", "garden"))
def sun_hat(x):
    def items(ch):
        cx, y = ch.crown
        y += 18
        return [gr("sun hat", [
            gr("flower", [el((cx + 44, y - 18), (22, 22)), fl(C["rose"])]),
            gr("ribbon", [rc((cx, y - 18), (98, 14), 4), fl(C["rose"])]),
            gr("crown", [el((cx, y - 34), (100, 64)), fl(C["sand"])]),
            gr("brim", [el((cx, y - 4), (230, 46)), fl(C["sand"])]),
            gr("weave", [el((cx, y - 4), (196, 30)), st(C["tan"], 3, 60)]),
        ], a=(cx, y), p=(cx, y), r=-6)]
    return on_head("sun hat", items)


@wear("headband", "Sweatband", "🏃", zone="hat", noun="a sweatband", tags=("gym", "sport", "workout"), tint=("red", "teal", "yellow"))
def headband(x):
    c = col(x.color or "red")

    def items(ch):
        cx, y = ch.crown
        l, r, w, h = eyes_of(ch)
        by, half = (y + l[1]) / 2.0 - 6, 120
        if by > _eye_top(ch) - 14:         # eyes on top of the head: the band goes over them
            by, half = _eye_top(ch) - 14, 100
        band = smooth([(cx - half, by + 10), (cx, by - 8), (cx + half, by + 10)], closed=False, tension=0.4)
        return [gr("stripe", [sh(band), st(C["white"], 6)]), gr("band", [sh(band), st(c, 24)])]
    return on_head("headband", items)


@wear("propeller_cap", "Propeller cap", "🌀", zone="hat", noun="a propeller cap", tags=("silly", "fun", "kid"))
def propeller_cap(x):
    L = x.L

    def items(ch, T, n):
        cx, y = ch.crown
        y += 22
        per = L / max(1, round(L / 12.0))
        spin = F(n, lambda f: (100 * math.cos(2 * math.pi * f / per), 100), tol=4.0)
        dome = smooth([(cx - 76, y), (cx - 66, y - 40), (cx, y - 62), (cx + 66, y - 40), (cx + 76, y)], closed=True, tension=0.38, sharp={0: 0.5, 4: 0.5})
        segs = [gr("seg", [sh(smooth([(cx, y - 62), (cx + k * 30, y - 46), (cx + k * 60, y - 20), (cx + k * 74, y), (cx + k * 40, y), (cx + k * 12, y - 30)],
                                      closed=True, tension=0.3)), fl(C[c])]) for k, c in ((-1, "coral"), (1, "teal"))]
        return [gr("propeller cap", [
            gr("propeller", [el((cx - 30, y - 74), (60, 12)), el((cx + 30, y - 74), (60, 12)), fl(C["yellow"])], a=(cx, y - 74), p=(cx, y - 74), s=spin),
            gr("stick", [rc((cx, y - 68), (6, 14), 2), fl(C["dark"])]),
        ] + segs + [gr("dome", [sh(dome), fl(C["yellow"])]), gr("visor", [el((cx, y + 2), (140, 18)), fl(C["blue"])])])]
    return on_head_anim("propeller cap", items)


@wear("nightcap", "Nightcap", "🛌", zone="hat", noun="a nightcap", tags=("sleep", "bedtime", "night"), tint=("sky2", "lilac", "mint"))
def nightcap(x):
    c = col(x.color or "sky2")

    def items(ch):
        cx, y = ch.crown
        y += 16
        body = cone(cx, y, 140, 130, tip_dx=-96, droop=96)
        return [gr("nightcap", [
            gr("pompom", [el((cx - 98, y - 26), (30, 30)), fl(C["white"])]),
            gr("stars", [sh(star5((cx + 10, y - 40), 9)), sh(star5((cx - 36, y - 60), 7)), fl(C["white"], 90)]),
            gr("band", [rc((cx, y), (150, 24), 12), fl(C["white"])]),
            gr("cap", [sh(body), fl(c)]),
        ], a=(cx, y), p=(cx, y), r=6)]
    return on_head("nightcap", items)


@wear("viking_helmet", "Viking helmet", "⚔️", zone="hat", noun="a viking helmet", tags=("brave", "warrior", "strong"))
def viking_helmet(x):
    def items(ch):
        cx, y = ch.crown
        y += 22
        dome = smooth([(cx - 80, y), (cx - 70, y - 44), (cx, y - 70), (cx + 70, y - 44), (cx + 80, y)], closed=True, tension=0.38, sharp={0: 0.5, 4: 0.5})
        horn = lambda k: smooth([(cx + k * 64, y - 26), (cx + k * 104, y - 50), (cx + k * 116, y - 96), (cx + k * 92, y - 56), (cx + k * 70, y - 40)],
                               closed=True, tension=0.36, sharp={2: 0.9})
        return [gr("viking helmet", [
            gr("rivets", [el((cx + dx, y - 6), (8, 8)) for dx in (-56, -28, 0, 28, 56)] + [fl(C["silver"])]),
            gr("band", [rc((cx, y - 6), (164, 18), 6), fl(C["gold2"])]),
            gr("dome", [sh(dome), fl(C["steel"])]),
            gr("horns", [sh(horn(1)), sh(horn(-1)), fl(C["cream"])]),
        ])]
    return on_head("viking helmet", items)


@wear("tiara", "Tiara", "👸", zone="hat", noun="a tiara", tags=("princess", "pretty", "queen"))
def tiara(x):
    def items(ch):
        cx, y = ch.crown
        y += 18
        pts = [(cx - 60, y), (cx - 40, y - 18), (cx - 20, y - 12), (cx, y - 38), (cx + 20, y - 12), (cx + 40, y - 18), (cx + 60, y), (cx, y - 6)]
        return [gr("tiara", [gr("gems", [el((cx, y - 26), (12, 12)), el((cx - 40, y - 12), (8, 8)), el((cx + 40, y - 12), (8, 8)), fl(C["rose"])]),
                             gr("band", [sh(Path(pts, closed=True)), fl(C["silver"])]), gr("edge", [sh(Path(pts, closed=True)), st(C["steel"], 3)])])]
    return on_head("tiara", items)


# ------------------------------------------------------------------ ears
@wear("earmuffs", "Earmuffs", "🎧", zone="ears", noun="earmuffs", tags=("winter", "cold"), tint=("gum", "teal", "lilac", "white"))
def earmuffs(x):
    c = col(x.color or "gum")

    def items(ch):
        l, r, w, h = eyes_of(ch)
        cy = l[1] - 10
        half = (r[0] - l[0]) / 2 + 92
        cx = ch.CX
        top = ch.crown[1] - 10
        band = Path([(cx - half, cy - 10), (cx, top), (cx + half, cy - 10)], i=[(0, 0), (-half * 0.6, 0), (0, -half * 0.5)],
                    o=[(0, -half * 0.5), (half * 0.6, 0), (0, 0)], closed=False)
        fluff = lambda px: [el((px + 14 * math.cos(a), cy + 14 * math.sin(a)), (30, 30)) for a in (k * math.pi / 3 for k in range(6))] + [el((px, cy), (46, 50))]
        return [gr("earmuffs", [gr("muffs", fluff(cx - half) + fluff(cx + half) + [fl(c)]), gr("band", [sh(band), st(C["silver"], 8)])])]
    return on_head("earmuffs", items)


# ------------------------------------------------------------------ eyes
def _lenses(ch, shape_fn, fill, edge, glare=True):
    l, r, w, h = eyes_of(ch)
    out = [gr("bridge", [sh(Path([(l[0] + w * 0.6, l[1] - 6), (r[0] - w * 0.6, r[1] - 6)], closed=False)), st(edge, 6)])]
    if glare:
        out.append(gr("glare", [sh(Path([(c[0] - w * 0.3, c[1] - h * 0.1), (c[0] - w * 0.05, c[1] - h * 0.32)], closed=False)) for c in (l, r)]
                      + [st(C["white"], 5, 70)]))
    out += [gr("lenses", [sh(shape_fn(c, w)) for c in (l, r)] + [fl(fill)]), gr("frames", [sh(shape_fn(c, w)) for c in (l, r)] + [st(edge, 6)])]
    return out


@wear("heart_glasses", "Heart glasses", "😍", zone="eyes", noun="heart-shaped glasses", covers=("eyes",), tags=("love", "party", "fun"),
      tint=("gum", "red", "lilac"))
def heart_glasses(x):
    c = col(x.color or "gum")
    return on_head("heart glasses", lambda ch: _lenses(ch, lambda e, w: heart_path(w * 0.78, e[0], e[1] + 4), c, C["red"]))


@wear("star_glasses", "Star glasses", "🤩", zone="eyes", noun="star-shaped glasses", covers=("eyes",), tags=("party", "fun", "star"),
      tint=("yellow", "teal", "gum"))
def star_glasses(x):
    c = col(x.color or "yellow")
    return on_head("star glasses", lambda ch: _lenses(ch, lambda e, w: star5((e[0], e[1] + 2), w * 0.8, k=0.55), c, C["gold2"]))


@wear("goggles", "Goggles", "🥽", zone="eyes", noun="goggles", covers=("eyes",), tags=("swim", "ski", "science"), tint=("teal", "orange", "lilac"))
def goggles(x):
    c = col(x.color or "teal")

    def items(ch):
        l, r, w, h = eyes_of(ch)
        cy = l[1]
        strap = smooth([(ch.CX - 150, cy - 2), (ch.CX, cy - 10), (ch.CX + 150, cy - 2)], closed=False, tension=0.4)
        lens = lambda e: rc((e[0], e[1]), (w * 1.5, h * 1.05), h * 0.45)
        return [
            gr("glare", [sh(Path([(e[0] - w * 0.35, e[1] - h * 0.15), (e[0] - w * 0.1, e[1] - h * 0.35)], closed=False)) for e in (l, r)] + [st(C["white"], 5, 80)]),
            gr("lenses", [lens(l), lens(r), fl(C["sky2"], 70)]),
            gr("frames", [lens(l), lens(r), st(c, 9)]),
            gr("strap", [sh(strap), st(c, 12)]),
        ]
    return on_head("goggles", items)


@wear("glasses_3d", "3D glasses", "🎬", zone="eyes", noun="3D glasses", covers=("eyes",), tags=("movie", "cinema", "fun"))
def glasses_3d(x):
    def items(ch):
        l, r, w, h = eyes_of(ch)
        lens = lambda e: rc((e[0], e[1] + 2), (w * 1.4, h * 0.9), 6)
        return [
            gr("left lens", [lens(l), fl(C["red"], 80)]),
            gr("right lens", [lens(r), fl(C["sky2"], 85)]),
            gr("frame", [rc((ch.CX, l[1] + 2), (r[0] - l[0] + w * 1.6, h * 1.1), 8), fl(C["white"])]),
        ]
    return on_head("glasses 3d", items)


@wear("monocle", "Monocle", "🧐", zone="eyes", noun="a monocle", tags=("fancy", "classy", "detective"))
def monocle(x):
    def items(ch):
        l, r, w, h = eyes_of(ch)
        d = max(w, h) * 1.25
        chain = smooth([(r[0] + d / 2, r[1] + 6), (r[0] + d / 2 + 20, r[1] + 60), (r[0] + 30, r[1] + 120)], closed=False, tension=0.4)
        return [gr("chain", [sh(chain), st(C["gold"], 3)]), gr("rim", [el(r, (d, d)), st(C["gold"], 6)]), gr("lens", [el(r, (d, d)), fl(C["lightblue"], 25)])]
    return on_head("monocle", items)


@wear("eye_patch", "Eye patch", "🏴‍☠️", zone="eyes", noun="an eye patch", tags=("pirate",))
def eye_patch(x):
    def items(ch):
        l, r, w, h = eyes_of(ch)
        return [gr("patch", [el(l, (w * 1.3, h * 1.15)), fl(C["black"])]),
                gr("strap", [sh(Path([(ch.CX - 140, l[1] - 70), (l[0], l[1]), (ch.CX + 140, l[1] + 60)], closed=False)), st(C["black"], 5)])]
    return on_head("eye patch", items)


@wear("sleep_mask", "Sleep mask", "😴", zone="eyes", noun="a sleep mask", covers=("eyes",), tags=("sleep", "bedtime", "night"),
      tint=("lilac", "gum", "sky2"))
def sleep_mask(x):
    c = col(x.color or "lilac")

    def items(ch):
        l, r, w, h = eyes_of(ch)
        mask = smooth([(l[0] - w, l[1] - 4), (l[0], l[1] - h * 0.62), (ch.CX, l[1] - h * 0.4), (r[0], r[1] - h * 0.62), (r[0] + w, r[1] - 4), (r[0], r[1] + h * 0.6),
                       (ch.CX, r[1] + h * 0.32), (l[0], l[1] + h * 0.6)], closed=True, tension=0.38)
        lash = lambda e: smooth([(e[0] - w * 0.4, e[1]), (e[0], e[1] + h * 0.22), (e[0] + w * 0.4, e[1])], closed=False, tension=0.4)
        return [gr("drawn eyes", [sh(lash(l)), sh(lash(r)), st(C["dark"], 5)]), gr("mask", [sh(mask), fl(c)]),
                gr("strap", [sh(Path([(ch.CX - 150, l[1] - 10), (ch.CX + 150, l[1] - 10)], closed=False)), st(c, 8)])]
    return on_head("sleep mask", items)


# ------------------------------------------------------------------ nose and mouth
@wear("mustache", "Mustache", "🥸", zone="mouth", noun="a mustache", tags=("fancy", "disguise", "funny"), tint=("dark", "brown", "darkbrown"))
def mustache(x):
    c = col(x.color or "dark")

    def items(ch):
        nx, ny = ch.nose
        half = lambda k: smooth([(nx, ny + 10), (nx + k * 22, ny + 6), (nx + k * 40, ny + 12), (nx + k * 50, ny + 2), (nx + k * 46, ny + 18),
                                 (nx + k * 26, ny + 24), (nx + k * 6, ny + 18)], closed=True, tension=0.36, sharp={3: 0.8})
        return [gr("mustache", [sh(half(1)), sh(half(-1)), fl(c)])]
    return on_head("mustache", items)


@wear("face_mask", "Face mask", "😷", zone="mouth", noun="a face mask", covers=("mouth",), tags=("sick", "doctor", "flu"), tint=("sky2", "white", "mint"))
def face_mask(x):
    c = col(x.color or "sky2")

    def items(ch):
        nx, ny = ch.nose
        mx, my = ch.mouth
        top, bot = ny - 12, my + 34
        mask = smooth([(nx - 66, top + 8), (nx, top), (nx + 66, top + 8), (nx + 62, bot - 10), (nx, bot), (nx - 62, bot - 10)], closed=True, tension=0.34,
                      sharp={0: 0.5, 2: 0.5})
        pleats = [sh(Path([(nx - 50, top + 18 + 12 * q), (nx + 50, top + 18 + 12 * q)], closed=False)) for q in range(3)]
        return [gr("pleats", pleats + [st(C["white"], 3, 60)]), gr("mask", [sh(mask), fl(c)]),
                gr("loops", [sh(Path([(nx - 66, top + 10), (nx - 110, top - 30)], closed=False)), sh(Path([(nx + 66, top + 10), (nx + 110, top - 30)], closed=False)),
                             st(C["white"], 4)])]
    return on_head("face mask", items)


@wear("clown_nose", "Clown nose", "🤡", zone="nose", noun="a clown nose", tags=("silly", "funny", "circus"))
def clown_nose(x):
    def items(ch):
        nx, ny = ch.nose
        return [gr("shine", [el((nx - 6, ny - 6), (8, 6)), fl(C["white"], 80)]), gr("nose", [el((nx, ny), (34, 32)), fl(C["red"])])]
    return on_head("clown nose", items)


# ------------------------------------------------------------------ neck
def _neck(ch):
    """Where things worn at the neck hang (body coordinates)."""
    if ch.collar:
        return ch.collar
    sx, sy = ch.neck_at or ch.neck
    return sx, sy + 14


@wear("bow_tie", "Bow tie", "🎀", zone="neck", noun="a bow tie", tags=("fancy", "classy", "party"), tint=("red", "navy", "black", "teal"))
def bow_tie(x):
    c = col(x.color or "red")

    def items(ch):
        sx, sy = _neck(ch)
        wing = lambda k: Path([(sx, sy), (sx + k * 30, sy - 16), (sx + k * 30, sy + 16)], closed=True)
        return [gr("bow tie", [gr("knot", [rc((sx, sy), (14, 16), 4), fl(c)]), gr("wings", [sh(wing(1)), sh(wing(-1)), fl(c)]),
                               gr("shade", [sh(wing(1)), sh(wing(-1)), st(C["black"], 3, 25)])])]
    return on_body("bow tie", items)


@wear("necktie", "Tie", "👔", zone="neck", noun="a tie", tags=("work", "office", "business"), tint=("navy", "red", "teal"))
def necktie(x):
    c = col(x.color or "navy")

    def items(ch):
        sx, sy = _neck(ch)
        tie = Path([(sx - 8, sy + 10), (sx + 8, sy + 10), (sx + 16, sy + 70), (sx, sy + 86), (sx - 16, sy + 70)], closed=True)
        return [gr("tie", [gr("stripes", [sh(Path([(sx - 10, sy + 34), (sx + 12, sy + 26)], closed=False)), sh(Path([(sx - 13, sy + 54), (sx + 14, sy + 46)], closed=False)),
                                          st(C["white"], 3, 60)]),
                           gr("knot", [sh(Path([(sx - 12, sy - 4), (sx + 12, sy - 4), (sx + 8, sy + 12), (sx - 8, sy + 12)], closed=True)), fl(c)]),
                           gr("blade", [sh(tie), fl(c)]),
                           gr("collar", [sh(Path([(sx - 30, sy - 10), (sx, sy + 4), (sx + 30, sy - 10)], closed=False)), st(C["white"], 10)])])]
    return on_body("necktie", items)


@wear("lei", "Flower lei", "🌺", zone="neck", noun="a flower lei", tags=("hawaii", "summer", "beach", "party"))
def lei(x):
    def items(ch):
        sx, sy = _neck(ch)
        out = []
        for q in range(9):                 # a garland hanging from the shoulders down onto the chest
            t = -1.0 + q / 4.0
            fx, fy = sx + 74 * t, sy - 8 + 48 * (1.0 - t * t)
            c = ("coral", "yellow", "rose", "gum")[q % 4]
            petals = [el((fx + 7 * math.cos(b), fy + 7 * math.sin(b)), (11, 11)) for b in (k * 2 * math.pi / 5 for k in range(5))]
            out.append(gr(f"flower {q}", [gr("centre", [el((fx, fy), (7, 7)), fl(C["white"])]), gr("petals", petals + [fl(C[c])])]))
        return out
    return on_body("lei", items)


@wear("bell_collar", "Bell collar", "🔔", zone="neck", noun="a collar with a bell", tags=("cat", "cute", "christmas"), tint=("red", "teal", "gum"))
def bell_collar(x):
    c = col(x.color or "red")

    def items(ch):
        sx, sy = _neck(ch)
        band = smooth([(sx - 60, sy - 8), (sx, sy + 6), (sx + 60, sy - 8)], closed=False, tension=0.4)
        return [gr("bell collar", [
            gr("slot", [sh(Path([(sx, sy + 20), (sx, sy + 26)], closed=False)), st(C["darkgold"], 3)]),
            gr("bell", [el((sx, sy + 18), (22, 22)), fl(C["gold"])]),
            gr("band", [sh(band), st(c, 11)]),
        ])]
    return on_body("bell collar", items)


@wear("bib", "Bib", "🍼", zone="neck", also=("body",), noun="a bib", tags=("eat", "baby", "food"), tint=("white", "sky2", "gum"))
def bib(x):
    c = col(x.color or "white")

    def items(ch):
        sx, sy = _neck(ch)
        shape = smooth([(sx - 40, sy - 4), (sx + 40, sy - 4), (sx + 46, sy + 40), (sx, sy + 70), (sx - 46, sy + 40)], closed=True, tension=0.36,
                       sharp={0: 0.4, 1: 0.4})
        return [gr("bib", [gr("heart", [sh(heart_path(14, sx, sy + 34)), fl(C["coral"])]), gr("bib", [sh(shape), fl(c)]),
                           gr("edge", [sh(shape), st(C["ice"], 4)])])]
    return on_body("bib", items)


# ------------------------------------------------------------------ back
@wear("hero_cape", "Hero cape", "🦸", zone="back", noun="a hero cape", tags=("hero", "brave", "costume"), tint=("red", "navy", "violet", "teal"))
def hero_cape(x):
    c = col(x.color or "red")
    L = x.L

    def items(ch, T, n):
        sx, sy = ch.neck_at or ch.neck
        per = L / max(1, round(L / 40.0))
        w = lambda f, ph: math.sin(2 * math.pi * f / per + ph)
        # wider than the body all the way down, so it shows beside the arms and legs from the front
        cape = lambda f: smooth([(sx - 64, sy + 4), (sx + 64, sy + 4), (sx + 100 + 4 * w(f, 0.3), sy + 90), (sx + 124 + 7 * w(f, 0.0), sy + 176),
                                 (sx + 44, sy + 166 + 8 * w(f, 1.0)), (sx, sy + 178),
                                 (sx - 44, sy + 166 + 8 * w(f, 2.0)), (sx - 124 + 7 * w(f, 0.5), sy + 176), (sx - 100 + 4 * w(f, 0.8), sy + 90)],
                                closed=True, tension=0.3, sharp={0: 0.4, 1: 0.4})
        return [gr("lining", [el((sx, sy + 116), (170, 110)), fl(C["black"], 16)]), gr("cape", [sh(F(n, cape, tol=0.6)), fl(c)])]

    def spec(char, T, n):
        sx, sy = char.neck_at or char.neck
        clasp = Layer("wear hero cape clasp", [gr("clasp", [el((sx - 40, sy + 8), (16, 16)), el((sx + 40, sy + 8), (16, 16)), fl(C["gold"])]),
                                               gr("cape top", [rc((sx, sy + 8), (92, 14), 7), fl(c)])], parent="body")
        return [("mid", clasp), ("back", Layer("wear hero cape", items(char, T, n), parent="body"))]
    return spec


@wear("angel_wings", "Angel wings", "👼", zone="back", noun="angel wings", tags=("angel", "innocent", "heaven"))
def angel_wings(x):
    L = x.L

    def spec(char, T, n):
        sx, sy = char.neck_at or char.neck
        per = L / max(1, round(L / 60.0))
        out = []
        for k in (1, -1):
            feathers = smooth([(sx + k * 20, sy + 40), (sx + k * 90, sy - 20), (sx + k * 150, sy - 30), (sx + k * 140, sy + 10), (sx + k * 150, sy + 30),
                               (sx + k * 120, sy + 50), (sx + k * 128, sy + 76), (sx + k * 70, sy + 80)], closed=True, tension=0.36)
            quills = [sh(smooth([(sx + k * 40, sy + 40), (sx + k * (80 + 18 * q), sy + 6 + 18 * q)], closed=False)) for q in range(3)]
            out.append(("back", Layer("wear angel wings" if k == 1 else "wear angel wings (left)", [gr("quills", quills + [st(C["sky2"], 4)]), gr("wing", [sh(feathers), fl(C["white"])]),
                                                               gr("edge", [sh(feathers), st(C["sky2"], 5)])],
                                      parent="body", a=(sx + k * 20, sy + 40), p=(sx + k * 20, sy + 40),
                                      r=F(n, lambda f, k=k: -k * 10 * math.sin(2 * math.pi * f / per), tol=1.0))))
        return out
    return spec


@wear("fairy_wings", "Fairy wings", "🧚", zone="back", noun="fairy wings", tags=("fairy", "magic", "cute"), tint=("lilac", "mint", "sky2", "gum"))
def fairy_wings(x):
    c = col(x.color or "lilac")
    L = x.L

    def spec(char, T, n):
        sx, sy = char.neck_at or char.neck
        per = L / max(1, round(L / 20.0))
        out = []
        for k in (1, -1):
            up = smooth([(sx + k * 10, sy + 40), (sx + k * 80, sy - 40), (sx + k * 140, sy - 30), (sx + k * 120, sy + 30)], closed=True, tension=0.4)
            low = smooth([(sx + k * 10, sy + 50), (sx + k * 100, sy + 70), (sx + k * 90, sy + 120), (sx + k * 40, sy + 100)], closed=True, tension=0.4)
            out.append(("back", Layer("wear fairy wings" if k == 1 else "wear fairy wings (left)", [gr("sparkle", [sh(star4((sx + k * 100, sy - 10), 10)), fl(C["white"])]),
                                                               gr("wings", [sh(up), sh(low), fl(c, 70)]), gr("edge", [sh(up), sh(low), st(C["white"], 3)])],
                                      parent="body", a=(sx + k * 10, sy + 45), p=(sx + k * 10, sy + 45),
                                      s=F(n, lambda f: (100 * (0.8 + 0.2 * math.cos(2 * math.pi * f / per)), 100), tol=2.0))))
        return out
    return spec


@wear("backpack", "Backpack", "🎒", zone="back", noun="a backpack", tags=("school", "travel", "hike"), tint=("coral", "teal", "yellow", "lilac"))
def backpack(x):
    c = col(x.color or "coral")

    def spec(char, T, n):
        sx, sy = char.neck_at or char.neck
        straps = Layer("wear backpack straps", [gr("straps", [sh(Path([(sx - 44, sy + 10), (sx - 54, sy + 90)], closed=False)),
                                                              sh(Path([(sx + 44, sy + 10), (sx + 54, sy + 90)], closed=False)), st(c, 10)])], parent="body")
        bag = Layer("wear backpack", [gr("pocket", [rc((sx + 70, sy + 70), (30, 40), 8), fl(C["white"], 40)]),
                                      gr("bag", [rc((sx, sy + 60), (180, 130), 24), fl(c)])], parent="body")
        return [("mid", straps), ("back", bag)]
    return spec


# ------------------------------------------------------------------ body
@wear("apron", "Apron", "👩‍🍳", zone="body", noun="an apron", tags=("cooking", "baking", "chef"), tint=("white", "coral", "teal"))
def apron(x):
    c = col(x.color or "white")

    def items(ch):
        sx, sy = ch.neck_at or ch.neck
        bib_ = smooth([(sx - 36, sy + 28), (sx + 36, sy + 28), (sx + 40, sy + 64), (sx + 66, sy + 74), (sx + 62, sy + 112), (sx, sy + 118), (sx - 62, sy + 112),
                       (sx - 66, sy + 74), (sx - 40, sy + 64)], closed=True, tension=0.3, sharp={0: 0.5, 1: 0.5})
        return [gr("apron", [gr("pocket", [rc((sx, sy + 90), (50, 22), 6), st(C["coral"], 3)]), gr("heart", [sh(heart_path(12, sx, sy + 48)), fl(C["coral"])]),
                             gr("apron", [sh(bib_), fl(c)]), gr("edge", [sh(bib_), st(C["ice"], 3)]),
                             gr("strap", [sh(Path([(sx - 34, sy + 30), (sx, sy + 4), (sx + 34, sy + 30)], closed=False)), st(c, 6)])])]
    return on_body("apron", items)


@wear("xmas_sweater", "Christmas sweater", "🎄", zone="body", noun="a Christmas sweater", tags=("christmas", "winter", "cozy"), tint=("red", "darkgreen", "navy"))
def xmas_sweater(x):
    c = col(x.color or "red")

    def items(ch):
        sx, sy = ch.neck_at or ch.neck
        body = smooth([(sx - 64, sy + 10), (sx + 64, sy + 10), (sx + 76, sy + 60), (sx + 78, sy + 104), (sx, sy + 112), (sx - 78, sy + 104), (sx - 76, sy + 60)],
                      closed=True, tension=0.34)
        zig = Path([(sx - 70 + 14 * q, sy + 60 + (8 if q % 2 else 0)) for q in range(11)], closed=False)
        tree = Path([(sx, sy + 66), (sx + 20, sy + 98), (sx - 20, sy + 98)], closed=True)
        return [gr("sweater", [gr("snow", [el((sx + dx, sy + dy), (7, 7)) for dx, dy in ((-44, 36), (40, 30), (-30, 92), (44, 88))] + [fl(C["white"])]),
                               gr("star", [sh(star5((sx, sy + 62), 8)), fl(C["yellow"])]), gr("tree", [sh(tree), fl(C["leaf"])]),
                               gr("zigzag", [sh(zig), st(C["white"], 5)]), gr("collar", [rc((sx, sy + 12), (100, 14), 7), fl(C["white"])]),
                               gr("body", [sh(body), fl(c)])])]
    return on_body("xmas sweater", items)


@wear("tshirt", "T-shirt", "👕", zone="body", noun="a T-shirt", tags=("casual", "summer"), tint=("teal", "coral", "yellow", "lilac", "white"))
def tshirt(x):
    c = col(x.color or "teal")

    def items(ch):
        sx, sy = ch.neck_at or ch.neck
        body = smooth([(sx - 62, sy + 8), (sx - 20, sy + 6), (sx, sy + 18), (sx + 20, sy + 6), (sx + 62, sy + 8), (sx + 74, sy + 52), (sx + 76, sy + 98),
                       (sx, sy + 104), (sx - 76, sy + 98), (sx - 74, sy + 52)], closed=True, tension=0.34)
        return [gr("tshirt", [gr("heart", [sh(heart_path(18, sx, sy + 56)), fl(C["white"], 90)]), gr("body", [sh(body), fl(c)])])]
    return on_body("tshirt", items)


@wear("tutu", "Tutu", "🩰", zone="waist", noun="a tutu", tags=("ballet", "dance", "pretty"), tint=("gum", "lilac", "mint", "sky2"))
def tutu(x):
    c = col(x.color or "gum")

    def items(ch):
        px, py = ch.pelvis
        frill = smooth([(px - 74, py - 20)] + [(px - 74 + 148 * q / 8, py + (14 if q % 2 else 2)) for q in range(9)] + [(px + 74, py - 20)], closed=True,
                       tension=0.34)
        return [gr("tutu", [gr("waist", [rc((px, py - 22), (140, 12), 6), fl(C["white"], 85)]), gr("frill", [sh(frill), fl(c, 85)]),
                            gr("under", [el((px, py - 4), (176, 40)), fl(c, 55)])])]
    return on_body("tutu", items, slot="mid")
