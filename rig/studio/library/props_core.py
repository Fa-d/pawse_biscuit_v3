"""The first eight held props (from v3), made loop-safe.

Changes from v3: the medal no longer vanishes at the loop point (it stays in the paw and its rays turn by exactly
one ray per loop); the gift box closes again before the loop ends (the lid flies off, then drops back on); the
balloon's sway period always divides the loop.
"""
from __future__ import annotations

from mascot import props as P

from ..registry import prop
from .common import C, F, K, Layer, Path, acted, col, el, env, fl, gr, grip, heart_path, math, rc, sh, st, star4, star5


# ------------------------------------------------------------------ tech and work
STEADY_PHONE = ("phone_call", "selfie", "texting")      # motions that use the phone all through the loop


@prop("phone", "Phone", "📱", noun="a phone", pose="hold", category="tech", peak=0.5)
def phone(x):
    mv = getattr(x.plan, "motion", None)
    if mv in STEADY_PHONE:
        return _phone_in_paw(x, mv)
    return P.phone(x.side, "hold", t_bars=(4, 12, 20), t_out=x.L - 16, t_gone=x.L)


def _phone_in_paw(x, mv):
    """The phone for the motions that use it the whole time: held to the ear, up for a selfie, or texting (the
    messages pop up on its screen one after another and clear just before the loop ends)."""
    side, L = x.side, x.L

    def spec(char, T, n):
        if mv == "selfie":                      # we see its back: the camera, a sticker on the case
            items = [
                gr("lens", [el((-15, -80), (13, 13)), el((-15, -62), (13, 13)), fl(C["ink"])]),
                gr("camera", [rc((-15, -71), (26, 42), 11), fl(C["steel"])]),
                gr("sticker", [sh(heart_path(9, 12, -30)), fl(C["gum"])]),
                gr("case", [rc((0, -46), (64, 106), 15), fl(C["lilac"])]),
            ]
            return [(f"hand.{side}", grip(char, T, side, items, upright=True, tilt=-8, nm="phone"))]
        dy = 34 if mv == "phone_call" else 0    # at the ear the paw holds it by the middle
        items = []
        if mv == "texting":
            for q, (bx, by, w, c, u0) in enumerate(((-7, -74, 36, "white", 0.06), (7, -52, 36, "teal", 0.32), (-7, -30, 30, "white", 0.58))):
                t0 = int(L * u0)
                sc = K(n, (0, (0, 0)), (t0, (0, 0), "hold"), (t0 + 8, (100, 100), "back"), (L - 10, (100, 100), "hold"), (L, (0, 0), "in"))
                kids = [gr("bubble", [rc((0, 0), (w, 14), 7), fl(C[c])])]
                if q == 2:
                    kids.insert(0, gr("dots", [el((d, 0), (4, 4)) for d in (-8, 0, 8)] + [fl(C["steel"])]))
                items.append(gr(f"message {q}", kids, a=(bx, by), p=(bx, by), s=sc))
        items += [
            gr("glare", [sh(Path([(-20, -78 + dy), (-8, -78 + dy), (-22, -52 + dy), (-26, -58 + dy)], closed=True)), fl(C["white"], 40)]),
            gr("screen", [rc((0, -42 + dy), (52, 84), 8), fl(C["lightblue"])]),
            gr("phone", [rc((0, -40 + dy), (64, 104), 14), fl(C["dark"])]),
        ]
        scale = dict(phone_call=0.82, texting=0.8).get(mv, 1.0)
        tilt = (-14.0 if side == "R" else 14.0) if mv == "phone_call" else 0.0      # its top leans in to the ear
        return [(f"hand.{side}", grip(char, T, side, items, upright=True, tilt=tilt, scale=scale, nm="phone"))]
    return spec


@prop("clipboard", "Clipboard", "📋", noun="a clipboard", paw="L", pose="hold", category="work", peak=0.7)
def clipboard(x):
    return P.clipboard(x.side, "hold", t_draw=(0, int(x.L * 0.45)), t_out=x.L - 18, t_gone=x.L)


@prop("bell", "Bell", "🔔", noun="a bell", pose="ring", category="object")
def bell(x):
    return P.bell(x.side, "ring", period=x.per(24), scale=0.9)


# ------------------------------------------------------------------ the medal: always in the paw, rays turning
@prop("badge", "Medal", "🏅", noun="a medal", pose="hold_up", category="award")
def badge(x):
    L = x.L
    side = x.side

    def spec(char, T, n):
        c = (0, -46)
        rays = []
        for q in range(8):
            a = q * math.pi / 4
            rays.append(sh(Path([(c[0] + 46 * math.cos(a), c[1] + 46 * math.sin(a)), (c[0] + 66 * math.cos(a), c[1] + 66 * math.sin(a))],
                                closed=False)))
        pulse = x.per(60)
        ray_grp = gr("rays", rays + [st(C["gold"], 6)], a=c, p=c, r=F(n, lambda f: 45.0 * f / L, tol=0.5),
                     s=F(n, lambda f: (100 + 10 * math.sin(2 * math.pi * f / pulse),) * 2, tol=1.0),
                     o=F(n, lambda f: 70 + 30 * math.sin(2 * math.pi * f / pulse), tol=2.0))
        rib = lambda k: sh(Path([(c[0] + k * 18, c[1] + 20), (c[0] + k * 28, c[1] + 64), (c[0] + k * 8, c[1] + 54), (c[0] + k * 4, c[1] + 26)],
                                closed=True))
        twinkle = gr("glint", [sh(star4((14, -60), 9)), fl(C["white"])], a=(14, -60), p=(14, -60),
                     s=F(n, lambda f: (100 * env(((f / float(pulse)) + 0.3) % 1.0, 0.2, 0.3),) * 2, tol=2.0))
        medal = gr("badge", [
            twinkle,
            gr("star", [sh(star5(c, 20, 0.42)), fl(C["white"])]),
            gr("medal", [el(c, (58, 58)), fl(C["gold"])]),
            gr("medal edge", [el(c, (72, 72)), fl(C["darkgold"])]),
            gr("ribbons", [rib(1), rib(-1), fl(C["coral"])]),
        ])
        return [(f"hand.{side}", grip(char, T, side, [medal, ray_grp], "hold_up", upright=acted(x), nm="badge"))]
    return spec


# ------------------------------------------------------------------ the cloud balloon
@prop("cloud", "Cloud balloon", "✅", noun="a cloud balloon", pose="carry", category="done")
def cloud(x):
    return P.cloud_on_string(x.side, offset=(46, -238), scale=0.9, period=x.per(60), sway_period=x.per(120))


# ------------------------------------------------------------------ the gift box: the lid flies off and comes back
def gift_box(L, cx=256.0, k=0.84, pop=True):
    """A present in front of the mascot.  With pop=True (loops of 100 frames or more) the lid wiggles, pops off in a
    burst of sparkles, spins in the air and drops back on, so the last frame equals the first."""
    def spec(char, T, n):
        gy = char.GROUND + 8.0
        ly = gy - 100.0 * k
        kk = lambda a, b: (a * k, b * k)
        t_shake = (int(L * 0.06), int(L * 0.2))
        t_dip, t_pop, t_top, t_land, t_rest = int(L * 0.27), int(L * 0.31), int(L * 0.5), int(L * 0.8), int(L * 0.88)

        def wob(f):
            if not (t_shake[0] <= f <= t_shake[1]):
                return 0.0
            mid, half = (t_shake[0] + t_shake[1]) / 2.0, (t_shake[1] - t_shake[0]) / 2.0
            return 3.0 * math.sin((f - t_shake[0]) * 1.3) * max(0.0, 1 - abs((f - mid) / half))

        box_s = K(n, (0, kk(100, 100)), (t_dip - 6, kk(100, 100), "hold"), (t_dip, kk(104, 94), "out"), (t_pop + 4, kk(96, 106), "out"),
                  (t_pop + 18, kk(100, 100), "back"), (t_land - 1, kk(100, 100), "hold"), (t_land + 4, kk(106, 92), "out"),
                  (t_rest, kk(100, 100), "back"), (L, kk(100, 100))) if pop else kk(100, 100)
        box = Layer("box", [
            gr("ribbon", [rc((0, -46), (24, 92), 0), fl(C["gold"])]),
            gr("box", [rc((0, -46), (140, 92), 10), fl(C["lilac"])]),
        ], a=(0, 0), p=(cx, gy), r=F(n, wob), s=box_s)
        if pop:
            lid_p = K(n, (0, (cx, ly)), (t_dip - 6, (cx, ly), "hold"), (t_dip, (cx, ly + 7 * k), "out"), (t_pop + 2, (cx, ly - 30), "out"),
                      (t_top, (cx + 70, ly - 150), "out"), (t_land, (cx, ly), "in"), (t_land + 3, (cx, ly + 4 * k), "out"),
                      (t_rest, (cx, ly), "back"), (L, (cx, ly)))
            lid_r = K(n, (0, 0.0), (t_pop, 0.0, "hold"), (t_top, 200.0, "out"), (t_land, 360.0, "in"), (L, 360.0))
        else:
            lid_p, lid_r = (cx, ly), 0.0
        lid = Layer("lid", [
            gr("bow", [el((-18, -24), (34, 22)), el((18, -24), (34, 22)), fl(C["gold"])]),
            gr("lid ribbon", [rc((0, 0), (24, 30), 0), fl(C["gold"])]),
            gr("lid", [rc((0, 0), (158, 30), 10), fl(C["lid"])]),
        ], a=(0, 0), p=lid_p, s=kk(100, 100), r=F(n, lambda f: wob(f) + (lid_r.s[f] if pop else 0.0)))
        out = [("mid", lid), ("mid", box)]
        if pop:
            cols = ["orange", "teal", "yellow", "coral", "mint"]
            for q in range(5):
                ang = math.radians(200 + q * 35)
                tx, ty = cx + 130 * math.cos(ang), ly + 4 + 130 * math.sin(ang)
                sp = Layer(f"gift spark {q}", [gr("sparkle", [sh(star4((0, 0), 18)), fl(C[cols[q]])])],
                           p=K(n, (0, (cx, ly + 4)), (t_pop, (cx, ly + 4), "hold"), (t_pop + 26, (tx, ty), "out"), (L, (tx, ty))),
                           s=K(n, (0, (0, 0)), (t_pop, (0, 0), "hold"), (t_pop + 12, (120, 120), "back"), (t_pop + 50, (0, 0), "io"), (L, (0, 0))),
                           r=F(n, lambda f, q=q: 90.0 * max(0, f - t_pop) / 60.0 + 20 * q))
                out.insert(0, ("top", sp))
        return out
    return spec


@prop("gift", "Gift box", "🎁", noun="a gift box", paw="LR", pose="lid", flexible=False, category="celebrate", peak=0.62,
      stance="wide", cost=1.6)
def gift(x):
    return gift_box(x.L, pop=x.L >= 100)


# ------------------------------------------------------------------ a mug of something hot, a heart
@prop("mug", "Mug", "☕", noun="a mug of something hot", pose="hold", tint=("teal", "coral", "lilac", "blue"), category="drink")
def mug(x):
    side, color = x.side, col(x.color or "teal")

    def spec(char, T, n):
        L = n - 1
        steam = []
        for q, dx in enumerate((-9, 9)):
            curl = Path([(dx, -66), (dx + 5, -82), (dx - 3, -98)], i=[(0, 0), (-6, 6), (5, 5)], o=[(6, -6), (-5, -5), (0, 0)], closed=False)
            u = lambda f, q=q: ((f / (L / 2.0)) + 0.5 * q) % 1.0
            steam.append(gr(f"steam {q}", [sh(curl), st(C["white"], 5)], a=(dx, -66), p=F(n, lambda f, dx=dx, u=u: (dx, -66 - 14 * u(f)), tol=0.5),
                            o=F(n, lambda f, u=u: 85 * math.sin(math.pi * u(f)), tol=2.0)))
        items = steam + [
            gr("coffee", [el((0, -58), (40, 9)), fl(C["board"])]),
            gr("rim", [el((0, -58), (48, 13)), fl(C["cream"])]),
            gr("shine", [rc((-14, -34), (6, 30), 3), fl(C["white"], 45)]),
            gr("mug", [rc((0, -32), (48, 54), 10), fl(color)]),
            gr("handle", [el((27, -32), (24, 26)), st(color, 7)]),
        ]
        return [(f"hand.{side}", grip(char, T, side, items, "hold", upright=acted(x), nm="mug"))]
    return spec


@prop("heart", "Heart", "❤️", noun="a heart", pose="hold_up", tint=("coral", "pink", "lilac", "teal"), category="love")
def heart(x):
    side, color, beat = x.side, col(x.color or "coral"), x.per(60)

    def spec(char, T, n):
        def s(f):
            u = (f % beat) / beat
            k = 100 + 12 * math.exp(-((u - 0.12) / 0.05) ** 2) + 7 * math.exp(-((u - 0.3) / 0.05) ** 2)
            return (k, k)
        items = [gr("heart", [gr("shine", [el((-17, -62), (14, 9)), fl(C["white"], 60)]), sh(heart_path(40, 0, -44)), fl(color)],
                    a=(0, -44), p=(0, -44), s=F(n, s, tol=1.5))]
        return [(f"hand.{side}", grip(char, T, side, items, "hold_up", upright=acted(x), nm="heart"))]
    return spec
