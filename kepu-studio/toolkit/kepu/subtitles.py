"""中文字幕切分与 .srt 导出（来源：《ETH》engine/subtitles.py，审片 av_a §3.2 定下的规则；词边界改用 kepu 自带的词表，
不再依赖 jieba）。

规则：只在标点处，或词边界上两个汉字之间切；不在引号、括号、{…}、公式或拉丁词串内部切；左引号、左括号跟后文，
右引号、右括号跟前文；行尾不落在“和 在 的 把 个 都……”上，行首不落在单独成词的“的 了 着……”上；不留只有标点的行；
不足 1.2 秒的行并入相邻行；每行宽度上限 22 个汉字（拉丁字母和数字按 0.55 计）。ETH 6 期实测：碎片 91 → 0，
拆开的引号 70 → 0，切进词内 6 → 0。
"""
from __future__ import annotations

import re

from . import seg

MAX_CHARS = 22
MIN_DUR = 1.2
MIN_VIS = 4
HARD_END = set("。！？!?")
SOFT = set("，；：、")
OPEN = "“‘「『《（([【"
CLOSE = "”’」』》）)]】"
PAIRS = dict(zip(OPEN, CLOSE))
SILENT = set("，。；：、！？!?…“”‘’「」『』《》（）()[]【】—·,.:; ")
FUNC_END = set("和与及跟同或在的把被对从向给让将而并且得地着个种条张位次些块份每这那下都就也还才又")
BAD_START = set("的了着过们地得吗呢吧啊么")
GOOD_START = set("也都就还却但才又并而")
_MATH_EXTRA = set("²³¹⁰⁴⁵⁶⁷⁸⁹ⁿᶜʲᵏⁱ₀₁₂₃₄₅₆₇₈₉ₐᵢₜᵥ′'’√+−-–×·^_={}|<>≤≥≠/().,!∨∧¬∑∏∞≈∈∉⊆#%")
_GREEK = set("αβγδεζηθικλμνξοπρστυφχψωΓΔΘΛΞΠΣΦΨΩ")


def is_cjk(c: str) -> bool:
    o = ord(c)
    return 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF


def is_math(c: str) -> bool:
    return (c.isascii() and (c.isalnum() or c in " +-=/^_{}()[].,'|<>!#%")) or c in _MATH_EXTRA or c in _GREEK


def vis(s: str) -> float:
    return sum(1.0 if (is_cjk(c) or ord(c) > 0x2E80) else 0.55 for c in s)


def tokenize(text: str, extra: tuple = ()) -> list[tuple[str, int, int]]:
    out, pos = [], 0
    for w in seg.cut(text):
        out.append((w, pos, pos + len(w)))
        pos += len(w)
    for w in extra:                                    # project words that must never be split
        i = text.find(w)
        while i >= 0:
            out.append((w, i, i + len(w)))
            i = text.find(w, i + 1)
    return out


def _forbidden(text: str, toks) -> list[bool]:
    n = len(text)
    forbid = [False] * (n + 1)
    forbid[0] = forbid[n] = True
    depth = 0
    for i, c in enumerate(text):
        if c == "{":
            depth += 1
        elif c == "}":
            depth = max(0, depth - 1)
        if depth > 0:
            forbid[i + 1] = True
    stack = []
    for i, c in enumerate(text):
        if c in PAIRS:
            stack.append((c, i))
        elif c in CLOSE and stack:
            _, j = stack.pop()
            span = text[j:i + 1]
            for k in range(j + 1, i + 1):
                if vis(span) <= MAX_CHARS + 4 or text[k - 1] not in SOFT:
                    forbid[k] = True
    for i, c in enumerate(text):
        if c in OPEN:
            forbid[i + 1] = True
        if c in CLOSE or c in SOFT or c in HARD_END or c == "…":
            forbid[i] = True
    for i in range(1, n):
        a, b = text[i - 1], text[i]
        if a in SOFT or a in HARD_END or (a in CLOSE and not a.isascii()):
            continue
        if is_math(a) or is_math(b):
            forbid[i] = True
    for _, s, e in toks:
        for k in range(s + 1, e):
            forbid[k] = True
    return forbid


def _cut_cost(text: str, i: int, single: set) -> float:
    a, b = text[i - 1], text[i] if i < len(text) else ""
    bad_start = 14.0 if (b in BAD_START and i in single) else 0.0
    func_end = 10.0 if a in FUNC_END else 0.0
    if a in HARD_END:
        return 0.0
    if a in SOFT:
        return 0.5
    if a in CLOSE:
        return (0.5 if (not b or not is_cjk(b)) else 8.0) + bad_start
    if a == "…":
        return 3.0
    if b in OPEN and is_cjk(a):
        return 10.0 + func_end
    c = 12.0 + func_end + bad_start
    if b in GOOD_START:
        c -= 3.0
    return c


def split_phrases(text: str, times: list, duration: float, max_chars: float = MAX_CHARS, min_dur: float = MIN_DUR,
                  extra_words: tuple = ()):
    """One beat's display text -> subtitle lines [[t0, t1, line], ...]; times = start time of each display char."""
    n = len(text)
    if n == 0:
        return []
    times = list(times) + [duration] * max(0, n - len(times))
    toks = tokenize(text, extra_words)
    forbid = _forbidden(text, toks)
    single = {s for w, s, e in toks if e - s == 1}
    cuts = [i for i in range(1, n) if not forbid[i]]
    nodes = [0] + cuts + [n]
    nxt = [n] * (n + 1)
    j = n
    for i in range(n - 1, -1, -1):
        if text[i] not in SILENT:
            j = i
        nxt[i] = j

    def t_at(pos):
        k = nxt[pos] if pos < n else n
        return duration if k >= n else times[k]

    def line_cost(a, b):
        core = text[a:b].strip().rstrip("，。；：、,;:")
        if not any(c not in SILENT for c in core):
            return 1e6
        w = vis(core)
        cost = 0.0
        if w > max_chars:
            over = w - max_chars
            cost += 12.0 * min(over, 3.0) + 400.0 * max(0.0, over - 3.0)
        ends = sum(1 for k in range(a, b - 1) if text[k] in HARD_END)
        cost += 30.0 * ends
        if ends and w > max_chars * 0.8:
            cost += 50.0
        dur = t_at(b) - t_at(a) if b < n else duration - t_at(a)
        if dur < min_dur:
            cost += 60.0 * (min_dur - dur) + 25.0
        if w < MIN_VIS:
            cost += 30.0
        cost += 0.03 * (max_chars - min(w, max_chars)) ** 2
        return cost

    INF = float("inf")
    best = {0: (0.0, None)}
    for bi, b in enumerate(nodes[1:], 1):
        cand = (INF, None)
        for a in nodes[:bi]:
            if a not in best:
                continue
            if vis(text[a:b]) > max_chars * 2.2 and a != nodes[bi - 1]:
                continue
            c = best[a][0] + line_cost(a, b) + (0.0 if b == n else _cut_cost(text, b, single))
            if c < cand[0]:
                cand = (c, a)
        best[b] = cand
    spans, b = [], n
    while b:
        a = best[b][1]
        spans.append((a, b))
        b = a
    spans.reverse()
    out = []
    for k, (a, b) in enumerate(spans):
        segm = text[a:b].strip().rstrip("，。；：、,;:")
        if not segm:
            continue
        t0 = t_at(a)
        t1 = t_at(spans[k + 1][0]) if k + 1 < len(spans) else duration
        out.append([t0, max(t1, t0 + 0.3), segm])
    if out:
        out[0][0] = 0.0
    return out


_SUP = dict(zip("0123456789+-−=()niktjcxyabm", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻⁼⁽⁾ⁿⁱᵏᵗʲᶜˣʸᵃᵇᵐ"))
_SUB = dict(zip("0123456789+-−=()aeioxjkmnpstuv", "₀₁₂₃₄₅₆₇₈₉₊₋₋₌₍₎ₐₑᵢₒₓⱼₖₘₙₚₛₜᵤᵥ"))


def _script(body: str, table: dict, mark: str) -> str:
    if body and all(c in table for c in body):
        return "".join(table[c] for c in body)
    return f"{mark}({body})" if len(body) > 1 else f"{mark}{body}"


def srt_text(s: str) -> str:
    """2^{o(n)} -> 2^(o(n)), 2^n -> 2ⁿ, x_{12} -> x₁₂, no braces."""
    s = re.sub(r"\^\{([^{}]*)\}", lambda m: _script(m.group(1), _SUP, "^"), s)
    s = re.sub(r"\^([A-Za-z0-9])", lambda m: _script(m.group(1), _SUP, "^"), s)
    s = re.sub(r"_\{([^{}]*)\}", lambda m: _script(m.group(1), _SUB, "_"), s)
    s = re.sub(r"(?<=[A-Za-z])_([A-Za-z0-9])", lambda m: _script(m.group(1), _SUB, "_"), s)
    return s.replace("{", "").replace("}", "")


def fmt_srt_time(t: float) -> str:
    ms = int(round(max(0.0, t) * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(lines: list, path) -> None:
    """lines: [[t0, t1, text]] on the episode timeline."""
    out = []
    for k, (t0, t1, s) in enumerate(lines, 1):
        out.append(f"{k}\n{fmt_srt_time(t0)} --> {fmt_srt_time(t1)}\n{srt_text(s)}\n")
    open(path, "w", encoding="utf-8").write("\n".join(out))
