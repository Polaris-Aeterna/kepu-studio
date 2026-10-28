"""逐字稿（transcript）、B 站分段、.srt —— 都从同一份稿子和 beats.json 生成，不会互相对不上。

    kepu transcript script/episodes/ep01.md                 # → output/ep01/transcript.md、chapters.txt、ep01.srt
    kepu transcript script/episodes/ep01.md --timeline t.json   # 用渲染出来的真实时间（{beat: 开始秒}），否则按配音时长估计

逐字稿给读者看：按场景分段、带时间戳、显示文字（不是念的文字，没有替身字和读音标记）、难度和严谨度标签。
chapters.txt 是 B 站“分段”/置顶评论里的章节：00:00 场景名（一行一个，场景名去掉括号里的时间）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import script as S
from .subtitles import split_phrases, srt_text, write_srt
from .voice import chapter_id


def _ts(t: float) -> str:
    t = int(round(t))
    return f"{t // 3600}:{t // 60 % 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60:02d}:{t % 60:02d}"


def build(path: Path, cfg, timeline: Path | None = None, out_dir: Path | None = None) -> Path:
    ep = S.parse(path)
    chapter = chapter_id(path)
    bj = cfg.path("project", "audio") / chapter / "beats.json"
    beats = json.loads(bj.read_text("utf-8"))["beats"] if bj.exists() else {}
    starts = json.loads(Path(timeline).read_text("utf-8")) if timeline else {}
    gap = float(cfg.get("voice", "beat_gap"))
    cpm = float(cfg.get("voice", "chars_per_minute"))
    out_dir = out_dir or cfg.path("project", "output") / chapter
    out_dir.mkdir(parents=True, exist_ok=True)
    t, estimated = 0.0, not starts
    md = [f"# {ep.title or chapter}", "", f"> 逐字稿 · {'时间按配音时长估计' if estimated else '时间取自成片'}。"
          "难度：[L1] 主线 · [L2] 进阶 · [L3] 硬核支线；严谨度标签与讲义一致。", ""]
    chapters, srt, scene = [], [], None
    for b in ep.beats:
        disp, _, _ = S.split_beat(b.narration)
        info = beats.get(b.id, {})
        dur = info.get("duration") or (len(disp) / cpm * 60 + sum(s for _, s in b.pauses))
        start = float(starts.get(b.id, t))
        if b.scene != scene:
            scene = b.scene
            title = re.sub(r"（[^）]*\d+:\d+[^）]*）", "", scene or "").strip() or "开场"
            chapters.append(f"{_ts(start)} {title}")
            md += [f"## {title}  `{_ts(start)}`", ""]
        tags = " ".join(x for x in (f"[{b.level}]" if b.level else "", f"[{b.rigor}]" if b.rigor else "") if x)
        md.append(f"{srt_text(disp)}" + (f"  {tags}" if tags else ""))
        md.append("")
        if info.get("char_times"):
            for t0, t1, line in split_phrases(info["text"], info["char_times"], info["duration"]):
                srt.append([start + t0, start + t1, line])
        t = start + dur + gap
    (out_dir / "transcript.md").write_text("\n".join(md), encoding="utf-8")
    (out_dir / "chapters.txt").write_text("\n".join(chapters) + "\n", encoding="utf-8")
    if srt:
        write_srt(srt, out_dir / f"{chapter}.srt")
    print(f"[transcript] {out_dir / 'transcript.md'}；分段 {len(chapters)} 个 → chapters.txt"
          + (f"；字幕 {len(srt)} 条 → {chapter}.srt" if srt else "（还没有配音，没生成字幕）"))
    return out_dir / "transcript.md"
