"""eiffel 寫實模型（尺寸依實測資料，公尺）"""

import math

from mathutils import Matrix, Vector, noise

from lib import TAU, Builder


# ====================================================================== 艾菲爾鐵塔
def eiffel(path):
    b = Builder("Eiffel", seed=29)
    grass = b.tex("grass", "grass_ground", tile=4.0, tint="#5d8a36")
    soil = b.color("soil", "#5d4a35", rough=0.95)
    gravel = b.tex("gravel", "gravel_floor", tile=2.5, tint="#c8b896")
    iron = b.tex("iron", "rusty_painted_metal", tile=6.0, tint="#6b5646", rough=0.55, metal=0.35)
    iron_dark = b.color("iron_dark", "#4a3b30", rough=0.55, metal=0.35)
    glass = b.color("glass", "#9fb6c4", rough=0.08, metal=0.2)
    stone = b.tex("pier", "large_sandstone_blocks", tile=3.0, tint="#b2a48c")

    b.ground_disc(grass, 420, soil, depth=6, rings=20, seg=128)
    b.box_base(gravel, (170, 170, 0.08), (0, 0, 0))
    b.box_base(gravel, (60, 400, 0.06), (0, -230, 0))
    for x in (-58, 58):
        for k in range(26):
            b.tree(x + b.rng.uniform(-2, 2), -95 - k * 12, 0, h=b.rng.uniform(13, 17))
    for x, y in b.scatter(80, 140, 410, avoid=lambda x, y: abs(x) < 75 and y < -60, min_dist=14):
        b.tree(x, y, 0, h=b.rng.uniform(12, 18))

    z1, z2, z3, ztop = 57.6, 115.7, 276.1, 300.0

    def leg(z):
        """單一支腳在高度 z 的中心距與截面半寬"""
        if z <= z1:
            t = z / z1
            return 51.5 - 18.0 * t ** 0.9, 12.0 - 4.0 * t
        t = (z - z1) / (z2 - z1)
        return 33.5 - 19.0 * t ** 0.85, 8.0 - 2.0 * t

    def sq(cx, cy, z, h):
        return [Vector((cx - h, cy - h, z)), Vector((cx + h, cy - h, z)), Vector((cx + h, cy + h, z)), Vector((cx - h, cy + h, z))]

    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box_base(stone, (26, 26, 3.0), (sx * 51.5, sy * 51.5, 0))
            rings = []
            for k in range(23):
                z = 3.0 + (z2 - 3.0) * k / 22
                c, h = leg(z)
                rings.append(sq(sx * c, sy * c, z, h))
            b.lattice(f"leg_{sx}_{sy}", rings, iron, 0.55)
            # 四個角的主弦桿（實心箱型樑）
            for k in range(22):
                za, zb = rings[k][0].z, rings[k + 1][0].z
                for ci in range(4):
                    pa, pb = rings[k][ci], rings[k + 1][ci]
                    mid = (pa + pb) / 2
                    dvec = pb - pa
                    L = dvec.length
                    rot = dvec.to_track_quat("Z", "Y").to_euler()
                    b.box(iron_dark, (1.1, 1.1, L + 0.3), tuple(mid), rot=tuple(rot))
    # 塔身（第二層以上）
    rings = []
    for k in range(29):
        z = z2 + (z3 - z2) * k / 28
        u = (z3 - z) / (z3 - z2)
        h = 9.3 + 11.0 * u**1.6
        rings.append(sq(0, 0, z, h))
    b.lattice("shaft", rings, iron, 0.45)
    for k in range(28):
        for ci in range(4):
            pa, pb = rings[k][ci], rings[k + 1][ci]
            mid = (pa + pb) / 2
            dvec = pb - pa
            b.box(iron_dark, (0.9, 0.9, dvec.length + 0.2), tuple(mid), rot=tuple(dvec.to_track_quat("Z", "Y").to_euler()))
    b.lattice("top", [sq(0, 0, z3 + 4, 9.0), sq(0, 0, z3 + 14, 6.5), sq(0, 0, ztop - 4, 4.0)], iron, 0.35)

    # 基部四面的裝飾拱
    for side in range(4):
        a = side * math.pi / 2
        nx, ny = math.cos(a), math.sin(a)
        tx, ty = -ny, nx
        R = 37.0
        for ring_r in (R, R - 2.5):
            for i in range(36):
                t = math.pi * (i + 0.5) / 36
                px = nx * 40 + tx * ring_r * math.cos(t)
                py = ny * 40 + ty * ring_r * math.cos(t)
                pz = 12 + ring_r * math.sin(t) * 1.02
                tangent = Vector((-tx * math.sin(t), -ty * math.sin(t), math.cos(t)))
                b.box(iron_dark, (0.9, 0.9, math.pi * ring_r / 36 + 0.3), (px, py, pz), rot=tuple(tangent.to_track_quat("Z", "Y").to_euler()))
    # 第一層平台（約 70 m 見方）與玻璃展廳
    b.box_base(iron, (72, 72, 4.5), (0, 0, z1 - 1.5))
    b.box_base(iron_dark, (73, 73, 1.2), (0, 0, z1 + 3.0))
    for side in range(4):
        a = side * math.pi / 2
        b.box_base(glass, (40, 8, 6), (math.cos(a - math.pi / 2) * 30, math.sin(a - math.pi / 2) * 30, z1 + 4.2), rot=(0, 0, a))
    # 第二層平台（約 40 m 見方）
    b.box_base(iron, (42, 42, 3.5), (0, 0, z2 - 1.0))
    b.box_base(iron_dark, (43, 43, 1.0), (0, 0, z2 + 2.5))
    b.box_base(glass, (22, 22, 5), (0, 0, z2 + 3.5))
    # 第三層觀景台、頂部構造與天線（至 330 m）
    b.box_base(iron, (19, 19, 3), (0, 0, z3))
    b.box_base(glass, (16.5, 16.5, 5), (0, 0, z3 + 3))
    b.box_base(iron_dark, (19.5, 19.5, 1), (0, 0, z3 + 8))
    b.cyl(iron, 3.5, 2.5, 6, (0, 0, ztop - 4), seg=12)
    b.cyl(iron_dark, 1.2, 0.6, 24, (0, 0, ztop + 2), seg=10)
    b.cyl(b.color("antenna", "#d8d8d8", rough=0.4, metal=0.6), 0.5, 0.2, 10, (0, 0, ztop + 26), seg=8)
    b.export(path)
