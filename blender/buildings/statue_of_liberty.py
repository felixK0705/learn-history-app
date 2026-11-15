"""statue-of-liberty 自由女神像寫實模型（公尺；雕像面向 -Y）

自由島：十一角星形的伍德堡（Fort Wood）城牆、兩層階梯基座、花崗岩台座（高約 27 m），
銅像腳跟至火炬頂 46 m，地面至火炬頂約 93 m。銅綠色外殼、右手高舉火炬（金色火焰）、左手抱著法典石板、頭戴七道光芒冠冕。
"""

import ast
import math
import os

from mathutils import Matrix, Vector, noise

from lib import TAU, Builder
from buildings.sphinx import lerp_table, loft

# 目標點、方位角、仰角、距離、焦距（對應參考照：自港灣水面望向島的正面）
CAMERA = ((0.0, 0.0, 43.5), 8.0, -10.5, 222.0, 52.0)
if os.environ.get("TL_CAM"):  # 開發用：覆寫預覽相機
    CAMERA = ast.literal_eval(os.environ["TL_CAM"])


def tube(b, mi, pts, radii, seg=12, smooth=True):
    """沿折線放樣的圓管（手臂、火炬柄）；radii 與 pts 對應"""
    rings = []
    for i, (p, r) in enumerate(zip(pts, radii)):
        p = Vector(p)
        d = (Vector(pts[min(i + 1, len(pts) - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        a = d.orthogonal().normalized()
        c = d.cross(a).normalized()
        rings.append([p + (a * math.cos(TAU * k / seg) + c * math.sin(TAU * k / seg)) * r for k in range(seg)])
    loft(b, mi, rings, smooth=smooth)


def statue_of_liberty(path):
    b = Builder("StatueOfLiberty", seed=17)
    copper = b.tex("copper", "plastered_wall_04", tile=3.0, tint="#5e9a86", normal=0.6, rough=0.6)
    copper2 = b.color("copper2", "#4d8573", rough=0.6)
    gold = b.color("gold", "#d9a43a", rough=0.3, metal=0.9)
    granite = b.tex("granite", "large_sandstone_blocks", tile=4.0, tint="#8a7254", normal=1.0, rough=0.8)
    granite2 = b.tex("granite2", "white_sandstone_blocks_02", tile=3.0, tint="#9a8466", normal=0.8, rough=0.8)
    concrete = b.tex("concrete", "plastered_wall_04", tile=4.0, tint="#958c7a", normal=0.6, rough=0.85)
    fortw = b.tex("fortw", "large_sandstone_blocks_01", tile=4.0, tint="#857a66", normal=1.0, rough=0.85)
    dark = b.color("dark", "#2a2826", rough=0.9)
    lawn = b.tex("lawn", "grass_ground", tile=3.0, tint="#557632", normal=0.0, rough=0.95)
    pave = b.tex("pave", "gravel_floor", tile=2.5, tint="#bdb5a5", normal=0.0, rough=0.85)
    water = b.color("water", "#2c4552", rough=0.12)
    seawall = b.tex("seawall", "large_sandstone_blocks_01", tile=3.0, tint="#857a66", normal=1.0, rough=0.85)  # 與城牆共用貼圖
    bark = b.color("bark", "#4d3e30", rough=0.9)
    leaf1 = b.tex("leaf1", "rocky_terrain_02", tile=3.0, tint="#43592a", normal=1.2, rough=0.9)
    leaf2 = b.color("leaf2", "#5e5229", rough=0.9)
    r = b.rng

    # ---- 海面與島（只做適量周邊）
    b.cyl(water, 230, 230, 0.1, (0, 0, -3.1), seg=96)
    island = [(math.cos(a) * rr, math.sin(a) * rr) for a, rr in
              [(TAU * k / 14, 92 + 14 * math.sin(3 * TAU * k / 14) + (25 if k in (10, 11) else 0)) for k in range(14)]]
    b.prism(seawall, island, -3.6, 3.0)
    b.prism(lawn, [(x * 0.985, y * 0.985) for x, y in island], -0.6, 0.62)
    b.prism(pave, [(x * 1.0, y * 1.0) for x, y in island], -0.62, 0.6)  # 外圍步道（比草地略低）

    # ---- 伍德堡：十一角星形城牆，內部填平為平台
    star = []
    for k in range(22):
        a = TAU * k / 22 - math.pi / 2
        rr = 47.0 if k % 2 == 0 else 37.0
        star.append((rr * math.cos(a), rr * math.sin(a)))
    b.prism(fortw, star, 0.0, 6.5)
    b.prism(pave, [(x * 0.97, y * 0.97) for x, y in star], 6.5, 0.15)
    # ---- 兩層階梯基座（混凝土）
    b.frustum(concrete, (44, 44), (42.5, 42.5), 4.6, (0, 0, 6.6))
    b.box_base(pave, (43.0, 43.0, 0.12), (0, 0, 11.2))
    b.frustum(concrete, (30, 30), (28.5, 28.5), 4.0, (0, 0, 11.3))
    b.frustum(granite, (23.0, 23.0), (20.5, 20.5), 3.6, (0, 0, 15.3))  # 台座下段的斜坡基礎
    # 正面階梯
    b.box_base(concrete, (12, 8, 2.4), (0, -25.0, 6.6))
    b.box_base(concrete, (8, 6, 2.4), (0, -17.5, 11.3))
    # ---- 花崗岩台座（19 → 46 m）
    z = 18.9
    b.frustum(granite, (20.5, 20.5), (19.0, 19.0), 4.2, (0, 0, z))
    b.box_base(granite2, (19.6, 19.6, 0.6), (0, 0, z + 4.2))
    b.box_base(granite, (16.8, 16.8, 15.0), (0, 0, z + 4.8))
    # 四面的凹入涼廊（三個開口、四根柱）與轉角壁柱
    for f in range(4):
        rot = Matrix.Rotation(f * math.pi / 2, 4, "Z")
        for k in range(3):
            u = -3.2 + k * 3.2
            M = rot @ Matrix.Translation(Vector((u, -8.42, z + 12.6)))
            b.profile_wall(dark, [(-1.05, 0), (1.05, 0), (1.05, 4.0), (-1.05, 4.0)], 0.06, M)
        for k in range(4):
            u = -4.8 + k * 3.2
            p = rot @ Vector((u, -8.9, z + 12.4))
            b.cyl(granite2, 0.42, 0.42, 4.6, tuple(p), seg=10)
        p = rot @ Vector((0, -8.9, z + 12.2))
        b.box_base(granite2, (11.0, 1.4, 0.3), tuple(p), rot=(0, 0, f * math.pi / 2))
        # 轉角的粗石壁柱
        for sx in (-1, 1):
            p = rot @ Vector((sx * 7.9, -7.9, z + 4.8))
            b.box_base(granite2, (1.6, 1.6, 15.0), tuple(p))
        # 下段的圓盤徽飾
        p = rot @ Vector((0, -8.42, z + 7.6))
        b.cyl(granite2, 1.3, 1.3, 0.25, tuple(p), seg=20, rot=(math.pi / 2, 0, f * math.pi / 2))
    zc = z + 19.8
    b.box_base(granite2, (19.4, 19.4, 1.2), (0, 0, zc))          # 簷口
    b.box_base(granite, (16.4, 16.4, 4.4), (0, 0, zc + 1.2))    # 頂部女兒牆段
    b.box_base(granite2, (17.6, 17.6, 0.8), (0, 0, zc + 5.6))
    for f in range(4):  # 頂段的小圓窗徽飾
        rot = Matrix.Rotation(f * math.pi / 2, 4, "Z")
        for k in range(5):
            p = rot @ Vector((-5.6 + k * 2.8, -8.22, zc + 3.4))
            b.cyl(dark, 0.45, 0.45, 0.1, tuple(p), seg=12, rot=(math.pi / 2, 0, f * math.pi / 2))
    z0 = zc + 6.4  # 雕像基座頂（≈ 46.5 m）
    b.box_base(granite2, (10.5, 10.5, 0.6), (0, 0, z0 - 0.6))

    # ---- 銅像
    S = z0
    # 長袍：水平截面放樣，帶縱向衣褶
    rtab = [  # z, 半寬x, 前y, 後y, 中心y
        (0.0, 6.8, 4.6, 4.2, 0.0), (2.0, 6.4, 4.6, 4.0, 0.0), (6.0, 5.8, 4.4, 3.8, 0.0), (11.0, 5.4, 4.1, 3.5, 0.2),
        (15.0, 5.3, 3.8, 3.4, 0.3), (19.0, 5.4, 3.5, 3.3, 0.3), (22.5, 5.5, 3.6, 3.3, 0.2), (25.0, 5.2, 3.4, 3.1, 0.2),
        (26.5, 4.0, 2.6, 2.6, 0.3), (27.4, 2.6, 1.9, 1.9, 0.3), (28.2, 1.4, 1.3, 1.4, 0.35),
    ]
    rings = []
    N = 72
    for i in range(41):
        zz = 28.2 * i / 40
        W, Df, Db, cy = lerp_table(rtab, zz)
        ring = []
        for k in range(N):
            t = TAU * k / N
            c, s = math.cos(t), math.sin(t)
            fold = 1.0 + (0.1 * math.sin(16 * t + zz * 0.15 + 2.0 * noise.noise(Vector((t * 2, zz * 0.08, 0.0)))) + 0.03 * math.sin(37 * t)) * (1.0 - min(1.0, zz / 27.0) * 0.6)
            x = W * math.copysign(abs(c) ** 0.85, c) * fold
            y = (-(Df) if s < 0 else Db) * abs(s) ** 0.85 * fold + cy
            ring.append(Vector((x, y, S + zz)))
        rings.append(ring)
    loft(b, copper, rings)
    # 披在左肩斜下的外袍（斜向厚褶）
    b.rock(copper2, (5.5, 1.6, 9.0), (0.6, -2.2, S + 19.5), rot=(0.1, -0.5, 0.0), rough=0.04, subdiv=3, seed=60, round_=0.9)
    # 腳：右腳在後，左腳尖露出袍緣
    b.rock(copper, (1.4, 2.6, 0.9), (1.6, -4.4, S + 0.45), rough=0.06, subdiv=2, seed=3, round_=0.7)

    # 頭與頸
    HX, HY, HZ = 0.0, 0.0, S + 31.0
    b.cyl(copper, 1.35, 1.25, 2.4, (0, 0.2, S + 27.6), seg=16, smooth=True)
    b.ico(copper, 1.0, (HX, HY, HZ), subdiv=3, scale=(1.9, 2.25, 2.6))
    # 臉部：鼻、眉、下巴（淺浮雕）
    b.rock(copper, (0.55, 0.9, 1.5), (0, -2.15, HZ - 0.1), rough=0.03, subdiv=2, seed=5, round_=0.8)   # 鼻
    b.rock(copper, (2.6, 0.6, 0.35), (0, -1.95, HZ + 0.75), rough=0.03, subdiv=2, seed=6, round_=0.8)  # 眉
    b.rock(copper, (1.6, 0.9, 0.9), (0, -1.75, HZ - 1.9), rough=0.03, subdiv=2, seed=7, round_=0.8)    # 下巴
    for sx in (-1, 1):
        b.rock(copper2, (0.7, 0.3, 0.35), (sx * 0.75, -1.95, HZ + 0.35), rough=0.03, subdiv=1, seed=8, round_=0.8)  # 眼窩
    # 頭髮（後腦髮髻與兩側波浪）
    b.ico(copper2, 1.0, (0, 0.7, HZ + 0.4), subdiv=2, scale=(2.0, 1.9, 2.3))
    # 冠冕：頭帶與七道光芒（呈扇形向上外放射）
    b.lathe(copper, [(1.7, 0.0), (2.15, 0.0), (2.2, 0.75), (1.75, 0.8)], (0, 0.1, HZ + 1.25), seg=24, smooth=True)
    for k in range(7):
        a = math.radians(-90 + (k - 3) * 27)  # 以前方（-Y）為中心
        dirv = Vector((math.cos(a), math.sin(a), 0.0))
        tilt = 0.55 + 0.2 * (1 - abs(k - 3) / 3)
        d = (dirv * math.cos(tilt) + Vector((0, 0, math.sin(tilt)))).normalized()
        base = Vector((0, 0.1, HZ + 1.6)) + dirv * 2.0
        tip = base + d * 3.0
        tube(b, copper, [tuple(base), tuple(base + d * 1.5), tuple(tip)], [0.35, 0.2, 0.02], seg=6, smooth=False)

    # 右臂高舉火炬（略向外、向前）
    sh = Vector((-4.0, 0.1, S + 26.0))
    el = Vector((-5.0, -0.3, S + 31.5))
    wr = Vector((-5.9, -0.6, S + 37.0))
    tube(b, copper, [tuple(sh), tuple(sh + Vector((-0.4, 0, 2.0))), tuple(el), tuple(wr)], [1.8, 1.5, 1.1, 0.8], seg=14)
    b.ico(copper, 0.9, tuple(wr + Vector((0, 0, 0.5))), subdiv=2, scale=(1.0, 1.0, 1.3))  # 握拳
    # 袖口垂下的布料
    b.rock(copper2, (1.6, 1.4, 4.2), tuple(sh + Vector((-0.4, 0.2, 1.4))), rot=(0, -0.15, 0), rough=0.1, subdiv=2, seed=31, round_=0.6)
    # 火炬：柄、雕花杯、欄杆陽台與金色火焰
    tb = wr + Vector((0, 0, 0.8))
    b.cyl(copper, 0.55, 0.65, 2.6, tuple(tb), seg=14)
    cup = tb + Vector((0, 0, 2.6))
    b.lathe(copper, [(0.6, 0.0), (1.1, 0.4), (1.6, 1.2), (1.75, 1.7), (0.0, 1.7)], tuple(cup), seg=20, smooth=True, radial=lambda t: 1.0 + 0.05 * abs(math.cos(6 * t)))
    b.ering(copper2, (1.95, 1.95), (2.15, 2.15), cup.z + 1.7, cup.z + 2.2, seg=24, center=(cup.x, cup.y))
    b.lathe(gold, [(0.0, 0.0), (1.35, 0.0), (1.2, 0.9), (0.75, 2.0), (0.25, 2.9), (0.0, 3.3)], tuple(cup + Vector((0, 0, 1.7))), seg=16, smooth=True,
            radial=lambda t: 1.0 + 0.12 * math.sin(5 * t))

    # 左臂抱法典石板（石板斜靠在身側，上緣朝外）
    lsh = Vector((4.2, 0.2, S + 25.0))
    lel = Vector((5.6, -0.4, S + 19.5))
    lwr = Vector((5.2, -2.6, S + 21.0))
    tube(b, copper, [tuple(lsh), tuple(lel), tuple(lwr)], [1.4, 1.1, 0.8], seg=12)
    tab_c = Vector((5.7, -2.2, S + 22.2))
    b.box(copper2, (0.62, 4.1, 7.2), tuple(tab_c), rot=(0.55, 0.1, -0.3))
    b.box(copper, (0.66, 4.15, 0.25), tuple(tab_c + Vector((0, -0.4, -0.2))), rot=(0.55, 0.1, -0.3))

    # ---- 島上的樹（落葉樹叢，樹冠由多個不規則團塊構成）
    def tree(x, y, h):
        b.cyl(bark, 0.3, 0.18, h * 0.4, (x, y, 0), seg=6)
        for k in range(9):
            ox, oy = r.uniform(-0.3, 0.3) * h, r.uniform(-0.3, 0.3) * h
            s = h * r.uniform(0.3, 0.45)
            b.rock(r.choice((leaf1, leaf1, leaf2)), (s, s, s * 0.8), (x + ox, y + oy, h * r.uniform(0.45, 0.8)),
                   rough=0.3, subdiv=2, seed=r.randint(0, 9999), flat_bottom=False, round_=0.7)

    for i in range(55):
        a = r.uniform(0, TAU)
        rr = r.uniform(52, 74)
        x, y = rr * math.cos(a), rr * math.sin(a)
        if y < -30 and abs(x) < 40:  # 正面草坪保持開闊
            continue
        tree(x, y, r.uniform(9, 14))
    b.export(path)
