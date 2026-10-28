# pixel/：8/16-bit 像素 RPG 引擎（来自《地基之下》）

纯 Python 实现：只用到 numpy、Pillow 和 ffmpeg，不需要 ManimGL，也不需要 LaTeX。

- 画布：320×180 的像素画布，放大 6 倍到 1080p，30fps。另有一层 640×360 的细字层，用来放公式和小字。
- 字幕：画成 RPG 对话框，打字机效果，逐字跟着配音走，左边是机器人头像。
- 配音：读 `./kepu voice` 生成的 `audio/<期>/beats.json`，在这里不会再调用任何 TTS。
- 写分镜：看 `GUIDE.md`。里面有画面约定、动作、部件和配色语义，《地基之下》两季 27 集都是照它做的。

## 1. 安装

```bash
pip install numpy pillow        # 用哪个 python 跑都行，有这两个包就可以
./kepu doctor                   # 逐项检查依赖
```

字体：
- 把 Noto Sans SC 的 `NotoSansSC-Bold.ttf` 和 `NotoSansSC-Regular.ttf` 放进 `assets/fonts/`。它们是 OFL 授权，可以从 fonts.google.com 下载。《地基之下》用的就是这一套，像素感最好。
- 没放的话，会依次退回到系统字体：黑体、冬青黑体、微软雅黑、Noto CJK。
- 公式字体会自动找 STIX Two Math，Windows 上退回 Cambria Math。

## 2. 一期的流程（在项目根目录执行）

```bash
./kepu lint script/episodes/ep01.md          # 稿子里的读音问题要全部解决，才能合成
./kepu voice script/episodes/ep01.md         # 合成配音，写到 audio/ep01/。要花钱，先加 --dry 预估、问过再跑；--engine edge 免费，可以先用来做画面
# 写分镜 pixel/ep01.py：每条旁白用一句 s.say("……[触发词]……", show(obj))，文字必须和稿子的显示文字一字不差
python -m pixel.checklines ep01              # 检查分镜里的旁白和稿子是否逐字一致 → OK
python -m pixel.build ep01 --check           # 检查时间线，以及有没有超过 3 秒的空白画面
python -m pixel.build ep01 --only S03Foo --sheet --step 1.5    # 指定场景的联系表，存成 output/ep01/sheet_*.png
python -m pixel.build ep01 --still S03Foo:12.5                 # 渲染单帧 PNG
python -m pixel.occlusion ep01 --json        # 遮挡检查：有没有东西被对话框盖住、字有没有被压住
python -m pixel.bounds ep01                  # 出框检查
python -m pixel.build ep01 --jobs 2          # 渲染整集，输出 output/ep01/ep01_pixel.mp4、.srt、chapters.txt
./kepu gate script/episodes/ep01.md          # 关卡：每个阶段的状态汇总成一张表
```

几点说明：
- 稿子用《地基之下》的格式最顺手：`## 场景 k · 名字` 下面写 `**旁白**：`，每一段是一条，单独合成。
  - `s.say` 和这些段落一一对应，按顺序念。
  - 稿子里的“场景”就是分镜里的 `@ep.scene(...)`，也就是 B 站的分段。
- 背景音乐放在 `assets/music/theme.mp3`，没有就不加。成片会响度标准化到 −16 LUFS，旁白响起时音乐自动压低。
- 并行渲染：默认两集两集地做。7 集同时跑，10 核机器的负载到了 200，电脑卡死。

## 3. 硬规矩（摘自 GUIDE.md，违反了成片就要返工）

- **内容区**：y ∈ [4, 134]。对话框 (3,138)–(316,177) 在有旁白时**最后画**，下面的东西都会被盖住（作者在第 2 集 7:14 发现的）。
- **细字层**永远画在像素层上面。弹窗盖不住细字，所以弹窗出现时要先把下面的细字 hide 掉。
- **标签高度**：11 号字 21 像素，12 号 22 像素，14 号 25 像素，16 号 28 像素。上下堆叠时，间距要大于字高。
- **字形陷阱**：
  - `·`（U+00B7）会被当成中文间隔号，变宽；公式里的乘号用 `⋅`。
  - `✗` 没有字形，用 `Icon("cross")`。
  - 像素字里数字 `1` 很像 `I`，B1F 会被读成 BIF。
- **配色语义**（全季统一）：青/蓝 = 符号、证明；橙 = 意义、真；紫 = 黑箱；绿 = 完整；黄 = 骨架、定理标题；红 = 错误、误解。
- **世界观**：游戏比喻是入口，不是定义。全季固定一张比喻表，比如 黑箱 = 宝箱、定理 = 道具说明窗、误解卡 = 红色。
