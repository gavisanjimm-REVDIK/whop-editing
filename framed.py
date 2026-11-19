#!/usr/bin/env python3
"""Clean "framed" layout renderer with face-aware auto-reframing.

Canvas 1080x1920, split into three fixed zones so graphics never sit on top of the picture:

    0    – 360   TOP band     hook title
    360  – 1560  WINDOW       the footage (1080x1200)
    1560 – 1920  BOTTOM band  captions (row 1) and labels / stamps (row 2)

Inside the window every source scene is reframed automatically:
  * one person  -> 0.9:1 crop centred on their face (static if they stay put, smooth pan if they walk)
  * two people far apart (interview two-shot) -> the full 16:9 picture, so nobody gets cut off
Faces come from OpenCV's YuNet detector, run on a 640x360 proxy of each shot before rendering.
Effects (punch-in, shake, flashes, tints) only touch the window; text only lives in the bands.
"""
import math
import os
import subprocess
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from editor import (Fx, FPS, H, SRC_H, SRC_W, W, build_captions, ease_out_back, layout_timeline, mix_audio,
                    place, render_text)

ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(ROOT, "assets", "models", "face_detection_yunet_2023mar.onnx")

TOP_H = 360
WIN_Y0, WIN_Y1 = 360, 1560
WIN_H = WIN_Y1 - WIN_Y0
WIN_AR = W / WIN_H                      # 0.9
# vertical centres (fraction of H) for text rows
Y_HOOK = 175 / H
Y_CAP = 1652 / H
Y_LABEL = 1820 / H

FIT_ZOOM = 1.0                          # two-shots: show the whole 16:9 frame (keeps lower-thirds intact)
PW, PH = 640, 360                       # analysis proxy size
PS = SRC_W / PW                         # proxy -> source scale


# --------------------------------------------------------------------------- analysis

_det = None


def detector():
    global _det
    if _det is None:
        _det = cv2.FaceDetectorYN.create(MODEL, "", (PW, PH), 0.72)
    return _det


def proxy_frames(path, t_in, t_out, speed):
    dur = t_out - t_in
    n = int(round(dur / speed * FPS))
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t_in:.3f}", "-t", f"{dur + 0.2:.3f}", "-i", path,
           "-vf", f"setpts=(PTS-STARTPTS)/{speed},fps={FPS},scale={PW}:{PH}", "-frames:v", str(n),
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    raw = subprocess.check_output(cmd)
    fr = np.frombuffer(raw, np.uint8).reshape(-1, PH, PW, 3)
    if len(fr) < n:
        fr = np.concatenate([fr, np.repeat(fr[-1:], n - len(fr), 0)])
    return fr[:n]


def analyse(src, shot):
    """per-frame plan [(mode, cx, cy)] for a shot, in source pixels."""
    vin = shot.src_in if shot.v_in is None else shot.v_in
    fr = proxy_frames(src.path, vin, vin + shot.src_out - shot.src_in, shot.speed)
    if shot.reverse:
        fr = fr[::-1]
    det = detector()
    faces, small = [], []
    for f in fr:
        _, res = det.detect(f)
        boxes = []
        if res is not None:
            for r in res:
                x, y, w, h, sc = r[0], r[1], r[2], r[3], r[-1]
                if h * PS >= 34:                         # ignore tiny background faces
                    boxes.append(((x + w / 2) * PS, (y + h / 2) * PS, w * PS, h * PS, sc))
        faces.append(boxes)
        small.append(cv2.cvtColor(cv2.resize(f, (64, 36)), cv2.COLOR_BGR2GRAY).astype(np.float32))
    # scene cuts
    scenes, cur = [], 0
    for i in range(len(fr)):
        if i and np.mean(np.abs(small[i] - small[i - 1])) > 28:
            cur += 1
        scenes.append(cur)

    plan = [None] * len(fr)
    for sid in range(cur + 1):
        idx = [i for i, s in enumerate(scenes) if s == sid]
        plan_scene(shot, idx, faces, plan)
    return plan


def plan_scene(shot, idx, faces, plan):
    zoom = shot.zoom
    ch = SRC_H / zoom
    cw = ch * WIN_AR
    n = len(idx)
    two = 0
    for i in idx:
        xs = sorted(b[0] for b in faces[i])
        if len(xs) >= 2 and xs[-1] - xs[0] > cw * 0.62:
            two += 1
    if shot.layout == "fit" or (shot.layout != "crop" and two >= 0.35 * n):
        for i in idx:
            plan[i] = ("fit", SRC_W / 2, SRC_H / 2)
        return
    # primary face per frame: biggest, but stick with the previous one if it is close
    xs, ys = np.full(n, np.nan), np.full(n, np.nan)
    prev = None
    for k, i in enumerate(idx):
        bs = faces[i]
        if not bs:
            continue
        if prev is not None:
            near = [b for b in bs if abs(b[0] - prev[0]) < cw * 0.35]
            bs = near or bs
        b = max(bs, key=lambda b: b[3])
        prev = b
        xs[k], ys[k] = b[0], b[1]
    ok = ~np.isnan(xs)
    if ok.sum() < max(3, 0.15 * n):                     # nobody found: use the shot's hint
        for i in idx:
            plan[i] = ("crop", shot.cx, shot.cy)
        return
    t = np.arange(n)
    xs = np.interp(t, t[ok], xs[ok])
    ys = np.interp(t, t[ok], ys[ok])
    spread = np.percentile(xs, 90) - np.percentile(xs, 10)
    if spread < cw * 0.22:                               # subject stays put: locked-off framing
        xs[:] = np.median(xs)
        ys[:] = np.median(ys)
    else:                                                # subject moves: smooth pan
        k = max(3, int(FPS * 0.9)) | 1
        pad = k // 2
        ker = np.ones(k) / k
        xs = np.convolve(np.pad(xs, pad, mode="edge"), ker, "valid")
        ys = np.convolve(np.pad(ys, pad, mode="edge"), ker, "valid")
    for k2, i in enumerate(idx):
        cx = float(xs[k2])
        cy = float(ys[k2]) + ch * (0.5 - 0.30)             # face sits ~30% down the window
        plan[i] = ("crop", cx, cy)


# --------------------------------------------------------------------------- render

def _bg(im):
    """dark blurred full-canvas background from a source frame."""
    b = im.resize((W // 8, H // 8), Image.BILINEAR, box=(SRC_W / 2 - 304, 0, SRC_W / 2 + 304, SRC_H))
    b = b.filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR)
    return Image.eval(b, lambda v: int(v * 0.30))


def _vig():
    yy, xx = np.mgrid[0:WIN_H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - WIN_H / 2) / (WIN_H / 2)) ** 2) / math.sqrt(2)
    return np.clip((d - 0.35) / 0.65, 0, 1)[..., None] ** 1.5


WIN_VIG = _vig()


def render_window(im, mode, cx, cy, z, shake):
    if mode == "fit":
        fw = int(W * z * FIT_ZOOM)
        fh = int(fw * SRC_H / SRC_W)
        fg = im.resize((fw, fh), Image.BICUBIC)
        win = _bg(im).crop((0, WIN_Y0, W, WIN_Y1))
        win.paste(fg, (int((W - fw) / 2 + shake[0]), int((WIN_H - fh) / 2 + shake[1])))
        return win
    ch = SRC_H / z
    cw = ch * WIN_AR
    cx += shake[0] * cw / W
    cy += shake[1] * ch / WIN_H
    x0 = min(max(cx - cw / 2, 0), SRC_W - cw)
    y0 = min(max(cy - ch / 2, 0), SRC_H - ch)
    return im.resize((W, WIN_H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


def fx_state(v, t, rng):
    punch, shake, tint, rgb, bw = 1.0, [0.0, 0.0], [], 0, False
    for e in v.fx:
        dt = t - e.t
        if dt < 0 or dt > e.dur:
            continue
        x = dt / e.dur
        if e.kind == "punch":
            punch *= (1 + (e.amount - 1) * ease_out_back(x / 0.15)) if x <= 0.15 else 1 + (e.amount - 1) * (1 - x) ** 2
        elif e.kind == "hold":
            punch *= e.amount
        elif e.kind == "shake":
            a = 20 * e.amount * (1 - x)
            shake[0] += rng.uniform(-a, a)
            shake[1] += rng.uniform(-a, a)
        elif e.kind in ("flash", "green", "red", "tint"):
            col = {"flash": (255, 255, 255), "green": (20, 220, 90), "red": (235, 30, 40)}.get(e.kind, e.color)
            alpha = e.amount * ((1 - x) ** 1.6 if e.kind == "flash" else
                                0.55 * min(1, x / 0.12) * (1 - max(0, (x - 0.6) / 0.4)))
            tint.append((col, alpha))
        elif e.kind == "rgb":
            rgb = max(rgb, int(14 * e.amount * (1 - x)))
        elif e.kind == "bw":
            bw = True
    return punch, shake, tint, rgb, bw


def render(v, src, out_path, preview=False, accent=(255, 255, 255)):
    total = layout_timeline(v)
    nframes = int(round(total * FPS))
    caps, cst = build_captions(v, src)
    rng = np.random.default_rng(3)
    plans = [analyse(src, s) for s in v.shots]
    if v.emph:   # tiny punch-in on every keyword as it is spoken
        for _, _, words in caps:
            for wt, w in words:
                if w.strip(" ,.?!'\"").lower() in v.emph:
                    v.fx.append(Fx(wt, "punch", 0.35, 1.04))

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
        for s, plan in zip(v.shots, plans):
            vin = s.src_in if s.v_in is None else s.v_in
            gen = src.frames(vin, vin + s.src_out - s.src_in, s.speed)
            if s.reverse:
                gen = iter([f.copy() for f in gen][::-1])
            n_tot = int(round((s.t0 + s.dur) * FPS)) - int(round(s.t0 * FPS))
            last = None
            for k in range(n_tot):
                if fi >= nframes:
                    break
                if k < len(plan):
                    last = next(gen, last)
                t = fi / FPS
                mode, cx, cy = plan[min(k, len(plan) - 1)]
                punch, shake, tint, rgb, bw = fx_state(v, t, rng)
                bw = bw or (s.bw and k >= len(plan))
                im = Image.fromarray(last)
                canvas = _bg(im)
                z = (s.zoom if mode == "crop" else 1.0) * punch     # two-shots never get cropped
                win = np.asarray(render_window(im, mode, cx, cy, z, shake)).astype(np.float32)
                if bw:
                    g = win @ np.array([0.299, 0.587, 0.114], np.float32)
                    win = np.repeat(g[..., None], 3, 2)
                if rgb:
                    win[..., 0] = np.roll(win[..., 0], rgb, 1)
                    win[..., 2] = np.roll(win[..., 2], -rgb, 1)
                for col, alpha in tint:
                    if alpha <= 0:
                        continue
                    if col == (255, 255, 255):
                        win = win + (255 - win) * min(alpha, 1)
                    else:
                        c = np.array(col, np.float32)
                        win = win * (1 - alpha * 0.45) + c * alpha * 0.45
                        win = win * (1 - alpha * 0.6 * WIN_VIG) + c * alpha * 0.6 * WIN_VIG
                canvas.paste(Image.fromarray(np.clip(win, 0, 255).astype(np.uint8)), (0, WIN_Y0))
                frame = canvas.convert("RGBA")
                d = ImageDraw.Draw(frame)
                d.rectangle([0, WIN_Y0 - 4, W, WIN_Y0], fill=accent)
                d.rectangle([0, WIN_Y1, W, WIN_Y1 + 4], fill=accent)
                if v.progress_bar:
                    d.rectangle([0, 0, int(W * t / total), 10], fill=v.progress_bar)

                for c0, c1, words in caps:
                    if c0 <= t < c1:
                        active = max([i for i, (wt, _) in enumerate(words) if wt <= t + 0.02] or [0])
                        txt = " ".join(w for _, w in words)
                        im_t = render_text(txt, cst["size"], cst["font"], cst["fill"], (0, 0, 0), cst["stroke_w"],
                                           width=cst.get("width", 18), highlight=active, hl_fill=cst["hl"],
                                           emph=v.emph)
                        sc = min(1.0, (W - 60) / im_t.width) * (0.85 + 0.15 * ease_out_back((t - c0) / 0.12))
                        place(frame, im_t, W / 2, H * cst["y"], scale=sc)
                for tx in v.texts:
                    if tx.t0 <= t < tx.t1:
                        im_t = render_text(tx.text, tx.size, tx.font, tx.fill, tx.stroke, tx.stroke_w, tx.box, tx.width)
                        a = t - tx.t0
                        fit = min(1.0, (W - 50) / im_t.width)
                        sc, x, rot, al = fit, W * tx.x, tx.rot, 1.0
                        if tx.anim == "pop":
                            sc = fit * ease_out_back(a / 0.18)
                        elif tx.anim == "slide":
                            x = W * tx.x + (1 - ease_out_back(a / 0.25)) * W
                        elif tx.anim == "shake":
                            sc = fit * ease_out_back(a / 0.15)
                            rot += math.sin(a * 40) * 3 * max(0, 1 - a / 0.5)
                        if tx.t1 - t < 0.12 and tx.t1 - tx.t0 > 0.4:   # no fade on counter steps
                            al = (tx.t1 - t) / 0.12
                        place(frame, im_t, x, H * tx.y, scale=sc, rot=rot, alpha=al)
                enc.stdin.write(frame.convert("RGB").tobytes())
                fi += 1
        enc.stdin.close()
        enc.wait()
    return total


# --------------------------------------------------------------------------- QA

def qa(path, step=0.5):
    """check rendered video: faces must be inside the window and not clipped by its edges."""
    det = cv2.FaceDetectorYN.create(MODEL, "", (W // 2, H // 2), 0.8)
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={1 / step},scale={W // 2}:{H // 2}",
                                   "-f", "rawvideo", "-pix_fmt", "bgr24", "-"])
    fr = np.frombuffer(raw, np.uint8).reshape(-1, H // 2, W // 2, 3)
    issues, nfaces = [], 0
    for i, f in enumerate(fr):
        _, res = det.detect(f)
        for r in (res if res is not None else []):
            x, y, w, h = [float(q) * 2 for q in r[:4]]
            nfaces += 1
            cyf = y + h / 2
            if not (WIN_Y0 <= cyf <= WIN_Y1):
                continue      # the blurred background in the bands (no real footage there)
            if y < WIN_Y0 - h * 0.15 or y + h > WIN_Y1 + h * 0.15:
                issues.append((i * step, "face outside window / under text", (int(x), int(y), int(w), int(h))))
            elif y < WIN_Y0 + 6 or x < 2 or x + w > W - 2:
                issues.append((i * step, "face clipped by window edge", (int(x), int(y), int(w), int(h))))
    return nfaces, issues
