"""Shared helpers for the BOXABL shorts: virtual camera, text, effects, audio synth, encoding."""
import math
import os
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
SR = 44100
ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(ROOT), "assets")
FONT_DIR = "/usr/share/fonts/opentype/inter"
F_BLACK = f"{FONT_DIR}/Inter-Black.otf"
F_XBOLD = f"{FONT_DIR}/Inter-ExtraBold.otf"
F_SEMI = f"{FONT_DIR}/Inter-SemiBold.otf"
F_MED = f"{FONT_DIR}/Inter-Medium.otf"
F_ITAL = "/usr/share/fonts/truetype/crosextra/Caladea-Italic.ttf"
F_SERIF = "/usr/share/fonts/truetype/crosextra/Caladea-Bold.ttf"


# ---------- easing ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_io(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x, p=3):
    x = clamp(x)
    return 1 - (1 - x) ** p


def lerp(a, b, t):
    return a + (b - a) * t


def back_out(x, s=2.2):
    """Overshoot pop (0->1 with a bounce past 1)."""
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


# ---------- camera ----------
def cam(img, cx, cy, w, rot=0.0):
    """Crop a 9:16 window of width w centred on (cx, cy) from img, rendered to W x H."""
    h = w * H / W
    iw, ih = img.size
    w = min(w, iw)
    h = min(h, ih)
    cx = clamp(cx, w / 2, iw - w / 2)
    cy = clamp(cy, h / 2, ih - h / 2)
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    out = img.transform((W, H), Image.EXTENT, box, Image.BICUBIC)
    if rot:
        out = out.rotate(rot, Image.BICUBIC, expand=False, fillcolor=(0, 0, 0))
    return out


def shake(t, amp, freq=23.0, seed=0):
    """Smooth pseudo-random offset (dx, dy, rot) for camera shake."""
    r = np.random.default_rng(seed)
    ph = r.uniform(0, 6.28, 6)
    dx = amp * (math.sin(t * freq + ph[0]) + 0.5 * math.sin(t * freq * 2.3 + ph[1]))
    dy = amp * (math.sin(t * freq * 1.1 + ph[2]) + 0.5 * math.sin(t * freq * 1.9 + ph[3]))
    rot = amp * 0.02 * math.sin(t * freq * 0.9 + ph[4])
    return dx, dy, rot


# ---------- text ----------
_font_cache = {}


def font(path, size):
    k = (path, size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(path, size)
    return _font_cache[k]


def text_img(text, path, size, fill="white", stroke=0, stroke_fill="black", shadow=0,
             shadow_alpha=150, max_w=None, spacing=1.12, align="center", tracking=0):
    """Render (possibly multi-line) text to a tight RGBA image."""
    f = font(path, size)
    lines = text.split("\n")
    if max_w:
        wrapped = []
        for ln in lines:
            words, cur = ln.split(" "), ""
            for wd in words:
                trial = (cur + " " + wd).strip()
                if f.getlength(trial) + stroke * 2 > max_w and cur:
                    wrapped.append(cur)
                    cur = wd
                else:
                    cur = trial
            wrapped.append(cur)
        lines = wrapped

    def lw(s):
        return f.getlength(s) + tracking * max(len(s) - 1, 0)

    asc, desc = f.getmetrics()
    lh = int((asc + desc) * spacing)
    pad = stroke + shadow + 8
    tw = int(max(lw(s) for s in lines)) + pad * 2
    th = lh * len(lines) + pad * 2
    img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))

    def draw_into(im, color, sw, sf, off):
        d = ImageDraw.Draw(im)
        for i, s in enumerate(lines):
            x = pad + (tw - 2 * pad - lw(s)) / 2 if align == "center" else pad
            y = pad + i * lh
            if tracking:
                for ch in s:
                    d.text((x + off, y + off), ch, font=f, fill=color, stroke_width=sw, stroke_fill=sf)
                    x += f.getlength(ch) + tracking
            else:
                d.text((x + off, y + off), s, font=f, fill=color, stroke_width=sw, stroke_fill=sf)

    if shadow:
        sh = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        draw_into(sh, (0, 0, 0, shadow_alpha), stroke, (0, 0, 0, shadow_alpha), shadow // 2)
        sh = sh.filter(ImageFilter.GaussianBlur(shadow / 2))
        img.alpha_composite(sh)
    draw_into(img, fill, stroke, stroke_fill, 0)
    return img


def paste(canvas, im, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    """Alpha-composite im onto canvas centred at (cx, cy)."""
    if alpha <= 0.001 or scale <= 0.01:
        return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 1.0:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im = im.copy()
        im.putalpha(a)
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def logo(color="white", width=600):
    im = Image.open(os.path.join(ASSETS, f"boxabl-logo-{color}.png")).convert("RGBA")
    im = im.crop(im.getbbox())
    return im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)


# ---------- image effects ----------
def vignette(strength=0.55):
    y, x = np.ogrid[:H, :W]
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
    v = 1 - strength * np.clip(d, 0, 1) ** 2.2
    return v[..., None].astype(np.float32)


def grain_bank(n=6, amt=10, seed=1):
    r = np.random.default_rng(seed)
    return [r.normal(0, amt, (H, W, 1)).astype(np.float32) for _ in range(n)]


def grade(arr, lift=(0, 0, 0), gain=(1, 1, 1), sat=1.0):
    a = arr.astype(np.float32)
    if sat != 1.0:
        g = a.mean(axis=2, keepdims=True)
        a = g + (a - g) * sat
    a = a * np.array(gain, np.float32) + np.array(lift, np.float32)
    return a


def rgb_split(img, px):
    if px < 1:
        return img
    r, g, b = img.split()
    r = r.transform(img.size, Image.AFFINE, (1, 0, -px, 0, 1, 0))
    b = b.transform(img.size, Image.AFFINE, (1, 0, px, 0, 1, 0))
    return Image.merge("RGB", (r, g, b))


def blur(img, r):
    return img.filter(ImageFilter.GaussianBlur(r))


def darken(img, k):
    return ImageEnhance.Brightness(img).enhance(k)


def desat(img, k):
    return ImageEnhance.Color(img).enhance(k)


# ---------- audio synth (numpy, mono 44.1k) ----------
def silence(sec):
    return np.zeros(int(sec * SR), np.float32)


def env_exp(n, decay):
    t = np.arange(n) / SR
    return np.exp(-t / decay).astype(np.float32)


def noise(sec, seed=0):
    return np.random.default_rng(seed).uniform(-1, 1, int(sec * SR)).astype(np.float32)


def onepole(x, cutoff):
    """One-pole-style low-pass applied in the frequency domain."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    h = 1 / np.sqrt(1 + (f / cutoff) ** 2)
    return np.fft.irfft(np.fft.rfft(x) * h, n).astype(np.float32)


def bandpass(x, lo, hi):
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    h = ((f > lo) & (f < hi)).astype(np.float32)
    return np.fft.irfft(np.fft.rfft(x) * h, n).astype(np.float32)


def highpass(x, cut):
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    h = 1 - 1 / np.sqrt(1 + (f / cut) ** 2)
    return np.fft.irfft(np.fft.rfft(x) * h, n).astype(np.float32)


def sine(freq, sec, phase=0.0):
    t = np.arange(int(sec * SR)) / SR
    if callable(freq):
        ph = 2 * math.pi * np.cumsum(freq(t)) / SR
        return np.sin(ph + phase).astype(np.float32)
    return np.sin(2 * math.pi * freq * t + phase).astype(np.float32)


def sfx_kick(sec=0.45):
    s = sine(lambda t: 45 + 110 * np.exp(-t * 28), sec)
    return s * env_exp(len(s), 0.16)


def sfx_boom(sec=2.2):
    s = sine(lambda t: 32 + 60 * np.exp(-t * 6), sec) * env_exp(int(sec * SR), 0.7)
    n = onepole(noise(sec, 3), 400) * env_exp(int(sec * SR), 0.25) * 2.5
    return np.tanh((s + n) * 1.6) * 0.9


def sfx_clap(sec=0.25):
    n = bandpass(noise(sec, 5), 900, 5000) * env_exp(int(sec * SR), 0.05)
    return n * 1.4


def sfx_hat(sec=0.06):
    return highpass(noise(sec, 7), 7000) * env_exp(int(sec * SR), 0.015) * 0.9


def sfx_whoosh(sec=0.6, up=True):
    n = noise(sec, 11)
    t = np.linspace(0, 1, len(n))
    e = np.sin(np.pi * t) ** 2
    lo = onepole(n, 600) * (1 - t if up else t)
    hi = bandpass(n, 1500, 6000) * (t if up else 1 - t)
    return ((lo * 1.5 + hi) * e).astype(np.float32)


def sfx_pop(sec=0.12, f0=600, f1=1400):
    s = sine(lambda t: f0 + (f1 - f0) * np.clip(t / sec, 0, 1), sec)
    return s * env_exp(len(s), 0.035) * 0.8


def sfx_ding(sec=1.4, f=1318.5):
    s = (sine(f, sec) + 0.4 * sine(f * 2.01, sec) + 0.2 * sine(f * 3.0, sec))
    return s * env_exp(len(s), 0.45) * 0.35


def sfx_scratch(sec=0.55):
    n = noise(sec, 13)
    t = np.arange(len(n)) / SR
    wob = np.sin(2 * np.pi * (9 * t + 4 * t * t)) * 0.5 + 0.5
    out = bandpass(n, 300, 3500) * (0.3 + wob)
    e = np.minimum(1, t / 0.02) * np.exp(-t / 0.35)
    return (out * e * 1.6).astype(np.float32)


def sfx_riser(sec=1.2):
    n = noise(sec, 17)
    t = np.linspace(0, 1, len(n))
    s = sine(lambda tt: 200 + 900 * (tt / sec) ** 2, sec) * 0.3
    return ((bandpass(n, 1000, 8000) * 0.5 + s) * t ** 2).astype(np.float32)


def sfx_boing(sec=0.6):
    s = sine(lambda t: 220 + 160 * np.sin(2 * np.pi * 9 * t) * np.exp(-t * 4), sec)
    return s * env_exp(len(s), 0.25) * 0.6


def pad_chord(sec, freqs, amp=0.12, trem=0.15, seed=0):
    t = np.arange(int(sec * SR)) / SR
    out = np.zeros_like(t, dtype=np.float32)
    r = np.random.default_rng(seed)
    for f in freqs:
        for det in (-0.6, 0.0, 0.7):
            out += np.sin(2 * np.pi * (f + det) * t + r.uniform(0, 6.28)).astype(np.float32)
    out /= (len(freqs) * 3)
    out *= (1 - trem + trem * np.sin(2 * np.pi * 0.25 * t)).astype(np.float32)
    att = np.minimum(1, t / 1.5).astype(np.float32)
    return out * att * amp


def wind(sec, amp=0.08, seed=21):
    n = onepole(noise(sec, seed), 350)
    t = np.arange(len(n)) / SR
    gust = 0.6 + 0.4 * np.sin(2 * np.pi * 0.13 * t) * np.sin(2 * np.pi * 0.071 * t + 1)
    n = n / (np.abs(n).max() + 1e-9)
    return (n * gust * amp).astype(np.float32)


class Mix:
    def __init__(self, sec):
        self.buf = np.zeros(int(sec * SR) + SR, np.float32)

    def add(self, clip, at, gain=1.0):
        i = int(at * SR)
        j = min(len(self.buf), i + len(clip))
        if j > i:
            self.buf[i:j] += clip[: j - i] * gain

    def duck(self, t0, t1, k):
        i, j = int(t0 * SR), int(t1 * SR)
        self.buf[i:j] *= k

    def write(self, path, sec):
        b = self.buf[: int(sec * SR)]
        # fade out last 0.25 s
        n = int(0.25 * SR)
        b[-n:] *= np.linspace(1, 0, n, dtype=np.float32)
        peak = np.abs(b).max() + 1e-9
        b = np.tanh(b / peak * 1.2) * 0.89
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((b * 32767).astype("<i2").tobytes())


# ---------- encoding ----------
class Encoder:
    def __init__(self, path, audio):
        self.p = subprocess.Popen([
            "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio,
            "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "slow", "-crf", "19",
            "-maxrate", "14M", "-bufsize", "28M", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
            "-movflags", "+faststart", path], stdin=subprocess.PIPE)

    def write(self, img):
        self.p.stdin.write(img.tobytes())

    def close(self):
        self.p.stdin.close()
        self.p.wait()
        if self.p.returncode:
            raise SystemExit("ffmpeg failed")
