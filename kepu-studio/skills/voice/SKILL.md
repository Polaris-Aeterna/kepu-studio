---
name: voice
description: 给科普视频合成 AI 配音（ElevenLabs，或免费的 edge-tts 占位）并做耳检：先 --dry 估字符和余额、问作者、分小批合成（每条立刻存缓存，只有改过的句子才花钱）、生成“耳检包”只听高风险的几十处、把作者的判断写回音色档案、只重录念错的 beat。用户说“配音 / 合成 / 生成旁白 / TTS / 重录 / 换音色 / 额度 / 听一下读音”时用。
---

# 配音与耳检

## 规矩（花钱的操作）

- **先估价，再问，再合成。** 作者在消息里明确说“合成”或“配音”，算已经批准。
- 一次运行最多发 2000 字符（`kepu.toml` 的 `max_chars`）。超过就一个字都不发，要先问作者，再加 `--max-chars`。
- **先做一小批，验证方法没问题，再全量。** 例如先合成冷开场的 3 个 beat。
- API key 只在 `.env` 或环境变量里。**不要打印，不要复制，不要让作者贴进聊天。**
- 余额不要低于 10,000：账户可能是几个项目共用的。账单有延迟，所以按“发出的字符”做预算。
- 同一期之内不要混用两种模型（例如 `eleven_v4` 和它的 turbo 版），否则前后音色不一致。

## 流程

```bash
./kepu voice script/episodes/epNN.md --dry
```
`--dry` 不花钱。它报告每个 beat 是“缓存”还是要新合成多少字符、被拦下的 beat 及其修法、送拼音的地方、总字符数，以及 ElevenLabs 余额。
有拦下的 beat，先按 `kepu-studio:pronounce` 解决，不要用 `--force`：它会让模型自己去猜。

```bash
./kepu voice script/episodes/epNN.md --only 01 02 03    # 先合成一小批
./kepu voice script/episodes/epNN.md                    # 再合成全部；已经合成过的走缓存，不花钱
./kepu voice script/episodes/epNN.md --engine edge      # 免费占位配音，先用来做画面；最后再换正式配音
./kepu quota
```
输出在 `<audio>/epNN/`：
- `beatNN.wav`（48 kHz 单声道）；
- `beats.json`：显示文字、念的文字、发给模型的文字、逐字时间，以及读音记录；
- `durations.json`。

两套引擎都直接读这些文件。（停顿）会在合成后插入静音，逐字时间随之平移。

## 耳检：只听高风险的几十处

```bash
./kepu earcheck build script/episodes/epNN.md      # → review/earcheck/epNN/index.html
```
页面里每一处是一段 2–3 秒的片段，从那个字前 1.3 秒开始，并标出应该念什么。作者逐条点“对”或“错”，快捷键：J/K 翻、空格播放、1 对、2 错。听完点“导出结果”。
把页面路径或文件发给作者（SendUserFile）。说清楚一共几处、预计 2 分钟听完。

耳检包收录这几类：
- 送拼音的地方；
- 第一次用的新替身字；
- 还没在这个音色上验证过的希腊字母；
- 词典给了非默认读音的低频词；
- 缩写（问的是：逐字母念还是当单词念）；
- 第一处数字；
- 5 处随机抽查的已强制替身字。这是对照组，用来确认“确定的”那部分也真的念对了。

```bash
./kepu earcheck ingest ~/Downloads/earcheck_epNN_results.json
```
作者判“对”的，记进音色档案（`~/.kepu/voices/<音色>.json`），以后同一个音色不再收录。
判“错”的，按类型处理：
- **替身字错**：这个替身字记为不可用，重录时自动换下一个；
- **拼音错**：改写这一句；
- **希腊字母错**：`kepu greek audition --letters X` 换一个拼写；
- **低频词错**：在词典里定下读音。

改完之后只重录列出来的 beat：`./kepu voice … --only 07 12`。改完再跑一次 `earcheck build`，只听改过的那几处。
`kepu gate --stage voice` 会读耳检状态：有没处理的“错”就不放行。

耳检页是**单个 HTML 文件**：音频以 mp3 内嵌在页面里，可以直接发给作者或同学，用手机也能听、能点。

**花钱记录**：每一条付过钱的合成（缓存命中不算）都会追加到 `review/cost.tsv`：日期、期、beat、字符数、音色。`./kepu quota` 会顺带汇总本项目花了多少；`./kepu status` 的表头也会显示。共享账号时，用它对账。

## 换音色

1. 用 `--only` 试 2–3 个音色。每个音色合成同一段（约 400 字）。
2. 比较语速（字/分钟）、停顿、对齐是否完整。
3. 请作者听，作者选定以后，改 `kepu.toml` 的 `voice_id` / `model`。
4. 缓存键包含音色和模型，换了音色不会误用旧录音；换回原来的音色也不用重新花钱。
5. **新音色要重新做希腊字母校准**：`kepu greek audition`。替身字的验证记录也是按音色分开记的。

## 迁移老项目（例如 ETH）

缓存键的算法和 ETH 的 `engine/tts.py` 相同。把 `kepu.toml` 的 `[voice] cache` 指向老项目的 `engine/audio/_cache`，发给模型的文字没变的句子直接复用老录音。实测 ETH 第 1 期有 63% 的字符命中；没命中的，是 kepu 新增保护的地方。
