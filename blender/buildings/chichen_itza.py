"""chichen_itza 寫實模型（尺寸依實測資料，公尺）"""

import math

from mathutils import Matrix, Vector, noise

from lib import TAU, Builder


# ====================================================================== 奇琴伊察・庫庫爾坎金字塔
def chichen_itza(path):
    b = Builder("ChichenItza", seed=5)
    grass = b.tex("grass", "grass_ground", tile=5.0, tint="#6d8f42")
    soil = b.color("soil", "#6b5536", rough=0.95)
    stone = b.tex("limestone", "white_sandstone_bricks_03", tile=2.4, tint="#c3bba6")
    stone_dark = b.tex("limestone_dark", "white_sandstone_bricks_03", tile=2.4, tint="#8f8878")
    smooth = b.tex("stair", "sandstone_blocks_05", tile=2.0, tint="#bfb6a0")
    path_m = b.tex("plaza", "gravel_floor", tile=3.0, tint="#c9bb98")

    b.ground_disc(grass, 75, soil, depth=4, rings=24, seg=112)
    b.box_base(path_m, (64, 64, 0.04), (0, 0, -0.02))
    base, top = 55.3, 19.6
    levels = 9
    hz = 24.0
    lh = hz / levels
    for k in range(levels):
        w0 = base - (base - top) * k / levels
        w1 = base - (base - top) * (k + 1) / levels + 1.6
        # 斜坡牆（talud）
        b.frustum(stone, (w0, w0), (w1, w1), lh * 0.78, (0, 0, k * lh))
        # 上方直立凹板（tablero）
        b.box_base(stone_dark, (w1 - 0.05, w1 - 0.05, lh * 0.22), (0, 0, k * lh + lh * 0.78))
        b.box_base(stone, (w1 + 0.25, w1 + 0.25, lh * 0.06), (0, 0, k * lh + lh * 0.94))
        # 立面上的矩形凹板
        n = max(3, int(w1 / 6))
        for side in range(4):
            a = side * math.pi / 2
            c, s = math.cos(a), math.sin(a)
            for i in range(n):
                off = -w1 / 2 + w1 * (i + 0.5) / n
                if abs(off) < 6.5:
                    continue
                d = w1 / 2 + 0.06
                b.box_base(stone, (0.15, w1 / n * 0.7, lh * 0.15), (c * d - s * off, s * d + c * off, k * lh + lh * 0.81), rot=(0, 0, a))

    zt = hz
    run = (base - top) / 2 + 0.8
    steps = 91
    for side in range(4):
        a = side * math.pi / 2
        c, s = math.cos(a), math.sin(a)
        for i in range(steps):
            t = i / steps
            d = base / 2 + 0.8 - run * t
            b.box_base(smooth, (run / steps + 0.25, 8.9, zt / steps + 0.02), (c * (d - run / steps / 2), s * (d - run / steps / 2), zt * t), rot=(0, 0, a))
        # 扶手（沿斜面的厚板）
        ang = math.atan2(zt, run)
        length = math.hypot(run, zt)
        for off in (-5.0, 5.0):
            mx = c * (base / 2 + 0.8 - run / 2) - s * off
            my = s * (base / 2 + 0.8 - run / 2) + c * off
            M = Matrix.Translation((mx, my, zt / 2)) @ Matrix.Rotation(a, 4, "Z") @ Matrix.Rotation(-ang, 4, "Y")
            vs = b.box(stone_dark, (length, 1.2, 0.9), (0, 0, 0))
            for v in vs:
                v.co = M @ v.co
            if side == 0:  # 北面羽蛇頭像
                hx = c * (base / 2 + 2.0) - s * off
                hy = s * (base / 2 + 2.0) + c * off
                b.rock(stone_dark, (2.2, 1.6, 1.6), (hx, hy, 0.8), rot=(0, 0, a), rough=0.12, seed=int(off))
    # 頂部神廟（約 13 × 13 m、高 6 m）
    b.box_base(stone, (top - 1.0, top - 1.0, 0.4), (0, 0, zt))
    tw = 13.0
    zt2 = zt + 0.4
    b.box_base(stone, (tw, tw, 3.4), (0, 0, zt2))
    b.box_base(stone_dark, (tw + 0.4, tw + 0.4, 0.5), (0, 0, zt2 + 3.4))
    b.box_base(stone, (tw + 0.2, tw + 0.2, 1.4), (0, 0, zt2 + 3.9))
    b.box_base(stone_dark, (tw + 0.5, tw + 0.5, 0.4), (0, 0, zt2 + 5.3))
    # 門洞（北面三門、其餘一門）
    dark = b.color("doorway", "#2a2620", rough=1.0)
    for side in range(4):
        a = side * math.pi / 2
        c, s = math.cos(a), math.sin(a)
        offs = (-3.4, 0, 3.4) if side == 1 else (0,)
        for off in offs:
            b.box_base(dark, (0.3, 2.0, 2.6), (c * tw / 2 - s * off, s * tw / 2 + c * off, zt2), rot=(0, 0, a))
    # 周圍樹林
    for x, y in b.scatter(70, 52, 73, min_dist=4.5):
        b.tree(x, y, 0, h=b.rng.uniform(7, 12))
    b.export(path)
