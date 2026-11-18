#!/usr/bin/env bash
# STRANGER THAN HEAVEN Act 2 Story Trailer clips (SEGA campaign).
# Footage: footage/sth_trailer.mp4 = STH_Kure_Story_Trailer.mp4 from the official Frame.io folder (4K H.264 transcode).
# Usage: ./render_sth.sh          render all
#        ./render_sth.sh 3        render only clip 3
set -euo pipefail
cd "$(dirname "$0")"
T=footage/sth_trailer.mp4
ONLY=${1:-}
want() { [ -z "$ONLY" ] || [ "$ONLY" = "$1" ]; }

# 1 - Bathhouse back-tattoo reveal (1:58.45-2:17.98). Original plain-hook look.
want 1 && python3 make_clip.py --input $T --seg 118.45-137.98 \
  --logo assets/sth-logo.png --logo-width 300 --tagline "PRE-ORDER NOW" \
  --text "STRANGER THAN HEAVEN is making me want to join the Yakuza." --out out/sth_01_yakuza_tattoo.mp4

# 2 - yellowhook. Combat: car chase, train tunnel, dojo brawl (2:25.68-2:44.68), then charge + explosion
#     (2:49.38-2:55.30). Skips the blade-on-board shot in between.
want 2 && python3 make_clip.py --style yellowhook --input $T --seg 145.68-164.68 --seg 169.38-175.30 \
  --text "The fights in|*STRANGER THAN HEAVEN*|look absolutely brutal." --out out/sth_02_combat.mp4

# 3 - yellowhook. 1929 KURE title card -> debt collector -> city street -> gambling den -> Red Oni scuffle
#     (0:47.00-1:08.95). Ends before the profanity subtitle at 1:09.05.
want 3 && python3 make_clip.py --style yellowhook --input $T --seg 47.00-68.95 \
  --text "Can't wait to explore|1929 Kure in|*STRANGER THAN HEAVEN*" --out out/sth_03_kure.mp4

# 3e - edit1 (white post-card style, see STYLES.md). Same 1929 Kure section, crop follows each shot,
#      official subtitle lines re-set inside the frame. Set HANDLE (and AVATAR) to your page.
HANDLE=${HANDLE:-@Clipsterssz}
AVATAR=${AVATAR:-assets/clipsterssz-logo.png}
want 3e && python3 make_edit1.py --input $T --handle "$HANDLE" --avatar "$AVATAR" \
  --text "This upcoming video game set in|1929 Japan looks unreal." \
  --seg 47.00-50.30@fit --seg 50.30-55.70@0.53 --seg 55.70-58.05@0.51 --seg 58.05-61.20@0.53 \
  --seg 61.20-62.70@0.50 --seg 62.70-65.25@0.55 --seg 65.25-68.95@0.58 \
  --sub "2.45-5.35|...I'll say it again! Pay up!" \
  --sub "5.35-10.30|Tribute! Tribute! Ha! Yeah, you're real noble, ain't ya?" \
  --sub "10.30-13.80|Last I checked, all Boss Iwaki cares about is results..." \
  --sub "13.80-17.60|Debt collection, gambling hall watch—they're all yours." \
  --sub "18.00-21.90|Pretty much everyone in Hiroshima knows about the Red Oni of Iwaki by now!" \
  --out out/sth_03_kure_edit1.mp4

# 4 - edit2 (black canvas, condensed hook, zoomed footage, big logo; inspired by a creator Short, not copied).
#     Cornered -> "Hold it" -> boss's verdict -> bowing ceremony (0:26.28-0:47.00), official subs kept.
want 4 && python3 make_clip.py --style edit2 --input $T --seg 26.28-47.00 \
  --text "The *yakuza* scenes in this upcoming|video game look so intense." --out out/sth_04_ceremony.mp4
# 5 - edit1. "Special project" offer: boss -> recruiter -> "act like a spy?" -> cafe -> "This is Mako!"
#     (1:41.78-1:58.45). Crop follows the speaker in each shot; official lines re-set in frame.
want 5 && python3 make_edit1.py --input $T --handle "$HANDLE" --avatar "$AVATAR" \
  --text "This upcoming video game's story|just got way more interesting." \
  --seg 101.78-104.47@0.57 --seg 104.47-108.50@0.30 --seg 108.50-110.58@0.72 --seg 110.58-113.03@0.33 \
  --seg 113.03-116.70@0.55 --seg 116.70-118.45@0.55 \
  --sub "0.67-2.22|He'll do nicely." \
  --sub "3.17-7.97|You're in luck. The boss was lookin' for someone to handle a special project of his." \
  --sub "8.47-10.62|So, what, you want me to act like a spy?" \
  --sub "11.27-13.62|Allow me to introduce to you our newest friend." \
  --sub "13.62-16.67|This is Mako!" \
  --out out/sth_05_special_project.mp4
true
