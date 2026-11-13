#!/usr/bin/env python3
"""LTK "Creator Earnings" clip: a 9:16 story edit built only from the official LTK content folder.

Story: keynote stat (464 creators earned $1M+, a new millionaire every week)
    -> a creator explains what she did after hearing a stat like that ("I wrote lock-in")
    -> payoff: her LTK income tripled what she made at the bank.

Style: jump cuts on the pauses, slow push-ins with punch-ins on key lines, bold pop-in text
with yellow emphasis words, official LTK logo watermark the whole time.
Audio: original audio only, loudness-normalised (no music added).

    python3 ltk_edit.py --out out/ltk_lock_in.mp4
"""
import argparse
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(ROOT, "footage", "ltk")
LOGO = os.path.join(ROOT, "assets", "ltk-logo-white.png")  # official logo from the LTK logo folder
FONT = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
W, H, FPS = 1080, 1920, 30
YELLOW = (255, 214, 10, 255)

KEY = os.path.join(F, "Opening_Keynote_New_millionaire_every_week_1_.mp4")
POD3 = os.path.join(F, "#3_See_Millionaires_Everywhere__You_Can_Be_One_Too_v2.mp4")
POD4 = os.path.join(F, "#4_Left_BANKING_for_Content_Creation__3X_Income_HUGE_Growth_.mp4")

# (source, start, end, zoom at start, zoom at end). Cut points sit in the speaker's pauses.
SEGMENTS = [
    (KEY, 0.00, 7.55, 1.00, 1.06),    # "We now have 464 creators who have earned more than a million dollars on the LTK platform."
    (KEY, 9.30, 11.20, 1.12, 1.14),   # "And over the last 18 months,"
    (KEY, 11.95, 16.70, 1.02, 1.08),  # "a new person has become an LTK millionaire every single week."
    (POD3, 0.00, 3.10, 1.00, 1.04),   # "You mentioned how many people became millionaires in 2025,"
    (POD3, 7.45, 10.30, 1.06, 1.10),  # "And I thought like, okay, and I wrote that down."
    (POD3, 10.35, 12.25, 1.22, 1.25), # "I wrote lock-in and I closed the book."  (punch-in)
    (POD3, 12.65, 14.35, 1.02, 1.05), # "That was all I needed to hear."
    (POD4, 4.82, 15.05, 1.00, 1.10),  # "...my income from LTK alone tripled what I made at the bank. In a year, I would make that in a month."
]


def seg_start(i):
    return sum(e - s for _, s, e, _, _ in SEGMENTS[:i])


def src_time(i, t):
    """Output time of source time t inside segment i."""
    return seg_start(i) + (t - SEGMENTS[i][1])


TOTAL = seg_start(len(SEGMENTS))

# On-screen text: (t_in, t_out, lines, emphasis words, centre y, font size)
# Every line is said in the footage itself (no made-up numbers).
TEXTS = [
    (0.0, seg_start(1), ["464 creators have", "become millionaires", "on LTK"], {"464", "millionaires"}, 490, 72),
    (seg_start(1), seg_start(3), ["A new LTK millionaire", "every single week"], {"every", "single", "week"}, 440, 72),
    (seg_start(1), seg_start(3), ["(over the last 18 months)"], set(), 565, 40),
    (seg_start(3), seg_start(5), ["One creator heard a", "stat like this.", "Here's what she did:"], {"what", "she", "did:"}, 1420, 58),
    (src_time(5, 10.55), seg_start(7), ["LOCK IN."], {"LOCK", "IN."}, 1420, 120),
    (seg_start(7), src_time(7, 9.24), ["She used to", "work at a bank"], {"bank"}, 1420, 62),
    (src_time(7, 9.24), src_time(7, 12.0), ["LTK income =", "3X her bank pay"], {"3X"}, 1420, 72),
    (src_time(7, 12.0), TOTAL, ["A year of bank pay", "in ONE month"], {"ONE", "month"}, 1420, 72),
]


def render_block(lines, emph, size):
    font = ImageFont.truetype(FONT, size)
    stroke = max(4, size // 9)
    space = font.getlength(" ")
    lh = int(size * 1.18)
    widths = [sum(font.getlength(w) for w in ln.split()) + space * (len(ln.split()) - 1) for ln in lines]
    bw, bh = int(max(widths)) + stroke * 4 + 40, lh * len(lines) + stroke * 4 + 40
    img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for li, ln in enumerate(lines):
        x = (bw - widths[li]) / 2
        y = 20 + stroke * 2 + li * lh
        for w in ln.split():
            fill = YELLOW if w in emph else (255, 255, 255, 255)
            d.text((x, y), w, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
            x += font.getlength(w) + space
    # soft drop shadow so text reads on bright stage footage too
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sh.putalpha(img.getchannel("A").point(lambda a: a * 0.55))
    sh = sh.filter(ImageFilter.GaussianBlur(8))
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, 6))
    out.alpha_composite(img)
    return out


def pop_scale(dt):
    if dt < 0.10:
        return 0.65 + (1.08 - 0.65) * dt / 0.10
    if dt < 0.18:
        return 1.08 - 0.08 * (dt - 0.10) / 0.08
    return 1.0


def logo_layer():
    logo = Image.open(LOGO).convert("RGBA")
    lw = 230
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    sh = Image.new("RGBA", logo.size, (0, 0, 0, 0))
    sh.putalpha(logo.getchannel("A").point(lambda a: a * 0.6))
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x, y = W - lw - 48, 230
    base.alpha_composite(sh, (x, y + 4))
    base.alpha_composite(logo, (x, y))
    return base


def base_video(tmp):
    srcs = []
    for s, *_ in SEGMENTS:
        if s not in srcs:
            srcs.append(s)
    parts, labels = [], ""
    for i, (src, s, e, z0, z1) in enumerate(SEGMENTS):
        k = srcs.index(src)
        n = max(1, round((e - s) * FPS))
        parts.append(
            f"[{k}:v]trim={s}:{e},setpts=PTS-STARTPTS,fps={FPS},scale={W*2}:{H*2}:flags=lanczos,"
            f"zoompan=z='{z0}+({z1}-{z0})*on/{n}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={W}x{H}:fps={FPS},"
            f"setsar=1,format=yuv420p[v{i}]")
        parts.append(f"[{k}:a]atrim={s}:{e},asetpts=PTS-STARTPTS,"
                     f"afade=t=in:d=0.03,afade=t=out:st={e - s - 0.04:.3f}:d=0.04[a{i}]")
        labels += f"[v{i}][a{i}]"
    parts.append(f"{labels}concat=n={len(SEGMENTS)}:v=1:a=1[cv][ca]")
    parts.append("[ca]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
    out = os.path.join(tmp, "base.mp4")
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for s in srcs:
        cmd += ["-i", s]
    cmd += ["-filter_complex", ";".join(parts), "-map", "[cv]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-c:a", "aac", "-b:a", "256k", out]
    subprocess.run(cmd, check=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(ROOT, "out", "ltk_lock_in.mp4"))
    a = ap.parse_args()
    tmp = os.path.join(ROOT, "out", ".tmp")
    os.makedirs(tmp, exist_ok=True)

    base = base_video(tmp)
    logo = logo_layer()
    blocks = [(t0, t1, render_block(lines, emph, size), y) for t0, t1, lines, emph, y, size in TEXTS]

    nframes = round(TOTAL * FPS)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-i", base,
         "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]",
         "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "slow", "-crf", "17",
         "-profile:v", "high", "-c:a", "copy", "-movflags", "+faststart", "-t", f"{TOTAL:.3f}", a.out],
        stdin=subprocess.PIPE)
    last_key, last_bytes = None, None
    for f in range(nframes):
        t = f / FPS
        active = []
        for bi, (t0, t1, img, y) in enumerate(blocks):
            if t0 <= t < t1:
                sc = pop_scale(t - t0)
                active.append((bi, round(sc, 3)))
        key = tuple(active)
        if key != last_key:
            frame = logo.copy()
            for bi, sc in active:
                _, _, img, y = blocks[bi]
                im = img if sc == 1.0 else img.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))), Image.LANCZOS)
                frame.alpha_composite(im, ((W - im.width) // 2, int(y - im.height / 2)))
            last_key, last_bytes = key, frame.tobytes()
        ff.stdin.write(last_bytes)
    ff.stdin.close()
    if ff.wait():
        sys.exit("ffmpeg overlay failed")
    print(f"wrote {a.out} ({TOTAL:.2f}s)")


if __name__ == "__main__":
    main()
