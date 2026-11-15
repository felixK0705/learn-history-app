"""pisa 比薩斜塔寫實模型（公尺；+Y 為北，塔身向南傾約 3.97°）

白色大理石圓柱形鐘樓：高約 56 m，底部外徑約 15.5 m。
底層為 15 根半柱的盲拱廊；其上 6 層開放式迴廊各有 30 根小柱與半圓拱；頂端為較小的鐘室（16 個拱窗）。
"""

import ast
import math
import os

from mathutils import Matrix, Vector, noise

from lib import TAU, Builder

# 目標點、方位角、仰角、距離、焦距（對應參考照：草地東側地面仰望，塔身向左＝南傾）
CAMERA = ((0.0, -2.0, 27.0), 90.0, 4.0, 98.0, 32.0)
if os.environ.get("TL_CAM"):  # 開發用：覆寫預覽相機
    CAMERA = ast.literal_eval(os.environ["TL_CAM"])

TILT = math.radians(3.97)


def bay_matrix(r, a, z):
    """切線方向為局部 X、徑向為局部 Y 的立面板矩陣"""
    return Matrix.Translation(Vector((r * math.cos(a), r * math.sin(a), z))) @ Matrix.Rotation(a + math.pi / 2, 4, "Z")


def arch_band(b, mi, r, z, n, h, opening_frac, depth, a0=0.0, seg=8):
    """環形拱廊上緣：n 個半圓拱（拱下無牆）"""
    chord = 2 * r * math.tan(math.pi / n)
    opening = chord * opening_frac
    w = chord / 2
    o = opening / 2
    for i in range(n):
        a = a0 + TAU * i / n
        M = bay_matrix(r, a, z)
        pts = []
        for k in range(seg + 1):
            t = math.pi - math.pi * k / seg
            pts.append((o * math.cos(t), 0.0 + o * math.sin(t)))
        mid = seg // 2
        left, right = pts[: mid + 1], pts[mid:]
        b.profile_wall(mi, [(-w, 0.0), (-o, 0.0)] + left[1:] + [(0.0, h), (-w, h)], depth, M)
        b.profile_wall(mi, [right[0]] + right[1:-1] + [(o, 0.0), (w, 0.0), (w, h), (0.0, h)], depth, M)


def pisa(path):
    b = Builder("Pisa", seed=7)
    marble = b.tex("marble", "marble_01", tile=2.4, tint="#ece6d8", normal=0.6, rough=0.45)
    wall = b.tex("wall", "white_sandstone_blocks_02", tile=3.0, tint="#ddd6c6", normal=0.6, rough=0.6)
    grey = b.tex("grey", "marble_01", tile=1.2, tint="#b9b6ae", normal=0.5, rough=0.5)
    col = b.color("column", "#efe9dc", rough=0.4)
    dark = b.color("dark", "#2f2c28", rough=0.9)
    bronze = b.color("bronze", "#5b4a33", rough=0.5, metal=0.6)
    lawn = b.tex("lawn", "grass_ground", tile=3.0, tint="#5f8a36", gain=1.0, normal=0.6, rough=0.95)
    pave = b.tex("pave", "marble_01", tile=1.6, tint="#d8d2c4", normal=0.4, rough=0.6)
    gravel = b.tex("gravel", "gravel_floor", tile=3.0, tint="#cbbfa8", normal=0.6, rough=0.9)
    soil = b.color("soil", "#5a4a36", rough=0.95)

    # ---- 地面：周邊草坪、塔基下陷的大理石環形步道
    b.ground_disc(lawn, 62, soil, depth=2.0, seg=96, rings=12)
    b.ering(pave, (9.2, 9.2), (12.2, 12.2), -0.25, 0.02, seg=96)
    b.ering(marble, (12.2, 12.2), (12.6, 12.6), -0.25, 0.25, seg=96)  # 環形矮牆
    b.box_base(gravel, (60, 6, 0.04), (-10, 22, 0.0))  # 北側通往主教座堂的步道
    b.box_base(gravel, (6, 40, 0.04), (19, 3, 0.0))

    tower_start = len(b.bm.verts)
    # ---- 基座台階
    b.cyl(marble, 9.2, 9.2, 0.3, (0, 0, -0.25), seg=72)
    b.cyl(marble, 8.6, 8.6, 0.45, (0, 0, 0.05), seg=72)
    # ---- 底層：實心牆加 15 根半柱與盲拱
    R0 = 7.75
    b.cyl(wall, R0, R0, 11.0, (0, 0, 0.5), seg=90)
    for i in range(15):
        a = TAU * (i + 0.5) / 15
        x, y = (R0 + 0.12) * math.cos(a), (R0 + 0.12) * math.sin(a)
        b.cyl(col, 0.42, 0.42, 0.5, (x, y, 0.5), seg=10)   # 柱礎
        b.cyl(col, 0.36, 0.33, 7.6, (x, y, 1.0), seg=10)
        b.cyl(col, 0.33, 0.45, 0.45, (x, y, 8.6), seg=10)  # 柱頭
    arch_band(b, marble, R0 + 0.12, 9.05, 15, 1.7, 0.86, 0.4, a0=0.0, seg=10)
    # 底層的門與盲拱內的菱形窗飾（以暗色小開口表示）
    for i in (2, 9):
        a = TAU * i / 15
        M = bay_matrix(R0 + 0.02, a, 0.5)
        b.profile_wall(dark, [(-0.9, 0), (0.9, 0), (0.9, 3.4), (-0.9, 3.4)], 0.12, M)
    b.ering(marble, (R0 - 0.2, R0 - 0.2), (R0 + 0.55, R0 + 0.55), 10.9, 11.6, seg=90)  # 簷口

    # ---- 六層開放迴廊
    FH = 6.55
    for f in range(6):
        z0 = 11.6 + f * FH
        # 迴廊地板（向外挑出的陽台）與下緣線腳
        b.ering(marble, (6.3, 6.3), (7.95, 7.95), z0, z0 + 0.42, seg=90)
        b.ering(grey, (7.9, 7.9), (8.05, 8.05), z0 + 0.12, z0 + 0.3, seg=90)
        # 內牆（灰白相間的帶狀石材）與暗色門窗
        b.cyl(wall, 6.35, 6.35, FH, (0, 0, z0), seg=72)
        for i in range(0, 30, 5):
            a = TAU * (i + 0.5 + f) / 30
            M = bay_matrix(6.38, a, z0 + 0.42)
            b.profile_wall(dark, [(-0.45, 0), (0.45, 0), (0.45, 2.2), (-0.45, 2.2)], 0.1, M)
        # 30 根小柱
        ch = FH - 0.42 - 1.55
        for i in range(30):
            a = TAU * (i + 0.5) / 30
            x, y = 7.55 * math.cos(a), 7.55 * math.sin(a)
            b.cyl(col, 0.2, 0.2, 0.25, (x, y, z0 + 0.42), seg=8)
            b.cyl(col, 0.16, 0.14, ch - 0.55, (x, y, z0 + 0.67), seg=8)
            b.cyl(col, 0.15, 0.24, 0.3, (x, y, z0 + 0.42 + ch - 0.3), seg=8)
        arch_band(b, marble, 7.55, z0 + 0.42 + ch, 30, 1.55, 0.8, 0.5, seg=8)
        # 拱上方的大理石橫帶（含拱肩的灰色菱形飾帶以灰色條紋表示）
        b.ering(grey, (7.78, 7.78), (7.84, 7.84), z0 + FH - 0.75, z0 + FH - 0.6, seg=90)
    # ---- 第六層迴廊上的簷口
    ztop = 11.6 + 6 * FH
    b.ering(marble, (6.3, 6.3), (8.0, 8.0), ztop, ztop + 0.5, seg=90)
    # ---- 鐘室：較小的圓筒，16 個拱窗
    RB = 5.0
    b.cyl(dark, RB - 0.6, RB - 0.6, 4.4, (0, 0, ztop + 0.5), seg=48)
    zb = ztop + 0.5
    for i in range(16):
        a = TAU * (i + 0.5) / 16
        x, y = RB * math.cos(a), RB * math.sin(a)
    # 拱窗之間的牆墩
    chord = 2 * RB * math.tan(math.pi / 16)
    for i in range(16):
        a = TAU * i / 16
        M = bay_matrix(RB, a, zb)
        w = chord / 2
        o = chord * 0.32
        pts = [(o * math.cos(math.pi - math.pi * k / 8), 2.6 + o * math.sin(math.pi - math.pi * k / 8)) for k in range(9)]
        b.profile_wall(wall, [(-w, 0), (-o, 0), (-o, 2.6), (-w, 2.6)], 0.55, M)
        b.profile_wall(wall, [(o, 0), (w, 0), (w, 2.6), (o, 2.6)], 0.55, M)
        b.profile_wall(wall, [(-w, 2.6), (-o, 2.6)] + pts[1:5] + [(0, 4.3), (-w, 4.3)], 0.55, M)
        b.profile_wall(wall, [pts[4]] + pts[5:8] + [(o, 2.6), (w, 2.6), (w, 4.3), (0, 4.3)], 0.55, M)
    b.ering(marble, (RB - 0.4, RB - 0.4), (RB + 0.35, RB + 0.35), zb + 4.3, zb + 4.75, seg=64)
    # 鐘室頂的平台與欄杆、小旗桿
    b.cyl(grey, RB - 0.4, RB - 0.4, 0.15, (0, 0, zb + 4.75), seg=48)
    for i in range(48):
        a = TAU * i / 48
        b.cyl(bronze, 0.03, 0.03, 0.9, ((RB + 0.2) * math.cos(a), (RB + 0.2) * math.sin(a), zb + 4.75), seg=4)
    b.ering(bronze, (RB + 0.17, RB + 0.17), (RB + 0.25, RB + 0.25), zb + 5.6, zb + 5.66, seg=64)
    b.cyl(bronze, 0.05, 0.04, 3.0, (2.5, 1.0, zb + 4.75), seg=6)
    b.box_base(b.color("flag", "#b0282c", rough=0.8), (0.03, 1.0, 0.65), (2.5, 1.5, zb + 7.0))

    # ---- 整座塔向南傾斜（以基座中心為軸）
    b.bm.verts.ensure_lookup_table()
    R = Matrix.Rotation(TILT, 4, "X")
    for v in b.bm.verts[tower_start:]:
        v.co = R @ v.co

    # ---- 草坪旁的幾棵樹（樹冠以多個不規則團塊組成）
    for x, y, h in ((-40, 34, 9), (-46, 26, 8), (40, -40, 8.5), (-30, -44, 9.5)):
        b.tree(x, y, 0, h)
    b.export(path)
