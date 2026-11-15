"""christ-redeemer 里約熱內盧救世基督像寫實模型（公尺；雕像面向 -Y）

科科瓦多山頂：雕像高 30 m（不含 8 m 台座），兩臂展開 28 m；鋼筋混凝土外覆淺灰綠色皂石馬賽克。
台座內有小禮拜堂，四周為觀景平台與階梯，山頂四周為花崗岩峭壁與大西洋雨林。
"""

import ast
import math
import os

from mathutils import Matrix, Vector, noise

from lib import TAU, Builder
from buildings.sphinx import lerp_table, loft
from buildings.statue_of_liberty import tube

# 目標點、方位角、仰角、距離、焦距（對應參考照：自正面略高處空拍）
CAMERA = ((0.0, 0.0, 18.5), 0.0, 20.0, 78.0, 50.0)
if os.environ.get("TL_CAM"):  # 開發用：覆寫預覽相機
    CAMERA = ast.literal_eval(os.environ["TL_CAM"])


def christ_redeemer(path):
    b = Builder("ChristRedeemer", seed=29)
    soap = b.tex("soap", "plastered_wall_04", tile=1.5, tint="#93927f", normal=0.9, rough=0.7)
    soap2 = b.tex("soap2", "plastered_wall_04", tile=1.5, tint="#82826f", normal=0.9, rough=0.7)
    ped = b.tex("ped", "large_sandstone_blocks", tile=3.0, tint="#3d3833", normal=0.9, rough=0.5)
    ped2 = b.tex("ped2", "marble_01", tile=2.0, tint="#b8b4aa", normal=0.5, rough=0.7)
    pave = b.tex("pave", "marble_01", tile=1.5, tint="#a39d90", normal=0.4, rough=0.75)
    wallw = b.tex("wallw", "plastered_wall_04", tile=3.0, tint="#b3ada1", normal=0.4, rough=0.85)
    granite = b.tex("granite", "rock_ground", tile=6.0, tint="#77736a", normal=1.4, rough=0.85)
    forest = b.tex("forest", "rocky_terrain_02", tile=6.0, tint="#2f4425", normal=1.0, rough=0.95)
    leafA = b.tex("leafA", "rocky_terrain_02", tile=3.0, tint="#2c4423", normal=1.4, rough=0.9)
    leafB = b.tex("leafB", "rocky_terrain_02", tile=3.0, tint="#3e5a2c", normal=1.4, rough=0.9)
    iron = b.color("iron", "#3c3c3a", rough=0.6, metal=0.4)
    r = b.rng

    # ---- 山頂：觀景平台四周陡降的花崗岩山體（覆蓋雨林）
    def gh(x, y):
        rr = math.hypot(x * 1.1, y)
        n = noise.noise(Vector((x * 0.05, y * 0.05, 0.3))) * 3.0 + noise.noise(Vector((x * 0.15, y * 0.15, 1.3))) * 0.8
        return -3.0 - 0.055 * max(0.0, rr - 17.0) ** 1.55 + n * min(1.0, max(0.0, rr - 17.0) / 10.0)

    b.ground_disc(forest, 90, granite, depth=60.0, seg=96, rings=30, height_fn=gh)
    # 外露的花崗岩壁
    for i in range(7):
        a = r.uniform(0, TAU)
        rr = r.uniform(34, 70)
        x, y = rr * math.cos(a), rr * math.sin(a)
        s = r.uniform(7, 13)
        b.rock(granite, (s, s * 0.5, s * 0.8), (x, y, gh(x, y) + s * 0.05), rot=(0, 0, a), rough=0.15, subdiv=2, seed=200 + i, round_=0.5)
    # 雨林樹冠：多團不規則深淺綠色團塊
    for i in range(650):
        a = r.uniform(0, TAU)
        rr = math.sqrt(r.uniform(20 ** 2, 86 ** 2))
        x, y = rr * math.cos(a), rr * math.sin(a)
        s = r.uniform(1.8, 3.6)
        b.rock(r.choice((leafA, leafA, leafB)), (s, s, s * 0.7), (x, y, gh(x, y) + s * 0.2), rough=0.3, subdiv=2,
               seed=500 + i, flat_bottom=False, round_=0.75)

    # ---- 觀景平台（上層環繞台座、前方較低的下層平台與階梯）
    top = [(-14, -11), (14, -11), (16, -4), (16, 9), (10, 13), (-10, 13), (-16, 9), (-16, -4)]
    b.prism(wallw, top, -3.5, 3.5)
    b.prism(pave, [(x * 0.99, y * 0.99) for x, y in top], -0.05, 0.1)
    low = [(-20, -24), (8, -24), (12, -18), (12, -11), (-20, -11)]
    b.prism(wallw, low, -8.0, 4.4)
    b.prism(pave, [(x, y) for x, y in low], -3.65, 0.1)
    for k in range(9):  # 階梯：下層平台通往上層
        b.box_base(pave, (6.0, 0.42, 0.4), (-12.0, -11.2 - k * 0.42, -3.6 + (8 - k) * 0.4))

    def railing(pts, z, closed=True):
        n = len(pts)
        for i in range(n if closed else n - 1):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            L = math.hypot(x1 - x0, y1 - y0)
            ang = math.atan2(y1 - y0, x1 - x0)
            b.box(iron, (L, 0.06, 0.06), ((x0 + x1) / 2, (y0 + y1) / 2, z + 1.05), rot=(0, 0, ang))
            b.box(wallw, (L, 0.25, 0.5), ((x0 + x1) / 2, (y0 + y1) / 2, z + 0.25), rot=(0, 0, ang))
            for k in range(int(L / 1.6) + 1):
                u = k / max(1, int(L / 1.6))
                b.cyl(iron, 0.03, 0.03, 1.05, (x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, z), seg=4)

    railing(top, 0.05)
    railing(low, -3.55)

    # ---- 台座（約 9.5 × 9.5 × 8 m，內為小禮拜堂）
    b.box_base(ped2, (11.0, 11.0, 0.5), (0, 0, 0.0))
    b.box_base(ped, (9.5, 9.5, 6.9), (0, 0, 0.5))
    for f in range(4):  # 立面的縱向壁柱與禮拜堂門
        rot = Matrix.Rotation(f * math.pi / 2, 4, "Z")
        for k in range(5):
            p = rot @ Vector((-3.6 + k * 1.8, -4.8, 0.5))
            b.box_base(ped, (0.3, 0.16, 6.9), tuple(p), rot=(0, 0, f * math.pi / 2))
    b.box_base(b.color("door", "#1f1c19", rough=0.9), (1.6, 0.1, 2.6), (0, -4.8, 0.5))
    b.box_base(ped, (10.0, 10.0, 0.5), (0, 0, 7.4))

    # ---- 雕像（自 z = 8.3 起）
    S = 7.9
    rtab = [  # z, 半寬, 前深, 後深
        (0.0, 3.3, 2.3, 2.2), (0.6, 3.25, 2.4, 2.2), (4.0, 3.05, 2.25, 2.1), (9.0, 2.95, 2.15, 2.0), (12.5, 2.9, 2.1, 1.95),
        (13.6, 2.82, 2.05, 1.9), (14.4, 2.95, 2.15, 1.95), (17.5, 3.25, 2.15, 1.9), (20.0, 3.5, 2.0, 1.85), (21.5, 3.45, 1.8, 1.75),
        (22.3, 3.0, 1.55, 1.55), (22.9, 2.0, 1.25, 1.3), (23.4, 1.0, 0.95, 1.0),
    ]
    rings = []
    N = 64
    for i in range(48):
        z = 23.4 * i / 47
        W, Df, Db = lerp_table(rtab, z)
        ring = []
        for k in range(N):
            t = TAU * k / N
            c, s = math.cos(t), math.sin(t)
            fold = 1.0 + (0.035 * math.sin(10 * t + 0.4 * noise.noise(Vector((t, z * 0.1, 0.0)))) + 0.02 * math.sin(23 * t)) * (1.0 - min(1.0, z / 21.0))
            x = W * math.copysign(abs(c) ** 0.7, c) * fold
            y = (-Df if s < 0 else Db) * math.copysign(abs(s) ** 0.85, s) * fold
            ring.append(Vector((x, y if s >= 0 else -abs(y), S + z)))
        rings.append(ring)
    loft(b, soap, rings)
    # 外袍（披風）：自肩頭垂到膝下，下緣比內袍略寬形成衣襬
    mr = []
    for i in range(30):
        z = 7.2 + (22.0 - 7.2) * i / 29
        W, Df, Db = lerp_table(rtab, z)
        ring = []
        for k in range(N):
            t = TAU * k / N
            c, s_ = math.cos(t), math.sin(t)
            fold = 1.0 + 0.05 * math.sin(9 * t + 1.3) * (1.0 - (z - 7.2) / 15.0)
            e = 0.28 * (1.0 - (z - 7.2) / 16.0) + 0.06
            x = (W + e) * math.copysign(abs(c) ** 0.7, c) * fold
            y = ((Df + e) if s_ < 0 else (Db + e)) * abs(s_) ** 0.85 * fold
            ring.append(Vector((x, -y if s_ < 0 else y, S + z)))
        mr.append(ring)
    loft(b, soap2, mr)
    # 腰間的繩帶與胸前的聖心
    b.ering(soap2, (2.86, 2.08), (2.98, 2.2), S + 13.4, S + 13.9, seg=48)
    b.rock(soap2, (0.9, 0.35, 1.0), (-0.9, -2.15, S + 18.6), rough=0.04, subdiv=2, seed=4, round_=0.8)
    # 長袍下緣的衣褶與腳
    for sx in (-0.9, 0.9):
        b.rock(soap, (1.0, 1.3, 0.5), (sx, -2.3, S + 0.25), rough=0.05, subdiv=2, seed=6, round_=0.8)

    # 雙臂：水平伸展，手掌朝前
    for sx in (-1, 1):
        tube(b, soap, [(sx * 2.6, 0.0, S + 21.6), (sx * 5.0, -0.1, S + 21.7), (sx * 9.0, -0.2, S + 21.75), (sx * 12.4, -0.3, S + 21.8)],
             [1.3, 1.15, 0.9, 0.65], seg=12)
        # 手
        b.box(soap, (1.6, 0.45, 1.2), (sx * 13.4, -0.35, S + 21.75), rot=(0, 0, 0))
        b.box(soap, (0.5, 0.4, 0.55), (sx * 12.9, -0.55, S + 22.45), rot=(0, 0.3 * sx, 0))  # 拇指
        # 袖子：自前臂垂下、斜向腋下的布幔
        M = Matrix.Translation(Vector((0, 0.0, S))) @ Matrix.Scale(1.0, 4)
        pts = [(sx * 2.8, 21.9), (sx * 10.2, 22.0), (sx * 10.5, 21.3), (sx * 10.1, 20.0), (sx * 9.0, 18.6), (sx * 7.4, 17.4), (sx * 5.4, 16.3), (sx * 3.2, 15.0)]
        if sx < 0:
            pts = list(reversed(pts))
        sl = b.profile_wall(soap, pts, 2.0, M)
        for v in sl:
            # 布幔中段略微外鼓、邊緣變薄
            k = (abs(v.co.x) - 3.0) / 7.0
            v.co.y += 0.25 * math.sin(max(0.0, min(1.0, k)) * math.pi) * (1 if v.co.y > 0 else -1)

    # 頭頸：略向前低垂，長髮披肩
    b.cyl(soap, 0.85, 0.8, 1.6, (0, -0.1, S + 22.9), seg=14, smooth=True)
    HZ = S + 25.7
    b.ico(soap, 1.0, (0, -0.35, HZ), subdiv=3, scale=(1.35, 1.55, 1.9))
    b.ico(soap2, 1.0, (0, 0.7, HZ + 0.1), subdiv=2, scale=(1.4, 1.2, 1.8))   # 頭髮（中分後披）
    b.rock(soap2, (2.9, 1.2, 2.4), (0, 0.4, HZ - 1.6), rough=0.06, subdiv=2, seed=12, round_=0.8)  # 披肩長髮
    b.rock(soap, (0.4, 0.55, 1.0), (0, -1.85, HZ - 0.1), rough=0.03, subdiv=2, seed=13, round_=0.8)  # 鼻
    b.rock(soap2, (1.5, 0.6, 1.2), (0, -1.5, HZ - 1.45), rough=0.05, subdiv=2, seed=14, round_=0.8)  # 鬍鬚
    # 中分長髮垂在臉頰兩側、眼窩與眉弓
    for sx in (-1, 1):
        b.rock(soap2, (0.75, 1.5, 3.2), (sx * 1.2, -0.25, HZ - 0.6), rot=(0.1, sx * 0.08, 0), rough=0.06, subdiv=2, seed=20 + sx, round_=0.85)
        b.rock(soap2, (0.62, 0.35, 0.32), (sx * 0.5, -1.42, HZ + 0.35), rough=0.02, subdiv=2, seed=24 + sx, round_=0.9)
        b.rock(soap, (0.85, 0.4, 0.22), (sx * 0.5, -1.48, HZ + 0.68), rough=0.02, subdiv=2, seed=26 + sx, round_=0.9)
    b.rock(soap2, (0.5, 0.3, 0.12), (0, -1.6, HZ - 0.95), rough=0.02, subdiv=1, seed=28, round_=0.9)  # 嘴
    # 頭頂的避雷針
    b.cyl(iron, 0.04, 0.02, 1.2, (0, -0.2, HZ + 1.85), seg=4)
    b.export(path)
