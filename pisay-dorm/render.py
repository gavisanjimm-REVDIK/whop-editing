#!/usr/bin/env python3
"""Render Scenes 1-3 of "A Day in My Life as a Pisay Scholar - Dorm Edition" (graphics pass).

Footage goes in footage/ (IMG_9867, 9868, 9873, 9879 .MOV). Output: out/scenes1-3.mp4

Every cut from real footage into a text-only card uses the crumpled-paper opening
transition (a paper ball lands and unfolds into the card). Going back to footage, the
sheet crumples up again and is tossed away.

No voice-over or music yet: the audio track has only Jimm's on-camera lines, the original
room sound, and SFX for the graphics, so the VO and music can be laid on top later.

  python3 render.py               # full render
  python3 render.py --stills      # just a few preview stills into out/stills/
  python3 render.py --from 30 --to 45   # render only part of the timeline
"""
import argparse
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import sfx
from paper import H, W, Paper

ROOT = os.path.dirname(os.path.abspath(__file__))
FOOT = os.path.join(ROOT, "footage")
CACHE = os.path.join(ROOT, "cache")
FPS = 30

# ---------------------------------------------------------------- fonts & colours
F_ANTON = os.path.join(ROOT, "fonts", "Anton-Regular.ttf")
F_HAND = os.path.join(ROOT, "fonts", "Caveat-Bold.ttf")
F_MARK = os.path.join(ROOT, "fonts", "PermanentMarker-Regular.ttf")
F_INTER_XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
F_INTER_SB = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
F_MONO = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Medium.ttf"

INK = (24, 24, 26)
YELLOW = (255, 214, 64)
RED = (214, 40, 57)
WHITE = (255, 255, 255)

_fonts = {}


def font(path, size):
    k = (path, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, size)
    return _fonts[k]


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def prog(t, t0, dur):
    return clamp((t - t0) / dur) if dur > 0 else float(t >= t0)


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out_back(x, s=1.7):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


# ---------------------------------------------------------------- footage
class Clip:
    """Streams frames of a footage segment through ffmpeg. frame(k) must be called with
    non-decreasing k; past the end it keeps returning the last frame (freeze)."""

    def __init__(self, path, ss, dur, speed=1.0, grade=""):
        vf = f"setpts=(PTS-STARTPTS)/{speed},fps={FPS},scale={W}:{H}:flags=lanczos,setsar=1"
        if grade:
            vf += "," + grade
        self.cmd = ["ffmpeg", "-v", "error", "-ss", f"{ss}", "-t", f"{dur / speed + 0.5}",
                    "-i", path, "-vf", vf, "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.p = None
        self.k = -1
        self.last = None
        self.n = int(round(dur / speed * FPS))

    def frame(self, k):
        k = min(k, self.n - 1)
        if self.p is None:
            self.p = subprocess.Popen(self.cmd, stdout=subprocess.PIPE)
        while self.k < k:
            buf = self.p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                self.k = k
                break
            self.last = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            self.k += 1
        return self.last.astype(np.float32)

    def close(self):
        if self.p:
            self.p.kill()
            self.p = None


def ensure_slowmo():
    """Optical-flow slow motion of the coins (src 1.75-3.0 s at 0.3x)."""
    out = os.path.join(CACHE, "coins_slowmo.mp4")
    if not os.path.exists(out):
        os.makedirs(CACHE, exist_ok=True)
        print("building slow-mo (one time, ~2 min)...", flush=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1.75", "-t", "1.3", "-i",
                        os.path.join(FOOT, "IMG_9868.MOV"), "-an", "-vf",
                        "setpts=PTS/0.3,minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
                        "-c:v", "libx264", "-crf", "12", "-preset", "fast", out], check=True)
    return out


# ---------------------------------------------------------------- 2D helpers
def to_np(img):
    return np.asarray(img, dtype=np.float32)


def paste(frame, img, cx, cy, alpha=1.0):
    """Alpha-composite a PIL RGBA image centred at (cx, cy) onto float frame in place."""
    if img is None or alpha <= 0:
        return frame
    a = to_np(img)
    h, w = a.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return frame
    sub = a[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
    al = sub[..., 3:4] / 255.0 * alpha
    frame[fy0:fy1, fx0:fx1] = frame[fy0:fy1, fx0:fx1] * (1 - al) + sub[..., :3] * al
    return frame


def xform(img, scale=1.0, rot=0.0):
    if scale <= 0.01:
        return None
    if abs(scale - 1) > 1e-3:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BICUBIC)
    if abs(rot) > 0.05:
        img = img.rotate(rot, resample=Image.BICUBIC, expand=True)
    return img


def with_shadow(img, blur=10, off=(6, 10), strength=0.55):
    pad = blur * 3 + max(abs(off[0]), abs(off[1]))
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
    alpha = img.split()[3].point(lambda v: int(v * strength))
    blk = Image.new("RGBA", img.size, (0, 0, 0, 255))
    blk.putalpha(alpha)
    sh.paste(blk, (pad + off[0], pad + off[1]), blk)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(sh)
    out.alpha_composite(img, (pad, pad))
    return out


def text_img(text, fpath, size, fill, stroke=0, stroke_fill=(0, 0, 0)):
    f = font(fpath, size)
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    img = Image.new("RGBA", (r - l + 4, b - t + 4), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((2 - l, 2 - t), text, font=f, fill=fill, stroke_width=stroke,
                             stroke_fill=stroke_fill)
    return img


def wipe(img, p, direction="lr"):
    """Reveal an image left-to-right (write-on / highlighter feel)."""
    if img is None or p >= 1:
        return img
    if p <= 0:
        return None
    out = img.copy()
    a = np.array(out.split()[3])
    cut = int(img.width * p)
    a[:, cut:] = 0
    out.putalpha(Image.fromarray(a))
    return out


def hand_arrow(p0, p1, bend=0.25, width=7, color=WHITE, head=26):
    """Hand-drawn style curved arrow as a list of points (quadratic bezier) + head."""
    (x0, y0), (x1, y1) = p0, p1
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = -(y1 - y0), (x1 - x0)
    cx, cy = mx + nx * bend, my + ny * bend
    pts = []
    for i in range(41):
        t = i / 40
        pts.append(((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1,
                    (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1))
    return pts


def draw_arrow(frame, pts, p, color=WHITE, width=7, head=28, shadow=True):
    if p <= 0:
        return
    n = max(2, int(len(pts) * p))
    seg = pts[:n]
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    pad = head + 30
    x0, y0 = int(min(xs)) - pad, int(min(ys)) - pad
    img = Image.new("RGBA", (int(max(xs)) - x0 + pad, int(max(ys)) - y0 + pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    loc = [(x - x0, y - y0) for x, y in seg]
    d.line(loc, fill=color, width=width, joint="curve")
    if p >= 0.98:
        (ax, ay), (bx, by) = loc[-4], loc[-1]
        ang = math.atan2(by - ay, bx - ax)
        for s in (-1, 1):
            a2 = ang + math.pi - s * 0.5
            d.line([(bx, by), (bx + head * math.cos(a2), by + head * math.sin(a2))], fill=color, width=width)
    if shadow:
        img = with_shadow(img, blur=5, off=(3, 4), strength=0.6)
        x0 -= 5 * 3 + 4
        y0 -= 5 * 3 + 4
    paste(frame, img, x0 + img.width / 2, y0 + img.height / 2)


# ---------------------------------------------------------------- stickers (paper strips over footage)
PAPER = None


def sticker(lines, pad=(34, 22), rot=0.0):
    """White crumpled-paper sticker. lines: list of (text, fontpath, size, colour)."""
    imgs = [text_img(t, fp, sz, col) for t, fp, sz, col in lines]
    gap = 6
    w = max(i.width for i in imgs) + 2 * pad[0]
    h = sum(i.height for i in imgs) + gap * (len(imgs) - 1) + 2 * pad[1]
    crop = PAPER.rest[300:300 + h, 400:400 + w]
    base = Image.fromarray(np.clip(crop, 0, 255).astype(np.uint8)).convert("RGBA")
    # slightly torn edges
    m = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(m)
    rng = np.random.default_rng(len(lines[0][0]) + w)
    poly = []
    for x in range(0, w + 1, 14):
        poly.append((x, rng.uniform(0, 4)))
    for y in range(0, h + 1, 14):
        poly.append((w - rng.uniform(0, 4), y))
    for x in range(w, -1, -14):
        poly.append((x, h - rng.uniform(0, 4)))
    for y in range(h, -1, -14):
        poly.append((rng.uniform(0, 4), y))
    md.polygon(poly, fill=255)
    base.putalpha(m)
    y = pad[1]
    for i in imgs:
        base.alpha_composite(i, ((w - i.width) // 2, y))
        y += i.height + gap
    img = with_shadow(base, blur=9, off=(5, 9), strength=0.5)
    return img.rotate(rot, resample=Image.BICUBIC, expand=True) if rot else img


def person_icon(size, color, filled=True):
    s = size
    img = Image.new("RGBA", (s, int(s * 1.35)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = s * 0.22
    w = max(2, s // 12)
    cx = s / 2
    if filled:
        d.ellipse([cx - r, 2, cx + r, 2 + 2 * r], fill=color)
        d.rounded_rectangle([s * 0.14, 2 * r + s * 0.12, s * 0.86, s * 1.32], radius=int(s * 0.3), fill=color)
    else:
        d.ellipse([cx - r, 2, cx + r, 2 + 2 * r], outline=color, width=w)
        d.rounded_rectangle([s * 0.14, 2 * r + s * 0.12, s * 0.86, s * 1.32], radius=int(s * 0.3),
                            outline=color, width=w)
    return img


# ---------------------------------------------------------------- text-only cards (ink layers)
def blank_ink():
    return Image.new("RGB", (W, H), "white")


def ink_text(d, xy, text, fp, size, fill=INK, anchor="mm"):
    d.text(xy, text, font=font(fp, size), fill=fill, anchor=anchor)


def highlighter(d, box, p=1.0, color=YELLOW, seed=1):
    x0, y0, x1, y1 = box
    if p <= 0:
        return
    x1 = x0 + (x1 - x0) * p
    rng = np.random.default_rng(seed)
    pts = [(x0 + rng.uniform(-4, 4), y0 + rng.uniform(-3, 5)), (x1 + rng.uniform(-4, 4), y0 + rng.uniform(-5, 3)),
           (x1 + rng.uniform(-4, 4), y1 + rng.uniform(-3, 5)), (x0 + rng.uniform(-4, 4), y1 + rng.uniform(-5, 3))]
    d.polygon(pts, fill=color)


def pen_ellipse(d, box, p, color=RED, width=9, seed=2):
    x0, y0, x1, y1 = box
    cx, cy, rx, ry = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.28)
    n = int(80 * p * 1.12)
    pts = []
    for i in range(n):
        t = i / 80 * 2 * math.pi + ph
        k = 1 + 0.03 * math.sin(3 * t) + 0.04 * i / 80
        pts.append((cx + rx * k * math.cos(t), cy + ry * k * math.sin(t) - 6 * i / 80))
    if len(pts) > 1:
        d.line(pts, fill=color, width=width, joint="curve")


def card_title(t):
    """COSTS BEHIND THE CHANCE (project title). t = seconds since the card is fully open."""
    img = blank_ink()
    d = ImageDraw.Draw(img)
    f = font(F_ANTON, 205)
    y1, y2 = 330, 545
    l2a, l2b = "THE ", "CHANCE"
    wa, wb = d.textlength(l2a, font=f), d.textlength(l2b, font=f)
    x2 = (W - wa - wb) / 2
    highlighter(d, (x2 + wa - 14, y2 - 70, x2 + wa + wb + 16, y2 + 98), ease_out(prog(t, 0.15, 0.45)), seed=4)
    ink_text(d, (W / 2, y1), "COSTS BEHIND", F_ANTON, 205)
    d.text((x2, y2), l2a + l2b, font=f, fill=INK, anchor="lm")
    sub = ["Financial Considerations and Student Participation in",
           "Extracurricular Opportunities at PSHS-CRC"]
    for i, s in enumerate(sub):
        p = ease_out(prog(t, 0.55 + 0.18 * i, 0.5))
        if p > 0:
            col = tuple(int(lerp(255, c, p)) for c in INK)
            ink_text(d, (W / 2, 770 + i * 64 + (1 - p) * 20), s, F_INTER_SB, 46, fill=col)
    return np.asarray(img)


def card_stat(t):
    """76.6% card. t = seconds since open."""
    img = blank_ink()
    d = ImageDraw.Draw(img)
    # count-up 0 -> 76.6
    c = ease_out(prog(t, 0.0, 1.3))
    val = 76.6 * c
    ink_text(d, (W / 2 - 40, 395), f"{val:.1f}%", F_ANTON, 330)
    bx = d.textbbox((W / 2 - 40, 395), "76.6%", font=font(F_ANTON, 330), anchor="mm")
    pen_ellipse(d, (bx[0] - 70, bx[1] - 55, bx[2] + 70, bx[3] + 55), ease_in_out(prog(t, 1.4, 0.55)), seed=5)
    note_p = prog(t, 1.75, 0.35)
    if note_p > 0:
        note = text_img("about 3 out of 4!", F_HAND, 78, RED)
        note = note.rotate(8, resample=Image.BICUBIC, expand=True)
        note = wipe(note, ease_out(note_p))
        if note:
            img.paste(note, (int(min(bx[2] - 40, W - note.width - 60)), 95), note)
    # description with highlighted verbs
    lines = [("had ", "declined, limited, or discontinued"), ("an opportunity because of expenses", "")]
    f = font(F_INTER_SB, 54)
    y = 720
    p = ease_out(prog(t, 0.9, 0.5))
    if p > 0:
        a, b = lines[0]
        wa, wb = d.textlength(a, font=f), d.textlength(b, font=f)
        x = (W - wa - wb) / 2
        highlighter(d, (x + wa - 8, y - 38, x + wa + wb + 8, y + 40), ease_out(prog(t, 1.2, 0.5)), seed=9)
        col = tuple(int(lerp(255, cc, p)) for cc in INK)
        d.text((x, y + (1 - p) * 18), a + b, font=f, fill=col, anchor="lm")
        ink_text(d, (W / 2, y + 78 + (1 - p) * 18), lines[1][0], F_INTER_SB, 54, fill=col)
    lab = ease_out(prog(t, 0.6, 0.4))
    if lab > 0:
        col = tuple(int(lerp(255, cc, lab)) for cc in (110, 110, 115))
        ink_text(d, (W / 2, 900), "of the PSHS-CRC students we surveyed", F_INTER_SB, 34, fill=col)
    return np.asarray(img)


_icons = {}


def icon(size, color, filled):
    k = (size, color, filled)
    if k not in _icons:
        _icons[k] = person_icon(size, color, filled)
    return _icons[k]


def card_ratio(t):
    """36 out of 47 students. t = seconds since this content started."""
    img = blank_ink()
    d = ImageDraw.Draw(img)
    p = ease_out(prog(t, 0.0, 0.45))
    f = font(F_ANTON, 210)
    a, b = "36", " OUT OF 47"
    wa, wb = d.textlength(a, font=f), d.textlength(b, font=f)
    x = (W - wa - wb) / 2
    y = 300 + (1 - p) * 30
    if p > 0:
        d.text((x, y), a, font=f, fill=RED if p >= 1 else tuple(int(lerp(255, c, p)) for c in RED), anchor="lm")
        d.text((x + wa, y), b, font=f, fill=tuple(int(lerp(255, c, p)) for c in INK), anchor="lm")
    q = ease_out(prog(t, 0.25, 0.4))
    if q > 0:
        ink_text(d, (W / 2, 470 + (1 - q) * 20), "STUDENTS", F_ANTON, 92,
                 fill=tuple(int(lerp(255, c, q)) for c in INK))
    # 47 people, 36 in red
    cols, size, gx, gy = 16, 62, 88, 104
    rows = [16, 16, 15]
    top = 600
    k = 0
    for r, n in enumerate(rows):
        x0 = (W - (n - 1) * gx) / 2
        for c in range(n):
            pt = prog(t, 0.6 + k * 0.035, 0.25)
            if pt > 0:
                filled = k < 36
                ic = icon(size, RED if filled else (150, 150, 155), filled)
                s = ease_out_back(pt)
                ic2 = ic.resize((max(1, int(ic.width * s)), max(1, int(ic.height * s))), Image.BICUBIC)
                cx, cy = x0 + c * gx, top + r * gy + 40
                img.paste(ic2, (int(cx - ic2.width / 2), int(cy - ic2.height / 2)), ic2)
            k += 1
    return np.asarray(img)


# ---------------------------------------------------------------- captions
BALCONY_WORDS = None


def caption_img(words, active, size=54):
    f = font(F_INTER_XB, size)
    space = f.getlength(" ") + 14
    widths = [f.getlength(w) for w, _, _ in words]
    total = sum(widths) + space * (len(words) - 1)
    img = Image.new("RGBA", (int(total) + 40, size + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = 20
    for i, (w, _, _) in enumerate(words):
        d.text((x, 20), w, font=f, fill=YELLOW if i == active else WHITE, stroke_width=7,
               stroke_fill=(0, 0, 0))
        x += widths[i] + space
    return img


def phrases_from(words, breaks):
    out, cur = [], []
    for w in words:
        cur.append(w)
        if w[0] in breaks:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


# ================================================================ TIMELINE
# (all times in output seconds)
T_CLOSET_END = 9.95       # closet + title over black
T_BLACK_END = 13.40       # black screen with typed line
T_MONEY_END = 17.57       # slow-mo coins (4.17 s)
LAP_SS, LAP_END_SRC = 2.0, 18.35
T_LAP_END = T_MONEY_END + (LAP_END_SRC - LAP_SS)   # 33.92
T_OPEN1 = T_LAP_END       # crumple open -> project title card
D_OPEN = 1.10
T_CLOSE1 = T_OPEN1 + D_OPEN + 5.2                   # crumple close -> balcony
D_CLOSE = 0.90
BAL_SS, BAL_TALK_END = 0.9, 17.0
T_BAL = T_CLOSE1
T_EMPTY = T_BAL + (BAL_TALK_END - BAL_SS)
EMPTY_SPEED = 0.65
EMPTY_SRC_DUR = 4.8
T_OPEN2 = T_EMPTY + EMPTY_SRC_DUR / EMPTY_SPEED - 0.35
T_STAT = T_OPEN2 + D_OPEN
T_RATIO = T_STAT + 5.0
T_END = T_RATIO + 5.2

GRADE_CLOSET = "eq=contrast=1.10:saturation=1.18:gamma=0.94"
GRADE_LAPTOP = "eq=contrast=1.22:brightness=-0.045:saturation=1.30:gamma=0.92"
GRADE_BAL = "eq=contrast=1.04:saturation=1.08"
GRADE_COIN = "eq=contrast=1.08:saturation=1.12"


class Timeline:
    def __init__(self):
        self.closet = Clip(os.path.join(FOOT, "IMG_9867.MOV"), 0.0, 7.8, grade=GRADE_CLOSET)
        self.coins = Clip(ensure_slowmo(), 0.0, 4.4, grade=GRADE_COIN)
        self.laptop = Clip(os.path.join(FOOT, "IMG_9873.MOV"), LAP_SS, LAP_END_SRC - LAP_SS + 0.1,
                           grade=GRADE_LAPTOP)
        self.bal = Clip(os.path.join(FOOT, "IMG_9879.MOV"), BAL_SS, BAL_TALK_END - BAL_SS + 0.1, grade=GRADE_BAL)
        self.empty = Clip(os.path.join(FOOT, "IMG_9879.MOV"), BAL_TALK_END, EMPTY_SRC_DUR,
                          speed=EMPTY_SPEED, grade=GRADE_BAL)
        self.title_ink_end = card_title(99)
        self.title_ink_start = card_title(-1)
        self.stat_ink_start = card_stat(-1)
        self.frozen = {}

    # --- clip access in output time
    def kf(self, t, t0):
        return max(0, int(round((t - t0) * FPS)))

    def render(self, t):
        if t < T_CLOSET_END:
            return self.s_closet(t)
        if t < T_BLACK_END:
            return self.s_black(t)
        if t < T_MONEY_END:
            return self.s_money(t)
        if t < T_OPEN1:
            return self.s_laptop(t)
        if t < T_OPEN1 + D_OPEN:
            bg = self.s_laptop(T_OPEN1 - 1 / FPS, freeze=True)
            return self.crumple_open(bg, self.title_ink_start, t - T_OPEN1)
        if t < T_CLOSE1:
            return PAPER.card(card_title(t - T_OPEN1 - D_OPEN))
        if t < BAL_END_OUT():
            fr = self.s_balcony(t)
            if t < T_CLOSE1 + D_CLOSE:
                fr = self.crumple_close(fr, self.title_ink_end, t - T_CLOSE1)
            return fr
        if t < T_OPEN2:
            return self.s_empty(t)
        if t < T_STAT:
            bg = self.s_empty(T_OPEN2 - 1 / FPS)
            return self.crumple_open(bg, self.stat_ink_start, t - T_OPEN2, from_xy=(560, 820), spin=-50)
        return self.s_stats(t)

    # --- paper transitions
    def crumple_open(self, bg, ink, lt, from_xy=(1450, 900), spin=70):
        """Ball tossed in (0-0.32 s), lands and unfolds to full-frame card (to D_OPEN)."""
        t_in = 0.32
        if lt < t_in:
            p = ease_out(lt / t_in)
            cx = lerp(from_xy[0] + 380, W / 2 + (from_xy[0] - W / 2) * 0.25, p)
            cy = lerp(H + 200, H / 2 + (from_xy[1] - H / 2) * 0.25, p) - math.sin(p * math.pi) * 120
            return PAPER.frame(bg, ink, 0.0, ball_r=165 * (0.6 + 0.4 * p), center=(cx, cy),
                               theta=spin * (1 + 2 * (1 - p)))
        e = ease_in_out(clamp((lt - t_in) / (D_OPEN - t_in)))
        c = (W / 2 + (from_xy[0] - W / 2) * 0.25, H / 2 + (from_xy[1] - H / 2) * 0.25)
        return PAPER.frame(bg, ink, e, ball_r=165, center=c, theta=spin)

    def crumple_close(self, bg, ink, lt):
        """Card crumples back into a ball (0-0.6 s) which is tossed off frame."""
        t_c = 0.58
        if lt < t_c:
            e = 1 - ease_in_out(lt / t_c)
            return PAPER.frame(bg, ink, e, ball_r=165, center=(W / 2, H / 2), theta=-60)
        p = clamp((lt - t_c) / (D_CLOSE - t_c)) ** 1.6
        cx = lerp(W / 2, -250, p)
        cy = lerp(H / 2, H / 2 - 260, p) - math.sin(p * math.pi) * 80
        return PAPER.frame(bg, ink, 0.0, ball_r=165 * (1 - 0.35 * p), center=(cx, cy), theta=-60 - 300 * p)

    # --- scene 1
    def s_closet(self, t):
        if t < 7.8:
            fr = self.closet.frame(self.kf(t, 0))
            fade = 1 - prog(t, 7.15, 0.45)
            fr = fr * fade
        else:
            fr = np.zeros((H, W, 3), np.float32)
        # "hi, I'm Jimm" callout with arrow (he is centre-right; text on the closet wall, left)
        p = prog(t, 2.3, 0.45)
        out = 1 - prog(t, 5.6, 0.3)
        if p > 0 and out > 0:
            hi = text_img("hi, I'm Jimm!", F_HAND, 104, WHITE)
            hi = with_shadow(hi, blur=6, off=(3, 5), strength=0.85)
            paste(fr, wipe(hi, ease_out(p)), 330, 255, alpha=out)
            pts = hand_arrow((420, 340), (700, 470), bend=-0.25)
            draw_arrow(fr, pts, ease_out(prog(t, 2.6, 0.4)) * (1 if out > 0.5 else 0))
        # Title stays behind when Jimm walks out of frame
        self.title_block(fr, t, t0=6.85, t_out=9.55)
        return fr

    def title_block(self, fr, t, t0, t_out):
        if t < t0:
            return
        outp = ease_in_out(prog(t, t_out, 0.38))
        s_all = 1 - 0.15 * outp
        alpha = 1 - outp
        words = ["A", "DAY", "IN", "MY", "LIFE"]
        f = font(F_ANTON, 180)
        sp = f.getlength(" ")
        ws = [f.getlength(w) for w in words]
        x = W / 2 - (sum(ws) + sp * 4) / 2 * s_all
        cy = 420
        for i, w in enumerate(words):
            p = prog(t, t0 + i * 0.07, 0.3)
            if p <= 0:
                break
            im = text_img(w, F_ANTON, 180, WHITE)
            im = xform(im, s_all * ease_out_back(p))
            if im is not None:
                paste(fr, im, x + ws[i] * s_all / 2, cy + (1 - ease_out(p)) * 40, alpha=alpha * clamp(p * 3))
            x += (ws[i] + sp) * s_all
        p2 = prog(t, t0 + 0.45, 0.45)
        if p2 > 0:
            im = text_img("as a Pisay Scholar", F_HAND, 120, WHITE)
            paste(fr, xform(wipe(im, ease_out(p2)), s_all), W / 2, 590, alpha=alpha)
        p3 = prog(t, t0 + 0.85, 0.35)
        if p3 > 0:
            tag = text_img("DORM EDITION", F_ANTON, 86, INK)
            box = Image.new("RGBA", (tag.width + 60, tag.height + 34), YELLOW + (255,))
            box.alpha_composite(tag, (30, 17))
            box = box.rotate(-3, resample=Image.BICUBIC, expand=True)
            box = wipe(box, ease_out(p3))
            paste(fr, xform(box, s_all * (1 + 0.15 * (1 - ease_out_back(p3)))), W / 2, 735, alpha=alpha)

    def s_black(self, t):
        fr = np.zeros((H, W, 3), np.float32)
        lines = ["aside from classes and requirements,", "there's one thing I also have to manage..."]
        starts = [T_CLOSET_END + 0.35, T_CLOSET_END + 1.75]
        cps = 26.0
        for i, (ln, s0) in enumerate(zip(lines, starts)):
            n = int(clamp((t - s0) * cps, 0, len(ln)))
            if n <= 0:
                continue
            caret = "_" if (i == 1 or n < len(ln)) and int(t * 3) % 2 == 0 else " "
            im = text_img(ln[:n] + (caret if i == 1 or n < len(ln) else ""), F_MONO, 46, (225, 225, 225))
            paste(fr, im, W / 2 - text_img(ln, F_MONO, 46, WHITE).width / 2 + im.width / 2,
                  H / 2 - 40 + i * 80, alpha=1 - prog(t, T_BLACK_END - 0.12, 0.1))
        return fr

    def s_money(self, t):
        lt = t - T_BLACK_END
        fr = self.coins.frame(self.kf(t, T_BLACK_END))
        # camera shake on the slam
        sh = max(0.0, 1 - prog(lt, 0.30, 0.35))
        if 0.30 <= lt and sh > 0:
            dx, dy = math.sin(lt * 90) * 14 * sh, math.cos(lt * 70) * 10 * sh
            M = np.float32([[1.03, 0, -W * 0.015 + dx], [0, 1.03, -H * 0.015 + dy]])
            fr = cv2.warpAffine(fr, M, (W, H), borderMode=cv2.BORDER_REFLECT)
        # vignette for contrast behind text
        fr *= VIGNETTE
        p = prog(lt, 0.30, 0.17)
        if p > 0:
            s = lerp(2.4, 1.0, ease_out(p))
            im = text_img("MY ALLOWANCE.", F_ANTON, 230, WHITE, stroke=9)
            im = with_shadow(im, blur=14, off=(0, 12), strength=0.7)
            paste(fr, xform(im, s), W / 2, H / 2 - 120, alpha=clamp(p * 2))
        return fr

    # --- scene 2
    def s_laptop(self, t, freeze=False):
        k = self.kf(t, T_MONEY_END)
        fr = self.laptop.frame(k)
        src = LAP_SS + (t - T_MONEY_END)
        # slow push toward the laptop, then a punch-in on Jimm when he turns to camera
        z1 = lerp(1.0, 1.12, ease_in_out(prog(src, 2.0, 13.8)))
        punch = ease_out(prog(src, 16.55, 0.25))
        z = lerp(z1, 1.22, punch)
        cx = lerp(700, 1130, punch)
        cy = lerp(640, 330, punch)
        if z > 1.001:
            M = np.float32([[z, 0, cx - z * cx], [0, z, cy - z * cy]])
            fr = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        # callout 1: the competition announcement on the laptop screen
        p = prog(src, 2.8, 0.4)
        o = 1 - prog(src, 8.4, 0.3)
        if p > 0 and o > 0:
            st = STICKERS["comp"]
            paste(fr, xform(st, ease_out_back(p)), 470, 250, alpha=o)
            draw_arrow(fr, hand_arrow((560, 365), (640, 560), bend=-0.3, color=INK), ease_out(prog(src, 3.2, 0.4)) if o > 0.6 else 0,
                       color=INK, width=8)
        # callout 2: everyday expenses
        p = prog(src, 9.2, 0.4)
        o = 1 - prog(src, 15.4, 0.3)
        if p > 0 and o > 0:
            st = STICKERS["expenses"]
            paste(fr, xform(st, ease_out_back(p)), 470, 260, alpha=o)
            for i, item in enumerate(["food", "fare", "school supplies"]):
                q = prog(src, 10.2 + i * 0.45, 0.3)
                if q > 0 and o > 0:
                    it = STICKERS["item_" + item]
                    paste(fr, xform(it, ease_out_back(q)), 300 + i * 0 + [0, 70, 190][i], 470 + i * 95, alpha=o)
        # the question
        if src >= 16.6:
            self.question(fr, src)
        return fr

    def question(self, fr, src):
        words = [("BUT", 16.72), ("CAN", 17.0), ("I", 17.16), ("ACTUALLY", 17.28)]
        f = font(F_ANTON, 104)
        sp = f.getlength(" ") + 16
        ws = [f.getlength(w) for w, _ in words]
        x = W / 2 - (sum(ws) + sp * 3) / 2
        for i, (w, ts) in enumerate(words):
            p = prog(src, ts - 0.05, 0.14)
            if p > 0:
                im = text_img(w, F_ANTON, 104, WHITE, stroke=7)
                paste(fr, xform(im, ease_out_back(p)), x + ws[i] / 2, 770)
            x += ws[i] + sp
        p = prog(src, 17.55, 0.16)
        if p > 0:
            im = text_img("AFFORD IT?", F_ANTON, 190, YELLOW, stroke=10)
            im = with_shadow(im, blur=10, off=(0, 10), strength=0.6)
            sh = (1 - prog(src, 17.7, 0.3))
            dx = math.sin(src * 80) * 8 * sh
            paste(fr, xform(im, lerp(1.6, 1.0, ease_out(p))), W / 2 + dx, 905)

    # --- scene 3
    def s_balcony(self, t):
        fr = self.bal.frame(self.kf(t, T_BAL))
        src = BAL_SS + (t - T_BAL)
        # lower third
        p = prog(src, 2.0, 0.45)
        o = 1 - prog(src, 6.6, 0.35)
        if p > 0 and o > 0:
            lt = STICKERS["jimm"]
            paste(fr, lt, lerp(-lt.width / 2, 60 + lt.width / 2, ease_out(p)), 190, alpha=o)
        # word-by-word captions
        for ph in BAL_PHRASES:
            s0, s1 = ph[0][1], ph[-1][2]
            if s0 - 0.08 <= src < s1 + 0.25:
                act = max([i for i, w in enumerate(ph) if w[1] <= src + 0.02] or [0])
                im = caption_img(ph, act)
                pp = ease_out_back(prog(src, s0 - 0.08, 0.16))
                paste(fr, xform(im, lerp(0.85, 1.0, pp)), W / 2, 960)
                break
        return fr

    def s_empty(self, t):
        fr = self.empty.frame(self.kf(t, T_EMPTY))
        lt = t - T_EMPTY
        p = prog(lt, 0.35, 0.5)
        if p > 0:
            card = self.survey_card(lt)
            paste(fr, card, lerp(W + 400, 1440, ease_out_back(p, 1.2)), 530)
        return fr

    def survey_card(self, lt):
        cw, ch = 760, 850
        base = Image.fromarray(np.clip(PAPER.rest[120:120 + ch, 980:980 + cw], 0, 255).astype(np.uint8)).convert("RGBA")
        d = ImageDraw.Draw(base)
        d.text((cw / 2, 92), "we surveyed", font=font(F_HAND, 84), fill=RED, anchor="mm")
        n = int(round(47 * ease_out(prog(lt, 0.6, 1.2))))
        d.text((cw / 2, 255), f"{n}", font=font(F_ANTON, 240), fill=INK, anchor="mm")
        d.text((cw / 2, 420), "PSHS-CRC STUDENTS", font=font(F_ANTON, 74), fill=INK, anchor="mm")
        cols, gx, gy, sz = 12, 54, 64, 38
        for k in range(47):
            pt = prog(lt, 0.6 + k * 0.026, 0.18)
            if pt <= 0:
                break
            r, c = divmod(k, cols)
            ic = icon(sz, INK, True)
            s = ease_out_back(pt)
            ic2 = ic.resize((max(1, int(ic.width * s)), max(1, int(ic.height * s))), Image.BICUBIC)
            x0 = (cw - (cols - 1) * gx) / 2
            base.alpha_composite(ic2, (int(x0 + c * gx - ic2.width / 2), int(520 + r * gy - ic2.height / 2)))
        q = prog(lt, 2.6, 0.5)
        if q > 0:
            line = text_img("on how expenses affect joining extracurriculars", F_HAND, 46, RED)
            line = wipe(line, ease_out(q))
            if line:
                base.alpha_composite(line, ((cw - line.width) // 2, 760))
        base = base.rotate(-2.5, resample=Image.BICUBIC, expand=True)
        return with_shadow(base, blur=14, off=(8, 14), strength=0.5)

    def s_stats(self, t):
        if t < T_RATIO:
            return PAPER.card(card_stat(t - T_STAT))
        # swap content: old card slides/fades, new one builds
        lt = t - T_RATIO
        if lt < 0.25:
            a = card_stat(99).astype(np.float32)
            k = ease_in_out(lt / 0.25)
            ink = a + (255 - a) * k
            return PAPER.card(ink)
        return PAPER.card(card_ratio(lt - 0.25))


def BAL_END_OUT():
    return T_EMPTY


# ---------------------------------------------------------------- stickers & globals
STICKERS = {}
VIGNETTE = None
BAL_PHRASES = []


def build_globals():
    global PAPER, VIGNETTE, BAL_PHRASES
    PAPER = Paper(seed=7)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    VIGNETTE = (1 - 0.45 * np.clip(r - 0.35, 0, 1) ** 1.5)[..., None].astype(np.float32)
    STICKERS["comp"] = sticker([("a competition", F_HAND, 76, INK), ("I wanted to join!", F_HAND, 76, RED)], rot=3)
    STICKERS["expenses"] = sticker([("but as a dormer...", F_HAND, 66, INK),
                                    ("everyday expenses", F_HAND, 80, RED)], rot=-3)
    for i, item in enumerate(["food", "fare", "school supplies"]):
        STICKERS["item_" + item] = sticker([("+ " + item, F_HAND, 58, INK)], pad=(24, 10), rot=[-4, 3, -2][i])
    STICKERS["jimm"] = sticker([("JIMM", F_ANTON, 82, INK), ("Pisay scholar · dormer", F_INTER_SB, 30, RED)],
                               pad=(40, 18), rot=-2)
    words = [
        ("As", 1.44, 1.96), ("a", 1.96, 2.12), ("dormer,", 2.12, 2.52), ("budgeting", 2.66, 2.94),
        ("can", 2.94, 3.38), ("be", 3.38, 3.5), ("a", 3.5, 3.58), ("very", 3.58, 3.86), ("serious", 3.86, 4.18),
        ("challenge.", 4.18, 4.7), ("We", 5.38, 5.56), ("need", 5.56, 5.68), ("to", 5.68, 5.76),
        ("make", 5.76, 5.9), ("sure", 5.9, 6.1), ("that", 6.1, 6.26), ("our", 6.26, 6.36), ("money", 6.36, 6.56),
        ("lasts,", 6.56, 7.0), ("not", 7.48, 7.64), ("just", 7.64, 7.9), ("for", 7.9, 8.26), ("our", 8.26, 9.06),
        ("personal", 9.06, 9.44), ("needs,", 9.44, 9.76), ("but", 10.02, 10.18), ("also", 10.18, 10.5),
        ("for", 10.5, 10.76), ("academic", 10.76, 11.06), ("purposes.", 11.06, 11.56), ("And", 12.28, 12.36),
        ("apparently,", 12.36, 12.74), ("I'm", 13.3, 13.44), ("not", 13.44, 13.54), ("the", 13.54, 13.68),
        ("only", 13.68, 13.9), ("one", 13.9, 14.14), ("who", 14.14, 14.34), ("is", 14.34, 14.44),
        ("being", 14.44, 14.64), ("challenged", 14.64, 15.06), ("by", 15.06, 15.28), ("this", 15.28, 15.42),
        ("problem.", 15.42, 15.82)]
    BAL_PHRASES = phrases_from(words, {"dormer,", "challenge.", "lasts,", "needs,", "purposes.", "apparently,",
                                       "one", "problem."})


# ---------------------------------------------------------------- audio
def build_audio(path):
    sr = sfx.SR
    n = int(T_END * sr) + sr
    mix = np.zeros((n, 2), np.float32)

    def src_audio(fname, ss, dur, gain=1.0, speed=1.0):
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{ss}", "-t", f"{dur}", "-i", os.path.join(FOOT, fname),
               "-vn", "-ac", "2", "-ar", str(sr)]
        if speed != 1.0:
            cmd += ["-af", f"asetrate={int(sr * speed)},aresample={sr}"]
        cmd += ["-f", "f32le", "-"]
        a = np.frombuffer(subprocess.check_output(cmd), np.float32).reshape(-1, 2).copy()
        f = min(len(a) // 4, int(0.06 * sr))
        if f > 0:
            a[:f] *= np.linspace(0, 1, f)[:, None]
            a[-f:] *= np.linspace(1, 0, f)[:, None]
        return a * gain

    def put(a, t):
        i = int(t * sr)
        j = min(n, i + len(a))
        if j > i:
            mix[i:j] += a[:j - i]

    def sfx_at(snd, t, gain=1.0):
        put(np.repeat(snd[:, None], 2, 1) * gain, t)

    # Scene 1: closet room sound (door open/close), title whoosh, typing, coins + impact
    put(src_audio("IMG_9867.MOV", 0.0, 7.7, 0.8), 0.0)
    sfx_at(sfx.whoosh(0.55), 6.30, 0.55)
    for i in range(5):
        sfx_at(sfx.pop(), 6.45 + i * 0.07, 0.25)
    sfx_at(sfx.whoosh(0.5, up=False), 9.5, 0.35)
    for s0, ln in [(T_CLOSET_END + 0.35, 36), (T_CLOSET_END + 1.75, 42)]:
        for k in range(ln):
            sfx_at(sfx.key(seed=k), s0 + k / 26.0, 0.35)
    sfx_at(sfx.boom(), T_BLACK_END + 0.28, 0.9)
    put(src_audio("IMG_9868.MOV", 1.9, 1.6, 0.9, speed=0.6), T_BLACK_END + 0.05)
    # Scene 2: Jimm's line to camera; pops for the stickers
    lap = lambda s: T_MONEY_END + (s - LAP_SS)
    put(src_audio("IMG_9873.MOV", 16.55, 1.85, 1.6), lap(16.55))
    for s in (2.8, 9.2, 10.2, 10.65, 11.1):
        sfx_at(sfx.pop(), lap(s), 0.45)
    sfx_at(sfx.boom(0.5), lap(17.55), 0.45)
    sfx_at(sfx.paper_open(D_OPEN), T_OPEN1, 0.9)
    sfx_at(sfx.marker(0.45), T_OPEN1 + D_OPEN + 0.15, 0.25)
    sfx_at(sfx.paper_close(D_CLOSE), T_CLOSE1, 0.9)
    # Scene 3: Jimm on the balcony
    put(src_audio("IMG_9879.MOV", BAL_SS, BAL_TALK_END - BAL_SS, 2.0), T_BAL)
    sfx_at(sfx.pop(), T_BAL + 1.1, 0.4)
    sfx_at(sfx.whoosh(0.45), T_EMPTY + 0.3, 0.4)
    for k in range(47):
        sfx_at(sfx.tick(seed=k), T_EMPTY + 0.6 + k * 0.026, 0.12)
    sfx_at(sfx.paper_open(D_OPEN), T_OPEN2, 0.9)
    for k in range(26):
        sfx_at(sfx.tick(seed=k), T_STAT + k * 0.05 * (1 + k / 30), 0.22)
    sfx_at(sfx.marker(0.55), T_STAT + 1.4, 0.3)
    sfx_at(sfx.marker(0.45), T_STAT + 1.2, 0.2)
    sfx_at(sfx.whoosh(0.4), T_RATIO, 0.3)
    for k in range(47):
        sfx_at(sfx.pop(seed=k) * 0.6, T_RATIO + 0.25 + 0.6 + k * 0.035, 0.18)

    peak = np.abs(mix).max()
    mix *= 0.89 / max(peak, 1e-6)
    mix = mix[:int(T_END * sr)]
    sfx.write_wav(path, mix)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "scenes1-3.mp4"))
    ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float, default=None)
    ap.add_argument("--stills", nargs="*", type=float, default=None,
                    help="write PNG stills at these times instead of a video")
    a = ap.parse_args()
    build_globals()
    tl = Timeline()
    t1 = a.t1 if a.t1 is not None else T_END
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    print(f"timeline: closet 0-{T_CLOSET_END:.2f} black -{T_BLACK_END:.2f} coins -{T_MONEY_END:.2f} "
          f"laptop -{T_LAP_END:.2f} title card {T_OPEN1:.2f}-{T_CLOSE1:.2f} balcony -{T_EMPTY:.2f} "
          f"survey -{T_OPEN2:.2f} stats {T_STAT:.2f}-{T_END:.2f}", flush=True)

    if a.stills is not None:
        d = os.path.join(ROOT, "out", "stills")
        os.makedirs(d, exist_ok=True)
        # frames must be pulled in order from each clip
        for t in sorted(a.stills):
            fr = tl.render(t)
            Image.fromarray(np.clip(fr, 0, 255).astype(np.uint8)).save(os.path.join(d, f"t{t:06.2f}.png"))
            print("still", t, flush=True)
        return

    wav = os.path.join(CACHE, "mix.wav")
    build_audio(wav)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-ss", f"{a.t0}", "-i", wav, "-map", "0:v", "-map", "1:a",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                            "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out],
                           stdin=subprocess.PIPE)
    nf = int(round((t1 - a.t0) * FPS))
    # skip ahead: clips are streamed, so warm them by rendering from 0 only if needed
    for i in range(nf):
        t = a.t0 + i / FPS
        fr = tl.render(t)
        enc.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
        if i % 60 == 0:
            print(f"  {t:6.2f}s / {t1:.2f}s", flush=True)
    enc.stdin.close()
    enc.wait()
    print("wrote", a.out)


if __name__ == "__main__":
    sys.exit(main())
