"""分镜节奏、花钱记录、响度、系列进度表的测试（v0.2）。

    python3 -m unittest discover -s toolkit/tests        # 或者 python3 -m kepu selftest
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kepu import board, config, loudness, status, voice  # noqa: E402

SCRIPT = "# 第 1 期 测试\n\n" + "".join(f"## beat {i:02d} [L1]\n台词：{'这是一句用来估计时长的台词。' * 4}\n画面：一\n\n" for i in range(1, 31))


def project(tmp: Path, board_text: str = "") -> config.Config:
    (tmp / "kepu.toml").write_text('[project]\nname = "测试系列"\nengine = "anime"\n', encoding="utf-8")
    (tmp / "script" / "episodes").mkdir(parents=True)
    (tmp / "script" / "storyboards").mkdir(parents=True)
    (tmp / "script" / "episodes" / "ep01.md").write_text(SCRIPT, encoding="utf-8")
    if board_text:
        (tmp / "script" / "storyboards" / "ep01.md").write_text(board_text, encoding="utf-8")
    return config.load(tmp)


def shots(spec: dict) -> str:
    """{beat: "【大】…"} -> storyboard text; unspecified beats are content shots with an accent."""
    return "# 分镜\n\n" + "".join(f"- {i:02d} {spec.get(i, '【内】内容。红：无。')}\n" for i in range(1, 31))


class Board(unittest.TestCase):
    def run_board(self, spec):
        with tempfile.TemporaryDirectory() as d:
            cfg = project(Path(d), shots(spec))
            return board.check(Path(d) / "script/storyboards/ep01.md", cfg, quiet=True)

    def test_within_budget(self):
        bad, rows = self.run_board({2: "【大】开场。红：无。", 12: "【插】插卡。红：无。", 20: "【白】回顾。红：无。",
                                    21: "【白】回顾。红：无。", 25: "【判】判定线。红：线。"})
        self.assertEqual(bad, 0, rows)
        self.assertIn("白底段落 1 段（建议 1–2）", [r[1] for r in rows])     # two adjacent 【白】 beats are one segment

    def test_over_budget(self):
        bad, rows = self.run_board({i: "【大】大字。红：无。" for i in range(1, 30, 3)})   # 10 big cards
        self.assertTrue(any(r[0] == board.BAD and r[1].startswith("大字卡 10 次") for r in rows), rows)

    def test_spacing_after_cold_open(self):
        # each beat ≈ 56 chars ≈ 13 s + 0.6 s gap: beats 20 and 21 start ~13.5 s apart, well after the 3-minute cold open
        bad, rows = self.run_board({20: "【大】一。红：无。", 21: "【插】二。红：无。"})
        self.assertTrue(any(r[0] == board.BAD and "≥ 20 秒" in r[1] for r in rows), rows)
        bad, rows = self.run_board({1: "【大】一。红：无。", 2: "【插】二。红：无。"})            # inside the cold open
        self.assertFalse(any(r[0] == board.BAD and "≥ 20 秒" in r[1] for r in rows), rows)

    def test_multiline_shot_and_unknown_beat(self):
        text = shots({}) + "- 31 【大】稿子里没有这个 beat。红：无。\n"
        text = text.replace("- 05 【内】内容。红：无。\n", "- 05 【大】定理卡：\n  - 第一行\n  - 红：等号。\n")
        with tempfile.TemporaryDirectory() as d:
            cfg = project(Path(d), text)
            sh = board.parse_board(Path(d) / "script/storyboards/ep01.md")
            five = next(s for s in sh if s.id == "05")
            self.assertTrue(five.accent and five.cards == ["大"])
            bad, rows = board.check(Path(d) / "script/storyboards/ep01.md", cfg, quiet=True)
            self.assertTrue(any(r[0] == board.BAD and "31" in r[2] for r in rows), rows)


class Ledger(unittest.TestCase):
    def test_paid_takes_are_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = project(Path(d))
            st = {"voice": "v1", "model": "eleven_v4"}
            voice.ledger_add(cfg, "ep01", "03", 120, "eleven", st)
            voice.ledger_add(cfg, "ep01", "04", 80, "eleven", st)
            voice.ledger_add(cfg, "ep01", "05", 999, "edge", st)            # free engines are not money
            rows = voice.ledger(cfg)
            self.assertEqual([r["chars"] for r in rows], [120, 80])
            self.assertIn("200", voice.ledger_summary(cfg))


class Loudness(unittest.TestCase):
    def test_parse(self):
        err = 'junk\n[Parsed_loudnorm_0 @ 0x1]\n{\n\t"input_i" : "-23.51",\n\t"input_tp" : "-4.20",\n\t"input_lra" : "3.10",' \
              '\n\t"input_thresh" : "-33.9",\n\t"output_i" : "-16.0",\n\t"target_offset" : "0.1"\n}\n'
        self.assertEqual(loudness._loudnorm_json(err)["input_i"], "-23.51")

    @unittest.skipUnless(shutil.which("ffmpeg"), "需要 ffmpeg")
    def test_fix_reaches_target(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / "quiet.wav", Path(d) / "norm.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                            "sine=frequency=440:duration=6,volume=0.05", "-ar", "48000", str(src)], check=True)
            self.assertLess(loudness.measure(src)["I"], -24)
            m = loudness.normalize(src, dst, -16.0, -1.5)
            self.assertLess(abs(m["I"] + 16.0), 1.0, m)
            self.assertLessEqual(m["TP"], -1.0)


class Status(unittest.TestCase):
    def test_row_and_html(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = project(Path(d), shots({2: "【大】开场。红：无。"}))
            row = status.episode_row(Path(d) / "script/episodes/ep01.md", cfg)
            self.assertEqual(row["cells"]["script"][0], status.DONE)
            self.assertEqual(row["cells"]["board"][0], status.DONE)
            self.assertEqual(row["cells"]["voice"][0], status.TODO)
            self.assertIn("kepu voice", row["next"])
            page = status.write_html(status.collect(cfg), cfg).read_text(encoding="utf-8")
            self.assertIn("测试系列", page)
            self.assertNotIn("__ROWS__", page)


if __name__ == "__main__":
    unittest.main()
