#!/usr/bin/env bash
# STRANGER THAN HEAVEN Act 2 Story Trailer clips (SEGA campaign).
# Footage: footage/sth_trailer.mp4 = STH_Kure_Story_Trailer.mp4 from the official Frame.io folder (4K H.264 transcode).
set -euo pipefail
cd "$(dirname "$0")"
T=footage/sth_trailer.mp4
STH=(--logo assets/sth-logo.png --logo-width 300 --tagline "PRE-ORDER NOW")

# Bathhouse back-tattoo reveal, cut on the trailer's own shot changes (1:58.45 - 2:17.98).
python3 make_clip.py --input $T --seg 118.45-137.98 "${STH[@]}" \
  --text "STRANGER THAN HEAVEN is making me want to join the Yakuza." --out out/sth_01_yakuza_tattoo.mp4
