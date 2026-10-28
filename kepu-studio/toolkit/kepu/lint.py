"""写稿时的检查（不花钱、不联网）：格式、念的一侧、多音字。有拦下的就退出码 1。

    kepu lint script/episodes/ep01.md            # 报告：拦下的（带现成的修法）、送拼音的
    kepu lint script/episodes/ep01.md -v         # 再列出每一处已经定下的读音
    kepu lint script/episodes/ep01.md --json     # 给工具读
    kepu pron "这一行为真，长子句"                 # 单句调试：每个多音字的决定和发给模型的文字
"""
from __future__ import annotations

import json
from pathlib import Path

from . import script as S
from .pron.speak import describe, prepare
from .util import pad
from .voice import prep_beat, suggestion


def lint(path: Path, cfg, verbose=False, as_json=False, quiet=False) -> int:
    ep = S.parse(path)
    pcfg = cfg.pron()
    rows, n_hold, n_pinyin, n_auto, chars = [], 0, 0, 0, 0
    problems = [f"第 {ln} 行：{msg}" for ln, msg in ep.problems]
    for b in ep.beats:
        for msg in S.syntax_problems(b.narration):
            problems.append(f"beat {b.id}（第 {b.line} 行）：{msg}")
        if not b.narration:
            continue
        bp = prep_beat(b, pcfg)
        p = bp.p
        chars += len(p.clean)
        hold = [s for s in p.spots if s.open]
        pinyin = [s for s in p.spots if s.status == "pinyin"]
        auto = [s for s in p.spots if s.status == "auto"]
        n_hold += len(hold) + len(p.held)
        n_pinyin += len(pinyin)
        n_auto += len(auto)
        rows.append({"beat": b.id, "line": b.line, "hold": [_spot_json(p.clean, s) for s in hold],
                     "held": [{"ctx": c, "why": w} for c, w in p.held], "pinyin": [_spot_json(p.clean, s) for s in pinyin],
                     "auto": [_spot_json(p.clean, s) for s in auto], "notes": p.notes,
                     "decided": [_spot_json(p.clean, s) for s in p.spots if s.status == "ok" and s.source != "default"]})
        if as_json or quiet:
            continue
        if hold or p.held or pinyin or (verbose and (auto or p.notes)):
            print(f"beat {b.id}（第 {b.line} 行）")
        for s in hold:
            print("  " + describe(s))
            print("    " + suggestion(p.clean, s))
        for c, w in p.held:
            print(f"  ✗ 读法   {pad(c, 34)}{w}")
        for s in pinyin:
            print("  " + describe(s) + (f"；更稳：{s.rewrite}" if s.rewrite else ""))
        if verbose:
            for s in p.spots:
                if s.status in ("ok", "auto") and s.source not in ("default",):
                    print("  " + describe(s))
            for n in p.notes:
                print(f"  ? {n}")
    if as_json:
        print(json.dumps({"script": str(path), "beats": len(ep.beats), "chars": chars, "problems": problems,
                          "hold": n_hold, "pinyin": n_pinyin, "auto": n_auto, "rows": rows}, ensure_ascii=False, indent=1))
    elif not quiet:
        for pr in problems:
            print(f"✗ 格式   {pr}")
        cpm = float(cfg.get("voice", "chars_per_minute"))
        print(f"{path.name}：{len(ep.beats)} 个 beat，念 {chars:,} 字，约 {chars / cpm:.1f} 分钟（{cpm:.0f} 字/分钟）；"
              f"拦下 {n_hold}，送拼音 {n_pinyin}（合成后进耳检包），交给模型的非默认读音 {n_auto}"
              + ("" if n_hold or problems else "。可以合成。"))
    return 1 if (n_hold or problems) else 0


def _spot_json(text, s):
    return {"i": s.i, "char": s.char, "ctx": s.ctx, "reading": s.reading, "source": s.source, "status": s.status,
            "say": s.say, "why": s.why, "suggest": s.suggest, "rewrite": s.rewrite, "entry": s.entry,
            "fix": suggestion(text, s) if s.open else ""}


def pron_debug(texts: list[str], cfg) -> int:
    pcfg = cfg.pron()
    rc = 0
    for t in texts:
        d, spoken, _ = S.split_beat(t)
        p = prepare(spoken, pcfg)
        print(f"显示：{d}\n念的：{p.clean}\n发给模型：{p.tts}")
        for s in p.spots:
            print("  " + describe(s))
            if s.open:
                print("    " + suggestion(p.clean, s))
                rc = 1
        for c, w in p.held:
            print(f"  ✗ 读法   {pad(c, 34)}{w}")
            rc = 1
        for n in p.notes:
            print(f"  ? {n}")
    return rc
