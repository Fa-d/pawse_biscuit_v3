"""Compatibility view of the motions (v3 names).  The motions themselves live in studio/library/ and are
registered in studio/registry.py; read REG.motions for everything about them."""
from __future__ import annotations

from .registry import ensure_loaded

REG = ensure_loaded()


def per(L, approx):
    """The period closest to `approx` that fits a whole number of times into L frames."""
    return L / max(1, round(L / approx))


# name -> (fn, paws it wants, ok while sitting)       fn takes a registry.Act (v4); v3 motions took (clip, k, hands)
MOTIONS = {name: (m.fn, m.paws, m.sit != "no") for name, m in REG.motions.items()}
# how much the tail wags with each motion (degrees per joint)
WAG = {name: m.wag for name, m in REG.motions.items()}
