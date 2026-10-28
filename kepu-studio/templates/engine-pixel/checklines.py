"""python -m pixel.checklines ep01 -> 分镜里念的旁白，是否与配音（audio/ep01/beats.json，来自稿子）逐字一致、顺序一致。
规矩：改画面不许顺手改旁白；要改台词，先改稿子、重新配音（./kepu voice），再改分镜。"""
import json
import re
import sys
from pathlib import Path

PROD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROD))
P = re.compile(r"[\s，。：；？！、“”‘’（）《》「」…—·,.:;?!()\"'\[\]]")
MARK = re.compile(r"〔[^〔〕]{0,12}〕")


def flat(texts):
    return "".join(P.sub("", MARK.sub("", t)) for t in texts)


def compare(mine_texts, refs):
    out = [f"MARK in storyboard（读音标记只该在稿子里）: {t[:40]}" for t in mine_texts if MARK.search(t)]
    mine, ref = flat(mine_texts), flat(refs)
    if mine == ref:
        return out + [f"OK: narration identical to the script ({len(ref)} chars)"]
    i = next((k for k in range(min(len(mine), len(ref))) if mine[k] != ref[k]), min(len(mine), len(ref)))
    return out + [f"DIFF at char {i}: storyboard={len(mine)} script={len(ref)}",
                  "  storyboard: " + mine[max(0, i - 30):i + 40], "  script    : " + ref[max(0, i - 30):i + 40]]


if __name__ == "__main__":
    from pixel.build import load
    tag = sys.argv[1]
    scenes = load(tag).build()
    beats = json.loads((PROD / "audio" / tag / "beats.json").read_text(encoding="utf-8"))["beats"]
    lines = compare([nr["text"] for s in scenes for nr in s.narr], [b["text"] for b in beats.values()])
    print("\n".join(lines))
    sys.exit(0 if lines[-1].startswith("OK") else 1)
