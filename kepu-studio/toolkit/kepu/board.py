"""分镜的节奏预算检查（不花钱）：大字卡、插卡、签名动作、镜头推拉、白底段落，数量和间隔（来源：《ETH》engine/README §5–§6）。

    kepu board script/storyboards/ep01.md                  # 对应的稿子默认是 script/episodes/ep01.md
    kepu board script/storyboards/ep01.md --script 稿子.md

分镜每个 beat 一行：`- 07 【内】……强调色：无。对应：同。`（`- **07**` 也认）。卡型记号：
  【章】章节卡（不计数）【大】大字卡 【插】插卡 【内】内容图 【混】大字和内容同屏 【白】白底段落 【判】签名动作
时间：配过音就用真实时长（<audio>/<期>/beats.json），否则按字数估。冷开场（默认 3 分钟）里的间隔不查。
教训（《ETH》）：大字卡是“重音”，用多了就没有重音；两次之间不到 20 秒，观众会觉得在被喊口号。
上限写在 kepu.toml 的 [board]，也就是系列设定里的“节奏预算”。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import script as S
from .util import pad, width

LINE = re.compile(r"^\s*[-*]\s*(?:\*\*)?#?(\d{1,3}[a-z]?)(?:\*\*)?(?=[\s【])\s*(.*)$")
PUSH = re.compile(r"推近|拉远|推拉|镜头推|镜头拉|[Zz]oom ?(?:in|out)|[Dd]olly")
ACCENT = re.compile(r"(?:红|强调色|强调|accent)\s*[：:]")
OK, BAD, WARN = "✓", "✗", "!"


@dataclass
class Shot:
    id: str
    line: int
    text: str
    cards: list = field(default_factory=list)       # "大" / "插" / "判" / ... in order of appearance
    push: bool = False
    accent: bool = False
    t: float | None = None                          # beat start, seconds


def _key(i: str) -> str:
    return i.lstrip("0") or "0"


def storyboard_for(script: Path, cfg) -> Path:
    """The storyboard of an episode: same file name as the script (ep1_sat.md), else the chapter id (ep1.md)."""
    from .voice import chapter_id
    d = cfg.path("project", "storyboards")
    same = d / Path(script).name
    return same if same.exists() else d / f"{chapter_id(Path(script))}.md"


def parse_board(path: Path) -> list[Shot]:
    """Beat lines, each with its indented continuation lines (a shot may run over several lines)."""
    shots, cur = [], None
    for n, ln in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        m = LINE.match(ln)
        if m and not ln[:1].isspace():
            cur = [m.group(1), n, m.group(2)]
            shots.append(cur)
        elif cur and ln[:1].isspace() and ln.strip():
            cur[2] += "\n" + ln.strip()
        elif not ln.strip() or ln.startswith("#") or not ln[:1].isspace():
            cur = None
    return [Shot(i, n, t, re.findall(r"【(章|大|插|内|混|白|判)】", t), bool(PUSH.search(t)), bool(ACCENT.search(t)))
            for i, n, t in shots]


def beat_starts(ep, cfg) -> dict[str, float]:
    """Start time of each beat: real durations when the episode is voiced, else an estimate from the character count."""
    cpm = float(cfg.get("voice", "chars_per_minute"))
    gap = float(cfg.get("voice", "beat_gap"))
    bj = cfg.path("project", "audio") / Path(ep.path).stem / "beats.json"
    real = json.loads(bj.read_text("utf-8")).get("beats", {}) if bj.exists() else {}
    out, t = {}, 0.0
    for b in ep.beats:
        out[_key(b.id)] = t
        if b.id in real:
            t += float(real[b.id].get("duration", 0)) + gap
        elif b.narration:
            _, spoken, _ = S.split_beat(b.narration)
            n = len(re.sub(r"[\s，。！？；：、“”‘’（）《》…—]", "", spoken))
            t += n / cpm * 60 + sum(s for _, s in b.pauses) + gap
    return out


def check(board: Path, cfg, script: Path | None = None, quiet: bool = False) -> tuple[int, list]:
    """-> (number of ✗, rows [(status, what, detail)])."""
    shots = parse_board(board)
    script = script or cfg.path("project", "scripts") / Path(board).name
    rows = []
    if not shots:
        rows.append((BAD, "分镜", f"{Path(board).name} 里没有认出 beat 行（格式：- 07 【内】……）"))
        return _report(board, rows, quiet)
    lim = {k: cfg.get("board", k) for k in ("big_max", "insert_max", "judge_max", "push_max", "white_min", "white_max",
                                            "gap_seconds", "cold_open_seconds")}
    starts = {}
    if Path(script).exists():
        ep = S.parse(script)
        starts = beat_starts(ep, cfg)
        known = set(starts)
        unknown = [s.id for s in shots if _key(s.id) not in known and "章" not in s.cards]   # 章节卡可以只在分镜里
        missing = [b.id for b in ep.beats if _key(b.id) not in {_key(s.id) for s in shots}]
        rows.append((BAD if unknown else OK, "分镜的 beat 都在稿子里", ("稿子里没有：" + " ".join(unknown)) if unknown else ""))
        rows.append((WARN if missing else OK, "稿子的 beat 都有分镜", ("没写分镜：" + " ".join(missing[:12])
                                                                + (" …" if len(missing) > 12 else "")) if missing else ""))
        for s in shots:
            s.t = starts.get(_key(s.id))
    else:
        rows.append((WARN, "对应的稿子", f"没找到 {script}：只数次数，不查间隔（用 --script 指定）"))
    count = {k: sum(s.cards.count(k) for s in shots) for k in ("大", "插", "判")}
    pushes = sum(s.push for s in shots)
    whites, prev = 0, False
    for s in shots:
        w = "白" in s.cards
        whites += w and not prev
        prev = w
    for k, what, cap in (("大", "大字卡", "big_max"), ("插", "插卡", "insert_max"), ("判", "签名动作【判】", "judge_max")):
        n, m = count[k], int(lim[cap])
        rows.append((BAD if n > m else OK, f"{what} {n} 次（上限 {m}）", "删掉最弱的几次：重音用多了就没有重音" if n > m else ""))
    m = int(lim["push_max"])
    rows.append((BAD if pushes > m else OK, f"镜头推拉 {pushes} 次（上限 {m}）", "推拉留给真正要看细节的地方" if pushes > m else ""))
    lo, hi = int(lim["white_min"]), int(lim["white_max"])
    rows.append((OK if lo <= whites <= hi else WARN, f"白底段落 {whites} 段（建议 {lo}–{hi}）",
                 "" if lo <= whites <= hi else "一期需要一两段换气：回顾、读定义、慢下来的地方"))
    gap, cold = float(lim["gap_seconds"]), float(lim["cold_open_seconds"])
    loud = [(s, k) for s in shots if s.t is not None for k in s.cards if k in ("大", "插")]
    close = [f"{a.id}→{b.id}（{b.t - a.t:.0f}s）" for (a, _), (b, _) in zip(loud, loud[1:])
             if b.t > cold and b.t - a.t < gap and a.id != b.id]
    if starts:
        rows.append((BAD if close else OK, f"大字卡 / 插卡之间 ≥ {gap:.0f} 秒（冷开场 {cold / 60:.0f} 分钟内不查）",
                     " ".join(close[:8]) + ("：挪开或合并" if close else "")))
    bare = [s.id for s in shots if "章" not in s.cards and not s.accent]
    rows.append((WARN if bare else OK, "每屏写明强调色落点（“强调色：……”或“红：……”，没有就写“无”）",
                 ("没写：" + " ".join(bare[:12]) + (" …" if len(bare) > 12 else "")) if bare else ""))
    return _report(board, rows, quiet, count, pushes, whites)


def _report(board, rows, quiet, count=None, pushes=0, whites=0):
    bad = sum(1 for r in rows if r[0] == BAD)
    if not quiet:
        print(f"分镜节奏 · {Path(board).name}" + (f"：大字 {count['大']}、插卡 {count['插']}、【判】{count['判']}、推拉 {pushes}、"
                                                  f"白底 {whites} 段" if count else ""))
        w = min(36, max(width(r[1]) for r in rows))
        for st, what, detail in rows:
            print(f"  {st} {pad(what, w + 2)}{detail}")
        print(f"  {'通过' if not bad else f'{bad} 项没过'}")
    return bad, rows
