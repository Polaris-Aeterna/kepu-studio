"""示例（不是正式分镜）：第 1 集开头几段，演示 say / play / show 的写法。"""
from pixel.engine import *  # noqa: F401,F403
from pixel.kit import *  # noqa: F401,F403

ep = Episode("ep01", "用停机问题证明哥德尔不完备定理")


@ep.scene("S00Radio", "1930 年：希尔伯特的愿望")
def s00(s: Scene):
    s.bg(bg_night(seed=4, ground=(20, 16, 40)), fade=0)
    cap = Text("1930 年 9 月 · 柯尼斯堡", 160, 24, 14, Y, anchor="ct")
    mic = Robot(160, 120, eyes="happy", mouth="smile", face="front")
    s.add(cap, mic)
    s.play(show(cap, how="type"), show(mic, how="drop", sfx="pop"))
    s.say("1930 年 9 月，德国柯尼斯堡。68 岁的希尔伯特，当时最有影响力的数学家之一，做了一场演讲。")
    s.wait(0.3)
    s.clear()


@ep.scene("S01Hook", "1930 年：希尔伯特的愿望")
def s01(s: Scene):
    s.bg(bg_night(seed=7), fade=0.4)
    de = Text("Wir müssen wissen. Wir werden wissen.", 160, 26, 13, G, anchor="ct")
    zh = Text("我们必须知道，我们必将知道。", 160, 48, 16, Y, anchor="ct")
    cap = Text("—— 希尔伯特，1930", 160, 72, 11, G, anchor="ct")
    grave = Panel(["这句话后来刻在了他的墓碑上"], 160, 92, anchor="ct")
    s.add(de, zh, cap, grave)
    s.play(show(de, how="type"))
    s.say("他用这样一句话收尾：[“我们必须知道，我们必将知道。”]", par(show(zh, how="type"), show(cap, how="dither")))
    s.say("[这句话后来刻在了他的墓碑上。]", show(grave, how="pop", sfx="pop"))
    s.clear()
    belief = Text("“数学里没有永远解决不了的问题。”", 160, 22, 12, G, anchor="ct")
    a1 = Chip("一套公理 + 推理规则", 34, 60, C, size=12)
    arr = Arrow(150, 68, 180, 68, W_, 2)
    a2 = Chip("每一个真命题都能被证明", 186, 60, O, size=12)
    hero = Robot(160, 132, eyes="happy", mouth="smile", face="front")
    s.add(belief, a1, arr, a2, hero)
    s.say("[希尔伯特相信，数学里没有永远解决不了的问题。]更具体地说，他希望找到[一套公理和推理规则]，"
          "让数学里[每一个真命题都能被证明出来]。",
          par(show(belief, how="type"), show(hero, how="rise")), show(a1, how="pop", sfx="select"),
          seq(show(arr, how="wipe"), show(a2, how="pop", sfx="select")))
    s.play(jump(hero, times=2))
    s.wait(0.4)
    s.clear()


@ep.scene("S00Title", "片头")
def s_title(s: Scene):
    title_screen(s, 1)
    stage_card(s, 1, "用停机问题证明哥德尔不完备定理", "数理逻辑 · 第一季")


@ep.scene("S99Credits", "片尾")
def s_cred(s: Scene):
    credits(s, 1)
