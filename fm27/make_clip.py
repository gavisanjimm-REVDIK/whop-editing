#!/usr/bin/env python3
"""Render a 9:16 Football Manager 27 clip from a vertical creator video.

Layout (1080x1920, black canvas), same house style as the Warzone clips:
  - hook text, bold white, above the footage (auto-fits to 2 lines)
  - the creator's vertical video, scaled into the centre with rounded corners
  - official white FOOTBALL MANAGER 27 wordmark below the footage

Audio is the creator video's ORIGINAL audio only (no music, no AI voice, per the brief).

Example:
  python3 fm27/make_clip.py --input footage/fm27/nick_ad1.mp4 --seg 0-18.75 \
      --text "Football Manager 27 has a new mode called Shuffle Draft" --out out/fm27/05.mp4
"""
import argparse
import os
import subprocess
import sys
import tempfile
import textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO = os.path.join(ROOT, "assets", "fm27-wordmark-white.png")  # official FM27 wordmark (light)
FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
W, H = 1080, 1920
FH = 1440                     # footage height on the canvas
FW = round(FH * 9 / 16 / 2) * 2  # 810
FTOP = 270                    # footage top edge
RADIUS = 28
LOGO_W = 430
TEXT_MAX_W = 980


def to_seconds(t):
    s = 0.0
    for p in str(t).split(":"):
        s = s * 60 + float(p)
    return s


def has_audio(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=index", "-of", "csv=p=0", path])
    return bool(out.strip())


def fit_lines(d, text):
    """Largest font size (56..40) at which the hook fits in 2 balanced lines."""
    for size in range(56, 39, -2):
        font = ImageFont.truetype(FONT, size)
        for width in range(18, 60):
            lines = textwrap.wrap(text, width=width)
            if len(lines) <= 2 and all(d.textlength(l, font=font) <= TEXT_MAX_W for l in lines):
                return font, lines
    return font, textwrap.wrap(text, width=40)


def build_overlay(path, text):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if text:
        font, lines = fit_lines(d, text)
        line_h = round(font.size * 1.22)
        y = FTOP - 34 - line_h * len(lines)
        for line in lines:
            tw = d.textlength(line, font=font)
            d.text(((W - tw) / 2, y), line, font=font, fill="white")
            y += line_h

    logo = Image.open(LOGO).convert("RGBA")
    lh = round(logo.height * LOGO_W / logo.width)
    logo = logo.resize((LOGO_W, lh), Image.LANCZOS)
    fbottom = FTOP + FH
    ly = fbottom + (H - fbottom - lh) // 2 - 6
    img.alpha_composite(logo, ((W - LOGO_W) // 2, ly))
    img.save(path)


def build_mask(path):
    m = Image.new("L", (FW, FH), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, FW - 1, FH - 1), RADIUS, fill=255)
    m.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="creator video from the content folder")
    ap.add_argument("--seg", action="append", required=True,
                    help="START-END (seconds or M:SS); repeat to join segments in order")
    ap.add_argument("--text", default="", help="on-screen hook text (English)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    segs = [tuple(to_seconds(x) for x in sg.split("-")) for sg in a.seg]
    dur = sum(e - s for s, e in segs)
    audio = has_audio(a.input)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        ov, mask = os.path.join(tmp, "overlay.png"), os.path.join(tmp, "mask.png")
        build_overlay(ov, a.text)
        build_mask(mask)

        parts, labels = [], ""
        for i, (s, e) in enumerate(segs):
            parts.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS,fps=30[v{i}]")
            labels += f"[v{i}]"
            if audio:
                parts.append(f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS[a{i}]")
                labels += f"[a{i}]"
        parts.append(f"{labels}concat=n={len(segs)}:v=1:a={1 if audio else 0}[cv]" + ("[ca]" if audio else ""))
        fo = max(dur - 0.3, 0)
        parts += [
            # fill the 9:16 box (centre-crop if the source isn't exactly 9:16)
            f"[cv]scale={FW}:{FH}:force_original_aspect_ratio=increase:flags=lanczos,crop={FW}:{FH},setsar=1,"
            f"fade=t=in:st=0:d=0.25,fade=t=out:st={fo:.2f}:d=0.3,format=yuva420p[cf]",
            "[2:v]format=gray[m]",
            "[cf][m]alphamerge[clip]",
            f"color=c=black:s={W}x{H}:r=30:d={dur:.3f}[bg]",
            f"[bg][clip]overlay={(W - FW) // 2}:{FTOP}:shortest=1[base]",
            "[base][1:v]overlay=0:0:shortest=1,format=yuv420p[v]",
        ]
        if audio:
            parts.append(f"[ca]afade=t=in:st=0:d=0.1,afade=t=out:st={fo:.2f}:d=0.3[a]")

        cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.input,
               "-loop", "1", "-i", ov, "-loop", "1", "-i", mask,
               "-filter_complex", ";".join(parts), "-map", "[v]"]
        if audio:
            cmd += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-r", "30",
                "-movflags", "+faststart", "-t", f"{dur:.3f}", a.out]
        subprocess.run(cmd, check=True)
    print(f"wrote {a.out} ({dur:.1f}s)")


if __name__ == "__main__":
    sys.exit(main())
