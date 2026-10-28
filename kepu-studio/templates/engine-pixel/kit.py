"""像素版的部件库：文字、RPG 窗口、卡片、标签、宝箱（黑箱）、角色精灵、箭头、表格、背景……

所有工厂函数返回 engine.Obj（或 Group），坐标按 320x180 像素给。对象创建后要 s.add(...) 才会被画，
默认不可见，用 show(...) 让它出现。
"""
from __future__ import annotations

import importlib.util
import math
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from pixel.engine import (B, BOX, C, E, FG, FULL, G, H, K, LILAC, M, MUTED, N, O, R, SEM, SKETCH, SYN, V, W, W_, WRONG,
                          Y, Obj, bayer_mask, e, flash, frame_to, g, hide, jump, n, par, show, text_mask, text_w, v, wrap)

PROD = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("pixcover", Path(__file__).with_name("pixcover.py"))
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)          # 复用像素封面里画好的角色与道具（robot, tortoise, barber, chest……）

KEY = (1, 2, 3)                         # 子画布的透明色


# ================================================================================================
# 基础：从 Pix 画法得到 RGBA 精灵
# ================================================================================================
def pix_canvas(w, h, bg=KEY):
    return pc.Pix(bg=bg, size=(w, h))


def to_rgba(p, crop=True):
    im = p.im.convert("RGBA")
    a = ImageChops.difference(p.im, Image.new("RGB", p.im.size, KEY)).convert("L").point(lambda x: 255 if x else 0)
    im.putalpha(a)
    if crop:
        bb = a.getbbox()
        if bb:
            im = im.crop(bb)
    return im


def sprite(draw, w, h, x=0, y=0, anchor="lt", crop=True, z=0, bob=0):
    """draw(p) 在 w x h 的透明画布上作画（可以直接调用 pc.robot(p, ...) 等），返回 Obj。"""
    p = pix_canvas(w, h)
    draw(p)
    return Obj(to_rgba(p, crop), x, y, anchor, z=z, bob=bob)


def img_obj(im: Image.Image, x=0, y=0, anchor="lt", fine=False, z=0):
    return Obj(im.convert("RGBA"), x, y, anchor, fine=fine, z=z)


class Group(Obj):
    """一组对象：show/hide/flash/move(by=…) 会作用到每个成员。"""

    def __init__(self, *members):
        super().__init__(None)
        self.children = [m_ for m_ in members if m_ is not None]

    def box(self, t=None):
        bs = [c.box(t) for c in self.children]
        return min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)

    @property
    def w(self):
        b = self.box()
        return b[2] - b[0]

    @property
    def h(self):
        b = self.box()
        return b[3] - b[1]

    def shift(self, dx, dy):
        for c in self.children:
            if isinstance(c, Group):
                c.shift(dx, dy)
            else:
                c.init["x"] += dx
                c.init["y"] += dy
        return self

    def place(self, x, y, anchor="lt"):
        x0, y0, x1, y1 = self.box()
        ax, ay = {"l": 0, "c": 0.5, "r": 1}[anchor[0]], {"t": 0, "c": 0.5, "b": 1}[anchor[1]]
        return self.shift(x - (x0 + ax * (x1 - x0)), y - (y0 + ay * (y1 - y0)))

    def __getitem__(self, i):
        return self.children[i]

    def __len__(self):
        return len(self.children)

    def __iter__(self):
        return iter(self.children)


# ================================================================================================
# 文字
# ================================================================================================
def _text_img(lines, size, color, bold, math_, outline, shadow, align, lead, scale_fine):
    masks = [text_mask(ln, size, bold, math_) for ln in lines]
    lw = max((m_.width for m_, _ in masks), default=1)
    lh = max((m_.height for m_, _ in masks), default=size)
    pad = 1 if (outline or shadow) else 0
    total_h = len(masks) * lh + (len(masks) - 1) * lead
    im = Image.new("RGBA", (lw + 2 * pad + (1 if shadow else 0), total_h + 2 * pad + (1 if shadow else 0)), (0, 0, 0, 0))
    edges = []
    y = pad
    for (mk, xs) in masks:
        x = pad + {"l": 0, "c": (lw - mk.width) // 2, "r": lw - mk.width}[align]
        if outline:
            mp = Image.new("L", (mk.width + 2, mk.height + 2), 0)
            mp.paste(mk, (1, 1))
            om = mp.filter(ImageFilter.MaxFilter(3))
            big = Image.new("L", im.size, 0)
            big.paste(om, (x - 1, y - 1))
            im.paste(outline + (255,), (0, 0), big)
        if shadow:
            im.paste(shadow + (255,), (x + 1, y + 1), mk)
        im.paste(color + (255,), (x, y), mk)
        edges.append((0, y + mk.height + (1 if shadow else 0) + pad, [x + xx + pad for xx in xs]))
        y += lh + lead
    # 打字机按行裁剪：每行的 (y0, y1, [右边界])
    fixed, prev = [], 0
    for (_, y1, xs) in edges:
        fixed.append((prev, min(im.height, y1), xs))
        prev = min(im.height, y1)
    return im, fixed


class Text(Obj):
    """文字。size：art 层的像素字号（12 起清楚；标题 16–24）。fine=True 时画在细字层（字号按 640 层给，
    16–20 适合公式与长句）。math=True 时拉丁字母也用数学字体（公式）。width 给定时自动折行。"""

    def __init__(self, s, x=0, y=0, size=12, color=W_, anchor="lt", fine=False, bold=True, math=False,
                 outline=K, shadow=None, width=None, align="l", lead=3, z=5):
        lines = []
        for part in str(s).split("\n"):
            lines += wrap(part, size, int(width * (2 if fine else 1)), bold, math) if width else [part]
        im, edges = _text_img(lines, size, color, bold, math, outline, shadow, align, lead, fine)
        super().__init__(im, x, y, anchor, fine=fine, z=z)
        self.edges = edges
        self.text = "".join(lines)
        self.lines = lines


def T(s, x=0, y=0, size=12, color=W_, **kw):
    return Text(s, x, y, size, color, **kw)


def F(s, x=0, y=0, size=18, color=W_, **kw):
    """公式（细字层 + 数学字体）。"""
    kw.setdefault("math", True)
    kw.setdefault("bold", False)
    return Text(s, x, y, size, color, fine=True, **kw)


# ================================================================================================
# RPG 窗口、卡片、标签
# ================================================================================================
def rpg_window(w, h, fill=N, border=W_, edge=G):
    """RPG 窗口图（RGBA）：黑描边 + 米白双线边框 + 圆角 + 深底。"""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = 0, 0, w - 1, h - 1
    d.rectangle([x0 + 1, y0, x1 - 1, y1], fill=K)
    d.rectangle([x0, y0 + 1, x1, y1 - 1], fill=K)
    d.rectangle([x0 + 2, y0 + 1, x1 - 2, y1 - 1], fill=border)
    d.rectangle([x0 + 1, y0 + 2, x1 - 1, y1 - 2], fill=border)
    d.rectangle([x0 + 2, y0 + 2, x1 - 2, y1 - 2], fill=edge)
    d.rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], fill=K)
    d.rectangle([x0 + 4, y0 + 4, x1 - 4, y1 - 4], fill=fill)
    lighter = tuple(min(255, c + 18) for c in fill)
    d.line([x0 + 4, y0 + 4, x1 - 4, y0 + 4], fill=lighter)
    return im


def Window(x, y, w, h, fill=N, border=W_, anchor="lt", z=2):
    return Obj(rpg_window(int(w), int(h), fill, border), x, y, anchor, z=z)


def Panel(lines, x=160, y=20, w=None, title=None, color=W_, title_color=Y, size=12, fine=False, fsize=18,
          anchor="ct", fill=N, pad=8, lead=4, math=False, align="l", z=3):
    """一扇 RPG 窗口，里面一行行字。返回 Group：g.frame、g.title、g.lines[i]（每行可单独 show）。
    fine=True 时正文用细字层（字号 fsize，按 640 层）。"""
    lines = [lines] if isinstance(lines, str) else list(lines)
    tsize = size
    objs = []
    if fine:
        line_objs = [Text(s, 0, 0, fsize, color, fine=True, bold=False, math=math, outline=None) for s in lines]
    else:
        line_objs = [Text(s, 0, 0, size, color, math=math, outline=None) for s in lines]
    title_obj = Text(title, 0, 0, tsize, title_color, outline=None) if title else None
    inner_w = max([o.w for o in line_objs] + ([title_obj.w] if title_obj else [0]))
    ww = int(w if w else inner_w + 2 * pad + 2)
    hh = pad * 2 + 2 + (title_obj.h + lead + 2 if title_obj else 0) + sum(o.h for o in line_objs) + lead * (len(line_objs) - 1)
    frame = Window(0, 0, ww, int(hh), fill=fill, z=z)
    ax, ay = {"l": 0, "c": 0.5, "r": 1}[anchor[0]], {"t": 0, "c": 0.5, "b": 1}[anchor[1]]
    fx0, fy0 = x - ax * ww, y - ay * hh
    frame.place(fx0, fy0)
    cy = fy0 + pad + 1
    if title_obj:
        title_obj.place(fx0 + pad + 1, cy)
        title_obj.z = z + 1
        cy += title_obj.h + lead + 2
    for o in line_objs:
        ox = {"l": fx0 + pad + 1, "c": fx0 + ww / 2 - o.w / 2, "r": fx0 + ww - pad - 1 - o.w}[align]
        o.place(ox, cy)
        o.z = z + 1
        cy += o.h + lead
    grp = Group(frame, *( [title_obj] if title_obj else []), *line_objs)
    grp.frame, grp.title, grp.lines = frame, title_obj, line_objs
    return grp


def Card(title, lines, x=160, y=24, color=Y, w=None, size=12, fine=False, fsize=18, anchor="ct", math=False, z=3):
    """定义 / 定理 / 引理卡片：标题用 color（定理黄、定义青、黑箱紫、误解红、实情绿）。"""
    return Panel(lines, x, y, w, title=title, title_color=color, size=size, fine=fine, fsize=fsize, anchor=anchor,
                 math=math, z=z)


def Chip(s, x=0, y=0, color=Y, size=12, anchor="lt", fill=None, fine=False, z=4):
    """小标签：圆角框 + 字。"""
    t = Text(s, 0, 0, size, color, outline=None, fine=fine, bold=not fine)
    tw, th = (t.img.width, t.img.height)
    pw, ph = tw + (8 if not fine else 14), th + (5 if not fine else 8)
    im = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bg = fill if fill else tuple(int(c * 0.22) for c in color)
    d.rounded_rectangle([0, 0, pw - 1, ph - 1], radius=3 if not fine else 5, fill=K)
    d.rounded_rectangle([1, 1, pw - 2, ph - 2], radius=3 if not fine else 5, fill=color)
    d.rounded_rectangle([2, 2, pw - 3, ph - 3], radius=2 if not fine else 4, fill=bg)
    im.paste(t.img, ((pw - tw) // 2, (ph - th) // 2 + (0 if fine else 1)), t.img)
    o = Obj(im, x, y, anchor, fine=fine, z=z)
    o.text = s
    return o


def Badge(kind, note="", x=316, y=4, anchor="rt"):
    """严谨程度角标：full 完整（绿）/ sketch 骨架（黄）/ box 黑箱（紫）。默认放右上角。"""
    col, word = {"full": (FULL, "完整"), "sketch": (SKETCH, "骨架"), "box": (BOX, "黑箱")}[kind]
    return Chip(word + (f" {note}" if note else ""), x, y, col, size=11, anchor=anchor, z=8)


# ================================================================================================
# 宝箱 = 黑箱
# ================================================================================================
def _chest_img(letter, state, w=34, h=24, label=None):
    p = pix_canvas(w + 12, h + 22)
    pc.chest(p, 6, h + 18, w, h, open_=(state == "open"), locked=(state == "locked"))
    im = to_rgba(p, crop=False)
    if letter:
        lt = Text(letter, 0, 0, 12, LILAC if state != "open" else Y, outline=K)
        cx = (w + 12) // 2 - lt.img.width // 2
        ly = h + 18 - h // 2 - 3 if state != "open" else h + 18 - h + 6
        im.alpha_composite(lt.img, (max(0, cx), max(0, ly)))
    bb = im.getbbox()
    return im.crop(bb) if bb else im


def Chest(letter="", x=0, y=0, state="closed", w=34, h=24, anchor="cb", z=4):
    """黑箱宝箱：state closed / locked / open。open_chest(obj) 动作把它打开（带音效与闪光）。"""
    o = Obj(_chest_img(letter, state, w, h), x, y, anchor, z=z)
    o.letter, o.cw, o.ch = letter, w, h
    return o


def chest_open_img(o):
    return _chest_img(o.letter, "open", o.cw, o.ch)


# ================================================================================================
# 角色
# ================================================================================================
def Robot(x=160, y=130, eyes="o", mouth="line", face="right", arms="down", anchor="cb", bob=1, z=5):
    """主角小机器人（约 25x43）。eyes: o / sq / worry / squeeze / happy；mouth: line / o / wavy / smile / tape。"""
    return sprite(lambda p: pc.robot(p, 4, 46, face=face, eyes=eyes, mouth=mouth, arms=arms), 32, 48, x, y, anchor,
                  z=z, bob=bob)


def robot_img(**kw):
    return Robot(**kw).img


def Tortoise(x=0, y=0, anchor="cb", z=5, bob=0):
    return sprite(lambda p: pc.tortoise(p, 4, 40), 60, 44, x, y, anchor, z=z, bob=bob)


def Runner(x=0, y=0, anchor="cb", z=5, bob=0):
    return sprite(lambda p: pc.runner(p, 6, 50), 44, 54, x, y, anchor, z=z, bob=bob)


def Barber(x=0, y=0, anchor="cb", z=5, bob=0):
    return sprite(lambda p: pc.barber(p, 8, 54), 50, 58, x, y, anchor, z=z, bob=bob)


def Moon(x=0, y=0, s=40, anchor="lt", z=3):
    return sprite(lambda p: pc.square_moon(p, 4, 4, s), s + 12, s + 12, x, y, anchor, z=z)


def CBoss(x=0, y=0, cell=3, anchor="cb", z=5, aura=False):
    return sprite(lambda p: pc.c_boss(p, 6, 70, cell=cell, aura=aura), 80, 76, x, y, anchor, z=z)


def Blob(col=O, x=0, y=0, r=6, crowned=False, eyes="o", anchor="cc", z=5):
    return sprite(lambda p: pc.blob(p, 14, 16, col, r=r, crowned=crowned, eyes=eyes), 30, 30, x, y, anchor, z=z)


def Heart(x=0, y=0, col=R, small=False, anchor="cc", z=6):
    return sprite(lambda p: pc.heart(p, 2, 2, col, small=small), 12, 10, x, y, anchor, z=z)


def Pawn(col=R, x=0, y=0, anchor="cb", z=5):
    return sprite(lambda p: pc.pawn(p, 8, 20, col), 16, 22, x, y, anchor, z=z)


def Golem(x=160, y=140, anchor="cb", z=3):
    return sprite(lambda p: pc.golem(p, 110, 130), 220, 140, x, y, anchor, z=z)


def Spinner(x=0, y=0, r=16, anchor="cc", z=5):
    return sprite(lambda p: pc.spinner_boss(p, r + 6, r + 6, r=r, dot=4), 2 * r + 12, 2 * r + 12, x, y, anchor, z=z)


def Gadget(x=0, y=0, anchor="cb", z=5):
    return sprite(lambda p: pc.gadget(p, 2, 2), 40, 32, x, y, anchor, z=z)


def Torch(x=0, y=0, anchor="cb", z=2):
    return sprite(lambda p: pc.torch(p, 4, 4), 14, 20, x, y, anchor, z=z)


# ================================================================================================
# 图形
# ================================================================================================
def _line_img(x0, y0, x1, y1, color, width, head, dashed=False):
    pad = 6
    ox, oy = min(x0, x1) - pad, min(y0, y1) - pad
    w_, h_ = int(abs(x1 - x0) + 2 * pad + 1), int(abs(y1 - y0) + 2 * pad + 1)
    im = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    a, b = (x0 - ox, y0 - oy), (x1 - ox, y1 - oy)
    if dashed:
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
        k = int(L // 4)
        for i in range(0, k, 2):
            p0 = (a[0] + (b[0] - a[0]) * i / k, a[1] + (b[1] - a[1]) * i / k)
            p1 = (a[0] + (b[0] - a[0]) * (i + 1) / k, a[1] + (b[1] - a[1]) * (i + 1) / k)
            d.line([p0, p1], fill=color, width=width)
    else:
        d.line([a, b], fill=color, width=width)
    if head:
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        hl = 5 + width
        pts = [b, (b[0] - hl * math.cos(ang - 0.5), b[1] - hl * math.sin(ang - 0.5)),
               (b[0] - hl * math.cos(ang + 0.5), b[1] - hl * math.sin(ang + 0.5))]
        d.polygon(pts, fill=color)
    return im, ox, oy


def Arrow(x0, y0, x1, y1, color=W_, width=2, head=True, dashed=False, z=4):
    im, ox, oy = _line_img(x0, y0, x1, y1, color, width, head, dashed)
    return Obj(im, ox, oy, "lt", z=z)


def Line(x0, y0, x1, y1, color=G, width=1, dashed=False, z=3):
    return Arrow(x0, y0, x1, y1, color, width, head=False, dashed=dashed, z=z)


def Rect(x0, y0, x1, y1, color=Y, width=1, fill=None, z=3):
    """矩形框（可选填充）。坐标含端点。"""
    w_, h_ = int(x1 - x0 + 1), int(y1 - y0 + 1)
    im = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if fill:
        d.rectangle([0, 0, w_ - 1, h_ - 1], fill=fill)
    if width:
        for k in range(width):
            d.rectangle([k, k, w_ - 1 - k, h_ - 1 - k], outline=color)
    return Obj(im, x0, y0, "lt", z=z)


def Highlight(target: Obj, color=Y, pad=2, z=7):
    """包住某个对象的高亮框（像游戏里的选择光标框）。"""
    x0, y0, x1, y1 = target.box()
    return Rect(int(x0) - pad, int(y0) - pad, int(x1) + pad, int(y1) + pad, color, 1, z=z)


def Dot(x, y, r=2, color=O, z=4):
    im = Image.new("RGBA", (2 * r + 1, 2 * r + 1), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse([0, 0, 2 * r, 2 * r], fill=color)
    return Obj(im, x, y, "cc", z=z)


def Icon(kind, x=0, y=0, color=None, k=1, anchor="cc", z=6):
    """小图标：check ✓ / cross ✗ / heart / q（问号气泡）/ excl（感叹号）/ star / spark。"""
    p = pix_canvas(40, 40)
    if kind == "check":
        pc.check_icon(p, 4, 4, color or E, k=k)
    elif kind == "cross":
        pc.cross_icon(p, 4, 4, color or R, k=k)
    elif kind == "heart":
        pc.heart(p, 4, 4, color or R)
    elif kind == "star":
        pc.Pix.twinkle(p, 10, 10, color or Y, big=True)
    elif kind in ("q", "excl"):
        ch = "?" if kind == "q" else "!"
        p.d.rounded_rectangle([2, 2, 14, 16], radius=3, fill=K)
        p.d.rounded_rectangle([3, 3, 13, 15], radius=2, fill=W_)
        p.glyphs(ch, 6, 5, color or R)
    elif kind == "spark":
        c = color or Y
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
            p.px(10 + dx, 10 + dy, c)
    return Obj(to_rgba(p), x, y, anchor, z=z)


def Bubble(s, x, y, tail=(0, 10), size=11, color=K, fill=W_, anchor="cb", z=7):
    """对话气泡，(x, y) = 气泡底边中点，tail = 尾巴尖相对 (x, y) 的偏移。"""
    t = Text(s, 0, 0, size, color, outline=None)
    pw, ph = t.img.width + 10, t.img.height + 8
    tx, ty = tail
    W2, H2 = pw + 2 * abs(tx) + 4, ph + abs(ty) + 4
    p = pix_canvas(W2, H2)
    bx0 = (W2 - pw) // 2
    p.bubble(bx0, 1, bx0 + pw - 1, ph, (W2 // 2 + tx, ph + ty), fill=fill)
    im = to_rgba(p, crop=False)
    im.alpha_composite(t.img, (bx0 + 5, 5))
    o = Obj(im, x, y + abs(ty), "cb", z=z)
    o.anchor = anchor if anchor != "cb" else "cb"
    o.text = s
    return o


def Grid(rows, cols, x, y, cw=14, ch=14, color=G, fill=None, z=3, labels=None, label_color=W_, size=11,
         fine_labels=False):
    """表格网格。返回 Group：g.cell(r, c) 取格子对象（一个可以填色/高亮的方块），g.lines 为网格线。
    labels[r][c] 可给格内文字。"""
    w_, h_ = cols * cw + 1, rows * ch + 1
    im = Image.new("RGBA", (w_, h_), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if fill:
        d.rectangle([0, 0, w_ - 1, h_ - 1], fill=fill)
    for r in range(rows + 1):
        d.line([0, r * ch, w_ - 1, r * ch], fill=color)
    for c in range(cols + 1):
        d.line([c * cw, 0, c * cw, h_ - 1], fill=color)
    lines = Obj(im, x, y, "lt", z=z)
    cells = {}
    texts = []
    for r in range(rows):
        for c in range(cols):
            cells[(r, c)] = None
            if labels and labels[r][c] not in (None, ""):
                t = Text(labels[r][c], 0, 0, size if not fine_labels else 16, label_color, outline=None,
                         fine=fine_labels, bold=not fine_labels, math=fine_labels)
                t.place(x + c * cw + cw / 2, y + r * ch + ch / 2 + 1, "cc")
                t.z = z + 2
                texts.append(t)
                cells[(r, c)] = t
    grp = Group(lines, *texts)
    grp.lines, grp.texts, grp.cw, grp.ch, grp.x0, grp.y0 = lines, texts, cw, ch, x, y
    grp.label = lambda r, c: cells.get((r, c))

    def cell(r, c, color=O, z=None):
        o = Rect(x + c * cw + 1, y + r * ch + 1, x + (c + 1) * cw - 1, y + (r + 1) * ch - 1, color, 0, fill=color,
                 z=(z if z is not None else lines.z + 1))
        return o
    grp.cell = cell
    return grp


def Bulb(on=False, x=0, y=0, label=None, anchor="cb", z=5):
    """灯泡（命题变元的真假）：亮 = 1（橙），灭 = 0（灰）。"""
    p = pix_canvas(24, 36)
    glass = O if on else g
    if on:
        p.dither_fill(p.ellipse_mask(10, 9, 9, 9), Y, 0.35)
    p.d.ellipse([4, 3, 16, 15], fill=K)
    p.d.ellipse([5, 4, 15, 14], fill=glass)
    if on:
        p.px(7, 6, W_)
        p.px(8, 6, Y)
    p.box(7, 15, 13, 19, G)
    p.rect(8, 17, 12, 17, g)
    im = to_rgba(p, crop=False)
    if label:
        t = Text(label, 0, 0, 10, W_, outline=K)
        im.alpha_composite(t.img, (max(0, 10 - t.img.width // 2), 20))
    bb = im.getbbox()
    im = im.crop((0, 0, 24, bb[3] if bb else 36))
    return Obj(im, x, y, anchor, z=z)


# ================================================================================================
# 背景（320x180 RGB）
# ================================================================================================
def bg_plain(color=N):
    return Image.new("RGB", (320, 180), color)


def bg_night(seed=1, top=(10, 8, 34), mid=(30, 22, 74), bottom=(66, 36, 110), ground=None, stars=60):
    p = pc.Pix(bg=K)
    p.vgrad(0, 179, [top, mid, bottom])
    p.stars(0, 120, stars, 8, seed)
    if ground:
        p.ridge(179, 18, 30, ground, seed + 3)
    return p.im


def bg_dungeon(seed=2, wall=(40, 34, 70), mortar=(24, 20, 44)):
    p = pc.Pix(bg=wall)
    for y in range(0, 180, 10):
        p.rect(0, y, 319, y, mortar)
        off = 0 if (y // 10) % 2 == 0 else 10
        for x in range(-off, 320, 20):
            p.rect(x, y, x, y + 9, mortar)
    rnd = random.Random(seed)
    for _ in range(40):
        x, y = rnd.randrange(320), rnd.randrange(180)
        p.px(x, y, (60, 52, 96))
    return p.im


def bg_meadow(seed=3):
    p = pc.Pix(bg=K)
    p.vgrad(0, 120, [(96, 170, 240), (150, 206, 250)])
    p.vgrad(110, 179, [(92, 190, 92), (54, 140, 70)])
    rnd = random.Random(seed)
    for _ in range(5):
        x, y = rnd.randrange(0, 300), rnd.randrange(8, 60)
        p.d.ellipse([x, y, x + 26, y + 8], fill=W_)
        p.d.ellipse([x + 8, y - 4, x + 22, y + 6], fill=W_)
    return p.im


def bg_room(wall=(52, 40, 80), floor=(90, 60, 50)):
    p = pc.Pix(bg=wall)
    p.vgrad(0, 120, [(44, 34, 72), wall])
    p.rect(0, 121, 319, 179, floor)
    for x in range(0, 320, 24):
        p.rect(x, 121, x, 179, (70, 46, 40))
    p.rect(0, 120, 319, 121, K)
    return p.im


def bg_split(left=(18, 34, 82), right=(86, 46, 14), mid=G):
    """蓝橙分屏：左 = 符号的世界（语法），右 = 意义的世界（语义）。"""
    p = pc.Pix(bg=K)
    p.vgrad(0, 179, [left, tuple(int(c * 0.7) for c in left)], 0, 159)
    p.vgrad(0, 179, [right, tuple(int(c * 0.7) for c in right)], 160, 319)
    p.rect(159, 0, 160, 179, mid)
    return p.im


def bg_grid(color=(22, 20, 52), line=(34, 32, 76), step=10):
    p = pc.Pix(bg=color)
    for x in range(0, 320, step):
        p.rect(x, 0, x, 179, line)
    for y in range(0, 180, step):
        p.rect(0, y, 319, y, line)
    return p.im


def cover_bg(ep: int):
    """该集像素封面（320x180 原画）。"""
    f = PROD / "output" / f"ep{ep:02d}" / "cover_16x9.png"     # kepu：封面放在 output/epNN/
    if not f.exists():                      # 封面还没画好时先用夜空占位
        return bg_night(seed=ep + 50)
    im = Image.open(f).convert("RGB")
    return im.resize((320, 180), Image.NEAREST)


# ================================================================================================
# 对话框头像
# ================================================================================================
_av_cache = {}


def avatar_img(kind="robot", talking=False):
    k = (kind, talking)
    if k in _av_cache:
        return _av_cache[k]
    p = pix_canvas(30, 30)
    p.box(0, 0, 29, 29, n)
    p.rect(1, 1, 28, 13, (58, 54, 124))
    # 机器人大头
    p.rect(14, 3, 15, 7, K)
    p.box(12, 1, 17, 5, Y)
    p.box(4, 7, 25, 28, G)
    p.rect(5, 8, 24, 8, W_)
    p.box(7, 10, 22, 25, N)
    for ex in (10, 17):
        p.rect(ex, 13, ex + 2, 17, C)
        p.px(ex, 13, W_)
    if talking:
        p.box(12, 20, 17, 24, N, C)
    else:
        p.rect(12, 22, 17, 22, C)
    im = to_rgba(p, crop=False)
    _av_cache[k] = im
    return im


# ================================================================================================
# 排版
# ================================================================================================
def hrow(*objs, y=60, gap=8, cx=160, anchor_y="t"):
    """把若干对象横排、整体水平居中在 cx。anchor_y: t（上沿对齐 y）/ c（中线对齐 y）/ b（下沿对齐 y）。"""
    ws = [o.w for o in objs]
    total = sum(ws) + gap * (len(objs) - 1)
    x = cx - total / 2
    for o, w_ in zip(objs, ws):
        if isinstance(o, Group):
            o.place(x, y, "l" + anchor_y)
        else:
            o.place(x, y, "l" + anchor_y)
        x += w_ + gap
    return objs


def vcol(*objs, x=160, y=20, gap=6, align="c"):
    """竖排，从 y 往下；align: l（左对齐到 x）/ c（居中于 x）/ r。"""
    for o in objs:
        if isinstance(o, Group):
            o.place(x, y, align + "t")
        else:
            o.place(x, y, align + "t")
        y += o.h + gap
    return objs


# ================================================================================================
# 片头标题画面、关卡标题卡、片尾
# ================================================================================================
def pixel_avatar(path, size=40, colors=24):
    """把头像缩成像素头像（有限色 + 圆形裁切）。"""
    im = Image.open(path).convert("RGBA").resize((size, size), Image.LANCZOS)
    rgb = im.convert("RGB").quantize(colors=colors, method=Image.Quantize.MEDIANCUT).convert("RGBA")
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    rgb.putalpha(ImageChops.multiply(mask, im.getchannel("A")))
    return rgb


def title_screen(s, ep_num: int, dur=3.2):
    """片头 3 秒：本集像素封面 + 闪烁的 PRESS START。用作第一个场景的开头。"""
    s.dialog = True
    s.bg(bg_plain(K), fade=0)
    cov = Obj(cover_bg(ep_num).convert("RGBA"), 0, 0, "lt", z=0)   # 封面作为对象画（空白检查不会误报）
    cov.init["vis"] = 1.0
    press = Text("▶ PRESS START", 160, 161, 11, Y, anchor="ct")
    s.add(cov, press)
    s.wait(0.6)
    s.play(show(press, how="blink", dur=1.2), wait=False)
    s.sfx("select", s.t + 1.4)
    s.wait(dur - 0.6)
    s.screen_flash(W_, 0.3)
    s.play(hide(press, how="cut"))
    s.play(hide(cov, how="cut"))         # 之后接 stage_card 等时不再压着封面


def stage_card(s, ep_num: int, title: str, sub: str = "", hold=2.4):
    """关卡标题卡：STAGE NN + 本集标题（像 RPG 进入新关卡）。不配旁白时用 play/wait。"""
    s.bg(bg_night(seed=ep_num + 30, stars=40), fade=0.3)
    st = Text(f"STAGE {ep_num:02d}", 160, 38, 16, Y, anchor="ct")
    tt = Text(title, 160, 62, 16, W_, anchor="ct", width=290, align="c")
    ss = Text(sub, 160, 96, 11, G, anchor="ct") if sub else None
    s.add(st, tt, *( [ss] if ss else []))
    s.play(show(st, how="drop", sfx="open"))
    s.play(show(tt, how="type"))
    if ss:
        s.play(show(ss, how="dither"))
    s.wait(hold)
    return st, tt, ss


def credits(s, ep_num: int):
    """片尾制作人员（像素版）。"""
    s.dialog = False
    s.bg(bg_night(seed=99, stars=50), fade=0.4)
    from pixel.engine import PROD as _P
    head = Text("制作", 160, 22, 12, G, anchor="ct")
    a1 = Obj(pixel_avatar(_P / "assets/avatars/beiji_tianxia.png", 44), 100, 52, "ct")
    a2 = Obj(pixel_avatar(_P / "assets/avatars/elvis.png", 44), 220, 52, "ct")
    n1 = Text("北极甜虾（剑心犹在！）", 100, 102, 11, LILAC, anchor="ct")
    n2 = Text("Elvis的游乐园", 220, 102, 11, O, anchor="ct")
    ser = Text(f"《证明的极限》第 {ep_num} 集", 160, 128, 11, G, anchor="ct")
    bye = Text("下一关见！", 160, 150, 12, Y, anchor="ct")
    s.add(head, a1, a2, n1, n2, ser, bye)
    s.play(show(head, how="dither"))
    s.play(show(a1, a2, how="pop", sfx="pop"), show(n1, n2, how="type"))
    s.play(show(ser, how="dither"))
    s.play(show(bye, how="blink"))
    s.wait(3.0)
    s.clear(dur=0.8)


# ================================================================================================
# 常用组合动作
# ================================================================================================
def open_chest(chest):
    """打开黑箱宝箱：换成打开的图 + 金色闪烁 + 音效。"""
    return par(frame_to(chest, chest_open_img(chest), sfx="chest"), flash(chest, color=Y, dur=0.6))


def mood(robot, eyes="o", mouth="line", face="right", arms="down"):
    """换机器人的表情/姿势（eyes: o sq worry squeeze happy；mouth: line o wavy smile tape；arms: down up）。"""
    return frame_to(robot, Robot(eyes=eyes, mouth=mouth, face=face, arms=arms).img)
