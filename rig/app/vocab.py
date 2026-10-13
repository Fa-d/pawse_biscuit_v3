"""What the editor's chips say.  Internal names stay in the spec; people see these words.

The labels come from the studio's registry and lexicon, so every motion, prop, effect, worn thing, face and mascot the
studio gains shows up in the editor by itself.
"""
from __future__ import annotations

from studio.parse.parser import Parser
from studio.registry import ensure_loaded

# the editor's idea buttons (app.js picks these by prompt); they lead the list of ideas
PICKS = ("good morning", "happy birthday", "thank you", "on my way", "busy", "weekend", "love you", "bad day")


def _hex(value):
    v = value["hex"] if isinstance(value, dict) else value
    return str(v).lower()


def vocab():
    reg = ensure_loaded()
    p = Parser()
    pick = lambda table: [{"id": k, "label": v.label} for k, v in table.items()]       # noqa: E731
    colours = [{"id": "", "label": "Original", "hex": None}]
    for name, entry in p.lex["colours"].items():
        if isinstance(entry, dict) and entry.get("swatch"):
            hx = _hex(entry)
            colours.append({"id": name, "label": name.replace("_", " ").capitalize(), "hex": hx, "palette": {"orange": hx}})
    ideas = [{"prompt": t["words"][0], "caption": t.get("caption")} for t in p.tpl.values()]
    ideas.sort(key=lambda i: PICKS.index(i["prompt"]) if i["prompt"] in PICKS else len(PICKS))
    # which way it faces (v5): one chip per view the lexicon names, numbers in degrees as the spec keeps them
    yaw = [{"id": float(e["yaw"]), "label": e.get("label") or name.replace("_", " ").capitalize()} for name, e in p.lex["view"].items()]
    yaw.sort(key=lambda c: (abs(c["id"]), c["id"] < 0))
    return dict(base=pick(reg.bases), face=pick(reg.faces), motion=pick(reg.motions),
                stance=[{"id": k, "label": v} for k, v in reg.stances.items()], yaw=yaw,
                props=pick(reg.props), effects=pick(reg.effects), accessories=pick(reg.wear), colours=colours, ideas=ideas,
                caption_style=[{"id": "outline", "label": "Outline"}, {"id": "bubble", "label": "Bubble"}],
                caption_pos=[{"id": "bottom", "label": "Bottom"}, {"id": "top", "label": "Top"}])
