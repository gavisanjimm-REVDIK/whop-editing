#!/usr/bin/env bash
# Renders the STRANGER THAN HEAVEN Act 2 clips from footage/sth_trailer.mp4 into out/sth/
# (STH_Kure_Story_Trailer.mp4 from the campaign's Frame.io folder).
set -euo pipefail
cd "$(dirname "$0")/.."
T=footage/sth_trailer.mp4
M="python3 sth/make_clip.py --input $T"

# Overall: gun-drawn opener, "Act 2 Story Trailer" card, the gang standoff (rating badge skipped)
$M --seg 5.4-26.3 \
  --text "STRANGER THAN HEAVEN’S|*AURA* IS INSANE." --out out/sth/01_aura.mp4

# Yakuza: the bow-to-the-boss initiation ceremony
$M --seg 32.5-46.9 \
  --text "CAN'T WAIT TO BE A BADASS *YAKUZA* IN|STRANGER THAN HEAVEN." --out out/sth/02_yakuza_ceremony.mp4

# Overall: "1929 KURE" title card into the streets of Kure
$M --seg 47.0-60.6 \
  --text "CAN'T WAIT TO EXPLORE *1929 KURE* IN|STRANGER THAN HEAVEN." --out out/sth/03_kure_1929.mp4

# Yakuza: back tattoo in the bathhouse
$M --seg 122.3-138.0 \
  --text "STRANGER THAN HEAVEN IS MAKING|ME WANT TO JOIN THE *YAKUZA*." --out out/sth/04_tattoo.mp4

# Combat: street fight, dojo brawl, chase and explosion (skips the bloodiest shots)
$M --seg 78.3-83.7 --seg 154.6-165.8 --seg 168.2-175.8 \
  --text "STRANGER THAN HEAVEN|LOOKS ABSOLUTELY *BRUTAL*." --out out/sth/05_brutal.mp4
