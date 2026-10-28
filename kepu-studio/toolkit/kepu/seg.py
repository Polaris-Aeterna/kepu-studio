"""Word list + segmentation, used only to *detect* pronunciation risk (and to break subtitle lines at word edges).

The list (data/words.tsv.gz) is jieba's dictionary plus pypinyin's phrase dictionary.  For words that contain a
character from data/polyphones.tsv it stores the dictionary reading:
    strength "P" = pypinyin phrase dictionary (curated, but wrong on many STEM terms: 方差 chà, 相变 xiāng …)
    strength "J" = jieba-only word, reading guessed (weak)
The first load takes a few seconds; a pickle is written to ~/.kepu/cache/ so later loads are fast.
"""
from __future__ import annotations

import gzip
import hashlib
import math
import pickle
from functools import lru_cache

from .util import DATA, USER_DIR, is_han

MAX_WORD = 8


@lru_cache(maxsize=1)
def words() -> tuple[dict, float]:
    """({word: (freq, strength, syllables tuple or None)}, log total)."""
    src = DATA / "words.tsv.gz"
    digest = hashlib.sha1(str(src.stat().st_size).encode() + str(int(src.stat().st_mtime)).encode()).hexdigest()[:10]
    cache = USER_DIR / "cache" / f"words-{digest}.pkl"
    if cache.exists():
        try:
            with open(cache, "rb") as f:
                return pickle.load(f)
        except Exception:  # noqa: BLE001  (corrupt / other Python version: rebuild)
            pass
    d: dict = {}
    total = 0
    with gzip.open(src, "rt", encoding="utf-8") as f:
        for ln in f:
            if ln.startswith("#"):
                continue
            w, fr, rd = (ln.rstrip("\n").split("\t") + ["", "", ""])[:3]
            n = int(fr or 1)
            total += n
            if rd:
                d[w] = (n, rd[0], tuple(rd[2:].split(" ")))
            else:
                d[w] = (n, "", None)
    res = (d, math.log(total))
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        with open(cache, "wb") as f:
            pickle.dump(res, f, protocol=4)
    except OSError:
        pass
    return res


def logp(word: str) -> float:
    d, lt = words()
    rec = d.get(word)
    if rec:
        return math.log(max(rec[0], 1)) - lt
    return (0.0 if len(word) == 1 else -1e9) - lt          # unknown single char: frequency 1


def dag(text: str) -> list[list[int]]:
    """dag[i] = end positions e (exclusive) such that text[i:e] is a word (single characters always count)."""
    d, _ = words()
    out = []
    for i in range(len(text)):
        ends = [i + 1]
        if is_han(text[i]):
            for e in range(i + 2, min(len(text), i + MAX_WORD) + 1):
                if not is_han(text[e - 1]):
                    break
                if text[i:e] in d:
                    ends.append(e)
        out.append(ends)
    return out


def _forward_backward(text: str):
    g = dag(text)
    n = len(text)
    fwd = [-math.inf] * (n + 1)
    fwd[0] = 0.0
    for i in range(n):
        if fwd[i] == -math.inf:
            continue
        for e in g[i]:
            v = fwd[i] + logp(text[i:e])
            if v > fwd[e]:
                fwd[e] = v
    bwd = [-math.inf] * (n + 1)
    bwd[n] = 0.0
    for i in range(n - 1, -1, -1):
        bwd[i] = max(logp(text[i:e]) + bwd[e] for e in g[i])
    return g, fwd, bwd


def cut(text: str) -> list[str]:
    """Most probable segmentation (jieba-style, without the HMM for unknown words)."""
    if not text:
        return []
    g, fwd, bwd = _forward_backward(text)
    out, i = [], 0
    while i < len(text):
        e = max(g[i], key=lambda e: logp(text[i:e]) + bwd[e])
        out.append(text[i:e])
        i = e
    return out


class Lattice:
    """All segmentations of one text: best path, and how plausible a segmentation with given edges is."""

    def __init__(self, text: str):
        self.text = text
        self.g, self.fwd, self.bwd = _forward_backward(text)
        self.best = self.bwd[0]
        self.bounds = {0}
        i = 0
        while i < len(text):
            i = max(self.g[i], key=lambda e, i=i: logp(text[i:e]) + self.bwd[e])
            self.bounds.add(i)

    def aligned(self, a: int, b: int) -> bool:
        return a in self.bounds and b in self.bounds

    def delta(self, a: int, b: int) -> float:
        """log-probability lost by forcing word edges at a and b (0 = the best segmentation already has them)."""
        if self.aligned(a, b):
            return 0.0
        t = self.text
        inner = [-math.inf] * (b - a + 1)
        inner[0] = 0.0
        for s in range(a, b):
            if inner[s - a] == -math.inf:
                continue
            for e in self.g[s]:
                if e <= b:
                    inner[e - a] = max(inner[e - a], inner[s - a] + logp(t[s:e]))
        return self.fwd[a] + inner[b - a] + self.bwd[b] - self.best

    def covering(self, margin: float = 3.0) -> dict[int, list[tuple[float, int, int]]]:
        return covering(self.text, margin, (self.g, self.fwd, self.bwd))


def covering(text: str, margin: float = 3.0, _fb=None) -> dict[int, list[tuple[float, int, int]]]:
    """For every position: the words that could cover it, with how plausible the best segmentation using that word
    is, relative to the best overall (0 = best; -margin.. kept).  {i: [(score_delta, start, end), ...]}"""
    g, fwd, bwd = _fb or _forward_backward(text)
    best = bwd[0]
    out: dict[int, list] = {}
    for s in range(len(text)):
        if fwd[s] == -math.inf:
            continue
        for e in g[s]:
            sc = fwd[s] + logp(text[s:e]) + bwd[e] - best
            if sc >= -margin:
                for i in range(s, e):
                    out.setdefault(i, []).append((sc, s, e))
    for i in out:
        out[i].sort(reverse=True)
    return out


def word_reading(word: str, k: int) -> tuple[str, str] | None:
    """Dictionary reading of word[k] -> (syllable, strength 'P'|'J'), or None when unknown."""
    d, _ = words()
    rec = d.get(word)
    if not rec or not rec[2] or len(rec[2]) != len(word):
        return None
    return rec[2][k], rec[1]
