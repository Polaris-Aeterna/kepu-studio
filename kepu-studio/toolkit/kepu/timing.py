"""逐字时间的停顿校正（来源：《地基之下》lib/fix_srt.py 的 SILENT / snap_to_pauses，《ETH》engine/voice/timing.py）。

ElevenLabs 的逐字时间在停顿处偶尔偏 0.3–0.4 秒：停顿被算进了标点，下一个字标早或标晚。用音频里真实的静音区间，
校正标点后第一个字的开始时刻（只在 ±0.45 秒内移动）。只用标准库读 wav；装了 numpy 会快一些。
"""
from __future__ import annotations

import array
import math
import wave

PUNCT = "，。：；？！、"
SILENT = set(PUNCT + "“”‘’（）《》「」『』…—·,.:;?!()\"' ")


def snap_to_pauses(chars: list, pauses, reach: float = 0.45) -> list:
    """chars: [(char, start or None, end)]; start None = glued to the previous char.  pauses: [(start, end)]."""
    out = list(chars)
    prev, gap = None, True
    for i, (c, s, e) in enumerate(out):
        if s is None or c in SILENT:
            if c in SILENT:
                gap = True
            continue
        if gap:
            lo = s - reach if prev is None else prev
            ends = [b for a, b in pauses if a <= s + 0.1 and b >= lo and abs(b - s) <= reach]
            if ends:
                t = max(ends)
                if prev is None or t > prev + 0.05:
                    out[i] = (c, t, max(e, t + 0.01))
                    s = t
        prev, gap = s, False
    return out


def read_wav_mono(path) -> tuple[list | object, int]:
    with wave.open(str(path), "rb") as w:
        sr, n, sw, ch = w.getframerate(), w.getnframes(), w.getsampwidth(), w.getnchannels()
        raw = w.readframes(n)
    if sw != 2:
        raise ValueError("expects 16-bit wav")
    a = array.array("h")
    a.frombytes(raw)
    if ch > 1:
        a = a[::ch]
    return a, sr


def find_pauses(path, min_len: float = 0.12, rel_db: float = -38.0) -> list[tuple[float, float]]:
    """Silent stretches [(start, end)] of a 16-bit wav: 10 ms frames whose RMS is rel_db below the peak, >= min_len."""
    a, sr = read_wav_mono(path)
    hop = max(1, sr // 100)
    n = len(a) // hop
    if n == 0:
        return []
    try:
        import numpy as np
        x = np.frombuffer(a.tobytes(), dtype=np.int16).astype(np.float32)[: n * hop].reshape(n, hop)
        rms = list(np.sqrt((x * x).mean(axis=1) + 1e-9))
    except ImportError:
        rms = []
        for k in range(n):
            seg = a[k * hop:(k + 1) * hop]
            rms.append(math.sqrt(sum(v * v for v in seg) / hop + 1e-9))
    peak = max(rms) or 1.0
    quiet = [20 * math.log10(r / peak + 1e-12) < rel_db for r in rms]
    out, start = [], None
    for i, q in enumerate(quiet + [False]):
        if q and start is None:
            start = i
        elif not q and start is not None:
            if (i - start) * 0.01 >= min_len:
                out.append((start * 0.01, i * 0.01))
            start = None
    return out


def wav_duration(path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


def write_wav_slice(src, dst, t0: float, t1: float):
    """Copy [t0, t1] seconds of a wav into a new wav (used for ear-check clips)."""
    with wave.open(str(src), "rb") as w:
        sr, sw, ch = w.getframerate(), w.getsampwidth(), w.getnchannels()
        a = max(0, int(t0 * sr))
        b = min(w.getnframes(), int(t1 * sr))
        w.setpos(a)
        raw = w.readframes(max(0, b - a))
    with wave.open(str(dst), "wb") as o:
        o.setnchannels(ch)
        o.setsampwidth(sw)
        o.setframerate(sr)
        o.writeframes(raw)


def insert_silence(src, dst, cuts: list[tuple[float, float]]):
    """Write src to dst with silence of `seconds` inserted at each (time, seconds); returns the shift function."""
    with wave.open(str(src), "rb") as w:
        sr, sw, ch = w.getframerate(), w.getsampwidth(), w.getnchannels()
        raw = w.readframes(w.getnframes())
    frame = sw * ch
    pieces, last = [], 0
    for t, sec in sorted(cuts):
        k = min(len(raw) // frame, int(t * sr)) * frame
        pieces.append(raw[last:k])
        pieces.append(b"\x00" * (int(sec * sr) * frame))
        last = k
    pieces.append(raw[last:])
    with wave.open(str(dst), "wb") as o:
        o.setnchannels(ch)
        o.setsampwidth(sw)
        o.setframerate(sr)
        o.writeframes(b"".join(pieces))
    cuts = sorted(cuts)

    def shift(t: float) -> float:
        return t + sum(sec for c, sec in cuts if c <= t)
    return shift
