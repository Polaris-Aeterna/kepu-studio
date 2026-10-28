"""一期的关卡：四个阶段一张表，有 ✗ 就退出码 1（来源：《地基之下》production/pixel/gate.py）。

    kepu gate script/episodes/ep01.md                # 全部阶段
    kepu gate script/episodes/ep01.md --stage voice  # 只查一个阶段：script / voice / picture / release
    kepu gate script/episodes/ep01.md --final        # 发布前：占位配音（edge / say）也算失败

  script   格式对、没有拦下的多音字和读法问题                 kepu lint
  voice    每个 beat 都有配音；配音是“当前稿子”合成的（稿子改了、录音没重做会被抓出来）；耳检做过、没有未处理的“错”
  picture  引擎的检查（ManimGL 渲染日志没有超时 / 节奏警告；像素引擎的遮挡、出框、空白检查）
  release  成片比配音和稿子新；字幕没有花括号；逐字稿、分段、讲义、封面都在
状态看文件（修改时间、缓存键、大小），不看“我记得做过”。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import script as S
from .lint import lint
from .voice import chapter_id, prep_beat

OK, BAD, SKIP, WARN = "✓", "✗", "–", "!"


def _row(rows, stage, what, status, detail=""):
    rows.append((stage, what, status, detail))


def check(script: Path, cfg, stages=None, final=False) -> int:
    stages = stages or ["script", "voice", "picture", "release"]
    chapter = chapter_id(script)
    rows = []
    ep = S.parse(script)
    audio = cfg.path("project", "audio") / chapter
    bj = audio / "beats.json"
    out = cfg.path("project", "output") / chapter
    if "script" in stages:
        rc = lint(script, cfg, quiet=True)
        _row(rows, "script", "格式与读音（kepu lint）", OK if rc == 0 else BAD, "" if rc == 0 else "跑 kepu lint 看拦下的地方")
    if "voice" in stages:
        if not bj.exists():
            _row(rows, "voice", "配音", BAD, f"没有 {bj}")
        else:
            meta = json.loads(bj.read_text("utf-8"))["beats"]
            pcfg = cfg.pron()
            missing, stale, ph = [], [], []
            for b in ep.beats:
                if not b.narration:
                    continue
                info = meta.get(b.id)
                if not info:
                    missing.append(b.id)
                    continue
                bp = prep_beat(b, pcfg)
                if info.get("tts") != bp.tts:
                    stale.append(b.id)
                if info.get("placeholder") or info.get("engine") in ("edge", "say"):
                    ph.append(b.id)
            _row(rows, "voice", "每个 beat 都有配音", OK if not missing else BAD, " ".join(missing))
            _row(rows, "voice", "配音和当前稿子一致", OK if not stale else BAD,
                 ("稿子或读音决定改过，重新合成：kepu voice --only " + " ".join(stale)) if stale else "")
            _row(rows, "voice", "不是占位配音", (BAD if final else WARN) if ph else OK, " ".join(ph))
        st = cfg.path("project", "review") / "earcheck" / chapter / "status.json"
        if st.exists():
            s = json.loads(st.read_text("utf-8"))
            _row(rows, "voice", "耳检", OK if not s.get("bad") else BAD,
                 f"听了 {s.get('checked', 0)} 处，错 {s.get('bad', 0)}" + ("（改完重录再耳检）" if s.get("bad") else ""))
        else:
            _row(rows, "voice", "耳检", BAD if final else WARN, f"还没做：kepu earcheck build {script}")
    if "picture" in stages:
        eng = cfg.get("project", "engine")
        logs = list((cfg.root or Path(".")).glob(f"episodes/{chapter}*/**/*.log")) if eng == "anime" else []
        if eng == "anime":
            bad = [p.name for p in logs if re.search(r"WARNING \[(narrated|eva)\]", p.read_text(errors="ignore"))]
            _row(rows, "picture", "渲染日志（超时 / 节奏警告）", (BAD if bad else OK) if logs else WARN,
                 " ".join(bad[:6]) if bad else ("" if logs else "没找到渲染日志"))
        elif eng == "pixel":
            _row(rows, "picture", "遮挡 / 出框 / 空白", WARN, "在像素引擎目录跑 build --check、occlusion、bounds（见 engine-pixel 说明）")
        else:
            _row(rows, "picture", "画面检查", SKIP, "没有内置引擎：用你自己的检查")
        sheets = list(out.glob("contact_sheet*.png")) + list((cfg.root or Path(".")).glob(f"episodes/{chapter}*/contact_sheet*.png"))
        _row(rows, "picture", "联系表（逐 beat 抽帧，自我批评过）", OK if sheets else WARN, "" if sheets else "还没有 contact_sheet*.png")
    if "release" in stages:
        vids = sorted(out.glob("*.mp4"), key=lambda p: p.stat().st_mtime) if out.exists() else []
        if not vids:
            _row(rows, "release", "成片", BAD if final else WARN, f"{out} 里还没有 mp4")
        else:
            v = vids[-1]
            newer = all(v.stat().st_mtime >= p.stat().st_mtime for p in (bj, script) if p.exists())
            _row(rows, "release", f"成片比配音和稿子新（{v.name}）", OK if newer else BAD, "" if newer else "重渲染 / 重拼")
        srts = list(out.glob("*.srt")) if out.exists() else []
        if srts:
            bad = [p.name for p in srts if "{" in p.read_text(encoding="utf-8", errors="ignore")]
            _row(rows, "release", "字幕可读（没有花括号）", OK if not bad else BAD, " ".join(bad))
        for f, what in (("transcript.md", "逐字稿"), ("chapters.txt", "B 站分段"), ("notes.pdf", "讲义 PDF"),
                        ("cover_16x9.png", "封面 16:9"), ("cover_4x3.png", "封面 4:3"), ("publish.md", "投稿文案")):
            _row(rows, "release", what, OK if (out / f).exists() else WARN, "" if (out / f).exists() else f"没有 {f}")
    w = max(len(r[1]) for r in rows) if rows else 10
    print(f"关卡 · {chapter}")
    cur = None
    for stage, what, st, detail in rows:
        if stage != cur:
            print(f"  [{stage}]")
            cur = stage
        print(f"    {st} {what}{' ' * max(1, w - len(what) + 2)}{detail}")
    bad = sum(1 for r in rows if r[2] == BAD)
    print(f"  {'通过' if not bad else f'{bad} 项没过'}" + ("（! 是提醒，发布前用 --final 会变成 ✗）" if any(r[2] == WARN for r in rows) else ""))
    return 1 if bad else 0
