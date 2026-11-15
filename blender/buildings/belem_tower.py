"""belem-tower 貝倫塔（里斯本，1514–1520，曼努埃爾式）寫實模型（公尺；+Y 為北＝岸邊，-Y 為太巴斯河）

方形塔樓約 12 × 12 m、高約 30 m，北側連接岸邊步橋；南側為伸入河中的多邊形稜堡（高約 8 m）。
塔頂與稜堡上緣為盾形垛口（刻十字），轉角有圓形哨亭（garita）與肋紋圓頂；塔南面有文藝復興式涼廊。
"""

import ast
import math
import os

from mathutils import Matrix, Vector, noise

from lib import TAU, Builder

# 目標點、方位角、仰角、距離、焦距（對應參考照：岸邊東北側略高處，塔在右、稜堡向左延伸）
CAMERA = ((0.0, -3.0, 11.5), 108.0, 3.0, 56.0, 28.0)
if os.environ.get("TL_CAM"):  # 開發用：覆寫預覽相機
    CAMERA = ast.literal_eval(os.environ["TL_CAM"])


def belem_tower(path):
    b = Builder("BelemTower", seed=3)
    stone = b.tex("stone", "white_sandstone_blocks_02", tile=2.6, tint="#b0a287", normal=1.0, rough=0.75)
    stone2 = b.tex("stone2", "white_sandstone_blocks_02", tile=3.0, tint="#c2b8a2", normal=0.9, rough=0.8)
    trim = b.tex("trim", "marble_01", tile=1.5, tint="#c4b89e", normal=0.6, rough=0.65)
    stain = b.tex("stain", "large_sandstone_blocks_01", tile=5.0, tint="#7d7464", normal=1.0, rough=0.85)
    dark = b.color("dark", "#2b2723", rough=0.9)
    water = b.color("water", "#34484a", rough=0.22)
    sand = b.tex("sand", "sand_01", tile=4.0, tint="#b9a888", normal=0.6, rough=0.95)
    lawn = b.tex("lawn", "grass_ground", tile=3.0, tint="#5d7d38", normal=0.6, rough=0.95)
    pave = b.tex("pave", "gravel_floor", tile=2.0, tint="#a69c8a", normal=0.4, rough=0.85)
    wood = b.color("wood", "#6e5a44", rough=0.85)
    iron = b.color("iron", "#3a3a38", rough=0.6, metal=0.4)
    r = b.rng

    # ---- 河面、低潮沙灘、岸邊草地與步道（只做適量周邊）
    b.cyl(water, 70, 70, 0.1, (0, 0, -1.1), seg=96)
    b.prism(sand, [(-16, 16), (-13, 2), (0, -2), (14, -8), (20, 4), (24, 24), (-18, 24)], -1.4, 0.9)
    b.prism(pave, [(-60, 24), (60, 24), (60, 38), (-60, 38)], -1.4, 1.6)
    b.prism(lawn, [(-60, 38), (60, 38), (60, 64), (-60, 64)], -1.4, 1.62)
    b.box_base(stone2, (120, 0.8, 1.0), (0, 24.2, -1.0))  # 岸邊護岸

    # ---- 稜堡：多邊形平面，外牆微斜，上緣垛口
    bast = [(-10.5, 0.0), (10.5, 0.0), (10.5, -15.0), (5.5, -24.0), (-5.5, -24.0), (-10.5, -15.0)]
    bast = list(reversed(bast))  # 逆時針
    H_B = 8.0
    b.prism(stain, bast, -1.4, 2.2)  # 受潮汐浸染的基部
    b.prism(stone, bast, 0.8, H_B - 0.8)
    b.prism(trim, [(x * 1.03, y * 1.02 - 0.0) for x, y in bast], H_B - 0.5, 0.35)  # 頂部線腳

    def merlons_along(pts, z, closed=True, step=1.15, w=0.62, h=1.0, t=0.45, inset=0.25):
        """沿多邊形邊緣放盾形垛口（下方方塊、上方尖頂）"""
        n = len(pts)
        segs = n if closed else n - 1
        for i in range(segs):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            L = math.hypot(x1 - x0, y1 - y0)
            ang = math.atan2(y1 - y0, x1 - x0)
            nx, ny = math.sin(ang), -math.cos(ang)  # 往外法線（逆時針多邊形）
            k = max(1, int(L / step))
            for j in range(k):
                u = (j + 0.5) / k
                cx = x0 + (x1 - x0) * u - nx * inset
                cy = y0 + (y1 - y0) * u - ny * inset
                M = Matrix.Translation(Vector((cx, cy, z))) @ Matrix.Rotation(ang, 4, "Z")
                b.profile_wall(trim, [(-w / 2, 0), (w / 2, 0), (w / 2, h * 0.62), (0, h), (-w / 2, h * 0.62)], t, M)
            # 垛牆（矮牆）
            M = Matrix.Translation(Vector(((x0 + x1) / 2 - nx * inset, (y0 + y1) / 2 - ny * inset, z - 0.9))) @ Matrix.Rotation(ang, 4, "Z")
            b.profile_wall(stone, [(-L / 2, 0), (L / 2, 0), (L / 2, 0.9), (-L / 2, 0.9)], t + 0.1, M)

    merlons_along(bast, H_B + 0.75)
    # 稜堡側牆的砲眼（方形暗口）
    for (x0, y0), (x1, y1) in zip(bast, bast[1:] + bast[:1]):
        if y0 == 0.0 and y1 == 0.0:
            continue
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        nx, ny = math.sin(ang), -math.cos(ang)
        k = max(1, int(L / 3.2))
        for j in range(k):
            u = (j + 0.5) / k
            M = Matrix.Translation(Vector((x0 + (x1 - x0) * u + nx * 0.03, y0 + (y1 - y0) * u + ny * 0.03, 3.4))) @ Matrix.Rotation(ang, 4, "Z")
            b.profile_wall(dark, [(-0.45, 0), (0.45, 0), (0.45, 0.8), (-0.45, 0.8)], 0.08, M)

    def garita(x, y, z, rad=0.75, h=2.0, dome=1.3):
        """圓形哨亭：下方錐形托座、圓筒、肋紋圓頂與尖頂飾"""
        b.lathe(trim, [(0.0, -1.1), (0.25, -1.0), (rad * 0.8, -0.35), (rad + 0.08, 0.0)], (x, y, z), seg=16, smooth=True)
        b.cyl(stone, rad, rad, h, (x, y, z), seg=16)
        for k in range(4):  # 小窗
            a = TAU * k / 4 + 0.4
            M = Matrix.Translation(Vector((x + (rad + 0.02) * math.cos(a), y + (rad + 0.02) * math.sin(a), z + 0.7))) @ Matrix.Rotation(a + math.pi / 2, 4, "Z")
            b.profile_wall(dark, [(-0.14, 0), (0.14, 0), (0.14, 0.6), (0, 0.75), (-0.14, 0.6)], 0.06, M)
        b.cyl(trim, rad + 0.12, rad + 0.12, 0.2, (x, y, z + h), seg=16)
        b.lathe(trim, [(rad + 0.05, 0.0), (rad * 0.95, dome * 0.35), (rad * 0.7, dome * 0.7), (rad * 0.3, dome * 0.95), (0.08, dome * 1.05), (0.12, dome * 1.2), (0.0, dome * 1.6)],
                (x, y, z + h + 0.2), seg=16, smooth=True, radial=lambda t: 1.0 + 0.07 * abs(math.cos(4 * t)))

    # 稜堡轉角哨亭
    for x, y in ((10.5, -15.0), (5.5, -24.0), (-5.5, -24.0), (-10.5, -15.0), (10.5, 0.0), (-10.5, 0.0), (10.5, -7.5), (-10.5, -7.5)):
        garita(x * 0.98, y * 0.98, H_B - 0.2, rad=0.8, h=2.2)

    # ---- 主塔：12 × 12 m，高 30 m；下段較寬（與稜堡相接）
    TW = 12.0
    z_m0 = 20.6
    ty0, ty1 = 0.0, 12.0
    b.box_base(stain, (TW + 0.4, TW + 0.4, 2.4), (0, 6, -1.4))
    b.box_base(stone, (TW, TW, 19.6), (0, 6, 1.0))
    # 轉角的繩紋立柱（曼努埃爾式）
    for sx in (-1, 1):
        for sy in (0.0, 12.0):
            b.cyl(trim, 0.22, 0.22, z_m0 - 1.0, (sx * TW / 2, sy, 1.0), seg=10)
    # 中段線腳
    for z in (H_B + 0.2, 14.2):
        b.box_base(trim, (TW + 0.3, TW + 0.3, 0.35), (0, 6, z))
    # 上段挑出的托架迴廊（machicolation）
    z_m = 20.6
    for i in range(24):
        for side in range(4):
            u = -TW / 2 + 0.25 + (TW - 0.5) * i / 23
            if side == 0:
                x, y, rz = u, ty0 - 0.3, 0
            elif side == 1:
                x, y, rz = u, ty1 + 0.3, 0
            elif side == 2:
                x, y, rz = -TW / 2 - 0.3, 6 + u, 1.57
            else:
                x, y, rz = TW / 2 + 0.3, 6 + u, 1.57
            b.frustum(trim, (0.18, 0.18), (0.32, 0.55), 0.9, (x, y, z_m - 0.9), rot_z=rz)
    b.box_base(trim, (TW + 1.3, TW + 1.3, 0.4), (0, 6, z_m))
    sq = [(-TW / 2 - 0.55, ty0 - 0.55), (TW / 2 + 0.55, ty0 - 0.55), (TW / 2 + 0.55, ty1 + 0.55), (-TW / 2 - 0.55, ty1 + 0.55)]
    merlons_along(sq, z_m + 1.3, step=1.3, w=0.85, h=1.35, t=0.5, inset=0.25)
    for x, y in sq:
        garita(x, y, z_m - 0.1, rad=0.85, h=2.4, dome=1.4)
    # 頂層（退縮的小塔樓）
    UW = 8.2
    b.box_base(stone, (UW, UW + 1.0, 6.4), (-0.6, 6.4, z_m + 0.4))
    sq2 = [(-UW / 2 - 0.6, 6.4 - (UW + 1) / 2), (UW / 2 - 0.6, 6.4 - (UW + 1) / 2), (UW / 2 - 0.6, 6.4 + (UW + 1) / 2), (-UW / 2 - 0.6, 6.4 + (UW + 1) / 2)]
    b.box_base(trim, (UW + 0.4, UW + 1.4, 0.3), (-0.6, 6.4, z_m + 6.8))
    merlons_along([(x + (0.2 if x > -0.6 else -0.2), y + (0.2 if y > 6.4 else -0.2)) for x, y in sq2], z_m + 7.95, step=1.0, inset=0.2)
    for x, y in sq2:
        garita(x, y, z_m + 6.9, rad=0.55, h=1.5, dome=1.0)
    b.cyl(iron, 0.05, 0.04, 4.0, (-0.6, 6.4, z_m + 7.1), seg=6)  # 旗桿

    # ---- 立面開口
    def wall_panel(mi, face, u, z, w, h, arch=True, depth=0.08, out=0.03):
        """在主塔某一面（0 南、1 北、2 西、3 東）貼上開口或浮雕板"""
        if face == 0:
            M = Matrix.Translation(Vector((u, ty0 - out, z)))
        elif face == 1:
            M = Matrix.Translation(Vector((u, ty1 + out, z))) @ Matrix.Rotation(math.pi, 4, "Z")
        elif face == 2:
            M = Matrix.Translation(Vector((-TW / 2 - out, 6 + u, z))) @ Matrix.Rotation(-math.pi / 2, 4, "Z")
        else:
            M = Matrix.Translation(Vector((TW / 2 + out, 6 + u, z))) @ Matrix.Rotation(math.pi / 2, 4, "Z")
        pts = [(-w / 2, 0), (w / 2, 0), (w / 2, h - (w / 2 if arch else 0))]
        if arch:
            pts += [(w / 2 * math.cos(t * math.pi / 6), h - w / 2 + w / 2 * math.sin(t * math.pi / 6)) for t in range(1, 6)]
        pts += [(-w / 2, h - (w / 2 if arch else 0))]
        b.profile_wall(mi, pts, depth, M)
        return M

    for face in (1, 2, 3):
        wall_panel(dark, face, 0.0, 10.4, 1.1, 2.2)            # 二樓窗
        wall_panel(dark, face, -1.6, 15.6, 0.7, 1.6)           # 三樓雙窗
        wall_panel(dark, face, 1.6, 15.6, 0.7, 1.6)
        # 窗下的小陽台（托座與欄板）
        M = wall_panel(trim, face, 0.0, 9.6, 2.4, 0.8, arch=False, depth=0.9, out=0.45)
        wall_panel(trim, face, 0.0, 14.9, 4.6, 0.6, arch=False, depth=0.7, out=0.35)
        # 盾徽與渾天儀浮雕（淺浮雕圓盤）
        wall_panel(trim, face, 0.0, 17.6, 1.4, 1.6, arch=True, depth=0.25, out=0.12)
    # 北面窗、稜堡東牆入口與沿東側的鋼構步橋（自岸邊往南接到入口）
    wall_panel(dark, 1, 0.0, 1.6, 1.2, 2.4)
    M = Matrix.Translation(Vector((10.53, -3.5, 0.9))) @ Matrix.Rotation(math.pi / 2, 4, "Z")
    b.profile_wall(dark, [(-0.9, 0), (0.9, 0), (0.9, 2.3), (0, 3.1), (-0.9, 2.3)], 0.08, M)
    bx = 12.6
    b.box_base(wood, (1.8, 29.0, 0.14), (bx, 10.0, 0.9))
    b.box_base(wood, (1.6, 1.6, 0.14), (11.4, -3.5, 0.9))
    for k in range(10):
        y = -4.0 + k * 3.0
        for sx in (-0.85, 0.85):
            b.cyl(iron, 0.05, 0.05, 2.4, (bx + sx, y, -1.4), seg=6)   # 支柱
            b.cyl(iron, 0.025, 0.025, 1.05, (bx + sx, y, 1.04), seg=4)  # 欄杆柱
    for sx in (-0.85, 0.85):
        b.box_base(iron, (0.05, 29.0, 0.05), (bx + sx, 10.0, 2.05))
        b.box_base(iron, (0.03, 29.0, 0.03), (bx + sx, 10.0, 1.55))
    # 南面文藝復興式涼廊（二樓，面向稜堡平台）
    for k in range(5):
        u = -4.0 + k * 2.0
        wall_panel(dark, 0, u, H_B + 0.6, 1.4, 3.0)
    b.box_base(trim, (TW - 1.0, 1.2, 0.5), (0, ty0 - 0.6, H_B + 0.55))  # 涼廊欄杆台
    for k in range(6):
        b.cyl(trim, 0.16, 0.16, 3.0, (-5.0 + k * 2.0, ty0 - 0.9, H_B + 1.05), seg=8)
    b.box_base(trim, (TW - 1.0, 1.2, 0.4), (0, ty0 - 0.6, H_B + 4.05))
    wall_panel(dark, 0, 0.0, 15.6, 1.0, 2.0)

    # ---- 輕微風化：主塔基部附近的水漬帶由 stain 材質負責；岸邊散落石塊
    for i in range(30):
        x, y = r.uniform(-24, 24), r.uniform(-20, 16)
        if -12 < x < 12 and -20 < y < 13:
            continue
        s = r.uniform(0.3, 1.0)
        b.rock(stain, (s, s * 0.8, s * 0.5), (x, y, -0.4), rough=0.15, subdiv=1, seed=100 + i)
    b.export(path)
