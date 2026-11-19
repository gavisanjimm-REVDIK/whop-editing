#!/usr/bin/env python3
"""Render 9:16 KreekCraft GTA 6 stream clips (TikTok / Reels / Shorts).

Layout (1080x1920):
  - blurred, darkened stream as the background
  - hook text (white box, black text) at the top, on screen the whole clip
  - KreekCraft's facecam (cropped from the top-left of the stream) under the hook
  - gameplay under the facecam
  - word-by-word subtitles on the seam between facecam and gameplay
  - official KreekCraft logo overlay (Twitch + YouTube @KreekCraft), always visible

Audio is the original stream audio, loudness-normalised.

Clips are described in clips.json. Every time is in seconds on the Twitch VOD timeline.
  python3 kreek_clip.py clips.json            # render every clip
  python3 kreek_clip.py clips.json 03_cops    # render one clip by name
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
import concurrent.futures as cf

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(ROOT, "assets", "kreekcraft-overlay.png")
SUB_FONT_DIR = os.path.join(ROOT, "assets", "fonts")
SUB_FONT = "Luckiest Guy"
HOOK_FONT = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
FOOTAGE = os.path.join(ROOT, "footage")
W, H, FPS = 1080, 1920, 60

# Where things sit on the 1920-high canvas.
CAM_Y, CAM_H = 330, 660          # facecam panel
GAME_Y = CAM_Y + CAM_H           # gameplay panel starts right under the cam
SEAM_Y = GAME_Y                  # subtitles are centred here
LOGO_W, LOGO_Y = 720, 1330       # logo overlay: above the Shorts/TikTok bottom UI

# Crops on the 1920x1080 stream.
CAM_CROP = (746, 456, 0, 80)     # w, h, x, y: facecam box top-left (+ a little game beside it)
GAME_CROP = (1520, 1080, 400, 0)  # gameplay with the facecam corner trimmed off


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


# ---------------------------------------------------------------- footage

def playlist(url):
    base = url.rsplit("/", 1)[0] + "/"
    text = urllib.request.urlopen(url, timeout=60).read().decode()
    init, segs, t, dur = None, [], 0.0, 10.0
    for ln in text.splitlines():
        if ln.startswith("#EXT-X-MAP"):
            init = ln.split('URI="')[1].split('"')[0]
        elif ln.startswith("#EXTINF"):
            dur = float(ln.split(":")[1].split(",")[0])
        elif ln and not ln.startswith("#"):
            segs.append((t, dur, ln))
            t += dur
    return base, init, segs


def fetch(url, a, b, out):
    """Download VOD time a..b (seconds) from the HLS playlist; returns the real start time of the file."""
    base, init, segs = playlist(url)
    pick = [s for s in segs if s[0] + s[1] > a and s[0] < b]

    def get(name):
        err = None
        for _ in range(5):
            try:
                return urllib.request.urlopen(base + name, timeout=60).read()
            except Exception as e:  # noqa: BLE001 - retry any network error
                err = e
        raise err

    with cf.ThreadPoolExecutor(16) as ex:
        data = list(ex.map(get, [p[2] for p in pick]))
    raw = out + ".frag.mp4"
    with open(raw, "wb") as f:
        if init:
            f.write(get(init))
        for d in data:
            f.write(d)
    run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-c", "copy", "-avoid_negative_ts", "make_zero",
         "-movflags", "+faststart", out])
    os.remove(raw)
    return pick[0][0]


def source_for(cfg, a, b):
    """Local file covering VOD time a..b; returns (path, file_start_on_vod)."""
    os.makedirs(FOOTAGE, exist_ok=True)
    a0, b0 = int(a // 10 * 10), int(-(-b // 10) * 10)
    path = os.path.join(FOOTAGE, f"vod_{a0}_{b0}.mp4")
    if not os.path.exists(path):
        print(f"  fetching VOD {a0}-{b0}s")
        fetch(cfg["playlist"], a0, b0, path)
    return path, a0


# ---------------------------------------------------------------- subtitles

def transcribe_words(wav, prompt=""):
    from faster_whisper import WhisperModel
    m = WhisperModel("small.en", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(wav, beam_size=5, word_timestamps=True, vad_filter=False,
                           initial_prompt=prompt or None, condition_on_previous_text=False)
    words = []
    for s in segs:
        for w in s.words:
            words.append({"s": round(w.start, 2), "e": round(w.end, 2), "w": w.word.strip()})
    return words


def ass_time(t):
    t = max(t, 0)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def chunk_words(words, max_words=3, max_chars=16, gap=0.45):
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words
                    or len(" ".join(x["w"] for x in cur + [w])) > max_chars
                    or w["s"] - cur[-1]["e"] > gap
                    or re.search(r"[.?!,]$", cur[-1]["w"])):
            chunks.append(cur)
            cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def clean(word):
    return re.sub(r"[.,]+$", "", word).upper()


def write_ass(words, path, dur):
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{SUB_FONT},92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,2,0,1,7,4,5,40,40,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    chunks = chunk_words(words)
    for ci, ch in enumerate(chunks):
        end_chunk = ch[-1]["e"] + 0.25
        if ci + 1 < len(chunks):
            end_chunk = min(end_chunk, chunks[ci + 1][0]["s"])
        end_chunk = min(end_chunk, dur)
        for wi, w in enumerate(ch):
            st = w["s"] if wi else ch[0]["s"]
            en = ch[wi + 1]["s"] if wi + 1 < len(ch) else end_chunk
            if en <= st:
                continue
            parts = []
            for k, x in enumerate(ch):
                txt = clean(x["w"])
                parts.append(r"{\c&H00F7FF&}" + txt + r"{\c&HFFFFFF&}" if k == wi else txt)
            pop = r"{\fscx80\fscy80\t(0,90,\fscx106\fscy106)\t(90,160,\fscx100\fscy100)}" if wi == 0 else ""
            lines.append(f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Sub,,0,0,0,,"
                         f"{{\\pos({W // 2},{SEAM_Y})}}{pop}{' '.join(parts)}")
    with open(path, "w") as f:
        f.write(head + "\n".join(lines) + "\n")


# ---------------------------------------------------------------- overlay

def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def build_overlay(path, hook):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Hook: black text in a white rounded box, centred in the band above the cam.
    size = 62
    while True:
        font = ImageFont.truetype(HOOK_FONT, size)
        lines = wrap(d, hook, font, W - 160)
        if len(lines) <= 3 or size <= 44:
            break
        size -= 4
    lh = int(size * 1.18)
    box_h = lh * len(lines) + 44
    box_w = max(d.textlength(l, font=font) for l in lines) + 70
    top = 110 + (CAM_Y - 110 - 20 - box_h) // 2
    d.rounded_rectangle([(W - box_w) / 2, top, (W + box_w) / 2, top + box_h], radius=26, fill="white")
    y = top + 22
    for l in lines:
        tw = d.textlength(l, font=font)
        d.text(((W - tw) / 2, y - size * 0.06), l, font=font, fill="black")
        y += lh

    # Official KreekCraft overlay, used as-is.
    logo = Image.open(LOGO).convert("RGBA")
    bbox = logo.getbbox()
    logo = logo.crop(bbox)
    lh_ = round(logo.height * LOGO_W / logo.width)
    logo = logo.resize((LOGO_W, lh_), Image.LANCZOS)
    img.alpha_composite(logo, ((W - LOGO_W) // 2, LOGO_Y))
    img.save(path)


# ---------------------------------------------------------------- render

def zoom_expr(zooms, amount=0.14):
    """scale factor over time: quick punch-in at each zoom time, held ~1.1 s, eased back out."""
    if not zooms:
        return "1"
    terms = []
    for z in zooms:
        terms.append(f"{amount}*clip((t-{z})/0.12,0,1)*clip(({z}+1.25-t)/0.25,0,1)")
    return "1+" + "+".join(terms)


def render(cfg, clip):
    name = clip["name"]
    work = os.path.join(ROOT, "build", name)
    os.makedirs(work, exist_ok=True)
    out = os.path.join(ROOT, "out", f"{name}.mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print(f"[{name}]")

    # 1) cut + join the segments into one 1080p60 clip
    src = os.path.join(work, "src.mp4")
    segs = clip["segments"]
    if not os.path.exists(src) or clip.get("recut"):
        inputs, parts, labels = [], [], ""
        for i, (a, b) in enumerate(segs):
            path, start = source_for(cfg, a, b)
            inputs += ["-i", path]
            parts.append(f"[{i}:v]trim={a - start}:{b - start},setpts=PTS-STARTPTS,fps={FPS}[v{i}]")
            parts.append(f"[{i}:a]atrim={a - start}:{b - start},asetpts=PTS-STARTPTS[a{i}]")
            labels += f"[v{i}][a{i}]"
        parts.append(f"{labels}concat=n={len(segs)}:v=1:a=1[v][a]")
        run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(parts),
             "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "14", "-preset", "fast",
             "-c:a", "aac", "-b:a", "256k", src])
    dur = sum(b - a for a, b in segs)

    # 2) word-level subtitles
    words_path = os.path.join(work, "words.json")
    if not os.path.exists(words_path):
        wav = os.path.join(work, "a.wav")
        run(["ffmpeg", "-y", "-v", "error", "-i", src, "-ac", "1", "-ar", "16000", wav])
        words = transcribe_words(wav, cfg.get("whisper_prompt", ""))
        json.dump(words, open(words_path, "w"), indent=0)
    words = json.load(open(words_path))
    for wrong, right in {**cfg.get("fixes", {}), **clip.get("fixes", {})}.items():
        for w in words:
            if w["w"].strip(".,!?").lower() == wrong.lower():
                w["w"] = re.sub(re.escape(w["w"].strip(".,!?")), right, w["w"], flags=re.I)
    words = [w for w in words if w["w"].strip(".,!?-")]
    ass = os.path.join(work, "subs.ass")
    write_ass(words, ass, dur)

    # 3) compose
    ov = os.path.join(work, "overlay.png")
    build_overlay(ov, clip["hook"])
    cw, ch, cx, cy = CAM_CROP
    gw, gh, gx, gy = GAME_CROP
    game_h = round(W * gh / gw / 2) * 2
    z = zoom_expr(clip.get("zooms", []))
    fo = max(dur - 0.35, 0)
    fc = ";".join([
        "[0:v]split=3[bgs][cams][games]",
        f"[bgs]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=12:2,"
        f"scale={W}:{H},eq=brightness=-0.22:saturation=1.2[bg]",
        f"[cams]crop={cw}:{ch}:{cx}:{cy},scale=w='{W}*({z})':h='{CAM_H}*({z})':eval=frame,"
        f"crop={W}:{CAM_H}:(iw-{W})/2:(ih-{CAM_H})/2[cam]",
        f"[games]crop={gw}:{gh}:{gx}:{gy},scale={W}:{game_h}[game]",
        f"[bg][cam]overlay=0:{CAM_Y}[b1]",
        f"[b1][game]overlay=0:{GAME_Y}[b2]",
        "[b2][1:v]overlay=0:0[b3]",
        f"[b3]ass={ass}:fontsdir={SUB_FONT_DIR},fade=t=in:st=0:d=0.15,fade=t=out:st={fo:.2f}:d=0.35,"
        "format=yuv420p[v]",
        f"[0:a]loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st={fo:.2f}:d=0.35,aresample=48000[a]",
    ])
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-loop", "1", "-framerate", str(FPS), "-i", ov,
         "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS), "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{dur:.3f}", out])
    print(f"  wrote {out} ({dur:.1f}s)")


def main():
    cfg = json.load(open(sys.argv[1]))
    if not cfg.get("playlist"):
        cfg["playlist"] = subprocess.check_output(
            ["yt-dlp", "-f", "1080p60", "-g", cfg["vod"]], text=True).strip()
    only = set(sys.argv[2:])
    for clip in cfg["clips"]:
        if not only or clip["name"] in only:
            render(cfg, clip)


if __name__ == "__main__":
    main()
