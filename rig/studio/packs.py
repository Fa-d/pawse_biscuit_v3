"""Sticker packs for messengers, as zip files.

Telegram  numbered .tgs files + a guide for Telegram's @Stickers bot, with a suggested emoji for each sticker.
          Telegram limits checked: 512 x 512, 60 fps, up to 3 s, up to 64 KB each.
WhatsApp  the pack format of WhatsApp's own sticker sample apps (github.com/WhatsApp/stickers): contents.json, a
          96 x 96 tray icon and 512 x 512 WebP stickers.  WhatsApp's rules checked: 3 to 30 stickers, all animated or
          all static, up to 500 KB (animated) or 100 KB (static) each, frames of at least 8 ms, up to 10 s, up to 3
          emoji per sticker, tray icon up to 50 KB.
Every sticker is checked before anything is zipped; problems come back as one list of plain sentences.
"""
from __future__ import annotations

import io
import json
import re
import tempfile
import zipfile

from PIL import Image

from .export import TGS_MAX, WA_ANIM_MAX, WA_STILL_MAX, die_cut, frame, save, tgs_bytes, webp_durations

TG_MAX_SECONDS = 3.0
WA_MIN, WA_MAX = 3, 30
TRAY_MAX = 50 * 1024

# motions too plain to say much on their own: the face tells more
PLAIN_MOTIONS = ("idle", "bounce", "sway", "walk")


class PackError(ValueError):
    """The pack can't be made; .problems lists every reason."""

    def __init__(self, problems):
        super().__init__("; ".join(problems))
        self.problems = problems


def emojis_for(spec, n=3):
    """Up to n emoji that describe the sticker, without repeats, most telling first: what it does, its face, what it holds,
    what is around it (Telegram suggests the sticker when someone types the first one)."""
    from .registry import ensure_loaded
    reg = ensure_loaded()
    cands = []
    m = reg.motions.get(spec.motion)
    if m and spec.motion not in PLAIN_MOTIONS:
        cands.append(m.emoji)
    f = reg.faces.get(spec.face)
    cands.append(f.emoji if f else "")
    cands += [reg.props[x].emoji for x in spec.props if x in reg.props]
    cands += [reg.effects[x].emoji for x in spec.effects if x in reg.effects]
    cands += [reg.wear[x].emoji for x in spec.accessories if x in reg.wear]
    if m and spec.motion in PLAIN_MOTIONS:
        cands.append(m.emoji)
    out = []
    for e in cands:
        if e and e not in out:
            out.append(e)
    return out[:n] or ["🙂"]


def describe(spec):
    """Short accessibility text: 'A joyful cat waving, holding a mug of something hot, with the words "Hi!"'."""
    from .registry import ensure_loaded
    reg = ensure_loaded()
    base = reg.bases.get(spec.base)
    animal = base.animal if base else "mascot"
    m = reg.motions.get(spec.motion)
    doing = m.doing if m else ""
    f = reg.faces.get(spec.face)
    mood = (f.mood if f and f.mood else (f.label.lower() if f else spec.face)) or "happy"
    bits = [f"{'An' if mood[0] in 'aeiou' else 'A'} {mood} {animal} {doing}".strip()]
    if spec.props:
        bits.append("holding " + " and ".join(reg.props[x].noun or ("a " + x.replace("_", " ")) for x in spec.props if x in reg.props))
    if spec.accessories:
        bits.append("wearing " + " and ".join(reg.wear[x].noun or ("a " + x.replace("_", " ")) for x in spec.accessories if x in reg.wear))
    if spec.caption and spec.caption.text.strip():
        bits.append(f'with the words "{spec.caption.text.strip()}"')
    return ", ".join(b for b in bits if b)[:250]


def _slug(text, n=24):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:n].strip("-") or "sticker"


# ---------------------------------------------------------------- Telegram
TELEGRAM_GUIDE = """How to add these stickers to Telegram
=====================================

You need the Telegram app (phone or desktop) and these {n} .tgs files.

1. Open a chat with @Stickers (Telegram's own sticker bot).
2. Send /newpack and choose an animated sticker set when it asks for the type.
3. Give the pack a name, for example "{title}".
4. Send the first .tgs file as a file (not as a photo), then send its emoji (listed below).
5. Repeat step 4 for each file, in order.
6. Send /publish. Send an icon or /skip, then choose a short name for the pack's link.
7. Open the link the bot gives you and tap Add Stickers.

The bot's wording can change; if a step looks different, follow what it asks.

Stickers and their emoji
------------------------
{rows}
"""


def telegram_zip(items, title="My stickers"):
    """items: [(spec, lottie doc)].  Returns zip bytes.  Raises PackError listing every problem."""
    problems, files = [], []
    if not items:
        raise PackError(["Save at least one sticker first."])
    for k, (spec, doc) in enumerate(items, 1):
        data = tgs_bytes(doc)
        secs = (doc["op"] - doc["ip"]) / doc["fr"]
        if (doc["w"], doc["h"]) != (512, 512):
            problems.append(f"Sticker {k} is {doc['w']}×{doc['h']}; Telegram needs 512×512.")
        if doc["fr"] not in (30, 60):
            problems.append(f"Sticker {k} runs at {doc['fr']} fps; Telegram needs 30 or 60.")
        if secs > TG_MAX_SECONDS:
            problems.append(f"Sticker {k} lasts {secs:.1f} s; Telegram allows up to 3 s.")
        if len(data) > TGS_MAX:
            problems.append(f"Sticker {k} is {len(data) / 1024:.0f} KB; Telegram allows up to 64 KB. Remove an effect or shorten it.")
        files.append((f"{k:02d}-{_slug(describe(spec))}.tgs", data, emojis_for(spec, 1)[0]))
    if problems:
        raise PackError(problems)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data, _ in files:
            z.writestr(name, data)
        rows = "\n".join(f"{name}   {emoji}" for name, _, emoji in files)
        z.writestr("HOW-TO-ADD-TO-TELEGRAM.txt", TELEGRAM_GUIDE.format(n=len(files), title=title, rows=rows))
    return buf.getvalue()


# ---------------------------------------------------------------- WhatsApp
def tray_icon(doc, still=0):
    """96 x 96 PNG of the first sticker for the pack's tab, under 50 KB."""
    img = die_cut(frame(doc, still, size=512), r=10).resize((96, 96), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, "PNG", optimize=True)
    return out.getvalue()


def whatsapp_zip(items, title="My stickers", publisher="Pawse Studio", animated=True, identifier="pawse_pack", website=""):
    """items: [(spec, lottie doc, still frame)].  Returns zip bytes in WhatsApp's sample-app pack format.
    animated: one pack is all animated or all static (WhatsApp's rule).  Raises PackError listing every problem."""
    problems = []
    if not WA_MIN <= len(items) <= WA_MAX:
        problems.append(f"A WhatsApp pack needs {WA_MIN} to {WA_MAX} stickers; this one has {len(items)}.")
    if problems:
        raise PackError(problems)
    fmt = "awebp" if animated else "webp"
    limit = WA_ANIM_MAX if animated else WA_STILL_MAX
    stickers, blobs = [], []
    with tempfile.TemporaryDirectory() as d:
        for k, (spec, doc, still) in enumerate(items, 1):
            res = save(doc, d, f"s{k}", formats=(fmt,), still=0 if animated else still)   # animated: frame 0 must show it whole
            path, size, _ = res[fmt]
            if size > limit:
                problems.append(f"Sticker {k} is {size / 1024:.0f} KB; WhatsApp allows up to {limit // 1024} KB. Remove an effect.")
            if animated:
                with open(path, "rb") as f:
                    durs = webp_durations(f.read())
                if not durs:
                    problems.append(f"Sticker {k} came out without animation frames.")
                elif min(durs) < 8:
                    problems.append(f"Sticker {k} has frames shorter than 8 ms.")
                if sum(durs) > 10000:
                    problems.append(f"Sticker {k} lasts {sum(durs) / 1000:.1f} s; WhatsApp allows up to 10 s.")
            name = f"{k:02d}_{_slug(describe(spec))}.webp"
            with open(path, "rb") as f:
                blobs.append((name, f.read()))
            stickers.append({"image_file": name, "emojis": emojis_for(spec, 3), "accessibility_text": describe(spec)[:255 if animated else 125]})
        tray = tray_icon(items[0][1], items[0][2])
        if len(tray) > TRAY_MAX:
            problems.append("The tray icon came out over 50 KB.")
    if problems:
        raise PackError(problems)
    contents = {
        "android_play_store_link": "",
        "ios_app_store_link": "",
        "sticker_packs": [{
            "identifier": re.sub(r"[^A-Za-z0-9_.\- ]", "_", identifier)[:120],
            "name": title[:128],
            "publisher": publisher[:128],
            "tray_image_file": "tray.png",
            "image_data_version": "1",
            "avoid_cache": False,
            "publisher_email": "",
            "publisher_website": website,
            "privacy_policy_website": f"{website}/privacy" if website else "",
            "license_agreement_website": "",
            "animated_sticker_pack": bool(animated),
            "stickers": stickers,
        }],
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("contents.json", json.dumps(contents, ensure_ascii=False, indent=2))
        z.writestr("tray.png", tray)
        for name, data in blobs:
            z.writestr(name, data)
        z.writestr("HOW-TO-ADD-TO-WHATSAPP.txt", WHATSAPP_GUIDE.format(n=len(blobs)))
    return buf.getvalue()


WHATSAPP_GUIDE = """How to add these stickers to WhatsApp
=====================================

WhatsApp adds sticker packs through a sticker app on your phone, not from a website.

Quickest: install a sticker-maker app that imports WebP stickers, make a new pack in it, and add these {n}
.webp files in order. The app then offers "Add to WhatsApp".

For developers: this zip follows the pack format of WhatsApp's own sample sticker apps
(https://github.com/WhatsApp/stickers). Put contents.json, tray.png and the .webp files in the sample app's
assets folder to build an app that adds the pack directly.
"""
