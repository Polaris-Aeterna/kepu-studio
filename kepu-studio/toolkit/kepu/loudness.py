"""成片响度：测量和一键校正（EBU R128，ffmpeg 的 loudnorm 滤镜；只改音轨，画面原样复制）。

    kepu loudness output/ep01/ep01.mp4            # 测：综合响度 LUFS、真峰值 dBTP、响度范围 LU
    kepu loudness output/ep01/ep01.mp4 --fix      # 两遍 loudnorm 校正到 kepu.toml [release] 的目标 → ep01.norm.mp4

为什么要管：B 站、YouTube 都会把响亮的视频压下去，太轻的却不会被拉上来；同一个系列每期忽大忽小，观众就得去调音量。
目标默认 −16 LUFS、真峰值 −1.5 dBTP（kepu.toml [release]）。gate 的 release 阶段会测成片。
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


def _loudnorm_json(stderr: str) -> dict:
    """The JSON block that loudnorm prints at the end of ffmpeg's stderr."""
    m = re.search(r"\{\s*\"input_i\"[^{}]*\}", stderr)
    if not m:
        raise RuntimeError("ffmpeg 没有输出 loudnorm 的测量结果")
    return json.loads(m.group(0))


def measure(path: Path, target: float = -16.0, tp: float = -1.5) -> dict:
    """-> {"I": LUFS, "TP": dBTP, "LRA": LU, "raw": loudnorm's json}."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("没有 ffmpeg")
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af",
                        f"loudnorm=I={target}:TP={tp}:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    d = _loudnorm_json(r.stderr)
    return {"I": float(d["input_i"]), "TP": float(d["input_tp"]), "LRA": float(d["input_lra"]), "raw": d}


def verdict(m: dict, cfg) -> tuple[bool, str]:
    target, tp = float(cfg.get("release", "lufs")), float(cfg.get("release", "true_peak"))
    tol = float(cfg.get("release", "lufs_tolerance"))
    ok = abs(m["I"] - target) <= tol and m["TP"] <= tp + 0.5
    return ok, f"{m['I']:.1f} LUFS，真峰值 {m['TP']:.1f} dBTP（目标 {target:.0f} ± {tol:g}，峰值 ≤ {tp:g}）"


AAC_MARGIN = 0.6      # dB: AAC encoding overshoots the true peak; aim this much lower so the .mp4 stays under the ceiling


def normalize(src: Path, dst: Path, target: float = -16.0, tp: float = -1.5) -> dict:
    """Two-pass loudnorm (linear when possible); video stream copied untouched. Returns the measurement of dst."""
    video = Path(dst).suffix.lower() in (".mp4", ".mov", ".mkv", ".webm")
    tp_aim = tp - AAC_MARGIN if video else tp
    m = measure(src, target, tp_aim)["raw"]
    af = (f"loudnorm=I={target}:TP={tp_aim}:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-af", af, "-ar", "48000"]
    cmd += (["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"] if video else [])
    subprocess.run(cmd + [str(dst)], check=True)
    return measure(dst, target, tp)


def main(path: Path, cfg, fix: bool = False, out: Path | None = None) -> int:
    target, tp = float(cfg.get("release", "lufs")), float(cfg.get("release", "true_peak"))
    m = measure(path, target, tp)
    ok, msg = verdict(m, cfg)
    print(f"[loudness] {Path(path).name}：{msg}，响度范围 {m['LRA']:.1f} LU  {'✓' if ok else '✗'}")
    if not fix:
        if not ok:
            print(f"[loudness] 校正：kepu loudness {path} --fix")
        return 0 if ok else 1
    dst = out or Path(path).with_name(Path(path).stem + ".norm" + Path(path).suffix)
    m2 = normalize(Path(path), dst, target, tp)
    ok2, msg2 = verdict(m2, cfg)
    print(f"[loudness] → {dst}：{msg2}  {'✓' if ok2 else '✗'}")
    return 0 if ok2 else 1
