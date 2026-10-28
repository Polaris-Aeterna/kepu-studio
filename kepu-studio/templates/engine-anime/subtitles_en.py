"""
English closed captions (README §11.4): one beat's display text + per-character times -> caption cues.
No ManimGL dependency; unit-tested in engine/tests/test_subtitles_en.py.

    from subtitles_en import split_cues
    cues = split_cues(text, char_times, duration)        # [[t0, t1, "line one\\nline two"], ...]

Rules (common broadcast / YouTube caption practice):
  - at most 2 lines of at most MAX_LINE (42) characters; a cue never splits a {…} span or a word;
  - cue boundaries prefer, in order: sentence end > ; : — > comma > before a conjunction / relative word /
    preposition > any other word gap; never right after an article, a preposition or an auxiliary
    ("the | proof", "of | ETH") unless nothing else fits;
  - each cue lasts MIN_DUR..MAX_DUR seconds (1–7 s) where the speech allows; reading speed is kept under
    MAX_CPS characters per second when possible;
  - no orphans: no cue and no line of a single word when a neighbour can take it; a new sentence does not
    start with a one- or two-word tail at the end of a cue;
  - line breaks inside a cue follow the same preferences and keep the two lines roughly balanced.
Timing: a cue starts when its first spoken word starts (the display->audio map from tts.py), and ends when the
next cue starts, but never more than MAX_DUR after its own start; the first cue of a beat starts at 0.
"""
from __future__ import annotations

import re

MAX_LINE = 42
MAX_LINES = 2
MIN_DUR = 1.0
MAX_DUR = 7.0
MAX_CPS = 20.0

SENT_END = (".", "?", "!", ".”", "?”", "!”", ".\"", "?\"", "!\"", ".)", "…")
STRONG = (";", ":", "—", ";”", ":”")
# a line / cue should not END on these (they bind to the next word)
BIND_NEXT = set("""a an the of to in on at by for from with into onto as than and or but nor if that which who
whom whose where when while because so not no is are was were be been being am has have had do does did can
could will would shall should may might must its their his her our your my this these those every each some
any both either neither very more most less least such just only also even never still already always really
actually exactly almost about nearly""".split())
# a line / cue may comfortably START on these
GOOD_START = set("""and but or so because which who that where when while if then although though whereas
since unless until after before to of in on for with from by as than""".split())
ADJ_END = ("ic", "al", "ous", "ive", "ful", "less", "able", "ible", "ary", "ian", "ean", "est", "er")
_SILENT = set(" \"'“”‘’()[]{},.;:!?…—–-")


def _tokens(text: str):
    """Words as (start, end) offsets; spaces inside {…} do not split a token."""
    out, depth, start = [], 0, None
    for i, c in enumerate(text):
        if c == "{":
            depth += 1
        elif c == "}":
            depth = max(0, depth - 1)
        if c.isspace() and depth == 0:
            if start is not None:
                out.append((start, i))
                start = None
        elif start is None:
            start = i
    if start is not None:
        out.append((start, len(text)))
    return out


def _plain(word: str) -> str:
    return word.strip("\"'“”‘’()[],.;:!?…").lower()


def _visible(s: str) -> str:
    from subtitles import srt_text
    return srt_text(s)


def quoted_gaps(words: list[str]) -> list[bool]:
    """q[k] = the gap before words[k] lies inside an open quote or bracket."""
    q, depth, dq = [False] * (len(words) + 1), 0, False
    for k, w in enumerate(words):
        q[k] = depth > 0 or dq
        for c in w:
            if c in "“(":
                depth += 1
            elif c in "”)":
                depth = max(0, depth - 1)
            elif c == '"':
                dq = not dq
    return q


def gap_cost(words: list[str], k: int, quoted: bool = False) -> float:
    """Cost of breaking (a cue or a line) between words[k-1] and words[k]."""
    a, b = words[k - 1], words[k]
    if k + 1 < len(words) and b.endswith((",", ";", ":", ".")) and not a.endswith((",", ";", ":", ".", "?", "!")):
        return 16.0                                   # "...four literals | each," leaves a one-word clause tail
    if quoted:
        return 15.0 + (0.0 if a.endswith(SENT_END + (",", ";", ":")) else 10.0)
    if a.endswith(SENT_END):
        return 0.0
    if a.endswith(STRONG) or b in ("—", "–"):
        return 1.0
    if a.endswith((",", ",”", ",\"")):
        return 2.0
    if _plain(a) in BIND_NEXT:
        return 25.0
    if a[:1].isupper() and b[:1].isupper():
        return 20.0                                   # inside a name: Exponential | Time Hypothesis
    if a.isalpha() and (a.endswith(ADJ_END) or a == "Boolean") and b[:1].islower() and _plain(b) not in GOOD_START:
        return 15.0                                   # algebraic | identity, Boolean | variable
    if a.startswith(("(", "“", "\"")) and not a.endswith((")", "”", "\"")):
        return 15.0                                   # inside a short quote / bracket
    if _plain(b) in GOOD_START:
        return 5.0
    if any(c.isdigit() for c in a) and b[:1].islower():
        return 18.0                                   # 2⁶³ | grains: keep a number with its noun
    if b[:1].isdigit() or a[:1].isdigit():
        return 12.0
    return 9.0


def _sent_ends(words: list[str], i: int, j: int) -> list[int]:
    return [k for k in range(i, j - 1) if words[k].endswith(SENT_END)]


def _strong_ends(words: list[str], i: int, j: int) -> list[int]:
    return [k for k in range(i, j - 1) if words[k].endswith(STRONG)]


def wrap(words: list[str], max_line: int = MAX_LINE, quoted=None) -> tuple[list[str], float, int]:
    """Best 1- or 2-line layout of a cue -> (lines, cost, words on line 1); cost >= 1e5 if it doesn't fit."""
    quoted = quoted or quoted_gaps(words)
    one = " ".join(words)
    if len(_visible(one)) <= max_line:
        return [one], 0.0, len(words)
    best = ([one], 1e6, len(words))
    for k in range(1, len(words)):
        l1, l2 = " ".join(words[:k]), " ".join(words[k:])
        n1, n2 = len(_visible(l1)), len(_visible(l2))
        if n1 > max_line or n2 > max_line:
            continue
        c = gap_cost(words, k, quoted[k]) + 0.15 * abs(n1 - n2)
        if k == 1 or k == len(words) - 1:
            c += 30.0                                 # a one-word line
        if c < best[1]:
            best = ([l1, l2], c, k)
    return best


def split_cues(text: str, times: list[float], duration: float, max_line: int = MAX_LINE,
               min_dur: float = MIN_DUR, max_dur: float = MAX_DUR, max_cps: float = MAX_CPS):
    """Split one beat's display text into caption cues [[t0, t1, text_with_newline], ...]."""
    toks = _tokens(text)
    if not toks:
        return []
    n = len(toks)
    words = [text[a:b] for a, b in toks]
    times = list(times) + [duration] * max(0, len(text) - len(times))

    def start(k):                                   # spoken start of word k (first non-silent char)
        if k >= n:
            return duration
        a, b = toks[k]
        for p in range(a, b):
            if text[p] not in _SILENT:
                return times[p]
        return times[a]

    st = [start(k) for k in range(n)] + [duration]
    q = quoted_gaps(words)
    lay = {}

    def cue_cost(i, j):
        if (i, j) not in lay:
            lay[(i, j)] = wrap(words[i:j], max_line, q[i:j + 1])
        lines, lc, k1 = lay[(i, j)]
        if lc >= 1e5:
            return 1e9
        nchar = len(_visible(" ".join(words[i:j])))
        dur = st[j] - st[i]
        c = lc
        if j - i == 1 and n > 1:
            c += 40.0                                 # single-word cue
        elif j - i == 2 and n > 2:
            c += 8.0
        if dur < min_dur:
            c += 30.0 + 40.0 * (min_dur - dur)
        if dur > max_dur:
            c += 10.0 * (dur - max_dur)
        cps = nchar / max(dur, 0.3)
        if cps > max_cps:
            c += 2.0 * (cps - max_cps)
        ends = _sent_ends(words, i, j)
        if ends:
            c += 3.0 * len(ends)
            c += 10.0 * sum(1 for e in ends if e != i + k1 - 1)   # a sentence ending in the middle of a line
            tail = j - 1 - ends[-1]                   # words of the next sentence carried in this cue
            if tail <= 3:
                c += 18.0
            head = ends[0] + 1 - i                    # words that close the previous sentence
            if head <= 2:
                c += 6.0
        strong = _strong_ends(words, i, j)
        if strong and j - 1 - strong[-1] <= 3 and not words[j - 1].endswith(SENT_END + STRONG + (",",)):
            c += 10.0                                 # "…unexpected places: an algebraic" (a dangling tail)
        whole = (i == 0 or words[i - 1].endswith(SENT_END)) and words[j - 1].endswith(SENT_END)
        if nchar < 25 and not whole:
            c += 8.0                                  # a short fragment that is not a sentence of its own
        c += 4.0                                      # per cue: prefer fuller cues
        c += 0.02 * (2 * max_line - nchar)            # slight pull towards using the two lines
        return c

    INF = float("inf")
    best = [(INF, -1)] * (n + 1)
    best[0] = (0.0, -1)
    for j in range(1, n + 1):
        for i in range(j - 1, -1, -1):
            if len(" ".join(words[i:j])) > MAX_LINES * max_line + 10:
                break
            if best[i][0] == INF:
                continue
            c = best[i][0] + cue_cost(i, j) + (gap_cost(words, j, q[j]) if j < n else 0.0)
            if c < best[j][0]:
                best[j] = (c, i)
    spans, j = [], n
    while j > 0:
        i = best[j][1]
        spans.append((i, j))
        j = i
    spans.reverse()
    out = []
    for k, (i, j) in enumerate(spans):
        lines = lay.get((i, j)) or wrap(words[i:j], max_line, q[i:j + 1])
        t0 = 0.0 if k == 0 else st[i]
        t1 = st[j] if j < n else duration
        t1 = min(t1, max(st[i], t0) + max_dur)
        out.append([round(t0, 3), round(max(t1, t0 + 0.3), 3), "\n".join(lines[0])])
    return out
