#!/usr/bin/env bash
# Downloads the background tracks (Kevin MacLeod, incompetech.com, CC BY 4.0) into assets/music/
set -euo pipefail
cd "$(dirname "$0")/assets/music"
for t in "Sneaky Snitch" "Fluffing a Duck" "Monkeys Spinning Monkeys" "Investigations" "Local Forecast - Elevator" "Wallpaper"; do
  f="$(echo "$t" | tr ' ' '_').mp3"
  [ -f "$f" ] || curl -fsSL -o "$f" "https://incompetech.com/music/royalty-free/mp3-royaltyfree/$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$t").mp3"
done
ls -la
