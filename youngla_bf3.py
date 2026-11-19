#!/usr/bin/env python3
"""YoungLA Black Friday – batch 3. Minimal: hook on top, footage in the middle, captions underneath,
background music, and one sound on the punchline. No labels, tints, flashes or rewinds. Hard cuts on
sentence ends only.

  07_three_hours_late   shows up 3 hours late, goes straight to the bathroom   – Pixel Peeker Polka (faster)
  08_already_handsome   the "safe" million-dollar answers... then the real one  – Carefree
  09_disney_villain     "he kind of looks like a supervillain" (while he walks) – Scheming Weasel (faster)

python3 youngla_bf3.py [name ...] [--preview] [--qa]
"""
import json
import os
import sys

import framed
from editor import FIXES, H, Fx, Shot, Sound, Video
from youngla_bf2 import (BLACK, GOLD, GREEN, MUSIC, PINK, ROOT, at, hook, load_source, mapper,
                         speech_shots)

MEDIUM3 = os.path.join(ROOT, "transcripts", "youngla_bvm_medium_words3.json")
Y_CAP_MID = 1740 / H          # captions centred in the bottom band (nothing else lives there)
BLUE = (90, 170, 255)


def caption_style(hl):
    return dict(font="montserrat", size=84, hl=hl, y=Y_CAP_MID, words=3, stroke_w=9, width=18)


def source():
    src = load_source()
    med = json.load(open(MEDIUM3))
    fixes = dict(FIXES, hail="pay")
    for key in ("500-540", "568-628"):              # the accurate words for these two scenes
        a, b = (float(x) for x in key.split("-"))
        merged = []
        for s, e, w in med[key]:
            if merged and (w.startswith(",") or w.startswith("-") or w == "%"):
                ps, pe, pw = merged.pop()
                merged.append((ps, e, pw + w))
                continue
            k = w.strip(" ,.?!").lower()
            merged.append((s, e, fixes[k] if k == "hail" else
                           (w.lower().replace(k, fixes[k]) if k in fixes else w)))
        src.override(a + 1.5, b - 1.5, merged)
    # two overlapping lines in the first transcript: "That's a good description." / "He looks like..."
    fixed = []
    for ws, we, w in src.words:
        if 819.7 <= ws <= 820.04 and w == "description.":
            ws, we = 820.02, 820.03
        fixed.append((ws, we, w))
    src.words = sorted(fixed)
    return src


def music(v, track, stops=()):
    v.music = dict(file=os.path.join(MUSIC, track), offset=0.0, gain_db=-18, open_db=-10, stops=list(stops))


# --------------------------------------------------------------------------- 07

def three_hours_late(src):
    v = Video(shots=speech_shots(src, 503.50, 536.75, zooms=(1.0,)), caption_style=caption_style(GOLD))
    T = mapper(v, 0)
    hook(v, "HE SHOWED UP 3 HOURS LATE AND WENT STRAIGHT TO THE BATHROOM")
    v.emph = {"three": GOLD, "hours": GOLD, "late": GOLD, "pee": GOLD, "bathroom": GOLD}
    v.sounds.append(Sound(T(507.1), "boom", 0.55))
    music(v, "Pixel_Peeker_Polka_-_faster.mp3")
    return v, GOLD


# --------------------------------------------------------------------------- 08

def already_handsome(src):
    shots = []
    for a, b, keep in [(570.00, 577.95, ()), (588.05, 589.55, ()), (590.60, 598.30, ()), (602.60, 605.50, ()),
                       (605.95, 608.15, ()), (608.75, 614.60, [(611.4, 613.8)]), (619.30, 620.30, ())]:
        shots += speech_shots(src, a, b, keep=keep, zooms=(1.0,))
    v = Video(shots=shots, caption_style=caption_style(GREEN))
    T = mapper(v, 0)
    hook(v, "WE ASKED WHAT HE'D BUY WITH A MILLION DOLLARS...")
    v.emph = {"million": GREEN, "mature": GREEN, "safe": GREEN, "g-wagon": GOLD, "handsome": GOLD}
    v.sounds.append(Sound(T(614.06), "shimmer", 0.8))
    v.fx.append(Fx(T(614.06), "punch", 0.5, 1.05))
    music(v, "Carefree.mp3", stops=[(T(611.6), T(613.75))])      # beat of silence before the punchline
    return v, GREEN


# --------------------------------------------------------------------------- 09

def disney_villain(src):
    shots = speech_shots(src, 801.95, 804.65, zooms=(1.0,)) + speech_shots(src, 807.95, 824.95, zooms=(1.0,))
    v = Video(shots=shots, caption_style=caption_style(BLUE))
    T = mapper(v, 0)
    hook(v, "WHEN YOUR BOY SAYS YOU LOOK LIKE A DISNEY VILLAIN")
    v.emph = {"supervillain": BLUE, "villain": BLUE, "disney": BLUE, "antagonist": BLUE, "evil": BLUE}
    v.sounds.append(Sound(T(815.6), "boom", 0.6))
    v.fx.append(Fx(T(815.6), "punch", 0.5, 1.05))
    music(v, "Scheming_Weasel_faster.mp3")
    return v, BLUE


VIDEOS = {"07_three_hours_late": three_hours_late, "08_already_handsome": already_handsome,
          "09_disney_villain": disney_villain}


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or list(VIDEOS)
    src = source()
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    for n in names:
        out = os.path.join(ROOT, "out", n + ".mp4")
        v, accent = VIDEOS[n](src)
        if "--no-music" in sys.argv:      # for adding a trending sound in the app instead
            v.music = None
            os.makedirs(os.path.join(ROOT, "out", "nomusic"), exist_ok=True)
            out = os.path.join(ROOT, "out", "nomusic", n + ".mp4")
        if "--dry" in sys.argv:
            print(n, round(at(v, len(v.shots)), 1), [(round(s.src_in, 2), round(s.src_out, 2)) for s in v.shots])
            continue
        d = framed.render(v, src, out, preview="--preview" in sys.argv, accent=accent)
        print(f"wrote {out} ({d:.1f}s, {len(v.shots)} shots)")
        if "--qa" in sys.argv:
            nf, issues = framed.qa(out)
            print(f"QA {n}: {nf} face detections, {len(issues)} issues")
            for i in issues[:20]:
                print("   ", i)


if __name__ == "__main__":
    main()
