"""rushmore 拉什莫爾山國家紀念公園寫實模型（公尺；崖面朝向 -Y）

南達科他州黑山的花崗岩峭壁上刻四位總統頭像（各高約 18 m）：由左至右為華盛頓、傑佛遜、老羅斯福、林肯。
頭像由山岩直接雕出（後方與山體相連），下方為開鑿時堆積的碎石坡，坡上散生西黃松。

建模方式：
- 頭像以隱函數（SDF：橢球、膠囊的平滑聯集／差集）雕出顱骨、眉骨、眼窩、鼻、唇、下巴、頭髮等，
  再由正面投射成深度圖，與岩壁深度以平滑最小值融合 → 臉自山岩「長出來」。
- 岩壁為正面高度場：未開鑿處以 Worley 胞元做出圓鈍的花崗岩節理塊與裂縫，開鑿面較平整。
- 正面貼圖為整面烘焙的 4K 圖（花崗岩紋理＋裂紋＋髒污垂流＋地衣＋片岩帶＋凹處陰影）。
"""

import ast
import math
import os

import numpy as np
from mathutils import Vector, noise

from lib import TAU, TEX, Builder
from buildings.sphinx import (FACE_DEFAULT, SDF, blur, face_head, fbm, surface_nets, gray_tex, grid3, img_mat, mesh_object, normal_from_height,
                              save_img, smax, smin, tile_sample, worley)

# 目標點、方位角、仰角、距離、焦距（對應參考照：自下方觀景步道正面仰望）
CAMERA = ((-2.0, 0.0, 42.0), 0.0, -3.0, 250.0, 88.0)
if os.environ.get("TL_CAM"):  # 開發用：覆寫預覽相機
    CAMERA = ast.literal_eval(os.environ["TL_CAM"])

GEN = os.path.join(TEX, "_gen", "rushmore")

# 頭像：(種類, 局部原點=下巴底下耳朵平面中點 (x, y, z), 頭高 H, 偏航, 俯仰)
HEADS = [
    ("w", (-23.0, -3.4, 50.0), 20.0, -0.10, 0.02),
    ("j", (-9.3, 1.4, 44.0), 18.5, 0.40, -0.06),
    ("r", (3.8, 6.0, 33.0), 18.0, 0.10, 0.0),
    ("l", (20.5, 2.6, 32.5), 19.0, -0.16, 0.0),
]


# ---------------------------------------------------------------- 頭像 SDF（局部單位：頭高 = 1，下巴底 z=0、頭頂 z=1，臉朝 -y）
def head_params(kind):
    P = dict(FACE_DEFAULT)
    P["cranium"] = ((0, 0.13, 0.54), (0.37, 0.42, 0.36))
    if kind == "w":
        P["cranium"] = ((0, 0.12, 0.54), (0.39, 0.43, 0.36))
        P["wf"] = [(z, w * 1.08) for z, w in P["wf"]]
        P["brow"] = 0.04
    elif kind == "j":
        P["wf"] = [(z, w * 0.98) for z, w in P["wf"]]
        P["nose"] = (0.095, 0.35, 0.04, 0.066, 0.072)
        P["mouth"] = (0.22, 0.1, 0.035)
    elif kind == "r":
        P["wf"] = [(z, w * 1.06) for z, w in P["wf"]]
        P["mouth"] = (0.2, 0.1, 0.03)
        P["lips"] = (0.0, 0.03)
    elif kind == "l":
        P["wf"] = [(z, w * (1.0 + 0.15 * max(0, 0.25 - z) / 0.25)) for z, w in P["wf"]]
        P["brow"] = 0.05
        P["eye"] = (0.13, 0.495, 0.1, 0.07)
        P["prof"] = [(z, dd + (0.03 if z < 0.16 else 0.0)) for z, dd in P["prof"]]
    return P


def head_sdf(S, kind):
    """拉什莫爾頭像（局部單位：頭高 = 1，下巴底 z=0、頭頂 z=1，臉朝 -y）"""
    # 縱向壓縮 0.9：臉部五官相對位置上移、頭頂較低（由下往上仰望時的比例）
    S = SDF(S.X, S.Y, S.Z * 0.9)
    X, Y, Z = S.X, S.Y, S.Z
    P = head_params(kind)
    d = face_head(S, P)
    e, c = S.ell, S.cap
    if kind == "w":
        # 華盛頓：高額、後梳頭髮在耳上捲成髮捲；領巾
        for sx in (-1, 1):
            d = smin(d, e((sx * 0.35, 0.1, 0.55), (0.075, 0.15, 0.11)), 0.03)
            d = smin(d, e((sx * 0.345, 0.14, 0.42), (0.07, 0.13, 0.095)), 0.03)
        d = smin(d, e((0, -0.16, -0.06), (0.22, 0.2, 0.1)), 0.06)
    elif kind == "j":
        # 傑佛遜：兩側與腦後蓬起的波浪髮
        hair = e((0, 0.12, 0.64), (0.37, 0.44, 0.4))
        for sx in (-1, 1):
            hair = smin(hair, e((sx * 0.32, 0.12, 0.56), (0.09, 0.3, 0.22)), 0.05)
        hair = hair + 0.012 * np.sin(Z * 40 + 3 * np.sin(Y * 14))
        d = smin(d, smax(hair, -Y - 0.28, 0.03), 0.03)
    elif kind == "r":
        # 老羅斯福：濃密八字鬍、眼鏡（細框與鼻樑架）
        mus = e((0, -0.455, 0.262), (0.135, 0.06, 0.04))
        for sx in (-1, 1):
            mus = smin(mus, e((sx * 0.11, -0.43, 0.24), (0.055, 0.05, 0.035)), 0.02)
        mus = mus + 0.004 * np.sin(X * 120)
        d = smin(d, mus, 0.015)
        d = smin(d, c((-0.05, -0.43, 0.505), (0.05, -0.43, 0.505), 0.01), 0.008)
        d = smin(d, e((0, 0.12, 0.66), (0.36, 0.42, 0.37)), 0.04)
    elif kind == "l":
        # 林肯：凹頰、下巴鬍（無八字鬍）、頭頂連著未修整的岩塊
        for sx in (-1, 1):
            d = smax(d, -e((sx * 0.2, -0.42, 0.33), (0.07, 0.08, 0.09)), 0.04)
        beard = e((0, -0.36, 0.08), (0.16, 0.13, 0.12))
        for sx in (-1, 1):
            beard = smin(beard, c((sx * 0.25, -0.15, 0.2), (sx * 0.07, -0.38, 0.03), 0.055), 0.05)
        beard = smax(beard, Z - 0.19, 0.03)
        beard = beard + 0.006 * np.sin(X * 70 + 2 * np.sin(Z * 30)) * np.sin(Z * 55)
        d = smin(d, beard, 0.025)
        d = smin(d, e((0.3, 0.12, 0.62), (0.12, 0.35, 0.22)), 0.05)  # 右側髮量
    # 石面粗糙度
    d = d + 0.003 * fbm(X * 14, Y * 14, Z * 14, 3, seed={"w": 1, "j": 2, "r": 3, "l": 4}[kind])
    return d


def head_depth(kind, C, H, yaw, pitch, step=0.12, coarse=0.45):
    """將頭像 SDF 由正面（-y → +y）投射成深度圖：回傳 (xs, zs, ymap)；未擊中為 +inf。
    先以粗網格找出表面大致位置，再於每欄前後小範圍內細取樣。"""
    R = SDF.rot(yaw, pitch)
    corners = np.array([[x, y, z] for x in (-0.48, 0.48) for y in (-0.62, 0.62) for z in (-0.42, 1.06)]) * H
    W = corners @ R.T + np.asarray(C)
    lo, hi = W.min(0), W.max(0)
    S, o = grid3(lo, hi, coarse)
    dc = head_sdf(S.local(C, R, H), kind) * H
    ins = dc < coarse * 0.7
    hitc = ins.any(1)
    yc = np.where(hitc, o[1] + np.argmax(ins, 1) * coarse, np.inf)
    xs = np.arange(lo[0], hi[0], step)
    zs = np.arange(lo[2], hi[2], step)
    # 細網格每欄的搜尋起點：鄰近粗格中最靠前者
    ci = np.clip(np.round((xs - o[0]) / coarse).astype(int), 0, yc.shape[0] - 1)
    cj = np.clip(np.round((zs - o[2]) / coarse).astype(int), 0, yc.shape[1] - 1)
    ycm = yc.copy()
    for di in (-1, 1):
        ycm = np.minimum(ycm, np.roll(yc, di, 0))
        ycm = np.minimum(ycm, np.roll(yc, di, 1))
    y0 = ycm[ci][:, cj] - coarse * 1.6
    fin = np.isfinite(y0)
    y0f = np.where(fin, y0, 0.0)
    Lc = SDF.rot(yaw, pitch)

    def search(ystart, xs_, zs_, K, dy):
        n = len(ystart)
        X = np.repeat(xs_[:, None], K, 1).astype(np.float32)
        Z = np.repeat(zs_[:, None], K, 1).astype(np.float32)
        Y = (ystart[:, None] + np.arange(K)[None, :] * dy).astype(np.float32)
        d = head_sdf(SDF(X, Y, Z).local(C, Lc, H), kind) * H
        inside = d < 0
        k = np.argmax(inside, 1)
        ok = inside.any(1) & (k > 0)
        k1 = np.maximum(k - 1, 0)
        r_ = np.arange(n)
        d0, d1 = d[r_, k1], d[r_, k]
        t = np.clip(d0 / np.maximum(d0 - d1, 1e-6), 0, 1)
        return np.where(ok, ystart + (k1 + t) * dy, np.inf)

    XX, ZZ = np.meshgrid(xs, zs, indexing="ij")
    y = np.full(XX.shape, np.inf)
    m = fin
    y[m] = search(y0f[m], XX[m], ZZ[m], int(coarse * 4.0 / 0.08), 0.08)
    # 第一輪沒找到（陡坡處）→ 加長搜尋範圍
    m2 = fin & ~np.isfinite(y)
    if m2.any():
        y[m2] = search(y0f[m2], XX[m2], ZZ[m2], 140, 0.08)
    return xs, zs, y


def sample_map(m, X, Z):
    xs, zs, Y = m
    fx = (X - xs[0]) / (xs[1] - xs[0])
    fz = (Z - zs[0]) / (zs[1] - zs[0])
    ok = (fx >= 0) & (fx <= len(xs) - 1.001) & (fz >= 0) & (fz <= len(zs) - 1.001)
    ix = np.clip(np.floor(fx).astype(int), 0, len(xs) - 2)
    iz = np.clip(np.floor(fz).astype(int), 0, len(zs) - 2)
    tx, tz = np.clip(fx - ix, 0, 1), np.clip(fz - iz, 0, 1)
    a, b2, c2, d2 = Y[ix, iz], Y[ix + 1, iz], Y[ix, iz + 1], Y[ix + 1, iz + 1]
    fin = np.isfinite(a) & np.isfinite(b2) & np.isfinite(c2) & np.isfinite(d2)
    a, b2, c2, d2 = (np.where(np.isfinite(q), q, 60.0) for q in (a, b2, c2, d2))
    v = (a * (1 - tx) + b2 * tx) * (1 - tz) + (c2 * (1 - tx) + d2 * tx) * tz
    return np.where(ok & fin, v, np.inf)


# ---------------------------------------------------------------- 岩壁
TOP = [(-112, 22), (-96, 52), (-82, 78), (-70, 85), (-58, 82), (-48, 73), (-40, 63), (-33, 60), (-20, 56), (-12, 56),
       (-4, 54), (3, 52), (8, 48.5), (13, 48.5), (16, 55), (20, 58), (28, 58.5), (35, 61), (42, 66), (52, 69), (62, 64),
       (75, 56), (92, 42), (112, 22)]


def cliff_top(x):
    tx, tz = zip(*TOP)
    return np.interp(x, tx, tz) + 2.0 * fbm(x * 0.08, 3.3, None, 3, seed=5)


def foot_z(x):
    return 10.0 + 11.5 * np.exp(-((x - 6) / 26.0) ** 2) + 2.5 * fbm(x * 0.03, 1.1, None, 3, seed=6) - 0.0006 * x * x


def carved_mask(X, Z):
    """開鑿範圍（0..1）"""
    n = 4.0 * fbm(X * 0.05, Z * 0.05, None, 3, seed=8)
    dx = np.maximum(0, np.abs(X + 4.0) - 39.0 + n)
    dz = np.maximum(0, 27.0 - Z + n * 0.6)
    return np.clip(1.0 - np.sqrt(dx * dx + dz * dz) / 3.0, 0, 1)


def gauss(X, Z, x0, z0, sx, sz):
    return np.exp(-(((X - x0) / sx) ** 2 + ((Z - z0) / sz) ** 2))


def joints(X, Z):
    """花崗岩節理：回傳 (塊體隆起量, 大裂縫, 小裂縫)；座標加上擾動讓裂縫不規則"""
    wx = X + 3.5 * fbm(X * 0.05, Z * 0.05, None, 3, seed=31)
    wz = Z + 3.5 * fbm(X * 0.05 + 9, Z * 0.05, None, 3, seed=32)
    f1, f2 = worley(wx / 11.0, wz / 17.0, seed=3)
    g1, g2 = worley(wx / 5.0 + 7.3, wz / 8.0, seed=4)
    pillow = 3.2 * (f1 ** 1.5 - 0.4) + 0.8 * (g1 - 0.55)
    big = np.exp(-((f2 - f1) / 0.045) ** 2)
    small = np.exp(-((g2 - g1) / 0.035) ** 2)
    return pillow, big, small


def rock_y(X, Z, J=None):
    """未含頭像的岩壁深度 y(x, z)"""
    cm = carved_mask(X, Z)
    y = -4.0 + 0.07 * (Z - 25.0)
    # 左、右兩側巨大的未開鑿岩體向前凸出
    y -= 4.0 * gauss(X, Z, -68, 60, 22, 30) + 3.0 * gauss(X, Z, 52, 50, 16, 26)
    # 華盛頓衣領與肩部（向前隆起的開鑿斜面）：數個平面取平滑最大值做出刀削的面
    P1 = -10.5 + 0.10 * (X + 22) + 0.10 * (38 - Z)
    P2 = -10.5 - 0.30 * (X + 22) + 0.12 * (38 - Z)
    P3 = -10.5 + 0.42 * (X + 22)
    P4 = -10.5 + 0.40 * (Z - 40)
    coat = smax(smax(P1, P2, 1.5), smax(P3, P4, 1.5), 1.5)
    # 衣領翻折的刀削面（右下斜面與左側台階）
    P5 = -10.0 + 0.9 * ((X + 14) * 0.6 - (Z - 40) * 0.8)
    P6 = -9.0 + 0.6 * (-(X + 30) * 0.7 - (Z - 43) * 0.7)
    coat = smax(coat, smin(P5, P6, 0.6) * 0 + np.maximum(P5, -40), 0.4) * 0.5 + smax(coat, P5, 0.4) * 0.5
    coat = coat + 6.0 * np.clip((31 - Z) / 6, 0, 1) ** 2 + 3.0 * np.clip((X + 2) / 6, 0, 1)
    y = smin(y, coat, 2.5)
    # 傑佛遜、羅斯福後方的凹入開鑿面；羅斯福與林肯之間的深槽
    y += 5.0 * gauss(X, Z, -4, 50, 10, 9) + 6.5 * gauss(X, Z, 5, 44, 8, 9) + 5.5 * gauss(X, Z, 11.5, 42, 2.6, 8)
    # 林肯頭部右側的開鑿平台與鬍子下方的岩階
    y -= 2.5 * gauss(X, Z, 31, 40, 6, 10)
    y -= 2.0 * gauss(X, Z, 19, 26, 12, 6)
    # 下段崖面（片岩帶附近）較陡且前突
    y -= 3.0 * np.clip((29 - Z) / 8, 0, 1)
    # 未開鑿：圓鈍節理塊＋裂縫
    pillow, big, small = joints(X, Z) if J is None else J
    rough = 1.0 * fbm(X * 0.12, Z * 0.12, None, 4, seed=9) + 0.3 * fbm(X * 0.6, Z * 0.6, None, 3, seed=10)
    y += (pillow + 1.3 * big + 0.4 * small + rough) * (1 - cm)
    # 開鑿面：平緩起伏
    y += cm * 0.45 * fbm(X * 0.08, Z * 0.08, None, 3, seed=11)
    # 頭像周圍往後挖深，讓頭部側面與陰影顯露
    for kind, C, H, yaw, pitch in HEADS:
        y += 5.5 * gauss(X, Z, C[0], C[2] + 0.55 * H, 0.6 * H, 0.42 * H)
    # 碎石坡（約 34°）
    fz = foot_z(X)
    talus = y - (fz - Z) * 1.5 + 0.35 * fbm(X * 0.4, Z * 0.4, None, 3, seed=12)
    return np.where(Z < fz, talus, y)


def rushmore(path):
    b = Builder("Rushmore", seed=41)
    r = b.rng

    # ---- 頭像深度圖
    maps = [head_depth(k, C, H, yaw, pitch) for k, C, H, yaw, pitch in HEADS]

    def front(X, Z):
        y = rock_y(X, Z)
        cm = carved_mask(X, Z)
        for m in maps:
            hy = sample_map(m, X, Z)
            y = np.where(np.isfinite(hy), smin(y, hy, 0.9), y)
        return y

    def head_top(xs):
        t = np.full(xs.shape, -1e9)
        for xs_m, zs_m, Ym in maps:
            col = np.isfinite(Ym)
            zt = np.where(col.any(1), np.max(np.where(col, zs_m[None, :], -1e9), 1), -1e9)
            t = np.maximum(t, np.interp(xs, xs_m, zt, left=-1e9, right=-1e9))
        return t

    # ---- 高度場網格（x 欄、s 列；s 超過崖頂後往山背摺回）
    def axis(segs):
        out = []
        for a, c, st in segs:
            n = max(1, int(round((c - a) / st)))
            out.extend(a + (c - a) * i / n for i in range(n))
        out.append(segs[-1][1])
        return np.array(out)

    xs = axis([(-112, -62, 1.6), (-62, -42, 0.6), (-42, 36, 0.38), (36, 56, 0.6), (56, 112, 1.6)])
    zs = axis([(-2, 20, 0.9), (20, 28, 0.5), (28, 72, 0.38), (72, 92, 0.8)])
    top = cliff_top(xs)
    NB = 26  # 山背列數
    X = np.repeat(xs[:, None], len(zs) + NB, 1)
    Zg = np.zeros_like(X)
    for i, (x, t) in enumerate(zip(xs, top)):
        zc = zs[zs < t - 0.15]
        n = len(zc)
        col = np.concatenate([zc, [t]])
        # 摺回：其餘列平均分配給山背
        rest = len(zs) + NB - len(col)
        Zg[i, : len(col)] = col
        Zg[i, len(col):] = t + 1.0 + np.arange(rest)  # 標記用（之後換成山背座標）
        Zg[i, len(col):] = -1000 - np.arange(rest) / max(rest, 1)
    front_mask = Zg > -999
    Zf = np.where(front_mask, Zg, 0.0)
    Y = rock_y(X, Zf)
    # 山背：自崖頂點往後越過山頂再落到地面
    Ytop = np.array([Y[i, front_mask[i]][-1] for i in range(len(xs))])
    for i in range(len(xs)):
        idx = np.nonzero(~front_mask[i])[0]
        if len(idx) == 0:
            continue
        t = (np.arange(1, len(idx) + 1)) / len(idx)
        Lb = 95.0
        zt = top[i]
        Y[i, idx] = Ytop[i] + t * Lb + 2.0 * np.sin(t * 7 + xs[i] * 0.1)
        Zf[i, idx] = zt + 2.0 * np.sin(np.pi * np.minimum(t * 3, 1)) - (zt + 2.0) * np.clip((t - 0.25) / 0.75, 0, 1) ** 1.6
    V = np.stack([X, Y, Zf], -1).reshape(-1, 3)
    nx_, nz_ = X.shape
    I = np.arange(nx_ * nz_).reshape(nx_, nz_)
    Q = np.stack([I[:-1, :-1], I[1:, :-1], I[1:, 1:], I[:-1, 1:]], -1).reshape(-1, 4)
    # 正面投影 UV（覆蓋 x -112..112、z -6..106）
    U = (V[:, 0] + 112) / 224.0
    Vv = (V[:, 2] + 6) / 112.0
    uv = np.stack([U, Vv], -1)[Q]
    back = (~front_mask[:-1, :-1] & ~front_mask[1:, 1:]).reshape(-1)

    # ---- 正面烘焙貼圖
    diff_p, nor_p = bake_front(front, maps)
    m_front = img_mat("Rushmore_front", diff_p, nor_p, rough=0.88, nor_strength=1.0)
    back_mi = b.tex("back", "rock_04", tile=7.0, tint="#7c766c", normal=1.4, rough=0.9)
    # 山背用方塊投影 UV
    from buildings.sphinx import box_uv
    buv = box_uv(V, Q, 7.0)
    uv = np.where(back[:, None, None], buv, uv)
    mesh_object("RushmoreCliff", V, Q, [m_front, b.mats[back_mi]], back.astype(int), uv, decimate=0.5)

    # ---- 頭像：3D 隱函數網格（含下巴、鼻、眉骨的倒切面），以平滑最小值與岩壁融合
    for kind, C, H, yaw, pitch in HEADS:
        R = SDF.rot(yaw, pitch)
        corners = np.array([[x, y, z] for x in (-0.5, 0.5) for y in (-0.62, 0.5) for z in (-0.4, 1.06)]) * H
        Wc = corners @ R.T + np.asarray(C)
        lo, hi = Wc.min(0) - 1.0, Wc.max(0) + 1.0
        step = 0.2
        S, o = grid3(lo, hi, step)
        dh = head_sdf(S.local(C, R, H), kind) * H
        ry = rock_y(S.X[:, 0, :], S.Z[:, 0, :])[:, None, :]
        dr = (ry + 0.08 - S.Y) * 0.9
        # 岩壁只保留到頭像的平滑過渡帶；其餘交給高度場
        F = smin(dh, dr, 1.1)
        F = np.where(S.Z > cliff_top(S.X) + 0.5, dh, F)
        Vh, Qh = surface_nets(F, o, step)
        # 去掉離頭像遠、純屬岩壁的面
        Sv = SDF(Vh[:, 0:1].astype(np.float32), Vh[:, 1:2].astype(np.float32), Vh[:, 2:3].astype(np.float32))
        dv = (head_sdf(Sv.local(C, R, H), kind) * H)[:, 0]
        keep = dv[Qh].min(1) < 1.6
        Qh = Qh[keep]
        uvh = np.stack([(Vh[:, 0] + 112) / 224.0, (Vh[:, 2] + 6) / 112.0], -1)[Qh]
        mesh_object("Head_" + kind, Vh, Qh, [m_front], None, uvh, decimate=0.5)

    # ---- 地面
    ground = b.tex("ground", "rocky_terrain_02", tile=8.0, tint="#5f5c46", normal=0.8, rough=0.95)
    soil = b.color("soil", "#5b4f40", rough=0.95)
    b.ground_disc(ground, 180, soil, depth=3.0, seg=96, rings=20,
                  height_fn=lambda x, y: 1.5 * noise.noise(Vector((x * 0.012, y * 0.012, 0.4))) - 1.6)

    # ---- 碎石坡上的落石
    talus_m = b.tex("talus", "gray_rocks", tile=3.0, tint="#7f7b74", normal=1.4, rough=0.9)
    for i in range(420):
        x = r.uniform(-70, 70)
        fz = float(foot_z(np.array(x)))
        z = r.uniform(-0.5, fz - 0.8)
        y = float(front(np.array([x]), np.array([z]))[0]) - 0.1
        s_ = r.uniform(0.6, 2.0) * (1.5 if r.random() < 0.15 else 1.0)
        b.rock(talus_m, (s_, s_ * 0.8, s_ * 0.5), (x, y, z + s_ * 0.1), rot=(0.55, r.uniform(-0.3, 0.3), r.uniform(0, TAU)), rough=0.12, subdiv=1, seed=900 + i, round_=0.15)

    # ---- 西黃松：細高樹幹、上半部不規則的針葉團簇
    pine = b.tex("pine", "rocky_terrain_02", tile=1.2, tint="#1c2617", normal=1.4, rough=0.9)
    pine2 = b.tex("pine2", "rocky_terrain_02", tile=1.2, tint="#283521", normal=1.4, rough=0.9)
    pine3 = b.tex("pine3", "rocky_terrain_02", tile=1.2, tint="#3c4a2a", normal=1.4, rough=0.9)
    bark = b.color("bark", "#4a3a2c", rough=0.9)

    def pine_tree(x, y, z, h):
        b.cyl(bark, 0.2 + h * 0.012, 0.08, h * 0.92, (x, y, z), seg=5)
        n = int(10 + h * 0.5)
        for k in range(n):
            u = k / (n - 1)
            zz = z + h * (0.3 + 0.68 * u)
            rad = (h * 0.2 * (1 - u) ** 0.7 + 0.5) * r.uniform(0.75, 1.1)
            a = r.uniform(0, TAU)
            ox, oy = math.cos(a) * rad * 0.45, math.sin(a) * rad * 0.45
            s_ = rad * r.uniform(1.0, 1.4)
            mi = pine3 if (k > n * 0.6 and r.random() < 0.4) else r.choice((pine, pine, pine2))
            b.rock(mi, (s_, s_ * 0.85, h * 0.06 + 0.45), (x + ox, y + oy, zz), rot=(r.uniform(-0.25, 0.25), r.uniform(-0.25, 0.25), a),
                   rough=0.9, subdiv=1, seed=r.randint(0, 9999), flat_bottom=False, round_=0.45)

    for i in range(58):
        if r.random() < 0.72:
            x = r.choice((r.uniform(-90, -25), r.uniform(-10, 60), r.uniform(-25, -10)))
            fz = float(foot_z(np.array(x)))
            z = r.uniform(-0.5, fz - 1.2)
            y = float(front(np.array([x]), np.array([z]))[0]) - 0.2
        else:
            x = r.uniform(-95, 95)
            y = r.uniform(-110, -60)
            z = 1.5 * noise.noise(Vector((x * 0.012, y * 0.012, 0.4))) - 1.6
        pine_tree(x, y, z - 0.3, r.uniform(9, 18))
    b.export(path)


# ---------------------------------------------------------------- 正面貼圖烘焙
def _up(a, s, shape):
    """雙線性放大 s 倍"""
    h, w = a.shape
    yi = (np.arange(shape[0]) + 0.5) / s - 0.5
    xi = (np.arange(shape[1]) + 0.5) / s - 0.5
    y0 = np.clip(np.floor(yi).astype(int), 0, h - 1)
    x0 = np.clip(np.floor(xi).astype(int), 0, w - 1)
    y1, x1 = np.minimum(y0 + 1, h - 1), np.minimum(x0 + 1, w - 1)
    ty = np.clip(yi - y0, 0, 1)[:, None].astype(np.float32)
    tx = np.clip(xi - x0, 0, 1)[None, :].astype(np.float32)
    top = a[y0][:, x0] * (1 - tx) + a[y0][:, x1] * tx
    bot = a[y1][:, x0] * (1 - tx) + a[y1][:, x1] * tx
    return top * (1 - ty) + bot * ty


def bake_front(front, maps, TW=4096, TH=2048):
    """整面正面貼圖：花崗岩顆粒＋裂紋＋節理＋片岩帶＋地衣＋髒污垂流＋凹處陰影"""
    os.makedirs(GEN, exist_ok=True)
    diff_p = os.path.join(GEN, "front_diff.jpg")
    nor_p = os.path.join(GEN, "front_nor.jpg")
    shape = (TH, TW)
    u = (np.arange(TW, dtype=np.float32) + 0.5) / TW
    v = 1.0 - (np.arange(TH, dtype=np.float32) + 0.5) / TH
    X = np.broadcast_to((u * 224 - 112)[None, :], shape)
    Z = np.broadcast_to((v * 112 - 6)[:, None], shape)
    # 低頻欄位以半解析度計算
    h = 2
    Xh, Zh = X[::h, ::h], Z[::h, ::h]
    cm = _up(carved_mask(Xh, Zh), h, shape)
    talus = _up(np.clip((foot_z(Xh) - Zh) / 1.2, 0, 1), h, shape)
    lo = _up(fbm(Xh * 0.035, Zh * 0.035, None, 4, seed=21), h, shape)
    mid = _up(fbm(Xh * 0.15, Zh * 0.15, None, 4, seed=22), h, shape)
    streak = _up(fbm(Xh * 0.35, Zh * 0.016, None, 4, seed=23), h, shape)
    pinkm = _up(np.clip(fbm(Xh * 0.06, Zh * 0.02, None, 3, seed=24) * 2.5 - 0.5, 0, 1), h, shape)
    darkm = _up(fbm(Xh * 0.09, Zh * 0.09, None, 4, seed=25), h, shape)
    ylw = _up(fbm(Xh * 0.2, Zh * 0.2, None, 3, seed=26), h, shape)
    lamn = _up(fbm(Xh * 0.1, Zh * 0.1, None, 2, seed=28), h, shape)
    bandn = _up(fbm(Xh * 0.04, Zh * 0.0 + 2.0, None, 2, seed=27), h, shape)
    pillow, big, small = joints(X, Z)
    grain = tile_sample(gray_tex("rock_04", 512), X / 2.6, -Z / 2.6)
    crack = tile_sample(gray_tex("rock_face_03", 1024), X / 10.0, -Z / 10.0)
    rubble = tile_sample(gray_tex("gray_rocks", 1024), X / 3.0, -Z / 3.0)
    lich = tile_sample(gray_tex("lichen_rock", 1024), X / 6.0, -Z / 6.0)

    # 凹處陰影（低解析度深度 → 與模糊比較）
    s = 4
    Yl = rock_y(X[::s, ::s], Z[::s, ::s])
    Yl = np.where(np.isfinite(Yl), Yl, 30.0)
    cav = _up(np.clip((Yl - blur(Yl, 18)) / 3.0, -1, 1), s, shape)
    cav2 = _up(np.clip((Yl - blur(Yl, 4)) / 0.7, -1, 1), s, shape)

    def col(hexs):
        q = hexs.lstrip("#")
        return np.array([int(q[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)[None, None]

    E = lambda a: a[..., None]  # noqa: E731
    # 開鑿面：淺灰帶暖色、粉橘色斑
    carved = col("#a9a296") * E(0.86 + 0.25 * (grain - 0.5) + 0.16 * lo + 0.07 * mid)
    carved = carved * E(1 - pinkm * 0.22) + E(pinkm * 0.22) * col("#c9a493")
    # 未開鑿：較深的褐灰，黑色地衣斑塊、黃綠地衣
    unc = col("#857a6c") * E(0.82 + 0.35 * (grain - 0.5) + 0.15 * mid)
    dark = np.clip(0.45 + 1.6 * darkm + 0.7 * (lich - 0.5), 0, 1)
    unc = unc * E(1 - 0.42 * dark)
    yl = np.clip((ylw - 0.2) * 3, 0, 1) * np.clip((45 - Z) / 15, 0, 1) * (1 - cm)
    unc = unc * E(1 - yl * 0.55) + E(yl * 0.55) * col("#a9a85a")
    # 片岩帶（華盛頓衣領下方的深灰藍色斜向層理）
    band_c = 20.0 - 0.1 * (X + 60) + 1.5 * bandn
    schist = np.exp(-((Z - band_c) / 3.2) ** 4) * np.clip((-X + 8) / 8, 0, 1) * np.clip((X + 75) / 10, 0, 1)
    lam = 0.5 + 0.5 * np.sin((Z - X * 0.35) * 2.2 + 3 * lamn)
    sch = col("#5b5f66") * E((0.72 + 0.45 * lam) * (0.85 + 0.3 * (grain - 0.5)))
    base = carved * E(cm) + unc * E(1 - cm)
    base = base * E(1 - schist) + sch * E(schist)
    # 碎石坡：淺灰碎石
    tal = col("#7e7a73") * E(0.2 + 1.9 * (rubble - 0.5) + 0.55)
    base = base * E(1 - talus) + tal * E(talus)
    # 裂紋、節理、髒污垂流、凹處陰影
    nt = 1 - talus
    crk = np.clip((crack - 0.5) * 1.3, -0.6, 0.35)
    base = base * E(1 + crk * (0.15 + 0.4 * (1 - cm)) * nt)
    base = base * E(1 - (0.32 * big + 0.18 * small) * (1 - 0.93 * cm) * nt)
    base = base * E(1 - 0.26 * np.clip(streak * 2.5, 0, 1) * nt * (1 - 0.7 * cm))
    base = base * E(1 - 0.3 * np.clip(cav, 0, 1) - 0.15 * np.clip(cav2, 0, 1))
    base = base * E(1 + 0.06 * np.clip(-cav, 0, 1))
    save_img(np.clip(base, 0, 1), diff_p, quality=86)
    # 法線：紋理細節＋節理裂縫
    hgt = (grain - 0.5) * 0.6 + (crack - 0.5) * 1.2 - (1.4 * big + 0.6 * small) * (1 - 0.7 * cm) + (rubble - 0.5) * 2.0 * talus
    hgt = blur(hgt[::2, ::2], 1)
    save_img(normal_from_height(hgt, 2.0), nor_p, quality=85)
    return diff_p, nor_p
