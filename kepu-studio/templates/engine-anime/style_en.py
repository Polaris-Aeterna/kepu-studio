"""
English entry point for episode code (README §11):

    from style_en import *          # instead of `from style import *`
    from narrated import NarratedScene
    class Ep1Scene(NarratedScene):
        LANG = "en"                 # audio from engine/audio/en/<chapter>/, English subtitle splitter, no burn-in

Same names as style (palette, sizes, components, manimlib); the components now use the English faces
(Times New Roman Bold squashed 0.78 for Display / Heading / cards, Times New Roman for CText / Markup / Latin)
and English UI words.  TEXT_FONT / DISPLAY_FONT / LATIN / SQUASH below are the English values.
Extra English sizes (Latin glyphs are smaller than CJK at the same font_size, see README §11.3):
    SIZE_BODY_EN 38 (body)   SIZE_SMALL_EN 30 (labels)   SIZE_H1_EN 80 (headings)
"""
import style as _style
from style import *  # noqa: F401,F403

_style.set_lang("en")
from style import *  # noqa: F401,F403,E402  (re-binds LANG, TEXT_FONT, DISPLAY_FONT, LATIN, SQUASH)

SIZE_BODY_EN = 38
SIZE_SMALL_EN = 30
SIZE_H1_EN = 80
