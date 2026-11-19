#!/usr/bin/env bash
# Renders the Football Manager 27 clips from footage/fm27/ into out/fm27/
# Footage = the creator videos from the campaign content folder (see fm27/README.md).
set -euo pipefail
cd "$(dirname "$0")/.."
F=footage/fm27
O=out/fm27
M="python3 fm27/make_clip.py"

# --- Kacee Anderson (@chi_kacee) ---
$M --input $F/kacee1_angelcity.mov --seg 0-29.6 \
  --text "A day in the life of an Angel City FC manager in FM27" --out $O/01_kacee_day_in_the_life.mp4
$M --input $F/kacee1_angelcity.mov --seg 29.8-53.3 \
  --text "Angel City FC vs Washington Spirit on FM27 match day" --out $O/02_kacee_match_day.mp4
$M --input $F/kacee2_van.mov --seg 0-23.6 \
  --text "Day one as manager and the star player already wants to leave" --out $O/03_kacee_star_player.mp4
$M --input $F/kacee2_van.mov --seg 38.6-66.0 \
  --text "Trying to keep the star player happy in Football Manager 27" --out $O/04_kacee_first_match.mp4

# --- NickRTFM (@nickrtfm / @NickRTFM) ---
$M --input $F/nick_ad1.mp4 --seg 0-18.75 \
  --text "Football Manager 27 has a new mode called Shuffle Draft" --out $O/05_nick_shuffle_draft.mp4
$M --input $F/nick_ad1.mp4 --seg 52.55-66.62 \
  --text "Shuffle Draft is FM27 for when you don't have time for a full save" --out $O/06_nick_quick_mode.mp4
$M --input $F/nick_ad1.mp4 --seg 81.15-97.55 \
  --text "Drafting Jude Bellingham in FM27 Shuffle Draft" --out $O/07_nick_bellingham.mp4
$M --input $F/nick_ad1.mp4 --seg 113.15-130.95 \
  --text "\"The best thing Football Manager has ever done\"" --out $O/08_nick_best_mode.mp4

# --- El Soccer Guy (handle not listed in the brief yet) ---
$M --input $F/elsoccer_angelcity.mov --seg 0-24.5 \
  --text "Hiring staff and negotiating contracts on day one in FM27" --out $O/09_elsoccer_angel_city.mp4
$M --input $F/elsoccer_clubamerica.mov --seg 0-28.0 \
  --text "Taking charge of Club América in Football Manager 27" --out $O/10_elsoccer_club_america.mp4
