"""耳检包：合成之后，只听高风险的几十处，而不是整集。

    kepu earcheck build script/episodes/ep01.md      # → review/earcheck/ep01/index.html（每处 2–3 秒的片段）
    kepu earcheck ingest 下载的结果.json              # 听完点“导出”，把结果喂回来：记进音色档案、列出要重录的 beat

收录：送拼音的（没有替身字）、第一次用的新替身字、还没在这个音色上验证的希腊字母读法、词典给了非默认读音的低频词、
缩写（逐字母念还是当单词念）、第一处数字，再加 5 处随机抽查的已强制替身字（对照组：确认“确定的”也真的念对了）。
教训（《地基之下》）：whisper 判断不了读音，会按上下文把念错的也写成对的；全片人耳复听又太贵——所以只听这几十处。
作者听过“对”的会记进音色档案（~/.kepu/voices/），以后同一个音色不再收录。
"""
from __future__ import annotations

import base64
import html
import json
import random
import re
import shutil
import subprocess
from pathlib import Path

from . import script as S
from .pron.greek import load_profile, save_profile
from .pron.inventory import standin_reading
from .timing import write_wav_slice
from .util import ASSETS
from .voice import chapter_id

EMBED_LIMIT = 15_000_000           # bytes of audio embedded in the page (one file: open it anywhere, send it to anyone)


def _mp3(wav: Path) -> bytes | None:
    """A small mono mp3 of a clip (for embedding); None when ffmpeg is missing or fails."""
    if not shutil.which("ffmpeg"):
        return None
    mp3 = wav.with_suffix(".mp3")
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-ac", "1", "-b:a", "64k", str(mp3)])
    return mp3.read_bytes() if r.returncode == 0 and mp3.exists() else None


KIND = {"pinyin": "拼音兜底", "standin": "新替身字", "greek": "希腊字母", "auto": "低频词", "latin": "缩写",
        "number": "数字", "control": "抽查"}


def _pick(beats: dict, profile: dict, n_control: int = 5) -> list[dict]:
    seen, out, controls = set(), [], []
    for bid, b in beats.items():
        for r in b.get("pron", []):
            k = r["kind"]
            key = (k, r.get("say") or r.get("char"), r.get("reading")) if k != "number" else ("number",)
            if k in ("standin",) and r["say"] in profile.get("standins_ok", []):
                continue
            if k == "pinyin" and r["reading"] in profile.get("pinyin_ok", []):
                continue
            if k == "greek" and profile.get("greek", {}).get(r["char"], {}).get("verified") and not r.get("watch"):
                continue
            if key in seen and k != "pinyin":
                continue
            seen.add(key)
            out.append({**r, "beat": bid})
        sr = standin_reading()
        tts, spoken = b.get("tts", ""), b.get("spoken", "")
        if len(tts) == len(spoken):                          # 1:1 stand-ins only (no Greek / symbol expansion)
            for i, (a, t) in enumerate(zip(spoken, tts)):
                if a != t and t in sr:
                    controls.append({"i": i, "kind": "control", "char": a, "reading": sr[t], "say": t, "beat": bid,
                                     "why": "已强制的替身字，抽查", "ctx": spoken[max(0, i - 8):i] + "【" + a + "】" + spoken[i + 1:i + 7]})
    random.Random(7).shuffle(controls)
    return out + controls[:n_control]


def build(script: Path, cfg, out_dir: Path | None = None) -> Path:
    chapter = chapter_id(script)
    bj = cfg.path("project", "audio") / chapter / "beats.json"
    if not bj.exists():
        raise SystemExit(f"[earcheck] 没有 {bj}：先 kepu voice {script}")
    meta = json.loads(bj.read_text("utf-8"))
    beats = meta["beats"]
    prof = load_profile(cfg.voice_key, cfg.root)
    spots = _pick(beats, prof)
    out_dir = out_dir or cfg.path("project", "review") / "earcheck" / chapter
    (out_dir / "clips").mkdir(parents=True, exist_ok=True)
    rows = []
    for n, sp in enumerate(spots, 1):
        b = beats[sp["beat"]]
        words = b.get("words", [])
        i = min(sp["i"], len(words) - 1) if words else 0
        t0 = (words[i][1] if words and words[i][1] is not None else (words[i][2] if words else 0.0))
        t1 = words[i][2] if words else 0.0
        clip = out_dir / "clips" / f"{n:03d}_{sp['beat']}.wav"
        write_wav_slice(bj.parent / b["file"], clip, max(0.0, t0 - 1.3), t1 + 0.9)
        rows.append({"n": n, "beat": sp["beat"], "kind": sp["kind"], "char": sp.get("char", ""), "reading": sp.get("reading", ""),
                     "say": sp.get("say", ""), "why": sp.get("why", ""), "ctx": sp.get("ctx", ""), "t": round(t0, 2),
                     "clip": f"clips/{clip.name}", "_mp3": _mp3(clip)})
    embed = all(r["_mp3"] for r in rows) and sum(len(r["_mp3"]) for r in rows) <= EMBED_LIMIT
    for r in rows:
        data = r.pop("_mp3")
        if embed:
            r["clip"] = "data:audio/mpeg;base64," + base64.b64encode(data).decode()
    page = (ASSETS / "earcheck.html").read_text(encoding="utf-8")
    page = page.replace("__TITLE__", html.escape(f"耳检 · {chapter}")).replace(
        "__DATA__", json.dumps({"chapter": chapter, "voice_key": cfg.voice_key, "kinds": KIND, "rows": rows},
                               ensure_ascii=False))
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    (out_dir / "spots.json").write_text(json.dumps([{k: v for k, v in r.items() if k != "clip" or not embed} for r in rows],
                                                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[earcheck] {chapter}：{len(rows)} 处，{sum(1 for r in rows if r['kind'] == 'control')} 处抽查 → {out_dir / 'index.html'}"
          + ("（单个文件，音频已内嵌，可以直接发给别人听）" if embed else "（音频在 clips/，连同文件夹一起打开）"))
    by = {}
    for r in rows:
        by[r["kind"]] = by.get(r["kind"], 0) + 1
    print("[earcheck] " + "，".join(f"{KIND.get(k, k)} {v}" for k, v in by.items()))
    return out_dir / "index.html"


def ingest(results: Path, cfg) -> int:
    """results: the JSON exported by the page: {"chapter", "voice_key", "results": [{n, beat, kind, char, reading, say, ok, note}]}"""
    d = json.loads(Path(results).read_text("utf-8"))
    key = d.get("voice_key") or cfg.voice_key
    upd = {"greek": {}, "standins_ok": [], "standins_bad": [], "pinyin_ok": []}
    redo = []
    for r in d.get("results", []):
        if r.get("ok") is None:
            continue
        k = r["kind"]
        if r["ok"]:
            if k in ("standin", "control"):
                upd["standins_ok"].append(r["say"])
            elif k == "pinyin":
                upd["pinyin_ok"].append(r["reading"])
            elif k == "greek":
                upd["greek"][r["char"]] = {"say": r["say"], "verified": True}
        else:
            redo.append(r)
            if k in ("standin", "control"):
                upd["standins_bad"].append(r["say"])
    p = save_profile(key, upd)
    print(f"[earcheck] 记进音色档案 {p}：替身字 ✓{len(upd['standins_ok'])} ✗{len(upd['standins_bad'])}，"
          f"拼音 ✓{len(upd['pinyin_ok'])}，希腊字母 ✓{len(upd['greek'])}")
    st = cfg.path("project", "review") / "earcheck" / d.get("chapter", "unknown") / "status.json"
    st.parent.mkdir(parents=True, exist_ok=True)
    checked = sum(1 for r in d.get("results", []) if r.get("ok") is not None)
    st.write_text(json.dumps({"checked": checked, "bad": len(redo), "beats": sorted({r['beat'] for r in redo}),
                              "date": __import__("time").strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False), "utf-8")
    if not redo:
        print("[earcheck] 全部念对。")
        return 0
    print(f"[earcheck] {len(redo)} 处念错，要处理后重录这些 beat：{' '.join(sorted({r['beat'] for r in redo}))}")
    for r in redo:
        how = {"standin": f"替身字“{r['say']}”已记为不可用，重录会换下一个替身字",
               "control": f"替身字“{r['say']}”已记为不可用，重录会换下一个替身字",
               "pinyin": "改写绕开（见 lint 的改写建议），或换一个说法",
               "greek": f"换一个拼写：kepu greek audition --letters {r['char']}",
               "auto": f"在项目词典里定读音：kepu lexicon add \"…{r['char']}〔正确读音〕…\"",
               "latin": "在读法一侧写清楚：{ETH|E T H} 或改成中文",
               "number": "把数字写进 {显示|读法}"}.get(r["kind"], "")
        note = f"（作者备注：{r['note']}）" if r.get("note") else ""
        print(f"  beat {r['beat']} {r['ctx']}  应念 {r['reading'] or r['say']}：{how}{note}")
    out = Path(results).with_name("redo.json")
    out.write_text(json.dumps(redo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[earcheck] 清单写在 {out}；改完再 kepu voice <稿子> --only {' '.join(sorted({r['beat'] for r in redo}))}")
    return 1
