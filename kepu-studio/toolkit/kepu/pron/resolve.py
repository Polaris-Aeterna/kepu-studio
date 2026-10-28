"""给每一处多音字一个决定（或者拦下）。

决定的来源，从强到弱：
    mark     稿子里的读音标记 字〔读音〕（作者的决定，什么都盖不过它）
    lexicon  三层读音词典（项目 > 个人 > 内置），最长匹配；词条同时修正通用词典（背〔bèi〕包）
    rule     上下文规则（rules.py）；规则给的读音和通用词典打架 → 拦下
    dict     通用词典（pypinyin 词组库）**只能放行、不能强制**：它给默认读音、且没有分词歧义 → 不改文字。
             它给非默认读音：A 级字拦下；B 级字交给模型并列出（status = auto）；C 级字（助词、极常用字）直接交给模型。
             教训：pypinyin 把 方差 标成 chà、背包 标成 bēi、用处 标成 chǔ —— 让它强制就会把错误固化。
分词陷阱（三级都查）：同一个字在两种说得通的切分里读音不同 → 拦下。例：长子句（长子+句 / 长+子句）、东西藏（东西+藏 / 东+西藏）、
    宣布了解答（了解 / 了+解答）、中间断开（中间 / 间断）、零处分组（处分 / 分组）。单字切分只有在旁边的词“抢走”了
    这个字的搭档时才算（长子句里“子句”抢走了“子”），所以“对应的”不会因为“对 / 应”能单切就报警。
A 级字（行 长 数 当 重 差 调 相 切）没有 mark / lexicon / rule、词典又不能放行 → 拦下。

决定之后：force → 换成替身字（standins.tsv）；没有替身字 → 送带调号的拼音（status = pinyin，合成后必须人耳听）；
严格模式（pron.strict）下改为拦下、要求改写。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .. import seg
from .inventory import polyphones, readings_of, stand_in
from .lexicon import LAYERS, Hit, Lexicon
from .rules import hang_positions, rewrite_hint, rule_at


@dataclass
class Spot:
    i: int
    char: str
    ctx: str
    reading: str = ""            # decided reading ('' = undecided)
    source: str = ""             # mark | lexicon | rule | dict | default
    action: str = "leave"        # force | leave | hold
    status: str = "ok"           # ok | auto | hold | pinyin | bad_mark
    why: str = ""
    suggest: list = field(default_factory=list)
    rewrite: str = ""
    entry: str = ""              # lexicon entry (spec) that decided it
    say: str = ""                # what is sent to the TTS for this character
    standin_status: str = ""     # field | new (stand-in), '' otherwise
    word: str = ""               # dictionary word around it (for reports and ear-check grouping)
    freq: int = 0
    span: tuple = ()             # (start, end) of the context a lexicon entry must cover to settle a held spot
    default: str = ""

    @property
    def open(self) -> bool:
        return self.status in ("hold", "bad_mark")


@dataclass
class DictView:
    reading: str                 # reading from the best curated dictionary word covering the char ('' = none)
    word: str                    # that word
    freq: int
    ambiguous: bool
    alts: list                   # [(word or '单字', reading)] behind an ambiguity
    alone: bool                  # the best segmentation leaves the char on its own
    spans: list = field(default_factory=list)   # [(start, end, reading, score, single)] for each plausible reading


_HANG_WORDS = re.compile(r"^(?:银|同|内|外|排|商|车|琴|车|米|字|行行|本|在|改|转|老|懂)行|^行(?:业|家|情|列|距|首|规|话|当|货|伍|长|号|间)")
_NUM_HANG = re.compile(r"^[一二三四五六七八九十两几多每各逐这那本整首末]行$")


def _ctx(text: str, i: int) -> str:
    return text[max(0, i - 8):i] + "【" + text[i] + "】" + text[i + 1:i + 7]


def _lex_reading(lex: Lexicon, word: str, k: int) -> str | None:
    for e in lex.by_first.get(word[0], ()):
        if e.clean == word and k in e.readings and e.readings[k] != "?":
            return e.readings[k]
    return None


def _curated(lex: Lexicon, word: str, k: int) -> str | None:
    """Reading of word[k] from the lexicon (which also patches the dictionary) or pypinyin's phrase dictionary."""
    r = _lex_reading(lex, word, k)
    if r is not None:
        return r
    wr = seg.word_reading(word, k)
    return wr[0] if wr is not None and wr[1] == "P" else None


def dict_view(text: str, i: int, cov: dict, default: str, lex: Lexicon) -> DictView:
    cands = cov.get(i, [])
    pc, single, single_sc = [], False, None
    for sc, s, e in cands:
        if e - s == 1:
            single, single_sc = True, sc
            continue
        w = text[s:e]
        r = _curated(lex, w, i - s)
        if r is None:
            # an idiom or jieba-only word (恰恰相反, 至关重要): use the longest curated word inside it (相反, 重要)
            for L in range(e - s - 1, 1, -1):
                for s2 in range(max(s, i - L + 1), min(i, e - L) + 1):
                    r = _curated(lex, text[s2:s2 + L], i - s2)
                    if r is not None:
                        break
                if r is not None:
                    break
        if r is None:
            continue
        pc.append((sc, s, e, r))
    alone = bool(cands) and cands[0][2] - cands[0][1] == 1
    if not pc:
        return DictView("", "", 0, False, [], alone, [])
    sc0, s0, e0, r0 = pc[0]
    seen, alts, spans = [], [], []
    for sc, s, e, r in pc:
        spans.append((s, e, r, sc, False))
        if r not in seen:
            seen.append(r)
            alts.append((text[s:e], r))
    if single:
        # the single-character split only counts when a neighbouring word steals the char's partner
        stealers = [(s2, e2) for j in range(s0, e0) if j != i for _, s2, e2 in cov.get(j, [])
                    if e2 - s2 >= 2 and not (s2 <= i < e2)]
        if stealers:
            spans.extend((s2, e2, default, single_sc, True) for s2, e2 in stealers)
            if default not in seen:
                seen.append(default)
                alts.append(("单字", default))
    w0 = text[s0:e0]
    freq = seg.words()[0].get(w0, (0,))[0]
    return DictView(r0, w0, freq, len(seen) > 1, alts, alone, spans)


def resolve(text: str, marks: dict[int, str], lex: Lexicon, *, strict: bool = False, margin: float = 3.0,
            bad_standins: frozenset = frozenset()) -> list[Spot]:
    """Decide every inventory polyphone (and every marked character) in `text` (marks already removed)."""
    poly = polyphones()
    targets = [i for i, c in enumerate(text) if c in poly or i in marks]
    if not targets:
        return []
    lexcov = lex.covering(text)
    lat = cov = None
    hang = hang_positions(text) if "行" in text else set()
    spots = []
    for i in targets:
        ch = text[i]
        P = poly.get(ch)
        tier = P.tier if P else "B"
        default = P.default if P else (readings_of(ch) or [""])[0]
        sp = Spot(i, ch, _ctx(text, i), default=default)
        dv = None
        if i not in marks:
            if lat is None:
                lat = seg.Lattice(text)
                cov = lat.covering(margin)
            dv = dict_view(text, i, cov, default, lex)
            sp.word, sp.freq = dv.word, dv.freq

        if i in marks:                                                  # 1. author's mark
            r = marks[i]
            rs = readings_of(ch)
            if rs and r not in rs:
                sp.status, sp.action = "bad_mark", "hold"
                sp.why = f"“{ch}”没有读音 {r}（可选：{'、'.join(rs)}）"
                sp.suggest = rs
            else:
                sp.reading, sp.source, sp.action = r, "mark", "force"
        elif i in lexcov and (lexhit := _lex_choose(text, i, lexcov[i], lat))[0] is not None:   # 2. lexicon
            h, aligned = lexhit
            sp.entry = h.entry.spec + ("" if h.entry.layer == "builtin" else f"（{h.entry.layer}）")
            if h.conflicts:
                sp.status, sp.action = "hold", "hold"
                sp.why = "词条冲突：" + " / ".join([h.entry.spec] + [e.spec for _, e in h.conflicts])
                sp.suggest = list(dict.fromkeys([h.reading] + [e.readings.get(i - st, "") for st, e in h.conflicts]))
            elif h.action == "hold":
                sp.status, sp.action = "hold", "hold"
                sp.why = f"同形词“{h.entry.clean}”：{h.entry.note or '读音取决于意思'}，请在稿子里标读音"
                sp.suggest = [r for r in readings_of(ch) if r] or [default]
            else:
                sp.reading, sp.source, sp.action = h.reading, "lexicon", h.action
                if h.action == "leave" and _single_reading(text, i, hang, "") == h.reading and rule_at(text, i):
                    sp.action = "force"                 # a context rule says the same and wants it forced (航为真)
                trap = "" if aligned else _trap(text, i, h, dv)
                if not trap:
                    # an entry settles a trap only if it contains every competing word (长〔cháng〕子句 contains 长子
                    # and 子句; 西藏〔zàng〕 does not contain 东西 in “东西藏在箱子里”)
                    a, b = h.start, h.start + len(h.entry.clean)
                    own = lat.delta(a, b)
                    for s2, e2, r2, sc2, is_single in dv.spans:
                        if is_single:          # the character on its own: its reading comes from the context rules
                            r2 = _single_reading(text, i, hang, default)
                        # a competing reading vetoes the entry only if its segmentation is at least as plausible
                        if r2 != h.reading and not (a <= s2 and e2 <= b) and sc2 >= own - 0.01:
                            trap = (f"分词陷阱：词条“{h.entry.clean}”说 {h.reading}，"
                                    f"但切成“{text[s2:e2]}”时念 {r2}")
                            sp.span = (min(a, s2), max(b, e2))
                            break
                if trap:
                    sp.status, sp.action = "hold", "hold"
                    sp.why = trap
                    if not sp.span and dv.word:
                        k = text.find(dv.word, max(0, i - len(dv.word) + 1))
                        a, b = h.start, h.start + len(h.entry.clean)
                        sp.span = (min(a, k if k >= 0 else a), max(b, (k + len(dv.word)) if k >= 0 else b))
                    sp.suggest = list(dict.fromkeys([h.reading] + [r for _, r in dv.alts] + [dv.reading]))
        else:
            if ch == "行":
                rule = ("háng" if i in hang else "xíng", "“行”的规则：" + ("表格的行" if i in hang else "其余念 xíng"), "")
            else:
                rule = rule_at(text, i)
            if rule is not None:                                        # 3. context rule
                r, why, rw = rule
                r = r or default
                sp.why, sp.rewrite = why, rw
                if _rule_conflict(ch, r, dv):
                    sp.status, sp.action = "hold", "hold"
                    sp.why = f"规则说 {r}（{why}），通用词典说“{dv.word}”念 {dv.reading}"
                    sp.suggest = [r, dv.reading]
                else:
                    sp.reading, sp.source = r, "rule"
                    sp.action = "force" if rule[0] else "leave"
            elif dv.ambiguous:                                          # 4. segmentation trap
                sp.status, sp.action = "hold", "hold"
                sp.why = "分词陷阱：" + " / ".join(f"{w}（{r}）" for w, r in dv.alts)
                sp.suggest = list(dict.fromkeys(r for _, r in dv.alts))
                sp.span = (min([i] + [a for a, *_ in dv.spans]), max([i + 1] + [b for _, b, *_ in dv.spans]))
            elif dv.reading and dv.reading == default:                  # 5. dictionary agrees with the default
                sp.reading, sp.source, sp.action = default, "dict", "leave"
                sp.why = f"词典：{dv.word}"
            elif tier in ("B", "C"):
                if dv.reading:                                          # non-default: the model decides
                    sp.reading, sp.source, sp.action = dv.reading, "dict", "leave"
                    sp.why = f"词典：{dv.word}（非默认读音，没有强制，交给模型）"
                    if tier == "B":
                        sp.status = "auto"
                else:
                    sp.reading, sp.source, sp.action = default, "default", "leave"
            else:                                                       # tier A with no curated evidence
                sp.status, sp.action = "hold", "hold"
                if dv.reading:
                    sp.why = f"词典说“{dv.word}”念 {dv.reading}（A 级字，词典不可靠，需要确认）"
                else:
                    sp.why = f"A 级字“{ch}”没有词条或规则能定"
                sp.suggest = list(dict.fromkeys(([dv.reading] if dv.reading else []) + [default] + readings_of(ch)[:2]))[:3]
                sp.rewrite = rewrite_hint(ch, sp.suggest[0]) if sp.suggest else ""

        # force_default characters (行 长 调): a decided default reading is still forced
        if sp.action == "leave" and P and P.force_default and sp.reading and sp.status == "ok":
            sp.action = "force"
        _finish(sp, strict, bad_standins, default)
        spots.append(sp)
    return spots


def _single_reading(text: str, i: int, hang: set, default: str) -> str:
    if text[i] == "行":
        return "háng" if i in hang else "xíng"
    r = rule_at(text, i)
    return (r[0] or default) if r else default


LEX_MARGIN = 6.0      # an entry whose edges cost more than this (log-probability) is a false match, not a trap


def _lex_choose(text: str, i: int, occ: list, lat) -> tuple:
    """Pick the lexicon entry for position i.  Entries must be compatible with a plausible segmentation:
    edges on the best path -> apply; plausible but not best -> apply only if nothing better, and let the trap check look;
    implausible (似的 inside 类似的) -> ignore.  Returns (Hit or None, aligned)."""
    cands = []
    for s, e in occ:
        b = s + len(e.clean)
        d = lat.delta(s, b)
        if d >= -LEX_MARGIN:
            cands.append((s, b, e, d))
    if not cands:
        return None, False
    maximal = [c for c in cands if not any(o[0] <= c[0] and c[1] <= o[1] and (o[0], o[1]) != (c[0], c[1]) for o in cands)]

    def key(c):
        return (c[3] == 0.0, c[3], c[1] - c[0], c[2].action == "force", LAYERS.index(c[2].layer))
    maximal.sort(key=key, reverse=True)
    top = maximal[0]
    r0 = top[2].readings[i - top[0]]
    others = [c for c in maximal[1:] if c[2].readings[i - c[0]] != r0]
    hit = Hit(r0, top[2].action, top[2], top[0])
    if others:
        aligned = [c for c in maximal if c[3] == 0.0]
        if not (len(aligned) == 1 and aligned[0] is top):
            hit.conflicts = [(c[0], c[2]) for c in others]
    return hit, top[3] == 0.0


def _rule_conflict(ch: str, r: str, dv: DictView | None) -> bool:
    if dv is None or not dv.reading or dv.reading == r or dv.ambiguous or dv.alone:
        return False          # (alone: the best segmentation leaves the char on its own, e.g. 切 | 不 | 开, not 切不)
    if ch == "行":
        # the 行 rules were checked by hand on 209 cases; only real háng-words (同行, 银行 …) overrule a xíng verdict
        if r == "háng" or _NUM_HANG.match(dv.word):
            return False
        return dv.reading == "háng" and bool(_HANG_WORDS.search(dv.word))
    return True


def _trap(text: str, i: int, hit, dv: DictView | None) -> str:
    """A lexicon entry that the dictionary's best word does not support: 可数〔shǔ〕 inside 可数学家 (可 + 数学家)."""
    if dv is None or not dv.word or dv.reading == hit.reading:
        return ""
    a, b = hit.start, hit.start + len(hit.entry.clean)
    w = dv.word
    for s in range(max(0, i - len(w) + 1), i + 1):
        if text.startswith(w, s):
            e = s + len(w)
            if (a <= s and e <= b) or (s <= a and b <= e):
                return ""
            return f"可能是分词陷阱：词条“{hit.entry.clean}”说 {hit.reading}，但这里也能读成“{w}”（{dv.reading}）"
    return ""


def _finish(sp: Spot, strict: bool, bad: frozenset, default: str = ""):
    if sp.action != "force" or not sp.reading:
        sp.say = sp.char
        return
    si = stand_in(sp.reading, bad)
    if si:
        sp.say, sp.standin_status = si
        return
    if sp.reading == default:
        # the default reading has no stand-in (切 qiē, 卷 juǎn, 散 sàn …): the model's default is already right,
        # sending pinyin would only add risk
        sp.action, sp.say = "leave", sp.char
        return
    hint = rewrite_hint(sp.char, sp.reading)
    if strict:
        sp.status, sp.action = "hold", "hold"
        sp.why = (sp.why + "；" if sp.why else "") + f"{sp.reading} 没有替身字（严格模式不送拼音）"
        sp.rewrite = sp.rewrite or hint
        sp.say = sp.char
    else:
        sp.say = sp.reading
        if sp.status == "ok":
            sp.status = "pinyin"
        sp.rewrite = sp.rewrite or hint
