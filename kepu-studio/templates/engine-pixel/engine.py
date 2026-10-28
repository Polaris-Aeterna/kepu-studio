"""像素版《证明的极限》引擎：320x180 像素画（放大 6 倍到 1080p）+ 640x360 细字层，30 fps。

一集 = 若干 Scene（一个 Scene = 一个章节）。每个 Scene 是一条时间线：
    s.say("旁白，[方括号里的词]出现时触发动画。", show(obj))
旁白音频与逐字时间直接取自 ElevenLabs 缓存（epNN/voice/*.json），文字必须与缓存一字不差（方括号除外），
因此重做画面不会产生任何新的语音费用。字幕 = 底部的 RPG 对话框，打字机效果与语音逐字同步。

坐标一律用 320x180 的像素坐标（左上角为原点）。fine=True 的对象画在 640x360 细字层（坐标仍按 320x180 给）。
用法见 pixel/GUIDE.md。
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

PROD = Path(__file__).resolve().parents[1]
W, H = 320, 180          # 像素画画布
FW, FH = 640, 360        # 细字层
FPS = 30
SR = 48000
OUT_W, OUT_H = 1920, 1080

FONTS = PROD / "assets" / "fonts"


def _first(*cands):
    """The first font file that exists: the project's assets/fonts/ first, then common system fonts (macOS / Windows /
    Linux).  Put NotoSansSC-Bold.ttf and NotoSansSC-Regular.ttf (OFL, fonts.google.com/noto/specimen/Noto+Sans+SC) in
    assets/fonts/ for the look of 《地基之下》."""
    for c in cands:
        if c and Path(c).exists():
            return str(c)
    raise FileNotFoundError("没找到中文字体：把 NotoSansSC-Bold.ttf / NotoSansSC-Regular.ttf 放进 assets/fonts/")


SANS_B = _first(FONTS / "NotoSansSC-Bold.ttf", "/System/Library/Fonts/STHeiti Medium.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "C:/Windows/Fonts/msyhbd.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc")
SANS_R = _first(FONTS / "NotoSansSC-Regular.ttf", "/System/Library/Fonts/STHeiti Light.ttc", "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "C:/Windows/Fonts/msyh.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
MATH = _first(FONTS / "STIXTwoMath-Regular.otf", "/System/Library/Fonts/Supplemental/STIXTwoMath.otf",
              "C:/Windows/Fonts/cambria.ttc", "/usr/share/fonts/opentype/stix/STIXTwoMath-Regular.otf", SANS_R)

# ---- 调色板（与像素封面一致） -------------------------------------------------------------------
K = (14, 9, 30)        # 描边黑
N = (30, 26, 70)       # 深蓝（窗口底）
n = (48, 44, 108)
V = (78, 48, 128)      # 紫
v = (124, 78, 176)
M = (214, 84, 196)     # 品红
R = (234, 58, 82)      # 红
O = (250, 146, 56)     # 橙（意义 / 真）
Y = (255, 218, 76)     # 黄
W_ = (252, 246, 228)   # 米白（文字）
G = (160, 166, 204)    # 灰
g = (90, 94, 140)
E = (70, 206, 118)     # 绿
e = (30, 124, 96)
C = (82, 206, 240)     # 青
B = (52, 104, 214)     # 蓝（符号 / 证明）
LILAC = (200, 160, 230)
SYN, SEM, BOX, FULL, SKETCH, WRONG, FG, MUTED = C, O, LILAC, E, Y, R, W_, G

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])


# ================================================================================================
# 文字：混排点阵字（汉字 Noto Sans SC，数学符号与希腊字母 STIX Two Math）
# ================================================================================================
CJK_PUNCT = set("，。：；？！、“”‘’（）《》「」『』【】…—·～")
_font_cache: dict = {}


def _font(path, size):
    k = (path, size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(path, size)
    return _font_cache[k]


def is_cjk(ch: str) -> bool:
    return ("一" <= ch <= "鿿") or ch in CJK_PUNCT or ("　" <= ch <= "〿") or ("＀" <= ch <= "￯")


_cmaps: dict = {}


def _has(path, ch):
    """字体里有没有这个字（没有就换字体，免得画出方块）。"""
    if path not in _cmaps:
        from fontTools.ttLib import TTFont
        _cmaps[path] = set(TTFont(path, fontNumber=0, lazy=True).getBestCmap())
    return ord(ch) in _cmaps[path]


def _glyph(ch, size, bold, math):
    """一个字的点阵：返回 (mask L, advance, baseline_y)。所有字按同一基线 (size*1.2) 渲染。"""
    key = ("g", ch, size, bold, math)
    if key in _font_cache:
        return _font_cache[key]
    if is_cjk(ch):
        path = SANS_B if bold else SANS_R
    elif (ch.isascii() or (ch.isalpha() and ord(ch) < 0x250)) and not math:
        path = SANS_B if bold else SANS_R
    else:
        path = MATH
    if ch != " " and not _has(path, ch):              # 缺字：在两套字体之间互相兜底
        for alt in (MATH, SANS_B if bold else SANS_R):
            if _has(alt, ch):
                path = alt
                break
    f = _font(path, size)
    hgt = int(size * 1.6)
    base = int(size * 1.2)
    im = Image.new("L", (size * 3, hgt), 0)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    d.text((size, base), ch, font=f, fill=255, anchor="ls")
    if ch == " ":
        res = (Image.new("L", (max(2, size // 3), hgt), 0), max(2, size // 3), base)
        _font_cache[key] = res
        return res
    bb = im.getbbox()
    if not bb:
        res = (Image.new("L", (1, hgt), 0), max(1, size // 3), base)
        _font_cache[key] = res
        return res
    if is_cjk(ch) and "一" <= ch <= "鿿":
        cw = size + 1                                   # 汉字：墨迹居中放进等宽格（小字号下 hinting 会漂）
        cell = Image.new("L", (cw, hgt), 0)
        ink = im.crop((bb[0], 0, bb[2], hgt))
        cell.paste(ink, ((cw - ink.width) // 2, 0))
        res = (cell, cw, base)
    elif is_cjk(ch):                                     # 中文标点：按字体步进，标点不缩
        adv = int(round(f.getlength(ch)))
        cell = im.crop((size, 0, size + adv, hgt))
        res = (cell, adv, base)
    else:
        ink = im.crop((bb[0], 0, bb[2], hgt))
        sp = 1 if size <= 16 else 2
        cell = Image.new("L", (ink.width + sp, hgt), 0)
        cell.paste(ink, (0, 0))
        res = (cell, cell.width, base)
    _font_cache[key] = res
    return res


def text_mask(s: str, size: int, bold=True, math=False):
    """单行文字 → (mask, 每个字右边界的 x 列表)。"""
    cells = [_glyph(ch, size, bold, math) for ch in s]
    hgt = int(size * 1.6)
    w = sum(c[1] for c in cells) or 1
    out = Image.new("L", (w, hgt), 0)
    x, edges = 0, []
    for m_, adv, _ in cells:
        out.paste(m_, (x, 0), m_)
        x += adv
        edges.append(x)
    # 竖直裁到统一的字面框：上沿 = 基线 - size，下沿 = 基线 + size*0.3
    base = int(size * 1.2)
    top, bot = max(0, base - size - 1), min(hgt, base + int(size * 0.32) + 1)
    return out.crop((0, top, w, bot)), edges


def text_w(s: str, size: int, bold=True, math=False) -> int:
    return sum(_glyph(ch, size, bold, math)[1] for ch in s)


def wrap(s: str, size: int, width: int, bold=True, math=False) -> list[str]:
    """按像素宽度折行（中文逐字、英文按词不拆）。行首不放中文标点。"""
    lines, cur = [], ""
    tokens = re.findall(r"[A-Za-z0-9_.'+\-*/=<>()]+|.", s)
    for tok in tokens:
        if text_w(cur + tok, size, bold, math) <= width or not cur:
            cur += tok
        else:
            if tok in CJK_PUNCT:          # 标点挂在行尾
                cur += tok
                continue
            lines.append(cur)
            cur = tok.lstrip()
    if cur:
        lines.append(cur)
    return lines


# ================================================================================================
# 对象与关键帧
# ================================================================================================
def ease_fn(name):
    return {
        "linear": lambda u: u,
        "out": lambda u: 1 - (1 - u) ** 3,
        "in": lambda u: u ** 3,
        "inout": lambda u: 3 * u * u - 2 * u ** 3,
        "step": lambda u: 1.0 if u >= 1 else 0.0,
        "back": lambda u: 1 + 2.7 * (u - 1) ** 3 + 1.7 * (u - 1) ** 2,
    }[name]


class Obj:
    """画面上的一个东西。img 是 RGBA 图（art 层按 320 像素，fine 层按 640 像素）。"""

    def __init__(self, img: Image.Image | None = None, x=0, y=0, anchor="lt", fine=False, z=0, frames=None,
                 frame_dt=0.5, bob=0):
        self.img = img
        self.frames = frames          # 动画帧列表（RGBA），按 frame_dt 循环
        self.frame_dt = frame_dt
        self.bob = bob                # 待机上下浮动的像素数（0 = 不动）
        self.fine = fine
        self.anchor = anchor
        self.z = z
        self.init = {"vis": 0.0, "x": float(x), "y": float(y), "reveal": 1.0}
        self.tracks: dict[str, list] = {}
        self.fx: list = []            # (t0, t1, kind, params)
        self.edges = None             # 打字机：每个字的右边界（单行）或 [(行, edges)]
        self.children: list[Obj] = []
        self._tint_cache = {}
        self.scene = None

    # ---- 尺寸与位置 ----
    @property
    def w(self):
        im = self.img or (self.frames[0] if self.frames else None)
        return 0 if im is None else (im.width / 2 if self.fine else im.width)

    @property
    def h(self):
        im = self.img or (self.frames[0] if self.frames else None)
        return 0 if im is None else (im.height / 2 if self.fine else im.height)

    def pos(self, t=None):
        if t is None:
            return self.init["x"], self.init["y"]
        return self.at("x", t), self.at("y", t)

    def box(self, t=None):
        """(x0, y0, x1, y1)，320 像素坐标。"""
        x, y = self.pos(t)
        ax, ay = {"l": 0, "c": 0.5, "r": 1}[self.anchor[0]], {"t": 0, "c": 0.5, "b": 1}[self.anchor[1]]
        x0, y0 = x - ax * self.w, y - ay * self.h
        return x0, y0, x0 + self.w, y0 + self.h

    def place(self, x, y, anchor=None):
        """改初始位置（未出现前用）。"""
        if anchor:
            self.anchor = anchor
        self.init["x"], self.init["y"] = float(x), float(y)
        return self

    def next_to(self, other: "Obj", side="b", gap=4, align="c"):
        x0, y0, x1, y1 = other.box()
        if side == "b":
            self.anchor = {"l": "lt", "c": "ct", "r": "rt"}[align]
            self.init["x"], self.init["y"] = {"l": x0, "c": (x0 + x1) / 2, "r": x1}[align], y1 + gap
        elif side == "t":
            self.anchor = {"l": "lb", "c": "cb", "r": "rb"}[align]
            self.init["x"], self.init["y"] = {"l": x0, "c": (x0 + x1) / 2, "r": x1}[align], y0 - gap
        elif side == "r":
            self.anchor = {"t": "lt", "c": "lc", "b": "lb"}[align]
            self.init["x"], self.init["y"] = x1 + gap, {"t": y0, "c": (y0 + y1) / 2, "b": y1}[align]
        elif side == "l":
            self.anchor = {"t": "rt", "c": "rc", "b": "rb"}[align]
            self.init["x"], self.init["y"] = x0 - gap, {"t": y0, "c": (y0 + y1) / 2, "b": y1}[align]
        return self

    # ---- 关键帧 ----
    def key(self, attr, t0, t1, v1, ease="out"):
        self.tracks.setdefault(attr, []).append((t0, max(t1, t0 + 1e-6), float(v1), ease))
        self.tracks[attr].sort(key=lambda s: s[0])

    def at(self, attr, t):
        val = self.init[attr]
        for t0, t1, v1, ease in self.tracks.get(attr, ()):
            if t < t0:
                break
            if t >= t1:
                val = v1
            else:
                u = (t - t0) / (t1 - t0)
                val = val + (v1 - val) * ease_fn(ease)(u)
                break
        return val

    def visible_ever(self):
        return self.init["vis"] > 0 or any(v1 > 0 for _, _, v1, _ in self.tracks.get("vis", ()))

    # ---- 画 ----
    def image_at(self, t):
        if self.frames:
            i = int(t / self.frame_dt) % len(self.frames)
            return self.frames[i]
        return self.img

    def tinted(self, im, color):
        """把不透明像素染成 color，但保留黑色描边（文字闪烁时仍可读）。"""
        k = (id(im), color)
        if k not in self._tint_cache:
            arr = np.asarray(im.convert("RGBA")).copy()
            outline = (arr[..., 0] <= K[0] + 6) & (arr[..., 1] <= K[1] + 6) & (arr[..., 2] <= K[2] + 6)
            paint = (arr[..., 3] > 0) & ~outline
            arr[paint, 0], arr[paint, 1], arr[paint, 2] = color
            self._tint_cache[k] = Image.fromarray(arr, "RGBA")
        return self._tint_cache[k]


# ================================================================================================
# 旁白缓存
# ================================================================================================
VOICE_TAG = "kAIqZ7fZv234ClKXwzDx"


def _clean(s):
    return re.sub(r"\s+", "", s)


class VoiceBank:
    def __init__(self, ep_dir: Path):
        self.ep_dir = ep_dir
        self.items: dict[str, dict] = {}
        self.loose: dict[str, dict] = {}
        kb = PROD / "audio" / ep_dir.name / "beats.json"          # kepu: ./kepu voice script/episodes/<tag>.md
        if kb.exists():
            self._load_kepu(kb)
        for f in sorted((ep_dir / "voice").glob("*.json")):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if "text" not in d or "words" not in d or VOICE_TAG not in d.get("voice", VOICE_TAG):
                continue
            mp3 = f.with_suffix(d.get("suffix", ".mp3"))
            if not mp3.exists():
                continue
            rec = {"text": d["text"], "words": d["words"], "audio": mp3, "mtime": mp3.stat().st_mtime}
            for table, k in ((self.items, d["text"]), (self.loose, _clean(d["text"]))):
                if k not in table or rec["mtime"] > table[k]["mtime"]:
                    table[k] = rec
        for f in sorted((ep_dir / "voice_ai").glob("*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            line = d.get("line") or d.get("text")
            mp3 = f.with_suffix(".mp3")
            if line and mp3.exists():
                rec = {"text": line, "words": None, "audio": mp3, "mtime": 0}
                self.items.setdefault(line, rec)
                self.loose.setdefault(_clean(line), rec)

    def _load_kepu(self, kb: Path):
        """kepu 的 beats.json：每个 beat（像素引擎里就是每一句旁白）的显示文字、wav、每个显示字的开始时刻。"""
        for info in json.loads(kb.read_text(encoding="utf-8"))["beats"].values():
            text, ct, dur = info["text"], info.get("char_times") or [], info["duration"]
            words = [[text[k], ct[k], ct[k + 1] if k + 1 < len(ct) else dur] for k in range(min(len(text), len(ct)))]
            wav = kb.parent / info["file"]
            if not wav.exists():
                continue
            rec = {"text": text, "words": words or None, "audio": wav, "mtime": wav.stat().st_mtime}
            for table, k in ((self.items, text), (self.loose, _clean(text))):
                if k not in table or rec["mtime"] > table[k]["mtime"]:
                    table[k] = rec

    def get(self, text: str) -> dict:
        rec = self.items.get(text) or self.loose.get(_clean(text))
        if rec is None:
            raise KeyError(f"配音里没有这句话（s.say 的文字必须与稿子的显示文字一字不差；先 ./kepu voice）：{text[:40]}…")
        if "pcm" not in rec:
            rec["pcm"] = decode_audio(rec["audio"])
            rec["dur"] = len(rec["pcm"]) / SR
        return rec


def decode_audio(path: Path) -> np.ndarray:
    cache = PROD / "pixel" / "_cache" / (path.parent.parent.name + "_" + path.stem + ".npy")
    if cache.exists() and cache.stat().st_mtime >= path.stat().st_mtime:
        return np.load(cache)
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32).copy()
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache, x)
    return x


def char_times(text: str, words, dur: float) -> list[float]:
    """display 文本每个字开始发音的时刻。没有逐字时间（AI 镜头旁白）时按字数均分。"""
    if not words:
        k = max(1, len(text))
        return [dur * 0.95 * i / k for i in range(len(text))]
    times = [None] * len(text)
    pos = 0
    for w_, s0, s1 in words:
        i = text.find(w_, pos)
        if i < 0:
            continue
        for j in range(len(w_)):
            times[i + j] = s0 + (s1 - s0) * j / max(1, len(w_))
        pos = i + len(w_)
    last = 0.0
    nxt = [None] * len(text)
    for i in range(len(text) - 1, -1, -1):          # 没对上的字取下一个字的时间
        nxt[i] = times[i] if times[i] is not None else (nxt[i + 1] if i + 1 < len(text) else None)
    out = []
    for i in range(len(text)):
        tt = nxt[i] if nxt[i] is not None else last
        last = tt
        out.append(tt)
    return out


def spans_of(script: str):
    """去掉方括号，返回 (文本, [(开始字号, 结束字号)])。"""
    text, spans, open_at = "", [], None
    for ch in script:
        if ch == "[":
            open_at = len(text)
        elif ch == "]":
            spans.append((open_at, len(text)))
            open_at = None
        else:
            text += ch
    return text, spans


def span_times(text, words, span, dur):
    a, b = span
    if not words:
        return dur * a / max(1, len(text)), dur * b / max(1, len(text))
    located, pos = [], 0
    for w_, s0, s1 in words:
        i = text.find(w_, pos)
        if i < 0:
            i = pos
        located.append((i, i + len(w_), s0, s1))
        pos = i + len(w_)
    inside = [x for x in located if x[0] < b and x[1] > a]
    if not inside:
        inside = [next((x for x in located if x[0] >= a), located[-1])]
    return inside[0][2], min(inside[-1][3], dur)


# ================================================================================================
# 动作（在 say / play 里用）
# ================================================================================================
def flat(objs):
    for o in objs:
        if getattr(o, "children", None):
            yield from flat(o.children)
        elif o is not None:
            yield o


class Action:
    dur = 0.4

    def apply(self, s: "Scene", t0: float, span: float) -> float:
        """在 t0 开始；span = 这段方括号的时长（可以不用）。返回结束时刻。"""
        raise NotImplementedError


class show(Action):
    """出现。how: pop（两帧闪现）/ dither（抖动淡入）/ type（打字机）/ wipe（从左到右擦出）/
    drop（从上方落下）/ rise（从下方升起）/ slide_l / slide_r（从左/右滑入）/ blink（闪三下后常亮）/ cut（立刻）"""

    def __init__(self, *objs, how="dither", dur=None, sfx=None, over=False):
        self.objs, self.how, self.sfx, self.over = objs, how, sfx, over
        self.dur = dur if dur is not None else {"pop": 0.15, "dither": 0.35, "type": None, "wipe": 0.5, "drop": 0.45,
                                                 "rise": 0.45, "slide_l": 0.45, "slide_r": 0.45, "blink": 0.6,
                                                 "cut": 0.0}[how]

    def apply(self, s, t0, span):
        end = t0
        for o in flat(self.objs):
            if o.scene is None:          # 忘了 s.add 的对象自动加入
                s.add(o)
            d = self.dur
            if self.how == "type":
                n_ = len(o.text) if hasattr(o, "text") else 10
                d = self.dur if self.dur is not None else min(max(0.4, n_ * 0.045), 2.5)
                if self.over and span:
                    d = max(d, span * 0.9)
                o.key("vis", t0, t0, 1.0, "step")
                o.key("reveal", t0, t0, 0.0, "step")
                o.key("reveal", t0, t0 + d, 1.0, "linear")
            elif self.how == "pop":
                o.key("vis", t0, t0, 1.0, "step")
                o.fx.append((t0, t0 + 0.18, "pop", {}))
            elif self.how == "cut":
                o.key("vis", t0, t0, 1.0, "step")
            elif self.how == "blink":
                o.key("vis", t0, t0, 1.0, "step")
                o.fx.append((t0, t0 + d, "blink", {}))
            elif self.how in ("dither", "wipe"):
                if self.how == "wipe":
                    o.key("vis", t0, t0, 1.0, "step")
                    o.fx.append((t0, t0 + d, "wipe", {}))
                else:
                    o.key("vis", t0, t0 + d, 1.0, "linear")
            else:
                x, y = o.at("x", t0), o.at("y", t0)
                dx, dy = {"drop": (0, -24), "rise": (0, 24), "slide_l": (-40, 0), "slide_r": (40, 0)}[self.how]
                o.key("x", t0, t0, x + dx, "step")
                o.key("y", t0, t0, y + dy, "step")
                o.key("x", t0, t0 + d, x, "back" if self.how == "drop" else "out")
                o.key("y", t0, t0 + d, y, "back" if self.how == "drop" else "out")
                o.key("vis", t0, t0 + min(d, 0.2), 1.0, "linear")
            end = max(end, t0 + d)
        if self.sfx:
            s.sfx(self.sfx, t0)
        return end


class hide(Action):
    def __init__(self, *objs, how="dither", dur=0.3):
        self.objs, self.how, self.dur = objs, how, dur

    def apply(self, s, t0, span):
        for o in flat(self.objs):
            if self.how == "cut" or self.how == "pop":
                o.key("vis", t0, t0, 0.0, "step")
            else:
                o.key("vis", t0, t0 + self.dur, 0.0, "linear")
        return t0 + (0 if self.how in ("cut", "pop") else self.dur)


class move(Action):
    def __init__(self, obj, to=None, by=None, dur=0.5, ease="out"):
        self.obj, self.to, self.by, self.dur, self.ease = obj, to, by, dur, ease

    def apply(self, s, t0, span):
        if getattr(self.obj, "children", None):        # 一组：整体平移
            if self.to is not None:
                bx0, by0, _, _ = self.obj.box(t0)
                dx, dy = self.to[0] - bx0, self.to[1] - by0
            else:
                dx, dy = self.by
            for o in flat([self.obj]):
                x, y = o.at("x", t0), o.at("y", t0)
                o.key("x", t0, t0 + self.dur, x + dx, self.ease)
                o.key("y", t0, t0 + self.dur, y + dy, self.ease)
            return t0 + self.dur
        x, y = self.obj.at("x", t0), self.obj.at("y", t0)
        if self.to is not None:
            tx, ty = self.to
        else:
            tx, ty = x + self.by[0], y + self.by[1]
        self.obj.key("x", t0, t0 + self.dur, tx, self.ease)
        self.obj.key("y", t0, t0 + self.dur, ty, self.ease)
        return t0 + self.dur


class flash(Action):
    """高亮闪烁（像游戏里选中/受击），color 为闪烁色。"""

    def __init__(self, *objs, color=Y, dur=0.8, sfx=None):
        self.objs, self.color, self.dur, self.sfx = objs, color, dur, sfx

    def apply(self, s, t0, span):
        for o in flat(self.objs):
            o.fx.append((t0, t0 + self.dur, "flash", {"color": self.color}))
        if self.sfx:
            s.sfx(self.sfx, t0)
        return t0 + self.dur


class shake(Action):
    def __init__(self, *objs, amp=2, dur=0.4, sfx=None):
        self.objs, self.amp, self.dur, self.sfx = objs, amp, dur, sfx

    def apply(self, s, t0, span):
        for o in flat(self.objs):
            o.fx.append((t0, t0 + self.dur, "shake", {"amp": self.amp}))
        if self.sfx:
            s.sfx(self.sfx, t0)
        return t0 + self.dur


class jump(Action):
    """原地跳一下（角色开心/惊讶）。"""

    def __init__(self, *objs, height=6, dur=0.35, times=1):
        self.objs, self.height, self.dur, self.times = objs, height, dur, times

    def apply(self, s, t0, span):
        for o in flat(self.objs):
            o.fx.append((t0, t0 + self.dur * self.times, "jump", {"h": self.height, "n": self.times}))
        return t0 + self.dur * self.times


class swap(Action):
    """a 消失、b 在同一时刻出现。"""

    def __init__(self, a, b, how="dither", dur=0.3):
        self.a, self.b, self.how, self.dur = a, b, how, dur

    def apply(self, s, t0, span):
        hide(self.a, dur=self.dur).apply(s, t0, span)
        return show(self.b, how=self.how, dur=self.dur).apply(s, t0, span)


class frame_to(Action):
    """把动画/多状态对象切到另一张图（如宝箱打开、表情变化）。img 为 RGBA 图或 Obj。"""

    def __init__(self, obj, img, sfx=None):
        self.obj, self.img, self.sfx = obj, img, sfx

    def apply(self, s, t0, span):
        im = self.img.img if isinstance(self.img, Obj) else self.img
        self.obj.fx.append((t0, 1e9, "img", {"img": im}))
        if self.sfx:
            s.sfx(self.sfx, t0)
        return t0


class par(Action):
    def __init__(self, *acts):
        self.acts = acts

    def apply(self, s, t0, span):
        return max([a.apply(s, t0, span) for a in self.acts] + [t0])


class seq(Action):
    def __init__(self, *acts, gap=0.0):
        self.acts, self.gap = acts, gap

    def apply(self, s, t0, span):
        t = t0
        for a in self.acts:
            t = a.apply(s, t, span) + self.gap
        return t


class stagger(Action):
    """一组动作依次开始。gap=None 时均匀铺满这段方括号的时长（适合“一、二、三……”逐个出现）。"""

    def __init__(self, *acts, gap=None):
        self.acts, self.gap = acts, gap

    def apply(self, s, t0, span):
        k = len(self.acts)
        gap = self.gap if self.gap is not None else (max(0.15, span * 0.85 / max(1, k)) if span else 0.25)
        end = t0
        for i, a in enumerate(self.acts):
            end = max(end, a.apply(s, t0 + i * gap, span))
        return end


class after(Action):
    """延迟 dt 秒再做 act。"""

    def __init__(self, dt, act):
        self.dt, self.act = dt, act

    def apply(self, s, t0, span):
        return self.act.apply(s, t0 + self.dt, span)


class sfx(Action):
    def __init__(self, name):
        self.name = name

    def apply(self, s, t0, span):
        s.sfx(self.name, t0)
        return t0


class call(Action):
    """自定义：fn(scene, t0, span) -> 结束时刻。"""

    def __init__(self, fn):
        self.fn = fn

    def apply(self, s, t0, span):
        r = self.fn(s, t0, span)
        return t0 if r is None else r


class nothing(Action):
    def apply(self, s, t0, span):
        return t0


# ================================================================================================
# 场景
# ================================================================================================
class Scene:
    def __init__(self, ep: "Episode", name: str, title: str = ""):
        self.ep, self.name, self.title = ep, name, title
        self.t = 0.0
        self.objs: list[Obj] = []
        self.bgs: list[tuple[float, Image.Image, float]] = []   # (t, 320x180 RGB, 过渡秒数)
        self.narr: list[dict] = []
        self.sfxs: list[tuple[float, str]] = []
        self.flashes: list[tuple[float, float, tuple]] = []      # 全屏闪光
        self.overlays: list = []                                   # fn(art_img, t) 自定义每帧绘制
        self.dialog = True
        self.speaker = "robot"

    # ---- 注册 ----
    def add(self, *objs: Obj, z=None):
        for o in objs:
            if z is not None:
                o.z = z
            o.scene = self
            if o not in self.objs:
                self.objs.append(o)
            for c in o.children:
                self.add(c)
        return objs[0] if len(objs) == 1 else objs

    def bg(self, img: Image.Image, fade=0.5):
        """从当前时刻起换背景（320x180 RGB）。"""
        self.bgs.append((self.t, img.convert("RGB"), fade))

    def sfx(self, name, t=None):
        self.sfxs.append((self.t if t is None else t, name))

    def screen_flash(self, color=W_, dur=0.25, t=None):
        t = self.t if t is None else t
        self.flashes.append((t, t + dur, color))

    # ---- 时间线 ----
    def say(self, script: str, *actions: Action, gap=0.25):
        """念一句旁白。方括号个数必须等于动作个数（或 0 个方括号 + 任意动作，动作在句首开始）。"""
        text, spans = spans_of(re.sub(r"〔[^〔〕]{0,12}〕", "", script))   # 多音字读音标记（数〔shù〕）不进字幕
        if spans and len(spans) != len(actions):
            raise ValueError(f"{self.name}: {len(spans)} 个方括号，却给了 {len(actions)} 个动作：{script[:30]}")
        rec = self.ep.voice.get(text)
        dur = rec["dur"]
        words = rec["words"]
        t0 = self.t
        self.narr.append({"t": t0, "text": text, "rec": rec, "dur": dur,
                          "chars": [t0 + c for c in char_times(text, words, dur)]})
        if spans:
            for act, sp in zip(actions, spans):
                a, b = span_times(text, words, sp, dur)
                act.apply(self, t0 + a, max(0.0, b - a))
        else:
            for act in actions:
                act.apply(self, t0, dur)
        last = max([dur] + ([words[-1][2]] if words else []))
        self.t = t0 + min(last, dur + 0.15) + gap
        return self

    def play(self, *actions: Action, wait=True):
        """不配旁白的动画；所有动作同时开始，时间线推进到最晚结束处。"""
        t0 = self.t
        end = max([a.apply(self, t0, 0.0) for a in actions] + [t0])
        if wait:
            self.t = end
        return self

    def wait(self, sec: float):
        self.t += sec
        return self

    def clear(self, keep=(), dur=0.35, how="dither"):
        """把当前画面上的对象都收掉（keep 里的除外）。"""
        t0 = self.t
        keep_ids = {id(k) for k in keep}
        for k in keep:
            keep_ids |= {id(c) for c in k.children}
        for k in keep:
            keep_ids |= {id(c) for c in flat([k])}
        for o in self.objs:
            if id(o) in keep_ids or getattr(o, "children", None):
                continue
            if o.at("vis", t0) > 0.001 or o.at("vis", t0 + 0.05) > 0.001:
                hide(o, how=how, dur=dur).apply(self, t0, 0)
        self.t = t0 + dur
        return self

    @property
    def duration(self):
        return self.t

    # ---- 渲染 ----
    def bg_at(self, t):
        cur, prev, tt, fade = None, None, 0, 0
        for (t0, img, f) in self.bgs:
            if t0 <= t:
                prev, cur, tt, fade = cur, img, t0, f
        if cur is None:
            return Image.new("RGB", (W, H), K)
        if prev is not None and fade > 0 and t < tt + fade:
            lvl = (t - tt) / fade
            return Image.composite(cur, prev, bayer_mask(W, H, lvl))
        return cur

    def render(self, t) -> Image.Image:
        art = self.bg_at(t).copy()
        fine = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
        for fn in self.overlays:
            fn(art, t)
        for o in sorted(self.objs, key=lambda o: o.z):
            vis = o.at("vis", t)
            if vis <= 0.001:
                continue
            draw_obj(o, t, vis, art, fine)
        if self.dialog:
            draw_dialog(self, art, t)
        for (t0, t1, col) in self.flashes:
            if t0 <= t < t1:
                lvl = 1 - (t - t0) / (t1 - t0)
                art = Image.composite(Image.new("RGB", (W, H), col), art, bayer_mask(W, H, lvl * 0.9))
        out = art.resize((FW, FH), Image.NEAREST)
        out.paste(fine, (0, 0), fine)
        return out


_bayer_cache: dict = {}


def bayer_mask(w, h, level):
    """覆盖率 level∈[0,1] 的 Bayer 抖动 mask（与屏幕对齐）。"""
    k = int(round(max(0.0, min(1.0, level)) * 16))
    key = (w, h, k)
    if key not in _bayer_cache:
        tile = (BAYER4 < k).astype(np.uint8) * 255
        arr = np.tile(tile, (h // 4 + 1, w // 4 + 1))[:h, :w]
        _bayer_cache[key] = Image.fromarray(arr, "L")
    return _bayer_cache[key]


def draw_obj(o: Obj, t, vis, art, fine):
    im = o.image_at(t)
    for (t0, t1, kind, p) in o.fx:
        if kind == "img" and t0 <= t:
            im = p["img"]
    if im is None:
        return
    x, y = o.at("x", t), o.at("y", t)
    sc = 2 if o.fine else 1
    ax, ay = {"l": 0, "c": 0.5, "r": 1}[o.anchor[0]], {"t": 0, "c": 0.5, "b": 1}[o.anchor[1]]
    px = int(round(x * sc - ax * im.width))
    py = int(round(y * sc - ay * im.height))
    if o.bob:
        py -= (o.bob * sc) if int(t / 0.5) % 2 else 0
    rev = o.at("reveal", t)
    if rev < 0.999 and o.edges:
        im = reveal_crop(im, o.edges, rev)
    for (t0, t1, kind, p) in o.fx:
        if not (t0 <= t < t1):
            continue
        u = (t - t0) / max(1e-6, t1 - t0)
        if kind == "flash":
            if int((t - t0) / 0.1) % 2 == 0:
                im = o.tinted(im, p["color"])
        elif kind == "shake":
            px += int(round(p["amp"] * sc * math.sin(u * 40) * (1 - u)))
        elif kind == "jump":
            ph = (u * p["n"]) % 1
            py -= int(round(p["h"] * sc * 4 * ph * (1 - ph)))
        elif kind == "pop":
            if u < 0.5:
                im = o.tinted(im, W_)
        elif kind == "blink":
            if int(u * 6) % 2 == 1:
                return
        elif kind == "wipe":
            cut = int(im.width * u)
            if cut <= 0:
                return
            im = im.crop((0, 0, cut, im.height))
    layer = fine if o.fine else art
    # 完全在画布外（例如从左/上方滑入的起点）：不画。alpha_composite 不接受越界的源区域
    if px >= layer.width or py >= layer.height or px + im.width <= 0 or py + im.height <= 0:
        return
    if vis < 0.999:
        m = bayer_mask(layer.width, layer.height, vis).crop((px, py, px + im.width, py + im.height))
        a = ImageChops.multiply(im.getchannel("A"), m)
        if layer.mode == "RGB":
            layer.paste(im.convert("RGB"), (px, py), a)
        else:
            tmp = im.copy()
            tmp.putalpha(a)
            layer.alpha_composite(tmp, (max(0, px), max(0, py)), (max(0, -px), max(0, -py)))
    else:
        if layer.mode == "RGB":
            layer.paste(im, (px, py), im)
        else:
            layer.alpha_composite(im, (max(0, px), max(0, py)), (max(0, -px), max(0, -py)))


def reveal_crop(im, edges, rev):
    """打字机：edges = [(y0, y1, [右边界...]), ...] 多行；按总字数比例显示。"""
    total = sum(len(e[2]) for e in edges)
    k = int(rev * total + 1e-6)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    for (y0, y1, xs) in edges:
        if k <= 0:
            break
        take = min(k, len(xs))
        if take > 0:
            x1 = xs[take - 1]
            out.paste(im.crop((0, y0, x1, y1)), (0, y0))
        k -= take
    return out


# ================================================================================================
# 对话框（字幕）
# ================================================================================================
DLG = (3, 138, 316, 177)      # 对话框外框
DLG_TEXT_X = 42
DLG_SIZE = 12
DLG_LINE = 15
DLG_WIDTH = 316 - 8 - DLG_TEXT_X


def chunk_text(text: str) -> list[tuple[int, int]]:
    """把一句旁白切成对话框里一页页的片段（每页最多两行），返回字号区间。"""
    clauses, start = [], 0
    for i, ch in enumerate(text):
        if ch in "，。：；？！、" or i == len(text) - 1:
            j = i + 1
            while j < len(text) and text[j] in "”’）」』":
                j += 1
            if j > start:
                clauses.append((start, j))
            start = j
    if start < len(text):
        clauses.append((start, len(text)))
    pages, cur = [], None
    for a, b in clauses:
        if cur is None:
            cur = (a, b)
            continue
        cand = (cur[0], b)
        if len(wrap(text[cand[0]:cand[1]], DLG_SIZE, DLG_WIDTH)) <= 2:
            cur = cand
        else:
            pages.append(cur)
            cur = (a, b)
    if cur:
        pages.append(cur)
    out = []
    for a, b in pages:                               # 单个子句太长：硬切
        lines = wrap(text[a:b], DLG_SIZE, DLG_WIDTH)
        if len(lines) <= 2:
            out.append((a, b))
            continue
        pos = a
        for k in range(0, len(lines), 2):
            seg = "".join(lines[k:k + 2])
            out.append((pos, pos + len(seg)))
            pos += len(seg)
    return out


_dialog_cache: dict = {}


def dialog_frame():
    if "frame" not in _dialog_cache:
        from pixel.kit import rpg_window   # noqa: circular-safe
        _dialog_cache["frame"] = rpg_window(DLG[2] - DLG[0] + 1, DLG[3] - DLG[1] + 1)
    return _dialog_cache["frame"]


def draw_dialog(s: Scene, art: Image.Image, t: float):
    # 找当前该显示的旁白片段
    active = None
    for i, nr in enumerate(s.narr):
        if "pages" not in nr:
            nr["pages"] = chunk_text(nr["text"])
        nxt_t = s.narr[i + 1]["t"] if i + 1 < len(s.narr) else 1e9
        if nr["t"] <= t < min(nr["t"] + nr["dur"] + 0.9, nxt_t):
            active = nr
            break
    if active is None:
        return
    pages = active["pages"]
    chars = active["chars"]
    page = pages[0]
    for pg in pages:
        if chars[pg[0]] <= t + 1e-3:
            page = pg
    frame = dialog_frame()
    art.paste(frame, (DLG[0], DLG[1]), frame)
    # 头像（说话时嘴巴开合）
    speaking = any(chars[i] <= t < chars[i] + 0.12 for i in range(page[0], page[1])) and t < active["t"] + active["dur"]
    from pixel.kit import avatar_img
    av = avatar_img(s.speaker, speaking and int(t * 10) % 2 == 0)
    art.paste(av, (DLG[0] + 6, DLG[1] + 5), av)
    # 打字机
    txt = active["text"][page[0]:page[1]]
    shown = sum(1 for i in range(page[0], page[1]) if chars[i] <= t + 0.02)
    key = ("dlg", id(active), page)
    if key not in _dialog_cache:
        lines = wrap(txt, DLG_SIZE, DLG_WIDTH)
        _dialog_cache[key] = [(ln, text_mask(ln, DLG_SIZE)) for ln in lines]
    rendered = _dialog_cache[key]
    y = DLG[1] + 6 if len(rendered) == 2 else DLG[1] + 13
    left = shown
    for ln, (mask, edges) in rendered:
        if left <= 0:
            break
        k = min(left, len(ln))
        x1 = edges[k - 1]
        mk = mask.crop((0, 0, x1, mask.height))
        art.paste(K, (DLG_TEXT_X + 1, y + 1), mk)
        art.paste(W_, (DLG_TEXT_X, y), mk)
        left -= len(ln)
        y += DLG_LINE
    # 翻页提示 ▼
    if shown >= len(txt) and page != pages[-1] and int(t * 3) % 2 == 0:
        x, yy = DLG[2] - 12, DLG[3] - 9
        ImageDraw.Draw(art).polygon([(x, yy), (x + 6, yy), (x + 3, yy + 3)], fill=Y)


# ================================================================================================
# 一集
# ================================================================================================
class Episode:
    def __init__(self, tag: str, title: str = ""):
        self.tag, self.title = tag, title
        self.ep_dir = PROD / tag
        self.voice = VoiceBank(self.ep_dir)
        self.builders: list[tuple[str, str, object]] = []
        self.scenes: list[Scene] = []

    def scene(self, name, title=""):
        def deco(fn):
            self.builders.append((name, title, fn))
            return fn
        return deco

    def build(self, only=None):
        self.scenes = []
        for name, title, fn in self.builders:
            if only and name not in only:
                continue
            s = Scene(self, name, title)
            fn(s)
            s.t = math.ceil(s.t * FPS - 1e-6) / FPS
            self.scenes.append(s)
        return self.scenes


if __name__ == "__main__":
    print("engine ok")
