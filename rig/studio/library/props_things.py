"""Things to hold that are not food: tech and work, fun and celebration, occasions, everyday life.

Same conventions as props_food: drawn upright around the point in the paw (0, 0), negative y up.  Things held with
both paws in front of the body (a book, a laptop, a gamepad, pom-poms) are drawn in the body's own coordinates.
"""
from __future__ import annotations

from mascot import props as P

from ..registry import prop
from .common import C, F, K, Layer, Path, col, el, fl, gr, grip, heart_path, math, rc, sh, shade, smooth, st, star4, star5
from .props_food import flame, held


# ------------------------------------------------------------------ tech and work
@prop("laptop", "Laptop", "💻", noun="a laptop", paw="LR", pose="lap", flexible=False, category="tech", tags=("work", "typing"),
      tint=("silver", "lilac", "teal", "coral"), cost=1.0)
def laptop(x):
    lid_c = col(x.color or "silver")

    def spec(char, T, n):
        cx, y = 256.0, 392.0
        return [("front", Layer("laptop", [
            gr("logo", [sh(heart_path(12, cx, y - 54)), fl(C["white"], 85)]),
            gr("lid shine", [sh(Path([(cx - 52, y - 88), (cx - 30, y - 88), (cx - 62, y - 34), (cx - 74, y - 40)], closed=True)), fl(C["white"], 35)]),
            gr("lid", [rc((cx, y - 56), (152, 100), 10), fl(lid_c)]),
            gr("base", [sh(Path([(cx - 84, y - 6), (cx + 84, y - 6), (cx + 92, y + 6), (cx - 92, y + 6)], closed=True)), fl(C["steel"])]),
        ], parent="body"))]
    return spec


@prop("book", "Book", "📖", noun="a book", paw="LR", pose="clap_open", flexible=False, category="study", tags=("read", "school", "nerd"),
      tint=("coral", "teal", "lilac", "blue"))
def book(x):
    cover = col(x.color or "coral")

    def spec(char, T, n):
        cx, cy = 256.0, 340.0
        return [("mid", Layer("book", [
            gr("title", [rc((cx + 10, cy - 18), (54, 8), 3), rc((cx + 10, cy - 4), (40, 6), 3), fl(C["white"], 85)]),
            gr("star", [sh(star5((cx + 10, cy + 20), 10)), fl(C["yellow"])]),
            gr("spine", [rc((cx - 40, cy), (12, 92), 3), fl(C["dark"], 30)]),
            gr("cover", [rc((cx + 4, cy), (96, 92), 8), fl(cover)]),
            gr("pages", [rc((cx + 8, cy + 3), (96, 92), 8), fl(C["paper"])]),
        ], parent="body"))]
    return spec


@prop("pencil", "Pencil", "✏️", noun="a pencil", category="study", tags=("write", "school", "draw"))
def pencil(x):
    body = Path([(-7, -10), (7, -10), (7, -84), (-7, -84)], closed=True)
    tip = Path([(-7, -84), (7, -84), (0, -102)], closed=True)
    items = [
        gr("lead", [sh(Path([(-2.5, -96), (2.5, -96), (0, -102)], closed=True)), fl(C["ink"])]),
        gr("tip", [sh(tip), fl(C["sand"])]),
        gr("stripe", [rc((2.5, -47), (3, 74), 1), fl(C["gold2"])]),
        gr("body", [sh(body), fl(C["yellow"])]),
        gr("band", [rc((0, -12), (16, 10), 2), fl(C["silver"])]),
        gr("eraser", [rc((0, -2), (14, 12), 4), fl(C["gum"])]),
    ]
    if getattr(x.plan, "motion", None) == "write":      # held near the tip, the lead down on the paper
        return held(x, [gr("pencil", items, p=(0, 66))], nm="pencil", tilt=200.0 if x.side == "R" else 160.0, scale=1.0)
    return held(x, items, nm="pencil", tilt=24, scale=1.15)


@prop("guitar", "Guitar", "🎸", noun="a guitar", paw="LR", pose="belly", flexible=False, category="music", tags=("music", "song", "band"),
      tint=("wood", "coral", "teal", "red"), cost=1.0)
def guitar(x):
    """Slung across the body: the strumming paw at the sound hole, the other along the neck."""
    wood = col(x.color or "wood")

    def spec(char, T, n):
        strings = [sh(Path([(dx, 14), (dx * 0.5, -176)], closed=False)) for dx in (-6, -2, 2, 6)]
        items = [
            gr("strings", strings + [st(C["paper"], 1.5, 80)]),
            gr("pegs", [el((side * 15, -176 + 10 * q), (8, 7)) for side in (-1, 1) for q in range(3)] + [fl(C["silver"])]),
            gr("headstock", [rc((0, -170), (22, 36), 6), fl(C["darkbrown"])]),
            gr("frets", [rc((0, -60 - 18 * q), (14, 2.5), 1) for q in range(5)] + [fl(C["silver"], 80)]),
            gr("neck", [rc((0, -100), (14, 132), 3), fl(C["darkbrown"])]),
            gr("bridge", [rc((0, 16), (30, 7), 3), fl(C["darkbrown"])]),
            gr("sound hole", [el((0, -20), (22, 22)), fl(C["ink"])]),
            gr("rosette", [el((0, -20), (30, 30)), st(C["sand"], 3)]),
            gr("shine", [el((-18, -2), (12, 30)), fl(C["white"], 30)]),
            gr("top", [el((0, 4), (84, 76)), el((0, -40), (64, 56)), fl(wood)]),
            gr("edge", [el((0, 4), (84, 76)), el((0, -40), (64, 56)), st(shade(wood, 0.7), 4)]),
        ]
        return [("mid", Layer("guitar", [gr("guitar", items, a=(0, 0), p=(300, 392), r=-58, s=(95, 95))], parent="body"))]
    return spec


@prop("microphone", "Microphone", "🎤", noun="a microphone", category="music", tags=("sing", "karaoke"))
def microphone(x):
    grille = [sh(Path([(-14, -78 + 7 * q), (14, -78 + 7 * q)], closed=False)) for q in range(4)]
    return held(x, [
        gr("grille lines", grille + [st(C["steel"], 2, 70)]),
        gr("head shine", [el((-7, -84), (8, 10)), fl(C["white"], 60)]),
        gr("head", [el((0, -74), (36, 36)), fl(C["silver"])]),
        gr("ring", [rc((0, -56), (24, 6), 3), fl(C["gold2"])]),
        gr("handle", [sh(Path([(-10, -54), (10, -54), (6, -2), (-6, -2)], closed=True)), fl(C["black"])]),
    ], nm="microphone", scale=1.1)


@prop("camera", "Camera", "📷", noun="a camera", category="tech", tags=("photo", "travel"))
def camera(x):
    def items(char, T, n):
        L = n - 1
        t_flash = int(L * 0.5)
        flash = gr("flash burst", [sh(star4((0, 0), 30, k=0.25)), fl(C["white"])], a=(0, 0), p=(30, -92),
                   s=K(n, (0, (0, 0)), (t_flash, (0, 0), "hold"), (t_flash + 4, (140, 140), "out"), (t_flash + 14, (0, 0), "io")))
        return [
            flash,
            gr("lens shine", [el((-5, -48), (8, 8)), fl(C["white"], 80)]),
            gr("lens", [el((0, -44), (28, 28)), fl(C["sky2"])]),
            gr("lens ring", [el((0, -44), (40, 40)), fl(C["black"])]),
            gr("flash", [rc((26, -66), (12, 8), 2), fl(C["paper"])]),
            gr("button", [rc((-22, -72), (14, 6), 2), fl(C["red"])]),
            gr("body", [rc((0, -42), (76, 52), 10), fl(C["silver"])]),
        ]
    return held(x, items, nm="camera", pose="hold_up")


@prop("controller", "Gamepad", "🎮", noun="a gamepad", paw="LR", pose="clap_open", flexible=False, category="tech", tags=("gaming", "games"),
      tint=("lilac", "teal", "coral", "steel"))
def controller(x):
    c = col(x.color or "lilac")

    def spec(char, T, n):
        cx, cy = 256.0, 342.0
        pad = smooth([(cx - 60, cy - 16), (cx - 30, cy - 22), (cx + 30, cy - 22), (cx + 60, cy - 16), (cx + 66, cy + 18), (cx + 50, cy + 30),
                      (cx + 28, cy + 14), (cx - 28, cy + 14), (cx - 50, cy + 30), (cx - 66, cy + 18)], closed=True, tension=0.36)
        return [("mid", Layer("gamepad", [
            gr("buttons", [el((cx + 30, cy - 6), (9, 9)), el((cx + 40, cy + 2), (9, 9)), el((cx + 20, cy + 2), (9, 9)), fl(C["white"])]),
            gr("dpad", [rc((cx - 32, cy - 2), (22, 7), 2), rc((cx - 32, cy - 2), (7, 22), 2), fl(C["dark"])]),
            gr("pad", [sh(pad), fl(c)]),
        ], parent="body"))]
    return spec


@prop("paintbrush", "Paintbrush", "🖌️", noun="a paintbrush", category="art", tags=("art", "paint", "creative"), tint=("coral", "teal", "lilac", "yellow"))
def paintbrush(x):
    paint = col(x.color or "coral")
    return held(x, [
        gr("paint", [sh(smooth([(-7, -86), (7, -86), (4, -100), (0, -108), (-4, -100)], closed=True, tension=0.4)), fl(paint)]),
        gr("bristles", [rc((0, -84), (14, 14), 4), fl(C["sand"])]),
        gr("ferrule", [rc((0, -72), (12, 12), 2), fl(C["silver"])]),
        gr("handle", [rc((0, -36), (9, 62), 4), fl(C["wood"])]),
    ], nm="paintbrush", tilt=22)


@prop("magnifier", "Magnifying glass", "🔍", noun="a magnifying glass", category="tool", tags=("detective", "search", "curious"))
def magnifier(x):
    return held(x, [
        gr("shine", [sh(smooth([(-16, -76), (-6, -86), (6, -88)], closed=False, tension=0.4)), st(C["white"], 4, 80)]),
        gr("lens", [el((0, -70), (52, 52)), fl(C["sky2"], 45)]),
        gr("rim", [el((0, -70), (52, 52)), st(C["steel"], 8)]),
        gr("handle", [rc((0, -26), (12, 44), 5), fl(C["wood"])]),
    ], nm="magnifier", tilt=-18, scale=1.15)


# ------------------------------------------------------------------ fun and celebration
@prop("balloons", "Balloons", "🎈", noun="a bunch of balloons", pose="carry", category="celebrate", tags=("birthday", "party"), cost=1.0)
def balloons(x):
    cols = (C["coral"], C["teal"], C["yellow"])

    def shapes():
        out = []
        for q, (dx, dy, c) in enumerate(((-34, -10, cols[0]), (34, -14, cols[1]), (0, -46, cols[2]))):
            out.append(gr(f"balloon {q}", [
                gr("shine", [el((dx - 10, dy - 14), (10, 16)), fl(C["white"], 55)], r=20),
                gr("knot", [sh(Path([(dx - 4, dy + 34), (dx + 4, dy + 34), (dx, dy + 28)], closed=True)), fl(c)]),
                gr("body", [el((dx, dy), (54, 64)), fl(c)]),
            ]))
            out.append(gr(f"string {q}", [sh(Path([(dx, dy + 34), (0, 96)], closed=False)), st(C["grey"], 2)]))
        return out
    return P.cloud_on_string(x.side, offset=(30, -230), scale=0.9, period=x.per(60), sway_period=x.per(120), shapes=shapes(), nm="balloons")


@prop("bouquet", "Bouquet", "💐", noun="a bouquet of flowers", category="love", tags=("flowers", "love", "thanks"))
def bouquet(x):
    flowers = []
    for q, (fx, fy, c) in enumerate(((-18, -74, "coral"), (16, -78, "yellow"), (0, -96, "gum"), (-30, -94, "lilac"), (28, -98, "white"))):
        petals = [el((fx + 9 * math.cos(a), fy + 9 * math.sin(a)), (12, 12)) for a in (k * 2 * math.pi / 5 for k in range(5))]
        flowers.append(gr(f"flower {q}", [gr("centre", [el((fx, fy), (8, 8)), fl(C["gold2"])]), gr("petals", petals + [fl(C[c])])]))
    leaves = [gr("leaf", [el((0, 0), (12, 30)), fl(C["leaf"])], p=(lx, -66), r=a) for lx, a in ((-34, -40), (34, 40), (-22, -16), (22, 16))]
    wrap = Path([(-34, -64), (34, -64), (6, -2), (-6, -2)], closed=True)
    return held(x, flowers + leaves + [
        gr("ribbon", [rc((0, -26), (24, 8), 3), fl(C["coral"])]),
        gr("wrap", [sh(wrap), fl(C["paper"])]),
        gr("wrap edge", [sh(wrap), st(C["sand"], 3)]),
    ], nm="bouquet", scale=1.2)


@prop("rose", "Rose", "🌹", noun="a rose", category="love", tags=("love", "romantic", "valentine"))
def rose(x):
    bloom = smooth([(-16, -88), (-10, -104), (0, -98), (10, -106), (16, -88), (8, -76), (-8, -76)], closed=True, tension=0.4)
    return held(x, [
        gr("petal line", [sh(smooth([(-6, -94), (2, -88), (8, -94)], closed=False, tension=0.4)), st(C["darkred"], 3)]),
        gr("bloom", [sh(bloom), fl(C["red"])]),
        gr("leaf", [el((0, 0), (12, 26)), fl(C["leaf"])], p=(10, -46), r=50),
        gr("stem", [rc((0, -40), (5, 76), 2), fl(C["darkgreen"])]),
    ], nm="rose", tilt=-10, scale=1.25)


@prop("sign", "Sign", "🪧", noun="a sign", pose="hold_up", category="message", tags=("message", "protest", "caption"), tint=("paper", "yellow", "mint"),
      cost=1.2)
def sign(x):
    """A board on a stick.  With a caption, the caption is written on the board (rule R23); without one, a heart."""
    board = col(x.color or "paper")
    text = getattr(x.plan, "sign_text", None) if x.plan is not None else None

    def items(char, T, n):
        w, h, cy = 168.0, 112.0, -150.0
        inner = []
        if text:
            from ..caption import glyph_paths, layout
            size, lines = layout(text, width=w - 26, max_size=40.0, min_size=14.0, max_lines=3)
            lh = size * 1.06
            top = cy - lh * len(lines) / 2.0
            paths = []
            for q, ln in enumerate(lines):
                paths += glyph_paths(ln, 0.0, top + lh * q + size * 0.8, size)
            inner.append(gr("text", [sh(p) for p in paths] + [fl(C["ink"])]))
        else:
            inner.append(gr("heart", [sh(heart_path(34, 0, cy + 4)), fl(C["coral"])]))
        return inner + [
            gr("board", [rc((0, cy), (w, h), 10), fl(board)]),
            gr("board edge", [rc((0, cy), (w, h), 10), st(C["wood"], 6)]),
            gr("stick", [rc((0, -46), (12, 120), 4), fl(C["wood"])]),
        ]
    return held(x, items, pose="hold_up", nm="sign", scale=1.0)


@prop("flag", "Flag", "🚩", noun="a flag", pose="hold_up", category="celebrate", tags=("cheer", "team", "win"), tint=("coral", "teal", "yellow", "lilac"))
def flag(x):
    c = col(x.color or "coral")

    def items(char, T, n):
        L = n - 1
        per = L / max(1, round(L / 40.0))
        cloth = lambda f: smooth([(4, -150), (40, -156 + 6 * math.sin(2 * math.pi * f / per)), (76, -148 + 6 * math.sin(2 * math.pi * f / per + 1.2)),
                                  (76, -104 + 6 * math.sin(2 * math.pi * f / per + 1.2)), (40, -110 + 6 * math.sin(2 * math.pi * f / per)), (4, -104)],
                                 closed=True, tension=0.3, sharp={0: 0.9, 5: 0.9})
        return [
            gr("star", [sh(star5((40, -128), 12)), fl(C["white"])]),
            gr("cloth", [sh(F(n, cloth, tol=0.6)), fl(c)]),
            gr("tip", [el((0, -160), (12, 12)), fl(C["gold2"])]),
            gr("pole", [rc((0, -76), (7, 160), 3), fl(C["wood"])]),
        ]
    return held(x, items, pose="hold_up", nm="flag", scale=1.0)


@prop("pom_poms", "Pom-poms", "🎊", noun="pom-poms", paw="LR", pose="cheer", flexible=False, category="celebrate", tags=("cheer", "team"),
      tint=("coral", "teal", "yellow", "lilac"))
def pom_poms(x):
    c = col(x.color or "coral")

    def pom():
        strands = [el((14 * math.cos(a), -30 + 14 * math.sin(a)), (24, 24)) for a in (q * 2 * math.pi / 7 for q in range(7))]
        return [gr("pom", strands + [el((0, -30), (40, 40)), fl(c)]), gr("shine", [el((-8, -38), (12, 8)), fl(C["white"], 50)])]

    def spec(char, T, n):
        return [(f"hand.{s}", grip(char, T, s, pom(), "cheer", upright=True, nm=f"pom {s}", scale=1.3)) for s in "RL"]
    return spec


@prop("trophy", "Trophy", "🏆", noun="a trophy", pose="hold_up", category="award", tags=("win", "champion"))
def trophy(x):
    cup = smooth([(-30, -112), (30, -112), (26, -84), (10, -66), (-10, -66), (-26, -84)], closed=True, tension=0.36, sharp={0: 0.8, 1: 0.8})
    return held(x, [
        gr("star", [sh(star5((0, -92), 11)), fl(C["white"], 90)]),
        gr("cup", [sh(cup), fl(C["gold"])]),
        gr("handles", [el((-32, -96), (20, 26)), el((32, -96), (20, 26)), st(C["darkgold"], 6)]),
        gr("stem", [rc((0, -54), (12, 26), 3), fl(C["darkgold"])]),
        gr("base", [rc((0, -32), (46, 18), 4), fl(C["wood"])]),
        gr("plate", [rc((0, -32), (26, 6), 2), fl(C["gold"])]),
    ], pose="hold_up", nm="trophy", scale=1.15)


@prop("wand", "Magic wand", "🪄", noun="a magic wand", pose="hold_up", category="magic", tags=("magic", "wizard", "fairy"))
def wand(x):
    def items(char, T, n):
        L = n - 1
        per = L / max(1, round(L / 30.0))
        star = gr("star", [gr("shine", [sh(star5((0, -118), 9)), fl(C["white"], 70)]), sh(star5((0, -118), 22)), fl(C["yellow"])],
                  a=(0, -118), p=(0, -118), r=F(n, lambda f: 360.0 * f / L, tol=1.0),
                  s=F(n, lambda f: (100 + 10 * math.sin(2 * math.pi * f / per),) * 2, tol=1.5))
        sparks = []
        for q, (sx, sy) in enumerate(((-26, -132), (22, -142), (30, -106))):
            u = lambda f, q=q: ((f / per) + q / 3.0) % 1.0
            sparks.append(gr(f"spark {q}", [sh(star4((sx, sy), 8)), fl(C["white"])], a=(sx, sy), p=(sx, sy),
                             s=F(n, lambda f, u=u: (100 * math.sin(math.pi * u(f)),) * 2, tol=2.0)))
        return sparks + [star, gr("tip", [rc((0, -96), (7, 14), 2), fl(C["white"])]), gr("wand", [rc((0, -50), (7, 96), 3), fl(C["black"])])]
    return held(x, items, pose="hold_up", nm="wand", tilt=18, scale=1.0)


@prop("umbrella", "Umbrella", "☂️", noun="an umbrella", pose="hold_up", category="weather", tags=("rain",), tint=("coral", "teal", "yellow", "lilac"),
      cost=1.0)
def umbrella(x):
    c = col(x.color or "coral")
    canopy = smooth([(-110, -176), (-80, -226), (0, -250), (80, -226), (110, -176), (82, -184), (55, -176), (28, -184), (0, -176), (-28, -184),
                     (-55, -176), (-82, -184)], closed=True, tension=0.32, sharp={0: 0.6, 4: 0.6})
    ribs = [sh(Path([(0, -250), (rx, -178)], closed=False)) for rx in (-55, 0, 55)]
    return held(x, [
        gr("ribs", ribs + [st(C["white"], 3, 45)]),
        gr("canopy", [sh(canopy), fl(c)]),
        gr("tip", [rc((0, -258), (6, 16), 2), fl(C["steel"])]),
        gr("shaft", [rc((0, -96), (6, 170), 2), fl(C["steel"])]),
        gr("handle", [sh(Path([(0, -14), (0, 2), (12, 4)], i=[(0, 0), (0, -6), (-4, 4)], o=[(0, 6), (4, 4), (0, 0)], closed=False)), st(C["wood"], 7)]),
    ], pose="hold_up", nm="umbrella", tilt=-14, scale=1.0)


@prop("fan", "Hand fan", "🪭", noun="a hand fan", category="weather", tags=("hot", "summer"), tint=("coral", "teal", "lilac", "gum"))
def fan(x):
    c = col(x.color or "coral")

    def items(char, T, n):
        L = n - 1
        per = L / max(1, round(L / 16.0))
        blades = []
        for q in range(7):
            a = -60 + q * 20
            blades.append(gr(f"blade {q}", [sh(Path([(0, 0), (-9, -66), (9, -66)], closed=True)), fl(c if q % 2 else C["white"])], r=a))
        return [gr("fan", blades + [gr("rivet", [el((0, 0), (8, 8)), fl(C["gold2"])])], p=(0, -18),
                   r=F(n, lambda f: 18 * math.sin(2 * math.pi * f / per), tol=1.0))]
    return held(x, items, nm="fan", scale=1.1)


@prop("party_horn", "Party horn", "🎉", noun="a party horn", pose="mouth", category="celebrate", tags=("party", "birthday", "new year"))
def party_horn(x):
    def items(char, T, n):
        L = n - 1
        per = L / max(1, round(L / 40.0))
        ext = lambda f: 0.5 + 0.5 * max(0.0, math.sin(2 * math.pi * f / per))
        return [
            gr("tube", [rc((0, 0), (70, 14), 7), fl(C["teal"])], a=(-35, 0), p=(30, -30), s=F(n, lambda f: (100 * ext(f), 100), tol=2.0)),
            gr("cone", [sh(Path([(-12, -24), (34, -38), (34, -22), (-12, -32)], closed=True)), fl(C["gum"])]),
        ]
    return held(x, items, pose="mouth", nm="party horn", scale=1.0)


@prop("sparkler", "Sparkler", "🎇", noun="a sparkler", pose="hold_up", category="celebrate", tags=("new year", "diwali", "party"))
def sparkler(x):
    def items(char, T, n):
        L = n - 1
        per = L / max(1, round(L / 10.0))
        sparks = []
        for q in range(8):
            a = q * math.pi / 4
            sparks.append(sh(Path([(18 * math.cos(a), -112 + 18 * math.sin(a)), (34 * math.cos(a), -112 + 34 * math.sin(a))], closed=False)))
        burst = gr("sparks", sparks + [st(C["yellow"], 4)], a=(0, -112), p=(0, -112),
                   s=F(n, lambda f: (80 + 30 * abs(math.sin(2 * math.pi * f / per)),) * 2, tol=2.0),
                   r=F(n, lambda f: 22.5 * (int(f / (per / 2.0)) % 2), hold=True))
        return [
            burst,
            gr("glow", [el((0, -112), (26, 26)), fl(C["white"])]),
            gr("halo", [el((0, -112), (44, 44)), fl(C["yellow"], 45)]),
            gr("wire", [rc((0, -58), (4, 110), 2), fl(C["steel"])]),
        ]
    return held(x, items, pose="hold_up", nm="sparkler", tilt=12, scale=1.0)


# ------------------------------------------------------------------ occasions
@prop("pumpkin", "Pumpkin", "🎃", noun="a jack-o'-lantern", pose="hold", category="halloween", tags=("halloween", "spooky", "autumn"))
def pumpkin(x):
    lobes = [el((dx, -46), (w, 64)) for dx, w in ((-26, 46), (26, 46), (0, 54))]
    eye = lambda dx: Path([(dx - 9, -48), (dx + 9, -48), (dx, -62)], closed=True)
    grin = Path([(-22, -38), (-12, -32), (-6, -36), (0, -30), (6, -36), (12, -32), (22, -38), (14, -26), (-14, -26)], closed=True)
    return held(x, [
        gr("face", [sh(eye(-14)), sh(eye(14)), sh(grin), fl(C["flame"])]),
        gr("face dark", [sh(eye(-14)), sh(eye(14)), sh(grin), st(C["darkbrown"], 3)]),
        gr("lobes", lobes + [fl(C["orange"])]),
        gr("ridges", [el((dx, -46), (w, 64)) for dx, w in ((-26, 46), (26, 46))] + [st(C["crust"], 3, 80)]),
        gr("stem", [rc((2, -82), (10, 16), 3), fl(C["darkgreen"])]),
    ], nm="pumpkin", scale=1.2)


@prop("lantern", "Lantern", "🏮", noun="a lantern", pose="hold_up", category="festival", tags=("ramadan", "eid", "diwali", "lunar new year"),
      tint=("gold2", "red", "teal"))
def lantern(x):
    c = col(x.color or "gold2")

    def items(char, T, n):
        L = n - 1
        per = L / max(1, round(L / 30.0))
        glow = gr("glow", [el((0, 64), (80, 80)), fl(C["yellow"], 30)], a=(0, 64), p=(0, 64),
                  s=F(n, lambda f: (100 + 12 * math.sin(2 * math.pi * f / per),) * 2, tol=1.5))
        body = smooth([(-22, 30), (22, 30), (30, 62), (22, 96), (-22, 96), (-30, 62)], closed=True, tension=0.3, sharp={0: 0.6, 1: 0.6})
        window = smooth([(-12, 40), (12, 40), (16, 62), (12, 86), (-12, 86), (-16, 62)], closed=True, tension=0.3)
        return [
            flame(n, L, at=(0, 64), size=0.9),
            gr("window", [sh(window), fl(C["yellow"], 90)]),
            gr("body", [sh(body), fl(c)]),
            gr("cap", [sh(Path([(-20, 30), (20, 30), (0, 10)], closed=True)), fl(c)]),
            gr("base", [rc((0, 100), (40, 10), 3), fl(c)]),
            gr("ring", [el((0, 4), (14, 14)), st(c, 4)]),
            glow,
        ]
    return held(x, items, pose="hold_up", nm="lantern", scale=1.0, grip_at=(0.0, 4.0))


@prop("diya", "Oil lamp", "🪔", noun="an oil lamp", pose="tray", category="festival", tags=("diwali",))
def diya(x):
    def items(char, T, n):
        L = n - 1
        bowl = Path([(-34, -24), (34, -24), (16, -4), (-16, -4)], i=[(0, 0), (0, 0), (10, 0), (0, 0)], o=[(0, 0), (-4, 14), (0, 0), (-10, 0)],
                    closed=True)
        return [
            flame(n, L, at=(22, -44), size=1.1),
            gr("dots", [el((dx, -16), (6, 6)) for dx in (-16, 0, 16)] + [fl(C["yellow"])]),
            gr("bowl", [sh(bowl), fl(C["crust"])]),
            gr("rim", [el((0, -24), (70, 12)), fl(C["darkbrown"])]),
        ]
    return held(x, items, pose="tray", nm="diya", scale=1.2)


@prop("red_envelope", "Red envelope", "🧧", noun="a red envelope", category="festival", tags=("lunar new year", "eid", "gift", "money"),
      tint=("red", "teal", "gold2"))
def red_envelope(x):
    c = col(x.color or "red")
    return held(x, [
        gr("seal", [el((0, -60), (22, 22)), fl(C["gold"])]),
        gr("seal ring", [el((0, -60), (30, 30)), st(C["gold2"], 3)]),
        gr("flap", [sh(Path([(-28, -96), (28, -96), (0, -66)], closed=True)), fl(C["darkred"])]),
        gr("envelope", [rc((0, -54), (60, 92), 6), fl(c)]),
    ], nm="red envelope", tilt=-8, scale=1.1)


@prop("easter_egg", "Easter egg", "🥚", noun="an Easter egg", category="festival", tags=("easter", "spring"), tint=("lilac", "mint", "gum", "sky2"))
def easter_egg(x):
    c = col(x.color or "lilac")
    egg = smooth([(0, -92), (24, -76), (32, -44), (22, -14), (0, -6), (-22, -14), (-32, -44), (-24, -76)], closed=True, tension=0.38)
    zig = Path([(-30, -50), (-18, -60), (-6, -50), (6, -60), (18, -50), (30, -60)], closed=False)
    return held(x, [
        gr("dots", [el((dx, -28), (8, 8)) for dx in (-12, 0, 12)] + [fl(C["white"])]),
        gr("zigzag", [sh(zig), st(C["yellow"], 6)]),
        gr("band", [rc((0, -74), (40, 6), 3), fl(C["white"], 85)]),
        gr("egg", [sh(egg), fl(c)]),
    ], nm="easter egg", scale=1.1)


@prop("love_letter", "Love letter", "💌", noun="a love letter", category="love", tags=("love", "valentine", "letter", "mail"))
def love_letter(x):
    return held(x, [
        gr("heart", [sh(heart_path(14, 0, -44)), fl(C["red"])]),
        gr("flap", [sh(Path([(-38, -72), (38, -72), (0, -40)], closed=True)), fl(C["rose"])]),
        gr("flap line", [sh(Path([(-38, -72), (0, -40), (38, -72)], closed=False)), st(C["coral"], 2.5)]),
        gr("envelope", [rc((0, -46), (80, 54), 5), fl(C["paper"])]),
        gr("edge", [rc((0, -46), (80, 54), 5), st(C["rose"], 3)]),
    ], nm="love letter", tilt=-10, scale=1.2)


@prop("diploma", "Diploma", "📜", noun="a diploma", category="study", tags=("graduation", "school"))
def diploma(x):
    return held(x, [
        gr("ribbon tails", [sh(Path([(-4, -40), (-12, -14), (-2, -20)], closed=True)), sh(Path([(4, -40), (12, -14), (2, -20)], closed=True)),
                            fl(C["red"])]),
        gr("ribbon", [rc((0, -46), (14, 30), 4), fl(C["red"])]),
        gr("ends", [el((-48, -46), (12, 26)), el((48, -46), (12, 26)), fl(C["sand"])]),
        gr("scroll", [rc((0, -46), (96, 24), 10), fl(C["paper"])]),
    ], nm="diploma", tilt=-30, scale=1.2)


# ------------------------------------------------------------------ everyday life
@prop("money", "Money", "💸", noun="some money", category="money", tags=("rich", "pay", "shopping"))
def money(x):
    bills = []
    for q, a in enumerate((-22, 0, 22)):
        bills.append(gr(f"bill {q}", [
            gr("mark", [el((0, -40), (18, 18)), st(C["darkgreen"], 3)]),
            gr("inner", [rc((0, -40), (44, 64), 3), st(C["darkgreen"], 2, 60)]),
            gr("bill", [rc((0, -40), (52, 72), 4), fl(C["lime"])]),
        ], a=(0, 0), p=(0, 0), r=a))
    return held(x, bills[::-1], nm="money", scale=1.15)


@prop("shopping_bag", "Shopping bag", "🛍️", noun="a shopping bag", pose="edge", category="shopping", tags=("shopping", "sale"),
      tint=("gum", "teal", "lilac", "coral"))
def shopping_bag(x):
    c = col(x.color or "gum")
    return held(x, [
        gr("heart", [sh(heart_path(14, 0, 44)), fl(C["white"], 90)]),
        gr("bag", [sh(Path([(-34, 16), (34, 16), (38, 90), (-38, 90)], closed=True)), fl(c)]),
        gr("handles", [sh(Path([(-16, 18), (-16, 2), (16, 2), (16, 18)], i=[(0, 0), (0, 6), (0, -12), (0, 0)], o=[(0, -6), (0, -12), (0, 6), (0, 0)],
                                closed=False)), st(C["dark"], 4)]),
    ], pose="edge", nm="shopping bag", upright=True, scale=1.0, grip_at=(0.0, 14.0))


@prop("suitcase", "Suitcase", "🧳", noun="a suitcase", pose="edge", category="travel", tags=("travel", "holiday", "trip"), tint=("teal", "coral", "lilac"))
def suitcase(x):
    c = col(x.color or "teal")
    return held(x, [
        gr("stickers", [el((-14, 46), (16, 16)), fl(C["yellow"])]),
        gr("sticker 2", [sh(star5((16, 64), 9)), fl(C["white"])]),
        gr("straps", [rc((-20, 56), (6, 76), 2), rc((20, 56), (6, 76), 2), fl(C["darkbrown"], 60)]),
        gr("case", [rc((0, 56), (84, 80), 10), fl(c)]),
        gr("handle", [rc((0, 10), (30, 8), 4), fl(C["dark"])]),
    ], pose="edge", nm="suitcase", upright=True, scale=1.0, grip_at=(0.0, 12.0))


@prop("toothbrush", "Toothbrush", "🪥", noun="a toothbrush", category="routine", tags=("morning", "night", "bedtime"))
def toothbrush(x):
    brushing = getattr(x.plan, "motion", None) == "brush_teeth"     # then it points into the mouth
    tilt = (-58.0 if x.side == "R" else 58.0) if brushing else 16.0
    return held(x, [
        gr("paste", [sh(smooth([(-10, -98), (0, -106), (10, -98), (4, -92), (-6, -92)], closed=True, tension=0.4)), fl(C["white"])]),
        gr("paste stripe", [rc((0, -99), (16, 3), 1.5), fl(C["teal"])]),
        gr("bristles", [rc((0, -86), (16, 16), 3), fl(C["white"])]),
        gr("handle", [rc((0, -42), (10, 92), 5), fl(C["teal"])]),
    ], nm="toothbrush", tilt=tilt, scale=1.05 if brushing else 1.15)


@prop("pillow", "Pillow", "🛏️", noun="a pillow", pose="edge", category="sleep", tags=("sleep", "bedtime", "tired"), tint=("lilac", "sky2", "mint", "gum"))
def pillow(x):
    c = col(x.color or "lilac")
    body = smooth([(-48, 10), (0, 18), (48, 10), (52, 50), (48, 92), (0, 84), (-48, 92), (-52, 50)], closed=True, tension=0.36,
                  sharp={0: 0.4, 2: 0.4, 4: 0.4, 6: 0.4})
    return held(x, [
        gr("stars", [sh(star5((-16, 46), 7)), sh(star5((18, 60), 6)), fl(C["white"], 85)]),
        gr("pillow", [sh(body), fl(c)]),
    ], pose="edge", nm="pillow", upright=True, scale=1.0, grip_at=(0.0, 4.0))


@prop("plushie", "Teddy", "🧸", noun="a teddy bear", category="toy", tags=("cute", "sleep", "kid"))
def plushie(x):
    return held(x, [
        gr("face", [el((-7, -66), (5, 6)), el((7, -66), (5, 6)), el((0, -58), (7, 5)), fl(C["dark"])]),
        gr("muzzle", [el((0, -58), (18, 12)), fl(C["sand"])]),
        gr("head", [el((0, -66), (40, 36)), fl(C["brown"])]),
        gr("ears", [el((-16, -82), (14, 14)), el((16, -82), (14, 14)), fl(C["brown"])]),
        gr("belly", [el((0, -28), (24, 26)), fl(C["sand"])]),
        gr("body", [el((0, -30), (44, 48)), fl(C["brown"])]),
        gr("bow", [el((-7, -48), (10, 8)), el((7, -48), (10, 8)), fl(C["coral"])]),
    ], nm="teddy", scale=1.2)


@prop("dumbbell", "Dumbbell", "🏋️", noun="a dumbbell", category="gym", tags=("gym", "strong", "workout"))
def dumbbell(x):
    # gripped in the middle of the bar: the paw closes over it and the plates stick out either side
    return held(x, [
        gr("weights", [rc((-36, -4), (18, 50), 5), rc((36, -4), (18, 50), 5), fl(C["dark"])]),
        gr("inner", [rc((-24, -4), (10, 38), 3), rc((24, -4), (10, 38), 3), fl(C["steel"])]),
        gr("bar", [rc((0, -4), (60, 10), 4), fl(C["silver"])]),
    ], nm="dumbbell", scale=1.25)


@prop("ball", "Ball", "⚽", noun="a ball", category="sport", tags=("sport", "football", "soccer"))
def ball(x):
    patches = [sh(star5((0, -44), 10, k=0.85, rot=-90))]
    for a in range(5):
        r = math.radians(-90 + a * 72)
        patches.append(sh(star5((24 * math.cos(r), -44 + 24 * math.sin(r)), 7, k=0.85, rot=-90 + a * 72)))
    return held(x, [
        gr("patches", patches + [fl(C["black"])]),
        gr("ball", [el((0, -44), (64, 64)), fl(C["white"])]),
        gr("edge", [el((0, -44), (64, 64)), st(C["silver"], 3)]),
    ], nm="ball", scale=1.15)


@prop("basketball", "Basketball", "🏀", noun="a basketball", pose="hold_up", category="sport", tags=("sport", "basketball"))
def basketball(x):
    def items(char, T, n):
        L = n - 1
        lines = [sh(Path([(0, -76), (0, -12)], closed=False)), sh(Path([(-32, -44), (32, -44)], closed=False)),
                 sh(smooth([(-20, -70), (-10, -44), (-20, -18)], closed=False, tension=0.4)), sh(smooth([(20, -70), (10, -44), (20, -18)], closed=False, tension=0.4))]
        return [gr("ball", [gr("lines", lines + [st(C["darkbrown"], 3)]), gr("body", [el((0, -44), (64, 64)), fl(C["orange"])])],
                   a=(0, -44), p=(0, -44), r=F(n, lambda f: 720.0 * f / L, tol=1.0))]
    return held(x, items, pose="hold_up", nm="basketball", scale=1.1)


@prop("tissue", "Tissue", "🤧", noun="a tissue", category="sick", tags=("sick", "cry", "sneeze"))
def tissue(x):
    sheet = smooth([(-22, -20), (-26, -54), (-12, -78), (4, -66), (18, -82), (28, -56), (20, -20)], closed=True, tension=0.4)
    return held(x, [
        gr("fold", [sh(smooth([(-10, -58), (2, -46), (14, -60)], closed=False, tension=0.4)), st(C["ice"], 3)]),
        gr("tissue", [sh(sheet), fl(C["white"])]),
        gr("edge", [sh(sheet), st(C["ice"], 2.5)]),
    ], nm="tissue", scale=1.15)


@prop("thermometer", "Thermometer", "🌡️", noun="a thermometer", category="sick", tags=("sick", "fever", "hot"))
def thermometer(x):
    return held(x, [
        gr("marks", [rc((6, -30 - 10 * q), (6, 2), 1) for q in range(5)] + [fl(C["steel"])]),
        gr("mercury", [rc((0, -46), (5, 56), 2.5), el((0, -16), (14, 14)), fl(C["red"])]),
        gr("glass", [rc((0, -50), (14, 74), 7), el((0, -16), (20, 20)), fl(C["white"])]),
        gr("edge", [rc((0, -50), (14, 74), 7), st(C["silver"], 2.5)]),
    ], nm="thermometer", tilt=-20, scale=1.2)


@prop("alarm_clock", "Alarm clock", "⏰", noun="an alarm clock", pose="hold_up", category="routine", tags=("morning", "late", "deadline"),
      tint=("coral", "teal", "yellow"))
def alarm_clock(x):
    c = col(x.color or "coral")

    def items(char, T, n):
        L = n - 1
        per = L / max(1, round(L / 6.0))
        hands = [sh(Path([(0, -46), (0, -64)], closed=False)), sh(Path([(0, -46), (12, -46)], closed=False))]
        return [gr("clock", [
            gr("hands", hands + [st(C["dark"], 4)]),
            gr("face", [el((0, -46), (46, 46)), fl(C["paper"])]),
            gr("bells", [el((-24, -76), (22, 18)), el((24, -76), (22, 18)), fl(C["gold2"])]),
            gr("body", [el((0, -46), (60, 60)), fl(c)]),
            gr("feet", [rc((-18, -14), (8, 12), 3), rc((18, -14), (8, 12), 3), fl(C["dark"])]),
        ], a=(0, -46), p=(0, -46), r=F(n, lambda f: 7 * math.sin(2 * math.pi * f / per), tol=1.0))]
    return held(x, items, pose="hold_up", nm="alarm clock", scale=1.15)
