# A Day in My Life as a Pisay Scholar – Dorm Edition (Scenes 1–3, graphics pass)

Renders `out/scenes1-3.mp4` (1920×1080, 30 fps, ~75 s) from Jimm's footage and the script.

```bash
python3 render.py                       # full render (~10 min)
python3 render.py --stills 7.5 36 66    # preview stills into out/stills/
```

Put the footage in `footage/` with its original names (`IMG_9867.MOV`, `IMG_9868.MOV`, `IMG_9873.MOV`,
`IMG_9879.MOV`). Needs `ffmpeg`, Python with `numpy`, `scipy`, `opencv-python-headless` and `Pillow`.
Fonts are in `fonts/` (Anton, Caveat, Permanent Marker, Archivo Black from Google Fonts) plus Inter and
JetBrains Mono from the system.

## Edit (output time)

| Time | Scene | Footage | Graphics |
|---|---|---|---|
| 0:00–0:10 | 1 | IMG_9867 closet cam (door opens, Jimm gets ready, leaves, door shuts) | "hi, I'm Jimm!" + arrow; when Jimm walks out, the title **A DAY IN MY LIFE / as a Pisay Scholar / DORM EDITION** builds and stays on the black |
| 0:10–0:13 | 1 | black screen | typed line "aside from classes and requirements, there's one thing I also have to manage..." |
| 0:13–0:18 | 1 | IMG_9868 cards + coins, 0.3× optical-flow slow motion | **MY ALLOWANCE.** slam + shake |
| 0:18–0:34 | 2 | IMG_9873 laptop → turns to camera | stickers: "a competition I wanted to join!" (arrow to the screen), "but as a dormer... everyday expenses + food + fare + school supplies"; punch-in and **BUT CAN I ACTUALLY AFFORD IT?** synced to his line |
| 0:34–0:40 | 2 | text-only | crumpled-paper opening → **COSTS BEHIND THE CHANCE** + full study title |
| 0:40–0:56 | 3 | IMG_9879 balcony | paper crumples away; JIMM lower third; word-by-word captions of his line |
| 0:56–1:03 | 3 | IMG_9879 after he walks off (0.65× slow) | survey card: "we surveyed 47 PSHS-CRC students", 47 people |
| 1:03–1:15 | 3 | text-only | crumpled-paper opening → **76.6%** (count-up, "about 3 out of 4") → **36 OUT OF 47 STUDENTS** (36 of 47 figures in red) |

## Transitions
Every cut from real footage to a text-only card uses the **crumpled-paper opening**: a paper ball is tossed in,
lands, and unfolds into the full-frame sheet with the card text printed on it (`paper.py`). Text-only cards stay
on that sheet (notebook paper with leftover wrinkles). Going back to footage, the sheet crumples and is tossed off.

## Audio
Voice-over and music are **not** in yet. The track has Jimm's on-camera lines (laptop question, balcony), the
closet room sound and coins, and synthesized SFX for the graphics (`sfx.py`), leaving room for VO and music.
Timings are set for the planned VO lines; nudge the `T_*` constants at the top of the timeline in `render.py`
once the VO is recorded.
