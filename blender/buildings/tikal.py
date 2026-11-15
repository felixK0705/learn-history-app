"""tikal 蒂卡爾一號神廟（大美洲豹神廟，約西元 732 年）寫實模型（公尺；+X 東、+Y 北）

- 金字塔基座 9 層階台，總高約 30 m，底約 30 × 30 m；每層下段為內縮的裙板（apron）、上段為陡峭斜面，
  四角內凹（inset corners）
- 西面中央一道陡梯（約 70°，寬約 10 m）自廣場直達頂台
- 頂上神廟：三室、西向門洞；其上為高聳的屋頂冠（roof comb），連同金字塔總高約 47 m
- 石材為灰白石灰岩，上段風化發黑；周圍為大廣場草地、石碑與祭壇、熱帶闊葉樹
"""

import math

from mathutils import Matrix, Vector

from lib import TAU
from buildings.forbidden_city import CnBuilder
from buildings.kinkakuji import gen_canopy, gen_leaves

# (目標點, 方位角, 仰角, 距離, 焦距)：參考照自北衛城一側（西北北）仰望：北面正對、西面大階梯在右側斜伸
CAMERA = ((-4.0, 0.0, 22.0), 218.0, -18.5, 63.0, 30)


def inset_rect(sx, sy, d, z):
    pts = []
    for (qx, qy) in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        quad = [(sx, sy - d), (sx - d, sy - d), (sx - d, sy)]
        if qx * qy < 0:
            quad = list(reversed(quad))
        pts += [(qx * x, qy * y, z) for x, y in quad]
    return pts


class MayaBuilder(CnBuilder):
    def loft_rect(self, mi, rings, cap_top=True):
        vr = [[self.V(p) for p in r] for r in rings]
        self.face(list(reversed(vr[0])), mi)
        self.strip(vr, mi)
        if cap_top:
            self.face(vr[-1], mi)


def tikal(path):
    b = MayaBuilder("Tikal", seed=5)
    lime = b.ptex("lime", "large_sandstone_blocks", tile=3.0, tint="#8c8679", rough=0.9, normal=1.0)
    lime_d = b.ptex("lime_dark", "large_sandstone_blocks", tile=3.0, tint="#67635b", rough=0.9, normal=1.0)
    lime_l = b.ptex("lime_light", "large_sandstone_blocks", tile=3.0, tint="#bcb29a", rough=0.9, normal=1.0)
    rubble = b.ptex("rubble", "gray_rocks", tile=2.5, tint="#77746c", rough=0.9, normal=1.0)
    plaster = b.ptex("plaster", "plastered_wall_04", tile=3.0, tint="#cfcab9", rough=0.9, normal=0.5)
    dark = b.color("void", "#14120f", rough=1.0)
    grass = b.ptex("grass", "grass_ground", tile=4.0, tint="#5f9a2e", rough=0.95, normal=0.5)
    soil = b.color("soil", "#5b4a36", rough=1.0)
    thatch = b.color("thatch", "#8a7550", rough=1.0)
    wood = b.color("wood", "#5a4430", rough=0.9)
    lf_broad = b.alpha_mat("leaf_broad", gen_leaves("broad"))
    lf_light = b.alpha_mat("leaf_light", gen_leaves("light"))
    lf_dark = b.alpha_mat("leaf_dark", gen_leaves("dark"))
    core_b = b.gtex("core_broad", gen_canopy("broad", (84, 120, 44), seed=5), tile=3.0, rough=0.9, normal=1.0)
    bark = b.color("bark", "#77705f", rough=0.9)

    # ---------------- 廣場地面（圓角方形，半徑 ≤ 2.5 × 建物尺寸）
    b.box_base(grass, (150.0, 150.0, 0.6), (-15.0, 0, -0.6))
    b.box_base(soil, (150.2, 150.2, 2.0), (-15.0, 0, -2.6))

    # ---------------- 金字塔 9 層（西面朝 -X）
    N = 9
    S0, S1 = 14.0, 8.0
    ZT = 30.4
    th = ZT / N
    for i in range(N):
        s = S0 - (S0 - S1) * i / N
        z = th * i
        d = 1.6 - 0.08 * i
        mi = (lime_l, lime_l, lime, lime_l, lime, lime, lime_d, lime, lime_d)[i]
        rings = [inset_rect(s - 0.5, s - 0.5, d, z), inset_rect(s - 0.5, s - 0.5, d, z + 0.9),
                 inset_rect(s, s, d, z + 0.95), inset_rect(s, s, d, z + 1.05), inset_rect(s - 0.35, s - 0.35, d, z + th)]
        b.loft_rect(mi, rings)
        # 裙板下緣陰影線
        b.loft_rect(dark, [inset_rect(s - 0.45, s - 0.45, d, z + 0.86), inset_rect(s - 0.45, s - 0.45, d, z + 0.92)], cap_top=False)
    # 頂台
    b.box_base(lime_d, (2 * S1 - 1.2, 2 * S1 - 3.0, 1.2), (0.6, 0, ZT))

    # ---------------- 西面大階梯（含兩側邊牆）
    X0, X1 = -S0 - 9.0, -S1 + 0.3
    W = 10.0
    nst = 80
    for k in range(nst):
        t0 = k / nst
        x = X0 + (X1 - X0) * t0
        z = ZT * (k + 1) / nst
        b.box_base(rubble if k % 7 else lime, ((X1 - X0) / nst + 0.5, W, ZT / nst + 0.02), (x + 0.25, 0, z - ZT / nst))
    # 階梯下方實體（斜面楔形）
    prof = [(X0, 0.0), (X1, 0.0), (X1, ZT), (X1 - 0.3, ZT)]
    b.profile_wall(lime, [(p[0], p[1]) for p in prof], W - 0.2, Matrix.Identity(4))
    for s in (-1, 1):
        b.profile_wall(lime, [(X0 - 0.4, 0.0), (X1, 0.0), (X1, ZT + 0.3), (X1 - 0.5, ZT + 0.3)], 0.9,
                       Matrix.Translation((0, s * (W / 2 + 0.45), 0)))
    # 階梯底的低台
    b.box_base(lime_l, (4.0, W + 6.0, 1.2), (X0 - 1.0, 0, 0))

    # ---------------- 頂上神廟＋屋頂冠
    ZB = ZT + 1.2
    TX, TY, TH = 10.0, 12.5, 5.0
    tx0 = 1.2
    b.box_base(plaster, (TX, TY, TH), (tx0, 0, ZB))
    b.box_base(lime, (TX + 0.6, TY + 0.6, 0.5), (tx0, 0, ZB + TH - 0.1))
    b.box_base(dark, (0.4, 1.4, 2.4), (tx0 - TX / 2 - 0.05, 0, ZB + 0.2))
    for s in (-1, 1):
        b.box_base(lime, (0.6, 0.25, 2.6), (tx0 - TX / 2 - 0.1, s * 0.85, ZB + 0.1))
    # 屋頂冠：階梯狀後退、上窄
    zc = ZB + TH + 0.4
    for k, (w, d, h, off) in enumerate(((8.0, 11.6, 3.0, 1.4), (7.2, 10.4, 3.0, 1.9), (6.2, 9.2, 2.8, 2.4), (5.0, 7.8, 2.6, 2.8))):
        b.rock(lime_d, (w, d, h), (tx0 + off, 0, zc + h / 2), rough=0.08, subdiv=2, seed=k * 7 + 1, round_=0.05)
        zc += h * 0.95
    b.box_base(lime_d, (TX - 0.4, TY - 0.6, 0.6), (tx0, 0, ZB + TH + 0.3))

    # ---------------- 石碑、祭壇、茅草棚
    for k in range(7):
        y = -16.0 + k * 5.3
        x = -32.0
        if abs(y) < 7:
            continue
        b.rock(lime_d, (0.9, 0.5, 2.6), (x, y, 0.0), rough=0.06, subdiv=2, seed=k, round_=0.15)
        b.lathe(lime, [(0, 0), (0.75, 0), (0.75, 0.55), (0, 0.55)], (x - 1.6, y, 0), seg=14)
    hx, hy = -26.0, -22.0
    for (dx, dy) in ((-1.4, -1.0), (1.4, -1.0), (-1.4, 1.0), (1.4, 1.0)):
        b.cyl(wood, 0.06, 0.06, 2.2, (hx + dx, hy + dy, 0), seg=6)
    b.tri_prism(thatch, 3.6, 3.0, 1.5, (hx, hy, 2.0))

    # ---------------- 熱帶樹林（兩側與後方）
    rng = b.rng
    spots = []
    for _ in range(140):
        a = rng.uniform(0, TAU)
        r = rng.uniform(26.0, 70.0)
        x, y = r * math.cos(a), r * math.sin(a)
        if (x < 10 and abs(y) < 50) or (y > 18 and x < 26):
            continue  # 西側、南側廣場空地
        if abs(x + 15) > 74 or abs(y) > 74:
            continue
        if any((x - px) ** 2 + (y - py) ** 2 < 70 for px, py in spots):
            continue
        spots.append((x, y))
    for x, y in spots[:40]:
        h = rng.uniform(16, 26)
        b.broadleaf(x, y, 0.0, h, (lf_light, lf_broad) if rng.random() < 0.6 else (lf_broad, lf_dark), core_b, bark,
                    R=h * 0.38, n_blobs=6, cap=55)

    b.export_glb(path)
