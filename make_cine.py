#!/usr/bin/env python3
"""Render a 9:16 Short in the clean "cinematic letterbox" style (R3born campaign, second look).

Style (modelled on the YouTube Short the brief owner shared, not copied):
  - black 1080x1920 canvas; wide 16:9 footage band in the middle, barely cropped
  - three-line hook above it in a condensed bold face (Oswald): first-person viewer reaction,
    with the show name in CAPS on the middle line
  - the official R3BORN logo (lifted from the episode's own title card) under the footage
  - big, calm phrase subtitles (2-3 words) in the black band under the footage (never over show graphics)
  - slow push-in across each shot, mild cinematic grade, hard cuts, no fades (clean loop)
  - swears censored on screen and bleeped (advertiser-friendly)

Example:
  python3 make_cine.py --input footage/ep2.mp4 --transcript footage/ep2_transcript.json \
      --seg 547.0-549.6@1.25:0.5:0.35 --seg 549.85-561.1 \
      --hook "I wouldn't last 5 seconds in|*R3BORN'S AERIAL SILKS*|challenge" --out out/r3born/06.mp4

--seg START-END[@ZOOM[:X[:Y]]] works like make_short.py. --say "A-B=text" overrides what the subtitles
say for words between source times A and B (for lines Whisper mishears).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

from make_short import SWEARS, ass_time, clean_word, probe, secs

ROOT = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
BOX_H = 640                     # footage band: 1080x640 (16:9 with a hair of side crop)
VIDEO_TOP = 600
FONT_DIR = os.path.join(ROOT, "assets", "fonts")
HOOK_FONT = os.path.join(FONT_DIR, "Oswald-700.ttf")
LOGO = os.path.join(ROOT, "assets", "r3born-logo.png")


def parse_seg(text):
    rng, _, opt = text.partition("@")
    a, b = rng.split("-")
    z, x, y = (opt.split(":") + ["", "", ""])[:3] if opt else ("", "", "")
    return secs(a), secs(b), float(z or 1.0), float(x or 0.5), float(y or 0.5)


def build_overlay(path, hook):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(HOOK_FONT, 68)
    lines = [ln.strip() for ln in hook.split("|")] if hook else []
    lh = 82
    y = VIDEO_TOP - 44 - lh * len(lines)
    for ln in lines:
        txt = re.sub(r"\*([^*]+)\*", lambda m: m.group(1).upper(), ln)
        tw = d.textlength(txt, font=font)
        d.text(((W - tw) / 2, y), txt, font=font, fill="white")
        y += lh
    logo = Image.open(LOGO).convert("RGBA")
    lw = 560
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, ((W - lw) // 2, VIDEO_TOP + BOX_H + 150))
    img.save(path)


def phrases(words, dur, max_words=3, max_len=0.95):
    """Group words into short phrases; break on punctuation, gaps, length."""
    out, cur = [], []
    for i, (a, b, t) in enumerate(words):
        if cur and (len(cur) >= max_words or a - cur[-1][1] > 0.35 or b - cur[0][0] > max_len):
            out.append(cur)
            cur = []
        cur.append((a, b, t))
        if re.search(r"[.?!,]$", t.strip()):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    ev = []
    for i, p in enumerate(out):
        start = p[0][0]
        nxt = out[i + 1][0][0] if i + 1 < len(out) else dur
        end = min(max(p[-1][1] + 0.25, start + 0.45), nxt, dur)
        txt, swear = [], False
        for _, _, t in p:
            c, s = clean_word(t.strip())
            swear |= s
            txt.append(c)
        ev.append((start, end, " ".join(x for x in txt if x)))
    return ev


def build_ass(path, events, cap_y):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: C,Oswald,80,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,1,0,1,3,0,5,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [f"Dialogue: 0,{ass_time(a)},{ass_time(b)},C,,0,0,0,,{{\\an5\\pos({W // 2},{cap_y})\\fad(60,0)}}{t}"
             for a, b, t in events if t]
    with open(path, "w") as f:
        f.write(head + "\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--transcript", required=True, help="full-episode transcript JSON (see make_short.py)")
    ap.add_argument("--seg", action="append", required=True)
    ap.add_argument("--hook", default="", help="lines split by |, *text* = CAPS")
    ap.add_argument("--say", action="append", default=[], help='"A-B=text": replace subtitle words in source A..B')
    ap.add_argument("--push", type=float, default=0.05, help="slow push-in amount per shot (default 0.05)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    segs = [parse_seg(s) for s in a.seg]
    dur = sum(e - s for s, e, *_ in segs)
    sw, sh, has_a = probe(a.input)
    if not has_a:
        sys.exit("input has no audio")

    # transcript words in source time, with --say overrides, then mapped to the output timeline
    src = [list(w) for sg in json.load(open(a.transcript)) for w in sg["w"]]
    for rule in a.say:
        rng, _, text = rule.partition("=")
        lo, hi = (secs(x) for x in rng.split("-"))
        new = text.split()
        src = [w for w in src if not (lo <= w[0] <= hi)]
        step = (hi - lo) / max(len(new), 1)
        src += [[lo + i * step, lo + (i + 1) * step - 0.02, t] for i, t in enumerate(new)]
    src.sort(key=lambda w: w[0])
    words, off = [], 0.0
    for s, e, *_ in segs:
        for ws, we, wt in src:
            if s - 0.05 <= ws < e - 0.08:
                words.append([max(ws - s, 0) + off, min(we, e) - s + off, wt])
        off += e - s

    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        ass = os.path.join(tmp, "c.ass")
        build_ass(ass, phrases(words, dur), VIDEO_TOP + BOX_H + 66)  # subtitles in the band under the footage
        ov = os.path.join(tmp, "ov.png")
        build_overlay(ov, a.hook)

        parts, labels = [], ""
        for i, (s, e, z, fx, fy) in enumerate(segs):
            d = e - s
            # cover the band, then a slow push-in (zoom grows linearly over the shot)
            base_h = BOX_H * z
            base_w = sw * base_h / sh
            if base_w < W:
                base_w = W * z
                base_h = sh * base_w / sw
            p = a.push
            bw = round(base_w / 2) * 2
            parts.append(
                f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS,fps=30,"
                # slow push-in: the frame is scaled up linearly over the shot, then cropped to the band
                f"scale=w='2*trunc({bw}*(1+{p}*t/{d:.3f})/2)':h=-2:eval=frame:flags=lanczos,"
                f"crop={W}:{BOX_H}:'(iw-{W})*{fx}':'(ih-{BOX_H})*{fy}',setsar=1[v{i}]")
            parts.append(f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS[a{i}]")
            labels += f"[v{i}][a{i}]"
        parts.append(f"{labels}concat=n={len(segs)}:v=1:a=1[cv][ca]")
        parts.append("[cv]eq=contrast=1.10:saturation=1.08:gamma=0.97,"
                     "colorbalance=bs=0.04:bm=0.02:rh=0.02,unsharp=5:5:0.4[clip]")
        parts.append(f"color=c=black:s={W}x{H}:r=30:d={dur:.3f}[bg]")
        parts.append(f"[bg][clip]overlay=0:{VIDEO_TOP}:shortest=1[b1]")
        parts.append("[b1][1:v]overlay=0:0:shortest=1[b2]")
        assp = ass.replace("\\", "/").replace(":", "\\:")
        parts.append(f"[b2]ass='{assp}':fontsdir='{FONT_DIR}',format=yuv420p[v]")

        bad = [(w[0], w[1]) for w in words if clean_word(w[2])[1]]
        if bad:
            en = "+".join(f"between(t,{x - 0.03:.3f},{y + 0.03:.3f})" for x, y in bad)
            parts.append(f"[ca]volume=0:enable='{en}',aresample=48000[mu]")
            parts.append(f"sine=f=1000:sample_rate=48000:d={dur:.3f},volume=0.18,volume=0:enable='not({en})'[bp]")
            parts.append("[mu][bp]amix=inputs=2:normalize=0:duration=first[a]")
        else:
            parts.append("[ca]anull[a]")
        parts[-1] += ";[a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[ao]"

        cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.input, "-loop", "1", "-i", ov,
               "-filter_complex", ";".join(parts), "-map", "[v]", "-map", "[ao]",
               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high", "-r", "30",
               "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{dur:.3f}", a.out]
        subprocess.run(cmd, check=True)
    print(f"wrote {a.out} ({dur:.1f}s, {len(segs)} shots, {len(bad)} bleeps)")


if __name__ == "__main__":
    sys.exit(main())
