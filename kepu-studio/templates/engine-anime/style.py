"""
EVA house style for the ETH series (ManimGL 1.7.2).  Read engine/README.md first.

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "engine"))
    from style import *          # re-exports `from manimlib import *`
    from narrated import NarratedScene

Frame 14.22 x 8 units (1920x1080).  Content lives in the SAFE box
x in [-6.4, 6.4], y in [-2.75, 3.5]; the strip below y = -2.75 belongs to the subtitle.
"""
from __future__ import annotations

import re
import warnings

import numpy as np
from manimlib import *  # noqa: F401,F403
from manimlib.mobject.svg.string_mobject import StringMobject
from manimlib.scene.scene import EndScene

# =====================================================================
# 0. Engine fixes (applied on import)
# =====================================================================


def _validate_markup_string(markup: str):
    import manimpango
    err = manimpango.MarkupUtils.validate(markup)
    if err:
        raise ValueError(f"Invalid markup string {markup!r}\n{err}")


if not hasattr(MarkupText, "validate_markup_string"):            # 1.7.2 bug
    MarkupText.validate_markup_string = staticmethod(_validate_markup_string)


def _render_leaves(m):
    """Units the renderer may batch: StringMobjects whole, otherwise leaf VMobjects."""
    if isinstance(m, StringMobject) or not m.submobjects or m.has_points():
        return [m]
    out = []
    for sm in m.submobjects:
        out.extend(_render_leaves(sm))
    return out


_LEGACY_KW = ("color_clauses", "show_box", "color", "node_color", "edge_color", "edge_width", "event_color",
              "label_size_legacy")


def _drop_legacy(kwargs):
    """Old (pre-EVA) component kwargs are accepted and ignored so old code keeps running."""
    for k in _LEGACY_KW:
        kwargs.pop(k, None)
    return kwargs


def _bbox(m):
    return (*m.get_corner(DL)[:2], *m.get_corner(UR)[:2])


def _assemble_render_groups(self):
    """
    Replacement for Scene.assemble_render_groups.  ManimGL computes fill winding with alpha blending
    over a whole batch, so two overlapping fills in one batch blend instead of occluding
    (light-on-dark turns grey, a glyph on a filled box disappears).  Here every leaf is batched with its
    predecessors only while it overlaps none of them; an overlap starts a new batch, so later leaves
    are painted over earlier ones (painter's order = scene order, then family order).
    """
    leaves = []
    for m in self.mobjects:
        leaves.extend(_render_leaves(m))
    batches, cur, boxes, key = [], [], [], None
    for leaf in leaves:
        if not leaf.has_points() and not leaf.submobjects:
            continue
        k = (leaf.get_group_class(), leaf.get_shader_wrapper(self.camera.ctx).get_id(), leaf.z_index)
        b = np.array(_bbox(leaf))
        hit = False
        if cur and k == key and boxes:
            arr = np.array(boxes)
            hit = bool(np.any((arr[:, 0] < b[2]) & (b[0] < arr[:, 2]) & (arr[:, 1] < b[3]) & (b[1] < arr[:, 3])))
        if cur and (k != key or hit):
            batches.append(cur)
            cur, boxes = [], []
        cur.append(leaf)
        boxes.append(b)
        key = k
    if cur:
        batches.append(cur)
    for group in self.render_groups:
        group.clear()
    self.render_groups = [batch[0].get_group_class()(*batch) for batch in batches]


def _family_signature(scene):
    return hash(tuple(id(sm) for m in scene.mobjects for sm in m.get_family()))


def _update_frame(self, dt: float = 0, force_draw: bool = False) -> None:
    """Scene.update_frame + re-batching whenever a family changed (subtitle swap, Transform alignment)
    or every 10 frames (things that moved into overlap)."""
    self.increment_time(dt)
    self.update_mobjects(dt)
    if self.skip_animations and not force_draw:
        return
    if self.is_window_closing():
        raise EndScene()
    if self.window and dt == 0 and not self.window.has_undrawn_event() and not force_draw:
        self.window._window.dispatch_events()
        return
    self._rg_tick = getattr(self, "_rg_tick", 0) + 1
    sig = _family_signature(self)
    if sig != getattr(self, "_rg_sig", None) or self._rg_tick % 10 == 0:
        self._rg_sig = sig
        _assemble_render_groups(self)
    self.camera.capture(*self.render_groups)
    if self.window and not self.skip_animations:
        import time as _time
        vt = self.time - self.virtual_animation_start_time
        rt = _time.time() - self.real_animation_start_time
        _time.sleep(max(vt - rt, 0))


Scene.assemble_render_groups = _assemble_render_groups
Scene.update_frame = _update_frame

# =====================================================================
# 1. Palette (roles).  Red is a judgement, never a decoration.
# =====================================================================
BG = "#0A0A0A"          # the ground: near-black, not #000
SURFACE = "#171717"     # one tone step: panels, cells, cards
SURFACE_2 = "#232323"   # second step (rare): cells inside a panel
INK = "#ECEAE4"         # main ink: warm white, not #fff
INK_2 = "#8D8A84"       # secondary ink: captions, inactive values (>= 4.5:1 on BG)
DIM = "#3C3B39"         # switched-off things: false literals, inactive edges, axes
RED = "#D8361F"         # the judgement: one thing per screen, small area
PAPER = "#E9E6DE"       # inverse ground (insert cards, paper segments)
PAPER_INK = "#0A0A0A"

# legacy aliases (old engine names) -> EVA roles
BG_COLOR, PANEL_COLOR, GRID_COLOR = BG, SURFACE, DIM
TEXT_COLOR, MUTED_COLOR, DIM_COLOR = INK, INK_2, DIM
TRUE_COLOR, FALSE_COLOR, UNKNOWN_COLOR = INK, DIM, INK_2
VAR_COLOR, NEG_COLOR, OP_COLOR = INK, INK, INK_2
ACCENT, ACCENT_2, ACCENT_3 = RED, INK, INK_2
ANTHROPIC_COLOR = OPENAI_COLOR = INK

# =====================================================================
# 2. Type
# =====================================================================
ZH_DISPLAY = "Songti SC"    # weight HEAVY, squashed horizontally -> the EVA title face
ZH_TEXT = "Songti SC"       # body + subtitles (NORMAL / BOLD)
LATIN = "Baskerville"       # small English lines on title cards
ZH_FONT = ZH_TEXT
SQUASH = 0.74               # horizontal compression of display type
BANNED_FONTS = {"Noto Sans CJK SC": "broken glyph paths (跨…)", "Noto Serif CJK SC": "broken glyph paths (隧 过…)"}

LIGHT, MEDIUM, SEMIBOLD, HEAVY = "LIGHT", "MEDIUM", "SEMIBOLD", "HEAVY"

# Language (README §11).  Every component reads its faces from here at call time; set_lang("en") switches them
# for an English episode (normally via `from style_en import *`).  "zh" is the default and is exactly the
# pre-English behaviour.
#   en display: Times New Roman Bold squashed to 0.78 — the Latin glyphs inside Songti are Times-like, so the
#   English cards look like the Latin already on the Chinese cards (ETH, 2026, 800+); full Latin-1 + math
#   symbols (ö á é ≤ × − ² ¬ ⊕ →) verified in ManimGL Text.  Body / subtitles: Times New Roman Regular / Bold.
FACES = {
    "zh": dict(display=ZH_DISPLAY, text=ZH_TEXT, latin="Baskerville", squash=0.74, display_weight=HEAVY),
    "en": dict(display="Times New Roman", text="Times New Roman", latin="Times New Roman", squash=0.78,
               display_weight="BOLD"),
}
LANG = "zh"
DISPLAY_FONT, TEXT_FONT = ZH_DISPLAY, ZH_TEXT
UI = {   # the few words components write by themselves
    "zh": dict(next="下一期", time="时间", true="真", false="假"),
    "en": dict(next="Next episode", time="time", true="T", false="F"),
}


def set_lang(lang: str = "zh"):
    """Switch every component to the faces / words of `lang` ("zh" | "en").  Module globals LANG, DISPLAY_FONT,
    TEXT_FONT, LATIN and SQUASH follow; re-import them (`from style_en import *` does this) after switching."""
    global LANG, DISPLAY_FONT, TEXT_FONT, LATIN, SQUASH
    f = FACES[lang]
    LANG, DISPLAY_FONT, TEXT_FONT, LATIN, SQUASH = lang, f["display"], f["text"], f["latin"], f["squash"]
    return lang

SIZE_XL = 280        # one-word title moment
SIZE_L = 200         # big card line
SIZE_M = 132         # big card secondary line / chapter title
SIZE_H1 = 72         # content heading (display face)
SIZE_BODY = 34       # body text in content moments
SIZE_SMALL = 28      # labels, captions
SIZE_TINY = 22       # axis numbers
SIZE_SUB = 32        # subtitles
SIZE_FORMULA = 52    # default formula
# legacy names
SIZE_TITLE, SIZE_H2 = SIZE_M, 48

ANCHOR_X = -6.4      # the one left edge for text
RIGHT_X = 6.4
SAFE_TOP, SAFE_BOTTOM = 3.5, -2.75
HEADING_Y = 3.05
SUBTITLE_Y = -3.42
SAFE_X = 6.4

ZH_TEX_PREAMBLE = r"""
\usepackage[UTF8,fontset=none]{ctex}
\setCJKmainfont{Songti SC}
\setCJKsansfont{Songti SC}
\usepackage{amsmath}
\usepackage{amssymb}
"""

# easing (see README §6) ------------------------------------------------
EASE_OUT = lambda t: 1 - (1 - t) ** 5                                   # noqa: E731  entrances
EASE_EXPO = lambda t: 1.0 if t >= 1 else 1 - 2 ** (-10 * t)              # noqa: E731  long reveals, sweeps
EASE_INOUT = lambda t: 8 * t ** 4 if t < 0.5 else 1 - (-2 * t + 2) ** 4 / 2  # noqa: E731  moves between places
EASE_EXIT = lambda t: t ** 3                                             # noqa: E731  leaving for good


def clean_glyphs(text_mob, font_size=None, grow=1.35, reach=0.85):
    """ManimGL 1.7.2: some glyph paths contain stray points (hairline across the frame, slashes inside a
    character, a bounding box thousands of units wide).  Snap them onto their neighbours."""
    glyphs = [g for g in text_mob.submobjects if g.has_points()]
    if not glyphs:
        return text_mob
    if font_size:
        ref = 0.0094 * font_size                 # em box of a CJK glyph (font_size 100 -> 0.94)
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


def _check_font(font, size):
    if font in BANNED_FONTS:
        raise ValueError(f"font {font!r} is banned in this project: {BANNED_FONTS[font]}")
    if font.startswith("PingFang") and size >= 90:
        warnings.warn("PingFang at display size shows a blend scar in 是 — use Display() instead")


def CText(text: str, size: float = SIZE_BODY, color=INK, weight=NORMAL, font: str | None = None, **kwargs) -> Text:
    """Body text (Songti; Times New Roman after set_lang("en")).  weight=BOLD for emphasis.  '\\n' for line breaks.  t2c={'词': RED}.
    Unicode super/subscripts (ʲ ₜ ᵥ ² ₁ …) are typeset automatically as raised/lowered spans (README §10);
    for real formulas prefer Formula()."""
    font = font or TEXT_FONT
    _check_font(font, size)
    kwargs.setdefault("alignment", "LEFT")
    auto = kwargs.pop("auto_scripts", True)
    if auto and has_unicode_scripts(text):
        if text not in _WARNED_SCRIPTS:
            _WARNED_SCRIPTS.add(text)
            warnings.warn(f"CText/Display: Unicode super/subscripts in {text!r} typeset as spans "
                          f"(write ^{{}}/_{{}} via Markup(sup_markup(.., span=True)) or use Formula)")
        t = MarkupText(unicode_scripts_markup(text, size), font=font, font_size=size, weight=weight,
                       fill_color=color, use_labelled_svg=True,
                       path_string_config=dict(use_simple_quadratic_approx=True), **kwargs)
        clean_glyphs(t, size)
        return t
    t = Text(text, font=font, font_size=size, weight=weight, fill_color=color, **kwargs)
    clean_glyphs(t, size)
    return t


def Display(text: str, size: float = SIZE_L, color=INK, squash: float | None = None, weight=None, **kwargs) -> Text:
    """The EVA face: Songti Heavy (en: Times New Roman Bold), compressed horizontally.  Big cards and headings only.
    squash / weight default to the language's face (zh: 0.74 / HEAVY)."""
    f = FACES[LANG]
    t = CText(text, size=size, color=color, weight=weight or f["display_weight"], font=DISPLAY_FONT, **kwargs)
    t.stretch(f["squash"] if squash is None else squash, 0)
    return t


def Latin(text: str, size: float = 30, color=INK, **kwargs) -> Text:
    """Small English line (Baskerville), e.g. 'EPISODE 1   What is SAT?'."""
    kwargs.setdefault("alignment", "LEFT")
    return clean_glyphs(Text(text, font=LATIN, font_size=size, fill_color=color, **kwargs), size)


# Unicode super/subscript characters -> plain characters (used by sup_markup(span=True))
_UNI_SUP = dict(zip("⁰¹²³⁴⁵⁶⁷⁸⁹ⁿⁱʲᵏᶜᵗˣʸᵃᵇᵐᵈᵉᶠᵍʰˡᵒᵖʳˢᵘᵛʷᶻ⁻⁺⁼⁽⁾",
                    "0123456789nijkctxyabmdefghlopr" "suvwz−+=()"))
_UNI_SUB = dict(zip("₀₁₂₃₄₅₆₇₈₉ₙᵢⱼₖₐₑₒₓₘₚₛₜᵤᵥₕₗᵣ₋₊₌₍₎", "0123456789nijkaeoxmpstuvhlr−+=()"))
SPAN_SUP = "<span size='68%' baseline_shift='superscript'>"   # positive rise= is ignored by 1.7.2's Pango path
                                                                # (2026-10-28 test: ʲ/² stayed on the baseline)
SPAN_SUB = "<span size='68%' rise='-4000'>"


def _spans(size=None):
    if not size or abs(size - SIZE_SUB) < 1e-6:
        return SPAN_SUP, SPAN_SUB
    k = size / SIZE_SUB
    return SPAN_SUP, f"<span size='68%' rise='{int(-4000 * k)}'>"


def has_unicode_scripts(text: str) -> bool:
    """True if text contains Unicode super/subscript letters or digits (ʲ ₜ ᵥ ² ₁ …)."""
    return any(c in _UNI_SUP or c in _UNI_SUB for c in text)


def unicode_scripts_markup(text: str, size=None) -> str:
    """Escape text for Pango and typeset runs of Unicode super/subscripts as raised/lowered spans
    (the glyphs themselves fall back to a wide or broken font in 1.7.2)."""
    sup, sub = _spans(size)
    s = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub("[%s]+" % re.escape("".join(_UNI_SUP)), lambda m: sup + "".join(_UNI_SUP[c] for c in m.group()) + "</span>", s)
    s = re.sub("[%s]+" % re.escape("".join(_UNI_SUB)), lambda m: sub + "".join(_UNI_SUB[c] for c in m.group()) + "</span>", s)
    return s


_WARNED_SCRIPTS = set()


def sup_markup(s: str, span: bool = False, size=None) -> str:
    """Plain text -> Pango markup: escapes &<>, ^x / ^{..} -> <sup>, _x / _{..} -> <sub>.

    span=True (used by the subtitles): write each super/subscript as a smaller, raised/lowered
    <span size rise> instead -- 1.7.2 renders <sup>/<sub> almost invisibly small, esp. multi-digit
    ones -- and also typeset runs of Unicode super/subscript characters (2¹⁰⁰, x₁₁₃) that way,
    because those glyphs fall back to a font with wide gaps.  Default (False) is unchanged."""
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    SUP, SUB, END = "\ue000", "\ue001", "\ue002"          # placeholders: attribute names never get re-matched
    s = re.sub(r"\^\{([^{}]*)\}", lambda m: SUP + m.group(1) + END, s)
    s = re.sub(r"\^([\w.]+)", lambda m: SUP + m.group(1) + END, s)
    s = re.sub(r"_\{([^{}]*)\}", lambda m: SUB + m.group(1) + END, s)
    s = re.sub(r"_(\w)", lambda m: SUB + m.group(1) + END, s)
    if span:
        s = re.sub("[%s]+" % re.escape("".join(_UNI_SUP)), lambda m: SUP + "".join(_UNI_SUP[c] for c in m.group()) + END, s)
        s = re.sub("[%s]+" % re.escape("".join(_UNI_SUB)), lambda m: SUB + "".join(_UNI_SUB[c] for c in m.group()) + END, s)
        sp, sb = _spans(size)
        out, stack = [], []
        for ch in s.replace("{", "").replace("}", ""):
            if ch in (SUP, SUB):
                out.append(sp if ch == SUP else sb)
            elif ch == END:
                out.append("</span>")
            else:
                out.append(ch)
        return "".join(out)
    s = s.replace("{", "").replace("}", "")
    out = []
    kinds = []
    for ch in s:
        if ch in (SUP, SUB):
            kinds.append(ch)
            out.append("<sup>" if ch == SUP else "<sub>")
        elif ch == END:
            out.append("</sup>" if kinds.pop() == SUP else "</sub>")
        else:
            out.append(ch)
    return "".join(out)


def Markup(markup: str, size: float = SIZE_BODY, color=INK, font: str | None = None, **kwargs) -> MarkupText:
    """Pango-markup text (<b>, <sup>, <sub>, <span foreground='#..'>).  Works around 1.7.2 bugs."""
    font = font or TEXT_FONT
    _check_font(font, size)
    kwargs.setdefault("alignment", "LEFT")
    kwargs.setdefault("use_labelled_svg", True)
    kwargs.setdefault("path_string_config", dict(use_simple_quadratic_approx=True))
    return clean_glyphs(MarkupText(markup, font=font, font_size=size, fill_color=color, **kwargs), size)


def Formula(tex: str, size: float = SIZE_FORMULA, color=INK, **kwargs) -> Tex:
    """Math (pdflatex, Computer Modern).  t2c={'x_1': RED} colours sub-strings."""
    return Tex(tex, font_size=size, fill_color=color, **kwargs)


def ZhTex(tex: str, size: float = SIZE_FORMULA, color=INK, **kwargs) -> Tex:
    r"""Math with Chinese inside \text{…} (xelatex + ctex + Songti; slower)."""
    return Tex(tex, font_size=size, fill_color=color, template="empty_ctex",
               additional_preamble=ZH_TEX_PREAMBLE, **kwargs)


def ZhTexText(text: str, size: float = SIZE_BODY, color=INK, **kwargs) -> TexText:
    r"""Chinese text with inline $math$: ZhTexText(r"子句 $C_1$ 被满足")."""
    return TexText(text, font_size=size, fill_color=color, template="empty_ctex",
                   additional_preamble=ZH_TEX_PREAMBLE, **kwargs)


def at_anchor(mob, y=None, x=ANCHOR_X):
    """Put mob's left edge on the anchor line (and optionally its centre at height y)."""
    if y is not None:
        mob.set_y(y)
    return mob.align_to(np.array([x, 0, 0]), LEFT)


def block(w, h, color=SURFACE):
    """Flat filled rectangle (no stroke)."""
    return Rectangle(width=w, height=h).set_fill(color, 1).set_stroke(width=0)


def full_frame(color=PAPER):
    return block(FRAME_WIDTH + 0.2, FRAME_HEIGHT + 0.2, color)


# =====================================================================
# 3. Cards
# =====================================================================
def Heading(text: str, size: float = SIZE_H1, color=INK) -> Text:
    """Content-moment heading: display face, top-left on the anchor line.  No underline."""
    return at_anchor(Display(text, size, color), HEADING_Y)


def BigCard(lines, layout: str = "stagger", en: str | None = None, color=INK, ground: str = "black",
            vertical: bool = False, gap: float = 0.0):
    """
    Full-screen title moment (the EVA card).
      lines   : list of str or (str, size) / (str, size, color).  Default sizes: first line SIZE_M, others SIZE_L.
      layout  : "stagger" (left, right, left, …), "left", "right", "center"
      vertical: True -> each line is a column read top-to-bottom, columns right-to-left.
      en      : small English line under the block.
      ground  : "black" or "paper" (paper = ink becomes black; place on scene.set_ground('paper') or InsertCard)
    Returns a VGroup positioned in the frame.
    """
    ink = PAPER_INK if ground == "paper" else color
    specs = []
    for i, ln in enumerate(lines):
        if isinstance(ln, str):
            ln = (ln, SIZE_L if vertical else (SIZE_M if (i == 0 and len(lines) > 1) else SIZE_L))
        s, size = ln[0], ln[1]
        c = ln[2] if len(ln) > 2 else ink
        specs.append((s, size, c))
    if vertical and LANG != "zh":
        vertical = False             # Latin words don't stack in columns: rows instead (same indexing card[0][k])
        layout = "right" if layout == "stagger" else layout
    if vertical:
        cols = VGroup()
        for s, size, c in specs:
            chars = VGroup(*[Display(ch, size, c, squash=0.92) for ch in s if ch.strip()])
            chars.arrange(DOWN, buff=0.06 * size / 100)
            cols.add(chars)
        cols.arrange(LEFT, buff=0.35, aligned_edge=UP)
        if cols.get_height() > 5.9:
            cols.set_height(5.9)
        cols.move_to(ORIGIN).align_to(np.array([0, SAFE_TOP - 0.1, 0]), UP)       # stays above the subtitle strip
        group = VGroup(cols)
        if en:
            group.add(Latin(en, 28, ink).next_to(cols, DOWN, buff=0.25).align_to(cols, RIGHT))
        return group
    rows = VGroup(*[Display(s, size, c) for s, size, c in specs])
    if LANG != "zh":
        for r in rows:
            if r.get_width() > 2 * SAFE_X:
                r.set_width(2 * SAFE_X)
    rows.arrange(DOWN, buff=gap, aligned_edge=LEFT)
    for i, r in enumerate(rows):
        if layout == "center":
            r.set_x(0)
        elif layout == "right" or (layout == "stagger" and i % 2 == 1):
            r.align_to(np.array([RIGHT_X, 0, 0]), RIGHT)
        else:
            r.align_to(np.array([ANCHOR_X, 0, 0]), LEFT)
    group = VGroup(rows)
    if en:
        last = rows[-1]
        e = Latin(en, 30, ink).next_to(last, DOWN, buff=0.25)
        e.align_to(last, RIGHT if (layout == "right" or (layout == "stagger" and (len(rows) - 1) % 2 == 1)) else LEFT)
        group.add(e)
    if group.get_height() > 7.3:
        group.set_height(7.3)
    group.set_y(0.15)
    return group


def TitleCard(title: str, subtitle: str | None = None, en: str | None = None, color=INK):
    """Single-title big card: title at SIZE_L, optional subtitle line under it."""
    lines = [(title, SIZE_L)] + ([(subtitle, SIZE_M)] if subtitle else [])
    return BigCard(lines, layout="stagger", en=en, color=color)


# The series table: the ONE place where episode titles live (ChapterCard / NextEpisodeCard read it).
# kepu: it lives in engine/episodes.json so a new series never edits this file:
#   {"zh": {"1": {"title": "SAT 是什么", "en": "What is SAT?"}}, "en": {"1": {"title": "What is SAT?", "sub": null}}}
def _load_episodes():
    import json as _json
    from pathlib import Path as _Path
    p = _Path(__file__).with_name("episodes.json")
    if not p.exists():
        return {}, {}
    d = _json.loads(p.read_text(encoding="utf-8"))
    return ({int(k): v for k, v in d.get("zh", {}).items()}, {int(k): v for k, v in d.get("en", {}).items()})


EPISODES, EPISODES_EN = _load_episodes()


def episode_en(n: int) -> str:
    return f"EPISODE {n}    {EPISODES[n]['en']}"


def ChapterCard(number, title: str | None = None, en: str | None = None, color=INK):
    """'第一期' + title, staggered (episode opener).  ChapterCard(3) takes title and English line from EPISODES."""
    if LANG != "zh":
        e = EPISODES_EN.get(number, {}) if isinstance(number, int) else {}
        title = title or e.get("title", "")
        en = en if en is not None else e.get("sub")
        num = f"Episode {number}" if isinstance(number, int) else str(number)
        return BigCard([(num, SIZE_M), (title, SIZE_L)], layout="stagger", en=en, color=color)
    zh = "零一二三四五六七八九十"
    if isinstance(number, int) and number in EPISODES:
        title = title or EPISODES[number]["title"]
        en = en if en is not None else episode_en(number)
    num = f"第{zh[number]}期" if isinstance(number, int) and 0 <= number <= 10 else str(number)
    return BigCard([(num, SIZE_M), (title, 240)], layout="stagger", en=en, color=color)


def NextEpisodeCard(number: int, color=INK):
    """End-of-episode teaser: exactly the next episode's ChapterCard (same title and English line, from
    EPISODES) with a small '下一期' above it.  Show with scene.next_episode(n) (not counted as a big moment)."""
    card = ChapterCard(number, color=color)
    tag = CText(UI[LANG]["next"], SIZE_BODY, INK_2)
    tag.next_to(card, UP, buff=0.35)
    at_anchor(tag)
    return VGroup(tag, card)


def InsertCard(lines, ground: str = "paper", size: float = SIZE_M, en: str | None = None):
    """
    The inverse insert frame (EVA's black/white text frames).  Full-frame ground + centred display text.
    Show it with scene.insert(card, hold) — a hard cut in and out, 0.6–1.5 s.
    """
    bg = PAPER if ground == "paper" else BG
    ink = PAPER_INK if ground == "paper" else INK
    if isinstance(lines, str):
        lines = [lines]
    text = VGroup(*[Display(s, size, ink) for s in lines]).arrange(DOWN, buff=0.05)
    if text.get_width() > 12.4:
        text.set_width(12.4)
    g = VGroup(full_frame(bg), text.move_to(ORIGIN))
    if en:
        g.add(Latin(en, 28, ink).next_to(text, DOWN, buff=0.3))
    return g


def Panel(content: Mobject, buff: float = 0.35, color=SURFACE) -> VGroup:
    """A filled surface block behind content (tone step, no frame)."""
    b = block(content.get_width() + 2 * buff, content.get_height() + 2 * buff, color).move_to(content)
    return VGroup(b, content)


def PaperCard(title: str, org: str, extra: str = "", width: float = 5.8) -> VGroup:
    """Citing a paper: org (Songti bold), title (Baskerville, ^{} -> superscript), extra (secondary ink)."""
    o = CText(org, SIZE_SMALL, INK_2, BOLD)
    t = Markup(sup_markup(title), size=32, font=LATIN)
    if t.get_width() > width - 0.7:
        t.set_width(width - 0.7)
    parts = [o, t] + ([CText(extra, SIZE_SMALL - 4, INK_2)] if extra else [])
    inner = VGroup(*parts).arrange(DOWN, aligned_edge=LEFT, buff=0.22)
    b = block(width, inner.get_height() + 0.75, SURFACE)
    inner.move_to(b).align_to(b.get_left() + RIGHT * 0.35, LEFT)
    return VGroup(b, inner)


# =====================================================================
# 4. Marks & highlights (no glow, no thin frames)
# =====================================================================
def Mark(mob: Mobject, color=RED, buff: float = 0.1, height: float = 0.06) -> Rectangle:
    """A short thick bar under mob — the standard way to point at something."""
    b = block(mob.get_width(), height, color)
    return b.next_to(mob, DOWN, buff=buff)


def Underline(mob: Mobject, color=RED, buff: float = 0.1) -> Rectangle:
    return Mark(mob, color, buff)


def InvertTag(text: str, size: float = SIZE_BODY, pad=(0.22, 0.12), color=INK, ink=BG, weight=BOLD) -> VGroup:
    """Ink block with ground-coloured text (the inverse tag)."""
    t = CText(text, size, ink, weight)
    b = block(t.get_width() + 2 * pad[0], t.get_height() + 2 * pad[1], color).move_to(t)
    return VGroup(b, t)


def HighlightBox(mob: Mobject, color=RED, buff: float = 0.14, width: float = 6) -> Rectangle:
    """A 6-px frame (rare: at most one per screen; prefer Mark)."""
    r = Rectangle(width=mob.get_width() + 2 * buff, height=mob.get_height() + 2 * buff)
    return r.set_stroke(color, width).set_fill(opacity=0).move_to(mob)


def highlight_part(tex_mob: Tex, part: str, color=RED) -> Animation:
    """Recolour a sub-string of a Tex/Text."""
    return tex_mob.select_parts(part).animate.set_fill(color)


def mark_anim(mark: Mobject, run_time: float = 0.35) -> Animation:
    """Grow a Mark from its left end (expo)."""
    return GrowFromEdge(mark, LEFT, run_time=run_time, rate_func=EASE_EXPO)


flash_around = lambda mob, color=RED: mark_anim(Mark(mob, color))  # noqa: E731  (legacy)


def rise_in(mob: Mobject, dist: float = 0.22, run_time: float = 0.6) -> Animation:
    """The quiet entrance: rise + fade, quint-out.  Use for content, never for big cards (those cut)."""
    return FadeIn(mob, shift=UP * dist, run_time=run_time, rate_func=EASE_OUT)


def rise_lines(mobs, dist: float = 0.22, run_time: float = 0.9, lag: float = 0.12) -> Animation:
    """Lines/items arriving in reading order (stagger <= 4 steps look best)."""
    return LaggedStart(*[FadeIn(m, shift=UP * dist, rate_func=EASE_OUT) for m in mobs], lag_ratio=lag,
                       run_time=run_time)


# =====================================================================
# 5. Judgement line & cuts
# =====================================================================
def JudgeLine(start, end, color=RED, width: float = 10) -> Line:
    """The red judgement line (a thick stroke).  Animate with judge_sweep()."""
    return Line(np.array([*start[:2], 0.0]), np.array([*end[:2], 0.0])).set_stroke(color, width)


def judge_sweep(line: Line, run_time: float = 0.45) -> Animation:
    """Draw the judgement line from its start, expo-out: the series' signature stroke."""
    return ShowCreation(line, run_time=run_time, rate_func=EASE_EXPO)


def cut_apart(left: Mobject, right: Mobject, line: Line, gap: float = 0.35, run_time: float = 0.6) -> Animation:
    """After a sweep: push the two sides apart perpendicular to the line (in-out)."""
    d = line.get_end() - line.get_start()
    n = normalize(np.array([d[1], -d[0], 0]))
    if np.dot(right.get_center() - line.get_center(), n) < 0:
        n = -n
    return AnimationGroup(left.animate.shift(-n * gap / 2), right.animate.shift(n * gap / 2),
                          run_time=run_time, rate_func=EASE_INOUT)


# =====================================================================
# 6. Boolean variables, clauses, CNF
# =====================================================================
def var_tex(i, names=None) -> str:
    if names is not None:
        return names(i) if callable(names) else names[i]
    return f"x_{{{i}}}"


def lit_tex(lit: int, names=None) -> str:
    """DIMACS literal: 3 -> x_{3}, -3 -> \\neg x_{3}."""
    v = var_tex(abs(lit), names)
    return (r"\neg " + v) if lit < 0 else v


class BoolVar(VGroup):
    """
    A variable cell.  True = inverted cell (ink block, ground numeral); False = surface cell, secondary ink;
    None = '?'.
        v = BoolVar(1, value=None, caption="小一")
        self.play(v.animate_set(True))      # flips (0.35 s, quint-out)
    style="01" shows 1/0 (default), style="TF" shows 真/假.
    """

    def __init__(self, name=1, value=None, size: float = 1.0, caption: str | None = None, style: str = "01",
                 show_name: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.size, self.style, self.value = size, style, value
        self.cell = block(size, size, SURFACE)
        self.glyph = self._glyph(value)
        self.add(self.cell, self.glyph)
        below = []
        if show_name:
            self.name = Formula(var_tex(name) if isinstance(name, int) else name, 40 * size, INK)
            below.append(self.name)
        if caption:
            self.caption = CText(caption, 28 * size, INK_2)
            below.append(self.caption)
        if below:
            VGroup(*below).arrange(DOWN, buff=0.1).next_to(self.cell, DOWN, buff=0.18)
            self.add(*below)
        self._style(value)

    def _glyph(self, value):
        if value is None:
            s = "?"
        elif self.style == "TF":
            s = UI[LANG]["true"] if value else UI[LANG]["false"]
        else:
            s = "1" if value else "0"
        g = Display(s, 64 * self.size, squash=0.9)
        return g.move_to(self.cell)

    def _style(self, value):
        if value:
            self.cell.set_fill(INK, 1)
            self.glyph.set_fill(BG)
        else:
            self.cell.set_fill(SURFACE, 1)
            self.glyph.set_fill(INK_2)

    def set_value(self, value):
        self.glyph.become(self._glyph(value))
        self.value = value
        self._style(value)
        return self

    def animate_set(self, value, run_time: float = 0.35) -> Animation:
        target = self.copy().set_value(value)
        self.value = value
        return Transform(self, target, run_time=run_time, rate_func=EASE_OUT)


class Clause(VGroup):
    """
    (x_1 ∨ ¬x_2 ∨ x_3) from DIMACS ints.
        c = Clause([1, -2, 3]);  c.literal(k);  c.is_satisfied(assign)
        self.play(*c.evaluate_anims(assign))   # true literals ink, false literals dim, red bar if violated
    """

    def __init__(self, lits, names=None, size: float = SIZE_FORMULA, parens: bool = True, spaced: bool = False,
                 **kwargs):
        """spaced=True keeps TeX's binary-operator spacing around ∨ (isolating `\\lor` otherwise removes it)."""
        super().__init__(**_drop_legacy(kwargs))
        self.lits = list(lits)
        self.lit_strs = [lit_tex(l, names) for l in self.lits]
        body = (r" \mathbin{\lor} " if spaced else r" \lor ").join(self.lit_strs)
        self.tex = Formula(rf"\left( {body} \right)" if parens else body, size, INK,
                           isolate=self.lit_strs + [r"\lor"])
        self.add(self.tex)
        self.bar = Mark(self.tex, DIM, buff=0.12).set_opacity(0)
        self.add(self.bar)

    def literal(self, k: int) -> VMobject:
        return self.tex.select_part(self.lit_strs[k])

    def lit_value(self, k, assignment):
        v = assignment.get(abs(self.lits[k]))
        return None if v is None else (v if self.lits[k] > 0 else not v)

    def is_satisfied(self, assignment):
        vals = [self.lit_value(k, assignment) for k in range(len(self.lits))]
        if any(v is True for v in vals):
            return True
        return False if all(v is False for v in vals) else None

    def evaluate_anims(self, assignment) -> list:
        anims = []
        for k in range(len(self.lits)):
            v = self.lit_value(k, assignment)
            if v is not None:
                anims.append(self.literal(k).animate.set_fill(INK if v else DIM))
        sat = self.is_satisfied(assignment)
        if sat is not None:
            anims.append(self.bar.animate.set_fill(INK if sat else RED, 1))
        return anims

    def reset_anims(self) -> list:
        return [self.tex.animate.set_fill(INK), self.bar.animate.set_opacity(0)]


class CNF(VGroup):
    """C_1 ∧ C_2 ∧ … wrapped to rows of `per_row`.  .clauses, .is_satisfied, .evaluate_anims."""

    def __init__(self, clauses, names=None, size: float = SIZE_FORMULA * 0.85, per_row: int = 4,
                 spaced: bool = False, **kwargs):
        super().__init__(**_drop_legacy(kwargs))
        self.clauses = VGroup(*[Clause(c, names=names, size=size, spaced=spaced) for c in clauses])
        self.ands = VGroup()
        rows = VGroup()
        for r in range(0, len(self.clauses), per_row):
            row = VGroup()
            for i, c in enumerate(self.clauses[r:r + per_row]):
                if r + i > 0:
                    a = Formula(r"\land", size, INK_2)
                    self.ands.add(a)
                    row.add(a)
                row.add(c)
            row.arrange(RIGHT, buff=0.2)
            rows.add(row)
        rows.arrange(DOWN, buff=0.4, aligned_edge=LEFT)
        self.add(*self.clauses, *self.ands)

    def is_satisfied(self, assignment):
        vals = [c.is_satisfied(assignment) for c in self.clauses]
        if all(v is True for v in vals):
            return True
        return False if any(v is False for v in vals) else None

    def evaluate_anims(self, assignment):
        return [a for c in self.clauses for a in c.evaluate_anims(assignment)]

    def reset_anims(self):
        return [a for c in self.clauses for a in c.reset_anims()]


# =====================================================================
# 7. Hexagon graph (clause graphs) with bit labels and a judgement cut
# =====================================================================
class SimpleGraph(VGroup):
    """
    Undirected graph with hexagon nodes (MAGI style).
        g = SimpleGraph(["E1", "E2", "E3"], [("E1", "E2"), ("E2", "E3")],
                        layout={"E1": (-2, 0), ...} or "circular",
                        node_labels={"E1": "E_1"} or True,   # Tex
                        bits={("E1", "E2"): 2})              # thickness + label; or edge_labels={...: "x_1"}
        g.node(v), g.edge(u, v), g.edge_label(u, v)
        line, marks, c = g.cut({"E1", "E2"})          # red judgement line + crossing marks + bits crossing
        self.play(judge_sweep(line)); self.play(FadeIn(marks))
    """

    def __init__(self, vertices, edges, layout="circular", radius: float = 2.5, node_radius: float = 0.42,
                 node_labels=True, bits: dict | None = None, edge_labels: dict | None = None,
                 label_size: float = 34, **kwargs):
        super().__init__(**_drop_legacy(kwargs))
        self.vertices = list(vertices)
        self.edge_keys = [tuple(e) for e in edges]
        self.bits = {tuple(k): v for k, v in (bits or {}).items()}
        if isinstance(layout, dict):
            pos = {v: np.array([*layout[v][:2], 0.0]) for v in self.vertices}
        else:
            n = len(self.vertices)
            pos = {v: radius * np.array([np.cos(TAU * k / n + PI / 2), np.sin(TAU * k / n + PI / 2), 0])
                   for k, v in enumerate(self.vertices)}
        self.positions = pos
        self.nodes, self.edges, self.edge_label_mobs = {}, {}, {}
        eg, lg, ng = VGroup(), VGroup(), VGroup()
        for (u, v) in self.edge_keys:
            b = self.bit_count(u, v)
            line = Line(pos[u], pos[v]).set_stroke(INK, 4 if b <= 1 else 9)
            self.edges[(u, v)] = line
            eg.add(line)
        labels = dict(edge_labels or {})
        for k, b in self.bits.items():
            labels.setdefault(k, str(b))
        for key, s in labels.items():
            line = self.edge(*key)
            lab = s if isinstance(s, Mobject) else Formula(s, label_size * 0.85, INK_2)
            d = line.get_end() - line.get_start()
            nrm = normalize(np.array([-d[1], d[0], 0])) if np.linalg.norm(d) > 0 else UP
            if nrm[1] < 0:
                nrm = -nrm
            lab.move_to(line.get_center() + nrm * 0.3)
            self.edge_label_mobs[tuple(key)] = lab
            lg.add(lab)
        for v in self.vertices:
            hexa = RegularPolygon(6, radius=node_radius).set_fill(INK, 1).set_stroke(width=0).move_to(pos[v])
            grp = VGroup(hexa)
            if node_labels:
                s = node_labels.get(v, str(v)) if isinstance(node_labels, dict) else str(v)
                lab = Formula(s, label_size, BG)
                if lab.get_width() > node_radius * 1.5:
                    lab.set_width(node_radius * 1.5)
                grp.add(lab.move_to(pos[v]))
            self.nodes[v] = grp
            ng.add(grp)
        self.edge_group, self.edge_label_group, self.node_group = eg, lg, ng
        self.add(eg, lg, ng)

    def bit_count(self, u, v):
        return self.bits.get((u, v), self.bits.get((v, u), 1))

    def node(self, v):
        return self.nodes[v]

    def edge(self, u, v):
        return self.edges[(u, v)] if (u, v) in self.edges else self.edges[(v, u)]

    def edge_label(self, u, v):
        return self.edge_label_mobs.get((u, v)) or self.edge_label_mobs[(v, u)]

    def highlight_node(self, v, color=RED):
        return self.nodes[v][0].animate.set_fill(color)

    def highlight_edge(self, u, v, color=RED):
        return self.edge(u, v).animate.set_stroke(color)

    def dim_edge(self, u, v):
        return self.edge(u, v).animate.set_stroke(DIM)

    def cut(self, side: set, x: float | None = None, margin: float = 0.7):
        """Vertical judgement line between `side` and the rest.  Returns (line, crossing marks, bits)."""
        P = {v: self.nodes[v].get_center() for v in self.vertices}      # live positions (after shifts)
        left = [P[v][0] for v in side]
        right = [P[v][0] for v in self.vertices if v not in side]
        if x is None:
            x = (max(left) + min(right)) / 2 if max(left) < min(right) else (np.mean(left) + np.mean(right)) / 2
        ys = [p[1] for p in P.values()]
        line = JudgeLine((x, max(ys) + margin), (x, min(ys) - margin))
        marks, total = VGroup(), 0
        for (u, v) in self.edge_keys:
            if (u in side) != (v in side):
                a, b = P[u], P[v]
                if abs(b[0] - a[0]) < 1e-9:
                    continue
                t = (x - a[0]) / (b[0] - a[0])
                if 0 <= t <= 1:
                    m = a + t * (b - a)
                    marks.add(Square(0.22).rotate(PI / 4).set_fill(RED, 1).set_stroke(width=0).move_to(m))
                    total += self.bit_count(u, v)
        return line, marks, total


# =====================================================================
# 8. Growth plot
# =====================================================================
def _nice_step(span: float) -> float:
    raw = span / 6
    mag = 10 ** np.floor(np.log10(raw))
    for m in (1, 2, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


class GrowthPlot(VGroup):
    r"""
    Running-time axes.  log_y=True plots log10 values with 10^k tick labels.
        p = GrowthPlot(n_max=100, log_y=True, y_max_log10=30)
        c = p.plot_base(2, label=r"2^n")                 # ink
        k = p.plot_base(1.308, label=r"1.308^n", color=RED)   # the one that matters
        self.play(ShowCreation(c, rate_func=EASE_OUT)); self.add(c.label)
    """

    def __init__(self, n_max: float = 50, log_y: bool = True, y_max_log10: float = 15, y_max: float = 1000,
                 width: float = 10, height: float = 5.0, x_label: str = "n", y_label: str | None = "时间",
                 x_step=None, y_step=None, **kwargs):
        super().__init__(**kwargs)
        self.log_y = log_y
        x_step = x_step or _nice_step(n_max)
        if log_y:
            y_step = y_step or max(1, round(y_max_log10 / 5))
            y_range = (0, y_max_log10, y_step)
        else:
            y_step = y_step or _nice_step(y_max)
            y_range = (0, y_max, y_step)
        self.axes = Axes(x_range=(0, n_max, x_step), y_range=y_range, width=width, height=height,
                         axis_config=dict(stroke_color=DIM, stroke_width=4, include_tip=False))
        self.axes.x_axis.add_numbers(font_size=SIZE_TINY, color=INK_2)
        if log_y:
            labs = VGroup()
            for k in np.arange(y_step, y_max_log10 + 1e-9, y_step):
                labs.add(Formula(rf"10^{{{int(k)}}}", SIZE_TINY, INK_2).next_to(self.axes.c2p(0, k), LEFT, buff=0.15))
            self.axes.y_axis.add(labs)
        else:
            self.axes.y_axis.add_numbers(font_size=SIZE_TINY, color=INK_2)
        self.add(self.axes)
        self.add(Formula(x_label, SIZE_SMALL, INK_2).next_to(self.axes.x_axis.get_end(), RIGHT, buff=0.15))
        if y_label == "时间":
            y_label = UI[LANG]["time"]
        if y_label:
            self.add(CText(y_label, SIZE_SMALL, INK_2).next_to(self.axes.y_axis.get_end(), UP, buff=0.15))
        self.curves = VGroup()
        self._n_max, self._y_top = n_max, y_range[1]

    def plot(self, fn, color=INK, label=None, x_range=None, width: float = 5):
        x0, x1 = x_range or (0, self._n_max)
        last = x1
        for x in np.linspace(x0, x1, 400):
            if fn(x) > self._y_top:
                last = x
                break
        g = self.axes.get_graph(lambda n: min(fn(n), self._y_top), x_range=(x0, last))
        g.set_stroke(color, width)
        g.label = None
        if label:
            g.label = Formula(label, SIZE_SMALL + 4, color).next_to(g.get_end(), RIGHT if last >= x1 - 1e-6 else UP, buff=0.12)
        self.curves.add(g)
        return g

    def plot_log10(self, log10_fn, **kw):
        return self.plot(log10_fn if self.log_y else (lambda n: 10 ** log10_fn(n)), **kw)

    def plot_base(self, base: float, poly: float = 0, **kw):
        lb = np.log10(base)
        return self.plot_log10(lambda n: n * lb + (poly * np.log10(max(n, 1e-9)) if poly else 0), **kw)


# =====================================================================
# 9. Timeline
# =====================================================================
class Timeline(VGroup):
    """
    events: (year, label) or (year, label, RED) — red marks the one event the beat is about.
        tl = Timeline([(1971, "Cook–Levin"), (2001, "ETH"), (2026, "ETH 被证伪", RED)], start=1965, end=2030)
        self.play(ShowCreation(tl.line, rate_func=EASE_EXPO)); self.play(rise_lines(tl.events))
    """

    def __init__(self, events, start=None, end=None, width: float = 12.4, tick_step: int = 10,
                 tick_labels: bool = False, **kwargs):
        super().__init__(**_drop_legacy(kwargs))
        years = [e[0] for e in events]
        start = start if start is not None else int(min(years) // tick_step * tick_step)
        end = end if end is not None else int(-(-max(years) // tick_step) * tick_step)
        self.start_year, self.end_year = start, end
        self.line = Line(LEFT * width / 2, RIGHT * width / 2).set_stroke(DIM, 6)
        self.ticks = VGroup()
        first = start + (-start) % tick_step
        for y in range(first, end + 1, tick_step):
            p = self.point_for(y)
            tk = VGroup(block(0.05, 0.22, DIM).move_to(p))
            if tick_labels:
                tk.add(CText(str(y), SIZE_TINY, INK_2).next_to(p, DOWN, buff=0.2))
            self.ticks.add(tk)
        self.events = VGroup()
        for k, ev in enumerate(events):
            year, label = ev[0], ev[1]
            c = ev[2] if len(ev) > 2 else INK
            p = self.point_for(year)
            up = k % 2 == 0
            stem_len = 0.8 if (k // 2) % 2 == 0 else 1.45
            stem = block(0.04, stem_len, c if c == RED else INK_2)
            stem.next_to(p, UP if up else DOWN, buff=0)
            dot = Square(0.16).rotate(PI / 4).set_fill(c, 1).set_stroke(width=0).move_to(p)
            yr = Display(str(year), 52, c, squash=0.8)
            lab = CText(label, SIZE_SMALL, INK)
            txt = VGroup(yr, lab).arrange(DOWN, buff=0.06, aligned_edge=LEFT)
            txt.next_to(stem, UP if up else DOWN, buff=0.1).align_to(stem, LEFT)
            self.events.add(VGroup(stem, dot, txt))
        self.add(self.line, self.ticks, self.events)

    def point_for(self, year: float) -> np.ndarray:
        a = (year - self.start_year) / (self.end_year - self.start_year)
        return self.line.get_start() + a * (self.line.get_end() - self.line.get_start())


# =====================================================================
# 10. Utilities
# =====================================================================
def stack(scene, *mobs):
    """Legacy helper (concept frames).  The engine now orders overlaps itself; this just adds in order."""
    flat = []
    for m in mobs:
        flat.extend(m if isinstance(m, (list, tuple)) else [m])
    scene.add(*flat)


__all__ = [n for n in dir() if not n.startswith("_")]
