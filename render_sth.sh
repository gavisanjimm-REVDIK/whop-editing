#!/usr/bin/env bash
# STRANGER THAN HEAVEN Act 2 Story Trailer clips (SEGA campaign).
# Footage: footage/sth_trailer.mp4 = STH_Kure_Story_Trailer.mp4 from the official Frame.io folder (4K H.264 transcode).
set -euo pipefail
cd "$(dirname "$0")"
T=footage/sth_trailer.mp4
STH=(--logo assets/sth-logo.png --logo-width 300 --tagline "PRE-ORDER NOW")

# Bathhouse back-tattoo reveal, cut on the trailer's own shot changes (1:58.45 - 2:17.98).
[ "${1:-}" = 2 ] || python3 make_clip.py --input $T --seg 118.45-137.98 "${STH[@]}" \
  --text "STRANGER THAN HEAVEN is making me want to join the Yakuza." --out out/sth_01_yakuza_tattoo.mp4

# Combat: car chase, train tunnel, dojo brawl (2:25.68-2:44.68), then the charge + explosion (2:49.38-2:55.30).
# Skips the blade-on-board shot in between. Short audio crossfade so the score doesn't jump at the join.
python3 make_clip.py --input $T --seg 145.68-164.68 --seg 169.38-175.30 --audio-xfade 0.35 "${STH[@]}" \
  --text "The fights in|*STRANGER THAN HEAVEN*|look absolutely brutal." --out out/sth_02_combat.mp4
