"""
E · 尼尔：机械纪元 UI 式  —  米灰单色 HUD，克制、精密
IDEA: 整季是一台 YoRHa 终端：变量是菜单项，选中（满足子句）的那一项整条反相；
      子句图是地图界面，切口把地图分成两块明度不同的区域，过界的比特在右侧面板里清点。
Reference: NieR:Automata (PlatinumGames, 2017) 菜单 / 地图界面 —— 单一米灰色相的明度台阶、反相选中条、方块项目符号。
House-rule adaptation: 原作大量使用细线框与小号大写标签；这里一律换成明度台阶与整条反相，字号保持可读。
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _kit import *  # noqa: F401,F403,E402

# palette roles ----------------------------------------------------------
BG = "#C8C5B8"        # khaki-grey ground (saturation ≈ 13%)
SURFACE = "#BAB6A8"   # one tone step: panels, unselected rows
INK = "#47443C"
MUTED = "#77736A"
ACCENT = INK          # the accent is inversion: an ink bar with ground-coloured text
ACCENT_INK = "#D6D3C7"

ANCHOR_X = -6.3
F_TITLE = "Hiragino Sans GB"
F_TEXT = "PingFang SC"
ROW_H = 0.64


def row(left, right, w, selected=False):
    fill = ACCENT if selected else SURFACE
    ink = ACCENT_INK if selected else INK
    b = box(w, ROW_H, fill)
    sq = Square(0.16).set_fill(ink, 1).set_stroke(width=0)
    l = left(ink) if callable(left) else T(left, F_TEXT, 28, ink)
    r = right(ink) if callable(right) else T(right, F_TEXT, 28, ink)
    sq.move_to(b.get_left() + RIGHT * 0.32)
    l.next_to(sq, RIGHT, buff=0.28)
    r.move_to(b.get_right() + LEFT * (0.3 + r.get_width() / 2))
    return VGroup(b, sq, l, r)


def panel(w, h, title):
    body = box(w, h, SURFACE)
    head = box(w, 0.56, INK).next_to(body, UP, buff=0)
    t = T(title, F_TEXT, 26, ACCENT_INK).move_to(head).align_to(head.get_left() + RIGHT * 0.3, LEFT)
    return VGroup(head, body, t), body


def caption(s):
    return T(s, F_TEXT, 30, INK, NORMAL).move_to([0, -3.45, 0]).align_to([ANCHOR_X, 0, 0], LEFT)


class E1_NieR_Title(Scene):
    default_camera_config = dict(background_color=BG)

    def construct(self):
        num = T(EP1_NUM, F_TEXT, 32, MUTED, NORMAL)
        title = T(EP1_TITLE, F_TITLE, 110, INK, NORMAL)
        sub = T(EP1_SUB, F_TEXT, 30, INK, LIGHT)
        head = VGroup(num, title, sub).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        head.move_to([0, 2.62, 0]).align_to([ANCHOR_X, 0, 0], LEFT)

        rows = VGroup()
        for k in (1, 2, 3):
            on = ASSIGN[k]
            hit = (k - 1) == SAT_LIT
            rows.add(row(lambda ink, k=k: VGroup(T("变量", F_TEXT, 28, ink), M(r"x_{%d}" % k, 38, ink)).arrange(RIGHT, buff=0.15),
                         "真" if on else "假", 5.2, selected=hit))
        rows.arrange(DOWN, buff=0.12).move_to([0, -1.1, 0]).align_to([ANCHOR_X, 0, 0], LEFT)

        pnl, body = panel(6.3, 2.9, "子句")
        pnl.move_to([3.3, -1.05, 0])
        lits = [lit_tex(l) for l in CLAUSE]
        left_part = M(r"(\," + r" \lor ".join(lits[:2]) + r" \lor {}", 74, INK)
        hit_part = M(lits[2], 74, ACCENT_INK)
        close = M(r")", 74, INK)
        hit_part.next_to(left_part, RIGHT, buff=0.3).align_to(left_part, DOWN)
        close.next_to(hit_part, RIGHT, buff=0.22)
        close.match_y(left_part[0])
        hl = box(hit_part.get_width() + 0.24, left_part.get_height() + 0.1, ACCENT).move_to(hit_part).match_y(left_part)
        clause = VGroup(left_part, hit_part, close)
        clause.move_to(body).shift(0.45 * UP).align_to(body.get_left() + RIGHT * 0.45, LEFT)
        hl.move_to(hit_part).match_y(left_part)
        note = T("x₃ 为真：子句满足", F_TEXT, 28, INK).next_to(clause, DOWN, buff=0.55)
        note.align_to(body.get_left() + RIGHT * 0.45, LEFT)
        rows.align_to(pnl, UP)
        stack(self, head, rows, pnl, hl, clause, note, caption(EP1_CAPTION))


class E2_NieR_Cut(Scene):
    default_camera_config = dict(background_color=BG)

    def construct(self):
        num = T(EP5_NUM, F_TEXT, 32, MUTED, NORMAL)
        title = T(EP5_TITLE, F_TITLE, 88, INK, NORMAL)
        head = VGroup(num, title).arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        head.move_to([0, 2.85, 0]).align_to([ANCHOR_X, 0, 0], LEFT)

        # map: two tone fields meeting at the cut
        L, R, Y0, Y1, CX = -6.3, 2.0, -2.85, 1.55, -2.35
        left_f = box(CX - L, Y1 - Y0, SURFACE).move_to([(L + CX) / 2, (Y0 + Y1) / 2, 0])
        right_f = box(R - CX, Y1 - Y0, "#ADA99B").move_to([(CX + R) / 2, (Y0 + Y1) / 2, 0])
        pos = {"E1": (-4.9, -1.9), "E2": (-4.5, 0.75), "E3": (-0.6, 0.95), "E4": (-1.1, -2.0), "E5": (1.2, -0.5)}
        P = {n: np.array([x, y, 0]) for n, (x, y) in pos.items()}
        edges, marks, bits = VGroup(), VGroup(), VGroup()
        for u, v, b, _ in EDGES:
            edges.add(bar(P[u], P[v], 0.05 if b == 1 else 0.11, INK))
            if crosses(u, v):
                t = (CX - P[u][0]) / (P[v][0] - P[u][0])
                m = P[u] + t * (P[v] - P[u])
                marks.add(Square(0.24).set_fill(INK, 1).set_stroke(width=0).move_to(m))
            else:
                bits.add(T(str(b), "Helvetica Neue", 26, INK, LIGHT).move_to(label_pos(P[u], P[v], 0.26)))
        nodes = VGroup()
        for n in NODES:
            nodes.add(VGroup(box(0.62, 0.62, INK).move_to(P[n]), M("E_{%s}" % n[1], 30, ACCENT_INK).move_to(P[n])))

        pnl, body = panel(4.2, 3.86, "切口")
        pnl.move_to([4.5, (Y0 + Y1) / 2 - 0.28, 0]).align_to([0, Y0, 0], DOWN)
        info = VGroup(
            row("跨过切口的比特", "3", 3.7, selected=True),
            row("外层枚举", lambda ink: M(r"2^3 = 8", 36, ink), 3.7),
            row("左侧", lambda ink: M(r"E_1\ E_2", 34, ink), 3.7),
            row("右侧", lambda ink: M(r"E_3\ E_4\ E_5", 34, ink), 3.7),
        ).arrange(DOWN, buff=0.12).move_to(body)
        # rows sit on the panel: give them the ground tone so they read as rows, selected stays inverted
        for r in info[1:]:
            r[0].set_fill(BG)
        stack(self, head, left_f, right_f, edges, marks, bits, nodes, pnl, info, caption(EP5_CAPTION))
