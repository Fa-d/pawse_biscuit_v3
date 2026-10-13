"""Turning motions (v5): the mascot turns away from the viewer and back, looks back over its shoulder, spins all the
way round.  They key body.yaw and head.yaw (mascot/views.py): the front drawing turns smoothly to three-quarter, then
snaps with a smear to the drawn side and back views.  A mascot without drawn side and back views turns as far as
three-quarter and shows its front past that (rule R24 notes it).

Every move loops: a turn that goes all the way round ends where it began (360 degrees is the front again).
"""
from __future__ import annotations

from ..registry import motion
from .acting import M, ease, frames_of, math


@motion("turn_around", "Turn around", "🔄", doing="turning around", paws=2, min_paws=0, wag=8, tags=("turn",), face="smiley",
        sit_alt="sway")
def turn_around(m):
    """Turns away (through the side view to the back), stays a moment, and turns on round to face the viewer again."""
    c, L, k = m.c, m.L, m.k
    a, b, d, e = frames_of(L, 0.06, 0.36, 0.6, 0.9)
    M.turn(c, a, 180.0, dur=b - a)
    M.turn(c, d, 360.0, dur=e - d)
    for s in m.hands:
        c.arm(s, (0, "rest"), (a + (b - a) // 2, "relax", "io"), (b, "rest", "io"), (d + (e - d) // 2, "relax", "io"), (e, "rest", "io"),
              (L, "rest"))
    c.k("root.y", (0, 0.0), (b - 2, 0.0, "hold"), (b + 4, -6.0 * k, "out"), (b + 12, 0.0, "io"), (L, 0.0))
    return a + int((b - a) * 0.3)                     # the still: three-quarter, on the way round


@motion("look_back", "Look back", "👀", doing="looking back over the shoulder", paws=2, min_paws=0, wag=12, tags=("turn",),
        face="smiley", sit_alt="look_around")
def look_back(m):
    """Faces away and looks back over the shoulder at the viewer, then away again; the tail wags."""
    c, L = m.c, m.L
    c.set("body.yaw", 158.0)
    t0, t1 = frames_of(L, 0.14, 0.7)
    M.look_back(c, t0, t1, at=-112.0, dur=max(8, L // 9))
    c.k("head.rot", (0, 0.0), (t0, 0.0, "hold"), (t0 + 10, -6.0, "io"), (t1, -6.0, "hold"), (t1 + 12, 0.0, "io"), (L, 0.0))
    for s in m.hands:
        c.arm(s, (0, "rest"))
    return (t0 + t1) // 2


@motion("full_spin", "Full spin", "🌀", doing="spinning all the way round", paws=2, min_paws=0, wag=10, tags=("turn",),
        face="joy", sit_alt="sway")
def full_spin(m):
    """A real spin: all the way round (front, side, back, the other side, front), up on tiptoe with the paws out."""
    c, L, k = m.c, m.L, m.k
    turns = max(1, round(L / 90.0))
    per = L / float(turns)
    a, b = 0.2, 0.85                                  # each turn: facing front, a whirl all the way round, front again

    def u(t):
        x = (t % per) / per
        return 0.0 if x < a else (1.0 if x > b else ease("io", (x - a) / (b - a)))

    c.add("body.yaw", lambda t: 360.0 * (math.floor(t / per + 1e-9) + u(t)) if t < L else 360.0 * turns)
    c.add("root.y", lambda t: -10.0 * k * math.sin(math.pi * u(t)))
    c.stance((0, "tiptoe"))
    for s in m.hands:
        c.arm(s, (0, "cheer_out"))
    c.osc("body.rot", 2.0 * k, per)
    return int(per * (a + (b - a) * 0.22))
