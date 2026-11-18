#!/usr/bin/env python3
"""BOXABL short #1: "Nature documentary" edit.

Style: slow telephoto drifts, warm film grade, grain + vignette, soft dissolves, doc subtitles and a
species lower-third... then a hard comedy cut (record scratch + crash zoom) on the confused rabbit.
"""
import os
import sys

import numpy as np
from PIL import Image

import fx
from fx import W, H, FPS

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "keyframes", "doc_truck.jpg")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "01_nature_documentary.mp4")
DUR = 21.0

RABBIT = (525, 2070)
BOX = (1050, 1165)
FULL = (768, 1376)

# (start, end, from(cx,cy,w), to(cx,cy,w), transition-in)
SHOTS = [
    (0.0, 2.6, (*RABBIT, 780), (*RABBIT, 640), "cut"),
    (2.6, 7.4, (*FULL, 1536), (900, 1260, 1250), "dissolve"),
    (7.4, 11.4, (1050, 1330, 840), (1050, 1300, 700), "dissolve"),
    (11.4, 14.0, (*RABBIT, 900), (*RABBIT, 520), "crash"),
    (14.0, 17.6, (1000, 1250, 1120), (1020, 1200, 940), "cut"),
    (17.6, DUR, (*FULL, 1536), (*FULL, 1400), "dissolve"),
]

SUBS = [
    (2.9, 7.2, "Here, in the Nevada desert... we witness one of nature's rarest migrations."),
    (8.4, 11.3, "Folded flat for travel, it rides a truck across the desert, searching for the perfect backyard."),
    (12.0, 13.9, "The local wildlife... is deeply confused."),
    (14.3, 17.4, "When it finds the perfect spot... it unfolds into a home. Right there."),
]


def shot_at(t):
    for i, s in enumerate(SHOTS):
        if s[0] <= t < s[1]:
            return i
    return len(SHOTS) - 1


def base_frame(img, i, t):
    t0, t1, a, b, kind = SHOTS[i]
    u = (t - t0) / (t1 - t0)
    if kind == "crash":
        k = fx.ease_out((t - t0) / 0.18, 4)
        cx, cy = a[0], a[1]
        w = fx.lerp(a[2], b[2], k) * (1 - 0.03 * fx.ease_io(u))
        dx, dy, rot = fx.shake(t, 9 * max(0.15, 1 - (t - t0) / 0.6), seed=3)
        return fx.cam(img, cx + dx, cy + dy, w, rot)
    e = fx.ease_io(u) if i != 0 else u
    cx = fx.lerp(a[0], b[0], e)
    cy = fx.lerp(a[1], b[1], e)
    w = fx.lerp(a[2], b[2], e)
    # gentle handheld telephoto float
    dx, dy, rot = fx.shake(t, 2.2, freq=1.3, seed=i)
    fr = fx.cam(img, cx + dx, cy + dy, w, rot * 0.3)
    if i == len(SHOTS) - 1:  # end card background
        fr = fx.darken(fx.blur(fr, 14), 0.42)
    return fr


def main():
    img = Image.open(SRC).convert("RGB")
    vig = fx.vignette(0.6)
    grains = fx.grain_bank(6, 7)

    hook = fx.text_img("They finally filmed the rarest animal in Nevada", fx.F_XBOLD, 70,
                       shadow=14, shadow_alpha=200, max_w=900)
    ep = fx.text_img("EPISODE 1", fx.F_SEMI, 34, tracking=10, shadow=8)
    ep2 = fx.text_img("The Great Migration", fx.F_SERIF, 76, shadow=12)
    subs = [(a, b, fx.text_img(s, fx.F_SEMI, 50, shadow=12, shadow_alpha=230, max_w=920)) for a, b, s in SUBS]
    lt_name = fx.text_img("BOXABL Casita", fx.F_SERIF, 92, align="left", shadow=12)
    lt_latin = fx.text_img("Domus foldablus", fx.F_ITAL, 58, align="left", shadow=10)
    lt_fact = fx.text_img("Folds flat  ·  Ships on a truck  ·  Unfolds on site", fx.F_MED, 34, align="left", shadow=8)
    q = fx.text_img("?", fx.F_BLACK, 170, stroke=6, shadow=12)
    end_logo = fx.logo("white", 780)
    end_1 = fx.text_img("The future of housing.", fx.F_SERIF, 70, shadow=10)
    end_2 = fx.text_img("It folds. It ships. It unfolds.", fx.F_MED, 44, shadow=8)
    end_3 = fx.text_img("Next episode: The Unfolding", fx.F_ITAL, 46, fill=(255, 220, 150, 255), shadow=8)

    audio = os.path.join(ROOT, "out", "_doc.wav")
    build_audio(audio)
    enc = fx.Encoder(OUT, audio)
    n = int(DUR * FPS)
    prev_i, prev_last = 0, None
    for f in range(n):
        t = f / FPS
        i = shot_at(t)
        fr = base_frame(img, i, t)
        t0 = SHOTS[i][0]
        if SHOTS[i][4] == "dissolve" and i > 0 and t - t0 < 0.45:
            fr = Image.blend(base_frame(img, i - 1, t0 - 1e-3), fr, fx.ease_io((t - t0) / 0.45))

        # warm documentary grade + vignette + grain
        a = fx.grade(np.asarray(fr), lift=(10, 4, -4), gain=(1.04, 1.0, 0.93), sat=0.92)
        a = a * vig + grains[f % len(grains)]
        if t < 0.35:
            a *= fx.ease_out(t / 0.35)
        fr = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")

        # hook
        if t < 2.6:
            al = fx.clamp(t / 0.25) * fx.clamp((2.6 - t) / 0.2)
            fx.paste(fr, hook, W / 2, 360, scale=1 + 0.02 * t, alpha=al)
        # episode title
        if 3.0 < t < 6.2:
            al = fx.clamp((t - 3.0) / 0.5) * fx.clamp((6.2 - t) / 0.4)
            fx.paste(fr, ep, W / 2, 300, alpha=al)
            fx.paste(fr, ep2, W / 2, 385, alpha=al)
        # species lower-third
        if 7.9 < t < 11.4:
            u = t - 7.9
            d = fx.ImageDraw.Draw(fr)
            lw = int(560 * fx.ease_out(u / 0.5))
            d.rectangle([90, 1236, 90 + lw, 1241], fill=(255, 210, 130, 255))
            fx.paste(fr, lt_name, 90 + lt_name.width / 2 - 20 * (1 - fx.ease_out(u / 0.5)), 1170,
                     alpha=fx.clamp(u / 0.4))
            fx.paste(fr, lt_latin, 90 + lt_latin.width / 2, 1295, alpha=fx.clamp((u - 0.35) / 0.4))
            fx.paste(fr, lt_fact, 90 + lt_fact.width / 2, 1360, alpha=fx.clamp((u - 0.7) / 0.4))
        # confused question marks
        if 11.65 < t < 14.0:
            for k, (dx, dy, at) in enumerate([(-170, -330, 11.65), (40, -420, 11.85), (200, -310, 12.05)]):
                if t > at:
                    s = fx.back_out((t - at) / 0.25) * (1 + 0.04 * np.sin(t * 8 + k))
                    fx.paste(fr, q, W / 2 + dx, 760 + dy, scale=s, rot=(-12, 6, 15)[k])
        # subtitles
        for a0, a1, im in subs:
            if a0 < t < a1:
                al = fx.clamp((t - a0) / 0.3) * fx.clamp((a1 - t) / 0.25)
                fx.paste(fr, im, W / 2, 1520, alpha=al)
        # end card
        if t >= 17.6:
            u = t - 17.6
            fx.paste(fr, end_logo, W / 2, 820, scale=0.92 + 0.08 * fx.ease_out(u / 0.8), alpha=fx.clamp(u / 0.6))
            fx.paste(fr, end_1, W / 2, 1000, alpha=fx.clamp((u - 0.7) / 0.5))
            fx.paste(fr, end_2, W / 2, 1090, alpha=fx.clamp((u - 1.2) / 0.5))
            fx.paste(fr, end_3, W / 2, 1290, alpha=fx.clamp((u - 2.0) / 0.5))
        enc.write(fr.convert("RGB"))
    enc.close()
    os.remove(audio)
    print("wrote", OUT)


def build_audio(path):
    m = fx.Mix(DUR)
    m.add(fx.wind(DUR, 0.10), 0)
    am = fx.pad_chord(11.4, [110, 220, 261.63, 329.63], amp=0.16)
    m.add(am, 0)
    m.add(fx.sfx_whoosh(0.9), 2.2, 0.25)
    m.add(fx.sfx_whoosh(0.9), 7.0, 0.25)
    m.add(fx.sfx_ding(1.6, 880), 7.9, 0.35)
    # comedy beat: needle scratch, music stops
    m.add(fx.sfx_scratch(), 11.35, 0.9)
    m.add(fx.sfx_boing(), 11.65, 0.5)
    m.add(fx.sfx_pop(0.1, 900, 1500), 11.65, 0.4)
    m.add(fx.sfx_pop(0.1, 1000, 1700), 11.85, 0.4)
    m.add(fx.sfx_pop(0.1, 1100, 1900), 12.05, 0.4)
    m.add(fx.pad_chord(DUR - 14.0, [130.81, 261.63, 329.63, 392.0], amp=0.17, seed=4), 14.0)
    m.add(fx.sfx_boom(2.5), 17.6, 0.35)
    m.add(fx.sfx_ding(2.0, 1046.5), 17.7, 0.45)
    m.write(path, DUR)


if __name__ == "__main__":
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    main()
