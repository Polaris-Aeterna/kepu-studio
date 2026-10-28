> **kepu 版说明**：这份指南写于《地基之下》第一季，那时的分镜是在给“原版”（ManimGX 版）重做画面。凡是提到“原版 epNN/scenes.py”
> “AI_SEGMENTS”“即梦镜头”“pixel/narr/”“ep01_art / ep02_parts / ep03_parts”的地方都是历史背景。在 kepu 项目里：
> 旁白的唯一来源是稿子 `script/episodes/epNN.md`；配音由 `./kepu voice` 生成在 `audio/epNN/`；
> `python -m pixel.checklines epNN` 对照的是配音里的显示文字。画面约定、动作、部件、配色语义、遮挡规则全部照旧有效。
> 流程见同目录 `README.md`。

# 像素版分镜写作指南（给写 pixel/epNN.py 的人）

目标：把《证明的极限》第 NN 集按 **像素勇者（8/16-bit RPG）画风** 完全重做。旁白一字不改（直接用原版的
ElevenLabs 缓存，不产生任何费用），画面全部重新设计。成片 1920x1080 30fps，由 `pixel/build.py` 渲染。

## 1. 硬性规则
1. **旁白一字不改，顺序不变。** 每个 `s.say("…")` 的文字（去掉方括号后）必须与原版 `epNN/scenes.py` 里
   对应 `self.say(...)` 的文字完全一致；原版 `AI_SEGMENTS` 里即梦镜头的 `line` 也照样用 `s.say(line)` 念出来
   （它们有缓存，但没有逐字时间，只能整句配画面，不能用方括号）。原版循环里念的（如 MISCONCEPTIONS 的
   speech）也要逐条念。缓存里找不到的文字会直接报错——**绝不能调用任何 TTS / 视频生成 API**。
   检查：`python -m pixel.checklines epNN` 必须输出 `OK`。
2. **场景结构跟原版走。** 原版 `SCENES` 列表的顺序 = 你的 `@ep.scene` 顺序；`AI:xxx` 镜头改成像素场景
   （名字如 `S00Radio`），旁白照念。第一个场景前面加一个 `S00Title`，只调用 `title_screen(s, NN)`；原版里出现
   `episode_title(...)` 的地方用 `stage_card(s, NN, "本集标题", "数理逻辑 · 第一季")`；最后一个场景
   `S99Credits` 只调用 `credits(s, NN)`。每个场景的 title（`@ep.scene(name, title)` 第二个参数）写成章节名
   （同一章的几个场景用同一个 title，B 站分段会合并）。原版 bilibili.md 的“分段”标题可直接借用。
3. **不能出现“只有字幕的空白画面”。** 每句旁白开始后 1 秒内画面上就要有与这句话相关的东西；内容区
   （对话框以上）只有背景超过 3 秒算空白。检查：`python -m pixel.build epNN --check` 必须报告 0 段空白。
4. **数学必须对。** 定义、定理、公式照原版画面上的内容写（可简化排版，不能改意思）；不能写出原版
   “常见误解”里纠正的说法。黑箱 A–F 的含义与“第几集打开”和原版一致。
5. 只写 `pixel/epNN.py`（以及需要的话 `pixel/epNN_*.py` 辅助文件）。**不要改** `engine.py`、`kit.py`、
   `build.py` 和别的集的文件；引擎有 bug 或缺功能，在你的文件里局部绕开，并在报告里写清楚。

## 2. 画面约定
- 画布 320x180 像素（放大 6 倍）。**内容区 y ∈ [4, 134]**，底部 y ≥ 138 是对话框（字幕 + 机器人头像，自动画，
  打字机效果与语音逐字同步，你不用管）。x 保持在 [6, 314]。
- 细字层（`F(...)`、`fine=True`）永远画在像素层**上面**：别让细字压在别的像素对象上。
- 字号：像素字 `Text(..., size)` 至少 11，正文 12，标题 14–20。长句、公式用细字层（`F(...)` 或
  `fine=True`，字号按 640 层给，16–20），像游戏里的小字。中文像素字一行最多约 22 字（12 号）。
- 配色语义（全季统一）：**青/蓝 C、B = 符号、证明、语法**；**橙 O = 意义、真、语义**；**紫 LILAC = 黑箱**；
  **绿 E = 完整/正确**；**黄 Y = 骨架/强调/定理标题**；**红 R = 错误/误解**；米白 W_ = 正文；灰 G = 次要。
- 世界观：这是一款 RPG。每集是一个 STAGE；主角是小机器人（`Robot`），它会对内容做出反应（`jump`、
  `mood(robot, eyes="happy")`）。**黑箱 = 宝箱**：`Chest("A")`，打开用 `open_chest(chest)`。定理/引理 =
  黄标题的 `Card`（像道具说明窗）；定义 = 青标题 `Card`；误解 = 红标题“误解”卡 + 绿标题“实情”卡；严谨程度
  角标 `Badge("full"|"sketch"|"box", note)` 放右上角。可以加 HP 条、对话气泡、宝箱、怪物、关卡地图等游戏元素，
  但信息要清楚：观众看完要学到和原版一样的东西。
- 节奏：出现动画要快（pop / dither / type / drop，0.15–0.5 秒），在**方括号开头**触发；不要让东西拖满整句才出现。
  一句长旁白里可以有多个方括号，把画面分几步搭起来。换话题时 `s.clear()`。
- 每个场景开头用 `s.bg(...)` 设背景：`bg_night`、`bg_dungeon`、`bg_meadow`、`bg_room`、`bg_split`（蓝橙分屏：
  左符号右意义）、`bg_grid`、`bg_plain(color)`、`cover_bg(NN)`，或用 `pc.Pix` 自己画一张 320x180 的图。

## 3. 写法
```python
from pixel.engine import *   # Scene, Episode, 动作, 颜色
from pixel.kit import *      # 部件、角色、背景、pc（像素封面里的画法函数）

ep = Episode("ep01", "用停机问题证明哥德尔不完备定理")

@ep.scene("S00Title", "1930 年：希尔伯特的愿望")
def _(s: Scene):
    title_screen(s, 1)

@ep.scene("S01Hook", "1930 年：希尔伯特的愿望")
def _(s: Scene):
    s.bg(bg_night(seed=7))
    zh = Text("我们必须知道，我们必将知道。", 160, 48, 16, Y, anchor="ct")
    grave = Panel(["这句话后来刻在了他的墓碑上"], 160, 92)
    s.add(zh, grave)                                   # 先 add，默认不可见
    s.say("他用这样一句话收尾：[“我们必须知道，我们必将知道。”]", show(zh, how="type"))
    s.say("[这句话后来刻在了他的墓碑上。]", show(grave, how="pop", sfx="pop"))
    s.clear()
```
完整示例：`pixel/examples/demo_ep01.py`（开头几段）、`pixel/examples/demo_kit.py`（卡片、表格、宝箱、灯泡、气泡、公式、表情）。示例里的 `from pixel.engine import *` 写法照抄即可。

### 时间线
- `s.say(script, *动作, gap=0.25)`：念一句。方括号个数 = 动作个数；每个动作在它那段方括号**开始**时触发。
  没有方括号时，动作都在句首触发。
- `s.play(*动作)`：不配旁白的动画，时间线推进到最晚结束处；`s.play(..., wait=False)` 不推进。
- `s.wait(秒)`；`s.clear(keep=(obj,…), dur=0.35)`：收掉画面上的对象。
- `s.sfx(name)`：音效（blip pop open chest error win step select hit type），也可以写在 `show(..., sfx=…)` 里。
- `s.screen_flash(color, dur)`：全屏闪白。`s.speaker`：对话框头像（目前只有 "robot"）。`s.dialog = False` 关掉对话框。

### 动作
| 动作 | 说明 |
|---|---|
| `show(*objs, how="dither", dur=None, sfx=None, over=False)` | how: `pop` `dither` `type`（打字机，`over=True` 时铺满这段方括号）`wipe` `drop` `rise` `slide_l` `slide_r` `blink` `cut` |
| `hide(*objs, how="dither", dur=0.3)` | how: `dither` `cut` |
| `move(obj, to=(x, y) / by=(dx, dy), dur=0.5, ease="out")` | 组（Group）只能按左上角 `to` 或 `by` 整体平移 |
| `flash(*objs, color=Y, dur=0.8)` | 闪烁高亮（选中/受击） |
| `shake(*objs, amp=2, dur=0.4)`、`jump(*objs, height=6, times=1)` | 抖动、跳一下 |
| `swap(a, b)` | a 消失 b 出现 |
| `frame_to(obj, img)` | 换图（表情、状态）；`mood(robot, eyes=…, mouth=…, arms=…)`、`open_chest(chest)` 是现成的 |
| `par(...)` `seq(..., gap=0)` `stagger(..., gap=None)` `after(dt, act)` | 组合：同时 / 依次 / 依次错开（gap=None 时铺满方括号时长）/ 延后 |
| `sfx(name)` `call(fn)` `nothing()` | 音效、自定义、占位 |

### 部件（坐标都按 320x180；`anchor` 两个字母：水平 l/c/r + 竖直 t/c/b，默认 lt）
- `Text(s, x, y, size=12, color=W_, anchor="lt", fine=False, math=False, outline=K, width=None, align="l")`；
  `T(...)` 同义；`F(s, x, y, size=18)` = 细字层公式（数学字体，ℕ ⊢ ⊨ ∀ ∃ ¬ ∧ ∨ → φ ψ 都能写）。
- `Panel(lines, x=160, y=20, w=None, title=None, title_color=Y, size=12, fine=False, fsize=18, anchor="ct")` → 组：
  `.frame`、`.title`、`.lines[i]`（可逐行 show）。`Card(title, lines, x, y, color=Y, fine=…)` 同理。
- `Chip(s, x, y, color=Y, size=12)` 小标签；`Badge(kind, note)` 右上角严谨度角标。
- `Window(x, y, w, h)` 空的 RPG 窗口；`Rect(x0,y0,x1,y1,color,width,fill)`；`Highlight(obj, color)` 选择框；
  `Arrow(x0,y0,x1,y1,color,width,head,dashed)`；`Line(...)`；`Dot(x, y, r, color)`；`Icon(kind, x, y)`：
  check cross heart q excl star spark；`Bubble(s, x, y, tail=(dx,dy))` 对话气泡。
- `Grid(rows, cols, x, y, cw, ch, labels=…)` 表格：`.cell(r, c, color)` 生成一个可以 show 的填色格，
  `.label(r, c)` 取格内文字对象。
- `Chest(letter, x, y, state="closed"|"locked"|"open")`；`Bulb(on, x, y, label)` 灯泡（真假赋值）。
- 角色：`Robot(x, y, eyes, mouth, face, arms)`（约 25x43，anchor 默认 cb = 脚底中点）、`Tortoise`、`Runner`、
  `Barber`、`Moon`、`CBoss`、`Blob(col)`、`Heart`、`Pawn`、`Golem`、`Spinner`、`Gadget`、`Torch`。
  自己画：`sprite(lambda p: …, w, h, x, y)`，p 是 `pc.Pix`，可用 `p.rect/box/bitmap/cjk/glyphs/window/bubble/
  hp_bar/stars/twinkle` 和 `pc.robot(p, …)` 等全部封面画法（见 `covers/pixel/make.py`）。
- 排版：`obj.place(x, y, anchor)`、`obj.next_to(other, side="b", gap=4, align="c")`、
  `hrow(*objs, y=60, gap=8, cx=160)`、`vcol(*objs, x=160, y=20, gap=6, align="c")`、`Group(*objs)`（`.place`、`.shift`）。
- 片头片尾：`title_screen(s, NN)`、`stage_card(s, NN, title, sub)`、`credits(s, NN)`。

## 4. 检查与渲染（在项目根目录，用装了 numpy 和 Pillow 的 python）
```
python -m pixel.checklines epNN                         # 旁白与原版逐字一致 → OK
python -m pixel.build epNN --check                       # 时间线 + 空白检查（几秒）
python -m pixel.build epNN --only S03Foo --sheet --step 1.5   # 某场景每 1.5 秒一帧的联系表 → pixel/out/epNN/sheet_*.png
python -m pixel.build epNN --still S03Foo:12.5           # 单帧 1080p PNG
python -m pixel.build epNN --jobs 3                      # 整集成片（几分钟）→ pixel/out/epNN/epNN_pixel.mp4
```
看联系表时注意：字有没有出框、和对话框重叠、互相压住；每句旁白有没有对应的画面；数学写得对不对。

**遮挡检查**（2026-10-26 起，成片前必做）：`python -m pixel.occlusion epNN --json` 列出两类问题——对话框开着时有东西半截压在对话框下面（对话框最后画，会把它盖住），和文字一部分被后画的东西（字、标签、机器人、气泡）盖住；`python -m pixel.occlusion_sheet epNN` 把每处渲染成一帧拼成联系表（红框被挡、黄框挡它）。逐张看，剩下的只能是有意的叠放（印章、删除线、裂纹、表格高亮、气泡里的图标）。再跑 `python -m pixel.bounds epNN` 查出框。常见原因：卡片太高把下面的标签挤进 y > 134；标签上下堆叠的间距小于标签高度（11 号 21 像素、12 号 22、14 号 25、16 号 28）；机器人或气泡放在字上。（作者 2026-10-26 指出第一季第 2 集 7:14 的红色标签被对话框挡住，之后两季全部用这个查过一遍。）

## 5. 第 1–3 集做完后补充的经验（第 4 集起必读）
- 引擎已修：`show()` 会自动 add 忘了加的对象；`flash()` 保留黑色描边（文字闪烁可读，色块/标签仍会整块变色，
  可当选中效果）；`title_screen` 不再被空白检查误报。
- 即梦镜头的旁白（`voice_ai`）没有逐字时间，但**可以用方括号**：引擎按字数比例估算方括号的时刻。
- 细字层永远画在像素层上面：弹窗盖不住细字，弹窗出现时要把底下的细字 hide 掉。
- "·"（U+00B7）会被当成中文间隔号（宽）；公式里的乘号用 "⋅"。"✗" 没有字形，用 `Icon("cross")`。
- 上下标、上划线：直接复用第 1–3 集写好的辅助函数（只读 import，不要改这些文件）：
  - `from pixel.ep03_parts import RT, FR, XCard, Tree, TT, VTag, Lamp, set_lamp, Machine, Block, Tile, Bridge,
    Brace, Pointer, Region, Stamp, Sign, Islander, bg_syn, bg_sem` —— `RT/FR` 富文本（`p_i`、`2^k`、`φ_K`），
    `Tree` 语法树（逐个节点长出来、真值沿树上流），`TT` 真值表，`XCard` 支持富文本的卡片。
  - `from pixel.ep02_parts import RText, RCard, DTable, frow, frame_around, say_at, castle, scroll, sack, ...` ——
    `DTable` 对角线表（翻转对角线、逐行比较），`RCard` 富文本卡片。
  - `from pixel.ep01_art import Fx, Fxs, card, ListBox, ProgCard, Gear, Stamp, Person, Machine, Booth, HPBar,
    MapChest, Block, Sparkle, Tape, Scroll, Lamp, Hourglass, Fish, Book, bg_city, bg_worldmap` —— `Fx` 支持
    `e‾`（上划线）与 `M_e`（下标）；`ListBox` 清单窗口；`ProgCard` 程序卡片；`Tape` 纸带。
  用之前先读一下函数签名和用法（看对应的 epNN.py 怎么调用）。
- 几个 agent 并行时共用 scratchpad：日志等临时文件名一律带集号前缀（如 `ep05_render.log`）。
- 整集渲染用 `--jobs 2`（同时有好几集在渲染）。改了分镜要重新渲染：渲染进程用的是启动时的代码。

## 6. 第 11–15 集（只有像素版、没有 ManimGX 原版）
- 旁白清单：`pixel/narr/epNN.json`（由剧本 `S1_证明的极限/scripts/epNN.md` 的“旁白”整理，语音已合成进 `epNN/voice/`）。
  它是按剧本场景分组的列表：`[{"scene": "场景 1 · 钩子", "lines": ["……", {"pause": 2.0}, "……"]}, …]`。
  每个字符串必须**原样、按顺序**各念一次：`s.say("……")`（可以加方括号，文字不能改一个字）；
  `{"pause": 秒}` 是剧本里的“（停顿）”：用 `s.wait(秒)` 配一个“暂停想一想”的画面（如倒计时，`ep01_art.Pause`）。
  `python -m pixel.checklines epNN` 会拿这个清单比对。
- 画面依据：剧本里的 **画面** 段落（按像素风改编），数学内容以讲义 `S1_证明的极限/notes/chNN.tex` 为准（定理编号照讲义）。
- 开头：`S00Title` 只调用 `title_screen(s, NN)`（封面若还没画好会先用夜空占位，最终渲染前会有封面）；剧本里
  出现“标题卡”的地方用 `stage_card(s, NN, "剧本标题", "数理逻辑 · 第一季")`；结尾 `S99Credits` 调 `credits(s, NN)`。
- 章节标题（`@ep.scene(name, title)`）：给观众看的分段名，每个剧本场景一个，16 字以内（参考第 10 集 bilibili.md 的分段风格）。
- 这几集没有即梦镜头。黑箱状态以剧本开头表格的“黑箱”一行为准（第 12 集打开 A、E 打开一半；第 13 集打开 E；
  第 14 集打开 F；第 15 集全部已开）。
