# engine/concepts — 六种画风的概念帧

```bash
FRAME=1 engine/render.sh engine/concepts/b_metro.py -a      # -> engine/concepts/videos/*.png
```

| 文件 | 方向 | 场景 |
|---|---|---|
| `a_monument.py` | 纪念碑谷式 | A1_Monument_Title, A2_Monument_Cut |
| `b_metro.py` | Mini Metro 式 | B1_Metro_Title, B2_Metro_Cut |
| `c_phantom.py` | 女神异闻录 5 式 | C1_Phantom_Title, C2_Phantom_Cut |
| `d_eva.py` | EVA 标题卡式 | D1_EVA_Title, D2_EVA_Cut |
| `e_nier.py` | 尼尔 UI 式 | E1_NieR_Title, E2_NieR_Cut |
| `f_hollow.py` | 空洞骑士剪影式 | F1_Hollow_Title, F2_Hollow_Cut |
| `_kit.py` | 共用的内容（子句、A 文图 1）、等距投影、`T()`/`M()`、`stack()`、`clean_glyphs()` | |

每个文件开头都有 `IDEA`、出处，以及完整的配色角色（BG / SURFACE / INK / MUTED / ACCENT）。展示页：`design/concepts.html`；审美原则：`design/TASTE_FOR_VIDEO.md`。
这些只是概念帧，没有改动 `style.py` 和 `narrated.py`。

## 渲染中发现的 ManimGL 1.7.2 坑（换皮时必须带进 style.py）

1. **同一批次里重叠的填充会混色，而不是遮挡。** 同类型的顶层对象会合成一次绘制，重叠部分会被叠加混色（浅色压在深色上会变成中间色，看起来像半透明）。解决：`_kit.stack()` 把所有对象拆到叶子，并给每个叶子不同的 `z_index`。凡是有遮挡关系的画面（等距、剪影、卡片上的字）都必须这样添加。
2. **字形路径里有离群点。** 某些字体在某些字号下，一个字的路径里会混进一个远处的点。结果可能是横贯画面的细线（PingFang “么”、冬青黑 “张” 都出现过），可能是字内的斜划痕，也可能是包围盒被撑到上万单位，导致 `align_to` / `move_to` 全部错位。解决：`_kit.clean_glyphs(text, font_size)`，参考尺寸按 0.0094 × font_size 推算，把离群点吸附到相邻的正常点上。
3. **Noto Sans / Serif CJK SC 不可用**：部分字（隧、过、跨、深……）的路径解析会坏掉。中文请用 **Songti SC**、**PingFang SC**、**Hiragino Sans GB**。
4. **PingFang 的“是”在大字号下**，重叠轮廓处会出现一条浅色细痕。展示级标题改用冬青黑（Hiragino Sans GB）或宋体。
5. `Tex(..., isolate=[...]).select_part()` 再加背景块时，在复杂场景里出现过块与字错位的情况；用 `\;` 结尾时，isolate 还会把右括号一起划进去。可靠的做法是把要高亮的部分拆成独立的 Tex 片段拼接（见 `e_nier.py`）；用 `\lor {}` 结尾可以保持运算符间距。
6. 字重常量 manimlib 没有导出：`_kit` 定义了 `ULTRALIGHT / LIGHT / MEDIUM / SEMIBOLD / HEAVY`（Pango 名称）。`"Futura Condensed ExtraBold"` 这类家族名会回退，`"Avenir Next Condensed"` + `HEAVY` 可以用。

## 自我批评记录（每个方向至少一轮）

- **A**
  - 第 1 轮：柱子互相透色（坑 1）；标题线上有一条横贯画面的细线（坑 2）；x₁ 的刻字溢出短柱；E₄ 标签压在边上；左中部有破洞。
  - 修正：z 序；字形清洗；改用冬青黑；柱子加高；标签刻在顶面；用一个大号的“3 个比特”填住破洞；缩小石板，避免出框。
- **B**
  - 第 1 轮：线路端头撞上标题；灰色线路在画面中间突兀断开；河弯处的桥没对齐；比特标签压在线路交叉点上。
  - 修正：地图整体右移；灰线加上 Mini Metro 的端头；河改成直的；标签手动定位；列车改成强调色作为焦点。
- **C**
  - 第 1 轮：x₃ 标签被画框裁掉；SAT 贴到顶边。
  - 修正：标签行内收、缩小；SAT 缩小；节点右移，避开左侧的计数块。
- **D**
  - 第 1 轮：D2 的计数块和标题、英文行重叠。
  - 修正：标题分成两档字号；计数块缩成一行；删掉与字幕重复的公式。
- **E**
  - 第 1 轮：E2 标题被离群点推出画面，还拖着一条斜线（坑 2）；E1 的高亮块错位（坑 5）；行组和面板顶边不齐。
  - 修正：字形清洗；高亮改用拆分的 Tex 片段；行组与面板顶对齐。
- **F**
  - 第 1 轮：剪影读起来像海浪；Noto Serif 的字坏掉（坑 3）。
  - 修正：剪影改为锯齿状岩线加石笋；地块改成不规则岩石轮廓；字体换成宋体。
