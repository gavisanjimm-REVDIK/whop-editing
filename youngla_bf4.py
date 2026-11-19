#!/usr/bin/env python3
"""YoungLA Black Friday – batch 4, in the style of the reference clip the user shared (refstyle.py):
square footage on black, small lowercase hook with one red keyword + emoji, one-word captions,
light grade, one white backflash, one emoji pop, music under the original audio, swears cut out.

  10_handsome_ref   "what would you buy with a million?" ... "I'm already handsome."   – Carefree
  11_152k_ref       cold open "try negative 152,000" -> the million flat -> the taxes   – Fluffing a Duck
  12_robbies_car_ref Jay Cutler's first show, picks the SF90... that's Robbie's car     – Wallpaper

python3 youngla_bf4.py [name ...] [--preview] [--no-music]
"""
import os
import sys

import refstyle
from editor import Fx, Shot, Sound, Video
from youngla_bf2 import MUSIC, ROOT, at, mapper, speech_shots
from youngla_bf3 import source

RED, WHITE = refstyle.RED, refstyle.WHITE


def base(shots):
    v = Video(shots=shots)
    v.bleep = "mute"           # cut swears out, like the reference
    return v


def music(v, track, stops=()):
    v.music = dict(file=os.path.join(MUSIC, track), offset=0.0, gain_db=-16, open_db=-9, stops=list(stops))


def flash(v, t, amount=0.95, dur=0.35):
    v.fx.append(Fx(t, "flash", dur, amount))
    v.sounds.append(Sound(t - 0.25, "whoosh", 0.45))


# --------------------------------------------------------------------------- 10

def handsome(src):
    z = (1.0, 1.08)
    shots = (speech_shots(src, 570.00, 572.60, zooms=z)          # "if you won a million, first thing you're doing?"
             + speech_shots(src, 573.70, 578.00, zooms=z)        # "I don't think I'd change much." "just pay my bills"
             + speech_shots(src, 588.05, 589.55, zooms=z)        # "that was the mature answer."
             + speech_shots(src, 590.60, 595.95, zooms=z)        # "what are you buying first?" -> apartment, crib
             + speech_shots(src, 605.95, 608.20, zooms=z)        # "again... that was a safe answer."
             + [Shot(608.75, 612.00, layout="auto"),             # "what are you buying, bro?" "I already have a G-Wagon."
                Shot(613.30, 614.80, layout="auto", zoom=1.06)])  # "I'm already handsome."
    v = base(shots)
    T = mapper(v, 0)
    t_hand = T(613.74)
    flash(v, at(v, len(v.shots) - 1), 0.7, 0.3)
    v.fx.append(Fx(T(614.0), "punch", 0.6, 1.06))
    v.sounds.append(Sound(T(614.0), "shimmer", 0.5))
    music(v, "Carefree.mp3", stops=[(T(611.5), t_hand)])
    hook = [("asked what he'd buy with a million... he said he's", WHITE), ("ALREADY HANDSOME", RED), ("😭", WHITE)]
    return v, hook, [(T(614.05), "😭", 1.3)]


# --------------------------------------------------------------------------- 11

def negative_152k(src):
    z = (1.0, 1.08)
    shots = ([Shot(765.95, 768.95, layout="auto", zoom=1.05)]   # cold open: "try negative 152,000 at one point."
             + speech_shots(src, 751.15, 753.45, zooms=z)       # "can you just give me the money? just a million flat?"
             + speech_shots(src, 758.10, 765.25, zooms=z)       # the hypothetical: emptied / happened before / zero
             + speech_shots(src, 769.70, 779.90, zooms=z))      # "geez, did you get robbed?" -> the taxes -> "that is wild"
    v = base(shots)
    T = mapper(v, 1)
    flash(v, at(v, 1))                                          # backflash out of the cold open
    v.fx.append(Fx(T(762.02), "punch", 0.5, 1.05))
    v.sounds.append(Sound(2.0, "ding_red", 0.5))
    music(v, "Fluffing_a_Duck.mp3", stops=[(0, at(v, 1) - 0.05)])
    hook = [('"try negative $152,000"... bro was in the', WHITE), ("NEGATIVES", RED), ("💀", WHITE)]
    return v, hook, [(T(762.1), "💀", 1.3)]


# --------------------------------------------------------------------------- 12

def robbies_car(src):
    v = base(speech_shots(src, 1061.32, 1080.95, keep=[(1078.3, 1079.6)], zooms=(1.0, 1.08)))
    T = mapper(v, 0)
    flash(v, T(1069.6), 0.6, 0.3)
    v.fx.append(Fx(T(1079.6), "punch", 0.6, 1.06))
    v.sounds.append(Sound(T(1078.5), "record_scratch", 0.45))
    music(v, "Wallpaper.mp3", stops=[(T(1078.45), T(1079.5))])
    hook = [("jay cutler called dibs on someone else's", WHITE), ("FERRARI", RED), ("😭", WHITE)]
    return v, hook, [(T(1079.65), "😂", 1.3)]


VIDEOS = {"10_handsome_ref": handsome, "11_152k_ref": negative_152k, "12_robbies_car_ref": robbies_car}


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or list(VIDEOS)
    src = source()
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    for n in names:
        v, hook, emojis = VIDEOS[n](src)
        out = os.path.join(ROOT, "out", n + ".mp4")
        if "--no-music" in sys.argv:
            v.music = None
            os.makedirs(os.path.join(ROOT, "out", "nomusic"), exist_ok=True)
            out = os.path.join(ROOT, "out", "nomusic", n + ".mp4")
        if "--dry" in sys.argv:
            print(n, round(at(v, len(v.shots)), 1), [(round(s.src_in, 2), round(s.src_out, 2)) for s in v.shots])
            continue
        d, moved, placed, hb = refstyle.render(v, src, out, hook, emojis, preview="--preview" in sys.argv)
        nf, hits = refstyle.qa(out, placed, hb)
        print(f"wrote {out} ({d:.1f}s, {len(v.shots)} shots) – captions moved off faces on {moved} frames; "
              f"QA: {nf} faces checked, {len(hits)} overlaps {hits[:5]}")


if __name__ == "__main__":
    main()
