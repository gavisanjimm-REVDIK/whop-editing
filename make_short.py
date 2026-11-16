#!/usr/bin/env python3
"""Render a fast-paced 9:16 Short in the "theme page" style (HardScope R3born campaign).

Style (modelled on ref/reference.mp4, not copied):
  - black 1080x1920 canvas, 2-line hook on top (white, one *keyword* in red, optional emoji)
  - footage punched in to a near-square box, saturated/contrasty grade
  - one-word-at-a-time captions that pop in, emphasis words in yellow / cyan / green
  - alternating zoom levels per cut (punch-ins) and a quick red flash on every cut
  - swears censored on screen (F***) and bleeped in audio (advertiser-friendly)
  - no fade in (hook lands on frame 1) and no fade out (clean loop back to the start)
All text stays out of the bottom 300 px and the right-hand button column.

Example:
  python3 make_short.py --input footage/ep2.mp4 \
      --seg 812.4-815.0 --seg 640.2-652.8@1.15:0.4 \
      --hook "N3on got *EXPOSED*|mid workout 💀" --out out/01.mp4

Segment syntax: START-END[@ZOOM[:X]]  (seconds or M:SS / H:MM:SS)
  ZOOM  extra punch-in for that cut (default alternates 1.0 / 1.12)
  X     horizontal focus 0..1 when cropping 16:9 into the box (default 0.5 = centre)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BOX_H = 1000                 # footage box height (box is full width)
VIDEO_TOP = 400              # footage box top
CAP_Y = VIDEO_TOP + BOX_H - 190  # caption centre line (inside lower part of footage)
FONT_DIR = "/usr/share/fonts/opentype/inter"
FONT_BLACK = os.path.join(FONT_DIR, "Inter-Black.otf")
FONT_XB = os.path.join(FONT_DIR, "Inter-ExtraBold.otf")
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
RED = (255, 38, 48)

SWEARS = {
    "fuck": "F***", "fucking": "F***ING", "fucked": "F***ED", "fuckin": "F***IN",
    "motherfucker": "MOTHERF***ER", "shit": "S***", "bullshit": "BULLS***",
    "bitch": "B****", "bitches": "B****ES", "dick": "D***", "pussy": "P****",
    "asshole": "A**HOLE", "nigga": "N****", "niggas": "N****S",
}
# Whisper spelling fixes for names in the show.
FIXES = {"neon": "N3ON", "neons": "N3ON'S", "neon's": "N3ON'S", "reborn": "R3BORN"}
HILITE = ["&H00FFFF&", "&HFFFF00&", "&H3CFF3C&"]  # ASS BGR: yellow, cyan, green


def secs(t):
    s = 0.0
    for p in str(t).split(":"):
        s = s * 60 + float(p)
    return s


def parse_seg(text, i):
    rng, _, opt = text.partition("@")
    a, b = rng.split("-")
    zoom, x = (1.0 if i % 2 == 0 else 1.12), 0.5
    if opt:
        z, _, xx = opt.partition(":")
        zoom = float(z) if z else zoom
        x = float(xx) if xx else x
    return secs(a), secs(b), zoom, x


def probe(path):
    out = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
        "-of", "json", path]))
    v = next(s for s in out["streams"] if s["codec_type"] == "video")
    has_a = any(s["codec_type"] == "audio" for s in out["streams"])
    return v["width"], v["height"], has_a


# ---------------------------------------------------------------- hook overlay
def emoji_img(ch, size):
    f = ImageFont.truetype(EMOJI_FONT, 109)
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((0, 0), ch, font=f, embedded_color=True)
    im = im.crop(im.getbbox())
    return im.resize((round(im.width * size / im.height), size), Image.LANCZOS)


def is_emoji(ch):
    return ord(ch) > 0x2500


def build_overlay(path, hook, cta):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_BLACK, 66)
    lines = [ln.strip() for ln in hook.split("|")] if hook else []
    line_h = 84
    y = VIDEO_TOP - 36 - line_h * len(lines)
    for line in lines:
        # tokens: (text, colour) runs; *word* = red; emoji drawn as images
        runs = []
        for part in re.split(r"(\*[^*]+\*)", line):
            if not part:
                continue
            red = part.startswith("*")
            part = part.strip("*")
            buf = ""
            for ch in part:
                if is_emoji(ch):
                    if buf:
                        runs.append((buf, red))
                        buf = ""
                    runs.append((ch, "emoji"))
                elif ch == "️":
                    continue
                else:
                    buf += ch
            if buf:
                runs.append((buf, red))
        esize = 64
        widths = [esize if c == "emoji" else d.textlength(t, font=font) for t, c in runs]
        x = (W - sum(widths)) / 2
        for (t, c), w in zip(runs, widths):
            if c == "emoji":
                e = emoji_img(t, esize)
                img.alpha_composite(e, (round(x), y + 8))
            else:
                d.text((x, y), t, font=font, fill=RED if c else "white",
                       stroke_width=4, stroke_fill="black")
            x += w
        y += line_h
    if cta:
        f2 = ImageFont.truetype(FONT_XB, 40)
        tw = d.textlength(cta, font=f2)
        d.text(((W - tw) / 2, VIDEO_TOP + BOX_H + 46), cta, font=f2, fill=(200, 200, 200))
    img.save(path)


# ---------------------------------------------------------------- captions
def transcribe(wav, model_name):
    from faster_whisper import WhisperModel
    import wave
    import numpy as np
    with wave.open(wav) as wf:  # 16 kHz mono s16 (decoded by ffmpeg, avoids PyAV quirks)
        audio = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
    m = WhisperModel(model_name, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(audio,word_timestamps=True, language="en", vad_filter=False,
                           condition_on_previous_text=False)
    words = []
    for s in segs:
        for w in s.words:
            t = w.word.strip()
            if t:
                words.append([w.start, w.end, t])
    return words


def clean_word(t):
    core = re.sub(r"[^\w']", "", t).lower()
    punct = "?" if t.endswith("?") else ("!" if t.endswith("!") else "")
    if core in SWEARS:
        return SWEARS[core] + punct, True
    if core in FIXES:
        return FIXES[core] + punct, False
    return re.sub(r"[.,;:\"]", "", t).upper(), False


def ass_time(t):
    t = max(t, 0)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def build_ass(path, words, dur):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: W,Inter Black,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,-1,0,0,0,100,100,1,0,1,8,4,5,40,40,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev, k = [], 0
    for i, (a, b, t) in enumerate(words):
        nxt = words[i + 1][0] if i + 1 < len(words) else dur
        end = min(max(b, a + 0.18), nxt, a + 1.2, dur)
        if end <= a:
            continue
        txt, swear = clean_word(t)
        if not txt:
            continue
        core = re.sub(r"[^A-Z0-9]", "", txt)
        emph = swear or txt.endswith(("?", "!")) or len(core) >= 6
        col = ""
        if emph:
            col = "\\c" + HILITE[k % 3]
            k += 1
        pop = "\\fscx72\\fscy72\\t(0,70,\\fscx112\\fscy112)\\t(70,130,\\fscx100\\fscy100)"
        ev.append(f"Dialogue: 0,{ass_time(a)},{ass_time(end)},W,,0,0,0,,"
                  f"{{\\an5\\pos({W // 2},{CAP_Y}){pop}{col}}}{txt}")
    with open(path, "w") as f:
        f.write(head + "\n".join(ev) + "\n")


# ---------------------------------------------------------------- render
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--seg", action="append", required=True, help="START-END[@ZOOM[:X]], repeatable")
    ap.add_argument("--hook", default="", help="two lines split by |, *word* = red, emoji allowed")
    ap.add_argument("--cta", default="R3BORN EP. 2  •  @HardScope")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="small.en")
    ap.add_argument("--no-flash", action="store_true")
    ap.add_argument("--keep-words", help="write the transcript JSON here (to hand-fix and reuse)")
    ap.add_argument("--words", help="use this transcript JSON instead of running Whisper")
    a = ap.parse_args()

    segs = [parse_seg(s, i) for i, s in enumerate(a.seg)]
    dur = sum(e - s for s, e, _, _ in segs)
    sw, sh, has_a = probe(a.input)
    if not has_a:
        sys.exit("input has no audio")

    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        # 1) cut audio, transcribe in output timeline
        apart = ";".join(f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS[a{i}]" for i, (s, e, _, _) in enumerate(segs))
        acat = "".join(f"[a{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=0:a=1[ca]"
        wav = os.path.join(tmp, "a.wav")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", a.input, "-filter_complex", apart + ";" + acat,
                        "-map", "[ca]", "-ac", "1", "-ar", "16000", wav], check=True)
        if a.words:
            words = json.load(open(a.words))
        else:
            words = transcribe(wav, a.model)
        if a.keep_words:
            json.dump(words, open(a.keep_words, "w"), indent=0)

        ass = os.path.join(tmp, "caps.ass")
        build_ass(ass, words, dur)
        ov = os.path.join(tmp, "ov.png")
        build_overlay(ov, a.hook, a.cta)

        # 2) video graph
        parts, labels, cuts, t = [], "", [], 0.0
        for i, (s, e, z, fx) in enumerate(segs):
            # scale to cover the box, extra zoom, then crop with horizontal focus
            sc_h = round(BOX_H * z / 2) * 2
            sc_w = round(sw * sc_h / sh / 2) * 2
            if sc_w < W:
                sc_w = round(W * z / 2) * 2
                sc_h = round(sh * sc_w / sw / 2) * 2
            cx = int(max(0, min(sc_w - W, sc_w * fx - W / 2)))
            cy = (sc_h - BOX_H) // 2
            parts.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS,fps=30,"
                         f"scale={sc_w}:{sc_h}:flags=lanczos,crop={W}:{BOX_H}:{cx}:{cy},setsar=1[v{i}]")
            parts.append(f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS[a{i}]")
            labels += f"[v{i}][a{i}]"
            t += e - s
            if i < len(segs) - 1:
                cuts.append(t)
        parts.append(f"{labels}concat=n={len(segs)}:v=1:a=1[cv][ca]")
        fx_chain = "eq=saturation=1.35:contrast=1.07:brightness=0.01,unsharp=5:5:0.6"
        if cuts and not a.no_flash:
            en = "+".join(f"between(t,{c:.3f},{c + 0.1:.3f})" for c in cuts)
            fx_chain += f",drawbox=x=0:y=0:w=iw:h=ih:color=0xFF1E28@0.5:t=fill:enable='{en}'"
        parts.append(f"[cv]{fx_chain}[clip]")
        parts.append(f"color=c=black:s={W}x{H}:r=30:d={dur:.3f}[bg]")
        parts.append(f"[bg][clip]overlay=0:{VIDEO_TOP}:shortest=1[b1]")
        parts.append(f"[b1][1:v]overlay=0:0:shortest=1[b2]")
        assp = ass.replace("\\", "/").replace(":", "\\:")
        parts.append(f"[b2]ass='{assp}':fontsdir={FONT_DIR},format=yuv420p[v]")

        # 3) bleep swears
        bad = [(w[0], w[1]) for w in words if clean_word(w[2])[1]]
        if bad:
            en = "+".join(f"between(t,{x - 0.03:.3f},{y + 0.03:.3f})" for x, y in bad)
            parts.append(f"[ca]volume=0:enable='{en}'[mu]")
            parts.append(f"sine=f=1000:sample_rate=48000:d={dur:.3f},volume=0.18,volume=0:enable='not({en})'[bp]")
            parts.append("[mu]aresample=48000[mu2];[mu2][bp]amix=inputs=2:normalize=0:duration=first[a]")
        else:
            parts.append("[ca]anull[a]")
        parts[-1] += ";[a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[ao]"

        cmd = ["ffmpeg", "-y", "-v", "error", "-i", a.input, "-loop", "1", "-i", ov,
               "-filter_complex", ";".join(parts), "-map", "[v]", "-map", "[ao]",
               "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high",
               "-r", "30", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
               "-t", f"{dur:.3f}", a.out]
        subprocess.run(cmd, check=True)
    print(f"wrote {a.out} ({dur:.1f}s, {len(segs)} cuts, {len(bad)} bleeps)")


if __name__ == "__main__":
    sys.exit(main())
