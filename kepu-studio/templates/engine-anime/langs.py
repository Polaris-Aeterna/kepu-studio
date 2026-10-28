"""
Language settings shared by tts.py, narrated.py, resrt.py and assemble.py (no ManimGL dependency).

    zh (default, the finished Chinese series)   en (English YouTube version, README §11)
    script/episodes/epN_*.md                    script/en/epN_*.md
    episodes/epN_*/                             episodes_en/epN_*/
    engine/audio/epN/                           engine/audio/en/epN/               final ElevenLabs audio
                                                engine/audio/en/_placeholder/epN/  free edge/say audio (never final)
    engine/audio/_cache/                        engine/audio/en/_cache/

Chinese paths are exactly the pre-English ones, so nothing about the Chinese build changes.
"""
from __future__ import annotations

import json
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
ROOT = ENGINE.parent
AUDIO_ROOT = ENGINE / "audio"
LANGS = ("zh", "en")
PLACEHOLDER = "_placeholder"


def check(lang: str) -> str:
    if lang not in LANGS:
        raise ValueError(f"unknown lang {lang!r} (expected one of {LANGS})")
    return lang


def audio_dir(lang: str, chapter: str, placeholder: bool = False) -> Path:
    """Where tts.py writes / NarratedScene reads one chapter's audio."""
    check(lang)
    if lang == "zh":
        return AUDIO_ROOT / chapter
    return AUDIO_ROOT / lang / PLACEHOLDER / chapter if placeholder else AUDIO_ROOT / lang / chapter


def cache_dir(lang: str) -> Path:
    return AUDIO_ROOT / "_cache" if lang == "zh" else AUDIO_ROOT / lang / "_cache"


def episodes_root(lang: str) -> Path:
    return ROOT / ("episodes" if check(lang) == "zh" else f"episodes_{lang}")


def script_root(lang: str) -> Path:
    return ROOT / "script" / ("episodes" if check(lang) == "zh" else lang)


def lang_of_path(path) -> str:
    """'en' for anything under script/en/, episodes_en/ or engine/audio/en/; else 'zh'."""
    parts = Path(path).resolve().parts
    for i, p in enumerate(parts):
        if p == "episodes_en":
            return "en"
        if p in ("en",) and i > 0 and parts[i - 1] in ("script", "audio"):
            return "en"
    return "zh"


def _read(path: Path) -> dict:
    return json.loads(path.read_text("utf-8"))["beats"] if path.exists() else {}


def load_beats(lang: str, chapter: str, directory: Path | None = None):
    """-> (beats {id: info}, source {id: 'final' | 'placeholder'}, info dir {id: Path}).
    zh (or an explicit directory): that one beats.json, as before.  en: final beats win; beats that only exist
    as placeholder audio are taken from _placeholder/ and marked, so a re-render after voicing picks up the
    ElevenLabs takes automatically."""
    if directory is not None or lang == "zh":
        d = Path(directory) if directory is not None else audio_dir(lang, chapter)
        b = _read(d / "beats.json")
        return b, {k: "final" for k in b}, {k: d for k in b}
    fd, pd = audio_dir(lang, chapter), audio_dir(lang, chapter, placeholder=True)
    final, ph = _read(fd / "beats.json"), _read(pd / "beats.json")
    beats, src, dirs = {}, {}, {}
    for k in list(final) + [k for k in ph if k not in final]:
        if k in final:
            beats[k], src[k], dirs[k] = final[k], "final", fd
        else:
            beats[k], src[k], dirs[k] = ph[k], "placeholder", pd
    return beats, src, dirs
