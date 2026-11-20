#!/usr/bin/env python3
"""YoungLA Black Friday – Tren Twins "Breaking Bad" giveaway trailer (second campaign brief).

Same editing style as batches 6/7 (podstyle.py): AI narrator intro over quick b-roll with a red arrow, then the
real scene. Changes asked for in this round:
  * captions in ONE fixed spot under the video (2-3 word phrases, spoken word highlighted) – no jumping around
  * "Say Goodbye" (sped up) a bit louder than batch 7, still clearly under the voices
  * narrator lively ([excited] [high voice] on ElevenLabs "Ethan"), already ~250-290 Hz so no extra pitch shift
  * on-screen hook mentions the $1,000,000 Black Friday giveaway (required by the brief)

The source has burned-in subtitles; footage/tren_1080.mp4 is cropped just above them
(ffmpeg -i tren.mp4 -vf "crop=3104:1746:0:60,scale=1920:1080" ...), and our captions use the subtitles' own text
(transcripts/tren_words.json).

  22_tren_lie_in_it   "Million bucks." "I gotta do it, bro." ... "Just try bro. It's comfy."
  23_tren_feels_like  "Suck your stomach in." ... "I guess this is what a million dollars feels like."
  24_tren_mexico      "Or we could just take it and go to Mexico." ... "Okay. I was just kidding, dude."

python3 youngla_tren.py [name ...] [--preview]
"""
import os
import sys

import podstyle
import refstyle
from editor import Fx, Shot, Sound, Source, Video, layout_timeline
from youngla_bf2 import ROOT, at, mapper
from youngla_bf6 import VO_DIR, VO_START, intro, punchline
import json

SRC = os.path.join(ROOT, "footage", "tren_1080.mp4")
WORDS = os.path.join(ROOT, "transcripts", "tren_words.json")
SONG = os.path.join(ROOT, "assets", "music", "say_goodbye_highpitch.mp3")
WHITE, RED = refstyle.WHITE, refstyle.RED

podstyle.CAPTION_MODE = "phrase"
podstyle.EMOJI_ON_TOP = True


def vo_words(name):
    ws = json.load(open(os.path.join(VO_DIR, "vo_words.json")))[name]
    out = []
    for a, b, w in ws:
        lw = w.lower().strip(",.!?")
        if lw == "trend":
            w = w.replace("trend", "Tren").replace("Trend", "Tren")
        if lw == "young":
            out.append([a + VO_START, b + VO_START, "YoungLA"])
            continue
        if out and out[-1][2] == "YoungLA" and lw in ("l", ".a.", "a", "l.a."):
            out[-1][1] = b + VO_START
            continue
        out.append([a + VO_START, b + VO_START, w])
    return [tuple(x) for x in out]


def finish(v, vo_name, n_intro, music_offset=1.0):
    v.extra_audio = [(VO_START, os.path.join(VO_DIR, vo_name + ".mp3"), 1.0)]
    v.vo_words = vo_words(vo_name)
    v.bleep = "mute"
    # louder than batch 7 (-21/-14), still well under the voices
    v.music = dict(file=SONG, offset=music_offset, gain_db=-15, open_db=-9, stops=[])
    t_conv = at(v, n_intro)
    v.fx.append(Fx(t_conv, "flash", 0.3, 0.6))
    v.sounds += [Sound(0.0, "boom", 0.6), Sound(t_conv - 0.2, "whoosh", 0.45)]
    for i in range(1, n_intro):
        v.fx.append(Fx(at(v, i), "punch", 0.25, 1.03))


def word_t(src, text, after):
    """source time of the first transcript word containing `text` after `after`."""
    return next(a for a, b, w in src.words if a >= after and text.lower() in w.lower())


# --------------------------------------------------------------------------- 22

def lie_in_it(src):
    broll = [(34.30, 35.10), (19.60, 20.40), (14.20, 15.00), (45.20, 46.00), (37.60, 38.40), (42.30, 43.10),
             (29.00, 29.80)]
    v = Video(shots=intro(broll, "vo_tren_lie") + [Shot(2.30, 24.00, layout="auto")])
    n = len(broll)
    T = mapper(v, n)
    finish(v, "vo_tren_lie", n)
    emojis = [(T(word_t(src, "ain't", 10.7)), "💀", 1.3)]           # "Bro, this ain't your money man."
    punchline(v, T(word_t(src, "comfy", 19.4)), "😂", emojis)      # "Just try bro. It's comfy."
    hook = [("YoungLA is giving away", WHITE), ("$1,000,000", RED), ("for Black Friday", WHITE), ("🤯", WHITE)]
    return v, hook, emojis


# --------------------------------------------------------------------------- 23

def feels_like(src):
    broll = [(2.60, 3.40), (4.30, 5.10), (9.50, 10.30), (11.20, 12.00), (14.20, 15.00), (45.20, 46.00),
             (48.50, 49.30), (52.00, 52.80)]
    v = Video(shots=intro(broll, "vo_tren_feels") + [Shot(23.90, 41.45, layout="auto")])
    n = len(broll)
    T = mapper(v, n)
    finish(v, "vo_tren_feels", n)
    emojis = [(T(29.95), "💀", 1.2)]                                   # "Heavy as —"
    punchline(v, T(word_t(src, "feels", 35.0)), "🤯", emojis)      # "...what a million dollars feels like."
    hook = [("the", WHITE), ("$1,000,000", RED), ("Black Friday giveaway... this is what it feels like", WHITE),
            ("🤯", WHITE)]
    return v, hook, emojis


# --------------------------------------------------------------------------- 24

def mexico(src):
    broll = [(2.60, 3.40), (19.60, 20.40), (29.00, 29.80), (34.30, 35.10), (37.60, 38.40), (14.20, 15.00),
             (22.00, 22.80), (11.00, 11.80)]
    v = Video(shots=intro(broll, "vo_tren_mexico") + [Shot(41.40, 57.18, layout="auto")])
    n = len(broll)
    T = mapper(v, n)
    finish(v, "vo_tren_mexico", n)
    emojis = []
    punchline(v, T(word_t(src, "mexico", 44.5)), "😭", emojis)     # "...and go to Mexico."
    emojis.append((T(word_t(src, "don't", 50.2)), "💀", 1.2))      # "Don't be an —"
    hook = [("YoungLA is giving away a", WHITE), ("MILLION", RED), ("and he wants to go to Mexico", WHITE),
            ("😭", WHITE)]
    return v, hook, emojis


# --------------------------------------------------------------------------- set 2

def line_shot(src, a, b, pre=0.15, post=0.30, keep_to=None):
    """one subtitle line as a shot, trimmed to its speech (optionally held to `keep_to` for the action after it)."""
    ws = [w for w in src.words if a - 0.2 <= w[0] < b]
    s0 = max(a - 0.25, ws[0][0] - pre) if ws else a
    s1 = min(b, ws[-1][1] + post) if ws else b
    return Shot(s0, keep_to or s1, layout="auto")


def supercut(src):
    """25: the whole trailer as a 20-second story."""
    broll = [(29.00, 29.80), (38.00, 38.80), (42.40, 43.20), (31.50, 32.30), (23.00, 23.80), (26.00, 26.80),
             (16.80, 17.60), (52.90, 53.60)]
    lines = [(4.05, 6.97, None), (9.38, 10.72, None), (10.72, 13.72, 15.40), (19.44, 21.86, None),
             (34.28, 37.41, None), (44.54, 47.26, None), (48.34, 50.26, None), (51.26, 52.80, None)]
    v = Video(shots=intro(broll, "vo_tren_story") + [line_shot(src, a, b, keep_to=k) for a, b, k in lines])
    n = len(broll)
    T = mapper(v, n)
    finish(v, "vo_tren_story", n, music_offset=20.0)
    for i in range(n + 1, len(v.shots)):                    # our cuts between lines: quick whoosh, no flash
        v.sounds.append(Sound(at(v, i) - 0.1, "whoosh", 0.25))
    emojis = []
    punchline(v, T(word_t(src, "comfy", 19.4)), "😂", emojis)
    punchline(v, T(word_t(src, "mexico", 44.5)), "😭", emojis)
    hook = [("no way YoungLA is giving away a", WHITE), ("MILLION BUCKS", RED), ("🔥", WHITE)]
    return v, hook, emojis


def caved(src):
    """26: "we have a job to do"... then he gets in the pile too."""
    broll = [(2.60, 3.40), (5.00, 5.80), (36.00, 36.80), (45.00, 45.80), (48.60, 49.40), (52.00, 52.80),
             (38.50, 39.30)]
    v = Video(shots=intro(broll, "vo_tren_caved") + [Shot(10.72, 14.80, layout="auto"),
                                                    Shot(16.40, 34.28, layout="auto")])
    n = len(broll)
    T = mapper(v, n)
    finish(v, "vo_tren_caved", n, music_offset=40.0)
    emojis = []
    punchline(v, T(word_t(src, "alright", 23.8)), "😭", emojis)    # "Alright." – he caves
    emojis.append((T(29.95), "💀", 1.2))                               # "Heavy as —"
    hook = [("this has to be the", WHITE), ("biggest giveaway", RED), ("ever", WHITE), ("🤯", WHITE)]
    return v, hook, emojis


def nap(src):
    """27: "I gotta do it, bro" ... jump to the end: "we should like take a nap right now." """
    broll = [(19.60, 20.40), (29.00, 29.80), (34.50, 35.30), (38.00, 38.80), (42.40, 43.20), (46.00, 46.80),
             (49.50, 50.10)]
    v = Video(shots=intro(broll, "vo_tren_nap") + [Shot(2.40, 13.72, layout="auto"), Shot(53.85, 57.18, layout="auto")])
    n = len(broll)
    T = mapper(v, n)
    finish(v, "vo_tren_nap", n, music_offset=60.0)
    v.fx.append(Fx(at(v, n + 1), "flash", 0.35, 0.8))           # jump to the ending
    v.sounds.append(Sound(at(v, n + 1) - 0.2, "whoosh", 0.5))
    emojis = []
    punchline(v, T(word_t(src, "nap", 53.8)), "😴", emojis)
    hook = [("YoungLA is giving away", WHITE), ("$1,000,000", RED), ("and they're napping on it", WHITE),
            ("😭", WHITE)]
    return v, hook, emojis


VIDEOS = {"22_tren_lie_in_it": lie_in_it, "23_tren_feels_like": feels_like, "24_tren_mexico": mexico,
          "25_tren_supercut": supercut, "26_tren_caved": caved, "27_tren_nap": nap}


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or list(VIDEOS)
    src = Source(SRC, WORDS)
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    for n in names:
        v, hook, emojis = VIDEOS[n](src)
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
