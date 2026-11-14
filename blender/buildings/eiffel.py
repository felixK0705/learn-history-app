"""eiffel 寫實模型（尺寸依實測資料，公尺）

實測：底座 124.9 m 見方；一層 57.6 m（平台約 70.7 m 見方、外懸於支腳之外）；
二層 115.7 m（約 40.5 m 見方）；三層 276.1 m（18.65 m 見方）；燈籠頂 300 m，天線至 330 m。
四支腳在二層以下分開：一層以下內緣急收、基部有大拱；一、二層之間內緣近乎垂直（開口約 14 m 寬）。
二層以上為單一方柱，依指數曲線收窄。

鋼構以「無端蓋的稜柱管」逐根建模（細桿 3 面平滑、主弦桿 4 面），
輸出前把無貼圖材質的 UV 歸零，讓平滑管頂點共用，控制 GLB 大小。
"""

import math

import bpy
from mathutils import Matrix, Vector

from lib import TAU, Builder


def _interp_log(knots, z):
    """在 (z, w) 節點間對 ln(w) 做 Hermite 插值，得到平滑的指數型輪廓"""
    zs = [k[0] for k in knots]
    ls = [math.log(k[1]) for k in knots]
    if z <= zs[0]:
        return knots[0][1]
    if z >= zs[-1]:
        return knots[-1][1]
    i = max(j for j in range(len(zs) - 1) if zs[j] <= z)
    h = zs[i + 1] - zs[i]
    t = (z - zs[i]) / h

    def slope(j):
        if j == 0:
            return (ls[1] - ls[0]) / (zs[1] - zs[0])
        if j == len(zs) - 1:
            return (ls[-1] - ls[-2]) / (zs[-1] - zs[-2])
        return (ls[j + 1] - ls[j - 1]) / (zs[j + 1] - zs[j - 1])

    m1, m2 = slope(i) * h, slope(i + 1) * h
    t2, t3 = t * t, t * t * t
    v = (2 * t3 - 3 * t2 + 1) * ls[i] + (t3 - 2 * t2 + t) * m1 + (-2 * t3 + 3 * t2) * ls[i + 1] + (t3 - t2) * m2
    return math.exp(v)


# 支腳外緣半寬（中心到支腳外側面）
LEG_OUT = [(0, 62.4), (28, 43.0), (57.6, 27.6), (85, 21.2), (110, 16.9)]
# 支腳內緣半寬
LEG_IN = [(0, 44.0), (20, 32.5), (40, 18.5), (57.6, 7.4), (85, 6.2), (110, 5.6)]
# 二層以上塔身半寬
SHAFT = [(116, 13.6), (180, 9.2), (230, 6.7), (276, 5.0), (300, 3.0)]


def _facade_texture():
    """奧斯曼式立面：米色石材＋每層兩扇深色長窗與鐵欄（6.4 m 見方 = 兩層兩開間）"""
    import os
    import random

    from PIL import Image, ImageDraw, ImageFilter

    from lib import TEX

    out = os.path.join(TEX, "_tinted", "eiffel_facade.jpg")
    if os.path.exists(out):
        return out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    N = 512
    px = N / 6.4
    rnd = random.Random(3)
    im = Image.new("RGB", (N, N), (214, 202, 176))
    d = ImageDraw.Draw(im)
    for _ in range(4000):
        x, y = rnd.randrange(N), rnd.randrange(N)
        v = rnd.randint(-10, 10)
        d.point((x, y), fill=(214 + v, 202 + v, 176 + v))
    for fl in range(2):
        y0 = fl * 3.2
        d.line([(0, N - (y0 + 0.02) * px), (N, N - (y0 + 0.02) * px)], fill=(190, 178, 152), width=3)
        for bay in range(2):
            cx = (bay + 0.5) * 3.2 * px
            x0, x1 = cx - 0.6 * px, cx + 0.6 * px
            ya, yb = N - (y0 + 0.75) * px, N - (y0 + 2.75) * px
            d.rectangle([x0 - 4, yb - 6, x1 + 4, ya + 3], fill=(196, 184, 158))
            d.rectangle([x0, yb, x1, ya], fill=(58, 62, 66))
            d.line([(cx, yb), (cx, ya)], fill=(150, 146, 136), width=2)
            d.line([(x0, yb + 0.6 * px), (x1, yb + 0.6 * px)], fill=(150, 146, 136), width=2)
            # 鑄鐵欄杆
            d.rectangle([x0 - 2, ya - 0.45 * px, x1 + 2, ya], outline=(40, 40, 42), width=2)
            for k in range(7):
                xx = x0 + (x1 - x0) * k / 6
                d.line([(xx, ya - 0.45 * px), (xx, ya)], fill=(40, 40, 42), width=1)
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    im.save(out, quality=88)
    return out


def _img_mat(b, name, img_path, tile, rough):
    m = bpy.data.materials.new(f"{b.name}_{name}")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(img_path, check_existing=True)
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    return b._register(name, m, tile)


def _export(b, path):
    obj = b.build_object()
    me = obj.data
    tex_mats = {i for i, m in enumerate(me.materials) if any(n.type == "TEX_IMAGE" for n in m.node_tree.nodes)}
    uv = me.uv_layers.active.data
    for poly in me.polygons:
        if poly.material_index not in tex_mats:
            for li in poly.loop_indices:
                uv[li].uv = (0.0, 0.0)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_apply=True, export_yup=True,
                              export_image_format="JPEG", export_jpeg_quality=80)


def eiffel(path):
    b = Builder("Eiffel", seed=29)
    bm = b.bm
    # ---------------------------------------------------------------- 材質
    grass = b.tex("grass", "grass_ground", tile=4.0, tint="#5e7f34", gain=0.95)
    soil = b.color("soil", "#5d4a35", rough=0.95)
    gravel = b.tex("gravel", "gravel_floor", tile=2.5, tint="#bba98a", normal=0.0, rough=0.9)
    water = b.color("water", "#53707a", rough=0.1, metal=0.1)
    # 艾菲爾鐵塔棕（暖褐銅色）：主弦桿稍深、斜撐中間調、細腹桿稍亮
    iron = b.color("iron", "#977659", rough=0.55, metal=0.12)
    iron_dark = b.color("iron_dark", "#7c5f48", rough=0.55, metal=0.12)
    iron_lt = b.color("iron_lt", "#a6876a", rough=0.6, metal=0.1)
    band = b.tex("band", "rusty_painted_metal", tile=4.0, tint="#8d6d52", rough=0.55, metal=0.1, normal=0.5)
    glass = b.color("glass", "#56656b", rough=0.1, metal=0.4)
    shade = b.color("shade", "#3d3026", rough=0.8)
    stone = b.tex("pier", "large_sandstone_blocks", tile=3.0, tint="#b9aa8e", normal=0.0, rough=0.85)
    cream = b.tex("cream", "white_sandstone_blocks_02", tile=3.0, tint="#d9cdb4", normal=0.0, rough=0.85)
    facade = _img_mat(b, "facade", _facade_texture(), 6.4, 0.8)
    roof = b.color("roof", "#5a6068", rough=0.6, metal=0.2)
    win = b.color("window", "#3f4448", rough=0.3)
    antenna = b.color("antenna", "#d6d6d2", rough=0.45, metal=0.4)
    trunk = b.color("trunk", "#4e3b2a", rough=0.9)
    leaves = [b.color("leaf1", "#3a5a24", rough=0.85), b.color("leaf2", "#46692a", rough=0.85),
              b.color("leaf3", "#314f20", rough=0.85), b.color("leaf4", "#537533", rough=0.85)]

    leg_out = lambda z: _interp_log(LEG_OUT, z)
    leg_in = lambda z: _interp_log(LEG_IN, z)
    shaft = lambda z: _interp_log(SHAFT, z)

    # ---------------------------------------------------------------- 鋼構桿件
    def tube(mi, p, q, s, n=3, smooth=True, ext=0.3):
        p, q = Vector(p), Vector(q)
        d = q - p
        L = d.length
        if L < 1e-3:
            return
        dn = d / L
        p2, q2 = p - dn * s * ext, q + dn * s * ext
        hz = dn.cross(Vector((0, 0, 1)))
        u = hz.normalized() if hz.length > 1e-4 else Vector((1, 0, 0))
        v = dn.cross(u)
        r = s * (0.62 if n == 3 else 0.7071)
        off = math.pi / 4 if n == 4 else math.pi / 2
        ra, rb = [], []
        for k in range(n):
            t = off + TAU * k / n
            o = (u * math.cos(t) + v * math.sin(t)) * r
            ra.append(bm.verts.new(p2 + o))
            rb.append(bm.verts.new(q2 + o))
        for k in range(n):
            j = (k + 1) % n
            f = bm.faces.new([ra[k], ra[j], rb[j], rb[k]])
            f.material_index = mi
            f.smooth = smooth

    def chord(mi, p, q, s):
        tube(mi, p, q, s, n=4, smooth=False, ext=0.15)

    lerp = lambda a, c, t: a + (c - a) * t

    def panel(BL, BR, TR, TL, ncol, s_main, s_sec, s_h, nrm, top=False, mid_h=True):
        """一格格架面：底橫桿、整格大 X 斜撐、細分欄位的小 X 與豎桿"""
        oi = nrm * (-0.35)
        chord(iron_dark, BL, BR, s_h)
        if top:
            chord(iron_dark, TL, TR, s_h)
        tube(iron, BL + nrm * 0.1, TR + nrm * 0.1, s_main, n=4, smooth=False)
        tube(iron, BR - nrm * 0.1, TL - nrm * 0.1, s_main, n=4, smooth=False)
        for c in range(ncol):
            bl, br = lerp(BL, BR, c / ncol), lerp(BL, BR, (c + 1) / ncol)
            tl, tr = lerp(TL, TR, c / ncol), lerp(TL, TR, (c + 1) / ncol)
            if ncol > 1:
                tube(iron_lt, bl + oi, tr + oi, s_sec)
                tube(iron_lt, br + oi * 1.4, tl + oi * 1.4, s_sec)
            if c > 0:
                tube(iron, bl + oi, tl + oi, s_sec * 1.2)
        if mid_h:
            tube(iron_lt, lerp(BL, TL, 0.5) + oi, lerp(BR, TR, 0.5) + oi, s_sec * 0.9)

    def ring_panels(rings, center_fn, sizes, ncol_fn, chord_s, last_top=True):
        for k in range(len(rings) - 1):
            A, B = rings[k], rings[k + 1]
            za = A[0].z
            cxy = center_fn(za)
            s_main, s_sec, s_h = sizes(za)
            for ci in range(4):
                cj = (ci + 1) % 4
                BL, BR, TR, TL = A[ci], A[cj], B[cj], B[ci]
                mid = (BL + BR) / 2
                nrm = Vector((mid.x - cxy[0], mid.y - cxy[1], 0)).normalized()
                panel(BL, BR, TR, TL, ncol_fn((BR - BL).length), s_main, s_sec, s_h, nrm, top=(last_top and k == len(rings) - 2))
                chord(iron_dark, A[ci], B[ci], chord_s(za))

    # ================================================================ 地景：戰神廣場（相機側 +Y）、塞納河與夏佑宮（-Y）
    R_G = 440
    b.ground_disc(grass, R_G, soil, depth=6, rings=16, seg=96)
    b.box_base(gravel, (150, 150, 0.1), (0, 0, 0))                 # 塔下鋪面
    b.box_base(gravel, (24, 340, 0.08), (0, 245, 0))               # 中央步道
    for xs in (-1, 1):
        b.box_base(gravel, (16, 340, 0.08), (xs * 52, 245, 0))     # 樹列下砂石步道
        b.box_base(gravel, (22, 340, 0.08), (xs * 88, 245, 0))

    def tree(x, y, h, n=4, spread=0.18):
        b.cyl(trunk, h * 0.035, h * 0.028, h * 0.45, (x, y, 0), seg=5)
        for k in range(n):
            ang = b.rng.uniform(0, TAU)
            rr = b.rng.uniform(0.04, spread) * h
            s = h * b.rng.uniform(0.34, 0.44)
            zc = h * (0.56 + 0.12 * k / n + b.rng.uniform(0, 0.1))
            b.rock(b.rng.choice(leaves), (s * 1.15, s * 1.15, s * 0.95),
                   (x + rr * math.cos(ang), y + rr * math.sin(ang), zc),
                   rot=(0, 0, b.rng.uniform(0, TAU)), rough=0.5, subdiv=1,
                   seed=b.rng.randint(0, 9999), flat_bottom=False, round_=0.75)

    # 兩側樹列（修剪整齊的七葉樹，三排）
    # 樹冠修剪成連續的「綠牆」：樹幹每 9 m 一株，樹冠團塊沿樹列重疊
    for xs in (-1, 1):
        for xr in (64, 76):
            x = xs * xr
            y = 72.0
            while y < 425:
                b.cyl(trunk, 0.45, 0.35, 7.5, (x + b.rng.uniform(-0.4, 0.4), y, 0), seg=5)
                y += 9.0
            y = 70.0
            while y < 428:
                s = b.rng.uniform(7.0, 9.0)
                b.rock(b.rng.choice(leaves), (s * 1.25, s, s * 1.0),
                       (x + b.rng.uniform(-1.5, 1.5), y, b.rng.uniform(11.0, 13.0)),
                       rot=(0, 0, b.rng.uniform(0, TAU)), rough=0.4, subdiv=1,
                       seed=b.rng.randint(0, 9999), flat_bottom=False, round_=0.7)
                y += b.rng.uniform(4.5, 6.0)
    # 塔周邊樹叢
    for x, y in b.scatter(46, 95, 330, avoid=lambda x, y: (abs(x) < 100 and y > 40) or (-205 < y < -110), min_dist=14):
        tree(x, y, b.rng.uniform(12, 19))
    # 塞納河與耶拿橋
    b.box_base(water, (1000, 46, 0.1), (0, -156, 0.02))
    for yy in (-131, -181):
        b.box_base(stone, (1000, 4, 0.9), (0, yy, 0.0))
    b.box_base(stone, (35, 54, 1.6), (0, -156, 0.0))
    # 外圍城市：奧斯曼式街廓（米色石材＋鋅灰屋頂），沿地景外圈排列以遮住邊緣
    def block(cx, cy, w, d, h, a):
        b.box_base(facade, (w, d, h), (cx, cy, 0), rot=(0, 0, a))
        b.box_base(cream, (w + 0.6, d + 0.6, 0.6), (cx, cy, h - 0.6), rot=(0, 0, a))
        b.box_base(roof, (w - 1.0, d - 1.0, 4.5), (cx, cy, h), rot=(0, 0, a))
        b.box_base(roof, (w - 5.0, d - 5.0, 1.5), (cx, cy, h + 4.5), rot=(0, 0, a))

    for r0, r1, step in ((R_G - 38, R_G - 18, (0.06, 0.08)), (R_G - 85, R_G - 62, (0.08, 0.11))):
        ang = b.rng.uniform(0, 0.05)
        while ang < TAU:
            r = b.rng.uniform(r0, r1)
            cx, cy = r * math.cos(ang), r * math.sin(ang)
            # 前方戰神廣場與後方夏佑宮的軸線留空
            if not (abs(cx) < 110 and cy > 0) and not (abs(cx) < 175 and -330 < cy < -150):
                block(cx, cy, b.rng.uniform(24, 34), b.rng.uniform(18, 26), b.rng.uniform(19, 25), ang)
            elif cy < -150 and abs(cx) < 175:
                tree(cx, cy, b.rng.uniform(12, 17))
            ang += b.rng.uniform(*step)
    for xs in (-1, 1):
        y = 40
        while y < 380:
            L = b.rng.uniform(32, 48)
            block(xs * 150, y + L / 2, 34, L, b.rng.uniform(20, 24), 0)
            y += L + b.rng.uniform(10, 16)
    # 夏佑宮（對岸兩翼弧形建築＋兩座端亭）
    for s in (-1, 1):
        t0, t1 = (math.pi * 1.20, math.pi * 1.43) if s < 0 else (math.pi * 1.57, math.pi * 1.80)
        b.ering(cream, (140, 140), (156, 156), 0, 21, seg=72, t0=t0, t1=t1, center=(0, -240))
        b.ering(roof, (141, 141), (155, 155), 21, 22.5, seg=72, t0=t0, t1=t1, center=(0, -240))
        te = t1 if s < 0 else t0
        b.box_base(cream, (24, 34, 27), (148 * math.cos(te), -240 + 148 * math.sin(te), 0))
        b.box_base(roof, (22, 32, 1.5), (148 * math.cos(te), -240 + 148 * math.sin(te), 27))
    for k in range(34):
        tree(b.rng.uniform(-150, 150), b.rng.uniform(-228, -195), b.rng.uniform(10, 15))

    # ================================================================ 石造基座
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = (leg_out(0) + leg_in(0)) / 2
            b.box_base(stone, (23, 23, 2.4), (sx * c, sy * c, 0))

    # ================================================================ 四支腳
    leg_z = [2.4, 9.0, 15.5, 22.0, 28.5, 35.0, 41.5, 47.0, 51.0, 57.6, 64.0, 70.5, 77.0, 83.5, 90.0, 96.5, 103.0, 110.0]
    for sx in (-1, 1):
        for sy in (-1, 1):
            rings = []
            for z in leg_z:
                i, o = leg_in(z), leg_out(z)
                rings.append([Vector((sx * i, sy * i, z)), Vector((sx * o, sy * i, z)),
                              Vector((sx * o, sy * o, z)), Vector((sx * i, sy * o, z))])
            cen = lambda z, sx=sx, sy=sy: (sx * (leg_in(z) + leg_out(z)) / 2, sy * (leg_in(z) + leg_out(z)) / 2)
            f = lambda z: 1.0 - z / 170
            ring_panels(rings, cen, lambda z: (1.05 * f(z) + 0.4, 0.5 * f(z) + 0.22, 0.9 * f(z) + 0.4),
                        lambda w: 3 if w > 16 else 2, lambda z: 2.6 * f(z) + 0.6)
            # 支腳內部斜撐
            for k in range(0, len(rings) - 1, 2):
                A, B = rings[k], rings[k + 1]
                tube(iron, A[0], B[2], 0.55)
                tube(iron, A[1], B[3], 0.55)

    # ================================================================ 基部四面大拱（拱形桁架）＋拱上橫向格架梁
    for side in range(4):
        R = Matrix.Rotation(side * math.pi / 2, 4, "Z")

        def P(u, z, inset=2.2):
            return R @ Vector((u, -(leg_out(z) - inset), z))

        zs, rise, A = 2.4, 36.0, leg_in(2.4) - 0.5
        n = 34
        pin, pout = [], []
        for i in range(n + 1):
            t = math.pi * i / n
            pin.append(P(A * math.cos(t), zs + rise * math.sin(t)))
            pout.append(P((A + 3.4) * math.cos(t), zs + (rise + 3.4) * math.sin(t)))
        for i in range(n):
            chord(iron_dark, pin[i], pin[i + 1], 1.8)
            chord(iron_dark, pout[i], pout[i + 1], 1.5)
            tube(iron, pin[i], pout[i + 1], 0.7)
            tube(iron, pout[i], pin[i + 1], 0.7)
            tube(iron_lt, pin[i], pout[i], 0.45)
        # 第二道拱（後方，形成拱的厚度）
        pin2 = [P(A * math.cos(math.pi * i / n), zs + rise * math.sin(math.pi * i / n), inset=6.0) for i in range(n + 1)]
        for i in range(n):
            chord(iron_dark, pin2[i], pin2[i + 1], 0.9)
            if i % 2 == 0:
                tube(iron, pin[i], pin2[i], 0.4)
        # 一層下方的格架梁（兩排 X），跨在兩腳之間
        za, zb, zc = 39.5, 45.2, 51.0
        wa, wc = leg_in(za) + 6, leg_in(zc) + 6
        for z0, z1 in ((za, zb), (zb, zc)):
            w0, w1 = lerp(wa, wc, (z0 - za) / (zc - za)), lerp(wa, wc, (z1 - za) / (zc - za))
            m = 12
            for k in range(m):
                u0a, u0b = -w0 + 2 * w0 * k / m, -w0 + 2 * w0 * (k + 1) / m
                u1a, u1b = -w1 + 2 * w1 * k / m, -w1 + 2 * w1 * (k + 1) / m
                tube(iron, P(u0a, z0), P(u1b, z1), 0.55)
                tube(iron, P(u0b, z0), P(u1a, z1), 0.55)
                tube(iron_lt, P(u0a, z0), P(u1a, z1), 0.4)
            chord(iron_dark, P(-w0, z0), P(w0, z0), 1.0)
        # 拱肩：拱背到格架梁底的豎桿
        for i in range(3, n - 2, 2):
            p = pout[i]
            if p.z < za - 1.0 and abs((A + 3.4) * math.cos(math.pi * i / n)) < leg_in(za) + 1.0:
                q = Vector((p.x, p.y, za))
                tube(iron, p, q, 0.45)
        # 二層下方的格架梁（開口頂部）
        z0, z1 = 101.5, 110.0
        w = leg_in(105) + 3
        m = 4
        for k in range(m):
            ua, ub = -w + 2 * w * k / m, -w + 2 * w * (k + 1) / m
            tube(iron, P(ua, z0, 1.5), P(ub, z1, 1.5), 0.5)
            tube(iron, P(ub, z0, 1.5), P(ua, z1, 1.5), 0.5)
        chord(iron_dark, P(-w, z0, 1.5), P(w, z0, 1.5), 0.8)

    # ================================================================ 平台
    def deck_band(half, z0, h, rib_step=3.3):
        """外圍實心橫帶：面板＋豎肋＋上下線腳，下方托架"""
        for side in range(4):
            a = side * math.pi / 2
            R = Matrix.Rotation(a, 4, "Z")
            b.box_base(band, (2 * half, 1.6, h), tuple(R @ Vector((0, -half + 0.8, z0))), rot=(0, 0, a))
            n = int(2 * half / rib_step)
            for k in range(n + 1):
                u = -half + 2 * half * k / n
                b.box_base(iron_dark, (0.45, 0.4, h - 0.6), tuple(R @ Vector((u, -half - 0.15, z0 + 0.3))), rot=(0, 0, a))
                # 托架（斜撐到下方支腳）
                p = R @ Vector((u, -half + 0.6, z0))
                q = R @ Vector((u * 0.92, -half + 4.0, z0 - 3.0))
                tube(iron, p, q, 0.35)
            b.box_base(iron_dark, (2 * half + 1.0, 2.2, 0.6), tuple(R @ Vector((0, -half + 0.8, z0 + h))), rot=(0, 0, a))
            b.box_base(iron_dark, (2 * half + 0.6, 2.0, 0.5), tuple(R @ Vector((0, -half + 0.8, z0 - 0.5))), rot=(0, 0, a))

    def floor_ring(half, hole, z, th):
        w = half - hole
        for side in range(4):
            a = side * math.pi / 2
            R = Matrix.Rotation(a, 4, "Z")
            b.box_base(shade, (2 * half - w, w, th), tuple(R @ Vector((w / 2, -half + w / 2, z - th))), rot=(0, 0, a))

    def railing(half, z, h=1.8, step=2.4):
        for side in range(4):
            a = side * math.pi / 2
            R = Matrix.Rotation(a, 4, "Z")
            p0, p1 = R @ Vector((-half, -half, z + h)), R @ Vector((half, -half, z + h))
            chord(iron_dark, p0, p1, 0.3)
            chord(iron_lt, p0 - Vector((0, 0, h * 0.55)), p1 - Vector((0, 0, h * 0.55)), 0.14)
            n = int(2 * half / step)
            for k in range(n + 1):
                u = -half + 2 * half * k / n
                tube(iron_dark, R @ Vector((u, -half, z)), R @ Vector((u, -half, z + h)), 0.2)

    def pavilion(c, w, d, h, a, z):
        R = Matrix.Rotation(a, 4, "Z")
        b.box_base(glass, (w, d, h), (c.x, c.y, z), rot=(0, 0, a))
        m = int(w / 2.0)
        for k in range(m + 1):
            p = c + R @ Vector((-w / 2 + w * k / m, -d / 2 - 0.1, 0))
            tube(iron_dark, (p.x, p.y, z), (p.x, p.y, z + h), 0.18)
        b.box_base(iron_dark, (w + 0.8, d + 1.6, 0.5), (c.x, c.y, z + h), rot=(0, 0, a))

    # 一層（57.6 m，約 70.7 m 見方）
    Z1 = 57.6
    deck_band(35.35, 51.0, 6.6)
    floor_ring(35.35, 11.0, Z1, 1.2)
    railing(35.35, Z1)
    for side in range(4):
        a = side * math.pi / 2
        R = Matrix.Rotation(a, 4, "Z")
        pavilion(R @ Vector((0, -29.0, 0)), 30, 4.5, 3.8, a, Z1)
        # 外廊上方的雨遮與立柱
        for k in range(13):
            u = -33 + 66 * k / 12
            tube(iron_dark, R @ Vector((u, -33.6, Z1)), R @ Vector((u, -33.6, Z1 + 5.6)), 0.25)
        b.box_base(iron_dark, (66, 3.0, 0.4), tuple(R @ Vector((0, -32.2, Z1 + 5.6))), rot=(0, 0, a))
    # 二層（115.7 m，約 40.5 m 見方）
    Z2 = 115.7
    deck_band(20.25, 110.0, 4.8, rib_step=2.9)
    floor_ring(20.25, 8.0, Z2, 1.0)
    railing(20.25, Z2, h=2.6, step=2.0)
    for side in range(4):
        a = side * math.pi / 2
        R = Matrix.Rotation(a, 4, "Z")
        pavilion(R @ Vector((0, -15.8, 0)), 18, 3.2, 3.2, a, Z2)

    # ================================================================ 塔身（二層以上單一方柱，指數收窄）
    sz = [Z2 + 0.2]
    while sz[-1] < 272:
        sz.append(sz[-1] + max(4.5, 0.85 * shaft(sz[-1])))
    sz[-1] = 276.1

    def sq(h, z):
        return [Vector((-h, -h, z)), Vector((h, -h, z)), Vector((h, h, z)), Vector((-h, h, z))]

    rings = [sq(shaft(z), z) for z in sz]
    g = lambda z: max(0.0, 1.0 - (z - 110) / 230)
    ring_panels(rings, lambda z: (0, 0), lambda z: (0.85 * g(z) + 0.35, 0.4 * g(z) + 0.2, 0.75 * g(z) + 0.3),
                lambda w: 3 if w > 20 else 2, lambda z: 1.9 * g(z) + 0.5)
    for k in range(0, len(rings) - 1, 3):
        A = rings[k]
        tube(iron, A[0], A[2], 0.4)
        tube(iron, A[1], A[3], 0.4)
    # 中段細橫帶（約 196 m）
    zb = 196.0
    hb = shaft(zb) + 0.5
    for side in range(4):
        a = side * math.pi / 2
        R = Matrix.Rotation(a, 4, "Z")
        b.box_base(iron_dark, (2 * hb + 1.0, 0.8, 1.4), tuple(R @ Vector((0, -hb, zb))), rot=(0, 0, a))

    # ================================================================ 三層（276 m）與頂部
    Z3 = 276.1
    b.box_base(band, (18.65, 18.65, 2.4), (0, 0, Z3 - 2.4))
    for side in range(4):
        a = side * math.pi / 2
        R = Matrix.Rotation(a, 4, "Z")
        for k in range(7):
            u = -9.3 + 18.6 * k / 6
            tube(iron, R @ Vector((u, -9.0, Z3 - 2.4)), R @ Vector((u * 0.6, -5.6, Z3 - 6.5)), 0.3)
    # 封閉觀景廊（玻璃＋窗櫺）
    b.box_base(glass, (16.0, 16.0, 5.0), (0, 0, Z3))
    for side in range(4):
        a = side * math.pi / 2
        R = Matrix.Rotation(a, 4, "Z")
        for k in range(9):
            p = R @ Vector((-8.0 + 16.0 * k / 8, -8.1, 0))
            tube(iron_dark, (p.x, p.y, Z3), (p.x, p.y, Z3 + 5.0), 0.28, n=4, smooth=False)
    b.box_base(iron_dark, (17.6, 17.6, 0.8), (0, 0, Z3 + 5.0))
    railing(8.8, Z3 + 5.8, h=2.4, step=1.6)
    # 頂部：艾菲爾公寓＋收分格架
    b.box_base(band, (8.6, 8.6, 3.4), (0, 0, Z3 + 5.8))
    top = [(6.0, Z3 + 9.2), (4.7, 289.0), (3.6, 293.5), (2.9, 297.4)]
    rings = [sq(h, z) for h, z in top]
    for k in range(len(rings) - 1):
        A, B = rings[k], rings[k + 1]
        for ci in range(4):
            cj = (ci + 1) % 4
            chord(iron_dark, A[ci], B[ci], 0.7)
            tube(iron, A[ci], B[cj], 0.35)
            tube(iron, A[cj], B[ci], 0.35)
            chord(iron_dark, A[ci], A[cj], 0.4)
    b.cyl(iron_dark, 3.0, 3.0, 0.8, (0, 0, 297.4), seg=16)
    b.cyl(glass, 2.2, 2.2, 2.6, (0, 0, 298.2), seg=16)
    b.lathe(iron_dark, [(2.6, 0), (2.4, 0.7), (1.6, 1.7), (0.6, 2.3), (0, 2.5)], (0, 0, 300.8), seg=16, smooth=True)
    # 天線（至 330 m）
    b.cyl(antenna, 0.95, 0.8, 8.5, (0, 0, 303.0), seg=10)
    b.cyl(iron_dark, 1.1, 1.1, 0.5, (0, 0, 306.5), seg=10)
    b.cyl(antenna, 0.55, 0.4, 10.0, (0, 0, 311.5), seg=8)
    b.cyl(antenna, 0.3, 0.1, 8.5, (0, 0, 321.5), seg=6)
    _export(b, path)
