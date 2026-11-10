#!/usr/bin/env python3
"""Render a 9:16 Warzone Season 1 clip in the reference style.

Layout (1080x1920, black canvas):
  - hook text, bold white, above the footage
  - official 16:9 footage centred (slight zoom so it fills more of the frame)
  - official Warzone logo (white) below the footage
  - "SEASON 1 OUT NOW" line under the logo

Audio is the ORIGINAL audio of the source clip only (no added music, per campaign rules).

Example:
  python3 make_clip.py --input footage/trailer.mp4 --start 00:00:12 --end 00:00:24 \
      --text "Call of Duty: Warzone gets two new maps Hajin and Zodiac in Season 1" \
      --out out/clip01.mp4
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(ROOT, "assets", "warzone-logo-white.png")  # official white logo
FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
W, H = 1080, 1920


def to_seconds(t):
    if t is None:
        return None
    parts = [float(p) for p in str(t).split(":")]
    s = 0.0
    for p in parts:
        s = s * 60 + p
    return s


def probe_size(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", path])
    st = json.loads(out)["streams"][0]
    return st["width"], st["height"]


def has_audio(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=index", "-of", "csv=p=0", path])
    return bool(out.strip())


def build_overlay(path, text, video_top, video_bottom, show_tagline):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Hook text, centred, bottom edge sits 40px above the footage.
    font = ImageFont.truetype(FONT, 54)
    lines = textwrap.wrap(text, width=30) if text else []
    line_h = 68
    y = video_top - 40 - line_h * len(lines)
    for line in lines:
        tw = d.textlength(line, font=font)
        d.text(((W - tw) / 2, y), line, font=font, fill="white")
        y += line_h

    # Official white Warzone logo, used as-is.
    logo = Image.open(LOGO).convert("RGBA")
    lw = 560
    lh = round(logo.height * lw / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    ly = video_bottom + 70
    img.alpha_composite(logo, ((W - lw) // 2, ly))

    if show_tagline:
        tf = ImageFont.truetype(FONT, 40)
        tag = "SEASON 1 OUT NOW"
        tw = d.textlength(tag, font=tf)
        d.text(((W - tw) / 2, ly + lh + 34), tag, font=tf, fill="white")

    img.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="official footage file")
    ap.add_argument("--start", help="start time (HH:MM:SS or seconds)")
    ap.add_argument("--end", help="end time (HH:MM:SS or seconds)")
    ap.add_argument("--text", default="", help="on-screen hook text")
    ap.add_argument("--out", required=True)
    ap.add_argument("--zoom", type=float, default=1.15,
                    help="zoom on the footage; 1.0 = full 16:9 frame, >1 crops the sides (default 1.15)")
    ap.add_argument("--no-tagline", action="store_true", help="hide the 'SEASON 1 OUT NOW' line")
    a = ap.parse_args()

    sw, sh = probe_size(a.input)
    # Footage box: full width, height from source aspect ratio, enlarged by zoom then side-cropped.
    box_h = round(W / (sw / sh) * a.zoom / 2) * 2
    scaled_w = round(W * a.zoom / 2) * 2
    video_top = (H - box_h) // 2 - 60  # sit a little above centre, like the reference
    video_bottom = video_top + box_h

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        ov = os.path.join(tmp, "overlay.png")
        build_overlay(ov, a.text, video_top, video_bottom, not a.no_tagline)

        ss, ee = to_seconds(a.start), to_seconds(a.end)
        dur = (ee - (ss or 0)) if ee is not None else None
        cmd = ["ffmpeg", "-y", "-v", "error", "-stats"]
        if ss is not None:
            cmd += ["-ss", str(ss)]
        if dur is not None:
            cmd += ["-t", str(dur)]
        cmd += ["-i", a.input, "-loop", "1", "-i", ov]

        fade = ""
        if dur:
            fade = f",fade=t=in:st=0:d=0.25,fade=t=out:st={max(dur - 0.3, 0):.2f}:d=0.3"
        vf = (
            f"[0:v]scale={scaled_w}:{box_h}:flags=lanczos,crop={W}:{box_h},setsar=1{fade}[clip];"
            f"color=c=black:s={W}x{H}:r=30[bg];"
            f"[bg][clip]overlay=0:{video_top}:shortest=1[base];"
            f"[base][1:v]overlay=0:0:shortest=1,format=yuv420p[v]"
        )
        cmd += ["-filter_complex", vf, "-map", "[v]"]
        if has_audio(a.input):
            cmd += ["-map", "0:a:0", "-c:a", "aac", "-b:a", "192k"]
            if dur:
                cmd += ["-af", f"afade=t=in:st=0:d=0.15,afade=t=out:st={max(dur - 0.3, 0):.2f}:d=0.3"]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-r", "30",
                "-movflags", "+faststart", "-shortest", a.out]
        subprocess.run(cmd, check=True)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    sys.exit(main())
