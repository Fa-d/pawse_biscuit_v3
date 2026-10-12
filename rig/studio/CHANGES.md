# Sticker studio v4: what changed

The sticker maker was rebuilt from the skeleton up so that ordinary English descriptions work. The web app's code is
untouched except `app/vocab.py`, and the app's 23 original animations are drawn byte-for-byte as before.

## In numbers

| | v3 | v4 |
|---|---|---|
| Realistic prompts understood (296 typed the way people type, none tuned against) | 137 | 294 |
| Golden test prompts (checked slot by slot, no AI) | — | 941 of 941 |
| Mascots | 3 | 14 |
| Motions | 14 | 99 |
| Props to hold | 8 | 76 |
| Effects | 12 | 43 |
| Things to wear | 9 | 56 |
| Faces | 11 | 41 |
| Scenarios (birthday, Eid, exam, payday …) | 32 | 220 |
| Phrases the rules know | 757 | 10,114 (plus 542 translated phrases) |
| Written, numbered rules | — | 67: P01–P33 reading, R01–R23 composing, L01–L11 library guarantees |

The two prompts still not understood are animals the studio doesn't have (an elephant, a dragon); the editor says so
and suggests words.

## Phase 1: the skeleton (mascot rig)

- **Fallbacks instead of crashes.** A mascot that lacks an arm pose, stance or tail pose plays the nearest one it has,
  so older and newer mascots never break on newer clips.
- **A data contract.** `Character.problems()` lists anything missing or malformed in a mascot's data.
- **52 arm poses** (was 23), **paw shapes** (fist, thumb up, pointing, peace sign), **41 expressions** (was 11), special
  eyes (hearts, stars, spirals, crosses), teary eyes, lids, one brow at a time, teeth, pursed lips, a wail.
  At rest these new channels draw exactly what v3 drew.
- **Mane-aware placement.** `top` and `collar` let hats, halos and scarves clear a lion's mane.
- **The best frame is frame 0.** The loop is turned so the PNG still, Telegram's first frame and WhatsApp's resting
  frame show the key pose with every effect at its fullest. In v3, for example, the z's never showed in the PNG.
- **Faster, closer keyframe fitting.** The general-purpose optimiser that took over 95 % of build time was replaced
  by a direct solve. Curves are as close to the samples as before.
- **Fades don't dim the mascot** in rlottie (Telegram), and raster exports use straight alpha, so there are no dark
  fringes or grey glows.

## Phase 2: one registry, a big library

- `studio/registry.py` holds every motion, prop, effect, worn item, face and mascot once, with the facts other parts
  need. The spec, composer, parser checks, LLM schema, pack emoji, accessibility text and the editor's chips are all
  read from it, so adding an item is one decorated function.
- `studio/library/` has 85 new motions (eating, sipping, typing, reading, phone calls, selfies, singing, toasts,
  painting, gaming, lifting, guitar, juggling, magic, roaring, boxing, dances, faints, sobs …), 68 new props, 31 new
  effects, 47 new things to wear and 11 new mascots (dog, bunny, panda, tiger, koala, raccoon, pig, frog, penguin,
  mouse, lion).
- Each mascot has a favourite snack, so "eating" brings a bone for the dog, bamboo for the panda and cheese for the mouse.

## Phase 3: composer rules

23 numbered rules in `studio/rules.py` (`python -m studio.cli --rules`):
- Props claim paws.
- Motions take what is left, or swap to a version that works.
- A motion brings what it acts with.
- Things a motion acts with stay upright.
- One item per place on the body.
- Masks come off for eating.
- One effect over the head.
- An effect a motion already draws is not doubled.
- A size budget for Telegram.
- Calm motions stay calm.
- Colours stand out from the fur.
- A sign carries the caption.

Every change is explained in the editor's notes.

## Phase 4: reading English

`studio/parse/` was rewritten and split:
- `text.py` reads emoji, emoticons, laughter in any spelling, stretched words, chat shorthand, contractions and other
  languages.
- `morph.py` handles word forms.
- `typo.py` only fixes real typos (v3 turned "eating" into "sweating" and "orange" into "rage").
- The lexicon and templates are split by topic into `lexicon/*.yaml` and `templates/*.yaml`.

The rules cover negation in lists, colours that stick to the right item, which paw holds what, gaze, tempo,
intensity, and captions from quotes, "saying …" or "a sign reading …".

## Phase 5: framing and checks

- **Auto-framing** (`studio/framing.py`) measures what the animation actually covers. Balloons, clouds and hats are no
  longer cut off, and the scene is placed above or below the caption.
- **`python -m studio.qa`** checks every item on every mascot, standing and sitting. It confirms the item builds, its
  loop has no seam (measured on the picture), nothing touches the canvas edge, and Telegram's 64 KB limit holds. It also
  checks every motion at 1, 1.5 and 3 seconds.
- **`python -m studio.cli --check`** keeps the lexicon consistent: one entry per phrase, and only names the registry
  knows.

## v3 bugs fixed

- **Crashes.** Two of the same effect crashed v3 with duplicate layer names. The composer now removes repeats, and an
  effect a motion already draws is not drawn twice.
- **The typo fixer changed real words.** It turned "eating" into "sweating" (a scared fox), "clapping" into
  "napping", "orange" into "rage" and "what" into "hat". Now real English words are never "fixed".
- **Animals and objects nobody understood.** "bunny reading a book" made a fox wearing glasses, and "raccoon with a
  trash can" made a fox. 159 of the 296 realistic test prompts were not understood at all.
- **Things cut off at the edge.** Fixed size guesses pushed a balloon on a string out of the top of the canvas while
  sitting, and cut off rain clouds and party hats under captions.
- **The still frame missed the effects.** The PNG showed the motion's best pose, but each effect at whatever point it
  had reached, so a sleepy sticker had no z's. Telegram's first frame and WhatsApp's resting frame were simply frame 0.
- **Dark fringes and grey glows** on exported PNG, WebP and GIF files. rlottie's pixels are premultiplied and were
  saved as if they were not.
- **Fading effects dimmed the mascot** in Telegram's player.
- **Misspelt channel names were ignored.** A misspelt channel in a clip was keyed and never played. It now raises an
  error naming the channel.

Before delivery, the QA run also found and fixed issues in the new items. Examples: loop seams, a dumbbell over the
face, snacks covering the eyes, hats sinking into the lion's mane, and phrases that belonged to two entries.

## Compatibility

- **Original animations:** the app's 23 clips and 4 effects build byte-identical files (`rig/RIG.md` → Checks).
- **Saved stickers:** every saved v3 spec still loads.
- **Web editor:** `app/vocab.py` returns the same shape, now filled from the registry. The app's 25 tests pass.
- **Old imports:** `studio/motions.py`, `accessories.py` and `extras.py` keep their v3 names as views of the registry.
