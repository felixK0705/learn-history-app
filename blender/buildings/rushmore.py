"""rushmore 拉什莫爾山國家紀念公園寫實模型（公尺；崖面朝向 -Y）

南達科他州黑山的花崗岩峭壁上刻四位總統頭像（各高約 18 m）：由左至右為華盛頓、傑佛遜、老羅斯福、林肯。
頭像下方為開鑿時堆積的碎石坡，坡上散生西黃松。
"""

import ast
import math
import os

from mathutils import Euler, Matrix, Vector, noise

from lib import TAU, Builder
from buildings.sphinx import lerp_table, loft

# 目標點、方位角、仰角、距離、焦距（對應參考照：自下方觀景台正面仰望）
CAMERA = ((-1.0, 0.0, 50.0), 0.0, -4.0, 250.0, 92.0)
if os.environ.get("TL_CAM"):  # 開發用：覆寫預覽相機
    CAMERA = ast.literal_eval(os.environ["TL_CAM"])


def rushmore(path):
    b = Builder("Rushmore", seed=41)
    carved = b.tex("carved", "rock_04", tile=4.0, tint="#8b857a", normal=1.0, rough=0.8)
    face_m = b.tex("face", "plastered_wall_04", tile=3.0, tint="#8e897f", normal=0.8, rough=0.8)
    face_d = b.tex("faced", "plastered_wall_04", tile=3.0, tint="#6c6861", normal=0.8, rough=0.8)
    cliff = b.tex("cliff", "rock_ground", tile=9.0, tint="#867d70", normal=1.6, rough=0.85)
    cliff2 = b.tex("cliff2", "rock_04", tile=7.0, tint="#766d62", normal=1.6, rough=0.85)
    talus = b.tex("talus", "gray_rocks", tile=4.0, tint="#7f7a71", normal=1.4, rough=0.9)
    ground = b.tex("ground", "rocky_terrain_02", tile=8.0, tint="#6b6a4a", normal=0.8, rough=0.95)
    soil = b.color("soil", "#5b4f40", rough=0.95)
    pine = b.tex("pine", "rocky_terrain_02", tile=2.0, tint="#2a3b22", normal=1.4, rough=0.9)
    pine2 = b.tex("pine2", "rocky_terrain_02", tile=2.0, tint="#36492a", normal=1.4, rough=0.9)
    bark = b.color("bark", "#4a3a2c", rough=0.9)
    r = b.rng

    # ---- 地面
    b.ground_disc(ground, 190, soil, depth=3.0, seg=96, rings=20,
                  height_fn=lambda x, y: 2.0 * noise.noise(Vector((x * 0.012, y * 0.012, 0.4))) - 1.0)

    # ---- 山體：每個 x 一條剖面（正面自坡腳到崖頂，再越過山頂往後到背面），相鄰剖面相連
    def top_z(x):
        return lerp_table([(-95, 30.0), (-80, 70.0), (-62, 92.0), (-52, 88.0), (-44, 72.0), (-32, 64.0), (-22, 65.0),
                           (-8, 60.0), (2, 59.0), (12, 61.0), (22, 60.0), (32, 70.0), (44, 84.0), (55, 82.0), (66, 70.0),
                           (80, 58.0), (95, 30.0)], x)[0] + 2.5 * noise.noise(Vector((x * 0.15, 3.3, 0)))

    def base_z(x):  # 崖腳（碎石坡頂）
        return 24.0 + 6.0 * noise.noise(Vector((x * 0.03, 1.1, 0))) - 0.002 * x * x

    def front_y(x, z):
        zb = base_z(x)
        n = noise.noise(Vector((x * 0.06, z * 0.06, 0.7))) * 4.0 + noise.noise(Vector((x * 0.2, z * 0.2, 1.7))) * 1.2 + noise.noise(Vector((x * 0.025, z * 0.03, 4.1))) * 5.0
        if z < zb:  # 碎石坡（約 33°）
            return -6.0 - (zb - z) * 1.55 + n * 0.4
        y = -4.0 + n
        # 華盛頓頭像下方的衣領與肩部（向前隆起）
        y -= 7.0 * math.exp(-(((x + 26) / 14) ** 2 + ((z - 42) / 9) ** 2))
        # 林肯右側與羅斯福後方的凹入（開鑿面）
        y += 5.0 * math.exp(-(((x - 8) / 9) ** 2 + ((z - 52) / 12) ** 2))
        # 兩側未開鑿的崖面較靠後、較粗糙
        y += 3.0 * max(0.0, abs(x) - 45) / 20
        return y

    NZ = 46
    profiles = []
    xs = [-95 + 190 * i / 126 for i in range(127)]
    for x in xs:
        zt = top_z(x)
        prof = []
        for k in range(NZ):
            z = zt * k / (NZ - 1)
            prof.append(Vector((x, front_y(x, z), z)))
        yt = prof[-1].y
        for k, (dy, dz) in enumerate(((6, 1.5), (16, 3.5), (30, 2.0), (45, -6.0))):
            prof.append(Vector((x, yt + dy, zt + dz - (0 if dz > 0 else 0))))
        prof.append(Vector((x, 60.0, -1.0)))
        prof.append(Vector((x, prof[0].y, -1.0)))
        profiles.append(prof)
    faces = loft(b, cliff, profiles)
    for f in faces:
        c = f.calc_center_median()
        if c.z < base_z(c.x) + 0.5 and c.y < -6.0:
            f.material_index = talus
        elif abs(c.x) < 40 + 6 * noise.noise(Vector((0, c.z * 0.08, 2.0))) and c.z > base_z(c.x) and c.y < 2.0:
            f.material_index = carved
        elif noise.noise(c * 0.05) > 0.15:
            f.material_index = cliff2
    # 碎石坡上的大塊落石
    for i in range(160):
        x = r.uniform(-80, 80)
        zb = base_z(x)
        z = r.uniform(0.0, zb)
        y = -6.0 - (zb - z) * 1.55 - 0.3
        s = r.uniform(0.8, 3.0)
        b.rock(talus, (s, s * 0.8, s * 0.6), (x, y, z + s * 0.15), rot=(0, 0, r.uniform(0, TAU)), rough=0.15, subdiv=1, seed=900 + i, round_=0.4)

    # ---- 四座頭像
    def head(cx, cy, cz, H, yaw=0.0, pitch=0.0, kind="w"):
        R = Euler((pitch, 0.0, yaw)).to_matrix().to_4x4()
        T = Matrix.Translation(Vector((cx, cy, cz))) @ R

        def P(x, y, z):
            return tuple(T @ Vector((x * H, y * H, z * H)))

        def part(mi, size, loc, rot=(0, 0, 0), rough=0.05, seed=0, rnd=0.7):
            vs = b.rock(mi, (size[0] * H, size[1] * H, size[2] * H), (0, 0, 0), rot=rot, rough=rough, subdiv=2, seed=seed, flat_bottom=False, round_=rnd)
            for v in vs:
                v.co = T @ (v.co + Vector((loc[0] * H, loc[1] * H, loc[2] * H)))

        # 頭部：水平截面放樣（以 H 正規化，前方為 -Y）；中線剖面決定下巴、唇、鼻、眉、額
        dc_tab = [(-0.62, 0.16), (-0.5, 0.3), (-0.44, 0.42), (-0.36, 0.43), (-0.31, 0.41), (-0.27, 0.43), (-0.22, 0.44),
                  (-0.17, 0.53), (-0.06, 0.5), (0.04, 0.46), (0.11, 0.47), (0.25, 0.44), (0.38, 0.36), (0.46, 0.22), (0.52, 0.02)]
        df_tab = [(-0.62, 0.16), (-0.5, 0.3), (-0.44, 0.42), (-0.36, 0.43), (-0.31, 0.41), (-0.27, 0.43), (-0.22, 0.43),
                  (-0.17, 0.43), (-0.06, 0.44), (0.04, 0.44), (0.11, 0.47), (0.25, 0.44), (0.38, 0.36), (0.46, 0.22), (0.52, 0.02)]
        w_tab = [(-0.62, 0.22), (-0.44, 0.22), (-0.3, 0.28), (-0.1, 0.33), (0.1, 0.35), (0.3, 0.34), (0.42, 0.27), (0.48, 0.16), (0.52, 0.04)]

        def depth(u, z):
            (dc,) = lerp_table(dc_tab, z)
            (df,) = lerp_table(df_tab, z)
            (W,) = lerp_table(w_tab, z)
            a = min(1.0, abs(u) / W)
            d = df * (1 - 0.6 * a ** 2.4)
            d += (dc - df) * math.exp(-(u / 0.075) ** 4)  # 鼻
            g = lambda cu, cz, su, sz: math.exp(-((abs(u) - cu) / su) ** 2 - ((z - cz) / sz) ** 2)
            d -= 0.1 * g(0.14, 0.03, 0.075, 0.06)   # 眼窩
            d += 0.035 * g(0.14, 0.03, 0.035, 0.03)   # 眼球
            d += 0.02 * g(0.14, 0.1, 0.1, 0.025)      # 眉弓
            d -= 0.025 * math.exp(-(u / 0.13) ** 6 - ((z + 0.305) / 0.012) ** 2)  # 嘴縫
            if kind == "l":
                d -= 0.035 * g(0.21, -0.17, 0.06, 0.09)  # 凹頰
                d += 0.05 * (1 - smooth(-0.5, -0.36, z)) * (1 - a ** 4)   # 下巴鬍
            if kind == "r":
                d += 0.045 * math.exp(-(u / 0.17) ** 4 - ((z + 0.255) / 0.035) ** 2)  # 八字鬍
            return d

        def smooth(e0, e1, x):
            k = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
            return k * k * (3 - 2 * k)

        hair = {"w": 0.06, "j": 0.09, "r": 0.04, "l": 0.05}[kind]
        rings = []
        NF, NB = 28, 14
        for i in range(31):
            z = -0.62 + 1.14 * i / 30
            (W,) = lerp_table(w_tab, z)
            Wh = W + (hair if z > 0.05 else 0.0) * smooth(0.05, 0.25, z)
            ring = []
            for k in range(NF):
                u = -W + 2 * W * k / (NF - 1)
                ring.append(T @ Vector((u * H, -depth(u, z) * H, z * H)))
            for k in range(1, NB):
                t = math.pi * k / NB
                bz = 0.5 * math.sqrt(max(0.0, 1.0 - max(0.0, (z - 0.1) / 0.42) ** 2)) + 0.02
                ring.append(T @ Vector((Wh * math.cos(t) * H, bz * math.sin(t) * H, z * H)))
            rings.append(ring)
        loft(b, face_m, rings)
        # 深色的眼窩陰影、鬍鬚（以較暗的石面表現）
        for sx in (-1, 1):
            part(face_d, (0.11, 0.03, 0.05), (sx * 0.14, -0.385, 0.03), seed=40 + sx, rnd=0.9)
        if kind == "r":
            part(face_d, (0.34, 0.1, 0.075), (0, -0.445, -0.245), seed=16, rnd=0.85)
        if kind == "l":
            part(face_d, (0.38, 0.14, 0.22), (0, -0.33, -0.48), seed=19, rnd=0.85)
        # 耳
        for sx in (-1, 1):
            part(face_m, (0.05, 0.13, 0.2), (sx * 0.33, -0.02, -0.02), seed=7)
        # 頸與肩（往下融入山體）
        part(face_m, (0.5, 0.55, 0.55), (0, 0.3, -0.72), seed=1, rnd=0.85)
        # 頭髮：頭頂與兩側的髮量
        for k in range(5):
            part(face_m, (0.26, 0.4, 0.16), ((k - 2) * 0.12, 0.02 + 0.03 * abs(k - 2), 0.44 - 0.05 * abs(k - 2)), seed=30 + k, rough=0.1, rnd=0.8)
        if kind == "w":  # 華盛頓：後梳髮辮
            for sx in (-1, 1):
                part(face_m, (0.1, 0.3, 0.32), (sx * 0.38, 0.1, 0.0), seed=13 + sx)
    head(-24.0, -10.0, 59.0, 18.5, yaw=-0.12, pitch=0.0, kind="w")
    head(-9.0, -4.5, 55.0, 17.0, yaw=0.38, pitch=-0.15, kind="j")
    head(3.5, 0.5, 49.5, 16.5, yaw=0.05, pitch=0.0, kind="r")
    head(21.5, -5.5, 49.5, 18.0, yaw=0.1, pitch=0.0, kind="l")

    # ---- 西黃松：碎石坡與地面上
    def pine_tree(x, y, z, h):
        b.cyl(bark, 0.25, 0.12, h * 0.6, (x, y, z), seg=6)
        tiers = 5
        for k in range(tiers):
            u = k / tiers
            s = h * (0.26 - 0.18 * u)
            b.rock(r.choice((pine, pine, pine2)), (s, s, h * 0.2), (x + r.uniform(-0.3, 0.3), y + r.uniform(-0.3, 0.3), z + h * (0.32 + 0.6 * u)),
                   rough=0.35, subdiv=1, seed=r.randint(0, 9999), flat_bottom=False, round_=0.5)
        b.cone(r.choice((pine, pine2)), h * 0.06, h * 0.16, (x, y, z + h * 0.88), seg=6)

    for i in range(70):
        x = r.uniform(-90, 90)
        if r.random() < 0.6:
            zb = base_z(x)
            z = r.uniform(1.0, zb - 2.0)
            y = -6.0 - (zb - z) * 1.55 - 0.2
        else:
            y = r.uniform(-140, -50)
            z = 2.0 * noise.noise(Vector((x * 0.012, y * 0.012, 0.4))) - 1.0
        pine_tree(x, y, z - 0.3, r.uniform(9, 17))
    b.export(path)
