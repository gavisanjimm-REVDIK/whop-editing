# Editing styles

## edit1 — white post card (`make_edit1.py`)
Reference: the creator-style clip you sent (white card, avatar + handle, caption, tall footage, small grey label).
Example output: `out/sth_03_kure_edit1.mp4` (render with `./render_sth.sh 3e`; handle @Clipsterssz, avatar `assets/clipsterssz-logo.png`;
override with `HANDLE=` / `AVATAR=`).

- 1080x1920 **white** canvas, Poppins font (`assets/fonts`, SIL OFL).
- Header: round avatar (`--avatar pic.jpg`, or a black initial circle) + bold `@handle` (`--handle`).
- Hook as a plain, left-aligned black caption under the handle (`--text`, `|` forces a line break).
  **One sentence, no game title** (the logo watermark names it), and make clear it is a video game,
  e.g. "This upcoming video game set in 1929 Japan looks unreal." No claims about other games or made-up facts.
- The whole block (header, caption, footage, label) is **centred vertically** on the canvas.
- Tall footage box (900x1160). **Shorts/TikTok/Reels-safe subtitles:** they always end at y 1440, above the
  bottom title bar, and stay narrower than the box so the right-side buttons don't cover them.
- Footage in the box. Each shot is cropped to follow its subject: `--seg START-END@XC`
  (XC = horizontal centre 0..1). Shots too wide to crop (title cards) use `@fit`: full frame over a blurred fill.
  Letterbox bars are detected and cropped off automatically.
- The trailer's burned-in subtitles are cropped off and the **official lines are re-set** inside the box
  (`--sub "START-END|line"`, output seconds, copy the trailer's text exactly).
- Official logo as a watermark, top-right of the footage (white logo, so it can't sit on the white card).
- Small grey bold label centred under the footage (`--label`, e.g. "Act 2 Story Trailer").
- Original audio only, cuts on the trailer's own shot changes, 0.35 s audio crossfade at real jumps.

## edit2 — black canvas, condensed hook (`make_clip.py --style edit2`)
Inspired by a creator Short (black canvas, tall condensed caption, zoomed footage, big logo), not copied.
Example output: `out/sth_04_ceremony.mp4` (`./render_sth.sh 4`).

- Black 1080x1920 canvas. Hook in **Oswald Bold** (`assets/fonts`, SIL OFL), white, centred, one sentence,
  no game title, one keyword in logo yellow via `*stars*`, `|` for the line break.
- Footage: letterbox bars detected and removed, then zoomed 1.33x so it fills the width with the sides cropped.
  The trailer's own subtitles stay (they sit inside the crop).
- Big official STH logo (250 px) under the footage, no tagline.
- Layout shifted up 120 px so the logo ends above the Shorts/TikTok/Reels title bar.
- Original audio only; 0.35 s audio crossfade if several `--seg` pieces are joined.

## yellowhook — black canvas, yellow game name (`make_clip.py --style yellowhook`)
Reference: `out/sth_02_combat.mp4`. Black canvas, 3-line bold hook with the game name alone on its line
in logo yellow (`|` line breaks, `*stars*` for yellow), 16:9 footage, STH logo + PRE-ORDER NOW below.
