# STRANGER THAN HEAVEN Act 2 clipping (SEGA)

9:16 clips in the reference style: black canvas, official STH logo top-left, two-line hook text
(yellow, game title in green, key word in red), official trailer footage cropped to 4:3 in the middle.

## Campaign rules (from the brief)
- Only footage from the official Frame.io folder (`STH_Kure_Story_Trailer.mp4`, 3840x2160, 3:26).
- **No added music, no AI voices.** Original trailer audio only.
- Official logo on every clip (done automatically).
- Caption copied exactly, `#Ad` on its own line (see `CAPTIONS.md`). YouTube Shorts also tags @SEGA_West.
- It's a trailer: don't call it "gameplay". Keep posts up 30+ days with likes visible; max 5 posts of the same video.

## Usage
1. Download the trailer from the Frame.io folder to `footage/sth_trailer.mp4`.
2. Run `./sth/render_all.sh` (writes `out/sth/`), or render one:

```bash
python3 sth/make_clip.py --input footage/sth_trailer.mp4 --seg 32.5-46.9 \
  --text "CAN'T WAIT TO BE A BADASS *YAKUZA* IN|STRANGER THAN HEAVEN." --out out/sth/02.mp4
```

Text markup: `|` = line break, `*word*` = red, "STRANGER THAN HEAVEN" is always green.
Repeat `--seg` to join several parts. The trailer's built-in letterbox bars are cropped off automatically.

Font: Bebas Neue (SIL OFL), bundled in `sth/assets/`.
