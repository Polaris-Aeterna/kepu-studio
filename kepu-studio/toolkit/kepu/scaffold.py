"""新建项目（kepu init）与环境体检（kepu doctor）。

    python3 <插件>/toolkit/kepu_run.py init 我的系列 --engine anime    # 新建项目，复制工具到 .kepu/toolkit，生成 ./kepu
    ./kepu doctor                                                     # 查 Python、ffmpeg、Chrome、API key、引擎依赖
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .util import PKG, USER_DIR

TEMPLATES = PKG / "templates" / "project"
PLUGIN_ROOT = PKG.parent.parent                 # <plugin>/toolkit/kepu -> <plugin>
ENGINES = {"anime": ("engine-anime", "engine", "engine/audio"), "pixel": ("engine-pixel", "pixel", "audio"),
           "none": (None, None, "audio")}

LAUNCHER_SH = """#!/bin/sh
# kepu：kepu-studio 插件的项目工具（复制在 .kepu/toolkit）。用法：./kepu --help
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="${KEPU_PYTHON:-python3}"
PYTHONPATH="$DIR/.kepu/toolkit${PYTHONPATH:+:$PYTHONPATH}" exec "$PY" -m kepu "$@"
"""
LAUNCHER_BAT = """@echo off
rem kepu：kepu-studio 插件的项目工具。用法：kepu --help
set PYTHONPATH=%~dp0.kepu\\toolkit;%PYTHONPATH%
py -3 -m kepu %*
"""


def _render(text: str, **kw) -> str:
    for k, v in kw.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def vendor_toolkit(root: Path) -> Path:
    """Copy (or refresh) the toolkit into <root>/.kepu/toolkit and write the launchers."""
    dst = root / ".kepu" / "toolkit"
    src = PKG.parent
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tools"))
    (root / "kepu").write_text(LAUNCHER_SH, encoding="utf-8")
    os.chmod(root / "kepu", 0o755)
    (root / "kepu.bat").write_text(LAUNCHER_BAT, encoding="utf-8")
    return dst


def init(target: Path, engine: str = "anime", name: str | None = None, upgrade: bool = False) -> int:
    target = target.resolve()
    if upgrade:
        if not (target / "kepu.toml").exists():
            raise SystemExit(f"[init] {target} 不是 kepu 项目（没有 kepu.toml）")
        dst = vendor_toolkit(target)
        print(f"[init] 工具更新到 {dst}（项目的稿子、词典、配音都没动）")
        return 0
    if (target / "kepu.toml").exists():
        raise SystemExit(f"[init] {target} 已经是 kepu 项目；更新工具用 --upgrade")
    target.mkdir(parents=True, exist_ok=True)
    name = name or target.name
    tmpl, engine_dir, audio = ENGINES[engine]
    for p in TEMPLATES.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(TEMPLATES)
        out = target / rel
        if out.exists():
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_render(p.read_text(encoding="utf-8"), NAME=name, ENGINE=engine, AUDIO=audio), encoding="utf-8")
    for d in ("notes", "review", "output", "assets"):
        (target / d).mkdir(exist_ok=True)
    (target / "pron").mkdir(exist_ok=True)
    lex = target / "pron" / "lexicon.tsv"
    if not lex.exists():
        lex.write_text("# 项目读音词典（kepu）。每行：词条（带读音标记）<TAB>动作 force|leave|hold<TAB>备注。只增改，不删别人的条目。\n"
                       "# 例：长〔cháng〕子句\tforce\t分词陷阱\n", encoding="utf-8")
    (target / "CLAUDE.md").exists() or (target / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
    (target / ".env.example").write_text("ELEVENLABS_API_KEY=把你的 key 填在复制出来的 .env 里，不要提交、不要发给别人\n",
                                         encoding="utf-8")
    gi = target / ".gitignore"
    if not gi.exists():
        gi.write_text(".env\n.kepu/\n**/_cache/\n**/__pycache__/\noutput/\n*.wav\n*.mp4\n", encoding="utf-8")
    vendor_toolkit(target)
    if tmpl:
        src = PLUGIN_ROOT / "templates" / tmpl
        if src.exists():
            shutil.copytree(src, target / engine_dir, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            print(f"[init] 渲染引擎模板 {tmpl} → {engine_dir}/（说明在 {engine_dir}/README.md）")
        else:
            print(f"[init] 没找到引擎模板 {src}：从插件目录运行 init，或者手动复制 templates/{tmpl}")
    print(f"[init] 新项目 {target}\n  下一步：cd 进去，./kepu doctor 查环境；把 .env.example 复制成 .env 填 key；"
          f"在 Claude 里说“开一个新系列”或运行 /kepu-studio:new")
    return 0


def _ok(flag, what, detail=""):
    print(f"  {'✓' if flag is True else ('!' if flag is None else '✗')} {what}{('：' + detail) if detail else ''}")
    return flag is not False


def doctor(cfg) -> int:
    print("kepu doctor")
    good = True
    good &= _ok(sys.version_info >= (3, 9), "Python ≥ 3.9", platform.python_version())
    ff = shutil.which("ffmpeg")
    good &= _ok(bool(ff), "ffmpeg（配音转码、拼接、响度）", ff or "没装：macOS 用 brew install ffmpeg，Windows 用 winget install ffmpeg")
    from .notes import chrome
    c = chrome()
    _ok(True if c else None, "Chrome / Edge（讲义导出 PDF）", c or "没找到；讲义仍可用浏览器打印")
    t = time.time()
    from . import seg
    seg.words()
    _ok(True, "读音词表", f"{len(seg.words()[0]):,} 词，{time.time() - t:.1f} 秒（第一次会写缓存到 {USER_DIR / 'cache'}）")
    if cfg.root is None:
        _ok(None, "kepu 项目", "当前目录不在 kepu 项目里（没有 kepu.toml）；kepu init 新建一个")
        return 0 if good else 1
    _ok(True, "kepu 项目", str(cfg.root))
    from .lint import lint  # noqa: F401  (import check)
    key = bool(os.environ.get("ELEVENLABS_API_KEY")) or (cfg.path("voice", "env_file").exists() and
                                                        "ELEVENLABS_API_KEY" in cfg.path("voice", "env_file").read_text(encoding="utf-8"))
    _ok(True if key else None, "ElevenLabs API key", "已配置（不显示）" if key else "没配置：只能用 --engine edge 做免费占位配音")
    eng = cfg.get("project", "engine")
    if eng == "anime":
        venv = cfg.root / "engine" / ".venv" / "bin" / "manimgl"
        _ok(True if venv.exists() else None, "ManimGL 1.7.2（engine/.venv）",
            "已装" if venv.exists() else "没装：见 engine/README.md 的安装一节（python -m venv engine/.venv && engine/.venv/bin/pip install -r engine/requirements.txt）")
        tex = shutil.which("latex") or shutil.which("pdflatex")
        _ok(True if tex else None, "LaTeX（公式）", tex or "没装：macOS 装 MacTeX / BasicTeX")
        song = Path("/System/Library/Fonts/Supplemental/Songti.ttc").exists()
        _ok(True if song or platform.system() != "Darwin" else None, "宋体（Songti SC）", "有" if song else "没找到")
    elif eng == "pixel":
        try:
            import numpy  # noqa: F401
            from PIL import Image  # noqa: F401
            _ok(True, "numpy + Pillow（像素引擎）")
        except ImportError:
            _ok(None, "numpy + Pillow（像素引擎）", "pip install numpy pillow")
        fonts = cfg.root / "pixel" / "assets" / "fonts"
        has = fonts.exists() and any(fonts.glob("*.ttf"))
        _ok(True if has else None, "像素引擎字体", "有" if has else f"放 NotoSansSC-Bold.ttf / Regular.ttf 到 {fonts}（见 pixel/README.md）")
    try:
        r = subprocess.run([sys.executable, "-c", "import edge_tts"], capture_output=True)
        _ok(True if r.returncode == 0 else None, "edge-tts（免费占位配音，可选）", "有" if r.returncode == 0 else "pip install edge-tts")
    except OSError:
        pass
    return 0 if good else 1
