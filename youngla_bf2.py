#!/usr/bin/env python3
"""YoungLA Black Friday – batch 2. Clean "framed" layout (see framed.py): hook on top, footage in the
middle, captions + labels underneath, so nothing covers a face or the clothes. Cuts land on sentence ends.

  04_aura_goosebumps  "aura detector": pink glow, shimmer + heartbeat, aura meter filling up
  05_negative_152k    "bank app": live balance counter rolling to -$152,000, coin ticks, buzzer, ka-ching
  06_jay_first_show   "talk show": the host asks for applause so it gets applause, ding / buzzer verdicts

python3 youngla_bf2.py [name ...] [--preview] [--qa]
"""
import json
import os
import sys

import framed
from editor import FIXES, Fx, Shot, Sound, Source, Text, Video
from framed import Y_CAP, Y_HOOK, Y_LABEL

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "footage", "bvm.mp4")
WORDS = os.path.join(ROOT, "transcripts", "youngla_bvm_words.json")
MEDIUM = os.path.join(ROOT, "transcripts", "youngla_bvm_medium_words.json")

PINK = (255, 110, 199)
GREEN = (40, 220, 110)
RED = (255, 64, 64)
GOLD = (255, 196, 40)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def at(v, i, dt=0.0):
    return sum(s.dur for s in v.shots[:i]) + dt


def src_t(v, i, x):
    s = v.shots[i]
    return at(v, i) + (x - s.src_in) / s.speed


def hook(v, text, color=(255, 255, 255, 255)):
    v.texts.append(Text(0, at(v, len(v.shots)), text, y=Y_HOOK, size=60, font="montserrat", fill=BLACK,
                        stroke_w=0, box=color, width=24, anim="none"))


def chip(v, t0, t1, text, bg, fg=WHITE, sound=None, anim="pop"):
    """label in the bottom band (row 2), under the captions."""
    v.texts.append(Text(t0, t1, text, y=Y_LABEL, size=62, font="dejavu", fill=fg, stroke_w=0,
                        box=bg + (255,), width=30, anim=anim))
    if sound:
        v.sounds.append(Sound(t0, sound, 0.9))


def cut_fx(v, accent_strength=0.35):
    """soft flash + whoosh on every cut we make (not on the source's own cuts)."""
    for i in range(1, len(v.shots)):
        v.fx.append(Fx(at(v, i), "flash", 0.22, accent_strength))
        v.sounds.append(Sound(at(v, i) - 0.12, "whoosh", 0.35))


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


# --------------------------------------------------------------------------- 04

def aura_goosebumps():
    v = Video(shots=[Shot(413.15, 445.45, cx=960, cy=520, layout="auto")],
              caption_style=dict(font="montserrat", size=78, hl=PINK, y=Y_CAP, words=3, stroke_w=9, width=18))
    hook(v, "WHEN A MODEL'S AURA HITS FROM 100 MILES AWAY")
    T = lambda x: src_t(v, 0, x)
    end = at(v, 1)
    v.fx += [Fx(T(413.4), "tint", 1.1, 0.8, PINK), Fx(T(413.4), "punch", 0.5, 1.05),
             Fx(T(418.34), "punch", 0.45, 1.08),
             Fx(T(431.4), "punch", 0.5, 1.06), Fx(T(431.4), "tint", 0.9, 0.5, PINK),
             Fx(T(440.74), "tint", 1.2, 0.9, PINK), Fx(T(440.74), "punch", 0.5, 1.07),
             Fx(T(443.74), "tint", 1.4, 0.7, PINK)]
    v.sounds += [Sound(T(413.4), "shimmer", 0.9), Sound(T(418.34), "boom", 0.6),
                 Sound(T(431.4), "heartbeat", 1.0), Sound(T(432.1), "heartbeat", 0.8),
                 Sound(T(440.74), "shimmer", 1.0), Sound(T(443.74), "applause", 0.5)]
    chip(v, T(413.4), T(418.3), "✦ JOHNNY SPOTTED", PINK)
    chip(v, T(418.34), T(422.2), "WAIT... NO PANTS??", RED, sound="pop")
    chip(v, T(422.3), T(431.3), "HIS FACE IS ON EVERY PRODUCT", (60, 60, 60), sound="pop")
    chip(v, T(431.4), T(433.4), "GOOSEBUMPS ✔", GREEN)
    chip(v, T(433.46), T(437.7), "AURA METER: 60%", PINK, sound="tick")
    chip(v, T(437.7), T(440.7), "AURA METER: 85%", PINK, sound="tick")
    chip(v, T(440.74), end, "AURA METER: 100% (MAX)", PINK, sound="ding_green")
    v.progress_bar = PINK
    return v, PINK


# --------------------------------------------------------------------------- 05

def counter(v, t0, t1, hold, a, b, bg, label="BALANCE"):
    """balance chip rolling from a to b between t0 and t1 (ease-out), then holding until `hold`."""
    steps = max(2, int((t1 - t0) * 15))
    for k in range(steps + 1):
        x = k / steps
        val = a + (b - a) * (1 - (1 - x) ** 3)
        ta = t0 + (t1 - t0) * k / steps
        tb = t0 + (t1 - t0) * (k + 1) / steps if k < steps else hold
        sign = "-" if val < 0 else ""
        v.texts.append(Text(ta, tb, f"{label}  {sign}${abs(val):,.0f}", y=Y_LABEL, size=62, font="dejavu",
                            fill=WHITE, stroke_w=0, box=bg + (255,), width=40, anim="none"))
        if k % 3 == 0 and k < steps:
            v.sounds.append(Sound(ta, "tick", 0.7))


def negative_152k():
    v = Video(shots=[
        Shot(740.50, 744.95, layout="auto"),        # "do you know we're giving away a million dollars?" "how do I enter?"
        Shot(751.15, 753.45, layout="auto"),        # "can you just give me the money? just a million flat?"
        Shot(753.50, 779.90, layout="auto"),        # the hypothetical -> "try negative 152,000" -> taxes -> "that is wild"
        Shot(782.55, 786.35, layout="auto"),        # "if you had a million right now, what's your first purchase?"
        Shot(788.75, 793.60, layout="auto"),        # "I would buy an equity in YoungLA."
        Shot(797.95, 798.75, layout="auto", freeze=0.7),   # "51%."
    ], caption_style=dict(font="montserrat", size=78, hl=GREEN, y=Y_CAP, words=3, stroke_w=9, width=18))
    hook(v, "HE ASKED IF HE COULD JUST HAVE THE MILLION. FLAT.")
    cut_fx(v)
    T = lambda i, x: src_t(v, i, x)
    end = at(v, len(v.shots))
    chip(v, T(1, 751.3), at(v, 2), "JUST THE MILLION. FLAT.", (40, 40, 40), sound="coin")
    # the hypothetical: account emptied
    counter(v, T(2, 760.72), T(2, 760.8), T(2, 762.0), 0, 0, (40, 40, 40))
    v.sounds.append(Sound(T(2, 760.72), "pop", 0.9))
    chip(v, T(2, 762.02), T(2, 764.2), "✘ BEEN THERE", RED)
    v.fx += [Fx(T(2, 762.02), "red", 0.8, 0.8)]
    v.sounds.append(Sound(T(2, 762.02), "ding_red", 0.9))
    counter(v, T(2, 764.26), T(2, 764.4), T(2, 766.0), 0, 0, (40, 40, 40))
    # the real story
    counter(v, T(2, 766.06), T(2, 768.7), T(2, 772.1), 0, -152000, (200, 30, 30))
    v.fx += [Fx(T(2, 768.7), "red", 1.0, 1.0), Fx(T(2, 768.7), "shake", 0.4, 0.6), Fx(T(2, 768.7), "punch", 0.5, 1.08)]
    v.sounds += [Sound(T(2, 768.7), "ding_red", 1.0), Sound(T(2, 769.2), "bruh_drop", 0.7)]
    chip(v, T(2, 772.16), at(v, 3), "-$152,000 · THE TAXES DID IT", (200, 30, 30))
    v.fx.append(Fx(T(2, 772.16), "punch", 0.5, 1.05))
    # the purchase
    chip(v, T(4, 791.76), at(v, 5), "BUYING INTO THE COMPANY", (40, 40, 40), sound="ka_ching")
    v.fx.append(Fx(T(4, 791.76), "punch", 0.5, 1.06))
    chip(v, T(5, 798.22), end, "✔ 51% OWNER", GREEN, sound="ding_green")
    v.fx += [Fx(T(5, 798.22), "green", 1.2, 1.0), Fx(T(5, 798.22), "punch", 0.6, 1.08)]
    v.sounds.append(Sound(T(5, 798.4), "ka_ching", 0.8))
    v.progress_bar = GREEN
    return v, GREEN


# --------------------------------------------------------------------------- 06

def jay_first_show():
    v = Video(shots=[Shot(1047.05, 1080.95, layout="auto")],
              caption_style=dict(font="montserrat", size=78, hl=GOLD, y=Y_CAP, words=3, stroke_w=9, width=18))
    hook(v, "JAY CUTLER'S FIRST EVER FASHION SHOW")
    T = lambda x: src_t(v, 0, x)
    end = at(v, 1)
    chip(v, T(1050.44), T(1053.3), "4X MR. OLYMPIA", GOLD, fg=BLACK, sound="pop")
    v.sounds.append(Sound(T(1053.5), "applause", 0.85))     # the host asked for it
    chip(v, T(1053.45), T(1056.4), "✔ APPLAUSE ADDED", GREEN)
    chip(v, T(1064.0), T(1069.1), "✔ FIRST TIME ON THE RUNWAY", GREEN, sound="ding_green")
    v.fx += [Fx(T(1064.0), "green", 0.9, 0.8), Fx(T(1064.0), "punch", 0.45, 1.05)]
    chip(v, T(1074.54), T(1077.7), "FERRARI SF90", GOLD, fg=BLACK, sound="ka_ching")
    v.fx.append(Fx(T(1074.54), "punch", 0.45, 1.06))
    chip(v, T(1077.82), T(1079.5), "✘ THAT'S ROBBIE'S CAR", RED, sound="ding_red")
    v.fx += [Fx(T(1077.82), "red", 0.9, 0.9), Fx(T(1077.82), "shake", 0.35, 0.5)]
    chip(v, T(1079.54), end, "✔ TAKING IT ANYWAY", GREEN, sound="ding_green")
    v.fx += [Fx(T(1079.54), "green", 1.0, 0.9), Fx(T(1079.54), "punch", 0.5, 1.07)]
    v.sounds.append(Sound(T(1080.2), "applause", 0.6))
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
            v, accent = VIDEOS[n]()
            d = framed.render(v, src, out, preview="--preview" in sys.argv, accent=accent)
            print(f"wrote {out} ({d:.1f}s)")
        if "--qa" in sys.argv or "--qa-only" in sys.argv:
            nf, issues = framed.qa(out)
            print(f"QA {n}: {nf} face detections, {len(issues)} issues")
            for i in issues[:20]:
                print("   ", i)


if __name__ == "__main__":
    main()
