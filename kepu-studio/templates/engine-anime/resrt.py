#!/usr/bin/env python
"""
Re-export subtitles without re-rendering.

    engine/.venv/bin/python engine/resrt.py episodes/ep6_openai              # every videos/*.timeline.json
                                                                             #   -> videos/<Scene>.srt (new segmentation,
                                                                             #   plain text) + <dir>/epN_final.srt
    engine/.venv/bin/python engine/resrt.py --plain episodes/ep6_openai/ep6_final.srt   # only make the text readable
                                                                             #   (2^{…} -> 2^(…)/ⁿ, x_{12} -> x₁₂), keep the cues

English episodes (episodes_en/…, timeline "lang": "en") use the English caption splitter (subtitles_en.py) and
engine/audio/en/<chapter>/ (placeholder beats from en/_placeholder/), exactly as the render did.

Timeline mode rebuilds each scene's cues from its .timeline.json (beat start times written by NarratedScene) and
engine/audio/<chapter>/beats.json (the same char_times the render used), so timing is identical to a render
with the current engine/subtitles.py.  NOTE: the subtitles burned into the existing .mp4 keep the OLD
segmentation until the scene is re-rendered; use timeline mode for CC files after (or instead of) a re-render.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE))
from subtitles import split_phrases, srt_text  # noqa: E402
import subtitles_en  # noqa: E402
import langs  # noqa: E402
import assemble  # noqa: E402


def ts(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(cues, path: Path):
    lines = []
    for k, (a, b, s) in enumerate(cues, 1):
        lines += [str(k), f"{ts(a)} --> {ts(b)}", srt_text(s), ""]
    path.write_text("\n".join(lines), "utf-8")


def scene_cues(timeline: Path):
    tl = json.loads(timeline.read_text("utf-8"))
    lang = tl.get("lang", "zh")
    if lang == "zh":
        beats = json.loads((ENGINE / "audio" / tl["chapter"] / "beats.json").read_text("utf-8"))["beats"]
        split = split_phrases
    else:
        beats = langs.load_beats(lang, tl["chapter"])[0]
        split = subtitles_en.split_cues
    cues = []
    for bid, start, dur in tl["beats"]:
        info = beats.get(bid)
        if not info or not info.get("text"):
            continue
        text = info["text"]
        for t0, t1, s in split(text, info.get("char_times") or [0.0] * len(text), float(dur)):
            cues.append((start + t0, start + t1, s))
    return cues


def plain(path: Path):
    blocks = re.split(r"\n\s*\n", path.read_text("utf-8").strip())
    out = []
    for blk in blocks:
        ls = blk.strip().splitlines()
        if len(ls) >= 3:
            ls = ls[:2] + [srt_text(" ".join(ls[2:]))]
        out.append("\n".join(ls))
    path.write_text("\n\n".join(out) + "\n", "utf-8")
    print(f"[resrt] {path}: {len(blocks)} cues made readable")


def episode(d: Path):
    clips = assemble.chapter_clips(d)
    t, total = 0.0, []
    for c in clips:
        tl = c.with_suffix(".timeline.json")
        frames, fps, _, _ = assemble.probe(c)
        if tl.exists():
            cues = scene_cues(tl)
            write_srt(cues, c.with_suffix(".srt"))
            total += [(a + t, b + t, s) for a, b, s in cues]
            print(f"[resrt] {c.name}: {len(cues)} cues")
        else:
            print(f"[resrt] {c.name}: no timeline, skipped")
        t += frames / fps
    finals = sorted(d.glob("*_final.mp4"))
    target = finals[0].with_suffix(".srt") if finals else d / f"{d.name}_final.srt"
    write_srt(total, target)
    print(f"[resrt] {target}: {len(total)} cues, {t / 60:.1f} min")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="episode folders (timeline mode) or .srt files (with --plain)")
    ap.add_argument("--plain", action="store_true", help="only convert the text of existing .srt files")
    args = ap.parse_args()
    for p in map(Path, args.paths):
        if args.plain or p.suffix == ".srt":
            plain(p)
        else:
            episode(p.resolve())


if __name__ == "__main__":
    main()
