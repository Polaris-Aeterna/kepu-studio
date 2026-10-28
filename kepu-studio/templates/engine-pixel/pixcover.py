"""《证明的极限》第一季封面 · 像素勇者风（8/16-bit RPG 画面）。

    （kepu 版：由 pixel/kit.py 加载，提供角色、道具、窗口的画法函数 pc.*；下面的封面批量入口是《地基之下》用的，
    要做自己的封面，照 cover() 的写法写一个，或者在分镜里写一个封面场景用 --still 出图。）

每张图都画在 320x180 的低分辨率画布上（有限调色板、无抗锯齿），最后 NEAREST 放大 6 倍到 1920x1080。
中文用 Noto Sans SC Bold 小字号 + fontmode "1" 渲染成点阵字；拉丁字母/数字用手写的 5x7 点阵字体。

输出：production/epNN/cover/cover_pixel_16x9.png 与 cover_pixel_4x3.png（中间 x 240–1680 裁成 1440x1080），
合集：production/season_cover/season_pixel_16x9.png 与 _4x3.png。

左上角是楼层牌（TEXT 的 floor，与宣传海报的层名一致）；对话框是这一层的谜题（TEXT 的 title，"|" 是换行位置）。
2026-10-25 起 B 站像素版标题 = 谜题 + 搜索词｜数理逻辑NN，不再和对话框逐字一致。
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

# ================================================================================================
# 每集文字（改这里再重跑即可）。title 里的 "|" = 换行位置。
# ================================================================================================
TEXT = {
    1: {"floor": "六只上锁的宝箱", "stack": True, "title": "机器能列出|全部数学真理吗？", "boss": "全部数学真理", "yes": "▶不能", "no": "能"},
    2: {"floor": "理发师的店", "title": "理发师悖论，|其实是一条定理"},
    3: {"floor": "方月亮神殿", "title": "如果2+2=5，|月亮就是方的？", "sign": "2+2=5"},
    4: {"floor": "乌龟不认 Z", "title": "乌龟认了A和B，|为什么不认Z？", "card": ["A✓", "B✓", "Z?"], "pages": "CDEF"},
    5: {"floor": "无限大的地图", "title": "无限大的地图，|能涂好吗？"},
    6: {"floor": "人人都爱某人", "title": "人人都爱某人，|和有人被人人爱，|一样吗？"},
    7: {"floor": "哥德尔的两扇门", "title": "哥德尔先证“完备”，|又证“不完备”，|矛盾吗？", "chestA": "完备", "chestB": "不完备"},
    8: {"floor": "c 的巢穴", "title": "比所有自然数都大的|“数”", "boss": "c", "hp": "∞?"},
    9: {"floor": "棋盘回廊", "title": "“有限”两个字，|一阶逻辑说不出", "bubble": "有…有…"},
    10: {"floor": "死循环转盘", "title": "万能的死循环检测器，|存在吗？", "item": "???"},
    11: {"floor": "对角线迷宫", "title": "四个著名论证，|其实是同一张图", "tables": ["康托尔", "罗素", "图灵", "说谎者"]},
    12: {"floor": "编码工坊", "title": "只会加法和乘法，|算术怎么谈论证明？", "number": "86027513949", "bubble": "我是公式！"},
    13: {"floor": "“我不能被证明”", "title": "“我不能被证明”，|算术句子能这么说？", "tablet": ["我不能", "被证明"]},
    14: {"floor": "Con(T) 之镜", "title": "一个理论，|能证明自己不矛盾吗？", "mirror": "Con(T)?", "opened": "ABCDE"},
    15: {"floor": "地牢的尽头？", "title": "哥德尔定理|没说的那些事", "banner": "THE END?"},
    0: {"title": "证明的极限", "sub": "地基之下 · 第一季", "press": "PRESS START"},
}
# B 站像素版单集标题（2026-10-25 起）：这一层的谜题 + 搜索词｜数理逻辑NN；问句里已有搜索词就不重复。
# 封面左上角是楼层牌、对话框是谜题；标题负责被检索，所以和对话框不必逐字一致。
BILI = {
    1: "机器能列出全部数学真理吗？哥德尔不完备定理｜数理逻辑01",
    2: "理发师悖论，其实是一条定理｜数理逻辑02",
    3: "如果2+2=5，月亮就是方的？命题逻辑｜数理逻辑03",
    4: "乌龟认了A和B，为什么不认Z？形式证明｜数理逻辑04",
    5: "无限大的地图，能涂好吗？紧致性定理｜数理逻辑05",
    6: "人人都爱某人，和有人被人人爱，一样吗？一阶逻辑｜数理逻辑06",
    7: "哥德尔先证“完备”，又证“不完备”，矛盾吗？完备性定理｜数理逻辑07",
    8: "有比所有自然数都大的“数”吗？非标准模型｜数理逻辑08",
    9: "“有限”两个字，一阶逻辑说不出｜数理逻辑09",
    10: "万能的死循环检测器，存在吗？停机问题｜数理逻辑10",
    11: "四个著名论证，为什么是同一张图？对角线论证｜数理逻辑11",
    12: "只会加法和乘法，算术怎么谈论证明？哥德尔编码｜数理逻辑12",
    13: "“我不能被证明”，算术句子能这么说？哥德尔句｜数理逻辑13",
    14: "一个理论，能证明自己不矛盾吗？哥德尔第二不完备定理｜数理逻辑14",
    15: "哥德尔不完备定理没说的那些事｜数理逻辑15",
}
SERIES = "证明的极限"

HERE = Path(__file__).resolve().parent
PROD = HERE.parent
sys.path.insert(0, str(PROD))
from pixel.engine import SANS_B  # noqa: E402  (same font resolution as the engine)

S = 6                      # 一个像素 = 6x6 实际像素
LW, LH = 320, 180          # 低分辨率画布
SAFE_L, SAFE_R = 40, 280   # = 240..1680 实际像素
SAFE_B = 150               # y > 150 (= 900 实际) 不放重要文字

# ---- 调色板（16 色基础 + 每集少量场景色） --------------------------------------------------------
K = (14, 9, 30)        # 描边黑
N = (30, 26, 70)       # 深蓝（窗口底色）
n = (48, 44, 108)
V = (78, 48, 128)      # 紫
v = (124, 78, 176)
M = (214, 84, 196)     # 品红
R = (234, 58, 82)      # 红
O = (250, 146, 56)     # 橙
Y = (255, 218, 76)     # 黄
W = (252, 246, 228)    # 米白
G = (160, 166, 204)    # 灰
g = (90, 94, 140)
E = (70, 206, 118)     # 绿
e = (30, 124, 96)
C = (82, 206, 240)     # 青
B = (52, 104, 214)     # 蓝
SKIN = (246, 196, 150)
SKIN_D = (206, 140, 104)
WOOD = (176, 112, 60)
WOOD_D = (116, 68, 40)
LILAC = (200, 160, 230)

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

# ---- 5x7 点阵字体 ------------------------------------------------------------------------------
F5 = {
    "0": [".XXX.", "X...X", "X..XX", "X.X.X", "XX..X", "X...X", ".XXX."],
    "1": ["..X..", ".XX..", "..X..", "..X..", "..X..", "..X..", ".XXX."],
    "2": [".XXX.", "X...X", "....X", "...X.", "..X..", ".X...", "XXXXX"],
    "3": ["XXXXX", "...X.", "..X..", "...X.", "....X", "X...X", ".XXX."],
    "4": ["...X.", "..XX.", ".X.X.", "X..X.", "XXXXX", "...X.", "...X."],
    "5": ["XXXXX", "X....", "XXXX.", "....X", "....X", "X...X", ".XXX."],
    "6": ["..XX.", ".X...", "X....", "XXXX.", "X...X", "X...X", ".XXX."],
    "7": ["XXXXX", "....X", "...X.", "..X..", ".X...", ".X...", ".X..."],
    "8": [".XXX.", "X...X", "X...X", ".XXX.", "X...X", "X...X", ".XXX."],
    "9": [".XXX.", "X...X", "X...X", ".XXXX", "....X", "...X.", ".XX.."],
    "A": [".XXX.", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"],
    "B": ["XXXX.", "X...X", "X...X", "XXXX.", "X...X", "X...X", "XXXX."],
    "C": [".XXX.", "X...X", "X....", "X....", "X....", "X...X", ".XXX."],
    "D": ["XXXX.", "X...X", "X...X", "X...X", "X...X", "X...X", "XXXX."],
    "E": ["XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "XXXXX"],
    "F": ["XXXXX", "X....", "X....", "XXXX.", "X....", "X....", "X...."],
    "G": [".XXXX", "X....", "X....", "X.XXX", "X...X", "X...X", ".XXXX"],
    "H": ["X...X", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"],
    "L": ["X....", "X....", "X....", "X....", "X....", "X....", "XXXXX"],
    "O": [".XXX.", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."],
    "P": ["XXXX.", "X...X", "X...X", "XXXX.", "X....", "X....", "X...."],
    "R": ["XXXX.", "X...X", "X...X", "XXXX.", "X.X..", "X..X.", "X...X"],
    "S": [".XXXX", "X....", "X....", ".XXX.", "....X", "....X", "XXXX."],
    "T": ["XXXXX", "..X..", "..X..", "..X..", "..X..", "..X..", "..X.."],
    "V": ["X...X", "X...X", "X...X", "X...X", "X...X", ".X.X.", "..X.."],
    "Z": ["XXXXX", "....X", "...X.", "..X..", ".X...", "X....", "XXXXX"],
    "c": [".....", ".....", ".XXXX", "X....", "X....", "X....", ".XXXX"],
    "+": [".....", "..X..", "..X..", "XXXXX", "..X..", "..X..", "....."],
    "-": [".....", ".....", ".....", "XXXXX", ".....", ".....", "....."],
    "=": [".....", ".....", "XXXXX", ".....", "XXXXX", ".....", "....."],
    ".": [".....", ".....", ".....", ".....", ".....", ".XX..", ".XX.."],
    "!": ["..X..", "..X..", "..X..", "..X..", "..X..", ".....", "..X.."],
    "?": [".XXX.", "X...X", "....X", "...X.", "..X..", ".....", "..X.."],
    " ": ["...", "...", "...", "...", "...", "...", "..."],
    "∞": [".......", ".XX.XX.", "X..X..X", "X..X..X", "X..X..X", ".XX.XX.", "......."],
    "N": ["X...X", "X...X", "XX..X", "X.X.X", "X..XX", "X...X", "X...X"],
    "o": [".....", ".....", ".XXX.", "X...X", "X...X", "X...X", ".XXX."],
    "n": [".....", ".....", "XXXX.", "X...X", "X...X", "X...X", "X...X"],
    "(": ["..X", ".X.", "X..", "X..", "X..", ".X.", "..X"],
    ")": ["X..", ".X.", "..X", "..X", "..X", ".X.", "X.."],
    "✓": ["......", ".....X", "....XX", "X..XX.", "XXXX..", ".XX...", "......"],
}

# 符号砖（5x5）
SYM = {
    "A": ["X...X", "X...X", "XXXXX", ".X.X.", "..X.."],          # ∀
    "E": ["XXXXX", "....X", ".XXXX", "....X", "XXXXX"],          # ∃
    "=": [".....", "XXXXX", ".....", "XXXXX", "....."],
    "+": ["..X..", "..X..", "XXXXX", "..X..", "..X.."],
    "~": [".....", "XXXXX", "....X", "....X", "....."],          # ¬
    "|": ["X....", "X....", "XXXXX", "X....", "X...."],          # ⊢
    "<": ["...X.", "..X..", ".X...", "..X..", "...X."],
    "1": [".X...", "XX...", ".X.X.", ".XXXX", "...X."],
    "M": ["X....", "XXXXX", "X....", "XXXXX", "X...."],          # ⊨
    "#": ["...X.", "XXXXX", "..X..", "XXXXX", ".X..."],          # ≠
}
HEART = [".XX.XX.", "XXXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."]
HEART_S = [".X.X.", "XXXXX", "XXXXX", ".XXX.", "..X.."]


class Pix:
    def __init__(self, bg=K, size=(LW, LH)):
        self.w, self.h = size
        self.im = Image.new("RGB", size, bg)
        self.d = ImageDraw.Draw(self.im)

    # -- 基础 --
    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.im.putpixel((int(x), int(y)), c)

    def rect(self, x0, y0, x1, y1, c):            # 含端点
        self.d.rectangle([x0, y0, x1, y1], fill=c)

    def box(self, x0, y0, x1, y1, fill, outline=K):
        self.d.rectangle([x0, y0, x1, y1], fill=outline)
        self.d.rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], fill=fill)

    def bitmap(self, rows, x, y, c, k=1):
        for j, row in enumerate(rows):
            for i, b in enumerate(row):
                if b == "X":
                    self.rect(x + i * k, y + j * k, x + i * k + k - 1, y + j * k + k - 1, c)

    def dither_fill(self, mask: Image.Image, c, level: float):
        """mask(L, 与画布同尺寸) 内按 Bayer 阈值铺颜色 c，level∈[0,1] 为覆盖率。"""
        mp = mask.load()
        bb = mask.getbbox()
        if not bb:
            return
        for y in range(bb[1], bb[3]):
            for x in range(bb[0], bb[2]):
                if mp[x, y] and BAYER[y % 4][x % 4] < level * 16:
                    self.im.putpixel((x, y), c)

    def vgrad(self, y0, y1, stops, x0=0, x1=None):
        """竖直有序抖动渐变：stops 均匀分布在 y0..y1。"""
        x1 = self.w - 1 if x1 is None else x1
        segs = len(stops) - 1
        for y in range(max(0, y0), min(self.h - 1, y1) + 1):
            t = (y - y0) / max(1, (y1 - y0)) * segs
            i = min(int(t), segs - 1)
            f = t - i
            for x in range(x0, x1 + 1):
                self.im.putpixel((x, y), stops[i + 1] if BAYER[y % 4][x % 4] < f * 16 else stops[i])

    def mask(self):
        return Image.new("L", (self.w, self.h), 0)

    def ellipse_mask(self, cx, cy, rx, ry):
        m = self.mask()
        ImageDraw.Draw(m).ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=255)
        return m

    def ridge(self, y_base, lo, hi, col, seed, step=(-1, 0, 0, 1)):
        rnd = random.Random(seed)
        h = (lo + hi) // 2
        for x in range(self.w):
            h = max(lo, min(hi, h + rnd.choice(step)))
            self.rect(x, y_base - h, x, y_base, col)

    # -- 字 --
    def glyphs(self, s, x, y, c, k=1, shadow=None, outline=None):
        """5x7 点阵字，k 倍。返回宽度。"""
        def draw(xx, yy, col):
            cx = xx
            for ch in s:
                rows = F5[ch]
                self.bitmap(rows, cx, yy, col, k)
                cx += (len(rows[0]) + 1) * k
            return cx - xx - k
        if outline:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx or dy:
                        draw(x + dx, y + dy, outline)
            if shadow:
                draw(x + 1, y + 2, outline)
        elif shadow:
            draw(x + 1, y + 1, shadow)
        return draw(x, y, c)

    @staticmethod
    def glyphs_w(s, k=1):
        return sum((len(F5[ch][0]) + 1) * k for ch in s) - k

    @staticmethod
    def cjk_mask(s, size, font=SANS_B):
        """逐字渲染成点阵 mask：汉字墨迹居中放进等宽格，标点/拉丁按墨迹宽度收紧。"""
        f = ImageFont.truetype(font, size)
        ref = f.getbbox("国")
        top, bot = ref[1] - 1, ref[3] + 1
        hgt = bot - top
        cells = []
        for ch in s:
            if ch == " ":
                cells.append(Image.new("L", (size // 3, hgt), 0))
                continue
            m = Image.new("L", (size * 2, size * 2), 0)
            dm = ImageDraw.Draw(m)
            dm.fontmode = "1"
            dm.text((size // 2, 0), ch, font=f, fill=255)
            bb = m.getbbox()
            if not bb:
                continue
            ink = m.crop((bb[0], top, bb[2], bot))
            if "一" <= ch <= "鿿":
                # 小字号下 hinting 会让字左右漂移：墨迹居中放进 size+1 宽的格子，字距才匀
                cw = size + 1
                cell = Image.new("L", (cw, hgt), 0)
                cell.paste(ink, ((cw - ink.width) // 2, 0))
                cells.append(cell)
            else:
                pad = 2 if ch.isalnum() or ch in "+=·" else 1
                if ch == "·":
                    pad = 3
                cells.append(Image.new("L", (pad, hgt), 0))
                cells.append(ink)
                cells.append(Image.new("L", (pad, hgt), 0))
        w = sum(c.width for c in cells)
        out = Image.new("L", (w + 4, hgt + 4), 0)
        x = 2
        for c in cells:
            out.paste(c, (x, 2))
            x += c.width
        bb = out.getbbox()
        return out.crop((bb[0] - 2, 0, bb[2] + 2, out.height))

    def cjk(self, s, x, y, size, c, shadow=None, outline=None, font=SANS_B):
        """中文点阵字。(x, y) 是字面上沿左端。返回宽度。"""
        m = Pix.cjk_mask(s, size, font)
        ox, oy = x - 2, y - 3
        if outline:
            om = m.filter(ImageFilter.MaxFilter(3))
            if shadow:
                self.im.paste(outline, (ox + 1, oy + 2), om)
            self.im.paste(outline, (ox, oy), om)
        elif shadow:
            self.im.paste(shadow, (ox + 1, oy + 1), m)
        self.im.paste(c, (ox, oy), m)
        return m.width - 4

    @staticmethod
    def cjk_w(s, size, font=SANS_B):
        return Pix.cjk_mask(s, size, font).width - 4

    # -- RPG 部件 --
    def window(self, x0, y0, x1, y1, fill=N):
        """RPG 窗口：黑描边 + 米白双线边框 + 圆角 + 深蓝底。"""
        d = self.d
        d.rectangle([x0 + 1, y0, x1 - 1, y1], fill=K)
        d.rectangle([x0, y0 + 1, x1, y1 - 1], fill=K)
        d.rectangle([x0 + 2, y0 + 1, x1 - 2, y1 - 1], fill=W)
        d.rectangle([x0 + 1, y0 + 2, x1 - 1, y1 - 2], fill=W)
        d.rectangle([x0 + 2, y0 + 2, x1 - 2, y1 - 2], fill=G)
        d.rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], fill=K)
        d.rectangle([x0 + 4, y0 + 4, x1 - 4, y1 - 4], fill=fill)
        d.line([x0 + 4, y0 + 4, x1 - 4, y0 + 4], fill=n if fill == N else fill)

    def bubble(self, x0, y0, x1, y1, tail, fill=W):
        """气泡，tail = 尾巴尖的位置（在气泡下方）。"""
        tx, ty = tail
        bx = max(x0 + 4, min(x1 - 10, tx - 3))
        self.d.polygon([(bx, y1 - 1), (bx + 7, y1 - 1), (tx, ty)], fill=K)
        self.d.rounded_rectangle([x0, y0, x1, y1], radius=3, fill=fill, outline=K)
        self.d.polygon([(bx + 1, y1 - 1), (bx + 6, y1 - 1), (tx + (1 if tx < bx + 3 else -1), ty - 2)], fill=fill)

    def hp_bar(self, x0, y0, w, frac, col=E, dark=e, h=4):
        self.box(x0, y0, x0 + w, y0 + h + 1, K)
        fw = int((w - 2) * frac)
        if fw > 0:
            self.rect(x0 + 1, y0 + 1, x0 + fw, y0 + h, col)
            self.rect(x0 + 1, y0 + 1, x0 + fw, y0 + 1, W if col != R else Y)
            self.rect(x0 + 1, y0 + h, x0 + fw, y0 + h, dark)

    def sym(self, key, x, y, c, k=1):
        self.bitmap(SYM[key], x, y, c, k)

    def twinkle(self, x, y, c=W, big=False):
        self.px(x, y, c)
        if big:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                self.px(x + dx, y + dy, c)
            for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                self.px(x + dx, y + dy, G if c == W else c)

    def stars(self, y0, y1, nsmall, nbig, seed, avoid=(), cols=(W, G, C, Y)):
        rnd = random.Random(seed)
        for i in range(nsmall + nbig):
            for _ in range(20):
                x, y = rnd.randrange(2, self.w - 2), rnd.randrange(y0, y1)
                if not any(a <= x <= b and c_ <= y <= d_ for a, c_, b, d_ in avoid):
                    break
            big = i >= nsmall
            self.twinkle(x, y, rnd.choice(cols) if big else rnd.choice([G, g, W]), big=big)

    def stamp(self, sub: "Pix", x, y, flip=False, key=(1, 2, 3)):
        """把子画布（背景色 key 视为透明）贴上来。"""
        im = sub.im.transpose(Image.FLIP_LEFT_RIGHT) if flip else sub.im
        m = Image.eval(ImageChops.difference(im, Image.new("RGB", im.size, key)).convert("L"), lambda a: 255 if a else 0)
        self.im.paste(im, (x, y), m)

    def out(self):
        return self.im.resize((LW * S, LH * S), Image.NEAREST)


# ================================================================================================
# 角色与道具
# ================================================================================================
def sweat(p: Pix, x, y):
    p.rect(x + 1, y, x + 1, y, K)
    p.rect(x, y + 1, x + 2, y + 3, K)
    p.rect(x + 1, y + 1, x + 1, y + 2, C)
    p.px(x + 1, y + 3, W)


def robot(p: Pix, x, yf, face="right", eyes="o", mouth="line", arms="down"):
    """小机器人勇者，x=左边，yf=脚底所在行。约 22 宽 x 41 高（含天线）。"""
    # 天线
    p.rect(x + 10, yf - 37, x + 11, yf - 33, K)
    p.box(x + 8, yf - 41, x + 13, yf - 36, Y)
    p.px(x + 9, yf - 40, W)
    # 头
    p.box(x + 1, yf - 33, x + 20, yf - 17, G)
    p.rect(x + 2, yf - 32, x + 19, yf - 32, W)
    p.rect(x + 19, yf - 31, x + 19, yf - 18, g)
    p.rect(x + 2, yf - 18, x + 19, yf - 18, g)
    p.box(x - 1, yf - 28, x + 1, yf - 23, g)
    p.box(x + 20, yf - 28, x + 22, yf - 23, g)
    # 屏幕脸
    p.box(x + 4, yf - 30, x + 17, yf - 20, N)
    ex = (x + 8, x + 13) if face == "right" else (x + 6, x + 11)
    if face == "front":
        ex = (x + 7, x + 12)
    if eyes == "o":
        for xx in ex:
            p.rect(xx, yf - 28, xx + 1, yf - 25, C)
            p.px(xx, yf - 28, W)
    elif eyes == "sq":
        for xx in ex:
            p.rect(xx, yf - 28, xx + 2, yf - 25, C)
            p.px(xx, yf - 28, W)
    elif eyes == "worry":   # 八字眉 + 小眼
        for i, xx in enumerate(ex):
            p.rect(xx, yf - 26, xx + 1, yf - 25, C)
            if i == 0:
                p.px(xx - 1, yf - 28, C)
                p.px(xx, yf - 29, C)
            else:
                p.px(xx + 2, yf - 28, C)
                p.px(xx + 1, yf - 29, C)
    elif eyes == "squeeze":  # > <
        a, b = ex
        for (px_, py_) in ((0, 0), (1, 1), (2, 2), (1, 3), (0, 4)):
            p.px(a - 1 + px_, yf - 29 + py_, C)
        for (px_, py_) in ((2, 0), (1, 1), (0, 2), (1, 3), (2, 4)):
            p.px(b + px_, yf - 29 + py_, C)
    elif eyes == "happy":   # ^ ^
        for xx in ex:
            p.px(xx, yf - 26, C)
            p.px(xx + 1, yf - 27, C)
            p.px(xx + 2, yf - 26, C)
    mx = x + 9 if face == "right" else x + 8
    if face == "front":
        mx = x + 9
    if mouth == "line":
        p.rect(mx, yf - 23, mx + 3, yf - 23, C)
    elif mouth == "o":
        p.box(mx, yf - 24, mx + 3, yf - 21, N, C)
    elif mouth == "wavy":
        for i in range(5):
            p.px(mx - 1 + i, yf - 22 - (i % 2), C)
    elif mouth == "smile":
        p.px(mx, yf - 23, C)
        p.rect(mx + 1, yf - 22, mx + 2, yf - 22, C)
        p.px(mx + 3, yf - 23, C)
    elif mouth == "tape":    # 嘴上贴了胶带（X）
        for (a_, b_) in (((x + 4, yf - 25), (x + 17, yf - 19)), ((x + 4, yf - 19), (x + 17, yf - 25))):
            p.d.line([a_, b_], fill=K, width=5)
        for (a_, b_) in (((x + 5, yf - 25), (x + 16, yf - 19)), ((x + 5, yf - 19), (x + 16, yf - 25))):
            p.d.line([a_, b_], fill=(240, 222, 170), width=3)
    # 脖子 / 身体
    p.rect(x + 8, yf - 17, x + 13, yf - 15, K)
    p.box(x + 3, yf - 16, x + 18, yf - 6, B)
    p.rect(x + 4, yf - 15, x + 17, yf - 15, C)
    p.rect(x + 17, yf - 14, x + 17, yf - 7, N)
    p.box(x + 7, yf - 13, x + 14, yf - 9, N)
    p.rect(x + 8, yf - 12, x + 9, yf - 11, R)
    p.rect(x + 11, yf - 12, x + 13, yf - 11, Y)
    # 胳膊
    if arms == "up":
        p.box(x - 2, yf - 39, x + 1, yf - 12, g)
        p.box(x + 20, yf - 39, x + 23, yf - 12, g)
        p.box(x - 3, yf - 42, x + 2, yf - 38, G)
        p.box(x + 19, yf - 42, x + 24, yf - 38, G)
    else:
        p.box(x, yf - 15, x + 3, yf - 8, g)
        p.box(x + 18, yf - 15, x + 21, yf - 8, g)
    # 腿和脚
    p.box(x + 5, yf - 6, x + 9, yf - 2, g)
    p.box(x + 12, yf - 6, x + 16, yf - 2, g)
    p.box(x + 3, yf - 3, x + 9, yf, K)
    p.box(x + 12, yf - 3, x + 18, yf, K)
    p.rect(x + 4, yf - 2, x + 8, yf - 2, g)
    p.rect(x + 13, yf - 2, x + 17, yf - 2, g)


def robot_portrait(p: Pix, x0, y0, x1, y1, eyes="sq", mouth="o"):
    """对话框里的大头像：机器人脸。"""
    p.box(x0, y0, x1, y1, n)
    p.rect(x0 + 1, y0 + 1, x1 - 1, y0 + (y1 - y0) // 2, (58, 54, 124))
    w, h = x1 - x0, y1 - y0
    hx0, hy0 = x0 + 6, y0 + 16
    hx1, hy1 = x1 - 6, y1 - 2
    # 天线
    cx = (hx0 + hx1) // 2
    p.rect(cx - 1, hy0 - 8, cx, hy0, K)
    p.box(cx - 4, hy0 - 13, cx + 3, hy0 - 7, Y)
    p.px(cx - 3, hy0 - 12, W)
    p.box(hx0, hy0, hx1, hy1 + 4, G)
    p.rect(hx0 + 1, hy0 + 1, hx1 - 1, hy0 + 1, W)
    p.rect(hx1 - 1, hy0 + 2, hx1 - 1, hy1 + 3, g)
    p.box(hx0 + 4, hy0 + 4, hx1 - 4, hy1 - 2, N)
    # 大眼睛（惊讶）
    ey = hy0 + 9
    for exx in (hx0 + 9, hx1 - 13):
        p.rect(exx, ey, exx + 3, ey + 6, C)
        p.rect(exx, ey, exx + 1, ey + 1, W)
    # 嘴
    my = hy1 - 9
    p.box(cx - 3, my, cx + 2, my + 4, N, C)
    _ = (w, h)


def golem(p: Pix, cx, yf):
    """「全部数学真理」魔王：刻着符号的石砖巨像，从对话框后面升起，只露出头、肩和举起的双拳。"""
    p.dither_fill(p.ellipse_mask(cx, yf - 30, 78, 62), V, 0.5)
    p.dither_fill(p.ellipse_mask(cx, yf - 34, 60, 48), M, 0.25)
    BS = 22
    syms = [["E", "A", "|"], ["=", "+", "~"]]
    for r in range(2):
        for c in range(3):
            bx = cx - 33 + c * BS
            by = yf - 26 + r * BS
            stone_block(p, bx, by, bx + BS - 1, by + BS - 1, syms[r][c], Y if c == 1 else M, k=2)
    for side in (-1, 1):
        sx0 = cx - 33 - BS if side < 0 else cx + 33
        stone_block(p, sx0, yf - 24, sx0 + BS - 1, yf - 3, "<" if side < 0 else "=", C, k=2)
        fx0 = sx0 - 4 if side < 0 else sx0 + 4
        stone_block(p, fx0, yf - 52, fx0 + BS - 1, yf - 26, None)
        for i in range(4):
            p.rect(fx0 + 2 + i * 5, yf - 52 + 3, fx0 + 2 + i * 5, yf - 52 + 8, N)
    hw, hh = 46, 34
    hx0, hy0 = cx - hw // 2, yf - 26 - hh
    stone_block(p, hx0, hy0, hx0 + hw - 1, hy0 + hh - 1, None)
    for ex, sgn in ((hx0 + 7, 1), (hx0 + 27, -1)):
        p.rect(ex - 1, hy0 + 12, ex + 11, hy0 + 20, K)
        p.rect(ex, hy0 + 13, ex + 10, hy0 + 19, Y)
        p.rect(ex + 3, hy0 + 14, ex + 7, hy0 + 19, R)
        p.rect(ex + 4, hy0 + 15, ex + 5, hy0 + 16, W)
        for i in range(13):
            yy = hy0 + 6 + (i // 3 if sgn > 0 else (12 - i) // 3)
            p.rect(ex - 1 + i, yy, ex - 1 + i, yy + 2, K)
    mx0, my = hx0 + 9, hy0 + 25
    p.rect(mx0, my - 2, mx0 + 27, my + 3, K)
    for i in range(0, 27, 5):
        p.rect(mx0 + i + 1, my - 2, mx0 + i + 3, my, W)
        p.rect(mx0 + i + 3, my + 1, mx0 + i + 5, my + 3, W)
    crown(p, hx0 + 3, hy0, 41, 11, gem=R)


def crown(p: Pix, x0, ybase, w, h, gem=R):
    """王冠：底边在 ybase，宽 w 高 h。"""
    x1 = x0 + w
    q = w / 4
    pts = [(x0, ybase), (x0, ybase - h + 3), (x0 + q, ybase - h + 8), (x0 + 2 * q, ybase - h),
           (x0 + 3 * q, ybase - h + 8), (x1, ybase - h + 3), (x1, ybase)]
    p.d.polygon(pts, fill=K)
    inner = [(x0 + 1, ybase - 1), (x0 + 1, ybase - h + 5), (x0 + q, ybase - h + 10), (x0 + 2 * q, ybase - h + 2),
             (x0 + 3 * q, ybase - h + 10), (x1 - 1, ybase - h + 5), (x1 - 1, ybase - 1)]
    p.d.polygon(inner, fill=Y)
    p.rect(x0 + 1, ybase - 3, x1 - 1, ybase - 1, O)
    gx = int(x0 + 2 * q)
    p.box(gx - 3, ybase - h + 5, gx + 3, ybase - h + 10, gem)
    p.px(gx - 2, ybase - h + 6, W)


def stone_block(p: Pix, x0, y0, x1, y1, symkey=None, symcol=M, base=V, hi=v, lo=N, k=1):
    p.box(x0, y0, x1, y1, base)
    p.rect(x0 + 1, y0 + 1, x1 - 1, y0 + 1, hi)
    p.rect(x0 + 1, y0 + 1, x0 + 1, y1 - 1, hi)
    p.rect(x0 + 1, y1 - 1, x1 - 1, y1 - 1, lo)
    p.rect(x1 - 1, y0 + 2, x1 - 1, y1 - 1, lo)
    if symkey:
        w = x1 - x0 + 1
        h = y1 - y0 + 1
        sx = x0 + (w - 5 * k) // 2
        sy = y0 + (h - 5 * k) // 2
        p.sym(symkey, sx + 1, sy + 1, lo, k)
        p.sym(symkey, sx, sy, symcol, k)


def floating_blocks(p: Pix, spots, seed=2):
    rnd = random.Random(seed)
    keys = ["A", "E", "=", "+", "~", "|", "<"]
    for x, y, sz in spots:
        stone_block(p, x, y, x + sz - 1, y + sz - 1, rnd.choice(keys) if sz >= 9 else None, rnd.choice([Y, M, C]))


def num_block(p: Pix, x0, y0, sz, label, base=O, hi=Y, lo=(178, 86, 40), txt=K, k=2):
    p.box(x0, y0, x0 + sz, y0 + sz, base)
    p.rect(x0 + 1, y0 + 1, x0 + sz - 1, y0 + 1, hi)
    p.rect(x0 + 1, y0 + 1, x0 + 1, y0 + sz - 1, hi)
    p.rect(x0 + 1, y0 + sz - 1, x0 + sz - 1, y0 + sz - 1, lo)
    p.rect(x0 + sz - 1, y0 + 2, x0 + sz - 1, y0 + sz - 1, lo)
    if label:
        tw = Pix.glyphs_w(label, k)
        p.glyphs(label, x0 + (sz - tw) // 2 + 1, y0 + (sz - 7 * k) // 2 + 1, txt, k=k)


C_SHAPE = ["...XXXXXX...",
           ".XXXXXXXXXX.",
           "XXXXX...XXXX",
           "XXXX.....XX.",
           "XXXX........",
           "XXXX........",
           "XXXX.....XX.",
           "XXXXX...XXXX",
           ".XXXXXXXXXX.",
           "...XXXXXX..."]


def c_boss(p: Pix, x0, yb, cell=4, aura=True, body=True, crowned=True, sparkle=True):
    """魔王 c：一个圆滚滚的点阵小写 c，眼睛蹲在上沿，看向左边。x0 = 左边，yb = 底边。"""
    rows, cols = len(C_SHAPE), len(C_SHAPE[0])
    w, h = cols * cell, rows * cell
    y0 = yb - h
    cx, cy = x0 + w // 2, y0 + h // 2
    if aura:
        p.dither_fill(p.ellipse_mask(cx, cy - 2, w // 2 + 18, h // 2 + 18), M, 0.25)
    if not body:
        return
    m = p.mask()
    md = ImageDraw.Draw(m)
    for j, row in enumerate(C_SHAPE):
        for i, b in enumerate(row):
            if b == "X":
                md.rectangle([x0 + i * cell, y0 + j * cell, x0 + (i + 1) * cell - 1, y0 + (j + 1) * cell - 1], fill=255)
    p.box(x0 + 2 * cell, yb - 1, x0 + 2 * cell + 2 * cell, yb + 3, K)
    p.box(x0 + 6 * cell, yb - 1, x0 + 6 * cell + 2 * cell, yb + 3, K)
    p.im.paste(K, (0, 0), m.filter(ImageFilter.MaxFilter(3)))
    p.im.paste(M, (0, 0), m)
    up = ImageChops.offset(m, max(1, cell // 2), max(1, cell // 2))
    dn = ImageChops.offset(m, -max(1, (3 * cell) // 4), -max(1, (3 * cell) // 4))
    hl = Image.composite(m, p.mask(), Image.eval(up, lambda a: 255 - a))
    sh = Image.composite(m, p.mask(), Image.eval(dn, lambda a: 255 - a))
    p.im.paste(V, (0, 0), sh)
    p.im.paste((248, 170, 236), (0, 0), hl)
    s = cell / 4
    mx, my = x0 + int(2 * s), y0 + 5 * cell - int(2 * s)
    tw = int(13 * s)
    p.rect(mx, my, mx + tw, my + int(6 * s), K)
    for i in range(0, tw - 1, max(2, int(4 * s))):
        p.rect(mx + 1 + i, my + 1, mx + 1 + i + max(0, int(s) - 1), my + max(1, int(2 * s)) - 0, W)
    er = int(11 * s)
    for ex in (x0 + 2 * cell - int(2 * s), x0 + 5 * cell):
        ey = y0 - int(7 * s)
        p.d.ellipse([ex - 1, ey - 1, ex + er + 1, ey + er + 1], fill=K)
        p.d.ellipse([ex, ey, ex + er, ey + er], fill=W)
        p.rect(ex + 1, ey + int(4 * s), ex + int(5 * s), ey + int(9 * s), K)
        p.rect(ex + 2, ey + int(5 * s), ex + 2 + max(0, int(s)), ey + int(5 * s) + max(0, int(s)), W)
    bl = int(12 * s)
    for i in range(bl):
        x_ = x0 + 2 * cell - int(2 * s) + i
        yy = y0 - int(11 * s) + int(i * s / 4 * 1.0 / s * 1)
        p.rect(x_, y0 - int(11 * s) + i // 4, x_, y0 - int(10 * s) + i // 4, K)
        x_ = x0 + 5 * cell + i
        p.rect(x_, y0 - int(8 * s) - i // 4, x_, y0 - int(7 * s) - i // 4, K)
        _ = yy
    if crowned:
        crown(p, x0 + 8 * cell + 1, y0 - int(1 * s), int(18 * s), int(12 * s), gem=C)
    if sparkle:
        for (sx, sy) in ((x0 - 6, y0 + 4), (x0 + w + 4, y0 + 18), (x0 + w - 2, yb - 4), (x0 - 3, yb - 10)):
            p.twinkle(sx, sy, Y, big=True)


def barber(p: Pix, x, yf):
    """理发师 NPC（虚构）：油头、八字胡、白大褂、领结，右手举剃刀。面朝右。约 30 宽 x 46 高。"""
    # 腿 + 鞋
    p.box(x + 9, yf - 11, x + 13, yf - 2, (40, 36, 60))
    p.box(x + 15, yf - 11, x + 19, yf - 2, (40, 36, 60))
    p.box(x + 7, yf - 3, x + 13, yf, K)
    p.box(x + 15, yf - 3, x + 21, yf, K)
    # 白大褂
    p.box(x + 6, yf - 27, x + 22, yf - 10, W)
    p.rect(x + 21, yf - 26, x + 21, yf - 11, G)
    p.rect(x + 14, yf - 25, x + 14, yf - 11, G)
    for yy in (yf - 23, yf - 19, yf - 15):
        p.px(x + 15, yy, g)
    # 后手臂
    p.box(x + 3, yf - 26, x + 7, yf - 14, W)
    p.box(x + 3, yf - 15, x + 7, yf - 12, SKIN)
    # 头
    p.box(x + 8, yf - 41, x + 21, yf - 27, SKIN)
    p.rect(x + 9, yf - 28, x + 20, yf - 28, SKIN_D)
    # 油头
    p.box(x + 7, yf - 45, x + 21, yf - 38, K)
    p.rect(x + 8, yf - 44, x + 20, yf - 39, (40, 30, 40))
    p.rect(x + 11, yf - 44, x + 17, yf - 44, (110, 100, 130))
    p.box(x + 7, yf - 39, x + 10, yf - 33, K)            # 鬓角
    # 耳朵
    p.box(x + 9, yf - 37, x + 11, yf - 33, SKIN_D)
    # 眼 + 眉
    p.rect(x + 16, yf - 36, x + 17, yf - 34, K)
    p.rect(x + 15, yf - 38, x + 19, yf - 38, K)
    # 鼻子
    p.box(x + 19, yf - 35, x + 23, yf - 31, SKIN)
    p.rect(x + 20, yf - 31, x + 22, yf - 31, SKIN_D)
    # 八字胡
    p.rect(x + 13, yf - 30, x + 24, yf - 29, K)
    p.rect(x + 11, yf - 31, x + 12, yf - 30, K)
    p.px(x + 11, yf - 32, K)
    p.rect(x + 25, yf - 31, x + 25, yf - 30, K)
    p.px(x + 26, yf - 32, K)
    # 领结
    p.rect(x + 11, yf - 27, x + 17, yf - 25, K)
    p.rect(x + 12, yf - 26, x + 13, yf - 26, R)
    p.rect(x + 15, yf - 26, x + 16, yf - 26, R)
    # 前手臂举剃刀
    p.box(x + 20, yf - 26, x + 25, yf - 20, W)
    p.box(x + 23, yf - 33, x + 27, yf - 24, W)
    p.box(x + 23, yf - 37, x + 27, yf - 33, SKIN)
    # 剃刀（折刀式：短柄 + 细长刀片）
    p.box(x + 24, yf - 43, x + 26, yf - 36, WOOD_D)
    p.box(x + 23, yf - 46, x + 34, yf - 43, (200, 206, 230))
    p.rect(x + 24, yf - 45, x + 33, yf - 45, W)


def barber_pole(p: Pix, x0, y0, y1):
    p.box(x0 - 1, y0 - 5, x0 + 9, y0, G)
    p.rect(x0 + 1, y0 - 4, x0 + 3, y0 - 3, W)
    p.box(x0, y0, x0 + 8, y1, W)
    for y in range(y0 + 1, y1):
        for x in range(x0 + 1, x0 + 8):
            t = (x - x0 + (y - y0)) % 12
            if t < 3:
                p.px(x, y, R)
            elif 6 <= t < 9:
                p.px(x, y, B)
    p.rect(x0 + 2, y0 + 1, x0 + 2, y1 - 1, W)
    p.box(x0 - 1, y1, x0 + 9, y1 + 5, G)


def blob(p: Pix, cx, cy, col, r=6, crowned=False, eyes="o", look=(0, 0)):
    """小团子角色（虚构）：椭圆身体 + 两只眼。"""
    hi = tuple(min(255, c + 60) for c in col)
    lo = tuple(max(0, c - 60) for c in col)
    rx, ry = r, r - 1
    p.d.ellipse([cx - rx - 1, cy - ry - 1, cx + rx + 1, cy + ry + 1], fill=K)
    p.d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=col)
    p.rect(cx - rx + 2, cy + ry - 1, cx + rx - 2, cy + ry - 1, lo)
    p.rect(cx - rx + 2, cy - ry + 1, cx - rx + 3, cy - ry + 2, hi)
    lx, ly = look
    for ex in (cx - r // 2 - 1, cx + r // 2):
        if eyes == "o":
            p.rect(ex + lx, cy - 1 + ly, ex + lx, cy + ly, K)
        elif eyes == "smug":
            p.rect(ex - 1 + lx, cy - 1 + ly, ex + 1 + lx, cy - 1 + ly, K)
            p.px(ex + lx, cy + ly, K)
        elif eyes == "heart":
            p.bitmap(HEART_S, ex - 2 + lx, cy - 2 + ly, R)
    if crowned:
        crown(p, cx - 6, cy - ry, 12, 8, gem=C)


def heart(p: Pix, x, y, col=R, small=False):
    rows = HEART_S if small else HEART
    p.bitmap(rows, x - 1, y, K)
    p.bitmap(rows, x + 1, y, K)
    p.bitmap(rows, x, y - 1, K)
    p.bitmap(rows, x, y + 1, K)
    p.bitmap(rows, x, y, col)
    p.px(x + 1, y + 1, W) if not small else None


def check_icon(p: Pix, x, y, col=E, k=1):
    p.bitmap(["......X", ".....XX", "X...XX.", "XX.XX..", ".XXX...", "..X...."], x, y, col, k)


def cross_icon(p: Pix, x, y, col=R, k=1):
    p.bitmap(["X...X", ".X.X.", "..X..", ".X.X.", "X...X"], x, y, col, k)


def chest(p: Pix, x0, yb, w=40, h=26, open_=False, locked=False):
    """宝箱。yb = 底边。"""
    y0 = yb - h
    lid = h * 2 // 5
    gold, gold_d = Y, O
    if open_:
        # 打开的盖子（向后翻起）
        p.box(x0 + 1, y0 - lid + 2, x0 + w - 1, y0 + 3, WOOD_D)
        p.rect(x0 + 3, y0 - lid + 4, x0 + w - 3, y0 + 1, (60, 30, 20))
        p.box(x0, y0 + 2, x0 + w, yb, WOOD)
        p.rect(x0 + 1, y0 + 3, x0 + w - 1, y0 + 6, (255, 240, 170))   # 箱口亮光
    else:
        p.box(x0, y0, x0 + w, yb, WOOD)
        p.d.rounded_rectangle([x0, y0 - 3, x0 + w, y0 + lid], radius=3, fill=K)
        p.d.rounded_rectangle([x0 + 1, y0 - 2, x0 + w - 1, y0 + lid - 1], radius=3, fill=WOOD)
        p.rect(x0 + 2, y0 - 1, x0 + w - 2, y0 - 1, (210, 150, 90))
        p.rect(x0, y0 + lid, x0 + w, y0 + lid, K)
    # 金属包边
    for xx in (x0 + 4, x0 + w - 7):
        p.rect(xx, y0 + (3 if open_ else -2), xx + 3, yb - 1, gold_d)
        p.rect(xx, y0 + (3 if open_ else -2), xx, yb - 1, gold)
    p.rect(x0 + 1, yb - 3, x0 + w - 1, yb - 1, WOOD_D)
    if not open_:
        cxm = x0 + w // 2
        p.box(cxm - 3, y0 + lid - 3, cxm + 3, y0 + lid + 4, gold)
        p.px(cxm, y0 + lid + 1, K)
    if locked:
        cxm = x0 + w // 2
        # 锁链交叉
        for i in range(-2, w + 3, 3):
            yy = y0 + int((i / w) * (h - 2)) - 2
            p.box(x0 + i, yy, x0 + i + 2, yy + 2, G)
            yy2 = yb - int((i / w) * (h - 2)) - 2
            p.box(x0 + i, yy2 - 2, x0 + i + 2, yy2, G)
        # 大挂锁
        p.d.arc([cxm - 6, y0 + lid - 12, cxm + 6, y0 + lid + 2], 180, 360, fill=K, width=4)
        p.d.arc([cxm - 5, y0 + lid - 11, cxm + 5, y0 + lid + 1], 180, 360, fill=G, width=2)
        p.box(cxm - 8, y0 + lid - 4, cxm + 8, y0 + lid + 9, Y)
        p.rect(cxm - 7, y0 + lid - 3, cxm + 7, y0 + lid - 3, W)
        p.rect(cxm - 1, y0 + lid + 1, cxm, y0 + lid + 5, K)


def pawn(p: Pix, cx, yb, col):
    hi = tuple(min(255, c + 70) for c in col)
    p.d.ellipse([cx - 4, yb - 17, cx + 4, yb - 9], fill=K)
    p.d.ellipse([cx - 3, yb - 16, cx + 3, yb - 10], fill=col)
    p.px(cx - 1, yb - 15, hi)
    p.d.polygon([(cx - 4, yb - 9), (cx + 4, yb - 9), (cx + 6, yb - 3), (cx - 6, yb - 3)], fill=K)
    p.d.polygon([(cx - 3, yb - 8), (cx + 3, yb - 8), (cx + 4, yb - 4), (cx - 4, yb - 4)], fill=col)
    p.box(cx - 7, yb - 3, cx + 7, yb, col)


def tortoise(p: Pix, x, yf):
    """得意的乌龟（虚构），头朝左。约 50 宽 x 30 高。"""
    SH, SH_D, SH_L = (60, 170, 90), (30, 110, 70), (120, 210, 120)
    LEG = (150, 200, 110)
    # 后腿 / 前腿
    for lx in (x + 12, x + 34):
        p.box(lx, yf - 7, lx + 7, yf, LEG)
        p.rect(lx + 1, yf - 1, lx + 6, yf - 1, (100, 150, 80))
    # 壳
    p.d.pieslice([x + 6, yf - 34, x + 48, yf + 6], 180, 360, fill=K)
    p.d.pieslice([x + 7, yf - 33, x + 47, yf + 5], 180, 360, fill=SH)
    for (hx, hy) in ((x + 19, yf - 24), (x + 30, yf - 25), (x + 13, yf - 15), (x + 25, yf - 15), (x + 37, yf - 15)):
        p.d.regular_polygon((hx + 3, hy + 3, 5), 6, fill=SH_D)
        p.d.regular_polygon((hx + 3, hy + 3, 3), 6, fill=SH_L)
    p.box(x + 5, yf - 10, x + 49, yf - 6, (220, 190, 90))
    # 头（朝左）
    p.box(x - 6, yf - 25, x + 9, yf - 11, LEG)
    p.box(x + 4, yf - 18, x + 10, yf - 8, LEG)
    p.rect(x - 5, yf - 24, x + 8, yf - 24, (190, 230, 150))
    # 半眯的得意眼
    p.rect(x - 2, yf - 21, x + 2, yf - 21, K)
    p.rect(x - 2, yf - 20, x + 2, yf - 20, W)
    p.rect(x - 1, yf - 20, x, yf - 19, K)
    # 坏笑
    p.rect(x - 5, yf - 15, x - 1, yf - 15, K)
    p.px(x, yf - 16, K)
    p.px(x - 3, yf - 22, (100, 150, 80))


def runner(p: Pix, x, yf):
    """戴希腊式头盔、满头大汗的跑者（虚构，非真人）。面朝右。约 26 宽 x 50 高。"""
    BRONZE, BRONZE_D = (236, 170, 70), (170, 104, 40)
    # 披风
    p.d.polygon([(x + 4, yf - 30), (x + 9, yf - 30), (x + 6, yf - 6), (x - 1, yf - 8)], fill=K)
    p.d.polygon([(x + 5, yf - 29), (x + 8, yf - 29), (x + 5, yf - 7), (x + 1, yf - 9)], fill=R)
    # 腿 + 凉鞋
    p.box(x + 8, yf - 12, x + 12, yf - 2, SKIN)
    p.box(x + 15, yf - 12, x + 19, yf - 2, SKIN)
    p.box(x + 7, yf - 3, x + 13, yf, WOOD_D)
    p.box(x + 15, yf - 3, x + 21, yf, WOOD_D)
    # 短袍
    p.box(x + 6, yf - 30, x + 21, yf - 11, W)
    p.rect(x + 6, yf - 19, x + 21, yf - 18, WOOD)
    p.rect(x + 20, yf - 29, x + 20, yf - 12, G)
    # 头
    p.box(x + 8, yf - 43, x + 21, yf - 30, SKIN)
    p.rect(x + 18, yf - 37, x + 19, yf - 36, K)         # 眼
    p.rect(x + 17, yf - 39, x + 20, yf - 39, K)         # 眉（八字）
    p.px(x + 17, yf - 40, K)
    p.rect(x + 16, yf - 33, x + 19, yf - 33, K)         # 嘴（发愁）
    p.px(x + 15, yf - 32, K)
    # 头盔
    p.box(x + 6, yf - 49, x + 22, yf - 41, BRONZE)
    p.box(x + 6, yf - 42, x + 11, yf - 32, BRONZE)       # 护颊
    p.rect(x + 7, yf - 48, x + 21, yf - 48, Y)
    p.rect(x + 21, yf - 47, x + 21, yf - 42, BRONZE_D)
    # 盔缨：从前额一路梳到脑后、再垂下来的马鬃
    crest = [(x + 20, yf - 49), (x + 17, yf - 55), (x + 10, yf - 57), (x + 3, yf - 55), (x - 3, yf - 49),
             (x - 4, yf - 42), (x, yf - 44), (x + 3, yf - 49)]
    p.d.polygon(crest, fill=R, outline=K)
    for i in range(0, 18, 3):
        p.px(x + 2 + i, yf - 53 + abs(i - 8) // 4, (255, 130, 130))
    p.rect(x + 6, yf - 50, x + 22, yf - 50, K)
    # 汗
    sweat(p, x + 24, yf - 44)
    sweat(p, x + 2, yf - 40)


def page(p: Pix, x, y, letter, tilt=0):
    p.box(x, y, x + 13, y + 17, W)
    p.rect(x + 1, y + 16, x + 12, y + 16, G)
    p.glyphs(letter, x + 2, y + 2, K, k=2)


def square_moon(p: Pix, x0, y0, s=48):
    """方形月亮，脸上一副“我没毛病”的表情。"""
    MOON, MOON_D = (255, 226, 110), (230, 184, 70)
    glow = p.mask()
    ImageDraw.Draw(glow).rectangle([x0 - 10, y0 - 10, x0 + s + 10, y0 + s + 10], fill=255)
    p.dither_fill(glow, (90, 90, 120), 0.25)
    glow = p.mask()
    ImageDraw.Draw(glow).rectangle([x0 - 5, y0 - 5, x0 + s + 5, y0 + s + 5], fill=255)
    p.dither_fill(glow, Y, 0.125)
    p.box(x0, y0, x0 + s, y0 + s, MOON)
    p.rect(x0 + 1, y0 + 1, x0 + s - 1, y0 + 2, (255, 246, 190))
    p.rect(x0 + s - 2, y0 + 3, x0 + s - 1, y0 + s - 1, MOON_D)
    p.rect(x0 + 1, y0 + s - 2, x0 + s - 1, y0 + s - 1, MOON_D)
    k_ = s / 48
    for (cx_, cy_, r_) in ((10, 9, 4), (36, 12, 3), (40, 36, 5), (8, 38, 3), (24, 6, 2)):
        cx_, cy_, r_ = round(cx_ * k_), round(cy_ * k_), max(1, round(r_ * k_))
        p.d.ellipse([x0 + cx_ - r_, y0 + cy_ - r_, x0 + cx_ + r_, y0 + cy_ + r_], fill=MOON_D)
        p.d.ellipse([x0 + cx_ - r_ + 1, y0 + cy_ - r_ + 1, x0 + cx_ + r_ - 1, y0 + cy_ + r_ - 1], fill=(242, 204, 90))
    def q(v_):
        return round(v_ * s / 48)
    # 闭眼得意
    for ex in (x0 + q(12), x0 + q(28)):
        p.rect(ex, y0 + q(20), ex + q(7), y0 + q(20) + 1, K)
        p.px(ex - 1, y0 + q(20) - 1, K)
        p.px(ex + q(7) + 1, y0 + q(20) - 1, K)
    # 腮红
    for bx in (x0 + q(9), x0 + q(32)):
        m = p.mask()
        ImageDraw.Draw(m).rectangle([bx, y0 + q(25), bx + q(6), y0 + q(28)], fill=255)
        p.dither_fill(m, (240, 120, 150), 0.5)
    # 微笑
    p.rect(x0 + q(19), y0 + q(31), x0 + q(28), y0 + q(31) + 1, K)
    p.px(x0 + q(19) - 1, y0 + q(31) - 1, K)
    p.px(x0 + q(28) + 1, y0 + q(31) - 1, K)


def gadget(p: Pix, x0, y0, w=32, h=24, phase=0):
    """死循环检测器：屏幕上转圈圈，输入线又插回自己。"""
    x1, y1 = x0 + w, y0 + h
    # 自己的输出线绕过头顶，又插回自己的输入口
    loop = [(x1, y0 + 8), (x1 + 6, y0 + 2), (x1 + 4, y0 - 6), (x0 + w // 2, y0 - 10), (x0 - 4, y0 - 6),
            (x0 - 6, y0 + 2), (x0, y0 + 8)]
    p.d.line(loop, fill=K, width=4, joint="curve")
    p.d.line(loop, fill=O, width=2, joint="curve")
    p.box(x0, y0, x1, y1, G)
    p.rect(x0 + 1, y0 + 1, x1 - 1, y0 + 1, W)
    p.rect(x1 - 1, y0 + 2, x1 - 1, y1 - 1, g)
    p.box(x0 + 3, y0 + 3, x0 + 20, y1 - 3, N)
    # 转圈圈
    import math
    scx, scy = x0 + 11, y0 + (h // 2)
    for i in range(8):
        a = (i + phase) / 8 * 2 * math.pi
        xx = scx + round(5 * math.cos(a))
        yy = scy + round(5 * math.sin(a))
        col = [W, C, C, B, B, n, n, n][i]
        p.rect(xx - 1, yy - 1, xx, yy, col)
    # 旋钮 + 灯
    p.box(x0 + 23, y0 + 4, x0 + 28, y0 + 9, R)
    p.box(x0 + 23, y0 + 12, x0 + 28, y0 + 17, Y)
    p.px(x0 + 24, y0 + 5, W)
    # 插口
    p.box(x0 - 2, y0 + 6, x0 + 1, y0 + 10, K)
    p.box(x1 - 1, y0 + 6, x1 + 2, y0 + 10, K)
    # 冒烟
    for (sx, sy, r_) in ((x1 + 9, y0 + 14, 2), (x1 + 13, y0 + 9, 3)):
        p.d.ellipse([sx - r_ - 1, sy - r_ - 1, sx + r_ + 1, sy + r_ + 1], fill=g)
        p.d.ellipse([sx - r_, sy - r_, sx + r_, sy + r_], fill=G)


def spinner_boss(p: Pix, cx, cy, r=28, dot=5):
    """转圈圈魔王：一圈渐隐的点，中间一张坏笑的脸。"""
    import math
    p.dither_fill(p.ellipse_mask(cx, cy, r + 14, r + 14), (120, 30, 80), 0.5)
    cols = [W, Y, Y, O, O, R, R, M, (200, 90, 200), v, (110, 80, 170), (96, 72, 150)]
    for i in range(12):
        a = -math.pi / 2 + i / 12 * 2 * math.pi
        xx = cx + round(r * math.cos(a))
        yy = cy + round(r * math.sin(a))
        rr = dot + (1 if i < 3 else 0)
        p.d.ellipse([xx - rr - 1, yy - rr - 1, xx + rr + 1, yy + rr + 1], fill=K)
        p.d.ellipse([xx - rr, yy - rr, xx + rr, yy + rr], fill=cols[i])
        if i < 3:
            p.px(xx - 1, yy - 2, W)
    # 中间的脸
    for ex, sgn in ((cx - 10, 1), (cx + 3, -1)):
        p.box(ex, cy - 6, ex + 7, cy + 1, Y)
        p.rect(ex + 2, cy - 4, ex + 4, cy + 1, R)
        for i in range(9):
            yy = cy - 9 + (i // 3 if sgn > 0 else (8 - i) // 3)
            p.rect(ex - 1 + i, yy, ex - 1 + i, yy + 1, K)
    p.rect(cx - 7, cy + 6, cx + 6, cy + 9, K)
    for i in range(0, 13, 4):
        p.rect(cx - 6 + i, cy + 6, cx - 5 + i, cy + 7, W)


def torch(p: Pix, x, y):
    p.box(x, y, x + 4, y + 12, WOOD_D)
    p.box(x - 2, y - 2, x + 6, y + 1, G)
    p.d.polygon([(x - 2, y - 2), (x + 2, y - 14), (x + 6, y - 2)], fill=R)
    p.d.polygon([(x - 1, y - 2), (x + 2, y - 10), (x + 5, y - 2)], fill=O)
    p.d.polygon([(x + 1, y - 2), (x + 2, y - 6), (x + 3, y - 2)], fill=Y)
    p.dither_fill(p.ellipse_mask(x + 2, y - 6, 16, 14), O, 0.125)


def paint_bucket(p: Pix, x, yb, col):
    """一桶颜料：铁桶 + 满满一桶色 + 外沿往下流的一道。"""
    p.d.arc([x - 1, yb - 17, x + 11, yb - 3], 200, 340, fill=K, width=1)
    p.box(x, yb - 10, x + 10, yb, G)
    p.rect(x + 1, yb - 9, x + 9, yb - 7, col)
    p.rect(x + 1, yb - 6, x + 1, yb - 1, W)
    p.rect(x + 9, yb - 6, x + 9, yb - 1, g)
    p.rect(x + 2, yb - 6, x + 3, yb - 3, col)


# ================================================================================================
# 版面部件
# ================================================================================================
def series_window(p: Pix, ep: int, x0=SAFE_L, y0=3):
    """左上角楼层牌：B3 方月亮神殿（地牢的这一层叫什么，名字与宣传海报一致）。
    2026-10-25 起取代原来的“证明的极限 / STAGE NN”存档栏：封面负责好玩好认，标题负责被检索。"""
    name = TEXT[ep]["floor"]
    tag = f"B{ep}"
    gw = Pix.glyphs_w(tag, 2)
    if TEXT[ep].get("stack"):          # 右上角另有东西（第 1 集的魔王血条）：层号、层名上下两行，牌子窄一些
        size = 16
        nw = Pix.cjk_w(name, size)
        w, h = max(gw, nw) + 16, 41
        p.window(x0, y0 - 1, x0 + w, y0 - 1 + h)
        p.glyphs(tag, x0 + 8, y0 + 4, O, k=2, shadow=K)
        p.cjk(name, x0 + 8, y0 + 19, size, Y, shadow=K)
        return x0 + w
    size = 20 if len(name) <= 4 else 18
    nw = Pix.cjk_w(name, size)
    w, h = 8 + gw + 8 + nw + 9, 30
    p.window(x0, y0, x0 + w, y0 + h)
    p.glyphs(tag, x0 + 8, y0 + (h - 14) // 2 + 1, O, k=2, shadow=K)
    p.cjk(name, x0 + 8 + gw + 8, y0 + (h - size) // 2 - 1, size, Y, shadow=K)
    return x0 + w


def title_lines(ep):
    return TEXT[ep]["title"].split("|")


def dialog(p: Pix, lines, colors=None, y1=150, x1=SAFE_R, cursor=False):
    """对话框：两行 21px；三行 20px。返回 (y0, 文字右端)。"""
    size = 21 if len(lines) <= 2 else 20
    pitch = size + 1
    y0 = y1 - (len(lines) * pitch + 6) - 2
    p.window(SAFE_L, y0, x1, y1)
    yy = y0 + 6
    right = 0
    for i, s in enumerate(lines):
        col = colors[i] if colors else W
        right = max(right, SAFE_L + 10 + p.cjk(s, SAFE_L + 10, yy, size, col, shadow=K))
        yy += pitch
    if cursor:
        tx, ty = x1 - 14, y1 - 10
        p.d.polygon([(tx, ty), (tx + 6, ty), (tx + 3, ty + 3)], fill=Y)
    return y0, right


def boss_plate(p: Pix, name_cjk=None, name_px=None, hp="∞", x1=SAFE_R, y0=3):
    if name_cjk:
        nw = Pix.cjk_w(name_cjk, 14)
        x0 = x1 - (nw + 16)
        p.window(x0, y0, x1, y0 + 34)
        p.cjk(name_cjk, x0 + 8, y0 + 6, 14, W, shadow=K)
        p.glyphs("HP", x0 + 8, y0 + 23, O, k=1)
        p.hp_bar(x0 + 21, y0 + 23, nw - 22, 1.0, col=R, dark=V, h=5)
        p.glyphs(hp, x1 - 16, y0 + 23, Y, k=1)
    else:
        x0 = x1 - 96
        p.window(x0, y0 + 1, x1, y0 + 24)
        p.glyphs(name_px, x0 + 8, y0 + 4, M, k=2, shadow=K)
        p.glyphs("HP", x0 + 24, y0 + 5, O, k=1)
        p.hp_bar(x0 + 24, y0 + 14, 36, 1.0, col=R, dark=V, h=3)
        p.glyphs(hp, x0 + 64, y0 + 5, Y, k=2, shadow=K)


# ================================================================================================
# 各集场景
# ================================================================================================
def ep01():
    t = TEXT[1]
    p = Pix()
    GROUND = 98
    p.vgrad(0, GROUND, [K, N, V])
    p.stars(2, 84, 70, 10, seed=7, avoid=[(36, 0, 150, 46)])
    p.ridge(GROUND, 6, 16, N, seed=3)
    p.vgrad(GROUND, LH - 1, [n, N, K])
    vx, vy = 160, GROUND - 40
    for xb in range(-400, LW + 400, 26):
        p.d.line([(vx + (xb - vx) * (GROUND - vy) / (LH - vy), GROUND), (xb, LH)], fill=V)
    yy, step = GROUND + 2, 2
    while yy < LH:
        p.d.line([(0, yy), (LW, yy)], fill=V)
        step += 2
        yy += step
    p.rect(0, GROUND, LW, GROUND, v)

    gx = 208
    golem(p, gx, GROUND + 10)
    floating_blocks(p, [(146, 50, 10), (156, 40, 7), (278, 52, 10), (292, 42, 7), (300, 66, 9), (138, 66, 6)])

    rx = 70
    tape = [(rx + 10, GROUND - 12), (rx + 2, GROUND - 26), (rx - 8, GROUND - 30), (rx - 16, GROUND - 24),
            (rx - 20, GROUND - 14)]
    p.d.line(tape, fill=K, width=6, joint="curve")
    p.d.line(tape, fill=W, width=4, joint="curve")
    for (x_, y_) in tape[1:4]:
        p.rect(x_ - 1, y_, x_ + 1, y_, g)
    for i in range(5):
        y0 = GROUND - i * 4
        x0 = rx - 30 + (i % 2) * 3
        p.box(x0, y0 - 4, x0 + 20, y0, W)
        for k_ in range(3):
            p.rect(x0 + 3 + k_ * 6, y0 - 2, x0 + 5 + k_ * 6, y0 - 2, g)
    robot(p, rx, GROUND, face="right", eyes="sq")
    p.glyphs("HP", rx - 4, GROUND - 52, E, k=1, shadow=K)
    p.hp_bar(rx + 8, GROUND - 52, 22, 0.3, col=E, dark=e)

    series_window(p, 1)
    boss_plate(p, name_cjk=t["boss"], hp="∞")

    dialog(p, title_lines(1))
    cw = Pix.cjk_w(t["yes"], 16)
    cx1 = SAFE_R - 3
    cx0 = cx1 - cw - 13
    cy0 = 103
    p.window(cx0, cy0, cx1, 147, fill=K)
    p.cjk(t["yes"], cx0 + 7, cy0 + 9, 16, Y, shadow=K)
    p.cjk(t["no"], cx0 + 7 + cw - Pix.cjk_w(t["yes"][1:], 16), cy0 + 26, 16, G, shadow=K)
    return p


def ep02():
    p = Pix()
    FLOOR = 88
    TILE, TILE2 = (46, 112, 118), (36, 92, 100)
    # 墙砖
    for y in range(0, FLOOR):
        for x in range(LW):
            c = TILE if ((x // 10) + (y // 10)) % 2 == 0 else TILE2
            if x % 10 == 0 or y % 10 == 0:
                c = (28, 70, 80)
            p.im.putpixel((x, y), c)
    # 护墙板
    p.rect(0, FLOOR - 18, LW, FLOOR - 1, WOOD)
    p.rect(0, FLOOR - 18, LW, FLOOR - 17, (210, 150, 90))
    for x in range(0, LW, 16):
        p.rect(x, FLOOR - 16, x, FLOOR - 1, WOOD_D)
    # 黑白格地板
    for y in range(FLOOR, LH):
        for x in range(LW):
            p.im.putpixel((x, y), (214, 208, 190) if ((x // 10) + ((y - FLOOR) // 10)) % 2 == 0 else (64, 60, 84))
    p.rect(0, FLOOR, LW, FLOOR, K)

    # 墙上的小黑板：谁给谁刮胡子（对角线高亮）
    bx0, by0, cells, cs = 190, 6, 6, 12
    bw = cells * cs
    p.box(bx0 - 6, by0, bx0 + bw + 6, by0 + bw + 12, WOOD_D)
    p.rect(bx0 - 5, by0 + 1, bx0 + bw + 5, by0 + 1, WOOD)
    p.box(bx0 - 3, by0 + 3, bx0 + bw + 3, by0 + bw + 9, (34, 66, 52))
    rnd = random.Random(12)
    gy0 = by0 + 6
    for i in range(cells):
        for j in range(cells):
            x = bx0 + j * cs
            y = gy0 + i * cs
            p.rect(x, y, x + cs, y, (90, 130, 110))
            p.rect(x, y, x, y + cs, (90, 130, 110))
            yes = rnd.random() < 0.5
            if i == j:
                p.box(x + 1, y + 1, x + cs - 1, y + cs - 1, (34, 66, 52), Y)
            if yes:
                check_icon(p, x + 3, y + 3, (150, 240, 170))
            else:
                cross_icon(p, x + 4, y + 4, (255, 150, 160))
    p.rect(bx0, gy0 + bw, bx0 + bw, gy0 + bw, (90, 130, 110))
    p.rect(bx0 + bw, gy0, bx0 + bw, gy0 + bw, (90, 130, 110))
    # 粉笔托
    p.rect(bx0 - 6, by0 + bw + 12, bx0 + bw + 6, by0 + bw + 13, WOOD_D)
    p.rect(bx0 + 8, by0 + bw + 10, bx0 + 14, by0 + bw + 11, W)

    # 理发店转灯
    barber_pole(p, SAFE_L + 2, 50, FLOOR - 4)
    # 镜子（里面是理发师的镜像）
    mx0, my0, mx1, my1 = 112, 42, 150, 86
    p.box(mx0, my0, mx1, my1, Y)
    p.rect(mx0 + 1, my0 + 1, mx1 - 1, my0 + 1, W)
    p.box(mx0 + 3, my0 + 3, mx1 - 3, my1 - 3, (150, 210, 230))
    sub = Pix(bg=(1, 2, 3), size=(40, 52))
    barber(sub, 2, 50)
    sub.im = sub.im.crop((0, 0, 40, (my1 - 4) - (my0 + 6)))
    p.stamp(sub, mx0 + 1, my0 + 6, flip=True)
    # 镜面反光（盖在镜像上）
    for i in range(10):
        p.px(mx0 + 6 + i, my0 + 18 - i, (220, 240, 250))
        p.px(mx0 + 8 + i, my0 + 22 - i, (220, 240, 250))
    p.box(mx0, my0, mx1, my0 + 3, Y)
    p.box(mx0, my1 - 3, mx1, my1, Y)
    p.rect(mx0, my0 + 3, mx0 + 2, my1 - 3, Y)
    p.rect(mx1 - 2, my0 + 3, mx1, my1 - 3, Y)
    p.rect(mx0, my0, mx0, my1, K)
    p.rect(mx1, my0, mx1, my1, K)
    p.rect(mx0, my0, mx1, my0, K)
    p.rect(mx0, my1, mx1, my1, K)
    # 理发师本人
    barber(p, 66, FLOOR + 10)
    sweat(p, 96, 52)
    # 头顶冒问号
    p.glyphs("?", 58, 46, R, k=2, outline=K)

    series_window(p, 2)
    dialog(p, title_lines(2))
    return p


def ep03():
    t = TEXT[3]
    p = Pix()
    GROUND = 99
    p.vgrad(0, GROUND, [K, N, (30, 50, 130)])
    p.stars(2, 80, 80, 10, seed=21, avoid=[(36, 0, 150, 46), (180, 0, 260, 70)])
    square_moon(p, 204, 12, 46)
    p.ridge(GROUND, 10, 20, (24, 70, 70), seed=8)
    p.ridge(GROUND, 3, 9, (20, 50, 50), seed=9, step=(-1, 0, 1))
    p.vgrad(GROUND, LH - 1, [(20, 50, 50), K])
    # 路牌 2+2=5
    sign = t["sign"]
    sw = Pix.glyphs_w(sign, 2)
    sx0 = 128
    p.box(sx0 + sw // 2 - 1, 66, sx0 + sw // 2 + 4, GROUND, WOOD_D)
    p.box(sx0 - 6, 50, sx0 + sw + 6, 70, WOOD)
    p.rect(sx0 - 5, 51, sx0 + sw + 5, 51, (220, 160, 100))
    p.rect(sx0 - 5, 69, sx0 + sw + 5, 69, WOOD_D)
    p.px(sx0 - 3, 53, WOOD_D)
    p.px(sx0 + sw + 3, 67, WOOD_D)
    p.glyphs(sign, sx0, 54, K, k=2)
    # 机器人抬头看月亮，气泡里一个大大的 ✓
    rx = 64
    robot(p, rx, GROUND, face="right", eyes="happy", mouth="smile")
    p.bubble(88, 44, 112, 62, (86, 66))
    check_icon(p, 93, 47, E, k=2)
    # 草丛
    for gx in (52, 100, 170, 236, 262):
        for i in range(0, 7, 2):
            p.rect(gx + i, GROUND - 3 - (i % 3), gx + i, GROUND, (60, 150, 90))
    series_window(p, 3)
    dialog(p, title_lines(3))
    return p


def ep04():
    t = TEXT[4]
    p = Pix()
    GROUND = 99
    p.vgrad(0, GROUND, [(70, 140, 220), (130, 196, 240), (190, 226, 246)])
    for (cx_, cy_, w_) in ((170, 14, 26), (292, 30, 22), (110, 60, 18)):
        for dx, dy, r_ in ((0, 0, 6), (w_ // 3, -3, 7), (2 * w_ // 3, 0, 6)):
            p.d.ellipse([cx_ + dx - r_, cy_ + dy - r_ + 2, cx_ + dx + r_, cy_ + dy + r_], fill=W)
    p.ridge(GROUND, 8, 16, (90, 170, 100), seed=4)
    p.vgrad(GROUND - 8, LH - 1, [(110, 190, 90), (70, 150, 70), (40, 100, 60)])
    for x in range(0, LW, 7):
        p.rect(x, GROUND - 9, x + 1, GROUND - 9, (140, 210, 110))
    # 跑者 + 飞散的笔记页
    runner(p, 46, GROUND)
    p.box(70, GROUND - 30, 84, GROUND - 18, W)          # 手里的本子
    p.rect(77, GROUND - 30, 77, GROUND - 18, G)
    for i in range(3):
        p.rect(71, GROUND - 27 + i * 3, 75, GROUND - 27 + i * 3, g)
        p.rect(79, GROUND - 27 + i * 3, 83, GROUND - 27 + i * 3, g)
    for (px_, py_, letter) in zip((88, 104, 122, 140), (64, 50, 60, 46), t["pages"]):
        page(p, px_, py_, letter)
    p.glyphs("...", 158, 60, W, k=1, shadow=K)
    # 乌龟举牌：A✓ B✓ Z?
    tx = 204
    card_rows = t["card"]
    cw_ = max(Pix.glyphs_w(r_, 2) for r_ in card_rows) + 10
    ch_ = len(card_rows) * 16 + 6
    cx0 = tx + 8
    cy0 = 6
    p.box(cx0 + cw_ // 2 - 1, cy0 + ch_, cx0 + cw_ // 2 + 2, GROUND - 2, WOOD_D)
    p.box(cx0, cy0, cx0 + cw_, cy0 + ch_, W)
    p.rect(cx0 + 1, cy0 + ch_ - 1, cx0 + cw_ - 1, cy0 + ch_ - 1, G)
    for i, row in enumerate(card_rows):
        yy = cy0 + 4 + i * 16
        xx = cx0 + 6
        for ch in row:
            col = K
            if ch == "✓":
                col = (30, 150, 80)
            elif ch == "?":
                col = R
            p.glyphs(ch, xx, yy, col, k=2)
            xx += (len(F5[ch][0]) + 1) * 2
    tortoise(p, tx, GROUND)
    series_window(p, 4)
    dialog(p, title_lines(4))
    return p


def _brick_map(seed=5, rows=80, cols=120):
    """砖块式“地图”，逐块贪心四染色（每块着色时最多 3 个已着色邻居，所以 4 色总够用，相邻国家颜色必不同）。"""
    rnd = random.Random(seed)
    col = {}
    for j in range(rows):
        for i in range(-cols // 2, cols // 2):
            used = set()
            used.add(col.get((i - 1, j)))
            # 上一行与本块重叠的两块
            if j > 0:
                if j % 2 == 1:   # 本行右移半格
                    used.update({col.get((i, j - 1)), col.get((i + 1, j - 1))})
                else:
                    used.update({col.get((i - 1, j - 1)), col.get((i, j - 1))})
            choices = [c for c in range(4) if c not in used]
            col[(i, j)] = rnd.choice(choices)
    return col


def ep05():
    p = Pix()
    HOR = 44
    p.vgrad(0, HOR, [(80, 150, 225), (150, 205, 240), (205, 232, 246)])
    for (cx_, cy_) in ((176, 12), (250, 26), (300, 10)):
        for dx, dy, r_ in ((0, 0, 5), (7, -3, 6), (14, 0, 5)):
            p.d.ellipse([cx_ + dx - r_, cy_ + dy - r_ + 2, cx_ + dx + r_, cy_ + dy + r_], fill=W)
    cmap = _brick_map()
    COLS = [(236, 96, 100), (252, 208, 92), (104, 200, 120), (96, 150, 232)]
    FOG = (205, 232, 246)
    import math

    def region(xx, yy):
        dy = yy - HOR
        vdist = 70 / dy
        u = (xx - 160) * vdist / 34
        u += 0.12 * math.sin(vdist * 9.0 + u * 1.3)
        vv = vdist * 2.2 + 0.10 * math.sin(u * 7.0)
        j = int(math.floor(vv))
        uu = u - (0.5 if j % 2 else 0)
        i = int(math.floor(uu))
        return (i, j), vdist

    ids = {}
    for y in range(HOR + 1, LH):
        for x in range(LW):
            ids[(x, y)] = region(x, y)
    for y in range(HOR + 1, LH):
        for x in range(LW):
            rid, vdist = ids[(x, y)]
            c = COLS[cmap.get(rid, 0)]
            # 国界
            if x + 1 < LW and ids[(x + 1, y)][0] != rid or y + 1 < LH and ids[(x, y + 1)][0] != rid:
                c = (60, 50, 80)
            # 远处起雾
            fog = max(0.0, min(1.0, (vdist - 2.0) / 6.0))
            if BAYER[y % 4][x % 4] < fog * 16:
                c = FOG
            p.im.putpixel((x, y), c)
    p.rect(0, HOR, LW, HOR, FOG)
    # 小机器人画家 + 4 桶颜料
    rx = 64
    GROUND = 98
    p.dither_fill(p.ellipse_mask(rx + 11, GROUND, 16, 3), (40, 30, 60), 0.5)
    robot(p, rx, GROUND, face="right", eyes="worry", mouth="wavy")
    sweat(p, rx + 24, GROUND - 34)
    sweat(p, rx - 5, GROUND - 30)
    # 刷子
    p.d.line([(rx + 21, GROUND - 11), (rx + 30, GROUND - 22)], fill=K, width=3)
    p.d.line([(rx + 21, GROUND - 11), (rx + 30, GROUND - 22)], fill=WOOD, width=1)
    p.box(rx + 28, GROUND - 27, rx + 33, GROUND - 21, R)
    for i, cc in enumerate(COLS):
        paint_bucket(p, 98 + i * 14, GROUND, cc)
    series_window(p, 5)
    dialog(p, title_lines(5))
    return p


def ep06():
    p = Pix()
    p.vgrad(0, LH - 1, [K, (70, 24, 82), (150, 52, 120), (210, 96, 150)])
    rnd = random.Random(6)
    for _ in range(16):
        heart(p, rnd.randrange(0, LW), rnd.randrange(0, 150), (230, 120, 170), small=True)
    lines = title_lines(6)
    dy0, right = dialog(p, lines)
    # 两个小窗：∀∃（每人各爱一个“别人”） vs ∃∀（大家都爱同一个）
    COLS = [(120, 210, 250), (130, 230, 140), (255, 200, 90), (250, 150, 110)]
    wy0, wy1 = 3, dy0 - 4
    import math
    for k_, (wx0, wx1, tag) in enumerate(((152, 214, "AE"), (218, 280, "EA"))):
        p.window(wx0, wy0, wx1, wy1, fill=(40, 26, 70))
        cx = (wx0 + wx1) // 2
        cy = (wy0 + 16 + wy1) // 2 + 2
        tw = 2 * 11 + 2
        p.sym(tag[0], cx - tw // 2, wy0 + 7, Y, k=2)
        p.sym(tag[1], cx - tw // 2 + 12, wy0 + 7, Y, k=2)
        rr = 18
        pts = []
        for i in range(4):
            a = -math.pi / 2 + i * math.pi / 2
            pts.append((cx + round(rr * math.cos(a)), cy + round(rr * math.sin(a))))
        if k_ == 0:
            for i in range(4):
                (x1_, y1_), (x2_, y2_) = pts[i], pts[(i + 1) % 4]
                mx_, my_ = (x1_ + x2_) // 2, (y1_ + y2_) // 2
                mx_ += (mx_ - cx) // 3
                my_ += (my_ - cy) // 3
                heart(p, mx_ - 2, my_ - 2, R, small=True)
            for i, (bx_, by_) in enumerate(pts):
                blob(p, bx_, by_, COLS[i], r=6, eyes="heart")
        else:
            for i, (bx_, by_) in enumerate(pts):
                mx_, my_ = cx + round((bx_ - cx) * 0.52), cy + round((by_ - cy) * 0.52)
                heart(p, mx_ - 2, my_ - 2, R, small=True)
            for i, (bx_, by_) in enumerate(pts):
                blob(p, bx_, by_, COLS[i], r=6, eyes="heart")
            blob(p, cx, cy + 1, (230, 120, 200), r=5, crowned=True, eyes="smug")
    # ≠ 徽章
    bx, by = 216, (wy0 + wy1) // 2 + 6
    p.d.ellipse([bx - 10, by - 10, bx + 10, by + 10], fill=K)
    p.d.ellipse([bx - 9, by - 9, bx + 9, by + 9], fill=W)
    p.bitmap(["...X.", "XXXXX", "..X..", "XXXXX", ".X..."], bx - 5, by - 5, R, k=2)
    # 窗口下方空地：两只团子在递爱心
    series_window(p, 6)
    blob(p, 66, wy1 - 8, COLS[0], r=7, eyes="heart", look=(1, 0))
    heart(p, 84, wy1 - 14, R)
    blob(p, 104, wy1 - 8, COLS[2], r=7, eyes="o", look=(1, 0))
    heart(p, 122, wy1 - 16, R)
    blob(p, 140, wy1 - 8, COLS[3], r=7, eyes="smug")
    # 对话框右侧头像：被所有人爱着的那位（得意）
    px0, px1 = SAFE_R - 52, SAFE_R - 6
    py0, py1 = dy0 + 6, 144
    p.box(px0, py0, px1, py1, (60, 30, 80))
    p.rect(px0 + 1, py0 + 1, px1 - 1, py0 + (py1 - py0) // 2, (80, 40, 100))
    pcx, pcy = (px0 + px1) // 2, py1 - 18
    p.d.ellipse([pcx - 17, pcy - 14, pcx + 17, pcy + 16], fill=K)
    p.d.ellipse([pcx - 16, pcy - 13, pcx + 16, pcy + 15], fill=(230, 120, 200))
    p.rect(pcx - 11, pcy + 13, pcx + 11, pcy + 14, (170, 70, 150))
    p.rect(pcx - 12, pcy - 9, pcx - 9, pcy - 7, (255, 190, 240))
    for ex in (pcx - 9, pcx + 4):
        p.rect(ex, pcy - 2, ex + 5, pcy - 1, K)
        p.rect(ex + 1, pcy, ex + 4, pcy + 1, K)
    p.rect(pcx - 3, pcy + 6, pcx + 3, pcy + 6, K)
    p.px(pcx + 4, pcy + 5, K)
    crown(p, pcx - 11, pcy - 12, 22, 12, gem=C)
    for (hx, hy) in ((px0 + 3, py0 + 4), (px1 - 11, py0 + 6), (px0 + 4, py0 + 22), (px1 - 10, py0 + 26)):
        heart(p, hx, hy, R, small=True)
    _ = right
    return p


def ep07():
    t = TEXT[7]
    p = Pix()
    lines = title_lines(7)
    FLOOR = 78
    # 地牢石墙
    STONE, STONE_D, MORTAR = (44, 70, 84), (34, 54, 68), (22, 34, 48)
    for y in range(0, FLOOR):
        for x in range(LW):
            row = y // 8
            off = 8 if row % 2 else 0
            c = STONE if ((x + off) // 16 + row) % 3 else STONE_D
            if y % 8 == 0 or (x + off) % 16 == 0:
                c = MORTAR
            p.im.putpixel((x, y), c)
    p.vgrad(FLOOR, LH - 1, [(40, 44, 60), (24, 26, 40), K])
    for x in range(0, LW, 20):
        p.d.line([(x, FLOOR), (x + (x - 160) // 2, LH)], fill=(30, 32, 48))
    torch(p, 60, 52)
    torch(p, 132, 52)
    # 两个宝箱：左“完备”打开发光，右“不完备”上锁
    ax0, bx0 = 154, 226
    yb = FLOOR + 1
    p.dither_fill(p.ellipse_mask(ax0 + 22, yb - 26, 30, 26), Y, 0.25)
    chest(p, ax0, yb, w=44, h=26, open_=True)
    # 从箱子里冒出 ⊢ ⊨ 符号
    for (sx, sy, key, col) in ((ax0 + 8, yb - 44, "|", Y), (ax0 + 26, yb - 52, "M", W), (ax0 + 17, yb - 62, "|", W),
                               (ax0 + 33, yb - 38, "M", Y)):
        p.sym(key, sx + 1, sy + 1, K, k=2)
        p.sym(key, sx, sy, col, k=2)
    chest(p, bx0, yb, w=44, h=26, locked=True)
    # 箱子上方的木牌
    for (x0, label) in ((ax0, t["chestA"]), (bx0, t["chestB"])):
        lw = Pix.cjk_w(label, 14)
        lx0 = x0 + 22 - (lw + 12) // 2
        ly0 = 4 if x0 == bx0 else 4
        p.box(lx0, ly0, lx0 + lw + 12, ly0 + 22, WOOD)
        p.rect(lx0 + 1, ly0 + 1, lx0 + lw + 11, ly0 + 1, (220, 160, 100))
        p.cjk(label, lx0 + 6, ly0 + 5, 14, W, shadow=K)
    series_window(p, 7)
    # 对话框 + 右侧头像：一脸问号的机器人
    dy0, right = dialog(p, lines)
    px0, px1 = SAFE_R - 50, SAFE_R - 6
    py0, py1 = dy0 + 6, 144
    robot_portrait(p, px0, py0, px1, py1)
    p.glyphs("?!", px1 - 22, py0 + 3, Y, k=2, outline=K)
    return p


def ep08():
    t = TEXT[8]
    p = Pix()
    GROUND = 99
    p.vgrad(0, GROUND, [K, N, V, M])
    p.stars(2, 60, 60, 9, seed=11, avoid=[(36, 0, 150, 46)])
    p.ridge(GROUND, 2, 18, V, seed=5)
    p.ridge(GROUND, 0, 9, N, seed=6, step=(-1, 0, 1))
    p.vgrad(GROUND, LH - 1, [N, K])

    rx = SAFE_L + 1
    robot(p, rx, GROUND, face="right", eyes="sq")
    bx, by = rx + 25, GROUND - 56
    p.box(bx, by, bx + 10, by + 15, W)
    p.rect(bx + 4, by + 3, bx + 6, by + 9, R)
    p.rect(bx + 4, by + 11, bx + 6, by + 12, R)
    p.d.polygon([(bx, by + 13), (bx - 4, by + 18), (bx + 4, by + 15)], fill=K)
    p.d.polygon([(bx + 1, by + 14), (bx - 2, by + 16), (bx + 3, by + 14)], fill=W)

    BS = 16
    y0 = GROUND - BS
    xs = [rx + 27 + i * (BS + 2) for i in range(5)]
    for i, x in enumerate(xs):
        num_block(p, x, y0, BS, str(i))
    xx = xs[-1] + BS + 4
    for sz in (8, 6, 4, 3, 2):
        p.box(xx, GROUND - sz, xx + sz, GROUND, O)
        xx += sz + 3

    PB, PH = 21, 13
    py0 = 80
    px0 = 212
    cbx = px0 + PB + 2 + PB // 2 - 24 + 1
    c_boss(p, cbx, py0 - 2, cell=4, body=False)
    p.dither_fill(p.ellipse_mask(px0 + 36, py0 + 17, 44, 4), K, 0.5)
    for i, lab in enumerate(("c-1", "c", "c+1")):
        x = px0 + i * (PB + 2)
        p.box(x, py0, x + PB, py0 + PH, v)
        p.rect(x + 1, py0 + 1, x + PB - 1, py0 + 1, LILAC)
        p.rect(x + 1, py0 + PH - 1, x + PB - 1, py0 + PH - 1, V)
        tw = Pix.glyphs_w(lab, 1)
        p.glyphs(lab, x + (PB - tw) // 2 + 1, py0 + 4, K, k=1)
    for xd in (px0 - 10, px0 - 6, px0 + 3 * (PB + 2) + 2, px0 + 3 * (PB + 2) + 6):
        p.rect(xd, py0 + 6, xd + 1, py0 + 7, LILAC)
    c_boss(p, cbx, py0 - 3, cell=4, aura=False)

    boss_plate(p, name_px=t["boss"], hp=t["hp"])
    series_window(p, 8)
    lines = title_lines(8)
    dialog(p, lines, colors=[W] + [(255, 140, 230)] * (len(lines) - 1), cursor=True)
    return p


def ep09():
    t = TEXT[9]
    p = Pix()
    GROUND = 99
    p.vgrad(0, GROUND, [K, (20, 36, 54), (30, 60, 76)])
    # 聚光灯
    m = p.mask()
    ImageDraw.Draw(m).polygon([(206, 0), (232, 0), (290, GROUND), (150, GROUND)], fill=255)
    p.dither_fill(m, (60, 96, 110), 0.25)
    p.vgrad(GROUND, LH - 1, [(26, 44, 60), K])
    # 透视棋盘（EF 游戏）
    bl, br, tl, tr = 150, 290, 178, 262
    top, bot = 50, GROUND
    rows, cols = 5, 6
    LIGHT, DARK = (226, 222, 200), (64, 74, 100)

    def edge(yy):
        f = (yy - top) / (bot - top)
        return tl + (bl - tl) * f, tr + (br - tr) * f

    def row_of(yy):
        f = (yy - top) / (bot - top)
        # 近大远小：用 1/z 插值
        z0, z1 = 1.0, 2.2
        inv = 1 / z1 + (1 / z0 - 1 / z1) * f
        z = 1 / inv
        return int((z1 - z) / (z1 - z0) * rows * 0.999)

    for yy in range(top, bot + 1):
        xl, xr = edge(yy)
        r_ = row_of(yy)
        for xx in range(int(xl), int(xr) + 1):
            c_ = int((xx - xl) / max(1, (xr - xl)) * cols * 0.999)
            p.im.putpixel((xx, yy), LIGHT if (r_ + c_) % 2 == 0 else DARK)
    p.d.polygon([(tl, top), (tr, top), (br, bot), (bl, bot)], outline=K)
    p.rect(bl, bot, br, bot + 3, (40, 36, 30))
    # 两枚棋子：红 = Spoiler，蓝 = Duplicator
    pawn(p, 196, 78, R)
    pawn(p, 250, 90, (80, 150, 240))
    # 机器人：嘴被胶带封住，憋得冒汗
    rx = 50
    robot(p, rx, GROUND, face="right", eyes="squeeze", mouth="tape")
    sweat(p, rx + 24, GROUND - 36)
    sweat(p, rx - 5, GROUND - 31)
    sweat(p, rx + 25, GROUND - 27)
    # 气泡：有…有…
    txt = t["bubble"]
    tw = Pix.cjk_w(txt, 14)
    bx0, by0 = 76, 46
    p.bubble(bx0, by0, bx0 + tw + 12, by0 + 22, (rx + 18, GROUND - 40))
    p.cjk(txt, bx0 + 6, by0 + 5, 14, K)
    series_window(p, 9)
    dialog(p, title_lines(9))
    return p


def ep10():
    t = TEXT[10]
    p = Pix()
    GROUND = 99
    p.vgrad(0, GROUND, [K, (54, 18, 50), (110, 30, 62)])
    import math
    # “获得道具”放射光
    gcx, gcy = 171, 40
    m = p.mask()
    md = ImageDraw.Draw(m)
    for i in range(12):
        a0 = i / 12 * 2 * math.pi
        a1 = a0 + 0.13
        md.polygon([(gcx, gcy), (gcx + 400 * math.cos(a0), gcy + 400 * math.sin(a0)),
                    (gcx + 400 * math.cos(a1), gcy + 400 * math.sin(a1))], fill=255)
    p.dither_fill(m, (170, 60, 70), 0.25)
    p.ridge(GROUND, 3, 10, (60, 20, 40), seed=10)
    p.vgrad(GROUND, LH - 1, [(60, 22, 44), K])
    # 转圈圈魔王
    spinner_boss(p, 248, 52, r=26, dot=5)
    # 打开的宝箱（道具从这里来）
    chest(p, 108, GROUND, w=30, h=20, open_=True)
    # 机器人高举死循环检测器
    rx = 160
    robot(p, rx, GROUND, face="front", eyes="happy", mouth="o", arms="up")
    gadget(p, rx - 5, 33, w=32, h=24, phase=1)
    iw = Pix.glyphs_w(t["item"], 2)
    p.glyphs(t["item"], rx + 11 - iw // 2, 7, Y, k=2, outline=K)
    for (sx, sy) in ((rx - 16, 26), (rx + 38, 36), (rx - 12, 54), (rx + 36, 14)):
        p.twinkle(sx, sy, Y, big=True)
    series_window(p, 10)
    dialog(p, title_lines(10))
    return p


def season():
    t = TEXT[0]
    p = Pix()
    GROUND = 132
    p.vgrad(0, GROUND, [K, N, V, (150, 60, 130)])
    p.stars(2, 100, 90, 14, seed=42)
    square_moon(p, 262, 10, 30)
    p.ridge(GROUND, 6, 16, V, seed=13)
    p.ridge(GROUND, 2, 8, N, seed=14, step=(-1, 0, 1))
    p.vgrad(GROUND, LH - 1, [n, N, K])
    for x in range(0, LW, 16):
        p.rect(x, GROUND + 1, x + 7, GROUND + 1, v)
    # 大标题 logo：三段色 + 立体厚度
    size = 32
    m = Pix.cjk_mask(t["title"], size)
    lw, lh = m.width - 4, m.height - 4
    lx = (LW - lw) // 2
    ly = 12
    ox, oy = lx - 2, ly - 3
    om = m.filter(ImageFilter.MaxFilter(3))
    for d_ in range(4, 0, -1):
        p.im.paste(K, (ox + d_, oy + d_ + 1), om)
        p.im.paste((150, 50, 60) if d_ > 1 else R, (ox + d_, oy + d_), m)
    p.im.paste(K, (ox, oy), om)
    ink = m.getbbox()
    band = Image.new("L", m.size, 0)
    bd = ImageDraw.Draw(band)
    h_ = ink[3] - ink[1]
    p.im.paste(O, (ox, oy), m)
    bd.rectangle([0, 0, m.width, ink[1] + int(h_ * 0.62)], fill=255)
    p.im.paste(Y, (ox, oy), ImageChops.multiply(m, band))
    band = Image.new("L", m.size, 0)
    ImageDraw.Draw(band).rectangle([0, 0, m.width, ink[1] + int(h_ * 0.22)], fill=255)
    p.im.paste(W, (ox, oy), ImageChops.multiply(m, band))
    # 副标题横幅
    sub = t["sub"]
    sw = Pix.cjk_w(sub, 16)
    sx0 = (LW - sw) // 2 - 10
    p.window(sx0, ly + lh + 10, sx0 + sw + 20, ly + lh + 36)
    p.cjk(sub, sx0 + 10, ly + lh + 17, 16, W, shadow=K)
    # PRESS START
    pw = Pix.glyphs_w(t["press"], 1)
    p.glyphs(t["press"], (LW - pw) // 2, ly + lh + 44, Y, k=1, shadow=K)
    p.d.polygon([((LW - pw) // 2 - 8, ly + lh + 44), ((LW - pw) // 2 - 8, ly + lh + 50), ((LW - pw) // 2 - 5, ly + lh + 47)], fill=Y)
    # 全季角色站成一排
    floor = GROUND + 4
    runner(p, 52, floor)
    barber(p, 80, floor)
    robot(p, 118, floor, face="front", eyes="happy", mouth="smile")
    sub_g = Pix(bg=(1, 2, 3), size=(70, 60))
    tortoise(sub_g, 10, 58)
    p.stamp(sub_g, 140, floor - 58)
    c_boss(p, 204, floor - 3, cell=3, aura=False, sparkle=False)
    blob(p, 256, floor - 7, (120, 210, 250), r=7, eyes="heart")
    blob(p, 272, floor - 7, (255, 200, 90), r=7, crowned=True, eyes="smug")
    heart(p, 262, floor - 26, R)
    chest(p, 284, floor, w=22, h=16, locked=False)
    return p


# ---------------------------------------------------------------------------------- 第 11–15 集
def robot_back(p: Pix, x, yf):
    """机器人的背影（镜子里看到的）：没有脸，只有后盖和螺丝。"""
    p.rect(x + 10, yf - 37, x + 11, yf - 33, K)
    p.box(x + 8, yf - 41, x + 13, yf - 36, Y)
    p.box(x + 1, yf - 33, x + 20, yf - 17, G)
    p.rect(x + 2, yf - 32, x + 19, yf - 32, W)
    p.rect(x + 2, yf - 18, x + 19, yf - 18, g)
    p.box(x - 1, yf - 28, x + 1, yf - 23, g)
    p.box(x + 20, yf - 28, x + 22, yf - 23, g)
    for yy in (yf - 29, yf - 26, yf - 23):          # 散热格栅
        p.rect(x + 6, yy, x + 15, yy, g)
    p.rect(x + 8, yf - 17, x + 13, yf - 15, K)
    p.box(x + 3, yf - 16, x + 18, yf - 6, B)
    p.box(x + 6, yf - 14, x + 15, yf - 8, (40, 80, 180))
    for (sx, sy) in ((x + 7, yf - 13), (x + 14, yf - 13), (x + 7, yf - 9), (x + 14, yf - 9)):
        p.px(sx, sy, G)
    p.box(x, yf - 15, x + 3, yf - 8, g)
    p.box(x + 18, yf - 15, x + 21, yf - 8, g)
    p.box(x + 5, yf - 6, x + 9, yf - 2, g)
    p.box(x + 12, yf - 6, x + 16, yf - 2, g)
    p.box(x + 3, yf - 3, x + 9, yf, K)
    p.box(x + 12, yf - 3, x + 18, yf, K)


def ghost(p: Pix, x, y, col=(220, 210, 250)):
    """误解小怪：一张会飘的床单。"""
    p.d.pieslice([x - 1, y - 1, x + 15, y + 15], 180, 360, fill=K)
    p.rect(x - 1, y + 7, x + 15, y + 16, K)
    p.d.pieslice([x, y, x + 14, y + 14], 180, 360, fill=col)
    p.rect(x, y + 7, x + 14, y + 14, col)
    for i in range(0, 15, 5):
        p.d.polygon([(x + i, y + 15), (x + i + 2, y + 13), (x + i + 4, y + 15)], fill=K)
    p.rect(x + 3, y + 5, x + 4, y + 7, K)
    p.rect(x + 9, y + 5, x + 10, y + 7, K)
    p.rect(x + 5, y + 10, x + 8, y + 10, K)


def big_x(p: Pix, cx, cy, r=9):
    p.d.line([(cx - r, cy - r), (cx + r, cy + r)], fill=K, width=5)
    p.d.line([(cx - r, cy + r), (cx + r, cy - r)], fill=K, width=5)
    p.d.line([(cx - r, cy - r), (cx + r, cy + r)], fill=R, width=3)
    p.d.line([(cx - r, cy + r), (cx + r, cy - r)], fill=R, width=3)


def exclaim(p: Pix, bx, by):
    p.box(bx, by, bx + 10, by + 15, W)
    p.rect(bx + 4, by + 3, bx + 6, by + 9, R)
    p.rect(bx + 4, by + 11, bx + 6, by + 12, R)
    p.d.polygon([(bx, by + 13), (bx - 4, by + 18), (bx + 4, by + 15)], fill=K)
    p.d.polygon([(bx + 1, by + 14), (bx - 2, by + 16), (bx + 3, by + 14)], fill=W)


def ep11():
    t = TEXT[11]
    p = Pix()
    GROUND = 99
    p.vgrad(0, GROUND, [K, (18, 40, 52), (30, 70, 72)])
    p.stars(2, 90, 40, 6, seed=111, avoid=[(36, 0, 150, 46), (148, 0, 284, 98)])
    p.vgrad(GROUND, LH - 1, [(30, 56, 60), K])
    for x in range(0, LW, 12):
        p.d.line([(x, GROUND), (x + (x - 160) // 3, LH)], fill=(24, 46, 52))
    # 2x2 四张小表，每张对角线都在发光
    labels = t["tables"]
    tw_, th_ = 62, 45
    origins = [(152, 3), (218, 3), (152, 52), (218, 52)]
    rnd = random.Random(11)
    for (x0, y0), lab in zip(origins, labels):
        p.window(x0, y0, x0 + tw_, y0 + th_, fill=(26, 52, 46))
        lw = Pix.cjk_w(lab, 13)
        p.cjk(lab, x0 + (tw_ - lw) // 2, y0 + 6, 13, W, shadow=K)
        n_, cs = 4, 5
        gx, gy = x0 + (tw_ - n_ * cs) // 2, y0 + 21
        glow = p.mask()
        ImageDraw.Draw(glow).polygon([(gx - 3, gy - 1), (gx + 3, gy - 3), (gx + n_ * cs + 3, gy + n_ * cs + 1),
                                      (gx + n_ * cs - 3, gy + n_ * cs + 3)], fill=255)
        p.dither_fill(glow, Y, 0.25)
        for i in range(n_):
            for j in range(n_):
                xx, yy = gx + j * cs, gy + i * cs
                if i == j:
                    p.rect(xx, yy, xx + cs - 1, yy + cs - 1, Y)
                    p.px(xx + 1, yy + 1, W)
                else:
                    p.rect(xx, yy, xx + cs - 1, yy + cs - 1, (150, 220, 170) if rnd.random() < 0.5 else (60, 100, 90))
                p.rect(xx, yy, xx + cs - 1, yy, (20, 40, 36))
                p.rect(xx, yy, xx, yy + cs - 1, (20, 40, 36))
    # 中间的 = 徽章：四张图是同一张
    bx, by = 216, 50
    p.d.ellipse([bx - 9, by - 9, bx + 9, by + 9], fill=K)
    p.d.ellipse([bx - 8, by - 8, bx + 8, by + 8], fill=Y)
    p.bitmap(["XXXXX", ".....", "XXXXX"], bx - 5, by - 3, K, k=2)
    # 机器人：恍然大悟
    rx = 74
    robot(p, rx, GROUND, face="right", eyes="sq", mouth="smile")
    exclaim(p, rx + 25, GROUND - 56)
    # 放大镜
    p.d.ellipse([rx + 26, GROUND - 30, rx + 38, GROUND - 18], fill=K)
    p.d.ellipse([rx + 28, GROUND - 28, rx + 36, GROUND - 20], fill=(170, 230, 240))
    p.px(rx + 30, GROUND - 26, W)
    p.d.line([(rx + 21, GROUND - 12), (rx + 28, GROUND - 19)], fill=WOOD_D, width=3)
    series_window(p, 11)
    dialog(p, title_lines(11))
    return p


def ep12():
    t = TEXT[12]
    p = Pix()
    GROUND = 99
    p.vgrad(0, GROUND, [K, (52, 28, 24), (100, 56, 36)])
    # 管道
    for (py, col) in ((50, (120, 110, 120)), (60, (90, 84, 96))):
        p.rect(0, py, LW, py + 4, K)
        p.rect(0, py + 1, LW, py + 3, col)
        p.rect(0, py + 1, LW, py + 1, (170, 160, 170))
        for x in range(8, LW, 40):
            p.box(x, py - 1, x + 4, py + 5, (150, 140, 150))
    p.vgrad(GROUND, LH - 1, [(70, 44, 32), K])
    for x in range(0, LW, 14):
        p.rect(x, GROUND + 1, x, LH, (56, 36, 28))
    # 编码机
    mx0, my0, mx1, my1 = 96, 44, 150, GROUND
    p.box(mx0, my0, mx1, my1, (150, 150, 168))
    p.rect(mx0 + 1, my0 + 1, mx1 - 1, my0 + 2, (200, 200, 216))
    p.rect(mx1 - 2, my0 + 3, mx1 - 1, my1 - 1, (100, 100, 120))
    p.box(mx0 + 4, my0 + 6, mx1 - 4, my0 + 20, N)
    for i, c_ in enumerate((R, Y, E)):
        p.box(mx0 + 8 + i * 8, my0 + 10, mx0 + 12 + i * 8, my0 + 14, c_)
    p.glyphs("123", mx1 - 24, my0 + 10, C, k=1)
    import math
    for (gcx, gcy, gr, col) in ((mx0 + 16, my0 + 34, 9, Y), (mx0 + 35, my0 + 40, 7, O)):
        for k_ in range(8):
            a = k_ / 8 * 2 * math.pi
            p.box(round(gcx + (gr + 1) * math.cos(a)) - 1, round(gcy + (gr + 1) * math.sin(a)) - 1,
                  round(gcx + (gr + 1) * math.cos(a)) + 1, round(gcy + (gr + 1) * math.sin(a)) + 1, col)
        p.d.ellipse([gcx - gr, gcy - gr, gcx + gr, gcy + gr], fill=K)
        p.d.ellipse([gcx - gr + 1, gcy - gr + 1, gcx + gr - 1, gcy + gr - 1], fill=col)
        p.d.ellipse([gcx - 2, gcy - 2, gcx + 2, gcy + 2], fill=K)
    # 进料口（左）与出纸口（右）
    p.box(mx0 - 3, 74, mx0 + 2, 86, K)
    p.box(mx1 - 2, 58, mx1 + 3, 72, K)
    # 机器人把一卷公式喂进去
    rx = 54
    p.box(rx + 20, 76, mx0 - 2, 85, W)
    for i, key in enumerate(("A", "E", "=")):
        p.sym(key, rx + 25 + i * 6, 78, K)
    robot(p, rx, GROUND, face="right", eyes="sq", mouth="smile")
    p.box(rx + 18, 74, rx + 23, 87, (230, 220, 190))
    # 吐出来的超长数字
    digits = t["number"]
    tx0, ty0 = mx1 + 2, 59
    tw = Pix.glyphs_w(digits, 2) + 10
    p.box(tx0, ty0, tx0 + tw, ty0 + 18, W)
    p.rect(tx0 + 1, ty0 + 17, tx0 + tw - 1, ty0 + 17, G)
    for x in range(tx0 + 3, tx0 + tw, 6):
        p.px(x, ty0 + 2, G)
        p.px(x, ty0 + 15, G)
    p.glyphs(digits, tx0 + 5, ty0 + 3, K, k=2)
    # 数字开口说话
    txt = t["bubble"]
    bw = Pix.cjk_w(txt, 14)
    bx1 = SAFE_R
    bx0 = bx1 - bw - 12
    p.bubble(bx0, 30, bx1, 52, (bx0 + 18, ty0 - 1))
    p.cjk(txt, bx0 + 6, 35, 14, K)
    series_window(p, 12)
    dialog(p, title_lines(12))
    return p


def stone_tablet(p: Pix, x0, y0, w, h, lines, size=14):
    STONE_T, STONE_L, STONE_S = (168, 164, 190), (206, 204, 222), (110, 104, 136)
    p.d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=8, fill=K)
    p.d.rounded_rectangle([x0 + 1, y0 + 1, x0 + w - 1, y0 + h - 1], radius=7, fill=STONE_T)
    p.rect(x0 + 6, y0 + 2, x0 + w - 6, y0 + 3, STONE_L)
    p.rect(x0 + w - 3, y0 + 8, x0 + w - 2, y0 + h - 2, STONE_S)
    for (cx_, cy_) in ((x0 + 6, y0 + h - 8), (x0 + w - 9, y0 + 12)):
        p.px(cx_, cy_, STONE_S)
        p.px(cx_ + 1, cy_ + 1, STONE_S)
    yy = y0 + 9
    for s in lines:
        lw = Pix.cjk_w(s, size)
        xx = x0 + (w - lw) // 2
        p.cjk(s, xx + 1, yy + 1, size, STONE_L)
        p.cjk(s, xx, yy, size, (54, 48, 78))
        yy += size + 4


def ep13():
    t = TEXT[13]
    p = Pix()
    GROUND = 98
    STONE, STONE_D, MORTAR = (66, 56, 92), (54, 46, 78), (34, 28, 52)
    for y in range(0, GROUND):
        for x in range(LW):
            row = y // 8
            off = 8 if row % 2 else 0
            c = STONE if ((x + off) // 16 + row) % 3 else STONE_D
            if y % 8 == 0 or (x + off) % 16 == 0:
                c = MORTAR
            p.im.putpixel((x, y), c)
    p.vgrad(GROUND, LH - 1, [(48, 40, 66), (28, 22, 42), K])
    torch(p, 100, 54)
    # 石碑
    tw_, th_ = 58, 52
    tx0 = 118
    stone_tablet(p, tx0, GROUND - th_, tw_, th_, t["tablet"])
    p.rect(tx0 - 4, GROUND - 3, tx0 + tw_ + 4, GROUND, (90, 84, 110))
    # 镜子：照出左右颠倒的石碑
    mx0, my0, mx1, my1 = 200, 34, 268, GROUND - 2
    p.box(mx0 - 3, my0 - 3, mx1 + 3, my1 + 3, Y)
    p.rect(mx0 - 2, my0 - 2, mx1 + 2, my0 - 2, W)
    p.box(mx0, my0, mx1, my1, (150, 200, 226))
    sub = Pix(bg=(1, 2, 3), size=(tw_ + 1, th_ + 1))
    stone_tablet(sub, 0, 0, tw_, th_, t["tablet"])
    p.stamp(sub, mx0 + (mx1 - mx0 - tw_) // 2, my1 - th_ - 1, flip=True)
    glass = p.mask()
    ImageDraw.Draw(glass).rectangle([mx0 + 1, my0 + 1, mx1 - 1, my1 - 1], fill=255)
    p.dither_fill(glass, (170, 220, 240), 0.125)
    for i in range(14):
        p.px(mx0 + 6 + i, my0 + 20 - i, (230, 246, 252))
        p.px(mx0 + 9 + i, my0 + 25 - i, (230, 246, 252))
    # 机器人一脸困惑
    rx = 60
    robot(p, rx, GROUND, face="right", eyes="worry", mouth="wavy")
    p.glyphs("?", rx + 24, GROUND - 58, Y, k=2, outline=K)
    p.glyphs("?", rx - 8, GROUND - 50, Y, k=1, outline=K)
    series_window(p, 13)
    dialog(p, title_lines(13))
    return p


def ep14():
    t = TEXT[14]
    p = Pix()
    GROUND = 98
    p.vgrad(0, GROUND, [K, (22, 26, 64), (40, 52, 100)])
    for cx_ in (8, 300):
        p.box(cx_, 0, cx_ + 12, GROUND, (60, 70, 120))
        p.rect(cx_ + 2, 0, cx_ + 3, GROUND, (90, 100, 160))
    p.vgrad(GROUND, LH - 1, [(44, 50, 90), (24, 26, 50), K])
    # 已经开过的小宝箱 A–E
    for i, letter in enumerate(t["opened"]):
        x0 = 44 + i * 14
        chest(p, x0, GROUND, w=11, h=9, open_=True)
        p.glyphs(letter, x0 + 3, GROUND - 22, W, k=1, shadow=K)
    # 机器人看着镜子，镜子里却是自己的背影
    rx = 118
    robot(p, rx, GROUND, face="right", eyes="sq", mouth="line")
    p.glyphs("?", rx + 6, GROUND - 58, Y, k=2, outline=K)
    mx0, my0, mx1, my1 = 156, 40, 196, GROUND - 4
    p.box(mx0 - 3, my0 - 3, mx1 + 3, my1 + 3, Y)
    p.rect(mx0 - 2, my0 - 2, mx1 + 2, my0 - 2, W)
    p.box(mx0, my0, mx1, my1, (150, 200, 226))
    sub = Pix(bg=(1, 2, 3), size=(26, 43))
    robot_back(sub, 2, 42)
    p.stamp(sub, mx0 + 7, my1 - 44)
    glass = p.mask()
    ImageDraw.Draw(glass).rectangle([mx0 + 1, my0 + 1, mx1 - 1, my1 - 1], fill=255)
    p.dither_fill(glass, (170, 220, 240), 0.125)
    for i in range(10):
        p.px(mx0 + 4 + i, my0 + 14 - i, (230, 246, 252))
    p.rect(mx0 + 10, my1 + 4, mx0 + 30, GROUND, WOOD_D)
    # 镜子上的牌子 Con(T)?
    lab = t["mirror"]
    lw = Pix.glyphs_w(lab, 1)
    lx0 = (mx0 + mx1) // 2 - lw // 2 - 4
    p.box(lx0, my0 - 15, lx0 + lw + 8, my0 - 4, WOOD)
    p.glyphs(lab, lx0 + 4, my0 - 13, W, k=1, shadow=K)
    # 最后一个大宝箱 F：打开
    fx0 = 214
    p.dither_fill(p.ellipse_mask(fx0 + 30, GROUND - 30, 40, 34), Y, 0.25)
    chest(p, fx0, GROUND, w=60, h=34, open_=True)
    p.glyphs("F", fx0 + 25, GROUND - 66, W, k=2, outline=K)
    for (sx, sy) in ((fx0 + 6, GROUND - 56), (fx0 + 54, GROUND - 60), (fx0 + 44, GROUND - 74)):
        p.twinkle(sx, sy, Y, big=True)
    series_window(p, 14)
    dialog(p, title_lines(14))
    return p


def ep15():
    t = TEXT[15]
    p = Pix()
    GROUND = 98
    p.vgrad(0, GROUND, [(24, 24, 80), (90, 54, 130), (230, 120, 120), (255, 200, 120)])
    p.stars(2, 30, 30, 4, seed=15, avoid=[(36, 0, 150, 46)])
    p.d.pieslice([150, GROUND - 26, 202, GROUND + 26], 180, 360, fill=(255, 236, 160))
    p.ridge(GROUND, 3, 11, (60, 50, 90), seed=16)
    p.vgrad(GROUND, LH - 1, [(50, 44, 80), (30, 26, 50), K])
    # （原来右上角的 THE END? 横幅去掉了：楼层牌“地牢的尽头？”说的是同一个笑点）
    # 被打叉的误解小怪
    for i, gx in enumerate((168, 206, 244)):
        gy = 36 + (i % 2) * 4
        ghost(p, gx, gy)
        big_x(p, gx + 12, gy + 13, r=5)
    # 六个宝箱 A–F 全部打开
    xs = [84 + i * 32 for i in range(6)]
    for x0, letter in zip(xs, "ABCDEF"):
        p.dither_fill(p.ellipse_mask(x0 + 13, GROUND - 14, 15, 13), Y, 0.25)
        chest(p, x0, GROUND, w=26, h=17, open_=True)
        p.glyphs(letter, x0 + 9, GROUND - 38, W, k=2, outline=K)
    # 机器人欢呼
    rx = 50
    robot(p, rx, GROUND, face="front", eyes="happy", mouth="smile", arms="up")
    for (sx, sy) in ((rx - 6, 50), (rx + 30, 46), (rx + 12, 40)):
        p.twinkle(sx, sy, Y, big=True)
    series_window(p, 15)
    dialog(p, title_lines(15))
    return p


BUILDERS = {1: ep01, 2: ep02, 3: ep03, 4: ep04, 5: ep05, 6: ep06, 7: ep07, 8: ep08, 9: ep09, 10: ep10, 11: ep11, 12: ep12, 13: ep13, 14: ep14, 15: ep15, 0: season}


def phone(img):
    sm = img.convert("RGB").resize((360, 203), Image.LANCZOS).convert("RGBA")
    ov = Image.new("RGBA", sm.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for yy in range(150, 203):
        od.line([(0, yy), (360, yy)], fill=(0, 0, 0, int(160 * (yy - 150) / 53)))
    sm.alpha_composite(ov)
    return sm.convert("RGB")


def out_paths(ep):
    if ep == 0:
        d = PROD / "season_cover"
        return d / "season_pixel_16x9.png", d / "season_pixel_4x3.png"
    d = PROD / f"ep{ep:02d}" / "cover"
    return d / "cover_pixel_16x9.png", d / "cover_pixel_4x3.png"


def render(ep):
    img = BUILDERS[ep]().out().convert("RGB")
    assert img.size == (1920, 1080)
    p16, p43 = out_paths(ep)
    p16.parent.mkdir(parents=True, exist_ok=True)
    img.save(p16)
    img.crop((240, 0, 1680, 1080)).save(p43)
    return img


if __name__ == "__main__":
    eps = [int(a) for a in sys.argv[1:]] or [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 0]
    for ep in eps:
        render(ep)
        print("wrote", *out_paths(ep))
