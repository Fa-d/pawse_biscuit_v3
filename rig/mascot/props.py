"""Props and effects.  Each function returns a *spec*: spec(char, T, n) -> [(slot, Layer), ...].

Slots (see Character.build):  'top' over everything, 'front' in front of the head, 'mid' between arms and feet,
'back' behind the character, 'hand.R' / 'hand.L' held in a paw (drawn under the paw), 'hand.R.over' / 'hand.L.over'.
Nothing here depends on which mascot is performing; positions come from the rig or are canvas coordinates.
"""
from __future__ import annotations

import math

import numpy as np

from .clip import Track, ease
from .geom import smooth
from .lottie import Anim, Layer, Path, el, fl, gr, rc, rgb, sh, st, tm

C = dict(
    yellow=rgb("#FFD93D"), gold=rgb("#FFC93C"), darkgold=rgb("#E8A317"), teal=rgb("#4ECDC4"), lilac=rgb("#AA96DA"),
    coral=rgb("#FF6B6B"), mint=rgb("#95E1D3"), blue=rgb("#4A90E2"), lightblue=rgb("#BFE3FF"), card=rgb("#2E3A4B"),
    cardline=rgb("#5B6B80"), lid=rgb("#9481CF"), board=rgb("#B5835A"), white=[1.0, 1.0, 1.0], dark=rgb("#3B2A20"),
    handle=rgb("#9C7A3C"), grey=rgb("#9AA5B1"), clip=rgb("#7A7A7A"), orange=rgb("#FF8A3D"), pink=rgb("#FF9AA2"),
    cream=rgb("#FFF4E6"), dust=rgb("#E9DCCB"), sky=rgb("#8FD3FF"), green=rgb("#4CAF50"),
)


def K(n, *keys, tol=None):
    """Sample keyframes [(t, value, ease)] into a per-frame Anim (the fitter turns it back into few keys)."""
    tr = Track(None)
    for k in keys:
        tr.key(*k)
    return Anim([tr.at(f) for f in range(n)], tol=tol)


def KH(n, *keys):
    """Hold (stepped) keys [(t, value)]."""
    tr = Track(None)
    for t, v in keys:
        tr.key(t, v, "hold")
    return Anim([tr.at(f) for f in range(n)], hold=True)


def F(n, fn, hold=False, tol=None):
    return Anim([fn(f) for f in range(n)], hold=hold, tol=tol)


def star4(c, R, k=0.32):
    pts = []
    for q in range(8):
        r = R if q % 2 == 0 else R * k
        a = -math.pi / 2 + q * math.pi / 4
        pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    return Path(pts, closed=True)


def star5(c, R, k=0.45, rot=-90):
    pts = []
    for q in range(10):
        r = R if q % 2 == 0 else R * k
        a = math.radians(rot) + q * math.pi / 5
        pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    return Path(pts, closed=True)


def world(char, T, f, p):
    """Rest-pose point p carried by the root (scale, squash, jump) at frame f -> canvas coordinates."""
    sc = T["root.scale"][f]
    x = char.CX + T["root.x"][f] + (p[0] - char.CX) * sc * T["root.sx"][f]
    y = char.GROUND + T["root.y"][f] + (p[1] - char.GROUND) * sc * T["root.sy"][f]
    return (x, y)


# ------------------------------------------------------------------ sparkles, dots, z's
def sparkles(items, slot="top", rot=90, peak=1.2):
    """items: [(x, y, R, colour, t0)]  -- pops in over 12 frames, gone 14 frames later, slowly turning."""
    def spec(char, T, n):
        out = []
        for q, (x, y, R, col, t0) in enumerate(items):
            s = K(n, (0, (0, 0)), (max(t0, 0), (0, 0), "hold"), (t0 + 12, (peak * 100, peak * 100), "back"), (t0 + 26, (0, 0), "io"), tol=1.5)
            r = F(n, lambda f, q=q: rot * f / max(n - 1, 1) + 20 * q, tol=1.0)
            out.append((slot, Layer(f"sparkle {q}", [gr("sparkle", [sh(star4((0, 0), R)), fl(C[col])])], p=(x, y), s=s, r=r)))
        return out
    return spec


def _anchor(char, rel, f=0):
    """Offset for effect positions: (0, 0) for canvas coordinates, or the top of the head when rel is set."""
    return char.crown_world(f) if rel else (0.0, 0.0)


def thought_dots(items, pop=12, t_out=160, t_gone=180, bob=3.0, rel=False):
    """items: [(x, y, d, t0)] dark bubbles that pop one after another and drift a little.
    rel=True: x, y are offsets from the top of the mascot's head (so they sit right for any mascot)."""
    def spec(char, T, n):
        ox, oy = _anchor(char, rel)
        out = []
        for q, (x, y, d, t0) in enumerate(items):
            x, y = x + ox, y + oy
            s = K(n, (0, (0, 0)), (t0, (0, 0), "hold"), (t0 + pop, (100, 100), "back"), (t_out, (100, 100), "hold"), (t_gone, (0, 0), "in"))
            p = F(n, lambda f, x=x, y=y, q=q: (x, y + bob * math.sin(2 * math.pi * (f / 90.0 + q * 0.22))))
            out.append(("top", Layer(f"dot {q}", [gr("dot", [el((0, 0), (d, d)), fl(C["dark"], 75)])], p=p, s=s)))
        return out[::-1]
    return spec


def zzz(items, drift=(14, -36), life=70, fade_in=20, period=None, rel=False):
    """items: [(x, y, size, t0)] little z's that rise and fade.  rel=True: offsets from the top of the head."""
    def spec(char, T, n):
        ox, oy = _anchor(char, rel)
        out = []
        for q, (x, y, sz, t0) in enumerate(items):
            x, y = x + ox, y + oy
            h = sz / 2.0
            z = Path([(-h, -h), (h, -h), (-h, h), (h, h)], closed=False)
            starts = [t0] if not period else list(range(t0, n, period))
            def life_u(f, starts=starts):
                for s0 in starts:
                    if s0 <= f <= s0 + life:
                        return (f - s0) / life
                return None
            def pos(f, x=x, y=y):
                u = life_u(f)
                u = 0.0 if u is None else ease("out", u) * 0.6 + u * 0.4
                return (x + drift[0] * u + 4 * math.sin(u * 6.0), y + drift[1] * u)
            def op(f):
                u = life_u(f)
                if u is None:
                    return 0.0
                a = min(1.0, u * life / fade_in)
                b = min(1.0, (1 - u) * life / (life - fade_in))
                return 100 * min(a, b)
            def scl(f):
                u = life_u(f)
                u = 0.0 if u is None else u
                k = 70 + 45 * ease("out", min(1.0, u * 2.2))
                return (k, k)
            rr = F(n, lambda f: -8 + 10 * math.sin((life_u(f) or 0.0) * 5.0), tol=1.0)
            out.append(("top", Layer(f"z {q}", [gr("z", [sh(z), st(C["dark"], 5)])], p=F(n, pos, tol=0.6), o=F(n, op, tol=2.5), s=F(n, scl, tol=1.5), r=rr)))
        return out[::-1]
    return spec


def dust(t0, x, y=None, side=0, n_puffs=3, size=18.0, slot="back", gap=44.0):
    """Small puffs kicked up at frame t0 around x (canvas).  They start `gap` away from x (just outside the feet)
    and roll outwards; side = -1 / +1 sends them all one way (a single footfall)."""
    def spec(char, T, n):
        gy = (char.GROUND if y is None else y)
        out = []
        for q in range(n_puffs):
            dirx = (-1.0 if q % 2 == 0 else 1.0) if side == 0 else side
            spread = 26 + 16 * (q // 2) + 10 * q
            d = size * (1.0 - 0.18 * q)
            def pos(f, dirx=dirx, spread=spread, q=q):
                u = min(max((f - t0) / 22.0, 0.0), 1.0)
                e = ease("out", u)
                return (x + dirx * (gap + spread * e), gy - 4 - (10 + 5 * q) * e + 6 * u * u)
            def scl(f, q=q):
                u = min(max((f - t0) / 22.0, 0.0), 1.0)
                k = 100 * (0.35 + 0.9 * ease("out", u)) if f >= t0 else 0.0
                return (k, k)
            def op(f):
                if f < t0 or f > t0 + 22:
                    return 0.0
                u = (f - t0) / 22.0
                return 75 * (1 - u) ** 1.2
            out.append((slot, Layer(f"dust {t0}-{x:.0f}-{q}", [gr("puff", [el((0, 0), (d, d * 0.86)), fl(C["dust"])])], p=F(n, pos, tol=0.8), s=F(n, scl, tol=2.0), o=F(n, op, tol=3.0))))
        return out
    return spec


def sweat_drop(t0, life=46, at=(374.0, 190.0), fall=46.0, side=1.0):
    """A worried little drop that slides down the temple.  Positions are in the head's rest-pose coordinates."""
    def spec(char, T, n):
        drop = smooth([(0, -9), (5, 0), (0, 6), (-5, 0)], closed=True, tension=0.42, sharp={0: 0.35})
        def pos(f):
            u = min(max((f - t0) / life, 0.0), 1.0)
            return (at[0] + side * 3 * u, at[1] + fall * ease("in", u) * 0.6 + fall * 0.4 * u)
        def op(f):
            if f < t0 or f > t0 + life:
                return 0.0
            u = (f - t0) / life
            return 100 * min(1.0, u * 8) * min(1.0, (1 - u) * 5)
        def scl(f):
            u = min(max((f - t0) / life, 0.0), 1.0)
            return (100 * (0.7 + 0.3 * min(1.0, u * 6)), 100 * (0.7 + 0.5 * min(1.0, u * 6)))
        lay = Layer(f"sweat {t0}", [gr("shine", [el((-1.5, 0.5), (3, 4)), fl(C["white"], 80)]), gr("drop", [sh(drop), fl(C["sky"])])],
                    parent="neck", p=F(n, pos), o=F(n, op), s=F(n, scl))
        return [("front", lay)]
    return spec


# ------------------------------------------------------------------ things held in a paw
def held(char, T, side, items, pose, grip=(0.0, 17.0), tilt=0.0, scale=1.0, nm="prop", swing=None):
    """Wrap upright-drawn shape items so they sit in the paw and stay upright while the arm is in `pose`.

    The items are drawn around (0, 0) = the point that rests in the paw, y up = negative (screen convention).
    swing: optional per-frame list of extra degrees (e.g. a bell swinging about the grip).
    """
    sgn = 1.0 if side == "R" else -1.0
    v = char.pose(pose)["v"]
    r0 = sgn * (v[0] + v[1] + v[2]) + tilt
    rot = r0 if swing is None else Anim([r0 + float(x) for x in swing])
    return gr(nm, items, p=grip, r=rot, s=(scale * 100, scale * 100))


def phone(side="R", pose="hold", t_bars=(0, 12, 24), t_out=160, t_gone=180, tilt=6.0):
    """A phone with a little bar chart that grows on screen."""
    def spec(char, T, n):
        bars = []
        for q, (x, h) in enumerate(((-15, 22), (0, 38), (15, 54))):
            t0 = t_bars[q]
            sc = K(n, (0, (100, 0)), (t0, (100, 0), "hold"), (t0 + 20, (100, 100), "back"), (t_out, (100, 100), "hold"), (t_gone, (100, 0), "in"))
            bars.append(gr(f"bar {q}", [rc((x, -6 - h / 2.0), (10, h), 3), fl(C["blue"])], a=(x, -6), p=(x, -6), s=sc))
        tt = t_bars[2] + 22
        star = gr("spark", [sh(star4((15, -70), 7)), fl(C["yellow"])], a=(15, -70), p=(15, -70),
                  s=K(n, (0, (0, 0)), (tt, (0, 0), "hold"), (tt + 8, (130, 130), "back"), (tt + 26, (0, 0), "io")))
        items = [star] + bars[::-1] + [
            gr("glare", [sh(Path([(-20, -78), (-8, -78), (-22, -52), (-26, -58)], closed=True)), fl(C["white"], 45)]),
            gr("screen", [rc((0, -42), (52, 84), 8), fl(C["lightblue"])]),
            gr("phone", [rc((0, -40), (64, 104), 14), fl(C["dark"])]),
        ]
        return [(f"hand.{side}", held(char, T, side, items, pose, tilt=tilt, nm="phone"))]
    return spec


def bell(side="R", pose="hold_up", period=24, swing=22.0, scale=0.82):
    """A hand bell that hangs from the paw and swings; the clapper trails behind and ring marks pulse."""
    def spec(char, T, n):
        sw = [-swing * math.cos(2 * math.pi * f / period) for f in range(n)]
        clap = [-swing * 1.5 * math.cos(2 * math.pi * (f / period - 0.18)) for f in range(n)]
        dome = smooth([(-36, 74), (-30, 44), (-16, 18), (0, 10), (16, 18), (30, 44), (36, 74)], closed=True, tension=0.34, sharp={0: 0.0, 6: 0.0})
        bell_items = [
            gr("shine", [el((-13, 40), (8, 20)), fl(C["white"], 50)]),
            gr("rim", [rc((0, 74), (82, 11), 5.5), fl(C["darkgold"])]),
            gr("bell", [sh(dome), fl(C["gold"])]),
            gr("clapper", [el((0, 86), (17, 17)), fl(C["darkgold"])], a=(0, 20), p=(0, 20), r=Anim([c_ - s_ for c_, s_ in zip(clap, sw)])),
            gr("handle", [rc((0, 2), (11, 24), 4), fl(C["handle"])]),
        ]
        rings = []
        for q, sx in enumerate((-1, 1)):
            arc = Path([(sx * 52, 20), (sx * 52, 76)], i=[(0, 0), (sx * 12, -20)], o=[(sx * 12, 20), (0, 0)], closed=False)
            pulse = [0.5 - 0.5 * math.cos(2 * math.pi * (f / (period / 2.0) + 0.5 * q)) for f in range(n)]
            rings.append(gr(f"ring {q}", [sh(arc), st(C["darkgold"], 5)], a=(sx * 52, 48), p=(sx * 52, 48),
                            s=Anim([(80 + 35 * u, 80 + 35 * u) for u in pulse]), o=Anim([100 * u for u in pulse])))
        return [
            (f"hand.{side}", held(char, T, side, bell_items, pose, scale=scale, nm="bell", swing=sw)),
            (f"hand.{side}", held(char, T, side, rings, pose, scale=scale, nm="ring marks")),
        ]
    return spec


def clipboard(side="L", pose="hold", t_draw=(0, 50), t_out=130, t_gone=150, tilt=-5.0):
    """A clipboard whose chart line draws itself."""
    def spec(char, T, n):
        line = lambda y, x0, x1: sh(Path([(x0, y), (x1, y)], closed=False))
        chart = Path([(-25, -24), (-10, -38), (5, -31), (25, -54)], closed=False)
        end = K(n, (t_draw[0], 0.0), (t_draw[1], 100.0, "io"), (t_out, 100.0, "hold"), (t_gone, 0.0, "io"))
        dot_s = K(n, (0, (0, 0)), (t_draw[1] - 4, (0, 0), "hold"), (t_draw[1] + 6, (100, 100), "back"), (t_out, (100, 100), "hold"), (t_out + 8, (0, 0), "in"))
        items = [
            gr("chart dot", [el((25, -54), (11, 11)), fl(C["teal"])], a=(25, -54), p=(25, -54), s=dot_s),
            gr("chart", [sh(chart), st(C["teal"], 5), tm(0, end)]),
            gr("lines", [line(-86, -25, 12), line(-74, -25, 25), st(C["grey"], 4)]),
            gr("clip", [rc((0, -108), (34, 14), 4), fl(C["clip"])]),
            gr("paper", [rc((0, -50), (70, 92), 4), fl(C["white"])]),
            gr("board", [rc((0, -56), (84, 112), 8), fl(C["board"])]),
        ]
        return [(f"hand.{side}", held(char, T, side, items, pose, tilt=tilt, nm="clipboard"))]
    return spec


def badge(side="R", pose="hold_up", t_pop=24, n_frames=None):
    """A medal that pops into the raised paw with turning rays."""
    def spec(char, T, n):
        c = (0, -46)
        pop = K(n, (0, (0, 0)), (t_pop, (0, 0), "hold"), (t_pop + 16, (115, 115), "back"), (t_pop + 24, (100, 100), "io"))
        rays = []
        for q in range(8):
            a = q * math.pi / 4
            rays.append(sh(Path([(c[0] + 46 * math.cos(a), c[1] + 46 * math.sin(a)), (c[0] + 68 * math.cos(a), c[1] + 68 * math.sin(a))], closed=False)))
        ray_grp = gr("rays", rays + [st(C["gold"], 6)], a=c, p=c, s=pop, r=F(n, lambda f: 60.0 * f / max(n - 1, 1)),
                     o=K(n, (0, 0.0), (t_pop, 0.0, "hold"), (t_pop + 16, 100.0, "io")))
        rib = lambda k: sh(Path([(c[0] + k * 18, c[1] + 20), (c[0] + k * 28, c[1] + 64), (c[0] + k * 8, c[1] + 54), (c[0] + k * 4, c[1] + 26)], closed=True))
        medal = gr("badge", [
            gr("star", [sh(star5(c, 20, 0.42)), fl(C["white"])]),
            gr("medal", [el(c, (58, 58)), fl(C["gold"])]),
            gr("medal edge", [el(c, (72, 72)), fl(C["darkgold"])]),
            gr("ribbons", [rib(1), rib(-1), fl(C["coral"])]),
        ], a=(0, 0), p=(0, 0), s=pop)
        return [(f"hand.{side}", held(char, T, side, [medal, ray_grp], pose, nm="badge"))]
    return spec


# ------------------------------------------------------------------ scenery
def card(top=395.0):
    """Foreground card the mascot pops up from behind."""
    def spec(char, T, n):
        cy = top + 75.0
        return [("top", Layer("card", [
            gr("dot", [el((380, cy - 8), (36, 36)), fl(C["teal"])]),
            gr("line", [rc((180, cy + 8), (110, 14), 7), fl(C["cardline"])]),
            gr("line", [rc((200, cy - 22), (150, 14), 7), fl(C["cardline"])]),
            gr("card", [rc((256, cy), (360, 150), 26), fl(C["card"])]),
        ]))]
    return spec


def aura(color="teal", period=480, center=None, size=360.0):
    """Breathing ring and soft glow behind the mascot.  One full swell per `period` (ease in-out, like the originals).
    Centred on the figure (whatever its stance) unless `center` gives root-space coordinates."""
    def spec(char, T, n, center=center):
        center = char.middle_root(0) if center is None else center
        def up(f):
            u = (f % period) / float(period)
            return ease("io", u * 2) if u <= 0.5 else 1.0 - ease("io", (u - 0.5) * 2)
        ring = Layer("aura", [gr("aura", [el(center, (size, size)), st(C[color], 10, 60)])], parent="root", a=center, p=center,
                     s=F(n, lambda f: (92 + 16 * up(f), 92 + 16 * up(f))), o=F(n, lambda f: 30 + 60 * up(f)))
        glow = Layer("aura glow", [gr("glow", [el(center, (size * 5 / 6, size * 5 / 6)), fl(C[color], 14)])], parent="root", a=center, p=center,
                     s=F(n, lambda f: (90 + 22 * up(f), 90 + 22 * up(f))))
        return [("back", ring), ("back", glow)]
    return spec


def cloud_on_string(side="R", offset=(34.0, -208.0), bob=5.0, period=60, sway=7.0, scale=1.0, sway_period=None, shapes=None, nm="cloud"):
    """A cloud with a tick that floats above the paw like a balloon; the string trails with a soft lag.
    sway_period defaults to two bob periods; a looping clip needs one that divides its length.
    shapes: draw something else on the string (a balloon), centred on (0, 0) with the string tied at (0, 38)."""
    sway_period = period * 2.0 if sway_period is None else sway_period

    def spec(char, T, n):
        from .clip import spring_follow
        loop = char.clip.loop
        hand = np.array([char.hand_to_world(side, f, (0.0, 17.0)) for f in range(n)])
        target = hand + np.array(offset)
        target[:, 1] += [bob * math.sin(2 * math.pi * f / period) for f in range(n)]
        target[:, 0] += [sway * math.sin(2 * math.pi * (f / sway_period + 0.1)) for f in range(n)]
        pos = spring_follow(target, freq=0.9, damp=0.5, loop=loop)
        lean = (target[:, 0] - pos[:, 0]) * 0.6
        cloud_shapes = shapes if shapes is not None else [
            gr("check", [sh(Path([(-16, 6), (-4, 18), (20, -8)], closed=False)), st(C["blue"], 7)]),
            gr("cloud shine", [el((-20, -20), (30, 14)), fl(C["lightblue"], 70)]),
            gr("cloud", [el((-44, 6), (70, 54)), el((0, -12), (84, 70)), el((46, 4), (72, 56)), rc((0, 20), (150, 40), 20), fl(C["white"])]),
        ]
        cloud = Layer(nm, cloud_shapes, a=(0, 0), p=Anim([tuple(p) for p in pos]), r=Anim(list(np.clip(lean, -9, 9))),
                      s=(scale * 100, scale * 100))

        def string(f):
            a = hand[f]
            b = (pos[f][0], pos[f][1] + 38.0 * scale)
            dx, dy = b[0] - a[0], b[1] - a[1]
            sag = 10.0 + 0.5 * (target[f][0] - pos[f][0])
            return Path([tuple(a), b], i=[(0, 0), (-dx * 0.1 - sag, -dy * 0.36)], o=[(dx * 0.1 + sag, dy * 0.36), (0, 0)], closed=False)

        line = Layer("string" if nm == "cloud" else f"{nm} string", [gr("string", [sh(F(n, string)), st(C["cardline"], 3)])])
        return [("top", cloud), ("front", line)]
    return spec


def gift(t_shake=(10, 22), t_dip=36, t_pop=40, t_land=80, cx=256.0, ground=None, k=1.0):
    """A present: the lid dips, pops off with sparkles, tumbles away and fades.  k scales the box."""
    def spec(char, T, n):
        gy = (char.GROUND if ground is None else ground) + 8.0     # the box stands a little in front of the ground line
        ly = gy - 100.0 * k                                         # lid centre
        K100 = lambda a, b: (a * k, b * k)
        wob = lambda f: (3.0 * math.sin((f - t_shake[0]) * 1.3) * max(0.0, 1 - abs((f - (t_shake[0] + t_shake[1]) / 2.0) / ((t_shake[1] - t_shake[0]) / 2.0))) if t_shake[0] <= f <= t_shake[1] else 0.0)
        box = Layer("box", [
            gr("ribbon", [rc((0, -46), (24, 92), 0), fl(C["gold"])]),
            gr("box", [rc((0, -46), (140, 92), 10), fl(C["lilac"])]),
        ], a=(0, 0), p=(cx, gy), r=F(n, wob),
            s=K(n, (0, K100(100, 100)), (t_dip - 6, K100(100, 100), "hold"), (t_dip, K100(104, 94), "out"), (t_pop + 4, K100(96, 106), "out"), (t_pop + 18, K100(100, 100), "back")))
        lid_p = K(n, (0, (cx, ly)), (t_dip - 6, (cx, ly), "hold"), (t_dip, (cx, ly + 7 * k), "out"), (t_pop + 16, (cx + 90, ly - 150), "out"), (t_land, (cx + 180, gy), "in"))
        lid = Layer("lid", [
            gr("bow", [el((-18, -24), (34, 22)), el((18, -24), (34, 22)), fl(C["gold"])]),
            gr("lid ribbon", [rc((0, 0), (24, 30), 0), fl(C["gold"])]),
            gr("lid", [rc((0, 0), (158, 30), 10), fl(C["lid"])]),
        ], a=(0, 0), p=lid_p, s=K100(100, 100),
            r=F(n, lambda f: wob(f) + (0.0 if f < t_pop else 150.0 * min(1.0, (f - t_pop) / float(t_land - t_pop)))),
            o=K(n, (0, 100.0), (t_land - 12, 100.0, "hold"), (t_land, 0.0, "io")))
        out = [("mid", lid), ("mid", box)]
        cols = ["orange", "teal", "yellow", "coral", "mint"]
        for q in range(5):
            ang = math.radians(200 + q * 35)
            tx, ty = cx + 130 * math.cos(ang), ly + 4 + 130 * math.sin(ang)
            sp = Layer(f"gift spark {q}", [gr("sparkle", [sh(star4((0, 0), 18)), fl(C[cols[q]])])],
                       p=K(n, (0, (cx, ly + 4)), (t_pop, (cx, ly + 4), "hold"), (t_pop + 26, (tx, ty), "out")),
                       s=K(n, (0, (0, 0)), (t_pop, (0, 0), "hold"), (t_pop + 12, (120, 120), "back"), (t_pop + 50, (0, 0), "io")),
                       r=F(n, lambda f, q=q: 90.0 * max(0, f - t_pop) / 60.0 + 20 * q))
            out.insert(0, ("top", sp))
        return out
    return spec


def confetti(t0=30, origin=(256.0, 250.0), count=14, t_end=150, seed=7):
    """Paper confetti: bursts out, then flutters down and fades."""
    def spec(char, T, n):
        rng = np.random.RandomState(seed)
        cols = ["coral", "teal", "yellow", "lilac", "mint", "orange", "blue"]
        out = []
        for q in range(count):
            ang = 2 * math.pi * (q + rng.uniform(-0.25, 0.25)) / count
            dist = 150 + 70 * rng.rand()
            tx = origin[0] + dist * math.cos(ang) * 1.05
            ty = origin[1] + dist * math.sin(ang) * 0.95 - 20
            drift = (rng.uniform(-14, 14), 70 + 30 * rng.rand())
            w, h = (16, 9) if q % 3 else (11, 11)
            per = 26 + 14 * rng.rand()
            ph = rng.rand()
            spin = (540 if q % 2 == 0 else -540) * (0.7 + 0.6 * rng.rand())
            pos = K(n, (0, origin), (t0, origin, "hold"), (t0 + 24, (tx, ty), "out"), (t_end, (tx + drift[0], ty + drift[1]), "lin"), tol=0.7)
            flut = F(n, lambda f, per=per, ph=ph: (100 * math.cos(2 * math.pi * (max(f - t0, 0) / per + ph)) if f >= t0 else 100, 100), tol=4.0)
            lay = Layer(f"confetti {q}", [gr("piece", [rc((0, 0), (w, h), 2), fl(C[cols[q % len(cols)]])])], p=pos, s=flut,
                        r=F(n, lambda f, spin=spin: spin * max(f - t0, 0) / float(t_end - t0), tol=2.0),
                        o=K(n, (0, 0.0), (t0, 0.0, "hold"), (t0 + 2, 100.0, "lin"), (t_end - 15, 100.0, "hold"), (t_end, 0.0, "io")))
            out.append(("top", lay))
        return out
    return spec


def breath_puff(t0, life=70, count=3, at=(256.0, 288.0)):
    """Soft little clouds leaving the mouth on the out-breath.  Coordinates are the head's rest pose."""
    def spec(char, T, n):
        out = []
        for q in range(count):
            ts = t0 + q * 14
            side = (-1.0, 1.0, 0.0)[q % 3]
            def u(f, ts=ts):
                return min(max((f - ts) / float(life), 0.0), 1.0)
            pos = F(n, lambda f, side=side, u=u: (at[0] + side * 26 * ease("out", u(f)), at[1] + 46 * ease("out", u(f))), tol=0.8)
            scl = F(n, lambda f, u=u: (40 + 90 * ease("out", u(f)),) * 2, tol=2.0)
            op = F(n, lambda f, u=u, ts=ts: 0.0 if (f < ts or f > ts + life) else 42 * min(1.0, u(f) * 5) * (1 - u(f)) ** 1.3, tol=2.0)
            out.append(("front", Layer(f"breath {q}", [gr("puff", [el((0, 0), (22, 18)), fl(C["white"])])], parent="neck", p=pos, s=scl, o=op)))
        return out
    return spec


def orbs(count=3, period=240, center=None, rx=176.0, ry=40.0, color="lilac", size=13.0, drop=30.0):
    """Little lights circling the mascot: in front on the near half of the orbit, behind on the far half.
    The orbit sits `drop` below the middle of the figure unless `center` gives canvas coordinates."""
    def spec(char, T, n, center=center):
        if center is None:
            m = char.middle_root(0)
            center = world(char, T, 0, (m[0], m[1] + drop))
            center = (center[0], center[1] - T["root.y"][0])
        out = []
        for q in range(count):
            th = lambda f, q=q: 2 * math.pi * (f / float(period) + q / float(count))
            lift = lambda f: T["root.y"][f] * 0.6
            pos = F(n, lambda f, th=th: (center[0] + rx * math.cos(th(f)), center[1] + ry * math.sin(th(f)) + lift(f)), tol=0.6)
            near = lambda f, th=th: math.sin(th(f)) > 0
            scl = F(n, lambda f, th=th: (100 + 22 * math.sin(th(f)),) * 2, tol=1.5)
            shapes = lambda: [gr("glow", [el((0, 0), (size * 2.2, size * 2.2)), fl(C[color], 28)]), gr("orb", [el((0, 0), (size, size)), fl(C["white"], 92)])]
            out.append(("top", Layer(f"orb {q} near", shapes(), p=pos, s=scl, o=F(n, lambda f, near=near: 100 if near(f) else 0, hold=True))))
            out.append(("back", Layer(f"orb {q} far", shapes(), p=pos, s=scl, o=F(n, lambda f, near=near: 0 if near(f) else 100, hold=True))))
        return out
    return spec


# ------------------------------------------------------------------ extras for the alternate takes
def butterfly(path, t_land, t_leave, perch=(256.0, 246.0), size=1.0, flap_fly=10, flap_sit=44, colors=("lilac", "teal")):
    """A butterfly that flies along `path` [(t, x, y)], sits on the mascot's nose from t_land to t_leave, then flies on.

    perch is given in the head's rest-pose coordinates, so the butterfly rides every head movement while it sits.
    """
    def spec(char, T, n):
        ts = [p[0] for p in path]
        xs = [p[1] for p in path]
        ys = [p[2] for p in path]

        def cr(vals, t):                                   # Catmull-Rom through the path points
            if t <= ts[0]:
                return vals[0]
            if t >= ts[-1]:
                return vals[-1]
            k = max(i for i in range(len(ts) - 1) if ts[i] <= t)
            u = (t - ts[k]) / float(ts[k + 1] - ts[k])
            p0, p1, p2, p3 = vals[max(k - 1, 0)], vals[k], vals[k + 1], vals[min(k + 2, len(vals) - 1)]
            return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)

        def free(f):
            wob = 5.0 * math.sin(f * 0.55) * (0.0 if t_land - 4 <= f <= t_leave + 2 else 1.0)
            return (cr(xs, f), cr(ys, f) + wob)

        def pos(f):
            if t_land <= f <= t_leave:
                return char.head_to_world(f, perch)
            if t_land - 10 < f < t_land:                   # glide onto the nose
                u = ease("io", (f - (t_land - 10)) / 10.0)
                a, b = free(t_land - 10), char.head_to_world(f, perch)
                return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
            if t_leave < f < t_leave + 10:
                u = ease("io", (f - t_leave) / 10.0)
                a, b = char.head_to_world(f, perch), free(t_leave + 10)
                return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
            return free(f)

        P_ = [pos(f) for f in range(n)]

        def tilt(f):
            if t_land <= f <= t_leave:
                return T["head.rot"][f]
            a, b = P_[max(f - 2, 0)], P_[min(f + 2, n - 1)]
            return max(-28.0, min(28.0, (b[0] - a[0]) * 2.2))

        def flap(f):
            sitting = t_land <= f <= t_leave
            if sitting:
                u = 0.5 + 0.5 * math.cos(2 * math.pi * (f - t_land) / flap_sit)
                return (100 * (0.35 + 0.65 * u), 100)
            return (100 * (0.22 + 0.78 * abs(math.cos(math.pi * f / flap_fly))), 100)

        wing = lambda k: smooth([(k * 2, -2), (k * 14, -22), (k * 26, -18), (k * 24, -4), (k * 12, 2)], closed=True, tension=0.4)
        low = lambda k: smooth([(k * 2, 2), (k * 16, 4), (k * 20, 16), (k * 10, 20), (k * 3, 10)], closed=True, tension=0.4)
        shapes = [
            gr("body", [rc((0, 0), (5, 22), 2.5), fl(C["dark"])]),
            gr("wings", [
                gr("dots", [el((15, -11), (6, 6)), el((-15, -11), (6, 6)), fl(C["white"], 85)]),
                gr("lower", [sh(low(1)), sh(low(-1)), fl(C[colors[1]])]),
                gr("upper", [sh(wing(1)), sh(wing(-1)), fl(C[colors[0]])]),
            ], s=F(n, flap, tol=3.0)),
        ]
        vis = F(n, lambda f: 100 if ts[0] <= f <= ts[-1] else 0, hold=True)
        lay = Layer("butterfly", shapes, a=(0, 6), p=Anim(P_, tol=0.5), r=F(n, tilt, tol=1.2), s=(size * 100, size * 100), o=vis)
        return [("top", lay)]
    return spec


def sneeze_burst(t0, at=(256.0, 262.0), count=7, reach=74.0, seed=3):
    """Little droplets and puff lines shooting forwards from the nose at frame t0 (head rest-pose coordinates)."""
    def spec(char, T, n):
        rng = np.random.RandomState(seed)
        out = []
        o_ = char.head_to_world(t0, at)
        for q in range(count):
            ang = math.radians(60 + 60 * q / (count - 1) + rng.uniform(-6, 6))     # a fan pointing down and out
            d = reach * (0.7 + 0.5 * rng.rand())
            tx, ty = o_[0] + d * math.cos(ang) * (1.0 if q % 2 else -1.0) * 1.2, o_[1] + d * math.sin(ang) * 0.75
            life = 16 + int(8 * rng.rand())
            u = lambda f, life=life: min(max((f - t0) / float(life), 0.0), 1.0)
            pos = F(n, lambda f, tx=tx, ty=ty, u=u: (o_[0] + (tx - o_[0]) * ease("out", u(f)), o_[1] + (ty - o_[1]) * ease("out", u(f)) + 14 * u(f) ** 2), tol=0.8)
            op = F(n, lambda f, u=u, life=life: 0.0 if (f < t0 or f > t0 + life) else 90 * (1 - u(f)) ** 0.8, tol=3.0)
            d0 = 5 + 4 * rng.rand()
            out.append(("top", Layer(f"sneeze {q}", [gr("drop", [el((0, 0), (d0, d0)), fl(C["sky"] if q % 3 else C["white"])])], p=pos, o=op,
                                     s=F(n, lambda f, u=u: (100 - 45 * u(f),) * 2, tol=3.0))))
        return out
    return spec


def sleep_bubble(breaths, t_pop, at=(262.0, 266.0), big=46.0):
    """A sleep bubble on the nose: swells and shrinks with each breath [(t_in, t_out, size 0..1)], then pops at t_pop."""
    def spec(char, T, n):
        keys = [(0, 0.0)]
        for t_in, t_out, sz in breaths:
            keys.append((t_in, keys[-1][1], "hold"))
            keys.append(((t_in + t_out) // 2, sz, "io"))
            keys.append((t_out, sz * 0.45, "io"))
        last = keys[-1][1]
        keys += [(t_pop - 10, last, "hold"), (t_pop, 1.12, "in"), (t_pop + 1, 0.0, "hold")]
        tr = Track(None)
        for k in keys:
            tr.key(*k)
        size = [max(0.0, tr.at(f)) for f in range(n)]
        d = big
        bub = Layer("sleep bubble", [
            gr("shine", [el((-d * 0.2, -d * 0.2), (d * 0.22, d * 0.14)), fl(C["white"], 85)], r=-30),
            gr("rim", [el((0, 0), (d, d)), st(C["white"], 2.5, 70)]),
            gr("bubble", [el((0, 0), (d, d)), fl(C["sky"], 55)]),
        ], parent="neck", a=(-d * 0.42, 0), p=at, s=Anim([(100 * v, 100 * v) for v in size], tol=0.8),
            o=F(n, lambda f: 100 if size[f] > 0.02 else 0, hold=True))
        out = [("front", bub)]
        for q in range(6):                                  # pop marks
            a = q * math.pi / 3 + 0.3
            c0 = (at[0] + d * 0.6 + d * 0.62 * math.cos(a), at[1] + d * 0.62 * math.sin(a))
            c1 = (at[0] + d * 0.6 + d * 0.95 * math.cos(a), at[1] + d * 0.95 * math.sin(a))
            out.append(("front", Layer(f"pop {q}", [gr("mark", [sh(Path([c0, c1], closed=False)), st(C["sky"], 4)])], parent="neck",
                                       o=K(n, (0, 0.0), (t_pop, 100.0, "hold"), (t_pop + 9, 0.0, "io"), tol=3.0),
                                       a=(at[0] + d * 0.6, at[1]), p=(at[0] + d * 0.6, at[1]),
                                       s=K(n, (0, (70, 70)), (t_pop, (70, 70), "hold"), (t_pop + 9, (125, 125), "out"), tol=2.0))))
        return out
    return spec


def tear(t0, life=40, at=(346.0, 236.0)):
    """A tiny happy / sleepy tear at the corner of the eye (head rest-pose coordinates)."""
    def spec(char, T, n):
        drop = smooth([(0, -6), (4, 1), (0, 5), (-4, 1)], closed=True, tension=0.42, sharp={0: 0.35})
        u = lambda f: min(max((f - t0) / float(life), 0.0), 1.0)
        return [("front", Layer(f"tear {t0}", [gr("tear", [sh(drop), fl(C["sky"])])], parent="neck",
                                p=F(n, lambda f: (at[0] + 2 * u(f), at[1] + 10 * u(f) ** 2), tol=0.5),
                                s=F(n, lambda f: (100 * min(1.0, u(f) * 5),) * 2, tol=2.0),
                                o=F(n, lambda f: 0.0 if (f < t0 or f > t0 + life) else 100 * min(1.0, (1 - u(f)) * 4), tol=3.0)))]
    return spec
