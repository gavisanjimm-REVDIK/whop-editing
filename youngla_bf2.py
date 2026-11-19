#!/usr/bin/env python3
"""YoungLA Black Friday – batch 2. Clean "framed" layout (see framed.py): hook on top, footage in the
middle, captions + labels underneath, so nothing covers a face or the clothes.

Each clip: cold-open teaser of the punchline -> tape rewind -> the story, with dead air between sentences
trimmed (never mid-sentence), keyword-coloured captions, and a ducked meme-music bed (Kevin MacLeod, CC BY 4.0).

  04_aura_goosebumps  "aura detector": pink glow, shimmer + heartbeat, aura meter   – Monkeys Spinning Monkeys
  05_negative_152k    "bank app": balance counter rolling to -$152,000, ka-ching    – Local Forecast (Elevator)
  06_jay_first_show   "talk show": applause on request, ding / buzzer verdicts      – Wallpaper

python3 youngla_bf2.py [name ...] [--preview] [--qa]
"""
import json
import os
import sys

import framed
from editor import FIXES, Fx, Shot, Sound, Source, Text, Video
from framed import Y_HOOK, Y_LABEL, Y_CAP

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "footage", "bvm.mp4")
WORDS = os.path.join(ROOT, "transcripts", "youngla_bvm_words.json")
MEDIUM = os.path.join(ROOT, "transcripts", "youngla_bvm_medium_words.json")
MUSIC = os.path.join(ROOT, "assets", "music")

PINK = (255, 110, 199)
GREEN = (40, 220, 110)
RED = (255, 64, 64)
GOLD = (255, 196, 40)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK = (40, 40, 40)


# --------------------------------------------------------------------------- helpers

def at(v, i, dt=0.0):
    return sum(s.dur for s in v.shots[:i]) + dt


def mapper(v, first_main):
    """T(source_time) -> output time, looking only at the story shots (not the teaser/rewind)."""
    def T(x):
        for i in range(first_main, len(v.shots)):
            s = v.shots[i]
            if s.src_in - 0.05 <= x <= s.src_out + 0.05:
                return at(v, i) + (min(max(x, s.src_in), s.src_out) - s.src_in) / s.speed
        raise ValueError(f"{x} is not inside any story shot")
    return T


def speech_shots(src, t0, t1, max_gap=0.75, keep=(), pre=0.14, post=0.24, zooms=(1.0, 1.08)):
    """split [t0, t1] into shots at pauses longer than max_gap that follow a finished sentence.
    `keep` = (a, b) windows whose pauses must stay (e.g. room for applause). Alternating zoom
    hides the jump cut on single-person shots (two-shots always stay uncropped)."""
    ws = [w for w in src.words if t0 - 0.01 <= w[0] < t1]
    groups = [[ws[0]]]
    for w in ws[1:]:
        p = groups[-1][-1]
        kept = any(a <= p[1] and w[0] <= b for a, b in keep)
        if w[0] - p[1] > max_gap and p[2][-1:] in ".?!" and not kept:
            groups.append([w])
        else:
            groups[-1].append(w)
    shots = []
    for k, g in enumerate(groups):
        a = t0 if k == 0 else g[0][0] - pre
        b = t1 if k == len(groups) - 1 else g[-1][1] + post
        shots.append(Shot(a, b, layout="auto", zoom=zooms[k % len(zooms)]))
    return shots


def hook(v, text, color=(255, 255, 255, 255), size=60):
    v.texts.append(Text(0, at(v, len(v.shots)), text, y=Y_HOOK, size=size, font="montserrat", fill=BLACK,
                        stroke_w=0, box=color, width=24, anim="none"))


def chip(v, t0, t1, text, bg, fg=WHITE, sound=None, anim="pop"):
    """label in the bottom band (row 2), under the captions."""
    v.texts.append(Text(t0, t1, text, y=Y_LABEL, size=62, font="dejavu", fill=fg, stroke_w=0,
                        box=bg + (255,), width=30, anim=anim))
    if sound:
        v.sounds.append(Sound(t0, sound, 0.9))


def cut_fx(v, start=1, amount=0.3):
    """soft flash + quiet whoosh on the cuts we make."""
    for i in range(start, len(v.shots)):
        v.fx.append(Fx(at(v, i), "flash", 0.2, amount))
        v.sounds.append(Sound(at(v, i) - 0.1, "whoosh", 0.25))


def teaser_rewind(v, teaser, rewind_from, rewind_to, label, bg):
    """cold open on the punchline, then a fast backwards rewind to where the story starts."""
    rw = Shot(rewind_from, rewind_to, layout="auto", speed=(rewind_to - rewind_from) / 1.8, reverse=True,
              audio="mute", captions=False)
    v.shots[:0] = [teaser, rw]
    chip(v, 0.0, teaser.dur, label, bg)
    v.fx += [Fx(0.0, "punch", 0.4, 1.06)]
    t_rw = teaser.dur
    v.fx += [Fx(t_rw, "flash", 0.25, 0.8), Fx(t_rw, "rgb", rw.dur, 0.9)]
    v.sounds += [Sound(t_rw - 0.05, "rewind", 1.0)]
    v.texts.append(Text(t_rw, t_rw + rw.dur, "◀◀ REWIND", y=Y_LABEL, size=62, font="dejavu", fill=WHITE,
                        stroke_w=0, box=(20, 20, 20, 255), width=30, anim="none"))
    v.fx.append(Fx(t_rw + rw.dur, "flash", 0.3, 0.9))
    return 2   # index of the first story shot


def load_source():
    src = Source(SRC, WORDS)
    med = json.load(open(MEDIUM))
    for key, ws in med.items():                      # use the more accurate medium-model words here
        a, b = (float(x) for x in key.split("-"))
        merged = []
        for s, e, w in ws:
            if merged and (w.startswith(",") or w.startswith("-") or w == "%"):
                ps, pe, pw = merged.pop()
                merged.append((ps, e, pw + w))
                continue
            k = w.strip(" ,.?!").lower()
            merged.append((s, e, w.lower().replace(k, FIXES[k]) if k in FIXES else w))
        src.override(a + 1.5, b - 1.5, merged)
    return src


def caption_style(hl):
    return dict(font="montserrat", size=78, hl=hl, y=Y_CAP, words=3, stroke_w=9, width=18)


# --------------------------------------------------------------------------- 04

def aura_goosebumps(src):
    v = Video(shots=speech_shots(src, 413.15, 445.45), caption_style=caption_style(PINK))
    m = teaser_rewind(v, Shot(442.95, 445.45, layout="auto", zoom=1.05), 413.2, 445.4,
                      "AURA LEVEL: CRITICAL", PINK)
    v.sounds.append(Sound(0.05, "shimmer", 0.9))
    T = mapper(v, m)
    end = at(v, len(v.shots))
    hook(v, "WHEN A MODEL'S AURA HITS FROM 100 MILES AWAY")
    cut_fx(v, start=m + 1)
    v.emph = {"johnny": PINK, "johnny's": PINK, "pants": RED, "goosebumps": PINK, "100": GOLD, "miles": GOLD,
              "section": PINK, "toe": PINK, "toes": PINK, "product": GOLD}
    v.fx += [Fx(T(413.4), "tint", 1.1, 0.8, PINK), Fx(T(413.4), "punch", 0.5, 1.05),
             Fx(T(418.34), "punch", 0.45, 1.08), Fx(T(418.34), "shake", 0.3, 0.4),
             Fx(T(431.4), "punch", 0.5, 1.06), Fx(T(431.4), "tint", 0.9, 0.5, PINK),
             Fx(T(440.74), "tint", 1.2, 0.9, PINK), Fx(T(440.74), "punch", 0.5, 1.07),
             Fx(T(443.74), "tint", 1.4, 0.7, PINK)]
    v.sounds += [Sound(T(413.4), "shimmer", 0.9), Sound(T(418.34), "record_scratch", 0.6),
                 Sound(T(431.4), "heartbeat", 1.0), Sound(T(432.0), "heartbeat", 0.8),
                 Sound(T(440.74), "shimmer", 1.0), Sound(T(443.74), "applause", 0.5)]
    chip(v, T(413.4), T(418.3), "✦ JOHNNY SPOTTED", PINK)
    chip(v, T(418.34), T(420.9), "WAIT... NO PANTS??", RED, sound="pop")
    chip(v, T(421.0), T(431.3), "HIS FACE IS ON EVERY PRODUCT", DARK, sound="pop")
    chip(v, T(431.4), T(433.4), "GOOSEBUMPS ✔", GREEN)
    chip(v, T(433.46), T(437.7), "AURA METER: 60%", PINK, sound="tick")
    chip(v, T(437.7), T(440.7), "AURA METER: 85%", PINK, sound="tick")
    chip(v, T(440.74), end, "AURA METER: 100% (MAX)", PINK, sound="ding_green")
    v.music = dict(file=os.path.join(MUSIC, "Monkeys_Spinning_Monkeys.mp3"), offset=0.0, gain_db=-17, open_db=-9,
                   stops=[(0, at(v, m) - 0.1)])
    v.progress_bar = PINK
    return v, PINK


# --------------------------------------------------------------------------- 05

def counter(v, t0, t1, hold, a, b, bg, label="BALANCE", ticks=True):
    """balance chip rolling from a to b between t0 and t1 (ease-out), then holding until `hold`."""
    steps = max(1, int((t1 - t0) * 15))
    for k in range(steps + 1):
        x = k / steps
        val = a + (b - a) * (1 - (1 - x) ** 3)
        ta = t0 + (t1 - t0) * k / steps
        tb = t0 + (t1 - t0) * (k + 1) / steps if k < steps else hold
        sign = "-" if val < 0 else ""
        v.texts.append(Text(ta, tb, f"{label}  {sign}${abs(val):,.0f}", y=Y_LABEL, size=62, font="dejavu",
                            fill=WHITE, stroke_w=0, box=bg + (255,), width=40, anim="none"))
        if ticks and k % 3 == 0 and k < steps:
            v.sounds.append(Sound(ta, "tick", 0.7))


def negative_152k(src):
    story = (speech_shots(src, 740.50, 744.95) + speech_shots(src, 751.15, 753.45)
             + speech_shots(src, 753.50, 779.90) + speech_shots(src, 782.55, 786.35)
             + speech_shots(src, 788.75, 793.60) + [Shot(797.95, 798.75, layout="auto", freeze=0.8)])
    v = Video(shots=story, caption_style=caption_style(GREEN))
    teaser = Shot(765.95, 768.95, layout="auto", zoom=1.05, freeze=0.5, bw=True)
    m = teaser_rewind(v, teaser, 740.5, 768.95, "BALANCE  -$152,000", (200, 30, 30))
    v.texts = [t for t in v.texts if t.text != "BALANCE  -$152,000"]        # counter does this one
    counter(v, 0.1, 2.75, teaser.dur, 0, -152000, (200, 30, 30))
    v.fx += [Fx(2.75, "red", 0.7, 1.0), Fx(2.75, "shake", 0.3, 0.6)]
    v.sounds.append(Sound(2.75, "ding_red", 1.0))
    T = mapper(v, m)
    end = at(v, len(v.shots))
    hook(v, "HE ASKED IF HE COULD JUST HAVE THE MILLION. FLAT.")
    cut_fx(v, start=m + 1)
    v.emph = {"million": GREEN, "flat": GREEN, "money": GREEN, "emptied": RED, "zero": RED, "negative": RED,
              "152,000": RED, "taxes": RED, "robbed": RED, "consent": RED, "equity": GREEN, "51%": GREEN,
              "wild": GOLD}
    chip(v, T(751.3), T(753.4), "JUST THE MILLION. FLAT.", DARK, sound="coin")
    counter(v, T(760.72), T(760.8), T(762.0), 0, 0, DARK, ticks=False)
    v.sounds.append(Sound(T(760.72), "pop", 0.9))
    chip(v, T(762.02), T(764.2), "✘ BEEN THERE", RED)
    v.fx += [Fx(T(762.02), "red", 0.8, 0.8)]
    v.sounds.append(Sound(T(762.02), "ding_red", 0.9))
    counter(v, T(764.26), T(764.4), T(766.0), 0, 0, DARK, ticks=False)
    counter(v, T(766.06), T(768.7), T(772.1), 0, -152000, (200, 30, 30))
    v.fx += [Fx(T(768.7), "red", 1.0, 1.0), Fx(T(768.7), "shake", 0.4, 0.6), Fx(T(768.7), "punch", 0.5, 1.08)]
    v.sounds += [Sound(T(768.7), "ding_red", 1.0), Sound(T(769.2), "bruh_drop", 0.7)]
    chip(v, T(772.16), T(779.9), "-$152,000 · THE TAXES DID IT", (200, 30, 30))
    v.fx.append(Fx(T(772.16), "punch", 0.5, 1.05))
    chip(v, T(791.76), T(793.6), "BUYING INTO THE COMPANY", DARK, sound="ka_ching")
    v.fx.append(Fx(T(791.76), "punch", 0.5, 1.06))
    chip(v, T(798.22), end, "✔ 51% OWNER", GREEN, sound="ding_green")
    v.fx += [Fx(T(798.22), "green", 1.2, 1.0), Fx(T(798.22), "punch", 0.6, 1.08)]
    v.sounds.append(Sound(T(798.4), "ka_ching", 0.8))
    v.music = dict(file=os.path.join(MUSIC, "Local_Forecast_-_Elevator.mp3"), offset=0.0, gain_db=-17, open_db=-9,
                   stops=[(0, at(v, m) - 0.1), (T(766.0), T(770.2))])   # silence for the reveal
    v.progress_bar = GREEN
    return v, GREEN


# --------------------------------------------------------------------------- 06

def jay_first_show(src):
    keep = [(1053.3, 1055.5), (1078.3, 1079.6)]   # applause gap; comic pause before "I take that one"
    v = Video(shots=speech_shots(src, 1048.75, 1080.95, keep=keep), caption_style=caption_style(GOLD))
    T = mapper(v, 0)
    end = at(v, len(v.shots))
    hook(v, "JAY CUTLER'S FIRST EVER FASHION SHOW (HE PICKED THE WRONG CAR)", size=56)
    cut_fx(v, start=1)
    v.emph = {"jay": GOLD, "cutler": GOLD, "applause": GOLD, "first": GOLD, "last": GOLD,
              "ferrari": RED, "sf90": RED, "robbie's": RED}
    v.sounds.append(Sound(0.0, "applause", 0.5))
    chip(v, T(1050.44), T(1053.3), "4X MR. OLYMPIA", GOLD, fg=BLACK, sound="pop")
    v.fx.append(Fx(T(1050.44), "punch", 0.5, 1.06))
    v.sounds.append(Sound(T(1053.5), "applause", 0.85))     # the host asked for it
    chip(v, T(1053.45), T(1056.4), "✔ APPLAUSE ADDED", GREEN)
    chip(v, T(1064.0), T(1069.1), "✔ FIRST TIME ON THE RUNWAY", GREEN, sound="ding_green")
    v.fx += [Fx(T(1064.0), "green", 0.9, 0.8), Fx(T(1064.0), "punch", 0.45, 1.05)]
    chip(v, T(1074.54), T(1077.7), "FERRARI SF90", GOLD, fg=BLACK, sound="ka_ching")
    v.fx.append(Fx(T(1074.54), "punch", 0.45, 1.06))
    chip(v, T(1077.82), T(1079.5), "✘ THAT'S ROBBIE'S CAR", RED, sound="ding_red")
    v.fx += [Fx(T(1077.82), "red", 0.9, 0.9), Fx(T(1077.82), "shake", 0.35, 0.5)]
    v.sounds.append(Sound(T(1078.5), "record_scratch", 0.6))
    chip(v, T(1079.54), end, "✔ TAKING IT ANYWAY", GREEN, sound="ding_green")
    v.fx += [Fx(T(1079.54), "green", 1.0, 0.9), Fx(T(1079.54), "punch", 0.5, 1.07)]
    v.sounds.append(Sound(T(1080.2), "applause", 0.6))
    v.music = dict(file=os.path.join(MUSIC, "Wallpaper.mp3"), offset=0.0, gain_db=-17, open_db=-9,
                   stops=[(T(1078.45), T(1079.5))])          # music cuts out on the record scratch
    v.progress_bar = GOLD
    return v, GOLD


VIDEOS = {"04_aura_goosebumps": aura_goosebumps, "05_negative_152k": negative_152k,
          "06_jay_first_show": jay_first_show}


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")] or list(VIDEOS)
    src = load_source()
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    for n in names:
        out = os.path.join(ROOT, "out", n + ".mp4")
        if "--qa-only" not in sys.argv:
            v, accent = VIDEOS[n](src)
            d = framed.render(v, src, out, preview="--preview" in sys.argv, accent=accent)
            print(f"wrote {out} ({d:.1f}s, {len(v.shots)} shots)")
        if "--qa" in sys.argv or "--qa-only" in sys.argv:
            nf, issues = framed.qa(out)
            print(f"QA {n}: {nf} face detections, {len(issues)} issues")
            for i in issues[:20]:
                print("   ", i)


if __name__ == "__main__":
    main()
