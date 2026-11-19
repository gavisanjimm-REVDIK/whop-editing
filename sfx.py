#!/usr/bin/env python3
"""Synthesised clipper sound effects (made from scratch here, so nothing is copyrighted).

Every function returns a mono float32 numpy array at SR (48 kHz), peak around 1.0.
Run this file directly to write every effect to assets/sfx/*.wav for a listen.

  ding_green   bright two-note "correct answer" chime
  ding_red     low double buzzer "wrong answer"
  boom         deep bass hit for punch-ins (vine-boom style, own synthesis)
  whoosh       filtered-noise swipe for transitions
  flash        camera-flash zap + shutter click (goes with the white backflash)
  shutter      camera shutter click
  riser        rising tension sweep
  record_scratch  "wait, what?" scratch
  pop          short bubble pop for text pop-ins
  tick         small UI tick for counters
  bruh_drop    descending tone for disappointment
  ka_ching     cash-register style double ring
  airhorn      stacked-saw horn blast
  applause     crowd applause
  shimmer      sparkly chime cluster
  heartbeat    lub-dub
  coin         two-note coin
"""
import os
import wave

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def t_(d):
    return np.arange(int(SR * d)) / SR


def env(n, a=0.002, r=None, curve=4.0):
    """attack then exponential decay envelope of n samples."""
    x = np.ones(n)
    na = max(1, int(a * SR))
    x[:na] = np.linspace(0, 1, na)
    if r is None:
        tail = np.linspace(0, 1, n - na)
        x[na:] = np.exp(-curve * tail)
    return x


def norm(x, peak=0.95):
    m = np.max(np.abs(x)) or 1.0
    return (x / m * peak).astype(np.float32)


def lowpass(x, cutoff):
    """one-pole lowpass; cutoff may be an array (per-sample)."""
    cutoff = np.broadcast_to(np.asarray(cutoff, dtype=float), x.shape)
    a = 1 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def bell(f, d, partials=((1, 1), (2.0, 0.5), (3.01, 0.25), (4.2, 0.12)), decay=5.0):
    t = t_(d)
    y = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-decay * m ** 0.6 * t) for m, a in partials)
    return y * env(len(t), 0.001, curve=0.01)


def ding_green():
    a = bell(1318.5, 0.9, decay=4.5)          # E6
    b = bell(1975.5, 1.1, decay=4.0)          # B6
    out = np.zeros(int(SR * 1.2))
    out[:len(a)] += a
    o = int(0.09 * SR)
    out[o:o + len(b)] += b * 1.1
    return norm(out, 0.9)


def ding_red():
    t = t_(0.28)
    def buzz(f):
        sq = np.sign(np.sin(2 * np.pi * f * t)) * 0.6 + np.sin(2 * np.pi * f * 1.5 * t) * 0.3
        return sq * env(len(t), 0.004, curve=1.2)
    gap = np.zeros(int(0.06 * SR))
    y = np.concatenate([buzz(155), gap, buzz(146)])
    return norm(lowpass(y, 2400), 0.8)


def boom():
    d = 1.6
    t = t_(d)
    f = 38 + 90 * np.exp(-t * 18)                    # pitch drop
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 2.2)
    body = np.tanh(body * 2.5)                      # saturation for weight
    click = rng.standard_normal(len(t)) * np.exp(-t * 90) * 0.6
    sub = np.sin(2 * np.pi * 32 * t) * np.exp(-t * 1.6) * 0.5
    rev = np.convolve(body, np.exp(-np.arange(int(0.25 * SR)) / (0.06 * SR)) * 0.0004)[:len(t)]
    return norm(lowpass(body + click + sub + rev, 900))


def whoosh(d=0.55, up=True):
    t = t_(d)
    n = rng.standard_normal(len(t))
    shape = np.sin(np.pi * t / d) ** 2
    cut = (300 + 5000 * (t / d)) if up else (5300 - 5000 * (t / d))
    y = lowpass(n, cut) - lowpass(n, cut * 0.25)
    return norm(y * shape, 0.7)


def shutter():
    t = t_(0.12)
    n = rng.standard_normal(len(t))
    c1 = highpass(n, 1800) * np.exp(-t * 120)
    o = int(0.055 * SR)
    c2 = np.zeros_like(c1)
    c2[o:] = c1[:len(c1) - o] * 0.7
    return norm(c1 + c2, 0.8)


def flash():
    t = t_(0.7)
    zap_f = 3200 * np.exp(-t * 6) + 400
    ph = 2 * np.pi * np.cumsum(zap_f) / SR
    zap = np.sin(ph) * np.exp(-t * 7) * 0.5
    hiss = highpass(rng.standard_normal(len(t)), 4000) * np.exp(-t * 9) * 0.35
    s = shutter()
    out = zap + hiss
    out[:len(s)] += s
    return norm(out, 0.85)


def riser(d=1.4):
    t = t_(d)
    f = 200 * (2 ** (3 * t / d))
    ph = 2 * np.pi * np.cumsum(f) / SR
    saw = (ph / np.pi % 2) - 1
    n = highpass(rng.standard_normal(len(t)), 2000) * 0.3
    y = (saw * 0.4 + np.sin(ph) * 0.4 + n) * (t / d) ** 2
    return norm(lowpass(y, 200 + 7000 * t / d), 0.7)


def record_scratch():
    d = 0.5
    t = t_(d)
    # back-and-forth playback-rate wobble on filtered noise + tone
    rate = np.sin(2 * np.pi * 7 * t) * np.exp(-t * 2)
    f = 300 + 900 * np.abs(rate)
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sign(np.sin(ph)) * 0.25
    n = lowpass(rng.standard_normal(len(t)), 1500 + 3000 * np.abs(rate)) * 1.2
    y = (tone + n) * np.abs(rate) * env(len(t), 0.003, curve=1.0)
    return norm(y, 0.8)


def pop():
    t = t_(0.09)
    f = 900 * np.exp(-t * 30) + 300
    ph = 2 * np.pi * np.cumsum(f) / SR
    return norm(np.sin(ph) * np.exp(-t * 45), 0.75)


def tick():
    t = t_(0.03)
    return norm(np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 200), 0.5)


def bruh_drop():
    d = 0.9
    t = t_(d)
    f = 420 * np.exp(-t * 1.8)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = (np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sign(np.sin(ph))) * env(len(t), 0.01, curve=2.0)
    return norm(lowpass(y, 1800), 0.7)


def ka_ching():
    out = np.zeros(int(SR * 1.0))
    c = highpass(rng.standard_normal(int(0.05 * SR)), 3000) * np.exp(-t_(0.05) * 60)
    out[:len(c)] += c
    b1 = bell(2637, 0.8, decay=6)
    b2 = bell(3136, 0.8, decay=5)
    o = int(0.05 * SR)
    out[o:o + len(b1)] += b1
    o2 = int(0.13 * SR)
    out[o2:o2 + len(b2)] += b2
    return norm(out, 0.8)


def airhorn(d=0.9):
    t = t_(d)
    y = np.zeros_like(t)
    for f in (466, 470, 587, 590, 698):
        ph = 2 * np.pi * f * t + np.sin(2 * np.pi * 5 * t) * 0.3
        y += (ph / np.pi % 2) - 1
    e = np.minimum(1, t / 0.02) * np.minimum(1, (d - t) / 0.08)
    return norm(lowpass(np.tanh(y * 0.6) * e, 3500), 0.7)


def applause(d=3.0):
    """crowd applause: thousands of tiny filtered noise claps with a swell and fade."""
    n = int(SR * d)
    out = np.zeros(n)
    clap = highpass(rng.standard_normal(int(0.012 * SR)), 900) * np.exp(-np.arange(int(0.012 * SR)) / (0.003 * SR))
    swell = np.minimum(1, np.arange(n) / (0.4 * SR)) * np.minimum(1, (n - np.arange(n)) / (1.2 * SR))
    for _ in range(int(d * 900)):
        i = rng.integers(0, n - len(clap))
        if rng.random() < swell[i]:
            out[i:i + len(clap)] += clap * rng.uniform(0.3, 1.0)
    return norm(lowpass(out, 6000), 0.8)


def shimmer(d=1.3):
    """sparkly rising chime cluster (aura / glow moments)."""
    out = np.zeros(int(SR * d))
    notes = [1568, 1760, 2093, 2349, 2637, 3136, 3520]
    for k, f in enumerate(notes):
        b = bell(f, d - k * 0.08, decay=4.5) * (0.7 + 0.3 * rng.random())
        o = int(k * 0.07 * SR)
        out[o:o + len(b)] += b[:len(out) - o]
    out += highpass(rng.standard_normal(len(out)), 7000) * np.exp(-t_(d) * 3) * 0.08
    return norm(out, 0.7)


def heartbeat():
    """lub-dub."""
    def thump(f, d):
        t = t_(d)
        return np.sin(2 * np.pi * (f + 40 * np.exp(-t * 30)) * t) * np.exp(-t * 18)
    out = np.zeros(int(SR * 0.7))
    a, b = thump(55, 0.25), thump(48, 0.3)
    out[:len(a)] += a
    o = int(0.18 * SR)
    out[o:o + len(b)] += b * 0.8
    return norm(np.tanh(out * 2), 0.9)


def coin():
    t = t_(0.5)
    f = np.where(t < 0.07, 988, 1319)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sign(np.sin(ph)) * 0.5 * np.exp(-t * 6)
    return norm(lowpass(y, 5000), 0.6)


def rewind(d=1.2):
    """VHS tape rewind: fast warbling chirps over hiss, speeding up."""
    t = t_(d)
    rate = 8 + 30 * (t / d)
    f = 900 + 700 * np.sin(2 * np.pi * np.cumsum(rate) / SR)
    ph = 2 * np.pi * np.cumsum(f) / SR
    chirp = np.sin(ph) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * np.cumsum(rate) / SR)))
    hiss = highpass(rng.standard_normal(len(t)), 3000) * 0.25
    e = np.minimum(1, t / 0.05) * np.minimum(1, (d - t) / 0.08)
    return norm((chirp * 0.6 + hiss) * e, 0.7)


ALL = dict(ding_green=ding_green, ding_red=ding_red, boom=boom, whoosh=whoosh, flash=flash,
           shutter=shutter, riser=riser, record_scratch=record_scratch, pop=pop, tick=tick,
           bruh_drop=bruh_drop, ka_ching=ka_ching, airhorn=airhorn, applause=applause,
           shimmer=shimmer, heartbeat=heartbeat, coin=coin, rewind=rewind)

_cache = {}


def get(name):
    if name not in _cache:
        _cache[name] = ALL[name]()
    return _cache[name]


def write_wav(path, x, sr=SR):
    x = np.asarray(x)
    if x.ndim == 1:
        x = x[:, None]
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(pcm.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sfx")
    os.makedirs(d, exist_ok=True)
    for k in ALL:
        write_wav(os.path.join(d, k + ".wav"), get(k))
        print("wrote", k)
