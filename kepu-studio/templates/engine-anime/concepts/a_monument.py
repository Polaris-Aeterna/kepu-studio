"""
A · 纪念碑谷式  —  低饱和等距几何
IDEA: 变量是压力板，子句是一扇门：任何一块“对的”压力板被踩下，门就打开；
      切割是把世界沿一条缝滑开（纪念碑谷的机关），过缝的走道就是要枚举的比特。
Reference: Monument Valley (ustwo, 2014) — 等距透视、同一色相的三档明度面、几乎无文字的留白。
"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _kit import *  # noqa: F401,F403,E402

# palette roles ----------------------------------------------------------
BG = "#E4DAD4"        # rosy stone ground (low chroma)
SURFACE = "#D7CBC4"   # one step from ground
INK = "#2A2628"
MUTED = "#776B67"
ACCENT = "#1F7A80"    # deep teal: the open door, the satisfying literal, cut ends
FACE_TOP = "#F3ECE8"  # three tone steps of one hue for every block
FACE_L = "#CBB8AE"
FACE_R = "#A78E84"
PLATE_ON = "#3B3437"  # pressed plate (variable = 真)

ANCHOR_X = -6.3
F_TITLE = "Hiragino Sans GB"   # W3: thin, clean contours (PingFang's 是 shows a blend artifact at display size)
F_TEXT = "PingFang SC"


def block(x, y, z, w, d, h, s, o, top=FACE_TOP, l=FACE_L, r=FACE_R):
    return iso_block(x, y, z, w, d, h, top, l, r, s=s, origin=o)


def caption(s):
    return T(s, F_TEXT, 30, INK, LIGHT).move_to([0, -3.45, 0]).align_to([ANCHOR_X, 0, 0], LEFT)


class A1_Monument_Title(Scene):
    default_camera_config = dict(background_color=BG)

    def construct(self):
        num = T(EP1_NUM, F_TITLE, 34, MUTED, LIGHT)
        title = T(EP1_TITLE, F_TITLE, 150, INK, ULTRALIGHT)
        sub = T(EP1_SUB, F_TITLE, 32, INK, LIGHT)
        head = VGroup(num, title, sub).arrange(DOWN, aligned_edge=LEFT, buff=0.32)
        head[2].shift(0.1 * DOWN)
        head.move_to([0, 1.55, 0]).align_to([ANCHOR_X, 0, 0], LEFT)

        lits = [lit_tex(l) for l in CLAUSE]
        clause = M(r"(\," + r" \lor ".join(lits) + r"\,)", 84, INK, isolate=lits)
        clause.select_part(lits[SAT_LIT]).set_fill(ACCENT)
        clause.move_to([0, -1.55, 0]).align_to([ANCHOR_X, 0, 0], LEFT)

        # isometric world: base, three stepped pillars with pressure plates, a gate
        s, o = 0.64, np.array([1.75, -3.05, 0])
        layers = [block(0, 0, 0, 8.6, 2.0, 0.5, s, o)]                       # base slab
        gate = block(7.0, 0.1, 0.5, 1.4, 1.8, 4.1, s, o)
        arch = [iso(7.0, 1.0 - 0.42 * np.cos(t), 2.0 + 0.42 * np.sin(t), s, o) for t in np.linspace(0, np.pi, 24)]
        door = Polygon(iso(7.0, 0.58, 0.5, s, o), *arch, iso(7.0, 1.42, 0.5, s, o),
                       fill_color=ACCENT, fill_opacity=1, stroke_width=0)
        layers += [gate, door]
        heights = [1.5, 2.35, 3.2]
        for k in reversed(range(3)):                                         # back to front
            h, x0 = heights[k], 0.55 + 2.15 * k
            on = ASSIGN[k + 1]
            pillar = block(x0, 0.4, 0.5, 1.2, 1.2, h, s, o)
            col = ACCENT if k == SAT_LIT else (PLATE_ON if on else FACE_TOP)
            ph = 0.05 if on else 0.22
            plate = block(x0 + 0.25, 0.65, 0.5 + h, 0.7, 0.7, ph, s, o,
                          top=col, l=col if on else FACE_L, r=col if on else FACE_R)
            # engraved on the pillar's right face: name, and its value
            face_c = iso(x0 + 0.6, 0.4, 0.5 + h * 0.5, s, o)
            name = M(r"x_{%d}" % (k + 1), 40, FACE_TOP)
            val = T("真" if on else "假", F_TEXT, 26, FACE_TOP, NORMAL)
            eng = VGroup(name, val).arrange(DOWN, buff=0.08).move_to(face_c)
            layers += [pillar, plate, eng]
        stack(self, *layers, head, clause, caption(EP1_CAPTION))


class A2_Monument_Cut(Scene):
    default_camera_config = dict(background_color=BG)

    def construct(self):
        num = T(EP5_NUM, F_TITLE, 34, MUTED, LIGHT)
        title = T(EP5_TITLE, F_TITLE, 120, INK, ULTRALIGHT)
        head = VGroup(num, title).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        head.move_to([0, 2.55, 0]).align_to([ANCHOR_X, 0, 0], LEFT)

        s, o = 0.6, np.array([1.0, -3.0, 0])
        W, D, H, CX, SHIFT, DROP = 9.0, 5.0, 0.45, 3.6, 1.7, -0.6
        pos = {"E1": (1.1, 1.0), "E2": (1.7, 3.8), "E3": (5.4, 4.0), "E4": (5.0, 1.0), "E5": (7.8, 2.4)}

        def P(x, y, z=H):
            right = x > CX + 1e-6
            return iso(x + (SHIFT if right else 0), y, z + (DROP if right else 0), s, o)

        right_slab = iso_block(CX + SHIFT, 0, DROP, W - CX, D, H, FACE_TOP, FACE_L, FACE_R, s=s, origin=o)
        left_slab = iso_block(0, 0, 0, CX, D, H, FACE_TOP, FACE_L, FACE_R, s=s, origin=o)
        edges, ends, bits = VGroup(), VGroup(), VGroup()
        for u, v, b, _ in EDGES:
            (x1, y1), (x2, y2) = pos[u], pos[v]
            wid = 0.06 if b == 1 else 0.11
            if crosses(u, v):
                t = (CX - x1) / (x2 - x1)
                ym = y1 + t * (y2 - y1)
                for a, c in (((x1, y1), (CX - 1e-3, ym)), ((CX + 1e-3, ym), (x2, y2))):
                    edges.add(bar(P(*a), P(*c), wid, INK))
                for pt in (P(CX - 1e-3, ym), P(CX + 1e-3, ym)):
                    ends.add(Circle(radius=0.085, fill_color=ACCENT, fill_opacity=1, stroke_width=0).move_to(pt))
            else:
                edges.add(bar(P(x1, y1), P(x2, y2), wid, INK))
                bits.add(T(str(b), "Avenir Next", 26, MUTED, MEDIUM).move_to(label_pos(P(x1, y1), P(x2, y2), 0.24)))
        blocks, nlabels = [], VGroup()
        for n in sorted(NODES, key=lambda n: -(pos[n][0] + pos[n][1])):   # back to front
            x, y = pos[n]
            right = x > CX
            blocks.append(iso_block(x - 0.35 + (SHIFT if right else 0), y - 0.35, H + (DROP if right else 0),
                                    0.7, 0.7, 0.5, FACE_TOP, FACE_L, FACE_R, s=s, origin=o))
            nlabels.add(M("E_{%s}" % n[1], 30, INK).move_to(P(x, y, H + 0.5)))
        # left of the world: the number that matters
        big = T("3", "Avenir Next", 220, INK, ULTRALIGHT)
        unit = T("个比特跨过切口", F_TEXT, 34, INK, LIGHT)
        calc = M(r"2^3 = 8", 54, INK)
        calc_l = T("外层枚举", F_TEXT, 30, MUTED, LIGHT)
        side = VGroup(big, unit, VGroup(calc_l, calc).arrange(RIGHT, buff=0.25)).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        side.move_to([0, -0.55, 0]).align_to([ANCHOR_X, 0, 0], LEFT)
        stack(self, right_slab, left_slab, edges, ends, bits, *blocks, nlabels, head, side, caption(EP5_CAPTION))
