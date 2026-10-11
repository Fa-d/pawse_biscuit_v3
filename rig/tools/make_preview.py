#!/usr/bin/env python3
"""Assemble the before / after review page (one self-contained HTML file).

Usage: make_preview.py --raw raw --new dist/biscuit --fx dist/effects --smoke out/smoke/bun_carry_cloud.json --out out/preview/biscuit_reel.html
       [--local-lottie render/node_modules/lottie-web/build/player/lottie.min.js]   (only for offline testing)
"""
import argparse, json, os

CLIPS = [
    ("idle", "Stands and shifts its weight from foot to foot. The free foot taps, the tail tip flicks and Biscuit glances at it."),
    ("wave", "Knees keep the rhythm and the right foot taps along. The tail thumps a beat behind the paw."),
    ("happy", "Knees load, a jump with the feet tucked, a squashy landing, then paws to the cheeks and happy feet."),
    ("cheer", "A star jump with the legs flung wide, then bouncing knees and a kick to each side."),
    ("concerned", "Knees together, toes turned in. One foot rubs the other ankle, paws fidget, a sweat drop slides down."),
    ("thinking", "Leans on one leg with a paw to the chin while the other foot taps slowly."),
    ("sleepy", "Sits down to rest, hugging its tail. Nods off, jerks awake, and its feet kick with the jerk."),
    ("hop_in", "Pops in, two hops on its own legs, a wave and a shuffle into place. Ends exactly on idle's first frame."),
    ("pop_up", "Ear tips first, paws hook over the card, eyes peek left and right, then the pop. The legs stay behind the card."),
    ("breathe", "Sits with its paws on its tummy. Chest and shoulders rise with the ring, toes spread on the in-breath."),
    ("deep_sleep", "Slumped and slow, tail in its lap. The feet paddle in a dream."),
    ("peek_phone", "Eyes climb the bars as they grow. A pleased bounce onto the toes when the tallest one lands."),
    ("meditate", "Floats cross-legged, palms up on its knees. Three small lights circle in front and behind."),
    ("ring_bell", "Knees bounce with the bell and the left foot stamps on every ring."),
    ("read_chart", "Eyes follow the line as it draws. The good news lifts it onto its toes, paw to chin."),
    ("carry_cloud", "A real walk towards you: each foot comes up and shows its pads, the body waddles, dust puffs at every step."),
    ("gift", "Up on its toes to sniff the box, a shake, a recoil when the lid pops, then a hop and happy feet."),
    ("badge_unlock", "Winds up on bent knees, shoots the paw up, hops, then pops one foot up to show the badge off."),
    ("big_celebration", "Deep crouch, a backflip with the knees tucked in, a wide landing, confetti."),
]
ALTS = [
    ("idle_alt_butterfly", "idle", "A butterfly lands on the nose. Biscuit freezes in mid-step, one foot in the air and wobbling, then waves it goodbye."),
    ("idle_alt_sneeze", "idle", "Ah… ah… choo. The sneeze knocks Biscuit onto its bottom. A dazed blink, a nose rub, and it hops back up."),
    ("idle_alt_peekaboo", "idle", "Hides behind both paws with its knees together, peeks with one eye, then a star jump."),
    ("sleepy_alt_bubble", "sleepy", "A sleep bubble swells, pops, and startles Biscuit awake for a second. Its feet jump too."),
]
FX = [
    ("flame", "The tip licks sideways, the core follows a moment later, sparks drift up."),
    ("check_burst", "Rays ripple round the circle, the tick pops on completion, a ring pulses out."),
    ("sparkle", "Sharper twinkle, with two small glints winking in and out."),
    ("star_burst", "Stars shoot out fast and ease to a stop, with a ring behind them."),
    ("pawse_logo", "Unchanged. It is your brand mark, so only the file was minified."),
]
ONCE = {"hop_in", "pop_up", "gift", "badge_unlock"}


def load(p):
    with open(p) as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="raw")
    ap.add_argument("--new", default="dist/biscuit")
    ap.add_argument("--fx", default="dist/effects")
    ap.add_argument("--smoke", default="out/smoke/bun_carry_cloud.json")
    ap.add_argument("--template", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview_template.html"))
    ap.add_argument("--out", default="out/preview/biscuit_reel.html")
    ap.add_argument("--local-lottie", default=None)
    a = ap.parse_args()

    anims, items = {}, []

    def add(key, path):
        d = load(path)
        anims[key] = d
        return dict(key=key, op=d["op"], fr=d["fr"], w=d["w"], h=d["h"], kb=round(os.path.getsize(path) / 1024.0, 1), layers=len(d["layers"]))

    for name, note in CLIPS:
        b = add(f"b:{name}", os.path.join(a.raw, f"biscuit_{name}.json"))
        n = add(f"a:{name}", os.path.join(a.new, f"biscuit_{name}.json"))
        items.append(dict(group="clips", name=name, file=f"biscuit_{name}.json", note=note, before=b, after=n, once=name in ONCE))
    for name, base, note in ALTS:
        n = add(f"a:{name}", os.path.join(a.new, f"biscuit_{name}.json"))
        items.append(dict(group="alts", name=name, file=f"biscuit_{name}.json", note=note, after=n, base=base, once=False))
    for name, note in FX:
        b = add(f"b:{name}", os.path.join(a.raw, f"{name}.json"))
        n = add(f"a:{name}", os.path.join(a.fx, f"{name}.json"))
        items.append(dict(group="fx", name=name, file=f"{name}.json", note=note, before=b, after=n, once=name in ("check_burst", "star_burst", "pawse_logo")))
    if a.smoke and os.path.exists(a.smoke):
        n = add("a:rigtest", a.smoke)
        items.append(dict(group="rig", name="rigtest", file="(not shipped)", note="", after=n, once=False))

    data = json.dumps(dict(items=items, anims=anims), separators=(",", ":")).replace("</", "<\\/")
    with open(a.template) as f:
        html = f.read()
    if a.local_lottie:
        with open(a.local_lottie) as f:
            lib = f.read().replace("</script>", "<\\/script>")
        html = html.replace('<script src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"></script>', "<script>" + lib + "</script>")
    html = html.replace("/*__DATA__*/null", data)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as f:
        f.write(html)
    print("wrote", a.out, f"{os.path.getsize(a.out) / 1024 / 1024:.2f} MB,", len(items), "items")


if __name__ == "__main__":
    main()
