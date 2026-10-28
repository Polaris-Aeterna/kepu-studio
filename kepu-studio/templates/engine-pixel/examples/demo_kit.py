from pixel.engine import *  # noqa
from pixel.kit import *  # noqa
ep = Episode("ep01", "test")


@ep.scene("K1", "kit")
def _(s):
    s.bg(bg_dungeon())
    card = Card("引理 1.8", ["A 可判定，当且仅当 A 和它的补集都可枚举。"], 160, 6, color=Y, fine=True, fsize=18)
    badge = Badge("full")
    g = Grid(4, 4, 20, 50, 14, 14, labels=[["0", "1", "2", "3"]] * 4)
    c1 = g.cell(1, 2, E)
    ch = Chest("D", 200, 110)
    b1, b2 = Bulb(True, 250, 110, "p"), Bulb(False, 280, 110, "q")
    rb = Robot(120, 130)
    bub = Bubble("列不完！", 120, 80, tail=(0, 8))
    f = F("∀x∃y(x<y)   T ⊢ φ   ℕ ⊨ φ   ¬Halt(e, n)", 160, 72, 18, C, anchor="ct")
    s.add(card, badge, g, c1, ch, b1, b2, rb, bub, f)
    s.say("这里说的“机器”，就是图灵机。你可以把它想成[任何一门编程语言写的程序]，只是内存不受限制。精确的定义在第 10 集。",
          par(show(card, how="pop"), show(badge), show(g), show(c1), show(ch), show(b1, b2), show(rb), show(f, how="type")))
    s.play(open_chest(ch), mood(rb, eyes="happy", mouth="smile", arms="up"), show(bub, how="pop"))
    s.wait(1.5)
