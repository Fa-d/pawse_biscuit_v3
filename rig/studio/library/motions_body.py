"""Whole-body moves: laughing, sobbing, stomping, roaring, boxing, fainting, spinning, hopping, running, sneaking, dancing styles,
floating, flips, sneezes and shakes.

Every move loops: positions and poses come back to where they started by the last frame, and repeated actions use
periods that divide the loop.
"""
from __future__ import annotations

from mascot import props as P
from mascot.clip import Track

from ..registry import motion
from .acting import M, alternate, beat, ease, frames_of, math, shake, shape, steps, sway_hips, wrap_pulse
from .common import C, F, K, Layer, Path, el, fl, gr, rc, sh, smooth, st
from .fx import burst, dust_at, flung_drops, speed_lines, streams


# ------------------------------------------------------------------ big feelings
@motion("laugh", "Belly laugh", "😂", doing="laughing", paws=2, min_paws=0, sit="ok", wag=10, tags=("funny",), face="laugh")
def laugh(m):
    c, L, k = m.c, m.L, m.k
    for s in m.hands:
        c.arm(s, (0, "belly"))
    p = m.per(9)
    c.osc("body.rot", 2.2 * k, p)
    c.osc("head.rot", -2.6 * k, p, phase=0.2)
    c.k("head.y", (0, -3.0))
    beat(c, "hip.y", 3.0 * k, m.per(18), L)
    beat(c, "body.sy", -0.02 * k, m.per(18), L)
    c.ears((0, 8))
    return 0


@motion("sob", "Sob", "😭", doing="sobbing", paws=2, min_paws=0, sit="ok", wag=1, blink=False, tags=("sad",), face="cry",
        draws=("waterfall_tears", "tear"))
def sob(m):
    c, L, k = m.c, m.L, m.k
    if m.hands:
        s = m.hands[0]
        c.arm(s, (0, "peek"))
        c.osc(f"arm.{s}.el", 6.0 * k, m.per(14))
    for s in m.hands[1:]:
        c.arm(s, (0, "relax"))
    p = m.per(28)
    beat(c, "body.sy", 0.03 * k, p, L, sharp=2.0)
    beat(c, "head.y", -3.0 * k, p, L, sharp=2.0)
    c.k("head.y", (0, 5.0))
    c.osc("root.x", 1.0 * k, m.per(6))
    c.ears((0, 20))
    c.prop(streams(L))
    return int(p / 2)


@motion("stomp", "Stomp", "😤", doing="stomping", paws=2, min_paws=0, wag=3, tags=("angry",), face="furious", sit_alt="shiver")
def stomp(m):
    c, L, k = m.c, m.L, m.k
    shape(c, "".join(m.hands), 1)
    for s in m.hands:
        c.arm(s, (0, (18, -30, 0, 1.0)))
    p = m.per(30)
    lands = []
    t, q = 0.0, 0
    while t + p / 2.0 <= L + 1e-6:
        side = "R" if q % 2 == 0 else "L"
        t0 = int(round(t))
        d = int(round(p / 2.0))
        M.step(c, side, t0, lift=22.0 * k, dur=d, sole=0.5, grow=0.06, e_down="in")
        lands.append(t0 + d)
        wrap_pulse(c, "root.sy", t0 + d - 1, -0.04 * k, L, up=2, down=8, e_up="out")
        wrap_pulse(c, f"arm.{side}.sh", t0 + d - 3, -10.0 * k, L, up=3, down=8)
        t += p / 2.0
        q += 1
    shake(c, "head.rot", 5.0 * k, 0, L, max(1, round(L / p)))
    c.prop(dust_at(lands, L, n_puffs=2, size=16.0))
    return lands[0] if lands else 0


@motion("roar", "Roar", "🦁", doing="roaring", paws=2, min_paws=0, sit="ok", wag=9, blink=False, tags=("rawr", "fierce", "angry"),
        face="angry")
def roar(m):
    """Crouch and gather, then RAWR: up tall, claws out, mouth wide with teeth, the head shaking with it while sound
    rings spread from the mouth; then it settles back."""
    c, L, k = m.c, m.L, m.k
    t_in, t_roar, t_end, t_back = frames_of(L, 0.12, 0.24, 0.66, 0.84)
    for s in m.hands:
        c.arm(s, (0, "rest"), (t_in, "chest", "io"), (t_roar - 4, "chest", "hold"), (t_roar, "cheer_out", "snap"),
              (t_end, "cheer_out", "hold"), (t_back, "rest", "io"), (L, "rest"))
        M.addkeys(c, f"hand.{s}.palm", (0, 0.0), (t_roar - 2, 0.0), (t_roar + 2, 1.0, "out"), (t_end, 1.0, "hold"),
                  (t_back, 0.0, "io"), (L, 0.0))
    M.addkeys(c, "hip.y", (0, 0.0), (t_in, 8.0 * k, "io"), (t_roar - 4, 10.0 * k, "hold"), (t_roar, -3.0 * k, "snap"),
              (t_end, -3.0 * k, "hold"), (t_back, 0.0, "io"), (L, 0.0))
    M.addkeys(c, "head.y", (0, 0.0), (t_in, 5.0 * k, "io"), (t_roar - 4, 6.0 * k, "hold"), (t_roar, -9.0 * k, "snap"),
              (t_end, -7.0 * k, "io"), (t_back, 0.0, "io"), (L, 0.0))
    M.addkeys(c, "body.sy", (0, 0.0), (t_in, -0.03 * k, "io"), (t_roar - 4, -0.04 * k, "hold"), (t_roar, 0.05 * k, "snap"),
              (t_roar + 10, 0.02 * k, "io"), (t_end, 0.02 * k, "hold"), (t_back, 0.0, "io"), (L, 0.0))
    M.addkeys(c, "mouth.open", (0, 0.0), (t_roar - 3, 0.0), (t_roar + 2, 1.35, "out"), (t_end, 1.2, "io"), (t_end + 8, 0.0, "io"), (L, 0.0))
    M.addkeys(c, "mouth.teeth", (0, 0.0), (t_roar - 3, 0.0), (t_roar + 2, 1.0, "out"), (t_end, 1.0, "hold"), (t_end + 8, 0.0, "io"), (L, 0.0))
    M.addkeys(c, "eye.open", (0, 0.0), (t_roar - 3, 0.0), (t_roar + 2, -0.35, "out"), (t_end, -0.35, "hold"), (t_end + 8, 0.0, "io"), (L, 0.0))
    shake(c, "head.rot", 3.5 * k, t_roar + 2, t_end, max(3, round((t_end - t_roar) / 6.0)))
    shake(c, "root.x", 2.0 * k, t_roar + 2, t_end, max(3, round((t_end - t_roar) / 5.0)), phase=0.25)
    c.ears((0, 0), (t_in, 6, "io"), (t_roar, 16, "snap"), (t_end, 14, "hold"), (t_back, 0, "io"), (L, 0))
    rings = [t_roar + int(round(u * (t_end - t_roar))) for u in (0.0, 0.3, 0.6)]
    life = max(12, int(round((t_end - t_roar) * 0.45)))

    def sound(char, T, n):
        x, y = char.head_to_world(t_roar + 4, char.mouth)
        out = []
        for q, t in enumerate(rings):
            arcs = []
            for a0 in (-26.0, 154.0):                       # one short arc each side of the mouth
                pts = [(math.cos(math.radians(a0 + 52.0 * i / 4)) * 120.0, math.sin(math.radians(a0 + 52.0 * i / 4)) * 120.0)
                       for i in range(5)]
                arcs.append(gr("arc", [sh(smooth(pts, closed=False)), st(C["dark"], 7, 55)]))
            grow = Track(None)
            for key in ((0, 70.0), (t, 70.0, "hold"), (t + life, 140.0, "out"), (L, 140.0, "hold")):
                grow.key(*key)
            sc = F(n, lambda f, g=grow: (g.at(f),) * 2, tol=2.0)
            op = K(n, (0, 0.0), (t, 0.0, "hold"), (t + 3, 100.0, "out"), (t + life, 0.0, "in"), (L, 0.0, "hold"))
            out.append(("top", Layer(f"roar ring {q}", arcs, p=(x, y - 10.0), s=sc, o=op)))
        return out
    c.prop(sound)
    return t_roar + 8


@motion("punch", "Boxing", "🥊", doing="boxing", paws=2, min_paws=1, sit="ok", wag=5, tags=("fight", "boxing", "strong"),
        face="determined")
def punch(m):
    """Gloves up, bouncing on its toes: one-two jabs at the viewer (the glove grows as it comes out of the screen,
    impact lines flash), back to the guard each time."""
    c, L, k = m.c, m.L, m.k
    p = m.per(40)                                      # one jab with each paw
    n = int(round(L / p))
    guard, jab = (30.0, 122.0, 0.0, 0.95), (52.0, 70.0, 0.0, 1.18)
    hits = []
    for q, s in enumerate(m.hands):
        off = 0.06 + 0.5 * q
        keys = [(0, guard)]
        for i in range(n):
            t0 = int(round((i + off) * p))
            t_hit, t_back = t0 + int(round(0.13 * p)), t0 + int(round(0.36 * p))
            keys += [(t0, guard, "hold"), (t_hit, jab, "out"), (t_back, guard, "io")]
            M.addkeys(c, f"hand.{s}.s", (t0, 0.0), (t_hit, 0.55 * k, "out"), (t_back, 0.0, "io"))
            hits.append((s, t_hit))
        if keys[-1][0] < L:
            keys.append((L, guard, "hold"))
        c.arm(s, *keys)
        c.set(f"arm.{s}.front", 1.0)
    shape(c, "".join(m.hands), 1)
    beat(c, "hip.y", 3.0 * k, p / 2.0, L, sharp=1.5)
    c.osc("body.rot", 3.0 * k, p, phase=0.1)
    c.osc("head.rot", -2.0 * k, p, phase=0.15)
    c.set("look.y", 0.1)
    c.ears((0, 6))

    def gloves(char, T, n_):
        out = []
        for s in m.hands:
            sgn = 1.0 if s == "R" else -1.0
            out.append((f"hand.{s}.over", gr("boxing glove", [
                gr("lace", [sh(smooth([(-10, 2), (0, 10), (10, 2)], closed=False)), st(C["white"], 3, 80)]),
                gr("thumb", [el((sgn * 26, 14), (22, 30)), fl(C["red"])]),
                gr("shine", [el((sgn * -12, 26), (14, 20)), fl(C["white"], 35)]),
                gr("glove", [el((0, 24), (62, 64)), fl(C["red"])]),
                gr("cuff", [rc((0, -2), (46, 18), 6), fl(C["white"])]),
            ])))
        for s, t in hits:
            def lines(char, T, n_, s=s, t=t):
                x, y = char.hand_to_world(s, t, (0.0, 26.0))
                res = []
                for q, a in enumerate((25, 70, 115, 160, 205)):
                    d = (math.cos(math.radians(a)), -math.sin(math.radians(a)))
                    seg = Path([(x + d[0] * 48, y + d[1] * 48), (x + d[0] * 70, y + d[1] * 70)], closed=False)
                    op = K(n_, (0, 0.0), (t, 0.0, "hold"), (t + 1, 100.0, "out"), (t + 8, 0.0, "in"), (L, 0.0, "hold"))
                    res.append(("top", Layer(f"punch {s} {t} {q}", [gr("line", [sh(seg), st(C["dark"], 6)])], o=op)))
                return res
            out += lines(char, T, n_)
        return out
    c.prop(gloves)
    return hits[0][1] if hits else 0


@motion("faint", "Faint", "😵", doing="fainting", paws=2, min_paws=0, wag=2, blink=False, tags=("shock", "tired"), face="dizzy",
        sit_alt="sway")
def faint(m):
    c, L, k = m.c, m.L, m.k
    t_wob, t_fall, t_rise, t_up = frames_of(L, 0.18, 0.32, 0.72, 0.9)
    c.set("root.pivot", 175.0)
    shake(c, "root.rot", 6.0 * k, 0, t_wob + 4, 2)
    M.addkeys(c, "root.rot", (t_wob, 0.0), (t_fall, -86.0, "in"), (t_fall + 6, -80.0, "out"), (t_fall + 12, -86.0, "io"), (t_rise, -86.0, "hold"),
              (t_up, 0.0, "back"), (L, 0.0))
    M.addkeys(c, "root.y", (t_wob, 0.0), (t_fall, 88.0, "in"), (t_fall + 6, 80.0, "out"), (t_fall + 12, 88.0, "io"), (t_rise, 88.0, "hold"),
              (t_up, 0.0, "back"), (L, 0.0))
    for s in m.hands:
        c.arm(s, (0, "relax"), (t_wob, "relax"), (t_fall, "wide", "out"), (t_rise, "wide", "hold"), (t_up, "relax", "io"), (L, "relax"))
    c.face(t_fall, "dead", dur=6)
    c.face(t_rise, "dead", dur=0)
    c.face(t_up, m.data.get("face") or "dizzy", dur=8)
    c.face(L, m.data.get("face") or "dizzy", dur=0)
    return (t_fall + t_rise) // 2


@motion("panic", "Panic", "😱", doing="panicking", paws=2, min_paws=0, sit="ok", wag=2, tags=("scared",), face="scared")
def panic(m):
    c, L, k = m.c, m.L, m.k
    for s in m.hands:
        c.arm(s, (0, "cheek"))
    if not m.sitting:
        c.stance((0, "crouch"))
    c.osc("root.x", 2.0 * k, m.per(5))
    c.osc("head.rot", 2.0 * k, m.per(7))
    c.ears((0, 24))
    c.set("tail.len", 0.92)
    return 0


@motion("victory", "Victory", "🏆", doing="celebrating a win", paws=2, min_paws=1, wag=14, tags=("win", "celebrate"), face="excited",
        sit_alt="fist_pump")
def victory(m):
    c, L, k = m.c, m.L, m.k
    shape(c, "".join(m.hands), 1)
    t0 = max(2, int(L * 0.08))
    air = 30 if L >= 90 else 20
    tl, ta, td = M.jump(c, t0, h=64 * k, air=air, anti=9, spread=10.0, settle=min(16, L - t0 - 9 - air - 4))
    for s in m.hands:
        c.arm(s, (0, "fist_pump"), (tl - 2, (62, 118, 0, 1.15), "out"), (tl + 6, "cheer_hi", "back"), (td, "cheer_hi"),
              (min(L - 2, td + 14), "fist_pump", "io"), (L, "fist_pump"))
    c.prop(burst(int(ta), lambda char, T: char.crown_world(int(ta)), count=6, colours=("yellow", "coral", "teal"), reach=90, life=20))
    return int(ta)


# ------------------------------------------------------------------ getting around
@motion("hop", "Hop", "🐇", doing="hopping", paws=0, wag=10, tags=("happy", "bunny"), face="joy")
def hop(m):
    c, L, k = m.c, m.L, m.k
    n = max(1, round(L / 40.0))
    gap = L / float(n)
    first = None
    for q in range(n):
        t0 = int(round(q * gap)) + 1
        air = max(10, int(gap * 0.36))
        tl, ta, td = M.jump(c, t0, h=26 * k, air=air, anti=5, sq=0.06, st=0.05, settle=min(12, int(gap) - air - 12), body=0.04, head=0.03)
        first = ta if first is None else first
    return int(first)


@motion("run", "Run", "🏃", doing="running", paws=2, min_paws=0, wag=8, tags=("hurry", "late"), face="determined", sit_alt="sway")
def run(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(26)
    M.walk(c, period=p, lift=24.0 * k, sway=4.0, lean=1.6, dip=6.0)
    for q, s in enumerate(m.hands):
        c.arm(s, (0, (44, -96, -8, 1.0)))
        c.osc(f"arm.{s}.sh", 22.0 * k, p, phase=0.5 * q + 0.25)
    c.k("head.y", (0, 3.0))
    c.ears((0, 14))
    lands = [int(round(p * (0.4 + 0.5 * q))) for q in range(int(2 * L / p)) if p * (0.4 + 0.5 * q) < L - 23]
    c.prop(dust_at(lands, L, n_puffs=2, size=14.0))
    return int(p * 0.2)


@motion("sneak", "Sneak", "🥷", doing="sneaking", paws=2, min_paws=0, wag=3, tags=("sneaky",), face="mischief", sit_alt="look_around")
def sneak(m):
    c, L, k = m.c, m.L, m.k
    c.stance((0, "crouch"))
    p = m.per(L)
    steps(c, L, p, lift=16.0 * k, sole=0.5, grow=0.05)
    for s in m.hands:
        c.arm(s, (0, (70, -118, -26, 1.0)))
    c.set("arm.R.front", 1.0)
    c.set("arm.L.front", 1.0)
    c.osc("look.x", 0.8, p)
    c.osc("head.rot", 4.0 * k, p)
    sway_hips(c, 5.0 * k, p, tilt=0.3)
    return int(p / 4)


@motion("march", "March", "💂", doing="marching", paws=2, min_paws=0, wag=4, tags=("proud",), face="determined", sit_alt="nod")
def march(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(36)
    M.walk(c, period=p, lift=26.0 * k, sway=3.0, lean=0.8, dip=2.0)
    for q, s in enumerate(m.hands):
        c.arm(s, (0, "rest"))
        c.osc(f"arm.{s}.sh", 26.0 * k, p, phase=0.5 * q + 0.25)
    shape(c, "".join(m.hands), 1)
    return int(p * 0.2)


@motion("float", "Float", "🎈", doing="floating", paws=2, min_paws=0, wag=4, tags=("dreamy", "calm"), face="calm", calm=True,
        sit_alt="meditate")
def float_(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(90)
    c.k("root.y", (0, -48.0 * k))
    c.osc("root.y", 7.0 * k, p)
    c.osc("root.rot", 2.0 * k, L)
    for s in m.hands:
        c.arm(s, (0, (72, 18, 0, 1.12)))
        c.osc(f"arm.{s}.sh", 5.0, p, phase=0.2)
    return int(p / 4)


@motion("soar", "Soar", "🦸", doing="soaring", paws=2, min_paws=0, wag=5, tags=("hero",), face="determined", sit_alt="sway",
        draws=("speed_lines",))
def soar(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(60)
    c.k("root.y", (0, -56.0 * k))
    c.osc("root.y", 6.0 * k, p)
    c.k("root.rot", (0, -7.0))
    for s in m.hands:
        c.arm(s, (0, "fly"))
    shape(c, "".join(m.hands), 1)
    c.ears((0, 18))
    c.prop(speed_lines(L, count=5, direction=-1))
    return 0


@motion("kick_feet", "Kick feet", "🦶", doing="kicking its feet", sit="only", stance="sit", wag=6, tags=("happy", "cute"), face="joy")
def kick_feet(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(30)
    for q, s in enumerate("RL"):
        c.osc(f"foot.{s}.y", 9.0 * k, p, phase=0.5 * q)
        c.osc(f"foot.{s}.rot", 8.0 * k, p, phase=0.5 * q + 0.25)
    for s in m.hands:
        c.arm(s, (0, "lap"))
    c.osc("head.rot", 3.0 * k, m.per(60))
    c.osc("body.rot", 1.5 * k, m.per(60), phase=0.1)
    return 0


@motion("meditate", "Meditate", "🧘", doing="meditating", sit="only", stance="lotus", wag=2, blink=False, tags=("calm", "zen"),
        face="calm", calm=True)
def meditate(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(120)
    c.k("root.y", (0, -16.0 * k))
    c.osc("root.y", 4.0 * k, p)
    for s in m.hands:
        c.arm(s, (0, "knee"))
    M.breathe(c, period=p, amp=0.025)
    return 0


@motion("nod_off", "Nod off", "😪", doing="nodding off", sit="ok", wag=2, blink=False, tags=("sleepy",), face="drowsy", calm=True)
def nod_off(m):
    c, L, k = m.c, m.L, m.k
    t_snap = frames_of(L, 0.72)[0]
    M.addkeys(c, "head.y", (0, 0.0), (t_snap, 14.0 * k, "in"), (t_snap + 6, -3.0 * k, "out"), (L, 0.0, "io"))
    M.addkeys(c, "head.rot", (0, 0.0), (t_snap, 9.0 * k, "in"), (t_snap + 6, -2.0 * k, "out"), (L, 0.0, "io"))
    c.pulse("eye.open", t_snap, 0.35, up=3, down=16)
    c.ears((0, 6), (t_snap, 16, "in"), (t_snap + 6, 2, "out"), (L, 6, "io"))
    M.breathe(c, period=m.per(120), amp=0.025)
    return t_snap - 10


# ------------------------------------------------------------------ dances
@motion("headbang", "Rock out", "🤘", doing="rocking out", paws=1, min_paws=0, sit="ok", wag=12, tags=("music", "party"), face="excited")
def headbang(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(16)
    beat(c, "head.y", 7.0 * k, p, L, sharp=2.0)
    c.osc("head.rot", 4.0 * k, m.per(32))
    M.bob(c, p, amp=3.5 * k, st=0.015)
    if m.side:
        shape(c, m.side, 1)
        c.arm(m.side, (0, "fist_pump"))
        c.osc(f"arm.{m.side}.sh", 8.0 * k, p)
    c.ears((0, 10))
    return int(p / 2)


@motion("wiggle", "Wiggle", "🍑", doing="wiggling", paws=2, min_paws=0, wag=16, tags=("silly", "dance"), face="silly", sit_alt="sway")
def wiggle(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(14)
    for s in m.hands:
        c.arm(s, (0, "hip"))
    c.osc("hip.x", 7.0 * k, p)
    c.osc("hip.rot", 5.0 * k, p)
    c.osc("head.rot", -3.0 * k, p, phase=0.1)
    M.bob(c, m.per(28), amp=2.0 * k, st=0.0)
    return int(p / 4)


@motion("spin", "Spin around", "💫", doing="spinning around", paws=2, min_paws=0, wag=10, tags=("happy", "dance"), face="joy",
        sit_alt="sway")
def spin(m):
    c, L, k = m.c, m.L, m.k
    turns = max(1, round(L / 70.0))
    per = L / float(turns)
    a, b = 0.45, 0.8                                   # each turn: facing front, a quick whirl, facing front again

    def turn(t):
        u = (t % per) / per
        return 0.0 if u < a else (1.0 if u > b else ease("io", (u - a) / (b - a)))

    c.add("root.sx", lambda t: math.cos(2 * math.pi * turn(t)) - 1.0)
    c.add("root.y", lambda t: -14.0 * k * math.sin(math.pi * turn(t)))
    c.stance((0, "tiptoe"))
    for s in m.hands:
        c.arm(s, (0, "cheer_out"))
    c.osc("body.rot", 2.0 * k, per)
    return int(per * 0.2)


@motion("flip", "Flip", "🤸", doing="doing a flip", paws=2, min_paws=0, wag=8, tags=("trick", "happy"), face="excited", sit_alt="sway")
def flip(m):
    c, L, k = m.c, m.L, m.k
    t0 = max(2, int(L * 0.08))
    air = 40 if L >= 100 else 28
    c.set("root.pivot", 175.0)
    tl, ta, td = M.jump(c, t0, h=110 * k, air=air, anti=10, spread=4.0, settle=min(18, L - t0 - 10 - air - 4))
    M.addkeys(c, "root.rot", (tl, 0.0), (td - 2, 360.0, "io"), (L, 360.0))
    for s in m.hands:
        c.arm(s, (0, "relax"), (tl - 2, "lap", "out"), (tl + 4, "cheer_hi", "out"), (ta, "cheer_out"), (td, "cheer", "io"),
              (min(L - 2, td + 14), "relax", "io"), (L, "relax"))
    c.prop(dust_at([td], L, n_puffs=4))
    return int(td + 8)                                 # the still: landed, paws up


@motion("moonwalk", "Moonwalk", "🕴️", doing="moonwalking", paws=1, min_paws=0, wag=4, tags=("dance", "cool"), face="cool", sit_alt="sway")
def moonwalk(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(30)
    for q, s in enumerate("RL"):
        beat(c, f"foot.{s}.sole", 0.55, p, L, phase=0.5 * q, sharp=1.5)
        beat(c, f"foot.{s}.y", -5.0 * k, p, L, phase=0.5 * q, sharp=1.5)
        c.osc(f"foot.{s}.x", -6.0 * k, p, phase=0.5 * q)
    c.osc("root.x", 26.0 * k, L)
    c.osc("body.rot", -2.5 * k, L)
    if m.side:
        c.arm(m.side, (0, "hip"))
    return int(L / 4)


@motion("robot", "Robot dance", "🤖", doing="doing the robot", paws=2, min_paws=0, wag=0, tags=("dance", "funny"), face="neutral")
def robot(m):
    c, L, k = m.c, m.L, m.k
    beats = max(4, round(L / 15.0))
    step = L / float(beats)
    up, down = (92, 90, 0, 1.0), (92, -90, 0, 1.0)
    for q, s in enumerate(m.hands):
        keys = []
        for b in range(beats + 1):
            pose = up if (b + q) % 2 == 0 else down
            keys.append((int(round(b * step)), pose, "snap"))
        keys[-1] = (L, keys[0][1], "snap")
        c.arm(s, *keys)
    hk = []
    for b in range(beats + 1):
        hk.append((int(round(b * step)), (-6.0, 0.0, 6.0, 0.0)[b % 4] * k, "snap"))
    hk[-1] = (L, hk[0][1], "snap")
    M.addkeys(c, "head.rot", *hk)
    return 0


@motion("floss", "Floss", "🕺", doing="flossing", paws=2, min_paws=2, wag=10, tags=("dance",), face="grin", paw_alt="wiggle",
        sit_alt="sway")
def floss(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(18)
    for s in m.hands:
        c.arm(s, (0, (22, 0, 0, 1.08)))
    c.osc("arm.R.sh", 34.0 * k, p)
    c.osc("arm.L.sh", -34.0 * k, p)
    c.osc("hip.x", -9.0 * k, p)
    c.osc("hip.rot", -4.0 * k, p)
    return int(p / 4)


@motion("disco", "Disco", "🪩", doing="dancing disco", paws=1, min_paws=1, wag=10, tags=("dance", "party"), face="cool", paw_alt="wiggle",
        sit_alt="sway")
def disco(m):
    c, L, k = m.c, m.L, m.k
    s = m.side
    shape(c, s, 3)
    p = m.per(30)
    alternate(c, s, "point_up", (14, -46, 0, 1.25), p, L, at_b=0.5, e_ab="io", e_ba="io")
    c.set(f"arm.{s}.front", 1.0)
    sway_hips(c, 6.0 * k, p, tilt=0.5, phase=0.25)
    M.bob(c, p / 2.0, amp=2.5 * k, st=0.01)
    return 0


@motion("jumping_jacks", "Jumping jacks", "🏋️", doing="doing jumping jacks", paws=2, min_paws=0, wag=6, tags=("gym", "energy"),
        face="determined", sit_alt="sway")
def jumping_jacks(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(30)
    n = max(1, round(L / p))
    keys_st, keys_arm = [(0, "stand")], [(0, "rest")]
    for q in range(n):
        t0 = q * p
        keys_st += [(int(round(t0 + p * 0.5)), "wide", "out"), (int(round(t0 + p)), "stand", "io")]
        keys_arm += [(int(round(t0 + p * 0.5)), "cheer_hi", "out"), (int(round(t0 + p)), "rest", "io")]
        c.pulse("root.y", int(round(t0 + p * 0.1)), -14.0 * k, up=int(p * 0.2), down=int(p * 0.2), e_up="out", e_down="in")
        c.pulse("root.y", int(round(t0 + p * 0.6)), -14.0 * k, up=int(p * 0.2), down=int(p * 0.2), e_up="out", e_down="in")
    keys_st[-1] = (L, "stand", "io")
    keys_arm[-1] = (L, "rest", "io")
    c.stance(*keys_st)
    for s in m.hands:
        c.arm(s, *keys_arm)
    return int(p * 0.5)


@motion("workout", "Squats", "🏋️‍♀️", doing="working out", paws=2, min_paws=0, wag=4, tags=("gym", "strong"), face="determined",
        sit_alt="flex")
def workout(m):
    c, L, k = m.c, m.L, m.k
    p = m.per(40)
    c.stance((0, "wide"))
    beat(c, "hip.y", 26.0 * k, p, L)
    for s in m.hands:
        c.arm(s, (0, (60, -10, 0, 1.1)))
        beat(c, f"arm.{s}.sh", 30.0 * k, p, L)
    shape(c, "".join(m.hands), 1)
    beat(c, "head.y", 4.0 * k, p, L)
    return int(p / 2)


# ------------------------------------------------------------------ little dramas
@motion("sneeze", "Sneeze", "🤧", doing="sneezing", paws=1, min_paws=0, sit="ok", wag=3, blink=False, tags=("sick",), face="sick")
def sneeze(m):
    c, L, k = m.c, m.L, m.k
    t_ah, t_choo = frames_of(L, 0.42, 0.56)
    M.addkeys(c, "head.y", (0, 0.0), (t_ah, -7.0 * k, "io"), (t_choo, 12.0 * k, "snap"), (t_choo + 14, 0.0, "io"), (L, 0.0))
    M.addkeys(c, "head.rot", (0, 0.0), (t_ah, -5.0 * k, "io"), (t_choo, 4.0 * k, "snap"), (t_choo + 14, 0.0, "io"), (L, 0.0))
    M.addkeys(c, "eye.open", (0, 0.0), (t_ah, -0.5, "io"), (t_choo, -1.0, "snap"), (t_choo + 16, 0.0, "io"), (L, 0.0))
    c.pulse("root.sy", t_choo - 1, -0.04 * k, up=2, down=10)
    c.ears((0, 0), (t_ah, -8, "io"), (t_choo, 18, "snap"), (t_choo + 18, 0, "io"), (L, 0))
    if m.side:
        c.arm(m.side, (0, "rest"), (t_choo + 4, "mouth", "out"), (t_choo + 26, "mouth", "hold"), (L, "rest", "io"))
    c.prop(P.sneeze_burst(t_choo, count=7))
    return t_choo + 2


@motion("shake", "Shake off", "💦", doing="shaking off", paws=0, wag=14, tags=("wet", "silly"), face="flustered", sit_alt="sway")
def shake_off(m):
    c, L, k = m.c, m.L, m.k
    t0, t1 = frames_of(L, 0.08, 0.7)
    shake(c, "root.rot", 7.0 * k, t0, t1, max(3, round((t1 - t0) / 7.0)))
    shake(c, "head.rot", -9.0 * k, t0, t1, max(3, round((t1 - t0) / 7.0)), phase=0.1)
    shake(c, "body.rot", 4.0 * k, t0, t1, max(3, round((t1 - t0) / 7.0)), phase=0.2)
    c.prop(flung_drops(t0 + 6, t1 - 6, 9, L))
    return (t0 + t1) // 2


@motion("tremble", "Tremble", "🫨", doing="trembling", paws=2, min_paws=0, sit="ok", wag=1, tags=("scared", "cold"), face="scared")
def tremble(m):
    c, L, k = m.c, m.L, m.k
    if not m.sitting:
        c.stance((0, "crouch"))
    for s in m.hands:
        c.arm(s, (0, "hug"))
    c.osc("root.x", 1.4 * k, m.per(4))
    c.osc("head.rot", 1.0 * k, m.per(6))
    c.ears((0, 26))
    return 0
