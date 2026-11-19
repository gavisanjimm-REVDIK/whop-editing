# SEGA – Football Manager 27 (USA/Canada) clipping

9:16 clips in the house style: black canvas, bold white English hook text, the creator's vertical video in
the middle (rounded corners), and the official white FOOTBALL MANAGER 27 wordmark under it on every clip.

## Campaign rules (from the brief)
- Use **only** the creator videos from the content folder (Kacee Anderson, NickRTFM, El Soccer Guy).
- **No added music, no AI voices.** Original creator audio only.
- FM logo on every clip (done automatically, from brand.footballmanager.com → FM27 wordmark, light).
- On-screen text in English, genuine and true. No exaggerated hooks, no made-up facts.
- Caption: `@footballmanager`, the creator's handle, `#Ad` first hashtag on its own line, max 3 more (see `CAPTIONS.md`).
- At least 10 s long. Keep it up 30+ days, likes visible. Max 5 posts of the same video. USA/Canada audience.

## Usage
1. Download the creator videos into `footage/fm27/` with these names:
   `kacee1_angelcity.mov`, `kacee2_van.mov`, `nick_ad1.mp4`, `elsoccer_angelcity.mov`, `elsoccer_clubamerica.mov`
2. Run `./fm27/render_all.sh` (outputs to `out/fm27/`), or render one:

```bash
python3 fm27/make_clip.py --input footage/fm27/nick_ad1.mp4 --seg 0-18.75 \
  --text "Football Manager 27 has a new mode called Shuffle Draft" --out out/fm27/05.mp4
```

Hook text auto-fits to two lines. Requires `ffmpeg`, Pillow and the Inter font.
