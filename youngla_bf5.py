#!/usr/bin/env python3
"""YoungLA Black Friday – batch 5, reference style (refstyle.py). Three more fun moments.

  13_run_me_my_money   Togi's photoshoot: bald spot, retoucher, "Gary, run me my money"   – Sneaky Snitch
  14_not_tryna_brag    Marlon: "Calvin Klein, Burberry, H&M... I'm not even trying to brag" – Monkeys Spinning Monkeys
  15_jay_rates_dance   Lex hits a runway dance, Jay Cutler: "Urs could do it better"       – Pixel Peeker Polka (faster)

python3 youngla_bf5.py [name ...] [--preview] [--no-music] [--dry]
"""
import json
import os
import sys

import refstyle
from editor import FIXES, Fx, Shot, Sound
from youngla_bf2 import MUSIC, ROOT, at, mapper, speech_shots
from youngla_bf3 import source as source3
from youngla_bf4 import base, flash, music

RED, WHITE = refstyle.RED, refstyle.WHITE
MEDIUM4 = os.path.join(ROOT, "transcripts", "youngla_bvm_medium_words4.json")


def source():
    src = source3()
    med = json.load(open(MEDIUM4))
    fixes = dict(FIXES, ers="Urs")
    for key in ("40-96", "255-302", "636-706"):
        a, b = (float(x) for x in key.split("-"))
        merged = []
        for s, e, w in med[key]:
            if merged and (w[:1] in ",-&%"):
                ps, pe, pw = merged.pop()
                merged.append((ps, e, pw + w))
                continue
            k = w.strip(" ,.?!").lower()
            merged.append((s, e, w.replace(w.strip(" ,.?!"), fixes[k]) if k in fixes else w))
        src.override(a + 0.5, b - 0.5, merged)
    return src


# --------------------------------------------------------------------------- 13

def run_me_my_money(src):
    z = (1.0, 1.08)
    shots = (speech_shots(src, 46.20, 51.60, zooms=z)       # "I think this flash is gonna make my bald spot go..."
             + speech_shots(src, 51.60, 54.75, zooms=z)     # "you guys gotta edit this" "that's why we got a retoucher"
             + speech_shots(src, 67.84, 71.00, zooms=z)     # "you're about to go make some money" "I'm locked in bro"
             + speech_shots(src, 74.60, 79.60, zooms=z)     # "bro, none of them shots get used. there's no job." (laughs)
             + speech_shots(src, 81.20, 88.40, zooms=z))    # "I crushed that one" "you're good to go home" "Gary, run me my money"
    v = base(shots)
    T = mapper(v, 0)
    flash(v, T(74.8), 0.8, 0.3)
    v.fx += [Fx(T(49.5), "punch", 0.5, 1.05), Fx(T(87.3), "punch", 0.6, 1.06)]
    music(v, "Sneaky_Snitch.mp3")
    hook = [("one photoshoot later... \"gary, run me my", WHITE), ('MONEY"', RED), ("😭", WHITE)]
    return v, hook, [(T(49.5), "💀", 1.1), (T(87.35), "😭", 1.3)]


# --------------------------------------------------------------------------- 14

def not_tryna_brag(src):
    z = (1.0, 1.08)
    shots = (speech_shots(src, 258.85, 261.55, zooms=z)     # "we got a little special guest, Big Marlon."
             + speech_shots(src, 269.20, 275.20, zooms=z)   # "I was going top of my lungs, bro..."
             + speech_shots(src, 275.60, 285.78, zooms=z)   # Burberry? "no comparison... this belongs to me right here"
             + speech_shots(src, 287.50, 296.30, zooms=z))  # "Calvin Klein, Burberry, H&M." "I'm not even trying to brag"
    v = base(shots)
    T = mapper(v, 0)
    flash(v, at(v, 1), 0.7, 0.3)
    v.fx += [Fx(T(291.4), "punch", 0.5, 1.04), Fx(T(294.8), "punch", 0.6, 1.06)]
    v.sounds.append(Sound(T(294.1), "ka_ching", 0.35))
    music(v, "Monkeys_Spinning_Monkeys.mp3", stops=[(T(293.9), T(294.8))])
    hook = [('calvin klein, burberry, H&M... "i\'m not even trying to', WHITE), ('BRAG"', RED), ("😭", WHITE)]
    return v, hook, [(T(294.85), "😭", 1.3)]


# --------------------------------------------------------------------------- 15

def jay_rates_dance(src):
    z = (1.0, 1.08)
    shots = ([Shot(641.70, 653.40, layout="crop", zoom=1.35, cx=910, cy=540)]   # "hit a little dance move" -> the dance
             + speech_shots(src, 653.50, 668.90, zooms=z))  # "What'd you think, Jay?" -> "Urs could do it better" -> Germany
    v = base(shots)
    T = mapper(v, 0)
    flash(v, at(v, 1), 0.7, 0.3)
    v.fx += [Fx(T(655.5), "punch", 0.6, 1.06)]
    v.sounds.append(Sound(T(651.9), "boom", 0.5))
    music(v, "Pixel_Peeker_Polka_-_faster.mp3")
    hook = [("asked jay cutler to rate the runway", WHITE), ("DANCE", RED), ("😭", WHITE)]
    return v, hook, [(T(655.6), "😂", 1.3)]


VIDEOS = {"13_run_me_my_money": run_me_my_money, "14_not_tryna_brag": not_tryna_brag,
          "15_jay_rates_dance": jay_rates_dance}


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
            from editor import layout_timeline
            layout_timeline(v)
            print(n, round(at(v, len(v.shots)), 1), [(round(s.src_in, 2), round(s.src_out, 2)) for s in v.shots])
            print("   ", " ".join(w for _, _, w in refstyle.word_track(v, src)))
            continue
        d, moved, placed, hb = refstyle.render(v, src, out, hook, emojis, preview="--preview" in sys.argv)
        nf, hits = refstyle.qa(out, placed, hb)
        print(f"wrote {out} ({d:.1f}s, {len(v.shots)} shots) – captions moved off faces on {moved} frames; "
              f"QA: {nf} faces checked, {len(hits)} overlaps {hits[:5]}")


if __name__ == "__main__":
    main()
