# Biscuit animations, version 3

Version 3 puts Biscuit on its feet. It replaces version 2, which sat down in every clip.

## What is in here

| Folder | Contents |
|---|---|
| `lottie/` | 24 files with the same names as the originals. 19 Biscuit animations rebuilt, 4 effects reworked, `pawse_logo.json` unchanged. |
| `lottie_alternates/` | 4 extra Biscuit takes to play once in a while. |
| `rig/` | The generator that made them, with a guide (`rig/RIG.md`) for adding more mascots. |

## What changed since version 2

- **Biscuit stands.** It has short legs now and stands in 15 clips. It sits down only to rest:
  `biscuit_sleepy`, `biscuit_deep_sleep` and `biscuit_breathe` sit, `biscuit_meditate` sits cross-legged.
- **The legs act.** Weight shifts and toe taps in the calm clips. Jumps load the knees, push off, tuck
  the feet in the air and take the landing. `biscuit_carry_cloud` walks on the spot.
- **Proportions.** The head is a little smaller (93 %) and the torso is shorter, to make room for legs.
  Arms are slightly shorter. Everything else about the look is the same.
- The effects and the logo are the same files as in version 2.

## Dropping them in

Every file in `lottie/` keeps its original name, canvas size, frame rate and frame count, so replacing
the old files is enough. Layer names inside the files differ from the originals (Biscuit has arms, legs
and a `hips` layer now). That only matters if your app addresses layers by name.

Things that behave differently on purpose:

- `biscuit_hop_in` ends on exactly the first frame of `biscuit_idle`, so switching to idle afterwards has no jump.
- The phone, bell and badge are on Biscuit's right, the clipboard on the left. The cloud in
  `biscuit_carry_cloud` floats on a string above the right paw.
- In `biscuit_gift` Biscuit stands behind the box with a foot showing at each side. The box is 16 % smaller.
- In `biscuit_pop_up` the legs stay hidden behind the card, as the whole lower body did before.

## The alternate takes

| File | Fits between loops of | Length | What happens |
|---|---|---|---|
| `biscuit_idle_alt_butterfly.json` | `biscuit_idle` | 6 s | A butterfly lands on the nose and Biscuit freezes in mid-step, one foot in the air |
| `biscuit_idle_alt_sneeze.json` | `biscuit_idle` | 3 s | The sneeze knocks Biscuit onto its bottom; it rubs its nose and hops back up |
| `biscuit_idle_alt_peekaboo.json` | `biscuit_idle` | 3 s | Hides behind its paws, knees together, then a star jump |
| `biscuit_sleepy_alt_bubble.json` | `biscuit_sleepy` | 3 s | A sleep bubble swells, pops and startles it |

Each one starts and ends on exactly the first frame of the regular clip. When a loop of the regular
clip finishes, play an alternate once now and then (one time in eight feels about right), then go back
to the regular clip.

## What was checked

- All 28 files load in lottie-web with no player errors.
- All 24 replacements match the originals' canvas size, frame rate and frame count.
- Looping clips were compared last frame against first frame: no seam.
- `biscuit_hop_in` and the four alternates were compared against the clip they hand over to: the poses match exactly.
- Nothing leaves the canvas, except the pop-up card (as in the original) and the butterfly flying in and out.
- Every file renders the same in lottie-web and in rlottie, a second independent player.
- The rig was run on two throwaway mascots (one with different legs and no tail, one with no legs at all): all 23 clips built for both.

They were not tested inside your app, or in the iOS and Android Lottie libraries directly. The files
only use features all Lottie players support (shape layers, groups, paths, fills, strokes, trim paths).
