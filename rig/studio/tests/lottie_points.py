"""Where things are in a written Lottie file, for tests: the transform chains evaluated straight from the JSON (layers,
their parents and nested groups), so the rig's own idea of a point can be checked against what a player draws.

    M = group_matrix(doc, "left arm [side]", "hand", f)        # the first group called 'hand' in that layer, at frame f
    x, y = point(M)                                            # its origin on the canvas (point(M, (0, 17)): the paw)
"""
from __future__ import annotations

import math

import numpy as np

from mascot.views import prop_at


def transform(p, a, s, r):
    """3 x 3 matrix of a Lottie transform: T(p) R(r) S(s) T(-a)."""
    rr = math.radians(float(np.ravel(r)[0]))
    c, sn = math.cos(rr), math.sin(rr)
    T = np.array([[1, 0, p[0]], [0, 1, p[1]], [0, 0, 1.0]])
    R = np.array([[c, -sn, 0], [sn, c, 0], [0, 0, 1.0]])
    S = np.diag([float(s[0]) / 100.0, float(s[1]) / 100.0, 1.0])
    A = np.array([[1, 0, -a[0]], [0, 1, -a[1]], [0, 0, 1.0]])
    return T @ R @ S @ A


def _tr(d, t):
    return transform(prop_at(d["p"], t), prop_at(d["a"], t), prop_at(d["s"], t), prop_at(d["r"], t))


def layer(doc, name):
    for L in doc["layers"]:
        if L["nm"] == name:
            return L
    raise KeyError(f"no layer {name!r}")


def layer_matrix(doc, name, t):
    """World matrix of a layer (its parents included) at frame t of the file."""
    L = layer(doc, name) if isinstance(name, str) else name
    M = _tr(L["ks"], t)
    if "parent" in L:
        P = next(x for x in doc["layers"] if x["ind"] == L["parent"])
        M = layer_matrix(doc, P, t) @ M
    return M


def _find(items, name, M, t):
    for it in items:
        if it.get("ty") != "gr":
            continue
        G = M @ _tr(it["it"][-1], t)
        if it.get("nm") == name:
            return G
        got = _find(it["it"][:-1], name, G, t)
        if got is not None:
            return got
    return None


def group_matrix(doc, layer_name, group, t):
    """World matrix of the first group called `group` inside a layer (depth first), at frame t of the file."""
    L = layer(doc, layer_name)
    got = _find(L.get("shapes", []), group, layer_matrix(doc, L, t), t)
    if got is None:
        raise KeyError(f"{layer_name}: no group {group!r}")
    return got


def point(M, p=(0.0, 0.0)):
    q = M @ np.array([p[0], p[1], 1.0])
    return (float(q[0]), float(q[1]))


def turn_of(M):
    """How far a matrix turns the vertical, in degrees clockwise on screen (a mirror left to right does not turn it, so
    a thing drawn mirrored reads as upright when it is)."""
    v = M[:2, :2] @ np.array([0.0, 1.0])
    return math.degrees(math.atan2(-v[0], v[1]))
