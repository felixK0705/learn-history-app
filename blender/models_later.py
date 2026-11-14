"""羅馬競技場、萬里長城、泰姬瑪哈陵、姬路城、艾菲爾鐵塔"""

import math

import bmesh
import bpy
from mathutils import Vector

from lib import Builder

TAU = 2 * math.pi


# ---------------------------------------------------------------- 羅馬競技場
def colosseum(path):
    b = Builder("Colosseum", seed=13)
    pave = b.mat("paving", "#b3a993", rough=0.95)
    pave_side = b.mat("paving_side", "#857b67")
    trav = b.mat("travertine", "#d9c8a2", rough=0.9)
    trav_dark = b.mat("travertine_dark", "#b5a17c", rough=0.95)
    shade = b.mat("shade", "#7a6a50", rough=0.95)
    sand = b.mat("arena_sand", "#d8b98a")
    brick = b.mat("brick", "#a86a4c", rough=0.95)
    grass = b.mat("grass", "#86a95a")
    b.plinth(15, pave, pave_side)
    for x, y in b.scatter(10, 12.5, 14.4):
        b.tree_cone(x, y, h=b.rng.uniform(1.6, 2.4), r=0.45, leaf=b.mat("pine", "#3d6b35"))
    b.ering(grass, (12.0, 10.4), (12.6, 11.0), 0, 0.05, seg=64)

    A, B_ = 9.4, 7.8  # 外牆半軸
    T = 0.38  # 外牆厚度
    tier_h = 0.66
    ruin = (2.55, 4.35)  # 西南側崩塌角度範圍

    def ruined(t, k):
        lo, hi = ruin
        shrink = (3 - k) * 0.12
        return k > 0 and lo + shrink < t < hi - shrink

    n_arch = 80
    for k in range(3):
        z = k * tier_h
        for i in range(n_arch):
            t = TAU * i / n_arch
            if ruined(t, k):
                continue
            x, y = A * math.cos(t), B_ * math.sin(t)
            ang = math.atan2(math.sin(t) / B_, math.cos(t) / A)
            # 拱柱（半露柱）
            b.box_base(trav, (T, 0.32, tier_h - 0.14), (x, y, z), rot=(0, 0, ang))
            b.box_base(trav_dark, (T + 0.08, 0.12, tier_h - 0.14), (x * 1.008, y * 1.008, z), rot=(0, 0, ang))
        # 每層頂部橫帶：沿完整角度但跳過崩塌區
        segs = []
        if k == 0:
            segs = [(0, TAU)]
        else:
            lo, hi = ruin
            shrink = (3 - k) * 0.12
            segs = [(hi - shrink, TAU + lo + shrink)]
        for t0, t1 in segs:
            b.ering(trav, (A - T / 2, B_ - T / 2), (A + T / 2 + 0.04, B_ + T / 2 + 0.04), z + tier_h - 0.14, z + tier_h, seg=96, t0=t0, t1=t1)
            # 拱內陰影面
            b.ering(shade, (A - T / 2 - 0.02, B_ - T / 2 - 0.02), (A - T / 2 + 0.02, B_ - T / 2 + 0.02), z, z + tier_h - 0.14, seg=96, t0=t0, t1=t1)
    # 頂層實牆（閣樓層）
    lo, hi = ruin
    b.ering(trav, (A - T / 2, B_ - T / 2), (A + T / 2, B_ + T / 2), 3 * tier_h, 3 * tier_h + 0.6, seg=96, t0=hi, t1=TAU + lo)
    for i in range(40):
        t = hi + (TAU + lo - hi) * (i + 0.5) / 40
        b.box_base(shade, (0.06, 0.18, 0.22), ((A + T / 2) * math.cos(t), (B_ + T / 2) * math.sin(t), 3 * tier_h + 0.22), rot=(0, 0, math.atan2(math.sin(t) / B_, math.cos(t) / A)))

    # 內牆與看台
    b.ering(brick, (8.2, 6.6), (8.6, 7.0), 0, 2.2, seg=96)
    tiers = [((4.6, 2.9), (5.3, 3.6), 0.0, 0.55), ((5.3, 3.6), (6.1, 4.4), 0.0, 0.95), ((6.1, 4.4), (7.0, 5.3), 0.0, 1.35), ((7.0, 5.3), (8.2, 6.6), 0.0, 1.8)]
    for inner, outer, z0, z1 in tiers:
        b.ering(trav_dark, inner, outer, z0, z1, seg=96)
        b.ering(trav, (inner[0], inner[1]), (inner[0] + 0.12, inner[1] + 0.12), z1, z1 + 0.06, seg=96)
    # 競技場地面：半邊鋪沙、半邊露出地下室牆
    b.ering(sand, (0.01, 0.01), (4.6, 2.9), 0, 0.12, seg=64, t0=-math.pi / 2, t1=math.pi / 2)
    b.ering(shade, (0.01, 0.01), (4.6, 2.9), 0, 0.02, seg=64, t0=math.pi / 2, t1=3 * math.pi / 2)
    for i in range(7):
        x = -0.5 - i * 0.55
        h = 2.9 * math.sqrt(max(0, 1 - (x / 4.6) ** 2))
        b.box_base(brick, (0.12, 2 * h - 0.2, 0.35), (x, 0, 0))
    b.box_base(brick, (4.2, 0.12, 0.35), (-2.2, 0, 0))
    b.export(path)


# ---------------------------------------------------------------- 萬里長城
def great_wall(path):
    b = Builder("GreatWall", seed=21)
    grass = b.mat("grass", "#6f9f4a")
    rock = b.mat("rock", "#7d8a5c")
    dirt = b.mat("dirt", "#5f4a33")
    wall = b.mat("wall", "#a39885", rough=0.95)
    wall_top = b.mat("wall_top", "#8a7f6c", rough=0.95)
    R = 15.0

    def height(x, y):
        r = math.hypot(x, y)
        fall = max(0.0, 1 - (r / R) ** 4)
        h = 1.6 * math.sin(x * 0.45) * math.cos(y * 0.35) + 1.2 * math.sin((x + y) * 0.25) + 2.4
        return (0.25 + max(0.0, h)) * fall

    # 極座標地形網格（邊緣高度為 0，與地台側面接合）
    rings, seg = 26, 72
    bm = b.bm
    grid = []
    for i in range(rings + 1):
        r = R * i / rings
        row = []
        for j in range(seg if i else 1):
            a = TAU * j / seg
            x, y = r * math.cos(a), r * math.sin(a)
            row.append(bm.verts.new((x, y, height(x, y))))
        grid.append(row)
    faces = []
    for j in range(seg):
        faces.append(bm.faces.new([grid[0][0], grid[1][j], grid[1][(j + 1) % seg]]))
    for i in range(1, rings):
        for j in range(seg):
            k = (j + 1) % seg
            faces.append(bm.faces.new([grid[i][j], grid[i + 1][j], grid[i + 1][k], grid[i][k]]))
    for f in faces:
        zc = sum(v.co.z for v in f.verts) / len(f.verts)
        f.material_index = rock if zc > 3.4 else grass
        f.smooth = False
    b.cyl(dirt, R * 0.97, R, 1.38, (0, 0, -1.42), seg=seg)

    # 長城路徑（沿山脊蜿蜒）
    pts = []
    x = -14.0
    while x <= 14.0:
        y = 3.2 * math.sin(x * 0.32) - 1.0 * math.cos(x * 0.7)
        if math.hypot(x, y) < R - 0.6:
            pts.append((x, y))
        x += 0.5
    wall_h, wall_w = 0.75, 0.75
    tower_every = 9
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        gz = min(height(x0, y0), height(x1, y1), height(mx, my))
        top = max(height(x0, y0), height(x1, y1)) + wall_h
        ang = math.atan2(y1 - y0, x1 - x0)
        L = math.hypot(x1 - x0, y1 - y0) + 0.06
        b.box_base(wall, (L, wall_w, top - gz + 0.6), (mx, my, gz - 0.6), rot=(0, 0, ang))
        b.box_base(wall_top, (L, wall_w - 0.12, 0.04), (mx, my, top), rot=(0, 0, ang))
        nx, ny = -math.sin(ang), math.cos(ang)
        for side in (-1, 1):
            for s in (-0.12, 0.13):
                b.box_base(wall, (0.13, 0.1, 0.16), (mx + math.cos(ang) * s + nx * side * (wall_w / 2 - 0.05), my + math.sin(ang) * s + ny * side * (wall_w / 2 - 0.05), top), rot=(0, 0, ang))
        if i % tower_every == 0:
            tz = height(mx, my)
            th = top - tz + 0.75
            b.box_base(wall, (1.5, 1.5, th + 0.6), (mx, my, tz - 0.6), rot=(0, 0, ang))
            b.box_base(wall_top, (1.62, 1.62, 0.1), (mx, my, tz + th), rot=(0, 0, ang))
            for cx in (-0.6, -0.2, 0.2, 0.6):
                for cy in (-0.72, 0.72):
                    for rot_extra in (0, math.pi / 2):
                        a2 = ang + rot_extra
                        px = mx + math.cos(a2) * cx - math.sin(a2) * cy
                        py = my + math.sin(a2) * cx + math.cos(a2) * cy
                        b.box_base(wall, (0.22, 0.12, 0.22), (px, py, tz + th + 0.1), rot=(0, 0, a2))

    def near_wall(x, y):
        return any((x - px) ** 2 + (y - py) ** 2 < 2.2 for px, py in pts)

    for x, y in b.scatter(70, 1.0, R - 0.8, avoid=near_wall):
        z = height(x, y)
        if b.rng.random() < 0.6:
            b.tree_cone(x, y, z - 0.05, h=b.rng.uniform(0.9, 1.5), r=0.32, leaf=b.mat("pine", "#2f6b34"))
        else:
            b.tree_round(x, y, z - 0.05, h=b.rng.uniform(0.7, 1.1), r=0.35, leaf=b.mat("autumn", "#c9843a"))
    b.export(path)


# ---------------------------------------------------------------- 泰姬瑪哈陵
def taj_mahal(path):
    b = Builder("TajMahal", seed=17)
    grass = b.mat("grass", "#7cae55")
    dirt = b.mat("dirt", "#6b5338")
    marble = b.mat("marble", "#f6f2ea", rough=0.35)
    marble_shade = b.mat("marble_shade", "#d9d1c3", rough=0.5)
    inlay = b.mat("inlay", "#8f8676", rough=0.6)
    gold = b.mat("gold", "#d2a63a", rough=0.3, metal=0.9)
    red = b.mat("red_sandstone", "#b1553c", rough=0.9)
    water = b.mat("water", "#4da3d6", rough=0.1)
    path_m = b.mat("path", "#d8c7a5")
    cypress = b.mat("cypress", "#2e5f34")
    b.plinth(15, grass, dirt)
    # 花園與水道（往 -Y 延伸）
    b.box_base(path_m, (2.4, 9.5, 0.03), (0, -9.2, 0))
    b.box_base(water, (0.9, 9.0, 0.05), (0, -9.2, 0.0))
    b.box_base(path_m, (18, 1.6, 0.03), (0, -9.2, 0))
    b.box_base(water, (16, 0.6, 0.05), (0, -9.2, 0.0))
    b.box_base(marble, (1.6, 1.6, 0.2), (0, -9.2, 0))
    b.box_base(water, (1.2, 1.2, 0.05), (0, -9.2, 0.2))
    for y in [-5.4 - k * 1.2 for k in range(8)]:
        for x in (-1.6, 1.6):
            b.cyl(cypress, 0.3, 0.0, 1.6, (x, y, 0), seg=6)

    # 大理石基座
    b.box_base(red, (11.6, 9.4, 0.25), (0, 0.6, 0))
    b.box_base(marble, (9.0, 9.0, 0.7), (0, 0.6, 0.25))
    z0 = 0.95
    cy = 0.6

    # 主體：八角（切角正方形）
    s, c = 2.5, 0.75
    octo = [(-s + c, -s), (s - c, -s), (s, -s + c), (s, s - c), (s - c, s), (-s + c, s), (-s, s - c), (-s, -s + c)]
    b.prism(marble, octo, z0, 3.0, offset=(0, cy, 0))
    # 四面拱門（巨型凹龕框）
    for k in range(4):
        rot = k * math.pi / 2
        dx, dy = math.cos(rot - math.pi / 2), math.sin(rot - math.pi / 2)
        fx, fy = dx * (s + 0.02), cy + dy * (s + 0.02)
        b.box_base(marble, (1.9 if k % 2 == 0 else 1.9, 0.14, 3.3), (fx, fy, z0), rot=(0, 0, rot))
        b.box_base(marble_shade, (1.3, 0.16, 2.2), (dx * (s + 0.06), cy + dy * (s + 0.06), z0), rot=(0, 0, rot))
        b.tri_prism(marble_shade, 0.16, 1.3, 0.55, (dx * (s + 0.06), cy + dy * (s + 0.06), z0 + 2.2), rot_z=rot + math.pi / 2)
        b.box_base(inlay, (1.5, 0.17, 0.08), (dx * (s + 0.06), cy + dy * (s + 0.06), z0 + 2.95), rot=(0, 0, rot))
        # 斜角面的雙層小拱
        for side in (-1, 1):
            a = rot + side * math.pi / 4
            ddx, ddy = math.cos(a - math.pi / 2), math.sin(a - math.pi / 2)
            dd = (s - c / 2) * math.sqrt(2) * 0.73
            for zz in (0.25, 1.65):
                b.box_base(marble_shade, (0.55, 0.06, 1.05), (ddx * dd, cy + ddy * dd, z0 + zz), rot=(0, 0, a))
    zr = z0 + 3.0
    b.prism(marble_shade, octo, zr, 0.12, offset=(0, cy, 0))
    # 鼓座與洋蔥頂
    b.cyl(marble, 1.35, 1.35, 0.9, (0, cy, zr), seg=24)
    b.cyl(inlay, 1.37, 1.37, 0.08, (0, cy, zr + 0.75), seg=24)
    dome = [(1.35, 0), (1.62, 0.45), (1.72, 1.0), (1.6, 1.6), (1.25, 2.2), (0.75, 2.65), (0.32, 2.95), (0.12, 3.15), (0.0, 3.25)]
    b.lathe(marble, dome, (0, cy, zr + 0.9), seg=28, smooth=True)
    b.lathe(gold, [(0.12, 0), (0.18, 0.12), (0.06, 0.25), (0.12, 0.4), (0.04, 0.55), (0.02, 0.9), (0, 0.95)], (0, cy, zr + 0.9 + 3.15), seg=10)

    def chattri(x, y, z, r):
        for k in range(8):
            a = TAU * k / 8
            b.cyl(marble, 0.05 * r / 0.5, 0.05 * r / 0.5, 0.55 * r / 0.5, (x + r * 0.8 * math.cos(a), y + r * 0.8 * math.sin(a), z), seg=6)
        b.cyl(marble, r * 1.05, r * 1.05, 0.08, (x, y, z + 0.55 * r / 0.5), seg=12)
        b.lathe(marble, [(r * 0.9, 0), (r, r * 0.4), (r * 0.6, r * 0.9), (r * 0.15, r * 1.15), (0, r * 1.3)], (x, y, z + 0.63 * r / 0.5), seg=14)
        b.cyl(gold, 0.03, 0.0, r * 0.6, (x, y, z + 0.63 * r / 0.5 + r * 1.25), seg=6)

    for sx in (-1, 1):
        for sy in (-1, 1):
            chattri(sx * 1.75, cy + sy * 1.75, zr + 0.12, 0.5)
    # 四座宣禮塔
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * 4.1, cy + sy * 4.1
            b.cyl(marble, 0.34, 0.26, 5.6, (x, y, z0), seg=12)
            for zz in (1.9, 3.7, 5.4):
                b.cyl(marble_shade, 0.42, 0.42, 0.1, (x, y, z0 + zz), seg=12)
            chattri(x, y, z0 + 5.6, 0.32)
    # 兩側紅砂岩清真寺與答辯廳
    for sx in (-1, 1):
        x = sx * 8.6
        b.box_base(red, (2.2, 5.6, 1.6), (x, cy, 0))
        b.box_base(marble_shade, (0.1, 1.0, 1.2), (x - sx * 1.12, cy, 0))
        for dy in (-1.6, 0, 1.6):
            r = 0.55 if dy == 0 else 0.42
            b.lathe(marble, [(r, 0), (r * 1.1, r * 0.4), (r * 0.6, r * 1.0), (0, r * 1.4)], (x, cy + dy, 1.6), seg=16)
    b.export(path)


# ---------------------------------------------------------------- 姬路城
def himeji(path):
    b = Builder("Himeji", seed=23)
    grass = b.mat("grass", "#76a650")
    dirt = b.mat("dirt", "#6b5338")
    stone = b.mat("stone", "#8d8b84", rough=0.95)
    stone_dark = b.mat("stone_dark", "#6f6d66", rough=0.95)
    white = b.mat("plaster", "#f5f4ef", rough=0.7)
    roof = b.mat("roof", "#4a5361", rough=0.6)
    window = b.mat("window", "#3a3a3a")
    gold = b.mat("gold", "#cfa43a", rough=0.3, metal=0.9)
    gravel = b.mat("gravel", "#d8d0bd")
    b.plinth(15, grass, dirt)
    b.box_base(gravel, (13, 10, 0.02), (0, 0, 0))

    def stone_base(cx, cy, w, d, h, rot=0.0):
        b.frustum(stone, (w + h * 0.5, d + h * 0.5), (w, d), h, (cx, cy, 0), rot_z=rot)
        for k in range(1, 4):
            z = h * k / 4
            g = h * 0.5 * (1 - k / 4)
            b.frustum(stone_dark, (w + g + 0.02, d + g + 0.02), (w + g - 0.02, d + g - 0.02), 0.03, (cx, cy, z), rot_z=rot)

    def roof_tier(cx, cy, w, d, z, over=0.45, h=0.38, rot=0.0, gable=False):
        b.frustum(roof, (w + over * 2, d + over * 2), (w * 0.7, d * 0.55), h, (cx, cy, z), rot_z=rot)
        # 翹起的屋簷邊
        b.frustum(roof, (w + over * 2 + 0.12, d + over * 2 + 0.12), (w + over * 2, d + over * 2), 0.06, (cx, cy, z - 0.02), rot_z=rot)
        if gable:  # 千鳥破風（三角山牆）
            for side in (-1, 1):
                gx = cx + math.cos(rot + math.pi / 2) * side * (d / 2 + over * 0.4)
                gy = cy + math.sin(rot + math.pi / 2) * side * (d / 2 + over * 0.4)
                b.tri_prism(roof, w * 0.45, 0.5, 0.45, (gx, gy, z + 0.05), rot_z=rot)
                b.tri_prism(white, w * 0.35, 0.36, 0.33, (gx, gy, z + 0.07), rot_z=rot)

    def keep(cx, cy, w, d, z0, tiers, tier_h=0.75, rot=0.0, top_scale=0.72):
        z = z0
        for k in range(tiers):
            t = k / max(1, tiers - 1)
            ww = w * (1 - (1 - top_scale) * t)
            dd = d * (1 - (1 - top_scale) * t)
            b.box_base(white, (ww, dd, tier_h), (cx, cy, z), rot=(0, 0, rot))
            for side in range(4):
                a = rot + side * math.pi / 2
                length = ww if side % 2 == 0 else dd
                dist = (dd if side % 2 == 0 else ww) / 2 + 0.01
                n = max(2, int(length / 0.55))
                for i in range(n):
                    off = -length / 2 + length * (i + 0.5) / n
                    px = cx + math.cos(a - math.pi / 2) * dist + math.cos(a) * off
                    py = cy + math.sin(a - math.pi / 2) * dist + math.sin(a) * off
                    b.box_base(window, (0.2, 0.04, 0.18), (px, py, z + tier_h * 0.45), rot=(0, 0, a))
            z += tier_h
            last = k == tiers - 1
            roof_tier(cx, cy, ww, dd, z, rot=rot, gable=(k % 2 == 1 and not last))
            z += 0.18 if not last else 0
        # 最頂層入母屋造屋頂與鯱
        b.tri_prism(roof, w * top_scale + 0.7, d * top_scale + 0.5, 0.75, (cx, cy, z + 0.3), rot_z=rot)
        for side in (-1, 1):
            gx = cx + math.cos(rot) * side * (w * top_scale / 2 + 0.28)
            gy = cy + math.sin(rot) * side * (w * top_scale / 2 + 0.28)
            b.box_base(gold, (0.12, 0.08, 0.28), (gx, gy, z + 1.0), rot=(0, 0, rot))
        return z

    # 大天守
    stone_base(0.6, 0.6, 5.2, 4.2, 2.4)
    keep(0.6, 0.6, 5.0, 4.0, 2.4, 5, tier_h=0.8)
    # 西、乾、東小天守與渡櫓
    stone_base(-3.6, 2.4, 2.6, 2.2, 2.0)
    keep(-3.6, 2.4, 2.4, 2.0, 2.0, 3, tier_h=0.65)
    stone_base(-3.4, -2.3, 2.4, 2.0, 1.8)
    keep(-3.4, -2.3, 2.2, 1.8, 1.8, 3, tier_h=0.6)
    stone_base(-1.2, -3.6, 4.2, 1.2, 1.6)
    b.box_base(white, (4.0, 1.0, 0.7), (-1.2, -3.6, 1.6))
    roof_tier(-1.2, -3.6, 4.0, 1.0, 2.3, over=0.25, h=0.3)
    # 石牆外圍與松樹
    for k in range(3):
        a = 0.5 + k * 0.4
        b.box_base(stone, (4.5, 0.6, 1.0), (7.5 * math.cos(-a), 7.5 * math.sin(-a) + 1, 0), rot=(0, 0, -a + math.pi / 2))
    for x, y in b.scatter(22, 9.0, 14.4):
        h = b.rng.uniform(1.2, 2.0)
        b.cyl(b.mat("trunk", "#6b4a2b"), 0.1, 0.07, h * 0.6, (x, y, 0), seg=6)
        for k in range(3):
            b.ico(b.mat("pine", "#2f6236"), 0.45 - k * 0.1, (x + b.rng.uniform(-0.2, 0.2), y + b.rng.uniform(-0.2, 0.2), h * 0.5 + k * 0.32), scale=(1.3, 1.3, 0.45))
    b.export(path)


# ---------------------------------------------------------------- 艾菲爾鐵塔
def _lattice(name, rings, material, thickness=0.045):
    """由一連串四邊形截面組成的管狀格架，套用 Wireframe 修改器形成鋼構"""
    bm = bmesh.new()
    vrings = [[bm.verts.new(p) for p in ring] for ring in rings]
    for a, b_ in zip(vrings, vrings[1:]):
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new([a[i], a[j], b_[j], b_[i]])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material)
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    mod = obj.modifiers.new("wire", "WIREFRAME")
    mod.thickness = thickness
    mod.use_even_offset = True
    mod.use_replace = True
    return obj


def _square(cx, cy, z, half):
    return [Vector((cx - half, cy - half, z)), Vector((cx + half, cy - half, z)), Vector((cx + half, cy + half, z)), Vector((cx - half, cy + half, z))]


def eiffel(path):
    b = Builder("Eiffel", seed=29)
    grass = b.mat("grass", "#7db35a")
    dirt = b.mat("dirt", "#6b5338")
    gravel = b.mat("gravel", "#d9ccaa")
    iron = b.mat("iron", "#6e4f36", rough=0.55, metal=0.4)
    stone = b.mat("pier", "#b7ad99")
    water = b.mat("water", "#4b9fd1", rough=0.1)
    b.plinth(15, grass, dirt)
    b.box_base(gravel, (9.5, 9.5, 0.03), (0, 0, 0))
    b.box_base(gravel, (3.2, 9.5, 0.02), (0, -9.4, 0))
    b.box_base(water, (2.2, 3.5, 0.02), (0, -10.5, 0.02))
    for x in (-4.4, 4.4):
        for y in [-6.0 - k * 1.4 for k in range(6)]:
            b.tree_round(x, y, h=1.2, r=0.5)
    for x, y in b.scatter(30, 8.0, 14.4, avoid=lambda x, y: abs(x) < 5.2 and y < -4.5):
        b.tree_round(x, y, h=b.rng.uniform(1.0, 1.5), r=b.rng.uniform(0.45, 0.65))

    iron_obj_mat = b.mats[iron]
    z1, z2, z3 = 2.9, 5.8, 13.6

    def leg_center(z):
        if z <= z1:
            t = z / z1
            return 2.6 - 0.7 * t, 0.62 - 0.17 * t
        t = (z - z1) / (z2 - z1)
        return 1.9 - 0.85 * t, 0.45 - 0.08 * t

    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box_base(stone, (1.6, 1.6, 0.25), (sx * 2.6, sy * 2.6, 0))
            rings = []
            for k in range(15):
                z = 0.25 + (z2 - 0.25) * k / 14
                c, half = leg_center(z)
                rings.append(_square(sx * c, sy * c, z, half))
            _lattice(f"leg_{sx}_{sy}", rings, iron_obj_mat, 0.085)
            # 斜柱內側實心主樑，讓輪廓更明確
            for k in range(14):
                za, zb = rings[k][0].z, rings[k + 1][0].z
                ca, _ = leg_center(za)
                cb, _ = leg_center(zb)
                mx, my, mz = sx * (ca + cb) / 2, sy * (ca + cb) / 2, (za + zb) / 2
                dz, dc = zb - za, cb - ca
                tilt = math.atan2(-dc, dz)
                b.box(iron, (0.16, 0.16, math.hypot(dz, dc * math.sqrt(2)) + 0.04), (mx, my, mz), rot=(sy * tilt * 0.707, -sx * tilt * 0.707, 0))

    # 主塔身（第二平台至頂層）
    rings = []
    for k in range(19):
        z = z2 + 0.3 + (z3 - z2 - 0.3) * k / 18
        u = (z3 - z) / (z3 - z2)
        half = 0.32 + 1.05 * u**1.7
        rings.append(_square(0, 0, z, half))
    _lattice("shaft", rings, iron_obj_mat, 0.07)
    # 塔身四角主樑
    for k in range(18):
        za, zb = rings[k][0].z, rings[k + 1][0].z
        ha = rings[k][1].x
        hb = rings[k + 1][1].x
        for sx in (-1, 1):
            for sy in (-1, 1):
                b.box(iron, (0.13, 0.13, zb - za + 0.03), (sx * (ha + hb) / 2, sy * (ha + hb) / 2, (za + zb) / 2))
    _lattice("top", [_square(0, 0, z3 + 0.3, 0.3), _square(0, 0, z3 + 0.8, 0.24), _square(0, 0, z3 + 1.3, 0.17)], iron_obj_mat, 0.05)

    # 第一層拱門
    for k in range(4):
        rot = k * math.pi / 2
        nx, ny = math.cos(rot), math.sin(rot)
        tx, ty = -ny, nx
        R = 1.85
        for i in range(14):
            a = math.pi * (i + 0.5) / 14
            px = nx * 2.25 + tx * R * math.cos(a)
            py = ny * 2.25 + ty * R * math.cos(a)
            pz = 1.05 + R * math.sin(a) * 0.95
            b.box(iron, (0.12, 0.42, 0.12), (px, py, pz), rot=(0, 0, rot))
    # 平台
    b.box_base(iron, (5.2, 5.2, 0.35), (0, 0, z1))
    b.box_base(iron, (5.4, 5.4, 0.08), (0, 0, z1 + 0.35))
    b.box_base(gravel, (3.4, 3.4, 0.25), (0, 0, z1 + 0.43))
    b.box_base(iron, (2.9, 2.9, 0.3), (0, 0, z2))
    b.box_base(iron, (3.05, 3.05, 0.06), (0, 0, z2 + 0.3))
    b.box_base(iron, (1.0, 1.0, 0.3), (0, 0, z3))
    b.box_base(gravel, (0.7, 0.7, 0.45), (0, 0, z3 + 0.3))
    b.cyl(iron, 0.12, 0.08, 0.6, (0, 0, z3 + 1.3), seg=8)
    b.cyl(stone, 0.04, 0.03, 1.2, (0, 0, z3 + 1.9), seg=6)
    b.export(path)
