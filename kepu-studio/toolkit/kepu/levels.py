"""一期稿子的体检：长度、节奏、提问间隔、句长、难度分级与严谨度分布（不花钱）。

    kepu stats script/episodes/ep01.md              # 报告
    kepu stats script/episodes/ep01.md --cut L1     # “主线精简版”：只留 L1 的 beat，列出清单和时长

分级（两个维度，见技能 kepu-notes 的 references/levels.md）：
  难度 L1 主线（只假设高中数学，所有观众都要跟上）/ L2 进阶（本科理工）/ L3 硬核支线（可以跳过，跳过不影响后面）
  严谨度 完整 / 骨架 / 黑箱→第 N 集 / 黑箱→文献（《地基之下》的严谨契约：视频角标可以低于讲义，不能高于）
"""
from __future__ import annotations

import re
from pathlib import Path

from . import script as S
from .util import pad

Q = re.compile(r"[？?]|想一想|暂停一下|你可以暂停|先别往下看|猜一猜|你觉得")
SENT = re.compile(r"[^。！？!?；]+[。！？!?；]?")


def stats(path: Path, cfg, cut: str | None = None) -> int:
    ep = S.parse(path)
    cpm = float(cfg.get("voice", "chars_per_minute"))
    max_sent = int(cfg.get("levels", "max_sentence_chars"))
    max_beat = float(cfg.get("levels", "max_beat_seconds"))
    q_every = float(cfg.get("levels", "question_every_min"))
    names = {k: cfg.get("levels", k) for k in ("L1", "L2", "L3")}
    rows, t = [], 0.0
    for b in ep.beats:
        d, spoken, _ = S.split_beat(b.narration)
        n = len(re.sub(r"[\s，。！？；：、“”‘’（）《》…—]", "", spoken))
        sec = n / cpm * 60 + sum(s for _, s in b.pauses)
        rows.append((b, n, sec, t, bool(Q.search(d)), [s for s in SENT.findall(d) if len(s) > max_sent]))
        t += sec
    total = t
    print(f"{path.name}：{len(ep.beats)} 个 beat（{ep.unit}），{sum(r[1] for r in rows):,} 字，约 {total / 60:.1f} 分钟"
          f"（{cpm:.0f} 字/分钟，含停顿）；场景 {len(ep.scenes)} 个")
    # levels
    by = {}
    for b, n, sec, *_ in rows:
        k = b.level or "未标"
        a = by.setdefault(k, [0, 0.0])
        a[0] += 1
        a[1] += sec
    print("难度分级：" + "，".join(f"{k}{('·' + names[k]) if k in names else ''} {v[0]} 个 / {v[1] / 60:.1f} 分钟（{v[1] / total:.0%}）"
                                 for k, v in sorted(by.items())) if total else "")
    warns = []
    l3 = by.get("L3", [0, 0.0])[1]
    if total and l3 / total > float(cfg.get("levels", "max_L3_share")):
        warns.append(f"L3 占 {l3 / total:.0%}，超过 {float(cfg.get('levels', 'max_L3_share')):.0%}：考虑移进讲义的支线框")
    if by.get("未标") and len(by) > 1:
        warns.append(f"{by['未标'][0]} 个 beat 没标难度（在 beat 标题后写 [L1] / [L2] / [L3]）")
    prev = None
    for b, *_ in rows:
        if prev == "L1" and b.level == "L3":
            warns.append(f"beat {b.id}：从 L1 直接跳到 L3，中间缺一座 L2 的桥（或者先说一句“这一段可以跳过”）")
        prev = b.level or prev
    rig = {}
    for b, *_ in rows:
        if b.rigor:
            rig[b.rigor] = rig.get(b.rigor, 0) + 1
    if rig:
        print("严谨度：" + "，".join(f"{k} {v}" for k, v in rig.items()))
    # pacing
    long_beats = [(b.id, sec) for b, n, sec, *_ in rows if sec > max_beat]
    if long_beats:
        warns.append(f"{len(long_beats)} 个 beat 超过 {max_beat:.0f} 秒（难返工、画面难撑）：" +
                     "、".join(f"{i}（{s:.0f}s）" for i, s in long_beats[:8]))
    qt = [st for b, n, sec, st, q, _ in rows if q]
    gaps = [b - a for a, b in zip([0.0] + qt, qt + [total])]
    if gaps and max(gaps) > q_every * 60 * 1.5:
        k = gaps.index(max(gaps))
        warns.append(f"最长 {max(gaps) / 60:.1f} 分钟没有给观众一个问题（约 {(([0.0] + qt)[k]) / 60:.1f} 分开始）；"
                     f"规矩是每 {q_every:.0f} 分钟左右一个，配（停顿 2 秒）")
    longs = [(b.id, s) for b, *_r, ls in rows for s in ls]
    if longs:
        warns.append(f"{len(longs)} 句超过 {max_sent} 字（念出来的中文要短句），例如 beat {longs[0][0]}：{longs[0][1][:40]}…")
    for w in warns:
        print("  ! " + w)
    if not warns:
        print("  ✓ 节奏、分级、句长都在范围内")
    if cut:
        keep = [r for r in rows if (r[0].level or "L1") <= cut]
        sec = sum(r[2] for r in keep)
        print(f"\n“{cut} 以内”的精简版：{len(keep)}/{len(rows)} 个 beat，约 {sec / 60:.1f} 分钟")
        print("  " + " ".join(r[0].id for r in keep))
    print("\n逐 beat：")
    for b, n, sec, st, q, ls in rows:
        print(f"  {pad(b.id, 8)}{st / 60:5.1f}′ {sec:5.1f}s {pad(b.level or '·', 4)}{pad(b.rigor or '', 10)}"
              f"{'？' if q else '  '} {b.scene[:24]}")
    return 0
