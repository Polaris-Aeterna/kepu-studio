"""宣传片的音效和底乐：全部用 numpy 合成（没有采样、没有版权问题），48 kHz。

    engine/.venv/bin/python engine/sfx.py                  # → assets/sfx/*.wav（场景里 add_sound 用）
    engine/.venv/bin/python engine/sfx.py --bed 106.2 --title 13.1 --end 97.4   # → assets/sfx/bed.wav（成片混音用）

音效的分工（EVA 标题卡的语法：硬切要有“重量”，红色判定要有“声音”）：
  hit    大字卡 / 片名 / 片尾的硬切：下潜的低频 + 噪声瞬态 + 一点金属余韵
  tick   快切、列表逐行进：短促的高频点
  key    终端逐行打出：比 tick 低一点、更软
  err    红色判定（念错、没过）：两个下行的低音
  ok     ✓：一声很轻的叮
  sweep  判定线扫过：带通噪声从低扫到高
  paper  纸色插卡闪切：亮的噪声 + 高频一响
  deal   发牌：短促的滑动声
底乐 bed：冷开场是心跳和低音持续音，片名之后换成安静的和弦铺底，片尾抬起来再收掉。
"""
from __future__ import annotations

import argparse
import wave
from pathlib import Path

import numpy as np

SR = 48000
OUT = Path(__file__).resolve().parents[1] / "assets" / "sfx"
rng = np.random.default_rng(7)


def t_(dur):
    return np.arange(int(dur * SR)) / SR


def env_exp(t, tau):
    return np.exp(-t / tau)


def attack(x, ms=2.0):
    n = max(1, int(ms * SR / 1000))
    x[:n] *= np.linspace(0, 1, n)
    return x


def lowpass(x, fc):
    """One-pole low-pass (fine for shaping noise)."""
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def bandpass_fft(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def svf_sweep(x, f0, f1, q=2.0):
    """State-variable band-pass whose centre glides exponentially f0 -> f1 over the clip."""
    n = len(x)
    fc = f0 * (f1 / f0) ** (np.arange(n) / n)
    low = band = 0.0
    y = np.empty_like(x)
    for i in range(n):
        f = 2 * np.sin(np.pi * fc[i] / SR)
        high = x[i] - low - band / q
        band += f * high
        low += f * band
        y[i] = band
    return y


def norm(x, peak):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


def write(name, x, stereo=False):
    OUT.mkdir(parents=True, exist_ok=True)
    x = np.clip(x, -1, 1)
    data = (x * 32767).astype("<i2")
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(2 if stereo else 1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    return OUT / f"{name}.wav"


# ---------------------------------------------------------------- one-shots
def hit():
    t = t_(1.6)
    f = 38 + 74 * np.exp(-t / 0.045)                          # pitch dive
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(t, 0.42)
    body = lowpass(rng.standard_normal(len(t)), 900) * env_exp(t, 0.05) * 2.2
    click = np.zeros_like(t)
    click[:90] = rng.standard_normal(90) * np.linspace(1, 0, 90)
    ring = sum(a * np.sin(2 * np.pi * 196 * k * t) for k, a in ((1, 1), (2.76, .55), (5.4, .3))) * env_exp(t, 0.6) * 0.07
    x = sub * 0.9 + body * 0.35 + click * 0.5 + ring
    return norm(attack(x, 1), 0.92)


def tick():
    t = t_(0.06)
    n = bandpass_fft(rng.standard_normal(len(t)), 2200, 7000) * env_exp(t, 0.0035)
    s = np.sin(2 * np.pi * 2400 * t) * env_exp(t, 0.012) * 0.35
    return norm(attack(n + s, 0.3), 0.5)


def key():
    t = t_(0.05)
    n = bandpass_fft(rng.standard_normal(len(t)), 900, 3500) * env_exp(t, 0.005)
    s = np.sin(2 * np.pi * 1300 * t) * env_exp(t, 0.01) * 0.25
    return norm(attack(n + s, 0.3), 0.32)


def err():
    out = []
    for f, d in ((233.1, 0.11), (174.6, 0.2)):
        t = t_(d)
        w = sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 3, 5))      # soft square
        e = np.minimum(1, t / 0.006) * np.minimum(1, (d - t) / 0.03)
        out.append(lowpass(w * e, 2500))
    x = np.concatenate([out[0], np.zeros(int(0.025 * SR)), out[1]])
    return norm(x, 0.55)


def ok():
    t = t_(0.5)
    x = (np.sin(2 * np.pi * 1318.5 * t) + 0.35 * np.sin(2 * np.pi * 1975.5 * t)) * env_exp(t, 0.16)
    return norm(attack(x, 3), 0.3)


def sweep():
    t = t_(0.55)
    x = svf_sweep(rng.standard_normal(len(t)), 260, 6500, q=3.0)
    e = np.sin(np.pi * np.minimum(1, t / 0.55)) ** 1.5
    return norm(x * e, 0.42)


def paper():
    t = t_(0.45)
    n = bandpass_fft(rng.standard_normal(len(t)), 3000, 12000) * env_exp(t, 0.012)
    ping = np.sin(2 * np.pi * 3520 * t) * env_exp(t, 0.09) * 0.25
    thump = np.sin(2 * np.pi * (60 + 40 * np.exp(-t / 0.03)) * t) * env_exp(t, 0.08) * 0.6
    return norm(attack(n + ping + thump, 0.5), 0.6)


def deal():
    t = t_(0.09)
    x = svf_sweep(rng.standard_normal(len(t)), 7000, 1200, q=1.2) * env_exp(t, 0.03)
    return norm(attack(x, 0.5), 0.38)


# ---------------------------------------------------------------- the bed
def bed(total: float, title: float, end: float) -> np.ndarray:
    """Stereo bed: heartbeat + drone until the title hit, a quiet pad after it, a lift into the end card."""
    t = t_(total)
    n = len(t)
    L = np.zeros(n)
    R = np.zeros(n)

    def saw(f, ph=0.0):
        p = (f * t + ph) % 1.0
        return 2 * p - 1

    # drone (whole film): two detuned A1 saws + E2, low-passed, slow movement
    drone_l = saw(55.0) + saw(55.21, .3) + 0.6 * saw(82.41, .1)
    drone_r = saw(54.83, .6) + saw(55.0, .9) + 0.6 * saw(82.6, .5)
    lp = 260 + 120 * np.sin(2 * np.pi * 0.05 * t)
    drone_l = lowpass(drone_l, 240) * 0.9
    drone_r = lowpass(drone_r, 240) * 0.9
    dl = np.interp(t, [0, 2, title - 0.4, title, title + 3, end - 4, end, total - 2.5, total],
                   [0, .75, 1.0, 0, .38, .38, .85, .6, 0])
    L += drone_l * dl * 0.16
    R += drone_r * dl * 0.16
    # heartbeat in the cold open (lub-dub, ~68 bpm), getting louder towards the title
    beat = np.zeros(n)
    k = 0.35
    while k < title - 0.6:
        for off, a in ((0.0, 1.0), (0.24, 0.62)):
            i0 = int((k + off) * SR)
            tt = t_(0.45)
            thump = np.sin(2 * np.pi * np.cumsum(46 + 40 * np.exp(-tt / 0.03)) / SR) * env_exp(tt, 0.11) * a
            j = min(n, i0 + len(tt))
            beat[i0:j] += thump[:j - i0] * (0.45 + 0.55 * k / title)
        k += 0.88
    L += beat * 0.32
    R += beat * 0.32
    # pad after the title: A minor add9 (A2 E3 B3 C4), slow attack, gentle chorus
    pad = np.zeros(n)
    for f, a in ((110.0, 1.0), (164.81, .8), (246.94, .55), (261.63, .45), (329.63, .3)):
        pad += a * (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.003 * t + 1.1))
    pad = lowpass(pad, 1400)
    pl = np.interp(t, [0, title + 0.6, title + 4.5, end - 3, end, end + 1.5, total - 2.5, total],
                   [0, 0, 1, 1, 1.5, 1.2, .9, 0])
    trem = 0.85 + 0.15 * np.sin(2 * np.pi * 0.13 * t)
    L += pad * pl * trem * 0.045
    R += pad * pl * (1.7 - trem) * 0.045
    # air: high band noise, barely there
    air = bandpass_fft(rng.standard_normal(n), 2500, 6000)
    air = air / np.max(np.abs(air))
    L += air * np.interp(t, [0, title, title + 2, total], [0.004, 0.006, 0.003, 0.003])
    R += np.roll(air, 4800) * np.interp(t, [0, title, title + 2, total], [0.004, 0.006, 0.003, 0.003])
    st = np.stack([L, R], axis=1)
    return st / max(1e-9, np.max(np.abs(st))) * 0.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bed", type=float)
    ap.add_argument("--title", type=float, default=13.0)
    ap.add_argument("--end", type=float, default=95.0)
    a = ap.parse_args()
    if a.bed:
        p = write("bed", bed(a.bed, a.title, a.end).reshape(-1), stereo=True)
        print(p)
        return
    for name, fn in (("hit", hit), ("tick", tick), ("key", key), ("err", err), ("ok", ok), ("sweep", sweep),
                     ("paper", paper), ("deal", deal)):
        print(write(name, fn()))


if __name__ == "__main__":
    main()
