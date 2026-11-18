#!/usr/bin/env python3
"""BOXABL short #2: "Meet Casitino Foldini" — brainrot hype edit.

Style: everything locked to a 120 BPM beat — zoom punches, screen shake, white flash frames, RGB split
on the drops, big word-by-word pop captions, a freeze-frame "character select" card with stat bars.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

import fx
from fx import W, H, FPS

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "keyframes", "foldini_driving.jpg")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "02_meet_foldini.mp4")
DUR = 14.0
BEAT = 0.5

FACE = (832, 1430)
VISOR = (660, 760)
FULL = (768, 1376)
YEL = (255, 222, 40, 255)

# word-pop captions: (time, text, colour)
WORDS = [
    (0.08, "WAIT.", "white"), (0.5, "WHO IS\nDRIVING??", YEL),
    (1.0, "A HOUSE.", "white"), (1.5, "IS DRIVING.", YEL), (2.0, "A TRUCK.", "white"),
    (6.5, "BUILT IN\nVEGAS", "white"), (7.25, "FOLDED UP", YEL), (8.0, "SHIPPED ON\nA TRUCK", "white"),
    (9.0, "FOLD IT.", "white"), (9.75, "SHIP IT.", YEL), (10.5, "LIVE IN IT.", "white"),
]
WORD_END = {2.0: 2.5, 8.0: 9.0, 10.5: 11.5}
STATS = [("FOLDS", "YES", 1.0), ("SHIPS ON", "A TRUCK", 0.85), ("BORN IN", "LAS VEGAS", 0.9),
         ("VIBES", "IMMACULATE", 1.0)]
FLASHES = [0.0, 1.0, 2.5, 6.5, 9.0, 9.75, 10.5, 11.5]


def camera(t):
    """Return (cx, cy, w, shake_amp, rgb_px)."""
    if t < 1.0:  # extreme close-up on the face, slow creep in
        return (*FACE, fx.lerp(600, 540, t), 3, 0)
    if t < 2.5:  # punch out to reveal, re-punch on each beat
        k = (t - 1.0) % BEAT
        w = fx.lerp(1100, 1300, fx.ease_out(k / 0.15)) - 60 * ((t - 1.0) // BEAT)
        return (*FULL, w, 14 * max(0, 1 - k / 0.25), 6 * max(0, 1 - k / 0.12))
    if t < 6.5:  # character card freeze: slow push
        u = (t - 2.5) / 4
        return (720, 1720, fx.lerp(1000, 900, fx.ease_io(u)), 0, 0)
    if t < 9.0:  # visor logo, punch on beats
        k = (t - 6.5) % 0.75
        w = fx.lerp(1060, 940, fx.ease_out(k / 0.12))
        return (*VISOR, w, 10 * max(0, 1 - k / 0.25), 0)
    if t < 11.5:  # FOLD IT / SHIP IT / LIVE IN IT
        idx = int((t - 9.0) // 0.75)
        k = (t - 9.0) % 0.75
        w = [760, 620, 500, 500][min(idx, 3)] * (1 + 0.25 * (1 - fx.ease_out(k / 0.12)))
        return (*FACE, w, 16 * max(0, 1 - k / 0.3), 10 * max(0, 1 - k / 0.15))
    u = (t - 11.5) / (DUR - 11.5)
    return (*FULL, fx.lerp(1536, 1420, u), 0, 0)


def main():
    img = Image.open(SRC).convert("RGB")
    words = {}
    for at, txt, col in WORDS:
        words[at] = fx.text_img(txt, fx.F_BLACK, 132, fill=col, stroke=12, shadow=18, shadow_alpha=220)
    name = fx.text_img("CASITINO\nFOLDINI", fx.F_BLACK, 150, fill=YEL, stroke=12, shadow=20, spacing=1.0)
    tag = fx.text_img("THE BOXABL MASCOT", fx.F_XBOLD, 46, fill="white", tracking=6, shadow=10)
    stat_l = [fx.text_img(a, fx.F_XBOLD, 40, align="left", shadow=8) for a, _, _ in STATS]
    stat_r = [fx.text_img(b, fx.F_BLACK, 48, fill=YEL, align="left", shadow=8) for _, b, _ in STATS]
    sel = fx.text_img("NEW CHARACTER UNLOCKED", fx.F_XBOLD, 40, fill=(20, 20, 20, 255), tracking=4)
    end_logo = fx.logo("white", 760)
    end_1 = fx.text_img("CASITINO FOLDINI\nWILL RETURN.", fx.F_BLACK, 84, fill=YEL, stroke=8, shadow=14)
    end_2 = fx.text_img("Where should he drive next?", fx.F_XBOLD, 50, shadow=12)

    audio = os.path.join(ROOT, "out", "_mascot.wav")
    build_audio(audio)
    enc = fx.Encoder(OUT, audio)
    keys = sorted(words)
    for f in range(int(DUR * FPS)):
        t = f / FPS
        cx, cy, w, amp, rgb = camera(t)
        dx, dy, rot = fx.shake(t, amp, seed=5) if amp else (0, 0, 0)
        fr = fx.cam(img, cx + dx, cy + dy, w, rot)
        if 2.5 <= t < 6.5:  # character-select freeze look
            fr = fx.darken(fx.desat(fr, 0.55), 0.6)
        if t >= 11.5:
            fr = fx.darken(fx.blur(fr, 16), 0.45)
        fr = fx.rgb_split(fr, rgb)
        a = fx.grade(np.asarray(fr), gain=(1.05, 1.03, 1.0), sat=1.18)
        # white flash frames on hits
        for ft in FLASHES:
            if 0 <= t - ft < 0.12:
                a = a + (255 - a) * (1 - (t - ft) / 0.12) * 0.85
        fr = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")
        d = ImageDraw.Draw(fr)

        # word-pop captions (one at a time, until the next word)
        cur = [k for k in keys if k <= t and not (2.5 <= t < 6.5) and t < 11.5]
        if cur:
            k = cur[-1]
            end = WORD_END.get(k, keys[keys.index(k) + 1] if keys.index(k) + 1 < len(keys) else DUR)
            if t < end:
                s = fx.back_out((t - k) / 0.16, 3.0)
                fx.paste(fr, words[k], W / 2, 1540, scale=0.55 + 0.45 * s, rot=(-3 if keys.index(k) % 2 else 3))

        # character card
        if 2.5 <= t < 6.5:
            u = t - 2.5
            bw = int(780 * fx.ease_out(u / 0.25))
            d.rectangle([W / 2 - bw / 2, 640, W / 2 + bw / 2, 712], fill=YEL)
            if u > 0.15:
                fx.paste(fr, sel, W / 2, 676, alpha=fx.clamp((u - 0.15) / 0.15))
            fx.paste(fr, name, W / 2 + 900 * (1 - fx.ease_out((u - 0.1) / 0.35)), 890,
                     rot=-4, alpha=fx.clamp((u - 0.1) / 0.1))
            fx.paste(fr, tag, W / 2, 1095, alpha=fx.clamp((u - 0.45) / 0.25))
            for i, (lab, val, fill) in enumerate(zip(stat_l, stat_r, [s[2] for s in STATS])):
                at = 0.7 + i * 0.55
                if u < at:
                    continue
                v = u - at
                y = 1200 + i * 120
                x0 = 120
                fx.paste(fr, lab, x0 + lab.width / 2, y, alpha=fx.clamp(v / 0.15))
                d.rounded_rectangle([x0, y + 40, W - 120, y + 72], 16, fill=(255, 255, 255, 70))
                bx = x0 + (W - 240) * fill * fx.ease_out(v / 0.35)
                d.rounded_rectangle([x0, y + 40, bx, y + 72], 16, fill=YEL)
                fx.paste(fr, val, W - 120 - val.width / 2, y - 4, scale=0.6 + 0.4 * fx.back_out(v / 0.2),
                         alpha=fx.clamp(v / 0.1))

        # end card
        if t >= 11.5:
            u = t - 11.5
            fx.paste(fr, end_logo, W / 2, 640, scale=0.6 + 0.4 * fx.back_out(u / 0.3), alpha=fx.clamp(u / 0.15))
            fx.paste(fr, end_1, W / 2, 900, scale=0.6 + 0.4 * fx.back_out((u - 0.4) / 0.3),
                     alpha=fx.clamp((u - 0.4) / 0.12))
            fx.paste(fr, end_2, W / 2, 1110, alpha=fx.clamp((u - 1.1) / 0.3))
        enc.write(fr.convert("RGB"))
    enc.close()
    os.remove(audio)
    print("wrote", OUT)


def build_audio(path):
    m = fx.Mix(DUR)
    kick, clap, hat = fx.sfx_kick(), fx.sfx_clap(), fx.sfx_hat()
    bass_notes = [55.0, 55.0, 65.41, 73.42]

    def groove(t0, t1, full=True):
        b = 0
        t = t0
        while t < t1 - 1e-6:
            m.add(kick, t, 0.9)
            if b % 2 == 1:
                m.add(clap, t, 0.45)
            m.add(hat, t + BEAT / 2, 0.35)
            if full:
                m.add(hat, t, 0.2)
                f = bass_notes[(b // 2) % 4]
                bs = fx.sine(f, BEAT * 0.9) * fx.env_exp(int(BEAT * 0.9 * fx.SR), 0.25)
                m.add(np.tanh(bs * 2.5) * 0.35, t + BEAT / 2)
            b += 1
            t += BEAT

    m.add(fx.sfx_boom(1.2), 0.0, 0.6)
    groove(0.5, 2.5)
    m.add(fx.sfx_scratch(), 2.45, 0.9)
    m.add(fx.sfx_riser(0.8), 2.5, 0.3)
    for i in range(len(STATS)):
        m.add(fx.sfx_pop(0.12, 700 + 120 * i, 1500 + 150 * i), 2.5 + 0.7 + i * 0.55, 0.55)
        m.add(fx.sfx_ding(0.8, 1318.5 + 100 * i), 2.5 + 0.7 + i * 0.55 + 0.2, 0.25)
    m.add(fx.sfx_riser(1.4), 5.1, 0.5)
    m.add(fx.sfx_boom(1.5), 6.5, 0.7)
    groove(6.5, 9.0)
    for at in (9.0, 9.75, 10.5):
        m.add(fx.sfx_boom(0.9), at, 0.8)
        m.add(fx.sfx_whoosh(0.35, up=False), at - 0.3, 0.4)
    groove(9.0, 11.5, full=True)
    m.add(fx.sfx_boom(2.4), 11.5, 0.9)
    m.add(fx.sfx_ding(2.0, 1046.5), 11.6, 0.5)
    m.add(fx.sfx_boing(0.6), 12.6, 0.35)
    m.write(path, DUR)


if __name__ == "__main__":
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    main()
