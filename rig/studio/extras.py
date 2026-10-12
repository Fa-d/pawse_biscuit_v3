"""Compatibility view of the v3 props and effects.  The drawings live in studio/library/ (props_*.py, effects_*.py)
and are registered in studio/registry.py; read REG.props and REG.effects for everything about them."""
from __future__ import annotations

from mascot.geom import heart_path  # noqa: F401  (v3 exported it from here)

from .registry import Make, ensure_loaded

REG = ensure_loaded()


def _factory(table, name):
    def make(side="R", color=None, L=120):
        return table[name].factory(Make(L=L, side=side, color=color))
    return make


PROPS = {name: _factory(REG.props, name) for name in REG.props}
EFFECTS = {name: _factory(REG.effects, name) for name in REG.effects}
