"""sphinx 吉薩獅身人面像寫實模型（公尺；長 73、寬 19、高 20，面向正東 = +X）"""

import math

from mathutils import Vector, noise

from lib import TAU, Builder

import os

# 目標點、方位角、仰角、距離、焦距（對應參考照：東南側地面視角）
CAMERA = ((0.0, 0.0, 8.5), 32.0, 1.0, 36.0, 20.0)

if os.environ.get("TL_CAM"):  # 開發用：覆寫預覽相機
    CAMERA = eval(os.environ["TL_CAM"])


# ---------------------------------------------------------------- 共用工具
def loft(b, mi, rings, smooth=True):
    """依序連接多個同點數截面環；兩端以中心點扇形封口"""
    vr = [[b.bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    faces = []
    for a, c in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append(b.bm.faces.new([a[i], a[j], c[j], c[i]]))
    for ring, rev in ((vr[0], True), (vr[-1], False)):
        cen = sum((v.co for v in ring), Vector()) / n
        cv = b.bm.verts.new(cen)
        for i in range(n):
            j = (i + 1) % n
            f = b.bm.faces.new([ring[j], ring[i], cv] if rev else [ring[i], ring[j], cv])
            faces.append(f)
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


# ---------------------------------------------------------------- 主體
def sphinx(path):
    b = Builder("Sphinx", seed=11)
    body_m = b.tex("body", "rock_04", tile=3.0, tint="#c98f48", normal=1.6)
    groove = b.tex("groove", "rock_04", tile=3.0, tint="#9a6e3c", normal=1.6)
    head_m = b.tex("head", "rock_04", tile=2.0, tint="#c98a4c", normal=1.2)
    clad = b.tex("clad", "sandstone_blocks_05", tile=3.0, tint="#c99552", normal=1.0)
    floor_m = b.tex("floor", "sand_01", tile=5.0, tint="#d6ab68", normal=0.8)
    bedrock = b.tex("bedrock", "rock_04", tile=6.0, tint="#c29a62", normal=1.3)
    granite = b.tex("granite", "rock_04", tile=1.5, tint="#8a5a4c", normal=0.6)
    dark = b.color("shade", "#7d6248", rough=0.95)

    def strata(v, amp=0.32, k_top=0.0):
        """沿水平層理的侵蝕：軟層內凹、硬層外凸"""
        z = v.z
        ph = z * TAU / 1.45 + 0.6 * noise.noise(Vector((v.x * 0.08, 0, z * 0.3)))
        band = max(-1.0, min(1.0, math.sin(ph) * 2.2))  # 階梯狀層理：硬層外凸、軟層內凹
        rnd = noise.noise(Vector((v.x * 0.35, v.y * 0.35, z * 0.9))) * 0.5
        d = (band * 0.7 + rnd) * amp * (1 - k_top)
        top = (noise.noise(Vector((v.x * 0.12, 7.0, 0))) * 0.9 + noise.noise(Vector((v.x * 0.5, v.y * 0.5, 3.0))) * 0.35) * max(0.0, k_top) if k_top > 0 else 0.0
        v = v + Vector((0, 0, top))
        out = Vector((0, v.y, 0))
        if out.length > 1e-6:
            out.normalize()
        return v + out * d

    # ---- 獅身：X 方向放樣（臀部 x=-45 → 胸前 x=+13）
    tab = [  # x, 半寬, 高
        (-45.5, 3.0, 4.5), (-44.0, 5.6, 8.6), (-41.5, 6.7, 10.6), (-36.0, 7.0, 11.0),
        (-24.0, 6.6, 10.6), (-12.0, 6.5, 10.8), (-4.0, 6.9, 11.6), (2.0, 7.4, 13.2),
        (7.0, 7.4, 14.4), (10.5, 6.9, 14.4), (12.6, 6.2, 13.8), (13.8, 5.2, 13.0), (14.5, 3.4, 10.5), (14.8, 1.2, 6.0),
    ]
    rings = []
    xs = [tab[0][0] + (tab[-1][0] - tab[0][0]) * i / 72 for i in range(73)]
    for x in xs:
        W, H = lerp_table(tab, x)
        rings.append(section_x(x, W, H, n=128, p=5.0, warp=lambda v, H=H: strata(v, 0.45, max(0.0, (v.z - H * 0.82) / (H * 0.18)))))
    faces = loft(b, body_m, rings)
    # 下層（約 3.5 m 內）為後世修補的石塊包覆
    for f in faces:
        if f.calc_center_median().z < 3.4 and abs(f.normal.z) < 0.7:
            f.material_index = clad

    # ---- 頭部：水平截面放樣（頸 → 頭巾 → 頭頂）
    hx = 8.2
    b.bm.verts.ensure_lookup_table()
    head_start = len(b.bm.verts)
    htab = [  # z, 中心x, 半寬, 半深, 前伸
        (11.8, hx - 0.8, 5.6, 3.8, 1.0), (13.2, hx - 0.5, 5.2, 3.3, 1.0), (14.3, hx - 0.5, 4.5, 2.9, 1.0),
        (15.6, hx - 0.6, 3.8, 2.6, 1.0), (17.0, hx - 0.6, 3.3, 2.6, 1.0), (18.4, hx - 0.6, 2.95, 2.7, 1.0),
        (19.2, hx - 0.7, 2.65, 2.6, 1.0), (19.8, hx - 0.8, 2.25, 2.3, 1.0), (20.2, hx - 0.9, 1.5, 1.6, 1.0),
    ]
    hr = []
    for z, cx, W, D, fr in htab:
        hr.append(section_z(z, cx, W, D, n=48, p=2.6, front=fr))
    loft(b, head_m, hr)

    # 臉：突出於頭巾前方的長方臉（寬約 4.1 m，自下巴到額頭 ≈ 5 m）
    fx = hx + 1.9
    ftab = [  # z, 半寬, 前伸
        (14.0, 1.25, 0.7), (14.6, 1.7, 1.2), (15.4, 2.0, 1.45), (16.6, 2.05, 1.55), (17.6, 2.05, 1.5),
        (18.4, 2.0, 1.4), (18.9, 1.9, 1.0),
    ]
    fr = []
    for z, W, D in ftab:
        fr.append(section_z(z, fx, W, D, n=32, p=3.6))
    loft(b, head_m, fr)
    # 眉骨、眼窩、斷鼻與嘴（風化後的淺浮雕）
    for sgn in (-1, 1):
        b.rock(groove, (0.5, 0.85, 0.42), (fx + 1.25, sgn * 0.95, 17.0), rough=0.08, subdiv=2, seed=3 + sgn)
        b.rock(head_m, (0.6, 1.25, 0.32), (fx + 1.4, sgn * 0.95, 17.5), rough=0.06, subdiv=2, seed=5 + sgn)
        b.rock(head_m, (0.7, 0.9, 1.2), (fx + 1.25, sgn * 1.1, 15.9), rough=0.1, subdiv=2, seed=7 + sgn)  # 臉頰
    b.rock(head_m, (0.9, 0.7, 1.6), (fx + 1.5, 0, 16.6), rough=0.12, subdiv=2, seed=9)   # 鼻樑殘部
    b.rock(groove, (0.5, 0.75, 0.5), (fx + 1.75, 0, 15.9), rough=0.12, subdiv=2, seed=19)  # 斷鼻斷面
    b.rock(head_m, (0.55, 1.3, 0.28), (fx + 1.45, 0, 15.35), rough=0.05, subdiv=2, seed=10)  # 上唇
    b.rock(groove, (0.45, 1.25, 0.14), (fx + 1.4, 0, 15.15), rough=0.03, subdiv=2, seed=13)  # 嘴縫
    b.rock(head_m, (0.55, 1.15, 0.3), (fx + 1.35, 0, 14.92), rough=0.05, subdiv=2, seed=15)  # 下唇
    b.rock(head_m, (1.0, 1.6, 0.7), (fx + 0.9, 0, 14.25), rough=0.1, subdiv=2, seed=12)  # 下巴
    # 頭巾兩側垂片（lappets）：自太陽穴往肩膀張開，與頭部相接
    for sgn in (-1, 1):
        lp = []
        for z, W, x in ((13.4, 4.6, hx + 1.6), (15.2, 4.2, hx + 1.65), (17.0, 3.55, hx + 1.55), (18.7, 3.1, hx + 1.2)):
            lp.append([Vector((x - 2.6, sgn * (W - 1.7), z)), Vector((x + 0.3, sgn * (W - 1.7), z)),
                       Vector((x + 0.3, sgn * W, z)), Vector((x - 2.2, sgn * (W + 0.1), z))])
        loft(b, head_m, lp, smooth=False)
    # 頭巾額帶
    b.rock(head_m, (2.5, 6.0, 0.45), (hx + 1.0, 0, 18.85), rough=0.05, subdiv=2, seed=14)

    # 頭部整體放大（以頸部為基準）
    b.bm.verts.ensure_lookup_table()
    anchor = Vector((hx, 0, 12.0))
    for v in b.bm.verts[head_start:]:
        v.co = anchor + (v.co - anchor) * Vector((1.25, 1.32, 1.2)) - Vector((0, 0, 0.6))
    # ---- 前爪（現代石塊包覆，長約 15 m）
    for s in (-1, 1):
        ptab = [(5.0, 2.2, 3.1), (12.0, 2.15, 3.2), (24.0, 2.1, 3.0), (27.0, 2.0, 2.7), (28.3, 1.6, 2.1), (29.0, 0.8, 1.2)]
        pr = []
        for i in range(25):
            x = 5.0 + 24.0 * i / 24
            W, H = lerp_table(ptab, x)
            pr.append(section_x(x, W, H, n=28, p=4.0, warp=lambda v, s=s: v + Vector((0, s * 4.7, 0))))
        loft(b, clad, pr)
        # 後腿（盤坐於臀側）
        hr2 = []
        for i in range(13):
            x = -43.0 + 18.0 * i / 12
            W, H = lerp_table([(-43.0, 1.0, 2.0), (-39.0, 2.0, 4.8), (-32.0, 1.8, 3.8), (-25.0, 0.8, 1.6)], x)
            hr2.append(section_x(x, W, H, n=24, p=3.0, warp=lambda v, s=s: strata(v + Vector((0, s * 6.6, 0)), 0.15)))
        loft(b, body_m, hr2)
    # 尾巴：繞右（南）臀
    b.rock(body_m, (9.0, 0.9, 0.7), (-38.0, -7.4, 1.5), rot=(0, 0, 0.12), rough=0.1, subdiv=3, seed=21)

    # 兩爪之間的夢之碑（紅花崗岩）與祭壇
    b.box_base(granite, (0.7, 2.2, 3.6), (14.3, 0, 0))
    b.box_base(clad, (2.5, 3.5, 0.8), (18.5, 0, 0))

    # ---- 圍場：岩床地面、三面岩壁與上方台地（只做適量周邊）
    b.box_base(floor_m, (124, 120, 1.0), (0, -2, -1.0))
    wall_h = 7.5

    def cliff(x0, y0, x1, y1, h, seed):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(2, int(L / 9))
        ang = math.atan2(y1 - y0, x1 - x0)
        for i in range(n):
            k = (i + 0.5) / n
            cx, cy = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
            hh = h * (0.9 + 0.15 * b.rng.random())
            b.rock(bedrock, (L / n * 1.3, 6.0, hh + 1.0), (cx, cy, hh / 2 - 0.5), rot=(0, 0, ang), rough=0.12, subdiv=3, seed=seed + i, round_=0.1)

    cliff(-60, -60, -60, 56, wall_h, 100)     # 西側
    cliff(-60, 50, 36, 50, wall_h - 0.5, 200)   # 北側
    cliff(-60, -60, -10, -60, wall_h - 1.0, 300)  # 南側（東段較開闊）
    # 上方台地（實心）
    for sx, sy, w, d, h in ((-77, -2, 30, 124, wall_h - 0.8), (-12, 63, 100, 22, wall_h - 1.2), (-35, -68, 52, 14, wall_h - 1.6)):
        b.box_base(floor_m, (w, d, h + 1.0), (sx, sy, -1.0))
    # 地面散落石塊
    for i in range(26):
        x, y = b.rng.uniform(-55, 50), b.rng.choice([-1, 1]) * b.rng.uniform(14, 38)
        sz = b.rng.uniform(0.4, 1.4)
        b.rock(bedrock, (sz, sz * 0.8, sz * 0.6), (x, y, sz * 0.25), rough=0.15, subdiv=2, seed=400 + i)
    b.export(path)
