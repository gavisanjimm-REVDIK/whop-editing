# BOXABL Phase 2 clips (ClipFarm brief)

Clips cut **only** from the 2 official videos ("Boxabl Factory Update (Phase 2)" and "Boxabl Phase 2 Update").
They come from the brief's WeTransfer link and are saved to `footage/boxabl_phase2_{1,2}.mp4`, which is git-ignored.
The WeTransfer files have no audio, so each clip uses an AI voiceover (ElevenLabs, voice "James").

**Style:** modeled on the reference short, without copying it.
- **Framing:** a blurred, zoomed copy of the footage fills the frame, and the sharp footage sits in a center band.
- **Title:** a two-line title stays pinned on top, with keywords color-coded and emojis at the end.
- **Captions:** the voiceover is captioned one word at a time. The timings come from a local Whisper model, and "Boxable" is forced to BOXABL.
- **Motion:** bobbing red arrows point at the house, every cut gets a zoom punch, and some cuts get a white flash with a whoosh and boom.
- **Music:** a dark, low drone with a trap beat at about 97 BPM. It's synthesized, so it's royalty-free.
- **Branding:** the BOXABL logo sits under the band.

| Clip | Output | Topic |
|---|---|---|
| `casita` | `out/01_casita_unfolds.mp4` (23 s) | Folded on a truck, then unfolds, then the interior tour |
| `phase2` | `out/02_phase2_two_story.mp4` (23 s) | Two-story Phase 2 demonstration unit |
| `crane` | `out/03_crane_delivery.mp4` (20.5 s) | Craned into a backyard, then unfolds |

```bash
python3 clipper.py all      # or: casita | phase2 | crane
```

The shot lists are in `clips.py`. The voiceovers and word timings are in `vo/`.
These parts of the source videos are deliberately not used:
- the securities disclaimer
- the NYSE/theCUBE interview
- the investor-numbers card
- the sign-up form
- shots showing other brands

Titles and captions are in `YOUTUBE_CAPTIONS.md`.
