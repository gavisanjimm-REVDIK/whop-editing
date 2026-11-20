#!/usr/bin/env python3
"""Render a 9:16 STRANGER THAN HEAVEN clip in the reference style.

Layout (1080x1920, black canvas), measured from the reference video:
  - official STH logo (white with the yellow half-moon) in the top-left corner
  - two-line hook text in a condensed caps font, coloured like the reference:
      plain words yellow, the game title green, *starred* words red, punctuation white
  - official trailer footage (its built-in letterbox bars removed) cropped to 4:3 across the full width
  - empty black space below the footage

Audio is the ORIGINAL trailer audio only (no added music, no AI voice), per the brief.

Hook text markup:
  "|"          forces a line break
  "*word*"     makes the word(s) red
  STRANGER THAN HEAVEN (and STRANGER THAN HEAVEN'S) is always green

Example:
  python3 sth/make_clip.py --input footage/sth_trailer.mp4 --seg 32.5-46.9 \
      --text "CAN'T WAIT TO BE A BADASS *YAKUZA* IN|STRANGER THAN HEAVEN." --out out/sth/02.mp4
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(HERE, "assets", "sth-logo.png")  # official logo from the brief, trimmed
FONT = os.path.join(HERE, "assets", "BebasNeue-Regular.ttf")
W, H = 1080, 1920

YELLOW = (250, 214, 10)
GREEN = (22, 190, 22)
RED = (240, 22, 26)
WHITE = (255, 255, 255)

LOGO_X, LOGO_Y, LOGO_W = 34, 30, 326   # top-left logo
VIDEO_TOP = 555                         # footage box top (reference: 370/1280)
BOX_H = 810                             # footage box 1080x810 (4:3), like the reference
BAR = 120 / 2160                        # the trailer is 3840x2160 with 120px black bars top and bottom
FONT_SIZE, LINE_H, TEXT_GAP, TRACK = 62, 68, 50, 1.5
TITLE = re.compile(r"STRANGER THAN HEAVEN(?:['’]S)?")


def to_seconds(t):
    s = 0.0
    for p in str(t).split(":"):
        s = s * 60 + float(p)
    return s


def probe(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
        "-of", "json", path])
    streams = json.loads(out)["streams"]
    v = next(s for s in streams if s["codec_type"] == "video")
    return v["width"], v["height"], any(s["codec_type"] == "audio" for s in streams)


def runs_for_line(line):
    """Split a line into (text, colour) runs."""
    runs = []
    for part in re.split(r"(\*[^*]+\*)", line):
        if not part:
            continue
        if part.startswith("*"):
            runs.append((part[1:-1], RED))
            continue
        pos = 0
        for m in TITLE.finditer(part):
            runs.append((part[pos:m.start()], YELLOW))
            runs.append((m.group(0), GREEN))
            pos = m.end()
        runs.append((part[pos:], YELLOW))
    # trailing punctuation goes white, like the reference's full stop
    out = []
    for text, col in runs:
        m = re.match(r"^(.*?)([.!?]+)$", text)
        if m and text:
            out += [(m.group(1), col), (m.group(2), WHITE)]
        else:
            out.append((text, col))
    return [(t, c) for t, c in out if t]


def build_overlay(path, text, video_top):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    logo = Image.open(LOGO).convert("RGBA")
    lh = round(logo.height * LOGO_W / logo.width)
    img.alpha_composite(logo.resize((LOGO_W, lh), Image.LANCZOS), (LOGO_X, LOGO_Y))

    font = ImageFont.truetype(FONT, FONT_SIZE)
    lines = [ln.strip() for ln in text.upper().replace("'", "’").split("|") if ln.strip()]
    asc, _ = font.getmetrics()
    y = video_top - TEXT_GAP - LINE_H * len(lines) + (LINE_H - asc)
    for line in lines:
        runs = runs_for_line(line)
        total = sum(d.textlength(ch, font=font) + TRACK for t, _ in runs for ch in t) - TRACK
        x = (W - total) / 2
        for t, col in runs:
            for ch in t:  # slight letter spacing, like the reference
                d.text((x, y), ch, font=font, fill=col)
                x += d.textlength(ch, font=font) + TRACK
        y += LINE_H
    img.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="official trailer file")
    ap.add_argument("--seg", action="append", required=True,
                    help="START-END in seconds or M:SS; repeat to join several segments in order")
    ap.add_argument("--text", default="", help="hook text (see markup above)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--bar", type=float, default=BAR,
                    help="letterbox bar height as a fraction of the source height (default 120/2160)")
    a = ap.parse_args()

    segs = [tuple(to_seconds(x) for x in sg.split("-")) for sg in a.seg]
    dur = sum(e - s for s, e in segs)
    sw, sh, audio = probe(a.input)
    bar = round(sh * a.bar / 2) * 2
    active_h = sh - 2 * bar
    scaled_w = round(BOX_H * sw / active_h / 2) * 2

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        ov = os.path.join(tmp, "overlay.png")
        build_overlay(ov, a.text, VIDEO_TOP)

        parts, labels = [], ""
        for i, (s, e) in enumerate(segs):
            parts.append(f"[{i}:v]setpts=PTS-STARTPTS,fps=30[v{i}]")
            labels += f"[v{i}]"
            if audio:  # tiny audio fade at each join so cuts don't click
                ad = e - s
                parts.append(f"[{i}:a]asetpts=PTS-STARTPTS,"
                             f"afade=t=in:st=0:d=0.06,afade=t=out:st={ad - 0.06:.3f}:d=0.06[a{i}]")
                labels += f"[a{i}]"
        parts.append(f"{labels}concat=n={len(segs)}:v=1:a={1 if audio else 0}[cv]" + ("[ca]" if audio else ""))
        fo = max(dur - 0.35, 0)
        parts += [
            f"[cv]crop={sw}:{active_h}:0:{bar},scale={scaled_w}:{BOX_H}:flags=lanczos,crop={W}:{BOX_H},setsar=1,"
            f"fade=t=in:st=0:d=0.2,fade=t=out:st={fo:.2f}:d=0.35[clip]",
            f"color=c=black:s={W}x{H}:r=30:d={dur:.3f}[bg]",
            f"[bg][clip]overlay=0:{VIDEO_TOP}:shortest=1[base]",
            f"[base][{len(segs)}:v]overlay=0:0:shortest=1,format=yuv420p[v]",
        ]
        if audio:
            parts.append(f"[ca]afade=t=in:st=0:d=0.15,afade=t=out:st={fo:.2f}:d=0.35[a]")

        cmd = ["ffmpeg", "-y", "-v", "error"]
        for s, e in segs:  # seek each segment directly (fast and frame-accurate when re-encoding)
            cmd += ["-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", a.input]
        cmd += ["-loop", "1", "-i", ov,
               "-filter_complex", ";".join(parts), "-map", "[v]"]
        if audio:
            cmd += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-r", "30",
                "-movflags", "+faststart", "-t", f"{dur:.3f}", a.out]
        subprocess.run(cmd, check=True)
    print(f"wrote {a.out} ({dur:.1f}s)")


if __name__ == "__main__":
    sys.exit(main())
