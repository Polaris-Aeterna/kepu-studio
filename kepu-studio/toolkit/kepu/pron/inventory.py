"""Polyphone inventory (data/polyphones.tsv), stand-in characters (data/standins.tsv), single-character readings."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from ..util import DATA, read_tsv


@dataclass(frozen=True)
class Poly:
    char: str
    default: str
    tier: str            # "A" | "B"
    force_default: bool
    note: str


@lru_cache(maxsize=1)
def polyphones() -> dict[str, Poly]:
    out = {}
    for row in read_tsv(DATA / "polyphones.tsv"):
        ch, default, tier, fd = row[:4]
        out[ch] = Poly(ch, default, tier, fd.strip() == "1", row[4] if len(row) > 4 else "")
    return out


@lru_cache(maxsize=1)
def standins() -> dict[str, list[tuple[str, str]]]:
    """reading -> [(char, status)] in order of preference; status 'field' (verified in production) or 'new'."""
    out: dict[str, list] = {}
    for row in read_tsv(DATA / "standins.tsv"):
        reading, chars, status = row[0], row[1], (row[2] if len(row) > 2 else "new")
        out.setdefault(reading, []).extend((c, status) for c in chars)
    return out


@lru_cache(maxsize=1)
def char_readings() -> dict[str, list[str]]:
    return {r[0]: [x for x in r[1].split(",") if x] for r in read_tsv(DATA / "char_readings.tsv") if len(r) > 1}


def readings_of(ch: str) -> list[str]:
    rs = char_readings().get(ch)
    if rs:
        return rs
    p = polyphones().get(ch)
    return [p.default] if p else []


def stand_in(reading: str, bad: frozenset = frozenset()) -> tuple[str, str] | None:
    """Best stand-in (char, status) for a reading, skipping characters the ear check rejected for this voice."""
    for c, status in standins().get(reading, []):
        if c not in bad:
            return c, status
    return None


def standin_reading() -> dict[str, str]:
    """stand-in char -> the reading it stands for (to show what a decision sounds like)."""
    return {c: r for r, cs in standins().items() for c, _ in cs}
