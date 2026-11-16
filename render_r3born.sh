#!/usr/bin/env bash
# Renders the 5 HardScope R3born Ep. 2 Shorts from footage/ep2.mp4 into out/r3born/
# (download Ep. 2 from the campaign's frame.io link as footage/ep2.mp4 first)
set -euo pipefail
cd "$(dirname "$0")"
E=footage/ep2.mp4
T=footage/ep2_transcript.json   # full-episode Whisper transcript (word timestamps)
O=out/r3born
mkdir -p "$O"

# 1. Wax finale: hook on the rip, rewind to the setup, end on "I'm f***ing hurt" (loops back to the rip)
python3 make_short.py --input $E --transcript $T --out $O/01_wax.mp4 \
  --hook "N3on lost the bet|and got *WAXED* 💀" \
  --seg 759.3-762.3@1.12 --seg 743.1-748.45 --seg 748.5-756.2@1.12 --seg 762.9-770.95

# 2. Pilates suffering: hook on "Did you just fart?", end on "you're not even doing s***" -> loops into "oh s***"
python3 make_short.py --input $E --transcript $T --out $O/02_pilates.mp4 \
  --hook "N3on vs Pilates went|*HORRIBLY* wrong 💀" \
  --seg 165.55-169.85 --seg 113.9-116.4@1.3:0.65:0.3 --seg 132.1-139.3 \
  --seg 140.9-143.5@1.3:0.5:0.3 --seg 147.85-149.1@1.12 --seg 156.45-160.85

# 3. Pole handstand: opens on the roast, ends on "I did it!"
python3 make_short.py --input $E --transcript $T --out $O/03_pole.mp4 \
  --hook "She *ROASTED* N3on|mid handstand 💀" \
  --seg 385.95-393.9 --seg 397.35-405.0@1.12 --seg 408.0-412.65

# 4. Losing on calories: scoreboard -> excuses -> "I'm like LeBron James" (cuts before the result)
python3 make_short.py --input $E --transcript $T --out $O/04_calories.mp4 \
  --hook "N3on is getting *CRUSHED*|in women's workouts 💀" --cap-y 0.4 \
  --seg 436.0-442.1@1.0:0.35 --seg 442.25-445.3@1.12:0.35 --seg 448.15-449.85@1.0:0.4 \
  --seg 450.15-453.35 --seg 453.55-455.15@1.3:0.5:0.3 --seg 455.15-457.55@1.0:0.35

# 5. Pilates was invented in prison: ends on "I'm not losing" -> "Can you go slower please?"
python3 make_short.py --input $E --transcript $T --out $O/05_prison.mp4 \
  --hook "Pilates was invented|in *PRISON*?? 💀" \
  --seg 78.5-84.15@1.0:0.55 --seg 61.35-62.4@1.12:0.6 --seg 63.2-66.75 \
  --seg 89.9-94.0@1.12:0.6 --seg 106.05-107.0@1.15
