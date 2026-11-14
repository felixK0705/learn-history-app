"""giza 寫實模型（尺寸依實測資料，公尺）"""

import math

from mathutils import Matrix, Vector, noise

from lib import TAU, Builder


# ====================================================================== 吉薩金字塔群
def giza(path):
    b = Builder("Giza", seed=3)
    sand = b.tex("sand", "sand_01", tile=12.0, tint="#d6b98a")
    sand_side = b.color("sand_side", "#a88a5f", rough=0.95)
    core = b.tex("core", "old_sandstone_02", tile=6.0, tint="#c7a679")
    casing = b.tex("casing", "white_sandstone_blocks_02", tile=5.0, tint="#d9cbb0")
    granite = b.tex("granite", "rock_04", tile=4.0, tint="#7f5b4c")
    rockm = b.tex("bedrock", "old_sandstone_02", tile=8.0, tint="#b99a70")

    def dunes(x, y):
        p = Vector((x * 0.002, y * 0.002, 0))
        return 6 * noise.noise(p) + 2 * noise.noise(p * 4) - 0.004 * max(0, 700 - math.hypot(x + 300, y + 350)) * 0

    b.ground_disc(sand, 1150, sand_side, depth=40, height_fn=lambda x, y: dunes(x, y) * min(1, max(0, (math.hypot(x + 300, y + 350) - 520) / 300)), rings=48, seg=128)

    def pyramid(cx, cy, base, height, layers, top_trunc=0.0, casing_from=None, granite_to=0.0, base_z=0.0, base_y=None):
        """以逐層石階堆疊（外層石灰岩已剝落，露出階梯狀核心）"""
        by = base_y or base
        lh = height / layers
        for k in range(layers):
            z = k * lh
            if top_trunc and z > height - top_trunc:
                break
            f = 1 - z / height
            w, d = base * f, by * f
            if casing_from is not None and z >= casing_from:
                # 卡夫拉頂部仍保留的平滑外殼
                top_h = height - z
                b.frustum(casing, (w, d), (0.6, 0.6), top_h, (cx, cy, base_z + z))
                break
            m = granite if z < granite_to else core
            b.box_base(m, (w, d, lh * 1.02), (cx, cy, base_z + z))

    # 位置依實際經緯度換算（以古夫金字塔為原點，+X 東、+Y 北）
    pyramid(0, 0, 230.3, 146.6, 64, top_trunc=8.0)  # 古夫（現高約 138.5 m）
    b.frustum(rockm, (232, 232), (226, 226), 4, (-330, -345, 0))
    pyramid(-330, -345, 215.3, 143.5, 56, top_trunc=7.0, casing_from=112, base_z=4)  # 卡夫拉（地勢較高）
    pyramid(-580, -745, 102.2, 65.5, 32, granite_to=7.5, base_y=104.6)  # 孟卡拉（底部花崗岩外殼）
    for k, (dx, dy) in enumerate([(140, 60), (140, 0), (140, -60)]):  # 古夫的王后金字塔
        pyramid(dx, dy - 20, 46, 29, 12, top_trunc=6 + k * 3)
    for k in range(3):  # 孟卡拉的王后金字塔（階梯狀）
        x = -680 + k * 50
        for s in range(4):
            w = 44 - s * 10
            b.box_base(core, (w, w * 0.9, 5.2), (x, -860, s * 5.2))
    # 馬斯塔巴墓群（東西兩側成排）
    for gx, gy in [(-230, 60), (220, -40)]:
        for i in range(5):
            for j in range(7):
                if b.rng.random() < 0.25:
                    continue
                b.frustum(core, (22, 11), (20.5, 9.8), b.rng.uniform(3, 6), (gx + i * 32, gy + j * 20, 0))

    # 獅身人面像（面向東）：長 73 m、高 20 m
    sx, sy = 330, -430
    b.frustum(rockm, (110, 70), (100, 60), 0.1, (sx - 15, sy, -4.0))
    body = b.tex("sphinx", "old_sandstone_02", tile=4.0, tint="#c09a6c")
    b.rock(body, (57, 13, 13), (sx - 6, sy, 6.0), rough=0.04, seed=11)  # 身體
    b.rock(body, (18, 12, 8), (sx - 30, sy, 4.0), rough=0.05, seed=12)  # 後臀
    for s in (-1, 1):
        b.rock(body, (16, 3.6, 3.0), (sx + 26, sy + s * 4.2, 1.5), rough=0.04, seed=13 + s)  # 前爪
    b.rock(body, (7.5, 9.5, 6), (sx + 20, sy, 11.5), rough=0.04, seed=15)  # 胸
    b.frustum(body, (6.5, 11.0), (3.5, 5.0), 7.0, (sx + 20.5, sy, 12.5))  # 頭巾
    b.rock(body, (4.2, 4.6, 5.0), (sx + 23.5, sy, 16.5), rough=0.04, seed=16)  # 臉
    # 獅身像周圍的鑿坑邊牆與河谷神廟
    for dx, dy, w, d in [(-20, 26, 90, 4), (-20, -26, 90, 4), (-64, 0, 4, 56)]:
        b.box_base(rockm, (w, d, 9), (sx + dx, sy + dy, -4))
    b.box_base(core, (45, 45, 10), (sx + 70, sy - 20, 0))
    # 卡夫拉參道
    L = math.hypot(330 + 330 - 60, 345 - 430)
    b.box_base(core, (L, 5, 1.2), ((330 + 40 - 330) / 2 - 10, (-430 - 345) / 2 + 20, 0), rot=(0, 0, math.atan2(-430 + 345, 330 + 330)))
    b.export(path)
