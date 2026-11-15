"""machu-picchu 馬丘比丘（印加古城，約 1450 年）寫實模型（公尺；+Y 北，城區高程定為 0）

- 地形：古城位於馬丘比丘山與瓦伊納比丘山（Huayna Picchu，比城區高約 300 m、尖峰）之間的鞍部山脊，
  東西兩側為陡降約 400 m 的烏魯班巴河谷（此處截至 -260 m）；西北側另有一座較低的尖峰
- 城區約 350 × 170 m：中央下沉廣場（草地）、西側神殿區（主神殿、三窗神殿、拴日石小丘）、
  東側住居區（密集的無頂石屋、兩端山牆）；南側與西側坡面為層層農業梯田（石砌擋土牆＋草面）
- 遠山與山坡覆蓋雲霧林（深綠樹冠貼圖），極陡處裸露岩壁
- 地景範圍約 1000 × 1000 m（≦ 城區最大尺寸的 2.5 倍半徑）
"""

import math

import numpy as np
from mathutils import Matrix, Vector, noise

from lib import TAU
from buildings.forbidden_city import CnBuilder
from buildings.kinkakuji import gen_canopy

# (目標點, 方位角, 仰角, 距離, 焦距)：參考照自南側守衛屋上方俯瞰古城，瓦伊納比丘山居中
CAMERA = ((-15.0, 200.0, 82.0), 6.6, -2.9, 393.0, 28)

PLAZA = (-42.0, 2.0, 25.0, 115.0)  # x0, x1, y0, y1（下沉廣場）


def _fbm(x, y, scale, octaves=4):
    v, a, f = 0.0, 1.0, 1.0 / scale
    for _ in range(octaves):
        v += a * noise.noise(Vector((x * f, y * f, 0.37)))
        a *= 0.5
        f *= 2.0
    return v


def base_height(x, y):
    """未分層的自然地形"""
    xc = -10.0 + 0.04 * y
    d = abs(x - xc)
    # 山脊縱剖面：城區平、南側往馬丘比丘山升高、北側鞍部
    if y < -60:
        E = 0.3 * (-60 - y)
    elif y < 175:
        E = 0.0
    else:
        E = -0.18 * (y - 175)
    # 橫剖面：城區頂部緩、兩翼漸陡（梯田）、外側陡降河谷
    h = E - 0.004 * d * d - (1.35 * (d - 95) ** 1.15 if d > 95 else 0.0)
    if -40 < y < 160 and d < 50:
        h += 0.001 * d * d - 0.07 * (x - xc) - 0.03 * (y - 60)
        h += 6.0 * math.exp(-(((x + 40) / 20) ** 2 + ((y - 128) / 20) ** 2))  # 拴日石小丘
    nz = _fbm(x, y, 45.0) + 0.6 * (1 - 2 * abs(noise.noise(Vector((x / 28.0, y / 28.0, 1.7)))))
    # 瓦伊納比丘（尖峰）
    r = math.hypot(x + 25, (y - 390) * 1.1)
    hp = 330.0 * max(0.0, 1 - r / 175) ** 1.2 - 40 + 22 * nz
    # 東側自主峰下降的巨大稜線（右側陡壁）
    ax, ay, bx, by = -25.0, 390.0, 330.0, 250.0
    t = max(0.0, min(1.0, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / ((bx - ax) ** 2 + (by - ay) ** 2)))
    q = math.hypot(x - (ax + (bx - ax) * t), y - (ay + (by - ay) * t))
    ridge = 290.0 * (1 - t) ** 1.1 * math.exp(-((q / 70) ** 2)) - 40 + 18 * nz
    # 西北較低尖峰
    r2 = math.hypot(x + 150, (y - 250) * 1.1)
    lp = 175.0 * max(0.0, 1 - r2 / 120) ** 1.35 - 50 + 15 * nz
    far = min(1.0, max(0.0, (d - 95) / 40.0)) if y < 200 else 1.0
    h += _fbm(x * 1.7, y * 1.7, 60.0) * 14.0 * far
    h = max(h, hp, ridge, lp)
    return max(h, -260.0)


def site_mask(x, y):
    xc = -10.0 + 0.04 * y
    return abs(x - xc) < 118 and -225 < y < 185


def height(x, y):
    h = base_height(x, y)
    if not site_mask(x, y):
        return h
    px0, px1, py0, py1 = PLAZA
    if px0 < x < px1 and py0 < y < py1:
        return -7.0
    s = 2.6
    q = h / s
    f = q - math.floor(q)
    return s * (math.floor(q) + min(1.0, max(0.0, (f - 0.8) / 0.2)))


class AndesBuilder(CnBuilder):
    def grid(self, x0, x1, y0, y1, step, hfun, mat_fn, skip=None, smooth_all=False):
        nx, ny = int(round((x1 - x0) / step)), int(round((y1 - y0) / step))
        H = np.zeros((nx + 1, ny + 1))
        for i in range(nx + 1):
            for j in range(ny + 1):
                H[i, j] = hfun(x0 + i * step, y0 + j * step)
        vs = [[None] * (ny + 1) for _ in range(nx + 1)]

        def v(i, j):
            if vs[i][j] is None:
                vs[i][j] = self.V((x0 + i * step, y0 + j * step, H[i, j]))
            return vs[i][j]
        for i in range(nx):
            for j in range(ny):
                cx, cy = x0 + (i + 0.5) * step, y0 + (j + 0.5) * step
                if skip and skip(cx, cy):
                    continue
                a, b_, c, d = (x0 + i * step, y0 + j * step, H[i, j]), (x0 + (i + 1) * step, y0 + j * step, H[i + 1, j]), \
                    (x0 + (i + 1) * step, y0 + (j + 1) * step, H[i + 1, j + 1]), (x0 + i * step, y0 + (j + 1) * step, H[i, j + 1])
                n = (Vector(b_) - Vector(a)).cross(Vector(d) - Vector(a)).normalized()
                span = max(a[2], b_[2], c[2], d[2]) - min(a[2], b_[2], c[2], d[2])
                self.face([v(i, j), v(i + 1, j), v(i + 1, j + 1), v(i, j + 1)], mat_fn(cx, cy, n.z, H[i, j], span), smooth=bool(smooth_all or span < 1.2))
        return H


def machu_picchu(path):
    b = AndesBuilder("MachuPicchu", seed=9)
    grass = b.ptex("grass", "grass_ground", tile=6.0, tint="#44681f", rough=0.95, normal=0.6)
    plaza_g = b.ptex("plaza", "grass_ground", tile=5.0, tint="#55842a", rough=0.95, normal=0.4)
    wall = b.ptex("wall", "stone_wall_04", tile=3.0, tint="#706c62", rough=0.9, normal=1.0)
    wall_d = b.ptex("wall_d", "stone_wall_04", tile=3.0, tint="#5c5952", rough=0.9, normal=1.0)
    forest = b.gtex("forest", gen_canopy("andes2", (34, 54, 30), seed=12), tile=16.0, rough=0.95, normal=1.0)
    forest_l = b.gtex("forest_l", gen_canopy("andes_l2", (52, 78, 36), seed=13), tile=12.0, rough=0.95, normal=1.0)
    cliff = b.color("cliff", "#383b31", rough=0.95)
    rocky = b.ptex("granite", "rock_04", tile=4.0, tint="#8e8b82", rough=0.9, normal=1.0)
    thatch = b.color("thatch", "#8f7a52", rough=1.0)

    # ---------------- 城區（細網格、梯田化）
    X0, X1, Y0, Y1 = -137.5, 112.5, -237.5, 200.0
    px0, px1, py0, py1 = PLAZA

    def inner_mat(cx, cy, nz, h, span):
        if px0 < cx < px1 and py0 < cy < py1:
            return plaza_g
        if not site_mask(cx, cy) or abs(cx - (-10.0 + 0.04 * cy)) > 96:
            return forest if nz > 0.3 else cliff
        if span > 1.3 or nz < 0.5:
            return wall
        return grass
    b.grid(X0, X1, Y0, Y1, 2.5, height, inner_mat)

    # ---------------- 外圍地形（粗網格，挖空城區）
    def outer_mat(cx, cy, nz, h, span):
        if nz < 0.3:
            return forest
        return forest_l if (h < 40 and nz > 0.75) else forest
    R = 500.0
    b.grid(-R, R, -R + 50, R + 150, 12.5, base_height, outer_mat, smooth_all=True,
           skip=lambda x, y: (X0 < x < X1 and Y0 < y < Y1) or math.hypot(x, y - 75) > R + 20)
    # 內外交界的裙邊（遮蔽 T 形接縫）
    for (ax, ay, bx, by) in ((X0, Y0, X1, Y0), (X1, Y0, X1, Y1), (X1, Y1, X0, Y1), (X0, Y1, X0, Y0)):
        n = int(math.hypot(bx - ax, by - ay) / 2.5)
        for k in range(n):
            p0 = (ax + (bx - ax) * k / n, ay + (by - ay) * k / n)
            p1 = (ax + (bx - ax) * (k + 1) / n, ay + (by - ay) * (k + 1) / n)
            h0, h1 = height(*p0), height(*p1)
            b.face([b.V((p0[0], p0[1], h0)), b.V((p1[0], p1[1], h1)), b.V((p1[0], p1[1], h1 - 8)), b.V((p0[0], p0[1], h0 - 8))], forest)

    # ---------------- 石屋（無頂、兩端山牆）
    rng = b.rng

    def house(cx, cy, w, d, ang, roof=False):
        zs = [height(cx + sx * w / 2 * math.cos(ang) - sy * d / 2 * math.sin(ang), cy + sx * w / 2 * math.sin(ang) + sy * d / 2 * math.cos(ang))
              for sx in (-1, 1) for sy in (-1, 1)]
        z0 = min(zs) - 0.4
        hw = max(zs) - z0 + 2.4
        M = Matrix.Translation((cx, cy, z0)) @ Matrix.Rotation(ang, 4, "Z")
        t = 0.6
        mi = wall if rng.random() < 0.7 else wall_d
        b.place(lambda: b.box_base(mi, (w, t, hw), (0, -d / 2 + t / 2, 0)), M)
        b.place(lambda: b.box_base(mi, (w, t, hw), (0, d / 2 - t / 2, 0)), M)
        for s in (-1, 1):
            b.place(lambda s=s: b.box_base(mi, (t, d - 2 * t, hw), (s * (w / 2 - t / 2), 0, 0)), M)
            b.place(lambda s=s: b.tri_prism(mi, t, d, 2.2, (s * (w / 2 - t / 2), 0, hw), rot_z=0.0), M)
        # 門洞
        b.place(lambda: b.box_base(b.color("shadow", "#2a2722", rough=1.0), (1.0, t + 0.04, 1.9), (rng.uniform(-w / 4, w / 4), -d / 2 + t / 2, hw - 2.4 + 0.1)), M)
        if roof:
            b.place(lambda: b.tri_prism(thatch, w + 0.6, d + 1.2, 2.5, (0, 0, hw - 0.1)), M)

    occupied = []

    def try_house(x, y, w, d, ang, roof=False):
        if px0 - 4 < x < px1 + 4 and py0 - 4 < y < py1 + 4:
            return
        if any(abs(x - ox) < (w + ow) / 2 + 1.2 and abs(y - oy) < (d + od) / 2 + 1.2 for ox, oy, ow, od in occupied):
            return
        occupied.append((x, y, max(w, d), max(w, d)))
        house(x, y, w, d, ang, roof)

    # 東側住居區：密集成排
    for gy in range(-60, 160, 9):
        for gx in range(6, 80, 10):
            if rng.random() < 0.9:
                try_house(gx + rng.uniform(-1.5, 1.5), gy + rng.uniform(-1.5, 1.5), rng.uniform(6.5, 10.0), rng.uniform(4.5, 6.0),
                          rng.choice((0.0, math.pi / 2)) + 0.04 * (gy / 10))
    # 西側神殿區與南側
    for gy in range(-20, 160, 10):
        for gx in range(-86, -44, 10):
            if rng.random() < 0.8:
                try_house(gx + rng.uniform(-1.5, 1.5), gy + rng.uniform(-1.5, 1.5), rng.uniform(7.0, 11.0), rng.uniform(4.5, 6.5), 0.0)
    for gy in (-50, -38, 128, 140, 150):
        for gx in range(-44, 6, 11):
            if rng.random() < 0.8:
                try_house(gx + rng.uniform(-2, 2), gy + rng.uniform(-2, 2), rng.uniform(6.5, 9.5), rng.uniform(4.5, 6.0), 0.0)
    # 主神殿（三面牆）、三窗神殿：西側廣場邊
    house(-50.0, 70.0, 12.0, 8.0, math.pi / 2)
    house(-50.0, 50.0, 10.5, 7.5, math.pi / 2)
    # 守衛屋（茅草頂）與梯田上的幾座茅頂小屋
    house(48.0, -205.0, 7.0, 5.0, 0.3, roof=True)
    house(30.0, -150.0, 6.0, 4.5, 0.0, roof=True)
    # 拴日石
    b.rock(rocky, (2.4, 1.6, 1.8), (-38.0, 128.0, height(-38.0, 128.0) - 0.2), seed=3, round_=0.2, rough=0.1)
    # 城中散落的花崗岩塊（採石場，參考照中央）
    for _ in range(14):
        x, y = rng.uniform(-30, 5), rng.uniform(-28, 15)
        s = rng.uniform(1.0, 2.6)
        b.rock(rocky, (s * 1.4, s, s * 0.8), (x, y, height(x, y) - 0.3), rot=(0, 0, rng.uniform(0, TAU)), seed=rng.randint(0, 99), round_=0.4)

    b.export_glb(path)
