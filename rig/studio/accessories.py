"""Compatibility view of the worn items (v3 names).  The drawings live in studio/library/ (wear_*.py) and are
registered in studio/registry.py with the place on the body they take (REG.wear[name].zone)."""
from __future__ import annotations

from .registry import Make, ensure_loaded

REG = ensure_loaded()


def _factory(name):
    def make(color=None, L=120):
        return REG.wear[name].factory(Make(L=L, color=color))
    return make


ACCESSORIES = {name: _factory(name) for name in REG.wear}
# items that cannot be worn together (they sit in the same place)
EXCLUSIVE = [g for g in ({n for n, w in REG.wear.items() if w.zone == z} for z in sorted({w.zone for w in REG.wear.values()}))
             if len(g) > 1]
