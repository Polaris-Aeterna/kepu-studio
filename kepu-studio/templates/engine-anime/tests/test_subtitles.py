"""
Subtitle segmentation regression tests (engine/subtitles.py).  No ManimGL needed, no API calls.

    engine/.venv/bin/python -m pytest engine/tests -q

Fixtures are the real beats of the six episodes (engine/audio/epN/beats.json: display text + per-character times
from ElevenLabs).  Named cases are the ones review/av_a/SUMMARY.md and the episode reviews called out.
"""
import json
import re
import sys
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
import subtitles as S  # noqa: E402

AUDIO = ENGINE / "audio"
EPISODES = [f"ep{n}" for n in range(1, 7) if (AUDIO / f"ep{n}" / "beats.json").exists()]


def beats(ep):
    return json.loads((AUDIO / ep / "beats.json").read_text("utf-8"))["beats"]


def lines(ep, bid):
    v = beats(ep)[bid]
    return S.split_phrases(v["text"], v["char_times"], v["duration"])


def texts(ep, bid):
    return [p[2] for p in lines(ep, bid)]


def find_beat(ep, needle):
    for bid, v in beats(ep).items():
        if needle in v["text"]:
            return bid
    pytest.skip(f"{needle!r} not in {ep} any more")


# ------------------------------------------------------------------ named regressions
@pytest.mark.parametrize("ep,word", [
    ("ep6", "技术概览"),             # was 技 / 术概览
    ("ep6", "共享线性摘要"),          # was 共 / 享线性摘要
    ("ep6", "低次多项式"),            # was 低次多 / 项式
    ("ep6", "n(log log n)²/√log n"),  # formula split in two
    ("ep2", "Stephen Cook"),         # Latin name split
    ("ep2", "Leonid Levin"),
    ("ep2", "库克–列文（Cook–Levin）定理"),
    ("ep5", "t + 3(t−i) + 6i"),      # ep5 #44: each formula in one subtitle
    ("ep5", "t + 6(t−i) + 3i"),
])
def test_kept_together(ep, word):
    bid = find_beat(ep, word)
    assert any(word in t for t in texts(ep, bid)), texts(ep, bid)


def test_if_then_quote_not_shattered():
    """ep6 #04: “如果……那么……” used to become 5 cues, two of them only an ellipsis."""
    bid = find_beat("ep6", "“如果……那么……”")
    ts = texts("ep6", bid)
    assert any("“如果……那么……”" in t for t in ts), ts
    assert not any(re.fullmatch(r"[…\s“”]+", t) for t in ts)


def test_no_lone_ellipsis_ep5():
    """ep5 #51: a 0.34 s cue that was only “…”."""
    bid = find_beat("ep5", "0.66……")
    assert not any(re.fullmatch(r"[…\s.]+", t) for t in texts("ep5", bid))


def test_closing_quote_stays_left():
    """ep2 #25: the closing quote was carried to the start of the next cue."""
    for ep in EPISODES:
        for bid in beats(ep):
            for t in texts(ep, bid):
                assert not t.startswith(("”", "’", "）", "」")), (ep, bid, t)


# ------------------------------------------------------------------ invariants on all six episodes
def all_beats():
    for ep in EPISODES:
        for bid, v in beats(ep).items():
            if v.get("text"):
                yield ep, bid, v


@pytest.mark.parametrize("ep", EPISODES)
def test_invariants(ep):
    for bid, v in beats(ep).items():
        text = v.get("text") or ""
        if not text:
            continue
        ph = S.split_phrases(text, v["char_times"], v["duration"])
        assert ph, (ep, bid)
        # 1. only the segmentation changes: the cues, in order, are the text minus spaces / cut punctuation
        def norm(s):
            return re.sub(r"[\s，。；：、,;:]", "", s)
        assert norm("".join(p[2] for p in ph)) == norm(text), (ep, bid)
        prev_end = 0.0
        for k, (t0, t1, s) in enumerate(ph):
            # 2. no cue of punctuation / ellipsis only
            assert re.search(r"[^\s…，。“”‘’（）().,、；：！？!?—]", s), (ep, bid, s)
            # 3. quotes are balanced inside a cue (unless one quote is longer than a whole line)
            if s.count("“") != s.count("”"):
                q = re.search(r"“[^”]*”", text[text.find(s[:4]):] if s[:4] in text else text)
                assert q is None or S.vis(q.group()) > S.MAX_CHARS + 4, (ep, bid, s)
            # 4. braces never split
            assert s.count("{") == s.count("}"), (ep, bid, s)
            # 5. times are monotone and come from the char_times (timing unchanged)
            assert t1 > t0 >= prev_end - 1e-6 or k == 0, (ep, bid, s, t0, prev_end)
            prev_end = t0
        # 6. no fragment shorter than MIN_DUR unless the whole beat is one cue
        if len(ph) > 1:
            short = [p for p in ph if p[1] - p[0] < S.MIN_DUR - 1e-6]
            assert not short, (ep, bid, short)


def test_cue_starts_are_first_spoken_char_times():
    """The start of every cue (except the first, pinned to 0) is the time of its first spoken character."""
    for ep, bid, v in all_beats():
        text, times = v["text"], v["char_times"]
        pos = 0
        for k, (t0, t1, s) in enumerate(S.split_phrases(text, times, v["duration"])):
            i = text.find(s, pos)
            assert i >= 0
            j = next(j for j in range(i, len(text)) if text[j] not in S.SILENT)
            if k:
                assert abs(t0 - times[j]) < 1e-9, (ep, bid, s)
            pos = i + len(s)


def test_no_word_split_and_no_function_word_end():
    import jieba  # noqa: F401
    for ep, bid, v in all_beats():
        text = v["text"]
        inner = {k for w, a, b in S._jieba().tokenize(text) for k in range(a + 1, b)}
        pos = 0
        for s in [p[2] for p in S.split_phrases(text, v["char_times"], v["duration"])][:-1]:
            i = text.find(s, pos)
            c = i + len(s)
            pos = c
            if S.is_cjk(text[c - 1]) and c < len(text) and S.is_cjk(text[c]):
                assert c not in inner, (ep, bid, s + "|" + text[c:c + 4])
                assert text[c - 1] not in "和与在的把被对从向给让将", (ep, bid, s + "|" + text[c:c + 4])


def test_max_width():
    for ep, bid, v in all_beats():
        for s in [p[2] for p in S.split_phrases(v["text"], v["char_times"], v["duration"])]:
            assert S.vis(s) <= S.MAX_CHARS + 6, (ep, bid, s, S.vis(s))


# ------------------------------------------------------------------ srt plain text
@pytest.mark.parametrize("src,want", [
    ("运行时间大约是2^{n/√log n}", "运行时间大约是2^(n/√log n)"),
    ("2^n 种赋值", "2ⁿ 种赋值"),
    ("2^{o(n)}", "2^(o(n))"),
    ("x_{12} 和 x_1", "x₁₂ 和 x₁"),
    ("2^{10}", "2¹⁰"),
    ("(−1)^{j}", "(−1)ʲ"),
    ("没有公式", "没有公式"),
])
def test_srt_text(src, want):
    assert S.srt_text(src) == want


def test_srt_text_has_no_source_syntax():
    for ep, bid, v in all_beats():
        for s in [p[2] for p in S.split_phrases(v["text"], v["char_times"], v["duration"])]:
            out = S.srt_text(s)
            assert "{" not in out and "}" not in out and "^{" not in out and "_{" not in out, (ep, bid, out)
