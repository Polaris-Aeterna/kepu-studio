"""
EvaScene / NarratedScene for the EVA house style.  See engine/README.md.

    from style import *
    from narrated import NarratedScene

    class Ep1_01_Opening(NarratedScene):
        chapter = "ep1"                       # reads engine/audio/ep1/beats.json
        def construct(self):
            self.beat("01")                   # beat 01 audio starts now; subtitles follow it
            self.play(rise_in(card), run_time=self.until("论文"))
            self.insert(InsertCard("是错的"), hold=0.9)      # EVA insert frame: hard cut in/out
            self.judge_cut([next_mobs])        # signature transition: red line sweeps, hard cut
            self.beat_wait()

Audio: Scene.add_sound at the beat's start time (frame-accurate).  Beats never overlap: an overrun
prints a warning and pushes the next beat later.
Subtitles: Songti, plain ink on the ground (no box), ink follows set_ground().  SUBTITLES=0 hides them.
English (README §11): class attribute LANG = "en" -> audio from engine/audio/en/<chapter>/ (beats that only exist
as placeholder audio come from engine/audio/en/_placeholder/<chapter>/, with a warning), English caption
splitter (engine/subtitles_en.py), subtitles NOT burned in (SUBTITLES=1 to preview them); the .srt is written
as always.  FINAL_AUDIO=1 makes a placeholder beat an error (use it for the YouTube render).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from manimlib import *  # noqa: F401,F403
from manimlib.logger import log

sys.path.insert(0, str(Path(__file__).resolve().parent))
import style as _style  # noqa: E402
from style import (BG, EASE_EXPO, INK, PAPER, PAPER_INK, RED, SIZE_SUB, SUBTITLE_Y, ZH_TEXT,  # noqa: E402
                   Markup, block, sup_markup)
import subtitles as _subtitles  # noqa: E402
import subtitles_en as _subtitles_en  # noqa: E402
import langs as _langs  # noqa: E402

# Subtitle segmentation lives in engine/subtitles.py (README §10).  The pre-2026-10-28 splitter is kept as
# split_phrases_legacy; set SUBTITLE_SPLITTER=legacy in the environment to get the old segmentation back.
srt_text = _subtitles.srt_text


def split_phrases(text, times, duration, max_chars=None, lang="zh"):
    """Subtitle lines [[t0, t1, text], ...] for one beat (engine/subtitles.py; lang "en": subtitles_en.py,
    where a cue may hold two lines joined by '\n')."""
    if lang == "en":
        return _subtitles_en.split_cues(text, times, duration)
    if os.environ.get("SUBTITLE_SPLITTER", "").strip().lower() == "legacy":
        return split_phrases_legacy(text, times, duration, max_chars or SUB_MAX_CHARS)
    return _subtitles.split_phrases(text, times, duration, max_chars=max_chars or _subtitles.MAX_CHARS)

ENGINE_DIR = Path(__file__).resolve().parent
AUDIO_ROOT = ENGINE_DIR / "audio"

SUB_BREAK = set("，。！？；：、,!?;:…")
SUB_MAX_CHARS = 22


def _env_flag(name: str):
    v = os.environ.get(name)
    if v is None:
        return None
    return v.strip().lower() not in ("0", "false", "no", "off", "")


SENT_END = set("。！？!?…")
_CUT_AFTER = set("的了地着过和与及或而在是把被将对从向给让")
_CUT_BEFORE = set("也都就还却并而但才又再")


def _good_cut(text, mid, lo, hi, reach=5):
    """A cut index near `mid` that does not split a word: prefer right after a particle (的/了…) or right
    before an adverb (也/都/就…), never inside a Latin word or number."""
    def latin(i):
        return 0 < i < len(text) and re.match(r"[A-Za-z0-9.\-]", text[i - 1]) and re.match(r"[A-Za-z0-9.\-]", text[i])
    best = None
    for d in sorted(range(-reach, reach + 1), key=abs):
        c = mid + d
        if c <= lo or c >= hi or latin(c):
            continue
        if text[c - 1] in _CUT_AFTER or text[c] in _CUT_BEFORE or text[c] == " ":
            best = c
            break
    if best is None:
        best = mid
        while best < hi and latin(best):
            best += 1
    return best


def split_phrases_legacy(text: str, times: list[float], duration: float, max_chars: int = SUB_MAX_CHARS):
    """Split narration into subtitle phrases [(start, end, text)] using per-char times.
    Pieces are cut at punctuation, packed up to `max_chars`, never across a sentence end."""
    pieces, start = [], 0
    for i, ch in enumerate(text):
        if ch == "," and 0 < i < len(text) - 1 and text[i - 1].isdigit() and text[i + 1].isdigit():
            continue                     # (0,0,1) / 1,000,000: a comma between digits is not a break
        if ch in SUB_BREAK or i == len(text) - 1:
            pieces.append((start, i + 1))
            start = i + 1
    spans, cur = [], None
    for a, b in pieces:
        if b - a > max_chars:  # split long pieces into balanced parts, never inside a Latin word/number
            if cur:
                spans.append(cur)
                cur = None
            k = -(-(b - a) // max_chars)
            cuts = [a]
            for j in range(1, k):
                c = _good_cut(text, a + round(j * (b - a) / k), cuts[-1] + 4, b - 4)
                cuts.append(c)
            for c0, c1 in zip(cuts[:-1], cuts[1:]):
                spans.append((c0, c1))
            a = cuts[-1]
        if cur and (b - cur[0]) <= max_chars:
            cur = (cur[0], b)
        else:
            if cur:
                spans.append(cur)
            cur = (a, b)
        if text[b - 1] in SENT_END:
            spans.append(cur)
            cur = None
    if cur:
        spans.append(cur)
    phrases = []
    for k, (a, b) in enumerate(spans):
        seg = text[a:b].strip().rstrip("，。；：、,;:")
        if not seg:
            continue
        t0 = times[a] if a < len(times) else 0.0
        t1 = times[spans[k + 1][0]] if k + 1 < len(spans) and spans[k + 1][0] < len(times) else duration
        phrases.append([t0, max(t1, t0 + 0.3), seg])
    if phrases:
        phrases[0][0] = 0.0
    return phrases


GROUNDS = {"black": (BG, INK), "paper": (PAPER, PAPER_INK)}


class EvaScene(Scene):
    """
    Base scene for the series (use NarratedScene when there is narration).
      set_ground("black" | "paper")  hard switch of the whole ground (subtitle ink follows)
      cut_to(*mobs)                 hard cut: everything (except subtitles) replaced at once
      insert(card, hold)            EVA insert frame: a full-frame card cut in and out
      big(card, hold)               a big-card moment (counted against the frequency limits)
      judge_cut(*mobs)              signature transition: red line sweeps across, hard cut at mid-frame
    """
    default_camera_config = dict(background_color=BG)
    big_min_gap = 20.0       # seconds between two big-card moments (warning below)
    insert_min_gap = 20.0    # seconds between two insert frames (warning below)
    LANG = "zh"              # "en": English faces / audio / captions (README §11)

    def setup(self):
        super().setup()
        if self.LANG != _style.LANG:
            _style.set_lang(self.LANG)
        self.ground = "black"
        self._moments = {"big": [], "insert": []}

    # ground --------------------------------------------------------------
    def set_ground(self, kind: str = "black"):
        bg, ink = GROUNDS[kind]
        self.ground = kind
        self.camera.background_rgba = list(color_to_rgba(bg))
        if hasattr(self, "_sub_cache"):
            self._sub_cache = {}
            self._sub_idx = -1
        return ink

    @property
    def ink(self):
        return GROUNDS[self.ground][1]

    def _keep(self):
        keep = {id(self.camera.frame)}
        if hasattr(self, "_sub_group"):
            keep.add(id(self._sub_group))
        return keep

    def stage_mobjects(self):
        keep = self._keep()
        return [m for m in self.mobjects if id(m) not in keep]

    # cuts ----------------------------------------------------------------
    def cut_to(self, *mobs, ground: str | None = None):
        """Hard cut: remove everything on stage, add `mobs` (and optionally switch ground)."""
        self.remove(*self.stage_mobjects())
        self.camera.frame.to_default_state()
        if ground:
            self.set_ground(ground)
        if mobs:
            self.add(*mobs)

    def _note(self, kind, gap):
        times = self._moments[kind]
        if times and self.time - times[-1] < gap:
            log.warning(f"[eva] {kind} moment {self.time - times[-1]:.1f}s after the previous one "
                        f"(rule: >= {gap:.0f}s) — see README §5")
        times.append(self.time)

    def insert(self, card: Mobject, hold: float = 0.9, sound: bool = False):
        """EVA insert frame: cut to a full-frame card for `hold` seconds, then cut back."""
        self._note("insert", self.insert_min_gap)
        card.fix_in_frame()
        card.z_index = 200
        subs = getattr(self, "_sub_group", None)
        if subs is not None:
            subs.set_opacity(0)
        self.add(card)
        self.wait(hold)
        self.remove(card)
        if subs is not None:
            subs.set_opacity(1)

    def big(self, card: Mobject, hold: float | None = None, ground: str | None = None, count: bool = True):
        """A big-card moment: hard cut to `card` (optionally on a new ground), optionally hold.
        count=False only for the episode's own ChapterCard (once per episode, exempt from the limits)."""
        if count:
            self._note("big", self.big_min_gap)
        self.cut_to(card, ground=ground)
        if hold:
            self.wait(hold)

    def next_episode(self, number: int, hold: float = 2.6, sweep: bool = True):
        """The standard end card: (signature sweep) -> NextEpisodeCard(number), held `hold` seconds,
        subtitles off.  Not counted against the big-card budget."""
        from style import NextEpisodeCard
        card = NextEpisodeCard(number)
        self.set_subtitles(False) if hasattr(self, "set_subtitles") else None
        if sweep:
            self.judge_cut(card)
        else:
            self.cut_to(card)
        if hold:
            self.wait(hold)

    def judge_cut(self, *mobs, run_time: float = 0.5, ground: str | None = None, y: float = 0.0):
        """The series' signature move: a red judgement bar sweeps left->right at constant speed;
        when it passes mid-frame the stage hard-cuts to `mobs`."""
        bar = block(0.14, FRAME_HEIGHT + 0.4, RED).move_to([-FRAME_WIDTH / 2 - 0.2, y, 0])
        bar.fix_in_frame()
        bar.z_index = 150
        self.add(bar)
        self.play(bar.animate.set_x(0), run_time=run_time / 2, rate_func=linear)
        self.cut_to(*mobs, ground=ground)
        self.add(bar)
        self.play(bar.animate.set_x(FRAME_WIDTH / 2 + 0.2), run_time=run_time / 2, rate_func=linear)
        self.remove(bar)

    def clear_stage(self, run_time: float = 0.0, keep=()):
        """Remove everything except subtitles (and `keep`).  run_time 0 = hard cut (house default)."""
        keep_ids = {id(m) for m in keep} | self._keep()
        mobs = [m for m in self.mobjects if id(m) not in keep_ids]
        if not mobs:
            return
        if run_time > 0:
            self.play(*[FadeOut(m) for m in mobs], run_time=run_time)
        else:
            self.remove(*mobs)


class NarratedScene(EvaScene):
    chapter: str = "demo"            # audio dir name: engine/audio/<chapter>/
    audio_dir: str | None = None     # override full path to audio dir
    subtitles: bool = True           # bottom subtitle bar (env SUBTITLES overrides)
    beat_gap: float = 0.4            # silence after each beat's audio before next beat
    lead_in: float = 0.0             # silence at the very beginning of the scene
    chars_per_sec: float = 4.5       # duration estimate for beats without audio
    burn_subtitles: bool = False     # non-zh: subtitles are a separate .srt (YouTube CC), not burned in
    # ------------------------------------------------------------------ setup
    def setup(self):
        super().setup()
        if self.LANG == "zh":
            d = Path(self.audio_dir) if self.audio_dir else AUDIO_ROOT / self.chapter
            self._audio_dir = d
            bj = d / "beats.json"
            self._beats = json.loads(bj.read_text("utf-8"))["beats"] if bj.exists() else {}
            self._beat_src, self._beat_dirs = {}, {}
        else:
            self._beats, self._beat_src, self._beat_dirs = _langs.load_beats(
                self.LANG, self.chapter, Path(self.audio_dir) if self.audio_dir else None)
            d = self._audio_dir = Path(self.audio_dir) if self.audio_dir else _langs.audio_dir(self.LANG, self.chapter)
            bj = d / "beats.json"
            ph = sorted(k for k, v in self._beat_src.items() if v == "placeholder")
            if ph:
                msg = (f"[narrated] PLACEHOLDER audio (edge/say, not final) for beats {' '.join(ph)} from "
                       f"{_langs.audio_dir(self.LANG, self.chapter, placeholder=True)}")
                if _env_flag("FINAL_AUDIO"):
                    raise RuntimeError(msg + " — FINAL_AUDIO=1 forbids it; voice them with tts.py first")
                log.warning(msg)
        if not self._beats:
            log.warning(f"[narrated] no audio found at {bj}; run tts.py first (durations will be estimated)")
        env = _env_flag("SUBTITLES")
        default_subs = self.subtitles if self.LANG == "zh" else self.burn_subtitles
        self._subs_on = default_subs if env is None else env
        self._cur = None             # current beat id
        self._beat_start = 0.0
        self._beat_dur = 0.0
        self._beat_info: dict = {}
        self._phrases = []
        self._timeline = []          # [(beat, start, dur)]
        self._srt = []               # [(start, end, text)] scene-absolute
        self._sub_group = VGroup()
        self._sub_group.z_index = 100
        self._sub_group.fix_in_frame()
        self._sub_cache: dict[int, Mobject] = {}
        self._sub_idx = -1
        if self._subs_on:
            self._sub_group.add_updater(lambda m: self._update_subtitle())
            self.add(self._sub_group)
        if self.lead_in > 0:
            self.wait(self.lead_in)

    # ------------------------------------------------------------------ beats
    def beat(self, beat_id: str | int, gap: float | None = None):
        """Start narration beat `beat_id` (e.g. "03") now. Auto-closes the previous beat."""
        bid = f"{int(beat_id):02d}" if str(beat_id).isdigit() else str(beat_id)
        if self._cur is not None:
            self.beat_wait()
        info = self._beats.get(bid)
        if info is None:
            log.warning(f"[narrated] beat {bid} has no audio in {self._audio_dir}; using 5s placeholder")
            info = {"text": "", "duration": 5.0, "char_times": []}
        else:
            wav = self._beat_dirs.get(bid, self._audio_dir) / info["file"]
            if wav.exists():
                self.add_sound(str(wav))
            else:
                log.warning(f"[narrated] missing {wav}")
        self._cur = bid
        self._beat_info = info
        self._beat_start = self.time
        self._beat_dur = float(info["duration"])
        self._gap = self.beat_gap if gap is None else gap
        self._timeline.append((bid, round(self.time, 3), self._beat_dur))
        text = info.get("text", "")
        if self.LANG == "zh":
            self._phrases = split_phrases(text, info.get("char_times") or [0.0] * len(text), self._beat_dur) \
                if text else []
        else:
            self._phrases = split_phrases(text, info.get("char_times") or [0.0] * len(text), self._beat_dur,
                                          lang=self.LANG) if text else []
        for t0, t1, s in self._phrases:
            self._srt.append((self._beat_start + t0, self._beat_start + t1, s))
        self._sub_cache = {}
        self._sub_idx = -1
        if self._subs_on:
            self.add(self._sub_group)  # make sure it's on screen (z_index keeps it on top)
            self._update_subtitle()
        return info

    @property
    def beat_duration(self) -> float:
        """Audio length of the current beat (seconds)."""
        return self._beat_dur

    def beat_time(self) -> float:
        """Seconds elapsed since the current beat started."""
        return self.time - self._beat_start

    def beat_remaining(self) -> float:
        """Seconds until the current beat's audio ends (can be negative)."""
        return self._beat_dur - self.beat_time()

    def word_time(self, word: str, occurrence: int = 1) -> float:
        """Time (s, relative to beat start) when `word` (substring of the 台词) is spoken."""
        text = self._beat_info.get("text", "")
        times = self._beat_info.get("char_times") or []
        idx = -1
        for _ in range(occurrence):
            idx = text.find(word, idx + 1)
            if idx < 0:
                raise ValueError(f"[narrated] word {word!r} not found in beat {self._cur}: {text}")
        return times[idx] if idx < len(times) else 0.0

    def until(self, target, min_time: float = 0.2) -> float:
        """
        Seconds from now until `target`, for use as run_time:
            target = float  -> seconds into the beat;   target = str -> when that word is spoken.
        Never less than `min_time` (warns if already past).
        """
        t = self.word_time(target) if isinstance(target, str) else float(target)
        dt = t - self.beat_time()
        if dt < min_time:
            if dt < -0.3:
                log.warning(f"[narrated] beat {self._cur}: already {-dt:.2f}s past {target!r}")
            return min_time
        return dt

    def wait_until_beat(self, target):
        """Wait until `target` (seconds into beat, or a word of the 台词)."""
        t = self.word_time(target) if isinstance(target, str) else float(target)
        dt = t - self.beat_time()
        if dt > 1 / 60:
            self.wait(dt)
        elif dt < -0.3:
            log.warning(f"[narrated] beat {self._cur}: already {-dt:.2f}s past {target!r}")

    def beat_play(self, *anims, frac: float = None, until=None, **kwargs):
        """play() with run_time = frac * beat duration, or ending at `until` (seconds / word)."""
        if until is not None:
            kwargs["run_time"] = self.until(until)
        elif frac is not None:
            kwargs["run_time"] = max(0.2, frac * self._beat_dur)
        self.play(*anims, **kwargs)

    def beat_wait(self, min_wait: float = 0.0):
        """Wait out the rest of the current beat (+gap). Warns if the beat overran its audio."""
        if self._cur is None:
            return
        remaining = self._beat_dur + self._gap - self.beat_time()
        if self.beat_time() > self._beat_dur + 0.05:
            log.warning(f"[narrated] beat {self._cur}: animations ran {self.beat_time() - self._beat_dur:.2f}s "
                        f"longer than its audio ({self._beat_dur:.2f}s) -> extra silence")
        w = max(remaining, min_wait)
        if w > 1 / 60:
            self.wait(w)
        self._cur = None
        self._phrases = []
        self._sub_idx = -1
        if self._subs_on:
            self._sub_group.set_submobjects([])

    # ------------------------------------------------------------------ subtitles
    def _make_sub(self, s: str) -> Mobject:
        font = ZH_TEXT if self.LANG == "zh" else _style.FACES[self.LANG]["text"]
        t = Markup(sup_markup(s, span=True), size=SIZE_SUB, color=self.ink, font=font, weight="BOLD")
        if t.get_width() > 12.8:
            t.set_width(12.8)
        t.move_to(SUBTITLE_Y * UP)
        t.fix_in_frame()
        return t

    def _update_subtitle(self):
        if self._cur is None or not self._phrases:
            if len(self._sub_group.submobjects):
                self._sub_group.set_submobjects([])
            return
        bt = self.beat_time()
        idx = -1
        for k, (t0, t1, s) in enumerate(self._phrases):
            if t0 <= bt + 1e-3:
                idx = k
        if bt > self._beat_dur + 0.2:
            idx = -1
        if idx == self._sub_idx:
            return
        self._sub_idx = idx
        if idx < 0:
            self._sub_group.set_submobjects([])
            return
        if idx not in self._sub_cache:
            self._sub_cache[idx] = self._make_sub(self._phrases[idx][2])
        self._sub_group.set_submobjects([self._sub_cache[idx]])

    def set_subtitles(self, on: bool):
        """Turn the subtitle bar on/off mid-scene (e.g. off during a full-screen formula)."""
        self._subs_on = on
        if on:
            if not self._sub_group.updaters:
                self._sub_group.add_updater(lambda m: self._update_subtitle())
            self.add(self._sub_group)
        else:
            self._sub_group.clear_updaters()
            self._sub_group.set_submobjects([])

    def tear_down(self):
        if self._cur is not None and not self.skip_animations:
            self.beat_wait()
        n_big = len(self._moments["big"])
        mins = max(self.time / 60, 1e-6)
        if self.time > 120 and n_big / mins > 0.5:
            log.warning(f"[eva] {n_big} big-card moments in {mins:.1f} min (rule: <= 1 per 2 min) — README §5")
        try:
            self._write_sidecars()
        except Exception as e:  # never fail a render because of sidecar files
            log.warning(f"[narrated] could not write timeline/srt: {e}")
        super().tear_down()

    def _write_sidecars(self):
        fw = self.file_writer
        if not getattr(fw, "write_to_movie", False):
            return
        movie = Path(fw.get_movie_file_path())
        stem = movie.with_suffix("")
        tl = {"chapter": self.chapter, "beats": self._timeline, "total": round(self.time, 3)}
        if self.LANG != "zh":
            tl["lang"] = self.LANG
            tl["placeholder_beats"] = sorted(b for b, *_ in self._timeline if self._beat_src.get(b) == "placeholder")
        (stem.parent / (stem.name + ".timeline.json")).write_text(json.dumps(
            tl, ensure_ascii=False, indent=1), "utf-8")
        lines = []
        for k, (a, b, s) in enumerate(self._srt, 1):
            lines += [str(k), f"{_srt_ts(a)} --> {_srt_ts(b)}", srt_text(s), ""]
        (stem.parent / (stem.name + ".srt")).write_text("\n".join(lines), "utf-8")


def _srt_ts(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
