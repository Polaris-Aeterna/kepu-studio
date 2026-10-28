"""读一期的稿子。两种写法都认（可以混用）：

ETH 式（一个 beat 一段台词，整段合成一次）：
    ## 场景 2 · 子句与 CNF [L1]            ← 场景（= B 站分段），标签向下继承
    ### beat 07 [L2] [骨架]                ← 也认 “## beat 07”
    台词：……{显示|读法}……字〔读音〕……（停顿 2 秒）……
    画面：……
    屏幕文字：……
    备注：……

《地基之下》式（场景里没有 beat 标题：旁白的每一段是一条，单独合成）：
    ## 场景 1 · 钩子（0:00–1:29）
    **画面**：……
    **旁白**：
    第一段。
    （停顿两秒）
    第二段。

标签：难度 [L1] [L2] [L3]（也认 ★ / ★★ / ★★★、[入门] [进阶] [硬核]）；严谨度 [完整] [骨架] [黑箱 A→12] [黑箱→文献]。
也可以在 beat 里写一行 “难度：L2” / “严谨度：骨架”。
台词里：{显示|读法} 字幕显示左边、合成念右边；字〔读音〕 读音标记（只在念的一侧生效，永远不进字幕）；
（停顿 2 秒）/（停顿两秒）/（停顿） 是停顿，不念，合成后插入静音。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .pron.marks import MARK

HEAD = re.compile(r"^(#{1,6})\s*(.*?)\s*$")
BEAT_HEAD = re.compile(r"^beat\s*([0-9A-Za-z_\-]+)\s*(.*)$", re.I)
FIELD = re.compile(r"^\s*(?:\*\*)?(台词|旁白|画面|屏幕文字|备注|难度|级别|严谨度|Narration|Visual|On-screen text|Note)(?:\*\*)?\s*[：:]\s*(?:\*\*)?\s*(.*)$")
TAG = re.compile(r"[\[【]\s*([^\]】]+?)\s*[\]】]")
PAUSE = re.compile(r"[（(]\s*(?:停顿|暂停)\s*([0-9.]+|[一二两三四五六七八九十半]+)?\s*(?:秒|s)?(?:钟)?\s*[）)]")
_ZH_NUM = {"半": 0.5, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
LEVELS = {"l1": "L1", "l2": "L2", "l3": "L3", "★": "L1", "★★": "L2", "★★★": "L3", "入门": "L1", "进阶": "L2", "硬核": "L3",
          "主线": "L1", "支线": "L3"}
RIGOR = re.compile(r"^(完整|骨架|黑箱.*)$")
NARR_FIELDS = ("台词", "旁白", "Narration")


@dataclass
class Beat:
    id: str
    narration: str                 # raw (with {显示|读法}, marks and pause markers)
    scene: str = ""
    visual: str = ""
    onscreen: str = ""
    note: str = ""
    level: str = ""
    rigor: str = ""
    line: int = 0

    @property
    def pauses(self) -> list[tuple[int, float]]:
        """[(position in the display text, seconds)]."""
        out = []
        disp, _, _ = split_beat(self.narration, keep_pauses=True)
        offset = 0
        for m in PAUSE.finditer(disp):
            out.append((m.start() - offset, pause_seconds(m.group(1))))
            offset += len(m.group(0))
        return out


@dataclass
class Episode:
    path: Path
    title: str = ""
    meta: str = ""
    scenes: list = field(default_factory=list)
    beats: list = field(default_factory=list)
    unit: str = "beat"             # "beat" (ETH) or "line" (地基之下: each narration paragraph is a beat)
    problems: list = field(default_factory=list)

    def beat(self, bid: str) -> Beat | None:
        return next((b for b in self.beats if b.id == bid), None)


def pause_seconds(s: str | None) -> float:
    if not s:
        return 1.5
    try:
        return float(s)
    except ValueError:
        if s in _ZH_NUM:
            return float(_ZH_NUM[s])
        return float(sum(_ZH_NUM.get(c, 0) for c in s) or 1.5)


def _tags(text: str) -> tuple[str, str, str]:
    """header text -> (text without tags, level, rigor)."""
    level = rigor = ""
    for m in TAG.finditer(text):
        t = m.group(1).strip()
        if t.lower() in LEVELS or t in LEVELS:
            level = LEVELS.get(t.lower(), LEVELS.get(t, ""))
        elif RIGOR.match(t):
            rigor = t
    for star in ("★★★", "★★", "★"):
        if star in text and not level:
            level = LEVELS[star]
    return TAG.sub("", text).strip(), level, rigor


def parse(path: Path | str) -> Episode:
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    ep = Episode(path)
    scene, s_level, s_rigor = "", "", ""
    cur: Beat | None = None
    cur_field = None
    buf: list[str] = []
    line_paras: list[tuple[int, str]] = []      # 地基之下: paragraphs of the current 旁白 block
    scene_has_beats = False
    scene_lines: list[Beat] = []
    nscene = 0

    def flush_field():
        nonlocal buf, cur_field
        if cur is not None and cur_field:
            text = "\n".join(buf).strip()
            if cur_field in NARR_FIELDS:
                cur.narration = (cur.narration + "\n" + text).strip() if cur.narration else text
            elif cur_field in ("画面", "Visual"):
                cur.visual = (cur.visual + "\n" + text).strip()
            elif cur_field in ("屏幕文字", "On-screen text"):
                cur.onscreen = (cur.onscreen + "\n" + text).strip()
            elif cur_field in ("备注", "Note"):
                cur.note = (cur.note + "\n" + text).strip()
        buf, cur_field = [], None

    def flush_beat():
        nonlocal cur
        flush_field()
        if cur is not None:
            ep.beats.append(cur)
        cur = None

    def flush_lines():
        """地基之下: emit the paragraphs of the scene's 旁白 blocks as line-beats."""
        nonlocal line_paras
        for ln, para in line_paras:
            scene_lines.append(Beat("", para, scene, line=ln, level=s_level, rigor=s_rigor))
        line_paras = []

    in_narr_block = False
    skip = False                                # 制作备注 / 附录: no narration in there
    para: list[str] = []
    para_line = 0
    for n, raw in enumerate(lines, 1):
        h = HEAD.match(raw)
        if h:
            skip = False
            if in_narr_block:
                if para:
                    line_paras.append((para_line, "".join(para)))
                    para = []
                in_narr_block = False
            text = h.group(2)
            bm = BEAT_HEAD.match(text)
            if bm:
                flush_beat()
                scene_has_beats = True
                rest, lv, rg = _tags(bm.group(2))
                cur = Beat(bm.group(1), "", scene, level=lv or s_level, rigor=rg or s_rigor, line=n)
                continue
            if len(h.group(1)) == 1 and not ep.title:
                ep.title = text
                continue
            # a new scene (## or ###) ends the previous one
            flush_beat()
            flush_lines()
            if not scene_has_beats and scene_lines:
                ep.beats.extend(scene_lines)
            scene_lines = []
            scene_has_beats = False
            if text and not text.startswith(("制作备注", "结尾备注", "备注", "附录", "参考")):
                scene, s_level, s_rigor = _tags(text)
                ep.scenes.append(scene)
                nscene += 1
            else:
                scene, skip = text, True
            continue
        if skip:
            continue
        fm = FIELD.match(raw)
        if cur is not None:                     # ETH style: fields of a beat
            if fm:
                flush_field()
                key, rest = fm.group(1), fm.group(2)
                if key in ("难度", "级别"):
                    _, lv, _ = _tags(f"[{rest.strip()}]")
                    cur.level = lv or cur.level
                elif key == "严谨度":
                    cur.rigor = rest.strip()
                else:
                    cur_field, buf = key, [rest]
            elif cur_field:
                buf.append(raw)
            continue
        # 地基之下 style: 旁白 blocks outside beats
        if fm:
            if in_narr_block and para:
                line_paras.append((para_line, "".join(para)))
                para = []
            in_narr_block = fm.group(1) in NARR_FIELDS
            if in_narr_block and fm.group(2).strip():
                para, para_line = [fm.group(2).strip()], n
            continue
        if in_narr_block:
            s = raw.strip()
            if not s:
                if para:
                    line_paras.append((para_line, "".join(para)))
                    para = []
            elif s.startswith(">"):
                continue
            else:
                if not para:
                    para_line = n
                para.append(s)
        elif not ep.beats and not cur and not scene:
            ep.meta += raw + "\n"
    if in_narr_block and para:
        line_paras.append((para_line, "".join(para)))
    flush_beat()
    flush_lines()
    if not scene_has_beats and scene_lines:
        ep.beats.extend(scene_lines)
    # ids for line-beats: s<scene>l<line>, in order
    if any(not b.id for b in ep.beats):
        ep.unit = "line" if all(not b.id for b in ep.beats) else "mixed"
        counters: dict[str, int] = {}
        for b in ep.beats:
            if not b.id:
                k = ep.scenes.index(b.scene) + 1 if b.scene in ep.scenes else 0
                counters[b.scene] = counters.get(b.scene, 0) + 1
                b.id = f"s{k:02d}l{counters[b.scene]:02d}"
    for b in ep.beats:
        b.narration = re.sub(r"\*\*|__|`", "", b.narration)
        b.narration = re.sub(r"\s*\n\s*", "", b.narration).strip()
        if not b.narration:
            ep.problems.append((b.line, f"beat {b.id} 没有台词"))
    seen = set()
    for b in ep.beats:
        if b.id in seen:
            ep.problems.append((b.line, f"beat 编号重复：{b.id}"))
        seen.add(b.id)
    return ep


# ------------------------------------------------------------------------------------------------ {显示|读法}
def overrides(text: str):
    """Yield (start, end, display, spoken) for each {显示|读法}; the display side may itself contain {...}."""
    i = 0
    while True:
        i = text.find("{", i)
        if i < 0:
            return
        depth, bar, j = 0, -1, i
        while j < len(text):
            c = text[j]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            elif c == "|" and depth == 1 and bar < 0:
                bar = j
            j += 1
        if j >= len(text):
            return
        if bar > 0:
            yield i, j + 1, text[i + 1:bar], text[bar + 1:j]
            i = j + 1
        else:
            i += 1


def split_beat(text: str, keep_pauses: bool = False):
    """narration -> (display, spoken_with_marks, map spoken-index -> display-index).
    Reading marks never reach the display; pause markers are removed from both sides unless keep_pauses."""
    if not keep_pauses:
        text = PAUSE.sub("", text)
    display, spoken, mapping = [], [], []

    def plain(seg):
        pos = 0
        for m in MARK.finditer(seg):
            for ch in seg[pos:m.start()]:
                mapping.append(len(display))
                display.append(ch)
                spoken.append(ch)
            for ch in m.group(0):
                mapping.append(max(len(display) - 1, 0))
                spoken.append(ch)
            pos = m.end()
        for ch in seg[pos:]:
            mapping.append(len(display))
            display.append(ch)
            spoken.append(ch)

    pos = 0
    for start, end, disp, spk in overrides(text):
        plain(text[pos:start])
        d0 = len(display)
        display.extend(MARK.sub("", disp))
        for ch in spk:
            mapping.append(d0)
            spoken.append(ch)
        pos = end
    plain(text[pos:])
    return "".join(display), "".join(spoken), mapping


def syntax_problems(text: str) -> list[str]:
    """{…|…} that do not pair up, empty sides, a '|' outside braces."""
    out = []
    depth = 0
    for c in text:
        depth += (c == "{") - (c == "}")
        if depth < 0:
            out.append("多了一个“}”")
            depth = 0
    if depth > 0:
        out.append("少了一个“}”")
    for _, _, d, s in overrides(text):
        if not d.strip() or not s.strip():
            out.append(f"{{{d}|{s}}} 的显示或读法为空")
        if "{" in s or "|" in s:
            out.append(f"{{{d}|{s}}} 的读法里还有花括号或“|”")
    stripped = re.sub(r"\{[^{}]*\}", "", text)
    if "|" in stripped and not re.search(r"\{[^}]*\|", text):
        out.append("花括号外出现了“|”")
    return out
