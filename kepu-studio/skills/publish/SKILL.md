---
name: publish
description: 科普视频成片后的发布包：拼接与响度（−16 LUFS）、字幕、B 站标题（三选一）、简介、标签、合集、分段章节、置顶评论、创作声明、封面（16:9 与 4:3）、讲义 PDF，准备好发布文件夹交给作者上传（agent 不替作者发布）。用户说“发布 / 投稿 / B 站文案 / 标题怎么起 / 简介 / 置顶评论 / 封面 / 上传准备”时用。
---

# 成片与发布包

**规矩：不替作者发布。** 不上传 B 站、抖音、网盘，不发朋友圈。发布文件夹准备好，上传由作者自己做。

## 1. 成片

- **anime 引擎**：
  ```bash
  engine/.venv/bin/python engine/assemble.py epNN -o output/epNN/epNN_final.mp4
  ```
  这一步做三件事：拼接；双遍 loudnorm，目标 −16 LUFS、真峰值 −1.5 dBTP；输出 srt。最后看打印出来的实测响度。
- **任何引擎、任何来源的成片**都可以单独测和校正（gate 的 release 阶段也会测）：
  ```bash
  ./kepu loudness output/epNN/epNN_final.mp4          # 实测 LUFS、真峰值
  ./kepu loudness output/epNN/epNN_final.mp4 --fix    # 两遍 loudnorm → epNN_final.norm.mp4，画面不重编码
  ```
- **pixel 引擎**：
  ```bash
  python -m pixel.build epNN --jobs 2
  ```
  输出 `output/epNN/epNN_pixel.mp4`、`.srt`、`chapters.txt`，另带一个 720p 预览。
- **字幕**：
  - 已经烧录在画面里的，**不要**再上传 srt 作为 CC 字幕，否则会出现两行。
  - 英文版字幕不烧录，YouTube 直接用 srt。
- **成片之后**：
  ```bash
  ./kepu transcript script/episodes/epNN.md
  ./kepu notes build notes/epNN.md
  ```

## 2. `output/epNN/publish.md`（投稿文案，照《ETH 之墙》的格式）

```
# 第 N 期 B 站投稿文案
## 标题
单集标题（三选一，推荐第一个）：
1. **谜题或搜索词：一句话｜系列名 NN**
2. ……
3. ……
合集里的短标题：……
## 投稿设置
| 封面 | output/epNN/cover_16x9.png（4:3 用 cover_4x3.png） |
| 类型 | 自制 |  | 分区 | 知识 → 科学科普（以投稿页当前名称为准） |
| 标签 | 10 个左右：主题词、人名、领域、“数学科普” |
| 合集 | 加入合集「系列名」，填短标题 |
| 创作声明 | 该视频使用人工智能合成技术（旁白为 AI 合成语音；脚本与动画在 AI 协助下制作） |
| 字幕 | 已烧录，不要再上传 srt |
## 简介（复制即可）
```

**简介的结构**：
1. 一段钩子。
2. 本期要点 6–10 条。每条是一句带具体数字或例子的话，不写“本期我们将介绍”。
3. 系列目录。
4. 论文或参考文献：只写有把握的。预印本要注明“尚未经过同行评审”。
5. 制作说明：用了什么工具，配音是 AI 合成，脚本与动画在 AI 协助下完成。哪些地方做了简化，哪些例子用程序验算过。

**置顶评论**：不超过 1000 字。写思考题（对应讲义习题编号）、讲义下载方式、勘误，最后贴上分段（`chapters.txt`）。

**标题**：“谜题加搜索词”。封面文字和标题都**不能说出本期要纠正的误解**。

## 3. 封面

- 16:9 和 4:3 各排一版，不要裁切。避开右下角的时长角标和底部的播放量条。
- 画风和片头章节卡一致。
- anime 引擎：写一个 `Cover16x9` / `Cover4x3` 场景，用 `FRAME=1 engine/render.sh` 出 PNG。
- pixel 引擎：用 `pixcover.py` 里的画法函数，或者写一个封面场景，用 `--still` 出图。

## 4. 发布前

```bash
./kepu gate script/episodes/epNN.md --final
```
这一步要求全部 ✓。占位配音、没做的耳检、成片比稿子旧，都算 ✗。

最后告诉作者三件事：
- 文件夹在哪里；
- 要复制哪几段文字；
- 哪几项要在投稿页上手动选。

如果是返工，还要写清楚哪几集要在 B 站换视频文件。
