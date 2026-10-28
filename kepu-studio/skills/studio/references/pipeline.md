# 流程速查：文件、格式、命令

## 项目结构（`kepu init` 生成）

```
<项目>/
├── kepu.toml                 设置：引擎、音色、读音策略、分级阈值
├── kepu / kepu.bat           工具入口（调用 .kepu/toolkit）
├── AGENTS.md  CLAUDE.md      给 agent 的规矩（CLAUDE.md 引用 AGENTS.md）
├── LESSONS.md                本项目的经验账本（每期复盘追加）
├── series/系列设定.md         系列圣经：观众、分级、比喻表、美术方向、期目录、误解清单、发布格式
├── script/episodes/epNN.md   稿子（唯一的旁白来源）
├── script/storyboards/       分镜
├── notes/epNN.md             讲义（先写）
├── pron/lexicon.tsv          项目读音词典
├── engine/ 或 pixel/          渲染引擎（anime：ManimGL；pixel：像素 RPG）
├── episodes/epNN/            （anime）各期场景代码与渲染输出
├── audio/ 或 engine/audio/   配音：<期>/beats.json、beatNN.wav、_cache/
├── review/                   审稿、耳检、事故预演
└── output/epNN/              成片、字幕、逐字稿、分段、讲义 PDF、封面、投稿文案
```

## 稿子格式

```
# 第 N 期　标题
- 目标时长 / 本期讲透的一件事 / 本期问题 / 伏笔 / 事实与出处 / 黑箱

## 场景 1 · 冷开场 [L1]                ← 场景 = B 站分段；标签向下继承
### beat 01 [L2] [骨架]                 ← 也认 “## beat 01”（ETH 写法）
台词：口语中文。{2ⁿ|二的 n 次方}、数〔shǔ〕、{ε|epsilon}，……（停顿 2 秒）……
画面：这一刻画面上是什么、怎么动（跟着词走）
屏幕文字：定理 1.1　……（与讲义一致）
```

另一种写法是《地基之下》式：场景下面直接写 `**旁白**：`，每段一条，每段单独合成，适合像素引擎。

- `{显示|读法}`：字幕显示左边，配音念右边。数字、公式、上下标、缩写、外文人名都要这样写。
- `字〔读音〕`：只管紧挨在它前面的那一个字，例如 `数〔shǔ〕`，也可以写成 `数〔shu3〕`。
- `（停顿 2 秒）`：不念出来，合成后插入静音。
- 难度标签：`[L1]` 主线、`[L2]` 进阶、`[L3]` 硬核支线（可以跳过）。
- 严谨度标签：`[完整]`、`[骨架]`、`[黑箱 A→12]`、`[黑箱→文献]`。

## 命令（在项目根目录）

| 命令 | 作用 | 花钱 |
|---|---|---|
| `./kepu doctor` | 查环境 | 否 |
| `./kepu lint 稿子 [-v]` | 写稿检查：格式、读法一侧、多音字；给出可以直接运行的修法 | 否 |
| `./kepu pron "一句话"` | 单句调试读音 | 否 |
| `./kepu lexicon add "长〔cháng〕子句" [--scope user]` | 定下一个词的读音，以后都这么念 | 否 |
| `./kepu stats 稿子 [--cut L1]` | 时长、节奏、提问间隔、句长、分级与严谨度；主线精简版 | 否 |
| `./kepu voice 稿子 --dry` | 估字符、看读音决定和余额 | 否 |
| `./kepu voice 稿子 [--only 03 04] [--engine edge]` | 合成：ElevenLabs，或者免费的占位配音 | eleven：是 |
| `./kepu earcheck build 稿子` / `ingest 结果.json` | 耳检包，结果写回音色档案 | 否 |
| `./kepu greek audition [--dry]` / `ingest` | 每个音色校准一次希腊字母的英文读音 | 是（约 900 字符） |
| `./kepu art deal --subject "题材"` | 美术方向发牌 | 否 |
| `./kepu transcript 稿子` | 逐字稿、B 站分段、.srt | 否 |
| `./kepu notes new 稿子` / `build 讲义.md` | 讲义骨架；HTML 和 PDF | 否 |
| `./kepu gate 稿子 [--final]` | 四阶段关卡 | 否 |
| `./kepu selftest` | 读音引擎回归测试 | 否 |

## 渲染引擎

| | anime（ManimGL 1.7.2） | pixel（像素 RPG） |
|---|---|---|
| 依赖 | Python venv + manimgl + LaTeX + 宋体 | numpy + Pillow + 中文字体 |
| 一个单位 | beat（一段 15–40 秒，整段合成） | 一句旁白（每段单独合成） |
| 字幕 | 宋体粗字，烧录，跟随底色反相 | RPG 对话框，打字机效果，逐字同步 |
| 签名 | 判定线、大字卡、插卡（引擎计数并报警） | 宝箱、道具说明窗、误解卡和实情卡、严谨度角标 |
| 检查 | 超时 / 节奏警告（日志）、联系表 | `pixel.checklines`、`build --check`、`occlusion`、`bounds` |
| 适合 | 理论、证明、对标 3B1B | 长系列、初学者、一步步推进 |

## 配音参数（两部作品一致）

- ElevenLabs `eleven_v4`，音色 Susan（`kAIqZ7fZv234ClKXwzDx`），stability 0.5，speed 1.0，`with-timestamps` 接口（返回逐字时间）。
- 一集 25–30 分钟约 4–5 千字符。额度每月重置。账单有延迟，所以按“发出的字符”做预算。
- `eleven_v4` turbo 半价。同一期之内不要混用两种模型。
