"""整个系列的进度一张表：每一期走到哪一关、卡在哪、下一步跑什么（不花钱、不联网，只看文件）。

    kepu status              # 终端里的表
    kepu status --html       # 另外写 review/status.html（深浅色都能看，可以发给合作者）

每一格的依据都是文件，不是“我记得做过”：
  稿子   kepu lint 有没有拦下的地方        分镜   kepu board 的节奏预算
  配音   每个 beat 都有、而且是当前稿子合成的    耳检   review/earcheck/<期>/status.json
  讲义   notes/<期>.md 和 output/<期>/notes.pdf  成片   output/<期>/ 里比配音和稿子都新的 mp4
"""
from __future__ import annotations

import html
import json
import re
import time
from pathlib import Path

from . import script as S
from .util import pad, width
from .voice import chapter_id, ledger, prep_beat

DONE, TODO, BAD, NONE = "done", "todo", "bad", "none"
MARK = {DONE: "✓", TODO: "·", BAD: "✗", NONE: "–"}
STAGES = [("script", "稿子"), ("board", "分镜"), ("voice", "配音"), ("ear", "耳检"), ("notes", "讲义"), ("release", "成片")]


def _rel(p: Path, root: Path | None) -> Path:
    """p relative to the project root when it lives inside it (commands read better), else p itself."""
    try:
        return p.relative_to(root) if root and p.is_absolute() else p
    except ValueError:
        return p


def episodes(cfg) -> list[Path]:
    d = cfg.path("project", "scripts")
    return sorted(p for p in d.glob("*.md") if not p.name.startswith(("_", "README")))


def _script(ep, cfg):
    pcfg, hold, chars, tts = cfg.pron(), len(ep.problems), 0, {}
    for b in ep.beats:
        hold += len(S.syntax_problems(b.narration))
        if not b.narration:
            continue
        bp = prep_beat(b, pcfg)
        hold += sum(1 for s in bp.p.spots if s.open) + len(bp.p.held)
        chars += len(bp.p.clean)
        tts[b.id] = bp.tts
    return hold, chars, tts


def episode_row(path: Path, cfg) -> dict:
    ep = S.parse(path)
    ch = chapter_id(path)
    hold, chars, tts = _script(ep, cfg)
    narrated = [b.id for b in ep.beats if b.narration]
    cpm = float(cfg.get("voice", "chars_per_minute"))
    title = re.sub(r"^第\s*\S+\s*[期集话回]\s*[　:：·\s]*", "", ep.title or "").strip()
    rel = _rel(path, cfg.root)
    row = {"chapter": ch, "title": title, "beats": len(ep.beats), "chars": chars, "minutes": chars / cpm, "real": False,
           "cells": {}, "next": ""}
    c = row["cells"]
    c["script"] = (BAD, f"拦下 {hold}") if hold else (DONE, f"{len(ep.beats)} beat")
    from .board import storyboard_for
    sb = storyboard_for(path, cfg)
    if sb.exists():
        from .board import check
        nbad, _ = check(sb, cfg, path, quiet=True)
        c["board"] = (BAD, f"{nbad} 项超预算") if nbad else (DONE, "预算内")
    else:
        c["board"] = (TODO, "")
    bj = cfg.path("project", "audio") / ch / "beats.json"
    if bj.exists():
        meta = json.loads(bj.read_text("utf-8")).get("beats", {})
        have = [i for i in narrated if i in meta]
        stale = [i for i in have if meta[i].get("tts") != tts.get(i)]
        ph = any(meta[i].get("placeholder") for i in have)
        dur = sum(float(v.get("duration", 0)) for v in meta.values())
        if dur:
            row["minutes"], row["real"] = dur / 60, True
        if stale:
            c["voice"] = (BAD, f"{len(stale)} 条过期")
        elif len(have) < len(narrated):
            c["voice"] = (TODO, f"{len(have)}/{len(narrated)}")
        else:
            c["voice"] = (DONE, "占位" if ph else "正式")
    else:
        c["voice"] = (TODO, "")
    st = cfg.path("project", "review") / "earcheck" / ch / "status.json"
    if st.exists():
        s = json.loads(st.read_text("utf-8"))
        c["ear"] = (BAD, f"错 {s['bad']}") if s.get("bad") else (DONE, f"{s.get('checked', 0)} 处")
    else:
        c["ear"] = (TODO, "")
    out = cfg.path("project", "output") / ch
    md = cfg.path("project", "notes") / f"{ch}.md"
    c["notes"] = (DONE, "PDF") if (out / "notes.pdf").exists() else (TODO, "草稿") if md.exists() else (TODO, "")
    vids = sorted(out.glob("*.mp4"), key=lambda p: p.stat().st_mtime) if out.exists() else []
    if vids:
        newer = all(vids[-1].stat().st_mtime >= p.stat().st_mtime for p in (bj, path) if p.exists())
        c["release"] = (DONE, vids[-1].name) if newer else (BAD, "比配音旧")
    else:
        c["release"] = (TODO, "")
    nxt = {"script": f"kepu lint {rel}", "board": f"写分镜 {sb.name}" if not sb.exists() else f"kepu board {_rel(sb, cfg.root)}",
           "voice": f"kepu voice {rel} --dry", "ear": f"kepu earcheck build {rel}", "notes": f"kepu notes new {rel}",
           "release": "渲染、拼接，然后 kepu gate --final"}
    first = next((k for k, _ in STAGES if c[k][0] == BAD), None) or next((k for k, _ in STAGES if c[k][0] == TODO), None)
    row["next"] = nxt[first] if first else "可以发布"
    return row


def collect(cfg) -> dict:
    rows = [episode_row(p, cfg) for p in episodes(cfg)]
    spent = {}
    for r in ledger(cfg):
        spent[r["chapter"]] = spent.get(r["chapter"], 0) + r["chars"]
    for r in rows:
        r["spent"] = spent.get(r["chapter"], 0)
    return {"name": cfg.get("project", "name") or (cfg.root.name if cfg.root else ""), "engine": cfg.get("project", "engine"),
            "rows": rows, "spent": sum(spent.values()), "date": time.strftime("%Y-%m-%d %H:%M")}


def show(cfg, as_html: bool = False) -> int:
    d = collect(cfg)
    rows = d["rows"]
    if not rows:
        print(f"[status] {cfg.path('project', 'scripts')} 里还没有稿子")
        return 0
    tw = min(18, max(width(r["title"] or r["chapter"]) for r in rows))
    print(f"{d['name']} · {len(rows)} 期 · 引擎 {d['engine']}" + (f" · 已花 {d['spent']:,} 字符" if d["spent"] else ""))
    print("  " + pad("期", 10) + pad("标题", tw + 2) + pad("时长", 8) + "".join(pad(n, 10) for _, n in STAGES) + "下一步")
    for r in rows:
        t = r["title"] or ""
        while width(t) > tw:
            t = t[:-1]
        dur = f"{r['minutes']:.1f}′" + ("" if r["real"] else "≈")
        cells = "".join(pad(_cell(r["cells"][k]), 10) for k, _ in STAGES)
        print("  " + pad(r["chapter"], 10) + pad(t, tw + 2) + pad(dur, 8) + cells + r["next"])
    total = sum(r["minutes"] for r in rows)
    done = sum(1 for r in rows if r["next"] == "可以发布")
    print(f"  合计约 {total:.0f} 分钟；{done}/{len(rows)} 期可以发布。✓ 完成  · 还没做  ✗ 有问题（≈ 按字数估的时长）")
    if as_html:
        p = write_html(d, cfg)
        print(f"[status] → {p}")
    return 1 if any(c[0] == BAD for r in rows for c in r["cells"].values()) else 0


def _cell(c) -> str:
    t = MARK[c[0]] + (" " + c[1] if c[0] == BAD else "")
    while width(t) > 9:
        t = t[:-1]
    return t


def write_html(d: dict, cfg) -> Path:
    out = cfg.path("project", "review") / "status.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    e = html.escape
    body = []
    for r in d["rows"]:
        cells = "".join(f'<td class="{r["cells"][k][0]}"><span class="dot"></span><span class="txt">{e(r["cells"][k][1])}</span></td>'
                        for k, _ in STAGES)
        n_done = sum(1 for k, _ in STAGES if r["cells"][k][0] == DONE)
        body.append(f'<tr><th><span class="ep">{e(r["chapter"])}</span><span class="tt">{e(r["title"])}</span></th>'
                    f'<td class="num">{r["minutes"]:.1f}{"" if r["real"] else "≈"}</td>{cells}'
                    f'<td class="next"><div class="meter"><i style="width:{n_done / len(STAGES):.0%}"></i></div>'
                    f'<code>{e(r["next"])}</code></td></tr>')
    heads = "".join(f"<th>{e(n)}</th>" for _, n in STAGES)
    page = (Path(__file__).parent / "assets" / "status.html").read_text(encoding="utf-8")
    page = (page.replace("__NAME__", e(d["name"])).replace("__META__", e(f"{len(d['rows'])} 期 · 引擎 {d['engine']} · "
                                                                            f"{d['date']}" + (f" · 已花 {d['spent']:,} 字符"
                                                                                              if d["spent"] else "")))
            .replace("__HEADS__", heads).replace("__ROWS__", "\n".join(body)))
    out.write_text(page, encoding="utf-8")
    return out
