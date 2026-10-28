# engine/ — 动漫标题卡风的 ManimGL 引擎（来自《ETH 之墙》）

ManimGL **1.7.2** · 1920×1080 · 30fps · 中文配音 + 烧录宋体字幕。默认风格是 **EVA 标题卡**：黑底、暖白墨、压扁的宋体 Heavy、
红色是唯一的“判定”色。换画风时按 `kepu-studio:art` 技能重写 `style.py` 的配色、字体和组件，`narrated.py` 的接口不变。
六种动漫 / 游戏画风的概念帧代码在 `concepts/`（纪念碑谷、Mini Metro、女神异闻录 5、EVA、NieR、空洞骑士），总览图
`concepts/concepts_overview.png`。

## 1. 安装（每台电脑一次）

```bash
python3 -m venv engine/.venv                       # Python 3.11–3.13
engine/.venv/bin/pip install -r engine/requirements.txt
# 还需要：ffmpeg、LaTeX（公式；macOS 装 MacTeX 或 BasicTeX）、宋体（macOS 自带 Songti SC）
./kepu doctor                                      # 逐项检查
```

## 2. 流程（命令都在项目根目录执行）

```bash
./kepu lint script/episodes/ep01.md                # 写稿时：0 处拦下才能合成
./kepu voice script/episodes/ep01.md --dry         # 免费：字符数、读音决定、余额
./kepu voice script/episodes/ep01.md               # 合成（花钱，先问）→ engine/audio/ep01/beats.json + beatNN.wav
./kepu voice script/episodes/ep01.md --engine edge # 免费占位配音（先做画面，最后换正式配音）

engine/render.sh episodes/ep01/ep01_opening.py Ep01_01_Opening   # → episodes/ep01/videos/<Scene>.mp4 + .srt + .timeline.json
QUALITY=low engine/render.sh ...                   # 480p 快速预览（时长不变）
FRAME=1 engine/render.sh ...                       # 只存最后一帧 PNG
engine/.venv/bin/python engine/assemble.py ep01 -o output/ep01/ep01_final.mp4   # 拼接 + 响度 −16 LUFS + srt
engine/.venv/bin/python engine/resrt.py episodes/ep01                           # 不重渲，按规则重导字幕
./kepu gate script/episodes/ep01.md                # 一张表的关卡
```

- 场景代码放在 `episodes/epNN/`，场景命名 `EpNN_KK_Name`；一个场景 2–5 分钟、若干个 beat，方便返工。
- 场景里 `chapter = "ep01"` 对应 `engine/audio/ep01/`（`./kepu voice` 按稿子文件名 `ep01*.md` 定）。
- 每期标题写在 `engine/episodes.json`（`ChapterCard(n)` / `NextEpisodeCard(n)` 从这里取）。
- 端到端样例：`./kepu voice engine/demo/demo.md --engine edge`，然后 `QUALITY=low engine/render.sh engine/demo/demo_scene.py DemoNarrated`。

每个场景文件的开头：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "engine"))
from style import *                 # 配色、字体、组件，同时 re-export manimlib
from narrated import NarratedScene
```

## 3. 风格规范

### 3.1 配色（只用这些常量，代码里不出现裸 hex）

| 常量 | 值 | 角色 |
|---|---|---|
| `BG` | #0A0A0A | 底色：近黑，不是 #000 |
| `SURFACE` / `SURFACE_2` | #171717 / #232323 | 一档 / 二档明度台阶：面板、格子、卡片、表格条纹 |
| `INK` | #ECEAE4 | 主墨：暖白，不是 #fff |
| `INK_2` | #8D8A84 | 次墨：说明、标签、未激活的值 |
| `DIM` | #3C3B39 | 熄灭：假的文字、轴线、未点亮的站点 |
| `RED` | #D8361F | **判定**：这一屏唯一要看的东西 |
| `PAPER` / `PAPER_INK` | #E9E6DE / #0A0A0A | 反相底（插卡、白底段落） |

- **红色规则**：红色在任何一屏的面积都很小（一根判定线、一个字、一道标记、一条曲线），每屏最多一处，最多再加一个呼应。标题、正文、装饰一律不用红。
- **真 / 假**不用两种颜色表达：真 = 反相（墨色块配底色字）或者全亮的 `INK`；假 = `DIM` / `INK_2`。红色只留给“违反 / 判定 / 结论”。
- **禁止**：渐变、发光、阴影、半透明叠层、到处细线框（线条用 ≥4px 的实线，`HighlightBox` 每屏最多一个）、紫色、霓虹、`FlashAround` / `Indicate` / `Wiggle` 这类闪烁强调。

### 3.2 字体层级

| 用途 | 函数 | 字体 | 字号（font_size） |
|---|---|---|---|
| 大字卡 | `Display()` / `BigCard()` | 宋体 Heavy，横向压缩到 0.74 | `SIZE_XL` 280 · `SIZE_L` 200 · `SIZE_M` 132 |
| 内容标题 | `Heading()` | 同上 | `SIZE_H1` 72，固定在左上角 |
| 正文 | `CText()` | 宋体 Regular（强调用 `weight=BOLD`） | `SIZE_BODY` 34 |
| 标签、说明 | `CText(.., SIZE_SMALL, INK_2)` | 宋体 | 28 / `SIZE_TINY` 22 |
| 字幕 | 自动 | 宋体 Bold | `SIZE_SUB` 32 |
| 公式 | `Formula()` / `ZhTex()` | LaTeX Computer Modern；`ZhTex` 里的中文用宋体 | `SIZE_FORMULA` 52 |
| 英文小字（卡片副标题、人名） | `Latin()` | Baskerville | 24–30 |

- 一屏最多三档字号：一个很大的、一个正文、一个小的。
- **字体禁用清单**（`style.BANNED_FONTS`，用了会直接报错）：`Noto Sans CJK SC`、`Noto Serif CJK SC`，它们在 1.7.2 里会坏字。PingFang 在 ≥90 号时“是”字有瑕疵（会警告）。中文只用宋体；PingFang 只在小字号里偶尔使用。
- 不要给标题里的某个词单独上色或加斜体。需要指向某个东西时，用 `Mark()`（红色短粗条）。

### 3.3 版面

- 画面 14.22 × 8。内容放在 **x ∈ [−6.4, 6.4]、y ∈ [−2.75, 3.5]** 之内；**y < −2.75 是字幕区**（`SUBTITLE_Y = −3.42`），不要放东西。
- 只有一条文字锚线：`ANCHOR_X = −6.4`，用 `at_anchor(mob, y)` 对齐。右侧对齐线是 `RIGHT_X = 6.4`。大字卡的“错落”就是在这两条线之间交替。
- 一屏一个主体。内容时刻留白要大：主体占画面一半左右，其余是底色。不用边框、网格或装饰去填空，空的时候把主体放大。
- 字幕是画面的一部分：宋体粗、无底框，颜色跟着底色反相（白底段落会自动变黑字）。

## 4. EVA 组件（style.py）

| 组件 | 用法 |
|---|---|
| `Display(text, size)` | 压扁宋体 Heavy，大字专用 |
| `BigCard(lines, layout="stagger"/"left"/"right"/"center", vertical=False, en=None)` | 全屏大字卡。lines 可以是字符串，或 `(text, size[, color])`；`vertical=True` 时为竖排，每行一列、从右往左读；`en` 是英文小字 |
| `ChapterCard(1, "SAT 是什么", en="EPISODE 1    What is SAT?")` | 每期的标题卡（一期一次） |
| `ChapterCard(3)` / `NextEpisodeCard(3)` / `scene.next_episode(3)` | 标题与英文行取自 `style.EPISODES`（全系列唯一的一张表）；预告卡 = 下一期的章节卡 + “下一期” |
| `TitleCard(title, subtitle)` | 单标题大字卡 |
| `InsertCard(lines, ground="paper"/"black", en=None)` | 反相插卡：满屏纸色底配黑字，配合 `scene.insert(card, hold)` |
| `Heading("子句与 CNF")` | 内容时刻的标题（左上角） |
| `CText` / `Latin` / `Markup` / `Formula` / `ZhTex` / `ZhTexText` | 文本与公式 |
| `Panel(mob)` / `block(w, h, color)` / `full_frame(color)` | 明度台阶面板 / 实心块 / 满屏底 |
| `PaperCard(title, org, extra)` | 论文卡片（标题支持 `2^{o(n)}` 写法） |
| `Mark(mob, RED)` + `mark_anim(mark)` | 指向：短粗条从左长出 |
| `InvertTag("3-SAT")` | 反相小标签 |
| `HighlightBox(mob)` | 6px 红框（少用） |
| `highlight_part(tex, "x_1", RED)` | 公式子串变色 |
| `BoolVar(1, value, caption="小一", style="01"/"TF")` | 变量格：真 = 反相格；`.animate_set(v)` 翻转 |
| `Clause([1, -2, 3])` / `CNF([[..],[..]])` | `.evaluate_anims(assign)`：真文字亮、假文字熄灭；子句下方条为白（满足）或红（违反） |
| `SimpleGraph(V, E, layout, bits={..}, node_labels={..})` | 六边形节点图，边的粗细与标签来自比特数；`line, marks, c = g.cut(side)` 生成红色判定线、过切口的标记和比特数 |
| `GrowthPlot(..).plot_base(2, label=r"2^n", color=RED)` | 增长曲线（对数纵轴） |
| `Timeline([(1971, "Cook–Levin"), (2026, "ETH 被证伪", RED)])` | 时间线 |
| `JudgeLine(p, q)` + `judge_sweep(line)` + `cut_apart(left, right, line)` | 红色判定线：划出，然后两侧分开 |
| `rise_in(mob)` / `rise_lines(mobs)` | 安静的入场：上移 + 淡入，quint-out |
| 缓动 `EASE_OUT` / `EASE_EXPO` / `EASE_INOUT` / `EASE_EXIT` | 见 §6 |

所有组件的样张：`FRAME=1 engine/render.sh engine/demo/components_demo.py -a`。

## 5. 节奏系统：为 3 小时设计

EVA 风格的风险是单调和压迫感（概念帧自评可持续性 3/5）。所以系统里内建四种“时刻”，按规则轮换：

| 时刻 | 怎么做 | 占时长 | 频率上限 |
|---|---|---|---|
| **内容时刻**（默认） | `Heading` + 一个主体（公式 / 图 / 表），正文 34、公式 52，留白大，红色最多一处 | ~80% | — |
| **大字时刻** | `scene.big(BigCard(..))`：硬切进全屏大字，停 1.5–3 秒 | 短 | **每期 ≤ 8 次，两次间隔 ≥ 20 秒**；每期的 `ChapterCard` 用 `count=False`，不计数 |
| **插卡** | `scene.insert(InsertCard(..), hold=0.8–1.5)`：纸色反相帧闪切，配音继续 | 极短 | **每期 ≤ 6 次，两次间隔 ≥ 20 秒**；用在结论句、反转句上（“是错的”） |
| **白底段落** | `scene.set_ground("paper")` 之后用 `PAPER_INK` 作墨（`scene.ink` 会返回当前墨色） | 每段 ≤ 90 秒 | 每期 1–2 段：定义卡、阶段回顾。给眼睛换一次气 |

- 引擎会帮你数：违反间隔规则时打 `WARNING [eva] ...`；场景超过 2 分钟、平均每 2 分钟超过 1 次大字卡时，结束时也会警告。**交付前必须清零这些警告。**
- **冷开场**（每期前 3 分钟）允许 3 次大字 / 插卡，用来抓人；之后回到正常节奏。
- 一期里，大字时刻集中在：开场、问题提出、定理陈述、反转、结尾。推导过程中不用。
- 内容时刻内部也要换构图：公式居中 → 左文右图 → 表格 → 满屏图。相邻的 beat 不要用同一种布局。

## 6. 动效原则

- **硬切为主**：每个 beat 开头用 `self.cut_to(...)` 整屏硬切（会同时复位镜头）。不要用 `FadeOut` 全部再 `FadeIn`；`clear_stage()` 默认也是硬切。
- **签名动作：判定线。** 一条红色竖线匀速划过画面，在中线处硬切到下一幕：`self.judge_cut(*mobs)`。它的变体是在画面里画一条红线，然后让两边分开：`judge_sweep` + `cut_apart`（切割、裂缝、“切一刀”）。**每期 ≤ 3 次**，只用在章节转换和真正的“切割”时刻上，用多了就不再是签名。
- **大字卡和插卡永远硬切**，不加淡入、不加缩放。
- **内容元素的入场**：`rise_in` / `rise_lines`（上移 0.15–0.3、淡入、quint-out，0.4–0.9 秒），列表逐行进，最多 4 级错落。曲线用 `ShowCreation(rate_func=EASE_OUT)`；线条和标记用 `EASE_EXPO`。
- **缓动曲线**：
  - 入场：`EASE_OUT`（quint out）；
  - 长揭示、判定线：`EASE_EXPO`；
  - 两点之间移动、镜头推拉：`EASE_INOUT`；
  - 离场：`EASE_EXIT`（时长为入场的 60–70%）；
  - 匀速扫过：`linear`；
  - **禁止**回弹、弹性、`there_and_back`、`wiggle`。
- **时长**：小变化 0.3–0.45 秒；入场 0.5–0.9 秒；镜头 1.2–1.8 秒。
- **镜头**：`self.camera.frame.animate.scale(..).move_to(..)` 推近，每期 ≤ 2 次；下一次 `cut_to` 会自动复位。
- **和配音同步**：`run_time=self.until("词")`、`self.wait_until_beat("词")`。画面上的变化发生在说出那个词的时刻，而不是整段台词的开头。
- 文字正在被读时，不要有东西从它上面经过。

## 7. NarratedScene / EvaScene API

```python
class Ep1_02_Variables(NarratedScene):
    chapter = "ep1"                                   # engine/audio/ep1/
    def construct(self):
        self.beat("07")                               # 本 beat 的音频从现在开始；字幕跟随
        self.cut_to(Heading("三条约束"), formula)       # 硬切
        self.play(rise_in(c1), run_time=self.until("第一条"))
        self.wait_until_beat("第二条")
        ...
        self.insert(InsertCard("暂停一下"), hold=1.0)   # 插卡（配音继续）
        self.beat_wait()                              # 补足到音频结束 + 0.4 秒
```

| 方法 | 作用 |
|---|---|
| `beat("07")` / `beat_wait()` | 开始 / 结束一个 beat。动画超出音频会警告，下一段音频顺延，绝不重叠 |
| `until(x)` / `wait_until_beat(x)` / `word_time(x)` | x 为秒数，或台词里的一个词（显示文本的子串） |
| `beat_duration` / `beat_time()` / `beat_remaining()` | 本 beat 的音频时长 / 已过时间 / 剩余时间 |
| `cut_to(*mobs, ground=None)` | 硬切 |
| `big(card, hold, count=True)` | 大字时刻（计数） |
| `insert(card, hold)` | 插卡（计数） |
| `judge_cut(*mobs)` | 签名转场 |
| `set_ground("black"/"paper")`、`self.ink` | 切换底色；返回当前底色对应的墨色 |
| `set_subtitles(False)` | 临时关闭字幕 |

台词里的 `{显示|读法}`：字幕显示左边、TTS 读右边。读法里可以带读音标记 `数〔shǔ〕`，标记永远不进字幕。显示文本里的 `^{..}`、`_x` 在字幕里会变成上 / 下标。
`until("词")` 用的是 ElevenLabs 的逐字时间戳（映射回字幕原字、并按音频停顿校正过），精度约一帧。台词改了以后，场景里的提示词可能不存在了：样片里的 `cue(word, frac)` 在找不到词时退回按比例取时间，可以照抄。

## 8. 引擎已自动处理的坑（知道就行）

1. **填充重叠会混色**（ManimGL 用 alpha 混合计算环绕数）：`style.py` 重写了 `Scene.assemble_render_groups` 和 `update_frame`，只在包围盒重叠时才另起批次，画家顺序 = 场景顺序 + 家族顺序。所以“后加的盖住先加的”是成立的，不需要再手动 `stack()` 或设 z_index。
2. **字形离群点**（横贯画面的细线、字内斜划痕、包围盒爆掉）：`CText` / `Display` / `Latin` / `Markup` 都会自动调用 `clean_glyphs()`。**请始终用这些函数，不要直接 `Text(...)`。**
3. `MarkupText` 在 1.7.2 里直接用会报错，请用 `Markup()`。
4. manimlib 没导出的字重常量 `LIGHT / MEDIUM / SEMIBOLD / HEAVY` 由 `style` 提供。

## 9. 仍需注意的坑

1. **永远经过 `render.sh`**（它会带上 `-w`）。裸 `manimgl file.py Scene` 或只加 `-s` 会弹出窗口并卡死。
2. 要把公式的一部分放进反相块里，请**拆成独立的 Tex 片段**再拼接（见 `ep1_opening.py` 里的 `truth_rows`）。`select_part()` + 背景块在复杂场景里出现过错位。
3. Tex 里写中文要用 `ZhTex`；`Formula` 走 pdflatex，不认中文。
4. `always_redraw` 里重建 `Display` 文字（例如滚动计数）可以用，但每帧都要排版，慢；只在短时间内使用。
5. 系统没有 ffprobe，看时长用 `ffmpeg -i x.mp4 2>&1 | grep Duration`。
6. 改了台词：重跑 `tts.py --only NN`，再重渲染对应的场景。
7. 交付前 checklist：
   - 日志里没有 `WARNING [narrated]`（超时）和 `WARNING [eva]`（节奏）；
   - 抽帧检查：没有东西压进字幕区、没有出框、每屏红色不超过一处；
   - `ffmpeg -i ... -af silencedetect` 检查：每个 beat 的语音起点约等于 `.timeline.json` 里的起点 + 0.2 秒。

## 10. 读音、配音与字幕（交给 kepu）

- 配音、读音（多音字替身字、希腊字母英文读法）、耳检、逐字稿都由 `./kepu` 负责，见插件技能 `kepu-studio:voice`、`kepu-studio:pronounce`。
- `beats.json` 的格式与《ETH》的 tts.py 相同，`NarratedScene.until("词")` 用的是逐字时间戳（已按音频停顿校正，精度约一帧）。
- 台词里的 `{显示|读法}`：字幕显示左边、配音念右边；`字〔读音〕` 永远不进字幕；`（停顿 2 秒）` 合成后插入静音。
- 字幕切分规则（只在标点或词边界切、不切进引号和公式、不足 1.2 秒的并入相邻行）在 `subtitles.py`。

## 11. 英文版

`from style_en import *`，场景类写 `LANG = "en"`：英文字体（Times New Roman Bold 压扁 0.78）、英文字幕切分、字幕不烧录
（YouTube 用 .srt）。英文稿子放 `script/en/`，配音同样用 `./kepu voice`（英文读音靠 respelling 表，见《ETH》的经验）。
