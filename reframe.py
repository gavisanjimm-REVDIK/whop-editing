#!/usr/bin/env python3
"""Shot-cut detection + face-based horizontal crop centre for the FOMO source.

analyse(src, t0, t1) -> list of shots [(start, end, cx)] in source seconds, where cx is the
horizontal centre (in 1920px source coords) to put the 4:5 crop on.
"""
import subprocess
import numpy as np
import cv2

SW, SH = 1920, 1080
AW, AH = 960, 540          # analysis size
FPS = 10
CROP_W = 768
_front = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
_prof = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")


def _frames(src, t0, t1):
    cmd = ["ffmpeg", "-v", "quiet", "-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", src,
           "-vf", f"fps={FPS},scale={AW}:{AH}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(raw) // (AW * AH)
    return np.frombuffer(raw[: n * AW * AH], np.uint8).reshape(n, AH, AW)


def _faces(g):
    g = g[: int(AH * 0.89)]  # ignore the burned-in subtitle band
    out = []
    for casc, flip in ((_front, False), (_prof, False), (_prof, True)):
        img = cv2.flip(g, 1) if flip else g
        for (x, y, w, h) in casc.detectMultiScale(img, 1.1, 6, minSize=(60, 60)):
            if flip:
                x = AW - x - w
            out.append((x, y, w, h))
    # merge overlapping detections
    merged = []
    for f in sorted(out, key=lambda f: -f[2]):
        cx = f[0] + f[2] / 2
        if all(abs(cx - (m[0] + m[2] / 2)) > m[2] * 0.6 for m in merged):
            merged.append(f)
    return merged


def _choose_cx(faces):
    """Pick the face to frame: big and near the centre (editors frame the speaker centrally)."""
    if not faces:
        return None
    s = SW / AW
    best = max(faces, key=lambda f: f[2] * (1.2 - abs((f[0] + f[2] / 2) - AW / 2) / AW))
    bx = (best[0] + best[2] / 2) * s
    # if a second face fits in the same crop together with the chosen one, frame both
    others = [f for f in faces if f is not best and f[2] > best[2] * 0.6]
    for o in others:
        ox = (o[0] + o[2] / 2) * s
        lo, hi = min(bx, ox) - best[2] * s * 0.7, max(bx, ox) + best[2] * s * 0.7
        if hi - lo < CROP_W:
            return (lo + hi) / 2
    return bx


def analyse(src, t0, t1):
    fr = _frames(src, t0, t1)
    if len(fr) == 0:
        return [(t0, t1, SW / 2)]
    small = fr[:, ::8, ::8].astype(np.int16)
    cuts = [0]
    for i in range(1, len(fr)):
        if np.abs(small[i] - small[i - 1]).mean() > 18:
            cuts.append(i)
    cuts.append(len(fr))
    shots = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        idx = sorted({a + (b - a) // 4, a + (b - a) // 2, a + 3 * (b - a) // 4})
        xs = [c for c in (_choose_cx(_faces(fr[i])) for i in idx if i < len(fr)) if c is not None]
        cx = float(np.median(xs)) if xs else None
        s = t0 + a / FPS
        e = t0 + b / FPS if b < len(fr) else t1
        shots.append([s, e, cx])
    # shots with no face: keep previous shot's framing if it was the same camera, else centre
    for i, sh in enumerate(shots):
        if sh[2] is None:
            sh[2] = SW / 2
    # merge tiny shots (< 0.3 s, usually false cuts / flashes) into neighbours
    merged = []
    for sh in shots:
        if merged and sh[1] - sh[0] < 0.3:
            merged[-1][1] = sh[1]
        else:
            merged.append(sh)
    return [tuple(s) for s in merged]


if __name__ == "__main__":
    import sys
    for s in analyse(sys.argv[1], float(sys.argv[2]), float(sys.argv[3])):
        print(f"{s[0]:7.2f}-{s[1]:7.2f}  cx={s[2]:.0f}")
