"""Reading marks written in the script: 字〔读音〕 (shù or shu4).  A mark binds to the character right before it,
never reaches the subtitles, and is the strongest decision there is."""
from __future__ import annotations

import re

from ..util import tone_mark

MARK = re.compile(r"〔([^〔〕]{0,12})〕")


def parse_marks(text: str) -> tuple[str, dict[int, str]]:
    """'一直数〔shu3〕下去' -> ('一直数下去', {2: 'shǔ'})."""
    out, marks, last, n = [], {}, 0, 0
    for m in MARK.finditer(text):
        out.append(text[last:m.start()])
        n += m.start() - last
        if n:
            marks[n - 1] = tone_mark(m.group(1))
        last = m.end()
    out.append(text[last:])
    return "".join(out), marks


def strip_marks(text: str) -> str:
    return MARK.sub("", text)
