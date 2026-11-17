#!/usr/bin/env python3
"""Render a 9:16 clip in the "edit1" style (see STYLES.md).

edit1 = white "post card" look:
  - white 1080x1920 canvas
  - header: round avatar + bold @handle, then the hook as a left-aligned black caption (Poppins)
  - footage in a tall portrait box, cropped per shot to follow the subject
    (--seg START-END@XC, XC = horizontal centre 0..1; @fit = whole 16:9 frame over a blurred fill)
  - the trailer's burned-in subtitles are cropped off and the official lines are re-set in the box (--sub)
  - official logo as a watermark in the top-right of the footage
  - small grey label centred under the footage
Audio is the ORIGINAL audio of the source only (no added music, no voiceover).

Example:
  python3 make_edit1.py --input footage/sth_trailer.mp4 --handle @mypage \
     --text "Can't wait to explore 1929 Kure in STRANGER THAN HEAVEN" \
     --seg 47-50.3@fit --seg 50.3-55.7@0.53 --sub "2.45-5.35|...I'll say it again! Pay up!" \
     --out out/clip.mp4
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import textwrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(ROOT, "assets", "fonts")
F_REG = os.path.join(FONTS, "Poppins-Regular.ttf")
F_SEMI = os.path.join(FONTS, "Poppins-SemiBold.ttf")
F_BOLD = os.path.join(FONTS, "Poppins-Bold.ttf")
W, H = 1080, 1920
BW, BH = 900, 1360          # footage box
BX = (W - BW) // 2
SUB_BAND = 0.852            # keep the top 85.2% of the source frame (drops the burned-in subtitle line)


def to_seconds(t):
    s = 0.0
    for p in str(t).split(":"):
        s = s * 60 + float(p)
    return s


def probe(path):
    out = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "json", path]))
    v = next(s for s in out["streams"] if s["codec_type"] == "video")
    return v["width"], v["height"], any(s["codec_type"] == "audio" for s in out["streams"])


def active_rows(path, t):
    """Top and bottom of the picture inside any letterbox bars (via ffmpeg cropdetect)."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-ss", f"{t:.2f}", "-t", "1", "-i", path,
                          "-vf", "cropdetect=limit=24:round=2", "-an", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    crops = [c for c in out.split() if c.startswith("crop=")]
    if not crops:
        return None
    w, h, x, y = (int(v) for v in crops[-1][5:].split(":"))
    return y, y + h


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def avatar(path_or_none, handle, size):
    if path_or_none:
        im = Image.open(path_or_none).convert("RGBA")
        s = min(im.size)
        im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2))
        im = im.resize((size, size), Image.LANCZOS)
    else:  # plain initial circle
        im = Image.new("RGBA", (size, size), (17, 17, 17, 255))
        d = ImageDraw.Draw(im)
        letter = (handle.lstrip("@")[:1] or "?").upper()
        f = ImageFont.truetype(F_BOLD, int(size * 0.5))
        d.text((size / 2, size / 2 + 2), letter, font=f, fill="white", anchor="mm")
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(im, (0, 0), mask)
    return out


def build_card(path, a):
    """Static layer: white canvas with header, caption and label. Returns the footage box top y."""
    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    d = ImageDraw.Draw(img)
    av = 96
    ay = 122
    img.alpha_composite(avatar(a.avatar, a.handle, av), (60, ay))
    d.text((180, ay + av / 2), a.handle, font=ImageFont.truetype(F_BOLD, 44), fill=(10, 10, 10), anchor="lm")

    cf = ImageFont.truetype(F_REG, 46)
    y = ay + av + 28
    for line in wrap(d, a.text, cf, W - 120):
        d.text((60, y), line, font=cf, fill=(10, 10, 10))
        y += 60
    box_top = y + 32

    if a.label:
        lf = ImageFont.truetype(F_BOLD, 34)
        d.text((W / 2, box_top + BH + (H - box_top - BH) / 2), a.label.upper(), font=lf,
               fill=(85, 85, 85), anchor="mm")
    img.save(path)
    return box_top


def build_logo(path, a):
    logo = Image.open(a.logo).convert("RGBA")
    logo = logo.crop(logo.getchannel("A").getbbox())
    lw = a.logo_width
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    pad = 24
    out = Image.new("RGBA", (logo.width + pad * 2, logo.height + pad * 2), (0, 0, 0, 0))
    shadow = Image.new("RGBA", out.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 170), (pad, pad), logo.getchannel("A"))
    out.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)))
    out.alpha_composite(logo, (pad, pad))
    out.save(path)
    return out.size


def build_sub(path, text):
    img = Image.new("RGBA", (BW, 220), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(F_SEMI, 38)
    lines = wrap(d, text, f, BW - 90)
    lh = 50
    y = 220 - 40 - lh * len(lines)
    for line in lines:
        d.text((BW / 2, y), line, font=f, fill="white", anchor="ma", stroke_width=4, stroke_fill=(0, 0, 0, 230))
        y += lh
    img.save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--seg", action="append", required=True,
                    help="START-END@XC (XC 0..1 crop centre, default 0.5) or START-END@fit; repeatable")
    ap.add_argument("--sub", action="append", default=[],
                    help="'START-END|text' in OUTPUT seconds; re-sets an official subtitle line")
    ap.add_argument("--text", required=True, help="hook caption under the handle")
    ap.add_argument("--handle", required=True, help="your page handle, e.g. @mypage")
    ap.add_argument("--avatar", help="profile picture (square-ish image); default = initial in a circle")
    ap.add_argument("--label", default="", help="small grey label under the footage")
    ap.add_argument("--logo", default=os.path.join(ROOT, "assets", "sth-logo.png"))
    ap.add_argument("--logo-width", type=int, default=150)
    ap.add_argument("--keep-subs", action="store_true", help="don't crop off the burned-in subtitle band")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    segs = []
    for sg in a.seg:
        rng, _, mode = sg.partition("@")
        s, e = (to_seconds(x) for x in rng.split("-"))
        segs.append((s, e, mode or "0.5"))
    dur = sum(e - s for s, e, _ in segs)
    sw, sh, audio = probe(a.input)
    band = 1.0 if a.keep_subs else SUB_BAND

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        card = os.path.join(tmp, "card.png")
        box_top = build_card(card, a)
        logo = os.path.join(tmp, "logo.png")
        lsz = build_logo(logo, a)
        subs = []
        for i, sp in enumerate(a.sub):
            rng, _, txt = sp.partition("|")
            s, e = (float(x) for x in rng.split("-"))
            p = os.path.join(tmp, f"sub{i}.png")
            build_sub(p, txt)
            subs.append((p, s, e))

        # One input per segment (fast seek, only that range is decoded) keeps memory low on 4K sources.
        inputs = ["-loop", "1", "-i", card, "-loop", "1", "-i", logo]
        for p, _, _ in subs:
            inputs += ["-loop", "1", "-i", p]
        n_in = 2 + len(subs)          # card, logo, subtitle images
        seg_in = n_in
        for s, e, _ in segs:
            inputs += ["-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", a.input]
            n_in += 1

        f, vl = [], ""
        act = active_rows(a.input, (segs[0][0] + segs[0][1]) / 2) or (0, sh)
        top, bot = act[0], min(act[1], round(sh * band))
        ch = (bot - top) // 2 * 2
        cw = round(ch * BW / BH / 2) * 2
        for i, (s, e, mode) in enumerate(segs):
            base = f"[{seg_in + i}:v]setpts=PTS-STARTPTS,fps=30,trim=duration={e - s:.3f}"
            if mode == "fit":
                ah = (act[1] - act[0]) // 2 * 2
                fh = round(BW * ah / sw / 2) * 2
                f.append(f"{base},split[fa{i}][fb{i}]")
                f.append(f"[fa{i}]crop={cw}:{ch}:{(sw - cw) // 2}:{top},scale={BW // 4}:{BH // 4},"
                         f"boxblur=12:2,scale={BW}:{BH},eq=brightness=-0.12[bg{i}]")
                f.append(f"[fb{i}]crop={sw}:{ah}:0:{act[0]},scale={BW}:{fh}:flags=lanczos[fg{i}]")
                f.append(f"[bg{i}][fg{i}]overlay=0:{(BH - fh) // 2},setsar=1[v{i}]")
            else:
                xc = float(mode)
                x = int(min(max(xc * sw - cw / 2, 0), sw - cw))
                f.append(f"{base},crop={cw}:{ch}:{x}:{top},scale={BW}:{BH}:flags=lanczos,setsar=1[v{i}]")
            vl += f"[v{i}]"
        f.append(f"{vl}concat=n={len(segs)}:v=1:a=0[foot]")
        f.append(f"[0:v][foot]overlay={BX}:{box_top}:shortest=1[c0]")
        f.append(f"[c0][1:v]overlay={BX + BW - lsz[0] + 2}:{box_top - 2}:shortest=1[c1]")
        last = "c1"
        for i, (_, s, e) in enumerate(subs):
            f.append(f"[{last}][{2 + i}:v]overlay={BX}:{box_top + BH - 220}:shortest=1:"
                     f"enable='between(t,{s},{e})'[s{i}]")
            last = f"s{i}"
        f.append(f"[{last}]format=yuv420p[v]")

        if audio:
            # merge touching segments so the audio stays continuous; crossfade real jumps
            runs = []
            for s, e, _ in segs:
                if runs and abs(runs[-1][1] - s) < 1e-3:
                    runs[-1][1] = e
                else:
                    runs.append([s, e])
            xf = 0.35
            al = []
            for i, (s, e) in enumerate(runs):
                ae = e + (xf if i < len(runs) - 1 else 0)
                inputs += ["-ss", f"{s:.3f}", "-t", f"{ae - s:.3f}", "-vn", "-i", a.input]
                f.append(f"[{n_in}:a]asetpts=PTS-STARTPTS[a{i}]")
                n_in += 1
                al.append(f"[a{i}]")
            cur = al[0]
            for i in range(1, len(al)):
                f.append(f"{cur}{al[i]}acrossfade=d={xf}:c1=tri:c2=tri[ax{i}]")
                cur = f"[ax{i}]"
            fo = max(dur - 0.3, 0)
            f.append(f"{cur}afade=t=in:st=0:d=0.15,afade=t=out:st={fo:.2f}:d=0.3[a]")

        cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(f), "-map", "[v]"]
        if audio:
            cmd += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "17", "-r", "30", "-movflags", "+faststart",
                "-write_tmcd", "0", "-map_metadata", "-1", "-t", f"{dur:.3f}", a.out]
        subprocess.run(cmd, check=True)
    print(f"wrote {a.out} ({dur:.1f}s)")


if __name__ == "__main__":
    sys.exit(main())
