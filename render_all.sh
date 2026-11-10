#!/usr/bin/env bash
# Renders the Season 1 clips from footage/trailer.mp4 into out/
set -euo pipefail
cd "$(dirname "$0")"
T=footage/trailer.mp4

python3 make_clip.py --input $T --seg 2-25.6 \
  --text "New Call of Duty: Warzone Season Comes to Korea in Season 1" --out out/01_korea.mp4

python3 make_clip.py --input $T --seg 28-38.5 --seg 101.5-111 \
  --text "Call of Duty: Warzone gets two new maps Hajin and Zodiac in Season 1" --out out/02_hajin_zodiac.mp4

python3 make_clip.py --input $T --seg 47-63 \
  --text "The new Call of Duty: Warzone look insane" --out out/03_combat.mp4

python3 make_clip.py --input $T --seg 120-135 \
  --text "Warzone Season 1 brings new gear to Hajin, like the Grabber Drone" --out out/04_new_gear.mp4
