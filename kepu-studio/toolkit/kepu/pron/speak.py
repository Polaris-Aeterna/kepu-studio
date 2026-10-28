"""念的一侧 → 发给 TTS 的文字。多音字换替身字、希腊字母和符号换成读法；记下每个字符在 TTS 文字里的位置（spans），
合成后用逐字时间戳映射回字幕原字；记下所有值得人耳抽查的地方（records，给耳检包用）。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from ..util import is_han
from .greek import greek_say, greek_table, load_profile, symbol_table
from .lexicon import Lexicon
from .marks import parse_marks
from .resolve import Spot, resolve

SUPSUB = re.compile(r"[⁰¹²³⁴-⁹ⁿⁱʲᵏᶜᵗˣʸᵃᵇᵐ⁺⁻₊₋ₐ-ₜ]")
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z'’\-]*")
DIGIT = re.compile(r"\d")
AUTO_EAR_FREQ = 3000          # dictionary words rarer than this (jieba frequency) go into the ear check


@dataclass
class PronConfig:
    project_root: Path | None = None
    greek: str = "en"            # en | zh
    strict: bool = False         # readings without a stand-in are held instead of sent as pinyin
    digits: str = "warn"         # warn | hold | ok
    margin: float = 3.0
    voice_key: str | None = None


@dataclass
class Prepared:
    raw: str
    clean: str
    marks: dict
    tts: str
    spans: list                  # [(char of clean, start, end in tts)]
    spots: list                  # [Spot]
    held: list = field(default_factory=list)       # [(context, reason)] spoken-side problems
    notes: list = field(default_factory=list)
    records: list = field(default_factory=list)    # ear-check candidates

    @property
    def open(self) -> list:
        return [s for s in self.spots if s.open]

    @property
    def blocked(self) -> bool:
        return bool(self.open or self.held)


@lru_cache(maxsize=8)
def _lexicon(root: str | None) -> Lexicon:
    return Lexicon(Path(root) if root else None)


def lexicon_for(cfg: PronConfig) -> Lexicon:
    return _lexicon(str(cfg.project_root) if cfg.project_root else None)


def reload_lexicon():
    _lexicon.cache_clear()


def prepare(spoken: str, cfg: PronConfig | None = None) -> Prepared:
    """spoken side of one beat (marks allowed) -> Prepared."""
    cfg = cfg or PronConfig()
    clean, marks = parse_marks(spoken)
    prof = load_profile(cfg.voice_key, cfg.project_root)
    spots = resolve(clean, marks, lexicon_for(cfg), strict=cfg.strict, margin=cfg.margin,
                    bad_standins=frozenset(prof.get("standins_bad", [])))
    by_i = {s.i: s for s in spots}
    say_map, hold_map = symbol_table()
    greek = greek_table()
    out, spans, records, held, notes = [], [], [], [], []
    pos = 0
    for i, ch in enumerate(clean):
        sp = by_i.get(i)
        say = ch
        if sp is not None and sp.action == "force":
            say = sp.say
            ok = sp.say in prof.get("standins_ok", []) or sp.say in prof.get("pinyin_ok", [])
            if sp.status == "pinyin" and not ok:
                records.append(_rec(clean, i, "pinyin", sp.reading, say, "没有替身字，送带调号拼音"))
            elif sp.standin_status == "new" and not ok:
                records.append(_rec(clean, i, "standin", sp.reading, say, "新替身字，第一次使用"))
        elif sp is not None and sp.status == "auto" and sp.freq < AUTO_EAR_FREQ:
            records.append(_rec(clean, i, "auto", sp.reading, ch, f"低频词“{sp.word}”，词典读 {sp.reading}，没有强制"))
        elif ch in greek:
            g = greek_say(ch, cfg.greek, prof)
            say = g[0]
            if LATIN_WORD.fullmatch(say) or (say and say[0].isascii() and say[0].isalpha()):
                left = clean[i - 1] if i else ""
                right = clean[i + 1] if i + 1 < len(clean) else ""
                say = (" " if left and (is_han(left) or left.isalnum()) else "") + say + \
                      (" " if right and (is_han(right) or right.isalnum()) else "")
            if g[1] in ("new",):
                records.append(_rec(clean, i, "greek", greek[ch]["name"], say.strip(), "希腊字母读法还没在这个音色上验证"))
            elif greek[ch].get("watch"):
                records.append({**_rec(clean, i, "greek", greek[ch]["name"], say.strip(), greek[ch]["watch"]), "watch": True})
        elif ch in say_map:
            say = say_map[ch]
        elif ch in hold_map:
            held.append((_ctx(clean, i), f"符号“{ch}”：{hold_map[ch]}"))
        elif SUPSUB.match(ch):
            held.append((_ctx(clean, i), f"上下标“{ch}”：放进 {{显示|读法}}"))
        spans.append((ch, pos, pos + len(say)))
        out.append(say)
        pos += len(say)
    tts = "".join(out)
    if DIGIT.search(clean):
        ds = sorted({m.group(0) for m in re.finditer(r"[\d.,/:%]+", clean)})
        msg = f"读法里有阿拉伯数字 {'、'.join(ds[:6])}{'…' if len(ds) > 6 else ''}：模型可能按位念或按数值念，最好写进 {{显示|读法}}"
        if cfg.digits == "hold":
            held.append(("", msg))
        elif cfg.digits == "warn":
            notes.append(msg)
            m = DIGIT.search(clean)
            records.append(_rec(clean, m.start(), "number", "", "", "数字的念法"))
    for m in LATIN_WORD.finditer(clean):
        w = m.group(0)
        if len(w) >= 2 and w.isupper():
            records.append(_rec(clean, m.start(), "latin", w, w, "缩写：逐字母念还是当单词念？"))
    return Prepared(spoken, clean, marks, tts, spans, spots, held, notes, records)


def _ctx(text: str, i: int) -> str:
    return text[max(0, i - 8):i] + "【" + text[i] + "】" + text[i + 1:i + 7]


def _rec(text, i, kind, reading, say, why):
    return {"i": i, "kind": kind, "char": text[i] if i < len(text) else "", "reading": reading, "say": say,
            "why": why, "ctx": _ctx(text, i) if i < len(text) else ""}


def describe(s: Spot) -> str:
    """One line for a report."""
    from ..util import pad
    src = {"mark": "标记", "lexicon": "词典", "rule": "规则", "dict": "通用词典", "default": "默认"}.get(s.source, "")
    if s.status in ("ok", "auto", "pinyin"):
        how = f"{s.reading}（{s.say}）" if s.action == "force" else f"{s.reading}（不换字）"
        head = {"ok": "✓", "auto": "◇ 自动", "pinyin": "~ 拼音"}[s.status]
        tail = s.why if s.source == "dict" else f"{src} {s.entry or s.why}".strip()
        return f"{pad(head, 8)}{pad(s.ctx, 34)}{pad(how, 16)}{tail}"
    head = "✗ 标错" if s.status == "bad_mark" else "✗ 未定"
    opts = "、".join(f"{s.char}〔{r}〕" for r in s.suggest if r)
    rw = f"；改写：{s.rewrite}" if s.rewrite else ""
    return f"{pad(head, 8)}{pad(s.ctx, 34)}{s.why}；标 {opts}{rw}"
