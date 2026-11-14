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

## LTK – Creator Earnings campaign
`python3 ltk_edit.py --edit lock_in` renders `out/ltk_lock_in.mp4` and `--edit old_posts` renders `out/ltk_old_posts.mp4`, from the official LTK folder (download it into `footage/ltk/`).
The cut list and on-screen text are at the top of `ltk_edit.py`. Captions and posting notes are in `LTK_CAPTIONS.md`.
The official logos are in `assets/ltk-logo-white.png` and `assets/ltk-logo-black.png`.
