"""遮挡检查（不渲染，每 0.5 秒采样）：

1. 被对话框挡住：对话框开着时，可见对象有不透明像素落在 y ≥ 138（对话框外框）里。对话框最后画，压在一切上面。
2. 文字被压住：文字一部分露在外面、一部分被后画的东西（z 更大，或 z 相同但后加入）盖住。按真实像素算，不按外框算，
   所以描边框、透明的空白不算；整个藏在面板底下的旧字观众看不见，也不算。两类都要持续 1 秒以上。

    python -m pixel.occlusion ep02 [s2ep05 ...]        # 每集列出问题：场景、集内时间、谁挡了谁、挡了多少像素
作者 2026-10-26 指出第一季第 2 集 7:14 的红字条被对话框挡住，之后所有像素版都用这个查一遍。
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pixel.build import load  # noqa: E402
from pixel.engine import DLG  # noqa: E402

STEP = 0.5
MIN_DLG_PX = 40        # 落进对话框的不透明像素至少这么多、且至少深入 3 像素才算（角色脚尖、阴影不算）
MIN_DLG_ROWS = 3
MIN_TEXT_PX = 10       # 文字被盖住的像素至少这么多，且占这段文字的 5% 以上，并且持续 1 秒以上（切换时的一瞬不算）
MIN_TEXT_SAMPLES = 2
_masks = {}


def _mask(o, t):
    """对象在 t 时刻的不透明像素（320 像素坐标下的布尔阵）。"""
    im = o.image_at(t)
    if im is None:
        return None
    k = (id(im), o.fine)
    if k not in _masks:
        a = np.asarray(im.convert("RGBA"))[..., 3] > 0
        if o.fine:                       # fine 层是 640 像素：缩回 320
            h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
            a = a[:h, :w].reshape(h // 2, 2, w // 2, 2).any(axis=(1, 3))
        _masks[k] = a
    return _masks[k]


def _text_of(o):
    return str(getattr(o, "text", "") or "")


def _label(o):
    tx = _text_of(o)
    return tx[:24] if tx else f"{type(o).__name__} {o.w:.0f}x{o.h:.0f}"


def _tick(h, t):
    """连续命中的采样数（动画路过的一瞬只命中一次，不算）。"""
    h["n"] += 1
    h["cur"] = h.get("cur", 0) + 1 if abs(t - h.get("last", -9) - STEP) < 1e-6 else 1
    h["last"] = t
    h["run"] = max(h.get("run", 0), h["cur"])


def dialog_on(s, t):
    """对话框在 t 时刻画不画（和 engine.draw_dialog 同一规则：有旁白在念、或刚念完 0.9 秒内）。"""
    if not getattr(s, "dialog", True):
        return False
    for i, nr in enumerate(s.narr):
        nxt = s.narr[i + 1]["t"] if i + 1 < len(s.narr) else 1e9
        if nr["t"] <= t < min(nr["t"] + nr["dur"] + 0.9, nxt):
            return True
    return False


def check(tag):
    """每 0.5 秒画一张“归属图”：每个像素归最后画上去的那个对象（对话框开着时，对话框压在最上面）。
    一个对象的像素一部分露在外面、一部分被别的东西盖住，就是观众看得见的遮挡；整个被盖住的（藏在面板底下的旧字）看不见，不算。"""
    ep = load(tag)
    out = []
    t_ep = 0.0
    DIALOG = -2
    for s in ep.build():
        leaves = [o for o in s.objs if not getattr(o, "children", None) and (o.img is not None or o.frames)]
        # 画的先后：像素层先画（按 z），细字层（fine）整层叠在像素层上面（engine.render 最后才把 fine 层合上去）；sorted 是稳定的
        order = sorted(leaves, key=lambda o: (bool(o.fine), o.z))
        seen = {}
        t = 0.0
        while t < s.duration:
            vis = [o for o in order if o.at("vis", t) >= 0.5]
            owner = np.full((180, 320), -1, np.int32)
            placed = []
            for idx, o in enumerate(vis):
                m = _mask(o, t)
                if m is None:
                    placed.append(None)
                    continue
                x0, y0, x1, y1 = o.box(t)
                xi, yi = int(round(x0)), int(round(y0))
                h, w = m.shape
                cx0, cy0, cx1, cy1 = max(0, xi), max(0, yi), min(320, xi + w), min(180, yi + h)
                if cx1 <= cx0 or cy1 <= cy0:
                    placed.append(None)
                    continue
                sub = m[cy0 - yi:cy1 - yi, cx0 - xi:cx1 - xi]
                owner[cy0:cy1, cx0:cx1][sub] = idx
                placed.append((cx0, cy0, cx1, cy1, sub, (x0, y0, x1, y1)))
            dlg = dialog_on(s, t)
            if dlg:
                owner[DLG[1]:DLG[3] + 1, DLG[0]:DLG[2] + 1] = DIALOG
            for idx, o in enumerate(vis):
                pl = placed[idx]
                if pl is None:
                    continue
                cx0, cy0, cx1, cy1, sub, box = pl
                own = owner[cy0:cy1, cx0:cx1]
                total = int(sub.sum())
                if total < 20:
                    continue
                mine = int((own[sub] == idx).sum())
                covered_by = own[sub][own[sub] != idx]
                if mine < 0.05 * total:          # 整个被盖住：观众看不见，不算
                    continue
                n_dlg = int((covered_by == DIALOG).sum())
                if dlg and n_dlg >= MIN_DLG_PX and box[3] - DLG[1] >= MIN_DLG_ROWS and o.h < 150:
                    k = ("dlg", id(o))
                    if k not in seen:
                        seen[k] = dict(kind="under-dialog", scene=s.name, t_scene=round(t, 1), t_ep=round(t_ep + t, 1),
                                       what=_label(o), px=n_dlg, y1=round(box[3], 1), box=[round(v) for v in box], n=0)
                    _tick(seen[k], t)
                if not _text_of(o):
                    continue
                others = covered_by[covered_by >= 0]
                if len(others) >= MIN_TEXT_PX and len(others) >= 0.05 * total:
                    b = vis[int(np.bincount(others).argmax())]
                    k = ("txt", id(o), id(b))
                    if k not in seen:
                        bb = b.box(t)
                        seen[k] = dict(kind="text-covered", scene=s.name, t_scene=round(t, 1), t_ep=round(t_ep + t, 1),
                                       what=_label(o), by=_label(b), px=int(len(others)), n=0,
                                       box=[round(v) for v in box], box_by=[round(v) for v in bb])
                    _tick(seen[k], t)
            t += STEP
        out += [h for h in seen.values() if h["run"] >= MIN_TEXT_SAMPLES]
        t_ep += s.duration
    return out


def fmt(sec):
    return f"{int(sec // 60)}:{sec % 60:04.1f}"


if __name__ == "__main__":
    import json
    js = "--json" in sys.argv
    for tag in [a for a in sys.argv[1:] if not a.startswith("--")]:
        hs = check(tag)
        if js:   # 存一份给复查用：pixel/out/<tag>/occlusion.json
            out = Path(__file__).resolve().parent / "out" / tag
            out.mkdir(parents=True, exist_ok=True)
            (out / "occlusion.json").write_text(json.dumps(hs, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{tag}: {len(hs)} occlusions")
        for h in hs:
            extra = f"by {h['by']}" if h["kind"] == "text-covered" else f"bottom y={h['y1']}"
            print(f"   {h['kind']:13s} ~{fmt(h['t_ep']):>7s}  {h['scene']:18s} {h['what']:26s} {extra}  ({h['px']} px)")
