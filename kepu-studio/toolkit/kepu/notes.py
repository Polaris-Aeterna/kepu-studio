"""讲义：先写讲义、再写稿子；屏幕上的定理从讲义里复制（《地基之下》的规矩）。

    kepu notes new script/episodes/ep01.md      # → notes/ep01.md：按本期场景、分级、术语生成骨架
    kepu notes build notes/ep01.md              # → output/ep01/notes.html（可打印）和 notes.pdf（需要 Chrome / Edge）

结构（固定）：本期地图（三档目标）→ 各节（主线正文 + 进阶框 + 硬核支线框，定理带严谨度）→ 常见误解 / 实情 →
习题（★ 到 ★★★，难题给提示，答案在最后）→ 术语表（中文、英文、读音）→ 延伸阅读（只写有把握的出处）。
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from . import script as S
from .md import render
from .pron.greek import greek_table
from .util import ASSETS
from .voice import chapter_id

KATEX = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist"


def new(script: Path, cfg) -> Path:
    ep = S.parse(script)
    chapter = chapter_id(script)
    out = cfg.path("project", "notes") / f"{chapter}.md"
    if out.exists():
        raise SystemExit(f"[notes] {out} 已经存在，不覆盖")
    t = (ASSETS / "notes_template.md").read_text(encoding="utf-8")
    secs = []
    for sc in ep.scenes or ["正文"]:
        bs = [b for b in ep.beats if b.scene == sc]
        lv = sorted({b.level for b in bs if b.level})
        rg = sorted({b.rigor for b in bs if b.rigor})
        name = re.sub(r"（[^）]*\d+:\d+[^）]*）", "", sc).strip()
        secs.append(f"## {name}\n\n<!-- 对应视频：{name}；beat {bs[0].id if bs else ''}–{bs[-1].id if bs else ''}；"
                    f"难度 {'/'.join(lv) or '未标'}；严谨度 {'/'.join(rg) or '未标'} -->\n\n"
                    "主线正文：先给具体例子，再抽象，最后用抽象工具回头看这个例子。\n\n"
                    "::: l2 进阶\n（给本科理工读者：精确定义、完整论证的关键一步）\n:::\n\n"
                    "::: l3 硬核支线\n（可以跳过；跳过不影响后面。留给想深挖的人：原论文的技术细节、推广、开放问题）\n:::\n")
    used = sorted({c for b in ep.beats for c in S.split_beat(b.narration)[0] if c in greek_table()})
    greek = "\n".join(f"| {c} | {greek_table()[c]['name']} | 英文读音 |" for c in used)
    t = (t.replace("{{TITLE}}", ep.title or chapter).replace("{{SECTIONS}}", "\n".join(secs))
         .replace("{{GREEK}}", greek or "| （本期没有希腊字母） | | |"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(t, encoding="utf-8")
    print(f"[notes] {out}：{len(secs)} 节的骨架。写完用 kepu notes build {out}")
    return out


def chrome() -> str | None:
    for c in (os.environ.get("CHROME_PATH"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", "/Applications/Chromium.app/Contents/MacOS/Chromium",
              shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser"), shutil.which("msedge"),
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"):
        if c and Path(c).exists():
            return c
    return None


def build(src: Path, cfg, pdf: bool = True) -> Path:
    text = Path(src).read_text(encoding="utf-8")
    title = next((m.group(1) for m in re.finditer(r"^#\s+(.*)$", text, re.M)), Path(src).stem)
    body = render(text)
    css = (ASSETS / "notes.css").read_text(encoding="utf-8")
    page = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="{KATEX}/katex.min.css">
<style>{css}</style></head>
<body><main class="notes">{body}</main>
<script defer src="{KATEX}/katex.min.js"></script>
<script defer src="{KATEX}/contrib/auto-render.min.js"
  onload="renderMathInElement(document.body,{{delimiters:[{{left:'$$',right:'$$',display:true}},{{left:'$',right:'$',display:false}},{{left:'\\\\(',right:'\\\\)',display:false}}],throwOnError:false}});document.body.dataset.math='done'"></script>
</body></html>"""
    out_dir = cfg.path("project", "output") / Path(src).stem
    out_dir.mkdir(parents=True, exist_ok=True)
    h = out_dir / "notes.html"
    h.write_text(page, encoding="utf-8")
    for m in re.finditer(r'<img src="([^"]+)"', body):              # copy local pictures next to the page
        p = (Path(src).parent / m.group(1))
        if p.exists() and not (out_dir / m.group(1)).exists():
            (out_dir / m.group(1)).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, out_dir / m.group(1))
    print(f"[notes] {h}")
    if pdf:
        c = chrome()
        if not c:
            print("[notes] 没找到 Chrome / Edge：用浏览器打开 notes.html，打印成 PDF（设置 CHROME_PATH 可以自动生成）")
            return h
        p = out_dir / "notes.pdf"
        subprocess.run([c, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--virtual-time-budget=15000",
                        f"--print-to-pdf={p}", h.resolve().as_uri()], capture_output=True, timeout=180)
        print(f"[notes] {p}" if p.exists() else "[notes] PDF 生成失败：用浏览器打开 notes.html 手动打印")
    return h
