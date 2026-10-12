"""The first twelve effects (from v3), made loop-safe, plus the helpers new effects are built from.

`peak` says when in the loop an effect looks most complete; the composer turns each effect's loop so that moment
lands on the still frame (the PNG, and the frame WhatsApp shows when an animated sticker stops).
"""
from __future__ import annotations

from mascot import props as P

from ..registry import effect
from .common import C, F, Layer, Path, col, el, fl, gr, heart_path, loop_pop, math, rc, sh, smooth, st, star4


# ------------------------------------------------------------------ building blocks
def twinkles(items, L, life=26, peak=1.2, slot="top", nm="sparkle"):
    """items: [(x, y, R, colour, t0)] four-point stars that pop in at t0, live `life` frames and wrap round the loop."""
    def spec(char, T, n):
        out = []
        for q, (x, y, R, colr, t0) in enumerate(items):
            s = F(n, lambda f, t0=t0: (100 * loop_pop(f, L, t0, life, peak),) * 2, tol=1.5)
            r = F(n, lambda f, q=q: 20 * q + 25 * math.sin(2 * math.pi * f / L), tol=1.0)
            out.append((slot, Layer(f"{nm} {q}", [gr(nm, [sh(star4((0, 0), R)), fl(col(colr))])], p=(x, y), s=s, r=r)))
        return out
    return spec


def floaters(name, shapes_fn, offsets, L, rise=90.0, life=0.6, sway=8.0, size=1.0, slot="top"):
    """Shapes that float up from around the head and fade, each on its own phase of the loop.
    offsets: [(dx, dy, phase, scale)] from the top of the head."""
    def spec(char, T, n):
        cx, cy = char.crown_world(0)
        out = []
        for q, (dx, dy, ph, k) in enumerate(offsets):
            def u(f, ph=ph):
                x = ((f / float(L)) + ph) % 1.0
                return x / life if x < life else None

            def pos(f, dx=dx, dy=dy, q=q):
                x = u(f)
                x = 0.0 if x is None else x
                return (cx + dx + sway * math.sin(2 * math.pi * x + q), cy + dy - rise * x)

            def op(f):
                x = u(f)
                return 0.0 if x is None else 100 * min(1.0, x * 6) * min(1.0, (1 - x) * 3)

            def scl(f, k=k):
                x = u(f)
                x = 0.0 if x is None else x
                v = 100 * size * k * (0.5 + 0.5 * min(1.0, x * 4))
                return (v, v)
            out.append((slot, Layer(f"{name} {q}", shapes_fn(q), p=F(n, pos, tol=0.6), o=F(n, op, tol=2.5), s=F(n, scl, tol=1.5))))
        return out
    return spec


# ------------------------------------------------------------------ the twelve
@effect("sparkles", "Sparkles", "✨", zone="around", peak=0.3)
def sparkles(x):
    L = x.L
    return twinkles([(84, 170, 22, "yellow", 0), (430, 120, 26, "teal", int(L * 0.25)), (456, 260, 18, "coral", int(L * 0.5)),
                     (60, 300, 18, "lilac", int(L * 0.72))], L, life=min(26, int(L * 0.45)))


@effect("confetti", "Confetti", "🎉", zone="around", peak=0.35, cost=1.6)
def confetti(x):
    return P.confetti(t0=4, origin=(256, 250), t_end=x.L)


@effect("zzz", "Zzz", "💤", zone="overhead", peak=0.45)
def zzz(x):
    L = x.L
    return P.zzz([(134, 44, 20, 0), (158, 8, 26, int(L * 0.2)), (178, -28, 30, int(L * 0.4))], life=int(L * 0.55),
                 fade_in=int(L * 0.15), rel=True)


@effect("thought", "Thought dots", "💭", zone="overhead", peak=0.6)
def thought(x):
    L = x.L
    return P.thought_dots([(162, 58, 20, 4), (188, 24, 28, 14), (216, -16, 40, 24)], t_out=L - 16, t_gone=L, rel=True)


@effect("tear", "Tear", "😢", zone="face", peak=0.4)
def tear(x):
    return P.tear(int(x.L * 0.2), life=int(x.L * 0.6))


@effect("sweat", "Sweat drop", "😅", zone="face", peak=0.35)
def sweat(x):
    return P.sweat_drop(int(x.L * 0.15), life=int(x.L * 0.6))


@effect("hearts", "Floating hearts", "💕", zone="around", tint=("coral", "pink", "lilac", "teal"))
def hearts(x):
    c = col(x.color or "coral")
    return floaters("heart", lambda q: [gr("heart", [sh(heart_path(22)), fl(c)])],
                    [(-110, 90, 0.0, 1.0), (115, 70, 0.33, 0.85), (-70, 20, 0.66, 0.75)], x.L)


@effect("notes", "Music notes", "🎵", zone="around")
def notes(x):
    def note(q):
        c = C[("teal", "lilac", "coral")[q % 3]]
        return [gr("note", [el((-7, 10), (16, 12)), rc((0, -8), (4, 36), 1), sh(Path([(2, -26), (14, -18), (14, -10), (2, -18)], closed=True)),
                            fl(c)])]
    return floaters("note", note, [(-130, 80, 0.0, 1.0), (130, 50, 0.3, 0.9), (-90, 10, 0.55, 0.8), (110, -10, 0.8, 0.85)], x.L,
                    rise=80, sway=12)


@effect("aura", "Glow ring", "🌀", zone="back", tint=("teal", "lilac", "yellow", "mint"))
def aura(x):
    return P.aura(x.color if isinstance(x.color, str) and x.color in C else "teal", period=x.L, size=336.0)


@effect("orbs", "Orbs", "🔮", zone="around", follows=True)
def orbs(x):
    return P.orbs(3, period=x.L)


@effect("rain", "Rain cloud", "🌧️", zone="overhead")
def rain(x, drops=6):
    L = x.L

    def spec(char, T, n):
        cx, cy = char.crown_world(0)
        cy -= 96
        cloud = Layer("rain cloud", [gr("cloud", [el((-34, 4), (60, 46)), el((4, -10), (70, 58)), el((40, 4), (58, 44)), rc((0, 16), (124, 32), 16),
                                                   fl(C["grey"])])],
                      p=F(n, lambda f: (cx, cy + 3 * math.sin(2 * math.pi * f / L)), tol=0.5))
        out = [("top", cloud)]
        for q in range(drops):
            x0 = cx - 45 + 18 * q
            ph = (q * 0.37) % 1.0
            per = L / max(1, round(L / (L / 3.0)))

            def pos(f, x0=x0, ph=ph):
                u = ((f / per) + ph) % 1.0
                return (x0, cy + 30 + 110 * u)

            def op(f, ph=ph):
                u = ((f / per) + ph) % 1.0
                return 90 * min(1.0, u * 8) * min(1.0, (1 - u) * 4)
            drop = smooth([(0, -9), (5, 0), (0, 6), (-5, 0)], closed=True, tension=0.42, sharp={0: 0.35})
            out.append(("top", Layer(f"rain {q}", [gr("drop", [sh(drop), fl(C["sky"])])], p=F(n, pos, tol=0.5), o=F(n, op, tol=3.0))))
        return out
    return spec


@effect("anger", "Anger mark", "💢", zone="face", tint=("coral", "red"))
def anger(x):
    L, c = x.L, col(x.color or "coral")

    def spec(char, T, n):
        px, py = char.crown[0] + 92, char.crown[1] + 58
        arcs = []
        for a in (45, 135, 225, 315):
            r = math.radians(a)
            cx, cy = 11 * math.cos(r), 11 * math.sin(r)
            arcs.append(sh(Path([(cx - 9 * math.sin(r), cy + 9 * math.cos(r)), (cx + 9 * math.sin(r), cy - 9 * math.cos(r))],
                                i=[(0, 0), (-5 * math.cos(r), -5 * math.sin(r))], o=[(-5 * math.cos(r), -5 * math.sin(r)), (0, 0)], closed=False)))
        per = L / max(1, round(L / 30))
        s = F(n, lambda f: (100 + 18 * max(0.0, math.sin(2 * math.pi * f / per)),) * 2, tol=1.5)
        return [("front", Layer("anger", [gr("mark", arcs + [st(c, 7)], s=(150, 150))], parent="neck", p=(px, py), s=s))]
    return spec
