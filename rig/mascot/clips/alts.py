"""Rare alternate takes: extra files an app can play once in a while instead of the regular loop.

Every `idle_alt_*` starts and ends on exactly the first frame of `idle`, and `sleepy_alt_*` on the first
frame of `sleepy`, so a take can be dropped in between two loops with no visible seam.
"""
from __future__ import annotations

from .. import props as P
from . import moves as M
from .core import idle_base, sleepy_base


# --------------------------------------------------------------------------- a butterfly lands on the nose
def idle_alt_butterfly(c):
    F = c.frames                                               # 360
    idle_base(c)
    land, leave = 176, 262
    c.prop(P.butterfly([(8, -30, 150), (44, 96, 96), (84, 214, 170), (118, 344, 112), (148, 392, 214), (166, 300, 236),
                        (land, 256, 250), (leave, 256, 250), (286, 330, 150), (312, 420, 76), (334, 540, 20)], land, leave, size=1.25))
    # eyes (and a little of the head) follow it in, go cross-eyed when it lands, follow it out
    M.look(c, (0, 0, 0), (30, 0, 0), (44, -0.9, -0.7, "out"), (84, -0.4, -0.3, "io"), (118, 0.8, -0.8, "io"), (148, 0.9, -0.1, "io"),
           (166, 0.3, 0.2, "io"), (land + 4, 0, 0.35, "io"), (leave, 0, 0.35), (286, 0.6, -0.6, "out"), (318, 0.95, -0.9, "io"), (342, 0, 0, "io"), (F, 0, 0))
    c.k("eye.cross", (0, 0), (166, 0), (land + 6, 1.0, "back"), (leave - 2, 1.0), (leave + 8, 0, "out"), (F, 0))
    c.k("head.rot", (0, 0), (36, 0), (50, -5, "io"), (118, 4, "io"), (150, 3, "io"), (land, 0, "io"), (leave, 0), (290, 5, "out"), (322, 7, "io"), (348, 0, "io"), (F, 0))
    c.k("head.y", (0, 0), (land - 6, 0), (land + 2, 3, "out"), (land + 14, 0, "back"), (F, 0))
    # the whole body follows: leaning after it, up on the toes when it flies high
    M.weight(c, (0, 0), (34, 0), (50, -6, "io"), (118, 6, "io"), (150, 5), (164, 6, "io"), (leave + 2, 6), (leave + 16, 0, "io"), (F, 0))
    M.addkeys(c, "hip.y", (34, 0.0), (48, -5.0, "io"), (84, -1.0, "io"), (118, -6.0, "io"), (150, 0.0, "io"))
    # ...and freezes in mid-step when it lands: one foot in the air, wobbling, not daring to move
    M.addkeys(c, "foot.L.y", (158, 0.0), (170, -19.0, "out"), (leave, -19.0), (leave + 9, 0.0, "in"))
    M.addkeys(c, "foot.L.x", (158, 0.0), (170, 4.0, "out"), (leave, 4.0), (leave + 9, 0.0, "io"))
    M.addkeys(c, "foot.L.sole", (158, 0.0), (170, 0.55, "out"), (leave, 0.55), (leave + 8, 0.0, "in"))
    M.addkeys(c, "foot.L.s", (158, 0.0), (170, 0.06, "out"), (leave, 0.06), (leave + 8, 0.0, "in"))
    c.osc("hip.x", 1.8, 22, t0=186, t1=252)
    c.osc("body.rot", 1.5, 22, t0=186, t1=252, phase=0.5)
    c.osc("foot.L.y", 2.0, 22, t0=186, t1=252, phase=0.25)
    c.arm("LR", (0, "rest"), (160, "rest"), (174, "relax", "back"), (leave - 2, "relax"), (leave + 10, "rest", "io"))   # arms out for balance
    for s, ph in (("L", 0.0), ("R", 0.5)):
        c.osc(f"arm.{s}.sh", 3.0, 22, t0=186, t1=252, phase=ph)
    M.squash(c, leave + 9, amount=0.03, pre=3, post=12)        # the foot comes down with relief
    # surprise, then delight
    for ch, a, b in (("eye.w", 1.0, 1.1), ("eye.h", 1.0, 1.1)):
        c.k(ch, (0, a), (land - 4, a), (land + 4, b, "back"), (220, b), (232, a, "io"), (F, a))
    c.k("mouth.o", (0, 0), (land - 2, 0), (land + 6, 0.9, "back"), (212, 0.9), (224, 0, "io"), (F, 0))
    c.k("tongue", (0, 1), (land - 4, 1), (land + 2, 0, "io"), (332, 0), (346, 1, "back"), (F, 1))
    M.happy_squint(c, 232, 254)
    c.k("mouth.open", (0, 0), (268, 0), (278, 0.85, "back"), (326, 0.85), (340, 0, "io"), (F, 0))
    c.k("blush", (0, 1), (land, 1), (land + 20, 1.35, "io"), (300, 1.35), (340, 1, "io"), (F, 1))
    M.ear_flick(c, "L", 42, amp=12)
    M.ear_flick(c, "R", land + 2, amp=14)
    M.ear_flick(c, "L", land + 6, amp=14)
    c.pulse("nose.y", 198, -1.8, up=3, down=5)
    c.pulse("nose.y", 208, -1.8, up=3, down=5)
    # the tail holds still while it sits, then gives a happy flick
    c.tailpose((leave, "rest"), (leave + 12, "up", "back"), (318, "up"), (344, "rest", "io"), (F, "rest"))
    c.wag(amp=8.0, period=22, lag=0.15, t0=leave + 6, t1=336, fade=12)
    # bye-bye
    M.wave(c, "R", 280, 320, period=17, up=9, down=12)
    c.blink(100)
    c.blink(leave + 4)


# --------------------------------------------------------------------------- a sneeze that knocks it off its feet
def idle_alt_sneeze(c):
    F = c.frames                                               # 180
    idle_base(c)
    A1, A2, CH = 30, 62, 86                                    # "ah...", "AH...", "CHOO!"
    SIT, UP = CH + 13, 150                                     # lands on its bottom; gets up again
    for t in (8, 15, 22):
        c.pulse("nose.y", t, -2.0, up=3, down=5)
    c.k("eye.cross", (0, 0), (6, 0), (14, 0.7, "io"), (A1, 0.7), (A1 + 10, 0, "io"), (F, 0))
    c.k("look.y", (0, 0), (6, 0), (14, 0.5, "io"), (A1, 0.5), (A1 + 10, 0, "io"), (F, 0))
    # wind-ups: head back, chest up, up on the toes, eyes squeezing shut
    c.k("head.rot", (0, 0), (A1 - 8, 0), (A1 + 12, -6, "out"), (A2 - 8, -3, "io"), (A2 + 14, -11, "out"), (CH - 3, -12), (CH + 3, 10, "in"),
        (SIT + 2, 5, "out"), (SIT + 16, -3, "io"), (UP - 8, 0, "io"), (F, 0))
    c.k("head.y", (0, 0), (A1 - 8, 0), (A1 + 12, -3, "out"), (A2 - 8, -1.5, "io"), (A2 + 14, -4, "out"), (CH - 3, -4.5), (CH + 3, 13, "in"),
        (SIT + 3, 9, "out"), (SIT + 14, 0, "back"), (F, 0))
    M.addkeys(c, "body.sy", (A1 - 8, 0), (A1 + 12, 0.03, "out"), (A2 - 8, 0.012, "io"), (A2 + 14, 0.045, "out"), (CH - 3, 0.05), (CH + 3, -0.07, "in"),
              (CH + 12, 0.02, "out"), (SIT + 10, 0, "io"))
    M.addkeys(c, "hip.y", (A1 - 8, 0.0), (A1 + 12, -3.0, "out"), (A2 - 8, -1.0, "io"), (A2 + 14, -5.0, "out"), (CH - 3, -5.5), (CH + 2, 5.0, "in"), (CH + 8, 0.0, "io"))
    # CHOO: the blast lifts it off its feet and it lands on its bottom, legs out in front
    c.stance((0, "stand"), (CH + 3, "stand"), (SIT, "sit", "in"), (UP, "sit"), (UP + 13, "stand", "out"), (F, "stand"))
    M.addkeys(c, "root.y", (CH + 1, 0.0), (CH + 7, -17.0, "out"), (SIT, 0.0, "in"))
    M.squash(c, SIT + 1, amount=0.07, pre=2, post=16, knees=0.0, body=0.05, head=0.03)
    M.addkeys(c, "root.x", (CH + 1, 0.0), (SIT, 0.0), (SIT + 1, 0.0))
    # ...sits there dazed, then hops back up
    M.addkeys(c, "root.y", (UP - 1, 0.0), (UP + 6, -15.0, "out"), (UP + 13, 0.0, "in"))
    M.addkeys(c, "root.sy", (UP - 9, 0.0), (UP - 2, -0.05, "out"), (UP + 4, 0.04, "io"), (UP + 13, -0.045, "in"), (UP + 20, 0.02, "io"), (UP + 28, 0.0, "io"))
    M.addkeys(c, "root.sx", (UP - 9, 0.0), (UP - 2, 0.04, "out"), (UP + 4, -0.03, "io"), (UP + 13, 0.035, "in"), (UP + 20, -0.015, "io"), (UP + 28, 0.0, "io"))
    M.addkeys(c, "hip.y", (UP + 12, 0.0), (UP + 16, 9.0, "out"), (UP + 23, -2.0, "io"), (UP + 29, 0.0, "io"))
    for s in "LR":                                             # the feet wave in the air for a moment after the plop
        c.pulse(f"foot.{s}.y", SIT, -12, up=5, down=14, e_down="bounce")
        c.pulse(f"foot.{s}.rot", SIT, 14, up=5, down=16, e_down="back")
    # face
    c.k("eye.open", (0, 1), (A1 - 4, 1), (A1 + 12, 0.55, "io"), (A2 - 8, 0.8, "io"), (A2 + 12, 0.0, "io"), (SIT + 4, 0.0), (SIT + 12, 1.0, "out"), (F, 1))
    c.k("eye.arc", (0, -0.45), (A2, -0.45), (CH - 2, -0.2, "io"), (CH + 3, 0.7, "out"), (SIT + 4, 0.3), (SIT + 12, -0.45, "hold"), (F, -0.45))
    c.k("eye.w", (0, 1), (SIT + 6, 1), (SIT + 12, 1.12, "back"), (SIT + 36, 1.12), (SIT + 46, 1, "io"), (F, 1))
    c.k("eye.h", (0, 1), (SIT + 6, 1), (SIT + 12, 1.12, "back"), (SIT + 36, 1.12), (SIT + 46, 1, "io"), (F, 1))
    c.k("brow.show", (0, 0), (A1 - 4, 0), (A1 + 6, 1, "io"), (SIT + 30, 1), (SIT + 42, 0, "io"), (F, 0))
    c.k("brow.tilt", (0, 8), (A1 - 4, 8), (A1 + 6, 14, "io"), (A2, 14), (CH + 3, -12, "in"), (SIT + 10, 6, "io"), (F, 8))
    c.k("brow.y", (0, 4), (A2 + 12, 9, "io"), (CH + 3, -2, "in"), (SIT + 10, 10, "back"), (SIT + 34, 10), (F, 4, "io"))
    c.k("mouth.open", (0, 0), (A1 - 4, 0), (A1 + 12, 0.5, "out"), (A2 - 8, 0.3, "io"), (A2 + 14, 0.95, "out"), (CH - 2, 1.0), (CH + 4, 0.25, "in"),
        (SIT + 2, 0.0, "io"), (F, 0))
    c.k("mouth.o", (0, 0), (SIT + 4, 0), (SIT + 12, 0.8, "back"), (SIT + 30, 0.8), (SIT + 40, 0, "io"), (F, 0))
    c.k("mouth.smile", (0, 1), (A1 - 4, 1), (A1 + 12, 0.2, "io"), (SIT + 34, 0.2), (SIT + 46, 1.15, "back"), (UP + 16, 1.15), (F, 1, "io"))
    c.k("tongue", (0, 1), (A1 - 6, 1), (A1, 0, "io"), (UP + 16, 0), (F - 4, 1, "back"), (F, 1))
    c.k("blush", (0, 1), (SIT, 1), (SIT + 24, 1.45, "io"), (UP + 6, 1.45), (F, 1, "io"))
    c.ears((0, 0), (A2, 0), (A2 + 14, 9, "out"), (CH - 2, 10), (CH + 4, -8, "in"), (SIT + 2, 16, "out"), (SIT + 22, 0, "back"), (F, 0))
    c.blink(SIT + 22, dur=8)
    c.blink(SIT + 34, dur=8)
    # arms: flung out by the blast, paws down between the feet while it sits, one rubs the nose
    c.arm("LR", (0, "rest"), (A2 - 6, "rest"), (A2 + 14, "relax", "out"), (CH - 2, "relax"), (CH + 5, (64, -18, 0, 1.15), "out"),
          (SIT + 6, "lap", "back"), (UP - 6, "lap"), (UP + 8, "relax", "out"), (F - 6, "rest", "io"))
    c.arm("R", (SIT + 16, "lap"), (SIT + 28, "mouth", "back"), (UP - 16, "mouth"), (UP - 6, "lap", "io"))
    for t in (SIT + 31, SIT + 39):
        c.pulse("arm.R.el", t, 10, up=3, down=4)
        c.pulse("nose.y", t + 1, -1.5, up=3, down=4)
    # the tail poofs with the sneeze, stays big while it sits, then settles with a wobble
    c.k("tail.fluff", (0, 1), (CH - 1, 1), (CH + 5, 1.32, "back"), (SIT + 30, 1.28), (UP - 4, 1.0, "io"), (F, 1))
    c.tailpose((CH - 2, "rest"), (CH + 5, "up", "back"), (SIT, "ground_up", "io"), (UP - 2, "ground", "io"), (UP + 13, "rest", "io"), (F, "rest"))
    c.prop(P.sneeze_burst(CH + 2))
    c.prop(P.dust(SIT + 1, 256, n_puffs=4, size=16))


# --------------------------------------------------------------------------- peekaboo behind the paws
def idle_alt_peekaboo(c):
    F = c.frames                                               # 180
    idle_base(c)
    UP, PEEK, OPEN = 12, 70, 106
    c.arm("LR", (0, "rest"), (UP - 4, "relax", "out"), (UP + 14, "cover_eyes", "back"), (OPEN - 6, "cover_eyes"), (OPEN - 2, "cover_eyes", "hold"),
          (OPEN + 8, "cheer", "back"), (148, "cheer"), (F - 4, "rest", "io"))
    for s_ in "LR":                                            # paws spread a little to hide the eyes properly
        c.k(f"hand.{s_}.s", (0, 1.0), (UP, 1.0), (UP + 14, 1.22, "back"), (OPEN - 4, 1.22), (OPEN + 8, 1.0, "io"), (F, 1.0))
    # one paw slides off for a peek, then snaps back
    c.arm("R", (PEEK, "cover_eyes"), (PEEK + 10, "peek", "back"), (PEEK + 22, "peek"), (PEEK + 28, "cover_eyes", "out"))
    M.look(c, (0, 0, 0), (PEEK, 0, 0), (PEEK + 8, 0.7, 0.0, "out"), (PEEK + 22, 0.7, 0.0), (PEEK + 28, 0, 0, "io"), (F, 0, 0))
    # eyes are shut behind the paws; only the peeking one opens
    c.k("eye.L.blink", (0, 0), (UP + 8, 0), (UP + 14, 1, "io"), (OPEN - 2, 1), (OPEN - 1, 0, "hold"), (F, 0))
    c.k("eye.R.blink", (0, 0), (UP + 8, 0), (UP + 14, 1, "io"), (PEEK + 2, 1), (PEEK + 9, 0, "out"), (PEEK + 22, 0), (PEEK + 27, 1, "io"),
        (OPEN - 2, 1), (OPEN - 1, 0, "hold"), (F, 0))
    c.k("head.y", (0, 0), (UP, 0), (UP + 14, 4, "io"), (OPEN - 6, 4), (OPEN - 2, 7, "in"), (OPEN + 6, -3, "out"), (OPEN + 20, 0, "back"), (F, 0))
    c.k("head.rot", (0, 0), (UP + 14, 0), (40, -3, "soft"), (60, 3, "soft"), (PEEK + 10, 5, "io"), (PEEK + 28, 0, "io"), (OPEN + 8, -4, "out"), (130, 4, "soft"), (160, 0, "soft"), (F, 0))
    # hiding: it makes itself small, knees together, and cannot keep its feet still for giggling
    c.k("hip.y", (0, 0), (UP, 0), (UP + 14, 9, "io"), (OPEN - 12, 9), (OPEN - 6, 0, "io"), (F, 0))
    for s_ in "LR":
        c.k(f"leg.{s_}.bend", (0, 1.0), (UP, 1.0), (UP + 14, -1.0, "io"), (OPEN - 12, -1.0), (OPEN - 6, 1.0, "io"), (F, 1.0))
        c.k(f"foot.{s_}.rot", (0, 0.0), (UP, 0.0), (UP + 14, -10.0, "io"), (OPEN - 12, -10.0), (OPEN - 6, 0.0, "io"), (F, 0.0))
    M.patter(c, 28, 58, period=10, lift=5.0)
    for t in (30, 40, 50):
        c.pulse("body.sy", t, 0.02, up=4, down=6)
    M.ear_flick(c, "L", 34, amp=12)
    M.ear_flick(c, "R", 46, amp=12)
    M.ear_flick(c, "L", 58, amp=9)
    c.k("mouth.open", (0, 0), (UP + 6, 0), (UP + 16, 0.5, "io"), (OPEN - 4, 0.5), (OPEN + 6, 1.0, "back"), (150, 1.0), (166, 0, "io"), (F, 0))
    c.k("tongue", (0, 1), (UP, 1), (UP + 8, 0, "io"), (160, 0), (172, 1, "back"), (F, 1))
    # ta-da: a star jump, eyes shut with joy for a moment, then bright
    c.k("eye.open", (0, 1), (OPEN - 2, 1), (OPEN - 1, 0, "hold"), (OPEN + 26, 0), (OPEN + 34, 1, "back"), (F, 1))
    c.k("eye.arc", (0, -0.45), (UP + 14, -1.0, "io"), (OPEN - 2, -1.0), (OPEN + 6, 1.0, "back"), (OPEN + 26, 1.0), (OPEN + 34, -0.45, "hold"), (F, -0.45))
    c.k("blush", (0, 1), (OPEN, 1), (OPEN + 10, 1.4, "io"), (150, 1.4), (F, 1, "io"))
    M.jump(c, OPEN - 6, h=16, air=16, anti=6, sq=0.06, st=0.025, body=0.05, head=0.03, crouch=0.0, tuck=3.0, spread=15.0)
    c.tailpose((OPEN - 4, "rest"), (OPEN + 8, "up", "back"), (150, "up"), (172, "rest", "io"), (F, "rest"))
    c.wag(amp=10.0, period=22, lag=0.15, t0=OPEN + 2, t1=166, fade=12)
    c.prop(P.sparkles([(96, 190, 18, "yellow", OPEN + 2), (420, 150, 20, "teal", OPEN + 8), (256, 40, 16, "coral", OPEN + 14)]))
    c.prop(P.dust(OPEN + 16, 256, n_puffs=2, size=12))


# --------------------------------------------------------------------------- sleep bubble (variation of `sleepy`)
def sleepy_alt_bubble(c):
    F = c.frames                                               # 180, same first frame as core.sleepy
    POP = 150
    sleepy_base(c)
    c.ears((POP - 2, 9), (POP + 5, -6, "out"), (POP + 26, 9, "back"))
    c.k("head.rot", (0, 7), (POP - 2, 9, "soft"), (POP + 5, 1, "out"), (POP + 22, 5, "io"), (F, 7, "io"))
    c.k("head.y", (0, 7), (POP - 2, 10, "soft"), (POP + 5, -1, "out"), (POP + 22, 5, "io"), (F, 7, "io"))
    c.k("body.rot", (0, 1.5), (F, 1.5))
    # the pop startles both eyes open for an instant; then they droop shut again
    c.k("eye.open", (0, 0), (POP, 0, "hold"), (POP + 5, 1.12, "out"), (POP + 12, 1.0, "io"), (POP + 18, 0.5, "io"), (F - 4, 0, "io"), (F, 0))
    c.k("eye.arc", (0, -1), (F - 6, -1), (F, -1))
    c.k("brow.show", (0, 0), (POP, 0), (POP + 5, 1, "out"), (POP + 16, 0, "io"), (F, 0))
    c.k("brow.y", (0, 8), (F, 8))
    c.k("mouth.o", (0, 0), (POP, 0), (POP + 5, 0.8, "out"), (POP + 16, 0, "io"), (F, 0))
    c.pulse("arm.L.sh", POP + 1, 14, up=4, down=14, e_down="back")
    c.pulse("arm.R.sh", POP + 1, 14, up=4, down=14, e_down="back")
    for s in "LR":                                             # the feet jump too
        c.pulse(f"foot.{s}.y", POP + 1, -9, up=4, down=14, e_down="bounce")
        c.pulse(f"foot.{s}.rot", POP + 1, 12, up=4, down=16, e_down="back")
    c.prop(P.sleep_bubble([(8, 70, 0.55), (76, 138, 0.9)], POP, big=62.0))
    c.prop(P.zzz([(134, 44, 20, 0), (158, 8, 26, 24)], rel=True))


# settle: the take starts with everything at rest and ends exactly on its keyed pose, which is the base clip's first frame
CLIPS = {
    "idle_alt_butterfly": dict(frames=360, loop=True, fn=idle_alt_butterfly, settle=True),
    "idle_alt_sneeze": dict(frames=180, loop=True, fn=idle_alt_sneeze, settle=True),
    "idle_alt_peekaboo": dict(frames=180, loop=True, fn=idle_alt_peekaboo, settle=True),
    "sleepy_alt_bubble": dict(frames=180, loop=True, fn=sleepy_alt_bubble, scale=1.08, settle=True),
}
