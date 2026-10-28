"""像素版整集渲染。

    python -m pixel.build ep01 --jobs 2                         # 整集（在项目根目录）：分场景并行渲染 + 混音 + 成片
    python -m pixel.build ep01 --only S01Hook,S02Rules --sheet  # 只看几个场景：每 2 秒一帧的联系表
    python -m pixel.build ep01 --still S03Arithmetic:12.5       # 单帧 PNG
    python -m pixel.build ep01 --check                          # 只排时间线 + 空白检查（不渲染视频）

输出在 output/epNN/：epNN_pixel.mp4、epNN_pixel.srt、chapters.txt、sheet_*.png、blank_report.txt。
"""
from __future__ import annotations

import argparse
import importlib
import math
import subprocess
import sys
import time
import wave
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw

PROD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROD))
from pixel import engine as E  # noqa: E402

MUSIC = PROD / "assets" / "music" / "theme.mp3"
OUT = PROD / "output"          # kepu 项目：output/<期>/


def load(tag):
    mod = importlib.import_module(f"pixel.{tag}")
    return mod.ep


# ------------------------------------------------------------------------------------------------ 音效
def _env(n, a=0.005, r=0.08):
    t = np.arange(n) / E.SR
    env = np.minimum(1, t / a) * np.exp(-t / r)
    return env


def _sq(freq, dur, duty=0.5):
    t = np.arange(int(dur * E.SR)) / E.SR
    return np.where((t * freq) % 1 < duty, 1.0, -1.0)


def synth_sfx(name):
    notes = {
        "blip": [(1046, 0.05)],
        "pop": [(784, 0.04), (1175, 0.06)],
        "open": [(523, 0.05), (659, 0.05), (784, 0.08)],
        "chest": [(523, 0.06), (659, 0.06), (784, 0.06), (1046, 0.16)],
        "error": [(196, 0.12), (147, 0.18)],
        "win": [(523, 0.08), (659, 0.08), (784, 0.08), (1046, 0.25)],
        "step": [(330, 0.03)],
        "select": [(880, 0.04), (1320, 0.05)],
        "hit": [(110, 0.08)],
        "type": [(1568, 0.015)],
    }.get(name, [(880, 0.05)])
    parts = []
    for f, d in notes:
        x = _sq(f, d, 0.25 if f > 600 else 0.5)
        parts.append(x * _env(len(x), r=max(0.03, d * 0.8)))
    y = np.concatenate(parts)
    return (y * 0.08).astype(np.float32)


# ------------------------------------------------------------------------------------------------ 渲染
def render_scene(args):
    tag, idx, out_path, fps = args
    ep = load(tag)
    scenes = ep.build()
    s = scenes[idx]
    n_frames = int(round(s.duration * fps))
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{E.FW}x{E.FH}",
           "-r", str(fps), "-i", "-", "-vf", f"scale={E.OUT_W}:{E.OUT_H}:flags=neighbor",
           "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-tune", "animation", "-pix_fmt", "yuv420p",
           "-r", str(fps), str(out_path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for i in range(n_frames):
        img = s.render(i / fps)
        p.stdin.write(img.tobytes())
    p.stdin.close()
    p.wait()
    return s.name, n_frames, time.time() - t0


def mix_audio(ep, scenes, offsets, total, out_wav):
    n = int(math.ceil(total * E.SR)) + E.SR
    track = np.zeros(n, dtype=np.float32)
    fx = np.zeros(n, dtype=np.float32)
    for s, off in zip(scenes, offsets):
        for nr in s.narr:
            a = int(round((off + nr["t"]) * E.SR))
            pcm = nr["rec"]["pcm"]
            track[a:a + len(pcm)] += pcm[: max(0, n - a)]
        for (t, name) in s.sfxs:
            a = int(round((off + t) * E.SR))
            y = synth_sfx(name)
            fx[a:a + len(y)] += y[: max(0, n - a)]
    track = track[: int(math.ceil(total * E.SR))]
    fx = fx[: len(track)]
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(E.SR)
        w.writeframes((np.clip(track, -1, 1) * 32767).astype(np.int16).tobytes())
    fx_wav = out_wav.with_name(out_wav.stem + "_sfx.wav")
    with wave.open(str(fx_wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(E.SR)
        w.writeframes((np.clip(fx, -1, 1) * 32767).astype(np.int16).tobytes())
    return fx_wav


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(scenes, offsets, path):
    cues = []
    for s, off in zip(scenes, offsets):
        for i, nr in enumerate(s.narr):
            pages = E.chunk_text(nr["text"])
            end_all = nr["t"] + nr["dur"]
            for k, (a, b) in enumerate(pages):
                st = nr["chars"][a]
                en = nr["chars"][pages[k + 1][0]] if k + 1 < len(pages) else end_all
                txt = nr["text"][a:b].rstrip("，、；：")
                cues.append((off + st, off + max(en, st + 0.4), txt))
    path.write_text("".join(f"{i + 1}\n{srt_time(a)} --> {srt_time(b)}\n{t}\n\n" for i, (a, b, t) in enumerate(cues)),
                    encoding="utf-8")


# ------------------------------------------------------------------------------------------------ 检查
def blank_report(s: E.Scene, step=0.5):
    """内容区（对话框以上）只剩背景的连续时段 ≥ 3 秒。"""
    out, run = [], None
    t = 0.0
    while t < s.duration:
        art = s.bg_at(t).copy()
        bg = art.copy()
        fine = Image.new("RGBA", (E.FW, E.FH), (0, 0, 0, 0))
        for fn in s.overlays:
            fn(art, t)
        for o in sorted(s.objs, key=lambda o: o.z):
            vis = o.at("vis", t)
            if vis > 0.001:
                E.draw_obj(o, t, vis, art, fine)
        diff = ImageChops.difference(art.crop((0, 0, 320, 136)), bg.crop((0, 0, 320, 136))).convert("L")
        frac = sum(1 for v_ in diff.getdata() if v_ > 20) / (320 * 136)
        fa = fine.getchannel("A").crop((0, 0, 640, 272))
        frac += sum(1 for v_ in fa.getdata() if v_ > 0) / (640 * 272)
        empty = frac < 0.004
        if empty and run is None:
            run = t
        if not empty and run is not None:
            if t - run >= 3:
                out.append((run, t))
            run = None
        t += step
    if run is not None and s.duration - run >= 3:
        out.append((run, s.duration))
    return out


def sheet(s: E.Scene, path, step=2.0, cols=6):
    ts = [i * step for i in range(int(s.duration / step) + 1)]
    tw, th = 320, 180
    rows = math.ceil(len(ts) / cols)
    im = Image.new("RGB", (cols * tw, rows * (th + 12)), (240, 240, 240))
    d = ImageDraw.Draw(im)
    for i, t in enumerate(ts):
        fr = s.render(min(t, s.duration - 1 / E.FPS)).resize((tw, th), Image.NEAREST)
        x, y = (i % cols) * tw, (i // cols) * (th + 12)
        im.paste(fr, (x, y + 12))
        d.text((x + 3, y), f"{s.name} {t:5.1f}s", fill=(0, 0, 0))
    im.save(path)


# ------------------------------------------------------------------------------------------------ 主程序
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tag")
    ap.add_argument("--only", default="")
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--step", type=float, default=2.0)
    ap.add_argument("--still", default="")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--jobs", type=int, default=5)
    ap.add_argument("--fps", type=int, default=E.FPS)
    a = ap.parse_args()
    ep = load(a.tag)
    out = OUT / a.tag
    out.mkdir(parents=True, exist_ok=True)
    only = [x for x in a.only.split(",") if x]
    scenes = ep.build()
    names = [s.name for s in scenes]
    if a.still:
        nm, t = a.still.split(":")
        s = scenes[names.index(nm)]
        p = out / f"still_{nm}_{float(t):.1f}.png"
        s.render(float(t)).resize((E.OUT_W, E.OUT_H), Image.NEAREST).save(p)
        print(p)
        return
    sel = [s for s in scenes if not only or s.name in only]
    total = sum(s.duration for s in scenes)
    print(f"{a.tag}: {len(scenes)} scenes, {total / 60:.1f} min")
    for s in sel:
        print(f"  {s.name:24s} {s.duration:7.1f}s  narr {len(s.narr)}")
    if a.check or a.sheet:
        rep = []
        for s in sel:
            for (t0, t1) in blank_report(s):
                rep.append(f"{s.name} {t0:.1f}-{t1:.1f}s ({t1 - t0:.1f}s)")
        (out / "blank_report.txt").write_text("\n".join(rep) + "\n", encoding="utf-8")
        print("blank stretches:", len(rep))
        for r in rep:
            print("  ", r)
        if a.sheet:
            for s in sel:
                p = out / f"sheet_{s.name}.png"
                sheet(s, p, a.step)
                print(p)
        return
    # 整集
    seg_dir = out / "segments"
    seg_dir.mkdir(exist_ok=True)
    jobs = [(a.tag, i, seg_dir / f"{i:02d}_{s.name}.mp4", a.fps) for i, s in enumerate(scenes)
            if not only or s.name in only]
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for name, nfr, dt in ex.map(render_scene, sorted(jobs, key=lambda j: -scenes[j[1]].duration)):
            print(f"  rendered {name}: {nfr} frames in {dt:.0f}s", flush=True)
    print(f"render done in {time.time() - t0:.0f}s")
    if only:
        return
    offsets, acc = [], 0.0
    for s in scenes:
        offsets.append(acc)
        acc += s.duration
    wav = out / "narration.wav"
    fx_wav = mix_audio(ep, scenes, offsets, acc, wav)
    write_srt(scenes, offsets, out / f"{a.tag}_pixel.srt")
    (out / "chapters.txt").write_text("".join(f"{int(o // 60):02d}:{int(o % 60):02d}  {s.title or s.name}\n"
                                              for s, o in zip(scenes, offsets)), encoding="utf-8")
    lst = out / "concat.txt"
    lst.write_text("".join(f"file '{seg_dir / f'{i:02d}_{s.name}.mp4'}'\n" for i, s in enumerate(scenes)))
    final = out / f"{a.tag}_pixel.mp4"
    fade_out_at = max(0.0, acc - 5)
    flt = (f"[2:a]aformat=channel_layouts=stereo,volume=0.15,afade=t=in:d=3,afade=t=out:st={fade_out_at:.2f}:d=5[bed];"
           f"[0:a]aformat=channel_layouts=stereo,asplit=2[voice][key];"
           f"[1:a]aformat=channel_layouts=stereo,volume=0.9[fx];"
           f"[bed][key]sidechaincompress=threshold=0.02:ratio=6:attack=30:release=600[ducked];"
           f"[voice][fx][ducked]amix=inputs=3:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
    if not MUSIC.exists():                      # no background music: a silent bed keeps the same filter graph
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "1",
                        str(out / "silence.wav")], check=True)
    bed = MUSIC if MUSIC.exists() else out / "silence.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), "-i", str(fx_wav), "-stream_loop", "-1",
                    "-i", str(bed), "-f", "concat", "-safe", "0", "-i", str(lst), "-filter_complex", flt,
                    "-map", "3:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-t", f"{acc:.3f}", "-movflags", "+faststart", str(final)], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(final), "-vf", "scale=1280:720:flags=neighbor",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "26", "-c:a", "aac", "-b:a", "96k",
                    "-movflags", "+faststart", str(out / f"{a.tag}_pixel_preview_720p.mp4")], check=True)
    print(f"done: {final} ({acc / 60:.1f} min) in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
