"""taj_mahal 寫實模型（尺寸依實測資料，公尺）"""

import math

from mathutils import Matrix, Vector, noise

from lib import TAU, Builder


# ====================================================================== 泰姬瑪哈陵
def taj_mahal(path):
    b = Builder("TajMahal", seed=17)
    grass = b.tex("grass", "grass_ground", tile=4.0, tint="#5f8a36")
    soil = b.color("soil", "#6b5338", rough=0.95)
    marble = b.tex("marble", "marble_01", tile=3.0, tint="#eeebe4", normal=0.5)
    marble_shade = b.tex("marble_recess", "marble_01", tile=3.0, tint="#d8d2c6", normal=0.5)
    inlay = b.color("inlay", "#3a3530", rough=0.4)
    gold = b.color("finial", "#c9a142", rough=0.3, metal=0.9)
    red = b.tex("red_sandstone", "red_sandstone_wall", tile=2.5, tint="#a4523c")
    water = b.color("water", "#5f87a3", rough=0.04)
    pathm = b.tex("walkway", "red_sandstone_wall", tile=2.0, tint="#b48a6e")
    cypress = b.color("cypress", "#294d27", rough=0.85)

    b.ground_disc(grass, 260, soil, depth=5, rings=24, seg=128)
    # 南北向花園水道與步道（mausoleum 位於 +Y 側）
    cy0 = 70.0
    b.box_base(pathm, (14, 260, 0.08), (0, cy0 - 170, 0))
    b.box_base(water, (6, 250, 0.12), (0, cy0 - 170, 0.0))
    b.box_base(pathm, (240, 12, 0.08), (0, -40, 0))
    b.box_base(water, (230, 5, 0.12), (0, -40, 0))
    b.box_base(marble, (20, 20, 1.2), (0, -40, 0))
    b.box_base(water, (16, 16, 0.1), (0, -40, 1.2))
    for y in [cy0 - 50 - k * 9 for k in range(22)]:
        if abs(y + 40) < 12:
            continue
        for x in (-11, 11, -24, 24):
            b.tree(x, y, 0, h=b.rng.uniform(9, 12), kind="cypress")
    # 紅砂岩台基與白色大理石基座（95 × 95 × 6.7 m）
    b.box_base(red, (300, 112, 1.2), (0, cy0, 0))
    b.box_base(marble, (95, 95, 6.7), (0, cy0, 1.2))
    for side in range(4):  # 基座立面的拱形壁龕
        a = side * math.pi / 2
        for k in range(-7, 8):
            dx, dy = math.cos(a - math.pi / 2), math.sin(a - math.pi / 2)
            px = dx * 47.55 + math.cos(a) * k * 6.0
            py = cy0 + dy * 47.55 + math.sin(a) * k * 6.0
            b.box_base(marble_shade, (3.6, 0.2, 4.2), (px, py, 2.2), rot=(0, 0, a))
    z0 = 7.9

    # 主體：56.6 m 見方、切角，各面中央有巨大尖拱門（pishtaq）
    s, c = 28.3, 9.0
    octo = [(-s + c, -s), (s - c, -s), (s, -s + c), (s, s - c), (s - c, s), (-s + c, s), (-s, s - c), (-s, -s + c)]
    b.prism(marble, octo, z0, 33.0, M=Matrix.Translation((0, cy0, 0)))
    b.prism(marble_shade, octo, z0 + 33.0, 1.2, M=Matrix.Translation((0, cy0, 0)))
    for side in range(4):
        a = side * math.pi / 2
        dx, dy = math.cos(a - math.pi / 2), math.sin(a - math.pi / 2)
        # 拱門外框（略凸出、較主體高）
        fx, fy = dx * (s + 0.4), cy0 + dy * (s + 0.4)
        M = Matrix.Translation((fx, fy, z0)) @ Matrix.Rotation(a, 4, "Z")
        b.profile_wall(marble, [(-11, 0), (11, 0), (11, 35.5), (-11, 35.5)], 1.2, M)
        # 書法飾框
        Mf = Matrix.Translation((fx + dx * 0.62, fy + dy * 0.62, z0)) @ Matrix.Rotation(a, 4, "Z")
        for u0, u1, v0, v1 in [(-9.6, -9.0, 2, 32.5), (9.0, 9.6, 2, 32.5), (-9.6, 9.6, 32.0, 32.6)]:
            b.profile_wall(inlay, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], 0.1, Mf)
        # 尖拱凹龕
        arc = b.arch_points(14.0, 18.0, "pointed", 16)
        Mr = Matrix.Translation((fx + dx * 0.66, fy + dy * 0.66, z0)) @ Matrix.Rotation(a, 4, "Z")
        b.profile_wall(marble_shade, [(-7, 0), (7, 0)] + list(reversed(arc))[1:-1], 0.1, Mr)
        arc2 = b.arch_points(5.0, 9.0, "pointed", 12)
        b.profile_wall(b.color("door", "#4a4036", rough=0.9), [(-2.5, 0), (2.5, 0)] + list(reversed(arc2))[1:-1], 0.12, Mr @ Matrix.Translation((0, -0.05, 0)))
        # 切角面上下兩層較小尖拱龕
        for sd in (-1, 1):
            a2 = a + sd * math.pi / 4
            ddx, ddy = math.cos(a2 - math.pi / 2), math.sin(a2 - math.pi / 2)
            dist = (s - c / 2) * math.sqrt(2) * 0.707 + 0.05
            for zz in (1.5, 17.5):
                M2 = Matrix.Translation((ddx * dist * 1.0 + 0, cy0 + ddy * dist, z0 + zz)) @ Matrix.Rotation(a2, 4, "Z")
                arc3 = b.arch_points(7.0, 9.5, "pointed", 12)
                b.profile_wall(marble_shade, [(-3.5, 0), (3.5, 0)] + list(reversed(arc3))[1:-1], 0.3, M2)
    # 屋頂四角的小亭（chhatri）
    def chhatri(x, y, z, r, h_col):
        for k in range(8):
            a = TAU * k / 8
            b.cyl(marble, r * 0.08, r * 0.07, h_col, (x + r * 0.82 * math.cos(a), y + r * 0.82 * math.sin(a), z), seg=8)
        b.cyl(marble, r * 1.12, r * 1.12, r * 0.18, (x, y, z + h_col), seg=24)
        b.lathe(marble, [(r * 0.95, 0), (r * 1.05, r * 0.35), (r * 0.9, r * 0.75), (r * 0.5, r * 1.05), (r * 0.15, r * 1.25), (0, r * 1.32)], (x, y, z + h_col + r * 0.18), seg=28)
        b.cyl(gold, r * 0.06, 0.0, r * 0.7, (x, y, z + h_col + r * 1.45), seg=8)

    zr = z0 + 34.2
    for sx in (-1, 1):
        for sy in (-1, 1):
            chhatri(sx * 18.5, cy0 + sy * 18.5, zr, 4.2, 5.5)
    # 鼓座與洋蔥形主穹頂（頂端距地約 73 m）
    b.cyl(marble, 13.2, 13.2, 7.0, (0, cy0, zr), seg=48)
    b.cyl(marble_shade, 13.5, 13.5, 0.8, (0, cy0, zr + 6.2), seg=48)
    dome = [(13.2, 0), (15.6, 3.5), (16.6, 8.0), (16.2, 12.5), (14.4, 16.5), (11.2, 20.0), (7.2, 22.8), (3.6, 24.8), (1.4, 26.2), (0.0, 27.0)]
    b.lathe(marble, dome, (0, cy0, zr + 7.0), seg=64)
    b.lathe(gold, [(1.0, 0), (1.6, 1.0), (0.5, 2.0), (1.1, 3.2), (0.35, 4.4), (0.25, 7.5), (0.6, 8.0), (0, 9.0)], (0, cy0, zr + 7.0 + 26.6), seg=16)
    # 四座宣禮塔（高 40 m，三層陽台）
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * 44.5, cy0 + sy * 44.5
            b.cyl(marble, 3.3, 2.6, 40.0, (x, y, z0), seg=24)
            for zz in (12.5, 25.0, 36.5):
                b.cyl(marble_shade, 4.1, 3.6, 0.9, (x, y, z0 + zz), seg=24)
                b.cyl(marble, 4.0, 4.0, 1.0, (x, y, z0 + zz + 0.9), seg=24)
            chhatri(x, y, z0 + 40.0, 3.2, 3.5)
    # 兩側紅砂岩清真寺與答辯廳（各三座白色穹頂）
    for sx in (-1, 1):
        x = sx * 120
        b.box_base(red, (28, 56, 15), (x, cy0, 1.2))
        b.box_base(marble, (28.6, 56.6, 1.0), (x, cy0, 16.2))
        M = Matrix.Translation((x - sx * 14.1, cy0, 1.2)) @ Matrix.Rotation(-sx * math.pi / 2, 4, "Z")
        arc = b.arch_points(9.0, 7.0, "pointed", 12)
        b.profile_wall(b.color("door", "#4a4036", rough=0.9), [(-4.5, 0), (4.5, 0)] + list(reversed(arc))[1:-1], 0.3, M)
        for dy, r in ((-17, 5.0), (0, 7.0), (17, 5.0)):
            b.cyl(red, r * 0.9, r * 0.9, 2.0, (x, cy0 + dy, 17.2), seg=24)
            b.lathe(marble, [(r * 0.9, 0), (r * 1.05, r * 0.5), (r * 0.8, r * 1.1), (r * 0.3, r * 1.5), (0, r * 1.65)], (x, cy0 + dy, 19.2), seg=32)
        for dy in (-28, 28):
            b.cyl(red, 1.6, 1.4, 22, (x - sx * 14, cy0 + dy, 1.2), seg=12)
            chhatri(x - sx * 14, cy0 + dy, 23.2, 2.0, 2.2)
    b.export(path)
