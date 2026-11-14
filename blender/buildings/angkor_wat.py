"""angkor_wat 寫實模型（尺寸依實測資料，公尺）"""

import math

from mathutils import Matrix, Vector, noise

from lib import TAU, Builder


# ====================================================================== 吳哥窟
def angkor_wat(path):
    b = Builder("AngkorWat", seed=9)
    grass = b.tex("grass", "grass_ground", tile=6.0, tint="#7a9a48")
    soil = b.color("soil", "#9a6a43", rough=0.95)
    water = b.color("water", "#4f6f63", rough=0.06)
    stone = b.tex("sandstone", "mossy_sandstone", tile=3.0, tint="#8c8775")
    stone_dark = b.tex("sandstone_dark", "mossy_sandstone", tile=3.0, tint="#615d50")
    laterite = b.tex("laterite", "old_sandstone_02", tile=3.0, tint="#8b6c55")
    roof = b.tex("roof", "mossy_sandstone", tile=2.0, tint="#4f4c44")

    b.ground_disc(grass, 260, soil, depth=6, rings=24, seg=128)
    # 西側參道前的兩座水池（倒影池）
    for py in (-55, 55):
        b.box_base(water, (60, 70, 0.1), (-185, py, -0.4))
        b.box_base(laterite, (62, 72, 0.4), (-185, py, -0.8))
    b.box_base(laterite, (190, 9.5, 1.2), (-215, 0, 0))  # 參道

    def tower(x, y, z, h, r):
        """蓮花苞形塔：十字凹凸平面＋多層收分，頂端尖錐"""
        prof = [(r, 0), (r, h * 0.22)]
        zz = h * 0.22
        rr = r
        tiers = 9
        for k in range(tiers):
            th = h * 0.62 / tiers
            prof += [(rr * 1.05, zz + th * 0.12), (rr * 0.97, zz + th * 0.7), (rr * 0.9, zz + th)]
            zz += th
            rr *= 0.86 if k < 5 else 0.78
        prof += [(rr * 0.6, zz + h * 0.1), (0, h)]
        b.lathe(stone, prof, (x, y, z), seg=48, smooth=False, radial=lambda t: 1 - 0.16 * abs(math.sin(2 * t)) ** 0.35 - 0.05 * abs(math.sin(8 * t)))

    def gallery(w, d, z, h, roof_h=3.0, width=6.0):
        """矩形迴廊：外牆＋石造屋頂"""
        for sx, sy, ww, dd in [(0, d / 2, w, width), (0, -d / 2, w, width), (w / 2, 0, width, d), (-w / 2, 0, width, d)]:
            b.box_base(stone, (ww, dd, h), (sx, sy, z))
            b.box_base(stone_dark, (ww + 0.4, dd + 0.4, 0.5), (sx, sy, z + h))
            if ww > dd:
                b.tri_prism(roof, ww, dd + 0.6, roof_h, (sx, sy, z + h + 0.5))
            else:
                b.tri_prism(roof, dd, ww + 0.6, roof_h, (sx, sy, z + h + 0.5), rot_z=math.pi / 2)

    # 第三層迴廊（187 × 215 m）與西門塔
    gallery(187, 215, 0.5, 5.0)
    b.box_base(laterite, (195, 223, 0.5), (0, 0, 0))
    for sy in (-1, 0, 1):
        tower(-93.5, sy * 18, 6, 18 if sy == 0 else 13, 4.5 if sy == 0 else 3.5)
    # 第二層（115 × 100，高台 7 m）
    b.box_base(laterite, (100, 115, 7.0), (0, 0, 0.5))
    gallery(100, 115, 7.5, 4.5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            tower(sx * 50, sy * 57.5, 12.5, 12, 3.0)
    # 西側十字迴廊
    b.box_base(stone, (40, 40, 5.0), (-70, 0, 0.5))
    b.tri_prism(roof, 40, 7, 3, (-70, 0, 5.5))
    b.tri_prism(roof, 40, 7, 3, (-70, 0, 5.5), rot_z=math.pi / 2)
    # 中央層（60 × 60，高台 13 m）
    z = 7.5
    for k in range(4):
        w = 75 - k * 5
        b.box_base(laterite if k == 0 else stone, (w, w, 3.0), (0, 0, z + k * 3.0))
    zc = z + 12
    gallery(60, 60, zc, 5.5, roof_h=3.5, width=7)
    # 四面陡梯
    for side in range(4):
        a = side * math.pi / 2
        c, s = math.cos(a), math.sin(a)
        for i in range(24):
            t = i / 24
            dist = 37.5 - 7.5 * t
            b.box_base(stone_dark, (0.6, 5.0, 0.55), (c * dist, s * dist, z + 12 * t), rot=(0, 0, a))
    # 五座蓮花塔：中央 65 m（距地面）
    for sx in (-1, 1):
        for sy in (-1, 1):
            tower(sx * 27, sy * 27, zc + 5.5, 22, 5.2)
    b.box_base(stone, (16, 16, 6), (0, 0, zc))
    tower(0, 0, zc + 6, 65 - zc - 6, 7.5)
    # 棕櫚與林木
    for x, y in b.scatter(60, 130, 255, avoid=lambda x, y: abs(y) < 12 and x < 0, min_dist=9):
        if b.rng.random() < 0.6:
            hgt = b.rng.uniform(12, 18)
            b.cyl(b.color("palm_trunk", "#7a6650"), 0.25, 0.18, hgt, (x, y, 0), seg=7)
            for k in range(8):
                ang = k * TAU / 8
                b.box(b.color("palm_leaf", "#567a35", rough=0.8), (5.5, 0.9, 0.12), (x + math.cos(ang) * 2.4, y + math.sin(ang) * 2.4, hgt - 0.6), rot=(0, 0.45, ang))
        else:
            b.tree(x, y, 0, h=b.rng.uniform(10, 16))
    b.export(path)
