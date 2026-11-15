"""neuschwanstein 新天鵝堡寫實模型（公尺）

- 建於阿爾卑斯山麓岩脊上，沿東西向約 150 m：西端為主樓（Palas，約 44 × 18 m，簷高約 33 m，
  兩端尖山牆、深灰石板屋頂與老虎窗）；主樓北側細高的樓梯塔（約 65 m，八角形尖頂）、南面中段小角塔、
  西南角兩座圓角樓
- 中段較低的騎士樓／閨房翼（簷高約 22 m），東端方塔（Viereckturm，約 45 m，雉堞頂＋小尖塔）
  與紅磚門樓（Torbau）
- 外牆為淺色石灰岩（近白），底部岩盤與陡崖，四周山坡為雲杉與闊葉混合林

座標：+X 東、+Y 北；主樓東南角附近為原點，岩脊平台頂面 z = 0。參考照由南方瑪麗恩橋拍攝（略高於城堡基座）。
"""

import math

from mathutils import Matrix, noise, Vector

from lib import TAU, Builder

from .hagia_sophia import arched_window, broadleaf, conifer, foliage_mats

CAMERA = ((4, 0, 20), -34, 3, 205, 45)


def neuschwanstein(path):
    b = Builder("Neuschwanstein", seed=23)
    stone = b.tex("stone", "white_sandstone_bricks_03", tile=3.0, tint="#e4e0d6", rough=0.8, normal=0.5)
    stone_d = b.color("stone_d", "#d3cdc1", rough=0.8)
    plinth = b.tex("plinth", "white_sandstone_bricks_03", tile=4.5, tint="#cbc4b6", rough=0.85, normal=0.7)
    trim = b.color("trim", "#f0ece4", rough=0.7)
    slate = b.color("slate", "#2e3136", rough=0.78)
    slate_l = b.color("slate_l", "#43474d", rough=0.7)
    copper = b.color("copper_green", "#5f8a7d", rough=0.5, metal=0.3)
    gold = b.color("gold", "#cfa449", rough=0.3, metal=0.9)
    win = b.color("window", "#2b2e33", rough=0.25)
    dormer_w = b.color("dormer", "#b9693e", rough=0.6)
    brick = b.color("brick", "#ad5e4a", rough=0.85)
    rock = b.tex("rock", "rock_04", tile=8.0, tint="#a39b8f", rough=0.9, normal=1.0)
    forest = b.tex("forest_floor", "aerial_grass_rock", tile=14.0, tint="#4c6232", gain=0.85, rough=0.95, normal=0.4)
    soil = b.color("soil", "#5a4a38", rough=0.95)
    con = [b.color("con_l", "#33502a", rough=0.9), b.color("con_m", "#264221", rough=0.9), b.color("con_d", "#1b3218", rough=0.9)]
    leaves = foliage_mats(b, ("#5e7f34", "#46652a", "#2e4a1d"))
    trunk = b.color("trunk", "#4f4032", rough=0.9)

    T = lambda x, y, z=0.0: Matrix.Translation((x, y, z))  # noqa: E731
    Rz = lambda a: Matrix.Rotation(a, 4, "Z")  # noqa: E731

    # ---------------------------------------------------------------- 地形：岩脊平台、陡坡、峽谷
    def ridge_d(x, y):
        """到岩脊（城堡平台）邊緣的距離（橢圓近似，平台沿 X）"""
        cx = min(max(x, -48.0), 88.0)
        return math.hypot(x - cx, (y - 0.0) / 1.0) - 16.0

    def height(x, y):
        d = ridge_d(x, y)
        n = noise.noise(Vector((x * 0.02, y * 0.02, 0.3))) * 6 + noise.noise(Vector((x * 0.06, y * 0.06, 1.7))) * 2.0
        if d <= 0:
            return -2.0
        if y < 0:      # 南側：陡崖落入波拉特峽谷，再爬升到對岸山坡
            h = -2.0 - 45.0 * (1 - math.exp(-d / 18.0)) + 0.32 * max(0.0, d - 80.0)
        else:          # 北側：較緩的山坡往平原
            h = -2.0 - 24.0 * (1 - math.exp(-d / 25.0)) - 0.12 * d
        return h + n * min(1.0, d / 15.0)

    b.ground_disc(forest, 230, soil, depth=110, rings=40, seg=96, height_fn=height)
    # 岩盤：城堡下方露出的灰白岩壁
    for x0 in range(-46, 90, 9):
        for sgn in (-1, 1):
            if sgn > 0 and b.rng.random() < 0.5:
                continue
            y0 = sgn * (14.0 + b.rng.uniform(-1, 2))
            hh = b.rng.uniform(14, 26) if sgn < 0 else b.rng.uniform(6, 10)
            b.rock(rock, (b.rng.uniform(9, 14), b.rng.uniform(7, 10), hh), (x0 + b.rng.uniform(-2, 2), y0, -hh / 2 - 1.0),
                   rough=0.28, subdiv=3, seed=b.rng.randint(0, 999), flat_bottom=False, round_=0.2)
    # 平台與擋土牆
    b.box_base(plinth, (138.0, 30.0, 4.0), (20.0, 0.0, -4.0))

    # ---------------------------------------------------------------- 共用構件
    def win_rows(x0, x1, y, face, rows, n, w=1.3, h=2.6, pair=True):
        """face=-1 南牆（朝 -Y）、+1 北牆"""
        for z in rows:
            for k in range(n):
                u = x0 + (x1 - x0) * (k + 0.5) / n
                M = T(u, y, z) @ (Rz(0) if face < 0 else Rz(math.pi))
                if pair:
                    for du in (-0.75, 0.75):
                        arched_window(b, win, w * 0.55, h, M @ T(du, 0, 0), depth=0.12)
                else:
                    arched_window(b, win, w, h, M, depth=0.12)

    def win_rows_y(y0, y1, x, face, rows, n, w=1.3, h=2.6):
        for z in rows:
            for k in range(n):
                u = y0 + (y1 - y0) * (k + 0.5) / n
                M = T(x, u, z) @ Rz(-math.pi / 2 if face < 0 else math.pi / 2)
                for du in (-0.75, 0.75):
                    arched_window(b, win, w * 0.55, h, M @ T(du, 0, 0), depth=0.12)

    def gable_roof(x0, x1, y0, y1, z, h, mi=slate, gable_mi=stone, ends=(True, True), dormers=0):
        """沿 X 的雙坡屋頂＋兩端尖山牆（山牆略高出屋面，帶小尖飾）"""
        L, D = x1 - x0, y1 - y0
        yc = (y0 + y1) / 2
        b.profile_wall(mi, [(-D / 2 - 0.6, 0), (D / 2 + 0.6, 0), (0, h)], L + 0.6, T((x0 + x1) / 2, yc, z) @ Rz(math.pi / 2))
        for k, x in enumerate((x0, x1)):
            if not ends[k]:
                continue
            M = T(x + (-0.5 if k == 0 else 0.5), yc, z) @ Rz(math.pi / 2)
            b.profile_wall(gable_mi, [(-D / 2 - 0.4, 0), (D / 2 + 0.4, 0), (D / 2 + 0.4, 1.0), (0, h + 1.6), (-D / 2 - 0.4, 1.0)], 1.0, M)
            for du, dz in ((-D / 2, 1.0), (D / 2, 1.0), (0.0, h + 1.6)):
                p = M @ Vector((du, 0, dz))
                b.cyl(gable_mi, 0.35, 0.35, 1.6, (p.x, p.y, p.z), seg=8)
                b.cone(slate_l, 0.45, 1.6, (p.x, p.y, p.z + 1.6), seg=8)
        for k in range(dormers):    # 老虎窗（兩坡）
            u = x0 + L * (k + 0.5) / dormers
            for s in (-1, 1):
                yy = yc + s * D * 0.22
                zz = z + h * 0.42
                Md = T(u, yy, zz) @ (Rz(0) if s < 0 else Rz(math.pi))
                b.profile_wall(slate_l, [(-0.9, 0), (0.9, 0), (0.9, 1.8), (0, 3.0), (-0.9, 1.8)], 2.4, Md)
                b.profile_wall(dormer_w, [(-0.55, 0.2), (0.55, 0.2), (0.55, 1.6), (-0.55, 1.6)], 0.1, Md @ T(0, -1.22, 0))

    def turret(x, y, z0, z1, r, cap_h, mi=stone, cap=slate, corbel=True, finial=True, seg=14):
        if corbel:
            b.lathe(mi, [(0.2, z0 - 2.4), (r * 0.6, z0 - 1.6), (r, z0)], (x, y, 0), seg=seg, smooth=False)
        b.lathe(mi, [(r, z0), (r, z1)], (x, y, 0), seg=seg, smooth=False)
        b.lathe(trim, [(r + 0.15, z1 - 0.4), (r + 0.3, z1), (r * 0.8, z1)], (x, y, 0), seg=seg, smooth=False)
        for k in range(4):
            a = TAU * k / 4 + 0.4
            M = T(x + math.cos(a) * r, y + math.sin(a) * r, z1 - 3.2) @ Rz(a + math.pi / 2)
            arched_window(b, win, 0.55, 1.6, M, depth=0.08)
        b.lathe(cap, [(r + 0.35, z1), (r * 0.7, z1 + cap_h * 0.35), (0.12, z1 + cap_h)], (x, y, 0), seg=seg, smooth=True)
        if finial:
            b.cyl(gold, 0.06, 0.04, 1.6, (x, y, z1 + cap_h - 0.1), seg=4)

    # ---------------------------------------------------------------- 主樓（Palas）
    PX0, PX1, PY0, PY1 = -44.0, 0.0, -9.0, 9.0
    H_P = 33.0
    b.box_base(stone, (PX1 - PX0, PY1 - PY0, H_P), ((PX0 + PX1) / 2, 0, 0))
    b.box_base(plinth, (PX1 - PX0 + 0.6, PY1 - PY0 + 0.6, 3.0), ((PX0 + PX1) / 2, 0, 0))
    for z in (8.2, 14.6, 21.0, 27.4):     # 樓層腰線
        b.box_base(trim, (PX1 - PX0 + 0.4, PY1 - PY0 + 0.4, 0.35), ((PX0 + PX1) / 2, 0, z))
    b.box_base(trim, (PX1 - PX0 + 0.8, PY1 - PY0 + 0.8, 0.7), ((PX0 + PX1) / 2, 0, H_P - 0.7))
    rows = (4.0, 9.4, 15.8, 22.2, 28.4)
    win_rows(PX0 + 1, PX1 - 1, PY0 - 0.02, -1, rows, 11, w=1.5, h=3.2)
    win_rows(PX0 + 1, PX1 - 1, PY1 + 0.02, 1, rows, 11, w=1.5, h=3.2)
    win_rows_y(PY0 + 1, PY1 - 1, PX0 - 0.02, -1, rows, 4, w=1.5, h=3.2)
    win_rows_y(PY0 + 1, PY1 - 1, PX1 + 0.02, 1, rows, 4, w=1.5, h=3.2)
    # 西立面的陽台（三層）
    for z in (9.0, 15.4, 21.8):
        b.box_base(trim, (1.6, 9.0, 0.5), (PX0 - 0.8, 0, z))
        b.box_base(stone_d, (0.3, 9.0, 1.1), (PX0 - 1.45, 0, z + 0.5))
    gable_roof(PX0, PX1, PY0, PY1, H_P, 15.0, dormers=7)
    # 西南、西北角樓（兩座並列於南立面左端）
    turret(PX0 + 0.5, PY0 - 0.5, 20.0, H_P + 3.0, 1.9, 6.5)
    turret(PX0 + 7.0, PY0 - 0.6, 24.0, H_P + 2.0, 1.4, 5.0)
    turret(PX0 + 0.5, PY1 + 0.5, 20.0, H_P + 3.0, 1.9, 6.5)
    # 南面中段小塔（帶尖頂）
    turret(-21.0, PY0 - 1.2, 18.0, H_P + 9.0, 2.0, 9.5)
    # 北側樓梯塔：八角形、65 m
    tx, ty = -30.0, PY1 + 2.6
    b.lathe(stone, [(3.4, 0), (3.4, H_P + 16.0)], (tx, ty, 0), seg=8, smooth=False, rot_offset=math.pi / 8)
    for z in range(6, int(H_P + 14), 5):
        M = T(tx, ty - 3.15, z) @ Rz(0)
        arched_window(b, win, 0.8, 1.8, M, depth=0.1)
    b.lathe(trim, [(3.5, H_P + 15.6), (3.9, H_P + 16.0), (3.2, H_P + 16.0)], (tx, ty, 0), seg=8, smooth=False, rot_offset=math.pi / 8)
    # 塔頂：開窗的小樓層＋尖頂
    b.lathe(stone, [(3.0, H_P + 16.0), (3.0, H_P + 21.5)], (tx, ty, 0), seg=16, smooth=False)
    for k in range(8):
        a = TAU * (k + 0.5) / 8
        arched_window(b, win, 0.8, 2.6, T(tx + math.cos(a) * 3.02, ty + math.sin(a) * 3.02, H_P + 17.5) @ Rz(a + math.pi / 2), depth=0.08)
    b.lathe(trim, [(3.1, H_P + 21.2), (3.4, H_P + 21.6), (2.8, H_P + 21.6)], (tx, ty, 0), seg=16, smooth=False)
    b.lathe(slate, [(3.3, H_P + 21.6), (1.6, H_P + 26.5), (0.9, H_P + 30.0), (0.1, H_P + 33.0)], (tx, ty, 0), seg=16, smooth=True)
    b.cyl(gold, 0.08, 0.04, 2.0, (tx, ty, H_P + 32.8), seg=4)
    # 小天鵝（屋脊東端）：以金色小球代表
    b.ico(gold, 0.5, (PX0 - 0.2, 0, H_P + 15.2), subdiv=1)

    # ---------------------------------------------------------------- 中段：閨房樓（Kemenate）與騎士樓
    KX0, KX1 = 0.0, 40.0
    H_K = 22.0
    b.box_base(stone, (KX1 - KX0, 13.0, H_K), ((KX0 + KX1) / 2, -2.5, 0))
    b.box_base(plinth, (KX1 - KX0 + 0.6, 13.6, 2.6), ((KX0 + KX1) / 2, -2.5, 0))
    for z in (7.8, 14.4):
        b.box_base(trim, (KX1 - KX0 + 0.4, 13.4, 0.3), ((KX0 + KX1) / 2, -2.5, z))
    b.box_base(trim, (KX1 - KX0 + 0.8, 13.8, 0.6), ((KX0 + KX1) / 2, -2.5, H_K - 0.6))
    win_rows(KX0 + 1, KX1 - 1, -9.02, -1, (3.6, 9.4, 16.0), 8, pair=False, w=1.1, h=2.4)
    gable_roof(KX0, KX1, -9.0, 4.0, H_K, 8.5, ends=(False, True), dormers=4)
    # 南側凸出的方形石造基座（拱門）：參考照中段下方的厚重石牆
    b.box_base(plinth, (15.0, 6.0, 14.0), (14.0, -11.5, -2.0))
    arched_window(b, win, 2.2, 4.2, T(14.0, -14.52, 0.0), depth=0.12)
    # 閨房樓的小尖塔（帶山牆）
    turret(4.5, -9.8, 16.0, H_K + 6.0, 1.8, 6.5)
    # 騎士樓與方塔間的連接段
    b.box_base(stone_d, (12.0, 10.0, 16.0), (46.0, 0.0, 0))
    gable_roof(40.0, 52.0, -5.0, 5.0, 16.0, 6.0, ends=(False, False), dormers=2)
    # ---------------------------------------------------------------- 方塔（Viereckturm）
    QX, QY = 47.0, 7.0
    b.box_base(stone, (8.5, 8.5, 38.0), (QX, QY, 0))
    for z in (12.0, 24.0):
        b.box_base(trim, (8.9, 8.9, 0.3), (QX, QY, z))
    for f in range(4):
        a = f * math.pi / 2
        for z in (16.0, 28.0, 33.0):
            M = T(QX, QY, z) @ Rz(a) @ T(0, -4.27, 0)
            for du in (-1.6, 1.6):
                arched_window(b, win, 0.8, 2.2, M @ T(du, 0, 0), depth=0.1)
    # 雉堞（托座外挑）＋四角小塔＋中央圓頂小塔
    b.box_base(trim, (9.4, 9.4, 1.0), (QX, QY, 38.0))
    for f in range(4):
        a = f * math.pi / 2
        for k in range(5):
            u = -4.0 + 8.0 * k / 4
            p = Vector((QX, QY, 0)) + Vector((math.cos(a) * u - math.sin(a) * -4.45, math.sin(a) * u + math.cos(a) * -4.45, 0))
            b.box_base(stone, (1.1, 1.1, 1.6), (p.x, p.y, 39.0), rot=(0, 0, a))
    b.lathe(stone, [(2.8, 39.0), (2.8, 44.0)], (QX, QY, 0), seg=14, smooth=False)
    b.lathe(slate, [(3.1, 44.0), (1.4, 46.5), (0.1, 49.0)], (QX, QY, 0), seg=14, smooth=True)
    b.cyl(gold, 0.06, 0.04, 1.4, (QX, QY, 48.8), seg=4)

    # ---------------------------------------------------------------- 門樓（Torbau，紅磚＋白石）
    GX0, GX1 = 58.0, 82.0
    b.box_base(brick, (GX1 - GX0, 16.0, 18.0), ((GX0 + GX1) / 2, 1.0, 0))
    for z in (6.0, 12.0):
        b.box_base(trim, (GX1 - GX0 + 0.3, 16.3, 0.4), ((GX0 + GX1) / 2, 1.0, z))
    b.box_base(trim, (GX1 - GX0 + 0.8, 16.8, 0.9), ((GX0 + GX1) / 2, 1.0, 18.0))
    win_rows(GX0 + 1, GX1 - 1, -7.02, -1, (7.4, 13.2), 6, pair=False, w=1.0, h=2.2)
    for k in range(10):
        u = GX0 + (GX1 - GX0) * (k + 0.5) / 10
        for yy in (-7.6, 9.6):
            b.box_base(trim, (1.2, 0.9, 1.5), (u, yy, 18.9))
    b.box_base(slate, (GX1 - GX0 - 3.0, 12.0, 0.6), ((GX0 + GX1) / 2, 1.0, 18.9))
    for cx_, cy_ in ((GX0, -7.0), (GX1, -7.0), (GX1, 9.0)):
        b.lathe(stone, [(2.2, 0), (2.2, 22.0)], (cx_, cy_, 0), seg=14, smooth=False)
        b.lathe(trim, [(2.4, 22.0), (2.7, 23.0), (2.0, 23.0)], (cx_, cy_, 0), seg=14, smooth=False)
        for k in range(7):
            a = TAU * k / 7
            b.box_base(stone, (0.8, 0.8, 1.2), (cx_ + math.cos(a) * 2.35, cy_ + math.sin(a) * 2.35, 23.0), rot=(0, 0, a))
    arched_window(b, win, 3.6, 6.0, T(70.0, -7.05, 0.0), depth=0.12)
    # 下庭院圍牆
    b.box_base(stone_d, (8.0, 1.6, 8.0), (54.0, -8.0, 0))

    # ---------------------------------------------------------------- 森林
    rng = b.rng

    def in_castle(x, y):
        return -52 < x < 90 and -18 < y < 18

    pts = b.scatter(330, 18, 110, min_dist=5.0, avoid=lambda x, y: in_castle(x, y))
    pts += b.scatter(150, 110, 228, min_dist=9.5, avoid=lambda x, y: in_castle(x, y))
    for i, (x, y) in enumerate(pts):
        z = height(x, y)
        if z < -92:
            continue
        if i % 5 == 0:
            broadleaf(b, x, y, rng.uniform(14, 22), leaves, trunk, z=z, blobs=6, sub=1)
        else:
            conifer(b, x, y, rng.uniform(18, 30), con, trunk, z=z)

    b.export(path)
