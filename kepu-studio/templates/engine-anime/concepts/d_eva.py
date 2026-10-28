"""
D · EVA 标题卡式  —  黑底白字、压扁的大号宋体、极简排版
IDEA: 每个定理、每个子句都是一张“标题卡”：字就是画面。变量的状态像 NERV 的判定读数，
      子句图画成六边形的 MAGI 节点，切割是一条红色的判定线。
Reference: 新世纪福音战士 (Gainax, 1995) 标题卡与字幕卡 —— 明朝体 Heavy 横向压缩、黑底、行首对齐与行尾对齐交错。
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _kit import *  # noqa: F401,F403,E402

# palette roles ----------------------------------------------------------
BG = "#060606"
SURFACE = "#161616"
INK = "#EDEBE6"       # warm white, not #fff
MUTED = "#7C7A76"
ACCENT = "#D8361F"    # NERV red-orange: one judgement per frame

ANCHOR_X = -6.4
RIGHT_X = 6.4
F_ZH = "Songti SC"
F_LAT = "Baskerville"
SQUASH = 0.74         # horizontal compression of display type


def big(s, size, color=INK, squash=SQUASH):
    t = T(s, F_ZH, size, color, HEAVY)
    t.stretch(squash, 0)
    return t


def caption(s):
    return T(s, F_ZH, 30, INK, NORMAL).move_to([0, -3.45, 0]).align_to([ANCHOR_X, 0, 0], LEFT)


class D1_EVA_Title(Scene):
    default_camera_config = dict(background_color=BG)

    def construct(self):
        ep = big("第一期", 96)
        sat = big("SAT", 330, squash=0.82)
        what = big("是什么", 210)
        ep.move_to([0, 3.0, 0]).align_to([ANCHOR_X, 0, 0], LEFT)
        sat.next_to(ep, DOWN, buff=0.1).align_to([ANCHOR_X - 0.08, 0, 0], LEFT)
        what.next_to(sat, DOWN, buff=-0.05).align_to([RIGHT_X, 0, 0], RIGHT)
        eng = T("EPISODE 1   What is SAT?", F_LAT, 34, INK).next_to(what, DOWN, buff=0.25).align_to([RIGHT_X, 0, 0], RIGHT)

        lits = [lit_tex(l) for l in CLAUSE]
        clause = M(r"(\," + r" \lor ".join(lits) + r"\,)", 60, INK, isolate=lits)
        clause.select_part(lits[SAT_LIT]).set_fill(ACCENT)
        rows = VGroup()
        for k in (1, 2, 3):
            on = ASSIGN[k]
            hit = (k - 1) == SAT_LIT
            r = VGroup(M(r"x_{%d}" % k, 44, ACCENT if hit else INK),
                       T("真" if on else "假", F_ZH, 40, ACCENT if hit else INK, HEAVY))
            r.arrange(RIGHT, buff=0.22, aligned_edge=DOWN)
            rows.add(r)
        rows.arrange(RIGHT, buff=0.7)
        read = VGroup(clause, rows).arrange(DOWN, aligned_edge=LEFT, buff=0.35)
        read.move_to([0, -1.75, 0]).align_to([ANCHOR_X, 0, 0], LEFT)
        stack(self, ep, sat, what, eng, read, caption(EP1_CAPTION))


def hexagon(r, color):
    return RegularPolygon(6, radius=r).set_fill(color, 1).set_stroke(width=0)


class D2_EVA_Cut(Scene):
    default_camera_config = dict(background_color=BG)

    def construct(self):
        ep = big("第五期", 72)
        t1 = big("切开", 200)
        t2 = big("扩张图", 124)
        ep.move_to([0, 3.05, 0]).align_to([ANCHOR_X, 0, 0], LEFT)
        t1.next_to(ep, DOWN, buff=0.1).align_to([ANCHOR_X, 0, 0], LEFT)
        t2.next_to(t1, DOWN, buff=0.0).align_to([ANCHOR_X, 0, 0], LEFT)
        eng = T("EPISODE 5   Cutting the expander", F_LAT, 30, INK).next_to(t2, DOWN, buff=0.25).align_to([ANCHOR_X, 0, 0], LEFT)

        pos = {"E1": (1.1, -1.9), "E2": (0.9, 1.3), "E3": (4.3, 2.3), "E4": (3.9, -1.5), "E5": (6.0, 0.4)}
        P = {n: np.array([x, y, 0]) for n, (x, y) in pos.items()}
        CX = 2.45
        cut = Rectangle(width=0.09, height=7.0).set_fill(ACCENT, 1).set_stroke(width=0).move_to([CX, 0.1, 0])
        edges, bits = VGroup(), VGroup()
        for u, v, b, _ in EDGES:
            col = INK
            edges.add(bar(P[u], P[v], 0.05 if b == 1 else 0.11, col))
            if crosses(u, v):
                t = (CX - P[u][0]) / (P[v][0] - P[u][0])
                m = P[u] + t * (P[v] - P[u])
                bits.add(Square(0.2).rotate(45 * DEGREES).set_fill(ACCENT, 1).set_stroke(width=0).move_to(m))
            else:
                bits.add(T(str(b), F_LAT, 34, MUTED).move_to(label_pos(P[u], P[v], 0.3)))
        nodes = VGroup()
        for n in NODES:
            nodes.add(VGroup(hexagon(0.42, INK).move_to(P[n]), M("E_{%s}" % n[1], 34, BG).move_to(P[n])))
        count = VGroup(big("三", 120, ACCENT), T("个比特穿过判定线", F_ZH, 34, INK, NORMAL)).arrange(RIGHT, buff=0.3, aligned_edge=DOWN)
        count.move_to([0, -2.35, 0]).align_to([ANCHOR_X, 0, 0], LEFT)
        stack(self, edges, cut, bits, nodes, ep, t1, t2, eng, count, caption(EP5_CAPTION))
