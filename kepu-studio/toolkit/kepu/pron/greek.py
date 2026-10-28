"""希腊字母与数学符号的读法，以及按音色保存的校准结果（音色档案）。

音色档案：~/.kepu/voices/<voice_key>.json（个人全局，所有项目共用），项目里的 pron/voice_profile.json 可以再覆盖。
    {"greek": {"σ": {"say": "Sigma", "verified": true}}, "standins_bad": ["档"], "standins_ok": ["尝"], "pinyin_ok": ["mú"]}
voice_key = 音色 id + "__" + 模型，例如 kAIqZ7fZv234ClKXwzDx__eleven_v4。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from ..util import DATA, USER_DIR


@lru_cache(maxsize=1)
def greek_table() -> dict:
    return json.loads((DATA / "greek.json").read_text(encoding="utf-8"))["letters"]


@lru_cache(maxsize=1)
def symbol_table() -> tuple[dict, dict]:
    d = json.loads((DATA / "symbols.json").read_text(encoding="utf-8"))
    return d["say"], d["hold"]


def profile_paths(voice_key: str | None, project_root: Path | None) -> list[Path]:
    out = []
    if voice_key:
        out.append(USER_DIR / "voices" / f"{voice_key}.json")
    if project_root:
        out.append(project_root / "pron" / "voice_profile.json")
    return out


def load_profile(voice_key: str | None, project_root: Path | None) -> dict:
    prof = {"greek": {}, "standins_bad": [], "standins_ok": [], "pinyin_ok": []}
    for p in profile_paths(voice_key, project_root):
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            prof["greek"].update(d.get("greek", {}))
            for k in ("standins_bad", "standins_ok", "pinyin_ok"):
                prof[k] = sorted(set(prof[k]) | set(d.get(k, [])))
    return prof


def save_profile(voice_key: str, update: dict) -> Path:
    p = USER_DIR / "voices" / f"{voice_key}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"voice_key": voice_key}
    d.setdefault("greek", {}).update(update.get("greek", {}))
    for k in ("standins_bad", "standins_ok", "pinyin_ok"):
        d[k] = sorted(set(d.get(k, [])) | set(update.get(k, [])))
    if update.get("standins_ok"):                       # a stand-in confirmed good is no longer bad
        d["standins_bad"] = sorted(set(d.get("standins_bad", [])) - set(update["standins_ok"]))
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return p


def greek_say(ch: str, style: str, profile: dict) -> tuple[str, str] | None:
    """Greek letter -> (text sent to the TTS, status 'field'|'new'|'verified').  None when not a known letter."""
    g = greek_table().get(ch)
    if not g:
        return None
    if style == "zh":
        return g["zh"], "field" if g["zh"] == g.get("en") and g.get("status") == "field" else "zh"
    p = profile.get("greek", {}).get(ch)
    if p and p.get("say"):
        return p["say"], "verified" if p.get("verified") else "new"
    return g["en"], g.get("status", "new")
