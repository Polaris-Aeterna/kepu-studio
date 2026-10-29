"""读音引擎的回归测试：每一条都是《地基之下》或《ETH》真实出过（或差点出）的事故。

    python3 -m unittest discover -s toolkit/tests        # 或者 python3 -m kepu selftest
"""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kepu import config, lint  # noqa: E402
from kepu import script as S  # noqa: E402
from kepu.pron import lexicon  # noqa: E402
from kepu.pron.inventory import stand_in  # noqa: E402
from kepu.pron.lexicon import Lexicon, add_entry, parse_entry  # noqa: E402
from kepu.pron.speak import PronConfig, prepare, reload_lexicon  # noqa: E402

CFG = PronConfig()


def spot(text, k=None, ch=None):
    """The decision for the k-th occurrence (0-based) of ch, or for the character before 【】."""
    if "【" in text:
        i = text.index("【")
        text = text.replace("【", "").replace("】", "")
    else:
        i = [j for j, c in enumerate(text) if c == ch][k or 0]
    p = prepare(text, CFG)
    return next(s for s in p.spots if s.i == i), p


class Decides(unittest.TestCase):
    def check(self, text, reading, forced=None):
        s, p = spot(text)
        self.assertFalse(s.open, f"{text}: held ({s.why})")
        self.assertEqual(s.reading, reading, f"{text}: {s.reading} via {s.source} {s.entry or s.why}")
        if forced is not None:
            self.assertEqual(s.action == "force", forced, f"{text}: action {s.action}")

    # 《ETH》2026-10-28：作者听出“长子句”念成 zhǎng（长子 + 句）
    def test_chang_zi_ju(self):
        self.check("如果原来的【长】子句能被满足", "cháng", True)

    def test_zengzhang(self):
        self.check("随变量个数指数增【长】。", "zhǎng", True)

    # 《地基之下》第四轮：“无穷多行无穷多列”念成 xíng；表格多的集里“就行了”念成 háng
    def test_hang(self):
        self.check("无穷多【行】无穷多列", "háng", True)
        self.check("最后一【行】是 φ。", "háng", True)
        self.check("这样就【行】了", "xíng", True)
        self.check("这一【行】为真", "háng", True)

    # 《地基之下》第五轮：数 shǔ 是最多的一类（可数 253 处）
    def test_shu(self):
        self.check("这个集合是可【数】的", "shǔ", True)
        self.check("一直【数】下去", "shǔ", True)
        s, _ = spot("经理从来没有【数】过客人")             # 动词；“有数”也是个词，所以拦下来问也算对
        self.assertTrue(s.open or s.reading == "shǔ", s.why)
        self.check("变量【数】约为四点二七倍", "shù")

    def test_shu_trap_kexuejia(self):
        # 《地基之下》第八轮：“可数学家”被换成了“可暑学家”
        s, _ = spot("这位可【数】学家说")
        self.assertTrue(s.open or s.reading == "shù", s.why)

    def test_dang_author_choice(self):
        self.check("把全部真句子【当】成公理", "dāng", True)   # 作者定 dāng（词典 dàng）
        self.check("只有【当】 x 一是零时", "dāng")

    def test_stem_terms_pypinyin_gets_wrong(self):
        self.check("随机变量的方【差】", "chā", True)        # pypinyin: chà
        self.check("这是一个【相】变", "xiàng", True)        # pypinyin: xiāng
        self.check("最大【似】然估计", "sì")                 # pypinyin: shì
        self.check("曲线在这一点的【切】线", "qiē")           # pypinyin: qiè（qiē 是默认读音，没有替身字，不强制）
        self.check("【泊】松分布", "bó", True)               # pypinyin: pō
        self.check("二【重】积分", "chóng", True)            # pypinyin: zhòng
        self.check("向量的第一个分【量】", "liàng")
        self.check("向量的第一个【分】量", "fēn", True)       # pypinyin: fèn
        self.check("我们把它定义【为】零", "wéi", True)       # pypinyin: wèi
        self.check("【背】包问题", "bèi")                    # pypinyin: bēi
        self.check("这条定理最大的用【处】", "chù")           # pypinyin: chǔ

    def test_wei(self):
        self.check("因【为】一旦 x 四为真", "wèi")
        self.check("模型认【为】它可数", "wéi")
        self.check("x 一【为】真", "wéi", True)

    def test_eth_false_matches(self):
        # ETH 现行的词规则“数完”“数出”会误配进“计数完美匹配”“计数出发”（成片录于规则加入之前，没受影响；重录就会念成 jìshǔ）
        self.check("从平面图问题到计【数】完美匹配", "shù")
        self.check("算法从计【数】出发", "shù")

    def test_yi_mu_yi_yang_pinyin(self):
        s, p = spot("和表里的某一列一【模】一样")
        self.assertEqual(s.reading, "mú")
        self.assertEqual(s.status, "pinyin")             # 没有替身字：送拼音，并进耳检包
        self.assertTrue(any(r["kind"] == "pinyin" for r in p.records))


class Traps(unittest.TestCase):
    """同一个字在两种说得通的切分里读音不同：必须拦下问人。"""

    def held(self, text):
        s, _ = spot(text)
        self.assertTrue(s.open, f"{text}: decided {s.reading} via {s.source} {s.entry or s.why}")

    def test_traps(self):
        self.held("这里没有任何东西【藏】在箱子里了")         # 东西 + 藏 / 东 + 西藏
        self.held("OpenAI 宣布【了】解答")                    # 了解 / 了 + 解答
        self.held("为什么不直接在零处【分】组")               # 处分 / 分组
        self.held("会把表达力大大【地】拿回来")               # 大地
        self.held("他能【量】出的距离")                       # 能量 / 量出
        self.held("有没有一种“【数】”")                       # 光秃秃的“数”：没有上下文
        self.held("成千上万的人【为】它们寻找快速算法")        # 人为

    def test_no_false_alarm(self):
        for text in ("它对【应】的 NP 问题", "恰恰【相】反", "至关【重】要", "改进不【了】", "一部【分】", "类【似】的结果",
                     "有多【重】要", "能多【处】理一个变量", "要处【处】分清"):
            s, _ = spot(text)
            self.assertFalse(s.open, f"{text}: {s.why}")


class Spoken(unittest.TestCase):
    def test_greek_english(self):
        # 默认音色（Susan · eleven_v4）：作者 2026-10-29 逐个试听选定，不再进耳检包；φ 是例外（watch）
        susan = PronConfig(voice_key="kAIqZ7fZv234ClKXwzDx__eleven_v4", project_root=Path("/nonexistent"))
        p = prepare("设σ等于零点五", susan)
        self.assertIn(" sigma ", p.tts)
        self.assertFalse(any(r["kind"] == "greek" for r in p.records))
        p = prepare("设π等于三点一四", susan)
        self.assertIn(" pie ", p.tts)
        p = prepare("φ 或非 φ", susan)
        self.assertIn("phi", p.tts)
        self.assertTrue(any(r["kind"] == "greek" and r.get("watch") for r in p.records))   # 逻辑式里曾念成 fi
        # 别的音色：一律按“没验证”处理，进耳检包
        p = prepare("设σ等于零点五", PronConfig(voice_key="someone-else__eleven_v4"))
        self.assertTrue(any(r["kind"] == "greek" for r in p.records))

    def test_symbols(self):
        self.assertIn("对所有", prepare("∀x", CFG).tts)
        self.assertTrue(prepare("x → y", CFG).held)                         # → 念法有歧义，必须写清楚
        self.assertTrue(prepare("x²", CFG).held)

    def test_spans_map_back(self):
        p = prepare("设σ为〔wéi〕零", CFG)
        self.assertEqual(len(p.spans), len(p.clean))
        for ch, a, b in p.spans:
            self.assertLessEqual(a, b)


def capture(fn, *args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = fn(*args)
    return buf.getvalue(), rc


class ProjectLexicon(unittest.TestCase):
    """项目词典 pron/lexicon.tsv 里的词条：写进去就要生效，不生效就要说出来。"""

    LEX = ("扎〔zhā〕堆\tforce\n球冠〔guān〕\tforce\n舍〔shě〕林\tforce\n什〔shí〕梅尔金\tforce\n"
           "雪茄〔jiā〕\tforce\n绑扎〔zā〕\tleave\n")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "pron").mkdir()
        (self.root / "pron" / "lexicon.tsv").write_text(self.LEX, encoding="utf-8")
        (self.root / "kepu.toml").write_text('[voice]\nvoice_id = "test"\n', encoding="utf-8")
        self.cfg = PronConfig(project_root=self.root)
        reload_lexicon()

    def tearDown(self):
        reload_lexicon()
        self.tmp.cleanup()

    def spot(self, text, ch, cfg=None):
        p = prepare(text, cfg or self.cfg)
        return next((s for s in p.spots if s.char == ch), None), p

    # 《挂谷猜想》2026-10-30：词条 扎〔zhā〕堆、球冠〔guān〕 写进去了，却一个字也没改（扎、冠 不在多音字清单里）
    def test_force_outside_inventory(self):
        p = prepare("管子扎堆。在球冠上。舍林和什梅尔金。", self.cfg)
        self.assertEqual(p.tts, "管子zhā堆。在球guān上。shě林和shí梅尔金。")
        got = {s.char: (s.reading, s.source, s.status) for s in p.spots if s.char in "扎冠舍什"}
        self.assertEqual(got, {"扎": ("zhā", "lexicon", "pinyin"), "冠": ("guān", "lexicon", "pinyin"),
                               "舍": ("shě", "lexicon", "pinyin"), "什": ("shí", "lexicon", "pinyin")})
        self.assertEqual(sum(r["kind"] == "pinyin" for r in p.records), 4)     # 送拼音的都进耳检包

    def test_standin_outside_inventory(self):
        self.assertEqual(prepare("点一根雪茄", self.cfg).tts, "点一根雪" + stand_in("jiā")[0])

    def test_entry_must_fit_the_segmentation(self):
        s, p = self.spot("他拿过足球冠军", "冠")               # 足球 + 冠军：球冠〔guān〕 是误配
        self.assertIsNone(s)
        self.assertEqual(p.tts, "他拿过足球冠军")

    def test_leave_outside_inventory(self):
        s, p = self.spot("把电线绑扎好", "扎")
        self.assertEqual((s.reading, s.source, s.action), ("zā", "lexicon", "leave"))
        self.assertEqual(p.tts, "把电线绑扎好")

    def test_strict_holds_instead_of_sending_pinyin(self):
        s, _ = self.spot("管子扎堆", "扎", PronConfig(project_root=self.root, strict=True))
        self.assertTrue(s.open, s)
        self.assertIn("没有替身字", s.why)

    def test_hold_entry_round_trip(self):
        # kepu lexicon add "分量" --action hold 写成 分〔?〕量〔?〕；读回来时“?”被当成错的读音，整条丢掉
        add_entry("分量", "hold", "重量 fèn / 分量 fēn", "project", self.root)
        self.assertEqual(Lexicon(self.root, user=False).errors, [])
        reload_lexicon()
        s, _ = self.spot("这句话的分量很重", "分")
        self.assertTrue(s.open and "同形词" in s.why, s.why)
        with self.assertRaises(ValueError):
            parse_entry("冠〔?〕军", "force")                   # “?”只给 hold 用，不能送给模型

    def test_lexicon_add_says_what_happens(self):
        cfg = config.load(self.root)
        with mock.patch.object(lexicon, "USER_DIR", self.root / "home"):
            e, _ = add_entry("拧〔nǐng〕紧", "force", "", "project", self.root)
            out, rc = capture(lint.lexicon_check, e, cfg)
            self.assertEqual(rc, 0, out)
            self.assertIn("发给模型：nǐng紧", out)
            # 个人词典的词条被这个项目的同名词条盖住：在这里不生效，要说出来
            e, _ = add_entry("扎〔zā〕堆", "force", "", "user", self.root)
            out, rc = capture(lint.lexicon_check, e, cfg)
            self.assertEqual(rc, 1, out)
            self.assertIn("没有生效", out)

    def test_unreadable_line_is_reported(self):
        with open(self.root / "pron" / "lexicon.tsv", "a", encoding="utf-8") as f:
            f.write("冠〔?〕军\tforce\n")
        out, _ = capture(lint.pron_debug, ["冠军"], config.load(self.root))
        self.assertIn("冠〔?〕军", out)
        self.assertIn("没有生效", out)


class Script(unittest.TestCase):
    def test_split(self):
        d, s, m = S.split_beat("长{x₁|x 一}数〔shǔ〕一数〔shǔ〕（停顿 2 秒）好")
        self.assertEqual(d, "长x₁数一数好")
        self.assertEqual(s, "长x 一数〔shǔ〕一数〔shǔ〕好")
        self.assertEqual(len(m), len(s))

    def test_both_formats(self):
        import tempfile
        eth = "# 第 1 期\n\n## beat 01 [L1]\n台词：第一句。\n画面：一\n\n## beat 02 [L3] [骨架]\n台词：第二句（停顿两秒）继续。\n"
        djx = ("# 第 1 集\n\n## 场景 1 · 钩子（0:00–1:00）\n\n**画面**：x\n\n**旁白**：\n第一段。\n\n第二段。\n\n"
               "## 制作备注\n**旁白**：不该被念出来\n")
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d, "a.md"), Path(d, "b.md")
            a.write_text(eth, encoding="utf-8")
            b.write_text(djx, encoding="utf-8")
            ea, eb = S.parse(a), S.parse(b)
        self.assertEqual([x.id for x in ea.beats], ["01", "02"])
        self.assertEqual((ea.beats[0].level, ea.beats[1].level, ea.beats[1].rigor), ("L1", "L3", "骨架"))
        self.assertEqual(ea.beats[1].pauses, [(3, 2.0)])
        self.assertEqual([x.narration for x in eb.beats], ["第一段。", "第二段。"])
        self.assertEqual(eb.unit, "line")


if __name__ == "__main__":
    unittest.main()
