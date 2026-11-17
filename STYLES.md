# Editing styles

## edit1 — white post card (`make_edit1.py`)
Reference: the creator-style clip you sent (white card, avatar + handle, caption, tall footage, small grey label).
Example output: `out/sth_03_kure_edit1.mp4` (render with `./render_sth.sh 3e`; handle defaults to @Clipsterssz,
set `AVATAR=path/to/pfp.png` to use a profile picture instead of the initial circle).

- 1080x1920 **white** canvas, Poppins font (`assets/fonts`, SIL OFL).
- Header: round avatar (`--avatar pic.jpg`, or a black initial circle) + bold `@handle` (`--handle`).
- Hook as a plain, left-aligned black caption under the handle (`--text`, `|` forces a line break).
  Say plainly that it's a video game and name it, e.g. "This upcoming video game set in 1929 Japan looks unreal.
  It's called STRANGER THAN HEAVEN". No claims about other games, no made-up facts (campaign rules).
- **Shorts/TikTok/Reels-safe:** footage box 900x980 so the box, subtitles and label all end above the bottom
  title bar (~y 1500), and subtitles stay narrower than the box so the right-side buttons don't cover them.
- Footage in the box. Each shot is cropped to follow its subject: `--seg START-END@XC`
  (XC = horizontal centre 0..1). Shots too wide to crop (title cards) use `@fit`: full frame over a blurred fill.
  Letterbox bars are detected and cropped off automatically.
- The trailer's burned-in subtitles are cropped off and the **official lines are re-set** inside the box
  (`--sub "START-END|line"`, output seconds, copy the trailer's text exactly).
- Official logo as a watermark, top-right of the footage (white logo, so it can't sit on the white card).
- Small grey bold label centred under the footage (`--label`, e.g. "Act 2 Story Trailer").
- Original audio only, cuts on the trailer's own shot changes, 0.35 s audio crossfade at real jumps.

## yellowhook — black canvas, yellow game name (`make_clip.py --style yellowhook`)
Reference: `out/sth_02_combat.mp4`. Black canvas, 3-line bold hook with the game name alone on its line
in logo yellow (`|` line breaks, `*stars*` for yellow), 16:9 footage, STH logo + PRE-ORDER NOW below.
