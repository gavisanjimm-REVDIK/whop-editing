#!/usr/bin/env python3
"""Render Scenes 1-3 of "A Day in My Life as a Pisay Scholar - Dorm Edition".

Minimalist edit: simple cuts, small plain captions, clean type. The only effect is the
crumpled-paper opening used whenever real footage cuts to a text-only graphic (and the
sheet crumpling away when going back to footage).

Media (names as in the shared Drive folder / script labels) go in footage/drive/:
  VID1.MOV  wake up            VO1.m4a  Scene 1 voice-over
  VID2.MOV  closet / perfume   VO2.m4a  Scene 2 voice-over
  VID3.MOV  cards + coins      VO3.m4a  "We surveyed 47 ..."
  VID4.MOV  laptop             VO4.m4a  "About three out of four ..."
  VID5.MOV  balcony

  python3 render.py                    # full render -> out/scenes1-3.mp4
  python3 render.py --stills 6 40 75   # preview stills -> out/stills/
"""
import argparse
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import sfx
from paper import H, W, Paper

ROOT = os.path.dirname(os.path.abspath(__file__))
MEDIA = os.path.join(ROOT, "footage", "drive")
CACHE = os.path.join(ROOT, "cache")
FPS = 30

F_INTER = "/usr/share/fonts/opentype/inter/"
F_BLACK = F_INTER + "Inter-ExtraBold.otf"
F_BOLD = F_INTER + "Inter-Bold.otf"
F_SEMI = F_INTER + "Inter-SemiBold.otf"
F_MED = F_INTER + "Inter-Medium.otf"

INK = (22, 22, 24)
GREY = (95, 95, 100)
RED = (200, 38, 52)
WHITE = (255, 255, 255)


def media(name):
    return os.path.join(MEDIA, name)


_fonts = {}


def font(path, size):
    if (path, size) not in _fonts:
        _fonts[(path, size)] = ImageFont.truetype(path, size)
    return _fonts[(path, size)]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, t0, dur):
    return clamp((t - t0) / dur) if dur > 0 else float(t >= t0)


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def lerp(a, b, t):
    return a + (b - a) * t


# ---------------------------------------------------------------- footage
class Clip:
    """Streams a footage segment through ffmpeg; frame(k) needs non-decreasing k and
    freezes on the last frame past the end."""

    def __init__(self, path, ss, dur, speed=1.0, grade=""):
        vf = f"setpts=(PTS-STARTPTS)/{speed},fps={FPS},scale={W}:{H}:flags=lanczos,setsar=1"
        if grade:
            vf += "," + grade
        self.cmd = ["ffmpeg", "-v", "error", "-ss", f"{ss}", "-t", f"{dur / speed + 0.5}", "-i", path,
                    "-vf", vf, "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.p, self.k, self.last = None, -1, None
        self.n = int(round(dur / speed * FPS))

    def frame(self, k):
        k = min(max(k, 0), self.n - 1)
        if self.p is None:
            self.p = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        while self.k < k:
            buf = self.p.stdout.read(W * H * 3)
            if len(buf) < W * H * 3:
                self.k = k
                break
            self.last = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            self.k += 1
        return self.last.astype(np.float32)


def ensure_slowmo():
    """Optical-flow slow motion of the coins (VID3 1.75-3.0 s at 0.3x)."""
    out = os.path.join(CACHE, "vid3_slowmo.mp4")
    if not os.path.exists(out):
        os.makedirs(CACHE, exist_ok=True)
        print("building slow-mo (one time, ~2 min)...", flush=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1.75", "-t", "1.3", "-i", media("VID3.MOV"), "-an",
                        "-vf", "setpts=PTS/0.3,minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
                        "-c:v", "libx264", "-crf", "12", "-preset", "fast", out], check=True)
    return out


# ---------------------------------------------------------------- drawing helpers
def text_img(text, fpath, size, fill, shadow=0.0):
    f = font(fpath, size)
    l, t, r, b = f.getbbox(text)
    pad = 24 if shadow else 4
    img = Image.new("RGBA", (r - l + 2 * pad, b - t + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(img).text((pad - l, pad - t), text, font=f, fill=fill)
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        a = img.split()[3].point(lambda v: int(v * shadow))
        blk = Image.new("RGBA", img.size, (0, 0, 0, 255))
        blk.putalpha(a)
        sh.alpha_composite(blk, (0, 2))
        wide = sh.filter(ImageFilter.GaussianBlur(7))
        tight = sh.filter(ImageFilter.GaussianBlur(2))
        wide.alpha_composite(tight)
        wide.alpha_composite(img)
        img = wide
    return img


def paste(frame, img, cx, cy, alpha=1.0):
    if img is None or alpha <= 0:
        return frame
    a = np.asarray(img, dtype=np.float32)
    h, w = a.shape[:2]
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return frame
    sub = a[fy0 - y0:fy1 - y0, fx0 - x0:fx1 - x0]
    al = sub[..., 3:4] / 255.0 * alpha
    frame[fy0:fy1, fx0:fx1] = frame[fy0:fy1, fx0:fx1] * (1 - al) + sub[..., :3] * al
    return frame


# ---------------------------------------------------------------- captions
_cap = {}


def caption(frame, phrases, t, t0):
    """phrases: list of (text, start, end) in seconds relative to t0. Small, plain, white."""
    lt = t - t0
    for text, s, e in phrases:
        if s - 0.05 <= lt < e + 0.15:
            if text not in _cap:
                _cap[text] = text_img(text, F_SEMI, 40, WHITE, shadow=0.95)
            a = min(prog(lt, s - 0.05, 0.12), 1 - prog(lt, e + 0.05, 0.1))
            paste(frame, _cap[text], W / 2, 985, alpha=a)
            return


# ---------------------------------------------------------------- text-only graphics (ink on paper)
def ink_canvas():
    return Image.new("RGB", (W, H), "white")


def fade_col(col, p):
    return tuple(int(lerp(255, c, p)) for c in col)


def tg_title(t):
    """Text-graphics 1: project title. t = seconds since the sheet is fully open."""
    img = ink_canvas()
    d = ImageDraw.Draw(img)
    d.text((W / 2, 440), "COSTS BEHIND THE CHANCE", font=font(F_BLACK, 112), fill=INK, anchor="mm")
    p = ease_out(prog(t, 0.25, 0.6))
    if p > 0:
        d.line([(W / 2 - 90, 540), (W / 2 + 90, 540)], fill=fade_col(RED, p), width=5)
        for i, s in enumerate(["Financial Considerations and Student Participation",
                               "in Extracurricular Opportunities at PSHS-CRC"]):
            d.text((W / 2, 610 + i * 58), s, font=font(F_MED, 42), fill=fade_col(GREY, p), anchor="mm")
    return np.asarray(img)


def tg_survey(t):
    """Text-graphics 2 (with VO3): we surveyed 47 PSHS-CRC students."""
    img = ink_canvas()
    d = ImageDraw.Draw(img)
    d.text((W / 2, 300), "We surveyed", font=font(F_SEMI, 52), fill=GREY, anchor="mm")
    d.text((W / 2, 470), "47", font=font(F_BLACK, 240), fill=INK, anchor="mm")
    d.text((W / 2, 630), "PSHS-CRC STUDENTS", font=font(F_BOLD, 64), fill=INK, anchor="mm")
    p = ease_out(prog(t, 3.2, 0.6))
    if p > 0:
        for i, s in enumerate(["to find out how expenses affect their participation",
                               "in extracurricular activities"]):
            d.text((W / 2, 760 + i * 54), s, font=font(F_MED, 40), fill=fade_col(GREY, p), anchor="mm")
    return np.asarray(img)


def tg_stat(t, vo4):
    """76.6% (end of VO3), then 36 out of 47 and the finding as VO4 says it.
    vo4 = seconds since VO4 started (negative before)."""
    img = ink_canvas()
    d = ImageDraw.Draw(img)
    p = ease_out(prog(t, 0.0, 0.5))
    d.text((W / 2, 400), "76.6%", font=font(F_BLACK, 250), fill=fade_col(INK, p), anchor="mm")
    q = ease_out(prog(vo4, 1.85, 0.5))           # "three out of four"
    if q > 0:
        d.text((W / 2, 590), "36 out of 47 students", font=font(F_BOLD, 60), fill=fade_col(RED, q), anchor="mm")
    r = ease_out(prog(vo4, 3.55, 0.6))           # "had declined, limited, or discontinued"
    if r > 0:
        for i, s in enumerate(["had declined, limited, or discontinued",
                               "an opportunity because of expenses"]):
            d.text((W / 2, 720 + i * 58), s, font=font(F_MED, 44), fill=fade_col(GREY, r), anchor="mm")
    return np.asarray(img)


# ================================================================ TIMELINE (output seconds)
# Scene 1 -------------------------------------------------------------
VO1_A = (0.0, 5.30)       # Welcome ... dormer edition
VO1_B = (5.45, 11.30)     # Hi, I'm Jimm ... on my own
VO1_C = (11.40, 16.20)    # And aside from ... to manage
VO1_D = (16.30, 18.84)    # my allowance
T_VID1, AT_A = 0.0, 0.30
T_VID2, AT_B = 8.00, 8.20
T_BLACK, AT_C = 15.15, 15.35
T_VID3, AT_D = 19.85, 19.75
# Scene 2 -------------------------------------------------------------
T_VID4 = T_VID3 + 4.17                 # coins slow-mo length
VID4_SS, VID4_ES = 4.7, 18.35
AT_VO2 = T_VID4 + 0.20
T_OPEN1 = T_VID4 + (VID4_ES - VID4_SS)
D_OPEN, D_CLOSE = 1.10, 0.90
T_CLOSE1 = T_OPEN1 + D_OPEN + 4.4
# Scene 3 -------------------------------------------------------------
T_VID5 = T_CLOSE1
VID5_SS, VID5_ES = 0.9, 17.0
T_OPEN2 = T_VID5 + (VID5_ES - VID5_SS)
AT_VO3 = T_OPEN2 + 0.45
T_STAT = AT_VO3 + 10.40                # "here's what we found."
AT_VO4 = T_STAT + 0.35
T_END = AT_VO4 + 8.2 + 1.6

V1 = lambda s: AT_A + s - VO1_A[0]     # VO1 file time -> output time (piece A)

CAP_VO1 = [  # (text, start, end) in output seconds
    ("Welcome to a day in my life", AT_A + 0.76, AT_A + 2.52),
    ("as a Pisay scholar, dormer edition.", AT_A + 2.52, AT_A + 4.85),
    ("Hi, I'm Jimm, and living in the dorm", AT_B + 5.70 - VO1_B[0], AT_B + 7.68 - VO1_B[0]),
    ("means being away from home", AT_B + 7.68 - VO1_B[0], AT_B + 9.20 - VO1_B[0]),
    ("and managing things on my own.", AT_B + 9.20 - VO1_B[0], AT_B + 11.02 - VO1_B[0]),
    ("And aside from classes and requirements,", AT_C + 11.64 - VO1_C[0], AT_C + 13.30 - VO1_C[0]),
    ("there's one thing I also have to manage:", AT_C + 13.86 - VO1_C[0], AT_C + 15.60 - VO1_C[0]),
    ("my allowance.", AT_D + 16.54 - VO1_D[0], AT_D + 17.60 - VO1_D[0]),
]
CAP_VO2 = [(txt, AT_VO2 + s, AT_VO2 + e) for txt, s, e in [
    ("Recently, I came across a competition I wanted to join.", 0.80, 3.70),
    ("It was another chance to learn something new", 4.36, 6.20),
    ("and represent our school.", 6.20, 7.22),
    ("But as a dormer, I also have to think", 7.84, 9.84),
    ("about my everyday expenses.", 9.84, 11.18),
]]
CAP_VID4 = [("Can I actually afford it?", T_VID4 + 16.72 - VID4_SS, T_VID4 + 18.20 - VID4_SS)]
CAP_VID5 = [(txt, T_VID5 + s - VID5_SS, T_VID5 + e - VID5_SS) for txt, s, e in [
    ("As a dormer, budgeting can be a very serious challenge.", 1.44, 4.70),
    ("We need to make sure that our money lasts,", 5.38, 7.00),
    ("not just for our personal needs,", 7.48, 9.76),
    ("but also for academic purposes.", 10.02, 11.56),
    ("And apparently, I'm not the only one", 12.28, 14.14),
    ("who is being challenged by this problem.", 14.14, 15.82),
]]
CAPTIONS = CAP_VO1 + CAP_VO2 + CAP_VID4 + CAP_VID5

GRADE_DORM = "eq=contrast=1.10:saturation=1.15:gamma=0.94"
GRADE_LAPTOP = "eq=contrast=1.20:brightness=-0.04:saturation=1.25:gamma=0.93"
GRADE_SOFT = "eq=contrast=1.05:saturation=1.08"


class Timeline:
    def __init__(self):
        self.paper = Paper(seed=7, lined=False)
        self.vid1 = Clip(media("VID1.MOV"), 0.0, T_VID2 - T_VID1, grade=GRADE_DORM)
        self.vid2 = Clip(media("VID2.MOV"), 0.0, 7.8, grade=GRADE_DORM)
        self.vid3 = Clip(ensure_slowmo(), 0.0, 4.4, grade=GRADE_SOFT)
        self.vid4 = Clip(media("VID4.MOV"), VID4_SS, VID4_ES - VID4_SS + 0.1, grade=GRADE_LAPTOP)
        self.vid5 = Clip(media("VID5.MOV"), VID5_SS, VID5_ES - VID5_SS + 0.1, grade=GRADE_SOFT)
        self.ink_title0 = tg_title(-1)
        self.ink_title1 = tg_title(99)
        self.ink_survey0 = tg_survey(-1)

    @staticmethod
    def k(t, t0):
        return int(round((t - t0) * FPS))

    def render(self, t):
        if t < T_VID2:
            fr = self.vid1.frame(self.k(t, T_VID1))
            self.title(fr, t)
        elif t < T_BLACK:
            fr = self.vid2.frame(self.k(t, T_VID2)) * (1 - prog(t, T_BLACK - 0.45, 0.4))
        elif t < T_VID3:
            fr = np.zeros((H, W, 3), np.float32)
        elif t < T_VID4:
            fr = self.vid3.frame(self.k(t, T_VID3))
        elif t < T_OPEN1:
            fr = self.laptop(t)
        elif t < T_OPEN1 + D_OPEN:
            return self.crumple_open(self.laptop(T_OPEN1 - 1 / FPS), self.ink_title0, t - T_OPEN1)
        elif t < T_CLOSE1:
            return self.paper.card(tg_title(t - T_OPEN1 - D_OPEN))
        elif t < T_OPEN2:
            fr = self.vid5.frame(self.k(t, T_VID5))
            caption(fr, CAPTIONS, t, 0)
            if t < T_CLOSE1 + D_CLOSE:
                fr = self.crumple_close(fr, self.ink_title1, t - T_CLOSE1)
            return fr
        elif t < T_OPEN2 + D_OPEN:
            bg = self.vid5.frame(self.k(T_OPEN2 - 1 / FPS, T_VID5))
            return self.crumple_open(bg, self.ink_survey0, t - T_OPEN2, from_xy=(620, 820), spin=-50)
        elif t < T_STAT:
            return self.paper.card(tg_survey(t - AT_VO3))
        else:
            lt = t - T_STAT
            if lt < 0.35:  # simple cross-fade between the two graphics on the same sheet
                a = tg_survey(99).astype(np.float32)
                ink = a + (255 - a) * ease_in_out(lt / 0.35)
                return self.paper.card(ink)
            return self.paper.card(tg_stat(lt - 0.35, t - AT_VO4))
        caption(fr, CAPTIONS, t, 0)
        return fr

    def laptop(self, t):
        fr = self.vid4.frame(self.k(t, T_VID4))
        src = VID4_SS + (t - T_VID4)
        z = lerp(1.0, 1.08, ease_in_out(prog(src, VID4_SS, 15.6 - VID4_SS)))  # very slow push-in
        if z > 1.001:
            cx, cy = 820, 560
            M = np.float32([[z, 0, cx - z * cx], [0, z, cy - z * cy]])
            fr = cv2.warpAffine(fr, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return fr

    def title(self, fr, t):
        """Title appears once Jimm has walked out of the wake-up shot and stays on the empty bed."""
        t0 = T_VID1 + 5.75
        p = ease_out(prog(t, t0, 0.7))
        if p <= 0:
            return
        o = 1 - prog(t, T_VID2 - 0.35, 0.3)
        a = text_img("A Day in My Life", F_BLACK, 84, INK)
        b = text_img("as a Pisay Scholar  —  Dorm Edition", F_MED, 35, INK)
        paste(fr, a, 530, 390 + (1 - p) * 14, alpha=p * o)
        q = ease_out(prog(t, t0 + 0.35, 0.7))
        paste(fr, b, 530, 468 + (1 - q) * 10, alpha=q * o)

    # --- paper transitions
    def crumple_open(self, bg, ink, lt, from_xy=(1450, 900), spin=70):
        """Crumpled-paper opening: a ball is tossed in, lands, and unfolds into the full sheet."""
        t_in = 0.32
        cx0 = W / 2 + (from_xy[0] - W / 2) * 0.25
        cy0 = H / 2 + (from_xy[1] - H / 2) * 0.25
        if lt < t_in:
            p = ease_out(lt / t_in)
            cx = lerp(from_xy[0] + 380, cx0, p)
            cy = lerp(H + 200, cy0, p) - np.sin(p * np.pi) * 120
            return self.paper.frame(bg, ink, 0.0, ball_r=165 * (0.6 + 0.4 * p), center=(cx, cy),
                                    theta=spin * (1 + 2 * (1 - p)))
        e = ease_in_out(clamp((lt - t_in) / (D_OPEN - t_in)))
        return self.paper.frame(bg, ink, e, ball_r=165, center=(cx0, cy0), theta=spin)

    def crumple_close(self, bg, ink, lt):
        t_c = 0.58
        if lt < t_c:
            e = 1 - ease_in_out(lt / t_c)
            return self.paper.frame(bg, ink, e, ball_r=165, center=(W / 2, H / 2), theta=-60)
        p = clamp((lt - t_c) / (D_CLOSE - t_c)) ** 1.6
        cx = lerp(W / 2, -250, p)
        cy = lerp(H / 2, H / 2 - 260, p) - np.sin(p * np.pi) * 80
        return self.paper.frame(bg, ink, 0.0, ball_r=165 * (1 - 0.35 * p), center=(cx, cy), theta=-60 - 300 * p)


# ---------------------------------------------------------------- audio
def build_audio(path):
    sr = sfx.SR
    n = int((T_END + 1) * sr)
    mix = np.zeros((n, 2), np.float32)

    def load(fname, ss, dur, speed=1.0):
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{ss}", "-t", f"{dur}", "-i", media(fname), "-vn", "-ac", "2",
               "-ar", str(sr)]
        if speed != 1.0:
            cmd += ["-af", f"asetrate={int(sr * speed)},aresample={sr}"]
        a = np.frombuffer(subprocess.check_output(cmd + ["-f", "f32le", "-"]), np.float32).reshape(-1, 2).copy()
        f = min(len(a) // 4, int(0.04 * sr))
        if f > 0:
            a[:f] *= np.linspace(0, 1, f)[:, None]
            a[-f:] *= np.linspace(1, 0, f)[:, None]
        return a

    def level(a, target_db):
        """Scale speech so its loud parts sit at target_db RMS."""
        x = a[:, 0]
        win = sr // 10
        rms = np.sqrt(np.convolve(x * x, np.ones(win) / win, mode="same"))
        ref = np.percentile(rms, 90)
        return a * (10 ** (target_db / 20) / max(ref, 1e-6))

    def put(a, t, gain=1.0):
        i = int(t * sr)
        j = min(n, i + len(a))
        mix[i:j] += a[:j - i] * gain

    # voice-over (already well levelled)
    for (s, e), at in [(VO1_A, AT_A), (VO1_B, AT_B), (VO1_C, AT_C), (VO1_D, AT_D)]:
        put(load("VO1.m4a", s, e - s), at)
    put(load("VO2.m4a", 0, 12.0), AT_VO2)
    put(load("VO3.m4a", 0, 11.0), AT_VO3)
    put(load("VO4.m4a", 0, 9.28), AT_VO4)
    # on-camera lines, levelled to match the VO
    put(level(load("VID4.MOV", 16.55, 1.85), -15.5), T_VID4 + 16.55 - VID4_SS)
    put(level(load("VID5.MOV", VID5_SS, VID5_ES - VID5_SS), -15.5), T_VID5)
    # quiet natural sound under the VO
    put(level(load("VID1.MOV", 0.0, 5.6), -32), T_VID1)
    put(level(load("VID2.MOV", 0.0, 7.4), -30), T_VID2)
    put(level(load("VID3.MOV", 1.9, 1.6, speed=0.6), -27), T_VID3 + 0.1)
    # paper sounds for the transitions
    for t0 in (T_OPEN1, T_OPEN2):
        put(np.repeat(sfx.paper_open(D_OPEN)[:, None], 2, 1), t0, 0.22)
    put(np.repeat(sfx.paper_close(D_CLOSE)[:, None], 2, 1), T_CLOSE1, 0.22)

    peak = np.abs(mix).max()
    if peak > 0.95:
        mix *= 0.95 / peak
    sfx.write_wav(path, mix[:int(T_END * sr)])


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "scenes1-3.mp4"))
    ap.add_argument("--stills", nargs="*", type=float, default=None)
    a = ap.parse_args()
    tl = Timeline()
    print(f"VID1 0 | VID2 {T_VID2:.2f} | black {T_BLACK:.2f} | VID3 {T_VID3:.2f} | VID4 {T_VID4:.2f} | "
          f"title {T_OPEN1:.2f} | VID5 {T_CLOSE1:.2f} | survey {T_OPEN2:.2f} | stats {T_STAT:.2f} | end {T_END:.2f}",
          flush=True)
    if a.stills is not None:
        d = os.path.join(ROOT, "out", "stills")
        os.makedirs(d, exist_ok=True)
        for t in sorted(a.stills):
            Image.fromarray(np.clip(tl.render(t), 0, 255).astype(np.uint8)).save(os.path.join(d, f"t{t:06.2f}.png"))
        print("stills done")
        return
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    wav = os.path.join(CACHE, "mix.wav")
    build_audio(wav)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                            "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                            "-shortest", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    nf = int(round(T_END * FPS))
    for i in range(nf):
        enc.stdin.write(np.clip(tl.render(i / FPS), 0, 255).astype(np.uint8).tobytes())
        if i % 90 == 0:
            print(f"  {i / FPS:6.2f}s / {T_END:.2f}s", flush=True)
    enc.stdin.close()
    enc.wait()
    print("wrote", a.out)


if __name__ == "__main__":
    sys.exit(main())
