"""Loop-safe bits of acting that the motions are built from.

Everything here returns to where it started by the end of the loop: bumps rise and fall back, shakes are windowed
sine waves that start and end at rest, alternating poses end on the pose they began with.  Built only from rig
channels and named poses, so every mascot can play them.
"""
from __future__ import annotations

import math

from mascot.clip import Track, ease
from mascot.clips import moves as M

__all__ = ["M", "bump", "shake", "alternate", "shape", "hold_pose", "sway_hips", "beat", "steps", "frames_of", "ease", "math",
           "wrap_pulse"]


def frames_of(L, *us):
    """Fractions of the loop -> whole frames."""
    return [int(round(u * L)) for u in us]


def bump(c, ch, t0, t1, amp, rise=None, fall=None, e_in="out", e_out="io"):
    """Additive bump on a channel: 0 at t0, `amp` after `rise` frames, held, back to 0 at t1."""
    rise = max(1, int(rise if rise is not None else (t1 - t0) * 0.25))
    fall = max(1, int(fall if fall is not None else (t1 - t0) * 0.25))
    tr = Track(None)
    tr.key(t0, 0.0)
    tr.key(t0 + rise, amp, e_in)
    if t1 - fall > t0 + rise:
        tr.key(t1 - fall, amp, "hold")
    tr.key(t1, 0.0, e_out)
    c.add(ch, lambda t: tr.at(t) if t0 <= t <= t1 else 0.0)


def shake(c, ch, amp, t0, t1, cycles, phase=0.0):
    """`cycles` sine waves between t0 and t1 under a smooth window: starts and ends exactly at rest."""
    span = float(max(1, t1 - t0))

    def fn(t):
        if t <= t0 or t >= t1:
            return 0.0
        u = (t - t0) / span
        w = math.sin(math.pi * u) ** 2
        return amp * w * math.sin(2 * math.pi * (cycles * u + phase))

    c.add(ch, fn)


def wrap_pulse(c, ch, t0, amp, L, up=6, down=14, e_up="out", e_down="io"):
    """An additive bump like Clip.pulse that may run over the end of the loop: what falls past the last frame
    comes back at the start, so frame 0 and the last frame always agree."""
    def fn(t):
        d = (t - t0) % L
        if d <= 0 or d >= up + down:
            return 0.0
        if d <= up:
            return amp * ease(e_up, d / float(up))
        return amp * (1 - ease(e_down, (d - up) / float(down)))
    c.add(ch, fn)


def beat(c, ch, amp, period, L, phase=0.0, sharp=1.0):
    """A pulse once per period all through the loop (period should divide L): 0 .. amp .. 0, `sharp` > 1 makes it
    a quick hit with a slower release."""
    def fn(t):
        u = ((t / period) + phase) % 1.0
        v = 0.5 - 0.5 * math.cos(2 * math.pi * u)
        return amp * v ** sharp
    c.add(ch, fn)


def alternate(c, side, a, b, period, L, at_b=0.5, e_ab="in", e_ba="out", t0=0, t1=None):
    """Swing a paw between pose a and pose b once per period (a at the start of each period, b at at_b of it).
    Ends on pose a at t1 (default: the end of the loop)."""
    t1 = L if t1 is None else t1
    keys = [(t0, a)]
    t = float(t0)
    while t + period <= t1 + 1e-6:
        keys.append((int(round(t + period * at_b)), b, e_ab))
        keys.append((int(round(t + period)), a, e_ba))
        t += period
    if keys[-1][0] != t1:
        keys.append((t1, a, "io"))
    c.arm(side, *keys)


def shape(c, side, k):
    """Paw shape for the whole clip: 0 open, 1 fist, 2 thumb up, 3 pointing finger, 4 peace sign."""
    for s in side:
        c.set(f"hand.{s}.shape", float(k))


def hold_pose(c, side, pose, t_in, t_out, L, rest="rest", e_in="back", e_out="io", first=None):
    """rest -> pose (arrives at t_in) -> held -> rest (back at t_out .. L).  first: the pose at frame 0 (default rest)."""
    first = first or rest
    keys = [(0, first)]
    if t_in > 0:
        keys.append((t_in, pose, e_in))
    else:
        keys[0] = (0, pose)
    if t_out < L:
        keys.append((t_out, pose, "hold"))
        keys.append((L, first, e_out))
    else:
        keys.append((L, pose, "hold"))
    c.arm(side, *keys)


def sway_hips(c, amp, period, tilt=0.4, phase=0.0):
    """Hips (and so the whole upper body) swing side to side; the feet stay planted."""
    c.osc("hip.x", amp, period, phase=phase)
    c.osc("hip.rot", amp * tilt, period, phase=phase)
    c.osc("head.rot", -amp * tilt * 0.6, period, phase=phase + 0.05)


def steps(c, L, period, lift=10.0, dur=None, first="R", sole=0.6, grow=0.06):
    """Alternating steps on the spot through the whole loop (two steps per period)."""
    dur = dur or period / 2.0
    t, q = 0.0, 0
    while t + period / 2.0 <= L + 1e-6:
        M.step(c, first if q % 2 == 0 else ("L" if first == "R" else "R"), int(round(t)), lift=lift, dur=int(round(dur)), sole=sole, grow=grow)
        t += period / 2.0
        q += 1
