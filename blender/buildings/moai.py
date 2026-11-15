"""moai 復活節島阿胡通加里基（Ahu Tongariki）15 尊摩艾寫實模型（公尺）

石台（ahu）長約 100 m，摩艾高 5.6–8.7 m，背向太平洋面向內陸；其中一尊戴紅色火山渣頂髻（pukao）。
座標：石台沿 X 軸，摩艾面向 -Y。
"""

import ast
import math
import os

from mathutils import Vector, noise

from lib import TAU, Builder
from buildings.sphinx import lerp_table, loft

# 目標點、方位角、仰角、距離、焦距（對應參考照：石台東北端前方低角度）
CAMERA = ((27.0, 0.0, 5.5), 64.0, -3.0, 38.0, 24.0)
if os.environ.get("TL_CAM"):  # 開發用：覆寫預覽相機
    CAMERA = ast.literal_eval(os.environ["TL_CAM"])

# 摩艾外形（以總高 H 正規化）：z, 半寬, 前深, 後深
PROFILE = [
    (0.00, 0.265, 0.175, 0.150), (0.25, 0.262, 0.180, 0.145), (0.40, 0.250, 0.185, 0.135),
    (0.455, 0.232, 0.150, 0.130), (0.475, 0.222, 0.135, 0.130), (0.50, 0.220, 0.210, 0.135),
    (0.525, 0.222, 0.205, 0.137), (0.545, 0.224, 0.172, 0.138), (0.60, 0.228, 0.162, 0.142),
    (0.78, 0.235, 0.155, 0.150), (0.815, 0.238, 0.155, 0.150), (0.835, 0.240, 0.205, 0.150),
    (0.87, 0.237, 0.188, 0.147), (0.93, 0.230, 0.125, 0.138), (0.975, 0.208, 0.068, 0.116),
    (1.00, 0.160, 0.020, 0.078),
]


def moai_statue(b, mi, x, y, H, yaw=0.0, seed=0, lean=0.0, z0=0.0):
    """單尊摩艾：水平截面放樣（臉朝 -Y），再加鼻、唇、耳、手臂浮雕"""
    fwd = Vector((math.sin(yaw), -math.cos(yaw), 0))
    lat = Vector((math.cos(yaw), math.sin(yaw), 0))
    base = Vector((x, y, z0))
    sd = seed * 3.7

    def P(f, l, z):
        # 微小前傾與表面風化雜訊
        f += lean * z
        n = noise.noise(Vector((f * 1.3 + sd, l * 1.3, z * 0.9))) * 0.035 * H
        return base + fwd * (f + n * (1 if f > 0 else -1)) + lat * (l + n * (1 if l > 0 else -1) * 0.5) + Vector((0, 0, z))

    rings = []
    N = 36
    for k in range(34):
        u = k / 33
        W, Df, Db = lerp_table(PROFILE, u)
        z = u * H
        ring = []
        for i in range(N):
            t = TAU * i / N
            c, s = math.cos(t), math.sin(t)
            f = (Df if c > 0 else Db) * H * math.copysign(abs(c) ** (2 / 3.2), c)
            l = W * H * math.copysign(abs(s) ** (2 / 3.2), s)
            ring.append(P(f, l, z))
        rings.append(ring)
    loft(b, mi, rings)

    # 鼻：長而挺，鼻尖在下
    nr = []
    for u, w, f in ((0.585, 0.055, 0.215), (0.60, 0.062, 0.232), (0.64, 0.050, 0.222), (0.72, 0.040, 0.195), (0.80, 0.032, 0.170), (0.83, 0.030, 0.160)):
        z = u * H
        nr.append([P(0.13 * H, -w * H, z), P(f * H, -w * 0.45 * H, z), P(f * H, w * 0.45 * H, z), P(0.13 * H, w * H, z)])
    loft(b, mi, nr, smooth=False)
    # 噘起的嘴唇
    for u, w, f in ((0.565, 0.085, 0.188), (0.548, 0.080, 0.182)):
        z = u * H
        b.rock(mi, (0.03 * H, w * 2 * H, 0.016 * H), tuple(P(f * H - 0.012 * H, 0, z)), rot=(0, 0, yaw), rough=0.04, subdiv=1, seed=seed)
    # 長耳
    for sgn in (-1, 1):
        er = []
        for u, f0, f1 in ((0.62, -0.02, 0.03), (0.70, -0.04, 0.05), (0.80, -0.035, 0.06), (0.835, -0.01, 0.04)):
            z = u * H
            w = lerp_table(PROFILE, u)[0] * H
            er.append([P(f0 * H, sgn * (w - 0.02 * H), z), P(f1 * H, sgn * (w - 0.02 * H), z),
                       P(f1 * H, sgn * (w + 0.018 * H), z), P(f0 * H, sgn * (w + 0.018 * H), z)])
        loft(b, mi, er, smooth=True)
    # 手臂：沿身側往前到腹部的淺浮雕
    for sgn in (-1, 1):
        ar = []
        for u, f in ((0.40, -0.06), (0.30, -0.02), (0.22, 0.04), (0.17, 0.10), (0.15, 0.15)):
            z = u * H
            W = lerp_table(PROFILE, u)[0] * H
            lw = W if f < 0.1 else W * (1 - (f - 0.1) * 3.0)
            ar.append([P(f * H, sgn * (lw - 0.02 * H), z + 0.02 * H), P(f * H, sgn * (lw + 0.012 * H), z + 0.02 * H),
                       P(f * H, sgn * (lw + 0.012 * H), z - 0.02 * H), P(f * H, sgn * (lw - 0.02 * H), z - 0.02 * H)])
        loft(b, mi, ar, smooth=True)


def moai(path):
    b = Builder("Moai", seed=5)
    tuff = b.tex("tuff", "rock_04", tile=2.0, tint="#5f5240", normal=1.7, rough=0.9)
    scoria = b.tex("scoria", "rock_04", tile=1.2, tint="#6a2a1e", normal=1.8, rough=0.95)
    basalt = b.tex("basalt", "gray_rocks", tile=3.0, tint="#403b35", normal=1.4, rough=0.9)
    pave = b.tex("pave", "gray_rocks", tile=2.0, tint="#46403a", normal=1.2, rough=0.9)
    grass = b.tex("grass", "grass_ground", tile=3.0, tint="#86744a", normal=0.0, rough=0.95)
    cobble = basalt
    r = b.rng

    # ---- 地面：微起伏的草地（約 220 × 130 m）
    def gh(x, y):
        return 0.6 * noise.noise(Vector((x * 0.02, y * 0.02, 0.5))) + (0.012 * (y - 20) if y > 20 else 0.0)

    nx, ny = 56, 34
    X0, X1, Y0, Y1 = -110, 110, -80, 50
    grid = [[b.bm.verts.new((X0 + (X1 - X0) * i / nx, Y0 + (Y1 - Y0) * j / ny, gh(X0 + (X1 - X0) * i / nx, Y0 + (Y1 - Y0) * j / ny) - 0.4)) for j in range(ny + 1)] for i in range(nx + 1)]
    for i in range(nx):
        for j in range(ny):
            f = b.bm.faces.new([grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]])
            f.material_index = grass
            f.smooth = True

    # ---- 石台（ahu）：玄武岩砌石前牆、平台與前方鋪石坡道
    L, D, Hh = 98.0, 6.0, 1.6
    b.box_base(basalt, (L, D, Hh + 0.6), (0, 0, -0.6))
    b.box_base(pave, (L + 0.4, D + 0.3, 0.2), (0, 0, Hh - 0.05))
    # 前牆的大塊切石
    x = -L / 2
    while x < L / 2 - 0.5:
        w = r.uniform(1.6, 3.2)
        w = min(w, L / 2 - x)
        b.box_base(basalt, (w - 0.08, 0.35, Hh * r.uniform(0.75, 0.98)), (x + w / 2, -D / 2 - 0.12, 0.0))
        x += w
    # 兩翼低矮石台
    for sgn in (-1, 1):
        b.box_base(basalt, (40, 5.0, 0.9), (sgn * (L / 2 + 20), 0.5, -0.4))
    # 前方鋪石坡道（poro 圓石）
    RW = 11.0
    ramp_top = Hh * 0.35

    def ramp_z(py):
        k = (-D / 2 - py) / RW
        return ramp_top + (-0.15 - ramp_top) * k

    loft(b, pave, [[Vector((x, -D / 2 + 0.1, -0.6)), Vector((x, -D / 2 - RW - 0.5, -0.6)), Vector((x, -D / 2 - RW - 0.5, -0.2)), Vector((x, -D / 2 + 0.1, ramp_top))] for x in (-L / 2, L / 2)], smooth=False)
    for i in range(650):
        px, py = r.uniform(-L / 2 + 0.3, L / 2 - 0.3), -D / 2 - RW * math.sqrt(r.random())
        s = r.uniform(0.35, 0.75)
        b.rock(cobble, (s, s * 0.8, s * 0.45), (px, py, ramp_z(py) + 0.04), rot=(0, 0, r.uniform(0, TAU)), rough=0.08, subdiv=1, seed=i, round_=0.8)
    # 草地上散落的黑色熔岩石
    for i in range(320):
        px, py = r.uniform(-100, 100), r.uniform(-75, -D / 2 - RW - 1)
        s = r.uniform(0.4, 1.3)
        b.rock(basalt, (s, s * 0.8, s * 0.3), (px, py, gh(px, py) - 0.4 + s * 0.06), rot=(0, 0, r.uniform(0, TAU)), rough=0.15, subdiv=1, seed=900 + i, round_=0.6)

    # ---- 15 尊摩艾（由西往東）；第 14 尊戴 pukao 頂髻
    heights = [5.6, 6.3, 5.9, 6.6, 6.1, 6.8, 6.2, 7.1, 6.5, 7.3, 6.9, 7.6, 7.0, 7.7, 8.7]
    sp = 6.2
    for k, H in enumerate(heights):
        x = (k - 7) * sp + r.uniform(-0.4, 0.4)
        mi = tuff
        b.box_base(basalt, (H * 0.62, H * 0.42, 0.45), (x, 0.3, Hh))  # 基座
        moai_statue(b, mi, x, 0.3, H, yaw=r.uniform(-0.06, 0.06), seed=k, z0=Hh + 0.3)
        if k == 13:  # 紅色火山渣頂髻
            top = Hh + 0.3 + H
            b.rock(scoria, (H * 0.46, H * 0.42, H * 0.24), (x, 0.3 + H * 0.01, top + H * 0.08), rough=0.1, subdiv=3, seed=77, round_=0.55)

    b.export(path)
