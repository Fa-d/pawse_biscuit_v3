# Pawse mascot rig

This is the generator behind the Biscuit animations. It exists so that the next mascot gets every
animation for free: you describe the new character once, run one command, and all 23 clips are
built for it, and the sticker studio (`studio/`) can use it with its 99 motions, 76 props, 43 effects and
56 things to wear.

## The one rule

**Animations never contain a character's coordinates.** A clip only says things like "raise the
right paw to the `wave_hi` pose", "sit down", "tail goes to `up` and wags", "face becomes `joy`",
"take a step with the left foot". Each character decides what those words mean for its own body.
Keep to that rule and any clip plays on any mascot.

```
mascot/
  characters/biscuit.py   what Biscuit looks like and where its joints are   <- copy this for a new mascot
  characters/*.py         13 more, each a subclass that redraws what differs: mochi (cat), bruno (bear), pip (dog),
                          clover (bunny), bao (panda), tora (tiger), kiko (koala), rocco (raccoon), truffle (pig),
                          fern (frog), pebble (penguin), nib (mouse), leo (lion)
  clips/core.py           the 19 standard animations
  clips/alts.py           the 4 rare alternate takes
  clips/moves.py          reusable acting: jump, walk, step, tap, kick, wave, breathe, squash...
  props.py                phone, bell, clipboard, badge, gift, cloud, sparkles, confetti...
  rig.py                  the list of channels, the 41 expressions, stances, automatic follow-through
  character.py            turns a pose into Lottie layers (shared by every mascot)
  clip.py                 keyframe tracks, easing, springs
  lottie.py               Lottie writer and the keyframe fitter
  effects.py              flame, check burst, sparkle, star burst
  build.py                command line
tools/                    preview and quality-check scripts
```

## Restoring this folder from the project docs

The project keeps these files under `rig/`. Recreate the same layout on disk and add three empty files:
`mascot/__init__.py`, `mascot/characters/__init__.py` and `mascot/clips/__init__.py`. The current
output is under `v3/` (the 24 replacement files) and `v3/alternates/` (the 4 extra takes). The
originals are under `raw/` and are never overwritten.

## Building

```
pip install numpy scipy pillow playwright rlottie-python     # the last three are only for the tools
python3 -m mascot.build --char biscuit                       # writes dist/biscuit/biscuit_<clip>.json
python3 -m mascot.build --char biscuit --only idle,wave      # just some clips
python3 -m mascot.effects --out dist/effects                 # flame, check_burst, sparkle, star_burst (+ logo copied)
```

The preview tools render with lottie-web in headless Chromium. They expect `render/node_modules/lottie-web`
(`cd render && npm install lottie-web`).

## Standing and sitting

A mascot stands on its own legs by default. Fifteen clips are played standing; `sleepy`, `deep_sleep`
and `breathe` sit down, and `meditate` sits cross-legged. A clip chooses with one line:

```python
c.stance((0, "sit"))        # 'stand' (default), 'wide', 'sit', 'lotus'
```

The character says what each stance means for its body (how far the hips drop, where the feet go,
whether the soles face the viewer). Stances blend, so a clip can also change stance on the way:
the sneeze take is knocked from `stand` to `sit` and hops back up.

## Adding a mascot

The quickest way is to subclass a mascot with similar proportions and redraw only what differs:
`characters/mochi.py` (a cat) and `characters/bruno.py` (a bear) subclass Biscuit and override the head, ears, face
details, body markings, tail and palette. They build all 23 clips unchanged.

For a mascot with different proportions, start from a copy:

1. Copy `mascot/characters/biscuit.py` to `mascot/characters/<name>.py` and rename the class.
2. Change the data (table below). Everything is in canvas pixels for a 512 x 512 canvas, drawn in the
   rest pose: standing, facing the viewer, feet on the ground line.
3. Add its name to `MASCOTS` in `mascot/build.py` (the class is the capitalised name).
   `Character.problems()` lists anything missing or out of shape in its data; `tools/smoke_test.py` and the
   studio's `python -m studio.qa --bases <name>` build everything on it.
4. Run `python3 -m mascot.build --char <name>`, then `python3 tools/check.py dist/<name>/*.json`
   and `python3 tools/handover.py <name>`.

| What to define | Attribute | Notes |
|---|---|---|
| Colours | `pal` | `orange` (main), `arm`, `leg`, `tail`, `tail_tip`, `stripe`, `cream`, `dark`, `iris`, `pink`, `white` |
| Size in the canvas | `base_scale` | Leaves headroom for bounces. Biscuit uses 0.98. |
| Head | `neck`, `neck_at`, `head_scale`, `crown` | `neck` is the pivot in the head drawing, `neck_at` where it sits on the body, `crown` the top of the skull. |
| Mane or hair | `top`, `collar` | Optional. `top` is the top of the head's outline when a mane or hair rises above the skull (halos and hats clear it); `collar` is where things worn at the neck hang, in body coordinates. |
| Head parts | `ear_pivot`, `tuft_pivot`, `eye`, `nose`, `mouth` | Give the right side only; the left side is mirrored. |
| Arms | `shoulder`, `arm` = lengths `L1`, `L2` and width `w` | Upper arm, forearm, thickness. |
| Where paws can go | `face_anchors`, `body_anchors` | Points on the face are given in the head drawing; `head_pt()` places them. |
| Arm poses | `arm_poses` (built in `__init__`) | Most are solved automatically from the anchors with `self.ik(...)`. The names must stay the same. A pose a mascot lacks is played as the nearest one it has (`POSE_FALLBACK`), so an older mascot never breaks on a newer clip. |
| Paw shapes | `paw`, `paw_color`, `hand_variant()` | Fist, thumb up, pointing finger and peace sign are drawn from the open paw's size; override `hand_variant` to draw them yourself. |
| Legs | `pelvis`, `hip`, `foot`, `leg` | `pelvis` is the pivot of hips and torso, `hip` where a leg leaves the body, `foot` the ankle when standing. `leg` = width `w`, `knee` (how far the knee bows), `stretch` (limit). Leg length is the distance from `hip` to `foot`, so keep them close for stubby legs. |
| Stances | `stances` | One row of numbers per name, in the order of `rig.STANCE`. `stand` and `sit` are required; Biscuit also has `wide` and `lotus`. |
| Tail | `tail` | `base`, `length`, `bones`, width `profile`, `tip_from`, and the named `poses`. Set `tail = None` for a mascot without one. |
| Drawings | `head_shapes`, `ear_shapes`, `tuft_shapes`, `eye_shapes`, `nose_shapes`, `blush_shapes`, `face_static`, `body_shapes`, `hand_shapes`, `foot_shapes` | Return Lottie shape groups. `geom.smooth(points)` makes a smooth outline through points. |
| How floppy it is | `dyn` | Overrides for the follow-through springs, for example `{"ear.freq": 1.6, "ear.y": 0.8}` for long soft ears. |

Paws are drawn with the wrist at (0, 0) and the fingertips towards +y. Like a paw print, the toe beans
go at the fingertip end and the big pad nearer the wrist. `thumb_at` is where the thumb sits when the
back of the paw faces the viewer; the rig moves it to the other edge when the paw turns palm-out.

Feet are drawn around the ankle at (0, 0). `foot_shapes` gives two ellipses, `flat` (standing, seen
from the front) and `sole` (tipped up towards the viewer), plus the `pads` that show on the sole and
optional `toes` marks for the flat view. The rig blends between the two as a foot lifts.

A mascot without legs sets `leg = None`. Its feet then hang from the body as plain drawings and
every clip still plays (`tools/smoke_test.py` builds one such mascot to prove it).

`tools/smoke_test.py` builds all 23 clips for two throwaway characters: one with no tail, long ears,
other colours and different legs, and one with no legs at all. Neither needs a change to any clip.

## The skeleton inside every file

Layer and group names are the same in every clip, so an app can address parts by name.

```
shadow
root            null   whole-character move, squash and stretch, flips
  hips          null   pelvis: sits down, bends the knees, shifts the weight
    tail               bone chain: groups "tail 0" > "tail 1" > ...  each rotates at its joint
    body               torso, pivot at the pelvis
      right arm / left arm     bone chain: "upper arm" > "forearm" > "hand"   (held props live inside "hand")
      neck      null   head pivot
        right ear, left ear, head (contains "tuft"), face, eyes, brows
  right leg, left leg  one bendy limb from the hip joint to the ankle, solved every frame
  right foot, left foot        stay where the clip plants them while the hips move
```

Arms and tail are real joints: every key in the file is a plain rotation. Legs are solved the other
way round: the feet say where they are, the hips say where they are, and the leg fills the gap,
bowing at the knee when it is shorter than its rest length.

## Channels a clip can key

`rig.CHANNELS` lists all of them with their rest values. The main ones:

- **Whole body:** `root.x`, `root.y`, `root.rot`, `root.sx`, `root.sy`, `root.scale`, `root.pivot`
- **Hips:** `hip.x`, `hip.y` (down = bend the knees, up = on tiptoe), `hip.rot`
- **Torso and head:** `body.rot`, `body.sx`, `body.sy`, `head.rot`, `head.x`, `head.y`, `head.sx`, `head.sy`
- **Ears and tuft:** `ear.L.rot`, `ear.R.rot`, `tuft.rot`
- **Eyes:** `eye.open` (1 open, 0 closed), `eye.arc` (+1 happy arch, -1 sleepy curve), `eye.w`, `eye.h`,
  `look.x`, `look.y`, `eye.cross`, `eye.L.blink`, `eye.R.blink`
- **Brows and mouth:** `brow.show`, `brow.y`, `brow.tilt`, `mouth.smile` (+1 cat smile, -1 frown),
  `mouth.open`, `mouth.o`, `tongue`, `nose.y`, `blush`
- **Arms:** named poses through `c.arm(...)`, plus offsets `arm.R.sh`, `arm.R.el`, `arm.R.wr`, `arm.R.len`;
  `hand.R.palm` (pads towards the viewer), `hand.R.s`
- **Legs and feet:** the stance through `c.stance(...)`, plus `foot.R.x` (outwards), `foot.R.y` (negative lifts),
  `foot.R.rot`, `foot.R.sole` (1 = pads towards the viewer), `foot.R.s`, `leg.R.bend` (1 knees out, -1 knees together)
- **Tail:** named poses through `c.tailpose(...)`, `c.wag(...)`, plus `tail.len`, `tail.fluff`,
  `tail.front` (0 behind the body, 1 in the lap, 2 in front of the feet)

Angles for arms: 0 hangs straight down, positive swings outwards and up, the same number for both sides.
Tail headings: 0 points right, positive turns up.

Named arm poses (52): `rest`, `relax`, `wave_lo`, `wave_hi`, `cheer`, `cheer_hi`, `cheer_out`, `chin`,
`mouth`, `cheek`, `belly`, `lap`, `hip`, `hold`, `hold_up`, `carry`, `edge`, `ring`, `knee`, `lid`,
`cover_eyes`, `peek`, `stretch`, `salute`, `facepalm`, `ear`, `chest`, `cross`, `hug`, `wide`, `shrug`, `flex`,
`pray`, `clap`, `clap_open`, `point_out`, `point_up`, `point_fwd`, `thumbs_up`, `thumbs_down`, `tray`, `present`,
`lift`, `fist_pump`, `reach`, `dab`, `dab_in`, `behind`, `fly`, `bite` (food to the mouth), `phone_ear`, `text`
(both paws on a phone at the chest).
Paw shapes (`hand.R.shape`): 0 open, 1 fist, 2 thumb up, 3 pointing finger, 4 peace sign.
Named tail poses, standing: `rest`, `out`, `in`, `up`, `low`, `floor`, `flick_out`, `flick_in`, `curl`, `alert`,
`tucked`. Sitting: `ground`, `ground_up`, `wrap` (across the lap, with `tail.front` = 1).
Stances: `stand`, `wide`, `sit`, `lotus`, `crouch`, `tiptoe` (and `kneel`, which falls back to `sit`).
Expressions (41): `neutral`, `smiley`, `joy`, `worried`, `curious`, `sleep`, `calm`, `surprised`, `angry`, `wink`,
`focused`, `laugh`, `grin`, `sad`, `cry`, `pleading`, `love`, `starry`, `dizzy`, `dead`, `shocked`, `smug`, `unamused`,
`pout`, `nervous`, `kiss`, `silly`, `yawn`, `drowsy`, `determined`, `mischief`, `sick`, `confused`, `flustered`,
`relieved`, `proud`, `scared`, `hungry`, `cool`, `furious`, `excited`. Special eyes (`eye.style`: 1 hearts, 2 stars,
3 spirals, 4 crosses, 5 squeezed shut, 6 sparkling), teary eyes (`eye.wet`), lids (`lid.top`), one brow at a time
(`brow.L.y`, `brow.R.tilt` …) and the mouth shapes are channels too; at their rest values every file draws exactly
what it drew before they existed.

## What moves by itself

`rig.evaluate` adds follow-through after the clip's own keys, so clips stay short:

- **planted feet:** while the body bounces, the feet stay on the ground and the legs stretch and bend.
  When the body rises further than the legs can reach, the feet let go, spring up into a tuck, reach
  for the ground on the way down and touch first. A foot never goes through the floor.
- **knees:** a leg that is shorter than its rest length bows at the knee; a stretched one thins a little
- a lifted foot turns with its leg, a planted one stays flat
- ears and tuft lag behind head turns and flop on jumps and landings
- the tail trails the hips, later and softer towards the tip
- wrists flop behind the forearm; arms swing a little with vertical motion
- the shadow shrinks as the character leaves the ground

A clip can turn any of these down with `c.auto.update({...})`.

## Writing a clip

```python
def wave(c):
    c.face(0, "smiley", dur=0)                 # expression at frame 0
    M.breathe(c, period=60, amp=0.02)
    M.wave(c, "R", None, None, period=30)      # right paw up and waving for the whole loop
    M.bob(c, 30, amp=3.0)                      # knees keep the rhythm, feet stay put
    M.tap(c, "R", 8, n=4, gap=30)              # the right foot taps along
    c.tailpose((0, "low"))
    c.wag(amp=8.0, period=30, lag=0.16)
    c.blink(102)
```

Leg moves in `clips/moves.py`:

| Move | What it does |
|---|---|
| `M.jump(c, t, h=...)` | Knees load, legs snap straight, tuck in the air, take the landing |
| `M.bob(c, period, amp)` | Rhythmic knee dips on the spot |
| `M.weight(c, (t, x), ...)` | Shifts the weight from foot to foot; the hips swing and tip |
| `M.step(c, side, t)` | Picks one foot up and puts it down (pads flash) |
| `M.tap(c, side, t, n)` | Toe taps |
| `M.kick(c, side, t)` | A little sideways kick |
| `M.patter(c, t0, t1)` | Happy feet: quick alternating steps |
| `M.walk(c, period)` | Walking towards the viewer on the spot, with a waddle |

Register a clip in `CLIPS` with its frame count. Looping clips must end where they start; the build stops
with a message naming the channel if one does not. Easing names: `io`, `soft`, `out`, `in`, `back`
(overshoot), `snap`, `anti` (wind-up), `hold`, `elastic`, `bounce`.

Two registry options control how a clip joins the next one:

- `settle=True` for a clip that hands over to another clip instead of looping (`hop_in`, every alternate take).
  Its springs start at rest and ease out, so its last frame is exactly the pose that was keyed.
- `calm=12` for a base clip that others hand over to (`idle`, `sleepy`). Its first frame is then exactly
  the keyed rest pose.

Paws that must stay on something (a card edge, a box lid) use `c.pin(side, t0, t1, point)`. Things held
in a paw are props placed in the slot `hand.R` or `hand.L`. Effects that belong near the head
(`P.zzz`, `P.thought_dots`) take `rel=True`: their positions are then offsets from the top of the
mascot's head, so they sit right for any mascot and any stance.

## Alternate takes

`biscuit_idle_alt_butterfly`, `biscuit_idle_alt_sneeze` and `biscuit_idle_alt_peekaboo` start and end
on exactly the first frame of `biscuit_idle`. `biscuit_sleepy_alt_bubble` does the same for
`biscuit_sleepy`. To use them: when a loop of the regular clip finishes, occasionally (for example one
time in eight) play one alternate once, then go back to the regular clip. `biscuit_hop_in` also ends
on the first frame of `biscuit_idle`.

## Checks

```
python3 tools/check.py --orig raw dist/biscuit/*.json dist/effects/*.json     # player errors, pops, loop seams, clipping, metadata
python3 tools/handover.py biscuit                                             # hop_in -> idle and every alternate take match their base clip
python3 tools/cross_render.py dist/biscuit/*.json                             # lottie-web against rlottie
python3 tools/smoke_test.py out/smoke                                         # all clips on two throwaway mascots
python3 tools/tailcheck.py                                                    # how low and how far right each tail pose reaches
python3 tools/render_sheet.py --out sheet.png --n 12 --cols 6 dist/biscuit/biscuit_wave.json
python3 tools/variants.py poses.png "wave:face=smiley;arm.R=wave_hi;tail=low" "sit:stance=sit;tail=ground;arms=belly"
python3 -m studio.qa --bases leo                                              # every sticker item on one mascot
```

## Compatibility notes

- Only features every Lottie player supports are written: shape layers, null layers, parenting, groups
  with transforms, paths, ellipses, rectangles, fills, strokes, trim paths, hold keys. No masks, mattes,
  gradients, effects or expressions.
- The rig is sampled every frame and then reduced to as few eased keyframes as an error tolerance allows.
  Opacity and trim keys never overshoot their range, because some players wrap values above 100 %.
- A patch that shares part of an outline with the shape under it (cream cheeks on the head, dark ear
  tips) is pushed out by about a pixel with `pushed(...)`, so the colour underneath cannot show as a
  fringe. Fills never sit at a level where they would also colour a nested group.
