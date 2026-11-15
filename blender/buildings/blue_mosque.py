"""blue_mosque 伊斯坦堡蘇丹艾哈邁德清真寺（藍色清真寺）寫實模型（公尺）

- 禮拜殿約 64 × 72 m；中央圓頂直徑 23.5 m、高 43 m，由四座半圓頂（各再帶三座小半圓頂）
  層層向下，四角各有小圓頂；中央方形四角有八角形「重力塔」小圓頂
- 六座宣禮塔高約 64 m：禮拜殿四角各一（三層陽台），前庭外側兩角各一（兩層陽台）
- 前庭與禮拜殿等寬，四周為帶 30 座小圓頂的拱廊，中央有淨身亭
- 外觀為帶藍灰色調的石灰岩與鉛覆圓頂

座標：禮拜殿中心在原點，+Y 為前庭方向（實際的西北），-Y 為朝拜牆（東南）。
參考照由東北側公園拍攝。
"""

import math

from mathutils import Matrix

from lib import TAU, Builder

from .hagia_sophia import arched_window, broadleaf, capture, dome, half_dome, minaret, window_row

CAMERA = ((2, -2, 30), 20, -10, 118, 27)


def blue_mosque(path):
    b = Builder("BlueMosque", seed=43)
    bm = b.bm
    stone = b.tex("stone", "white_sandstone_blocks_02", tile=4.0, tint="#b3b2ad", rough=0.85, normal=0.6)
    stone_d = b.color("stone_shade", "#a9a8a3", rough=0.85)
    trim = b.color("trim", "#cfcdc6", rough=0.75)
    lead = b.color("lead", "#7f8992", rough=0.45, metal=0.35)
    win = b.color("window", "#2a2c30", rough=0.3)
    gold = b.color("gold", "#c9a14a", rough=0.3, metal=0.9)
    pave = b.tex("pave", "gravel_floor", tile=4.0, tint="#958f84", rough=0.95, normal=0)
    marble = b.color("court_marble", "#d9d6cf", rough=0.6)
    grass = b.tex("grass", "grass_ground", tile=8.0, tint="#5f7c3c", gain=0.92, rough=0.95, normal=0)
    soil = b.color("soil", "#6b5a45", rough=0.95)
    leaves = [b.color("leaf_l", "#6b8f3e", rough=0.85), b.color("leaf_m", "#4c6e2c", rough=0.88), b.color("leaf_d", "#34521f", rough=0.9)]
    trunk = b.color("trunk", "#5a4a3a", rough=0.9)
    palm_leaf = b.color("palm_leaf", "#5b7a2f", rough=0.8)
    palm_trunk = b.color("palm_trunk", "#8a7254", rough=0.95)

    T = lambda x, y, z=0.0: Matrix.Translation((x, y, z))  # noqa: E731
    Rz = lambda a: Matrix.Rotation(a, 4, "Z")  # noqa: E731

    # ---------------------------------------------------------------- 地面與外圍牆
    b.ground_disc(grass, 190, soil, depth=4, rings=20, seg=96)
    b.box_base(pave, (150, 230, 0.1), (0, 25, 0))
    # 外院圍牆（低矮、帶窗）
    for (cx, cy, w, d) in ((0, -72, 150, 1.5), (-75, 25, 1.5, 195), (75, 25, 1.5, 195), (0, 122, 150, 1.5)):
        b.box_base(stone_d, (w, d, 4.5), (cx, cy, 0))
        b.box_base(trim, (w + 0.6, d + 0.6, 0.4), (cx, cy, 4.5))

    # ---------------------------------------------------------------- 禮拜殿本體
    HX, Y0, Y1 = 27.0, -28.0, 26.0       # 殿身 54 × 54，兩側另有拱廊（總寬約 64 m）
    H_W = 17.0
    b.box_base(stone, (2 * HX, Y1 - Y0, H_W), (0, (Y0 + Y1) / 2, 0))
    b.box_base(trim, (2 * HX + 0.8, Y1 - Y0 + 0.8, 0.6), (0, (Y0 + Y1) / 2, H_W))
    b.box_base(lead, (2 * HX - 2, Y1 - Y0 - 2, 0.8), (0, (Y0 + Y1) / 2, H_W + 0.6))
    # 側牆窗：三排
    for z, n, w, h in ((3.0, 9, 1.8, 3.4), (9.0, 9, 1.6, 3.0), (14.5, 9, 1.4, 2.6)):
        for sx in (-1, 1):
            window_row(b, win, n, Y0 + 3, Y1 - 3, z, w, h, sx * (HX + 0.05), face_dir=sx, axis="y", depth=0.12)
        window_row(b, win, n, -HX + 3, HX - 3, z, w, h, Y0 - 0.05, face_dir=-1, depth=0.12)
    # 兩側二層拱廊（側立面下半部的特徵）
    for sx in (-1, 1):
        x = sx * (HX + 3.0)
        b.box_base(lead, (6.6, Y1 - Y0 - 6, 0.5), (x, (Y0 + Y1) / 2 + 1, 11.5))
        nb = 9
        for k in range(nb):
            y = Y0 + 4 + (Y1 - Y0 - 6) * (k + 0.5) / nb
            for zb, hh in ((0.0, 5.6), (5.8, 5.7)):
                M = T(x + sx * 3.0, y, zb) @ Rz(math.pi / 2 if sx > 0 else -math.pi / 2)
                bw = (Y1 - Y0 - 6) / nb
                b.arch_frame(stone, bw, hh, hh * 0.55, bw * 0.62, 0.8, M, kind="pointed")
        b.box_base(stone_d, (6.0, Y1 - Y0 - 6, 0.3), (x, (Y0 + Y1) / 2 + 1, 5.6))

    # ---------------------------------------------------------------- 中央方形：四座半圓頂＋重力塔＋主圓頂
    A = 11.75             # 圓頂半徑（直徑 23.5 m）
    Z_HD = 21.5           # 半圓頂起拱
    Z_DR = Z_HD + 8.6
    # 中央方形下部量體（半圓頂與鼓座的支座）
    b.box_base(stone_d, (2 * A + 4, 2 * A + 4, Z_DR - H_W), (0, 0, H_W))
    for ang in (0, 90, 180, 270):
        a = math.radians(ang)
        c, s = round(math.cos(a)), round(math.sin(a))
        cx, cy = c * A, s * A
        # 半圓頂下的半圓牆（帶兩排窗）
        t0 = a - math.pi / 2
        b.ering(stone, (A - 0.6, A - 0.6), (A + 0.5, A + 0.5), H_W, Z_HD, seg=40, t0=t0, t1=t0 + math.pi, center=(cx, cy))
        for k in range(7):
            t = t0 + math.pi * (k + 0.5) / 7
            M = T(cx + math.cos(t) * (A + 0.52), cy + math.sin(t) * (A + 0.52), Z_HD - 3.6) @ Rz(t + math.pi / 2)
            arched_window(b, win, 1.2, 2.6, M, depth=0.1)
        half_dome(b, lead, A + 0.6, 9.0, (cx, cy, Z_HD), facing=a + math.pi, seg=32, n=8, ribs=14, flat_mi=stone_d)
        # 三座小半圓頂（exedra）沿半圓頂外緣
        for k, dt in enumerate((-0.62, 0.0, 0.62)):
            t = a + dt * 1.15
            ex, ey = cx + math.cos(t) * (A + 2.5), cy + math.sin(t) * (A + 2.5)
            if k == 1:
                continue
            b.lathe(stone, [(4.2, H_W), (4.2, H_W + 3.0)], (ex, ey, 0), seg=20, smooth=False)
            dome(b, lead, 4.4, 3.2, (ex, ey, H_W + 3.0), seg=24, ribs=10, n=6)
    # 四角小圓頂（禮拜殿四角，位於半圓頂之間）
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (A + 9.5), sy * (A + 9.5)
            b.box_base(stone, (12.0, 12.0, 3.0), (cx, cy, H_W))
            b.lathe(stone, [(5.4, H_W + 3.0), (5.4, H_W + 5.0)], (cx, cy, 0), seg=24, smooth=False)
            for k in range(8):
                t = TAU * (k + 0.5) / 8
                arched_window(b, win, 0.9, 1.5, T(cx + math.cos(t) * 5.42, cy + math.sin(t) * 5.42, H_W + 3.3) @ Rz(t + math.pi / 2), depth=0.08)
            dome(b, lead, 5.7, 4.3, (cx, cy, H_W + 5.0), seg=28, ribs=12, n=7)
            b.lathe(gold, [(0.12, H_W + 9.2), (0.22, H_W + 9.9), (0.0, H_W + 10.8)], (cx, cy, 0), seg=6)
    # 重力塔：中央方形四角的八角形小塔
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (A + 1.2), sy * (A + 1.2)
            b.lathe(stone, [(2.6, H_W), (2.6, Z_HD + 9.5), (2.9, Z_HD + 9.9), (2.5, Z_HD + 10.1)], (cx, cy, 0), seg=8, smooth=False)
            for k in range(8):
                t = TAU * (k + 0.5) / 8
                arched_window(b, win, 0.7, 1.6, T(cx + math.cos(t) * 2.42, cy + math.sin(t) * 2.42, Z_HD + 6.8) @ Rz(t + math.pi / 2), depth=0.08)
            dome(b, lead, 2.5, 2.2, (cx, cy, Z_HD + 10.1), seg=16, n=5)
            zf = Z_HD + 12.2
            b.lathe(gold, [(0.12, zf), (0.25, zf + 0.6), (0.08, zf + 1.1), (0.18, zf + 1.5), (0.0, zf + 2.4)], (cx, cy, 0), seg=6)

    # 鼓座（28 窗）與主圓頂
    H_DR = 4.5
    b.lathe(stone, [(A + 0.6, Z_DR), (A + 0.6, Z_DR + H_DR)], (0, 0, 0), seg=56, smooth=False)
    for k in range(28):
        t = TAU * (k + 0.5) / 28
        arched_window(b, win, 1.15, 2.9, T(math.cos(t) * (A + 0.62), math.sin(t) * (A + 0.62), Z_DR + 0.8) @ Rz(t + math.pi / 2), depth=0.1)
        t2 = TAU * k / 28
        b.frustum(stone, (1.1, 0.9), (0.6, 0.8), H_DR, (math.cos(t2) * (A + 1.0), math.sin(t2) * (A + 1.0), Z_DR), rot_z=t2)
    b.lathe(trim, [(A + 1.2, Z_DR + H_DR), (A + 1.4, Z_DR + H_DR + 0.4), (A + 0.4, Z_DR + H_DR + 0.4)], (0, 0, 0), seg=56, smooth=False)
    Z_DM = Z_DR + H_DR + 0.4
    dome(b, lead, A + 0.9, 43.0 - Z_DM, (0, 0, Z_DM), seg=128, ribs=32, rib_amp=0.008, n=12, power=0.9)
    b.lathe(gold, [(0.0, 42.8), (0.5, 43.0), (0.7, 43.6), (0.25, 44.2), (0.55, 45.0), (0.15, 45.8), (0.35, 46.4), (0.08, 47.3), (0.0, 48.6)],
            (0, 0, 0), seg=10)

    # ---------------------------------------------------------------- 前庭（+Y）：拱廊＋小圓頂＋淨身亭
    CY0, CY1 = Y1, Y1 + 64.0
    CW = 32.0
    b.box_base(marble, (2 * CW, CY1 - CY0, 0.5), (0, (CY0 + CY1) / 2, 0))
    # 外牆
    for (cx, cy, w, d) in ((0, CY1 - 0.9, 2 * CW, 1.8), (-CW + 0.9, (CY0 + CY1) / 2, 1.8, CY1 - CY0), (CW - 0.9, (CY0 + CY1) / 2, 1.8, CY1 - CY0)):
        b.box_base(stone, (w, d, 10.0), (cx, cy, 0))
    for z in (2.5,):
        for sx in (-1, 1):
            window_row(b, win, 8, CY0 + 4, CY1 - 4, z, 1.6, 3.2, sx * (CW + 0.05), face_dir=sx, axis="y", depth=0.12)
    # 正門（北側）
    b.box_base(stone, (12, 4, 15), (0, CY1, 0))
    arched_window(b, win, 5.0, 9.0, T(0, CY1 + 2.05, 0.5) @ Rz(math.pi), depth=0.12)
    # 拱廊小圓頂（沿內側一圈）
    bay = 6.4
    ring = []
    nx, ny = int(2 * CW / bay), int((CY1 - CY0) / bay)
    for i in range(nx):
        ring.append((-CW + bay * (i + 0.5), CY1 - bay / 2 - 1.8))
    for j in range(1, ny - 1):
        ring.append((-CW + bay / 2 + 1.8, CY0 + bay * (j + 0.5)))
        ring.append((CW - bay / 2 - 1.8, CY0 + bay * (j + 0.5)))
    for i in range(nx):
        ring.append((-CW + bay * (i + 0.5), CY0 + bay / 2 + 1.0))
    for x, y in ring:
        b.box_base(stone_d, (bay, bay, 0.8), (x, y, 7.6))
        dome(b, lead, bay * 0.42, bay * 0.33, (x, y, 8.4), seg=16, n=5)
    # 內側拱廊立面（柱＋尖拱）
    for x, y in ring:
        pass
    inner = [(-CW + bay + 1.8, CW - bay - 1.8, CY0 + bay + 1.0, CY1 - bay - 1.8)]
    x0, x1, y0, y1 = inner[0]
    for (ax, ay, L, rot) in ((x0, (y0 + y1) / 2, y1 - y0, math.pi / 2), (x1, (y0 + y1) / 2, y1 - y0, -math.pi / 2),
                             ((x0 + x1) / 2, y1, x1 - x0, math.pi), ((x0 + x1) / 2, y0, x1 - x0, 0.0)):
        n = max(1, round(L / bay))
        for k in range(n):
            u = -L / 2 + L * (k + 0.5) / n
            M = T(ax, ay, 0.5) @ Rz(rot) @ T(u, 0, 0)
            b.arch_frame(stone, L / n, 7.1, 3.6, L / n * 0.7, 0.9, M, kind="pointed")
    # 淨身亭（八角）
    fy = (CY0 + CY1) / 2
    for k in range(8):
        t = TAU * k / 8
        b.cyl(marble, 0.35, 0.35, 4.5, (math.cos(t) * 3.6, fy + math.sin(t) * 3.6, 0.5), seg=8)
    b.lathe(stone, [(4.4, 5.0), (4.4, 5.8)], (0, fy, 0), seg=8, smooth=False)
    dome(b, lead, 4.3, 3.0, (0, fy, 5.8), seg=24, n=6)

    # ---------------------------------------------------------------- 六座宣禮塔
    for sx in (-1, 1):
        for y in (Y0 - 2.0, Y1 + 0.5):
            minaret(b, sx * (HX + 7.0), y, 64.0, 2.0, stone, lead, gold, balcony=stone_d, balconies=(0.47, 0.64, 0.80), base_h=9.0,
                    seg=16, cap_h=12.0)
        minaret(b, sx * (CW + 3.0), CY1 + 2.0, 58.0, 1.9, stone, lead, gold, balcony=stone_d, balconies=(0.55, 0.76), base_h=8.0,
                seg=16, cap_h=11.0)

    # ---------------------------------------------------------------- 植栽：闊葉樹與棕櫚
    rng = b.rng

    def palm(x, y, h):
        b.cyl(palm_trunk, 0.45, 0.3, h, (x, y, 0), seg=8)
        for k in range(14):
            a = TAU * k / 14 + rng.uniform(-0.1, 0.1)
            droop = rng.uniform(0.35, 0.8)
            L = rng.uniform(4.5, 6.0)
            pts = []
            for i in range(6):
                u = i / 5
                r = L * u
                z = h + 1.2 * math.sin(math.pi * u * 0.6) - droop * 3.0 * u * u
                w = 0.9 * math.sin(math.pi * min(1, u * 1.1 + 0.05))
                pts.append((r, z, w))
            vs_l = [bm.verts.new((x + math.cos(a) * r - math.sin(a) * w, y + math.sin(a) * r + math.cos(a) * w, z)) for r, z, w in pts]
            vs_r = [bm.verts.new((x + math.cos(a) * r + math.sin(a) * w, y + math.sin(a) * r - math.cos(a) * w, z - 0.15)) for r, z, w in pts]
            for i in range(5):
                f = bm.faces.new([vs_l[i], vs_l[i + 1], vs_r[i + 1], vs_r[i]])
                f.material_index = palm_leaf
                f.smooth = True

    def in_complex(x, y):
        return -48 < x < 48 and -46 < y < 104

    for x, y in b.scatter(46, 50, 185, min_dist=12, avoid=lambda x, y: in_complex(x, y) or abs(x) > 140):
        broadleaf(b, x, y, rng.uniform(12, 18), leaves, trunk)
    for x, y in ((62, -10), (60, 20), (-62, 40), (64, 60)):
        palm(x, y, rng.uniform(8, 10))

    b.export(path)
