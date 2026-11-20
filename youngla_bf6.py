#!/usr/bin/env python3
"""YoungLA Black Friday – batch 6, modelled on the "Clip The Pod" reference (podstyle.py):
AI narrator intro (ElevenLabs, "Ethan – Energetic YouTube Narrator") over quick b-roll with a red arrow,
then the real conversation; big colour-cycling one-word captions; an original ElevenLabs trap beat
(G minor, 123 BPM – same feel as the reference's bed) ducked under speech; riser + 808 on the punchline.

  16_skully_debate    "you don't wear no skully, dude" ... "that's what I thought"
  17_can_i_have_some  Skyline GT-R R34 ("Godzilla") ... "can I have some?" "No."
  18_hype_man         "that was me, I'm the hype man" ... the all-black Lambo ... "Disgusting."

python3 youngla_bf6.py [name ...] [--preview]
"""
import json
import os
import sys

import podstyle
import refstyle
import youngla_bf
from editor import FIXES, Fx, Shot, Sound, Video, layout_timeline
from youngla_bf2 import ROOT, at, mapper, speech_shots
from youngla_bf3 import source as source3

VO_DIR = os.path.join(ROOT, "assets", "vo")
BEAT = os.path.join(ROOT, "assets", "music", "elevenlabs_trap_beat.mp3")
MEDIUM5 = os.path.join(ROOT, "transcripts", "youngla_bvm_medium_words5.json")
WHITE = refstyle.WHITE
VO_START = 0.15


def source():
    src = source3()
    youngla_bf.fix_transcript(src)                       # the skully lines, checked twice
    med = json.load(open(MEDIUM5))
    merged = []
    for s, e, w in med["347-393"]:
        if merged and w[:1] in ",-&%":
            ps, pe, pw = merged.pop()
            merged.append((ps, e, pw + w))
            continue
        merged.append((s, e, w.replace("Luca", "Lukey")))
    src.override(347.5, 391.0, [m for m in merged if m[0] < 391.0])
    return src


def vo_words(name):
    ws = json.load(open(os.path.join(VO_DIR, "vo_words.json")))[name]
    out = []
    for a, b, w in ws:
        if out and w.startswith("-"):
            pa, pb, pw = out.pop()
            out.append((pa, b + VO_START, pw + w))
            continue
        w = {"scully,": "skully,", "scully": "skully", "skyline": "Skyline"}.get(w, w)
        out.append((a + VO_START, b + VO_START, w))
    return out


def intro(broll, vo_name):
    """b-roll shots (picture only, source audio dipped) under the narrator line."""
    shots = []
    for a, b, *kw in broll:
        sh = Shot(a, b, layout=(kw[0] if kw else "auto"), cx=(kw[1] if len(kw) > 1 else 960),
                  zoom=(kw[2] if len(kw) > 2 else 1.0), gain=0.12, captions=False)
        sh.lock = len(kw) > 1                            # an explicit cx means: stay on that person
        shots.append(sh)
    return shots


def finish(v, vo_name, n_intro):
    v.extra_audio = [(VO_START, os.path.join(VO_DIR, vo_name + ".mp3"), 1.0)]
    v.vo_words = [(a, b, w) for a, b, w in vo_words(vo_name)]
    v.bleep = "mute"
    v.music = dict(file=BEAT, offset=0.0, gain_db=-11, open_db=-6, stops=[])
    t_conv = at(v, n_intro)
    v.fx.append(Fx(t_conv, "flash", 0.3, 0.6))
    v.sounds += [Sound(0.0, "boom", 0.6), Sound(t_conv - 0.2, "whoosh", 0.45)]
    for i in range(1, n_intro):                          # quick cuts land on a subtle punch
        v.fx.append(Fx(at(v, i), "punch", 0.25, 1.03))


def punchline(v, t, emoji, out_emojis):
    v.sounds += [Sound(t - 1.35, "riser", 0.5), Sound(t, "boom", 0.9)]
    v.fx += [Fx(t, "punch", 0.6, 1.07), Fx(t, "shake", 0.3, 0.5)]
    out_emojis.append((t + 0.05, emoji, 1.4))


# --------------------------------------------------------------------------- 16

def skully_debate(src):
    broll = [(164.30, 165.10), (166.20, 167.00), (168.00, 168.80), (170.00, 170.80), (171.60, 172.40),
             (162.60, 163.40), (169.10, 169.80)]
    shots = intro(broll, "vo_skully") + speech_shots(src, 178.55, 192.15, zooms=(1.0, 1.08))
    v = Video(shots=shots)
    n = len(broll)
    T = mapper(v, n)
    finish(v, "vo_skully", n)
    emojis = []
    punchline(v, T(186.85), "😳", emojis)                 # "you don't wear no skully, dude"
    punchline(v, T(191.54), "💀", emojis)                 # "that's what I thought"
    return v, [("the skully debate got personal", WHITE), ("💀", WHITE)], emojis


# --------------------------------------------------------------------------- 17

def can_i_have_some(src):
    broll = [(343.70, 344.90, "crop", 1400), (162.10, 163.00), (174.00, 174.80), (248.10, 248.90),
             (1072.00, 1072.80), (345.00, 345.90, "crop", 1400), (249.00, 249.70)]
    shots = (intro(broll, "vo_skyline") + speech_shots(src, 349.40, 360.30, zooms=(1.0, 1.08))
             + speech_shots(src, 385.60, 391.80, zooms=(1.0, 1.08)))
    v = Video(shots=shots)
    n = len(broll)
    T = mapper(v, n)
    finish(v, "vo_skyline", n)
    emojis = []
    v.sounds.append(Sound(T(358.5), "pop", 0.6))          # "Godzilla."
    punchline(v, T(390.9), "😭", emojis)                  # "Can I have some?" "No."
    return v, [("he really asked for some of the million", WHITE), ("😭", WHITE)], emojis


# --------------------------------------------------------------------------- 18

def hype_man(src):
    broll = [(414.00, 414.80), (421.20, 422.00), (423.20, 424.00), (425.30, 426.00), (430.20, 431.00),
             (431.50, 432.30), (436.20, 437.00), (437.30, 438.10)]
    shots = intro(broll, "vo_hypeman") + speech_shots(src, 544.85, 561.95, zooms=(1.0, 1.08))
    v = Video(shots=shots)
    n = len(broll)
    T = mapper(v, n)
    finish(v, "vo_hypeman", n)
    emojis = []
    v.sounds.append(Sound(T(552.36), "pop", 0.6))         # "I'm the hype man."
    punchline(v, T(560.64), "😂", emojis)                 # "Disgusting."
    return v, [("he became his personal hype man", WHITE), ("😂", WHITE)], emojis


VIDEOS = {"16_skully_debate": skully_debate, "17_can_i_have_some": can_i_have_some, "18_hype_man": hype_man}


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
