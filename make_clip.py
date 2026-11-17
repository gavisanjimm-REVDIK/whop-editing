#!/usr/bin/env python3
"""Render a 9:16 Warzone Season 1 clip in the reference style.

Layout (1080x1920, black canvas):
  - hook text, bold white, above the footage
  - official 16:9 footage centred (slight zoom so it fills more of the frame)
  - official logo below the footage (--logo; default Warzone white logo)
  - tagline under the logo (--tagline; default "SEASON 1 OUT NOW")

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

# Named editing styles (see STYLES.md). A style only sets defaults; any flag given on the command line wins.
STYLES = {
    # yellowhook: STRANGER THAN HEAVEN combat look (out/sth_02_combat.mp4).
    # Black 9:16 canvas, 3-line hook with the game name alone on its line in logo yellow,
    # footage cut on the trailer's own shot changes, audio crossfaded at jumps, STH logo + PRE-ORDER NOW.
    "yellowhook": {
        "logo": os.path.join(ROOT, "assets", "sth-logo.png"),
        "logo_width": 300,
        "tagline": "PRE-ORDER NOW",
        "highlight": "#DFBE31",
        "audio_xfade": 0.35,
    },
}


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


def build_overlay(path, text, video_top, video_bottom, tagline, logo_path, logo_w, highlight="white"):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Hook text, centred, bottom edge sits 40px above the footage.
    # Words wrapped in *asterisks* are drawn in the highlight colour; "|" forces a line break.
    font = ImageFont.truetype(FONT, 54)
    words, hl, on = [], [], False
    for tok in text.replace("|", " ").split():
        start, end = tok.startswith("*"), tok.endswith("*") and len(tok.strip("*")) > 0
        if start:
            on = True
        words.append(tok.strip("*"))
        hl.append(on)
        if end and tok.endswith("*"):
            on = False
    plain = " ".join(words)
    manual = "|" in text
    if manual:
        lines = [" ".join(t.strip("*") for t in part.split()) for part in text.split("|")]
    else:
        lines = textwrap.wrap(plain, width=30) if plain else []
    if len(lines) > 1 and not manual:  # rebalance so the last line isn't a lone word or two
        w = -(-len(plain) // len(lines))
        while len(textwrap.wrap(plain, width=w)) > len(lines):
            w += 1
        lines = textwrap.wrap(plain, width=w)
    line_h = 68
    y = video_top - 40 - line_h * len(lines)
    space = d.textlength(" ", font=font)
    i = 0
    for line in lines:
        n = len(line.split())
        seg = list(zip(words[i:i + n], hl[i:i + n]))
        i += n
        tw = d.textlength(line, font=font)
        x = (W - tw) / 2
        for word, h in seg:
            d.text((x, y), word, font=font, fill=highlight if h else "white")
            x += d.textlength(word, font=font) + space
        y += line_h

    # Official logo, used as-is (transparent padding trimmed so it sits evenly).
    logo = Image.open(logo_path).convert("RGBA")
    logo = logo.crop(logo.getchannel("A").getbbox())
    lw = logo_w
    lh = round(logo.height * lw / logo.width)
    logo = logo.resize((lw, lh), Image.LANCZOS)
    ly = video_bottom + 70
    img.alpha_composite(logo, ((W - lw) // 2, ly))

    if tagline:
        tf = ImageFont.truetype(FONT, 40)
        tag = tagline
        tw = d.textlength(tag, font=tf)
        d.text(((W - tw) / 2, ly + lh + 34), tag, font=tf, fill="white")

    img.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="official footage file")
    ap.add_argument("--start", help="start time (HH:MM:SS or seconds)")
    ap.add_argument("--end", help="end time (HH:MM:SS or seconds)")
    ap.add_argument("--seg", action="append", default=[],
                    help="START-END segment (seconds or M:SS); repeat to join several segments in order")
    ap.add_argument("--text", default="", help="on-screen hook text")
    ap.add_argument("--out", required=True)
    ap.add_argument("--zoom", type=float, default=1.15,
                    help="zoom on the footage; 1.0 = full 16:9 frame, >1 crops the sides (default 1.15)")
    ap.add_argument("--logo", default=LOGO, help="logo PNG shown under the footage (default: Warzone)")
    ap.add_argument("--logo-width", type=int, default=560, help="logo width in px (default 560)")
    ap.add_argument("--tagline", default="SEASON 1 OUT NOW", help="line under the logo")
    ap.add_argument("--highlight", default="#DFBE31",
                    help="colour for *starred* words in --text (default: STH logo yellow)")
    ap.add_argument("--audio-xfade", type=float, default=0.0,
                    help="seconds of audio crossfade at each segment join (video stays a hard cut)")
    ap.add_argument("--no-tagline", action="store_true", help="hide the tagline")
    ap.add_argument("--style", choices=sorted(STYLES), help="named editing style preset (see STYLES.md)")
    pre, _ = ap.parse_known_args()
    if pre.style:
        ap.set_defaults(**STYLES[pre.style])
    a = ap.parse_args()

    segs = [tuple(to_seconds(x) for x in sg.split("-")) for sg in a.seg]
    if not segs:
        if a.start is None or a.end is None:
            ap.error("give --start/--end or one or more --seg")
        segs = [(to_seconds(a.start), to_seconds(a.end))]
    dur = sum(e - s for s, e in segs)

    sw, sh = probe_size(a.input)
    # Footage box: full width, height from source aspect ratio, enlarged by zoom then side-cropped.
    box_h = round(W / (sw / sh) * a.zoom / 2) * 2
    scaled_w = round(W * a.zoom / 2) * 2
    video_top = (H - box_h) // 2 - 60  # sit a little above centre, like the reference
    video_bottom = video_top + box_h
    audio = has_audio(a.input)

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        ov = os.path.join(tmp, "overlay.png")
        build_overlay(ov, a.text, video_top, video_bottom,
                      None if a.no_tagline else a.tagline, a.logo, a.logo_width, a.highlight)

        parts, vl, al = [], "", []
        xf = a.audio_xfade if len(segs) > 1 else 0.0
        for i, (s, e) in enumerate(segs):
            parts.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS,fps=30[v{i}]")
            vl += f"[v{i}]"
            if audio:
                ae = e + (xf if i < len(segs) - 1 else 0)  # extra tail is eaten by the crossfade
                parts.append(f"[0:a]atrim={s}:{ae},asetpts=PTS-STARTPTS[a{i}]")
                al.append(f"[a{i}]")
        parts.append(f"{vl}concat=n={len(segs)}:v=1:a=0[cv]")
        if audio:
            if xf > 0:
                cur = al[0]
                for i in range(1, len(al)):
                    out = "[ca]" if i == len(al) - 1 else f"[ax{i}]"
                    parts.append(f"{cur}{al[i]}acrossfade=d={xf}:c1=tri:c2=tri{out}")
                    cur = out
            else:
                parts.append(f"{''.join(al)}concat=n={len(al)}:v=0:a=1[ca]")
        fo = max(dur - 0.3, 0)
        parts += [
            f"[cv]scale={scaled_w}:{box_h}:flags=lanczos,crop={W}:{box_h},setsar=1,"
            f"fade=t=in:st=0:d=0.25,fade=t=out:st={fo:.2f}:d=0.3[clip]",
            f"color=c=black:s={W}x{H}:r=30:d={dur:.3f}[bg]",
            f"[bg][clip]overlay=0:{video_top}:shortest=1[base]",
            "[base][1:v]overlay=0:0:shortest=1,format=yuv420p[v]",
        ]
        if audio:
            parts.append(f"[ca]afade=t=in:st=0:d=0.15,afade=t=out:st={fo:.2f}:d=0.3[a]")

        cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.input, "-loop", "1", "-i", ov,
               "-filter_complex", ";".join(parts), "-map", "[v]"]
        if audio:
            cmd += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-r", "30",
                "-movflags", "+faststart", "-write_tmcd", "0", "-map_metadata", "-1", "-t", f"{dur:.3f}", a.out]
        subprocess.run(cmd, check=True)
    print(f"wrote {a.out} ({dur:.1f}s)")


if __name__ == "__main__":
    sys.exit(main())
