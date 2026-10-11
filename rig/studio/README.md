# Sticker studio

Type a sentence and get a sticker of the mascot as PNG, WebP, a Telegram `.tgs` file, a WhatsApp animated WebP, a GIF
or Lottie JSON. The rig draws everything. No AI is needed for prompts the word lists understand. Claude Haiku is an
optional fallback for the rest, and it can only answer with names the rig knows.

```
prompt ─► parse/ (rules: lexicon.yaml + templates.yaml) ─► StickerSpec ─► compose.py (rules) ─► mascot rig ─► export.py
             └─ fallback.py: typo fix, then optional Haiku, cached; misses are logged to grow the lexicon
```

## Try it

```
cd rig
python3 -m venv .venv && .venv/bin/pip install -r studio/requirements.txt
.venv/bin/python -m studio.cli "a sleepy purple fox with coffee saying 'monday again'" --out out/
.venv/bin/python -m studio.cli "happy birthday" --set face=surprised --formats png,tgs,awebp,gif
.venv/bin/python -m studio.cli "omg no way" --dry          # only show what was understood
```

`--set slot=value` changes one slot after parsing, as an editor chip would (`base`, `face`, `motion`, `stance`, `tail`, `arm_L`,
`arm_R`, `props`, `effects`, `accessories`, `caption`, `caption_style`, `caption_pos`, `intensity`, `seconds`, `look`).
`--llm` turns on the Haiku fallback; it needs Anthropic credentials.

## Files

| File | What it does |
|---|---|
| `spec.py` | `StickerSpec`, the one structure the parser, editor and composer share, plus the allowed names (`VOCAB`) |
| `parse/lexicon.yaml` | Words for moods, actions, props, effects, poses, colours, intensity, stopwords and negators |
| `parse/templates.yaml` | 33 scenario recipes (monday, birthday, thank you…), each with an optional suggested caption |
| `parse/parser.py` | Matches the longest phrase first, picks one template, then the highest weight wins per slot. Handles negation (stops at punctuation), intensity, colours and quoted or "saying …" captions |
| `parse/fallback.py` | Typo fix (difflib), then Haiku with a JSON schema made of enums; answers cached in `cache/llm.json`, misses in `cache/misses.jsonl` |
| `compose.py` | Rules: props claim paws, motions get the paws that are left, sitting swaps out leg motions, the tail follows the stance, a caption shrinks the scene to fit |
| `motions.py` | 14 loopable motions built from `mascot/clips/moves.py`; every period divides the loop length |
| `accessories.py` | Things worn: party hat, crown, glasses, sunglasses, bow, flower, headphones, scarf, star clip. Head items hang from the `neck` null and are placed from each mascot's crown, eyes and ears, so they fit every mascot |
| `extras.py` | New props and effects in the `props.py` style: mug, held heart, floating hearts, music notes, rain cloud |
| `caption.py` | Captions as vector paths (fontTools), so every player shows them; outline or bubble style, top or bottom |
| `packs.py` | Sticker packs as zips: Telegram (.tgs files, a suggested emoji each, steps for the @Stickers bot) and WhatsApp (the pack format of WhatsApp's sample apps: `contents.json`, 96×96 tray icon, WebP stickers). Checks every messenger rule first and says what's wrong in plain words |
| `export.py` | rlottie rasteriser; raster files get the white die-cut edge messengers expect; checks Telegram's ≤64 KB / ≤3 s and WhatsApp's ≤100 KB static / ≤500 KB animated limits |

## Mascots and expressions

Three bases: `biscuit` (fox), `mochi` (cat) and `bruno` (bear), in `mascot/characters/`. The cat and the bear subclass
Biscuit and only redraw the head, ears, face details, body markings and tail, so all 23 rig clips and every studio
motion work on them unchanged. The prompt picks one by name ("cat", "kitten", "teddy"…). Expressions now also include
`angry` (with the `anger` effect) and `wink`.

## Adding to it

- **A new word for an existing thing:** add it to `lexicon.yaml`. Check `cache/misses.jsonl` for words people actually use.
- **A new scenario:** add a block to `templates.yaml`.
- **A new prop or effect:** write it in `extras.py`, register it in `PROPS` / `EFFECTS` in `compose.py` and in `spec.py`.
- **A new mascot:** subclass a close one (as `mochi.py` and `bruno.py` do), or follow `rig/RIG.md` → "Adding a mascot".
  Register it in `characters()` in `mascot/build.py`, add it to `BASES` in `spec.py` and its words under `bases:` in the lexicon.
- **A new accessory:** add a function to `accessories.py` that places itself from the mascot's data, then list it in
  `ACCESSORIES` there and in `spec.py`.

## Checks

```
.venv/bin/python -m unittest studio.tests.test_studio -v     # loop seams, Telegram limits, paw rules, captions
.venv/bin/python -m studio.tests.eval_parser --min 0.9       # golden prompts understood without the LLM
```

Captions use Fredoka SemiBold (`studio/assets/font.ttf`, SIL Open Font License, licence next to it). Set `STUDIO_FONT`
to use another .ttf.
