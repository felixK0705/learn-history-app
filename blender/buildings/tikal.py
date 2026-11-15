"""tikal 蒂卡爾一號神廟（大美洲豹神廟，約西元 732 年）寫實模型（公尺；+X 東、+Y 北）

- 金字塔 9 層階台，台基約 35 × 32 m、頂台高約 33 m；每層為「斜面裙壁＋外凸線腳」，四角內凹（inset corners），
  側面陡峭（約 70°）
- 西面中央一道陡梯（寬約 10 m，現況多為崩落的碎石坡，僅底段可見階級）自大廣場直達頂台
- 頂上神廟：三室、西向門洞，立於約 1.6 m 的小台上；其上為高大的屋頂冠（roof comb），兩段收分、頂部殘缺，
  總高約 47 m
- 石材為灰白石灰岩，帶垂直黑色風化流痕、局部長苔；周圍為大廣場草地、石碑與祭壇、熱帶闊葉樹
"""

import math
import os

import numpy as np
from mathutils import Matrix, Vector, noise

from lib import TAU, TEX
from buildings.kinkakuji import GEN, AsiaBuilder, _cloud, _height_to_normal, _save_maps, gen_canopy, gen_leaves

# (目標點, 方位角, 仰角, 距離, 焦距)：參考照自大廣場西南側仰望：西面（大階梯、神廟門洞）居左、南面在右側斜伸
CAMERA = ((-2.0, 0.0, 20.0), 236.0, -16.0, 66.0, 27)


# ====================================================================== 程式貼圖
def gen_limestone(name, light, dark, moss, seed=3, streak=0.55, moss_amt=0.25, size=1024):
    """灰白石灰岩砌塊：以 large_sandstone_blocks 的明暗為底，加垂直黑色風化流痕與苔斑（u 水平、v 垂直）"""
    out = os.path.join(GEN, f"tikal_{name}")
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return out
    from PIL import Image

    N = 1024
    rng = np.random.default_rng(seed)
    src = Image.open(os.path.join(TEX, "large_sandstone_blocks", "diff.jpg")).convert("L").resize((N, N))
    g = np.asarray(src, dtype=float) / 255.0
    g = (g - g.mean()) / (g.std() + 1e-6)
    # 垂直流痕：沿 u 變化快、沿 v 很慢的雜訊（無縫：以小陣列平鋪縮放）
    small = rng.normal(0, 1, size=(5, 28))
    small = np.tile(small, (3, 3))
    im = Image.fromarray(((small - small.min()) / np.ptp(small) * 255).astype(np.uint8)).resize((N * 3, N * 3), Image.Resampling.BICUBIC)
    st = np.asarray(im, dtype=float)[N:2 * N, N:2 * N] / 255.0
    st = np.clip((st - 0.5) * 2.5, 0, 1)
    blot = _cloud(rng, N, 256, 1.6) + _cloud(rng, N, 48, 0.8) + 0.15
    dk = np.clip(st * streak * 0.6 + np.clip(blot * 1.3, 0, 1) * 0.75, 0, 1)
    mo = np.clip((_cloud(rng, N, 96, 1.0) + _cloud(rng, N, 16, 0.5) - (0.62 - moss_amt)) * 2.0, 0, 0.7)
    L, D, M = (np.array(c, float)[None, None] for c in (light, dark, moss))
    base = L * (1 - dk[..., None]) + D * dk[..., None]
    base = base * (1 - 0.65 * mo[..., None]) + M * 0.65 * mo[..., None]
    base = base * (1 + 0.2 * g[..., None] + _cloud(rng, N, 4, 0.12)[..., None])
    nor = _height_to_normal(g * 1.4 + _cloud(rng, N, 4, 0.6), 1.0)
    _save_maps(out, base, nor, size=size)
    return out


def inset_rect(sx, sy, d, z):
    """四角內凹的矩形環（逆時針，12 點）"""
    pts = []
    for (qx, qy) in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        quad = [(sx, sy - d), (sx - d, sy - d), (sx - d, sy)]
        if qx * qy < 0:
            quad = list(reversed(quad))
        pts += [(qx * x, qy * y, z) for x, y in quad]
    # 依角度排序成逆時針
    pts.sort(key=lambda p: math.atan2(p[1], p[0]))
    return pts


class MayaBuilder(AsiaBuilder):
    def loft(self, rings, mats, cap_bottom=True, cap_top=None):
        vr = [[self.V(p) for p in r] for r in rings]
        if cap_bottom:
            self.face(list(reversed(vr[0])), mats[0])
        for k, (a, c) in enumerate(zip(vr, vr[1:])):
            n = len(a)
            for i in range(n):
                j = (i + 1) % n
                self.face([a[i], a[j], c[j], c[i]], mats[min(k, len(mats) - 1)])
        if cap_top is not None:
            self.face(vr[-1], cap_top)
        return vr

    def block(self, mi, x0, x1, y0, y1, z0, z1, top=None):
        vs = [self.V(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                  (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        for f in ((0, 3, 2, 1), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.face([vs[i] for i in f], mi)
        self.face([vs[i] for i in (4, 5, 6, 7)], top if top is not None else mi)


def jungle_tree(b, x, y, h, mats, core, bark):
    """熱帶闊葉樹：細高樹幹、上部分枝，傘狀不規則扁平樹冠（數個扁平團塊）"""
    rng = b.rng
    zc = h * rng.uniform(0.5, 0.6)
    top = (x + rng.uniform(-1, 1), y + rng.uniform(-1, 1), zc)
    b.tube([(x, y, -0.3), (x + rng.uniform(-0.4, 0.4), y + rng.uniform(-0.4, 0.4), zc * 0.5), top], max(0.25, h * 0.025), 0.15, bark, seg=7)
    W = h * rng.uniform(0.38, 0.48)
    n = rng.randint(4, 6)
    for k in range(n):
        a = TAU * k / n + rng.uniform(-0.4, 0.4)
        rr = W * rng.uniform(0.35, 0.7)
        ex, ey, ez = top[0] + rr * math.cos(a), top[1] + rr * math.sin(a), zc + rng.uniform(0.5, 2.5)
        b.tube([top, ((top[0] + ex) / 2, (top[1] + ey) / 2, (zc + ez) / 2 - 0.3), (ex, ey, ez)], 0.16, 0.06, bark, seg=5, cap=False)
        br = W * rng.uniform(0.38, 0.55)
        b.crown(ex, ey, ez + br * 0.25, br, br * 0.72, mats, core, min(1.1, br * 0.45), cap=50)
    br = W * 0.5
    b.crown(top[0], top[1], zc + h * 0.2, br, br * 0.75, mats, core, min(1.1, br * 0.45), cap=50)


def tikal(path):
    b = MayaBuilder("Tikal", seed=5)
    rng = b.rng
    lime = b.gtex("lime", gen_limestone("lime7", (212, 202, 178), (34, 33, 30), (92, 104, 58), seed=3, streak=0.6, moss_amt=0.2),
                  tile=7.0, rough=0.9, normal=1.0)
    lime_d = b.gtex("lime_dark", gen_limestone("lime_d7", (170, 162, 142), (26, 26, 24), (78, 92, 50), seed=8, streak=0.85, moss_amt=0.3),
                    tile=7.0, rough=0.9, normal=1.0)
    lime_l = b.gtex("lime_light", gen_limestone("lime_l7", (228, 216, 190), (52, 50, 44), (110, 118, 70), seed=11, streak=0.4, moss_amt=0.12),
                    tile=7.0, rough=0.9, normal=1.0)
    lime_m = b.gtex("lime_mould", gen_limestone("lime_m7s", (150, 144, 128), (40, 39, 35), (90, 90, 80), seed=14, streak=0.5, moss_amt=-0.5, size=512),
                    tile=7.0, rough=0.9, normal=1.0)
    stair = b.gtex("stair", gen_limestone("stair7s", (120, 116, 104), (30, 29, 26), (70, 80, 46), seed=17, streak=0.4, moss_amt=0.1, size=512),
                   tile=5.0, rough=0.9, normal=1.0)
    rubble = b.ptex("rubble", "medieval_blocks_02", tile=2.4, tint="#77746a", rough=0.92, normal=1.2)
    ledge = b.ptex("ledge", "gray_rocks", tile=3.0, tint="#59574d", rough=0.95, normal=0.6)  # 階台頂面（風化碎石與苔）
    dark = b.color("void", "#100e0c", rough=1.0)
    grass = b.ptex("grass", "grass_ground", tile=2.5, tint="#74a536", rough=0.95, normal=0.5)
    soil = b.color("soil", "#5b4a36", rough=1.0)
    thatch = b.ptex("thatch", "grass_ground", tile=1.5, tint="#9a8256", rough=1.0, normal=0.6)
    wood = b.color("wood", "#5a4430", rough=0.9)
    lf_broad = b.alpha_mat("leaf_broad", gen_leaves("broad"))
    lf_light = b.alpha_mat("leaf_light", gen_leaves("light"))
    lf_dark = b.alpha_mat("leaf_dark", gen_leaves("dark"))
    core_b = b.gtex("core_broad", gen_canopy("broad", (84, 120, 44), seed=5), tile=3.0, rough=0.9, normal=1.0)
    bark = b.color("bark", "#77705f", rough=0.9)

    # ---------------- 廣場地面
    b.block(soil, -90, 60, -75, 75, -2.6, -0.02, top=grass)

    # ---------------- 金字塔 9 層（西面朝 -X）
    N = 9
    ZT = 33.0
    th = ZT / N
    SX0, SY0 = 17.5, 16.0    # 台基半寬（東西、南北）
    SX1, SY1 = 7.2, 7.6      # 頂台半寬
    stone_seq = (lime_l, lime, lime_l, lime, lime_d, lime, lime_d, lime_d, lime)
    for i in range(N):
        t = i / N
        sx, sy = SX0 + (SX1 - SX0) * t, SY0 + (SY1 - SY0) * t
        nx, ny = SX0 + (SX1 - SX0) * (i + 1) / N, SY0 + (SY1 - SY0) * (i + 1) / N
        z = th * i
        d = 1.5 - 0.07 * i          # 內凹角深度
        bat = (sx - nx) * 0.55      # 斜面收分
        mi = stone_seq[i]
        r0 = inset_rect(sx, sy, d, z)
        r1 = inset_rect(sx - bat, sy - bat, d, z + th * 0.62)
        r2 = inset_rect(sx - bat + 0.25, sy - bat + 0.25, d, z + th * 0.64)   # 外凸線腳
        r3 = inset_rect(sx - bat + 0.25, sy - bat + 0.25, d, z + th * 0.74)
        r4 = inset_rect(sx - bat - 0.05, sy - bat - 0.05, d, z + th * 0.76)
        r5 = inset_rect(sx - bat - 0.25, sy - bat - 0.25, d, z + th)
        b.loft([r0, r1, r2, r3, r4, r5], [mi, lime_m, lime_m, lime_d, lime_d], cap_bottom=(i == 0), cap_top=ledge)
    # 頂台
    b.block(lime_d, -SX1 + 0.4, SX1 - 0.4, -SY1 + 0.4, SY1 - 0.4, ZT - 0.2, ZT + 0.5, top=ledge)

    # ---------------- 西面大階梯：底段可見階級，上段為崩落碎石坡
    W = 10.4
    XB, XT = -SX0 - 3.2, -SX1 + 0.6     # 梯腳、梯頂（x）
    nst = 70
    rise = (ZT + 0.5) / nst
    run = (XT - XB) / nst
    prof = [(XB, 0.0)]
    for k in range(nst):
        x = XB + run * k
        zz = rise * (k + 1)
        prof += [(x, zz), (x + run, zz)]
    prof += [(XT + 2.0, ZT + 0.5), (XT + 2.0, 0.0)]
    # 階梯本體（剖面沿 X–Z，向 Y 擠出）：底段 14 階用淺色石材，其上為碎石
    M = Matrix.Identity(4)
    b.profile_wall(rubble, prof, W, M)
    for k in range(nst):
        x = XB + run * k
        b.block(lime_l if k < 6 else stair, x - 0.02, x + run + 0.02, -W / 2 + 0.3, W / 2 - 0.3, rise * k, rise * (k + 1) + 0.01)
    # 兩側邊牆（梯側石框），斜面
    for s in (-1, 1):
        y0 = s * (W / 2 + 0.6)
        b.profile_wall(lime_d, [(XB - 0.3, 0.0), (XT + 1.0, 0.0), (XT + 1.0, ZT + 0.8), (XT - 0.4, ZT + 0.8)], 1.2,
                       Matrix.Translation((0, y0, 0)))
    # 碎石坡上的散石
    for _ in range(10):
        k = rng.uniform(0.25, 0.95)
        x = XB + (XT - XB) * k + rng.uniform(-0.4, 0.4)
        z = (ZT + 0.5) * k
        y = rng.uniform(-W / 2 + 0.8, W / 2 - 0.8)
        s = rng.uniform(0.5, 1.2)
        b.rock(lime_d, (s * 1.3, s, s * 0.6), (x - 0.3, y, z - 0.2), rot=(0, 0, rng.uniform(0, TAU)), seed=rng.randint(0, 999), round_=0.3, rough=0.15)
    # 梯腳低台
    b.block(lime_l, XB - 3.0, XB + 0.2, -W / 2 - 3.0, W / 2 + 3.0, 0.0, 0.9, top=ledge)

    # ---------------- 頂上神廟＋屋頂冠
    ZB = ZT + 0.5
    # 神廟小台（稍內凹的兩段）
    b.block(lime, -6.0, 5.8, -6.8, 6.8, ZB, ZB + 0.9)
    b.block(lime_d, -5.7, 5.5, -6.5, 6.5, ZB + 0.9, ZB + 1.6)
    Z0 = ZB + 1.6
    TX0, TX1, TY = -5.0, 5.0, 6.0     # 神廟（東西深 9.2、南北寬 10.4）
    ZW = Z0 + 4.4                    # 牆頂
    b.block(lime_l, TX0, TX1, -TY, TY, Z0, ZW)
    # 上部斜面簷帶（mansard）
    b.loft([[(TX0 - 0.15, -TY - 0.15, ZW), (TX1 + 0.15, -TY - 0.15, ZW), (TX1 + 0.15, TY + 0.15, ZW), (TX0 - 0.15, TY + 0.15, ZW)],
            [(TX0 - 0.15, -TY - 0.15, ZW + 0.35), (TX1 + 0.15, -TY - 0.15, ZW + 0.35), (TX1 + 0.15, TY + 0.15, ZW + 0.35), (TX0 - 0.15, TY + 0.15, ZW + 0.35)],
            [(TX0 + 0.35, -TY + 0.35, ZW + 2.0), (TX1 - 0.35, -TY + 0.35, ZW + 2.0), (TX1 - 0.35, TY - 0.35, ZW + 2.0), (TX0 + 0.35, TY - 0.35, ZW + 2.0)]],
           [lime, lime_d], cap_bottom=False, cap_top=lime_d)
    # 西向門洞（凹入、暗）＋木門楣
    b.block(dark, TX0 - 0.03, TX0 + 0.9, -0.75, 0.75, Z0, Z0 + 2.5)
    b.block(wood, TX0 - 0.06, TX0 + 0.3, -0.95, 0.95, Z0 + 2.5, Z0 + 2.75)
    # 屋頂冠：坐在神廟後半（東側），兩段收分，表面粗糙、頂部殘缺
    ZC = ZW + 2.0
    cx0, cx1 = -0.8, 4.2
    b.block(lime_d, cx0, cx1, -5.2, 5.2, ZC, ZC + 4.6)
    b.block(lime_d, cx0 + 0.35, cx1 - 0.35, -4.4, 4.4, ZC + 4.6, ZC + 4.9)
    b.block(lime, cx0 + 0.55, cx1 - 0.45, -4.0, 4.0, ZC + 4.9, ZC + 9.0)
    # 殘缺頂緣與表面凹凸（散布的突出石塊，象徵已剝落的灰泥雕飾）
    for k in range(9):
        y = -3.0 + 6.0 * k / 8
        h = rng.uniform(0.3, 1.1)
        b.rock(lime_d, (2.6, 0.9, h * 1.2), (cx0 + 2.0, y, ZC + 8.9 + h * 0.3), seed=rng.randint(0, 999), round_=0.15, rough=0.12)
    for side in (-1, 1):
        for _ in range(10):
            y = rng.uniform(-4.2, 4.2) if side else 0
            z = rng.uniform(ZC + 0.4, ZC + 7.5)
            hy = 4.5 if z < ZC + 4.6 else 3.4
            yy = rng.uniform(-hy + 0.5, hy - 0.5)
            b.rock(lime, (0.25, rng.uniform(0.6, 1.4), rng.uniform(0.4, 0.9)), (cx0 + 0.02 if side < 0 else cx1 - 0.02, yy, z),
                   seed=rng.randint(0, 999), round_=0.2, rough=0.1)

    # ---------------- 石碑、祭壇、茅草棚（大廣場北側一列）
    for k in range(9):
        y = 22.0 - k * 5.5
        x = -36.0
        if abs(y) < 9:
            continue
        b.rock(lime_d, (0.9, 0.55, rng.uniform(2.0, 2.8)), (x, y, 0.0), rough=0.06, subdiv=2, seed=k, round_=0.15)
        b.lathe(lime, [(0, 0), (0.8, 0), (0.8, 0.55), (0, 0.55)], (x - 1.7, y, 0), seg=14)
    hx, hy = -31.0, -19.0
    for (dx, dy) in ((-1.4, -1.0), (1.4, -1.0), (-1.4, 1.0), (1.4, 1.0)):
        b.lathe(wood, [(0, 0), (0.07, 0), (0.06, 2.2), (0, 2.2)], (hx + dx, hy + dy, 0), seg=6)
    b.tri_prism(thatch, 3.8, 3.4, 1.6, (hx, hy, 2.0))

    # ---------------- 熱帶樹林（南、東、北側；西側為大廣場空地）
    spots = []
    for _ in range(400):
        x, y = rng.uniform(-88, 58), rng.uniform(-73, 73)
        if x < -24 and abs(y) < 50 or (x < 0 and y > 0):
            continue  # 大廣場
        if abs(x) < 26 and abs(y) < 24:
            continue  # 金字塔
        if any((x - px) ** 2 + (y - py) ** 2 < 80 for px, py in spots):
            continue
        spots.append((x, y))
    for x, y in spots[:46]:
        h = rng.uniform(15, 26)
        for _ in range(3):  # 林下灌叢
            ux, uy = x + rng.uniform(-6, 6), y + rng.uniform(-6, 6)
            if ux < -24 and abs(uy) < 50 or (abs(ux) < 25 and abs(uy) < 23):
                continue
            rr = rng.uniform(2.5, 4.5)
            b.crown(ux, uy, rr * 0.4, rr, rr * 0.5, (lf_broad, lf_dark), core_b, 1.0, cap=40)
        jungle_tree(b, x, y, h, (lf_light, lf_broad) if rng.random() < 0.6 else (lf_broad, lf_dark), core_b, bark)

    b.export_glb(path)
