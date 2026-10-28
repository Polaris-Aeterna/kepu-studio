"""
C · 女神异闻录 5 式  —  红 / 黑 / 白平面设计，倾斜构图，大字排版
IDEA: 证伪 ETH 是一次怪盗行动：子句是“预告信”，满足它的那个文字就是得手的那一张牌；
      切割是一道红色斜斩——斩口两侧错开，过口的边就是要偷运的比特。
Reference: Persona 5 (Atlus, 2016) UI / 预告信 —— 大面积纯色场、−8° 倾斜、黑底反白字块、无渐变。
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _kit import *  # noqa: F401,F403,E402

# palette roles ----------------------------------------------------------
BG = "#0E0E0E"        # black ground
SURFACE = "#262626"   # one step: inactive tags
INK = "#F4F1EC"       # white
MUTED = "#8E8A85"
ACCENT = "#E3141B"    # the red: used as whole fields (title field, the slash), never as a tint
ACCENT_INK = "#0E0E0E"

ANCHOR_X = -6.3
F_ZH = "Hiragino Sans GB"           # BOLD = W6
F_LAT = "Avenir Next Condensed"     # HEAVY
TILT = -8 * DEGREES


def slab(w, h, color, skew=0.35):
    """Parallelogram (P5 'cut' box), centred at origin."""
    return poly([(-w / 2 + skew, h / 2), (w / 2 + skew, h / 2), (w / 2 - skew, -h / 2), (-w / 2 - skew, -h / 2)], color)


def tag(content, fill, pad=(0.35, 0.18), skew=0.18):
    b = slab(content.get_width() + 2 * pad[0], content.get_height() + 2 * pad[1], fill, skew)
    b.move_to(content)
    return VGroup(b, content)


def caption(s):
    t = T(s, F_ZH, 30, INK, BOLD)
    box = slab(t.get_width() + 0.9, t.get_height() + 0.4, BG, 0.2)
    g = VGroup(box, t)
    t.move_to(box)
    return g.move_to([0, -3.4, 0]).align_to([ANCHOR_X - 0.2, 0, 0], LEFT)


class C1_Phantom_Title(Scene):
    default_camera_config = dict(background_color=BG)

    def construct(self):
        field = poly([(-7.2, 4.2), (1.6, 4.2), (-1.3, -4.2), (-7.2, -4.2)], ACCENT)
        num = T("第 1 期", F_ZH, 40, ACCENT_INK, BOLD)
        sat = T("SAT", F_LAT, 270, ACCENT_INK, HEAVY)
        what = T("是什么", F_ZH, 120, INK, BOLD)
        what_box = tag(what, BG, pad=(0.4, 0.2), skew=0.3)
        head = VGroup(num, sat, what_box)
        num.move_to([-5.2, 3.15, 0]).align_to([ANCHOR_X, 0, 0], LEFT)
        sat.next_to(num, DOWN, buff=0.05).align_to([ANCHOR_X - 0.15, 0, 0], LEFT)
        what_box.next_to(sat, DOWN, buff=-0.15).align_to([ANCHOR_X + 1.3, 0, 0], LEFT)
        head.rotate(TILT, about_point=[-4, 1.2, 0])
        sub = T(EP1_SUB, F_ZH, 30, ACCENT_INK, BOLD).move_to([0, -1.95, 0]).align_to([ANCHOR_X, 0, 0], LEFT)

        # the calling card
        lits = [lit_tex(l) for l in CLAUSE]
        clause = M(r"(\," + r" \lor ".join(lits) + r"\,)", 78, ACCENT_INK, isolate=lits)
        card = Rectangle(width=clause.get_width() + 1.1, height=clause.get_height() + 1.5).set_fill(INK, 1).set_stroke(width=0)
        clause.move_to(card).shift(0.15 * DOWN)
        card_t = T("预告信", F_ZH, 28, ACCENT, BOLD).next_to(card.get_corner(UL), DR, buff=0.22)
        cardg = VGroup(card, clause, card_t).rotate(5 * DEGREES).move_to([3.55, 0.95, 0])
        # variable tags: false = surface, true = white, the satisfying one = red
        tags = VGroup()
        for k in (1, 2, 3):
            on = ASSIGN[k]
            hit = (k - 1) == SAT_LIT
            fill = ACCENT if hit else (INK if on else SURFACE)
            ink = ACCENT_INK if (hit or on) else INK
            c = VGroup(M(r"x_{%d}" % k, 44, ink), T("真" if on else "假", F_ZH, 34, ink, BOLD)).arrange(RIGHT, buff=0.18, aligned_edge=DOWN)
            tags.add(tag(c, fill, pad=(0.38, 0.2)))
        tags.arrange(RIGHT, buff=0.3).rotate(-4 * DEGREES).move_to([3.45, -1.75, 0])
        stack(self, field, head, sub, cardg, tags, caption(EP1_CAPTION))


class C2_Phantom_Cut(Scene):
    default_camera_config = dict(background_color=BG)

    def construct(self):
        num = T(EP5_NUM, F_ZH, 36, MUTED, BOLD)
        title = T(EP5_TITLE, F_ZH, 112, INK, BOLD)
        head = VGroup(num, title).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        head.move_to([0, 2.75, 0]).align_to([ANCHOR_X, 0, 0], LEFT).rotate(-5 * DEGREES)

        # the slash: a long red parallelogram; everything right of it is knocked down-right
        sx, ang = 1.1, 74 * DEGREES
        d = np.array([np.cos(ang), np.sin(ang), 0])
        nrm = np.array([np.sin(ang), -np.cos(ang), 0])          # points to the right side
        c0 = np.array([sx, 0, 0])
        w = 0.32
        slash = Polygon(c0 - 6 * d - w * nrm, c0 + 6 * d - w * nrm, c0 + 6 * d + w * nrm, c0 - 6 * d + w * nrm,
                        fill_color=ACCENT, fill_opacity=1, stroke_width=0)
        OFF = 0.38 * nrm + 0.22 * DOWN
        pos = {"E1": (-1.7, -1.7), "E2": (-1.5, 0.9), "E3": (3.7, 1.8), "E4": (3.1, -1.9), "E5": (5.8, -0.1)}
        P = {n: np.array([x, y, 0]) + (OFF if n not in LEFT_SIDE else 0) for n, (x, y) in pos.items()}

        def side(p):
            return np.dot(p - c0, nrm)

        edges, bits = VGroup(), VGroup()
        for u, v, b, _ in EDGES:
            wid = 0.09 if b == 1 else 0.2
            if crosses(u, v):
                a, c = (P[u], P[v]) if u in LEFT_SIDE else (P[v], P[u])
                # split where the original (un-shifted) segment meets the slash
                a0 = np.array([*pos[u if u in LEFT_SIDE else v], 0])
                c1 = np.array([*pos[v if u in LEFT_SIDE else u], 0])
                t = side(a0) / (side(a0) - side(c1))
                m = a0 + t * (c1 - a0)
                edges.add(bar(a, m - w * nrm, wid, INK), bar(m + w * nrm + OFF, c, wid, INK))
            else:
                edges.add(bar(P[u], P[v], wid, INK))
                bits.add(T(str(b), F_LAT, 40, MUTED, HEAVY).move_to(label_pos(P[u], P[v], 0.34)))
        nodes = VGroup()
        for n in NODES:
            sq = Square(0.78).rotate(45 * DEGREES).set_fill(INK, 1).set_stroke(width=0).move_to(P[n])
            lab = M("E_{%s}" % n[1], 34, ACCENT_INK).move_to(P[n])
            nodes.add(VGroup(sq, lab))
        big = VGroup(T("3", F_LAT, 150, ACCENT_INK, HEAVY), T("比特", F_ZH, 54, ACCENT_INK, BOLD)).arrange(RIGHT, buff=0.15, aligned_edge=DOWN)
        bigtag = tag(big, ACCENT, pad=(0.45, 0.15), skew=0.3).rotate(-5 * DEGREES)
        calc = VGroup(T("外层枚举", F_ZH, 32, INK, BOLD), M(r"2^3 = 8", 58, INK)).arrange(RIGHT, buff=0.25)
        left = VGroup(bigtag, calc).arrange(DOWN, aligned_edge=LEFT, buff=0.35)
        left.move_to([0, -1.25, 0]).align_to([ANCHOR_X, 0, 0], LEFT)
        stack(self, edges, slash, bits, nodes, head, left, caption(EP5_CAPTION))
