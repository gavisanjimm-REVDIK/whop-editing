#!/usr/bin/env python3
"""YoungLA Black Friday – batch 7, same "Clip The Pod" style as batch 6 (podstyle.py) but:
  * the narrator (ElevenLabs "Ethan") is pitched up ~4 semitones, timing unchanged
  * every clip uses the user's "Say Goodbye" track, sped up 1.2x (higher pitch, ~144 BPM), kept low under speech

  19_late_bathroom   shows up three hours late... "shows up and directly goes to the bathroom"
  20_villain_walk    "he kind of looks like a supervillain... some Disney villain"
  21_aura_midsection "you get goosebumps"... "I felt it in my midsection"... "head, shoulders, knees and toes"

The track is the user's own upload and is not committed (assets/music/*.mp3 is git-ignored).
python3 youngla_bf7.py [name ...] [--preview]
"""
import os
import sys

import podstyle
import refstyle
from editor import Video, layout_timeline
from youngla_bf2 import ROOT, at, mapper, speech_shots
from youngla_bf6 import finish, intro, punchline, source, vo_words

SONG = os.path.join(ROOT, "assets", "music", "say_goodbye_highpitch.mp3")
podstyle.EMOJI_ON_TOP = True
WHITE = refstyle.WHITE


def song(v):
    # quieter than batch 6: ~-21 dB under speech, ~-14 dB in the gaps, so it never fights the dialogue
    v.music = dict(file=SONG, offset=1.0, gain_db=-21, open_db=-14, stops=[])


def conv(src, parts):
    out = []
    for a, b in parts:
        out += speech_shots(src, a, b, zooms=(1.0, 1.08))
    return out


# --------------------------------------------------------------------------- 19

def late_bathroom(src):
    broll = [(520.00, 520.70), (525.00, 525.80), (527.00, 527.80), (529.50, 530.30), (531.00, 531.80),
             (533.00, 533.80), (534.50, 535.30), (536.00, 536.80)]
    shots = intro(broll, "vo_late") + conv(src, [(503.50, 510.10), (518.85, 532.75)])
    v = Video(shots=shots)
    n = len(broll)
    T = mapper(v, n)
    finish(v, "vo_late", n)
    song(v)
    emojis = []
    punchline(v, T(526.98), "💀", emojis)                 # "shows up and directly goes to the bathroom"
    return v, [("3 hours late and the first stop is the bathroom", WHITE), ("😭", WHITE)], emojis


# --------------------------------------------------------------------------- 20

def villain_walk(src):
    broll = [(825.00, 825.90), (825.90, 826.80), (826.80, 827.70), (827.70, 828.60), (806.20, 807.05),
             (807.05, 807.90)]
    shots = intro(broll, "vo_villain") + conv(src, [(801.95, 804.65), (807.95, 824.95)])
    v = Video(shots=shots)
    n = len(broll)
    T = mapper(v, n)
    finish(v, "vo_villain", n)
    song(v)
    emojis = []
    punchline(v, T(815.6), "😳", emojis)                  # "he kind of looks like a supervillain"
    punchline(v, T(820.48), "💀", emojis)                 # "the antagonist in a really evil story"
    return v, [("his boy really called him a disney villain", WHITE), ("💀", WHITE)], emojis


# --------------------------------------------------------------------------- 21

def aura_midsection(src):
    broll = [(413.30, 414.10), (414.20, 415.00), (419.60, 420.40), (421.00, 421.80), (422.00, 422.80),
             (423.20, 424.00), (425.30, 426.00)]
    shots = intro(broll, "vo_aura") + conv(src, [(415.40, 419.52), (427.90, 432.54), (433.32, 445.45)])
    v = Video(shots=shots)
    n = len(broll)
    T = mapper(v, n)
    finish(v, "vo_aura", n)
    v.vo_words = [(a, b, "hosts" if w == "host" else w) for a, b, w in v.vo_words]
    song(v)
    emojis = []
    emojis.append((T(439.06), "😳", 1.2))                 # "...in my midsection"
    punchline(v, T(443.74), "😭", emojis)                 # "head, shoulders, knees and toes"
    return v, [("the aura reached his midsection", WHITE), ("😭", WHITE)], emojis


VIDEOS = {"19_late_bathroom": late_bathroom, "20_villain_walk": villain_walk, "21_aura_midsection": aura_midsection}


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or list(VIDEOS)
    src = source()
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    for n in names:
        v, hook, emojis = VIDEOS[n](src)
        out = os.path.join(ROOT, "out", n + ".mp4")
        if "--dry" in sys.argv:
            layout_timeline(v)
            print(n, round(at(v, len(v.shots)), 1), [(round(s.src_in, 2), round(s.src_out, 2)) for s in v.shots])
            print("   ", " ".join(w for _, _, w, _ in podstyle.track_words(v, src)))
            continue
        d, moved, placed, hb = podstyle.render(v, src, out, hook, emojis, preview="--preview" in sys.argv)
        nf, hits = refstyle.qa(out, placed, hb)
        print(f"wrote {out} ({d:.1f}s, {len(v.shots)} shots) – captions moved off faces on {moved} frames; "
              f"QA: {nf} faces checked, {len(hits)} overlaps {hits[:5]}")


if __name__ == "__main__":
    main()
