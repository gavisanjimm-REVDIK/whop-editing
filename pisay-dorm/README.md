# A Day in My Life as a Pisay Scholar – Dorm Edition (Scenes 1–3)

Renders `out/scenes1-3.mp4` (1920×1080, 30 fps, ~1:20) from the script and the media in the shared Drive folder.

```bash
python3 render.py                       # full render (~10 min)
python3 render.py --stills 7 40 75      # preview stills into out/stills/
```

Put the media in `footage/drive/` with the Drive names: `VID1.MOV`–`VID5.MOV`, `VO1.m4a`–`VO4.m4a`.
Needs `ffmpeg`, Python with `numpy`, `scipy`, `opencv-python-headless`, `Pillow`, and the Inter font.

## Style
Minimalist: simple cuts, small plain white captions (one phrase at a time, no word highlighting), clean Inter type.
The one effect is the **crumpled-paper opening** whenever real footage cuts to a text-only graphic; going back to
footage the sheet crumples and is tossed away. Text-only graphics sit on that plain crumpled sheet.

## Edit (output time)

| Time | Script | Media | Graphics |
|---|---|---|---|
| 0:00–0:08 | Scene 1, VO1 "Welcome…" | VID1 wake up | when Jimm leaves the bed, **A Day in My Life / as a Pisay Scholar — Dorm Edition** stays |
| 0:08–0:15 | VO1 "Hi, I'm Jimm…" | VID2 closet / perfume | captions |
| 0:15–0:20 | VO1 "And aside from…" | black screen | captions |
| 0:20–0:24 | VO1 "my allowance." | VID3 coins, 0.3× slow-mo | caption |
| 0:24–0:38 | Scene 2, VO2 + "Can I actually afford it?" | VID4 laptop | captions |
| 0:38–0:43 | Text-graphics1 | paper | **COSTS BEHIND THE CHANCE** + study title |
| 0:43–0:59 | Scene 3, Jimm on screen | VID5 balcony | captions |
| 0:59–1:10 | Text-graphics2, VO3 | paper | We surveyed **47** PSHS-CRC students |
| 1:10–1:20 | VO4 | paper | **76.6%**, 36 out of 47 students, finding |

## Audio
VO1–VO4 as recorded (VO1 split at its pauses to land on the cuts), Jimm's on-camera lines levelled to match, quiet
natural sound under VID1–VID3, and soft paper sounds on the transitions. No music yet (none in the folder).
