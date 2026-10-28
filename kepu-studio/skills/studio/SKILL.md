---
name: studio
description: 动漫 / 动画 / 游戏风中文科普视频的一条龙工作流（kepu-studio），合并自《地基之下》（像素 RPG，两季 27 集）和《ETH 之墙》（ManimGL EVA 标题卡，6 期）的制作经验。覆盖：立项与系列设定、美术方向（taste-skill）、讲义先行、写稿（{显示|读法}、分级、严谨度）、多音字与希腊字母读音、AI 配音与耳检、ManimGL / 像素引擎出画面、审稿、成片与 B 站发布包、复盘。用户说“做一期科普视频 / 出一期 / 开一个新系列 / 用动漫（游戏、像素、EVA）风格讲 X / 科普动画 / 下一集 / 把这期做完 / 整个流程”时用；要做其中某一步时，转到对应的 kepu-studio 技能（new、art、script、pronounce、voice、notes、review、publish、fix、retro）。
---

# kepu-studio：动漫 / 游戏风中文科普视频工作流

这套流程来自两部作品的实战和返工，见 `references/lessons.md`：
- 《地基之下》：数理逻辑系列，像素 RPG 风，两季 27 集，每集配一讲讲义。
- 《ETH 之墙》：复杂性理论系列，EVA 标题卡风，6 期，每期 25–30 分钟，还有英文版。

这套流程的核心是三句话：
1. **能强制就别检测。**
2. **决定写进文件，不靠记忆。**
3. **每个阶段都有机器关卡，人的耳朵和眼睛只花在高风险的地方。**

## 0. 先看环境

**命令入口**：
- 在 kepu 项目里（有 `kepu.toml` 的目录），所有命令都是 `./kepu …`。Windows 上用 `kepu.bat …`。
- 不在项目里，就直接用插件里的工具：`python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/kepu_run.py" …`。

**新建项目**：
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/kepu_run.py" init <目录> --engine anime   # ManimGL 动漫标题卡风（EVA 等）
python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/kepu_run.py" init <目录> --engine pixel   # 像素 RPG 风（纯 Python）
python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/kepu_run.py" init <目录> --engine none    # 自带渲染器
```

**接手已有项目**：
- 先读项目里的 `AGENTS.md`、`series/系列设定.md`、`LESSONS.md`，再运行 `./kepu doctor`。
- 插件更新以后，在项目里运行 `python3 "${CLAUDE_PLUGIN_ROOT}/toolkit/kepu_run.py" init . --upgrade`。这只刷新 `.kepu/toolkit`，稿子、词典、配音都不动。

**作者用中文，回复也用中文。**

## 1. 九个阶段，每个阶段一道关

| # | 阶段 | 产出 | 关卡（机器） | 人看什么 | 技能 |
|---|---|---|---|---|---|
| 0 | 立项 | `series/系列设定.md`：观众、分级、比喻表、期目录；本期的“讲透的一件事”；事故预演 | 设定里每一节都填了 | 作者拍板选题和观众 | `new` |
| 1 | 美术方向 | 3–6 个方向的概念帧（标题卡 + 内容帧）；选定后得到风格圣经和样式代码 | 每个方向都有 IDEA 句、过了竞品测试；评委打分 | 作者从样张里选 | `art` |
| 2 | 讲义先行 | `notes/epNN.md`：定义、定理（带严谨度）、误解、习题 | `kepu notes build` 能出 PDF | 数学对不对 | `notes` |
| 3 | 写稿 | `script/episodes/epNN.md`：beat、`{显示\|读法}`、`字〔读音〕`、[L1–L3]、[严谨度]、（停顿） | `kepu lint` 0 处拦下；`kepu stats` 节奏、分级达标 | 读一遍：像不像人话 | `script`、`pronounce` |
| 4 | 审稿 | `review/epNN_*.md`：🔴 必改 / 🟠 应改 / 🟡 可改，每条附出处 | 🔴 清零；数字都有复算脚本 | 作者看 🔴 和前 10 条 🟠 | `review` |
| 5 | 配音 | `<audio>/epNN/beats.json` 和 wav | `kepu voice --dry` 估价；耳检 0 错；`kepu gate --stage voice` | 只听耳检包里那几十处（约 2 分钟） | `voice` |
| 6 | 画面 | 分镜 `script/storyboards/epNN.md`；场景代码；联系表 | 引擎的检查（超时、节奏、遮挡、出框、空白）；`gate --stage picture` | 看联系表，逐帧自我批评一轮 | `art`（风格）、引擎 README |
| 7 | 成片与发布包 | 成片、字幕、逐字稿、B 站分段、讲义 PDF、封面、投稿文案 | `kepu gate --final` 全 ✓ | 作者自己上传（agent 不替作者发布） | `publish` |
| 8 | 复盘 | `LESSONS.md` 新条目；词典、规则、检查的升级 | 每个事故都对应一个系统改动 | 作者看一眼 | `retro` |

**顺序可以重叠**：画面可以先用免费的占位配音（`--engine edge`）做，等稿子定了再换正式配音，这样不浪费钱。
**不能跳过的是关卡**：有 ✗ 就停下来修，不要“先往下做，回头再说”。

## 2. 元认知：这套流程怎么防止自己出错

细节见 `references/metacognition.md`。每次开工前，先过一遍这五个问题：
1. **事故预演**：这一期最可能在哪里翻车？例如：
   - 读音：新的领域词、裸写的“数”、希腊字母。
   - 事实：日期、四舍五入、署名。
   - 画面：遮挡、出框。
   - 节奏：连续 5 分钟没有问题抛给观众。
   每一条都要对应到某个关卡。对应不到的，就加一个检查。
2. **决定写在哪**：作者定下的东西必须落到文件里。
   - 读音进 `pron/lexicon.tsv`，或者写成 `字〔读音〕`。
   - 配色进系列设定。
   - 希腊字母的读法进音色档案。
3. **检查器可信吗**：新检查器上线前，先喂已知的坏例子。whisper 判断不了读音，所以不用它验收。
4. **偏好问作者**：读音、配色、措辞这类事，给作者 5–6 个候选的试听或样张，让作者选。不要靠猜。
5. **花钱、对外先问**：
   - ElevenLabs 合成：先 `--dry` 报字符数和余额。
   - 发布：只准备好文件夹，不替作者上传。

## 3. 一期的标准动作（作者说“做第 N 期”时）

```bash
./kepu lint script/episodes/epNN.md && ./kepu stats script/episodes/epNN.md    # 稿子过关
# 审稿：并行派 kepu-studio:kepu-fact-checker 和 kepu-studio:kepu-pedagogy-reviewer 两个子 agent（见 review 技能）
./kepu voice script/episodes/epNN.md --dry                                      # 估价 → 问作者 → 合成
./kepu voice script/episodes/epNN.md
./kepu earcheck build script/episodes/epNN.md                                   # 把耳检页发给作者听
./kepu earcheck ingest <作者导出的结果>.json                                     # 念错的改掉，重录那几个 beat
# 画面：按引擎 README 写场景代码，分段渲染，每段出联系表，自我批评改一轮；kepu-studio:kepu-av-reviewer 审片
./kepu transcript script/episodes/epNN.md && ./kepu notes build notes/epNN.md
./kepu gate script/episodes/epNN.md --final
```

## 4. 分派和并行（大活怎么拆）

- **先手工做完一个范例**，再并行铺开。范例可以是一期、一个场景或一处修法。把范例写进分派说明，各个 worker 的风格和质量才会一致。
- **分派说明要自包含**：
  - 背景，以及必读文件：`AGENTS.md`、系列设定、引擎 README、本期稿子和分镜。
  - 规矩、命令。
  - 禁止事项：
    - 不改共享引擎；
    - 不改稿子正文，要改就写进本期 NOTES.md；
    - 不合成配音，除非已经批准；
    - 不渲染别人的期。
  - 范例。
  - 汇报格式：
    - 做了什么，花了多少字符；
    - 自我批评改了哪些地方；
    - 还有哪些不满意；
    - 对稿子的疑问。
- **每个 worker 只写自己那一期的文件夹**。共享引擎只由一个“引擎作者”改，而且必须向后兼容。证明方法：改动前后各渲染同一帧，比较像素哈希。
- **渲染两集两集地跑**：7 个渲染同时跑，会把 10 核机器的负载推到 200，电脑卡死。

## 5. 汇报给作者

- 中文、简短，附上完成时间的估计。
- 读音问题给试听剪辑，画面问题给联系表或截图。
- 说清楚三件事：哪些做完了，哪些还在跑，哪些要作者定。
- 花了钱的，写清楚字符数。

## 参考

| 文件 | 内容 |
|---|---|
| `references/lessons.md` | 两部作品的经验总结：事、根子、以后怎么做、插件里落在哪 |
| `references/pipeline.md` | 每个阶段的文件、命令、关卡，以及脚本格式速查 |
| `references/metacognition.md` | 事故预演、决定账本、检查器校准、复盘回路 |
| 项目里的 `engine/README.md` 或 `pixel/README.md` + `pixel/GUIDE.md` | 两套渲染引擎的组件、规则、坑 |
