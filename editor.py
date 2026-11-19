#!/usr/bin/env python3
"""Tiny frame-by-frame vertical-video editor for clipping (1080x1920, 30 fps).

A video is a list of Shots (pieces of the source) plus timeline events:
  - punch-in zooms with screen shake
  - flashes: white "backflash", green (correct) / red (wrong) screen tints
  - freeze frames, slow-mo / speed-ups
  - pop-up text, auto word-by-word captions from the whisper transcript
  - synthesised sound effects (see sfx.py), bleeps over swear words

Only the provided source footage is used for picture; original audio is kept.
"""
import json
import math
import os
import subprocess
import tempfile
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import sfx

ROOT = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(ROOT, "assets", "fonts")
W, H, FPS = 1080, 1920, 30
SRC_W, SRC_H = 1920, 1080
ASR = sfx.SR

# whisper mishearings -> what is actually said
FIXES = {"jake": "Jay", "ora": "aura", "skully": "skully", "alay": "LA", "alay's": "LA's"}

SWEARS = {"fuck", "fucking", "fucked", "shit", "bitch", "ass", "damn", "motherfucker", "fuckin"}


def is_swear(w):
    w = w.strip(" ,.?!").lower()
    return w in SWEARS or ("*" in w and w[:1].isalpha())


def font(name, size):
    if name == "montserrat":
        f = ImageFont.truetype(os.path.join(FONTS, "Montserrat-VF.ttf"), size)
        f.set_variation_by_name("Black")
        return f
    if name == "dejavu":
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    files = {"anton": "Anton-Regular.ttf", "bangers": "Bangers-Regular.ttf",
             "luckiest": "LuckiestGuy-Regular.ttf"}
    if name in files:
        return ImageFont.truetype(os.path.join(FONTS, files[name]), size)
    return ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Black.otf", size)


# --------------------------------------------------------------------------- data

@dataclass
class Shot:
    src_in: float
    src_out: float
    cx: float = 960          # crop centre in source pixels (x)
    cy: float = 540
    zoom: float = 1.0        # 1.0 = full source height fills the 9:16 frame
    zoom_end: float = None   # slow push-in/out across the shot
    cx_end: float = None     # pan across the shot
    speed: float = 1.0
    freeze: float = 0.0      # hold the last frame this long (seconds)
    layout: str = "crop"     # "crop" (full-screen 9:16) or "fit" (16:9 over blurred bg)
    audio: str = "normal"    # normal | mute | pitch (slow-mo pitch drop)
    gain: float = 1.0
    captions: bool = True
    bw: bool = False         # black & white (for freeze frames / dramatic beats)
    v_in: float = None       # J-cut: take picture from here instead of src_in (audio stays at src_in)
    # filled by timeline
    t0: float = 0.0

    @property
    def run(self):
        return (self.src_out - self.src_in) / self.speed

    @property
    def dur(self):
        return self.run + self.freeze


@dataclass
class Text:
    t0: float
    t1: float
    text: str
    y: float = 0.22          # vertical centre, fraction of H
    x: float = 0.5           # horizontal centre, fraction of W
    size: int = 96
    font: str = "montserrat"
    fill: tuple = (255, 255, 255)
    stroke: tuple = (0, 0, 0)
    stroke_w: int = 10
    box: tuple = None        # background box colour (r,g,b,a)
    anim: str = "pop"        # pop | slide | none | shake
    rot: float = 0.0
    width: int = 18          # wrap width (chars)
    sound: str = None        # sfx to play at t0


@dataclass
class Fx:
    t: float
    kind: str                # flash | green | red | punch | shake | rgb | bw
    dur: float = 0.25
    amount: float = 1.0
    color: tuple = (255, 255, 255)


@dataclass
class Sound:
    t: float
    name: str
    gain: float = 1.0


@dataclass
class Video:
    shots: list
    texts: list = field(default_factory=list)
    fx: list = field(default_factory=list)
    sounds: list = field(default_factory=list)
    caption_style: dict = field(default_factory=dict)
    bleep: bool = True
    progress_bar: tuple = None   # colour of a thin top progress bar, or None


# --------------------------------------------------------------------------- source IO

class Source:
    def __init__(self, path, words_json=None):
        self.path = path
        self.words = []
        if words_json and os.path.exists(words_json):
            for seg in json.load(open(words_json)):
                for w in seg["words"]:
                    word = w["w"].strip()
                    if word.startswith("-") and self.words:   # "Bieber" "-esque" -> one word
                        ps, pe, pw = self.words.pop()
                        self.words.append((ps, w["e"], pw + word))
                        continue
                    key = word.strip(" ,.?!").lower()
                    if key in FIXES:
                        word = word.lower().replace(key, FIXES[key])
                    self.words.append((w["s"], w["e"], word))

    def override(self, t0, t1, words):
        """replace the transcript between t0 and t1 with hand-checked (start, end, word) tuples."""
        self.words = [w for w in self.words if not (t0 <= w[0] < t1)] + list(words)
        self.words.sort()

    def frames(self, t_in, t_out, speed):
        """yield RGB uint8 frames (SRC_H, SRC_W, 3) at FPS output rate."""
        dur = t_out - t_in
        n = int(round(dur / speed * FPS))
        vf = f"setpts=(PTS-STARTPTS)/{speed},fps={FPS}"
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{t_in:.3f}", "-t", f"{dur + 0.2:.3f}", "-i", self.path,
               "-vf", vf, "-frames:v", str(n), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        sz = SRC_W * SRC_H * 3
        last, got = None, 0
        for _ in range(n):
            buf = p.stdout.read(sz)
            if len(buf) < sz:
                break
            last = np.frombuffer(buf, np.uint8).reshape(SRC_H, SRC_W, 3)
            got += 1
            yield last
        p.stdout.close()
        p.wait()
        while got < n and last is not None:   # pad if the decoder came up short
            got += 1
            yield last

    def audio(self, t_in, t_out):
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{t_in:.3f}", "-t", f"{t_out - t_in:.3f}", "-i", self.path,
               "-vn", "-ac", "2", "-ar", str(ASR), "-f", "f32le", "-"]
        raw = subprocess.check_output(cmd)
        a = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
        want = int(round((t_out - t_in) * ASR))
        if len(a) < want:
            a = np.vstack([a, np.zeros((want - len(a), 2), np.float32)])
        return a[:want]


# --------------------------------------------------------------------------- text rendering

_text_cache = {}


def _wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def render_text(text, size, fname, fill, stroke, stroke_w, box=None, width=18, highlight=None, hl_fill=None):
    """Return an RGBA image of the text block. `highlight` is a word index to colour hl_fill."""
    key = (text, size, fname, fill, stroke, stroke_w, box, width, highlight, hl_fill)
    if key in _text_cache:
        return _text_cache[key]
    f = font(fname, size)
    lines = _wrap(text, width)
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lh = int(size * 1.12)
    widths = [tmp.textlength(l, font=f) for l in lines]
    pad = stroke_w + 24
    bw = int(max(widths) + pad * 2)
    bh = int(lh * len(lines) + pad * 2)
    img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if box:
        d.rounded_rectangle([pad // 2, pad // 2, bw - pad // 2, bh - pad // 2], radius=28, fill=box)
    wi = 0
    for li, (line, lw) in enumerate(zip(lines, widths)):
        x = (bw - lw) / 2
        y = pad + li * lh
        for word in line.split(" "):
            col = hl_fill if (highlight is not None and wi == highlight) else fill
            if stroke_w:
                d.text((x, y), word, font=f, fill=col, stroke_width=stroke_w, stroke_fill=stroke)
            else:
                d.text((x, y), word, font=f, fill=col)
            x += tmp.textlength(word + " ", font=f)
            wi += 1
    if not box and stroke_w:   # soft drop shadow for readability
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.paste((0, 0, 0, 150), mask=img.split()[3])
        sh = sh.filter(ImageFilter.GaussianBlur(8))
        base = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        base.alpha_composite(sh, (0, 8))
        base.alpha_composite(img)
        img = base
    _text_cache[key] = img
    return img


def ease_out_back(x):
    c1, c3 = 1.70158, 2.70158
    x = min(max(x, 0), 1)
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def place(canvas, img, cx, cy, scale=1.0, rot=0.0, alpha=1.0):
    if scale <= 0.01 or alpha <= 0.01:
        return
    if scale != 1.0:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BILINEAR)
    if rot:
        img = img.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        a = img.split()[3].point(lambda v: int(v * alpha))
        img = img.copy()
        img.putalpha(a)
    canvas.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


# --------------------------------------------------------------------------- render

def layout_timeline(v):
    t = 0.0
    for s in v.shots:
        s.t0 = t
        t += s.dur
    return t


def build_captions(v, src):
    """word-by-word caption chunks mapped onto the output timeline."""
    st = dict(dict(words=3, size=92, font="montserrat", fill=(255, 255, 255), hl=(255, 230, 0),
                   y=0.70, stroke_w=11, upper=True), **v.caption_style)
    chunks = []
    for s in v.shots:
        if not s.captions:
            continue
        ws = [w for w in src.words if w[0] >= s.src_in - 0.05 and w[1] <= s.src_out + 0.15 and w[2]]
        group = []
        for w in ws:
            if group and (len(group) >= st["words"] or w[0] - group[-1][1] > 0.6
                          or group[-1][2][-1:] in ".?!,"):
                chunks.append((s, group))
                group = []
            group.append(w)
        if group:
            chunks.append((s, group))
    items = []
    for i, (s, g) in enumerate(chunks):
        to_out = lambda x, s=s: s.t0 + (min(max(x, s.src_in), s.src_out) - s.src_in) / s.speed
        start = to_out(g[0][0])
        end = to_out(g[-1][1]) + 0.25
        if i + 1 < len(chunks) and chunks[i + 1][0] is s:
            end = min(end, s.t0 + (chunks[i + 1][1][0][0] - s.src_in) / s.speed)
        end = min(end, s.t0 + s.run)
        words = []
        for w in g:
            raw = w[2].strip(" ,.?!").replace("…", "")
            if is_swear(raw):
                raw = raw[0] + "***"
            words.append((to_out(w[0]), raw.upper() if st["upper"] else raw))
        items.append((start, end, words))
    return items, st


def frame_for(shot, src_frame, t_local, punch, shake):
    """crop/zoom one source frame into a 1080x1920 PIL image."""
    p = t_local / max(shot.dur, 1e-6)
    z = shot.zoom + ((shot.zoom_end or shot.zoom) - shot.zoom) * min(p * shot.dur / max(shot.run, 1e-6), 1)
    cx = shot.cx + ((shot.cx_end if shot.cx_end is not None else shot.cx) - shot.cx) * min(p * shot.dur / max(shot.run, 1e-6), 1)
    z *= punch
    im = Image.fromarray(src_frame)
    if shot.layout == "fit":
        bg = im.resize((W // 6, H // 6), Image.BILINEAR, box=(960 - 304, 0, 960 + 304, 1080))
        bg = bg.filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR)
        bg = Image.eval(bg, lambda v: int(v * 0.45))
        fw = int(W * z)
        fh = int(fw * SRC_H / SRC_W)
        fg = im.resize((fw, fh), Image.BICUBIC)
        out = bg
        out.paste(fg, (int((W - fw) / 2 + shake[0]), int((H - fh) / 2 + shake[1])))
        return out
    ch = SRC_H / z
    cw = ch * W / H
    cx += shake[0] * cw / W
    cy = shot.cy + shake[1] * ch / H
    x0 = min(max(cx - cw / 2, 0), SRC_W - cw)
    y0 = min(max(cy - ch / 2, 0), SRC_H - ch)
    return im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


def render(v, src, out_path, preview=False):
    total = layout_timeline(v)
    nframes = int(round(total * FPS))
    caps, cst = build_captions(v, src)
    rng = np.random.default_rng(3)

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
        for s in v.shots:
            vin = s.src_in if s.v_in is None else s.v_in
            frames = list(src.frames(vin, vin + s.src_out - s.src_in, s.speed))
            n_run = len(frames)
            n_tot = int(round((s.t0 + s.dur) * FPS)) - int(round(s.t0 * FPS))
            for k in range(n_tot):
                if fi >= nframes:
                    break
                t = fi / FPS
                src_frame = frames[min(k, n_run - 1)]
                punch, shake, tint = 1.0, [0.0, 0.0], []
                bw = s.bw and k >= n_run
                rgb_split = 0
                for e in v.fx:
                    dt = t - e.t
                    if dt < 0 or dt > e.dur:
                        continue
                    x = dt / e.dur
                    if e.kind == "punch":       # zoom kick that eases back out
                        punch *= 1 + (e.amount - 1) * (1 - x) ** 2 if x > 0.15 else 1 + (e.amount - 1) * ease_out_back(x / 0.15)
                    elif e.kind == "hold":      # zoom held for the whole duration
                        punch *= e.amount
                    elif e.kind == "shake":
                        a = 26 * e.amount * (1 - x)
                        shake[0] += rng.uniform(-a, a)
                        shake[1] += rng.uniform(-a, a)
                    elif e.kind in ("flash", "green", "red", "tint"):
                        col = {"flash": (255, 255, 255), "green": (20, 220, 90), "red": (235, 30, 40)}.get(e.kind, e.color)
                        alpha = e.amount * ((1 - x) ** 1.6 if e.kind == "flash" else
                                            (0.55 * min(1, x / 0.12) * (1 - max(0, (x - 0.6) / 0.4))))
                        tint.append((col, alpha))
                    elif e.kind == "rgb":
                        rgb_split = max(rgb_split, int(18 * e.amount * (1 - x)))
                    elif e.kind == "bw":
                        bw = True
                img = frame_for(s, src_frame, k / FPS, punch, shake)
                arr = np.asarray(img).astype(np.float32)
                if bw:
                    g = arr @ np.array([0.299, 0.587, 0.114], np.float32)
                    arr = np.repeat(g[..., None], 3, 2) * 0.95
                if rgb_split:
                    arr[..., 0] = np.roll(arr[..., 0], rgb_split, 1)
                    arr[..., 2] = np.roll(arr[..., 2], -rgb_split, 1)
                for col, alpha in tint:
                    if alpha <= 0:
                        continue
                    if col == (255, 255, 255):    # backflash: overexpose then fade
                        arr = arr + (255 - arr) * min(alpha, 1)
                    else:                         # coloured screen tint + edge glow
                        arr = arr * (1 - alpha * 0.6) + np.array(col, np.float32) * alpha * 0.6
                        arr = arr * (1 - alpha * 0.5 * VIGNETTE) + np.array(col, np.float32) * alpha * 0.5 * VIGNETTE
                frame = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")

                # captions
                for c0, c1, words in caps:
                    if c0 <= t < c1:
                        active = max([i for i, (wt, _) in enumerate(words) if wt <= t + 0.02] or [0])
                        txt = " ".join(w for _, w in words)
                        im = render_text(txt, cst["size"], cst["font"], cst["fill"], (0, 0, 0), cst["stroke_w"],
                                         width=cst.get("width", 16), highlight=active, hl_fill=cst["hl"])
                        sc = 0.8 + 0.2 * ease_out_back((t - c0) / 0.12)
                        place(frame, im, W / 2, H * cst["y"], scale=sc)
                # pop-up texts
                for tx in v.texts:
                    if tx.t0 <= t < tx.t1:
                        im = render_text(tx.text, tx.size, tx.font, tx.fill, tx.stroke, tx.stroke_w, tx.box, tx.width)
                        a = (t - tx.t0)
                        sc, cx, rot, al = 1.0, W * tx.x, tx.rot, 1.0
                        if tx.anim == "pop":
                            sc = ease_out_back(a / 0.18)
                        elif tx.anim == "slide":
                            cx = W * tx.x + (1 - ease_out_back(a / 0.25)) * W
                        elif tx.anim == "shake":
                            sc = ease_out_back(a / 0.15)
                            rot += math.sin(a * 40) * 4 * max(0, 1 - a / 0.6)
                        if tx.t1 - t < 0.1:
                            al = (tx.t1 - t) / 0.1
                        place(frame, im, cx, H * tx.y, scale=sc, rot=rot, alpha=al)
                if v.progress_bar:
                    d = ImageDraw.Draw(frame)
                    d.rectangle([0, 0, int(W * t / total), 12], fill=v.progress_bar)
                enc.stdin.write(frame.convert("RGB").tobytes())
                fi += 1
        enc.stdin.close()
        enc.wait()
    return total


def _vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / math.sqrt(2)
    return np.clip((d - 0.35) / 0.65, 0, 1)[..., None] ** 1.5


VIGNETTE = _vignette()


# --------------------------------------------------------------------------- audio

def bleep_tone(n):
    t = np.arange(n) / ASR
    e = np.minimum(1, np.minimum(t, (n / ASR - t)) / 0.008)
    return (np.sin(2 * np.pi * 1000 * t) * 0.45 * e).astype(np.float32)


def mix_audio(v, src, total, path):
    n = int(round(total * ASR)) + ASR
    out = np.zeros((n, 2), np.float32)
    fade = int(0.006 * ASR)
    for s in v.shots:
        if s.audio == "mute":
            continue
        a = src.audio(s.src_in, s.src_out) * s.gain
        if v.bleep:   # replace swear words with a 1 kHz bleep
            for ws, we, w in src.words:
                if is_swear(w) and ws >= s.src_in and we <= s.src_out:
                    i0, i1 = int((ws - s.src_in) * ASR), int((we - s.src_in) * ASR)
                    a[i0:i1] = bleep_tone(i1 - i0)[:, None]
        if s.speed != 1.0:
            m = int(len(a) / s.speed)
            idx = np.linspace(0, len(a) - 1, m)
            a = np.stack([np.interp(idx, np.arange(len(a)), a[:, c]) for c in range(2)], 1).astype(np.float32)
            if s.audio == "normal" and s.speed < 1:
                a *= 0.6
        a[:fade] *= np.linspace(0, 1, fade)[:, None]
        a[-fade:] *= np.linspace(1, 0, fade)[:, None]
        i = int(round(s.t0 * ASR))
        out[i:i + len(a)] += a[:max(0, n - i)]
    for snd in v.sounds:
        x = sfx.get(snd.name) * snd.gain * 0.55
        i = int(round(snd.t * ASR))
        j = min(n, i + len(x))
        out[i:j] += x[:j - i, None]
    out = np.tanh(out * 1.1) / np.tanh(1.1)
    sfx.write_wav(path, out[: int(round(total * ASR))])
