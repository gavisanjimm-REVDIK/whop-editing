# BOXABL × ClipFarm, AI original Shorts

Brief: original photorealistic AI videos where **BOXABL is the star**. The house is on screen and BOXABL is
spelled right. Everyone in them looks good. @boxabl goes in the caption and the AI label is on.
Titles and captions are in `YOUTUBE_CAPTIONS.md`.

## How the videos are made
1. **Keyframes**: photoreal AI images (Nano Banana 2 via ElevenLabs). The real BOXABL Casita photo is used as the reference image so the house looks right.
2. **Branding**: the official BOXABL wordmark (`../assets/boxabl-logo-*.png`, taken from boxabl.com) is perspective-mapped onto the house/truck in the edit, because AI can't spell. `keyframes/*_raw.jpg` are the untouched AI outputs.
3. **Edit**: `fx.py` is a frame-by-frame compositor. It has a virtual camera for pans, zooms, punches and shake, plus text animation, grading, grain, flashes and RGB split. Sound effects and music are synthesized in numpy, so there are no copyrighted tracks.

| Script | Output | Style |
|---|---|---|
| `short_documentary.py` | `out/01_nature_documentary.mp4` (21 s) | Nature documentary: telephoto drifts, film grade, species lower-third, record-scratch comedy cut |
| `short_mascot.py` | `out/02_meet_foldini.mp4` (14 s) | Brainrot hype: beat-locked zoom punches, flash frames, word pops, "new character unlocked" card |

```bash
python3 short_documentary.py && python3 short_mascot.py
```

Requires `ffmpeg`, Python with Pillow and numpy, and the Inter and Caladea fonts.

## Mascot: Casitino Foldini
A living BOXABL Casita with window eyes, a door smile, little panel arms and a red neckerchief.
Catchphrase: **"Fold it. Ship it. LIVE in it."** Bring him back in every video so people recognize him.

## Real people
There are no AI likenesses of Elon, Trump or the Tiramanis in these videos. Photoreal fake footage of real
people promoting a product reads like a real endorsement, and many AI tools refuse it anyway. Everything
here uses the mascot and the house.
