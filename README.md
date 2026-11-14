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

---

# FOMO "Guess The Fake Millionaire" clipping

`fomo_clip.py` renders 9:16 clips from the focus video (`footage/fomo.mp4`, from the campaign Drive link):
a cold open on the craziest line, then a quick rewind, then the full moment (always 8 s or more of continuous source).
The speaker sits in a 4:5 crop over a blurred fill, with the hook on top and big word-by-word captions
(the active word is highlighted) placed over the source's burned-in subtitles. Punch-in zooms land on the big lines.

- `reframe.py` detects camera cuts and finds faces to centre the crop on the speaker for each shot.
  Masked contestants can fool it, so `clips.json` has manual `cx` overrides.
- `transcript/` holds word-level timestamps (faster-whisper). Caption fixes are in each clip's `edit` map
  (by word start time), checked against the video's own burned-in subtitles.
- Every clip has its own moment, hook, accent colour and caption (`CAPTIONS_FOMO.md`).

```bash
python3 fomo_clip.py clips.json            # all clips -> out/
python3 fomo_clip.py clips.json 06_bowling # one clip
```

Approved creators are Insentos, Maurits and Orangie. Brez is in the video but not on the list,
so no clip is built around him.
