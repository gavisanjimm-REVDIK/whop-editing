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

# YoungLA Black Friday clipping (Bodybuilders vs Models)

Three 9:16 clips, each in a different editing style, cut from the one source video in the brief.
Only that footage is used. Sound effects are synthesised from scratch in `sfx.py` (no copyrighted audio),
and swears are bleeped.

| Clip | Moment | Style |
|---|---|---|
| `out/01_rage_quit.mp4` (30 s) | co-host "goes to the bathroom"... then drives off | meme storytime: cold-open hook, B&W freeze + record scratch, 2.6x speed ramp, punch-ins with bass booms, white backflash transitions |
| `out/02_fit_judges.mp4` (36 s) | skully debate + guessing Quav's song | game show: live W/L scoreboard, green ding + green flash for a W, red buzzer + red flash for an L, check/cross stamps |
| `out/03_aura_battle.mp4` (39 s) | Jay Cutler vs Marlin "Mog Off"; Lex says the sound guy has the most aura | hype runway: camera-flash backflash + shutter on every cut, VS card, aura-meter pop-ups, B&W "plot twist", airhorn |

Captions for posting: `YOUNGLA_CAPTIONS.md`.

## Usage
```bash
mkdir -p footage && curl -L -o footage/bvm.mp4 "<dropbox link from the brief, with dl=1>"
python3 youngla_bf.py              # all three -> out/
python3 youngla_bf.py 02_fit_judges --preview   # one clip, fast encode
python3 sfx.py                     # writes every sound effect to assets/sfx/*.wav to listen to
```

- `editor.py` – frame-by-frame vertical editor: shots (crop/zoom/pan, speed, freeze, J-cuts), flashes,
  green/red tints, punch-ins, shake, RGB split, pop-up text, word-by-word captions, SFX mixing, bleeps.
- `sfx.py` – green ding, red buzzer, boom, whoosh, camera flash, shutter, riser, record scratch, pop,
  tick, ka-ching, airhorn, "bruh" drop.
- `youngla_bf.py` – the three edits (shot lists, text, effects, sound cues).
- `transcripts/` – whisper word timings of the source (captions are built from these; a few mishearings are
  fixed in `fix_transcript()`).

Requires `ffmpeg`, Python with numpy + Pillow. Fonts (Anton, Bangers, Luckiest Guy, Montserrat; all OFL/Apache)
are in `assets/fonts/`.
