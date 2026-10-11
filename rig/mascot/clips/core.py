"""The standard clip set.  Nothing in here knows which mascot is performing.

Fifteen clips are played standing; `sleepy`, `deep_sleep`, `breathe` and `meditate` sit down to rest.
"""
from __future__ import annotations

import math

from .. import props as P
from . import moves as M


# --------------------------------------------------------------------------- idle
def idle_base(c):
    """What fixes the first frame of `idle` (the alternate takes start and end on it)."""
    c.face(0, "neutral", dur=0)
    M.breathe(c, period=180, amp=0.03)
    c.tailpose((0, "rest"))
    c.wag(amp=5.0, period=180, lag=0.14)


def idle(c):
    F = c.frames
    idle_base(c)
    # the weight settles on the right foot, wanders over to the left one, then a small step back to the middle
    M.weight(c, (0, 0), (12, 0), (40, 8), (84, 8), (118, -7), (150, -7), (172, 0, "io"), (F, 0))
    c.k("body.rot", (0, 0), (12, 0), (40, -1.6, "soft"), (84, -1.6), (118, 1.4, "soft"), (150, 1.4), (172, 0, "soft"), (F, 0))   # chest stays upright
    c.k("head.rot", (0, 0), (46, 2.4, "soft"), (112, -1.8, "soft"), (F, 0, "soft"))
    M.tap(c, "L", 50, n=2, gap=12)                             # the free foot taps while it waits
    M.step(c, "R", 156, lift=7, dur=13, sole=0.35, grow=0.03)
    # tail: lazy sway, then the tip flicks and Biscuit notices it
    c.tailpose((92, "rest"), (102, "flick_out", "out"), (114, "flick_in", "io"), (134, "rest", "back"), (F, "rest"))
    M.look(c, (0, 0, 0), (104, 0, 0), (113, 0.9, 0.3, "out"), (134, 0.9, 0.3), (148, 0, 0, "io"), (F, 0, 0))
    c.blink(70)
    c.blink(150)
    # ear flicks (the second one answers the tail)
    M.ear_flick(c, "L", 38)
    M.ear_flick(c, "R", 108, amp=11)
    M.ear_flick(c, "R", 120, amp=7)
    c.pulse("tongue", 164, -0.55, up=5, down=9)                # tiny tongue wiggle


# --------------------------------------------------------------------------- wave
def wave(c):
    F = c.frames
    c.face(0, "smiley", dur=0)
    M.breathe(c, period=60, amp=0.02)
    M.wave(c, "R", None, None, period=30)
    c.arm("L", (0, "rest"))
    # head tilts towards the paw and nods along
    c.k("head.rot", (0, 3), (60, 6, "soft"), (F, 3, "soft"))
    c.osc("head.rot", 1.2, 30, phase=0.1)
    c.k("body.rot", (0, 1.2), (60, 2.4, "soft"), (F, 1.2, "soft"))
    # knees keep the rhythm and the right foot taps along with every wave
    c.set("hip.x", -3.0)
    M.bob(c, 30, amp=3.0, st=0.008)
    M.tap(c, "R", 8, n=4, gap=30)
    # the tail waves hello too, a beat behind the paw
    c.tailpose((0, "low"))
    c.wag(amp=8.0, period=30, lag=0.16, phase=-0.2, taper=(0.25, 1.0))
    M.happy_squint(c, 44, 72)
    c.blink(102)


# --------------------------------------------------------------------------- happy
def happy(c):
    F = c.frames
    c.face(0, "joy", dur=0)
    tl, ta, td = M.jump(c, 2, h=44, air=30, anti=9, st=0.055, spread=9.0)   # launch 11, apex 26, land 41
    flop = (82, -52, 10, 1.15)                                  # elbows give way first when the arms drop
    c.arm("LR", (0, "relax"), (tl - 2, "lap", "out"), (tl + 9, "cheer", "back"), (td - 3, "cheer"), (td + 5, flop, "out"),
          (td + 15, "relax", "back"), (62, "relax"), (74, "cheek", "back"), (104, "cheek"), (F, "relax", "io"))
    c.tailpose((0, "up"))
    c.wag(amp=11.0, period=30, lag=0.14)
    # after the landing: paws to the cheeks, a delighted wiggle and happy feet
    c.k("head.rot", (0, -3), (30, 4, "soft"), (60, -3, "soft"), (76, 6, "io"), (88, -6, "io"), (100, 5, "io"), (F, -3, "soft"))
    c.osc("body.rot", 1.6, 40, t0=60)
    M.patter(c, 66, 106, period=10, lift=7.0)
    M.bob(c, 20, amp=2.5, t0=60, t1=F, st=0.012)
    c.prop(P.dust(td, 256, n_puffs=4))


# --------------------------------------------------------------------------- cheer
def cheer(c):
    F = c.frames
    c.face(0, "joy", dur=0)
    tl, ta, td = M.jump(c, 2, h=62, air=34, anti=9, tuck=5.0, spread=17.0)   # star jump: launch 11, apex 28, land 45
    c.arm("LR", (0, "cheer"))
    for s, ph in (("L", 0.0), ("R", 0.06)):                   # arms pump, a hair out of step so it feels loose
        c.osc(f"arm.{s}.sh", 13.0, 24, phase=ph)
        c.osc(f"arm.{s}.el", 9.0, 24, phase=ph + 0.12)
    c.tailpose((0, "up"))
    c.wag(amp=12.0, period=24, lag=0.15)
    c.k("head.rot", (0, -3), (24, 3, "soft"), (48, -3, "soft"), (72, 3, "soft"), (96, -3, "soft"), (F, -3, "soft"))
    # back on the ground: bouncing knees and a kick to each side
    M.bob(c, 24, amp=5.0, t0=48, t1=F, st=0.02)
    M.kick(c, "R", 62, out=30, up=20, dur=18, hold=2)
    M.kick(c, "L", 86, out=30, up=20, dur=18, hold=2)
    c.k("hip.x", (0, 0), (58, 0), (66, -7, "out"), (80, 0, "io"), (82, 0), (90, 7, "out"), (104, 0, "io"), (F, 0))
    c.k("hip.rot", (0, 0), (58, 0), (66, -3, "out"), (80, 0, "io"), (82, 0), (90, 3, "out"), (104, 0, "io"), (F, 0))
    c.prop(P.dust(td, 256, n_puffs=4))
    c.prop(P.sparkles([(84, 170, 22, "yellow", 0), (430, 120, 26, "teal", 11), (456, 260, 18, "coral", 22),
                       (60, 300, 18, "lilac", 33), (256, 36, 20, "yellow", 44)]))


# --------------------------------------------------------------------------- concerned
def concerned(c):
    F = c.frames
    c.face(0, "worried", dur=0)
    M.breathe(c, period=75, amp=0.016)
    # small and tense: knees together, toes turned in
    c.set("hip.y", 6.0)
    for s in "LR":
        c.set(f"leg.{s}.bend", -1.0)
        c.set(f"foot.{s}.rot", -13.0)
        c.set(f"foot.{s}.x", -3.0)
    c.set("head.y", 3.0)
    c.ears((0, 22), (F, 22))
    c.pulse("ear.L.rot", 50, -7, up=4, down=12, e_down="back")
    c.pulse("ear.R.rot", 118, 7, up=4, down=12, e_down="back")
    c.k("head.rot", (0, -3), (75, 3, "soft"), (F, -3, "soft"))
    # nervous glances
    M.look(c, (0, -0.6, 0.3), (30, -0.6, 0.3), (40, 0.6, 0.2, "out"), (98, 0.6, 0.2), (110, -0.6, 0.3, "out"), (F, -0.6, 0.3))
    c.blink(36)
    c.blink(104)
    # paws fidget in front of the tummy
    c.arm("LR", (0, "belly"))
    c.osc("arm.L.el", 5.0, 25)
    c.osc("arm.R.el", 5.0, 25, phase=0.5)
    c.osc("arm.L.sh", 2.0, 50)
    c.osc("arm.R.sh", 2.0, 50, phase=0.5)
    # one foot rubs against the other ankle, then the knees wobble
    M.addkeys(c, "foot.L.y", (56, 0.0), (66, -9.0, "out"), (100, -9.0), (110, 0.0, "in"))
    M.addkeys(c, "foot.L.x", (56, 0.0), (66, -15.0, "out"), (100, -15.0), (110, 0.0, "io"))
    M.addkeys(c, "foot.L.rot", (56, 0.0), (66, -10.0, "out"), (100, -10.0), (110, 0.0, "io"))
    c.osc("foot.L.y", 3.0, 12, t0=66, t1=102)
    c.k("hip.x", (0, 0), (52, 0), (64, 4, "io"), (102, 4), (114, 0, "io"), (F, 0))
    c.osc("hip.x", 0.9, 6, t0=120, t1=144)
    # tail hangs low, only the tip twitches
    c.tailpose((0, "low"))
    c.set("tail.fluff", 0.94)
    c.wag(amp=3.5, period=50, lag=0.2, taper=(0.0, 1.0))
    c.prop(P.sweat_drop(46))


# --------------------------------------------------------------------------- thinking
def thinking(c):
    F = c.frames
    c.face(0, "neutral", dur=0, tongue=0)
    c.face(24, "curious", dur=16)
    c.face(156, "curious", dur=0)
    c.face(F, "neutral", dur=22, tongue=0)
    M.breathe(c, period=90, amp=0.02)
    c.k("head.rot", (0, 0), (8, 2.5, "out"), (24, -8, "back"), (156, -8), (F, 0, "io"))
    c.k("head.y", (0, 0), (24, 3, "io"), (156, 3), (F, 0, "io"))
    c.k("ear.R.rot", (0, 0), (24, 5, "back"), (156, 5), (F, 0))
    c.k("ear.L.rot", (0, 0), (24, -7, "back"), (156, -7), (F, 0))
    # paw to chin, other arm across the tummy
    c.arm("R", (0, "rest"), (6, "relax", "out"), (26, "chin", "back"), (156, "chin"), (F, "rest", "io"))
    c.arm("L", (0, "rest"), (10, "rest"), (30, "belly", "back"), (156, "belly"), (F, "rest", "io"))
    for t in (72, 84, 128):                                   # chin taps
        c.pulse("arm.R.el", t, 9, up=4, down=7)
        c.pulse("head.y", t + 2, -1.5, up=3, down=7)
    # leaning on the left leg, the right foot taps slowly while the thought takes shape
    M.weight(c, (0, 0), (8, 0), (28, -6), (154, -6), (F, 0))
    M.tap(c, "R", 40, n=3, gap=15)
    M.tap(c, "R", 104, n=2, gap=15)
    # tail: slow sway with a thoughtful flick of the tip
    c.tailpose((0, "rest"), (70, "rest"), (82, "flick_out", "out"), (96, "flick_in", "io"), (118, "rest", "back"), (F, "rest"))
    c.wag(amp=4.0, period=90, lag=0.15)
    c.blink(130)
    c.prop(P.thought_dots([(162, 58, 20, 20), (188, 24, 28, 38), (216, -16, 40, 56)], rel=True))


# --------------------------------------------------------------------------- sleepy (sitting)
def sleepy_base(c):
    """What fixes the first frame of `sleepy` (its alternate take starts and ends on it)."""
    F = c.frames
    c.stance((0, "sit"))
    c.face(0, "sleep", dur=0)
    M.breathe(c, period=F, amp=0.045)
    c.ears((0, 9), (F, 9))
    # hugging the tail like a pillow
    c.arm("LR", (0, "belly"))
    c.tailpose((0, "wrap"))
    c.set("tail.front", 1.0)
    c.set("tail.len", 0.86)
    c.set("tail.fluff", 0.94)
    c.wag(amp=2.0, period=F, lag=0.2, taper=(0.0, 1.0))


def sleepy(c):
    F = c.frames
    sleepy_base(c)
    # nodding off: the head sinks... sinks... then jerks back up
    c.k("head.rot", (0, 7), (112, 13, "in"), (121, 3, "out"), (138, 8.5, "back"), (F, 7, "io"))
    c.k("head.y", (0, 7), (112, 15, "in"), (121, 2, "out"), (138, 8, "back"), (F, 7, "io"))
    c.k("body.rot", (0, 1.5), (112, 3.5, "in"), (121, 0.5, "out"), (138, 2, "back"), (F, 1.5, "io"))
    # one eye peeks open at the jerk, then gives up
    c.k("eye.open", (0, 0), (118, 0, "hold"), (124, 0.5, "out"), (140, 0.5), (152, 0, "io"), (F, 0))
    c.k("eye.L.blink", (0, 0), (116, 1, "hold"), (156, 1), (157, 0, "hold"), (F, 0))
    c.pulse("ear.R.rot", 119, -14, up=4, down=14, e_down="back")
    c.pulse("ear.L.rot", 121, 12, up=4, down=14, e_down="back")
    for s in "LR":                                             # the feet kick with the jerk
        c.pulse(f"foot.{s}.rot", 119, 10, up=4, down=16, e_down="back")
        c.pulse(f"foot.{s}.y", 119, -5, up=4, down=14, e_down="back")
    c.prop(P.zzz([(134, 44, 20, 0), (158, 8, 26, 24), (178, -28, 30, 48)], rel=True))


# --------------------------------------------------------------------------- hop_in (entrance, plays once)
def hop_in(c):
    F = c.frames
    grow = 1.0 / c.scale                                       # finish at full size so it hands over to idle without a jump
    c.k("root.scale", (0, 0.0), (9, 1.12, "out"), (15, 0.95, "io"), (21, 1.0, "io"), (60, 1.0), (106, grow, "io"))
    c.face(0, "joy", dur=0)
    c.face(62, "smiley", dur=7)
    c.face(F - 2, "neutral", dur=12)
    t1 = M.jump(c, 8, h=56, air=24, anti=6, spread=10.0)       # launch 14, apex 26, land 38
    t2 = M.jump(c, 38, h=24, air=16, anti=3, sq=0.05, st=0.04, settle=14, body=0.04, head=0.03, crouch=0.0)   # rebound: land 57
    c.arm("LR", (0, "cheer_out"), (13, "relax", "io"), (22, "cheer", "back"), (35, "cheer"), (47, "relax", "back"), (60, "rest", "io"))
    c.arm("R", (60, "rest"))
    M.wave(c, "R", 62, 100, period=19)
    c.k("head.rot", (0, 0), (26, -3, "soft"), (48, 3, "soft"), (66, 5, "soft"), (100, 5), (F - 4, 0, "io"))
    # a little shuffle into place once it has landed
    M.step(c, "L", 66, lift=6, dur=10, sole=0.3, grow=0.03)
    M.step(c, "R", 78, lift=6, dur=10, sole=0.3, grow=0.03)
    c.tailpose((0, "up"), (72, "up"), (112, "rest", "io"))
    c.wag(amp=12.0, period=24, lag=0.15, t0=0, t1=110, fade=18)
    c.wag(amp=5.0, period=180, lag=0.14, t0=F - 36, t1=F, phase=-0.2, fade=30, fade_out=0)   # arrives in step with idle's sway
    c.blink(84)
    c.prop(P.dust(6, 256, n_puffs=4, size=15))
    c.prop(P.dust(t1[2], 256, n_puffs=4))
    c.prop(P.dust(t2[2], 256, n_puffs=2, size=13))


# --------------------------------------------------------------------------- pop_up (plays once)
def pop_up(c):
    F = c.frames
    c.opt(hands_over_top=True)
    c.set("shadow.o", 0.0)
    c.prop(P.card())
    # only the ear tips show at first, then the eyes peek over the edge, then the whole fox pops up
    c.k("root.y", (0, 296), (7, 296), (17, 130, "out"), (27, 130), (31, 148, "io"), (40, -10, "out"), (47, 12, "io"), (54, 8, "io"))
    M.addkeys(c, "root.sy", (27, 0.0), (31, -0.05, "out"), (38, 0.055, "io"), (44, -0.05, "io"), (52, 0.02, "io"), (58, 0.0, "io"))
    M.addkeys(c, "root.sx", (27, 0.0), (31, 0.04, "out"), (38, -0.04, "io"), (44, 0.04, "io"), (52, -0.015, "io"), (58, 0.0, "io"))
    M.ear_flick(c, "R", 1, amp=15, dur=10)
    M.ear_flick(c, "L", 5, amp=13, dur=10)
    # paws: come up behind the card, flop over its edge, hang on during the pop
    def edge(sx):                                              # wide while it peeks (clear of the eyes), closer once it is up
        def at(f):
            u = min(1.0, max(0.0, (f - 32) / 14.0))
            return (256 + sx * (120 - 22 * (0.5 - 0.5 * math.cos(math.pi * u))), 390)
        return at
    flop = lambda f: 180.0 if f < 16 else (180.0 + (8.0 - 180.0) * min(1.0, (f - 16) / 7.0) ** 0.7)
    c.set("arm.L.front", 1.0)
    c.set("arm.R.front", 1.0)
    c.arm("LR", (0, "edge"))
    c.pin("L", 10, F + 20, edge(-1), hand=flop)
    c.pin("R", 10, 50, edge(1), hand=flop, blend=4)
    for s in "LR":
        c.k(f"hand.{s}.over", (0, 0.0), (17, 1.0, "hold"))
    c.arm("R", (50, "edge"))
    M.wave(c, "R", 50, 86, period=18, rest="edge", up=9, down=11)
    # face: wide-eyed peek left and right, surprise on the pop, then a big hello
    c.face(0, "curious", dur=0, look_x=0.0, look_y=0.0, mouth_o=0.0)
    M.look(c, (0, 0, 0), (17, 0, 0), (21, -0.9, 0.0, "out"), (25, 0.9, 0.0, "io"), (29, 0, 0.2, "io"))
    c.face(40, "surprised", dur=6)
    c.face(50, "smiley", dur=7)
    c.k("head.rot", (0, 0), (40, 0), (48, -4, "out"), (62, 5, "io"), (86, 5), (F, 2, "io"))
    c.tailpose((0, "curl"), (34, "curl"), (50, "rest", "io"))        # tucked away until the pop
    c.k("tail.len", (0, 0.8), (34, 0.8), (46, 1.0, "back"))
    c.wag(amp=8.0, period=50, lag=0.15, t0=44, t1=F, fade=10)
    c.blink(74)


# --------------------------------------------------------------------------- breathe (one slow breath, sitting)
def breathe(c):
    F = c.frames
    H = F // 2
    c.stance((0, "sit"))
    c.face(0, "calm", dur=0)
    for ch, lo, hi in (("body.sy", 0.0, 0.08), ("body.sx", 0.0, 0.035), ("head.y", 0.0, -3.0), ("head.sy", 1.0, 1.012),
                       ("arm.L.sh", 0.0, 5.0), ("arm.R.sh", 0.0, 5.0), ("nose.y", 0.0, -1.2), ("ear.R.rot", 3.0, -2.5), ("ear.L.rot", -3.0, 2.5)):
        if ch.startswith("body."):                             # on top of the seated shape
            M.addkeys(c, ch, (0, lo), (H, hi, "io"), (F, lo, "io"))
        else:
            c.k(ch, (0, lo), (H, hi, "io"), (F, lo, "io"))
    c.arm("LR", (0, "belly"))
    for s in "LR":                                             # toes spread on the in-breath
        c.k(f"foot.{s}.rot", (0, 0.0), (H, 5.0, "io"), (F, 0.0, "io"))
    c.tailpose((0, "ground"), (H, "ground_up", "io"), (F, "ground", "io"))
    c.wag(amp=2.5, period=F // 2, lag=0.2)
    # out-breath through the mouth, with a soft puff
    c.k("mouth.o", (0, 0.0), (H + 6, 0.0), (H + 26, 0.6, "io"), (H + 110, 0.5), (H + 150, 0.0, "io"), (F, 0.0))
    c.prop(P.breath_puff(H + 22))
    c.prop(P.aura("teal", period=F, size=336.0))


# --------------------------------------------------------------------------- deep_sleep (sitting)
def deep_sleep(c):
    F = c.frames
    c.stance((0, "sit"))
    c.face(0, "sleep", dur=0, mouth_smile=0.7)
    M.addkeys(c, "body.sy", (0, -0.07), (F, -0.07))            # slumped
    M.addkeys(c, "body.sx", (0, 0.035), (F, 0.035))
    M.breathe(c, period=F, amp=0.06)
    c.k("head.rot", (0, 13), (F // 2, 15.5, "soft"), (F, 13, "soft"))
    c.k("head.y", (0, 20), (F // 2, 24, "soft"), (F, 20, "soft"))
    c.ears((0, 17), (F, 17))
    c.arm("LR", (0, "belly"))
    c.tailpose((0, "wrap"))
    c.set("tail.front", 1.0)
    c.set("tail.len", 0.86)
    c.wag(amp=1.5, period=F, lag=0.2, taper=(0.0, 1.0))
    # dreaming of running: the feet paddle and an ear twitches
    for q, t in enumerate((150, 160, 170)):
        c.pulse("foot.R.rot", t, 12 - 3 * q, up=3, down=6)
        c.pulse("foot.R.y", t, -(5 - q), up=3, down=6)
        c.pulse("foot.L.rot", t + 5, 10 - 3 * q, up=3, down=6)
        c.pulse("foot.L.y", t + 5, -(4 - q), up=3, down=6)
    c.pulse("ear.R.rot", 154, -9, up=3, down=10, e_down="back")
    c.pulse("mouth.open", 152, 0.25, up=6, down=22)
    c.prop(P.zzz([(98, 112, 22, 0), (122, 70, 28, 44), (144, 28, 34, 88)], life=100, fade_in=26, drift=(10, -44), rel=True))


# --------------------------------------------------------------------------- peek_phone
def peek_phone(c):
    F = c.frames
    gaze = dict(look_x=0.9, look_y=0.45)
    c.face(0, "curious", dur=0, **gaze)
    M.breathe(c, 90, amp=0.02)
    c.arm("R", (0, "hold"))
    c.arm("L", (0, "rest"))
    c.osc("arm.R.sh", 1.5, 90)
    c.k("head.rot", (0, 6), (90, 9, "soft"), (F, 6, "soft"))
    c.set("hip.x", 4.0)                                        # weight on the phone side
    c.set("hip.rot", 1.4)
    # eyes climb the bars as they grow; a pleased bounce on the toes when the tallest one lands
    c.face(52, "smiley", dur=8, look_x=0.9, look_y=-0.15)
    c.face(150, "smiley", dur=0, look_x=0.9, look_y=-0.15)
    c.face(F, "curious", dur=20, **gaze)
    c.k("look.y", (0, 0.45), (18, 0.4), (44, -0.15, "io"))
    M.addkeys(c, "hip.y", (42, 0.0), (47, 5.0, "out"), (52, -6.0, "out"), (58, 2.0, "io"), (63, -4.0, "out"), (72, 0.0, "io"))
    c.pulse("ear.R.rot", 46, -9, up=5, down=16, e_down="back")
    c.pulse("ear.L.rot", 46, 9, up=5, down=16, e_down="back")
    M.tap(c, "L", 92, n=3, gap=12)
    c.tailpose((0, "low"))
    c.wag(amp=5.0, period=90, lag=0.15)
    c.wag(amp=6.0, period=20, lag=0.15, t0=50, t1=130, fade=14)
    c.blink(120)
    c.prop(P.phone("R", "hold"))


# --------------------------------------------------------------------------- meditate (cross-legged, floating)
def meditate(c):
    F = c.frames
    c.stance((0, "lotus"))
    c.face(0, "calm", dur=0)
    c.k("root.y", (0, -22), (60, -31, "soft"), (120, -22, "soft"), (180, -31, "soft"), (F, -22, "soft"))   # floating
    M.breathe(c, 120, amp=0.025)
    c.arm("LR", (0, "knee"))
    c.auto.update({"arm.y": 0.15})
    for s, ph in (("L", 0.0), ("R", 0.5)):                     # toes wiggle, one foot after the other
        c.osc(f"foot.{s}.rot", 4.0, 60, phase=ph)
    c.ears((0, 5), (F, 5))
    c.tailpose((0, "ground"))
    c.wag(amp=7.0, period=120, lag=0.2)
    c.prop(P.aura("lilac", period=120))
    c.prop(P.orbs(3, period=F))


# --------------------------------------------------------------------------- ring_bell
def ring_bell(c):
    F = c.frames
    c.face(0, "smiley", dur=0)
    c.arm("R", (0, "ring"))
    c.arm("L", (0, "rest"))
    c.osc("arm.R.sh", 4.5, 24, phase=0.25)
    c.osc("arm.R.el", 6.0, 24, phase=0.3)
    # knees bounce with the bell and the left foot stamps on every ring
    M.bob(c, 24, amp=3.5, st=0.012)
    M.tap(c, "L", 5, n=4, gap=24, up=0.6, lift=4.0)
    c.set("hip.x", 3.0)
    c.k("head.rot", (0, -2), (48, 4, "soft"), (F, -2, "soft"))
    c.osc("head.rot", 1.5, 24)
    c.osc("ear.R.rot", 3.0, 12)
    c.osc("ear.L.rot", 3.0, 12, phase=0.5)
    c.tailpose((0, "low"))
    c.wag(amp=7.0, period=48, lag=0.15)
    c.blink(52)
    c.prop(P.bell("R", "ring", period=24, scale=0.9))


# --------------------------------------------------------------------------- read_chart
def read_chart(c):
    F = c.frames
    c.face(0, "focused", dur=0, look_x=-0.9, look_y=0.45)
    M.breathe(c, 75, amp=0.018)
    c.arm("L", (0, "hold"))
    c.arm("R", (0, "rest"), (50, "rest"), (66, "chin", "back"), (124, "chin"), (F, "rest", "io"))
    c.k("head.rot", (0, -5), (30, -8, "soft"), (60, -3, "soft"), (90, -8, "soft"), (120, -3, "soft"), (F, -5, "soft"))
    c.set("head.y", 3.0)
    c.set("hip.x", -4.0)                                       # weight on the clipboard side
    c.set("hip.rot", -1.4)
    # eyes follow the line as it draws; then the "oh, that's good" moment lifts it onto its toes
    c.k("look.x", (0, -0.9), (50, -0.55, "io"), (130, -0.55), (F, -0.9, "io"))
    c.k("look.y", (0, 0.45), (50, -0.05, "io"), (130, -0.05), (F, 0.45, "io"))
    c.k("brow.tilt", (0, -10), (52, -10), (60, 5, "back"), (126, 5), (F, -10, "io"))
    c.k("brow.y", (0, -4), (52, -4), (60, 5, "back"), (126, 5), (F, -4, "io"))
    c.k("eye.open", (0, 0.6), (52, 0.6), (60, 0.9, "back"), (126, 0.9), (F, 0.6, "io"))
    c.k("mouth.smile", (0, 0.8), (52, 0.8), (60, 1.15, "back"), (126, 1.15), (F, 0.8, "io"))
    M.addkeys(c, "hip.y", (50, 0.0), (55, 4.0, "out"), (61, -6.0, "out"), (70, 1.5, "io"), (78, 0.0, "io"))
    M.ear_flick(c, "R", 56, amp=10)
    M.tap(c, "R", 14, n=2, gap=13)                             # an absent-minded foot while reading
    M.tap(c, "R", 98, n=2, gap=13)
    c.tailpose((0, "rest"), (56, "rest"), (66, "up", "back"), (126, "up"), (F, "rest", "io"))
    c.wag(amp=5.0, period=F, lag=0.15)
    c.blink(100)
    c.prop(P.clipboard("L", "hold"))


# --------------------------------------------------------------------------- carry_cloud (walking)
def carry_cloud(c):
    F = c.frames
    c.face(0, "smiley", dur=0)
    M.walk(c, period=60, lift=15.0, sway=6.0, lean=2.2, dip=3.0, first="R")     # four steps per loop
    c.arm("R", (0, "carry"))
    c.arm("L", (0, "relax"))
    c.osc("arm.L.sh", 12.0, 60, phase=0.3)                     # the free arm swings against the legs
    c.osc("arm.L.el", 8.0, 60, phase=0.35)
    M.look(c, (0, 0, 0), (22, 0, 0), (32, 0.7, -0.8, "out"), (58, 0.7, -0.8), (70, 0, 0, "io"), (F, 0, 0))   # proud glance at the cloud
    c.blink(84)
    c.tailpose((0, "rest"))
    c.wag(amp=9.0, period=60, lag=0.16)
    for t, side in ((24, 1), (54, -1), (84, 1), (114, -1)):   # a puff of dust at every footfall
        c.prop(P.dust(t, 256 + side * 40 * c.scale, side=side, n_puffs=1, size=9.0, gap=26.0))
    c.prop(P.cloud_on_string("R", offset=(46, -238), scale=0.95, sway=5.0))


# --------------------------------------------------------------------------- gift (plays once)
def gift(c):
    F = c.frames
    c.stance((0, "wide"))                                      # feet either side of the box
    c.prop(P.gift(k=0.84))
    c.face(0, "curious", dur=0, look_x=0.0, look_y=0.85)
    c.face(34, "curious", dur=0, look_x=0.0, look_y=0.85)
    c.face(46, "surprised", dur=6)
    c.face(68, "joy", dur=8)
    # up on its toes to sniff the box, a shake, then it jumps back as the lid pops
    c.k("head.rot", (0, 5), (18, -5, "soft"), (34, 4, "soft"), (40, 0, "out"), (47, -5, "out"), (64, 0, "back"), (F, 0))
    c.k("head.y", (0, 6), (34, 8), (38, 11, "in"), (46, -6, "out"), (60, 0, "back"), (F, 0))
    c.k("hip.y", (0, -5), (30, -5), (38, 6, "in"), (46, -7, "out"), (58, 0, "io"), (F, 0))
    c.osc("nose.y", 1.3, 8, t0=2, t1=26)
    c.arm("LR", (0, "lid"), (34, "lid"), (38, "lap", "in"), (48, "cheek", "back"), (62, "cheek"), (78, "cheer", "back"), (F, "cheer"))
    for s, ph in (("L", 0.0), ("R", 0.08)):
        c.osc(f"arm.{s}.sh", 9.0, 24, phase=ph, t0=82, t1=F)
    c.ears((0, 0), (36, 0), (42, -9, "out"), (60, 0, "back"), (F, 0))
    M.jump(c, 62, h=15, air=18, anti=8, sq=0.06, st=0.025, body=0.05, head=0.03, spread=6.0)   # happy hop (little headroom at full size)
    M.patter(c, 98, 128, period=10, lift=7.0)
    c.tailpose((0, "rest"), (40, "rest"), (52, "up", "back"), (F, "up"))
    c.wag(amp=4.0, period=60, lag=0.15, t0=0, t1=44, fade=8)
    c.wag(amp=12.0, period=24, lag=0.15, t0=52, t1=F + 40, fade=10)
    c.blink(20)


# --------------------------------------------------------------------------- badge_unlock (plays once)
def badge_unlock(c):
    F = c.frames
    c.face(0, "neutral", dur=0, tongue=0)
    c.face(28, "surprised", dur=6, look_x=0.8, look_y=-0.6)
    c.face(44, "joy", dur=8)
    # wind up on bent knees, then up on the toes as the paw shoots up: the badge pops into it
    c.arm("R", (0, "rest"), (8, "lap", "out"), (22, "hold_up", "back"), (F, "hold_up"))
    M.addkeys(c, "hip.y", (2, 0.0), (10, 11.0, "out"), (20, -6.0, "out"), (29, 2.0, "io"), (38, 0.0, "io"))
    M.addkeys(c, "root.sy", (2, 0.0), (9, -0.045, "out"), (20, 0.03, "out"), (28, -0.015, "io"), (38, 0.0, "io"))
    M.addkeys(c, "root.sx", (2, 0.0), (9, 0.035, "out"), (20, -0.02, "out"), (28, 0.01, "io"), (38, 0.0, "io"))
    c.arm("L", (0, "rest"), (22, "rest"), (36, "cheek", "back"), (54, "cheek"), (68, "hip", "back"), (F, "hip"))
    c.k("head.rot", (0, 0), (22, 0), (34, 6, "back"), (F, 6))
    M.jump(c, 44, h=14, air=16, anti=6, sq=0.05, st=0.02, body=0.04, head=0.03, spread=6.0)     # launch 50, land 66
    # showing it off: weight on the right leg, the left foot pops up
    c.k("hip.x", (0, 0), (72, 0), (84, 5, "io"), (106, 5), (F, 0, "io"))
    M.addkeys(c, "foot.L.y", (76, 0.0), (86, -14.0, "back"), (102, -14.0), (112, 0.0, "in"))
    M.addkeys(c, "foot.L.x", (76, 0.0), (86, 8.0, "out"), (102, 8.0), (112, 0.0, "io"))
    M.addkeys(c, "foot.L.rot", (76, 0.0), (86, 22.0, "back"), (102, 22.0), (112, 0.0, "io"))
    c.tailpose((0, "rest"), (22, "rest"), (34, "out", "back"), (F, "out"))       # swishing low, clear of the badge
    c.wag(amp=11.0, period=30, lag=0.15, t0=30, t1=F + 40, fade=8)
    c.prop(P.badge("R", "hold_up", t_pop=24))
    c.prop(P.sparkles([(96, 150, 22, "yellow", 0), (420, 90, 24, "teal", 11), (450, 230, 18, "coral", 22)]))


# --------------------------------------------------------------------------- big_celebration
def big_celebration(c):
    F = c.frames
    c.face(0, "smiley", dur=0)
    c.face(12, "joy", dur=6)
    c.face(F, "smiley", dur=8)
    t0, air, H = 16, 42, 122.0
    td = t0 + air
    # deep crouch, backflip around the tummy with the legs tucked in, big landing
    def y(t):
        if t <= t0 or t >= td:
            return 0.0
        u = (t - t0) / float(air)
        return -H * 4 * u * (1 - u)
    c.add("root.y", y)
    c.k("root.rot", (0, 0), (t0 - 1, 0), (td - 4, 360, "soft"), (F, 360))
    c.k("root.pivot", (0, 0), (t0 - 3, 0), (t0 + 5, 150, "io"), (td - 9, 150), (td - 1, 0, "io"), (F, 0))
    M.addkeys(c, "hip.y", (2, 0.0), (12, 20.0, "out"), (t0, 0.0, "in"), (t0 + 3, -5.0, "out"), (t0 + 9, 0.0, "io"), (td - 1, 0.0, "hold"),
              (td + 4, 22.0, "out"), (td + 12, -4.0, "io"), (td + 22, 0.0, "io"))
    M.addkeys(c, "root.sy", (2, 0.0), (13, -0.09, "out"), (t0 + 4, 0.10, "io"), (t0 + 14, 0.0, "io"), (td - 6, 0.0, "hold"), (td - 1, 0.08, "io"),
              (td + 3, -0.12, "out"), (td + 11, 0.05, "io"), (td + 22, 0.0, "io"))
    M.addkeys(c, "root.sx", (2, 0.0), (13, 0.07, "out"), (t0 + 4, -0.07, "io"), (t0 + 14, 0.0, "io"), (td - 6, 0.0, "hold"), (td - 1, -0.05, "io"),
              (td + 3, 0.10, "out"), (td + 11, -0.04, "io"), (td + 22, 0.0, "io"))
    M.addkeys(c, "head.y", (2, 0.0), (13, 6.0, "out"), (t0 + 5, -2.0, "io"), (td - 2, 0.0, "io"), (td + 4, 8.0, "out"), (td + 13, -2.0, "io"), (td + 24, 0.0, "io"))
    c.auto.update({"ear.rot": 0.35, "tuft.rot": 0.5, "tail.rot": 0.25, "arm.y": 0.2})
    for s in "LR":                                             # knees to the chest for the flip, feet wide for the landing
        M.addkeys(c, f"foot.{s}.y", (t0 + 3, 0.0), (t0 + 12, -20.0, "out"), (td - 12, -20.0), (td - 3, 0.0, "in"))
        M.addkeys(c, f"foot.{s}.x", (t0 + 3, 0.0), (t0 + 12, 6.0, "out"), (td - 12, 6.0), (td - 2, 13.0, "io"), (F, 13.0, "hold"))
    # the feet come back together with two little steps at the end
    M.step(c, "R", 114, lift=8, dur=12, sole=0.3, grow=0.03)
    M.addkeys(c, "foot.R.x", (114, 0.0), (126, -13.0, "io"), (F, -13.0, "hold"))
    M.step(c, "L", 128, lift=8, dur=12, sole=0.3, grow=0.03)
    M.addkeys(c, "foot.L.x", (128, 0.0), (140, -13.0, "io"), (F, -13.0, "hold"))
    # arms: swing down, tuck for the flip, fling up on the landing and keep pumping
    c.arm("LR", (0, "cheer"), (12, "lap", "io"), (t0 + 6, "belly", "out"), (td - 8, "belly"), (td + 6, "cheer_hi", "back"), (td + 20, "cheer", "io"), (F, "cheer"))
    for s, ph in (("L", 0.0), ("R", 0.07)):
        c.osc(f"arm.{s}.sh", 12.0, 24, phase=ph, t0=td + 20, t1=td + 20 + 72)
    M.bob(c, 24, amp=5.0, t0=td + 20, t1=td + 20 + 72, st=0.02)
    c.k("head.rot", (0, 0), (td + 8, 0), (td + 20, -3, "soft"), (td + 44, 3, "soft"), (td + 68, -3, "soft"), (F, 0, "soft"))
    c.tailpose((0, "up"))
    c.wag(amp=11.0, period=25, lag=0.15)
    c.prop(P.dust(td, 256, n_puffs=4, size=22))
    c.prop(P.confetti(t0=td - 2, origin=(256, 250), t_end=F))
    c.prop(P.sparkles([(84, 170, 22, "yellow", 0), (430, 120, 26, "teal", 11), (456, 260, 18, "coral", 22),
                       (60, 300, 18, "lilac", 33), (256, 36, 20, "yellow", 44)]))


CLIPS = {
    "idle": dict(frames=180, loop=True, fn=idle, calm=12),              # calm: its first frame is exactly the keyed rest pose
    "wave": dict(frames=120, loop=True, fn=wave),
    "happy": dict(frames=120, loop=True, fn=happy, scale=0.93),
    "cheer": dict(frames=120, loop=True, fn=cheer, scale=0.875),
    "concerned": dict(frames=150, loop=True, fn=concerned),
    "thinking": dict(frames=180, loop=True, fn=thinking),
    "sleepy": dict(frames=180, loop=True, fn=sleepy, scale=1.08, calm=12),
    "hop_in": dict(frames=120, loop=False, fn=hop_in, scale=0.9, settle=True),   # settle: ends exactly on idle's first frame
    "pop_up": dict(frames=100, loop=False, fn=pop_up),
    "breathe": dict(frames=480, loop=True, fn=breathe, scale=1.08),
    "deep_sleep": dict(frames=240, loop=True, fn=deep_sleep, scale=1.08),
    "peek_phone": dict(frames=180, loop=True, fn=peek_phone),
    "meditate": dict(frames=240, loop=True, fn=meditate, scale=1.04),
    "ring_bell": dict(frames=96, loop=True, fn=ring_bell),
    "read_chart": dict(frames=150, loop=True, fn=read_chart),
    "carry_cloud": dict(frames=120, loop=True, fn=carry_cloud, scale=0.86),
    "gift": dict(frames=130, loop=False, fn=gift),
    "badge_unlock": dict(frames=120, loop=False, fn=badge_unlock),
    "big_celebration": dict(frames=150, loop=False, fn=big_celebration, scale=0.79),
}
