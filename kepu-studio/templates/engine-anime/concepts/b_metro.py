"""
B · Mini Metro 式  —  极简地铁线路图
IDEA: 变量是车站（圆 / 三角 / 方，Mini Metro 的站型），子句是一条线路；
      切割是一条河：过河的每一座桥就是一个要枚举的比特，桥越少，切得越便宜。
Reference: Mini Metro (Dinosaur Polo Club, 2015) / Harry Beck 1933 伦敦地铁图 —— 八向折线、圆角、平面色、粗线。
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _kit import *  # noqa: F401,F403,E402

# palette roles ----------------------------------------------------------
BG = "#EEEDE8"        # bone paper, almost neutral
SURFACE = "#E2E0DA"   # one step: other (inactive) lines, panels
INK = "#1E1F22"
MUTED = "#76777C"
STATION = "#FFFFFF"   # station fill
RIVER = "#C9DCE4"     # the one field colour: water
LINE_A = "#2F6FD6"    # line colours carry meaning, not decoration
LINE_B = "#E9AE0C"
ACCENT = "#E2412E"    # the red line: the thing this frame is about

ANCHOR_X = -6.3
F_TITLE = "Hiragino Sans GB"   # BOLD = W6
F_TEXT = "PingFang SC"
LW = 15                        # line stroke width (px-ish)


def octi(p, q, diag_first=True):
    """Two-segment octilinear route from p to q (45° then straight)."""
    p, q = np.array(p, float), np.array(q, float)
    dx, dy = q[0] - p[0], q[1] - p[1]
    m = min(abs(dx), abs(dy))
    if diag_first:
        mid = p + np.array([np.sign(dx) * m, np.sign(dy) * m])
    else:
        mid = q - np.array([np.sign(dx) * m, np.sign(dy) * m])
    return [p, mid, q]


def station(kind, pos, filled=False, r=0.25):
    fill = INK if filled else STATION
    if kind == "circle":
        m = Circle(radius=r)
    elif kind == "triangle":
        m = Triangle().set_height(2.1 * r)
        m.move_to(ORIGIN).shift(0.04 * DOWN)
    else:
        m = Square(side_length=1.7 * r)
    return m.set_fill(fill, 1).set_stroke(INK, 7).move_to(pos)


def cap(p, q, color, length=0.42):
    """Mini Metro line terminus: a short bar perpendicular to the last segment."""
    p, q = np.array([*p[:2], 0.0]), np.array([*q[:2], 0.0])
    d = (q - p) / np.linalg.norm(q - p)
    n = np.array([-d[1], d[0], 0])
    return Line(q - n * length / 2, q + n * length / 2).set_stroke(color, LW)


def caption(s):
    return T(s, F_TEXT, 30, INK, NORMAL).move_to([0, -3.45, 0]).align_to([ANCHOR_X, 0, 0], LEFT)


class B1_Metro_Title(Scene):
    default_camera_config = dict(background_color=BG)

    def construct(self):
        num = T(EP1_NUM, F_TEXT, 34, MUTED, NORMAL)
        title = T(EP1_TITLE, F_TITLE, 120, INK, BOLD)
        sub = T(EP1_SUB, F_TEXT, 32, INK, NORMAL)
        head = VGroup(num, title, sub).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        head.move_to([0, 2.2, 0]).align_to([ANCHOR_X, 0, 0], LEFT)

        lits = [lit_tex(l) for l in CLAUSE]
        clause = M(r"(\," + r" \lor ".join(lits) + r"\,)", 76, INK)
        clause.move_to([0, -1.2, 0]).align_to([ANCHOR_X, 0, 0], LEFT)

        S = {1: np.array([1.4, 0.1]), 2: np.array([3.8, 0.1]), 3: np.array([5.4, -1.5])}
        route = [np.array([0.6, 0.9]), S[1], S[2], S[3], np.array([5.4, -2.8])]
        line = rounded_path(route, 0.45, LINE_A, LW)
        caps = VGroup(cap(route[1], route[0], LINE_A), cap(route[-2], route[-1], LINE_A))
        # other clauses through the same stations, in the surface tone (inactive)
        o1 = [[3.8, 4.3], [3.8, 0.1], [2.2, -1.5], [1.2, -1.5]]
        o2 = [[5.4, -1.5], [7.4, -1.5]]
        o3 = [[1.4, 0.1], [1.4, 2.0], [2.4, 3.0]]
        others = VGroup(*[rounded_path(o, 0.45, SURFACE, LW) for o in (o1, o2, o3)],
                        cap(o1[-2], o1[-1], SURFACE), cap(o3[-2], o3[-1], SURFACE))
        kinds = {1: "circle", 2: "triangle", 3: "square"}
        stations = VGroup(*[station(kinds[k], [*S[k], 0], filled=ASSIGN[k]) for k in (1, 2, 3)])
        # labels: literal + its truth, under/right of each station
        labs = VGroup()
        for i, l in enumerate(CLAUSE):
            k = abs(l)
            ok = lit_value(l)
            t = VGroup(M(lit_tex(l), 40, INK if ok else MUTED),
                       T("真" if ok else "假", F_TEXT, 28, INK if ok else MUTED, SEMIBOLD if ok else NORMAL))
            t.arrange(RIGHT, buff=0.14, aligned_edge=DOWN)
            off = {1: UP * 0.62 + RIGHT * 0.35, 2: UP * 0.62, 3: RIGHT * 0.95 + DOWN * 0.55}[k]
            labs.add(t.move_to([*S[k], 0] + off))
        # the train: parked at the station that satisfies the clause
        d = normalize(np.array([*(S[3] - S[2]), 0]))
        train = RoundedRectangle(width=0.56, height=0.3, corner_radius=0.06).set_fill(ACCENT, 1).set_stroke(width=0)
        train.rotate(np.arctan2(d[1], d[0])).move_to([*S[3], 0] - d * 0.62)
        legend = VGroup(
            VGroup(Circle(radius=0.13).set_fill(INK, 1).set_stroke(INK, 5), T("变量为真", F_TEXT, 26, MUTED)).arrange(RIGHT, buff=0.18),
            VGroup(Circle(radius=0.13).set_fill(STATION, 1).set_stroke(INK, 5), T("变量为假", F_TEXT, 26, MUTED)).arrange(RIGHT, buff=0.18),
        ).arrange(RIGHT, buff=0.6).next_to(clause, DOWN, buff=0.45).align_to([ANCHOR_X, 0, 0], LEFT)
        stack(self, others, line, caps, train, *stations, labs, head, clause, legend, caption(EP1_CAPTION))


BIT_POS = {("E3", "E4"): (3.45, -0.75), ("E1", "E2"): (-1.5, -0.35)}


class B2_Metro_Cut(Scene):
    default_camera_config = dict(background_color=BG)

    def construct(self):
        num = T(EP5_NUM, F_TEXT, 34, MUTED, NORMAL)
        title = T(EP5_TITLE, F_TITLE, 110, INK, BOLD)
        head = VGroup(num, title).arrange(DOWN, aligned_edge=LEFT, buff=0.28)
        head.move_to([0, 2.65, 0]).align_to([ANCHOR_X, 0, 0], LEFT)

        river = Polygon(*[np.array([*p, 0]) for p in
                          [(1.15, 4.3), (2.45, 4.3), (2.45, 3.6), (1.65, 2.8), (1.65, -4.3), (0.35, -4.3),
                           (0.35, 2.8), (1.15, 3.6)]], fill_color=RIVER, fill_opacity=1, stroke_width=0)
        river.round_corners(0.5)
        pos = {"E1": (-1.1, -1.8), "E2": (-0.9, 1.1), "E3": (4.0, 2.2), "E4": (3.6, -1.9), "E5": (6.1, 0.1)}
        routes = {
            ("E1", "E2"): octi(pos["E1"], pos["E2"]),
            ("E2", "E3"): octi(pos["E2"], pos["E3"]),
            ("E1", "E4"): octi(pos["E1"], pos["E4"], False),
            ("E3", "E4"): octi(pos["E3"], pos["E4"]),
            ("E3", "E5"): octi(pos["E3"], pos["E5"], False),
            ("E2", "E5"): octi(pos["E2"], pos["E5"]),
            ("E4", "E5"): octi(pos["E4"], pos["E5"]),
        }
        bridges, lines, bits = VGroup(), VGroup(), VGroup()
        for u, v, b, _ in EDGES:
            pts = routes[(u, v)]
            if crosses(u, v):
                col = ACCENT
            else:
                col = LINE_A if u in LEFT_SIDE else LINE_B
            if b == 2:   # two bits = two parallel tracks
                for sgn in (-1, 1):
                    lines.add(rounded_path([np.array(p) + sgn * np.array([0.13, 0]) for p in pts], 0.45, col, LW * 0.7))
            else:
                lines.add(rounded_path(pts, 0.45, col, LW))
            if crosses(u, v):
                # bridge deck under the line where it crosses the water
                seg = [np.array(p) for p in pts]
                for a, c in zip(seg[:-1], seg[1:]):
                    xs = sorted([a[0], c[0]])
                    if xs[0] < 1.0 < xs[1]:
                        t0 = (0.2 - a[0]) / (c[0] - a[0]) if c[0] != a[0] else 0
                        t1 = (1.8 - a[0]) / (c[0] - a[0]) if c[0] != a[0] else 1
                        t0, t1 = sorted([max(0, min(1, t0)), max(0, min(1, t1))])
                        p0, p1 = a + t0 * (c - a), a + t1 * (c - a)
                        bridges.add(Line([*p0, 0], [*p1, 0]).set_stroke(INK, LW + 12))
            # bit count beside the longest segment
            seg = [np.array([*p, 0]) for p in pts]
            k = max(range(len(seg) - 1), key=lambda i: np.linalg.norm(seg[i + 1] - seg[i]))
            if not crosses(u, v):
                lp = BIT_POS.get((u, v))
                lp = np.array([*lp, 0]) if lp else label_pos(seg[k], seg[k + 1], 0.32)
                bits.add(T(str(b), "Avenir Next", 28, MUTED, MEDIUM).move_to(lp))
        nodes, nlabels = VGroup(), VGroup()
        for n, (x, y) in pos.items():
            nodes.add(Circle(radius=0.33).set_fill(STATION, 1).set_stroke(INK, 9).move_to([x, y, 0]))
            nlabels.add(M("E_{%s}" % n[1], 32, INK).move_to([x, y, 0]))
        big = T("3", "Avenir Next", 190, ACCENT, MEDIUM)
        unit = T("座桥 = 3 个比特", F_TEXT, 34, INK, NORMAL)
        calc = VGroup(T("外层枚举", F_TEXT, 30, MUTED), M(r"2^3 = 8", 52, INK)).arrange(RIGHT, buff=0.25)
        side = VGroup(big, unit, calc).arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        side.move_to([0, -0.9, 0]).align_to([ANCHOR_X, 0, 0], LEFT)
        stack(self, river, bridges, lines, bits, nodes, nlabels, head, side, caption(EP5_CAPTION))
