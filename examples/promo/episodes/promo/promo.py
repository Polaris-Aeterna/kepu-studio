"""kepu-studio 宣传片：13 个 beat，4 个场景（EVA 标题卡风，引擎来自《ETH 之墙》）。

    engine/render.sh episodes/promo/promo.py -a                      # 1080p，全部场景
    QUALITY=low engine/render.sh episodes/promo/promo.py Promo_02_Voice

稿子 script/episodes/promo.md，分镜 script/storyboards/promo.md，配音 engine/audio/promo/（kepu voice）。
音效 assets/sfx/（engine/sfx.py 合成），图 assets/img/（两部作品的真实成片帧、概念帧、试听页截图）。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "engine"))
from style import *  # noqa: E402,F403
from narrated import NarratedScene  # noqa: E402

IMG = ROOT / "assets" / "img"
SFX = ROOT / "assets" / "sfx"
MONO = "Menlo"
CONTENT_Y = 0.375                      # centre of the content area (y ∈ [−2.75, 3.5])


# ---------------------------------------------------------------- parts
def img(name: str, width: float | None = None, height: float | None = None) -> ImageMobject:
    m = ImageMobject(str(IMG / name))
    if width:
        m.set_width(width)
    if height:
        m.set_height(height)
    return m


def window(name: str, width: float = 11.1, center=(0, CONTENT_Y, 0), edge=DIM, height: float | None = None) -> Group:
    """A real frame shown as a monitor: the picture plus a hairline edge (a frame, not a decoration)."""
    m = (img(name, height=height) if height else img(name, width=width)).move_to(np.array(center))
    e = Rectangle(width=m.get_width(), height=m.get_height()).set_stroke(edge, 2).set_fill(opacity=0).move_to(m)
    return Group(m, e)


def mono(text: str, size: float = 24, color=INK) -> Text:
    return CText(text, size, color, font=MONO)


def chip(text: str, lit: bool = False, size: float = 30) -> VGroup:
    t = CText(text, size, BG if lit else INK_2, BOLD if lit else NORMAL)
    r = Rectangle(width=t.get_width() + 0.56, height=t.get_height() + 0.34).move_to(t)
    r.set_fill(INK, 1).set_stroke(width=0) if lit else r.set_fill(opacity=0).set_stroke(DIM, 2)
    return VGroup(r, t)


def head(text: str, num: str | None = None) -> VGroup:
    """Content heading, optionally followed by a small Latin counter (01 / 03)."""
    h = Heading(text)
    if num is None:
        return VGroup(h)
    n = Latin(num, 30, INK_2).next_to(h, RIGHT, buff=0.45).align_to(h, DOWN).shift(UP * 0.04)
    return VGroup(h, n)


def chars(s: str, size: float, color=INK, buff: float = 0.05) -> VGroup:
    """One Display mobject per character (so single characters can be pointed at)."""
    return VGroup(*[Display(c, size, color) for c in s]).arrange(RIGHT, buff=buff, aligned_edge=DOWN)


def arrow(a, b, color=INK_2, width=3) -> VGroup:
    """Hairline arrow from a to b with a small solid head (no curves, no glow)."""
    a, b = np.array(a), np.array(b)
    d = (b - a) / np.linalg.norm(b - a)
    n = np.array([-d[1], d[0], 0])
    tip = Polygon(b, b - d * 0.22 + n * 0.09, b - d * 0.22 - n * 0.09).set_fill(color, 1).set_stroke(width=0)
    return VGroup(Line(a, b - d * 0.18).set_stroke(color, width), tip)


class Promo(NarratedScene):
    chapter = "promo"
    beat_gap = 0.3

    def sfx(self, name: str, gain: float = -10.0):
        self.add_sound(str(SFX / f"{name}.wav"), gain=gain)

    def swap(self, old, new, sound: str | None = "tick", gain: float = -16):
        self.remove(old)
        self.add(new)
        if sound:
            self.sfx(sound, gain)


# =====================================================================
# Scene 1 · 冷开场、三个事故、片名
# =====================================================================
class Promo_01_Open(Promo):
    def construct(self):
        self.b01()
        self.b02()
        self.b03()

    def b01(self):
        self.beat("01")
        frames = ["e1_1", "p12_480", "r_760", "p12_40", "r_1290", "p12_880", "e5_250", "r_800"]
        dt = (self.word_time("最难的") - 0.04) / len(frames)
        for f in frames:
            self.cut_to(window(f + ".png"))
            self.sfx("tick", -17)
            self.wait(dt)
        rows = BigCard([("最难的", SIZE_L), ("不是画面", SIZE_L)], layout="stagger")[0]
        self.wait_until_beat("最难的")
        self.big(rows[0])
        self.sfx("hit", -6)
        self.wait_until_beat("不是")
        self.add(rows[1])
        self.sfx("hit", -14)
        self.beat_wait()

    def b02(self):
        self.beat("02")
        # the real frame where it happened
        w = window("r_375.png", width=10.0, center=(0, 0.05, 0))
        lab = CText("《ETH 之墙》第一期　真实画面", 26, INK_2).next_to(w, UP, buff=0.16).align_to(w, LEFT)
        self.cut_to(w, lab)
        self.play(w.animate.scale(1.035), run_time=self.until("配音") - 0.05, rate_func=linear)
        # 01 读音
        self.wait_until_beat("配音")
        word = chars("长子句", SIZE_L).move_to(UP * 0.05)
        src = CText("2026-10-28　作者在成片里听出来的", SIZE_SMALL, INK_2)
        src.align_to(np.array([RIGHT_X, 0, 0]), RIGHT).set_y(-2.25)
        self.cut_to(head("读音", "01 / 03"), word, src)
        self.sfx("tick", -15)
        self.wait_until_beat("zhǎng")
        py = Latin("zhǎng", 72, RED).next_to(word[0], UP, buff=0.32)
        bar = block(word[0].get_width(), 0.07, RED).next_to(word[0], DOWN, buff=0.18)
        self.add(py, bar)
        self.sfx("err", -9)
        # 02 画风
        self.wait_until_beat("画风")
        slide = self.ppt_slide().scale(0.9).move_to(DOWN * 0.08)
        self.cut_to(head("画风", "02 / 03"), slide)
        self.sfx("tick", -15)
        self.wait(0.5)
        line = JudgeLine(slide.get_corner(UL) + np.array([-0.3, 0.17, 0]), slide.get_corner(DR) + np.array([0.3, -0.17, 0]))
        self.sfx("sweep", -11)
        self.play(judge_sweep(line, run_time=0.45))
        # 03 讲义
        self.wait_until_beat("讲义")
        left, right, neq = self.mismatch()
        self.cut_to(head("讲义", "03 / 03"), left, right, neq)
        self.sfx("tick", -15)
        self.wait_until_beat("对不上")
        num = right[-1]
        self.add(num.copy().set_color(RED), Mark(num, RED, buff=0.12, height=0.07))
        self.remove(num)
        self.sfx("err", -10)
        self.beat_wait()

    def ppt_slide(self) -> VGroup:
        """What the series must never look like: a stock office slide."""
        W, H = 9.6, 5.4
        bg = block(W, H, "#FFFFFF")
        blue, navy, grey = "#4472C4", "#1F3864", "#595959"
        title = CText("第三章　布尔可满足性问题", 40, navy, BOLD, font="PingFang SC")
        title.move_to(bg.get_corner(UL) + np.array([0.5, -0.6, 0]), aligned_edge=UL)
        rule = block(W - 1.0, 0.05, blue).next_to(title, DOWN, buff=0.22).align_to(title, LEFT)
        bullets = VGroup(*[CText(f"•  {s}", 30, "#222222", font="PingFang SC") for s in ("定义与记号", "基本性质", "典型例题", "本章小结")])
        bullets.arrange(DOWN, buff=0.34, aligned_edge=LEFT).next_to(rule, DOWN, buff=0.5).align_to(title, LEFT)
        boxes = VGroup()
        for s in ("输入", "处理", "输出"):
            r = RoundedRectangle(width=2.1, height=0.72, corner_radius=0.14).set_fill(blue, 1).set_stroke("#2F528F", 2)
            boxes.add(VGroup(r, CText(s, 28, "#FFFFFF", BOLD, font="PingFang SC").move_to(r)))
        boxes.arrange(DOWN, buff=0.42).move_to(bg.get_right() + np.array([-1.75, -0.45, 0]))
        links = VGroup(*[arrow(boxes[i].get_bottom() + DOWN * 0.02, boxes[i + 1].get_top() + UP * 0.02, "#A5A5A5", 3)
                         for i in range(2)])
        foot = CText("第 12 页", 18, grey, font="PingFang SC").move_to(bg.get_corner(DR) + np.array([-0.75, 0.3, 0]))
        return VGroup(bg, title, rule, bullets, boxes, links, foot)

    def mismatch(self):
        """The handout says 1.27, the video says 1.72."""
        def panel(ground, ink, sub, label, value):
            b = block(5.7, 3.7, ground)
            cap = CText(label, 24, INK_2 if ground != PAPER else "#5E5B55").move_to(b.get_corner(UL) + np.array([0.4, -0.45, 0]), aligned_edge=UL)
            s = CText(sub, 32, ink).next_to(cap, DOWN, buff=0.55).align_to(cap, LEFT)
            v = VGroup(CText("约", 40, ink), Latin(value, 96, ink), CText("倍", 40, ink)).arrange(RIGHT, buff=0.18, aligned_edge=DOWN)
            v.next_to(s, DOWN, buff=0.45).align_to(cap, LEFT)
            return VGroup(b, cap, s, v)
        left = panel(PAPER, PAPER_INK, "新算法比旧算法快", "讲义 PDF · 定理 2.1", "1.27").move_to(np.array([-3.15, 0.2, 0]))
        right = panel(SURFACE, INK, "新算法比旧算法快", "视频 · 12:06", "1.72").move_to(np.array([3.15, 0.2, 0]))
        neq = Formula(r"\neq", 84, INK_2).move_to(np.array([0, 0.2, 0]))
        return left, VGroup(*right[:-1], right[-1][0], right[-1][2], right[-1][1]), neq

    def b03(self):
        self.beat("03")
        card = BigCard([("科普", SIZE_M), ("番剧工坊", 240)], layout="stagger")
        self.big(card, count=False)
        self.sfx("hit", -4)
        self.wait_until_beat("一套")
        en = Latin("KEPU-STUDIO   ·   A CLAUDE CODE PLUGIN", 30, INK_2)
        en.next_to(card, DOWN, buff=0.32).align_to(np.array([RIGHT_X, 0, 0]), RIGHT)
        self.add(en)
        self.sfx("tick", -15)
        self.wait_until_beat("挡")
        bar = block(2 * SAFE_X, 0.09, RED).set_y(en.get_bottom()[1] - 0.42)
        self.sfx("hit", -15)
        self.play(GrowFromEdge(bar, LEFT), run_time=0.5, rate_func=EASE_EXPO)
        self.beat_wait()
        self.sfx("sweep", -11)
        self.judge_cut()
        self.wait(0.15)


# =====================================================================
# Scene 2 · 读音、希腊字母、耳检
# =====================================================================
class Promo_02_Voice(Promo):
    def construct(self):
        self.b04()
        self.b05()
        self.b06()

    def b04(self):
        self.beat("04")
        h = head("读音先定死")
        s = chars("原来的长子句", 120).move_to(UP * 1.15)
        target = s[3]
        box = Rectangle(width=target.get_width() + 0.22, height=target.get_height() + 0.26).set_stroke(INK, 2).move_to(target)
        names = ["词典", "上下文规则", "分词陷阱检测"]
        off = VGroup(*[chip(n, size=34) for n in names]).arrange(RIGHT, buff=0.42).move_to(DOWN * 0.55)
        on = VGroup(*[chip(n, lit=True, size=34).move_to(o) for n, o in zip(names, off)])
        self.cut_to(h, s, off)
        self.play(ShowCreation(box), run_time=0.35, rate_func=EASE_OUT)
        for i, n in enumerate(names):
            self.wait_until_beat(n)
            self.swap(off[i], on[i])
        self.wait_until_beat("每个")
        py = Latin("cháng", 64, INK).next_to(target, UP, buff=0.3)
        self.add(py)
        self.sfx("ok", -10)
        self.wait_until_beat("答案")
        lab1, lab2 = CText("字幕", 28, INK_2), CText("发给模型", 28, INK_2)
        sub = CText("原来的长子句", 40, INK)
        tts = VGroup(CText("原来的", 40, INK), CText("尝", 40, RED), CText("子句", 40, INK)).arrange(RIGHT, buff=0.02)
        rows = VGroup(VGroup(lab1, sub), VGroup(lab2, tts))
        for lab, t in rows:
            t.next_to(lab, RIGHT, buff=0.4)
        rows.arrange(DOWN, buff=0.28, aligned_edge=LEFT)
        for lab, t in rows:
            t.align_to(np.array([-1.0, 0, 0]), LEFT)
            lab.align_to(np.array([-1.4, 0, 0]), RIGHT)
        rows.set_y(-1.95)
        mk = Mark(tts[1], RED, buff=0.06, height=0.06)
        self.play(rise_lines([rows[0], rows[1]], run_time=0.6, lag=0.25))
        self.play(mark_anim(mk))
        # the trap: two plausible segmentations, held for a human
        self.wait_until_beat("拿不准")
        s2 = chars("东西藏在箱子里", 110).move_to(UP * 1.1)
        seg = VGroup(
            VGroup(CText("东西｜藏", 40, INK), Latin("cáng", 36, INK_2)).arrange(RIGHT, buff=0.35, aligned_edge=DOWN),
            VGroup(CText("东｜西藏", 40, INK), Latin("zàng", 36, INK_2)).arrange(RIGHT, buff=0.35, aligned_edge=DOWN),
        ).arrange(DOWN, buff=0.36, aligned_edge=LEFT).move_to(np.array([-2.2, -1.15, 0]))
        hold = InvertTag("拦下 · 问你", 34, color=RED, ink=INK).move_to(np.array([3.4, -1.15, 0]))
        self.cut_to(h, s2, seg)
        self.sfx("tick", -15)
        self.wait_until_beat("拦下")
        self.add(hold, s2[2].copy().set_color(RED))
        self.remove(s2[2])
        self.sfx("err", -9)
        self.beat_wait()

    def b05(self):
        self.beat("05")
        h = head("希腊字母")
        g = Formula(r"\alpha\beta\pi", 300)
        for i, x in enumerate((-4.3, 0.0, 4.3)):
            g[i].set_x(x)
        g.set_y(0.95)
        names = [("alpha", INK_2), ("beta", INK_2), ("pie", RED)]
        labs = VGroup(*[Latin(n, 62, c).move_to(np.array([g[i].get_x(), g.get_bottom()[1] - 0.6, 0]))
                        for i, (n, c) in enumerate(names)])
        self.cut_to(h)
        for i, w in enumerate("αβπ"):
            self.wait_until_beat(w)
            self.add(g[i], labs[i])
            self.sfx("tick", -13)
        self.wait_until_beat("换了")
        shot = window("greek2x.png", height=5.25, center=(0, 0.05, 0), edge=INK_2)
        cap = CText("每个音色试听一次：每个字母选最像英文的一条，所有项目共用", SIZE_SMALL, INK_2)
        cap.next_to(shot, UP, buff=0.16).align_to(shot, LEFT)
        self.cut_to(shot, cap)
        self.sfx("tick", -15)
        self.play(shot.animate.scale(1.03), run_time=max(0.3, self.beat_remaining()), rate_func=linear)
        self.beat_wait()

    def b06(self):
        self.beat("06")
        h = head("耳检")
        wav = json.loads((ROOT / "assets" / "wave.json").read_text())
        rms = np.array(wav["rms"])
        rms = (rms - rms.min()) / (rms.max() - rms.min())
        rng = np.random.default_rng(11)
        n = len(rms)
        xs = np.linspace(-6.3, 6.3, n)
        hs = 0.12 + 2.4 * (rms ** 1.6) * (0.75 + 0.5 * rng.random(n))
        bars = VGroup(*[block(0.032, hh, DIM).move_to(np.array([x, 0.35, 0])) for x, hh in zip(xs, hs)])
        cap = CText("《ETH 之墙》第一期　25 分 37 秒", SIZE_SMALL, INK_2).next_to(bars, UP, buff=0.42).align_to(bars, LEFT)
        self.cut_to(h, cap)
        self.play(LaggedStart(*[GrowFromCenter(b) for b in bars], lag_ratio=0.004), run_time=0.8)
        self.wait_until_beat("不用")
        whole = CText("整集重听　25 分钟", 32, INK_2).align_to(np.array([RIGHT_X, 0, 0]), RIGHT).set_y(-1.85)
        self.play(rise_in(whole, run_time=0.4))
        self.wait_until_beat("只听")
        strike = Line(whole.get_left() + LEFT * 0.08, whole.get_right() + RIGHT * 0.08).set_stroke(INK_2, 3)
        self.add(strike)
        lit = VGroup(*[block(0.05, hs[i] + 0.36, RED).move_to(bars[i]) for i in wav["spots"]])
        self.play(LaggedStart(*[FadeIn(b) for b in lit], lag_ratio=0.06), run_time=1.1)
        for k in range(6):
            self.sfx("tick", -20)
            self.wait(0.07)
        few = CText("只听这几十处　约 2 分钟", 34, INK).align_to(np.array([RIGHT_X, 0, 0]), RIGHT).set_y(-2.4)
        self.play(rise_in(few, run_time=0.4))
        self.wait_until_beat("两分钟")
        card = self.ear_card()
        self.cut_to(h, card)
        self.sfx("tick", -15)
        self.wait(0.55)
        self.swap(card.ok_off, card.ok_on, "ok", -10)
        self.beat_wait()

    def ear_card(self) -> VGroup:
        b = block(8.8, 3.5, SURFACE).move_to(UP * 0.3)
        n = Latin("07 / 41", 28, INK_2).move_to(b.get_corner(UL) + np.array([0.45, -0.4, 0]), aligned_edge=UL)
        kind = CText("新替身字 · beat 02", 28, INK_2).next_to(n, RIGHT, buff=0.4)
        ctx = VGroup(CText("原来的", 50, INK_2), CText("长", 50, INK, BOLD), CText("子句能被满足", 50, INK_2)).arrange(RIGHT, buff=0.04)
        ctx.next_to(n, DOWN, buff=0.85).align_to(n, LEFT)
        rd = Latin("cháng", 38, INK).next_to(ctx[1], UP, buff=0.12)
        okoff, bad = chip("对", size=34), chip("错", size=34)
        okon = chip("对", lit=True, size=34)
        btn = VGroup(okoff, bad).arrange(RIGHT, buff=0.3).move_to(b.get_corner(DR) + np.array([-1.3, 0.6, 0]))
        okon.move_to(okoff)
        clip = VGroup(*[block(0.05, h, DIM) for h in 0.12 + 0.5 * np.abs(np.sin(np.linspace(0, 9, 46)))]).arrange(RIGHT, buff=0.045)
        clip.next_to(ctx, DOWN, buff=0.45).align_to(ctx, LEFT)
        g = VGroup(b, n, kind, ctx, rd, okoff, bad, clip)
        g.ok_off, g.ok_on = okoff, okon
        return g


# =====================================================================
# Scene 3 · 画风、两套引擎、讲义与分级、关卡
# =====================================================================
DIRECTIONS = ["EVA 标题卡", "像素 RPG", "怪盗预告信", "机械纪元 UI", "深渊灯笼", "不可能的建筑", "地铁线路图", "法庭举证", "规则积木",
              "卡牌构筑", "回合制对战", "神庙试炼", "文字演出", "涂地墨水", "方块消行", "流水线工厂", "红石电路", "扁平水彩"]
DEALT = [("EVA 标题卡", "D1_EVA_Title.png", "7.6"), ("地铁线路图", "B1_Metro_Title.png", "8.3"),
         ("怪盗预告信", "C1_Phantom_Title.png", "7.7"), ("机械纪元 UI", "E1_NieR_Title.png", "7.5")]
PALETTE = [("BG", BG), ("SURFACE", SURFACE), ("INK", INK), ("INK 2", INK_2), ("DIM", DIM), ("RED", RED), ("PAPER", PAPER)]


class Promo_03_Craft(Promo):
    def construct(self):
        self.b07()
        self.b08()
        self.b09()
        self.b10()

    def b07(self):
        self.beat("07")
        h = head("画风")
        cards = VGroup()
        for name in DIRECTIONS:
            b = block(1.95, 1.08, SURFACE)
            cards.add(VGroup(b, CText(name, 24, INK_2).move_to(b)))
        cards.arrange_in_grid(3, 6, buff=0.13).move_to(UP * 0.25)
        sub = CText("18 个动漫 / 游戏方向", SIZE_SMALL, INK_2).next_to(cards, DOWN, buff=0.35).align_to(cards, LEFT)
        self.cut_to(h)
        self.play(rise_lines(list(cards), run_time=0.9, lag=0.03), FadeIn(sub), run_time=0.9)
        self.wait_until_beat("发牌")
        idx = [DIRECTIONS.index(n) for n, _, _ in DEALT]
        slots = [np.array([x, 0.75, 0]) for x in (-4.8, -1.6, 1.6, 4.8)]
        rest = [c for i, c in enumerate(cards) if i not in idx]
        anims = [c.animate.set_opacity(0.1) for c in rest] + [FadeOut(sub)]
        for k, i in enumerate(idx):
            anims.append(cards[i].animate.scale(1.5).move_to(slots[k]))
        self.sfx("deal", -10)
        self.play(*anims, run_time=0.55, rate_func=EASE_INOUT)
        self.wait_until_beat("样张")
        shots = Group(*[img(f, width=2.93).move_to(slots[k]) for k, (_, f, _) in enumerate(DEALT)])
        for k, i in enumerate(idx):
            self.remove(cards[i])
            self.add(shots[k])
        self.remove(*rest)
        self.sfx("tick", -13)
        names = VGroup(*[CText(n, 26, INK).next_to(shots[k], DOWN, buff=0.22) for k, (n, _, _) in enumerate(DEALT)])
        self.add(names)
        self.wait_until_beat("评委")
        jury = CText("taste 评委", 28, INK_2).move_to(np.array([ANCHOR_X, -0.95, 0]), aligned_edge=LEFT)
        scores = VGroup(*[Latin(s, 64, INK).next_to(names[k], DOWN, buff=0.3) for k, (_, _, s) in enumerate(DEALT)])
        self.add(jury)
        for sc in scores:
            self.add(sc)
            self.sfx("tick", -18)
            self.wait(0.09)
        self.wait_until_beat("最后")
        eva = img("D1_EVA_Title.png", width=6.0).move_to(np.array([-3.3, 0.55, 0]))
        pick = Mark(eva, RED, buff=0.16, height=0.08)
        pick_lab = CText("作者选定：EVA 标题卡", 26, INK).next_to(pick, DOWN, buff=0.22).align_to(eva, LEFT)
        sw = VGroup()
        for name, col in PALETTE:
            sq = Square(0.74).set_fill(col, 1).set_stroke(DIM if col in (BG, SURFACE) else col, 1.5)
            sw.add(VGroup(sq, Latin(name, 20, INK_2).next_to(sq, DOWN, buff=0.12)))
        sw.arrange(RIGHT, buff=0.12).move_to(np.array([3.35, 1.7, 0]))
        t1 = Display("宋体 Heavy　压缩 0.74", 58).next_to(sw, DOWN, buff=0.6).align_to(sw, LEFT)
        t2 = Latin("Baskerville  —  English lines", 32, INK_2).next_to(t1, DOWN, buff=0.3).align_to(sw, LEFT)
        rule = CText("一底一墨一强调色　红色只给判定", 30, INK_2).next_to(t2, DOWN, buff=0.45).align_to(sw, LEFT)
        self.cut_to(h, eva, sw, t1, t2, rule)
        self.sfx("tick", -14)
        self.play(mark_anim(pick), FadeIn(pick_lab), run_time=0.4)
        self.beat_wait()

    def b08(self):
        self.beat("08")
        h = head("两套引擎")
        W = 6.1
        L = np.array([-3.25, 0.55, 0])
        Rr = np.array([3.25, 0.55, 0])
        fl = Rectangle(width=W, height=W * 9 / 16).set_stroke(DIM, 2).move_to(L)
        fr = Rectangle(width=W, height=W * 9 / 16).set_stroke(DIM, 2).move_to(Rr)
        ll = VGroup(CText("EVA 标题卡", 34, INK, BOLD), Latin("ManimGL  ·  《ETH 之墙》", 24, INK_2)).arrange(RIGHT, buff=0.35, aligned_edge=DOWN)
        lr = VGroup(CText("像素 RPG", 34, INK, BOLD), Latin("Pillow + numpy  ·  《地基之下》", 24, INK_2)).arrange(RIGHT, buff=0.35, aligned_edge=DOWN)
        ll.next_to(fl, DOWN, buff=0.3).align_to(fl, LEFT)
        lr.next_to(fr, DOWN, buff=0.3).align_to(fr, LEFT)
        left = [img(f, width=W).move_to(L) for f in ("e1_1.png", "r_1290.png", "e5_500.png", "r_1215.png")]
        right = [img(f, width=W).move_to(Rr) for f in ("p12_480.png", "p12_520.png", "p12_880.png")]
        dim_l, dim_r = left[0].copy().set_opacity(0.16), right[0].copy().set_opacity(0.16)
        self.cut_to(h, dim_l, dim_r, fl, fr)
        self.wait_until_beat("EVA")
        cur_l = left[0]
        self.remove(dim_l)
        self.add(cur_l, fl, ll)
        self.sfx("tick", -14)
        self.wait(0.75)
        self.swap(cur_l, left[1], None)
        cur_l = left[1]
        self.add(fl)
        self.wait_until_beat("像素")
        cur_r = right[0]
        self.remove(dim_r)
        self.add(cur_r, fr, lr)
        self.sfx("tick", -14)
        for k in range(1, 3):
            self.wait(0.62)
            self.swap(cur_l, left[k + 1], None)
            cur_l = left[k + 1]
            self.swap(cur_r, right[k], None)
            cur_r = right[k]
            self.add(fl, fr)
        self.beat_wait()

    def b09(self):
        self.beat("09")
        h = head("一份稿子")
        doc = block(3.3, 4.3, SURFACE).move_to(np.array([-4.75, 0.3, 0]))
        dt = Latin("ep07.md", 26, INK).move_to(doc.get_corner(UL) + np.array([0.35, -0.42, 0]), aligned_edge=UL)
        lines = VGroup(mono("## beat 12 [L2]", 21, INK_2), mono("台词：同一个子句…", 21, INK_2),
                       mono("画面：判定条变红", 21, INK_2), mono("## beat 13 [L3]", 21, INK_2), mono("台词：每个子句…", 21, INK_2))
        lines.arrange(DOWN, buff=0.24, aligned_edge=LEFT).next_to(dt, DOWN, buff=0.4).align_to(dt, LEFT)
        bars = VGroup(*[block(w, 0.08, DIM) for w in (2.4, 1.7, 2.1)]).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        bars.next_to(lines, DOWN, buff=0.32).align_to(dt, LEFT)
        self.cut_to(h, doc, dt, lines, bars)
        self.sfx("tick", -15)
        start = doc.get_right() + RIGHT * 0.15

        def card(title, body=(), pic=None, y=0.0):
            b = block(5.0, 1.6, SURFACE).move_to(np.array([3.2, y, 0]))
            parts = VGroup(b)
            x0 = b.get_left()[0] + 0.3
            if pic is not None:
                pic.set_height(1.36).move_to(np.array([x0 + pic.get_width() / 2, y, 0]))
                x0 = pic.get_right()[0] + 0.3
            t = CText(title, 30, INK, BOLD).move_to(np.array([x0, b.get_top()[1] - 0.36, 0]), aligned_edge=UL)
            ln = VGroup(*[mono(x, 20, INK_2) for x in body]).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
            ln.next_to(t, DOWN, buff=0.2).align_to(t, LEFT)
            parts.add(t, ln)
            return parts, pic
        c0, hand = card("讲义 PDF", ["定义 · 定理（带严谨度）", "误解 · 习题 · 分级框"], img("handout.png"), 1.8)
        c1, _ = card("逐字稿 · B 站分段", ["00:00 冷开场", "03:12 子句只禁止一种取值"], None, 0.0)
        c2, _ = card("字幕 .srt", ["00:01:12,300 --> 00:01:14,900", "原来的长子句能被满足"], None, -1.8)
        for c, w in ((c0, "生成讲义"), (c1, "逐字稿"), (c2, "字幕")):
            self.wait_until_beat(w)
            a = arrow(start, c[0].get_left() + LEFT * 0.12)
            extra = [FadeIn(hand, shift=LEFT * 0.15)] if c is c0 else []
            self.play(ShowCreation(a[0]), FadeIn(a[1]), FadeIn(c, shift=LEFT * 0.15), *extra, run_time=0.42, rate_func=EASE_OUT)
            self.sfx("tick", -16)
        # levels
        self.wait_until_beat("内容分成")
        h2 = head("三级")
        x0 = -2.9
        spec = [("L1", "主线", "只假设高中数学", 7.6, INK), ("L2", "进阶", "本科理工", 2.6, INK_2), ("L3", "硬核支线", "可以跳过", 1.15, RED)]
        rows, fills = VGroup(), []
        for k, (lv, name, note, w, col) in enumerate(spec):
            y = 1.55 - k * 1.25
            lab = VGroup(Latin(lv, 40, INK), CText(name, 34, INK, BOLD)).arrange(RIGHT, buff=0.22, aligned_edge=DOWN)
            at_anchor(lab, y)
            nt = CText(note, 25, INK_2).next_to(lab, DOWN, buff=0.12).align_to(lab, LEFT)
            track = block(9.2, 0.42, SURFACE).move_to(np.array([x0 + 4.6, y - 0.1, 0]))
            fill = block(w, 0.42, col).move_to(np.array([x0 + w / 2, y - 0.1, 0]))
            rows.add(VGroup(lab, nt, track))
            fills.append(fill)
        lim_x = x0 + 0.2 * (7.6 + 2.6 + 1.15)
        lim = DashedLine(np.array([lim_x, -0.55, 0]), np.array([lim_x, -1.25, 0]), dash_length=0.08).set_stroke(INK_2, 2)
        lim_lab = CText("上限 20%", 25, INK_2).next_to(lim, RIGHT, buff=0.12).align_to(lim, DOWN)
        self.cut_to(h2, rows)
        self.sfx("tick", -15)
        for k, w in enumerate(("主线", "进阶", "硬核")):
            self.wait_until_beat(w)
            self.play(GrowFromEdge(fills[k], LEFT), run_time=0.45, rate_func=EASE_EXPO)
            if k == 2:
                self.add(lim, lim_lab)
        self.wait_until_beat("观众")
        cut = CText("kepu stats --cut L1　→　只留主线的精简版，剪预告、做短视频", 28, INK_2)
        at_anchor(cut, -2.35)
        self.play(rise_in(cut, run_time=0.4))
        self.beat_wait()

    def b10(self):
        self.beat("10")
        h = head("四道检查")
        names = ["脚本", "配音", "画面", "发布"]
        items = [("读音 0 处拦下", "格式"), ("和当前稿子一致", "耳检 0 错"), ("分镜节奏预算", "渲染无警告"), ("响度 −16 LUFS", "字幕 讲义 封面")]
        xs = [-4.7, -1.57, 1.57, 4.7]
        W, H = 2.72, 1.35
        gates, lits, subs = VGroup(), VGroup(), VGroup()
        for x, n, (i1, i2) in zip(xs, names, items):
            b = block(W, H, SURFACE).move_to(np.array([x, 1.05, 0]))
            t = CText(n, 44, INK_2, BOLD).move_to(b)
            gates.add(VGroup(b, t))
            lb = Rectangle(width=W, height=H).set_stroke(INK, 3).set_fill(SURFACE, 1).move_to(b)
            lits.add(VGroup(lb, CText(n, 44, INK, BOLD).move_to(b)))
            s = VGroup(CText(i1, 26, INK_2), CText(i2, 26, INK_2)).arrange(DOWN, buff=0.16, aligned_edge=LEFT)
            s.next_to(b, DOWN, buff=0.3).align_to(b, LEFT).shift(RIGHT * 0.12)
            subs.add(s)
        links = VGroup(*[arrow(gates[i][0].get_right() + RIGHT * 0.05, gates[i + 1][0].get_left() + LEFT * 0.05, DIM, 3) for i in range(3)])
        self.cut_to(h, gates, links, subs)
        self.sfx("tick", -15)
        for i, n in enumerate(names):
            self.wait_until_beat(n)
            self.swap(gates[i], lits[i], "tick", -15)
        self.wait_until_beat("有一项")
        marks = VGroup()
        for i in (0, 1):
            marks.add(Latin("✓", 40, INK).move_to(lits[i][0].get_corner(UR) + np.array([-0.3, -0.3, 0])))
        bad = VGroup(block(W, H, RED).move_to(lits[2]), CText("画面", 44, BG, BOLD).move_to(lits[2]))
        why = CText("大字卡 9 次 > 上限 8", 26, RED).move_to(subs[2][0], aligned_edge=LEFT)
        self.add(marks)
        self.remove(lits[2], subs[2][0])
        self.add(bad, why)
        self.sfx("err", -9)
        self.wait_until_beat("就不往下")
        stop = block(0.12, 2.3, RED).move_to(links[2]).set_y(1.05)
        self.add(stop)
        self.play(lits[3].animate.set_opacity(0.25), subs[3].animate.set_opacity(0.25), run_time=0.35)
        self.sfx("hit", -16)
        self.beat_wait()


# =====================================================================
# Scene 4 · 复盘、这支片子本身、片尾
# =====================================================================
class Promo_04_Close(Promo):
    def construct(self):
        self.b11()
        self.b12()
        self.b13()

    def b11(self):
        self.beat("11")
        h = head("每一个错")
        rows = [("长子句", "zhǎng", "《ETH 之墙》第一期", "test_chang_zi_ju"),
                ("可数学家", "可暑学家", "《地基之下》第八轮", "test_shu_trap_kexuejia"),
                ("无穷多行", "xíng", "《地基之下》第四轮", "test_hang"),
                ("计数完美匹配", "jìshǔ", "《ETH 之墙》规则误配", "test_eth_false_matches")]
        left, right, arrows, ticks = VGroup(), VGroup(), VGroup(), VGroup()
        for k, (w, wrong, src, test) in enumerate(rows):
            y = 1.85 - k * 1.08
            a = VGroup(CText(w, 40, INK, BOLD), CText("念成", 28, INK_2), CText(wrong, 36, INK) if any("\u4e00" <= c <= "\u9fff" for c in wrong) else Latin(wrong, 40, INK))
            a.arrange(RIGHT, buff=0.22, aligned_edge=DOWN)
            at_anchor(a, y)
            s = CText(src, 24, INK_2).next_to(a, DOWN, buff=0.1).align_to(a, LEFT)
            left.add(VGroup(a, s))
            t = mono(test, 28, INK).move_to(np.array([1.4, y, 0]), aligned_edge=LEFT)
            right.add(t)
            arrows.add(arrow(np.array([0.35, y, 0]), np.array([1.15, y, 0]), INK_2, 3))
            ticks.add(Latin("✓", 36, INK).next_to(t, RIGHT, buff=0.3))
        self.cut_to(h)
        self.play(rise_lines(list(left), run_time=1.2, lag=0.18))
        self.wait_until_beat("都会")
        for k in range(len(rows)):
            self.add(arrows[k], right[k])
            self.sfx("key", -12)
            self.wait(0.3)
        self.wait_until_beat("一个测试")
        for k in range(len(rows)):
            self.add(ticks[k])
            self.sfx("ok", -16)
            self.wait(0.12)
        self.wait_until_beat("同一个错")
        self.sfx("paper", -9)
        card = InsertCard(["同一个错", "不出第二次"])        # stays through the gap; the next beat's cut removes it
        card.fix_in_frame()
        card.z_index = 200
        self._note("insert", self.insert_min_gap)
        self.add(card)
        self.beat_wait()

    def b12(self):
        self.beat("12")
        h = head("这支宣传片")
        lp = block(6.25, 4.75, SURFACE).move_to(np.array([-3.2, 0.25, 0]))
        rp = block(6.25, 4.75, SURFACE).move_to(np.array([3.2, 0.25, 0]))
        lt = Latin("script/episodes/promo.md", 22, INK_2).move_to(lp.get_corner(UL) + np.array([0.35, -0.38, 0]), aligned_edge=UL)
        rt = Latin("terminal", 22, INK_2).move_to(rp.get_corner(UL) + np.array([0.35, -0.38, 0]), aligned_edge=UL)
        src = VGroup(mono("## beat 02 [L1]", 24, INK_2), mono("台词：……配音把“长子句”", 24, INK),
                     mono("念成了“", 24, INK), mono("## beat 05 [L1]", 24, INK_2), mono("台词：希腊字母按英文念：", 24, INK),
                     mono("α、β、π。", 24, INK))
        src.arrange(DOWN, buff=0.3, aligned_edge=LEFT).next_to(lt, DOWN, buff=0.42).align_to(lt, LEFT)
        mk = mono("{zhǎng 子句|涨子句}", 24, INK).next_to(src[2], RIGHT, buff=0.0)
        tail = mono("”；……", 24, INK).next_to(mk, RIGHT, buff=0.0)
        term = [("$ kepu lint promo.md", INK_2), ("  13 个 beat，拦下 0。可以合成。", INK),
                ("$ kepu voice promo.md", INK_2), ("  新合成 450 字符 · 96 秒", INK),
                ("$ kepu board promo.md", INK_2), ("  分镜节奏：通过", INK),
                ("$ kepu gate promo.md", INK_2), ("  通过", INK)]
        tl = VGroup(*[mono(s, 23, c) for s, c in term]).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        tl.next_to(rt, DOWN, buff=0.38).align_to(rt, LEFT)
        self.cut_to(h, lp, rp, lt, rt, src, mk, tail)
        self.sfx("tick", -15)
        self.wait_until_beat("读音")
        per = max(0.12, (self.word_time("就是") - self.beat_time()) / len(tl))
        for t in tl:
            self.add(t)
            self.sfx("key", -15)
            self.wait(per)
        self.wait_until_beat("就是")
        red = mk.copy().set_color(RED)
        self.remove(mk)
        self.add(red)
        self.play(mark_anim(Mark(red, RED, buff=0.08, height=0.06)))
        self.sfx("ok", -12)
        self.beat_wait()

    def b13(self):
        self.beat("13")
        title = Display("科普番剧工坊", 168)
        at_anchor(title, 1.45)
        en = Latin("KEPU-STUDIO", 40, INK_2).next_to(title, DOWN, buff=0.28).align_to(title, LEFT)
        self.sfx("sweep", -12)
        self.judge_cut(title, en)
        self.sfx("hit", -7)
        self.wait_until_beat("装上")
        box = block(2 * SAFE_X, 1.3, SURFACE).move_to(np.array([0, -1.05, 0]))
        cmd = VGroup(mono("claude plugin marketplace add Polaris-Aeterna/kepu-studio", 25, INK),
                     mono("claude plugin install kepu-studio@kepu-studio-market", 25, INK)).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        if cmd.get_width() > box.get_width() - 1.2:
            cmd.set_width(box.get_width() - 1.2)
        cmd.move_to(box).align_to(box.get_left() + RIGHT * 0.75, LEFT)
        pr = VGroup(*[Latin("$", 25, INK_2).next_to(c, LEFT, buff=0.2) for c in cmd])
        self.add(box, cmd, pr)
        self.sfx("key", -12)
        self.wait_until_beat("做你的")
        mk = block(1.9, 0.1, RED).next_to(en, DOWN, buff=0.32).align_to(title, LEFT)
        url = Latin("github.com/Polaris-Aeterna/kepu-studio      v0.2.0", 30, INK_2).next_to(box, DOWN, buff=0.3).align_to(box, LEFT)
        self.play(mark_anim(mk), FadeIn(url), run_time=0.4)
        self.beat_wait()
        self.set_subtitles(False)
        self.wait(3.2)
        self.sfx("hit", -12)
        self.cut_to()
        self.wait(0.6)
