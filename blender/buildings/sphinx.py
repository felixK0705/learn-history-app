"""sphinx 吉薩獅身人面像寫實模型（公尺；長 73、寬 19、高 20，面向正東 = +X）

獅身由石灰岩床直接雕出，水平層理風化成一圈圈凹凸的岩層；下半部與前爪為後世修補的小石塊包覆。
頭戴條紋頭巾（nemes），兩側垂片向肩膀張開；臉寬約 4.1 m，鼻已斷。
"""

import ast
import math
import os

from mathutils import Vector, noise

from lib import TAU, Builder

# 目標點、方位角、仰角、距離、焦距（對應參考照：東南側地面視角，頭朝右）
CAMERA = ((-1.0, 0.0, 7.5), 32.0, 3.0, 38.0, 18.0)

if os.environ.get("TL_CAM"):  # 開發用：覆寫預覽相機
    CAMERA = ast.literal_eval(os.environ["TL_CAM"])


# ---------------------------------------------------------------- 共用工具（moai.py 也會使用）
def loft(b, mi, rings, smooth=True, cap=True):
    """依序連接多個同點數截面環；兩端以中心點扇形封口"""
    vr = [[b.bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    faces = []
    for a, c in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append(b.bm.faces.new([a[i], a[j], c[j], c[i]]))
    if cap:
        for ring, rev in ((vr[0], True), (vr[-1], False)):
            cen = sum((v.co for v in ring), Vector()) / n
            cv = b.bm.verts.new(cen)
            for i in range(n):
                j = (i + 1) % n
                faces.append(b.bm.faces.new([ring[j], ring[i], cv] if rev else [ring[i], ring[j], cv]))
    for f in faces:
        f.material_index = mi
        f.smooth = smooth
    return faces


def section_x(x, W, H, z0=0.0, n=40, p=4.0, warp=None):
    """垂直於 X 軸的圓角矩形截面（YZ 平面），底部壓平於 z0"""
    pts = []
    for i in range(n):
        t = TAU * i / n
        c, s = math.cos(t), math.sin(t)
        y = W * math.copysign(abs(c) ** (2 / p), c)
        z = z0 + H / 2 + H / 2 * math.copysign(abs(s) ** (2 / p), s)
        z = max(z, z0)
        v = Vector((x, y, z))
        if warp:
            v = warp(v)
        pts.append(v)
    return pts


def section_z(z, cx, W, D, n=40, p=3.0, front=1.0, warp=None):
    """水平截面（XY 平面）：W 為半寬（Y），D 為半深（X）；front 為前緣伸長倍率"""
    pts = []
    for i in range(n):
        t = TAU * i / n
        c, s = math.cos(t), math.sin(t)
        x = D * math.copysign(abs(c) ** (2 / p), c)
        if x > 0:
            x *= front
        y = W * math.copysign(abs(s) ** (2 / p), s)
        v = Vector((cx + x, y, z))
        if warp:
            v = warp(v)
        pts.append(v)
    return pts


def lerp_table(tab, x):
    if x <= tab[0][0]:
        return tab[0][1:]
    for a, c in zip(tab, tab[1:]):
        if a[0] <= x <= c[0]:
            k = (x - a[0]) / (c[0] - a[0])
            k = k * k * (3 - 2 * k)
            return tuple(av + (cv - av) * k for av, cv in zip(a[1:], c[1:]))
    return tab[-1][1:]


def smooth01(e0, e1, x):
    k = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return k * k * (3 - 2 * k)


# ---------------------------------------------------------------- 主體
def sphinx(path):
    b = Builder("Sphinx", seed=11)
    body_m = b.tex("body", "rock_04", tile=3.5, tint="#bf8c4c", normal=1.6)
    groove = b.tex("groove", "rock_04", tile=3.0, tint="#8f6a40", normal=1.6)
    head_m = b.tex("head", "rock_04", tile=2.5, tint="#bd8b52", normal=1.2)
    clad = b.tex("clad", "sandstone_blocks_05", tile=2.4, tint="#c99d63", normal=1.0)
    floor_m = b.tex("floor", "sand_01", tile=6.0, tint="#cfa870", normal=0.8)
    bedrock = b.tex("bedrock", "rock_04", tile=6.0, tint="#c39a62", normal=1.2)
    wall_m = b.tex("wallm", "sandstone_blocks_05", tile=4.0, tint="#c9a26c", normal=0.9)
    granite = b.tex("granite", "rock_04", tile=1.5, tint="#7d5a4e", normal=0.6)

    # ---- 水平岩層侵蝕：每層上緣硬層外凸、下緣軟層內凹（階梯狀）
    def strata(v, amp, keep_top=0.0):
        z = v.z
        wob = 0.35 * noise.noise(Vector((v.x * 0.06, 0.3, 0.0)))
        layer = 1.15
        ph = (z + wob) / layer
        fr = ph - math.floor(ph)
        step = -1.0 + 2.0 * smooth01(0.05, 0.7, fr)  # 下凹 → 上凸，頂端急收
        if fr > 0.88:
            step = 1.0 - (fr - 0.88) / 0.12 * 1.6
        lid = math.floor(ph)
        strength = 0.7 + 0.6 * (0.5 + 0.5 * noise.noise(Vector((lid * 1.7, v.x * 0.05, 0.0))))
        rnd = noise.noise(Vector((v.x * 0.3, v.y * 0.3, z * 0.7))) * 0.35 + noise.noise(Vector((v.x * 0.08, v.y * 0.1 + 5, z * 0.15))) * 0.6 + noise.noise(Vector((v.x * 0.7, v.y * 0.2, lid * 3.1))) * 0.45 * (abs(noise.noise(Vector((v.x * 0.15, lid * 2.3, 1.0)))) > 0.15)
        d = (step * strength * 0.75 + rnd) * amp * (1.0 - keep_top) * (0.25 + 0.75 * smooth01(2.6, 4.5, z))
        out = Vector((0, v.y, 0))
        if out.length > 1e-6:
            out.normalize()
        return v + out * d

    # ---- 獅身：X 方向放樣（臀部 → 胸前）；高度為背脊高
    tab = [  # x, 半寬, 高
        (-46.0, 3.4, 4.4), (-45.0, 5.6, 7.6), (-43.0, 6.8, 9.4), (-40.0, 7.1, 10.0), (-30.0, 6.8, 10.1),
        (-18.0, 6.5, 9.9), (-8.0, 6.6, 10.0), (-1.0, 6.9, 10.3), (4.0, 7.3, 10.9), (9.0, 7.4, 11.4),
        (12.0, 7.1, 11.2), (14.0, 6.8, 10.8), (15.8, 6.2, 9.2), (16.9, 5.0, 7.0), (17.3, 2.6, 4.0),
    ]
    rings = []
    N = 260
    xs = [tab[0][0] + (tab[-1][0] - tab[0][0]) * i / 90 for i in range(91)]
    for x in xs:
        W, H = lerp_table(tab, x)
        # 背脊頂面保留較平整，側面與胸前層理明顯
        rings.append(section_x(x, W, H, n=N, p=6.0, warp=lambda v, H=H: strata(v, 0.8, 0.6 * smooth01(H * 0.9, H, v.z))))
    faces = loft(b, body_m, rings)
    for f in faces:
        c = f.calc_center_median()
        if c.z < 3.2 and abs(f.normal.z) < 0.8 and c.x > -44:
            f.material_index = clad  # 下層修補石塊
    # 胸前胸甲般的層疊（前胸更明顯的凸出岩層）
    for k, z in enumerate((5.6, 7.0, 8.4)):
        b.rock(body_m, (2.2, 10.5 - k * 0.8, 0.8), (16.2 - k * 0.7, 0, z), rough=0.08, subdiv=3, seed=31 + k, round_=0.6)

    # ---- 頸部（下巴下方）
    hx = 8.6  # 頭部中心 x
    neck = []
    for z, W, D in ((10.0, 3.3, 3.0), (11.5, 2.9, 2.4), (13.0, 2.6, 2.0), (14.6, 2.5, 1.9)):
        neck.append(section_z(z, hx + 0.4, W, D, n=32, p=2.6))
    loft(b, head_m, neck)
    # 胸部隆起：由前胸往上收成頸部（頭部底下不留台階）
    chest = []
    for z, cx, W, D in ((5.0, hx + 2.6, 6.6, 5.6), (8.0, hx + 2.4, 6.5, 5.2), (10.0, hx + 1.9, 5.9, 4.5),
                        (11.4, hx + 1.3, 4.6, 3.5), (12.6, hx + 0.9, 3.2, 2.5), (13.8, hx + 0.8, 2.6, 2.0)):
        chest.append(section_z(z, cx, W, D, n=120, p=2.4, warp=lambda v: strata(v, 0.45)))
    loft(b, body_m, chest)
    b.bm.verts.ensure_lookup_table()
    head_start = len(b.bm.verts)

    # ---- 頭巾（nemes）：水平截面放樣；下方張開到肩膀、上方收成圓頂
    ntab = [  # z, 中心x, 半寬, 半深
        (10.6, hx - 1.6, 5.4, 4.1), (12.0, hx - 1.4, 5.25, 3.5), (13.5, hx - 1.3, 4.75, 3.0),
        (15.0, hx - 1.2, 4.2, 2.6), (16.5, hx - 1.0, 3.65, 2.35), (17.9, hx - 0.8, 3.2, 2.25), (18.4, hx - 0.2, 3.0, 2.75),
        (18.75, hx + 0.2, 2.9, 3.05), (19.5, hx + 0.15, 2.6, 2.8), (20.0, hx - 0.1, 2.0, 2.1), (20.3, hx - 0.3, 1.0, 1.1),
    ]
    nr = []
    for z, cx, W, D in ntab:
        def nw(v, z=z):
            # 頭巾橫條紋（淺凹槽）
            g = 0.06 * math.sin(v.z * TAU / 0.55)
            o = Vector((v.x - hx, v.y, 0))
            return v + (o.normalized() * g if o.length > 1e-6 else Vector())
        nr.append(section_z(z, cx, W, D, n=56, p=3.2, warp=nw))
    loft(b, head_m, nr)

    # ---- 臉：水平截面放樣；中線剖面（下顎→下巴→唇→斷鼻→眉→額）決定前緣，再刻眼窩
    xc_tab = [(13.4, 1.6), (14.1, 3.3), (14.6, 3.6), (15.4, 3.7), (16.5, 3.75), (17.6, 3.8), (18.4, 3.65), (19.15, 3.45)]
    w_tab = [(13.5, 1.25), (14.15, 1.45), (14.8, 1.8), (15.6, 2.0), (19.15, 2.05)]

    def face_x(y, z):
        (xc,) = lerp_table(xc_tab, z)
        (W,) = lerp_table(w_tab, z)
        a = min(1.0, abs(y) / W)
        x = xc - 1.6 * a ** 2.6  # 臉頰往兩側圓弧後收
        eye = math.exp(-((abs(y) - 0.95) / 0.36) ** 2) * math.exp(-((z - 17.2) / 0.3) ** 2)
        x -= 0.42 * eye
        x += 0.12 * math.exp(-((z - 17.72) / 0.14) ** 2) * (1 - a ** 2)  # 眉骨
        nose = math.exp(-(y / 0.45) ** 4) * smooth01(15.6, 15.85, z) * (1 - smooth01(16.9, 17.5, z))
        x += 0.55 * nose  # 鼻樑殘部（鼻頭已斷，斷面平整）
        mouth = math.exp(-(y / 1.05) ** 6)
        x += 0.14 * mouth * math.exp(-((z - 15.3) / 0.15) ** 2) + 0.12 * mouth * math.exp(-((z - 14.9) / 0.15) ** 2)
        x -= 0.12 * mouth * math.exp(-((z - 15.1) / 0.06) ** 2)
        x += 0.07 * math.exp(-((abs(y) - 1.25) / 0.4) ** 2) * math.exp(-((z - 16.3) / 0.5) ** 2)  # 顴骨
        return hx + x

    fr = []
    M = 40
    for k in range(25):
        z = 13.5 + (19.15 - 13.5) * k / 24
        (W,) = lerp_table(w_tab, z)
        ring = [Vector((face_x(-W + 2 * W * i / (M - 1), z), -W + 2 * W * i / (M - 1), z)) for i in range(M)]
        ring.append(Vector((hx + 0.4, W, z)))
        ring.append(Vector((hx + 0.4, -W, z)))
        fr.append(list(reversed(ring)))
    loft(b, head_m, fr)
    # 耳：位於頭巾垂片前、臉兩側
    for sgn in (-1, 1):
        b.rock(head_m, (0.7, 0.35, 1.2), (hx + 1.95, sgn * 2.2, 16.3), rough=0.08, subdiv=2, seed=40 + sgn, round_=0.6)
    # 頭巾垂片（lappets）前緣：自太陽穴到肩膀的厚板
    for sgn in (-1, 1):
        lp = []
        for z, W in ((11.2, 5.1), (13.0, 4.55), (15.0, 3.75), (17.0, 3.0), (18.8, 2.55)):
            x0 = hx + 1.15 + (0.3 if z > 16 else 0.0)
            lp.append([Vector((x0 - 1.6, sgn * (W - 1.5), z)), Vector((x0 + 0.35, sgn * (W - 1.5), z)),
                       Vector((x0 + 0.35, sgn * W, z)), Vector((x0 - 1.6, sgn * (W + 0.05), z))])
        loft(b, head_m, lp, smooth=False)

    # 頭部整體略放大（以頭頂為基準，臉寬約 4.3 m）
    b.bm.verts.ensure_lookup_table()
    top = Vector((hx, 0, 20.3))
    for v in b.bm.verts[head_start:]:
        v.co = top + (v.co - top) * 1.08
    # ---- 前爪（現代小石塊包覆，長約 15 m）與後腿
    for s in (-1, 1):
        ptab = [(10.0, 2.3, 3.2), (16.0, 2.25, 3.1), (28.0, 2.2, 2.9), (30.5, 2.0, 2.6), (31.6, 1.5, 2.0), (32.2, 0.6, 1.0)]
        pr = []
        for i in range(31):
            x = 10.0 + 22.2 * i / 30
            W, H = lerp_table(ptab, x)
            pr.append(section_x(x, W, H, n=32, p=5.0, warp=lambda v, s=s: v + Vector((0, s * 4.6, 0))))
        loft(b, clad, pr)
        # 爪尖的趾縫
        for t in (-0.75, 0.0, 0.75):
            b.box_base(groove, (1.2, 0.12, 1.4), (31.4, s * 4.6 + t, 0.0))
        # 後腿（盤坐於臀側）
        hr2 = []
        for i in range(15):
            x = -44.5 + 20.0 * i / 14
            W, H = lerp_table([(-44.5, 0.8, 2.0), (-41.0, 1.9, 5.0), (-34.0, 1.8, 4.2), (-28.0, 1.2, 2.2), (-24.5, 0.6, 1.2)], x)
            hr2.append(section_x(x, W, H, n=28, p=3.0, warp=lambda v, s=s: strata(v + Vector((0, s * 6.4, 0)), 0.18)))
        loft(b, body_m, hr2)
        # 後爪
        b.rock(clad, (6.0, 2.0, 1.6), (-27.0, s * 7.9, 0.75), rough=0.05, subdiv=2, seed=60 + s, round_=0.5)
    # 尾巴：繞南側臀部
    b.rock(body_m, (10.0, 0.9, 0.7), (-38.0, -7.6, 1.3), rot=(0, 0, 0.1), rough=0.1, subdiv=3, seed=21)
    # 南側下方的修補扶壁石塊（參考照中可見）
    for x, w, h in ((-31.0, 5.5, 2.6), (-16.0, 4.0, 2.2), (-3.0, 4.5, 3.0)):
        b.box_base(clad, (w, 1.6, h), (x, -6.9, 0.0))

    # 兩爪之間的夢之碑（紅花崗岩）與祭壇
    b.box_base(granite, (0.7, 2.6, 3.6), (17.6, 0, 0))
    b.box_base(clad, (3.0, 4.0, 0.9), (24.0, 0, 0))

    # ---- 圍場：岩床地面、三面岩壁與上方台地（只做適量周邊）
    b.box_base(floor_m, (150, 128, 1.0), (5, -2, -1.0))
    wall_h = 7.0

    def cliff(x0, y0, x1, y1, h, seed):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(2, int(L / 9))
        ang = math.atan2(y1 - y0, x1 - x0)
        for i in range(n):
            k = (i + 0.5) / n
            cx, cy = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
            hh = h * (0.92 + 0.12 * b.rng.random())
            b.rock(bedrock, (L / n * 1.3, 6.0, hh + 1.0), (cx, cy, hh / 2 - 0.5), rot=(0, 0, ang), rough=0.1, subdiv=3, seed=seed + i, round_=0.1)

    cliff(-62, -58, -62, 56, wall_h, 100)       # 西側
    cliff(-62, 52, 30, 52, wall_h - 0.5, 200)    # 北側
    cliff(-62, -58, -14, -58, wall_h - 1.0, 300)  # 南側（東段較開闊）
    # 北側岩壁上的現代石砌護牆（參考照背景的長牆）
    b.box_base(wall_m, (92, 1.2, 2.4), (-16, 55.5, wall_h - 1.4))
    # 上方台地（實心）
    for sx, sy, w, d, h in ((-79, -2, 30, 124, wall_h - 0.8), (-16, 65, 102, 24, wall_h - 1.2), (-38, -66, 50, 12, wall_h - 1.6)):
        b.box_base(floor_m, (w, d, h + 1.0), (sx, sy, -1.0))
    # 地面散落石塊
    for i in range(26):
        x, y = b.rng.uniform(-55, 50), b.rng.choice([-1, 1]) * b.rng.uniform(14, 40)
        sz = b.rng.uniform(0.4, 1.4)
        b.rock(bedrock, (sz, sz * 0.8, sz * 0.6), (x, y, sz * 0.25), rough=0.15, subdiv=2, seed=400 + i)
    b.export(path)
