"""callanish 卡拉尼什巨石陣（Calanais I，蘇格蘭路易斯島）寫實模型（公尺）

路易斯片麻岩薄石板：中央巨石高約 4.8 m；13 石圓環直徑約 13 m，內有石室墓；
北向雙列石道長約 83 m，另有東、南、西三條單列石排，平面呈十字形。+Y 為北。
"""

import ast
import math
import os

from mathutils import Vector, noise

from lib import TAU, Builder

# 目標點、方位角、仰角、距離、焦距（對應參考照：由南側低角度望向石圈與北石道）
CAMERA = ((0.0, 2.0, 2.4), 12.0, 1.0, 13.5, 22.0)
if os.environ.get("TL_CAM"):  # 開發用：覆寫預覽相機
    CAMERA = ast.literal_eval(os.environ["TL_CAM"])


def callanish(path):
    b = Builder("Callanish", seed=23)
    gneiss = b.tex("gneiss", "rock_04", tile=1.3, tint="#6c6d66", normal=2.0, rough=0.85)
    gneiss2 = b.tex("gneiss2", "rock_04", tile=1.0, tint="#5f615c", normal=2.0, rough=0.9)
    lichen = b.tex("lichen", "rock_04", tile=1.2, tint="#6b6c5e", normal=1.8, rough=0.9)
    grass = b.tex("grass", "grass_ground", tile=2.5, tint="#587230", normal=1.0, rough=0.95)
    soil = b.color("soil", "#4a3c2a", rough=0.95)
    r = b.rng

    def gh(x, y):
        # 略微隆起的山脊（石陣位於小丘上），北側緩降
        return 1.2 * math.exp(-(x * x + (y - 10) ** 2) / 4000) + 0.35 * noise.noise(Vector((x * 0.03, y * 0.03, 0.2)))

    b.ground_disc(grass, 115, soil, depth=2.5, seg=96, rings=36, height_fn=gh)

    def stone(x, y, h, w, t, face, lean=(0.0, 0.0), mi=None, sharp=0.3):
        """片麻岩石板：寬 w、厚 t、高 h；face 為石面朝向角（弧度）；頂端收尖"""
        z0 = gh(x, y)
        mi = mi if mi is not None else r.choice((gneiss, gneiss, gneiss2, lichen))
        vs = b.rock(mi, (t, w, h + 0.4), (x, y, z0 + h / 2 - 0.2), rot=(lean[0], lean[1], face), rough=0.2, subdiv=4, seed=r.randint(0, 99999), round_=0.45)
        seed = r.random() * 50
        top_off = r.uniform(-0.5, 0.5)  # 尖端偏向一側
        slant = r.uniform(-1.0, 1.0)
        for v in vs:
            k = max(0.0, (v.co.z - z0) / h)
            loc = v.co - Vector((x, y, v.co.z))
            # 寬度隨高度收窄（不對稱），形成片麻岩石板的尖頂
            shrink = 1 - sharp * k ** 1.6
            side = Vector((-math.sin(face), math.cos(face), 0))
            along = loc.dot(side)
            perp = loc - side * along
            along = along * shrink + top_off * w * 0.5 * k ** 2
            if k > 0.75:  # 斜切、不規則的頂面
                v.co.z -= (k - 0.75) * h * (0.35 * along / max(w, 0.1) * slant)
            # 片麻岩的縱向節理：沿高度拉長的雜訊形成直條凹凸
            g = 1 + 0.08 * noise.noise(Vector((v.co.x * 1.5 + seed, v.co.y * 1.5, v.co.z * 0.6))) + 0.07 * noise.noise(Vector((v.co.x * 4.0 + seed, v.co.y * 4.0, v.co.z * 0.15)))
            v.co = Vector((x, y, v.co.z)) + (side * along + perp * (1 - 0.3 * k)) * g

    # ---- 中央巨石（4.8 m）
    stone(0.0, 0.0, 4.8, 1.5, 0.38, math.radians(-8), mi=gneiss, sharp=0.3)
    # ---- 13 石圓環（略呈扁圓）
    ring_h = [3.4, 2.9, 3.6, 3.1, 3.3, 2.6, 3.0, 3.5, 2.8, 3.2, 3.6, 3.0, 2.7]
    for i, h in enumerate(ring_h):
        a = TAU * i / 13 + math.radians(6)
        x, y = 6.2 * math.cos(a), 6.8 * math.sin(a)
        stone(x, y, h, r.uniform(0.9, 1.4), r.uniform(0.32, 0.45), a + r.uniform(-0.25, 0.25), (r.uniform(-0.05, 0.05), r.uniform(-0.05, 0.05)), sharp=r.uniform(0.1, 0.35))
    # ---- 圓環內東側的石室墓：低矮石堆與內室石板
    cx, cy = 2.6, -0.4
    for i in range(70):
        a = r.uniform(0, TAU)
        rr = 2.6 * math.sqrt(r.random())
        px, py = cx + rr * math.cos(a), cy + rr * 0.8 * math.sin(a)
        s = r.uniform(0.3, 0.75)
        b.rock(gneiss2, (s, s * 0.8, s * 0.5), (px, py, gh(px, py) + 0.05), rot=(0, 0, r.uniform(0, TAU)), rough=0.12, subdiv=1, seed=500 + i, round_=0.6)
    for dx, dy, ang in ((0.0, 0.7, 0.0), (0.0, -0.7, 0.0), (0.9, 0.0, 1.57)):
        stone(cx + dx, cy + dy, 0.9, 1.0, 0.18, ang, mi=gneiss2, sharp=0.15)
    # 散落的小石塊
    for i in range(30):
        a = r.uniform(0, TAU)
        rr = r.uniform(3, 30)
        px, py = rr * math.cos(a), rr * math.sin(a)
        s = r.uniform(0.25, 0.6)
        b.rock(gneiss2, (s, s * 0.7, s * 0.4), (px, py, gh(px, py) + 0.05), rough=0.15, subdiv=1, seed=700 + i, round_=0.5)

    # ---- 北向雙列石道（偏東約 10°，長約 83 m，兩列相距約 8 m）
    az = math.radians(10)
    fx, fy = math.sin(az), math.cos(az)
    px_, py_ = math.cos(az), -math.sin(az)
    west = [(10, 2.6), (16, 2.0), (22, 1.6), (29, 2.2), (36, 1.4), (43, 1.8), (51, 1.2), (60, 1.5), (70, 1.1)]
    east = [(9, 2.4), (15, 2.2), (21, 1.7), (27, 1.9), (34, 1.5), (41, 1.3), (49, 1.6), (57, 1.0), (66, 1.3), (80, 1.0)]
    for side, rows in ((-1, west), (1, east)):
        for d, h in rows:
            off = side * (3.4 + d * 0.012) + r.uniform(-0.3, 0.3)
            x, y = fx * d + px_ * off, fy * d + py_ * off
            stone(x, y, h, r.uniform(0.7, 1.2), r.uniform(0.3, 0.45), az + math.pi / 2 + r.uniform(-0.3, 0.3), sharp=0.3)
    # ---- 東、南、西單列石排
    for bearing, rows in ((82, [(10, 1.7), (14, 1.4), (18, 1.6), (22, 1.2)]),
                          (190, [(10, 2.2), (14, 1.9), (18, 1.6), (22, 1.5), (26, 1.8)]),
                          (265, [(10, 2.1), (13, 1.6), (16, 1.3), (19, 1.5)])):
        a = math.radians(bearing)
        for d, h in rows:
            x, y = math.sin(a) * d, math.cos(a) * d
            stone(x, y, h, r.uniform(0.7, 1.2), r.uniform(0.3, 0.45), math.pi - a + r.uniform(-0.3, 0.3), sharp=0.3)
    b.export(path)
