"""More effects: signs over the head (?, !, an idea, a clock, a tick), weather (sun, snow, petals, leaves, lightning),
celebration (fireworks, a spotlight, a rainbow), feelings (a broken heart, steam, panic sweat, waterfall tears, dizzy
stars) and fun (bubbles, money, bats, a ghost, butterflies, flies).

Everything loops: things that fall or rise wrap round the loop, things that pop are timed with `peak` so they are
fully there in the still frame.
"""
from __future__ import annotations

import numpy as np

from mascot import props as P

from ..registry import effect
from .common import C, F, K, Layer, Path, col, el, fl, gr, heart_path, loop_pop, math, rc, sh, smooth, st, star4, star5
from .effects_core import floaters, twinkles
from .fx import speed_lines, streams


def _over_head(char, dy=-70.0, dx=0.0):
    cx, cy = char.crown_world(0)
    return cx + dx, cy + dy


def _popper(name, shapes, at_fn, L, life=None, bob=4.0, slot="top"):
    """Something that pops in over the head, bobs, and shrinks away before the loop ends (peak ~ 0.3)."""
    life = life or int(L * 0.85)

    def spec(char, T, n):
        x, y = at_fn(char)
        per = L / max(1, round(L / 30.0))
        return [(slot, Layer(name, shapes, p=F(n, lambda f: (x, y + bob * math.sin(2 * math.pi * f / per)), tol=0.5),
                             s=F(n, lambda f: (100 * loop_pop(f, L, 2, life, 1.2),) * 2, tol=1.5)))]
    return spec


def _fallers(name, shape_fn, count, L, area=(40.0, 472.0), top=-20.0, fall=440.0, sway=18.0, spin=180.0, seed=3, slot="top", speed=1.0):
    """Things falling through the picture (snow, petals, leaves, money) on a loop: each wraps round to the top."""
    def spec(char, T, n):
        rng = np.random.RandomState(seed)
        out = []
        per = L / max(1, round(L * speed / 90.0))
        for q in range(count):
            x0 = area[0] + (area[1] - area[0]) * (q + rng.uniform(0.1, 0.9)) / count
            ph = rng.rand()
            sw = rng.uniform(0.6, 1.0) * sway
            k = rng.uniform(0.75, 1.1)

            def u(f, ph=ph):
                return ((f / per) + ph) % 1.0

            pos = F(n, lambda f, u=u, x0=x0, sw=sw: (x0 + sw * math.sin(2 * math.pi * 2 * u(f)), top + fall * u(f)), tol=0.8)
            op = F(n, lambda f, u=u: 100 * min(1.0, u(f) * 10) * min(1.0, (1 - u(f)) * 6), tol=3.0)
            rot = F(n, lambda f, u=u, q=q: spin * u(f) * (1 if q % 2 else -1), tol=2.0)
            out.append((slot, Layer(f"{name} {q}", shape_fn(q), p=pos, o=op, r=rot, s=(100 * k, 100 * k))))
        return out
    return spec


# ------------------------------------------------------------------ signs over the head
@effect("question", "Question marks", "❓", zone="overhead", peak=0.35, tags=("confused", "curious"))
def question(x):
    L = x.L

    def mark(q):
        hook = smooth([(-10, -12), (-8, -24), (4, -28), (12, -18), (8, -8), (0, -2), (0, 8)], closed=False, tension=0.4)
        return [gr("dot", [el((0, 20), (9, 9)), fl(C["coral"])]), gr("hook", [sh(hook), st(C["coral"], 8)])]
    return floaters("question", mark, [(-70, -10, 0.0, 1.2), (60, -30, 0.45, 0.9)], L, rise=40, life=0.8, sway=6)


@effect("exclaim", "Exclamation", "❗", zone="overhead", peak=0.3, tags=("surprise", "alert"))
def exclaim(x):
    shapes = [gr("dot", [el((0, 30), (14, 14)), fl(C["red"])]), gr("bar", [rc((0, -8), (14, 52), 7), fl(C["red"])])]
    return _popper("exclamation", shapes, lambda ch: _over_head(ch, dy=-60.0, dx=70.0), x.L)


@effect("idea", "Light bulb", "💡", zone="overhead", peak=0.3, tags=("idea", "smart"))
def idea(x):
    L = x.L

    def spec(char, T, n):
        bx, by = _over_head(char, dy=-72.0)
        per = L / max(1, round(L / 30.0))
        rays = [sh(Path([(30 * math.cos(a), -6 + 30 * math.sin(a)), (44 * math.cos(a), -6 + 44 * math.sin(a))], closed=False))
                for a in (math.radians(d) for d in (-150, -115, -90, -65, -30))]
        bulb = [
            gr("rays", rays + [st(C["yellow"], 5)], o=F(n, lambda f: 60 + 40 * math.sin(2 * math.pi * f / per), tol=3.0)),
            gr("shine", [el((-7, -14), (7, 10)), fl(C["white"], 90)]),
            gr("glass", [el((0, -6), (40, 42)), fl(C["yellow"])]),
            gr("base", [rc((0, 18), (18, 12), 3), fl(C["steel"])]),
        ]
        return [("top", Layer("light bulb", bulb, p=F(n, lambda f: (bx, by + 3 * math.sin(2 * math.pi * f / per)), tol=0.5),
                              s=F(n, lambda f: (100 * loop_pop(f, L, 2, int(L * 0.85), 1.25),) * 2, tol=1.5)))]
    return spec


@effect("clock", "Clock", "⏰", zone="overhead", peak=0.3, tags=("late", "deadline", "waiting"))
def clock(x):
    L = x.L

    def spec(char, T, n):
        cx, cy = _over_head(char, dy=-70.0, dx=10.0)
        per = L / max(1, round(L / 30.0))
        hand = gr("hand", [sh(Path([(0, 0), (0, -18)], closed=False)), st(C["dark"], 4)], r=F(n, lambda f: 360.0 * f / L, tol=1.0))
        return [("top", Layer("clock", [
            gr("hub", [el((0, 0), (6, 6)), fl(C["dark"])]),
            hand,
            gr("short hand", [sh(Path([(0, 0), (12, 0)], closed=False)), st(C["dark"], 4)]),
            gr("face", [el((0, 0), (52, 52)), fl(C["paper"])]),
            gr("rim", [el((0, 0), (60, 60)), fl(C["coral"])]),
        ], p=F(n, lambda f: (cx + 4 * math.sin(2 * math.pi * f / (per / 2)), cy), tol=0.5),
            s=F(n, lambda f: (100 * loop_pop(f, L, 2, int(L * 0.85), 1.2),) * 2, tol=1.5)))]
    return spec


@effect("check", "Tick", "✅", zone="overhead", peak=0.3, tags=("done", "yes", "ok"))
def check(x):
    shapes = [gr("tick", [sh(Path([(-14, 0), (-4, 12), (16, -12)], closed=False)), st(C["white"], 8)]),
              gr("box", [rc((0, 0), (52, 52), 12), fl(C["green"])])]
    return _popper("tick", shapes, lambda ch: _over_head(ch, dy=-64.0, dx=60.0), x.L)


@effect("cross_mark", "Cross", "❌", zone="overhead", peak=0.3, tags=("no", "wrong"))
def cross_mark(x):
    shapes = [gr("cross", [sh(Path([(-14, -14), (14, 14)], closed=False)), sh(Path([(-14, 14), (14, -14)], closed=False)), st(C["white"], 8)]),
              gr("box", [rc((0, 0), (52, 52), 12), fl(C["red"])])]
    return _popper("cross", shapes, lambda ch: _over_head(ch, dy=-64.0, dx=60.0), x.L)


@effect("broken_heart", "Broken heart", "💔", zone="overhead", peak=0.3, tags=("sad", "heartbroken"))
def broken_heart(x):
    L = x.L

    def spec(char, T, n):
        cx, cy = _over_head(char, dy=-66.0)
        crack = [(0, -24), (-6, -12), (5, -2), (-4, 10), (0, 26)]
        left = Path([(-1, -24)] + [(px - 1, py) for px, py in crack[1:]] + [(0, 26)], closed=False)
        t_split = int(L * 0.4)
        half = lambda sgn: gr(f"half {sgn}", [sh(heart_path(30, 0, 0)), fl(C["red"])],
                              p=K(n, (0, (0, 0)), (t_split, (0, 0), "hold"), (t_split + 10, (sgn * 9, 4), "back"), (int(L * 0.85), (sgn * 9, 4), "hold"),
                                  (L, (0, 0), "io")),
                              r=K(n, (0, 0.0), (t_split, 0.0, "hold"), (t_split + 10, sgn * 12.0, "back"), (int(L * 0.85), sgn * 12.0, "hold"), (L, 0.0, "io")))
        return [("top", Layer("broken heart", [
            gr("crack", [sh(left), st(C["white"], 5)]),
            half(-1), half(1),
        ], p=(cx, cy), s=F(n, lambda f: (100 * loop_pop(f, L, 2, int(L * 0.9), 1.15),) * 2, tol=1.5)))]
    return spec


@effect("dizzy_stars", "Dizzy stars", "💫", zone="overhead", tags=("dizzy", "knocked out"))
def dizzy_stars(x):
    L = x.L

    def spec(char, T, n):
        out = []
        for q in range(3):
            def pos(f, q=q):
                cx, cy = char.crown_world(f)
                a = 2 * math.pi * (f / float(L) * 2 + q / 3.0)
                return (cx + 104 * math.cos(a), cy - 18 + 22 * math.sin(a))

            def front(f, q=q):
                return math.sin(2 * math.pi * (f / float(L) * 2 + q / 3.0)) > 0
            shapes = [gr("star", [sh(star5((0, 0), 18)), fl(C["yellow"])]), gr("edge", [sh(star5((0, 0), 18)), st(C["darkgold"], 3)])]
            out.append(("top", Layer(f"dizzy star {q}", shapes, p=F(n, pos, tol=0.6), r=F(n, lambda f: 360.0 * f / L * 2, tol=2.0),
                                     o=F(n, lambda f, front=front: 100 if front(f) else 0, hold=True))))
            out.append(("back", Layer(f"dizzy star {q} far", shapes, p=F(n, pos, tol=0.6), r=F(n, lambda f: 360.0 * f / L * 2, tol=2.0),
                                      o=F(n, lambda f, front=front: 0 if front(f) else 100, hold=True))))
        return out
    return spec


# ------------------------------------------------------------------ face and body
@effect("steam", "Steam", "😤", zone="face", tags=("angry", "furious"))
def steam(x):
    L = x.L

    def spec(char, T, n):
        out = []
        per = L / max(1, round(L / 40.0))
        for s, sgn in (("R", 1.0), ("L", -1.0)):
            ex, ey = char.side(char.ear_pivot, s)
            for q in range(2):
                ph = q * 0.5

                def u(f, ph=ph):
                    return ((f / per) + ph) % 1.0
                pos = F(n, lambda f, u=u, ex=ex, ey=ey, sgn=sgn: (ex + sgn * (10 + 40 * u(f)), ey + 30 - 50 * u(f)), tol=0.6)
                scl = F(n, lambda f, u=u: (50 + 90 * u(f),) * 2, tol=2.0)
                op = F(n, lambda f, u=u: 80 * min(1.0, u(f) * 6) * (1 - u(f)), tol=3.0)
                out.append(("front", Layer(f"steam {s} {q}", [gr("puff", [el((0, 0), (30, 26)), el((10, -6), (22, 20)), fl(C["steel"], 55)])],
                                           parent="neck", p=pos, s=scl, o=op)))
        return out
    return spec


@effect("panic_sweat", "Panic sweat", "😰", zone="face", tags=("panic", "nervous", "stress"))
def panic_sweat(x):
    L = x.L
    drops = [P.sweat_drop(int(L * t), life=int(L * 0.4), at=at, side=sd) for t, at, sd in
             ((0.05, (374.0, 190.0), 1.0), (0.3, (146.0, 196.0), -1.0), (0.55, (382.0, 216.0), 1.0))]

    def spec(char, T, n):
        out = []
        for d in drops:
            out += d(char, T, n)
        return out
    return spec


@effect("waterfall_tears", "Waterfall tears", "😭", zone="face", tags=("cry", "sad"))
def waterfall_tears(x):
    return streams(x.L)


@effect("snore_bubble", "Snot bubble", "😪", zone="face", peak=0.5, tags=("sleep", "tired"))
def snore_bubble(x):
    L = x.L
    q = L / 4.0
    return P.sleep_bubble([(int(q * 0.2), int(q * 1.6), 0.6), (int(q * 1.8), int(q * 3.0), 0.85)], t_pop=int(L * 0.86), at=(262.0, 262.0),
                          big=40.0)


@effect("cold_breath", "Cold breath", "🌬️", zone="face", tags=("cold", "winter", "sigh"))
def cold_breath(x):
    L = x.L
    return P.breath_puff(int(L * 0.1), life=min(70, int(L * 0.8)), count=3)


@effect("shock_lines", "Shock lines", "💥", zone="around", peak=0.2, tags=("shock", "surprise"))
def shock_lines(x):
    L = x.L

    def spec(char, T, n):
        cx, cy = char.head_to_world(0, (char.CX, (char.crown[1] + char.mouth[1]) / 2.0))
        per = L / max(1, round(L / 20.0))
        lines = []
        for q in range(8):
            a = math.radians(-160 + q * 20) if q < 4 else math.radians(-20 - (q - 4) * 20)
            r0, r1 = 150, 182
            lines.append(sh(Path([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a))], closed=False)))
        return [("back", Layer("shock lines", [gr("lines", lines + [st(C["dark"], 6, 85)])], a=(cx, cy), p=(cx, cy),
                               s=F(n, lambda f: (100 + 8 * math.sin(2 * math.pi * f / per),) * 2, tol=1.0)))]
    return spec


@effect("flies", "Stinky flies", "🪰", zone="around", tags=("gross", "stinky", "messy"))
def flies(x):
    L = x.L

    def spec(char, T, n):
        cx, cy = char.crown_world(0)
        out = []
        for q in range(3):
            def pos(f, q=q):
                a = 2 * math.pi * (f / float(L) * (2 + q) + q / 3.0)
                return (cx + 60 * math.cos(a) + 8 * math.sin(3 * a), cy - 20 + 24 * math.sin(2 * a))
            per = L / max(1, round(L / 4.0))
            wings = gr("wings", [el((-5, -6), (9, 7)), el((5, -6), (9, 7)), fl(C["white"], 80)], s=F(n, lambda f: (100, 60 + 40 * abs(math.sin(2 * math.pi * f / per))), tol=4.0))
            out.append(("top", Layer(f"fly {q}", [wings, gr("body", [el((0, 0), (10, 8)), fl(C["black"])])], p=F(n, pos, tol=0.6), s=(160, 160))))
        lines = [sh(smooth([(cx + dx, cy + 40), (cx + dx + 8, cy + 20), (cx + dx - 6, cy + 2), (cx + dx + 4, cy - 14)], closed=False, tension=0.4))
                 for dx in (-90, 90)]
        out.append(("back", Layer("stink lines", [gr("lines", lines + [st(C["lettuce"], 5, 70)])])))
        return out
    return spec


# ------------------------------------------------------------------ weather and nature
@effect("sun", "Sun rays", "☀️", zone="back", tags=("hot", "summer", "morning"))
def sun(x):
    L = x.L

    def spec(char, T, n):
        cx, cy = char.middle_root(0)
        cy -= 70
        rays = [sh(Path([(cx + 150 * math.cos(a), cy + 150 * math.sin(a)), (cx + 230 * math.cos(a), cy + 230 * math.sin(a))], closed=False))
                for a in (q * math.pi / 8 for q in range(16))]
        return [("back", Layer("sun rays", [gr("rays", rays + [st(C["yellow"], 14, 60)], a=(cx, cy), p=(cx, cy), r=F(n, lambda f: 8.0 * math.sin(2 * math.pi * f / L), tol=0.3),
                                                s=F(n, lambda f: (100 + 5 * math.sin(4 * math.pi * f / L),) * 2, tol=0.5)),
                                            gr("glow", [el((cx, cy), (300, 300)), fl(C["yellow"], 22)])]))]
    return spec


@effect("snow", "Snow", "❄️", zone="around", tags=("winter", "cold", "christmas"), cost=1.4)
def snow(x):
    def flake(q):
        arms = [sh(Path([(0, 0), (9 * math.cos(a), 9 * math.sin(a))], closed=False)) for a in (k * math.pi / 3 for k in range(6))]
        return [gr("flake", arms + [st(C["white"], 3)]), gr("rim", arms + [st(C["sky2"], 5, 60)])]
    return _fallers("snowflake", flake, 9, x.L, sway=14, spin=90, seed=4)


@effect("petals", "Cherry blossoms", "🌸", zone="around", tags=("spring", "love", "calm"), cost=1.3)
def petals(x):
    def petal(q):
        return [gr("petal", [sh(smooth([(0, -8), (6, 0), (0, 8), (-6, 0)], closed=True, tension=0.42, sharp={0: 0.4})), fl(C["rose"] if q % 2 else C["pink"])])]
    return _fallers("petal", petal, 8, x.L, sway=26, spin=270, seed=6)


@effect("leaves", "Falling leaves", "🍂", zone="around", tags=("autumn", "fall"), cost=1.3)
def leaves(x):
    def leaf(q):
        c = (C["orange"], C["crust"], C["tomato"])[q % 3]
        return [gr("vein", [sh(Path([(0, -9), (0, 9)], closed=False)), st(C["darkbrown"], 1.5, 60)]),
                gr("leaf", [sh(smooth([(0, -12), (8, -2), (0, 12), (-8, -2)], closed=True, tension=0.4, sharp={0: 0.6, 2: 0.6})), fl(c)])]
    return _fallers("leaf", leaf, 7, x.L, sway=30, spin=300, seed=8)


@effect("money_rain", "Money rain", "💸", zone="around", tags=("rich", "money", "payday"), cost=1.3)
def money_rain(x):
    def bill(q):
        if q % 3 == 2:
            return [gr("coin", [el((0, 0), (20, 20)), fl(C["gold"])]), gr("coin edge", [el((0, 0), (20, 20)), st(C["darkgold"], 3)])]
        return [gr("mark", [el((0, 0), (9, 9)), st(C["darkgreen"], 2)]), gr("bill", [rc((0, 0), (34, 20), 3), fl(C["lime"])])]
    return _fallers("money", bill, 8, x.L, sway=22, spin=200, seed=9)


@effect("lightning", "Lightning", "⚡", zone="around", peak=0.02, tags=("storm", "shock", "angry"))
def lightning(x):
    L = x.L

    def spec(char, T, n):
        cx, cy = char.crown_world(0)
        bolt = Path([(8, -40), (-10, 0), (2, 0), (-8, 40), (14, -6), (2, -6), (12, -40)], closed=True)
        out = []
        for q, (dx, t0) in enumerate(((-120, 0), (130, int(L * 0.5)))):
            op = F(n, lambda f, t0=t0: 100 if ((f - t0) % L) < 6 or 10 <= ((f - t0) % L) < 14 else 0, hold=True)
            out.append(("top", Layer(f"lightning {q}", [gr("bolt", [sh(bolt), fl(C["yellow"])]), gr("edge", [sh(bolt), st(C["gold2"], 4)])],
                                     p=(cx + dx, cy + 10), o=op, s=(130, 130))))
        return out
    return spec


@effect("rainbow", "Rainbow", "🌈", zone="back", tags=("happy", "pride", "hope"))
def rainbow(x):
    def spec(char, T, n):
        cx, cy = char.middle_root(0)
        cy += 40
        bands = []
        for q, c in enumerate(("red", "orange", "yellow", "lime", "sky2", "purple")):
            r = 230 - q * 18
            arc = Path([(cx - r, cy), (cx, cy - r), (cx + r, cy)], i=[(0, 0), (-r * 0.552, 0), (0, -r * 0.552)],
                       o=[(0, -r * 0.552), (r * 0.552, 0), (0, 0)], closed=False)
            bands.append(gr(f"band {q}", [sh(arc), st(C[c], 18, 85)]))
        return [("back", Layer("rainbow", bands))]
    return spec


@effect("bubbles", "Bubbles", "🫧", zone="around", tags=("bath", "calm", "underwater"), cost=1.2)
def bubbles(x):
    def bubble(q):
        return [gr("shine", [el((-5, -5), (6, 4)), fl(C["white"], 90)], r=-30), gr("ring", [el((0, 0), (26, 26)), st(C["bubble"], 3)]),
                gr("fill", [el((0, 0), (26, 26)), fl(C["bubble"], 25)])]
    return floaters("bubble", bubble, [(-120, 120, 0.0, 1.0), (110, 140, 0.2, 0.8), (-80, 60, 0.45, 0.7), (140, 40, 0.65, 1.1), (60, 100, 0.85, 0.6)],
                    x.L, rise=160, life=0.9, sway=14)


@effect("butterflies", "Butterflies", "🦋", zone="around", tags=("spring", "calm", "love"))
def butterflies(x):
    """Two butterflies flutter round the mascot on closed loops; wings beat on a period that divides the loop."""
    L = x.L

    def wing_pair(c1, c2):
        up = smooth([(0, 0), (16, -22), (30, -14), (24, 2)], closed=True, tension=0.4)
        low = smooth([(0, 2), (18, 8), (16, 22), (4, 12)], closed=True, tension=0.4)
        mir = lambda path_pts: smooth([(-a, b) for a, b in path_pts], closed=True, tension=0.4)
        return [gr("spots", [el((17, -12), (7, 7)), el((-17, -12), (7, 7)), fl(C["white"], 70)]),
                gr("upper", [sh(up), sh(mir([(0, 0), (16, -22), (30, -14), (24, 2)])), fl(C[c1])]),
                gr("lower", [sh(low), sh(mir([(0, 2), (18, 8), (16, 22), (4, 12)])), fl(C[c2])])]

    def spec(char, T, n):
        out = []
        flap = L / max(1, round(L / 8.0))
        for q, (cx, cy, rx, ry, c1, c2, k) in enumerate(((112, 150, 70, 40, "lilac", "teal", 1.0), (400, 210, 60, 50, "yellow", "coral", 0.85))):
            ph = 0.37 * q

            def pos(f, cx=cx, cy=cy, rx=rx, ry=ry, ph=ph, q=q):
                u = 2 * math.pi * (f / float(L) + ph)
                return (cx + rx * math.sin(u), cy + ry * math.sin(2 * u) * 0.6 - 8 * math.cos(u * (2 + q)))
            wings = gr("wings", wing_pair(c1, c2), s=F(n, lambda f, q=q: (100 * (0.25 + 0.75 * abs(math.cos(math.pi * f / flap + q))), 100), tol=3.0))
            body = gr("body", [el((0, 2), (6, 22)), fl(C["ink"])])
            ant = gr("antennae", [sh(Path([(-2, -8), (-8, -20)], closed=False)), sh(Path([(2, -8), (8, -20)], closed=False)), st(C["ink"], 2)])
            out.append(("top", Layer(f"butterfly {q}", [ant, body, wings], p=F(n, pos, tol=0.6), s=(100 * k, 100 * k),
                                     r=F(n, lambda f, ph=ph: 12 * math.cos(2 * math.pi * (f / float(L) + ph)), tol=1.0))))
        return out
    return spec


@effect("bats", "Bats", "🦇", zone="around", tags=("halloween", "spooky", "night"))
def bats(x):
    L = x.L

    def spec(char, T, n):
        out = []
        per = L / max(1, round(L / 10.0))
        for q, (cx, cy, r) in enumerate(((120, 90, 50), (400, 120, 40), (420, 60, 30))):
            pos = F(n, lambda f, cx=cx, cy=cy, r=r, q=q: (cx + r * math.cos(2 * math.pi * f / L + q), cy + r * 0.4 * math.sin(4 * math.pi * f / L + q)), tol=0.6)
            wing = lambda k: smooth([(0, 0), (k * 14, -10), (k * 26, -4), (k * 20, 2), (k * 14, 0), (k * 8, 6)], closed=True, tension=0.3)
            wings = gr("wings", [sh(wing(1)), sh(wing(-1)), fl(C["night"])], s=F(n, lambda f: (100, 40 + 60 * abs(math.cos(math.pi * f / per))), tol=4.0))
            out.append(("top", Layer(f"bat {q}", [gr("eyes", [el((-3, -1), (3, 3)), el((3, -1), (3, 3)), fl(C["yellow"])]),
                                                  gr("body", [el((0, 0), (12, 14)), fl(C["night"])]), wings], p=pos)))
        return out
    return spec


@effect("ghost", "Ghost", "👻", zone="around", tags=("halloween", "spooky", "boo"))
def ghost(x):
    L = x.L

    def spec(char, T, n):
        per = L / max(1, round(L / 60.0))
        body = smooth([(-28, 30), (-30, -10), (-18, -36), (0, -42), (18, -36), (30, -10), (28, 30), (18, 22), (8, 32), (-2, 22), (-12, 32), (-20, 22)],
                      closed=True, tension=0.35)
        shapes = [gr("face", [el((-9, -12), (8, 12)), el((9, -12), (8, 12)), el((0, 6), (10, 12)), fl(C["dark"])]),
                  gr("ghost", [sh(body), fl(C["white"], 92)]), gr("edge", [sh(body), st(C["ice"], 3)])]
        return [("top", Layer("ghost", shapes, p=F(n, lambda f: (420 + 20 * math.sin(2 * math.pi * f / L), 150 + 14 * math.sin(2 * math.pi * f / per)), tol=0.6),
                              r=F(n, lambda f: 8 * math.sin(2 * math.pi * f / L), tol=1.0), s=(140, 140)))]
    return spec


# ------------------------------------------------------------------ celebration and stage
@effect("fireworks", "Fireworks", "🎆", zone="back", peak=0.3, tags=("new year", "celebrate", "diwali"), cost=1.4)
def fireworks(x):
    L = x.L

    def one(cx, cy, t0, colour, q):
        def spec(char, T, n):
            out = []
            life = int(L * 0.45)
            for k in range(10):
                a = 2 * math.pi * k / 10
                u = lambda f: ((f - t0) % L) / float(life)
                pos = F(n, lambda f, a=a: (cx + 92 * math.cos(a) * math.sin(math.pi / 2 * min(1.0, u(f))), cy + 92 * math.sin(a) * math.sin(math.pi / 2 * min(1.0, u(f))) + 20 * max(0.0, u(f)) ** 2), tol=0.8)
                op = F(n, lambda f: 0.0 if u(f) >= 1.0 else 100 * (1 - u(f)) ** 0.7, tol=3.0)
                out.append(("back", Layer(f"firework {q} {k}", [gr("spark", [sh(star4((0, 0), 14)), fl(col(colour))])], p=pos, o=op)))
            return out
        return spec
    parts = [one(110, 110, 0, "coral", 0), one(400, 90, int(L * 0.3), "yellow", 1), one(250, 60, int(L * 0.6), "teal", 2)]

    def spec(char, T, n):
        out = []
        for p in parts:
            out += p(char, T, n)
        return out
    return spec


@effect("spotlight", "Spotlight", "🔦", zone="back", tags=("star", "show", "ta-da"))
def spotlight(x):
    def spec(char, T, n):
        cx, gy = char.CX, char.GROUND
        beam = Path([(cx - 40, -20), (cx + 40, -20), (cx + 200, gy + 10), (cx - 200, gy + 10)], closed=True)
        return [("back", Layer("spotlight", [gr("pool", [el((cx, gy + 4), (360, 50)), fl(C["yellow"], 35)]), gr("beam", [sh(beam), fl(C["yellow"], 18)])]))]
    return spec


@effect("speed_lines", "Speed lines", "💨", zone="back", tags=("fast", "hurry", "running"))
def speed_lines_fx(x):
    return speed_lines(x.L, count=6, direction=-1)


@effect("boom", "Boom", "💥", zone="back", peak=0.2, tags=("shock", "explode", "mind blown"))
def boom(x):
    L = x.L

    def spec(char, T, n):
        cx, cy = char.crown_world(0)
        cy -= 20
        pts = []
        for q in range(16):
            r = 120 if q % 2 == 0 else 78
            a = q * math.pi / 8
            pts.append((cx + r * math.cos(a), cy + r * 0.85 * math.sin(a)))
        star = Path(pts, closed=True)
        inner = Path([(cx + (k * 0.6) * (p[0] - cx), cy + (k * 0.6) * (p[1] - cy)) for p, k in zip(pts, [1.0] * len(pts))], closed=True)
        return [("back", Layer("boom", [gr("inner", [sh(inner), fl(C["yellow"])]), gr("burst", [sh(star), fl(C["flame"])])], a=(cx, cy), p=(cx, cy),
                               s=F(n, lambda f: (100 * loop_pop(f, L, 2, int(L * 0.8), 1.15),) * 2, tol=1.5)))]
    return spec


@effect("night_sky", "Moon and stars", "🌙", zone="back", tags=("night", "sleep", "good night"))
def night_sky(x):
    L = x.L

    def spec(char, T, n):
        moon = smooth([(10, -42), (-22, -30), (-34, 0), (-22, 30), (10, 42), (-4, 22), (-10, 0), (-4, -22)], closed=True, tension=0.38,
                      sharp={0: 0.8, 4: 0.8})
        out = [("back", Layer("moon", [gr("moon", [sh(moon), fl(C["yellow"])])], p=(410, 90)))]
        tw = twinkles([(80, 70, 14, "white", 0), (150, 30, 10, "yellow", int(L * 0.3)), (460, 190, 12, "white", int(L * 0.6)), (340, 40, 9, "yellow", int(L * 0.8))],
                      L, life=int(L * 0.5), slot="back", nm="night star")
        return out + tw(char, T, n)
    return spec
