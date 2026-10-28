"""希腊字母的英文读音：每个音色只校准一次。

    kepu greek audition --dry                 # 免费：列出要合成的候选句和字符数（全部 24 个字母约 900 字符）
    kepu greek audition                       # 合成候选（花钱，先问），生成 review/greek/index.html：每个字母选一个最像英文的
    kepu greek audition --letters σμξ         # 只试这几个
    kepu greek ingest 下载的选择.json          # 写进音色档案 ~/.kepu/voices/<音色>.json，所有项目共用

候选写法见 data/greek.json：多音节字母用英文拼写（sigma、Sigma、sig-ma），单音节字母另备能确定念出英文音的写法
（τ→套、ψ→赛、χ→凯、π→派）。每个候选放在同一个载体句里：“设 X 等于零点五。”默认音色（Susan · eleven_v4）的 24 个
字母已由作者 2026-10-29 逐个选定，写进了 greek.json 的 en。
教训（《地基之下》第一到三轮）：先让作者从 5–6 个候选里选定，再调工具；phi、fye 两轮都白做了。
"""
from __future__ import annotations

import base64
import html
import json
from pathlib import Path

from .pron.greek import greek_table, load_profile, save_profile
from .timing import wav_duration
from .util import ASSETS
from .voice import cache_key, settings, take, to_wav

CARRIER = "设 {x} 等于零点五。"
VARIANT_OF = {"ϵ": "ε", "ϕ": "φ", "ς": "σ"}
VARIANTS = set(VARIANT_OF)          # follow their main letter (ε φ σ) unless asked for explicitly
EMBED_LIMIT = 15_000_000           # bytes of audio embedded in the page (self-contained, opens anywhere)


def candidates(letters: str | None, profile: dict) -> list[tuple[str, str, str]]:
    out = []
    for ch, g in greek_table().items():
        if letters and ch not in letters:
            continue
        if not letters and ((ch.isupper() and ch.lower() in greek_table()) or ch in VARIANTS):
            continue                                  # uppercase / variant forms follow their main letter unless asked
        if profile.get("greek", {}).get(ch, {}).get("verified") and not letters:
            continue
        for c in g["cands"]:
            out.append((ch, g["name"], c))
    return out


def audition(cfg, letters: str | None = None, dry: bool = False, max_chars: int | None = None) -> int:
    prof = load_profile(cfg.voice_key, cfg.root)
    cands = candidates(letters, prof)
    engine = cfg.get("voice", "engine")
    st = settings(cfg, engine)
    lines = []
    for n, (ch, name, c) in enumerate(cands, 1):
        lines.append((n, ch, name, c, CARRIER.format(x=c)))
    cache = Path(cfg.get("voice", "cache")) if cfg.get("voice", "cache") else cfg.path("project", "audio") / "_cache"
    new = sum(len(t) for *_, t in lines if not (cache / f"{cache_key(t, engine, st)}.mp3").exists())
    print(f"[greek] {len(set(c[0] for c in cands))} 个字母，{len(lines)} 条候选，新合成 {new} 字符（{engine}，{st.get('voice')}）")
    if dry:
        for n, ch, name, c, t in lines:
            print(f"  {n:3d} {ch} {name:8s} → {t}")
        return 0
    limit = int(max_chars or cfg.get("voice", "max_chars"))
    if engine == "eleven" and new > limit:
        print(f"[greek] {new} 字符 > 上限 {limit}：先问，再加 --max-chars")
        return 2
    out = cfg.path("project", "review") / "greek"
    (out / "clips").mkdir(parents=True, exist_ok=True)
    rows, total = [], 0
    for n, ch, name, c, t in lines:
        mp3, _, hit = take(t, engine, st, cache, cfg)
        wav = to_wav(mp3, out / "clips" / f"{n:03d}.wav")
        data = mp3.read_bytes()
        total += len(data)
        rows.append({"n": n, "char": ch, "name": name, "say": c, "text": t, "dur": round(wav_duration(wav), 2),
                     "clip": f"clips/{wav.name}", "_mp3": data})
        print(f"  {n:3d} {ch} {c}: {'缓存' if hit else engine}")
    embed = total <= EMBED_LIMIT
    for r in rows:
        data = r.pop("_mp3")
        if embed:                                     # self-contained page: works when sent, mailed or opened anywhere
            r["clip"] = "data:audio/mpeg;base64," + base64.b64encode(data).decode()
    page = (ASSETS / "greek.html").read_text(encoding="utf-8")
    page = page.replace("__DATA__", json.dumps({"voice_key": cfg.voice_key, "rows": rows}, ensure_ascii=False))
    page = page.replace("__TITLE__", html.escape(f"希腊字母试听 · {cfg.voice_key}"))
    (out / "index.html").write_text(page, encoding="utf-8")
    print(f"[greek] → {out / 'index.html'}：每个字母选最像英文的一个，点“导出”，再 kepu greek ingest <文件>")
    return 0


def ingest(path: Path, cfg) -> int:
    d = json.loads(Path(path).read_text("utf-8"))
    key = d.get("voice_key") or cfg.voice_key
    chosen = {r["char"]: {"say": r["say"], "verified": True} for r in d.get("choices", [])}
    for ch, v in list(chosen.items()):                 # uppercase and variant forms follow their main letter
        for other in (ch.upper(), *(k for k, base in VARIANT_OF.items() if base == ch)):
            if other != ch and other in greek_table() and other not in chosen:
                chosen[other] = dict(v)
    p = save_profile(key, {"greek": chosen})
    print(f"[greek] {len(chosen)} 个字母的读法写进 {p}")
    return 0
