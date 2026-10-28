"""把 occlusion.json 里的每处问题渲染成一帧（只渲染那一帧），拼成联系表给人看：红框 = 被挡的，黄框 = 挡它的。

    python -m pixel.occlusion_sheet ep02            # → pixel/out/ep02/occlusion_sheet_NN.png（每张 3×3）
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pixel.build import load  # noqa: E402

TW, TH = 640, 360


def font(sz):
    for f in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def main(tag):
    out = Path(__file__).resolve().parent / "out" / tag
    hs = json.loads((out / "occlusion.json").read_text(encoding="utf-8"))
    if not hs:
        print(tag, "no occlusions")
        return
    scenes = {s.name: s for s in load(tag).build()}
    groups = []          # 同一场景、0.6 秒内的问题画在同一帧
    for h in sorted(hs, key=lambda h: h["t_ep"]):
        if groups and groups[-1][0]["scene"] == h["scene"] and h["t_scene"] - groups[-1][0]["t_scene"] <= 0.6:
            groups[-1].append(h)
        else:
            groups.append([h])
    tiles = []
    f = font(15)
    for i, g in enumerate(groups):
        s = scenes[g[0]["scene"]]
        t = min(g[0]["t_scene"] + 0.25, s.duration - 0.01)
        im = s.render(t).convert("RGB")
        k = im.width / 320
        d = ImageDraw.Draw(im)
        for h in g:
            if h.get("box_by"):
                d.rectangle([v * k for v in h["box_by"]], outline=(255, 210, 0), width=4)
            d.rectangle([v * k for v in h["box"]], outline=(255, 40, 40), width=5)
        im = im.resize((TW, TH))
        tile = Image.new("RGB", (TW, TH + 44), (20, 20, 20))
        tile.paste(im, (0, 44))
        dd = ImageDraw.Draw(tile)
        m, sec = divmod(g[0]["t_ep"], 60)
        kinds = "、".join(sorted({"对话框" if h["kind"] == "under-dialog" else "压字" for h in g}))
        dd.text((6, 2), f"#{i + 1}  {int(m)}:{sec:04.1f}  {g[0]['scene']}  [{kinds}]", fill=(255, 255, 255), font=f)
        dd.text((6, 22), " | ".join(h["what"][:14] for h in g)[:60], fill=(255, 200, 120), font=f)
        tiles.append(tile)
    for n in range(0, len(tiles), 9):
        sheet = Image.new("RGB", (TW * 3, (TH + 44) * 3), (0, 0, 0))
        for j, tl in enumerate(tiles[n:n + 9]):
            sheet.paste(tl, ((j % 3) * TW, (j // 3) * (TH + 44)))
        p = out / f"occlusion_sheet_{n // 9 + 1:02d}.png"
        sheet.save(p)
        print(p)
    (out / "occlusion_groups.json").write_text(json.dumps(groups, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    for tag in sys.argv[1:]:
        main(tag)
