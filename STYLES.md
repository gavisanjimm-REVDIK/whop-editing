# Editing styles

Use a style with `python3 make_clip.py --style <name> ...`. A style only sets defaults; any flag you pass wins.

## edit1
Reference: `out/sth_02_combat.mp4` (STRANGER THAN HEAVEN combat clip).

- 1080x1920 black canvas, official 16:9 footage centred slightly above middle (1.15 zoom, sides cropped).
- Hook text above the footage, bold white Inter ExtraBold, **3 short lines** split with `|`.
  The game name sits **alone on its own line in logo yellow** (`#DFBE31`), marked with `*stars*`.
  Example: `--text "The fights in|*STRANGER THAN HEAVEN*|look absolutely brutal."`
- Footage cut on the trailer's own shot changes (find them with ffmpeg `select='gt(scene,0.25)'`);
  several `--seg` pieces can be joined to skip shots, with a 0.35 s audio crossfade at each jump (video hard cut).
- Original trailer audio only, short fade in/out. No music, no voiceover.
- Official STH logo (300 px wide) under the footage with **PRE-ORDER NOW** beneath it.
- 15-30 s, ends before any subtitle with swearing.
