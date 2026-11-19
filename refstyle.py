#!/usr/bin/env python3
"""Reference-style renderer (modelled on the clip the user shared, not a copy of it).

  * black 1080x1920 canvas, the footage in a 1080x1080 square in the middle (auto-reframed on faces)
  * small lowercase hook above the square: white, one red keyword, an emoji
  * one-word-at-a-time captions in the lower part of the square, sentence case, soft shadow
  * a light cinematic grade (contrast, saturation, warmth, subtle vignette)
  * one emoji pop on the punchline, one white "backflash" on a key cut
  * captions and emoji are face-aware: if they would land on a face they move off it
    (caption drops below the square, emoji moves to the free side / below)
  * swear words are cut out of the audio and left out of the captions (like the reference)
"""
import math
import os
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import framed
from editor import FPS, H, SRC_H, SRC_W, W, ease_out_back, font, is_swear, layout_timeline, mix_audio, place

framed.WIN_AR = 1.0                     # square window for the face planner
SQ = 1080
SQ_Y0 = 420
SQ_Y1 = SQ_Y0 + SQ
CAP_Y = SQ_Y0 + int(SQ * 0.70)          # default caption centre (inside the square, lower part)
CAP_Y_BELOW = SQ_Y1 + 95                # fallback: on the black under the square
HOOK_Y = SQ_Y0 - 95
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
RED = (255, 59, 48)
FIT_Z = 1.3                             # two-shots: enlarge the 16:9 picture inside the square (both people stay in)
WHITE = (255, 255, 255)


# --------------------------------------------------------------------------- text

_emoji_cache = {}


def emoji_img(ch, size):
    key = (ch, size)
    if key not in _emoji_cache:
        f = ImageFont.truetype(EMOJI_FONT, 109)
        im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((0, 0), ch, font=f, embedded_color=True)
        im = im.crop(im.getbbox())
        _emoji_cache[key] = im.resize((size, int(im.height * size / im.width)), Image.LANCZOS)
    return _emoji_cache[key]


def is_emoji(tok):
    return any(ord(c) > 0x2600 for c in tok)


def rich_text(segments, size=52, max_w=980, line_gap=1.18):
    """segments: [(text, colour)]; emoji tokens are drawn with the colour emoji font."""
    f = font("montserrat-xb", size)
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    toks = []
    for text, col in segments:
        for i, w in enumerate(text.split(" ")):
            if w:
                toks.append((w, col))
    space = tmp.textlength(" ", font=f)
    widths = [size * 1.05 if is_emoji(w) else tmp.textlength(w, font=f) for w, _ in toks]
    lines, cur, cw = [], [], 0
    for t, wd in zip(toks, widths):
        if cur and cw + space + wd > max_w:
            lines.append((cur, cw))
            cur, cw = [], 0
        cw += (space if cur else 0) + wd
        cur.append((t, wd))
    if cur:
        lines.append((cur, cw))
    lh = int(size * line_gap)
    img = Image.new("RGBA", (max_w + 40, lh * len(lines) + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for li, (ln, lw) in enumerate(lines):
        x = (img.width - lw) / 2
        y = 12 + li * lh
        for (w, col), wd in ln:
            if is_emoji(w):
                e = emoji_img(w, int(size * 1.05))
                img.alpha_composite(e, (int(x), int(y + size * 0.05)))
            else:
                d.text((x, y), w, font=f, fill=col)
            x += wd + space
    return img.crop(img.getbbox())


_word_cache = {}


def word_img(word, size=66):
    if word not in _word_cache:
        f = font("montserrat-xb", size)
        tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        tw = int(tmp.textlength(word, font=f)) + 40
        img = Image.new("RGBA", (tw, size + 40), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((20, 12), word, font=f, fill=WHITE, stroke_width=3, stroke_fill=(0, 0, 0))
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.paste((0, 0, 0, 170), mask=img.split()[3])
        sh = sh.filter(ImageFilter.GaussianBlur(7))
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        out.alpha_composite(sh, (0, 4))
        out.alpha_composite(img)
        _word_cache[word] = out
    return _word_cache[word]


# --------------------------------------------------------------------------- geometry

def face_boxes_out(shot, k, mode, cx, cy, z):
    """faces of plan frame k mapped to canvas coordinates (padded a little)."""
    faces = getattr(shot, "_faces", None)
    if not faces:
        return []
    fs = faces[min(k, len(faces) - 1)]
    out = []
    if mode == "fit":
        s = SQ * z * FIT_Z / SRC_W
        ox = (SQ - SRC_W * s) / 2
        oy = SQ_Y0 + (SQ - SRC_H * s) / 2
        for fx, fy, fw, fh, _ in fs:
            out.append((ox + fx * s - fw * s * 0.7, oy + fy * s - fh * s * 0.7, fw * s * 1.4, fh * s * 1.5))
        return out
    ch = SRC_H / z
    cw = ch
    x0 = min(max(cx - cw / 2, 0), SRC_W - cw)
    y0 = min(max(cy - ch / 2, 0), SRC_H - ch)
    s = SQ / cw
    for fx, fy, fw, fh, _ in fs:
        X, Y = (fx - x0) * s, SQ_Y0 + (fy - y0) * s
        out.append((X - fw * s * 0.7, Y - fh * s * 0.7, fw * s * 1.4, fh * s * 1.55))
    return out


def overlaps(box, faces):
    x, y, w, h = box
    for fx, fy, fw, fh in faces:
        if x < fx + fw and fx < x + w and y < fy + fh and fy < y + h:
            return True
    return False


def window(im, mode, cx, cy, z, shake):
    if mode == "fit":
        sq = im.resize((SQ // 8, SQ // 8), Image.BILINEAR, box=(SRC_W / 2 - SRC_H / 2, 0, SRC_W / 2 + SRC_H / 2, SRC_H))
        sq = sq.filter(ImageFilter.GaussianBlur(4)).resize((SQ, SQ), Image.BILINEAR)
        sq = Image.eval(sq, lambda v: int(v * 0.35))
        fw = int(SQ * z * FIT_Z)
        fh = int(fw * SRC_H / SRC_W)
        sq.paste(im.resize((fw, fh), Image.BICUBIC), (int((SQ - fw) / 2 + shake[0]), int((SQ - fh) / 2 + shake[1])))
        return sq
    ch = SRC_H / z
    cx += shake[0] * ch / SQ
    cy += shake[1] * ch / SQ
    x0 = min(max(cx - ch / 2, 0), SRC_W - ch)
    y0 = min(max(cy - ch / 2, 0), SRC_H - ch)
    return im.resize((SQ, SQ), Image.BICUBIC, box=(x0, y0, x0 + ch, y0 + ch))


def _vig():
    yy, xx = np.mgrid[0:SQ, 0:SQ].astype(np.float32)
    d = np.sqrt(((xx - SQ / 2) / (SQ / 2)) ** 2 + ((yy - SQ / 2) / (SQ / 2)) ** 2) / math.sqrt(2)
    return (1 - 0.28 * np.clip((d - 0.45) / 0.55, 0, 1) ** 1.6)[..., None]


VIG = _vig()


def grade(a):
    """light cinematic grade: lift dark scenes, contrast, saturation, warmth, vignette."""
    lum = float(np.mean(a[::8, ::8]))
    if lum < 70:                                  # dark interview set: gentle exposure lift
        g = min(1.45, 70 / max(lum, 20))
        a = 255 * (a / 255) ** (1 / g)
    a = (a - 128) * 1.10 + 128
    g = a @ np.array([0.299, 0.587, 0.114], np.float32)
    a = g[..., None] + (a - g[..., None]) * 1.18
    a *= np.array([1.03, 1.0, 0.95], np.float32)
    return a * VIG


# --------------------------------------------------------------------------- captions

def word_track(v, src):
    """[(t_start, t_end, word)] one word at a time, swears left out."""
    items = []
    for s in v.shots:
        if not s.captions:
            continue
        ws = [w for w in src.words if s.src_in - 0.05 <= w[0] < s.src_out and w[2]]
        for i, (a, b, w) in enumerate(ws):
            if is_swear(w):
                continue
            t0 = s.t0 + (max(a, s.src_in) - s.src_in) / s.speed
            nxt = ws[i + 1][0] if i + 1 < len(ws) else s.src_out
            t1 = s.t0 + (min(max(b + 0.15, a + 0.25), nxt, s.src_out) - s.src_in) / s.speed
            items.append((t0, max(t1, t0 + 0.12), w.strip(" ")))
    return items


# --------------------------------------------------------------------------- render

def render(v, src, out_path, hook, emojis=(), preview=False):
    """hook: rich-text segments; emojis: [(t, char, dur)]."""
    total = layout_timeline(v)
    nframes = int(round(total * FPS))
    words = word_track(v, src)
    rng = np.random.default_rng(5)
    plans = [framed.analyse(src, s) for s in v.shots]
    hook_img = rich_text(hook)

    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "a.wav")
        mix_audio(v, src, total, wav)
        enc = subprocess.Popen(
            ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
             "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a",
             "-c:v", "libx264", "-preset", "veryfast" if preview else "medium", "-crf", "18", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
             "-movflags", "+faststart", "-shortest", out_path], stdin=subprocess.PIPE)
        fi = 0
        moved = 0
        placed = {}
        for s, plan in zip(v.shots, plans):
            vin = s.src_in if s.v_in is None else s.v_in
            gen = src.frames(vin, vin + s.src_out - s.src_in, s.speed)
            n_tot = int(round((s.t0 + s.dur) * FPS)) - int(round(s.t0 * FPS))
            last = None
            for k in range(n_tot):
                if fi >= nframes:
                    break
                if k < len(plan):
                    last = next(gen, last)
                t = fi / FPS
                kk = min(k, len(plan) - 1)
                mode, cx, cy = plan[kk]
                punch, shake, tint, rgb, bw = framed.fx_state(v, t, rng)
                z = (s.zoom if mode == "crop" else 1.0) * punch
                win = np.asarray(window(Image.fromarray(last), mode, cx, cy, z, shake)).astype(np.float32)
                win = grade(win)
                for col, alpha in tint:
                    if alpha > 0 and col == (255, 255, 255):
                        win = win + (255 - win) * min(alpha, 1)
                canvas = Image.new("RGB", (W, H), (0, 0, 0))
                canvas.paste(Image.fromarray(np.clip(win, 0, 255).astype(np.uint8)), (0, SQ_Y0))
                frame = canvas.convert("RGBA")
                faces = face_boxes_out(s, kk, mode, cx, cy, z)

                place(frame, hook_img, W / 2, HOOK_Y, scale=min(1.0, (W - 60) / hook_img.width))
                for w0, w1, w in words:
                    if w0 <= t < w1:
                        im = word_img(w)
                        y = CAP_Y
                        if overlaps((W / 2 - im.width / 2, y - im.height / 2, im.width, im.height), faces):
                            y = CAP_Y_BELOW
                            moved += 1
                        sc = 0.9 + 0.1 * ease_out_back((t - w0) / 0.1)
                        place(frame, im, W / 2, y, scale=sc)
                        placed.setdefault(fi, []).append((W / 2 - im.width / 2, y - im.height / 2 + 12, im.width, im.height - 24))
                        break
                for et, ch, dur in emojis:
                    if et <= t < et + dur:
                        e = emoji_img(ch, 190)
                        a = t - et
                        sc = ease_out_back(a / 0.2) * (1 + 0.04 * math.sin(a * 9))
                        al = min(1.0, (et + dur - t) / 0.15)
                        spots = [(W / 2, CAP_Y - 150), (W * 0.80, SQ_Y0 + 230), (W * 0.20, SQ_Y0 + 230),
                                 (W / 2, SQ_Y1 + 230)]
                        for ex, ey in spots:
                            if ey > SQ_Y1 or not overlaps((ex - 110, ey - 110, 220, 220), faces):
                                break
                        place(frame, e, ex, ey, scale=sc, alpha=al)
                        placed.setdefault(fi, []).append((ex - 95, ey - 95, 190, 190))
                enc.stdin.write(frame.convert("RGB").tobytes())
                fi += 1
        enc.stdin.close()
        enc.wait()
    hb = (W / 2 - hook_img.width / 2, HOOK_Y - hook_img.height / 2, hook_img.width, hook_img.height)
    return total, moved, placed, hb


def qa(path, placed, hook_box, step=4):
    """re-detect faces on the rendered video (every `step` frames) and check them against every text /
    emoji box that was actually drawn on that frame, plus the hook."""
    import cv2
    det = cv2.FaceDetectorYN.create(framed.MODEL, "", (W // 2, H // 2), 0.8)
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-vf", f"select='not(mod(n\\,{step}))',scale={W // 2}:{H // 2}",
                                   "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"])
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H // 2, W // 2, 3)
    hits, nf = [], 0
    for i, f in enumerate(fr):
        fi = i * step
        _, res = det.detect(f)
        boxes = placed.get(fi, []) + [hook_box]
        for r in (res if res is not None else []):
            x, y, w, h = [float(q) * 2 for q in r[:4]]
            if not (SQ_Y0 <= y + h / 2 <= SQ_Y1):
                continue
            nf += 1
            if overlaps((x, y, w, h), boxes):
                hits.append((round(fi / FPS, 2), (int(x), int(y), int(w), int(h))))
    return nf, hits
