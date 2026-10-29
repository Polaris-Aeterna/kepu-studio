# 宣传片的源码

这支 1 分 45 秒的宣传片，从稿子、读音、配音到画面，全部是用 kepu-studio 自己做的。它同时是一个完整的 anime 引擎项目范例：想知道“一期”具体长什么样，就看这里。

成片在 [Releases](https://github.com/Polaris-Aeterna/kepu-studio/releases) 里（`kepu-studio_promo.mp4`，1080p）。

| 文件 | 内容 |
|---|---|
| `script/episodes/promo.md` | 稿子，13 个 beat。beat 02 的 `{zhǎng 子句\|涨子句}` 是“显示 \| 读法”写法：字幕显示左边，配音念右边。片中故意演示的那个错误读音，就是这样写出来的 |
| `script/storyboards/promo.md` | 分镜：本片 IDEA、节奏预算、每个 beat 的卡型和红色落点。`kepu board` 通过 |
| `episodes/promo/promo.py` | 4 个 `NarratedScene`（ManimGL 1.7.2）。画面变化跟着词走：`wait_until_beat("词")` |
| `engine/sfx.py` | 音效和底乐，全部用 numpy 合成，没有采样，也就没有版权问题 |
| `assets/wave.json` | 《ETH 之墙》第一期整集的音量包络，耳检那一幕的波形就是它 |
| `kepu.toml` | 项目设置（key 只放在 `.env`，不在仓库里） |

## 制作记录

```bash
./kepu lint script/episodes/promo.md            # 13 个 beat，拦下 0；长子句→cháng、重新→chóng、几十处→chù 都是引擎自己定的
./kepu voice script/episodes/promo.md --dry     # 450 字符
./kepu voice script/episodes/promo.md           # ElevenLabs · Susan · eleven_v4，配音 96 秒
./kepu board script/storyboards/promo.md        # 大字 2、插卡 1、判定线 3，通过
engine/.venv/bin/python engine/sfx.py           # 音效 → assets/sfx/
engine/render.sh episodes/promo/promo.py -a     # 1080p，4 个场景
engine/.venv/bin/python engine/assemble.py --dirs episodes/promo -o output/promo/promo_raw.mp4 --no-loudnorm
engine/.venv/bin/python engine/sfx.py --bed 105.6 --title 16.233 --end 96.867   # 底乐；两个时间点取自各场景的 timeline.json
```

底乐压在旁白下面（旁白一响，底乐自动让开），然后校正响度：

```bash
ffmpeg -i output/promo/promo_raw.mp4 -i assets/sfx/bed.wav -filter_complex \
  "[0:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,asplit=2[nar][sc];\
   [1:a]volume=-10dB[bed0];[bed0][sc]sidechaincompress=threshold=0.015:ratio=5:attack=12:release=380[bed];\
   [nar][bed]amix=inputs=2:duration=first:normalize=0[mix]" \
  -map 0:v -map "[mix]" -c:v copy -c:a pcm_s16le output/promo/promo_mixed.mov
./kepu loudness output/promo/promo_mixed.mov --fix -o output/promo/kepu-studio_promo.mp4   # −16.1 LUFS，真峰值 −1.7 dBTP
```

## 素材

`assets/img/` 没有放进仓库。里面是：

- 两部作品的成片帧：《ETH 之墙》第一、五期；《地基之下》第十二集；
- ETH 的四张概念帧（`D1_EVA_Title`、`B1_Metro_Title`、`C1_Phantom_Title`、`E1_NieR_Title`），以及它们真实的 taste 评委分数；
- 希腊字母试听页的截图。

换成你自己系列的帧，改 `promo.py` 里的文件名就能重做一支。

这些素材和宣传片成片保留所有权利，不适用仓库的 MIT 许可（见 [`docs/README.md`](../../docs/README.md)）；这个目录里的代码是 MIT。

## 做这支片子时顺手修掉的问题

宣传片也是一次完整的“吃自己的狗粮”。它撞出了三个问题，都已经修进 v0.2.0：

- `kepu loudness --fix` 输出 AAC 时，真峰值会超出上限 0.2 dB → 现在给 AAC 留 0.6 dB 余量。
- `kepu status` 和 `gate` 找分镜时只认 `期号.md`，找不到 `ep1_sat.md` 这种和稿子同名的分镜 → 现在先找同名文件。
- 稿子目录不在项目文件夹里时，`kepu status` 会报错退出 → 已修。

还有一条留作教训：拿真实项目试新命令时，输出目录先指到临时文件夹，别往原项目里写。
