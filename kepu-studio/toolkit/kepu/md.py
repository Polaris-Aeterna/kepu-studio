"""讲义用的小 Markdown（不依赖第三方库）：标题、段落、列表、表格、引用、代码、图片、链接、公式（交给 KaTeX），
外加容器块和标签：

    ::: thm 定理 3.1（Cook–Levin）[完整]       ::: misconception     ::: exercise ★★ 习题 3.2
    ……                                           ……                     ……
    :::                                          :::                    :::

容器种类：def 定义、thm 定理、lem 引理、prop 命题、cor 推论、proof 证明、example 例、misconception 常见误解、fact 实情、
note 注、warning 注意、exercise 习题、hint 提示、answer 答案、l1 主线、l2 进阶、l3 硬核支线、blackbox 黑箱、recap 小结、
map 本期地图、video 对应视频。行内标签：[L1] [L2] [L3]、[完整] [骨架] [黑箱 A→12] [黑箱→文献]、★。
"""
from __future__ import annotations

import html
import re

KINDS = {"def": "定义", "thm": "定理", "lem": "引理", "prop": "命题", "cor": "推论", "proof": "证明", "example": "例",
         "misconception": "常见误解", "fact": "实情", "note": "注", "warning": "注意", "exercise": "习题", "hint": "提示",
         "answer": "答案", "l1": "主线", "l2": "进阶", "l3": "硬核支线", "blackbox": "黑箱", "recap": "本期小结",
         "map": "本期地图", "video": "对应视频"}
_MATH = re.compile(r"\$\$.+?\$\$|\$[^$\n]+?\$|\\\(.+?\\\)", re.S)
_TAG = re.compile(r"\[(L[123]|完整|骨架|黑箱[^\]]*)\]")


def inline(s: str) -> str:
    keep = []

    def put(x: str) -> str:
        keep.append(x)
        return f"\x00{len(keep) - 1}\x00"
    s = re.sub(r"`([^`]+)`", lambda m: put(f"<code>{html.escape(m.group(1))}</code>"), s)
    s = _MATH.sub(lambda m: put(html.escape(m.group(0), quote=False)), s)
    s = html.escape(s, quote=False)
    s = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r'<img src="\2" alt="\1">', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"<em>\1</em>", s)

    def tag(m):
        t = m.group(1)
        cls = "lv" if t.startswith("L") else ("full" if t == "完整" else "sketch" if t == "骨架" else "box")
        return f'<span class="tag {cls} {t.lower() if t.startswith("L") else ""}">{t}</span>'
    s = _TAG.sub(tag, s)
    s = s.replace("★", '<span class="star">★</span>')
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], s)


def _table(lines: list[str]) -> str:
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines]
    head, body = rows[0], rows[2:]
    out = ["<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"]
    for r in body:
        out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
    return "\n".join(out) + "</tbody></table>"


def _list(lines: list[str]) -> str:
    out, stack = [], []
    for ln in lines:
        m = re.match(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$", ln)
        if not m:
            if out:
                out[-1] = out[-1][:-5] + " " + inline(ln.strip()) + "</li>"
            continue
        ind, kind = len(m.group(1).replace("\t", "  ")), ("ol" if m.group(2)[0].isdigit() else "ul")
        while stack and stack[-1][0] > ind:
            out.append(f"</{stack.pop()[1]}>")
        if not stack or stack[-1][0] < ind:
            stack.append((ind, kind))
            out.append(f"<{kind}>")
        out.append(f"<li>{inline(m.group(3))}</li>")
    while stack:
        out.append(f"</{stack.pop()[1]}>")
    return "\n".join(out)


def render(src: str) -> str:
    lines = src.splitlines()
    out, i, para = [], 0, []

    def flush():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s.startswith("<!--"):                       # author / production notes never reach the reader
            flush()
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
            i += 1
            continue
        if s.startswith(":::") and len(s) > 3:
            flush()
            m = re.match(r"^:::\s*(\w+)\s*(.*)$", s)
            kind, title = (m.group(1).lower(), m.group(2)) if m else ("note", "")
            depth, j, body = 1, i + 1, []
            while j < len(lines):
                t = lines[j].strip()
                if t.startswith(":::") and len(t) > 3:
                    depth += 1
                elif t == ":::":
                    depth -= 1
                    if depth == 0:
                        break
                body.append(lines[j])
                j += 1
            label = KINDS.get(kind, kind)
            if title and label in title:
                head = f'<div class="box-title">{inline(title)}</div>'
            else:
                head = f'<div class="box-title"><span class="kind">{label}</span>{(" " + inline(title)) if title else ""}</div>'
            out.append(f'<section class="box {kind}">{head}{render(chr(10).join(body))}</section>')
            i = j + 1
            continue
        if s.startswith("```"):
            flush()
            j, body = i + 1, []
            while j < len(lines) and not lines[j].strip().startswith("```"):
                body.append(lines[j])
                j += 1
            out.append("<pre><code>" + html.escape("\n".join(body)) + "</code></pre>")
            i = j + 1
            continue
        if s.startswith("$$"):
            flush()
            j, body = i, [ln]
            if not (s.endswith("$$") and len(s) > 2 and s != "$$"):
                j += 1
                while j < len(lines) and "$$" not in lines[j]:
                    body.append(lines[j])
                    j += 1
                if j < len(lines):
                    body.append(lines[j])
            out.append('<div class="math">' + "\n".join(body) + "</div>")
            i = j + 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            flush()
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
            i += 1
            continue
        if s in ("---", "***"):
            flush()
            out.append("<hr>")
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1]):
            flush()
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            out.append(_table(lines[i:j]))
            i = j
            continue
        if re.match(r"^\s*([-*+]|\d+[.)])\s+", ln):
            flush()
            j = i
            while j < len(lines) and (re.match(r"^\s*([-*+]|\d+[.)])\s+", lines[j]) or (lines[j].startswith("  ") and lines[j].strip())):
                j += 1
            out.append(_list(lines[i:j]))
            i = j
            continue
        if s.startswith(">"):
            flush()
            j, body = i, []
            while j < len(lines) and lines[j].strip().startswith(">"):
                body.append(lines[j].strip()[1:].lstrip())
                j += 1
            out.append("<blockquote>" + render("\n".join(body)) + "</blockquote>")
            i = j
            continue
        if not s:
            flush()
        else:
            para.append(s)
        i += 1
    flush()
    return "\n".join(out)
