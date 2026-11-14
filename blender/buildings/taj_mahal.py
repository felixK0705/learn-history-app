"""taj_mahal 泰姬瑪哈陵寫實模型（尺寸依實測資料，公尺）

- 白色大理石基座 95 × 95 m、高 6.7 m，四面為連續的尖拱盲龕
- 陵墓本體約 56.6 m 見方、四角切角；每面中央為高約 25 m 的 pishtaq 大拱門，
  內為深 7.5 m 的尖拱凹室（iwan），兩側為上下兩層的深壁龕
- 鼓座＋洋蔥形主穹頂（最寬約 26.5 m，比鼓座外凸、頂端收尖），連同青銅頂飾總高約 73 m
- 四座宣禮塔高約 41.6 m，三層陽台，頂部小亭；塔身略向外傾
- 南側查巴格花園：中軸水道、紅砂岩步道、成列柏樹與草坪

座標先以地理方位建模（+Y 北、花園在南 -Y），最後整體旋轉 180°，讓正立面朝向預覽相機。
"""

import math
import os

import bmesh
import numpy as np
from mathutils import Matrix, Vector, noise

from lib import TAU, TEX, Builder

GEN_MARBLE = "_gen/taj_marble_v2"
GEN_MINARET = "_gen/taj_minaret_v2"


def _gen_marble(name, stripes=False):
    """白色大理石：柔和雲紋、極淡的石材接縫（避免明顯方格）。貼圖對應 6 m"""
    out = os.path.join(TEX, name)
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return name
    from PIL import Image, ImageFilter

    N = 1024
    rng = np.random.default_rng(11 if not stripes else 12)

    def cloud(scale, amp):
        small = rng.normal(0, 1, size=(N // scale, N // scale))
        im = Image.fromarray(((small - small.min()) / (np.ptp(small) + 1e-9) * 255).astype(np.uint8))
        im = im.resize((N, N), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(scale / 3))
        a = np.asarray(im, dtype=float) / 255 - 0.5
        return a * amp

    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    lum = cloud(64, 0.06) + cloud(16, 0.035) + cloud(4, 0.015)
    # 細紋（淡灰色石紋）
    vein = np.abs(np.sin((xx * 0.012 + yy * 0.007 + cloud(32, 6.0)) * 2.0))
    lum -= np.where(vein < 0.04, 0.035, 0.0)
    # 石材接縫：每 0.75 m 一層、每 1.5 m 一塊（錯縫）— 非常淡
    ch = N / 8  # 0.75 m
    course = np.floor(yy / ch)
    bx = (xx + (course % 2) * ch) % (2 * ch)
    joint = (yy % ch < 1.6) | (bx < 1.6)
    tone = rng.uniform(-0.02, 0.02, size=(9, 9))
    lum += tone[course.astype(int) % 9, np.floor((xx + (course % 2) * ch) / (2 * ch)).astype(int) % 9]
    if stripes:  # 宣禮塔：黑色大理石嵌線
        sx = xx % (N / 10)
        lum -= np.where(sx < 4, 0.33, 0.0)
        lum -= np.where(yy % (N / 6) < 3, 0.22, 0.0)
    lum -= np.where(joint, 0.045, 0.0)
    base = np.array([240.0, 235.0, 226.0])
    diff = base[None, None, :] * (1 + lum[..., None])
    hgt = np.where(joint, -1.0, 0.0)
    gy, gx = np.gradient(hgt)
    nx, ny, nz = -gx * 0.6, gy * 0.6, np.ones_like(hgt)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nor = np.stack([(nx / ln * 0.5 + 0.5) * 255, (ny / ln * 0.5 + 0.5) * 255, (nz / ln * 0.5 + 0.5) * 255], -1)
    arm = np.stack([np.full((N, N), 255.0), 255 * (0.32 + cloud(16, 0.12)), np.zeros((N, N))], -1)
    os.makedirs(out, exist_ok=True)
    for fn, arr in (("diff", diff), ("nor", nor), ("arm", arm)):
        Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(os.path.join(out, fn + ".jpg"), quality=88)
    return name


# ====================================================================== 泰姬瑪哈陵
def taj_mahal(path):
    b = Builder("TajMahal", seed=17)
    bm = b.bm
    grass = b.tex("grass", "grass_ground", tile=5.0, tint="#5d8c37", rough=0.95, normal=0)
    soil = b.color("soil", "#6b5338", rough=0.95)
    marble = b.tex("marble", _gen_marble(GEN_MARBLE), tile=6.0, normal=0.6)
    mmin = b.tex("marble_minaret", _gen_marble(GEN_MINARET, stripes=True), tile=6.0, normal=0.6)
    inlay = b.color("inlay", "#6f675d", rough=0.4)
    trim = b.color("trim", "#cfc6b6", rough=0.4)
    dark = b.color("opening", "#2f2a24", rough=0.85)
    bronze = b.color("finial", "#a27f45", rough=0.35, metal=0.85)
    red = b.tex("red_sandstone", "red_sandstone_wall", tile=3.0, tint="#a9583f", rough=0.85, normal=0.8)
    pave = b.tex("paving", "red_sandstone_tiles", tile=3.0, tint="#c3a08a", gain=1.05, rough=0.85, normal=0)
    walk = b.tex("walkway", "red_sandstone_tiles", tile=2.0, tint="#b67a63", rough=0.85, normal=0)
    water = b.color("water", "#5b7a80", rough=0.03)
    hedge = b.color("hedge", "#3b5f2a", rough=0.9)
    cyp = [b.color("cypress_a", "#2d4b26", rough=0.88), b.color("cypress_b", "#38582d", rough=0.88)]
    leaf = [b.color("leaf_l", "#6c9443", rough=0.8), b.color("leaf_m", "#527a33", rough=0.82), b.color("leaf_d", "#3b5f27", rough=0.85)]
    trunk = b.color("trunk", "#5a4a3a", rough=0.9)

    def V(p):
        return bm.verts.new(p)

    def face(vs, mi, smooth=False):
        f = bm.faces.new(vs)
        f.material_index = mi
        f.smooth = smooth
        return f

    def strip(rows, mi, closed=True, smooth=False):
        for a, c in zip(rows, rows[1:]):
            n = len(a)
            for i in range(n if closed else n - 1):
                j = (i + 1) % n
                face([a[i], a[j], c[j], c[i]], mi, smooth)

    def capture(fn):
        bm.verts.ensure_lookup_table()
        start = len(bm.verts)
        fn()
        bm.verts.ensure_lookup_table()
        return list(bm.verts[start:])

    def place(fn, M):
        vs = capture(fn)
        bmesh.ops.transform(bm, matrix=M, verts=vs)

    def Rz(a):
        return Matrix.Rotation(a, 4, "Z")

    def T(x, y, z=0.0):
        return Matrix.Translation((x, y, z))

    def panel(mi, pts_uv, M, depth=0.06):
        """貼在牆面上的薄片（u 水平、v 垂直；局部 -Y 為外側）"""
        b.profile_wall(mi, pts_uv, depth, M)

    def arch_poly(width, spring, kind="pointed", seg=12, base=0.0):
        arc = b.arch_points(width, spring, kind, seg)
        return [(-width / 2, base), (width / 2, base)] + list(reversed(arc))[1:-1]

    # ================================================================ 地面、台地與花園
    b.ground_disc(grass, 280, soil, depth=5, rings=30, seg=128)
    # 紅砂岩台地（chameli farsh）：僅在基座周圍露出一圈，鋪面為淡粉色
    b.box_base(pave, (300, 118, 1.2), (0, 0, 0))
    z_t = 1.2

    # 中軸水道（南北）與東西橫向水道
    def channel(x0, x1, y0, y1):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        L, W = abs(x1 - x0), abs(y1 - y0)
        b.box_base(water, (L, W, 0.05), (cx, cy, 0.0))
        horiz = L > W
        for s in (-1, 1):
            if horiz:
                b.box_base(trim, (L, 0.6, 0.28), (cx, cy + s * (W / 2 + 0.3), 0))
                b.box_base(walk, (L, 6.0, 0.14), (cx, cy + s * (W / 2 + 3.6), 0))
                b.box_base(hedge, (L, 0.6, 0.55), (cx, cy + s * (W / 2 + 6.9), 0))
            else:
                b.box_base(trim, (0.6, W, 0.28), (cx + s * (L / 2 + 0.3), cy, 0))
                b.box_base(walk, (6.0, W, 0.14), (cx + s * (L / 2 + 3.6), cy, 0))
                b.box_base(hedge, (0.6, W, 0.55), (cx + s * (L / 2 + 6.9), cy, 0))
        # 噴泉噴口
        n = int(max(L, W) / 4)
        for k in range(n):
            t = (k + 0.5) / n
            px = x0 + (x1 - x0) * t if horiz else cx
            py = cy if horiz else y0 + (y1 - y0) * t
            b.box_base(trim, (0.18, 0.18, 0.3), (px, py, 0))

    GC = -207.0  # 花園中心（大理石水池）
    channel(-3, 3, -59.5, GC - 11)
    channel(-3, 3, GC + 11, -275)
    channel(-150, -11, GC - 3, GC + 3)
    channel(11, 150, GC - 3, GC + 3)
    b.box_base(trim, (22, 22, 1.4), (0, GC, 0))
    b.box_base(water, (18, 18, 0.1), (0, GC, 1.38))
    # 花園外圈與四分園的步道
    for s in (-1, 1):
        b.box_base(walk, (6, 215, 0.12), (s * 75, -167, 0))
    b.box_base(walk, (300, 6, 0.12), (0, -61.5, 0))

    # ================================================================ 大理石基座（95 × 95 × 6.7 m）
    z_p = z_t + 6.7
    HP = 47.5
    b.box_base(marble, (2 * HP - 1.2, 2 * HP - 1.2, 6.2), (0, 0, z_t))
    nb = 19
    bay = (2 * HP - 1.2) / nb
    for side in range(4):
        R = Rz(side * math.pi / 2)
        for k in range(nb):
            u = -HP + 0.6 + bay * (k + 0.5)
            M = R @ T(u, -(HP - 0.3), z_t)
            b.arch_frame(marble, bay, 6.2, 2.9, bay * 0.68, 0.6, M, kind="pointed")
            if k == nb // 2:
                panel(dark, arch_poly(bay * 0.6, 2.7), R @ T(u, -(HP - 0.58), z_t), 0.04)
        b.box_base(marble, (0.6, 0.6, 6.2), tuple(R @ Vector((HP - 0.3, -(HP - 0.3), z_t))))
    b.box_base(marble, (2 * HP + 0.6, 2 * HP + 0.6, 0.5), (0, 0, z_p - 0.5))  # 簷口
    b.box_base(trim, (2 * HP + 0.4, 2 * HP + 0.4, 0.35), (0, 0, z_t))  # 勒腳

    # ================================================================ 陵墓本體
    z0 = z_p
    S, C = 28.3, 9.0        # 外緣半寬、切角
    DEP = 2.0               # 兩側壁龕深度
    PW, RB = 10.5, 21.3     # pishtaq 半寬、iwan 後牆位置
    PF = S + 0.5            # pishtaq 正面（較兩翼凸出 0.5 m）
    HW, HPI = 22.5, 25.4    # 兩翼女兒牆下緣、pishtaq 頂
    si = S - DEP
    ci = C - DEP * (2 - math.sqrt(2))
    side_pts = [(-(si - ci), -si), (-PW, -si), (-PW, -RB), (PW, -RB), (PW, -si), ((si - ci), -si)]
    foot = []
    for k in range(4):
        a = k * math.pi / 2
        ca, sa = math.cos(a), math.sin(a)
        foot += [(x * ca - y * sa, x * sa + y * ca) for x, y in side_pts]
    b.prism(marble, foot, z0, HW)

    tier = HW / 2
    for side in range(4):
        R = Rz(side * math.pi / 2)
        # ---- pishtaq：深拱門
        Mp = R @ T(0, -(RB + PF) / 2, z0)
        b.arch_frame(marble, 2 * PW, HPI, 9.2, 14.0, PF - RB, Mp, kind="pointed")
        Mf = R @ T(0, -PF - 0.02, z0)
        # 書法飾框（黑色大理石嵌字）與拱緣
        for u0, u1, v0, v1 in [(-9.4, -8.6, 0.6, 22.6), (8.6, 9.4, 0.6, 22.6), (-9.4, 9.4, 21.8, 22.6)]:
            panel(inlay, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], Mf, 0.05)
        for u0, u1, v0, v1 in [(-10.1, -9.85, 0.0, 23.4), (9.85, 10.1, 0.0, 23.4), (-10.1, 10.1, 23.15, 23.4)]:
            panel(trim, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], Mf, 0.05)
        # iwan 後牆：下層拱門、上層花格窗
        Mb = R @ T(0, -RB - 0.03, z0)
        panel(trim, arch_poly(5.6, 5.0, base=0.0), Mb, 0.05)
        panel(dark, arch_poly(4.4, 4.6, base=0.0), R @ T(0, -RB - 0.06, z0), 0.05)
        panel(trim, arch_poly(6.0, 11.8, base=9.0), Mb, 0.05)
        panel(dark, arch_poly(5.0, 11.8, base=9.4), R @ T(0, -RB - 0.06, z0), 0.05)
        for k in range(9):  # jali 花格
            u = -2.0 + k * 0.5
            panel(trim, [(u - 0.05, 9.4), (u + 0.05, 9.4), (u + 0.05, 14.5 - abs(u) * 0.6), (u - 0.05, 14.5 - abs(u) * 0.6)],
                  R @ T(0, -RB - 0.1, z0), 0.04)
        for v in (10.6, 11.8, 13.0):
            panel(trim, [(-2.5, v), (2.5, v), (2.5, v + 0.1), (-2.5, v + 0.1)], R @ T(0, -RB - 0.1, z0), 0.04)
        # pishtaq 頂部女兒牆與兩側細柱（guldasta）
        b.box_base(marble, (2 * PW + 0.4, PF - RB + 0.4, 0.6), tuple(R @ Vector((0, -(RB + PF) / 2, z0 + HPI))))
        for sx in (-1, 1):
            p = R @ Vector((sx * PW, -PF, 0))
            b.cyl(marble, 0.55, 0.5, HPI + 1.6, (p.x, p.y, z0), seg=12)
            b.lathe(marble, [(0.55, 0), (0.85, 0.5), (0.8, 1.2), (0.45, 1.9), (0.0, 2.4)], (p.x, p.y, z0 + HPI + 1.6), seg=12)
            b.cyl(bronze, 0.08, 0.0, 1.4, (p.x, p.y, z0 + HPI + 3.9), seg=6)
        # ---- 兩翼：上下兩層深壁龕
        for sx in (-1, 1):
            uc = sx * (PW + (S - C - PW) / 2)
            wbay = S - C - PW
            for tz in range(2):
                M = R @ T(uc, -(si + S) / 2, z0 + tz * tier)
                b.arch_frame(marble, wbay, tier, 6.0, 5.4, DEP, M, kind="pointed")
                Mw = R @ T(uc, -si - 0.03, z0 + tz * tier)
                panel(trim, arch_poly(3.4, 3.4, base=0.6), Mw, 0.05)
                panel(dark, arch_poly(2.6, 3.2, base=0.8), R @ T(uc, -si - 0.06, z0 + tz * tier), 0.05)
                Mfw = R @ T(uc, -S - 0.02, z0 + tz * tier)
                for u0, u1, v0, v1 in [(-4.15, -3.95, 0.4, 10.6), (3.95, 4.15, 0.4, 10.6), (-4.15, 4.15, 10.4, 10.6)]:
                    panel(trim, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], Mfw, 0.04)
        # ---- 切角面：上下兩層壁龕
        for sx in (-1, 1):
            # 切角外緣中點與方向
            p0 = Vector((sx * (S - C), -S, 0))
            p1 = Vector((sx * S, -(S - C), 0))
            mid = (p0 + p1) / 2
            nrm = Vector((sx * 1, -1, 0)).normalized()
            L = (p1 - p0).length
            ang = math.atan2(p1.y - p0.y, p1.x - p0.x) if sx > 0 else math.atan2(p0.y - p1.y, p0.x - p1.x)
            for tz in range(2):
                c = mid - nrm * (DEP / 2)
                M = R @ T(c.x, c.y, z0 + tz * tier) @ Rz(ang)
                b.arch_frame(marble, L, tier, 6.0, 6.4, DEP, M, kind="pointed")
                cb = mid - nrm * (DEP - 0.03)
                panel(trim, arch_poly(3.6, 3.4, base=0.6), R @ T(cb.x, cb.y, z0 + tz * tier) @ Rz(ang), 0.05)
                cb2 = mid - nrm * (DEP - 0.06)
                panel(dark, arch_poly(2.8, 3.2, base=0.8), R @ T(cb2.x, cb2.y, z0 + tz * tier) @ Rz(ang), 0.05)
            # 角柱
            for p in (p0, p1):
                q = R @ p
                b.cyl(marble, 0.6, 0.55, HW + 3.4, (q.x, q.y, z0), seg=12)
                b.lathe(marble, [(0.6, 0), (0.9, 0.5), (0.85, 1.2), (0.45, 1.9), (0.0, 2.4)], (q.x, q.y, z0 + HW + 3.4), seg=12)
                b.cyl(bronze, 0.08, 0.0, 1.3, (q.x, q.y, z0 + HW + 5.7), seg=6)
        # 女兒牆（兩翼與切角）
        for sx in (-1, 1):
            a0 = R @ Vector((sx * PW, -S + 0.3, 0))
            b.box_base(marble, (S - C - PW, 0.6, 1.1), tuple(R @ Vector((sx * (PW + (S - C - PW) / 2), -S + 0.3, z0 + HW))), rot=(0, 0, side * math.pi / 2))
            p0 = Vector((sx * (S - C), -S, 0))
            p1 = Vector((sx * S, -(S - C), 0))
            mid = R @ ((p0 + p1) / 2 - Vector((sx, -1, 0)).normalized() * 0.3)
            b.box_base(marble, ((p1 - p0).length, 0.6, 1.1), (mid.x, mid.y, z0 + HW), rot=(0, 0, side * math.pi / 2 + sx * math.pi / 4))

    # ================================================================ 屋頂：四座小亭（chhatri）
    def onion(R, base, z, mi=marble, k_h=1.0, seg=32):
        prof = [(1.0, 0), (1.09, 0.12), (1.15, 0.3), (1.13, 0.5), (1.0, 0.72), (0.78, 0.95), (0.53, 1.12), (0.3, 1.25), (0.12, 1.35), (0.0, 1.4)]
        b.lathe(mi, [(R * r, R * h * k_h) for r, h in prof], (base[0], base[1], z), seg=seg)
        return z + R * 1.4 * k_h

    def chhatri(x, y, z, R, hcol, mi=marble):
        b.cyl(mi, R * 1.12, R * 1.12, 0.35, (x, y, z), seg=16)
        side = 2 * R * math.sin(math.pi / 8)
        ap = R * math.cos(math.pi / 8)
        for k in range(8):
            a = TAU * k / 8
            M = T(x + ap * math.cos(a), y + ap * math.sin(a), z + 0.35) @ Rz(a + math.pi / 2)
            b.arch_frame(mi, side, hcol, hcol * 0.5, side * 0.66, 0.3, M, kind="pointed")
            va = a + math.pi / 8
            b.cyl(mi, 0.16 * R / 3, 0.16 * R / 3, hcol, (x + R * math.cos(va), y + R * math.sin(va), z + 0.35), seg=8)
        zt = z + 0.35 + hcol
        b.lathe(mi, [(0, zt + 0.3), (R * 1.04, zt + 0.3), (R * 1.42, zt - 0.22), (R * 1.42, zt - 0.36), (R * 0.95, zt - 0.05), (0, zt - 0.05)],
                (x, y, 0), seg=24, smooth=False)
        b.cyl(mi, R * 0.95, R * 0.95, 0.45, (x, y, zt + 0.3), seg=24)
        top = onion(R * 0.88, (x, y), zt + 0.75, mi, seg=24)
        b.lathe(bronze, [(R * 0.12, 0), (R * 0.2, R * 0.18), (R * 0.06, R * 0.36), (R * 0.12, R * 0.5), (R * 0.03, R * 0.65), (0, R * 0.95)],
                (x, y, top - 0.1), seg=8)

    zr = z0 + HW
    for sx in (-1, 1):
        for sy in (-1, 1):
            chhatri(sx * 16.6, sy * 16.6, zr, 3.6, 4.4)

    # ================================================================ 鼓座與主穹頂
    b.cyl(marble, 12.8, 12.8, 1.8, (0, 0, zr), seg=48)
    b.cyl(trim, 13.0, 13.0, 0.3, (0, 0, zr + 1.8), seg=48)
    zd = zr + 2.1
    b.cyl(marble, 11.3, 11.3, 7.6, (0, 0, zd), seg=64)
    # 鼓座上的盲拱帶
    for k in range(24):
        a = TAU * (k + 0.5) / 24
        M = T(11.32 * math.cos(a), 11.32 * math.sin(a), zd + 1.2) @ Rz(a + math.pi / 2)
        panel(trim, arch_poly(1.9, 3.0), M, 0.04)
    b.cyl(inlay, 11.36, 11.36, 0.8, (0, 0, zd + 5.4), seg=64)
    b.cyl(marble, 11.8, 11.6, 0.6, (0, 0, zd + 7.0), seg=64)
    zdome = zd + 7.6
    prof = [(11.3, 0), (11.95, 0.8), (12.6, 2.2), (13.1, 4.2), (13.27, 6.3), (13.05, 8.6), (12.35, 10.8), (11.15, 12.9), (9.55, 14.8),
            (7.65, 16.5), (5.6, 18.0), (3.7, 19.2), (2.25, 20.1), (1.1, 20.8), (0.35, 21.3), (0.0, 21.5)]
    b.lathe(marble, [(r, z) for r, z in prof], (0, 0, zdome), seg=72)
    # 頂端蓮瓣冠
    b.lathe(marble, [(2.4, 19.7), (3.4, 19.15), (3.55, 19.0), (3.0, 19.35), (2.6, 19.9), (1.4, 20.9)], (0, 0, zdome), seg=32, smooth=True)
    # 青銅頂飾
    zf = zdome + 21.2
    b.lathe(bronze, [(0.0, -0.2), (0.9, 0), (1.45, 0.9), (0.5, 1.8), (1.1, 2.8), (0.4, 3.7), (0.85, 4.5), (0.3, 5.3), (0.18, 5.6),
                     (0.18, 8.2), (0.45, 8.5), (0.12, 8.8), (0.0, 9.6)], (0, 0, zf), seg=16)
    print(f"  taj: roof {zr:.1f}, dome base {zdome:.1f}, finial top {zf + 9.6:.1f}")

    # ================================================================ 宣禮塔（三層陽台、略向外傾）
    def minaret():
        b.cyl(marble, 4.5, 4.5, 1.6, (0, 0, 0), seg=8)
        b.cyl(trim, 4.7, 4.7, 0.3, (0, 0, 1.6), seg=8)
        secs = [(1.9, 10.6, 3.15, 3.0), (11.85, 21.6, 2.9, 2.75), (22.85, 33.6, 2.65, 2.5)]
        for z_a, z_b, r_a, r_b in secs:
            b.cyl(mmin, r_a, r_b, z_b - z_a, (0, 0, z_a), seg=24)
            r = r_b
            b.lathe(marble, [(r - 0.2, z_b - 1.4), (r + 0.45, z_b - 0.8), (r + 1.1, z_b - 0.15), (r + 1.3, z_b), (r + 1.3, z_b + 0.3), (r - 0.2, z_b + 0.3)],
                    (0, 0, 0), seg=24, smooth=False)
            b.ering(marble, (r + 1.05, r + 1.05), (r + 1.3, r + 1.3), z_b + 0.3, z_b + 1.25, seg=32)
        b.cyl(mmin, 2.5, 2.5, 1.25, (0, 0, 33.6), seg=24)
        chhatri(0, 0, 34.85, 2.55, 3.0)

    for sx in (-1, 1):
        for sy in (-1, 1):
            d = Vector((sx, sy, 0)).normalized()
            axis = Vector((-d.y, d.x, 0))
            M = T(sx * 43.6, sy * 43.6, z_p) @ Matrix.Rotation(math.radians(0.6), 4, axis)
            place(minaret, M)

    # ================================================================ 兩側紅砂岩清真寺與答辯廳
    def mosque(sx):
        x = sx * 103.0
        F = x - sx * 11.5           # 立面（面向陵墓）
        cxb = x + sx * 0.6          # 主體中心
        b.box_base(red, (21.8, 56.0, 14.0), (cxb, 0, z_t))
        for yc in (-22.5, -11.5, 11.5, 22.5):
            M = T(F + sx * 0.6, yc, z_t) @ Rz(math.pi / 2)
            b.arch_frame(red, 11.0, 14.0, 5.8, 6.8, 1.2, M, kind="pointed")
            panel(trim, arch_poly(7.2, 5.8), T(F - sx * 0.02, yc, z_t) @ Rz(math.pi / 2), 0.03)
            panel(dark, arch_poly(3.0, 3.6), T(F + sx * 1.15, yc, z_t) @ Rz(math.pi / 2), 0.04)
        b.arch_frame(red, 12.0, 18.5, 6.8, 7.8, 1.6, T(F - sx * 0.2, 0, z_t) @ Rz(math.pi / 2), kind="pointed")
        panel(dark, arch_poly(4.0, 5.0), T(F + sx * 1.15, 0, z_t) @ Rz(math.pi / 2), 0.04)
        for u0, u1, v0, v1 in [(-5.7, -5.35, 0.4, 17.7), (5.35, 5.7, 0.4, 17.7), (-5.7, 5.7, 17.35, 17.7)]:
            panel(trim, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], T(F - sx * 1.02, 0, z_t) @ Rz(math.pi / 2), 0.03)
        b.box_base(red, (22.2, 56.4, 0.8), (cxb, 0, z_t + 14.0))
        b.box_base(trim, (22.4, 56.6, 0.25), (cxb, 0, z_t + 14.8))
        for yc, R in ((0.0, 6.6), (-17.0, 4.6), (17.0, 4.6)):
            b.cyl(red, R * 1.05, R * 1.05, 2.4, (cxb, yc, z_t + 14.8), seg=32)
            top = onion(R, (cxb, yc), z_t + 17.2, seg=32)
            b.cyl(bronze, R * 0.08, 0.0, R * 0.6, (cxb, yc, top - 0.2), seg=6)
        for yc in (-28.0, 28.0):
            for xc in (F, x + sx * 11.5):
                b.cyl(red, 1.9, 1.7, 17.0, (xc, yc, z_t), seg=8)
                chhatri(xc, yc, z_t + 17.0, 1.9, 2.4)

    for sx in (-1, 1):
        mosque(sx)

    # ================================================================ 植栽
    def cypress(x, y, h, mi):
        r = h * b.rng.uniform(0.11, 0.14)
        off = Vector((b.rng.uniform(0, 99), b.rng.uniform(0, 99), 0))
        seg, nr = 10, 9
        prof = []
        for i in range(nr):
            t = i / (nr - 1)
            rr = r * (0.75 + 0.35 * math.sin(math.pi * min(1, t * 1.35)) ** 0.6) * (1 - t ** 3 * 0.85)
            prof.append((rr, h * (0.06 + 0.94 * t)))
        rings = []
        for i, (rr, z) in enumerate(prof):
            ring = []
            for j in range(seg):
                a = TAU * j / seg
                p = Vector((math.cos(a), math.sin(a), z / (r * 3)))
                k = 1 + 0.18 * noise.noise(p * 1.8 + off)
                ring.append(V((x + rr * k * math.cos(a), y + rr * k * math.sin(a), z)))
            rings.append(ring)
        strip(rings, mi, smooth=True)
        face(list(reversed(rings[0])), mi)
        tip = V((x, y, h * 1.03))
        for j in range(seg):
            face([rings[-1][j], rings[-1][(j + 1) % seg], tip], mi, smooth=True)
        b.cyl(trunk, r * 0.18, r * 0.15, h * 0.1, (x, y, 0), seg=6)

    def blob(mi, loc, rx, ry, rz, lump=0.3):
        off = Vector((b.rng.uniform(0, 99), b.rng.uniform(0, 99), b.rng.uniform(0, 99)))
        r = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0, matrix=Matrix.Identity(4))
        for v in r["verts"]:
            p = v.co.copy()
            n = noise.noise(p * 1.6 + off) * 0.7 + noise.noise(p * 3.5 + off) * 0.3
            k = 1 + lump * n
            v.co = Vector((loc[0] + p.x * rx * k, loc[1] + p.y * ry * k, loc[2] + p.z * rz * k))
        for f in {f for v in r["verts"] for f in v.link_faces}:
            f.material_index = mi
            f.smooth = True

    def broadleaf(x, y, h):
        R = h * b.rng.uniform(0.3, 0.38)
        cz = h - R * 0.95
        b.cyl(trunk, h * 0.035, h * 0.02, cz, (x, y, 0), seg=7)
        for i in range(b.rng.randint(9, 13)):
            a = b.rng.uniform(0, TAU)
            rr = R * math.sqrt(b.rng.uniform(0.05, 1)) * 0.65
            dz = b.rng.uniform(-0.45, 0.55) * R
            br = R * b.rng.uniform(0.42, 0.62)
            mi = leaf[0] if dz > 0.18 * R else (leaf[2] if dz < -0.15 * R else leaf[1])
            blob(mi, (x + rr * math.cos(a), y + rr * math.sin(a), cz + dz), br * 1.05, br * 1.05, br * 0.85)

    # 柏樹：沿中軸步道兩側與草坪
    for sx in (-1, 1):
        for xr, step in ((11.3, 7.0), (19.5, 7.0)):
            y = -66.0
            while y > -270:
                if abs(y - GC) > 15:
                    cypress(sx * xr + b.rng.uniform(-0.2, 0.2), y + b.rng.uniform(-0.4, 0.4), b.rng.uniform(6.5, 9.5), cyp[b.rng.randint(0, 1)])
                y -= step
    # 花園中的大樹
    for x, y in b.scatter(40, 30, 270, min_dist=14, avoid=lambda x, y: y > -70 or abs(x) < 30 or abs(x) > 150 or abs(abs(x) - 75) < 6 or abs(y - GC) < 8):
        broadleaf(x, y, b.rng.uniform(10, 16))
    # 河岸與東西兩側的樹叢
    for x, y in b.scatter(45, 160, 270, min_dist=14, avoid=lambda x, y: y < -60):
        broadleaf(x, y, b.rng.uniform(10, 15))

    # 地理座標 → 正立面朝向相機（+Y）
    bmesh.ops.rotate(bm, verts=bm.verts[:], cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi, 3, "Z"))
    b.export(path)
