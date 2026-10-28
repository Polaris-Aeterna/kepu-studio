"""Small shared helpers: paths, tone marks, display width, TSV reading."""
from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

PKG = Path(__file__).resolve().parent
DATA = PKG / "data"
ASSETS = PKG / "assets"
USER_DIR = Path(os.environ.get("KEPU_HOME", Path.home() / ".kepu"))

_TONES = {"a": "āáǎà", "e": "ēéěè", "i": "īíǐì", "o": "ōóǒò", "u": "ūúǔù", "ü": "ǖǘǚǜ"}
_TONED = {c: (base, k + 1) for base, cs in _TONES.items() for k, c in enumerate(cs)}
HAN = re.compile(r"[㐀-鿿豈-﫿]")


def is_han(ch: str) -> bool:
    return bool(HAN.match(ch))


def tone_mark(reading: str) -> str:
    """shu4 -> shù, lv4 -> lǜ, de5 -> de; already tone-marked readings are returned as they are."""
    r = reading.strip().lower().replace("u:", "ü").replace("v", "ü")
    if not r or not r[-1:].isdigit():
        return r
    s, t = r[:-1], int(r[-1])
    if t not in (1, 2, 3, 4):
        return s
    k = next((s.index(v) for v in "ae" if v in s), s.find("ou") if "ou" in s else -1)
    if k < 0:
        k = max((j for j, c in enumerate(s) if c in _TONES), default=-1)
    return s if k < 0 else s[:k] + _TONES[s[k]][t - 1] + s[k + 1:]


def tone_number(reading: str) -> str:
    """shù -> shu4, lǜ -> lv4, de -> de5 (for engines that take numbered pinyin)."""
    out, tone = [], 5
    for c in reading:
        if c in _TONED:
            base, tone = _TONED[c]
            out.append(base)
        else:
            out.append(c)
    return "".join(out).replace("ü", "v") + str(tone)


def has_tone_mark(s: str) -> bool:
    return any(c in _TONED for c in s)


def width(s: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)


def pad(s: str, w: int) -> str:
    return s + " " * max(0, w - width(s))


def read_tsv(path: Path) -> list[list[str]]:
    """Rows of a tab-separated file; '#' comment lines and blank lines are skipped."""
    if not path.exists():
        return []
    rows = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip() and not ln.lstrip().startswith("#"):
            rows.append(ln.split("\t"))
    return rows


def find_project_root(start: Path | None = None) -> Path | None:
    """The nearest folder (start or a parent) that holds kepu.toml."""
    p = (start or Path.cwd()).resolve()
    for q in [p, *p.parents]:
        if (q / "kepu.toml").exists():
            return q
    return None
