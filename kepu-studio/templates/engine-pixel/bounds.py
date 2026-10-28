"""usage: python -m pixel.bounds epNN [epMM ...] -> 可见对象超出画面的情况（每秒采样，不渲染）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pixel.build import load  # noqa: E402


def check(tag, margin=2):
    ep = load(tag)
    hits = {}
    for s in ep.build():
        t = 0.0
        while t < s.duration:
            for o in s.objs:
                if getattr(o, "children", None) or (o.img is None and not o.frames):
                    continue
                if o.at("vis", t) < 0.5:
                    continue
                x0, y0, x1, y1 = o.box(t)
                over = max(-x0, x1 - 320, -y0, y1 - 180)
                if over > margin:
                    key = (s.name, id(o))
                    if key not in hits:
                        label = getattr(o, "text", "") or f"{type(o).__name__} {o.w:.0f}x{o.h:.0f}"
                        hits[key] = (s.name, t, over, str(label)[:40])
            t += 1.0
    return list(hits.values())


if __name__ == "__main__":
    for tag in sys.argv[1:]:
        hs = check(tag)
        print(f"{tag}: {len(hs)} objects outside the frame")
        for name, t, over, label in hs:
            print(f"   {name:18s} t={t:6.1f}s  over by {over:5.1f}px  {label}")
