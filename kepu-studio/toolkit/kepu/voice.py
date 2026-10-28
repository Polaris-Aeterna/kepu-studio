"""稿子 → 每个 beat 一条配音 + 逐字时间（来源：《ETH》engine/tts.py；做法与《地基之下》lib/eleven_voice.py 一致）。

    kepu voice script/episodes/ep01.md --dry          # 免费：字符数、读音决定、被拦下的句子、剩余额度
    kepu voice script/episodes/ep01.md --only 03 04   # 合成（花钱：先 --dry、先问）；默认一次最多 2000 字符
    kepu voice script/episodes/ep01.md --engine edge  # 免费占位配音（微软 edge-tts，要联网）
    kepu quota                                        # ElevenLabs 剩余额度（免费接口）

输出 <audio>/<期>/：beatNN.wav（48 kHz 单声道）、beats.json（每个 beat 的显示文字、念的文字、发给模型的文字、
逐字时间 char_times、读音记录 pron）、durations.json。beats.json 的格式与《ETH》引擎一致，NarratedScene 直接能用。
原始录音按“发给模型的文字 + 音色参数”缓存在 <audio>/_cache/，合成完立刻存盘：脚本崩了也不丢已经付过钱的录音；
只有改过的句子才会重新花钱。缓存键的算法与《ETH》相同，可以把 voice.cache 指向 ETH 的 engine/audio/_cache 直接复用。
API key：环境变量 ELEVENLABS_API_KEY，或 voice.env_file 指向的 .env；运行时读取，从不打印、不写进日志和缓存。
"""
from __future__ import annotations

import base64
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from . import script as S
from .pron.speak import Prepared, describe, prepare
from .timing import find_pauses, insert_silence, snap_to_pauses, wav_duration
from .util import pad

SAMPLE_RATE = 48000


@dataclass
class BeatPrep:
    beat: S.Beat
    display: str
    clean: str
    map: list                 # clean index -> display index
    p: Prepared
    pauses: list              # [(clean index, seconds)]

    @property
    def tts(self) -> str:
        return self.p.tts


def prep_beat(beat: S.Beat, pcfg) -> BeatPrep:
    display, spoken_m, map_m = S.split_beat(beat.narration)
    removed = set()
    for m in S.MARK.finditer(spoken_m):
        removed.update(range(m.start(), m.end()))
    p = prepare(spoken_m, pcfg)
    cmap = [d for i, d in enumerate(map_m) if i not in removed]
    assert len(cmap) == len(p.clean), (len(cmap), len(p.clean))
    pauses = []
    for d, sec in beat.pauses:
        k = next((k for k, dd in enumerate(cmap) if dd >= d), len(cmap))
        pauses.append((k, sec))
    return BeatPrep(beat, display, p.clean, cmap, p, pauses)


def chapter_id(path: Path) -> str:
    m = re.match(r"((?:s\d+)?(?:ch|ep)\d+)", path.stem)
    return m.group(1) if m else path.stem


# ------------------------------------------------------------------------------------------------ credentials
def api_key(cfg) -> str:
    if os.environ.get("ELEVENLABS_API_KEY"):
        return os.environ["ELEVENLABS_API_KEY"]
    env = cfg.path("voice", "env_file")
    if env.exists():
        for ln in env.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln.startswith("ELEVENLABS_API_KEY") and "=" in ln:
                return ln.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit(f"[voice] 没找到 ELEVENLABS_API_KEY（环境变量，或 {env}）。不合成也能用 --engine edge 做免费占位配音。")


def quota(cfg) -> dict:
    req = urllib.request.Request("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": api_key(cfg)})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read())
    used, limit = d.get("character_count", 0), d.get("character_limit", 0)
    reset = d.get("next_character_count_reset_unix")
    return {"tier": d.get("tier"), "used": used, "limit": limit, "remaining": limit - used,
            "reset": datetime.datetime.fromtimestamp(reset).strftime("%Y-%m-%d %H:%M") if reset else "?"}


# ------------------------------------------------------------------------------------------------ engines
def settings(cfg, engine: str) -> dict:
    v = lambda k: cfg.get("voice", k)  # noqa: E731
    if engine == "eleven":
        d = {"model": v("model"), "voice": v("voice_id"), "speed": v("speed"), "stability": v("stability"),
             "format": v("output_format")}
        if v("similarity_boost") is not None:
            d["similarity_boost"] = v("similarity_boost")
        return d
    return {"voice": v("edge_voice") if engine == "edge" else v("say_voice")}


def cache_key(tts: str, engine: str, st: dict) -> str:
    """Same algorithm as ETH engine/tts.py for Chinese, so existing takes are reused."""
    params = [tts, engine]
    if engine == "eleven":
        params += [st["model"], st["voice"], st["speed"], st["stability"], st["format"]]
        if "similarity_boost" in st:
            params.append(st["similarity_boost"])
    else:
        params += [st["voice"]]
    return engine + "-" + hashlib.sha1(json.dumps(params, ensure_ascii=False).encode()).hexdigest()[:16]


def synth_eleven(tts: str, st: dict, key: str):
    body = {"text": tts, "model_id": st["model"], "voice_settings": {"stability": st["stability"], "speed": st["speed"]}}
    if "similarity_boost" in st:
        body["voice_settings"]["similarity_boost"] = st["similarity_boost"]
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{st['voice']}/with-timestamps?output_format={st['format']}"
    req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), method="POST",
                                 headers={"xi-api-key": key, "Content-Type": "application/json"})
    last = ""
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read())
            al = d.get("alignment") or {}
            times = list(zip(al.get("character_start_times_seconds", []), al.get("character_end_times_seconds", [])))
            return base64.b64decode(d["audio_base64"]), times
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:200].decode(errors='ignore')}"
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(4 * (attempt + 1))
                continue
            raise RuntimeError(last) from e
        except (urllib.error.URLError, TimeoutError) as e:
            last = str(e)
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"ElevenLabs failed after retries: {last}")


def _chars_from_words(tts: str, words):
    times = [None] * len(tts)
    cur = 0
    for s, e, w in words:
        w = w.strip()
        idx = tts.find(w, cur) if w else -1
        if idx < 0 or idx - cur > 30:
            continue
        for k in range(len(w)):
            times[idx + k] = (s + (e - s) * k / len(w), s + (e - s) * (k + 1) / len(w))
        cur = idx + len(w)
    last = (0.0, 0.0)
    for i, t in enumerate(times):
        times[i] = last = t if t else (last[1], last[1])
    return times


def synth_offline(tts: str, engine: str, st: dict):
    with tempfile.TemporaryDirectory() as td:
        if engine == "edge":
            try:
                import asyncio

                import edge_tts
            except ImportError:
                raise SystemExit("[voice] 免费占位配音需要 edge-tts：pip install edge-tts")

            async def go(out):
                comm = edge_tts.Communicate(tts, st["voice"], boundary="WordBoundary")
                words = []
                with open(out, "wb") as f:
                    async for ch in comm.stream():
                        if ch["type"] == "audio":
                            f.write(ch["data"])
                        elif ch["type"] == "WordBoundary":
                            s0 = ch["offset"] / 1e7
                            words.append((s0, s0 + ch["duration"] / 1e7, ch["text"]))
                return words
            mp3 = Path(td) / "x.mp3"
            words = asyncio.run(go(mp3))
            return mp3.read_bytes(), _chars_from_words(tts, words)
        aiff, mp3 = Path(td) / "x.aiff", Path(td) / "x.mp3"
        subprocess.run(["say", "-v", st["voice"], "-o", str(aiff), tts], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(aiff), str(mp3)], check=True)
        wav = to_wav(mp3, Path(td) / "x.wav")
        dur, n = wav_duration(wav), max(1, len(tts))
        return mp3.read_bytes(), [(dur * k / n, dur * (k + 1) / n) for k in range(n)]


def take(tts: str, engine: str, st: dict, cache_dir: Path, cfg):
    """Cached synthesis -> (mp3 path, per-tts-char times, from_cache)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = cache_key(tts, engine, st)
    mp3, meta = cache_dir / f"{key}.mp3", cache_dir / f"{key}.json"
    if mp3.exists() and meta.exists():
        return mp3, [tuple(t) for t in json.loads(meta.read_text("utf-8"))["times"]], True
    if engine == "eleven":
        audio, times = synth_eleven(tts, st, api_key(cfg))
    else:
        audio, times = synth_offline(tts, engine, st)
    mp3.write_bytes(audio)                                  # saved at once: a crash never loses a paid take
    meta.write_text(json.dumps({"tts": tts, "engine": engine, **st, "times": times,
                                "created": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False), "utf-8")
    return mp3, times, False


LEDGER_HEAD = "# kepu 的花钱记录：每一条付过钱的合成一行（kepu voice / greek audition 自动写，缓存命中不记）\n" \
              "date\tchapter\tbeat\tchars\tengine\tvoice\tmodel\n"


def ledger_add(cfg, chapter: str, beat: str, chars: int, engine: str, st: dict):
    """Append one paid synthesis to <review>/cost.tsv (written per take, so a crash never loses the record)."""
    if engine != "eleven" or cfg.root is None:
        return
    p = cfg.path("project", "review") / "cost.tsv"
    p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists()
    with p.open("a", encoding="utf-8") as f:
        if new:
            f.write(LEDGER_HEAD)
        f.write(f"{time.strftime('%Y-%m-%d %H:%M')}\t{chapter}\t{beat}\t{chars}\t{engine}\t{st.get('voice', '')}\t"
                f"{st.get('model', '')}\n")


def ledger(cfg) -> list[dict]:
    p = cfg.path("project", "review") / "cost.tsv" if cfg.root else None
    if not p or not p.exists():
        return []
    rows = [ln.split("\t") for ln in p.read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("#")]
    head, body = rows[0], rows[1:]
    return [dict(zip(head, r)) | {"chars": int(r[3])} for r in body if len(r) >= 4 and r[3].isdigit()]


def ledger_summary(cfg) -> str:
    rows = ledger(cfg)
    if not rows:
        return ""
    by: dict[str, int] = {}
    for r in rows:
        by[r["chapter"]] = by.get(r["chapter"], 0) + r["chars"]
    return (f"本项目记账 {len(rows)} 条合成、共 {sum(by.values()):,} 字符：" +
            "，".join(f"{k} {v:,}" for k, v in by.items()) + f"（最近 {rows[-1]['date']}）")


def to_wav(src: Path, dst: Path) -> Path:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", str(SAMPLE_RATE), "-sample_fmt", "s16",
                    str(dst)], check=True)
    return dst


# ------------------------------------------------------------------------------------------------ timing
def beat_timing(bp: BeatPrep, times, wav: Path, duration: float):
    """-> (display char start times, per-clean-char [char, start, end]) pause-corrected."""
    ok = len(times) == len(bp.tts)
    chars = []
    for ch, a, b in bp.p.spans:
        segt = times[a:b] if ok else []
        if segt:
            chars.append((ch, min(s for s, _ in segt), max(e for _, e in segt)))
        else:
            chars.append((ch, None, chars[-1][2] if chars else 0.0))
    if ok:
        chars = snap_to_pauses(chars, find_pauses(wav))
    else:
        print(f"[voice]   WARN 对齐长度 {len(times)} ≠ 文字长度 {len(bp.tts)}，时间按字数估计")
        n = max(1, len(chars))
        chars = [(c, duration * k / n, duration * (k + 1) / n) for k, (c, _, _) in enumerate(chars)]
    disp = [None] * len(bp.display)
    for k, (c, s, e) in enumerate(chars):
        d = bp.map[k] if k < len(bp.map) else len(bp.display) - 1
        if s is not None and 0 <= d < len(disp) and disp[d] is None:
            disp[d] = round(s, 3)
    last = 0.0
    for i, t in enumerate(disp):
        disp[i] = last = t if t is not None else last
    return disp, [[c, None if s is None else round(s, 3), round(e, 3)] for c, s, e in chars]


# ------------------------------------------------------------------------------------------------ report
def report_beat(bid: str, bp: BeatPrep, status: str, verbose: bool):
    p = bp.p
    flag = " HELD" if p.blocked else ""
    print(f"[voice] beat {bid}: {status}{flag}")
    for s in p.spots:
        if s.open or s.status == "pinyin" or (verbose and s.status in ("ok", "auto") and s.source != "default"):
            print("     " + describe(s))
            if s.open:
                print("       " + suggestion(p.clean, s))
    for ctx, why in p.held:
        print(f"     ✗ 读法   {pad(ctx, 34)}{why}")
    for n in p.notes:
        print(f"     ? {n}")


def suggestion(text: str, s) -> str:
    """A ready-to-run fix for a held spot: a mark for this place, or a lexicon entry that covers the whole trap."""
    opts = [r for r in s.suggest if r and r != "?"]
    if not opts:
        return ""
    lo, hi = s.span if s.span else (max(0, s.i - 1), min(len(text), s.i + 2))
    while lo > 0 and hi - lo < 3 and text[lo - 1].strip() and text[lo - 1] not in "，。；：！？、":
        lo -= 1
    ctx = text[lo:hi]
    k = s.i - lo
    pick = s.default if s.default in opts else opts[0]
    entry = ctx[:k + 1] + f"〔{pick}〕" + ctx[k + 1:]
    alt = " 或 ".join(f"{s.char}〔{r}〕" for r in opts)
    rw = f"；或改写：{s.rewrite}" if s.rewrite else ""
    return (f"→ 稿子里标 {alt}（只管这一处）；以后都这么念：kepu lexicon add \"{entry}\""
            f"（〔〕里换成正确的读音）{rw}")


# ------------------------------------------------------------------------------------------------ main
def run(script: Path, cfg, *, dry=False, only=None, engine=None, max_chars=None, force=False, verbose=False,
        out_root: Path | None = None) -> int:
    ep = S.parse(script)
    pcfg = cfg.pron()
    engine = engine or cfg.get("voice", "engine")
    st = settings(cfg, engine)
    chapter = chapter_id(script)
    root = out_root or cfg.path("project", "audio")
    out_dir = root / chapter
    cache_dir = Path(cfg.get("voice", "cache")) if cfg.get("voice", "cache") else root / "_cache"
    if not cache_dir.is_absolute() and cfg.root:
        cache_dir = cfg.root / cache_dir
    max_chars = int(max_chars or cfg.get("voice", "max_chars"))
    for ln, msg in ep.problems:
        print(f"[voice] 稿子第 {ln} 行：{msg}")
    beats = [b for b in ep.beats if not only or b.id in set(only)]
    plan, held, new_chars, cached_chars = [], [], 0, 0
    for b in beats:
        if not b.narration:
            continue
        bp = prep_beat(b, pcfg)
        cached = (cache_dir / f"{cache_key(bp.tts, engine, st)}.mp3").exists()
        status = "cached" if cached else f"{len(bp.tts)} 字符"
        if dry or bp.p.blocked or verbose:
            report_beat(b.id, bp, status, verbose)
        if bp.p.blocked and not force:
            held.append(b.id)
            continue
        plan.append((b, bp, cached))
        if cached:
            cached_chars += len(bp.tts)
        else:
            new_chars += len(bp.tts)
    print(f"[voice] {chapter}：{len(plan)} 个 beat 待生成，新合成 {new_chars:,} 字符，缓存 {cached_chars:,} 字符；"
          f"拦下 {len(held)} 个{(' ' + ' '.join(held)) if held else ''}")
    q = None
    if engine == "eleven" and (dry or new_chars):
        try:
            q = quota(cfg)
            print(f"[voice] ElevenLabs 剩余 {q['remaining']:,} / {q['limit']:,}（{q['reset']} 重置）")
        except SystemExit as e:
            if not dry:
                raise
            print(f"{e}（--dry 不需要 key）")
        except Exception as e:  # noqa: BLE001
            print(f"[voice] 读不到额度：{e.__class__.__name__}")
    if dry:
        return 1 if held else 0
    if engine == "eleven" and new_chars > max_chars:
        print(f"[voice] 新合成 {new_chars} 字符 > 上限 {max_chars}：一个字都没发。先问作者，再加 --max-chars。")
        return 2
    if engine == "eleven" and new_chars and q and new_chars > q["remaining"]:
        print("[voice] 额度不够")
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)
    bj = out_dir / "beats.json"
    meta = json.loads(bj.read_text("utf-8")) if bj.exists() else {"chapter": chapter, "beats": {}}
    meta["script"] = str(script)
    meta["engine"] = engine
    order = [b.id for b in ep.beats]
    for b, bp, _ in plan:
        mp3, times, hit = take(bp.tts, engine, st, cache_dir, cfg)
        if not hit:
            ledger_add(cfg, chapter, b.id, len(bp.tts), engine, st)
        wav = to_wav(mp3, out_dir / f"beat{b.id}.wav")
        dur = wav_duration(wav)
        disp, words = beat_timing(bp, times, wav, dur)
        if bp.pauses:                                        # （停顿 2 秒）: insert silence, shift the times
            cuts = []
            for k, sec in bp.pauses:
                t = words[k - 1][2] if 0 < k <= len(words) else (words[0][1] or 0.0) if words else 0.0
                cuts.append((t + 0.05, sec))
            shift = insert_silence(wav, wav, cuts)
            words = [[c, None if s is None else round(shift(s), 3), round(shift(e), 3)] for c, s, e in words]
            disp = [round(shift(t), 3) for t in disp]
            dur = wav_duration(wav)
        meta["beats"][b.id] = {
            "text": bp.display, "spoken": bp.clean, "tts": bp.tts, "file": wav.name, "duration": round(dur, 3),
            "engine": engine, "voice": st.get("voice"), "model": st.get("model", engine),
            "cache": cache_key(bp.tts, engine, st), "char_times": disp, "words": words,
            "pinyin_marks": [s.ctx for s in bp.p.spots if s.status == "pinyin"],
            "pron": bp.p.records, "scene": b.scene, "level": b.level, "rigor": b.rigor,
            "pauses": [[k, sec] for k, sec in bp.pauses], "placeholder": engine != "eleven",
        }
        meta["beats"] = {k: meta["beats"][k] for k in order if k in meta["beats"]} | \
            {k: v for k, v in meta["beats"].items() if k not in order}
        bj.write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
        (out_dir / "durations.json").write_text(json.dumps({k: v["duration"] for k, v in meta["beats"].items()}, indent=1),
                                                "utf-8")
        print(f"[voice] {chapter} beat {b.id}: {'缓存' if hit else engine} {dur:.2f}s")
    if held:
        print(f"[voice] {len(held)} 个 beat 被拦下：按上面的建议改写或标读音，再跑一次（--force 会照模型的猜测去念）")
        return 1
    print(f"[voice] 完成。下一步：kepu earcheck build {script}（只听高风险的几十处，而不是整集）")
    return 0


def main_quota(cfg) -> int:
    q = quota(cfg)
    print(f"[voice] ElevenLabs {q['tier']}：已用 {q['used']:,} / {q['limit']:,}，剩余 {q['remaining']:,}（{q['reset']} 重置）")
    if ledger_summary(cfg):
        print(f"[voice] {ledger_summary(cfg)}")
    return 0


if __name__ == "__main__":
    sys.exit("use: python -m kepu voice …")
