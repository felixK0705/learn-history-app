"""上古與古典建築：巨石陣、吉薩金字塔群、帕德嫩神廟、奇琴伊察、吳哥窟"""

import math

from lib import Builder

TAU = 2 * math.pi


def stonehenge(path):
    b = Builder("Stonehenge", seed=7)
    grass = b.mat("grass", "#7fae5a")
    dirt = b.mat("dirt", "#6b5338")
    sarsen = b.mat("sarsen", "#9c968a", rough=0.95)
    sarsen_dark = b.mat("sarsen_dark", "#827c71", rough=0.95)
    blue = b.mat("bluestone", "#6f7680", rough=0.9)
    path_m = b.mat("path", "#cdbf9c")
    b.plinth(13, grass, dirt)
    pa = math.radians(40)
    b.box_base(path_m, (3.6, 1.2, 0.02), (11.0 * math.cos(pa), 11.0 * math.sin(pa), 0), rot=(0, 0, pa))

    r = b.rng
    # 外圈 30 根砂岩立石與楣石
    R = 8.0
    n = 30
    missing = {6, 7, 8, 18, 19, 23, 24}
    for i in range(n):
        if i in missing:
            continue
        a = TAU * i / n
        x, y = R * math.cos(a), R * math.sin(a)
        m = sarsen if r.random() > 0.3 else sarsen_dark
        tilt = r.uniform(-0.04, 0.04)
        b.box_base(m, (0.65, 1.15, 3.6 + r.uniform(-0.15, 0.1)), (x, y, 0), rot=(tilt, tilt, a))
    for i in range(n):
        j = (i + 1) % n
        if i in missing or j in missing or i in (2, 13, 27):
            continue
        a = TAU * (i + 0.5) / n
        x, y = R * math.cos(a), R * math.sin(a)
        b.box_base(sarsen, (0.75, 2 * R * math.sin(math.pi / n) - 0.04, 0.55 + (i % 2) * 0.03), (x, y, 3.62), rot=(0, 0, a))
    # 倒下的立石
    b.box_base(sarsen_dark, (3.6, 1.15, 0.65), (R * math.cos(TAU * 7 / n) * 1.12, R * math.sin(TAU * 7 / n) * 1.12, 0), rot=(0, 0, 1.2))

    # 青石圈
    for i in range(36):
        if r.random() < 0.3:
            continue
        a = TAU * i / 36 + 0.04
        b.box_base(blue, (0.35, 0.45, 1.6 + r.uniform(-0.3, 0.3)), (6.3 * math.cos(a), 6.3 * math.sin(a), 0), rot=(r.uniform(-0.08, 0.08), 0, a))

    # 中央馬蹄形巨石牌坊（開口朝東北）
    open_dir = math.radians(40)
    heights = [4.3, 4.9, 5.6, 4.9, 4.3]
    for k, ang in enumerate([-120, -60, 0, 60, 120]):
        a = open_dir + math.pi + math.radians(ang)
        cx, cy = 4.0 * math.cos(a), 4.0 * math.sin(a)
        tx, ty = -math.sin(a), math.cos(a)
        h = heights[k]
        if k == 3:  # 一座牌坊已倒塌
            b.box_base(sarsen_dark, (h, 1.3, 0.8), (cx + tx * 0.6, cy + ty * 0.6, 0), rot=(0, 0, a + 0.3))
            b.box_base(sarsen, (1.0, 1.2, h), (cx - tx * 0.9, cy - ty * 0.9, 0), rot=(0, 0, a))
            continue
        for s in (-0.9, 0.9):
            b.box_base(sarsen, (1.0, 1.2, h), (cx + tx * s, cy + ty * s, 0), rot=(0, 0, a))
        b.box_base(sarsen_dark, (0.9, 3.2, 0.75), (cx, cy, h), rot=(0, 0, a))

    # 祭壇石與踵石
    b.box_base(sarsen_dark, (2.6, 0.9, 0.35), (0.3, -0.2, 0), rot=(0, 0, 0.5))
    b.box_base(sarsen, (1.2, 1.0, 3.0), (11.0 * math.cos(open_dir), 11.0 * math.sin(open_dir), 0), rot=(0.15, 0.1, 0.4))
    b.export(path)


def giza(path):
    b = Builder("Giza", seed=3)
    sand = b.mat("sand", "#efd9a8")
    sand_side = b.mat("sand_side", "#b8945e")
    stone = b.mat("pyramid", "#c9965a", rough=0.95)
    stone_shade = b.mat("pyramid_shade", "#a87a45", rough=0.95)
    casing = b.mat("casing", "#efe3c4", rough=0.6)
    sphinx_m = b.mat("sphinx", "#bf8f55", rough=0.95)
    b.plinth(15, sand, sand_side)

    stone_lit = b.mat("pyramid_lit", "#ddb27a", rough=0.95)

    def pyramid(cx, cy, base, h, cap=0.0):
        rr = base / math.sqrt(2)
        vs = b.cone(stone, rr, h, (cx, cy, 0), seg=4, rot=(0, 0, math.pi / 4))
        # 風格化受光面：朝 +X 與 +Y 的兩面較亮
        for f in {f for v in vs for f in v.link_faces}:
            f.normal_update()
            if f.normal.z > -0.5 and (f.normal.y > 0.3 or f.normal.x > 0.3):
                f.material_index = stone_lit
        # 階層紋理：數圈略微內縮的薄帶
        for k in range(1, 6):
            z = h * k / 7
            w = base * (1 - k / 7) * 1.004
            b.box_base(stone_shade, (w, w, 0.04), (cx, cy, z))
        if cap:
            ch = h * cap
            b.cyl(casing, rr * cap * 1.01, 0, ch * 1.005, (cx, cy, h - ch), seg=4, rot=(0, 0, math.pi / 4))

    pyramid(-3.5, 3.0, 9.0, 5.7)  # 古夫
    pyramid(3.0, -1.0, 8.2, 5.4, cap=0.16)  # 卡夫拉
    pyramid(7.0, -6.8, 4.2, 2.7)  # 孟卡拉
    for k in range(3):
        pyramid(4.6 + k * 1.5, -9.8, 1.1, 0.75)
    for k in range(3):
        pyramid(-8.6, 6.8 - k * 1.6, 1.2, 0.8)

    # 獅身人面像（面向東）
    sx, sy = -2.0, -8.0
    b.box_base(sphinx_m, (3.0, 1.0, 0.75), (sx, sy, 0))
    b.box_base(sphinx_m, (1.2, 0.3, 0.25), (sx + 1.9, sy + 0.3, 0))
    b.box_base(sphinx_m, (1.2, 0.3, 0.25), (sx + 1.9, sy - 0.3, 0))
    b.box_base(sphinx_m, (0.7, 0.85, 0.7), (sx + 1.1, sy, 0.6))
    b.frustum(sphinx_m, (0.75, 1.15), (0.45, 0.5), 0.75, (sx + 1.05, sy, 0.75))
    b.box_base(sphinx_m, (0.4, 0.45, 0.5), (sx + 1.35, sy, 0.95))
    # 圍坑
    b.ering(sand_side, (2.3, 1.2), (2.6, 1.5), 0.0, 0.18, seg=24, center=(sx + 0.4, sy))
    # 參道
    b.box_base(casing, (0.6, 7.0, 0.08), (0.2, -5.5, 0), rot=(0, 0, 0.35))

    for x, y in [(-11.5, -4), (-12, -2.5), (-10.6, -6.2), (11, 4), (12, 2.2), (10.2, 6.5), (-6, -11.5)]:
        b.palm(x, y, h=b.rng.uniform(1.6, 2.3))
    b.export(path)


def parthenon(path):
    b = Builder("Parthenon", seed=11)
    rock = b.mat("rock", "#b9a585", rough=0.95)
    rock_side = b.mat("rock_side", "#8f7c62", rough=0.95)
    grass = b.mat("grass", "#9cae6a")
    marble = b.mat("marble", "#ece2cb", rough=0.55)
    marble_dark = b.mat("marble_dark", "#cfc2a5", rough=0.6)
    shadow = b.mat("shadow", "#a69676", rough=0.7)
    b.plinth(14, rock, rock_side, depth=2.0)
    for x, y in b.scatter(14, 10.5, 13.3):
        b.ico(grass, b.rng.uniform(0.4, 0.8), (x, y, 0.0), scale=(1, 1, 0.35))

    L, W = 15.4, 6.9  # 柱座頂面
    # 三層台階
    for k in range(3):
        g = (2 - k) * 0.35
        b.box_base(marble_dark if k < 2 else marble, (L + g * 2, W + g * 2, 0.24), (0, 0, k * 0.24))
    z0 = 0.72
    col_h = 2.35
    cols = []
    nx, ny = 17, 8
    for i in range(nx):
        x = -L / 2 + 0.45 + (L - 0.9) * i / (nx - 1)
        cols += [(x, -W / 2 + 0.45), (x, W / 2 - 0.45)]
    for j in range(1, ny - 1):
        y = -W / 2 + 0.45 + (W - 0.9) * j / (ny - 1)
        cols += [(-L / 2 + 0.45, y), (L / 2 - 0.45, y)]
    broken = {5, 9, 22}
    for idx, (x, y) in enumerate(cols):
        h = col_h if idx not in broken else col_h * 0.45
        prof = [(0.22, 0), (0.225, h * 0.35), (0.205, h * 0.8), (0.18, h)]
        b.lathe(marble, prof, (x, y, z0), seg=14, smooth=False)
        if idx in broken:
            continue
        b.lathe(marble, [(0.18, 0), (0.27, 0.12), (0.28, 0.15)], (x, y, z0 + h), seg=14, smooth=True)
        b.box_base(marble, (0.6, 0.6, 0.08), (x, y, z0 + h + 0.14))

    ze = z0 + col_h + 0.22
    # 東西兩端完整、南北側中段柱楣斷裂（呼應 1687 年爆炸）
    def entab(x0, x1, y0, y1):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        sx, sy = abs(x1 - x0), abs(y1 - y0)
        b.box_base(marble, (sx, sy, 0.38), (cx, cy, ze))
        b.box_base(marble_dark, (sx, sy, 0.36), (cx, cy, ze + 0.38))
        b.box_base(marble, (sx + 0.12, sy + 0.12, 0.12), (cx, cy, ze + 0.74))

    ew = 0.68
    entab(-L / 2 + 0.1, -L / 2 + 0.1 + ew, -W / 2 + 0.1, W / 2 - 0.1)
    entab(L / 2 - 0.1 - ew, L / 2 - 0.1, -W / 2 + 0.1, W / 2 - 0.1)
    for side in (-1, 1):
        y1 = side * (W / 2 - 0.1)
        y0 = y1 - side * ew
        entab(-L / 2 + 0.1 + ew, -2.2, min(y0, y1), max(y0, y1))
        entab(2.6, L / 2 - 0.1 - ew, min(y0, y1), max(y0, y1))
    # 三角楣
    for sx in (-1, 1):
        x = sx * (L / 2 - 0.1 - ew / 2)
        b.tri_prism(marble, ew, W + 0.02, 1.0, (x, 0, ze + 0.86), rot_z=0)
        b.tri_prism(shadow, ew * 0.4, W - 0.7, 0.75, (x + sx * 0.2, 0, ze + 0.92), rot_z=0)
    # 內殿殘牆
    b.box_base(marble_dark, (9.6, 0.32, 1.4), (0.2, 1.75, z0))
    b.box_base(marble_dark, (6.0, 0.32, 0.8), (-1.6, -1.75, z0))
    b.box_base(marble_dark, (0.32, 3.8, 1.9), (-4.6, 0, z0))
    for k in range(6):
        b.box_base(marble_dark, (0.5 + b.rng.random() * 0.4, 0.4, 0.3), (b.rng.uniform(-9, 9), b.rng.uniform(-5.2, -4.4), 0), rot=(0, 0, b.rng.random()))
    b.export(path)


def chichen_itza(path):
    b = Builder("ChichenItza", seed=5)
    grass = b.mat("grass", "#6fa04a")
    dirt = b.mat("dirt", "#6a5236")
    lime = b.mat("limestone", "#d2c6a8", rough=0.9)
    lime_dark = b.mat("limestone_dark", "#aa9f84", rough=0.95)
    shade = b.mat("shade", "#5b5446", rough=0.95)
    b.plinth(14, grass, dirt)
    b.box_base(b.mat("plaza", "#c9bb92"), (13.5, 13.5, 0.02), (0, 0, 0))

    levels = 9
    base, top = 10.8, 4.6
    lh = 0.42
    for k in range(levels):
        w0 = base - (base - top) * k / levels
        w1 = w0 - 0.35
        b.frustum(lime if k % 2 == 0 else lime_dark, (w0, w0), (w1, w1), lh, (0, 0, k * lh))
        b.box_base(shade, (w1 + 0.02, w1 + 0.02, 0.05), (0, 0, k * lh + lh * 0.55))
    zt = levels * lh
    # 四面階梯與扶手
    steps = 24
    for side in range(4):
        rot = side * math.pi / 2
        c, s = math.cos(rot), math.sin(rot)
        for i in range(steps):
            t = i / steps
            dist = base / 2 + 0.6 - (base / 2 + 0.6 - top / 2) * t
            z = zt * t
            x, y = c * dist, s * dist
            b.box_base(lime, (0.42, 2.0, zt / steps + 0.02), (x, y, z), rot=(0, 0, rot))
        for off in (-1.15, 1.15):
            ox, oy = -s * off, c * off
            dx = (base / 2 + 0.6 - top / 2)
            # 以多段方塊組成斜扶手（避免複雜旋轉矩陣）
            for k in range(steps):
                t = (k + 0.5) / steps
                d = base / 2 + 0.6 - dx * t
                b.box_base(lime_dark, (dx / steps + 0.04, 0.3, zt / steps * 1.2), (c * d + ox, s * d + oy, zt * t), rot=(0, 0, rot))
            if side == 0:  # 北面羽蛇頭
                d = base / 2 + 0.75
                b.box_base(lime_dark, (0.6, 0.45, 0.4), (c * d + ox, s * d + oy, 0), rot=(0, 0, rot))
    # 頂部神廟
    b.box_base(lime, (3.6, 3.6, 0.15), (0, 0, zt))
    b.box_base(lime, (3.2, 3.2, 1.0), (0, 0, zt + 0.15))
    b.box_base(lime_dark, (3.4, 3.4, 0.25), (0, 0, zt + 1.15))
    b.box_base(lime, (3.0, 3.0, 0.2), (0, 0, zt + 1.4))
    for side in range(4):
        rot = side * math.pi / 2
        c, s = math.cos(rot), math.sin(rot)
        b.box_base(shade, (0.06, 0.9 if side else 1.6, 0.7), (c * 1.6, s * 1.6, zt + 0.15), rot=(0, 0, rot))

    for x, y in b.scatter(26, 9.0, 13.4):
        b.tree_round(x, y, h=b.rng.uniform(1.0, 1.8), r=b.rng.uniform(0.5, 0.85))
    b.export(path)


def angkor_wat(path):
    b = Builder("AngkorWat", seed=9)
    grass = b.mat("grass", "#7aa452")
    dirt = b.mat("dirt", "#6b5338")
    water = b.mat("water", "#3f8fc4", rough=0.15)
    stone = b.mat("sandstone", "#9b947f", rough=0.95)
    stone_dark = b.mat("sandstone_dark", "#757060", rough=0.95)
    roof = b.mat("roof", "#5f5b4f", rough=0.95)
    b.plinth(15, grass, dirt)
    # 護城河（正方形水道）
    M = 9.6
    for sx, sy, w, d in [(0, M, 2 * M + 1.6, 1.6), (0, -M, 2 * M + 1.6, 1.6), (M, 0, 1.6, 2 * M - 1.6), (-M, 0, 1.6, 2 * M - 1.6)]:
        b.box_base(water, (w, d, 0.02), (sx, sy, -0.005))
    # 西向參道與入口塔門
    b.box_base(stone_dark, (5.6, 1.0, 0.18), (-9.2, 0, 0))
    b.box_base(stone, (1.0, 3.6, 0.9), (-8.0, 0, 0))
    b.cone(stone, 0.5, 1.0, (-8.0, 0, 0.9), seg=8)

    def tower(x, y, z, h, r):
        tiers = 7
        prof = [(r, 0)]
        zz = 0
        rr = r
        for k in range(tiers):
            th = h * 0.8 / tiers
            prof += [(rr * 1.06, zz + th * 0.15), (rr * 0.96, zz + th * 0.8), (rr * 0.82, zz + th)]
            zz += th
            rr *= 0.82
        prof += [(rr * 0.6, zz + h * 0.12), (0, zz + h * 0.2)]
        b.lathe(stone, prof, (x, y, z), seg=8, smooth=False, rot_offset=math.pi / 8)

    levels = [((12.0, 10.6), 0.7), ((8.6, 7.8), 1.0), ((5.8, 5.8), 1.5)]
    z = 0.0
    for (w, d), h in levels:
        b.box_base(stone, (w, d, h), (0, 0, z))
        b.box_base(stone_dark, (w + 0.15, d + 0.15, 0.12), (0, 0, z + h * 0.45))
        # 迴廊屋頂
        b.frustum(roof, (w + 0.1, d + 0.1), (w - 0.6, d - 0.6), 0.3, (0, 0, z + h))
        # 角樓
        for sx in (-1, 1):
            for sy in (-1, 1):
                if h < 1.4:
                    tower(sx * (w / 2 - 0.3), sy * (d / 2 - 0.3), z + h, 1.3 * h, 0.35)
        # 西側階梯
        b.box_base(stone_dark, (1.0, 1.2, h + 0.05), (-w / 2 - 0.4, 0, z))
        z += h + 0.3
    ztop = z - 0.3
    # 五座蓮花寶塔
    for sx in (-1, 1):
        for sy in (-1, 1):
            tower(sx * 2.35, sy * 2.35, ztop, 2.6, 0.62)
    tower(0, 0, ztop, 3.8, 0.85)

    for x, y in b.scatter(22, 11.4, 14.5, avoid=lambda x, y: abs(y) < 1.4 and x < 0):
        b.palm(x, y, h=b.rng.uniform(1.5, 2.2))
    b.export(path)
