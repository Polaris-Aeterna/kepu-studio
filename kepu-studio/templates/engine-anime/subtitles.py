"""
Subtitle segmentation + plain-text export (no ManimGL dependency; unit-tested in engine/tests/).

    from subtitles import split_phrases, srt_text
    phrases = split_phrases(text, char_times, duration)     # [[t0, t1, "显示文本"], ...]

Rules (engine README §10; review/av_a/SUMMARY.md §3.2):
  - cut only at punctuation, or between two CJK characters at a jieba word boundary (never inside a word:
    技术、共享、多项式…);
  - never inside quotes / brackets / {…} / a formula or Latin run, never between a Latin word and the Chinese
    next to it (Stephen|Cook, Anthropic|的);
  - an opening quote or bracket stays with what follows, a closing one with what precedes;
  - a line does not end on a function word (和 在 的 把 …);
  - no line made only of punctuation or ellipses; lines shorter than MIN_DUR seconds are merged;
  - at most MAX_CHARS (CJK = 1, Latin/digits = 0.55) per line unless an unbreakable span is longer.
Only the segmentation changes: text, audio and timing are untouched (each line starts when its first spoken
character starts, exactly as before).
"""
from __future__ import annotations

import logging
import re

MAX_CHARS = 22          # visual width of one subtitle line (CJK characters)
MIN_DUR = 1.2           # seconds: shorter lines are merged with a neighbour
MIN_VIS = 4             # visual width below which a line is a fragment

HARD_END = set("。！？!?")
SOFT = set("，；：、")
OPEN = "“‘「『《（([【"
CLOSE = "”’」』》）)]】"
PAIRS = dict(zip(OPEN, CLOSE))
SILENT = set("，。；：、！？!?…“”‘’「」『』《》（）()[]【】—·,.:; ")
FUNC_END = set("和与及跟同或在的把被对从向给让将而并且得地着个种条张位次些块份每这那下都就也还才又")   # a line should not end on these
BAD_START = set("的了着过们地得吗呢吧啊么")                                 # …nor start on these
GOOD_START = set("也都就还却但才又并而")                        # a line may start on these
# glyphs that belong to formulas / Latin text (a cut never falls between two of them)
_MATH_EXTRA = set("²³¹⁰⁴⁵⁶⁷⁸⁹ⁿᶜʲᵏⁱ₀₁₂₃₄₅₆₇₈₉ₐᵢₜᵥ′'’√+−-–×·^_={}|<>≤≥≠/().,!∨∧¬∑∏∞≈∈∉⊆#%")
_GREEK = set("αβγδεζηθικλμνξοπρστυφχψωΓΔΘΛΞΠΣΦΨΩ")

_JIEBA = None
PROJECT_WORDS = ["多项式", "子句", "子句图", "满足赋值", "扩张图", "亚指数", "稀疏化", "判定线", "八平方恒等式",
                 "线性摘要", "共享线性摘要", "技术概览", "合取范式", "布尔变量", "真值表", "读写头", "证明助手",
                 "插值", "低次多项式", "张量网络", "交换矩阵", "单位矩阵", "对角线", "指数时间假说", "细粒度"]


def _jieba():
    global _JIEBA
    if _JIEBA is None:
        import jieba
        jieba.setLogLevel(logging.WARNING)
        for w in PROJECT_WORDS:
            jieba.add_word(w, freq=200000)
        _JIEBA = jieba
    return _JIEBA


def is_cjk(c: str) -> bool:
    o = ord(c)
    return 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF


def is_math(c: str) -> bool:
    return (c.isascii() and (c.isalnum() or c in " +-=/^_{}()[].,'|<>!#%")) or c in _MATH_EXTRA or c in _GREEK


def vis(s: str) -> float:
    return sum(1.0 if (is_cjk(c) or ord(c) > 0x2E80) else 0.55 for c in s)


def _forbidden(text: str) -> list[bool]:
    """forbid[i] = True if a cut between text[i-1] and text[i] is not allowed."""
    n = len(text)
    forbid = [False] * (n + 1)
    forbid[0] = forbid[n] = True
    # inside {…}
    depth = 0
    for i, c in enumerate(text):
        if c == "{":
            depth += 1
        elif c == "}":
            depth = max(0, depth - 1)
        if depth > 0:
            forbid[i + 1] = True
    # inside quotes / brackets (only punctuation-free cuts are blocked; long quotes may still cut at punctuation)
    stack = []
    for i, c in enumerate(text):
        if c in PAIRS:
            stack.append((c, i))
        elif c in CLOSE and stack:
            o, j = stack.pop()
            span = text[j:i + 1]
            for k in range(j + 1, i + 1):
                if vis(span) <= MAX_CHARS + 4 or text[k - 1] not in SOFT:
                    forbid[k] = True
        elif c == "”" and not stack:
            pass
    # opening marks stay with what follows, closing marks with what precedes
    for i, c in enumerate(text):
        if c in OPEN:
            forbid[i + 1] = True
        if c in CLOSE or c in SOFT or c in HARD_END or c == "…":
            forbid[i] = True
    # Latin / formula runs, and their joints with neighbouring CJK characters
    for i in range(1, n):
        a, b = text[i - 1], text[i]
        if a in SOFT or a in HARD_END or (a in CLOSE and not a.isascii()):
            continue
        if is_math(a) or is_math(b):
            forbid[i] = True
    # inside jieba words
    for w, s, e in _jieba().tokenize(text):
        for k in range(s + 1, e):
            forbid[k] = True
    return forbid


def _cut_cost(text: str, i: int, single: set) -> float:
    """cost of cutting between text[i-1] and text[i] (assumed allowed).  `single` = start indices of
    one-character jieba tokens (a particle like 的/了 starts a line only if it stands alone)."""
    a, b = text[i - 1], text[i] if i < len(text) else ""
    bad_start = 14.0 if (b in BAD_START and i in single) else 0.0
    func_end = 10.0 if a in FUNC_END else 0.0
    if a in HARD_END:
        return 0.0
    if a in SOFT:
        return 0.5
    if a in CLOSE:
        return (0.5 if (not b or not is_cjk(b)) else 8.0) + bad_start   # （Cook–Levin）定理 stays together
    if a == "…":
        return 3.0
    if b in OPEN and is_cjk(a):
        return 10.0 + func_end                                # 库克–列文（Cook–Levin）: keep the gloss attached
    c = 12.0 + func_end + bad_start                           # a cut between two words, not at punctuation
    if b in GOOD_START:
        c -= 3.0
    return c


def split_phrases(text: str, times: list[float], duration: float, max_chars: float = MAX_CHARS,
                  min_dur: float = MIN_DUR):
    """Split one beat's display text into subtitle lines [[t0, t1, line], ...] (see module docstring)."""
    n = len(text)
    if n == 0:
        return []
    times = list(times) + [duration] * max(0, n - len(times))
    forbid = _forbidden(text)
    single = {st for w, st, e in _jieba().tokenize(text) if e - st == 1}
    cuts = [i for i in range(1, n) if not forbid[i]]
    nodes = [0] + cuts + [n]

    spoken = [i for i, c in enumerate(text) if c not in SILENT]
    nxt_spoken = [n] * (n + 1)
    j = n
    for i in range(n - 1, -1, -1):
        if text[i] not in SILENT:
            j = i
        nxt_spoken[i] = j

    def t_at(pos):
        k = nxt_spoken[pos] if pos < n else n
        return duration if k >= n else times[k]

    def line_cost(a, b):
        seg = text[a:b]
        core = seg.strip().rstrip("，。；：、,;:")
        if not any(c not in SILENT for c in core):
            return 1e6                                   # only punctuation / ellipsis
        w = vis(core)
        cost = 0.0
        if w > max_chars:                                 # a little over is tolerable, a lot only when forced
            over = w - max_chars
            cost += 12.0 * min(over, 3.0) + 400.0 * max(0.0, over - 3.0)
        ends = sum(1 for k in range(a, b - 1) if text[k] in HARD_END)
        cost += 30.0 * ends                              # merging across a sentence end
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
                continue                                  # prune very long lines (unless forced)
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
        seg = text[a:b].strip().rstrip("，。；：、,;:")
        if not seg:
            continue
        t0 = t_at(a)
        t1 = t_at(spans[k + 1][0]) if k + 1 < len(spans) else duration
        out.append([t0, max(t1, t0 + 0.3), seg])
    if out:
        out[0][0] = 0.0
    return out


# ---------------------------------------------------------------- plain text for .srt
_SUP = dict(zip("0123456789+-−=()niktjcxyabm", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁻⁼⁽⁾ⁿⁱᵏᵗʲᶜˣʸᵃᵇᵐ"))
_SUB = dict(zip("0123456789+-−=()aeioxjkmnpstuv", "₀₁₂₃₄₅₆₇₈₉₊₋₋₌₍₎ₐₑᵢₒₓⱼₖₘₙₚₛₜᵤᵥ"))


def _script(body: str, table: dict, mark: str) -> str:
    if body and all(c in table for c in body):
        return "".join(table[c] for c in body)
    return f"{mark}({body})" if len(body) > 1 else f"{mark}{body}"


def srt_text(s: str) -> str:
    """Display text -> readable plain text for .srt: 2^{o(n)} -> 2^(o(n)), 2^n -> 2ⁿ, x_{12} -> x₁₂, no braces."""
    s = re.sub(r"\^\{([^{}]*)\}", lambda m: _script(m.group(1), _SUP, "^"), s)
    s = re.sub(r"\^([A-Za-z0-9])", lambda m: _script(m.group(1), _SUP, "^"), s)
    s = re.sub(r"_\{([^{}]*)\}", lambda m: _script(m.group(1), _SUB, "_"), s)
    s = re.sub(r"(?<=[A-Za-z])_([A-Za-z0-9])", lambda m: _script(m.group(1), _SUB, "_"), s)
    return s.replace("{", "").replace("}", "")
