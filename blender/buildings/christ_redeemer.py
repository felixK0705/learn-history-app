"""christ-redeemer 里約熱內盧救世基督像寫實模型（公尺；雕像面向 -Y）

科科瓦多山頂：雕像高 30 m（不含 8 m 台座），兩臂展開 28 m；鋼筋混凝土外覆淺灰白皂石三角馬賽克。
台座為深褐色花崗岩貼面、四角切角，內有小禮拜堂；四周為觀景平台、欄杆與階梯，山頂四周為花崗岩峭壁與大西洋雨林。

建模方式：雕像以隱函數（SDF）組合──長袍（縱向褶紋）、外披的斗篷（胸前橫向垂褶、右側直落的衣緣、
不對稱的下襬）、自前臂垂下呈弧形的厚袖幔、張開的雙手、低垂的頭（中分長髮、鬍鬚、五官）──
再以 Surface Nets 轉成網格。雨林為連續的樹冠高度場（大小不一的圓頂樹冠、樹冠間陰影），配自製樹冠貼圖。
"""

import ast
import math
import os

import numpy as np

from lib import TAU, TEX, Builder
from buildings.sphinx import (FACE_DEFAULT, SDF, blur, box_uv, cr_interp, face_head, fbm, g2, grid3, img_mat,
                              mesh_object, normal_from_height, save_img, smax, smin, surface_nets, tile_sample,
                              gray_tex, worley)

# 目標點、方位角、仰角、距離、焦距（對應參考照：自正面略高處空拍）
CAMERA = ((0.0, 0.0, 15.0), 0.0, 15.0, 112.0, 62.0)
if os.environ.get("TL_CAM"):  # 開發用：覆寫預覽相機
    CAMERA = ast.literal_eval(os.environ["TL_CAM"])

GEN = os.path.join(TEX, "_gen", "christ_redeemer")
Z0 = 8.4  # 雕像腳底（台座頂）高度


# ---------------------------------------------------------------- 2D 多邊形距離（x, z 平面）
def sd_poly(px, pz, pts):
    pts = np.asarray(pts, float)
    d = (px - pts[0, 0]) ** 2 + (pz - pts[0, 1]) ** 2
    s = np.ones_like(px)
    n = len(pts)
    for i in range(n):
        j = (i - 1) % n
        vi, vj = pts[i], pts[j]
        ex, ez = vj[0] - vi[0], vj[1] - vi[1]
        wx, wz = px - vi[0], pz - vi[1]
        h = np.clip((wx * ex + wz * ez) / (ex * ex + ez * ez), 0, 1)
        bx, bz = wx - ex * h, wz - ez * h
        d = np.minimum(d, bx * bx + bz * bz)
        c1 = pz >= vi[1]
        c2 = pz < vj[1]
        c3 = ex * wz > ez * wx
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        s = np.where(flip, -s, s)
    return s * np.sqrt(d)


def chain(S, pts, r):
    """沿折線的膠囊串"""
    d = None
    for a, b_ in zip(pts, pts[1:]):
        rr = r if np.isscalar(r) else None
        q = S.cap(a, b_, rr if rr else r[0], rr if rr else r[1])
        d = q if d is None else np.minimum(d, q)
    return d


# ---------------------------------------------------------------- 雕像 SDF（z 以雕像腳底為 0）
def head_P():
    P = dict(FACE_DEFAULT)
    P["wf"] = [(z, w * 0.94) for z, w in P["wf"]]
    P["brow"] = 0.03
    P["nose"] = (0.1, 0.35, 0.04, 0.062, 0.07)
    P["cranium"] = ((0, 0.12, 0.6), (0.34, 0.42, 0.42))
    P["neck"] = ((0, 0.08, 0.25), (0, 0.15, -0.5), 0.2, 0.25)
    return P


def statue_sdf(S):
    X, Y, Z = S.X, S.Y, S.Z
    ax = np.abs(X)
    th = np.arctan2(Y, X)
    # ---- 內袍（下段，縱向褶紋）
    a = 3.05 + 0.12 * np.clip((6 - Z) / 6, 0, 1)
    bb = 1.55 + 0.25 * np.clip(Z / 14, 0, 1)
    p = 2.6
    pleat = 0.085 * np.abs(np.sin(15 * th + 0.2)) ** 0.6 * (Y < 0.5) - 0.04
    rn = (np.abs(X / a) ** p + np.abs(Y / bb) ** p) ** (1 / p)
    tunic = (rn - 1.0) * np.minimum(a, bb) - pleat
    tunic = smax(tunic, -Z + 0.35, 0.1)
    tunic = smax(tunic, Z - 16.0, 0.3)
    # 腳趾（袍下緣露出）
    for sx in (-1, 1):
        tunic = smin(tunic, S.ell((sx * 0.75, -1.55, 0.28), (0.55, 0.75, 0.32)), 0.1)
    # ---- 上身（胸、肩）
    wz = cr_interp(Z, [12, 15, 18, 20.5, 22.6, 23.4, 24.0], [3.0, 3.2, 3.55, 3.85, 4.0, 3.7, 2.6])
    dz = cr_interp(Z, [13, 18, 22, 23.6, 24.2], [1.8, 1.95, 2.0, 1.8, 1.4])
    rn2 = (np.abs(X / wz) ** 2.4 + np.abs(Y / dz) ** 2.4) ** (1 / 2.4)
    torso = (rn2 - 1.0) * np.minimum(wz, dz)
    torso = smax(torso, Z - 24.3, 0.4)
    torso = smax(torso, 5.0 - Z, 0.3)
    body = smin(tunic, torso, 0.5)
    # ---- 外披斗篷：比身體大一圈，下襬左高右低，帶斜向衣褶
    hem = 9.2 - 2.8 * np.clip((X + 3.0) / 6.0, 0, 1) + 0.35 * np.sin(X * 2.3)
    fold = 0.07 * np.sin(9 * th + 1.3 + 0.3 * Z) * np.clip((22 - Z) / 12, 0, 1)
    mant = (rn2 - 1.0) * np.minimum(wz, dz) - 0.28 - fold
    mzone = smax(mant, hem - Z, 0.15)
    mzone = smax(mzone, Z - 24.0, 0.4)
    body = smin(body, mzone, 0.15)
    # 斗篷右側直落的衣緣（自胸前到下襬）與胸前橫向垂褶
    # 斗篷前片：胸前橫向垂褶線以下、右側衣緣以左的布層較厚（重疊布料形成階差與陰影）
    swag_z = 19.75 + 0.22 * X ** 2 / 4.0 + 0.25 * X / 3.0
    edge_x = 1.3 + 0.1 * (21 - Z)
    layer = np.clip((swag_z - Z) / 0.25, 0, 1) * np.clip((edge_x - X) / 0.2, 0, 1) * np.clip((Z - hem + 0.5) / 0.5, 0, 1) * np.clip((3.0 + X) / 1.2, 0, 1)
    layer = layer * (Y < 0)
    body = body - 0.2 * layer
    # 垂褶本身：沿弧線的圓鼓布卷
    swag = None
    for t in np.linspace(-1, 1, 13):
        xx = 3.4 * t
        zz = 19.9 + 2.0 * t ** 4 + 0.3 * t
        yy = -2.0 - 0.25 * (1 - t * t)
        q = S.ell((xx, yy, zz), (0.7, 0.22, 0.4 + 0.15 * t * t))
        swag = q if swag is None else smin(swag, q, 0.25)
    body = smin(body, swag, 0.5)
    # 衣緣自胸前直落下襬，邊緣略捲
    edge = chain(S, [(1.3, -2.3, 20.8), (1.65, -2.35, 16.0), (2.0, -2.2, 10.0), (2.35, -2.05, 6.6)], 0.13)
    body = smin(body, edge, 0.1)
    # 斗篷下襬的 Z 字形衣褶（右側）
    for k in range(4):
        zz = 6.8 + k * 0.9
        body = smin(body, S.ell((2.75, -1.75 + k * 0.05, zz), (0.35, 0.3, 0.55)), 0.15)
    # 聖心
    body = smin(body, S.ell((0.0, -2.12, 22.7), (0.32, 0.12, 0.36)), 0.06)
    # ---- 手臂（水平伸展，略微上揚）
    arms = None
    for sx in (-1, 1):
        arm = S.cap((sx * 3.0, 0.1, 23.3), (sx * 11.3, -0.1, 23.85), 1.3, 0.62)
        arms = arm if arms is None else np.minimum(arms, arm)
    body = smin(body, arms, 0.6)
    # ---- 袖幔：前臂垂下的厚布，下緣呈弧形回到身側
    sl_pts = [(11.25, 24.1), (11.5, 23.2), (10.7, 22.0), (9.7, 20.9), (8.6, 20.15), (7.4, 20.0), (6.2, 20.5),
              (5.0, 21.2), (3.4, 21.5), (3.3, 24.0)]
    d2 = sd_poly(ax, Z, sl_pts)
    u = np.clip((ax - 3.3) / 8.0, 0, 1)
    ymid = 0.05 + 0.25 * np.sin(u * math.pi) * np.clip((23.6 - Z) / 3.0, 0, 1) + 0.06 * np.sin(ax * 2.2 + Z * 1.4)
    thick = 0.5 + 0.35 * np.clip((Z - 21.0) / 2.5, 0, 1) + 0.25 * np.clip((6.0 - ax) / 2.5, 0, 1)
    sleeve = smax(d2, np.abs(Y - ymid) - thick, 0.18)
    # 袖幔上自手腕向下放射的衣褶
    ang = np.arctan2(Z - 23.9, ax - 11.0)
    sleeve = sleeve - 0.05 * np.abs(np.sin(ang * 9.0)) * np.clip((23.5 - Z) / 2, 0, 1)
    body = smin(body, sleeve, 0.3)
    # ---- 手（掌心朝前，四指伸直、拇指上翹）
    for sx in (-1, 1):
        hand = S.box((sx * 12.15, -0.18, 23.85), (0.7, 0.24, 0.5), 0.18)
        for k, (zf, L) in enumerate(((24.22, 1.75), (23.97, 1.95), (23.72, 1.85), (23.48, 1.55))):
            hand = smin(hand, S.cap((sx * 12.6, -0.2, zf), (sx * (12.6 + L), -0.3, zf + 0.02), 0.155, 0.13), 0.06)
        hand = smin(hand, S.cap((sx * 12.0, -0.25, 24.25), (sx * 12.75, -0.42, 24.95), 0.2, 0.15), 0.08)
        body = smin(body, hand, 0.12)
    # ---- 頭（低垂約 18°）、中分長髮、鬍鬚
    C, H, pitch = (0.0, -0.55, 25.05), 3.9, 0.32
    R = SDF.rot(0.0, pitch)
    L = S.local(C, R, H)
    hd = face_head(L, head_P())
    lx, ly, lz = L.X, L.Y, L.Z
    hair = L.ell((0, 0.1, 0.62), (0.37, 0.46, 0.44))
    for sxx in (-1, 1):
        hair = smin(hair, L.cap((sxx * 0.31, -0.08, 0.72), (sxx * 0.34, 0.02, 0.0), 0.085, 0.11), 0.06)
        hair = smin(hair, L.cap((sxx * 0.28, 0.12, 0.3), (sxx * 0.4, 0.2, -0.3), 0.16, 0.2), 0.08)
    hair = hair + 0.01 * np.sin(lx * 70 + 4 * lz) * (ly > -0.25)
    hair = smax(hair, -(ly + 0.33 - 0.25 * np.clip(0.72 - lz, 0, 1)), 0.03)  # 頭髮在臉前方切開
    part = np.exp(-(lx / 0.02) ** 2) * (lz > 0.8)
    hair = hair + 0.012 * part
    hd = smin(hd, hair, 0.03)
    beard = L.ell((0, -0.32, 0.1), (0.2, 0.15, 0.15))
    for sxx in (-1, 1):
        beard = smin(beard, L.cap((sxx * 0.27, -0.12, 0.28), (sxx * 0.08, -0.38, 0.04), 0.06), 0.05)
    beard = smin(beard, L.ell((0, -0.45, 0.262), (0.12, 0.05, 0.03)), 0.03)  # 八字鬍
    beard = smax(beard, lz - 0.3, 0.03) + 0.006 * np.sin(lz * 60) * np.sin(lx * 50)
    hd = smin(hd, beard, 0.03)
    body = smin(body, hd * H, 0.35)
    return body


# ---------------------------------------------------------------- 貼圖
def mosaic_tex():
    """皂石三角馬賽克：每片 3–4 cm，深淺不一，細縫與零星污漬（貼圖對應 1.6 m）"""
    os.makedirs(GEN, exist_ok=True)
    p = os.path.join(GEN, "soapstone.jpg")
    pn = os.path.join(GEN, "soapstone_nor.jpg")
    N = 1024
    u = (np.arange(N) + 0.5) / N * 1.6
    U, V = np.meshgrid(u, u)
    P = 45
    cell = 1.6 / P
    f1, f2, tile_v = worley(U / cell, V / cell, seed=51, return_id=True, period=P)
    _, _, jit = worley(U / (cell * 5), V / (cell * 5), seed=54, return_id=True, period=P // 5 if P % 5 == 0 else None)
    jit = jit - 0.5
    grout = np.clip((f2 - f1) / 0.07, 0, 1)
    base = np.array([0.70, 0.69, 0.61], np.float32)
    g = 0.86 + 0.16 * (tile_v - 0.5) + 0.05 * jit
    _, _, st = worley(U / 0.4, V / 0.4, seed=55, return_id=True, period=4)
    stain = np.clip(st * 1.4 - 0.9, 0, 1) * 0.6
    g = g * (0.75 + 0.25 * grout) * (1 - 0.15 * stain)
    tint = np.stack([g * base[0], g * base[1] * (1 + 0.02 * jit), g * base[2] * (1 - 0.03 * stain)], -1)
    save_img(np.clip(tint, 0, 1), p, quality=88)
    save_img(normal_from_height(grout * 1.0 + 0.2 * tile_v, 1.5), pn, quality=85)
    return p, pn


def canopy_tex(crowns, mask_rock, size=2048, extent=82.0):
    """雨林樹冠俯視貼圖：每棵樹冠不同綠色、冠頂亮冠緣暗、葉團細節，零星淺色開花樹冠；岩壁處為深灰花崗岩"""
    os.makedirs(GEN, exist_ok=True)
    p = os.path.join(GEN, "canopy.jpg")
    pn = os.path.join(GEN, "canopy_nor.jpg")
    u = (np.arange(size) + 0.5) / size * 2 * extent - extent
    Xg, Yg = np.meshgrid(u, -u)
    h, top, c = crowns(Xg, Yg)
    # 葉團：高頻、凹凸分明的雜訊（花椰菜狀）
    l1 = np.abs(fbm(Xg * 2.2, Yg * 2.2, None, 3, seed=61))
    l2 = fbm(Xg * 6.0, Yg * 6.0, None, 2, seed=62)
    leaf = 1.0 - 1.4 * l1 + 0.35 * l2
    greens = np.array([[0.10, 0.17, 0.07], [0.14, 0.22, 0.08], [0.18, 0.26, 0.10], [0.09, 0.15, 0.08], [0.22, 0.29, 0.12],
                       [0.16, 0.21, 0.09], [0.12, 0.20, 0.11], [0.24, 0.27, 0.12]], np.float32)
    gi = np.floor(c * len(greens) * 0.999).astype(int)
    col = greens[gi]
    lit = 0.25 + 0.75 * np.clip(top, 0, 1) ** 0.7
    bright = np.clip(lit * (0.75 + 0.45 * leaf), 0.08, 1.6)
    col = col * bright[..., None]
    flower = ((c * 13.7) % 1.0 > 0.975)[..., None] & (top[..., None] > 0.05)
    col = np.where(flower, np.array([0.5, 0.5, 0.45]) * bright[..., None], col)
    rock = mask_rock(Xg, Yg)
    grain = tile_sample(gray_tex("rock_face_03", 512), Xg / 8, Yg / 8)
    rk = np.stack([0.33 * grain, 0.32 * grain, 0.30 * grain], -1) * (0.8 + 0.4 * fbm(Xg * 0.2, Yg * 0.05, None, 3, seed=63))[..., None]
    col = col * (1 - rock[..., None]) + rk * rock[..., None]
    save_img(np.clip(col, 0, 1), p, quality=86)
    hh = leaf * 0.8 + h * 0.6
    save_img(normal_from_height(hh, 2.5), pn, quality=82)
    return p, pn


# ---------------------------------------------------------------- 主體
def christ_redeemer(path):
    b = Builder("ChristRedeemer", seed=29)
    r = b.rng
    ped = b.tex("ped", "marble_01", tile=2.4, tint="#3a2d27", normal=0.3, rough=0.35)
    ped_cap = b.tex("pedcap", "marble_01", tile=2.0, tint="#c9c5bb", normal=0.4, rough=0.6)
    pave = b.tex("pave", "marble_01", tile=1.5, tint="#a8a297", normal=0.4, rough=0.75)
    wallw = b.tex("wallw", "plastered_wall_04", tile=3.0, tint="#b9b3a7", normal=0.4, rough=0.85)
    wallc = b.tex("wallc", "plastered_wall_04", tile=4.0, tint="#7d786e", normal=0.6, rough=0.9)
    wallg = b.tex("wallg", "plastered_wall_04", tile=3.0, tint="#7f8a72", normal=0.4, rough=0.85)
    iron = b.color("iron", "#3c3c3a", rough=0.6, metal=0.4)

    # ---- 雕像
    lo, hi = (-15.3, -3.4, 0.0), (15.3, 3.0, 30.4)
    step = 0.1
    S, o = grid3(lo, hi, step)
    F = statue_sdf(S)
    V, Q = surface_nets(F, o, step)
    V[:, 2] += Z0
    diff, nor = mosaic_tex()
    soap = img_mat("Christ_soapstone", diff, nor, rough=0.75, nor_strength=0.6)
    mesh_object("Statue", V, Q, [soap], None, box_uv(V, Q, 1.6), decimate=0.42)

    # ---- 台座：深褐色花崗岩、四角切角，上下白色石材飾帶
    def octo(w, c):
        h = w / 2
        return [(-h + c, -h), (h - c, -h), (h, -h + c), (h, h - c), (h - c, h), (-h + c, h), (-h, h - c), (-h, -h + c)]

    b.prism(ped_cap, octo(11.6, 1.6), -0.1, 0.6)
    b.prism(ped, octo(9.6, 1.25), 0.5, 7.2)
    for k in range(1, 6):  # 石板分格縫
        b.prism(b.color("joint", "#2a221e", rough=0.6), octo(9.64, 1.26), 0.5 + k * 1.2 - 0.02, 0.04)
    b.prism(ped_cap, octo(10.2, 1.35), 7.7, 0.35)
    b.prism(ped_cap, octo(7.4, 1.0), 8.05, 0.35)
    b.box_base(b.color("door", "#1f1c19", rough=0.9), (1.6, 0.1, 2.6), (0, -4.82, 0.5))

    # ---- 觀景平台：上層環繞台座，前方延伸的下層平台與階梯，白色欄杆
    top = [(-15, -12), (13, -12), (17, -6), (17, 8), (11, 13), (-11, 13), (-17, 8), (-17, -5)]
    b.prism(wallc, top, -6.5, 6.5)
    b.prism(pave, [(x * 0.995, y * 0.995) for x, y in top], -0.05, 0.1)
    low = [(-12, -26), (6, -26), (10, -20), (10, -12), (-12, -12)]
    b.prism(wallc, low, -10.0, 6.0)
    b.prism(pave, low, -4.05, 0.1)
    for k in range(10):  # 階梯
        b.box_base(pave, (5.0, 0.42, 0.4), (-8.0, -12.2 - k * 0.42, -4.0 + (9 - k) * 0.4))
    # 右側的綠色電梯塔與左側白色鷹架（參考照）
    b.box_base(wallg, (6.0, 5.0, 7.5), (19.5, -2.0, -6.0))
    b.box_base(wallw, (6.4, 5.4, 0.4), (19.5, -2.0, 1.5))
    for x in (-13.5, -11.0):
        for y in (-8.0, -5.5):
            b.cyl(iron, 0.06, 0.06, 7.5, (x, y, 0.0), seg=4)
    b.box_base(b.color("banner", "#d9dcd8", rough=0.8), (2.3, 2.3, 5.5), (-12.25, -6.75, 1.5))

    def railing(pts, z, closed=True):
        n = len(pts)
        for i in range(n if closed else n - 1):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            L = math.hypot(x1 - x0, y1 - y0)
            ang = math.atan2(y1 - y0, x1 - x0)
            b.box(wallw, (L, 0.32, 0.16), ((x0 + x1) / 2, (y0 + y1) / 2, z + 1.0), rot=(0, 0, ang))
            b.box(wallw, (L, 0.36, 0.2), ((x0 + x1) / 2, (y0 + y1) / 2, z + 0.1), rot=(0, 0, ang))
            nb = int(L / 0.45)
            for k in range(nb):
                t = (k + 0.5) / nb
                b.cyl(wallw, 0.09, 0.07, 0.8, (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z + 0.2), seg=5)

    railing(top, 0.05)
    railing(low, -3.95, closed=False)

    # ---- 山頂地形：花崗岩山體＋雨林樹冠（連續高度場）
    R0 = 82.0

    def ground(x, y):
        rr = np.hypot(x * 1.05, y)
        n = fbm(x * 0.03, y * 0.03, None, 4, seed=71) * 6.0
        g = -5.0 - 0.25 * np.maximum(0, rr - 14) - 0.05 * np.maximum(0, rr - 14) ** 1.55 + n * np.clip((rr - 18) / 12, 0, 1)
        return g

    def rock_mask(x, y):
        rr = np.hypot(x, y)
        a = np.arctan2(y, x)
        m = np.clip((fbm(x * 0.025, y * 0.025, None, 3, seed=72) - 0.05) * 4, 0, 1)
        m = np.maximum(m, np.clip(1 - np.abs(np.sin(a * 1.0 + 2.2)) * 3, 0, 1) * np.clip((rr - 22) / 6, 0, 1) * 0.0)
        # 平台正下方左前側的裸露花崗岩
        m = np.maximum(m, g2(x + 14, y + 22, 9, 8))
        return np.clip(m * np.clip((rr - 15) / 4, 0, 1), 0, 1)

    def crowns(x, y):
        """多層圓頂樹冠（取最大值 → 彼此重疊、冠間留陰影）：回傳 (高度, 冠頂比例 0..1, 樹冠編號亂數)"""
        wx = x + 1.6 * fbm(x * 0.12, y * 0.12, None, 2, seed=81)
        wy = y + 1.6 * fbm(x * 0.12 + 5, y * 0.12, None, 2, seed=82)
        best = np.zeros(np.shape(x))
        top = np.zeros(np.shape(x))
        cid = np.zeros(np.shape(x))
        for size, seed, rad, hh in ((4.4, 73, 0.62, 3.0), (3.3, 77, 0.6, 2.4), (8.0, 76, 0.5, 5.0), (2.2, 78, 0.6, 1.5)):
            f1, _, idv = worley(wx / size + seed * 0.37, wy / size, seed=seed, jitter=1.0, return_id=True)
            k = np.clip(1 - (f1 / rad) ** 2, 0, 1)
            h = np.sqrt(k) * hh * (0.75 + 0.5 * idv)
            win = h > best
            best = np.where(win, h, best)
            top = np.where(win, np.sqrt(k), top)
            cid = np.where(win, idv + seed, cid)
        return best, top, cid % 1.0

    def canopy_h(x, y):
        dome = crowns(x, y)[0]
        rr = np.hypot(x, y)
        veg = (1 - rock_mask(x, y)) * np.clip((rr - 14.5) / 3, 0, 1)
        return ground(x, y) + veg * (4.0 + dome + 1.5 * fbm(x * 0.05, y * 0.05, None, 2, seed=75))

    n = 329
    g = np.linspace(-R0, R0, n)
    Xg, Yg = np.meshgrid(g, g, indexing="ij")
    rr = np.hypot(Xg, Yg)
    k = np.minimum(1.0, R0 / np.maximum(rr, 1e-6))
    Xg, Yg = Xg * np.where(rr > R0, k, 1), Yg * np.where(rr > R0, k, 1)  # 圓形外緣
    Zg = canopy_h(Xg, Yg)
    Vt = np.stack([Xg, Yg, Zg], -1).reshape(-1, 3)
    I = np.arange(n * n).reshape(n, n)
    Qt = np.stack([I[:-1, :-1], I[1:, :-1], I[1:, 1:], I[:-1, 1:]], -1).reshape(-1, 4)
    # 平台內部不需要地形（被平台覆蓋）→ 保留，作為平台下的岩體
    uvt = np.stack([(Vt[:, 0] + R0) / (2 * R0), (Vt[:, 1] + R0) / (2 * R0)], -1)[Qt]
    cdiff, cnor = canopy_tex(crowns, rock_mask)
    cmat = img_mat("Christ_canopy", cdiff, cnor, rough=0.9, nor_strength=1.0)
    mesh_object("Forest", Vt, Qt, [cmat], None, uvt, decimate=0.34)
    b.export(path)
