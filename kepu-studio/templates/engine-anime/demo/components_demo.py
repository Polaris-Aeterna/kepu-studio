"""Every EVA component on a still.  FRAME=1 engine/render.sh engine/demo/components_demo.py -a"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # engine/
from style import *  # noqa: E402,F403
from narrated import EvaScene  # noqa: E402


class DemoBigCard(EvaScene):
    def construct(self):
        self.add(ChapterCard(1, "SAT 是什么", en="EPISODE 1   What is SAT?"))


class DemoBigVertical(EvaScene):
    def construct(self):
        card = BigCard(["为什么信", "为什么错"], vertical=True)
        self.add(card.move_to(RIGHT * 2.5))
        note = at_anchor(CText("竖排：每行一列，从右往左读。", SIZE_BODY, INK_2), -2.2)
        self.add(note)


class DemoInsert(EvaScene):
    def construct(self):
        self.add(InsertCard(["指数时间假说", "是错的"], en="The Exponential Time Hypothesis is false"))


class DemoContent(EvaScene):
    def construct(self):
        h = Heading("子句与 CNF")
        vs = VGroup(BoolVar(1, True, caption="小一"), BoolVar(2, False, caption="小二"), BoolVar(3)).arrange(RIGHT, buff=0.6)
        at_anchor(vs, 1.0)
        f = CNF([[1, 2, -3], [-1, 3], [-2, -3]], per_row=3)
        at_anchor(f, -1.0)
        assign = {1: True, 2: False, 3: False}
        self.add(h, vs, f)
        self.play(*f.evaluate_anims(assign), run_time=0.3)
        m = Mark(f.clauses[0])
        body = CText("一个子句只禁止一种取值。", SIZE_BODY).next_to(f, DOWN, buff=0.6)
        at_anchor(body)
        tag = InvertTag("3-SAT", SIZE_SMALL).next_to(h, RIGHT, buff=0.5)
        z = ZhTex(r"\text{当 } n \to \infty \text{ 时，} 2^{o(n)} \ll 1.308^n", 44).move_to([3.3, 1.0, 0])
        self.add(m, body, tag, z)


class DemoGraph(EvaScene):
    def construct(self):
        h = Heading("切开扩张图")
        pos = {"E1": (-1.6, -1.8), "E2": (-1.8, 1.2), "E3": (2.4, 2.0), "E4": (2.0, -1.6), "E5": (4.6, 0.3)}
        bits = {("E1", "E2"): 2, ("E2", "E3"): 1, ("E1", "E4"): 1, ("E3", "E4"): 1, ("E3", "E5"): 1,
                ("E2", "E5"): 1, ("E4", "E5"): 1}
        g = SimpleGraph(list(pos), list(bits), layout=pos, bits=bits,
                        node_labels={k: "E_%s" % k[1] for k in pos})
        g.shift(RIGHT * 1.3 + DOWN * 0.3)
        line, marks, c = g.cut({"E1", "E2"})
        n = at_anchor(VGroup(Display(str(c), 150, RED), CText("个比特穿过判定线", SIZE_BODY)).arrange(RIGHT, aligned_edge=DOWN, buff=0.25), -2.1)
        self.add(h, g, n)
        self.play(judge_sweep(line))
        self.add(marks)


class DemoPlot(EvaScene):
    def construct(self):
        h = Heading("指数墙")
        p = GrowthPlot(n_max=100, log_y=True, y_max_log10=30, width=10.5, height=4.6)
        p.next_to(h, DOWN, buff=0.45).set_x(0.3)
        a = p.plot_base(2, label=r"2^n")
        b = p.plot_base(1.308, label=r"1.308^n", color=INK_2)
        c = p.plot_log10(lambda n: 3 * np.sqrt(n) * np.log10(2), label=r"2^{o(n)}", color=RED)
        self.add(h, p, a, b, c, a.label, b.label, c.label)


class DemoTimeline(EvaScene):
    def construct(self):
        h = Heading("四十年")
        tl = Timeline([(1971, "Cook–Levin"), (1972, "Karp 21 问题"), (1999, "Schöning"), (2001, "ETH"),
                       (2005, "PPSZ"), (2026, "ETH 被证伪", RED)], start=1965, end=2030)
        tl.shift(DOWN * 0.4)
        self.add(h, tl)


class DemoPapers(EvaScene):
    def construct(self):
        h = Heading("两篇论文")
        p1 = PaperCard("A 2^{o(n)} time algorithm for 3-SAT", "Anthropic · Claude", "arXiv 2610.00577")
        p2 = PaperCard("The Exponential Time Hypothesis is False", "OpenAI", "2026 年 10 月")
        VGroup(p1, p2).arrange(RIGHT, buff=0.4).move_to(DOWN * 0.2)
        self.add(h, p1, p2)


class DemoPaperGround(EvaScene):
    def construct(self):
        self.set_ground("paper")
        h = Heading("定义", color=PAPER_INK)
        d = CText("3-SAT：给定每个子句不超过 3 个文字的 CNF，\n是否存在使它为真的赋值？", 40, PAPER_INK)
        at_anchor(d, 0.4)
        f = Formula(r"\varphi = (x_1 \lor x_2 \lor \neg x_3) \land (\neg x_1 \lor x_3)", 56, PAPER_INK)
        at_anchor(f, -1.3)
        self.add(h, d, f, Mark(f[0:6], RED))
