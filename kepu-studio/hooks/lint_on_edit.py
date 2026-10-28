#!/usr/bin/env python3
"""kepu-studio 的 PostToolUse 钩子：Claude 写完或改完一份稿子（kepu 项目里、带“台词/旁白”的 .md）之后，自动跑读音检查。

只有真的有拦下的地方才说话（退出码 2，把摘要交给 Claude）；别的文件、别的项目、没装好的环境，一律安静地放过。
这样多音字检查不靠“记得去跑”：每改一次稿子就查一次。"""
import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        d = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return 0
    fp = (d.get("tool_input") or {}).get("file_path") or ""
    if not fp.endswith(".md"):
        return 0
    p = Path(fp)
    if not p.is_file():
        return 0
    root = next((q for q in [p.parent, *p.parents] if (q / "kepu.toml").exists()), None)
    if root is None:
        return 0
    text = p.read_text(encoding="utf-8", errors="ignore")
    if not any(k in text for k in ("台词：", "台词:", "**旁白**", "旁白：", "Narration:")):
        return 0
    tk = root / ".kepu" / "toolkit"
    if not (tk / "kepu").is_dir():
        tk = Path(__file__).resolve().parents[1] / "toolkit"
    env = dict(os.environ, PYTHONPATH=str(tk))
    try:
        r = subprocess.run([sys.executable, "-m", "kepu", "lint", str(p), "--json"], cwd=str(root), env=env,
                           capture_output=True, text=True, timeout=55)
        res = json.loads(r.stdout)
    except Exception:  # noqa: BLE001
        return 0
    if not res.get("hold") and not res.get("problems"):
        return 0
    out = [f"[kepu lint] {p.name}：拦下 {res.get('hold', 0)} 处、格式问题 {len(res.get('problems', []))} 处——合成前必须解决"
           "（改写绕开 / 稿子里标 字〔读音〕 / kepu lexicon add；见 kepu-studio:pronounce）"]
    out += ["  ✗ " + x for x in res.get("problems", [])[:5]]
    n = 0
    for row in res.get("rows", []):
        for s in row.get("hold", []):
            if n < 12:
                out.append(f"  beat {row['beat']}：{s['ctx']}  {s['why']}  {s.get('fix', '')}")
            n += 1
        for h in row.get("held", []):
            if n < 12:
                out.append(f"  beat {row['beat']}：{h['ctx']}  {h['why']}")
            n += 1
    if n > 12:
        out.append(f"  ……还有 {n - 12} 处：./kepu lint {p.name}")
    print("\n".join(out), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
