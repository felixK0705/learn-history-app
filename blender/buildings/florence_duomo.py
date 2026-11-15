"""florence_duomo 佛羅倫斯聖母百花大教堂（Santa Maria del Fiore）寫實模型（公尺）

- 全長約 153 m；中殿連側廊寬約 41 m，側廊外牆高約 24 m，中殿高側窗牆約 38 m（圓形高窗），屋脊約 45 m
- 十字交會處為八角形結構：八角鼓座（每面一個大圓窗）頂約 55 m；布魯內萊斯基圓頂為「尖五分」
  八角迴廊拱頂，外部頂高約 91 m，8 條白色大理石稜、紅陶瓦面；燈籠亭連金球十字至 114.5 m
- 北、南、東三座多邊形後殿（tribune），各帶放射狀小禮拜堂與紅瓦圓頂；斜面上的四座「死後殿」小半圓室
- 喬托鐘樓：14.45 m 方形、高 84.7 m，位於立面南側；西側八角形聖若望洗禮堂
- 外牆為白（卡拉拉）、綠（普拉托）、粉紅（馬雷馬）三色大理石鑲板

座標：+X 東、+Y 北，圓頂中心在原點。參考照由南方高處（舊宮塔方向）以長焦拍攝。
"""

import math
import os

from mathutils import Matrix

from lib import TAU, TEX, Builder

from .hagia_sophia import broadleaf, cypress, foliage_mats

CAMERA = ((-34, 0, 40), 4, 11, 540, 85)

GEN = os.path.join(TEX, "_gen", "florence_v1")


# ====================================================================== 自產大理石鑲板貼圖
def gen_textures():
    """三色大理石鑲板（白底、綠框、粉紅嵌板）；兩種：教堂牆面（8 m 一循環）與鐘樓（7.2 m）"""
    import numpy as np
    from PIL import Image

    os.makedirs(GEN, exist_ok=True)
    outs = {}
    rng = np.random.default_rng(7)
    N = 1024
    white = np.array([236, 231, 220], float)
    green = np.array([70, 92, 80], float)
    pink = np.array([214, 160, 146], float)

    def base_noise():
        w = rng.standard_normal((N // 8, N // 8))
        w = np.kron(w, np.ones((8, 8)))
        fine = rng.standard_normal((N, N))
        return w * 4 + fine * 3

    def paint(img, x0, y0, x1, y1, col, px_per_m):
        a, b_ = int(y0 * px_per_m), int(y1 * px_per_m)
        c, d = int(x0 * px_per_m), int(x1 * px_per_m)
        img[N - b_:N - a, c:d] = col

    # ---- 教堂牆面：8 m × 8 m
    for name, size, recipe in (("wall", 8.0, "wall"), ("tower", 7.2, "tower")):
        out = os.path.join(GEN, f"{name}", "diff.jpg")
        outs[name] = f"_gen/florence_v1/{name}"
        if os.path.exists(out):
            continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        ppm = N / size
        img = np.zeros((N, N, 3)) + white
        if recipe == "wall":
            for cx in (0.0, 4.0):
                # 綠色壁柱條
                paint(img, cx, 0, cx + 0.35, size, green, ppm)
                # 下格：粉紅嵌板＋綠框
                paint(img, cx + 0.8, 0.6, cx + 3.55, 3.4, green, ppm)
                paint(img, cx + 0.95, 0.75, cx + 3.4, 3.25, white, ppm)
                paint(img, cx + 1.25, 1.05, cx + 3.1, 2.95, pink, ppm)
                # 上格：細長綠框
                paint(img, cx + 0.9, 4.3, cx + 3.45, 7.6, green, ppm)
                paint(img, cx + 1.02, 4.42, cx + 3.33, 7.48, white, ppm)
                paint(img, cx + 1.6, 4.9, cx + 2.75, 7.0, green, ppm)
                paint(img, cx + 1.7, 5.0, cx + 2.65, 6.9, white, ppm)
            for z, h, col in ((0.0, 0.3, green), (3.8, 0.22, green), (4.02, 0.12, pink), (7.85, 0.15, green)):
                paint(img, 0, z, size, z + h, col, ppm)
        else:
            # 鐘樓：粉紅與綠色水平帶、方形嵌板
            for z in (0.0, 3.6):
                paint(img, 0, z, size, z + 0.25, green, ppm)
                paint(img, 0, z + 0.25, size, z + 0.42, pink, ppm)
                for cx in (0.3, 2.7, 5.1):
                    paint(img, cx, z + 0.8, cx + 1.8, z + 3.2, green, ppm)
                    paint(img, cx + 0.12, z + 0.92, cx + 1.68, z + 3.08, pink if cx == 2.7 else white, ppm)
                    paint(img, cx + 0.5, z + 1.3, cx + 1.3, z + 2.7, green, ppm)
                    paint(img, cx + 0.58, z + 1.38, cx + 1.22, z + 2.62, white, ppm)
        img += base_noise()[..., None]
        Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(out, quality=88)
    outs.setdefault("wall", "_gen/florence_v1/wall")
    outs.setdefault("tower", "_gen/florence_v1/tower")
    return outs


# ====================================================================== 幾何工具
def oct_radial(offset=0.0):
    """八角形徑向倍率：角點 = 1，面中心 = cos(π/8)；offset 為第一個角點的角度"""
    c8 = math.cos(math.pi / 8)

    def f(t):
        d = (t - offset) % (math.pi / 4) - math.pi / 8
        return c8 / math.cos(d)

    return f


def oct_prism(b, mi, R, z0, z1, center=(0, 0), seg=8):
    """正八角柱（R 為角點半徑），面朝四正方向"""
    cx, cy = center
    pts = [(cx + R * math.cos(math.pi / 8 + TAU * k / 8), cy + R * math.sin(math.pi / 8 + TAU * k / 8)) for k in range(8)]
    return b.prism(mi, pts, z0, z1 - z0)


def pointed_profile(Rc, rise_scale=1.0, r_top=0.0, n=14, fifth=0.8):
    """尖五分拱剖面（角點方向）：圓心在對側，半徑 = fifth × 直徑"""
    rho = fifth * 2 * Rc
    xc = Rc - rho
    pts = []
    r_end = max(r_top, 1e-3)
    for i in range(n + 1):
        r = Rc - (Rc - r_end) * (i / n) ** 0.9
        z = math.sqrt(max(0.0, rho * rho - (r - xc) ** 2)) * rise_scale
        pts.append((r, z))
    return pts


def band_strip(b, mi, prof, ang, width, thick, z0, inset=0.15):
    """沿剖面（r, z）在 ang 方向掃出一條稜（白色大理石肋）"""
    ca, sa = math.cos(ang), math.sin(ang)
    for (r0, za), (r1, zb) in zip(prof, prof[1:]):
        M = Matrix.Translation((0, 0, z0)) @ Matrix.Rotation(ang - math.pi / 2, 4, "Z")
        # 在局部座標：u 為徑向（沿 +Y 轉到 ang），用 profile_wall 的 (u, v)
        pts = [(r0 - inset, za), (r1 - inset, zb), (r1 + thick, zb + 0.0), (r0 + thick, za)]
        # profile_wall 以局部 X 為 u，故先旋轉使局部 X 指向 ang
        M2 = Matrix.Translation((0, 0, z0)) @ Matrix.Rotation(ang, 4, "Z")
        poly = [(u, v) for u, v in pts]
        # 保持逆時針
        area = sum(poly[i][0] * poly[(i + 1) % 4][1] - poly[(i + 1) % 4][0] * poly[i][1] for i in range(4))
        if area < 0:
            poly.reverse()
        b.profile_wall(mi, poly, width, M2)
    _ = (ca, sa, M)


def gothic_window(b, mi, w, h, M, depth=0.15, kind="pointed"):
    """尖拱窗（深色）；M：局部 X 水平、Z 垂直、面朝 -Y"""
    arc = b.arch_points(w, h - w * 0.62, kind, seg=8)
    pts = [(-w / 2, 0), (w / 2, 0)] + list(reversed(arc))[1:-1]
    pts = [(-w / 2, 0), (w / 2, 0)] + [p for p in reversed(arc)][0:]
    # 去除重複點
    clean = []
    for p in pts:
        if not clean or (abs(p[0] - clean[-1][0]) > 1e-4 or abs(p[1] - clean[-1][1]) > 1e-4):
            clean.append(p)
    if abs(clean[0][0] - clean[-1][0]) < 1e-4 and abs(clean[0][1] - clean[-1][1]) < 1e-4:
        clean.pop()
    b.profile_wall(mi, clean, depth, M)


def disc_window(b, mi, r, M, depth=0.2, seg=20, frame=None, fw=0.6):
    """圓窗（oculus）：深色圓盤＋白框；M 面朝 -Y"""
    R = M @ Matrix.Rotation(math.pi / 2, 4, "X")
    if frame is not None:
        b.cyl(frame, r + fw, r + fw, depth * 0.6, (0, 0, 0), seg=seg)
        vs = b.bm.verts[-2 * seg:]
        import bmesh

        b.bm.verts.ensure_lookup_table()
        bmesh.ops.transform(b.bm, matrix=R @ Matrix.Translation((0, 0, -depth * 0.3)), verts=list(vs))
    b.cyl(mi, r, r, depth, (0, 0, 0), seg=seg)
    import bmesh

    b.bm.verts.ensure_lookup_table()
    bmesh.ops.transform(b.bm, matrix=R @ Matrix.Translation((0, 0, -depth * 0.2)), verts=list(b.bm.verts[-2 * seg:]))


def pyramid_roof(b, mi, w, d, h, base, rot_z=0.0, overhang=0.5):
    """四坡屋頂（帶出簷）"""
    b.frustum(mi, (w + 2 * overhang, d + 2 * overhang), (max(0.2, w - d) if w > d else 0.2, 0.2 if w > d else max(0.2, d - w)), h, base,
              rot_z=rot_z)


# ====================================================================== 主體
def florence_duomo(path):
    tex = gen_textures()
    b = Builder("FlorenceDuomo", seed=17)
    bm = b.bm
    marble = b.tex("marble", tex["wall"], tile=8.0, rough=0.55, normal=0)
    tmarble = b.tex("tower_marble", tex["tower"], tile=7.2, rough=0.55, normal=0)
    white = b.tex("white", "marble_01", tile=4.0, tint="#e9e4d8", rough=0.5, normal=0.3)
    green = b.color("green_marble", "#4a5f52", rough=0.45)
    pinkm = b.color("pink_marble", "#d29e90", rough=0.5)
    tiles = b.tex("tiles", "grey_roof_tiles", tile=3.0, tint="#ad5b3b", gain=1.0, rough=0.85, normal=0.8)
    tiles_d = b.tex("tiles_d", "grey_roof_tiles", tile=3.0, tint="#a8573a", gain=0.95, rough=0.85, normal=0.8)
    drum_c = b.color("drum_stone", "#cdbb9c", rough=0.8)
    win = b.color("window", "#2b2827", rough=0.35)
    gold = b.color("gold", "#d2a640", rough=0.25, metal=1.0)
    copper = b.color("bronze", "#6b5a3f", rough=0.5, metal=0.6)
    pave = b.tex("pave", "gravel_floor", tile=3.0, tint="#a39a8d", rough=0.9, normal=0.3)
    street = pave
    soil = b.color("soil", "#6b5a45", rough=0.95)
    plasters = [b.tex(f"plaster{k}", "plastered_wall_04", tile=6.0, tint=c, rough=0.9, normal=0.5)
                for k, c in enumerate(("#e0c49a", "#e8dcc4"))]
    plasters += [b.tex("plaster_c", "plastered_wall_04", tile=6.0, tint="#cfa27c", rough=0.9, normal=0.5)]
    roof_c = b.tex("roof_c", "red_sandstone_tiles", tile=4.0, tint="#a2604a", rough=0.85, normal=0.6)
    leaves = foliage_mats(b)
    trunk = b.color("trunk", "#5a4a3a", rough=0.9)
    cyp = b.color("cypress", "#2c4020", rough=0.9)

    T = lambda x, y, z=0.0: Matrix.Translation((x, y, z))  # noqa: E731
    Rz = lambda a: Matrix.Rotation(a, 4, "Z")  # noqa: E731

    # ---------------------------------------------------------------- 地面：廣場＋街道
    b.ground_disc(street, 235, soil, depth=3, rings=12, seg=72)
    b.box_base(pave, (230, 110, 0.12), (-60, -2, 0))
    b.box_base(pave, (70, 150, 0.08), (10, 0, 0))

    # ---------------------------------------------------------------- 中殿與側廊
    XF, XC = -101.0, -24.0      # 立面、八角形起點
    YA, YN = 20.5, 10.5         # 側廊外牆、中殿高牆
    H_A, H_N = 24.0, 38.0
    L = XC - XF
    b.box_base(marble, (L, 2 * YA, H_A), ((XF + XC) / 2, 0, 0))
    b.box_base(green, (L + 0.6, 2 * YA + 0.6, 0.6), ((XF + XC) / 2, 0, H_A - 0.6))     # 簷口
    b.box_base(white, (L + 1.2, 2 * YA + 1.2, 0.5), ((XF + XC) / 2, 0, H_A))
    b.box_base(green, (L + 0.4, 2 * YA + 0.4, 1.2), ((XF + XC) / 2, 0, 0))              # 勒腳
    # 側廊單坡屋頂
    for s in (-1, 1):
        prof = [(s * YA * 1.0 + s * 0.6, 0), (s * YN, 0), (s * YN, 3.4)]
        if s > 0:
            prof = [(YN, 0), (YA + 0.6, 0), (YN, 3.4)]
        else:
            prof = [(-YA - 0.6, 0), (-YN, 0), (-YN, 3.4)]
        b.profile_wall(tiles, prof, L, T((XF + XC) / 2, 0, H_A + 0.5) @ Rz(-math.pi / 2))
    # 側廊外牆：四個開間，每間一扇細長尖窗與壁柱
    bay = L / 4
    for s in (-1, 1):
        R = Rz(0 if s < 0 else math.pi)
        for k in range(5):
            x = XF + bay * k
            b.box_base(white, (1.6, 1.2, H_A), (x + (0.8 if k == 0 else (-0.8 if k == 4 else 0)), s * (YA + 0.4), 0))
        for k in range(4):
            x = XF + bay * (k + 0.5)
            M = T(x, s * (YA + 0.08), 11.5) @ R
            if s < 0:
                M = T(x, -(YA + 0.08), 11.5)
            else:
                M = T(x, YA + 0.08, 11.5) @ Rz(math.pi)
            gothic_window(b, win, 2.0, 9.0, M, depth=0.2)
            # 側門（南北各兩座）帶三角山牆
            if k in (1, 3):
                xd = x - bay * 0.32
                Md = T(xd, -(YA + 0.5), 0) if s < 0 else T(xd, YA + 0.5, 0) @ Rz(math.pi)
                b.profile_wall(white, [(-3.0, 0), (3.0, 0), (3.0, 9.0), (0, 13.0), (-3.0, 9.0)], 1.4, Md)
                b.profile_wall(pinkm, [(-2.2, 9.4), (2.2, 9.4), (0, 12.2)], 1.5, Md)
                gothic_window(b, win, 2.6, 7.0, Md @ T(0, -0.72, 0), depth=0.1)
    # 中殿高牆（圓形高窗）與雙坡屋頂
    b.box_base(marble, (L, 2 * YN, H_N - H_A), ((XF + XC) / 2, 0, H_A))
    b.box_base(green, (L + 0.5, 2 * YN + 0.5, 0.5), ((XF + XC) / 2, 0, H_N - 0.5))
    b.box_base(white, (L + 1.0, 2 * YN + 1.0, 0.45), ((XF + XC) / 2, 0, H_N))
    for k in range(4):
        x = XF + bay * (k + 0.5)
        for s in (-1, 1):
            M = T(x, -(YN + 0.05), 31.5) if s < 0 else T(x, YN + 0.05, 31.5) @ Rz(math.pi)
            disc_window(b, win, 1.6, M, depth=0.3, seg=20, frame=white, fw=0.55)
    b.profile_wall(tiles, [(-YN - 0.8, 0), (YN + 0.8, 0), (0, 7.2)], L + 0.8, T((XF + XC) / 2 + 0.4, 0, H_N + 0.45) @ Rz(-math.pi / 2))

    # ---------------------------------------------------------------- 立面（新哥德式）
    Mf = T(XF - 1.0, 0, 0) @ Rz(-math.pi / 2)   # 局部 -Y 朝西
    b.profile_wall(marble, [(-YA - 1, 0), (YA + 1, 0), (YA + 1, 31.0), (-YA - 1, 31.0)], 2.0, Mf)
    b.profile_wall(marble, [(-YN - 1, 31.0), (YN + 1, 31.0), (YN + 1, 44.0), (0, 52.0), (-YN - 1, 44.0)], 2.0, Mf)
    for u in (-YA - 0.5, -YN - 0.6, YN + 0.6, YA + 0.5):     # 扶壁柱＋尖塔
        top = 34.0 if abs(u) > 15 else 49.0
        b.box_base(white, (2.4, 2.4, top), (XF - 2.0, u, 0))
        b.cone(white, 1.5, 4.0, (XF - 2.0, u, top), seg=4, rot=(0, 0, math.pi / 4))
    for u, w, h in ((0, 5.0, 13.0), (-14.5, 3.6, 9.5), (14.5, 3.6, 9.5)):    # 三座大門
        Mp = Mf @ T(u, -1.2, 0)
        b.profile_wall(white, [(-w / 2 - 1.4, 0), (w / 2 + 1.4, 0), (w / 2 + 1.4, h), (0, h + w * 0.9), (-w / 2 - 1.4, h)], 1.2, Mp)
        b.profile_wall(pinkm, [(-w / 2 - 0.4, h + 0.3), (w / 2 + 0.4, h + 0.3), (0, h + w * 0.75)], 1.3, Mp)
        gothic_window(b, copper, w, h - 0.5, Mp @ T(0, -0.62, 0.2), depth=0.1)
    disc_window(b, win, 3.6, Mf @ T(0, -1.05, 37.5), depth=0.3, seg=28, frame=white, fw=1.0)    # 玫瑰窗
    for u in (-15.0, 15.0):
        gothic_window(b, win, 2.0, 6.5, Mf @ T(u, -1.05, 19.0), depth=0.15)

    # ---------------------------------------------------------------- 八角形結構與鼓座
    A_OCT = 27.0                                  # 鼓座外側面心距
    RC = A_OCT / math.cos(math.pi / 8)            # 角點半徑
    Z_DR0, Z_DR1 = 33.0, 53.0
    oct_prism(b, marble, RC - 1.0, 0, Z_DR0)
    oct_prism(b, white, RC + 0.4, Z_DR0 - 0.8, Z_DR0)
    oct_prism(b, marble, RC, Z_DR0, Z_DR1)
    oct_prism(b, green, RC + 0.35, Z_DR0 + 0.0, Z_DR0 + 1.0)
    oct_prism(b, green, RC + 0.35, Z_DR1 - 1.4, Z_DR1 - 0.6)
    # 鼓座頂的未完成迴廊（ballatoio）：只有東南面做了白色拱廊，其餘為粗石
    oct_prism(b, drum_c, RC - 0.2, Z_DR1, Z_DR1 + 3.0)
    oct_prism(b, white, RC + 0.3, Z_DR1 - 0.6, Z_DR1)
    for k in range(8):
        a = TAU * k / 8                  # 面心方向（0 = 東）
        M = T(math.cos(a) * (A_OCT + 0.05), math.sin(a) * (A_OCT + 0.05), 43.5) @ Rz(a + math.pi / 2)
        disc_window(b, win, 2.6, M, depth=0.3, seg=24, frame=white, fw=0.9)
        # 角柱（白色）
        ac = a + math.pi / 8
        b.box_base(white, (1.4, 1.4, Z_DR1 - Z_DR0), (math.cos(ac) * (RC + 0.1), math.sin(ac) * (RC + 0.1), Z_DR0), rot=(0, 0, ac))
        if k in (6, 7):  # 東南面：白色小拱廊
            for j in range(7):
                u = -A_OCT * 0.36 + A_OCT * 0.72 * (j + 0.5) / 7
                Mg = T(math.cos(a) * (A_OCT + 0.2), math.sin(a) * (A_OCT + 0.2), Z_DR1) @ Rz(a + math.pi / 2) @ T(u, 0, 0)
                b.arch_frame(white, A_OCT * 0.72 / 7, 3.0, 1.6, 1.2, 0.5, Mg, kind="round")

    # ---------------------------------------------------------------- 布魯內萊斯基圓頂
    Z_D = Z_DR1 + 3.0
    R_LANT = 5.6
    prof = pointed_profile(RC + 0.2, rise_scale=0.8, r_top=R_LANT, n=16)
    z_top_dome = prof[-1][1]
    radial = oct_radial(math.pi / 8)
    b.lathe(tiles, prof + [(0.0, z_top_dome)], (0, 0, Z_D), seg=64, smooth=True, rot_offset=0.0, radial=radial)
    for k in range(8):           # 白色大理石稜
        band_strip(b, white, prof, math.pi / 8 + TAU * k / 8, 1.9, 0.75, Z_D, inset=0.25)
    # 屋面上的小圓窗（每面一個）
    for k in range(8):
        a = TAU * k / 8
        r = A_OCT * 0.62
        zr = Z_D + 0.93 * math.sqrt((0.8 * 2 * (RC + 0.2)) ** 2 - (r / math.cos(0) - (RC + 0.2 - 1.6 * (RC + 0.2))) ** 2) + 0.2
        _ = zr
    Z_L = Z_D + z_top_dome
    # 燈籠亭
    oct_prism(b, white, R_LANT + 0.6, Z_L - 0.4, Z_L + 0.8)
    oct_prism(b, white, R_LANT - 1.2, Z_L + 0.8, Z_L + 10.0)
    for k in range(8):
        a = math.pi / 8 + TAU * k / 8
        # 外伸扶壁（帶渦卷的斜扶壁簡化為楔形）
        Mb = T(math.cos(a) * (R_LANT - 1.5), math.sin(a) * (R_LANT - 1.5), Z_L + 0.8) @ Rz(a - math.pi / 2)
        b.profile_wall(white, [(-0.0, 0), (0.0, 0)][:0] + [(0, 0), (2.8, 0), (2.8, 1.5), (0.6, 8.8), (0, 9.2)], 0.9,
                       Mb @ Matrix.Rotation(math.pi / 2, 4, "Z"))
        af = TAU * k / 8
        M = T(math.cos(af) * (R_LANT - 1.15), math.sin(af) * (R_LANT - 1.15), Z_L + 2.5) @ Rz(af + math.pi / 2)
        gothic_window(b, win, 1.2, 5.6, M, depth=0.1, kind="round")
    oct_prism(b, white, R_LANT - 0.6, Z_L + 10.0, Z_L + 11.0)
    b.lathe(white, [(R_LANT - 1.3, Z_L + 11.0), (2.0, Z_L + 14.5), (0.9, Z_L + 17.0), (0.5, Z_L + 18.2)], (0, 0, 0), seg=8, smooth=False,
            rot_offset=math.pi / 8)
    b.ico(gold, 1.15, (0, 0, Z_L + 19.2), subdiv=2)
    b.box_base(gold, (0.25, 0.25, 2.6), (0, 0, Z_L + 20.2))
    b.box_base(gold, (1.3, 0.22, 0.22), (0, 0, Z_L + 21.6))

    # ---------------------------------------------------------------- 三座後殿（北、南、東）
    def tribune(ang):
        ca, sa = math.cos(ang), math.sin(ang)
        cx, cy = ca * (A_OCT - 2.0), sa * (A_OCT - 2.0)
        Rt = 15.0
        # 主體：八角形（內側埋入八角結構）
        oct_prism(b, marble, Rt, 0, 27.0, center=(cx, cy))
        oct_prism(b, white, Rt + 0.5, 27.0, 27.6, center=(cx, cy))
        oct_prism(b, marble, Rt - 3.5, 27.6, 32.0, center=(cx, cy))
        for k in range(8):
            a = TAU * k / 8
            if math.cos(a - ang) < -0.2:
                continue
            M = T(cx + math.cos(a) * ((Rt - 3.5) * math.cos(math.pi / 8) + 0.05), cy + math.sin(a) * ((Rt - 3.5) * math.cos(math.pi / 8) + 0.05),
                  29.8) @ Rz(a + math.pi / 2)
            disc_window(b, win, 0.9, M, depth=0.2, seg=14, frame=white, fw=0.3)
        rprof = pointed_profile(Rt - 3.3, rise_scale=0.55, r_top=1.4, n=10)
        b.lathe(tiles_d, rprof + [(0.0, rprof[-1][1])], (cx, cy, 32.0), seg=32, smooth=True, radial=oct_radial(math.pi / 8))
        for k in range(8):
            band_strip(b, white, rprof, math.pi / 8 + TAU * k / 8, 0.7, 0.35, 32.0, inset=0.15)
        zt = 32.0 + rprof[-1][1]
        b.lathe(white, [(1.6, zt - 0.3), (1.6, zt + 2.0), (0.9, zt + 2.6), (0.0, zt + 3.6)], (cx, cy, 0), seg=8, smooth=False)
        # 放射狀小禮拜堂：外側五面各一，帶尖窗與單坡瓦頂
        for k in range(-2, 3):
            a = ang + k * math.pi / 4
            px, py = cx + math.cos(a) * (Rt + 1.2), cy + math.sin(a) * (Rt + 1.2)
            Mc = T(px, py, 0) @ Rz(a + math.pi / 2)
            b.box_base(marble, (9.0, 5.0, 18.0), (px, py, 0), rot=(0, 0, a + math.pi / 2))
            b.box_base(white, (9.6, 5.6, 0.5), (px, py, 18.0), rot=(0, 0, a + math.pi / 2))
            b.profile_wall(tiles_d, [(-4.9, 0), (4.9, 0), (0, 3.2)], 5.8, Mc @ T(0, 0, 18.5))
            gothic_window(b, win, 1.4, 6.5, Mc @ T(0, -2.55, 8.0), depth=0.12)
        # 尖塔與壁柱
        for k in range(-3, 4):
            a = ang + (k + 0.5) * math.pi / 4
            if abs(k + 0.5) > 3:
                continue
            px, py = cx + math.cos(a) * (Rt * 0.98 + 1.5), cy + math.sin(a) * (Rt * 0.98 + 1.5)
            b.box_base(white, (1.5, 1.5, 24.0), (px, py, 0), rot=(0, 0, a))
            b.cone(white, 1.0, 3.5, (px, py, 24.0), seg=4, rot=(0, 0, a + math.pi / 4))

    for ang in (math.pi / 2, -math.pi / 2, 0.0):
        tribune(ang)
    # 四座「死後殿」：八角形斜面上的小半圓室（鼓座底部）
    for k in (1, 3, 5, 7):
        a = TAU * k / 8
        cx, cy = math.cos(a) * (A_OCT + 1.5), math.sin(a) * (A_OCT + 1.5)
        b.lathe(marble, [(4.6, 0), (4.6, 31.0)], (cx, cy, 0), seg=16, smooth=False)
        b.lathe(white, [(5.0, 31.0), (5.0, 31.6), (4.4, 31.6)], (cx, cy, 0), seg=16, smooth=False)
        b.lathe(tiles_d, [(4.5, 31.6), (3.6, 33.6), (2.0, 35.0), (0.0, 35.6)], (cx, cy, 0), seg=16, smooth=True)
        for j in range(5):
            t = a - math.pi / 2 + math.pi * (j + 0.5) / 5
            gothic_window(b, win, 0.9, 3.0, T(cx + math.cos(t) * 4.62, cy + math.sin(t) * 4.62, 26.0) @ Rz(t + math.pi / 2), depth=0.08,
                          kind="round")

    # ---------------------------------------------------------------- 喬托鐘樓
    CX, CY = XF + 5.5, -(YA + 13.0)
    W = 14.45
    H_T = 82.0
    levels = [(0, 8.0), (8.0, 16.0), (16.0, 31.0), (31.0, 45.0), (45.0, 59.0), (59.0, 78.0)]
    b.box_base(tmarble, (W, W, H_T - 4.0), (CX, CY, 0))
    for z0, z1 in levels:
        b.box_base(white, (W + 0.5, W + 0.5, 0.45), (CX, CY, z1 - 0.45))
        b.box_base(green, (W + 0.4, W + 0.4, 0.25), (CX, CY, z1 - 0.7))
    for sx in (-1, 1):            # 八角形角柱
        for sy in (-1, 1):
            b.cyl(white, 1.05, 1.05, H_T - 4.0, (CX + sx * (W / 2 - 0.2), CY + sy * (W / 2 - 0.2), 0), seg=8)
    for f in range(4):
        a = f * math.pi / 2
        n_ = (math.cos(a + math.pi / 2), math.sin(a + math.pi / 2))
        Mface = T(CX - n_[0] * 0, CY, 0) @ Rz(a) @ T(0, -(W / 2 + 0.05), 0)
        Mface = T(CX, CY, 0) @ Rz(a) @ T(0, -(W / 2 + 0.05), 0)
        # 第三層：壁龕（四個）
        for j in range(4):
            u = -W / 2 + W * (j + 0.5) / 4
            gothic_window(b, win, 1.3, 4.6, Mface @ T(u, 0, 18.5), depth=0.12, kind="pointed")
        # 兩層雙窗
        for z in (33.5, 47.5):
            for u in (-2.6, 2.6):
                gothic_window(b, win, 2.3, 9.0, Mface @ T(u, 0, z), depth=0.15)
            b.profile_wall(white, [(-5.0, 0), (5.0, 0), (5.0, 0.4), (-5.0, 0.4)], 0.3, Mface @ T(0, -0.1, z - 0.4))
        # 頂層三聯高窗
        gothic_window(b, win, 6.8, 15.5, Mface @ T(0, 0, 61.0), depth=0.15)
        for u in (-1.15, 1.15):
            b.profile_wall(white, [(-0.18, 0), (0.18, 0), (0.18, 11.0), (-0.18, 11.0)], 0.4, Mface @ T(u, -0.15, 61.0))
        # 下層六角形浮雕
        for j in range(5):
            u = -W / 2 + W * (j + 0.5) / 5 + 0.0
            Mh = Mface @ T(u, -0.05, 4.0) @ Matrix.Rotation(math.pi / 2, 4, "X")
            b.cyl(pinkm, 0.95, 0.95, 0.12, (0, 0, 0), seg=6)
            import bmesh

            bm.verts.ensure_lookup_table()
            bmesh.ops.transform(bm, matrix=Mh, verts=list(bm.verts[-12:]))
    # 頂部出挑簷口與低矮屋頂
    b.box_base(white, (W + 2.6, W + 2.6, 1.2), (CX, CY, H_T - 4.0))
    b.box_base(marble, (W + 2.0, W + 2.0, 2.4), (CX, CY, H_T - 2.8))
    for sx in (-1, 1):
        for k in range(9):
            u = -W / 2 - 0.8 + (W + 1.6) * k / 8
            b.box_base(white, (0.35, 0.35, 0.9), (CX + u, CY + sx * (W / 2 + 0.9), H_T - 0.4))
            b.box_base(white, (0.35, 0.35, 0.9), (CX + sx * (W / 2 + 0.9), CY + u, H_T - 0.4))
    b.frustum(tiles_d, (W - 0.5, W - 0.5), (0.4, 0.4), 3.2, (CX, CY, H_T - 0.4))
    b.cyl(copper, 0.15, 0.06, 9.0, (CX, CY, H_T + 2.6), seg=6)

    # ---------------------------------------------------------------- 聖若望洗禮堂（西側八角）
    BX = XF - 46.0
    RB = 13.0 / math.cos(math.pi / 8)
    oct_prism(b, marble, RB, 0, 26.0, center=(BX, 0))
    oct_prism(b, white, RB + 0.4, 12.0, 12.6, center=(BX, 0))
    oct_prism(b, white, RB + 0.5, 26.0, 26.8, center=(BX, 0))
    oct_prism(b, marble, RB - 1.0, 26.8, 30.0, center=(BX, 0))
    b.lathe(tiles_d, [(RB - 0.4, 30.0), (RB * 0.5, 34.5), (2.2, 36.0)], (BX, 0, 0), seg=8, smooth=False, rot_offset=math.pi / 8)
    oct_prism(b, white, 2.4, 36.0, 40.0, center=(BX, 0))
    b.lathe(white, [(2.6, 40.0), (0.8, 42.5), (0.0, 43.4)], (BX, 0, 0), seg=8, smooth=False, rot_offset=math.pi / 8)
    for k in range(8):
        a = TAU * k / 8
        M = T(BX + math.cos(a) * 13.05, math.sin(a) * 13.05, 0) @ Rz(a + math.pi / 2)
        for u in (-3.2, 0.0, 3.2):
            gothic_window(b, win, 1.4, 4.0, M @ T(u, 0, 15.5), depth=0.1, kind="round")
        if k in (0, 2, 4, 6):
            b.profile_wall(white, [(-3.0, 0), (3.0, 0), (3.0, 9.5), (-3.0, 9.5)], 0.8, M @ T(0, -0.3, 0))
            b.box_base(copper, (3.6, 0.3, 7.2), (BX + math.cos(a) * 13.75, math.sin(a) * 13.75, 0), rot=(0, 0, a + math.pi / 2))

    # ---------------------------------------------------------------- 周邊街區（紅瓦屋頂民宅）
    rng = b.rng

    def busy(x, y):
        if -116 < x < 56 and -50 < y < 46:
            return True
        if -168 < x < -100 and -34 < y < 34:
            return True
        return False

    placed = []
    for _ in range(4000):
        if len(placed) >= 230:
            break
        x, y = rng.uniform(-220, 220), rng.uniform(-200, 200)
        if math.hypot(x, y) > 225 or busy(x, y):
            continue
        w, d = rng.uniform(12, 26), rng.uniform(10, 18)
        if any(abs(x - px) < (w + pw) / 2 + 1.2 and abs(y - py) < (d + pd) / 2 + 1.2 for px, py, pw, pd in placed):
            continue
        placed.append((x, y, w, d))
        h = rng.uniform(10, 17)
        mi = plasters[rng.randrange(len(plasters))]
        b.box_base(mi, (w, d, h), (x, y, 0))
        rh = min(w, d) * 0.17
        b.frustum((tiles, tiles_d, roof_c)[rng.randrange(3)], (w + 1.0, d + 1.0), (max(0.3, w - d), max(0.3, d - w)) if w > d else
                  (max(0.3, w - d), max(0.3, d - w)), rh, (x, y, h))
        # 立面窗列（遠處省略以控制檔案大小）
        for s in ((-1, 1) if math.hypot(x, y) < 150 else ()):
            for row in range(int(h // 3.6) - 1):
                for j in range(max(1, int(w // 4))):
                    u = -w / 2 + w * (j + 0.5) / max(1, int(w // 4))
                    b.box_base(win, (1.1, 0.12, 1.8), (x + u, y + s * (d / 2 + 0.02), 3.2 + row * 3.6))
    for x, y in ((40, -60), (-150, -50), (-170, 40), (70, 70)):
        broadleaf(b, x, y, rng.uniform(10, 14), leaves, trunk)
    for x, y in ((-180, -10), (-185, 12)):
        cypress(b, x, y, 14, cyp, trunk)

    b.export(path)
