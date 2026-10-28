"""读音引擎：多音字的决定（resolve）、替身字与符号读法（speak）、希腊字母（greek）、读法一侧的检查。

    from kepu.pron import prepare
    p = prepare("这一行〔háng〕为真，长子句")      # -> Prepared: tts text, spans, spots, held …
"""
from .speak import Prepared, prepare  # noqa: F401
