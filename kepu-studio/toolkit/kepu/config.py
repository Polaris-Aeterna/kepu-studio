"""kepu.toml：一个项目的设置。Python 3.11+ 用 tomllib；更老的版本用这里的小解析器（只认本文件用到的写法）。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .util import find_project_root

DEFAULTS = {
    "project": {"name": "", "scripts": "script/episodes", "engine": "none", "audio": "audio", "series": "series/系列设定.md",
                "notes": "notes", "review": "review", "output": "output"},
    "voice": {"engine": "eleven", "voice_id": "kAIqZ7fZv234ClKXwzDx", "model": "eleven_v4", "stability": 0.5, "speed": 1.0,
              "similarity_boost": None, "output_format": "mp3_44100_128", "env_file": ".env", "max_chars": 2000,
              "edge_voice": "zh-CN-YunxiNeural", "say_voice": "Tingting", "chars_per_minute": 260, "cache": "",
              "beat_gap": 0.6},
    "pron": {"greek": "en", "strict": False, "digits": "warn", "margin": 3.0},
    "levels": {"L1": "主线", "L2": "进阶", "L3": "硬核支线", "max_L3_share": 0.2, "question_every_min": 3.0,
               "max_sentence_chars": 25, "max_beat_seconds": 45},
    "release": {"lufs": -16.0, "true_peak": -1.5},
}


def _parse_value(v: str):
    v = v.strip()
    if v.startswith(('"', "'")):
        return v[1:v.rindex(v[0])]
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def _mini_toml(text: str) -> dict:
    out: dict = {}
    sec = out
    for ln in text.splitlines():
        ln = re.sub(r"\s+#.*$", "", ln).strip() if not ln.strip().startswith("#") else ""
        if not ln:
            continue
        m = re.match(r"^\[([^\]]+)\]$", ln)
        if m:
            sec = out.setdefault(m.group(1).strip(), {})
            continue
        if "=" in ln:
            k, v = ln.split("=", 1)
            sec[k.strip()] = _parse_value(v)
    return out


def load_toml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        import tomllib
        return tomllib.loads(text)
    except ImportError:
        return _mini_toml(text)


@dataclass
class Config:
    root: Path | None
    data: dict = field(default_factory=dict)

    def get(self, section: str, key: str, default=None):
        v = self.data.get(section, {}).get(key)
        if v is None:
            v = DEFAULTS.get(section, {}).get(key, default)
        return v

    def path(self, section: str, key: str) -> Path:
        p = Path(str(self.get(section, key)))
        return p if p.is_absolute() or self.root is None else self.root / p

    @property
    def voice_key(self) -> str:
        return f"{self.get('voice', 'voice_id')}__{self.get('voice', 'model')}"

    def pron(self):
        from .pron.speak import PronConfig
        return PronConfig(project_root=self.root, greek=self.get("pron", "greek"), strict=bool(self.get("pron", "strict")),
                          digits=self.get("pron", "digits"), margin=float(self.get("pron", "margin")),
                          voice_key=self.voice_key)


def load(start: Path | None = None) -> Config:
    root = find_project_root(start)
    data = load_toml(root / "kepu.toml") if root else {}
    return Config(root, data)
