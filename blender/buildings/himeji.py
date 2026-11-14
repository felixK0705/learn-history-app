"""himeji 寫實模型（尺寸依實測資料，公尺）"""

import math

from mathutils import Matrix, Vector, noise

from lib import TAU, Builder


# ====================================================================== 姬路城
def himeji(path):
    b = Builder("Himeji", seed=23)
    grass = b.tex("grass", "grass_ground", tile=4.0, tint="#5a8034")
    soil = b.color("soil", "#5d4a35", rough=0.95)
    gravel = b.tex("gravel", "gravel_floor", tile=2.5, tint="#c9c0ac")
    stone = b.tex("ishigaki", "large_sandstone_blocks", tile=3.0, tint="#8e897f", normal=1.4)
    plaster = b.tex("plaster", "plastered_wall_04", tile=3.0, tint="#f2f1ec", normal=0.6)
    roof = b.tex("roof", "grey_roof_tiles", tile=1.6, tint="#5f6266", normal=1.2)
    dark = b.color("window", "#2c2b29", rough=0.9)
    gable_dark = b.color("gable_trim", "#4b4d50", rough=0.6)
    gold = b.color("shachihoko", "#c79d3a", rough=0.3, metal=0.9)

    def hill(x, y):
        return 9.0 * math.exp(-((x * x + y * y) / (95.0**2)))

    b.ground_disc(grass, 170, soil, depth=6, height_fn=hill, rings=30, seg=112)

    def ishigaki(cx, cy, w, d, h, z):
        """弧形向內收的石垣：分層堆疊形成「扇之勾配」"""
        layers = 8
        for k in range(layers):
            f0, f1 = k / layers, (k + 1) / layers
            batter = lambda f: h * 0.32 * (1 - f) ** 1.8
            b.frustum(stone, (w + 2 * batter(f0), d + 2 * batter(f0)), (w + 2 * batter(f1), d + 2 * batter(f1)), h / layers, (cx, cy, z + h * f0))

    def floor(cx, cy, w, d, z, h, rot=0.0):
        b.box_base(plaster, (w, d, h), (cx, cy, z), rot=(0, 0, rot))
        for side in range(4):
            a = rot + side * math.pi / 2
            length = w if side % 2 == 0 else d
            dist = (d if side % 2 == 0 else w) / 2 + 0.05
            nwin = max(1, int(length / 4.5))
            for i in range(nwin):
                off = -length / 2 + length * (i + 0.5) / nwin
                px = cx + math.cos(a - math.pi / 2) * dist + math.cos(a) * off
                py = cy + math.sin(a - math.pi / 2) * dist + math.sin(a) * off
                b.box_base(dark, (1.6, 0.15, 1.2), (px, py, z + h * 0.42), rot=(0, 0, a))
                for g in range(4):  # 格子
                    b.box_base(plaster, (0.08, 0.2, 1.2), (px + math.cos(a) * (-0.6 + g * 0.4), py + math.sin(a) * (-0.6 + g * 0.4), z + h * 0.42), rot=(0, 0, a))

    def chidori(cx, cy, z, w, rot, depth_out):
        """千鳥破風：屋面上突出的三角山牆"""
        px = cx + math.cos(rot - math.pi / 2) * depth_out
        py = cy + math.sin(rot - math.pi / 2) * depth_out
        M = Matrix.Translation((px, py, z)) @ Matrix.Rotation(rot, 4, "Z")
        b.profile_wall(plaster, [(-w / 2, 0), (w / 2, 0), (0, w * 0.42)], 2.4, M)
        b.profile_wall(gable_dark, [(-w / 2 - 0.4, -0.1), (w / 2 + 0.4, -0.1), (0, w * 0.42 + 0.35)], 2.0, M @ Matrix.Translation((0, 0.5, 0)))
        b.tri_prism(roof, 3.6, w + 1.2, w * 0.44 + 0.3, (px + math.cos(rot + math.pi / 2) * 1.6, py + math.sin(rot + math.pi / 2) * 1.6, z), rot_z=rot + math.pi / 2)

    def keep(cx, cy, z, w, d, floors, fh=3.6, shrink=0.86, rot=0.0, gables=True):
        ww, dd = w, d
        for k in range(floors):
            floor(cx, cy, ww, dd, z, fh, rot)
            z += fh
            last = k == floors - 1
            if not last:
                b.hip_roof(roof, ww, dd, 2.2, (cx, cy, z - 0.2), overhang=2.0, upturn=0.55, rot_z=rot)
                if gables and k % 2 == 1:
                    chidori(cx, cy, z - 0.1, ww * 0.42, rot, dd / 2 + 1.0)
                    chidori(cx, cy, z - 0.1, ww * 0.42, rot + math.pi, dd / 2 + 1.0)
                if gables and k % 2 == 0 and k > 0:
                    chidori(cx, cy, z - 0.1, dd * 0.38, rot + math.pi / 2, ww / 2 + 1.0)
                    chidori(cx, cy, z - 0.1, dd * 0.38, rot - math.pi / 2, ww / 2 + 1.0)
                z += 1.0
                ww *= shrink
                dd *= shrink
        # 最上層：入母屋造屋頂與鯱
        b.hip_roof(roof, ww, dd, 4.2, (cx, cy, z - 0.2), overhang=2.2, upturn=0.7, rot_z=rot)
        chidori(cx, cy, z + 0.6, dd * 0.55, rot + math.pi / 2, ww / 2 * 0.5)
        chidori(cx, cy, z + 0.6, dd * 0.55, rot - math.pi / 2, ww / 2 * 0.5)
        for s in (-1, 1):
            rx = cx + math.cos(rot) * s * max(0.4, (ww - dd) / 2)
            ry = cy + math.sin(rot) * s * max(0.4, (ww - dd) / 2)
            b.box_base(gold, (0.6, 0.4, 1.4), (rx, ry, z + 3.8), rot=(0, 0, rot))
        return z

    zb = hill(0, 0)
    # 大天守：石垣 14.85 m ＋ 天守 31.5 m
    ishigaki(0, 0, 26, 22, 14.85, zb)
    keep(0, 0, zb + 14.85, 26, 22, 6, fh=3.9, shrink=0.88)
    # 西小天守、乾小天守、東小天守（位於大天守北側，以渡櫓相連）
    for (x, y, w, d, nf) in [(-30, 14, 14, 12, 3), (-26, 34, 13, 11, 3), (4, 30, 12, 10, 3)]:
        ishigaki(x, y, w, d, 11.0, hill(x, y))
        keep(x, y, hill(x, y) + 11.0, w, d, nf, fh=3.4, shrink=0.85)
    for (x0, y0, x1, y1) in [(-14, 6, -26, 12), (-30, 20, -27, 28), (-20, 36, -2, 32), (2, 22, 2, 12)]:
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        ishigaki(mx, my, L, 7, 10.0, hill(mx, my))
        floor(mx, my, L, 7, hill(mx, my) + 10.0, 3.6, rot=ang)
        b.hip_roof(roof, L, 7, 2.4, (mx, my, hill(mx, my) + 13.4), overhang=1.6, upturn=0.4, rot_z=ang)
    # 前方的城牆與櫓（白壁＋瓦頂）
    for (x0, y0, x1, y1) in [(-70, -40, -10, -55), (-10, -55, 50, -45), (50, -45, 75, -10)]:
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        z = hill(mx, my)
        ishigaki(mx, my, L, 3, 6.0, z - 1)
        b.box_base(plaster, (L, 1.0, 2.6), (mx, my, z + 5), rot=(0, 0, ang))
        b.tri_prism(roof, L, 2.4, 1.0, (mx, my, z + 7.6), rot_z=ang)
    for (x, y) in [(-10, -55), (50, -45)]:
        z = hill(x, y)
        ishigaki(x, y, 12, 9, 7.0, z - 1)
        keep(x, y, z + 6.0, 11, 8, 2, fh=3.4, gables=False)
    b.box_base(gravel, (70, 40, 0.1), (0, -25, hill(0, -25) - 0.05))
    # 松樹與林木
    for x, y in b.scatter(120, 40, 165, min_dist=8, avoid=lambda x, y: abs(x) < 45 and -30 < y < 50):
        z = hill(x, y)
        hgt = b.rng.uniform(8, 14)
        b.cyl(b.color("trunk", "#5a4330"), 0.3, 0.2, hgt * 0.7, (x, y, z), seg=7)
        for k in range(3):
            b.rock(b.color("pine", "#2f5530", rough=0.9), (hgt * 0.55 - k * 1.2, hgt * 0.55 - k * 1.2, hgt * 0.2), (x + b.rng.uniform(-1, 1), y + b.rng.uniform(-1, 1), z + hgt * (0.55 + 0.17 * k)), rough=0.3, subdiv=2, seed=b.rng.randint(0, 9999), flat_bottom=False)
    b.export(path)
