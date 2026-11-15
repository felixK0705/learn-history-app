"""louvre 羅浮宮拿破崙中庭（Cour Napoléon）與貝聿銘玻璃金字塔寫實模型（公尺）

- 玻璃金字塔：底邊 35.42 m、高 21.64 m，菱形玻璃格（鋼索桁架）；北、南、東三座小金字塔（底 8 m、高約 5 m）
  與七座三角形水池
- 中庭三面為拿破崙三世時期的新羅浮宮翼樓：北黎塞留翼、南德農翼、東側敘利翼（鐘樓館）
  三層立面（底層拱廊、主樓層帶山牆窗、閣樓層）＋石欄杆，簷口約 21 m；藍灰色石板複折式屋頂（mansard）
  與老虎窗；各翼中央與轉角為高起的樓閣（pavillon），頂為方形穹頂
- 外牆為暖米黃色石灰岩

座標：+X 東、+Y 北，大金字塔中心在原點。參考照在中庭西南側地面以廣角拍攝。
"""

import math
import os

import bmesh
from mathutils import Matrix, Vector

from lib import TAU, TEX, Builder

CAMERA = ((-3.5, -10.0, 8.5), -128.7, -8.5, 44.0, 20)

GEN = os.path.join(TEX, "_gen", "louvre_v1")
FACADE_H = 22.0     # 立面貼圖一個循環的高度（= 寬度）
BAY = FACADE_H / 5  # 4.4 m 一個開間


# ====================================================================== 立面貼圖（numpy 產生）
def gen_facade():
    import numpy as np
    from PIL import Image

    d = os.path.join(GEN, "facade")
    if os.path.exists(os.path.join(d, "nor.jpg")):
        return "_gen/louvre_v1/facade"
    os.makedirs(d, exist_ok=True)
    N = 1024
    ppm = N / FACADE_H
    rng = np.random.default_rng(5)
    stone = np.array([206, 186, 146], float)
    img = np.zeros((N, N, 3)) + stone
    hgt = np.zeros((N, N))
    yy, xx = np.mgrid[0:N, 0:N]
    Z = (N - 1 - yy) / ppm          # 公尺（由下往上）
    X = xx / ppm

    def rect(x0, x1, z0, z1, col=None, h=None, alpha=1.0):
        for k in range(5):
            o = k * BAY
            m = (X >= o + x0) & (X < o + x1) & (Z >= z0) & (Z < z1)
            if col is not None:
                img[m] = img[m] * (1 - alpha) + np.array(col, float) * alpha
            if h is not None:
                hgt[m] = h

    def band(z0, z1, col=None, h=None):
        m = (Z >= z0) & (Z < z1)
        if col is not None:
            img[m] = col
        if h is not None:
            hgt[m] = h

    def arch(cx, w, z0, spring, col, h):
        for k in range(5):
            o = k * BAY
            r = w / 2
            m = (np.abs(X - (o + cx)) < r) & (Z >= z0) & ((Z < spring) | ((X - (o + cx)) ** 2 + (Z - spring) ** 2 < r * r))
            img[m] = col
            hgt[m] = h

    c = BAY / 2
    # 勒腳與底層粗面石（水平凹縫）
    band(0, 0.9, (196, 182, 150), 0.3)
    groove = ((Z % 0.55) < 0.05) & (Z < 7.4)
    img[groove] *= 0.82
    hgt[groove] = -0.15
    # 底層拱廊
    arch(c, 2.7, 0.0, 5.0, (70, 62, 52), -1.0)
    arch(c, 2.1, 0.0, 4.7, (48, 44, 40), -1.2)
    # 拱心石
    rect(c - 0.25, c + 0.25, 6.2, 6.9, (230, 214, 180), 0.4)
    # 底層簷帶
    band(7.4, 7.6, (175, 160, 128), -0.2)
    band(7.6, 8.4, (236, 220, 186), 0.6)
    # 主樓層：雙壁柱、窗、山牆
    rect(0.05, 0.55, 8.4, 15.0, (232, 216, 182), 0.35)
    rect(BAY - 0.55, BAY - 0.05, 8.4, 15.0, (232, 216, 182), 0.35)
    rect(0.52, 0.6, 8.4, 15.0, (176, 160, 128), -0.1)
    rect(BAY - 0.6, BAY - 0.52, 8.4, 15.0, (176, 160, 128), -0.1)
    rect(c - 1.15, c + 1.15, 9.1, 13.8, (238, 224, 192), 0.25)        # 窗框
    rect(c - 0.9, c + 0.9, 9.3, 13.6, (58, 63, 72), -0.8)              # 玻璃
    rect(c - 0.05, c + 0.05, 9.3, 13.6, (226, 220, 206), -0.5)         # 中梃
    for zz in (10.9, 12.3):
        rect(c - 0.9, c + 0.9, zz, zz + 0.07, (226, 220, 206), -0.5)
    for k in range(5):                                                   # 三角山牆
        o = k * BAY
        m = (Z >= 14.0) & (Z < 14.0 + 0.9 * (1 - np.abs(X - (o + c)) / 1.4)) & (np.abs(X - (o + c)) < 1.4)
        img[m] = (240, 226, 194)
        hgt[m] = 0.5
    rect(c - 1.4, c + 1.4, 13.85, 14.05, (165, 150, 120), -0.2)
    band(15.0, 15.25, (172, 156, 124), -0.2)
    band(15.25, 15.9, (236, 220, 186), 0.5)
    # 閣樓層
    rect(c - 0.85, c + 0.85, 16.3, 18.9, (238, 224, 192), 0.25)
    rect(c - 0.65, c + 0.65, 16.5, 18.7, (58, 63, 72), -0.8)
    rect(c - 0.04, c + 0.04, 16.5, 18.7, (226, 220, 206), -0.5)
    # 主簷口（下方陰影）＋欄杆
    band(19.2, 19.5, (150, 135, 105), -0.3)
    band(19.5, 20.6, (240, 226, 194), 0.9)
    band(20.6, 20.75, (176, 160, 128), 0.2)
    band(20.75, 21.0, (232, 216, 182), 0.6)
    bal = (Z >= 21.0) & (Z < 21.9) & (((X * 3.2) % 1.0) > 0.45)
    img[bal] *= 0.72
    hgt[bal] = -0.4
    band(21.9, 22.0, (236, 220, 186), 0.5)
    # 石材雜訊與髒污
    noise = rng.standard_normal((N // 16, N // 16))
    noise = np.kron(noise, np.ones((16, 16)))
    img *= (1 + 0.035 * noise + 0.02 * rng.standard_normal((N, N)))[..., None]
    img *= (0.9 + 0.1 * np.clip(Z / 6.0, 0, 1))[..., None]
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(os.path.join(d, "diff.jpg"), quality=88)
    # 法線
    hs = hgt
    dx = (np.roll(hs, -1, 1) - np.roll(hs, 1, 1)) * 1.4
    dy = (np.roll(hs, -1, 0) - np.roll(hs, 1, 0)) * 1.4
    n = np.stack([-dx, dy, np.ones_like(hs)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    Image.fromarray((np.clip(n * 0.5 + 0.5, 0, 1) * 255).astype(np.uint8)).save(os.path.join(d, "nor.jpg"), quality=90)
    return "_gen/louvre_v1/facade"


# ====================================================================== 工具
def bar(b, mi, p0, p1, t):
    """兩點間的細方桿"""
    p0, p1 = Vector(p0), Vector(p1)
    v = p1 - p0
    L = v.length
    if L < 1e-4:
        return
    q = v.normalized().to_track_quat("Z", "Y")
    M = Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4() @ Matrix.Diagonal((t, t, L, 1))
    r = bmesh.ops.create_cube(b.bm, size=1.0, matrix=M)
    b._assign(r["verts"], mi)


def glass_pyramid(b, glass, frame, cx, cy, base, h, n):
    """玻璃金字塔：四面三角玻璃＋菱形格框（兩組平行於斜稜的桿件）＋底框"""
    a = base / 2
    apex = Vector((cx, cy, h))
    corners = [Vector((cx - a, cy - a, 0)), Vector((cx + a, cy - a, 0)), Vector((cx + a, cy + a, 0)), Vector((cx - a, cy + a, 0))]
    for i in range(4):
        c0, c1 = corners[i], corners[(i + 1) % 4]
        vs = [b.bm.verts.new(p) for p in (c0, c1, apex)]
        f = b.bm.faces.new(vs)
        f.material_index = glass
        # 菱形格：沿 c0→c1 等分，畫平行於兩條斜稜的線
        for k in range(1, n):
            t = k / n
            p = c0.lerp(c1, t)
            # 平行於 c1→apex 的線：從 p 到 c0→apex 上對應點
            q1 = c0.lerp(apex, t)
            q2 = c1.lerp(apex, 1 - t)
            off = (p - Vector((cx, cy, p.z))).normalized() * 0.06 + Vector((0, 0, 0))
            bar(b, frame, p + off, q1 + off, 0.11)
            bar(b, frame, p + off, q2 + off, 0.11)
        bar(b, frame, c0, apex, 0.22)
        bar(b, frame, c0, c1, 0.3)


def square_radial(t):
    return math.cos(math.pi / 4) / max(abs(math.cos(t)), abs(math.sin(t)))


# ====================================================================== 主體
def louvre(path):
    fac_id = gen_facade()
    b = Builder("Louvre", seed=11)
    bm = b.bm
    facade = b.tex("facade", fac_id, tile=FACADE_H, rough=0.75, normal=1.0)
    stone = b.tex("stone", "white_sandstone_blocks_02", tile=3.0, tint="#cdb68c", rough=0.8, normal=0.5)
    stone_l = b.color("stone_light", "#d6c19a", rough=0.75)
    slate = b.tex("slate", "grey_roof_tiles", tile=2.5, tint="#5b6470", gain=1.0, rough=0.6, normal=0.8)
    lead = b.color("lead", "#4d5560", rough=0.45, metal=0.5)
    gilt = b.color("gilt", "#c9a24c", rough=0.3, metal=0.9)
    win = b.color("window", "#3a3f47", rough=0.2)
    glass = b.color("glass", "#b4c3cd", rough=0.03, metal=0.2, alpha=0.5)
    frame = b.color("steel", "#6f777e", rough=0.35, metal=0.8)
    pave = b.tex("pave", "gravel_floor", tile=2.0, tint="#9d9a93", rough=0.85, normal=0.3)
    slab = b.color("granite", "#77746f", rough=0.7)
    rim = b.color("rim", "#b9b6b0", rough=0.6)
    water = b.color("water", "#2f3b42", rough=0.04)
    soil = b.color("soil", "#6b5a45", rough=0.95)

    T = lambda x, y, z=0.0: Matrix.Translation((x, y, z))  # noqa: E731
    Rz = lambda a: Matrix.Rotation(a, 4, "Z")  # noqa: E731

    # ---------------------------------------------------------------- 地面
    b.ground_disc(pave, 210, soil, depth=2, rings=10, seg=72)
    # 花崗岩分隔帶（大方格）
    for k in range(-6, 7):
        b.box_base(slab, (0.5, 240, 0.03), (k * 16.0, 0, 0))
        b.box_base(slab, (240, 0.5, 0.02), (0, k * 16.0, 0))

    # ---------------------------------------------------------------- 金字塔與水池
    glass_pyramid(b, glass, frame, 0, 0, 35.42, 21.64, 24)
    for x, y in ((0, 28.0), (0, -28.0), (28.0, 0)):
        glass_pyramid(b, glass, frame, x, y, 8.0, 4.9, 5)
    # 不鏽鋼底座
    b.box_base(rim, (36.6, 36.6, 0.35), (0, 0, 0))
    # 七座三角形水池（以方形廣場對角分割）
    S = 34.0
    pools = [((19, 19), (S + 15, 19), (19, S + 15)), ((-9, 21), (9, 21), (0, 46)),
             ((21, -19), (21, -S - 10), (S + 12, -19)), ((22, 5), (22, -5), (36, 0))]
    for tri in pools:
        b.prism(rim, list(tri), 0.0, 0.55)
        cxp = sum(p[0] for p in tri) / 3
        cyp = sum(p[1] for p in tri) / 3
        inner = [(cxp + (p[0] - cxp) * 0.9, cyp + (p[1] - cyp) * 0.9) for p in tri]
        b.prism(water, inner, 0.0, 0.6)

    # ---------------------------------------------------------------- 翼樓
    D = 22.0           # 翼樓進深
    H = FACADE_H       # 簷口＋欄杆頂
    YN, YS, XE = 66.0, -66.0, 82.0
    X_W = -150.0

    def wing(x0, x1, y0, y1):
        """x0..x1 × y0..y1 的長方翼樓＋複折式屋頂（沿長邊）"""
        w, d = x1 - x0, y1 - y0
        b.box_base(facade, (w, d, H), ((x0 + x1) / 2, (y0 + y1) / 2, 0))
        along_x = w >= d
        L, Dd = (w, d) if along_x else (d, w)
        M = T((x0 + x1) / 2, (y0 + y1) / 2, H) @ (Rz(0) if along_x else Rz(math.pi / 2))
        hd = Dd / 2
        prof = [(-hd + 0.6, 0), (hd - 0.6, 0), (hd - 2.2, 6.0), (hd - 4.2, 7.6), (-hd + 4.2, 7.6), (-hd + 2.2, 6.0)]
        # profile_wall：u 沿局部 X → 需要沿長軸擠出，所以再轉 90°
        b.profile_wall(slate, prof, L - 0.4, M @ Rz(math.pi / 2))
        # 老虎窗：每開間一個，兩側
        n = int(L / BAY)
        for k in range(n):
            u = -L / 2 + BAY * (k + 0.5)
            for s in (-1, 1):
                Md = M @ T(u, s * (hd - 2.0), 1.4) @ (Rz(0) if s < 0 else Rz(math.pi))
                b.profile_wall(stone_l, [(-0.8, 0), (0.8, 0), (0.8, 2.4), (0, 3.2), (-0.8, 2.4)], 1.6, Md)
                b.profile_wall(win, [(-0.5, 0.3), (0.5, 0.3), (0.5, 2.0), (-0.5, 2.0)], 0.1, Md @ T(0, -0.81, 0))
            if k % 4 == 2:   # 煙囪
                b.box_base(stone_l, (1.4, 0.8, 2.6), tuple(M @ Vector((u, 0, 7.2))))

    def pavilion(cx, cy, w, d, h, roof_h, dome=True):
        b.box_base(facade, (w, d, H), (cx, cy, 0))
        b.box_base(stone, (w, d, h - H), (cx, cy, H))
        b.box_base(stone_l, (w + 0.8, d + 0.8, 0.8), (cx, cy, h - 0.8))
        # 上層窗與山牆（四面）
        for ang in (0, math.pi / 2, math.pi, -math.pi / 2):
            face_w = w if ang in (0, math.pi) else d
            off = d / 2 if ang in (0, math.pi) else w / 2
            Mf = T(cx, cy, 0) @ Rz(ang) @ T(0, -off - 0.02, 0)
            for k in range(3):
                u = -face_w / 4 + face_w / 4 * k
                b.profile_wall(win, [(-0.8, 0), (0.8, 0), (0.8, 2.6), (0, 3.3), (-0.8, 2.6)], 0.12, Mf @ T(u, 0, H + 0.8))
            # 弧形山牆（以三角形近似）
            b.profile_wall(stone_l, [(-face_w * 0.3, 0), (face_w * 0.3, 0), (0, 3.6)], 1.2, Mf @ T(0, -0.3, h))
            # 雙柱（主樓層）
            for u in (-face_w * 0.3, -face_w * 0.22, face_w * 0.22, face_w * 0.3):
                b.cyl(stone_l, 0.38, 0.34, 7.0, tuple(Mf @ Vector((u, -0.45, 8.3))), seg=10)
        # 方形穹頂
        prof = [(max(w, d) * 0.72, 0)]
        R0 = min(w, d) * 0.5 * math.sqrt(2) * 0.96
        for i in range(1, 9):
            t = i / 8
            prof.append((R0 * math.cos(t * math.pi / 2) ** 0.8 + 0.6, roof_h * math.sin(t * math.pi / 2)))
        prof[0] = (R0 + 0.6, 0)
        prof[-1] = (1.4, roof_h)
        b.lathe(slate, prof + [(0.0, roof_h)], (cx, cy, h), seg=32, smooth=True, radial=square_radial, rot_offset=0.0)
        b.lathe(lead, [(1.6, h + roof_h - 0.1), (1.6, h + roof_h + 1.0), (0.9, h + roof_h + 1.3), (0.0, h + roof_h + 1.8)], (cx, cy, 0), seg=8)
        b.ico(gilt, 0.4, (cx, cy, h + roof_h + 2.1), subdiv=1)
        # 屋頂裝飾群像（簡化為一組石塊）
        for sx in (-1, 1):
            b.rock(stone_l, (1.2, 1.0, 2.2), (cx + sx * w * 0.38, cy, h + 1.0), rough=0.2, subdiv=2, seed=int(cx + sx * 7) % 97)

    # 北翼（黎塞留）、南翼（德農）
    wing(X_W, XE - D, YN, YN + D)
    wing(X_W, XE - D, YS - D, YS)
    # 東翼（敘利，中央為鐘樓館）
    wing(XE - D, XE, YS - D, YN + D)
    # 樓閣：北、南翼中央；三個轉角；東側鐘樓館
    for cy_ in (YN + D / 2, YS - D / 2):
        pavilion(-30.0, cy_, 28.0, D + 4.0, 29.0, 9.0)
        pavilion(-118.0, cy_, 24.0, D + 3.0, 27.0, 8.0)
        pavilion(XE - D / 2, cy_, D + 4.0, D + 4.0, 29.0, 9.0)
    pavilion(XE - D / 2 + 1.0, 0.0, D + 6.0, 30.0, 33.0, 13.0)   # 鐘樓館

    # 西側：連接卡魯塞爾的較低翼樓（僅短段）
    for cy_ in (YN + D / 2, YS - D / 2):
        b.box_base(facade, (40.0, D, H), (X_W - 20.0, cy_, 0))
        b.profile_wall(slate, [(-D / 2 + 0.6, 0), (D / 2 - 0.6, 0), (D / 2 - 2.2, 6.0), (D / 2 - 4.2, 7.6), (-D / 2 + 4.2, 7.6),
                               (-D / 2 + 2.2, 6.0)], 40.0, T(X_W - 20.0, cy_, H) @ Rz(math.pi / 2))

    # ---------------------------------------------------------------- 路燈與人行動線點綴
    for k in range(10):
        x = -120 + k * 20
        for y in (YN - 6, YS + 6):
            b.cyl(lead, 0.09, 0.07, 4.2, (x, y, 0), seg=6)
            b.box_base(gilt, (0.4, 0.4, 0.6), (x, y, 4.2))

    b.export(path)
