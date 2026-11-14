# Warzone Season 1 clipping

Makes 9:16 clips in the reference style: black canvas, bold white hook text, official footage in the
middle, and the official Warzone logo (always on) with "SEASON 1 OUT NOW" underneath.

## Campaign rules (from the brief)
- Use **only** footage from the official content link (Season 1 Trailer + Developer Briefing).
- **No added music and no AI voices.** Original audio only (the trailer already has "Haegeum" in it).
- Warzone logo on every clip, clear and visible (done automatically).
- Caption needs `@callofduty`, `Season 1 out now`, the song credit, and `#Ad` (see `CAPTIONS.md`).
- Keep the post up for 30+ days with likes visible. Don't post the same video more than 5 times.

## Usage
1. Download the Trailer and Developer Briefing from the MediaSilo link into `footage/`.
2. Run `./render_all.sh` to make all clips, or render one (aim for 10–30 s):

```bash
python3 make_clip.py --input footage/trailer.mp4 --start 0:05 --end 0:18 \
  --text "Call of Duty: Warzone gets two new maps Hajin and Zodiac in Season 1" \
  --out out/clip01.mp4
```

Options: `--zoom 1.0` shows the full 16:9 frame (default 1.15 crops the sides a little, like the reference).
`--no-tagline` hides the "SEASON 1 OUT NOW" line.

Requires `ffmpeg` and Python with Pillow. The font path in `make_clip.py` uses Inter ExtraBold.

## STRANGER THAN HEAVEN Act 2 (SEGA)
Footage: `STH_Kure_Story_Trailer.mp4` from the official Frame.io folder, saved as `footage/sth_trailer.mp4`.
Logo: `assets/sth-logo.png` (official, from the brief). Render with `./render_sth.sh`; captions in `CAPTIONS_STH.md`.
The renderer takes `--logo`, `--logo-width` and `--tagline`, so other campaigns can reuse the same layout.
