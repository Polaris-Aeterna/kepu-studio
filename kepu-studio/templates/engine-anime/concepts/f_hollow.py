"""
F · 空洞骑士 / 剪影式  —  深色单色剪影，三层水墨般的明度，加一个冷色
IDEA: SAT 是一座地下王国：变量是吊着的灯（亮 = 真），子句是一扇只要一盏对的灯亮着就会开的门；
      子句图是洞穴地图，切割是一道深渊，跨过深渊的隧道就是要枚举的比特。
Reference: Hollow Knight (Team Cherry, 2017) —— 同一冷色相的 3 层平面剪影（远 / 中 / 近）、灯笼、尖塔；只用一种冷色表示“魂”。
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _kit import *  # noqa: F401,F403,E402

# palette roles ----------------------------------------------------------
BG = "#0F151A"        # blue-black ground
FAR = "#151E25"       # silhouette layers: three tone steps, flat, no blur
MID = "#1B2730"
NEAR = "#24323B"
SURFACE = NEAR
INK = "#E2E6E8"
MUTED = "#8996A0"
ACCENT = "#9FD3E0"    # pale 'soul' blue, flat (never glows)

ANCHOR_X = -6.3
F_ZH = "Songti SC"        # Noto CJK glyphs break in ManimGL 1.7.2 (隧, 过, 跨…)
F_TEXT = "PingFang SC"


def ridge(f, y_base, color, x0=-7.4, x1=7.4, n=160):
    xs = np.linspace(x0, x1, n)
    pts = [[x, f(x)] for x in xs] + [[x1, y_base], [x0, y_base]]
    return poly(pts, color)


def rocks(y, amp, seed, color, n=22, spikes=(), x0=-7.4, x1=7.4, y_base=-4.2):
    """Jagged flat-shaded rock line (piecewise linear) with optional stalagmite spikes (x, height)."""
    rng = np.random.default_rng(seed)
    xs = np.sort(np.concatenate([[x0, x1], rng.uniform(x0, x1, n)]))
    pts = []
    for x in xs:
        pts.append([x, y + amp * rng.uniform(-1, 1)])
        for sx, sh in spikes:
            if abs(x - sx) < (x1 - x0) / n / 2:
                pts += [[sx - 0.12, y + 0.05], [sx, y + sh], [sx + 0.12, y + 0.05]]
    pts += [[x1, y_base], [x0, y_base]]
    return poly(pts, color)


def spire(x, y, w, h, color):
    """A slim Hallownest-style spire: shaft + pointed cap."""
    return poly([(x - w / 2, y), (x - w / 2, y + h), (x - w * 0.18, y + h + w * 0.9), (x, y + h + w * 2.2),
                 (x + w * 0.18, y + h + w * 0.9), (x + w / 2, y + h), (x + w / 2, y)], color)


def lantern(pos, lit, color_lit, r=0.32):
    c = color_lit if lit else NEAR
    body = poly([(-r * 0.55, r), (r * 0.55, r), (r, 0), (r * 0.55, -r * 1.2), (-r * 0.55, -r * 1.2), (-r, 0)], c)
    cap_ = poly([(-r * 0.4, r), (r * 0.4, r), (r * 0.25, r * 1.35), (-r * 0.25, r * 1.35)], MID if lit else FAR)
    return VGroup(body, cap_).move_to(pos)


def caption(s):
    return T(s, F_TEXT, 30, INK, NORMAL).move_to([0, -3.45, 0]).align_to([ANCHOR_X, 0, 0], LEFT)


class F1_Hollow_Title(Scene):
    default_camera_config = dict(background_color=BG)

    def construct(self):
        far = rocks(-1.45, 0.28, 3, FAR, n=16)
        spires = VGroup(spire(2.2, -1.4, 0.5, 2.3, FAR), spire(3.3, -1.4, 0.38, 3.2, FAR), spire(5.6, -1.4, 0.44, 1.6, FAR))
        mid = rocks(-2.15, 0.2, 7, MID, n=26, spikes=[(-3.9, 0.9), (0.4, 0.6), (4.8, 1.1), (6.4, 0.5)])
        near = rocks(-2.95, 0.08, 11, NEAR, n=30, spikes=[(-5.6, 0.45), (2.6, 0.35)])

        num = T(EP1_NUM, F_ZH, 32, MUTED)
        title = T(EP1_TITLE, F_ZH, 118, INK)
        sub = T(EP1_SUB, F_ZH, 30, INK)
        head = VGroup(num, title, sub).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        head.move_to([0, 2.15, 0]).align_to([ANCHOR_X, 0, 0], LEFT)
        lits = [lit_tex(l) for l in CLAUSE]
        pieces = VGroup(M(r"(\," + r" \lor ".join(lits[:2]) + r" \lor {}", 70, INK), M(lits[2], 70, ACCENT), M(r"\,)", 70, INK))
        pieces[1].next_to(pieces[0], RIGHT, buff=0.24).align_to(pieces[0], DOWN)
        pieces[2].next_to(pieces[1], RIGHT, buff=0.12).match_y(pieces[0])
        pieces.move_to([0, -0.4, 0]).align_to([ANCHOR_X, 0, 0], LEFT)

        lamps = VGroup()
        for k, x in zip((1, 2, 3), (2.6, 4.1, 5.6)):
            on = ASSIGN[k]
            hit = (k - 1) == SAT_LIT
            y = 1.1 - 0.35 * (k - 2) ** 2 + (0.25 if k == 2 else 0)
            chain = box(0.035, 4.0 - y, MID).move_to([x, (4.0 + y) / 2 + 0.25, 0])
            lamp = lantern([x, y, 0], on, ACCENT if hit else INK)
            lab = VGroup(M(r"x_{%d}" % k, 40, ACCENT if hit else INK), T("亮" if on else "暗", F_ZH, 30, ACCENT if hit else MUTED))
            lab.arrange(RIGHT, buff=0.15, aligned_edge=DOWN).next_to(lamp, DOWN, buff=0.28)
            lamps.add(VGroup(chain, lamp, lab))
        legend = T("灯亮 = 变量为真", F_ZH, 26, MUTED).next_to(pieces, DOWN, buff=0.4).align_to([ANCHOR_X, 0, 0], LEFT)
        stack(self, far, spires, mid, near, lamps, head, pieces, legend, caption(EP1_CAPTION))


class F2_Hollow_Cut(Scene):
    default_camera_config = dict(background_color=BG)

    def construct(self):
        num = T(EP5_NUM, F_ZH, 32, MUTED)
        title = T(EP5_TITLE, F_ZH, 96, INK)
        head = VGroup(num, title).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        head.move_to([0, 2.8, 0]).align_to([ANCHOR_X, 0, 0], LEFT)

        # two landmasses and the abyss between them
        CX0, CX1 = 1.55, 2.35
        lpts = [(-1.3, 1.6), (-0.7, 1.95), (-0.1, 1.8), (0.5, 2.15), (1.0, 1.9), (CX0, 2.05), (CX0 - 0.2, 1.2),
                (CX0 + 0.05, 0.6), (CX0 - 0.15, -0.3), (CX0 + 0.1, -1.1), (CX0 - 0.1, -2.0), (CX0, -2.9),
                (0.4, -2.75), (-0.6, -2.9), (-1.3, -2.6), (-1.6, -1.6), (-1.35, -0.6), (-1.7, 0.4)]
        rpts = [(CX1, 2.25), (2.9, 2.5), (3.6, 2.35), (4.3, 2.7), (5.2, 2.45), (5.9, 2.75), (6.9, 2.55),
                (6.9, -2.9), (5.4, -2.75), (4.2, -2.9), (3.1, -2.7), (CX1 + 0.05, -2.9), (CX1 + 0.2, -2.0),
                (CX1 - 0.05, -1.2), (CX1 + 0.15, -0.3), (CX1 - 0.1, 0.5), (CX1 + 0.1, 1.4)]
        land_l = poly(lpts, FAR)
        land_r = poly(rpts, FAR)
        land_l.round_corners(0.08)
        land_r.round_corners(0.08)
        pos = {"E1": (-0.2, -1.9), "E2": (0.1, 1.0), "E3": (4.0, 1.6), "E4": (3.6, -1.8), "E5": (5.9, 0.0)}
        P = {n: np.array([x, y, 0]) for n, (x, y) in pos.items()}
        tunnels, ends, bits = VGroup(), VGroup(), VGroup()
        for u, v, b, _ in EDGES:
            wid = 0.16 if b == 1 else 0.3
            if crosses(u, v):
                a, c = P[u], P[v]
                t0 = (CX0 - a[0]) / (c[0] - a[0])
                t1 = (CX1 - a[0]) / (c[0] - a[0])
                m0, m1 = a + t0 * (c - a), a + t1 * (c - a)
                tunnels.add(bar(a, m0, wid, MID), bar(m1, c, wid, MID))
                ends.add(Circle(radius=0.11).set_fill(ACCENT, 1).set_stroke(width=0).move_to(m0),
                         Circle(radius=0.11).set_fill(ACCENT, 1).set_stroke(width=0).move_to(m1))
            else:
                tunnels.add(bar(P[u], P[v], wid, MID))
                bits.add(T(str(b), F_ZH, 30, MUTED).move_to(label_pos(P[u], P[v], 0.32)))
        rooms = VGroup()
        for n in NODES:
            rooms.add(VGroup(RoundedRectangle(width=0.9, height=0.66, corner_radius=0.2).set_fill(NEAR, 1).set_stroke(width=0).move_to(P[n]),
                             M("E_{%s}" % n[1], 32, INK).move_to(P[n])))
        big = T("3", F_ZH, 170, ACCENT)
        unit = T("条隧道跨过深渊", F_ZH, 32, INK)
        calc = VGroup(T("外层枚举", F_ZH, 28, MUTED), M(r"2^3 = 8", 50, INK)).arrange(RIGHT, buff=0.25)
        side = VGroup(big, unit, calc).arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        side.move_to([0, -0.95, 0]).align_to([ANCHOR_X, 0, 0], LEFT)
        stack(self, land_l, land_r, tunnels, ends, bits, rooms, head, side, caption(EP5_CAPTION))
