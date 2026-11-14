"""stonehenge 寫實模型（尺寸依實測資料，公尺）"""

import math

from mathutils import Matrix, Vector, noise

from lib import TAU, Builder


# ====================================================================== 巨石陣
def stonehenge(path):
    b = Builder("Stonehenge", seed=7)
    grass = b.tex("grass", "grass_ground", tile=3.0, tint="#4e7d2e")
    soil = b.color("soil", "#5b4733", rough=0.95)
    sarsen = b.tex("sarsen", "rock_04", tile=2.2, tint="#9a9586", normal=1.6)
    blue = b.tex("bluestone", "rock_04", tile=1.8, tint="#77797a")
    path_m = b.tex("path", "gravel_floor", tile=2.0, tint="#b9ae95")
    r = b.rng

    def ground(x, y):
        d = math.hypot(x, y)
        # 周圍的環形溝與土堤（直徑約 110 m）
        bank = 0.5 * math.exp(-((d - 47) / 3.0) ** 2) - 0.35 * math.exp(-((d - 51) / 2.0) ** 2)
        return bank + 0.25 * noise.noise(Vector((x * 0.03, y * 0.03, 0)))

    b.ground_disc(grass, 60, soil, depth=4.0, height_fn=ground, rings=40, seg=128)
    axis = math.radians(50)  # 夏至日出方向（東北）

    def stone(m, w, t, h, x, y, ang, tilt=(0.0, 0.0), sink=0.4):
        vs = b.rock(m, (t, w, h + sink), (x, y, h / 2 - sink / 2), rot=(tilt[0], tilt[1], ang), rough=0.16, subdiv=5, seed=r.randint(0, 9999))
        # 直向風化溝紋與頂部收分，讓砂岩更接近實物
        seed = r.random() * 100
        for v in vs:
            local = v.co - Vector((x, y, 0))
            k = max(0.0, (v.co.z - h * 0.55) / (h * 0.45))
            v.co.x -= local.x * 0.12 * k
            v.co.y -= local.y * 0.12 * k
            gro = 0.06 * noise.noise(Vector((local.x * 2.5 + seed, local.y * 2.5, v.co.z * 0.25)))
            v.co.x += local.x * gro
            v.co.y += local.y * gro

    # 外圈砂岩圈：30 根直立石，直徑約 33 m；現存多集中於東北側
    R = 16.4
    standing = {0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 14, 16, 21, 22, 27, 28, 29}
    fallen = {12, 19, 25}
    for i in range(30):
        a = axis + TAU * i / 30
        x, y = R * math.cos(a), R * math.sin(a)
        if i in standing:
            stone(sarsen, 2.1 + r.uniform(-0.2, 0.2), 1.1, 4.1 + r.uniform(-0.15, 0.1), x, y, a, (r.uniform(-0.03, 0.03), r.uniform(-0.03, 0.03)))
        elif i in fallen:
            b.rock(sarsen, (4.0, 2.0, 1.0), (x * 1.08, y * 1.08, 0.3), rot=(0, 0, a + r.uniform(0.6, 1.2)), rough=0.09, seed=i)
        elif r.random() < 0.5:
            b.rock(sarsen, (1.2, 1.4, 0.6), (x, y, 0.15), rot=(0, 0, a), rough=0.12, seed=i)
    # 楣石：只在相鄰兩石都站立且屬現存段落時放置
    lintel_runs = {0, 1, 2, 3, 4, 5, 6, 27, 28, 21}
    for i in lintel_runs:
        j = (i + 1) % 30
        if i in standing and j in standing:
            a = axis + TAU * (i + 0.5) / 30
            L = 2 * R * math.sin(math.pi / 30) + 0.6
            b.rock(sarsen, (1.0, L - 0.25, 1.0), (R * math.cos(a), R * math.sin(a), 4.55), rot=(0, 0, a), rough=0.1, subdiv=4, seed=i + 100)

    # 青石圈（直徑約 23 m）
    for i in range(38):
        if r.random() < 0.45:
            continue
        a = axis + TAU * i / 38 + 0.03
        h = r.uniform(1.3, 2.2)
        stone(blue, r.uniform(0.6, 0.9), r.uniform(0.4, 0.6), h, 11.6 * math.cos(a), 11.6 * math.sin(a), a, (r.uniform(-0.15, 0.15), r.uniform(-0.1, 0.1)), 0.3)

    # 五座巨石牌坊（馬蹄形，開口朝東北），中央大牌坊最高 7.3 m
    tri = [(-80, 6.0, "ok"), (-42, 6.5, "ok"), (0, 7.3, "great"), (42, 6.5, "fallen_lintel"), (80, 6.0, "ok")]
    for ang, h, state in tri:
        a = axis + math.pi + math.radians(ang)
        rad = 7.6 if abs(ang) > 60 else 8.2
        cx, cy = rad * math.cos(a), rad * math.sin(a)
        tx, ty = -math.sin(a), math.cos(a)
        if state == "great":
            stone(sarsen, 2.3, 1.3, h, cx + tx * 1.3, cy + ty * 1.3, a, (0.06, 0.0))
            b.rock(sarsen, (7.2, 2.2, 1.2), (cx - tx * 2.6, cy - ty * 2.6, 0.5), rot=(0, 0, a + 1.4), rough=0.08, seed=77)
            b.rock(sarsen, (1.1, 4.8, 1.0), (cx - tx * 0.3 - math.cos(a) * 2.2, cy - ty * 0.3 - math.sin(a) * 2.2, 0.45), rot=(0, 0, a + 0.3), rough=0.06, seed=78)
            continue
        for s in (-1.15, 1.15):
            stone(sarsen, 2.0, 1.2, h, cx + tx * s, cy + ty * s, a)
        if state == "ok":
            b.rock(sarsen, (1.0, 4.6, 0.95), (cx, cy, h + 0.42), rot=(0, 0, a), rough=0.05, seed=int(h * 10))
        else:
            b.rock(sarsen, (1.0, 4.6, 0.95), (cx + math.cos(a) * 3.0, cy + math.sin(a) * 3.0, 0.4), rot=(0.1, 0, a + 0.5), rough=0.06, seed=55)
    # 內側青石馬蹄
    for k in range(11):
        a = axis + math.pi + math.radians(-75 + k * 15)
        stone(blue, 0.7, 0.5, r.uniform(1.6, 2.4), 5.6 * math.cos(a), 5.6 * math.sin(a), a, (r.uniform(-0.08, 0.08), 0), 0.3)
    # 祭壇石、屠宰石、踵石
    b.rock(blue, (4.9, 1.0, 0.5), (math.cos(axis + math.pi) * 4.2, math.sin(axis + math.pi) * 4.2, 0.2), rot=(0, 0, axis + 1.2), rough=0.05, seed=5)
    b.rock(sarsen, (6.4, 2.1, 0.8), (math.cos(axis) * 27, math.sin(axis) * 27, 0.25), rot=(0, 0, axis + 1.6), rough=0.06, seed=6)
    stone(sarsen, 2.4, 2.1, 4.7, math.cos(axis) * 42, math.sin(axis) * 42, axis, (0.18, 0.05), 0.6)
    b.export(path)
