"""Small synthesized sound effects for the graphics (no stock audio needed)."""
import wave

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000


def _bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], btype="band", fs=SR, output="sos"), x)


def _lp(x, f, order=2):
    return sosfilt(butter(order, f, btype="low", fs=SR, output="sos"), x)


def _hp(x, f, order=2):
    return sosfilt(butter(order, f, btype="high", fs=SR, output="sos"), x)


def _norm(x, peak=1.0):
    m = np.abs(x).max()
    return (x / m * peak).astype(np.float32) if m > 0 else x.astype(np.float32)


def whoosh(dur=0.5, up=True, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    chunks = 24
    for c in range(chunks):
        i0, i1 = c * n // chunks, (c + 1) * n // chunks
        p = c / (chunks - 1)
        f = 300 + 3500 * (p if up else 1 - p)
        out[i0:i1] = _bp(noise[i0:i1 + 2000], f * 0.6, f * 1.4)[: i1 - i0]
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    return _norm(out * env, 0.8)


def pop(seed=0):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    f = 700 * np.exp(-t * 18) + 260 + 40 * (seed % 5)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return _norm(np.sin(ph) * np.exp(-t * 45), 0.7)


def tick(seed=0):
    rng = np.random.default_rng(seed)
    n = int(0.025 * SR)
    t = np.arange(n) / SR
    x = _hp(rng.standard_normal(n), 2500) * np.exp(-t * 400) + np.sin(2 * np.pi * 3200 * t) * np.exp(-t * 300)
    return _norm(x, 0.6)


def key(seed=0):
    rng = np.random.default_rng(seed + 100)
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    x = _bp(rng.standard_normal(n), 1500, 6000) * np.exp(-t * 260)
    x += 0.4 * np.sin(2 * np.pi * rng.uniform(1800, 2600) * t) * np.exp(-t * 200)
    return _norm(x, rng.uniform(0.5, 0.8))


def boom(dur=0.9, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 38 + 70 * np.exp(-t * 14)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.5)
    hit = _lp(rng.standard_normal(n), 2500) * np.exp(-t * 60)
    return _norm(body + 0.5 * hit, 0.95)


def _crackle(dur, density, seed, lo=900, hi=7000):
    """Paper crackle: many tiny decaying noise bursts with a time-varying density."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    out = np.zeros(n + SR // 10)
    t_axis = np.linspace(0, 1, n)
    expected = density(t_axis)
    times = np.nonzero(rng.uniform(0, 1, n) < expected / SR)[0]
    for i in times:
        ln = int(rng.uniform(0.0015, 0.008) * SR)
        b = rng.standard_normal(ln) * np.exp(-np.arange(ln) / (ln / 4)) * rng.uniform(0.2, 1.0)
        out[i:i + ln] += b
    out = _bp(out, lo, hi)
    rustle = _bp(rng.standard_normal(len(out)), 300, 2500) * 0.08
    env = np.interp(np.linspace(0, 1, len(out)), np.linspace(0, 1, n), expected / expected.max())
    return out + rustle * env


def paper_open(dur=1.1, seed=1):
    # toss (light), landing crunch, then unfolding crackle that fades
    def dens(x):
        return 120 + 2600 * np.exp(-((x - 0.32) / 0.08) ** 2) + 1400 * np.clip(1 - (x - 0.35) / 0.65, 0, 1) * (x > 0.3)
    x = _crackle(dur, dens, seed)
    x[: int(0.3 * dur * SR)] += whoosh(0.3 * dur, seed=seed)[: int(0.3 * dur * SR)] * 0.15
    return _norm(x, 0.9)


def paper_close(dur=0.9, seed=2):
    def dens(x):
        return 200 + 3000 * np.clip(x / 0.6, 0, 1) * (x < 0.66) + 200 * (x >= 0.66)
    x = _crackle(dur, dens, seed)
    w = whoosh(0.35, seed=seed)
    i = int(0.6 * dur * SR)
    x[i:i + len(w)] += w[: len(x) - i] * 0.25
    return _norm(x, 0.9)


def marker(dur=0.45, seed=3):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = _bp(rng.standard_normal(n), 2000, 5000) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * t))
    env = np.minimum(1, t / 0.03) * np.minimum(1, (dur - t) / 0.05)
    return _norm(x * env, 0.5)


def write_wav(path, stereo):
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
