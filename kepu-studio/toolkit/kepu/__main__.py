"""kepu：动漫 / 动画 / 游戏风中文科普视频的工作流工具。所有命令在项目根目录（有 kepu.toml 的地方）运行。

  init [目录] --engine anime|pixel|none   新建项目（复制工具、模板、渲染引擎）；--upgrade 只更新工具
  doctor                                  查环境
  lint 稿子 [-v] [--json]                 写稿时的检查：格式、念的一侧、多音字（不花钱）
  pron "一句话" …                          单句调试：每个多音字的决定、发给模型的文字
  lexicon add "长〔cháng〕子句" [--action force|leave|hold] [--note …] [--scope project|user]
  lexicon find 词 | lexicon export [--scope user|project]
  voice 稿子 [--dry] [--only 03 04] [--engine eleven|edge|say] [--max-chars N] [--force] [-v]
  quota                                   ElevenLabs 剩余额度
  greek audition [--letters σμ] [--dry] | greek ingest 选择.json | greek show
  earcheck build 稿子 | earcheck ingest 结果.json
  stats 稿子 [--cut L1]                   时长、节奏、提问间隔、句长、分级与严谨度
  transcript 稿子 [--timeline t.json]     逐字稿、B 站分段、.srt
  notes new 稿子 | notes build 讲义.md [--no-pdf]
  board 分镜 [--script 稿子]               分镜的节奏预算：大字卡、插卡、签名动作、推拉、白底段落，数量和间隔
  loudness 成片.mp4 [--fix] [-o 输出]      成片响度（−16 LUFS），--fix 两遍 loudnorm 校正，画面不重编码
  status [--html]                         整个系列一张表：每期走到哪一关、下一步跑什么；--html 写 review/status.html
  gate 稿子 [--stage script|voice|picture|release] [--final]
  art deal --subject "题材" [--n 4] [--engine anime|pixel] | art list   美术方向发牌
  selftest                                跑读音引擎的回归测试
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="kepu", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("init")
    p.add_argument("dir", nargs="?", default=".")
    p.add_argument("--engine", choices=["anime", "pixel", "none"], default="anime")
    p.add_argument("--name")
    p.add_argument("--upgrade", action="store_true")
    sub.add_parser("doctor")
    p = sub.add_parser("lint")
    p.add_argument("script", nargs="+")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--quick", action="store_true")
    p = sub.add_parser("pron")
    p.add_argument("text", nargs="+")
    p = sub.add_parser("lexicon")
    p.add_argument("op", choices=["add", "find", "export"])
    p.add_argument("arg", nargs="?")
    p.add_argument("--action", default="force", choices=["force", "leave", "hold"])
    p.add_argument("--note", default="")
    p.add_argument("--scope", default="project", choices=["project", "user"])
    p = sub.add_parser("voice")
    p.add_argument("script")
    p.add_argument("--dry", action="store_true")
    p.add_argument("--only", nargs="*")
    p.add_argument("--engine", choices=["eleven", "edge", "say"])
    p.add_argument("--max-chars", type=int)
    p.add_argument("--force", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    sub.add_parser("quota")
    p = sub.add_parser("greek")
    p.add_argument("op", choices=["audition", "ingest", "show"])
    p.add_argument("file", nargs="?")
    p.add_argument("--letters")
    p.add_argument("--dry", action="store_true")
    p.add_argument("--max-chars", type=int)
    p = sub.add_parser("earcheck")
    p.add_argument("op", choices=["build", "ingest"])
    p.add_argument("file")
    p = sub.add_parser("stats")
    p.add_argument("script")
    p.add_argument("--cut", choices=["L1", "L2", "L3"])
    p = sub.add_parser("transcript")
    p.add_argument("script")
    p.add_argument("--timeline")
    p = sub.add_parser("notes")
    p.add_argument("op", choices=["new", "build"])
    p.add_argument("file")
    p.add_argument("--no-pdf", action="store_true")
    p = sub.add_parser("gate")
    p.add_argument("script")
    p.add_argument("--stage", action="append", choices=["script", "voice", "picture", "release"])
    p.add_argument("--final", action="store_true")
    p = sub.add_parser("board")
    p.add_argument("storyboard")
    p.add_argument("--script")
    p = sub.add_parser("loudness")
    p.add_argument("file")
    p.add_argument("--fix", action="store_true")
    p.add_argument("-o", "--out")
    p = sub.add_parser("status")
    p.add_argument("--html", action="store_true")
    p = sub.add_parser("art")
    p.add_argument("op", choices=["deal", "list"])
    p.add_argument("--subject", default="")
    p.add_argument("--n", type=int, default=4)
    p.add_argument("--engine", choices=["anime", "pixel"])
    p.add_argument("--seed", type=int)
    sub.add_parser("selftest")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 0

    from . import config
    if a.cmd == "init":
        from .scaffold import init
        return init(Path(a.dir), a.engine, a.name, a.upgrade)
    cfg = config.load()
    if a.cmd == "doctor":
        from .scaffold import doctor
        return doctor(cfg)
    if a.cmd == "lint":
        from .lint import lint
        rc = 0
        for s in a.script:
            rc |= lint(Path(s), cfg, verbose=a.verbose, as_json=a.json)
        return rc
    if a.cmd == "pron":
        from .lint import pron_debug
        return pron_debug(a.text, cfg)
    if a.cmd == "lexicon":
        from .pron.lexicon import Lexicon, add_entry, layer_path
        if a.op == "add":
            if not a.arg:
                ap.error("lexicon add 需要一个词条，例如 \"长〔cháng〕子句\"")
            e, path = add_entry(a.arg, a.action, a.note, a.scope, cfg.root)
            print(f"[lexicon] {e.spec}\t{e.action}\t{e.note} → {path}")
            from .lint import lexicon_check
            return lexicon_check(e, cfg)
        lex = Lexicon(cfg.root)
        if a.op == "find":
            for e in sorted(lex.find(a.arg or ""), key=lambda e: e.clean):
                print(f"{e.spec}\t{e.action}\t{e.layer}\t{e.note}")
            return 0
        path = layer_path(a.scope if a.scope == "user" else "project", cfg.root)
        print(path.read_text(encoding="utf-8") if path and path.exists() else f"[lexicon] {path} 是空的")
        return 0
    if a.cmd == "voice":
        from .voice import run
        return run(Path(a.script), cfg, dry=a.dry, only=a.only, engine=a.engine, max_chars=a.max_chars, force=a.force,
                   verbose=a.verbose)
    if a.cmd == "quota":
        from .voice import main_quota
        return main_quota(cfg)
    if a.cmd == "greek":
        from . import greek_audition as G
        if a.op == "audition":
            return G.audition(cfg, a.letters, a.dry, a.max_chars)
        if a.op == "ingest":
            return G.ingest(Path(a.file), cfg)
        from .pron.greek import greek_say, greek_table, load_profile
        prof = load_profile(cfg.voice_key, cfg.root)
        for ch, g in greek_table().items():
            say, st = greek_say(ch, cfg.get("pron", "greek"), prof)
            print(f"{ch}  {g['name']:8s} → {say:10s} {st}")
        return 0
    if a.cmd == "earcheck":
        from . import earcheck as E
        return 0 if a.op == "build" and E.build(Path(a.file), cfg) else E.ingest(Path(a.file), cfg) if a.op == "ingest" else 1
    if a.cmd == "stats":
        from .levels import stats
        return stats(Path(a.script), cfg, a.cut)
    if a.cmd == "transcript":
        from .transcript import build
        build(Path(a.script), cfg, Path(a.timeline) if a.timeline else None)
        return 0
    if a.cmd == "notes":
        from . import notes as N
        if a.op == "new":
            N.new(Path(a.file), cfg)
        else:
            N.build(Path(a.file), cfg, pdf=not a.no_pdf)
        return 0
    if a.cmd == "gate":
        from .gate import check
        return check(Path(a.script), cfg, a.stage, a.final)
    if a.cmd == "board":
        from .board import check as board_check
        return 1 if board_check(Path(a.storyboard), cfg, Path(a.script) if a.script else None)[0] else 0
    if a.cmd == "loudness":
        from .loudness import main as loud
        return loud(Path(a.file), cfg, a.fix, Path(a.out) if a.out else None)
    if a.cmd == "status":
        from .status import show
        return show(cfg, a.html)
    if a.cmd == "art":
        from . import art
        ds = art.directions() if a.op == "list" else art.deal(a.subject, a.n, a.engine, a.seed)
        print("\n\n".join(art.show(d) for d in ds))
        return 0
    if a.cmd == "selftest":
        import unittest
        tests = Path(__file__).resolve().parents[1] / "tests"
        suite = unittest.defaultTestLoader.discover(str(tests))
        r = unittest.TextTestRunner(verbosity=1).run(suite)
        return 0 if r.wasSuccessful() else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
