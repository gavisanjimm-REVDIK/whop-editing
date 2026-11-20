#!/usr/bin/env python3
"""Five clips across BOTH YoungLA briefs, same style as the Tren Twins sets (podstyle phrase captions,
lively high-pitched ElevenLabs narrator, sped-up "Say Goodbye" under the dialogue). Each clip uses ONLY its own
campaign's footage, so it stays eligible for that campaign:

  Tren Twins trailer (footage/tren_1080.mp4) – on-screen hook mentions the $1,000,000 giveaway
    28_tren_gotta_do_it     "I gotta do it." "Do what?" "I gotta do it, bro." -> the dive into the cash
    29_tren_cant_believe    "...what a million dollars feels like." "I can't believe they're giving it away"
  Fashion show (footage/bvm.mp4)
    30_fs_30_seconds        "Give me 30 seconds." ... walks out ... drives home
    31_fs_sound_guy         most aura goes to "the sound guy" ... "doesn't produce any himself"
    32_fs_not_tryna_brag    "Calvin Klein, Burberry, H&M." "I'm not even trying to brag"

python3 youngla_mix.py [name ...] [--preview] [--dry]
"""
import os
import sys

import podstyle
import refstyle
import youngla_tren as tren
from editor import Shot, Source, Video, layout_timeline
from youngla_bf2 import ROOT, at, mapper, speech_shots
from youngla_bf6 import intro, punchline
import youngla_bf
import youngla_bf5


def fashion_source():
    src = youngla_bf5.source()          # base + accurate transcripts (incl. 255-302 for Marlon)
    youngla_bf.fix_transcript(src)      # checked skully / runway lines
    return src

WHITE, RED = refstyle.WHITE, refstyle.RED


def conv(src, parts):
    out = []
    for a, b in parts:
        out += speech_shots(src, a, b, zooms=(1.0, 1.08))
    return out


def locked(a, b, cx, cy, zoom, **kw):
    s = Shot(a, b, layout="crop", cx=cx, cy=cy, zoom=zoom, **kw)
    s.lock = True
    return s


# --------------------------------------------------------------------------- Tren Twins

def tren_gotta_do_it(src):
    broll = [(34.30, 35.10), (37.60, 38.40), (45.20, 46.00), (29.00, 29.80), (52.00, 52.60), (42.40, 42.90)]
    v = Video(shots=intro(broll, "vo_tren_gotta") + [Shot(6.85, 16.45, layout="auto")])
    n = len(broll)
    T = mapper(v, n)
    tren.finish(v, "vo_tren_gotta", n, music_offset=75.0)
    emojis = []
    punchline(v, T(14.18), "😭", emojis)                     # the dive into the money
    hook = [("YoungLA is giving away", WHITE), ("$1,000,000", RED), ("and he HAD to do it", WHITE), ("😭", WHITE)]
    return v, hook, emojis


def tren_cant_believe(src):
    broll = [(2.60, 3.40), (4.30, 5.10), (11.00, 11.80), (19.60, 20.40), (22.40, 23.00), (9.50, 10.00)]
    v = Video(shots=intro(broll, "vo_tren_believe") + [Shot(31.15, 41.45, layout="auto")])
    n = len(broll)
    T = mapper(v, n)
    tren.finish(v, "vo_tren_believe", n, music_offset=10.0)
    emojis = []
    punchline(v, T(tren.word_t(src, "giving", 37.3)), "🤯", emojis)   # "...giving it away to someone"
    hook = [("YoungLA is giving away", WHITE), ("$1,000,000", RED), ("and even they can't believe it", WHITE),
            ("🤯", WHITE)]
    return v, hook, emojis


# --------------------------------------------------------------------------- fashion show

def fs_30_seconds(src):
    broll = [(52.00, 52.80), (57.00, 57.80), (76.60, 77.40), (83.50, 84.30)]
    shots = intro(broll, "vo_fs_30sec")
    # teaser of the car (cropped above the source's own burned-in captions)
    shots += [locked(329.50, 330.30, 1250, 420, 1.3, gain=0.12, captions=False),
              locked(335.00, 335.80, 1400, 400, 1.3, gain=0.12, captions=False)]
    n = len(shots)
    shots += conv(src, [(307.10, 314.25)])                                       # "...give me 30 seconds."
    shots += [Shot(314.25, 327.40, layout="auto", speed=2.6, audio="mute", captions=False)]   # walks out
    shots += [locked(327.50, 338.10, 1330, 420, 1.3)]                           # in the car
    shots += [locked(338.10, 342.60, 1000, 420, 1.15, speed=1.5, captions=False)]           # drives off
    v = Video(shots=shots)
    T = mapper(v, n)
    tren.finish(v, "vo_fs_30sec", n, music_offset=30.0)
    emojis = []
    punchline(v, T(329.5), "💀", emojis)                       # "I'm not getting paid to — be here"
    emojis.append((at(v, len(v.shots) - 1) + 0.2, "😭", 1.6))   # he actually drives off
    hook = [("he said \"give me 30 seconds\"...", WHITE), ("he never came back", RED), ("😭", WHITE)]
    return v, hook, emojis


def fs_sound_guy(src):
    broll = [(166.50, 167.30), (236.00, 236.80), (370.00, 370.80), (415.50, 416.30), (1074.50, 1075.20)]
    shots = intro(broll, "vo_fs_soundguy") + conv(src, [
        (836.75, 838.35), (841.80, 843.75), (844.10, 846.20), (847.30, 850.70), (851.50, 855.80),
        (861.00, 863.75), (865.40, 867.30)])
    v = Video(shots=shots)
    n = len(broll)
    T = mapper(v, n)
    tren.finish(v, "vo_fs_soundguy", n, music_offset=50.0)
    emojis = []
    punchline(v, T(843.3), "😭", emojis)                       # "The sound guy."
    emojis.append((T(861.1), "🤯", 1.4))                       # "a man who can handle all the noise..."
    hook = [("the most aura at the fashion show went to...", WHITE), ("the sound guy", RED), ("😭", WHITE)]
    return v, hook, emojis


def fs_not_tryna_brag(src):
    broll = [(164.20, 165.00), (166.20, 167.00), (168.00, 168.80), (170.00, 170.80), (171.60, 172.40),
             (179.35, 180.20), (162.60, 163.40), (169.10, 169.80)]
    shots = intro(broll, "vo_fs_brag") + conv(src, [(269.20, 275.20), (275.60, 285.62), (287.50, 296.30)])
    v = Video(shots=shots)
    n = len(broll)
    T = mapper(v, n)
    tren.finish(v, "vo_fs_brag", n, music_offset=5.0)
    emojis = [(T(291.4), "💀", 1.2)]                           # "Calvin Klein, Burberry, H&M."
    punchline(v, T(294.8), "😭", emojis)                       # "I'm not even trying to brag"
    hook = [("calvin klein, burberry, H&M...", WHITE), ("\"not even trying to brag\"", RED), ("😭", WHITE)]
    return v, hook, emojis


VIDEOS = {"28_tren_gotta_do_it": ("tren", tren_gotta_do_it), "29_tren_cant_believe": ("tren", tren_cant_believe),
          "30_fs_30_seconds": ("fs", fs_30_seconds), "31_fs_sound_guy": ("fs", fs_sound_guy),
          "32_fs_not_tryna_brag": ("fs", fs_not_tryna_brag)}


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or list(VIDEOS)
    sources = {}
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    for n in names:
        kind, fn = VIDEOS[n]
        if kind not in sources:
            sources[kind] = Source(tren.SRC, tren.WORDS) if kind == "tren" else fashion_source()
        src = sources[kind]
        v, hook, emojis = fn(src)
        out = os.path.join(ROOT, "out", n + ".mp4")
        if "--dry" in sys.argv:
            layout_timeline(v)
            print(n, round(at(v, len(v.shots)), 1))
            print("   ", " | ".join(" ".join(x[2] for x in ph) for ph in podstyle.phrases(podstyle.track_words(v, src))))
            continue
        d, moved, placed, hb = podstyle.render(v, src, out, hook, emojis, preview="--preview" in sys.argv)
        nf, hits = refstyle.qa(out, placed, hb)
        print(f"wrote {out} ({d:.1f}s, {len(v.shots)} shots) – QA: {nf} faces checked, {len(hits)} overlaps {hits[:5]}")


if __name__ == "__main__":
    main()
