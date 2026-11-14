"""great_wall 寫實模型（尺寸依實測資料，公尺）"""

import math

from mathutils import Matrix, Vector, noise

from lib import TAU, Builder


# ====================================================================== 萬里長城（金山嶺段）
def great_wall(path):
    b = Builder("GreatWall", seed=21)
    terrain = b.tex("terrain", "aerial_grass_rock", tile=40.0, tint="#61773d")
    soil = b.color("soil", "#5b4a36", rough=0.95)
    wall = b.tex("wall", "white_sandstone_bricks_03", tile=1.8, tint="#9a9284", normal=1.2)
    wall_top = b.tex("walkway", "gravel_floor", tile=2.0, tint="#8a8478")
    dark = b.color("opening", "#1f1d1a", rough=1.0)
    shrub = b.color("shrub", "#3f6328", rough=0.9)
    shrub2 = b.color("shrub2", "#557a32", rough=0.9)
    R = 420.0

    # 長城沿著山脊；山脊高度隨路徑起伏
    def path_pt(u):  # u ∈ [0, 1]
        x = -360 + 720 * u
        y = 60 * math.sin(u * 5.2) + 25 * math.sin(u * 13)
        return x, y

    def ridge_h(u):
        return 70 + 45 * math.sin(u * 7.0 + 0.4) + 18 * math.sin(u * 19)

    samples = [path_pt(i / 400) for i in range(401)]

    def height(x, y):
        # 與長城路徑的距離 → 山脊剖面
        best, bu = 1e9, 0
        for i in range(0, 401, 4):
            px, py = samples[i]
            d = (x - px) ** 2 + (y - py) ** 2
            if d < best:
                best, bu = d, i / 400
        d = math.sqrt(best)
        h = ridge_h(bu) * math.exp(-((d / 95) ** 2))
        h += 30 * noise.noise(Vector((x * 0.006, y * 0.006, 2))) + 12 * noise.noise(Vector((x * 0.02, y * 0.02, 5)))
        back = 60 * max(0.0, (y - 120) / 250)  # 後方較高的山
        fall = max(0.0, 1 - (math.hypot(x, y) / R) ** 6)
        return max(0.0, h + back) * fall

    b.ground_disc(terrain, R, soil, depth=20, height_fn=height, rings=70, seg=160)

    # 牆體：每 3 m 一段，隨山勢呈階梯；外側（南）有雉堞
    pts = [path_pt(i / 240) for i in range(241)]
    pts = [p for p in pts if math.hypot(*p) < R - 15]
    H, Wd = 7.0, 5.0
    tower_idx = set(range(6, len(pts), 22))
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        ang = math.atan2(y1 - y0, x1 - x0)
        L = math.hypot(x1 - x0, y1 - y0) + 0.3
        g0 = min(height(x0, y0), height(x1, y1))
        top = height(mx, my) + H
        nx, ny = -math.sin(ang), math.cos(ang)
        b.box_base(wall, (L, Wd, top - g0 + 3), (mx, my, g0 - 3), rot=(0, 0, ang))
        b.box_base(wall_top, (L, Wd - 1.2, 0.12), (mx, my, top), rot=(0, 0, ang))
        # 外側雉堞（垛口牆）
        for s in range(3):
            off = -L / 2 + L * (s + 0.5) / 3
            px = mx + math.cos(ang) * off - nx * (Wd / 2 - 0.3)
            py = my + math.sin(ang) * off - ny * (Wd / 2 - 0.3)
            b.box_base(wall, (L / 3 * 0.62, 0.6, 1.9), (px, py, top), rot=(0, 0, ang))
            b.box_base(dark, (0.25, 0.65, 0.3), (px, py, top + 0.9), rot=(0, 0, ang))
        b.box_base(wall, (L, 0.5, 1.0), (mx + nx * (Wd / 2 - 0.25), my + ny * (Wd / 2 - 0.25), top), rot=(0, 0, ang))
        if i in tower_idx:
            tz = height(mx, my)
            th = H + 6.0
            b.box_base(wall, (11, 11, th + 4), (mx, my, tz - 4), rot=(0, 0, ang))
            b.box_base(wall_top, (11.6, 11.6, 0.5), (mx, my, tz + th), rot=(0, 0, ang))
            # 箭窗（圓拱）
            for side in range(4):
                a2 = ang + side * math.pi / 2
                for k in (-3, 0, 3):
                    cx = mx + math.cos(a2 - math.pi / 2) * 5.55 + math.cos(a2) * k
                    cy = my + math.sin(a2 - math.pi / 2) * 5.55 + math.sin(a2) * k
                    M = Matrix.Translation((cx, cy, tz + H - 0.4)) @ Matrix.Rotation(a2, 4, "Z")
                    pts_arch = [(-0.6, 0), (0.6, 0)] + list(reversed(b.arch_points(1.2, 1.6, "round", 8)))[1:-1]
                    b.profile_wall(dark, [(-0.6, 0), (0.6, 0), (0.6, 1.6)] + pts_arch[2:] + [(-0.6, 1.6)], 0.2, M)
            # 頂部雉堞
            for side in range(4):
                a2 = ang + side * math.pi / 2
                for k in range(6):
                    off = -4.6 + k * 1.84
                    cx = mx + math.cos(a2 - math.pi / 2) * 5.5 + math.cos(a2) * off
                    cy = my + math.sin(a2 - math.pi / 2) * 5.5 + math.sin(a2) * off
                    b.box_base(wall, (1.1, 0.6, 1.6), (cx, cy, tz + th + 0.5), rot=(0, 0, a2))
            # 部分敵樓頂部有小屋（金山嶺特色）
            if i % 44 == 6:
                b.box_base(wall, (5, 5, 3), (mx, my, tz + th + 0.5), rot=(0, 0, ang))
                b.hip_roof(b.tex("roof_tile", "grey_roof_tiles", tile=1.5, tint="#55555a"), 5, 5, 2.4, (mx, my, tz + th + 3.5), overhang=0.8, upturn=0.25, rot_z=ang)

    # 植被：大量灌木叢與林木
    def near_wall(x, y):
        return any((x - px) ** 2 + (y - py) ** 2 < 120 for px, py in pts[::2])

    for x, y in b.scatter(900, 5, R - 8, avoid=near_wall, min_dist=6):
        z = height(x, y)
        s = b.rng.uniform(3, 7)
        b.rock(shrub if b.rng.random() < 0.6 else shrub2, (s, s, s * 0.7), (x, y, z + s * 0.25), rough=0.35, subdiv=1, seed=b.rng.randint(0, 9999), flat_bottom=False)
    b.export(path)
