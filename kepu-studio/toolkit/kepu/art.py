"""美术方向发牌（照 taste-skill 的做法：让脚本发牌，而不是让模型每次都挑品类默认款）。

    kepu art deal --subject "SAT 与指数时间假说" [--n 4] [--engine anime|pixel] [--seed 3]
    kepu art list

发出的方向记在 ~/.kepu/art_history.json，下次少发重复的。拿到几张牌之后，按技能 kepu-studio:art 的步骤做：
盘点题材 → 每个方向写 IDEA 句、过竞品测试 → 每个方向做标题卡 + 内容帧两张概念帧 → 评委打分 → 作者选定 → 写进系列设定。
"""
from __future__ import annotations

import json
import random
import time

from .util import DATA, USER_DIR

HIST = USER_DIR / "art_history.json"


def directions() -> list[dict]:
    return json.loads((DATA / "directions.json").read_text(encoding="utf-8"))["directions"]


def deal(subject: str = "", n: int = 4, engine: str | None = None, seed: int | None = None) -> list[dict]:
    ds = [d for d in directions() if not engine or d["engine"] in (engine, "either")]
    try:
        hist = json.loads(HIST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        hist = []
    recent = {h["id"] for h in hist[-8:]}
    rng = random.Random(seed if seed is not None else time.time_ns())
    words = [w for w in subject.replace("、", " ").replace("，", " ").split() if w]
    def weight(d):
        w = 1.0 + sum(2.0 for x in words if x in d["fits"] or x in d["idea_hint"])
        return w * (0.35 if d["id"] in recent else 1.0) * (1.3 if d.get("proven") else 1.0)
    pool, out = list(ds), []
    while pool and len(out) < n:
        tot = sum(weight(d) for d in pool)
        r, acc = rng.random() * tot, 0.0
        for d in pool:
            acc += weight(d)
            if acc >= r:
                out.append(d)
                pool.remove(d)
                break
    try:
        HIST.parent.mkdir(parents=True, exist_ok=True)
        HIST.write_text(json.dumps(hist[-40:] + [{"id": d["id"], "subject": subject, "at": time.strftime("%Y-%m-%d %H:%M")}
                                                 for d in out], ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass
    return out


def show(d: dict) -> str:
    p = d["palette"]
    return (f"■ {d['name']}（{d['id']}，引擎：{d['engine']}）— 出自{d['from']}\n"
            f"  装置：{d['device']}\n  IDEA 提示：{d['idea_hint']}\n"
            f"  配色：bg {p['bg']} · surface {p['surface']} · ink {p['ink']} · muted {p['muted']} · accent {p['accent']}\n"
            f"  字体：{d['type']}\n  签名动作：{d['signature']}\n  适合：{d['fits']}\n  风险：{d['risks']}"
            + (f"\n  实战：{d['proven']}" if d.get("proven") else ""))
