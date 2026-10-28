"""End-to-end demo: engine/demo/demo.md -> kepu voice -> this scene -> mp4 with narration.

    ./kepu voice engine/demo/demo.md --engine edge          # free placeholder voice -> engine/audio/demo/
    QUALITY=low engine/render.sh engine/demo/demo_scene.py DemoNarrated
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # engine/
from style import *  # noqa: E402,F403
from narrated import NarratedScene  # noqa: E402


class DemoNarrated(NarratedScene):
    chapter = "demo"

    def construct(self):
        # ---------------------------------------------------------- beat 01
        self.beat("01")
        h = Heading("布尔变量")
        v = BoolVar(1).scale(1.4)
        self.play(FadeIn(h), FadeIn(v, scale=0.8), run_time=self.until("真"))
        self.play(v.animate_set(True), run_time=0.4)
        self.wait_until_beat("假")
        self.play(v.animate_set(False), run_time=0.4)
        self.wait_until_beat("三个")
        vs = VGroup(BoolVar(1), BoolVar(2), BoolVar(3)).arrange(RIGHT, buff=0.6).scale(1.2)
        self.play(ReplacementTransform(v, vs[0]), FadeIn(vs[1:], shift=LEFT * 0.3), run_time=0.8)
        count = Formula(r"2 \times 2 \times 2 = 8").next_to(vs, DOWN, buff=0.8)
        self.play(Write(count), run_time=self.until("八种"))
        self.play(*[b.animate_set(val) for b, val in zip(vs, (True, False, True))], run_time=0.6)
        self.beat_wait()

        # ---------------------------------------------------------- beat 02
        self.beat("02")
        self.play(FadeOut(VGroup(vs, count)), Transform(h, Heading("子句与 CNF")), run_time=0.6)
        c1 = Clause([1, -2, 3])
        self.play(Write(c1), run_time=self.until("就得到一个子句"))
        self.play(mark_anim(Mark(c1)), run_time=0.5)
        f = CNF([[1, -2, 3], [-1, 2, 3], [2, -3]]).move_to(UP * 0.3)
        self.wait_until_beat("再把")
        self.play(ReplacementTransform(c1, f.clauses[0]), FadeIn(f[1:]), run_time=self.until("合取范式"))
        tag = CText("CNF 公式", size=SIZE_SMALL, color=INK_2).next_to(f, DOWN, buff=0.5)
        self.play(FadeIn(tag, shift=UP * 0.2), run_time=0.5)
        assign = {1: True, 2: True, 3: False}
        self.play(*f.evaluate_anims(assign), run_time=self.beat_remaining() * 0.8)
        self.beat_wait()

        # ---------------------------------------------------------- beat 03
        self.beat("03")
        self.clear_stage(run_time=0.5)
        h = Heading("指数墙")
        p = GrowthPlot(n_max=100, log_y=True, y_max_log10=30, width=9.5, height=4.6)
        p.next_to(h, DOWN, buff=0.3).set_x(0.3)
        c2n = p.plot_base(2, label=r"2^n")
        c13 = p.plot_base(1.308, label=r"1.308^n")
        self.play(FadeIn(h), FadeIn(p), run_time=0.8)
        self.play(ShowCreation(c2n), FadeIn(c2n.label), run_time=self.until("种赋值"))
        self.play(ShowCreation(c13), FadeIn(c13.label), run_time=self.until("把时间"))
        sub = p.plot_log10(lambda n: 3 * np.sqrt(n) * np.log10(2), label=r"2^{o(n)}", color=RED)
        self.play(ShowCreation(sub), FadeIn(sub.label), run_time=self.until("指数墙"))
        big = Formula(r"2^{o(n)}", size=96, color=RED)
        big.move_to(p.axes.c2p(30, 22))
        self.play(Write(big), run_time=self.until("倒了"))
        self.play(c2n.animate.set_stroke(opacity=0.25), c13.animate.set_stroke(opacity=0.25), run_time=0.6)
        self.beat_wait()
