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
CAMERA = ((30.0, 0.0, 4.5), 42.0, 3.0, 30.0, 18.0)
if os.environ.get("TL_CAM"):  # 開發用：覆寫預覽相機
    CAMERA = ast.literal_eval(os.environ["TL_CAM"])

# 摩艾外形（以總高 H 正規化）：z, 半寬, 前深, 後深
PROFILE = [
    (0.0, 0.18, 0.143, 0.123),
    (0.25, 0.178, 0.148, 0.119),
    (0.4, 0.17, 0.152, 0.111),
    (0.455, 0.158, 0.123, 0.107),
    (0.475, 0.151, 0.111, 0.107),
    (0.5, 0.15, 0.172, 0.111),
    (0.525, 0.151, 0.168, 0.112),
    (0.545, 0.152, 0.141, 0.113),
    (0.6, 0.155, 0.133, 0.116),
    (0.78, 0.16, 0.127, 0.123),
    (0.815, 0.162, 0.127, 0.123),
    (0.835, 0.163, 0.168, 0.123),
    (0.87, 0.161, 0.154, 0.121),
    (0.93, 0.156, 0.102, 0.113),
    (0.975, 0.141, 0.056, 0.095),
    (1.0, 0.109, 0.016, 0.064),
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
    for u, w, f in ((0.585, 0.044, 0.176), (0.60, 0.050, 0.19), (0.64, 0.040, 0.182), (0.72, 0.032, 0.16), (0.80, 0.026, 0.139), (0.83, 0.024, 0.131)):
        z = u * H
        nr.append([P(0.105 * H, -w * H, z), P(f * H, -w * 0.45 * H, z), P(f * H, w * 0.45 * H, z), P(0.105 * H, w * H, z)])
    loft(b, mi, nr, smooth=False)
    # 噘起的嘴唇
    for u, w, f in ((0.565, 0.06, 0.154), (0.548, 0.056, 0.149)):
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
    tuff = b.tex("tuff", "rock_04", tile=2.0, tint="#3d3426", normal=1.8, rough=0.9)
    tuff2 = b.tex("tuff2", "rock_04", tile=2.0, tint="#4a4436", normal=1.8, rough=0.9)
    scoria = b.tex("scoria", "rock_04", tile=1.2, tint="#3f1a12", normal=1.8, rough=0.95)
    basalt = b.tex("basalt", "gray_rocks", tile=3.0, tint="#575046", normal=1.4, rough=0.9)
    pave = b.tex("pave", "gray_rocks", tile=2.0, tint="#3e3830", normal=1.2, rough=0.9)
    grass = b.tex("grass", "aerial_grass_rock", tile=9.0, gain=0.8, normal=0.0, rough=0.95)
    cobble = basalt
    r = b.rng

    # ---- 地面：微起伏的草地（約 220 × 130 m）
    def gh(x, y):
        return 0.6 * noise.noise(Vector((x * 0.02, y * 0.02, 0.5))) - (0.03 * (y - 25) if y > 25 else 0.0)

    soil = b.color("soil", "#4a3f30", rough=0.95)
    b.ground_disc(grass, 125, soil, depth=2.5, seg=96, rings=30, height_fn=lambda x, y: gh(x, y) - 0.4)

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
        b.box_base(basalt, (36, 4.0, 0.75), (sgn * (L / 2 + 18), 0.8, -0.4))
    # 前方鋪石坡道（poro 圓石）：靠牆的碎石堆，往外漸疏並融入草地
    RW = 6.5

    def ramp_z(px, py):
        k = max(0.0, min(1.0, (-D / 2 - py) / 3.0))
        return (Hh * 0.45) * (1 - k) ** 1.5 + (gh(px, py) - 0.4) * k

    loft(b, pave, [[Vector((x, -D / 2 + 0.1, -0.6)), Vector((x, -D / 2 - 3.2, -1.5)), Vector((x, -D / 2 - 3.2, -0.9)), Vector((x, -D / 2 + 0.1, Hh * 0.45))] for x in (-L / 2, L / 2)], smooth=False)
    for i in range(900):
        px, py = r.uniform(-L / 2 + 0.3, L / 2 - 0.3), -D / 2 - RW * r.random() ** 1.8
        s = r.uniform(0.3, 0.75)
        b.rock(cobble, (s, s * 0.8, s * 0.45), (px, py, ramp_z(px, py) + 0.04), rot=(0, 0, r.uniform(0, TAU)), rough=0.1, subdiv=1, seed=i, round_=0.75)
    # 草地上散落的黑色熔岩石
    for i in range(520):
        px, py = r.uniform(-100, 100), -D / 2 - 2 - 60 * r.random() ** 1.6
        s = r.uniform(0.35, 1.2)
        b.rock(basalt, (s, s * 0.8, s * 0.3), (px, py, gh(px, py) - 0.4 + s * 0.04), rot=(0, 0, r.uniform(0, TAU)), rough=0.15, subdiv=1, seed=900 + i, round_=0.6)

    # ---- 15 尊摩艾（由西往東）；第 14 尊戴 pukao 頂髻
    heights = [5.6, 6.3, 5.9, 6.6, 6.1, 6.8, 6.2, 7.1, 6.5, 7.3, 6.9, 7.6, 7.0, 7.7, 8.7]
    sp = 6.2
    for k, H in enumerate(heights):
        x = (k - 7) * sp + r.uniform(-0.4, 0.4)
        mi = tuff2 if k in (3, 8, 12) else tuff
        b.box_base(basalt, (H * 0.44, H * 0.36, 0.45), (x, 0.3, Hh))  # 基座
        moai_statue(b, mi, x, 0.3, H, yaw=r.uniform(-0.06, 0.06), seed=k, z0=Hh + 0.3)
        if k == 13:  # 紅色火山渣頂髻
            top = Hh + 0.3 + H
            # 頂髻：略呈鼓形的圓柱（直徑約 2 m、高約 1.6 m）
            vs = b.lathe(scoria, [(0, -0.1), (1.1, -0.1), (1.25, 0.5), (1.2, 1.1), (1.05, 1.5), (0.0, 1.6)], (x, 0.3 + H * 0.01, top - 0.25), seg=20, smooth=True)
            for v in vs:
                v.co += Vector((0, 0, 1)) * 0.06 * noise.noise(v.co * 1.7) + (v.co - Vector((x, 0.3, v.co.z))) * 0.08 * noise.noise(v.co * 2.3 + Vector((3, 1, 0)))

    b.export(path)
