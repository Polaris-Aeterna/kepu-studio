"""Shared helpers + content for the style concept frames (not a style itself)."""
import sys
from pathlib import Path

import numpy as np
from manimlib import *  # noqa: F401,F403

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ---------------------------------------------------------------- content (same in every direction)
EP1_NUM = "第 1 期"
EP1_TITLE = "SAT 是什么"
EP1_SUB = "一个被 800 篇论文当作地基的假说，倒了"
EP1_CAPTION = "一个子句里，只要有一个文字为真，它就被满足。"
CLAUSE = [1, -2, 3]
ASSIGN = {1: False, 2: True, 3: True}      # x1 假, x2 真, x3 真  -> only x3 satisfies the clause
SAT_LIT = 2                                 # index of the satisfying literal (x3)

EP5_NUM = "第 5 期"
EP5_TITLE = "切开扩张图"
EP5_CAPTION = "切口上只有 3 个比特：外层只需枚举 2³ = 8 种。"
# A 文图 1：5 个子句、7 个变量、8 个边比特
NODES = ["E1", "E2", "E3", "E4", "E5"]
EDGES = [  # (u, v, bits, shared vars)
    ("E1", "E2", 2, "x_1,x_3"),
    ("E2", "E3", 1, "x_1"),
    ("E1", "E4", 1, "x_2"),
    ("E3", "E4", 1, "x_5"),
    ("E3", "E5", 1, "x_6"),
    ("E2", "E5", 1, "x_4"),
    ("E4", "E5", 1, "x_7"),
]
LEFT_SIDE = {"E1", "E2"}                     # cut {E1,E2} | {E3,E4,E5}: crosses E2-E3, E1-E4, E2-E5 = 3 bits


def crosses(u, v):
    return (u in LEFT_SIDE) != (v in LEFT_SIDE)


def lit_tex(l):
    return (r"\neg x_{%d}" % -l) if l < 0 else (r"x_{%d}" % l)


def lit_value(l):
    v = ASSIGN[abs(l)]
    return v if l > 0 else not v


# ---------------------------------------------------------------- type & shapes
def clean_glyphs(text_mob, font_size=None, grow=1.35, reach=0.85):
    """ManimGL 1.7.2 + CJK fonts: a glyph path sometimes contains stray points (from a hairline across the
    frame to small slashes inside a character, plus a broken bounding box). A glyph whose size exceeds
    `grow` x the median glyph size gets every point farther than `reach` x median size from its median
    point snapped onto the nearest good point."""
    glyphs = [g for g in text_mob.submobjects if g.has_points()]
    if not glyphs:
        return text_mob
    if font_size:
        ref = 0.0094 * font_size          # measured em box of a CJK glyph (font_size 100 -> 0.94)
    else:
        sizes = sorted(max(g.get_width(), g.get_height()) for g in glyphs)
        ref = max(sizes[len(sizes) // 2], 1e-3)
    for g in glyphs:
        if max(g.get_width(), g.get_height()) <= grow * ref:
            continue
        pts = g.get_points().copy()
        med = np.median(pts, axis=0)
        far = np.linalg.norm(pts - med, axis=1) > reach * ref
        good = np.where(~far)[0]
        if len(good) == 0:
            continue
        for i in np.where(far)[0]:
            pts[i] = pts[good[np.argmin(np.abs(good - i))]]
        g.set_points(pts)
    return text_mob


def T(s, font="PingFang SC", size=36, color=WHITE, weight=NORMAL, **kw):
    kw.setdefault("alignment", "LEFT")
    t = Text(s, font=font, font_size=size, weight=weight, fill_color=color, **kw)
    clean_glyphs(t, size)
    t.center()
    return t


def M(s, size=48, color=WHITE, **kw):
    return Tex(s, font_size=size, fill_color=color, **kw)


def box(w, h, color, corner=0.0):
    if corner:
        return RoundedRectangle(width=w, height=h, corner_radius=corner, fill_color=color, fill_opacity=1,
                                stroke_width=0)
    return Rectangle(width=w, height=h, fill_color=color, fill_opacity=1, stroke_width=0)


def poly(points, color, opacity=1.0):
    return Polygon(*[np.array([*p[:2], 0]) if len(p) == 2 else np.array(p) for p in points],
                   fill_color=color, fill_opacity=opacity, stroke_width=0)


def bar(p, q, width, color):
    """A thick straight 'stroke' drawn as a filled quad (fill renders in add-order, unlike strokes)."""
    p, q = np.array([*p[:2], 0.0]), np.array([*q[:2], 0.0])
    d = q - p
    n = np.array([-d[1], d[0], 0.0]) / (np.linalg.norm(d) + 1e-9) * width / 2
    return Polygon(p + n, q + n, q - n, p - n, fill_color=color, fill_opacity=1, stroke_width=0)


def rounded_path(points, radius=0.35, color=WHITE, width=12):
    """Open polyline with rounded corners (metro-map style)."""
    pts = [np.array([*p[:2], 0.0]) for p in points]
    vm = VMobject()
    vm.start_new_path(pts[0])
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        r = min(radius, np.linalg.norm(b - a) / 2, np.linalg.norm(c - b) / 2)
        p1 = b + (a - b) / np.linalg.norm(a - b) * r
        p2 = b + (c - b) / np.linalg.norm(c - b) * r
        vm.add_line_to(p1)
        vm.add_quadratic_bezier_curve_to(b, p2)
    vm.add_line_to(pts[-1])
    vm.set_stroke(color, width)
    vm.set_fill(opacity=0)
    return vm


# ---------------------------------------------------------------- isometric projection
COS30, SIN30 = np.cos(np.pi / 6), 0.5


def iso(x, y, z, s=1.0, origin=ORIGIN):
    return origin + s * np.array([(x - y) * COS30, (x + y) * SIN30 + z, 0.0])


def iso_block(x, y, z, w, d, h, top, left, right, s=1.0, origin=ORIGIN):
    """Axis-aligned box [x,x+w]x[y,y+d]x[z,z+h]; visible faces: top, front-left (y=y0... ) and front-right."""
    P = lambda a, b, c: iso(a, b, c, s, origin)
    top_f = Polygon(P(x, y, z + h), P(x + w, y, z + h), P(x + w, y + d, z + h), P(x, y + d, z + h))
    # viewer looks from -x,-y: faces at x=x (left) and y=y (right) are visible
    left_f = Polygon(P(x, y, z), P(x, y + d, z), P(x, y + d, z + h), P(x, y, z + h))
    right_f = Polygon(P(x, y, z), P(x + w, y, z), P(x + w, y, z + h), P(x, y, z + h))
    for f, c in ((top_f, top), (left_f, left), (right_f, right)):
        f.set_fill(c, 1).set_stroke(width=0)
    return VGroup(left_f, right_f, top_f)


def save_name(scene_cls_name):
    return scene_cls_name

# Pango weight names (manimlib only exports NORMAL/BOLD)
ULTRALIGHT, LIGHT, MEDIUM, SEMIBOLD, HEAVY = "ULTRALIGHT", "LIGHT", "MEDIUM", "SEMIBOLD", "HEAVY"


def _leaves(m):
    from manimlib.mobject.svg.string_mobject import StringMobject
    if isinstance(m, StringMobject) or not m.submobjects:
        return [m]
    out = [m] if m.has_points() else []
    for sm in m.submobjects:
        out.extend(_leaves(sm))
    return out


def stack(scene, *mobs):
    """Add mobjects back-to-front with distinct z_index, flattened to leaves (Text/Tex stay whole).
    ManimGL batches same-type top-level mobjects into one draw and blends overlapping fills inside a
    batch; one z_index per leaf gives true painter's-order occlusion."""
    flat = []
    for m in mobs:
        for mm in (m if isinstance(m, (list, tuple)) else [m]):
            flat.extend(_leaves(mm))
    for i, m in enumerate(flat):
        m.z_index = i
    scene.add(*flat)


def label_pos(p, q, off=0.26):
    """Point beside the middle of segment p-q, offset along the upward normal."""
    p, q = np.array(p), np.array(q)
    d = q - p
    n = np.array([-d[1], d[0], 0.0])
    n = n / (np.linalg.norm(n) + 1e-9)
    if n[1] < 0:
        n = -n
    return (p + q) / 2 + off * n
