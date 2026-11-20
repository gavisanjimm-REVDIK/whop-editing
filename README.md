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
| `out/03_aura_battle.mp4` (39 s) | Jay Cutler vs Marlon "Mog Off"; Lex says the sound guy has the most aura | hype runway: camera-flash backflash + shutter on every cut, VS card, aura-meter pop-ups, B&W "plot twist", airhorn |

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

## Batch 2 – clean layout (`youngla_bf2.py`, `framed.py`)

| Clip | Moment | Style |
|---|---|---|
| `out/04_aura_goosebumps.mp4` (32 s) | Johnny on the runway: "I could feel it 100 miles away... head, shoulders, knees and toes" | aura detector: pink glow, shimmer + heartbeat, aura meter |
| `out/05_negative_152k.mp4` (43 s) | Lex wants the million flat, was once at -$152,000 over taxes, would buy 51% | bank app: live balance counter, coin ticks, buzzer, ka-ching |
| `out/06_jay_first_show.mp4` (34 s) | Jay Cutler's first fashion show; picks the SF90 that turns out to be Robbie's | talk show: applause (the host asks for it), ding / buzzer verdicts |

Layout: hook in the top band, footage in a 1080x1200 window, captions + labels in the bottom band, so text never
covers faces or clothes. Each source scene is auto-reframed with the YuNet face detector (crop on one person,
full 16:9 for two-shots). Cuts land on sentence ends. `--qa` re-detects faces in the output and reports any that
sit under text or get clipped. Captions use a second, more accurate transcription (`transcripts/*medium*`).

```bash
python3 youngla_bf2.py --qa        # all three -> out/, with the face check
```
Extra requirement: `opencv-python-headless` (model file is in `assets/models/`).

## Music + pacing update
- Every clip now has a meme-music bed (Kevin MacLeod, CC BY 4.0 – see `assets/music/CREDITS.md`; run
  `./fetch_music.sh` first). It ducks automatically under speech, fills the pauses, and cuts out on punchlines.
  **The credit lines in `YOUNGLA_CAPTIONS.md` must be posted with each clip.**
- Batch 2 opens on the punchline, tape-rewinds to the start, then tells the story. Dead air between finished
  sentences is trimmed (never mid-sentence); keywords in the captions are coloured with a small punch-in.

## Batch 3 – minimal (`youngla_bf3.py`)
Hook + footage + captions + music + one sound on the punchline. No labels, tints, flashes or rewinds.

| Clip | Moment | Music |
|---|---|---|
| `out/07_three_hours_late.mp4` (30 s) | shows up three hours late, goes straight to the bathroom | Pixel Peeker Polka (faster) |
| `out/08_already_handsome.mp4` (27 s) | mature answer, safe answer, then "I already have a G-Wagon. I'm already handsome." | Carefree |
| `out/09_disney_villain.mp4` (18 s) | "he kind of looks like a supervillain" while he walks the runway | Scheming Weasel (faster) |

## Batch 4 – reference style (`youngla_bf4.py`, `refstyle.py`)
Modelled on the user's reference clip (not copied): square footage on black, small lowercase hook with one red
keyword + emoji, one-word captions, light grade with exposure lift, one white backflash, one emoji pop, swears
cut out, music under the original audio. Captions/emoji are face-aware and every drawn box is re-checked against
faces detected in the finished video. `--no-music` writes versions for adding a trending sound in the app.

## Batch 5 – reference style (`youngla_bf5.py`)
`13_run_me_my_money` (Togi's photoshoot), `14_not_tryna_brag` (Marlon's runway résumé),
`15_jay_rates_dance` (Jay Cutler judges Lex's dance). Same renderer as batch 4; `--no-music` versions too.

## Batch 6 – "Clip The Pod" style (`youngla_bf6.py`, `podstyle.py`)
AI narrator intro (ElevenLabs "Ethan – Energetic YouTube Narrator", files in `assets/vo/`) over quick b-roll with a
red arrow on the subject, then the real conversation. Big colour-cycling one-word captions, an original ElevenLabs
trap beat (G minor, 123 BPM – the same feel as the reference's bed, `assets/music/elevenlabs_trap_beat.mp3`),
riser + 808 hit into each punchline. `16_skully_debate`, `17_can_i_have_some`, `18_hype_man`.

## Batch 7 – "Say Goodbye" + high-pitched narrator (`youngla_bf7.py`)
Same style as batch 6. The narrator lines are pitched up ~4 semitones (timing kept); the user's "Say Goodbye"
track is sped up 1.2x (`asetrate`) and mixed ~16–20 dB under the dialogue. The track is the user's upload and is
not committed: put it at `assets/music/say_goodbye_highpitch.mp3` (made with
`ffmpeg -i "Say Goodbye.mp3" -af "asetrate=44100*1.2,aresample=44100" assets/music/say_goodbye_highpitch.mp3`).
Emoji pops sit above the video; captions use live face detection on every frame.

## Tren Twins giveaway trailer (`youngla_tren.py`) – second brief, `TREN_CAPTIONS.md`
Footage: `footage/tren.mp4` from the brief's Dropbox link, converted to `footage/tren_1080.mp4` cropped just above
its burned-in subtitles (`crop=3104:1746:0:60,scale=1920:1080`). Captions use the subtitles' own text with
timings read off the subtitle on/off points (`transcripts/tren_words.json`). Same style as batches 6/7, with
captions in one fixed spot under the video (balanced 2-3 word phrases), lively `[excited] [high voice]` narrator,
and "Say Goodbye" ~6 dB louder than batch 7. Clips: `22_tren_lie_in_it`, `23_tren_feels_like`, `24_tren_mexico`; set 2: `25_tren_supercut`, `26_tren_caved`, `27_tren_nap`.

## Mixed set across both briefs (`youngla_mix.py`)
Five clips in the Tren Twins style, each using ONLY its own campaign's footage: `28_tren_gotta_do_it`,
`29_tren_cant_believe` (Tren Twins brief, giveaway hook on screen) and `30_fs_30_seconds`, `31_fs_sound_guy`,
`32_fs_not_tryna_brag` (fashion show brief). Captions/IG captions: `TREN_CAPTIONS.md` and `YOUNGLA_CAPTIONS.md`.
