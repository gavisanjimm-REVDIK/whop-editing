#!/usr/bin/env python3
"""BOXABL Phase 2 clips in the "viral explainer" style of the reference short.

Layout (1080x1920): blurred zoomed copy of the footage fills the frame; the sharp footage sits in a
centre band; a 2-line title with colour-coded keywords + emoji is pinned on top; the voiceover is
captioned ONE WORD AT A TIME in the middle of the band; red arrows point at the house; every cut gets
a zoom punch, some get a white flash + whoosh. Audio = AI voiceover + dark drone/trap bed (~97 BPM).

Footage: ONLY the two official Phase 2 videos (footage/boxabl_phase2_{1,2}.mp4, video-only).

  python3 clipper.py casita|phase2|crane|all
"""
import json
import math
import os
import re
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "boxabl"))
import fx  # noqa: E402  (shared text/audio helpers)
from clips import CLIPS  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
FOOT = os.path.join(REPO, "footage")
W, H, FPS = 1080, 1920, 30
BAND_Y, BAND_H = 470, 960          # footage band (9:8 crop of the 16:9 source)
SRC_W, SRC_H = 1920, 1080
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
COL = {"w": (255, 255, 255), "y": (255, 214, 0), "o": (255, 140, 0), "r": (255, 45, 45),
       "b": (40, 150, 255), "g": (60, 230, 90)}


# ---------------- text ----------------
def emoji_img(ch, size):
    f = ImageFont.truetype(EMOJI_FONT, 109)
    im = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((4, 4), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    return im.resize((round(im.width * size / im.height), size), Image.LANCZOS)


def rich_line(spans, size, stroke=6):
    """spans: list of (text, colour-key) ; emoji spans use colour key 'e'."""
    f = fx.font(fx.F_BLACK, size)
    parts = []
    for txt, c in spans:
        if c == "e":
            for ch in txt:
                if ch.strip() and ch != "\ufe0f":
                    parts.append(("img", emoji_img(ch, int(size * 1.05))))
        else:
            parts.append(("txt", txt, COL[c]))
    gaps = [int(size * 0.12) if (i + 1 < len(parts) and parts[i + 1][0] == "img") else -stroke * 2
            for i in range(len(parts))]
    widths = [p[1].width if p[0] == "img" else int(f.getlength(p[1])) + stroke * 2 for p in parts]
    asc, desc = f.getmetrics()
    h = asc + desc + stroke * 2
    im = Image.new("RGBA", (sum(widths) + sum(gaps[:-1]) + 8, h + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x = 4
    for p, wdt, gap in zip(parts, widths, gaps):
        if p[0] == "img":
            im.alpha_composite(p[1], (x, 4 + (h - p[1].height) // 2))
        else:
            d.text((x + stroke, 4 + stroke), p[1], font=f, fill=p[2], stroke_width=stroke, stroke_fill="black")
        x += wdt + gap
    return im


def header(lines, size=68):
    rows = [rich_line(l, size) for l in lines]
    wmax = max(r.width for r in rows)
    out = Image.new("RGBA", (wmax, sum(r.height for r in rows) - 10 * (len(rows) - 1)), (0, 0, 0, 0))
    y = 0
    for r in rows:
        out.alpha_composite(r, ((wmax - r.width) // 2, y))
        y += r.height - 10
    if out.width > 1000:
        out = out.resize((1000, round(out.height * 1000 / out.width)), Image.LANCZOS)
    return out


def caption_word(word):
    w = re.sub(r"[^\w'?!\-]", "", word).upper().replace("-", "")
    w = re.sub(r"^BOXABLE", "BOXABL", w)
    return w


def arrow_img(length=150):
    im = Image.new("RGBA", (length + 20, 110), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = [(10, 40), (length - 55, 40), (length - 55, 10), (length + 10, 55), (length - 55, 100),
           (length - 55, 70), (10, 70)]
    d.polygon(pts, fill=(235, 20, 20, 255), outline=(255, 255, 255, 255), width=6)
    return im


# ---------------- footage ----------------
def read_shot(video, start, dur):
    p = subprocess.run([
        "ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-i", os.path.join(FOOT, f"boxabl_phase2_{video}.mp4"),
        "-t", f"{dur + 0.2:.3f}", "-vf", f"fps={FPS},scale={SRC_W}:{SRC_H}", "-f", "rawvideo",
        "-pix_fmt", "rgb24", "-"], capture_output=True, check=True)
    a = np.frombuffer(p.stdout, np.uint8)
    n = len(a) // (SRC_W * SRC_H * 3)
    frames = a[: n * SRC_W * SRC_H * 3].reshape(n, SRC_H, SRC_W, 3)
    need = int(round(dur * FPS))
    if n < need:  # pad by holding the last frame
        frames = np.concatenate([frames, np.repeat(frames[-1:], need - n, 0)])
    return frames[:need]


def compose(src, t_in_shot, cx, zoom, fit=False):
    """src: HxWx3 frame. Returns the full 1080x1920 frame (blurred bg + sharp band)."""
    img = Image.fromarray(src)
    # background: cover-scale, blurred at low res
    small = img.resize((480, 270), Image.BILINEAR)
    bw = 270 * 9 / 16
    bx = (480 - bw) / 2
    bg = small.crop((int(bx), 0, int(bx + bw), 270)).filter(ImageFilter.GaussianBlur(9))
    bg = bg.resize((W, H), Image.BILINEAR)
    bg = fx.darken(bg, 0.72)
    if fit:  # whole 16:9 frame (e.g. title cards with text), centred in the band
        fw = int(W * zoom)
        fh = round(fw * SRC_H / SRC_W)
        full = img.resize((fw, fh), Image.BICUBIC).crop(((fw - W) // 2, 0, (fw - W) // 2 + W, fh))
        bg.paste(full, (0, BAND_Y + (BAND_H - fh) // 2))
        return bg
    # band: 9:8 crop with punch/push zoom
    ch = SRC_H / zoom
    cw = ch * W / BAND_H
    x0 = min(max(cx * SRC_W - cw / 2, 0), SRC_W - cw)
    y0 = (SRC_H - ch) / 2
    band = img.transform((W, BAND_H), Image.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BICUBIC)
    bg.paste(band, (0, BAND_Y))
    return bg


# ---------------- audio ----------------
def build_audio(vo_path, dur, cuts, flashes, out):
    sr = fx.SR
    vo = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", vo_path, "-ac", "1", "-ar", str(sr),
                                       "-f", "f32le", "-"], capture_output=True, check=True).stdout, np.float32)
    m = fx.Mix(dur)
    bpm = 97.0
    beat = 60 / bpm
    # dark bed: B minor drone pads changing every 2 bars (Bm - G - Em - F#)
    chords = [[61.74, 123.47, 146.83, 185.0], [49.0, 98.0, 123.47, 146.83], [41.2, 82.41, 98.0, 123.47],
              [46.25, 92.5, 116.54, 138.59]]
    bar = beat * 4
    t, k = 0.0, 0
    while t < dur:
        seg = fx.pad_chord(min(bar * 2 + 0.6, dur - t + 0.6), chords[k % 4], amp=0.22, trem=0.25, seed=k)
        seg *= np.minimum(1, np.arange(len(seg)) / (0.08 * sr)).astype(np.float32)
        m.add(seg, t, 1.0)
        t += bar * 2
        k += 1
    # 808 + trap hats
    kick = fx.sfx_kick(0.6)
    hat = fx.sfx_hat(0.05)
    t, b = 0.0, 0
    while t < dur:
        if b % 8 in (0, 3, 6):
            m.add(np.tanh(kick * 2.2) * 0.8, t, 0.55)
        m.add(hat, t, 0.10)
        m.add(hat, t + beat / 2, 0.07)
        if b % 4 == 3:
            for j in range(3):
                m.add(hat, t + beat / 2 + j * beat / 6, 0.06)
        t += beat
        b += 1
    for c in cuts[1:]:
        m.add(fx.sfx_whoosh(0.32, up=False), max(0, c - 0.22), 0.16)
    for c in flashes:
        m.add(fx.sfx_whoosh(0.5), max(0, c - 0.45), 0.35)
        m.add(fx.sfx_boom(0.9), c, 0.35)
    m.add(fx.sfx_riser(0.6), 0, 0.15)
    music = m.buf.copy()
    # duck music under voice
    env = np.abs(vo)
    k = int(0.05 * sr)
    env = np.convolve(env, np.ones(k) / k, "same")
    duck = 1 - 0.45 * np.clip(env / (env.max() * 0.25 + 1e-9), 0, 1)
    n = min(len(music), len(duck))
    music[:n] *= duck[:n]
    mix = music * 0.55
    mix[: len(vo)] += vo[: len(mix)] * 1.0
    mm = fx.Mix(dur)
    mm.buf = mix.astype(np.float32)
    mm.write(out, dur)


# ---------------- render ----------------
def render(name):
    cfg = CLIPS[name]
    vo_path = os.path.join(ROOT, "vo", cfg["vo"])
    words = json.load(open(vo_path.rsplit(".", 1)[0] + ".words.json"))
    shots = cfg["shots"]
    dur = sum(s[2] for s in shots)
    cuts, t = [], 0.0
    for s in shots:
        cuts.append(round(t, 3))
        t += s[2]
    flashes = [cuts[i] for i in cfg.get("flash", [])]

    head = header(cfg["title"])
    logo = fx.logo("white", 300)
    arrow = arrow_img()
    word_imgs = {}
    for w in words:
        cw = caption_word(w["w"])
        if cw and cw not in word_imgs:
            col = (255, 214, 0) if cw in cfg.get("yellow", []) else "white"
            word_imgs[cw] = fx.text_img(cw, fx.F_BLACK, 76, fill=col, stroke=8, shadow=10, shadow_alpha=200)

    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    out = os.path.join(ROOT, "out", cfg["out"])
    wav = out + ".wav"
    build_audio(vo_path, dur, cuts, flashes, wav)
    enc = fx.Encoder(out, wav)
    f_global = 0
    for si, shot in enumerate(shots):
        video, start, sdur = shot[:3]
        opt = shot[3] if len(shot) > 3 else {}
        frames = read_shot(video, start, sdur)
        for fi, src in enumerate(frames):
            t = f_global / FPS
            u = fi / FPS
            punch = 1.0 + 0.14 * (1 - fx.ease_out(u / 0.2, 3))
            zoom = opt.get("zoom", 1.0) * punch * (1 + 0.035 * u)
            fr = compose(src, u, opt.get("cx", 0.5), zoom, opt.get("fit", False)).convert("RGBA")
            a = None
            if si in cfg.get("flash", []) and u < 0.14:
                a = np.asarray(fr).astype(np.float32)
                k = (1 - u / 0.14) * 0.9
                a[..., :3] = a[..., :3] + (255 - a[..., :3]) * k
            if t < 0.12:  # hook flash, tinted like the reference's colour flash
                a = np.asarray(fr).astype(np.float32) if a is None else a
                k = (1 - t / 0.12) * 0.7
                a[..., :3] = a[..., :3] * (1 - k) + np.array([255, 230, 40]) * k
            if a is not None:
                fr = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
            # pinned header + logo
            fx.paste(fr, head, W / 2, BAND_Y - 40 - head.height / 2)
            fx.paste(fr, logo, W / 2, BAND_Y + BAND_H + 70, alpha=0.95)
            # arrow
            if "arrow" in opt:
                ax, ay, ang = opt["arrow"]
                bob = 14 * math.sin(t * 9)
                pop = fx.back_out(u / 0.18)
                rad = math.radians(ang)
                tipx = ax * W - math.cos(rad) * (95 + bob)
                tipy = BAND_Y + ay * BAND_H - math.sin(rad) * (95 + bob)
                fx.paste(fr, arrow, tipx, tipy, scale=0.5 + 0.5 * pop, rot=-ang)
            # one word at a time
            cur = None
            for w in words:
                if w["s"] - 0.03 <= t:
                    cur = w
            if cur and t < cur["e"] + 0.35:
                cw = caption_word(cur["w"])
                if cw:
                    s = fx.back_out((t - cur["s"]) / 0.12, 2.5)
                    fx.paste(fr, word_imgs[cw], W / 2, BAND_Y + BAND_H * 0.62, scale=0.7 + 0.3 * s)
            enc.write(fr.convert("RGB"))
            f_global += 1
    enc.close()
    os.remove(wav)
    print(f"wrote {out} ({dur:.1f}s)")


if __name__ == "__main__":
    names = list(CLIPS) if (len(sys.argv) < 2 or sys.argv[1] == "all") else sys.argv[1:]
    for n in names:
        render(n)
