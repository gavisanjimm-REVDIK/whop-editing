#!/usr/bin/env python3
"""Render a 9:16 FOMO clip ("Guess The Fake Millionaire") from a JSON clip definition.

Layout (1080x1920):
  - blurred, darkened copy of the footage fills the frame
  - 4:5 crop of the speaker (source rows 0-960, which keeps the burned-in subtitles out) at y=300
  - hook text at the top, word-by-word captions (active word highlighted) over the lower part of the crop

Timeline:
  - optional cold open (the craziest line) -> quick silent rewind -> the full moment
  - "segs" are cut back to back; adjacent segs with the same source times keep continuous audio,
    so splitting one moment into several segs with different zoom = punch-ins on the beats

Clip definition (one entry of clips.json):
  {
    "out": "out/01_name.mp4",
    "hook": "Text with *accent* words",
    "accent": "#FFD400",
    "coldopen": [start, end, cx, zoom],      # optional
    "segs": [[start, end, cx, zoom], ...],   # cx = horizontal centre in the 1920px source
    "fix": {"wrong": "right"}                 # optional transcript corrections (case-insensitive, per word)
  }

Usage: python3 fomo_clip.py clips.json [name ...]
"""
import json
import os
import re
import subprocess
import sys
import tempfile

import reframe

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "footage", "fomo.mp4")
WORDS = os.path.join(ROOT, "transcript", "words.json")
FONTDIR = "/usr/share/fonts/opentype/inter"
W, H = 1080, 1920
SW, SH = 1920, 1080
CROP_H = 960            # source rows kept (subtitles live at ~985-1030)
CROP_W = 768            # 4:5
PW, PH = 1080, 1350     # panel size on the canvas
PY = 300                # panel top
REWIND = 0.45           # seconds of rewind between cold open and main
REWIND_SPEED = 4.0
FPS = 30


def ass_color(hexstr):
    h = hexstr.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def ts(t):
    t = max(t, 0)
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def clean(word, fix):
    w = word.strip()
    key = re.sub(r"[^\w']", "", w).lower()
    if key in fix:
        w = re.sub(re.escape(re.sub(r"[^\w']", "", w)), fix[key], w, flags=re.I) if key else w
    w = w.strip(",.;:")
    return w.upper()


def crop_box(cx, zoom, cy=None):
    cw = round(CROP_W / zoom / 2) * 2
    ch = round(CROP_H / zoom / 2) * 2
    x = min(max(round(cx - cw / 2), 0), SW - cw)
    if cy is None:  # zooming in keeps faces (upper part of frame) in view
        y = round((CROP_H - ch) * 0.35)
    else:
        y = min(max(round(cy - ch / 2), 0), CROP_H - ch)
    return cw, ch, x, y


def _q(t, s):
    """Snap a source time to the 30 fps frame grid of a block starting at s."""
    return s + round((t - s) * FPS) / FPS


def _subs(clip, s, e, zoom, fixed_cx=None):
    """Split a continuous source range into (a, b, cx, zoom) sub-shots: auto-reframed per camera cut,
    with manual cx overrides and punch-in zooms from the clip definition."""
    if fixed_cx is not None:
        shots = [(s, e, fixed_cx)]
    else:
        shots = [list(x) for x in reframe.analyse(SRC, s, e)]
        for t0, t1, cx in clip.get("cx", []):
            for sh in shots:
                if t0 <= (sh[0] + sh[1]) / 2 < t1:
                    sh[2] = cx
        merged = []
        for sh in shots:  # same camera, tiny framing change -> keep one framing (no jitter)
            if merged and abs(merged[-1][2] - sh[2]) < 90:
                merged[-1][1] = sh[1]
            else:
                merged.append(sh)
        shots = merged
    punches = [p for p in clip.get("punch", []) if p[1] > s and p[0] < e]
    cuts = {s, e} | {x for sh in shots for x in sh[:2]} | {x for p in punches for x in p[:2]}
    cuts = sorted({_q(min(max(c, s), e), s) for c in cuts})
    out = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        if b - a < 1.5 / FPS:
            continue
        mid = (a + b) / 2
        cx = next((sh[2] for sh in shots if sh[0] <= mid < sh[1]), shots[-1][2])
        z = next((p[2] for p in punches if p[0] <= mid < p[1]), zoom)
        cy = next((p[3] for p in punches if p[0] <= mid < p[1] and len(p) > 3), None)
        out.append((a, b, cx, z, cy))
    return out


def build_pieces(clip):
    pieces = []
    if clip.get("coldopen"):
        co = clip["coldopen"]
        s, e = co[0], co[1]
        z = co[2] if len(co) > 2 else 1.25
        subs = _subs(clip, s, e, z)
        pieces.append(dict(s=s, e=e, kind="normal", subs=subs))
        rs = max(e - REWIND * REWIND_SPEED, s)
        pieces.append(dict(s=rs, e=e, kind="rewind", subs=[(rs, e, subs[-1][2], z, None)]))
    for sg in clip["segs"]:
        s, e = sg[0], sg[1]
        z = sg[2] if len(sg) > 2 else 1.0
        pieces.append(dict(s=s, e=e, kind="normal", subs=_subs(clip, s, e, z)))
    t = 0.0
    for p in pieces:
        nf = round((p["e"] - p["s"]) * FPS)
        p["e"] = p["s"] + nf / FPS
        p["dur"] = nf / FPS / (REWIND_SPEED if p["kind"] == "rewind" else 1)
        p["off"] = t
        t += p["dur"]
    return pieces, t


def chunk_words(words):
    chunks, cur = [], []
    for w in words:
        if cur:
            prev = cur[-1]
            text_len = sum(len(x["t"]) + 1 for x in cur) + len(w["t"])
            if (len(cur) >= 3 or text_len > 17 or w["s"] - prev["e"] > 0.4
                    or prev["t"][-1:] in "?!."):
                chunks.append(cur)
                cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    return chunks


def build_ass(clip, pieces, total, words_all, path):
    accent = ass_color(clip.get("accent", "#FFD400"))
    fix = {k.lower(): v for k, v in clip.get("fix", {}).items()}
    hook = clip["hook"]
    hook_ass = re.sub(r"\*(.+?)\*", lambda m: "{\\c" + accent + "}" + m.group(1) + "{\\c&HFFFFFF&}", hook)

    out_words = []
    edits = {round(float(k), 1): v for k, v in clip.get("edit", {}).items()}
    merged = []
    for w in words_all:
        if merged and w["w"].strip().startswith("-"):
            merged[-1] = dict(merged[-1], w=merged[-1]["w"] + w["w"].strip(), e=w["e"])
        else:
            merged.append(dict(w))
    for w in merged:
        hit = edits.get(float(f"{w['s']:.1f}"))
        if hit is not None:
            w["w"], w["raw"] = hit, True
    for p in pieces:
        if p["kind"] != "normal":
            continue
        for w in merged:
            mid = (w["s"] + w["e"]) / 2
            if p["s"] <= mid < p["e"]:
                txt = w["w"].upper() if w.get("raw") else clean(w["w"], fix)
                if not re.sub(r"\W", "", txt):
                    continue
                s = p["off"] + max(w["s"] - p["s"], 0)
                e = p["off"] + min(w["e"] - p["s"], p["dur"])
                out_words.append(dict(t=txt, s=s, e=e, piece=id(p)))
    out_words.sort(key=lambda w: w["s"])

    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Hook,Inter Black,68,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,5,0,"
        "5,70,70,0,1",
        "Style: Cap,Inter Black,92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,0,0,1,7,3,"
        "5,60,60,0,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        f"Dialogue: 1,{ts(0)},{ts(total)},Hook,,0,0,0,,{{\\pos({W // 2},{PY // 2 + 8})\\q0}}{hook_ass}",
    ]

    cap_y = PY + PH - 250
    chunks = chunk_words(out_words)
    for ci, ch in enumerate(chunks):
        nxt = chunks[ci + 1][0]["s"] if ci + 1 < len(chunks) else total
        chunk_end = min(nxt, ch[-1]["e"] + 0.6)
        for wi, w in enumerate(ch):
            st = w["s"]
            en = ch[wi + 1]["s"] if wi + 1 < len(ch) else chunk_end
            if en <= st:
                continue
            parts = []
            for wj, x in enumerate(ch):
                if wj == wi:
                    parts.append("{\\c" + accent + "\\fscx112\\fscy112}" + x["t"] + "{\\c&HFFFFFF&\\fscx100\\fscy100}")
                else:
                    parts.append(x["t"])
            pop = "\\t(0,80,\\fscx104\\fscy104)" if wi == 0 else ""
            lines.append(f"Dialogue: 0,{ts(st)},{ts(en)},Cap,,0,0,0,,"
                         f"{{\\pos({W // 2},{cap_y})\\fscx96\\fscy96{pop}}}" + " ".join(parts))
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def render(clip, words_all):
    pieces, total = build_pieces(clip)
    out = os.path.join(ROOT, clip["out"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        ass = os.path.join(tmp, "caps.ass")
        build_ass(clip, pieces, total, words_all, ass)
        cmd = ["ffmpeg", "-y", "-v", "error"]
        fg, labels = [], ""
        for i, p in enumerate(pieces):
            cmd += ["-ss", f"{p['s']:.3f}", "-t", f"{p['e'] - p['s'] + 0.1:.3f}", "-i", SRC]
            rew = p["kind"] == "rewind"
            pre = f"reverse,setpts=(PTS-STARTPTS)/{REWIND_SPEED:g},fps={FPS}," if rew else ""
            n = len(p["subs"])
            fg.append(f"[{i}:v]fps={FPS},setpts=PTS-STARTPTS,trim=end_frame={round((p['e'] - p['s']) * FPS)},"
                      f"{pre}setpts=PTS-STARTPTS,split={n + 1}[bg{i}]" + "".join(f"[r{i}_{j}]" for j in range(n)))
            plabels = ""
            for j, (a, b, cx, z, cy) in enumerate(p["subs"]):
                cw, ch, x, y = crop_box(cx, z, cy)
                if rew:
                    tr = ""
                else:
                    tr = (f"trim=start_frame={round((a - p['s']) * FPS)}:end_frame={round((b - p['s']) * FPS)},"
                          "setpts=PTS-STARTPTS,")
                look = ",eq=brightness=0.06:saturation=1.4,noise=alls=18:allf=t" if rew else ""
                fg.append(f"[r{i}_{j}]{tr}crop={cw}:{ch}:{x}:{y},scale={PW}:{PH}:flags=lanczos,setsar=1{look}[p{i}_{j}]")
                plabels += f"[p{i}_{j}]"
            fg.append(f"{plabels}concat=n={n}:v=1:a=0[pc{i}]" if n > 1 else f"{plabels}null[pc{i}]")
            fg.append(f"[bg{i}]crop={SW}:{CROP_H}:0:0,scale=-2:{H},crop={W}:{H},gblur=sigma=38,"
                      f"eq=brightness=-0.22:saturation=1.2,setsar=1[g{i}]")
            fg.append(f"[g{i}][pc{i}]overlay=0:{PY}:shortest=1,trim=duration={p['dur']:.4f}[v{i}]")
            if rew:
                fg.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={p['dur']:.4f}[s{i}]")
            else:
                fg.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=PTS-STARTPTS,"
                          f"atrim=duration={p['dur']:.4f},afade=t=in:d=0.02,"
                          f"afade=t=out:st={max(p['dur'] - 0.02, 0):.4f}:d=0.02[s{i}]")
            labels += f"[v{i}][s{i}]"
        fg.append(f"{labels}concat=n={len(pieces)}:v=1:a=1[cv][ca]")
        fg.append(f"[cv]ass={ass}:fontsdir={FONTDIR},format=yuv420p[v]")
        cmd += ["-filter_complex", ";".join(fg), "-map", "[v]", "-map", "[ca]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS),
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out]
        subprocess.run(cmd, check=True)
    print(f"wrote {clip['out']} ({total:.1f}s)")
    for p in pieces:
        print(f"  {p['kind']:6s} {p['s']:.2f}-{p['e']:.2f}: " +
              ", ".join(f"{a:.1f}-{b:.1f}@{cx:.0f}x{z:g}" for a, b, cx, z, _ in p["subs"]))


def main():
    clips = json.load(open(sys.argv[1]))
    names = set(sys.argv[2:])
    words_all = []
    for seg in json.load(open(WORDS)):
        for w in seg["words"]:
            words_all.append(dict(w=w["w"], s=w["s"], e=w["e"]))
    for c in clips:
        if names and not any(n in c["out"] for n in names):
            continue
        render(c, words_all)


if __name__ == "__main__":
    main()
