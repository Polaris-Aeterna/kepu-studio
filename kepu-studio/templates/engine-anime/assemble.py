#!/usr/bin/env python
"""
Concatenate rendered chapter videos (with narration) into output/final.mp4.

    engine/.venv/bin/python engine/assemble.py                    # all episodes/ep*_*/ (and legacy chapters/ch*_*/)
    engine/.venv/bin/python engine/assemble.py ep1 ep2 -o output/preview.mp4
    engine/.venv/bin/python engine/assemble.py --dirs engine/demo  # any folder(s) with videos/
    engine/.venv/bin/python engine/assemble.py ep1 --lang en -o output/en/ep1.mp4   # English: episodes_en/ep1_*/

Clip order inside a chapter folder:
    1. if <chapter>/order.txt exists: one scene name (or mp4 file name) per line, '#' comments ok
    2. else: all <chapter>/videos/*.mp4 sorted by file name  (so name scenes Ch01_01_..., Ch01_02_...)

Video streams are stream-copied (all clips must be 1920x1080 @ 30fps h264, i.e. rendered with
render.sh at default quality). Audio is decoded, padded to exactly each clip's video length,
concatenated as PCM and encoded once -> no A/V drift across clips. Clips without audio get silence.
Per-clip .srt files (written by NarratedScene) are merged into <out>.srt.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
ROOT = ENGINE.parent
FPS = 30
RES = "1920x1080"
TARGET_LUFS, TARGET_TP, TARGET_LRA = -16.0, -1.5, 11.0
AAC_MARGIN = 0.6     # dB: AAC encoding overshoots true peak; normalise to TP - margin so the .mp4 stays under TP
sys.path.insert(0, str(ENGINE))
from subtitles import srt_text  # noqa: E402
import langs  # noqa: E402


def _loudnorm_json(stderr: str) -> dict:
    j = stderr[stderr.rfind("{"):stderr.rfind("}") + 1]
    return json.loads(j)


def loudnorm_two_pass(src: Path, dst: Path, lufs: float, tp: float, lra: float = TARGET_LRA) -> dict:
    """EBU R128 two-pass loudnorm on a PCM file: measure, then apply the measured values with linear=true.
    Returns the second pass' report (normalization_type should be 'linear')."""
    base = f"loudnorm=I={lufs}:TP={tp}:LRA={lra}"
    r1 = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(src), "-af", base + ":print_format=json", "-f", "null", "-"])
    m = _loudnorm_json(r1.stderr)
    f2 = (f"{base}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=json")
    r2 = run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", str(src), "-af", f2, "-ar", "48000",
              "-c:a", "pcm_s16le", str(dst)])
    if r2.returncode:
        raise RuntimeError(r2.stderr[-800:])
    rep = _loudnorm_json(r2.stderr)
    rep["measured_input_i"] = m["input_i"]
    return rep


def measure_lufs(path: Path) -> tuple[float, float]:
    """(integrated LUFS, true peak dBTP) via ebur128."""
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
             "-af", "ebur128=peak=true", "-f", "null", "-"])
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s*(-?[\d.]+) LUFS", tail)
    pk = re.search(r"Peak:\s*(-?[\d.]+) dBFS", tail)
    return (float(i.group(1)) if i else float("nan"), float(pk.group(1)) if pk else float("nan"))


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe(path: Path):
    """(frames, fps, resolution, has_audio) without ffprobe."""
    r = run(["ffmpeg", "-hide_banner", "-i", str(path), "-map", "0:v:0", "-c", "copy", "-f", "null", "-"])
    err = r.stderr
    frames = [int(x) for x in re.findall(r"frame=\s*(\d+)", err)]
    m = re.search(r"Video:.*?(\d{3,5}x\d{3,5}).*?([\d.]+) fps", err)
    has_audio = bool(re.search(r"Stream #\d+:\d+.*Audio:", err))
    if not frames or not m:
        raise RuntimeError(f"cannot probe {path}:\n{err[-800:]}")
    return frames[-1], float(m.group(2)), m.group(1), has_audio


def chapter_clips(ch_dir: Path) -> list[Path]:
    vids = ch_dir / "videos"
    order = ch_dir / "order.txt"
    if order.exists():
        clips = []
        for line in order.read_text("utf-8").splitlines():
            line = line.split("#")[0].strip()
            if not line:
                continue
            p = vids / (line if line.endswith(".mp4") else line + ".mp4")
            if not p.exists():
                sys.exit(f"[assemble] {order}: missing {p}")
            clips.append(p)
        return clips
    return sorted(p for p in vids.glob("*.mp4") if not p.stem.endswith("_temp"))


def find_chapter_dirs(ids: list[str], lang: str = "zh") -> list[Path]:
    if lang != "zh":
        all_dirs = sorted(p for p in langs.episodes_root(lang).glob("ep*") if p.is_dir())
    else:
        all_dirs = sorted(p for p in (ROOT / "episodes").glob("ep*") if p.is_dir()) + \
            sorted(p for p in (ROOT / "chapters").glob("ch*") if p.is_dir())
    if not ids:
        return all_dirs
    out = []
    for i in ids:
        hit = [p for p in all_dirs if p.name == i or p.name.startswith(i + "_")]
        if not hit:
            sys.exit(f"[assemble] no chapter folder for {i!r}")
        out += hit
    return out


def parse_srt(path: Path):
    def ts(s):
        h, m, rest = s.split(":")
        sec, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000
    out = []
    for block in re.split(r"\n\s*\n", path.read_text("utf-8").strip()):
        lines = block.strip().splitlines()
        if len(lines) >= 3 and "-->" in lines[1]:
            a, b = [x.strip() for x in lines[1].split("-->")]
            out.append((ts(a), ts(b), "\n".join(lines[2:])))
    return out


def fmt_ts(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chapters", nargs="*", help="chapter ids like ch01 (default: all)")
    ap.add_argument("--dirs", nargs="*", help="explicit folders (each containing videos/)")
    ap.add_argument("-o", "--out", default=str(ROOT / "output" / "final.mp4"))
    ap.add_argument("--loudnorm", action="store_true", help="(default now; kept for old command lines)")
    ap.add_argument("--no-loudnorm", action="store_true", help="skip loudness normalisation")
    ap.add_argument("--lufs", type=float, default=TARGET_LUFS, help="integrated loudness target (default -16)")
    ap.add_argument("--tp", type=float, default=TARGET_TP, help="true-peak ceiling in dBTP (default -1.5)")
    ap.add_argument("--gap", type=float, default=0.0, help="black+silence seconds between chapters")
    ap.add_argument("--lang", choices=list(langs.LANGS), default="zh",
                    help="en: chapter ids are looked up in episodes_en/ (default output output/en/final.mp4)")
    args = ap.parse_args()
    if args.lang != "zh" and args.out == str(ROOT / "output" / "final.mp4"):
        args.out = str(ROOT / "output" / args.lang / "final.mp4")

    dirs = [Path(d).resolve() for d in args.dirs] if args.dirs else find_chapter_dirs(args.chapters, args.lang)
    clips = []
    for d in dirs:
        cs = chapter_clips(d)
        if not cs:
            print(f"[assemble] warning: no clips in {d}/videos", file=sys.stderr)
        clips += [(d, c) for c in cs]
    if not clips:
        sys.exit("[assemble] nothing to assemble")

    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="assemble_"))
    try:
        vlist, alist, srt, t = [], [], [], 0.0
        prev_dir = None
        gap_clip = None
        for k, (d, c) in enumerate(clips):
            if args.gap > 0 and prev_dir is not None and d != prev_dir:
                if gap_clip is None:
                    gap_clip = tmp / "gap.mp4"
                    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                         f"color=c=0x12141C:s={RES}:r={FPS}:d={args.gap}",
                         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(gap_clip)], check=True)
                    gw = tmp / "gap.wav"
                    run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                         "anullsrc=r=48000:cl=stereo", "-t", f"{args.gap}", "-c:a", "pcm_s16le", str(gw)],
                        check=True)
                vlist.append(gap_clip)
                alist.append(tmp / "gap.wav")
                t += round(args.gap * FPS) / FPS
            prev_dir = d
            frames, fps, res, has_audio = probe(c)
            if res != RES or abs(fps - FPS) > 0.01:
                sys.exit(f"[assemble] {c} is {res}@{fps}; expected {RES}@{FPS}. Re-render with render.sh (no QUALITY=low).")
            dur = frames / fps
            wav = tmp / f"a{k:04d}.wav"
            if has_audio:
                cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(c), "-vn", "-ac", "2", "-ar", "48000",
                       "-af", "apad", "-t", f"{dur:.6f}", "-c:a", "pcm_s16le", str(wav)]
            else:
                cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                       "-t", f"{dur:.6f}", "-c:a", "pcm_s16le", str(wav)]
            run(cmd, check=True)
            vlist.append(c)
            alist.append(wav)
            s = c.with_suffix(".srt")
            if s.exists():
                srt += [(a + t, b + t, txt) for a, b, txt in parse_srt(s)]
            tl = c.with_suffix(".timeline.json")
            if tl.exists() and json.loads(tl.read_text("utf-8")).get("placeholder_beats"):
                print(f"[assemble] WARNING {c.name}: placeholder audio in beats "
                      f"{' '.join(json.loads(tl.read_text('utf-8'))['placeholder_beats'])} (not final)")
            print(f"[assemble] {t:8.2f}s  +{dur:7.2f}s  {c.relative_to(ROOT) if c.is_relative_to(ROOT) else c}"
                  f"{'' if has_audio else '  (no audio)'}")
            t += dur

        def write_list(paths, name):
            f = tmp / name
            f.write_text("".join(f"file '{p}'\n" for p in paths), "utf-8")
            return f

        vcat = tmp / "video.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(write_list(vlist, "v.txt")),
             "-c", "copy", "-an", str(vcat)], check=True)
        acat = tmp / "audio.wav"
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(write_list(alist, "a.txt")),
             "-c", "copy", str(acat)], check=True)
        if not args.no_loudnorm:
            anorm = tmp / "audio_norm.wav"
            rep = loudnorm_two_pass(acat, anorm, args.lufs, args.tp - AAC_MARGIN)
            print(f"[assemble] loudnorm: input {rep['measured_input_i']} LUFS -> target {args.lufs} LUFS, "
                  f"TP {args.tp} dBTP ({rep.get('normalization_type', '?')}: 'dynamic' = linear gain + "
                  f"look-ahead peak limiting, needed when the source peaks are too high for pure gain)")
            acat = anorm
        r = run(["ffmpeg", "-v", "error", "-y", "-i", str(vcat), "-i", str(acat), "-map", "0:v:0", "-map", "1:a:0",
                 "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])
        if r.returncode:
            sys.exit(r.stderr)
        if srt:
            lines = []
            for i, (a, b, txt) in enumerate(srt, 1):
                lines += [str(i), f"{fmt_ts(a)} --> {fmt_ts(b)}", srt_text(txt), ""]
            out.with_suffix(".srt").write_text("\n".join(lines), "utf-8")
        print(f"[assemble] {len(clips)} clips, {t:.2f}s ({t / 60:.1f} min) -> {out}")
        li, pk = measure_lufs(out)
        print(f"[assemble] final loudness {li:.1f} LUFS, true peak {pk:.1f} dBTP")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
