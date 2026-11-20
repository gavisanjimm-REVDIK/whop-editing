#!/usr/bin/env python3
"""Renderer modelled on the "Clip The Pod" reference (not a copy of it).

  * square footage on black (slightly lower than refstyle), small one-colour hook just above it, with emoji
  * an AI narrator intro over quick b-roll cuts of the subject (original audio dipped underneath)
  * a red arrow pointing at the subject's face for the first second
  * ONE BIG UPPERCASE WORD captions, cycling green / yellow / cyan / white with a thick outline
  * a trap beat under everything (ducked under speech), a riser into the punchline and an 808 hit on it
  * captions, arrow and emoji are face-aware; every drawn box is re-checked against faces in the output
"""
import math
import os
import subprocess
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import framed
import refstyle
from editor import FPS, H, W, ease_out_back, font, is_swear, layout_timeline, mix_audio, place

refstyle.SQ_Y0 = 500
refstyle.SQ_Y1 = refstyle.SQ_Y0 + refstyle.SQ
SQ, SQ_Y0, SQ_Y1 = refstyle.SQ, refstyle.SQ_Y0, refstyle.SQ_Y1
CAP_Y = SQ_Y0 + int(SQ * 0.66)
CAP_Y_BELOW = SQ_Y1 + 110
CAP_Y_FIXED = SQ_Y1 + 120                   # phrase mode: always here, on the black under the video
HOOK_Y = SQ_Y0 - 70
CAPTION_MODE = "word"                   # "word": one word, face-aware | "phrase": fixed spot under the video
EMOJI_ON_TOP = False                    # batch 7 sets this: emoji pops go above the square
CYCLE = [(90, 255, 110), (255, 232, 30), (40, 220, 255), (255, 255, 255)]


_live_det = None


def live_faces(win_rgb):
    """faces detected directly on the rendered square (catches motion-blurred close-ups the planning
    pass missed), returned in canvas coordinates with the same padding as refstyle.face_boxes_out."""
    global _live_det
    if _live_det is None:
        _live_det = cv2.FaceDetectorYN.create(framed.MODEL, "", (360, 360), 0.6)
    small = cv2.resize(cv2.cvtColor(win_rgb, cv2.COLOR_RGB2BGR), (360, 360))
    _, res = _live_det.detect(small)
    out = []
    for r in (res if res is not None else []):
        x, y, w, h = [float(q) * SQ / 360 for q in r[:4]]
        cx, cy = x + w / 2, SQ_Y0 + y + h / 2
        out.append((cx - w * 0.7, cy - h * 0.7, w * 1.4, h * 1.55))
    return out


_phrase_cache = {}


def phrase_img(words, active, col, size=84):
    """2-3 word phrase, white with the spoken word in colour; fixed width-safe layout."""
    key = (tuple(words), active, col, size)
    if key not in _phrase_cache:
        f = font("montserrat", size)
        tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        sp = tmp.textlength(" ", font=f)
        widths = [tmp.textlength(w, font=f) for w in words]
        tw = int(sum(widths) + sp * (len(words) - 1)) + 60
        img = Image.new("RGBA", (tw, size + 60), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        x = 30
        for i, (w, wd) in enumerate(zip(words, widths)):
            d.text((x, 18), w, font=f, fill=col if i == active else (255, 255, 255), stroke_width=9,
                   stroke_fill=(0, 0, 0))
            x += wd + sp
        _phrase_cache[key] = img
    return _phrase_cache[key]


def phrases(words, max_words=3, max_chars=20):
    """split the word track into sentences (or at pauses), then cut each sentence into evenly sized
    chunks of at most 3 words, so there are no dangling single words ("I GOTTA DO | IT")."""
    sents, cur = [], []
    for w in words:
        if cur and (w[0] - cur[-1][1] > 0.45 or cur[-1][4]):
            sents.append(cur)
            cur = []
        cur.append(w)
    if cur:
        sents.append(cur)
    out = []
    for snt in sents:
        n = len(snt)
        k = -(-n // max_words)
        while True:                                    # even split: 9 -> 3+3+3, 5 -> 3+2, 4 -> 2+2
            sizes = [n // k + (1 if i < n % k else 0) for i in range(k)]
            chunks, j = [], 0
            for sz in sizes:
                chunks.append(snt[j:j + sz])
                j += sz
            if k >= n or all(sum(len(y[2]) + 1 for y in c) - 1 <= max_chars for c in chunks):
                break
            k += 1
        out += chunks
    return out


_cap_cache = {}


def cap_img(word, col, size=96):
    key = (word, col, size)
    if key not in _cap_cache:
        f = font("montserrat", size)
        tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        tw = int(tmp.textlength(word, font=f)) + 60
        img = Image.new("RGBA", (tw, size + 60), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((30, 18), word, font=f, fill=col, stroke_width=10, stroke_fill=(0, 0, 0))
        _cap_cache[key] = img
    return _cap_cache[key]


def arrow_img(size=170):
    """bold red arrow pointing down-right."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size
    pts = [(0.10 * s, 0.22 * s), (0.22 * s, 0.10 * s), (0.66 * s, 0.54 * s), (0.78 * s, 0.42 * s),
           (0.86 * s, 0.86 * s), (0.42 * s, 0.78 * s), (0.54 * s, 0.66 * s)]
    d.polygon(pts, fill=(235, 30, 30, 255), outline=(255, 255, 255, 255))
    d.line(pts + [pts[0]], fill=(255, 255, 255, 255), width=5)
    return im


ARROW = arrow_img()


def track_words(v, src):
    """[(t0, t1, word)] for the conversation shots + the narrator words (v.vo_words, output time)."""
    items = list(getattr(v, "vo_words", []))
    for s in v.shots:
        if not s.captions:
            continue
        ws = [w for w in src.words if s.src_in - 0.05 <= w[0] < s.src_out and w[2]]
        for i, (a, b, w) in enumerate(ws):
            if is_swear(w):
                if w.rstrip()[-1:] in ".?!" and items and not items[-1][2].rstrip()[-1:] in ".?!":
                    items[-1] = (items[-1][0], items[-1][1], items[-1][2] + ".")
                continue
            t0 = s.t0 + (max(a, s.src_in) - s.src_in) / s.speed
            nxt = ws[i + 1][0] if i + 1 < len(ws) else s.src_out
            t1 = s.t0 + (min(max(b + 0.12, a + 0.22), nxt, s.src_out) - s.src_in) / s.speed
            items.append((t0, max(t1, t0 + 0.12), w))
    items.sort()
    out = []
    for k, (a, b, w) in enumerate(items):
        clean = w.strip(" ,.?!\"").upper()
        if clean:
            out.append((a, b, clean, CYCLE[k % len(CYCLE)], w.rstrip()[-1:] in ".?!"))
    return out


def render(v, src, out_path, hook, emojis=(), arrow_until=1.0, preview=False):
    total = layout_timeline(v)
    nframes = int(round(total * FPS))
    words = track_words(v, src)
    groups = phrases(words)
    if CAPTION_MODE == "phrase":                        # hold each phrase until the next one starts
        for i in range(len(groups) - 1):
            nxt = groups[i + 1][0][0]
            last = groups[i][-1]
            if nxt - last[1] < 0.6:
                groups[i][-1] = (last[0], nxt, *last[2:])
    rng = np.random.default_rng(9)
    plans = [framed.analyse(src, s) for s in v.shots]
    hook_img = refstyle.rich_text(hook, size=46)

    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "a.wav")
        mix_audio(v, src, total, wav)
        enc = subprocess.Popen(
            ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
             "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a",
             "-c:v", "libx264", "-preset", "veryfast" if preview else "medium", "-crf", "18", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
             "-movflags", "+faststart", "-shortest", out_path], stdin=subprocess.PIPE)
        fi, moved, placed = 0, 0, {}
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
                win = np.asarray(refstyle.window(Image.fromarray(last), mode, cx, cy, z, shake)).astype(np.float32)
                win = refstyle.grade(win)
                for col, alpha in tint:
                    if alpha > 0 and col == (255, 255, 255):
                        win = win + (255 - win) * min(alpha, 1)
                canvas = Image.new("RGB", (W, H), (0, 0, 0))
                win8 = np.clip(win, 0, 255).astype(np.uint8)
                canvas.paste(Image.fromarray(win8), (0, SQ_Y0))
                frame = canvas.convert("RGBA")
                faces = refstyle.face_boxes_out(s, kk, mode, cx, cy, z) + live_faces(win8)

                place(frame, hook_img, W / 2, HOOK_Y, scale=min(1.0, (W - 60) / hook_img.width))
                boxes = []
                central = [b for b in faces if 150 < b[0] + b[2] / 2 < W - 150]   # ignore cut-off people at the edges
                if t < arrow_until and central:                  # red arrow at the subject's face
                    fx, fy, fw, fh = max(central, key=lambda b: b[2] * b[3])
                    ax = max(90, fx - 95)                       # whole arrow sits left of the face,
                    ay = max(SQ_Y0 + 60, fy - 90)               # tip pointing in at it
                    bob = 12 * math.sin(t * 14)
                    place(frame, ARROW, ax + bob, ay + bob, scale=ease_out_back(t / 0.2))
                    boxes.append((ax - 85, ay - 85, 170, 170))
                if CAPTION_MODE == "phrase":
                    for ph in groups:
                        p0, p1 = ph[0][0], max(ph[-1][1], ph[0][0] + 0.35)
                        if p0 <= t < p1:
                            act = max([i for i, x in enumerate(ph) if x[0] <= t + 0.02] or [0])
                            im = phrase_img([x[2] for x in ph], act, ph[act][3])
                            sc = min(1.0, (W - 60) / im.width) * (0.92 + 0.08 * ease_out_back((t - p0) / 0.1))
                            place(frame, im, W / 2, CAP_Y_FIXED, scale=sc)
                            boxes.append((W / 2 - im.width * sc / 2, CAP_Y_FIXED - im.height * sc / 2 + 15,
                                          im.width * sc, im.height * sc - 30))
                            break
                for w0, w1, w, col, _end in (words if CAPTION_MODE == "word" else []):
                    if w0 <= t < w1:
                        im = cap_img(w, col)
                        y = CAP_Y
                        if refstyle.overlaps((W / 2 - im.width / 2, y - im.height / 2, im.width, im.height), faces):
                            y = CAP_Y_BELOW
                            moved += 1
                        sc = min(1.0, (W - 60) / im.width) * (0.85 + 0.15 * ease_out_back((t - w0) / 0.08))
                        place(frame, im, W / 2, y, scale=sc)
                        boxes.append((W / 2 - im.width * sc / 2, y - im.height * sc / 2 + 15, im.width * sc,
                                      im.height * sc - 30))
                        break
                for et, ch, dur in emojis:
                    if et <= t < et + dur:
                        e = refstyle.emoji_img(ch, 190)
                        a = t - et
                        sc = ease_out_back(a / 0.2) * (1 + 0.04 * math.sin(a * 9))
                        al = min(1.0, (et + dur - t) / 0.15)
                        if EMOJI_ON_TOP:                            # empty black band above the hook: never on the video
                            ex, ey = W / 2, HOOK_Y - 175
                        else:
                            for ex, ey in [(W / 2, CAP_Y - 170), (W * 0.8, SQ_Y0 + 220), (W * 0.2, SQ_Y0 + 220),
                                           (W / 2, SQ_Y1 + 250)]:
                                if ey > SQ_Y1 or not refstyle.overlaps((ex - 110, ey - 110, 220, 220), faces):
                                    break
                        place(frame, e, ex, ey, scale=sc, alpha=al)
                        boxes.append((ex - 95, ey - 95, 190, 190))
                if boxes:
                    placed[fi] = boxes
                enc.stdin.write(frame.convert("RGB").tobytes())
                fi += 1
        enc.stdin.close()
        enc.wait()
    hb = (W / 2 - hook_img.width / 2, HOOK_Y - hook_img.height / 2, hook_img.width, hook_img.height)
    return total, moved, placed, hb
