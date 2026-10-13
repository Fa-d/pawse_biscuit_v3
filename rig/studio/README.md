# Sticker studio

Type a sentence and get a sticker of a mascot as PNG, WebP, a Telegram `.tgs` file, a WhatsApp animated WebP, a GIF
or Lottie JSON. The rig draws everything. No AI is needed for prompts the word lists understand (all 941 test
prompts). Claude Haiku is an optional fallback for the rest, and it can only answer with names the rig knows.

What changed in v4, with the bugs it fixed: [CHANGES.md](CHANGES.md). Every decision, step by step: [PIPELINE.md](PIPELINE.md).

```
prompt ─► parse/ (text.py → lexicon/ + templates/ → parser.py) ─► StickerSpec ─► rules.py ─► Plan ─► compose.py
                                                                                                       │
            library/ (motions, props, effects, things worn, faces, mascots) ─► registry.py ───────────┘
                                                                                                       ▼
                                                                        mascot rig ─► framing.py ─► export.py
```

## Try it

```
cd rig
python3 -m venv .venv && .venv/bin/pip install -r studio/requirements.txt
.venv/bin/python -m studio.cli "a sleepy purple cat with coffee and a scarf saying 'monday again'" --out out/
.venv/bin/python -m studio.cli "panda eating bamboo" --formats png,tgs,awebp,gif
.venv/bin/python -m studio.cli "omg no way" --dry          # only show what was understood
.venv/bin/python -m studio.cli --list motions              # what the library has (props, effects, wear, faces, bases ...)
.venv/bin/python -m studio.cli --rules                     # every rule, numbered
.venv/bin/python -m studio.cli --check                     # lexicon and library consistency
```

`--set slot=value` changes one slot after parsing, as an editor chip would (`base`, `face`, `motion`, `stance`, `tail`,
`arm_L`, `arm_R`, `props`, `effects`, `accessories`, `caption`, `caption_style`, `caption_pos`, `intensity`, `seconds`,
`look`, `tempo`). `--llm` turns on the Haiku fallback; it needs Anthropic credentials.

## What's in the library

| Kind | Count | Examples |
|---|---|---|
| Mascots | 14 | fox, cat, bear, dog, bunny, panda, tiger, koala, raccoon, pig, frog, penguin, mouse, lion (plus fur colours: "polar bear", "golden retriever", "black cat" …) |
| Motions | 99 | wave, dance, clap, facepalm, shrug, salute, laugh, sob, roar, boxing, faint, run, dab, eat, sip, type, read, phone call, selfie, sing, toast, paint, game, lift weights, strum a guitar, juggle, magic, brush teeth, knock … |
| Held props | 76 | mug, boba, pizza, burger, ice cream, cake, laptop, phone, book, microphone, guitar, camera, balloon, flag, rose, sign, gift, trophy, diya, lantern, red envelope, pumpkin, wand … |
| Effects | 43 | confetti, hearts, rain, snow, sparkles, fireworks, money rain, zzz, idea bulb, lightning, rainbow, butterflies, spotlight, speed lines, waterfall tears … |
| Things worn | 56 | party hat, crown, santa hat, witch hat, grad cap, sunglasses, heart glasses, headphones, scarf, bow tie, hero cape, angel wings, halo, devil horns, tutu, lei … |
| Faces | 41 | smiley, joy, laugh, cry, pleading, love, starry, dizzy, smug, unamused, pout, nervous, kiss, silly, sick, furious, excited … |
| Scenarios | 220 | good morning, monday, birthday, thank you, sorry, get well, exam, payday, Eid, Diwali, Lunar New Year, Christmas, Holi, Pohela Boishakh … |

Every item is checked on every mascot (`python -m studio.qa`): it builds, its loop has no seam, nothing touches the
canvas edge after framing, and the `.tgs` file fits Telegram's 64 KB.

## Files

| File | What it does |
|---|---|
| `spec.py` | `StickerSpec`, the one structure the parser, editor and composer share; its allowed names come from the registry |
| `registry.py` | Every motion, prop, effect, worn item, face and mascot, registered once with the facts other parts need (paws, place on the body, colour choices, best still frame, size cost) |
| `library/` | The drawings and the acting, registered with `@motion`, `@prop`, `@effect`, `@wear`, `face(...)`, `base(...)` |
| `rules.py` | Composer rules R01–R24: paws, motion swaps, worn-item clashes, effect zones, size budget, tail, tempo, colours, views a mascot has not got |
| `compose.py` | Spec → plan (rules) → clip → the rig bakes Lottie; picks the still frame |
| `framing.py` | Measures where the sticker draws and scales it to fill the canvas without touching the edge |
| `parse/text.py` | From what people type to clean tokens: emoji, emoticons, laughter, stretched words, chat shorthand, translations |
| `parse/lexicon/*.yaml` | What words mean: moods, actions, things, mascots, poses, colours, small words, translations (`../lexicon.yaml` is for your own words) |
| `parse/templates/*.yaml` | Scenario recipes: everyday life and occasions (`../templates.yaml` is for your own) |
| `parse/parser.py` | Rules P01–P33: longest phrase first, negation, weights, colours to items, sides, captions, confidence |
| `parse/morph.py`, `typo.py` | Word forms ("clapping" → clap) and safe typo fixes (real words are never "fixed") |
| `parse/fallback.py` | Haiku with a JSON schema of the rig's own names; cached; misses logged to `cache/misses.jsonl` |
| `caption.py` | Captions as vector paths (fontTools), so every player shows them; outline or bubble, top or bottom |
| `packs.py` | Telegram and WhatsApp pack zips; emoji and accessibility text are written from the registry |
| `export.py` | rlottie rasteriser, white die-cut edge, messenger size limits |
| `qa.py` | Library checks on every mascot and contact sheets |
| `motions.py`, `accessories.py`, `extras.py` | v3 names, kept as views of the registry |
| `scene_spec.py`, `scene_compose.py` | v5: stickers of two mascots (SceneSpec, scene rules S01-S09, composing); see `../V5.md` |
| `qa_scene.py`, `snapshots.py` | v5: every pair of mascots as a scene (L12); one-mascot output byte-identical to v4 (L17) |
| `library/motions_turn.py` | v5: turning motions (turn around, look back, full spin); `StickerSpec.yaw` turns any sticker (`../V5.md`) |

## Adding to it

- **A word for something that exists:** add it to `words:` of the entry in `parse/lexicon/` (or your own
  `parse/lexicon.yaml`). `python -m studio.cli --check` says when a phrase already belongs to another entry.
  `cache/misses.jsonl` lists the words people used that nothing understood.
- **A scenario:** a block in `parse/templates/*.yaml`: `words` (the first is the idea shown in the editor), `spec`, `caption`.
- **A motion:** a function in `library/motions_*.py` with `@motion(name, label, emoji, doing=..., paws=..., sit=...)`.
  Build it from `m.c` (the clip), use periods from `m.per(...)` so it loops, and return its best still frame. Say
  what it acts with (`uses=`), what it brings (`brings=`), what it becomes sitting or with too few paws (`sit_alt=`,
  `paw_alt=`), and which effects it draws itself (`draws=`). Then give it words under `actions:` in the lexicon.
- **A prop, effect or worn item:** a factory in `library/props_*.py`, `effects_*.py` or `wear_*.py` with `@prop`,
  `@effect` or `@wear`. Draw from the mascot's own data (crown, eyes, ears, `top`, `collar`), never from fixed
  coordinates, so it fits every mascot. Then add its words to `parse/lexicon/things.yaml`.
- **A mascot:** see `rig/RIG.md` → "Adding a mascot", then `base(...)` in `library/looks.py` and its words in
  `parse/lexicon/mascots.yaml`.

Run the checks below after any change; the web editor's chips (`app/vocab.py`) pick up new items by themselves.

## Checks

```
.venv/bin/python -m studio.cli --check                                       # lexicon and registry agree
.venv/bin/python -m studio.tests.eval_parser --min 0.98                      # 941 golden prompts, no LLM
.venv/bin/python -m unittest studio.tests.test_library studio.tests.test_studio   # loops, limits, rules, captions
.venv/bin/python -m studio.qa --kind motions --only strum                    # one item on every mascot
.venv/bin/python -m studio.qa --sheet out/wear.png --kind wear --bases leo   # look at it
.venv/bin/python -m studio.snapshots --check                                 # v5: one-mascot output unchanged (379 items)
.venv/bin/python -m studio.qa_scene                                          # v5: all 196 pairs of mascots as scenes
.venv/bin/python -m unittest studio.tests.test_v5                            # v5: scenes, SceneSpec, parser notes
.venv/bin/python -m studio.qa --kind views                                   # v5: turned stickers on every mascot (L15)
.venv/bin/python -m unittest studio.tests.test_views                         # v5: the view rig, drawn views, yaw in specs
```

Captions use Fredoka SemiBold (`studio/assets/font.ttf`, SIL Open Font License, licence next to it). Set `STUDIO_FONT`
to use another .ttf. The typo checker's word list (`parse/data/english-words.txt.gz`) is from SCOWL; its copyright
notice is next to it.
