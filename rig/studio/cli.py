#!/usr/bin/env python3
"""Make a sticker from a sentence.

    python3 -m studio.cli "sleepy fox with coffee saying 'monday'" --out out/
    python3 -m studio.cli "happy birthday" --set face=surprised --set effects=confetti,sparkles --formats png,tgs,awebp
    python3 -m studio.cli --spec spec.json --out out/          # skip the parser: render a saved spec (or a scene of two)
    python3 -m studio.cli "fox waving" --friend pip             # a second mascot next to it (until the parser reads two)
    python3 -m studio.cli "..." --dry                           # only show what was understood
    python3 -m studio.cli --list motions                        # what the library has: motions, props, effects, wear,
                                                                #   faces, bases, stances, tails, arms, templates, colours
    python3 -m studio.cli --rules                               # every rule: reading a prompt, composing, the library
    python3 -m studio.cli --check                               # lexicon and library consistency (exit 1 on a problem)

--set changes one slot after parsing, the same way an editor chip would.  --llm lets the fallback ask Claude Haiku
when the rules do not understand the prompt (needs Anthropic credentials; answers are cached).
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from .compose import compose
from .export import save
from .parse.fallback import parse
from .scene_compose import compose_scene
from .scene_spec import ActorSpec, SceneSpec
from .spec import Caption, StickerSpec


def _mascot(word):
    """A mascot name ('pip') or a word for it ('dog', 'puppy') -> the mascot's name."""
    from .registry import ensure_loaded
    reg = ensure_loaded()
    if word in reg.bases:
        return word
    r = parse(word)
    hits = [m for m in r.matches if m.section == "bases"]
    if not hits:
        raise SystemExit(f"--friend: {word!r} is not a mascot; try one of {', '.join(b.animal for b in reg.bases.values())}")
    return r.spec.base


def apply_set(spec: StickerSpec, items):
    for item in items:
        k, _, v = item.partition("=")
        k = k.strip().replace(".", "_")
        if k in ("props", "effects", "accessories"):
            setattr(spec, k, [x for x in v.split(",") if x])
        elif k == "caption":
            spec.caption = Caption(v) if v else None
        elif k == "caption_style":
            spec.caption = Caption(spec.caption.text if spec.caption else "", style=v)
        elif k == "caption_pos":
            spec.caption = Caption(spec.caption.text if spec.caption else "", style=spec.caption.style if spec.caption else "outline", pos=v)
        elif k in ("intensity", "seconds", "tempo", "yaw"):
            try:
                setattr(spec, k, float(v))
            except ValueError:
                raise SystemExit(f"--set {k}: {v!r} is not a number")
        elif k == "look":
            spec.look = tuple(float(x) for x in v.split(","))
        elif k in StickerSpec.__dataclass_fields__:
            setattr(spec, k, v or None)
        else:
            raise SystemExit(f"--set: unknown slot {k!r}")
    try:
        return spec.validate()
    except ValueError as e:
        raise SystemExit(f"--set: {e}")


def list_items(kind):
    """Lines describing everything of a kind in the library."""
    from .parse.parser import Parser
    from .registry import ensure_loaded
    reg = ensure_loaded()
    out = []
    if kind == "motions":
        for n, m in reg.motions.items():
            extra = []
            if m.uses:
                extra.append("uses " + ",".join(m.uses))
            if m.brings:
                extra.append("brings " + m.brings)
            sit = {"no": "standing only", "ok": "", "only": "sitting only"}.get(m.sit, m.sit)
            out.append(f"{n:<14} {m.emoji:<3} {m.label:<22} paws {m.paws}{' ' + sit if sit else ''}{'  ' + '; '.join(extra) if extra else ''}")
    elif kind == "props":
        for n, x in reg.props.items():
            out.append(f"{n:<14} {x.emoji:<3} {x.label:<20} {x.category:<10} paw {x.paw:<2} pose {x.pose}")
    elif kind == "effects":
        for n, x in reg.effects.items():
            out.append(f"{n:<16} {x.emoji:<3} {x.label:<20} {x.zone}")
    elif kind in ("wear", "accessories"):
        for n, x in reg.wear.items():
            cov = f"  covers {','.join(x.covers)}" if x.covers else ""
            out.append(f"{n:<14} {x.emoji:<3} {x.label:<20} {x.zone}{cov}")
    elif kind == "faces":
        for n, x in reg.faces.items():
            out.append(f"{n:<11} {x.emoji:<3} {x.label}")
    elif kind in ("bases", "mascots"):
        for n, x in reg.bases.items():
            out.append(f"{n:<9} {x.emoji:<3} {x.label:<9} favourite snack: {x.snack}")
    elif kind in ("stances", "tails", "arms"):
        table = {"stances": reg.stances, "tails": reg.tails, "arms": reg.arm_poses}[kind]
        out += [f"{n:<12} {lab}" for n, lab in table.items()]
    elif kind == "templates":
        p = Parser()
        for n, t in p.tpl.items():
            out.append(f"{n:<22} '{t['words'][0]}'  ->  {t.get('caption', '')}")
    elif kind == "colours":
        p = Parser()
        for n, e in p.lex["colours"].items():
            hx = e["hex"] if isinstance(e, dict) else e
            out.append(f"{n:<14} {hx}")
    else:
        raise SystemExit(f"--list: unknown kind {kind!r}")
    return out


def all_rules():
    from .parse.parser import PARSER_RULES
    from .qa import GUARANTEES
    from .rules import describe
    from .scene_compose import describe as describe_scene
    return [("Reading a prompt", PARSER_RULES), ("Composing a sticker", describe()), ("Composing a scene of two mascots", describe_scene()),
            ("What the library guarantees", GUARANTEES)]


def check():
    """Problems in the lexicon, the scenarios and the library's own cross references."""
    from .parse.parser import Parser
    from .registry import ensure_loaded
    reg = ensure_loaded()
    bad = list(Parser().problems())
    cats = {x.category for x in reg.props.values()}
    for n, m in reg.motions.items():
        for alt in (m.paw_alt, m.sit_alt):
            if alt and alt not in reg.motions:
                bad.append(f"motion {n}: unknown alternative {alt!r}")
        if m.brings and m.brings != "snack" and m.brings not in reg.props:
            bad.append(f"motion {n}: brings unknown prop {m.brings!r}")
        for u in m.uses:
            if u not in reg.props and u not in cats:
                bad.append(f"motion {n}: uses unknown prop or category {u!r}")
        if m.brings and not m.uses:
            bad.append(f"motion {n}: brings a prop but uses none")
    for n, b in reg.bases.items():
        if b.snack not in reg.props:
            bad.append(f"mascot {n}: unknown snack {b.snack!r}")
    for kind, table in (("motion", reg.motions), ("prop", reg.props), ("effect", reg.effects), ("worn item", reg.wear)):
        for n, x in table.items():
            if not x.emoji or not x.label:
                bad.append(f"{kind} {n}: needs a label and an emoji")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", nargs="?", default="")
    ap.add_argument("--spec", help="render this spec (JSON file) instead of parsing a prompt")
    ap.add_argument("--set", action="append", default=[], metavar="SLOT=VALUE")
    ap.add_argument("--out", default="out")
    ap.add_argument("--name", default=None)
    ap.add_argument("--formats", default="png,webp,tgs,json", help="png, webp, tgs, awebp (WhatsApp), gif, json")
    ap.add_argument("--llm", action="store_true", help="allow the LLM fallback for prompts the rules do not understand")
    ap.add_argument("--no-auto-caption", action="store_true")
    ap.add_argument("--watermark", action="store_true", help="free-tier watermark on raster exports")
    ap.add_argument("--dry", action="store_true", help="print the spec and stop")
    ap.add_argument("--friend", metavar="MASCOT", help="add a second mascot (fox, cat ... or a name such as pip), standing still")
    ap.add_argument("--list", metavar="KIND", help="list the library: motions, props, effects, wear, faces, bases, stances, tails, "
                                                   "arms, templates, colours")
    ap.add_argument("--rules", action="store_true", help="list every rule")
    ap.add_argument("--check", action="store_true", help="check the lexicon and the library")
    a = ap.parse_args(argv)

    if a.list:
        lines = list_items(a.list)
        print("\n".join(lines))
        print(f"({len(lines)} {a.list})")
        return 0
    if a.rules:
        for title, rules in all_rules():
            print(f"\n{title}")
            for code, text in rules:
                print(f"  {code}  {text}")
        return 0
    if a.check:
        bad = check()
        for b in bad:
            print("PROBLEM", b)
        print("all good" if not bad else f"{len(bad)} problems")
        return 1 if bad else 0

    scene = None
    if a.spec:
        with open(a.spec) as f:
            data = json.load(f)
        if isinstance(data, dict) and "actors" in data:
            scene = SceneSpec.from_dict(data)
            spec = scene.actors[0].sticker(scene.caption, scene.seconds, scene.tempo)
        else:
            spec = StickerSpec.from_dict(data)
        print("spec from", a.spec)
    elif a.prompt:
        r = parse(a.prompt, llm=a.llm, auto_caption=not a.no_auto_caption)
        print(r.explain())
        spec = r.spec
        if not r.confident:
            print("  (not sure what this means; showing a friendly default. Try other words, or --llm)", file=sys.stderr)
    else:
        ap.error("give a prompt or --spec")
    apply_set(spec, a.set)
    if scene is not None:
        scene.actors[0] = ActorSpec.of(spec)
        scene.caption, scene.seconds, scene.tempo = spec.caption, spec.seconds, spec.tempo
    if a.friend:
        base = _mascot(a.friend)
        scene = scene or SceneSpec.from_sticker(spec)
        if len(scene.actors) > 1:
            raise SystemExit("--friend: the scene has two mascots already")
        scene.actors.append(ActorSpec(base=base))
    if scene is not None and not scene.solo:
        print("scene:", scene.to_json())
    else:
        print("spec:", spec.to_json())
    if a.dry:
        return 0

    t = time.time()
    if scene is not None and not scene.solo:
        doc, info = compose_scene(scene)
        name = a.name or scene.key()
    else:
        doc, info = compose(spec)
        name = a.name or spec.key()
    for n in info["notes"]:
        print("  note:", n)
    res = save(doc, a.out, name, formats=tuple(f.strip() for f in a.formats.split(",")), still=info["still"], mark=a.watermark)
    for fmt, (path, size, warn) in res.items():
        print(f"  {fmt:<6} {size / 1024:7.1f} KB  {path}{'   ! ' + warn if warn else ''}")
    print(f"done in {time.time() - t:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
