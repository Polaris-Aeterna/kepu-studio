# 科普番剧工坊 kepu-studio

这是一套做**动漫 / 动画 / 游戏风中文科普视频**的一条龙工作流，以 Claude Code 插件的形式提供。合并自两部作品的实战：

- **《地基之下》**：数理逻辑系列。像素 RPG 风，两季 27 集，每集配一讲讲义。
- **《ETH 之墙》**：复杂性理论系列。ManimGL 制作，EVA 标题卡风，6 期，每期 25–30 分钟，另有英文版。

两部作品踩过的坑和十几轮返工，都已经做进了工具和关卡里。经验总结见 `skills/studio/references/lessons.md`。

## 它解决什么

| 痛点 | kepu 的做法 |
|---|---|
| AI 配音老是念错多音字（长子句念成 zhǎng、可数、方差、行……） | **合成前就把读音定死**。三层读音词典（约 700 条内置词条，加上个人层和项目层）、上下文规则、分词陷阱检测，决定后换成替身字，字幕照写原字。还没定的地方拦下，不合成。每个词只需要定一次 |
| 希腊字母念不对（σ 念成 sick、φ 念成“非”） | **默认按英文念**。默认写法已在默认音色上逐个试听选定（π→pie、φ→phi、τ→套、ψ→赛……）。换了音色就重新试听一次，结果所有项目共用 |
| 听不出哪里念错，全片复听又太累 | **耳检包**：只截出高风险的几十处，每处 2–3 秒，一页点完。结果会写回音色档案 |
| 画风像 PPT，或者只是贴了一层游戏皮 | 用 **taste 方法**定美术方向：从 18 个动漫 / 游戏方向里发牌，写 IDEA 句并做竞品测试，渲染概念帧，请独立评委打分，最后定成风格系统 |
| 讲义、逐字稿、字幕、分段对不上 | 全部从**同一份稿子**生成：讲义（PDF）、逐字稿、B 站分段、.srt |
| 观众有的跟不上，有的嫌浅 | **分级**：难度分 L1 主线、L2 进阶、L3 硬核支线；严谨度分完整、骨架、黑箱。会统计每级占比，并能生成只保留主线的精简版 |
| “做完了吗？”没有统一答案 | **一张表的关卡**：脚本、配音、画面、发布四个阶段，有 ✗ 就不往下走 |
| 同样的错误反复出现 | **复盘回路**：每个事故都追问“为什么没被更早的关卡拦住”，然后修改系统本身，并补上回归测试 |

## 里面有什么

```
skills/        11 个技能，可以用 /kepu-studio:<名字> 调用，也可以直接说需求让它自动触发：
               studio（总流程）new art script pronounce voice notes review publish fix retro
agents/        4 个独立审稿子 agent：事实核查、教学审稿、审片、美术评委
hooks/         改完稿子自动跑读音检查（只在 kepu 项目里、只在有问题时说话）
toolkit/       kepu 工具（Python 3.9+，只用标准库）：读音引擎、配音、耳检、讲义、逐字稿、关卡……
templates/     两套渲染引擎：engine-anime（ManimGL 动漫标题卡，来自 ETH）、engine-pixel（像素 RPG，来自《地基之下》）
```

## 开始

1. 在 Claude 里说：“用 kepu 开一个新的科普系列，讲 ××”，或者运行 `/kepu-studio:new`。
2. 也可以自己在终端新建项目：
   ```bash
   python3 <插件目录>/toolkit/kepu_run.py init 我的系列 --engine anime   # 或 --engine pixel / none
   cd 我的系列 && ./kepu doctor
   ```
3. 常用的说法，直接对 Claude 说：
   - “做第 1 期”
   - “这期写稿”
   - “检查读音”
   - “配音”
   - “出讲义”
   - “审一下这期”
   - “第 3 期 2:15 的‘数’读错了”
   - “复盘”

## 依赖

| 用途 | 需要 |
|---|---|
| 读音、稿子、讲义、关卡 | Python 3.9+（只用标准库） |
| 配音 | ffmpeg。正式配音用 ElevenLabs 账号（key 只放在项目的 `.env`）；免费的占位配音要 `pip install edge-tts` |
| 讲义 PDF | Chrome 或 Edge（没有的话，用浏览器打开 HTML 再打印） |
| anime 引擎 | ManimGL 1.7.2（见 `templates/engine-anime/README.md`）、LaTeX、宋体 |
| pixel 引擎 | numpy、Pillow、中文字体（推荐 Noto Sans SC，OFL 授权） |

## 隐私与花钱

- **ElevenLabs 的 key 不要提交、不要分享、不要贴进聊天。** 只放在项目的 `.env` 里。
- 合成要花钱，所以先 `--dry` 估算字符数，问过作者再合成。一次合成最多 2000 字符，超过就拒绝。
- 个人的读音决定和音色档案存在 `~/.kepu/`。想分享给同学，用 `./kepu lexicon export --scope user` 导出。

## 关于 taste-skill

美术方向这一步用的是 taste-skill（`design-taste-frontend`）的方法。
- 插件里自带了它在视频上的浓缩版：`skills/art/references/taste-for-video.md`。
- 如果你也装了 taste-skill（放在 `~/.claude/skills/design-taste-frontend/`），art 技能会自动读它的原文。
- taste-skill 本身没有打包进来，因为它的分发许可没有写明。

## 来源与许可

- 读音词表由 jieba 和 pypinyin 的词典生成（MIT）。见 `toolkit/kepu/data/THIRD_PARTY.md`。
- 两套引擎与工作流来自作者自己的两部作品。
- 引擎改编时致敬了一些游戏和动画的画风语法，但没有使用任何原作的角色、logo、字体或素材。
