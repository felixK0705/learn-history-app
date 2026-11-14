"""chichen_itza 寫實模型：庫庫爾坎金字塔（El Castillo）

實測：底邊 55.3 m、九層台階高 24 m、頂部神廟約 6 m（總高約 30 m）；
四面各 91 階（坡度約 45°，向外突出於塔基）、北面階梯底部兩側有羽蛇頭；
每層為斜坡牆（talud）＋上方凹板（tablero）；灰白石灰岩帶黑色風化斑。
座標：+Y 為北、+X 為東。
"""

import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import TEX, TAU, Builder


# ---------------------------------------------------------------- 自製風化貼圖
def _fbm(n, cells, octaves, seed, stretch=(1, 1)):
    """可無縫拼接的分形雜訊（0..1）"""
    from PIL import Image

    rng = np.random.default_rng(seed)
    acc = np.zeros((n, n), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        ky, kx = max(2, int(cells * 2**o * stretch[1])), max(2, int(cells * 2**o * stretch[0]))
        g = rng.random((ky, kx)).astype(np.float32)
        big = np.tile(g, (3, 3))
        im = Image.fromarray((big * 255).astype(np.uint8)).resize((3 * n, 3 * n), Image.BICUBIC)
        acc += amp * (np.asarray(im, np.float32)[n : 2 * n, n : 2 * n] / 255.0)
        tot += amp
        amp *= 0.5
    acc /= tot
    return (acc - acc.min()) / (acc.max() - acc.min() + 1e-6)


def _weathered(src, out_name, tint, dark, cover=0.25, strength=0.75, streak=0.0, seed=1, contrast=1.0, rep=1, cells=3, nor_size=1024):
    """以貼圖明暗為底、上色後疊加風化斑（地衣）與垂直水痕；rep>1 時把原貼圖拼成 rep×rep，
    讓大尺度斑紋不明顯重複。回傳（漫反射路徑, 法線路徑）"""
    from PIL import Image, ImageOps

    out_dir = os.path.join(TEX, "_tinted")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"ci_{out_name}.jpg")
    out_n = os.path.join(out_dir, f"ci_{src}_nor_x{rep}.jpg")
    im = Image.open(os.path.join(TEX, src, "diff.jpg")).convert("RGB")
    if rep > 1:
        big = Image.new("RGB", (im.width * rep, im.height * rep))
        for i in range(rep):
            for j in range(rep):
                big.paste(im, (i * im.width, j * im.height))
        im = big
        if not os.path.exists(out_n):
            nm = Image.open(os.path.join(TEX, src, "nor.jpg")).convert("RGB")
            bn = Image.new("RGB", (nm.width * rep, nm.height * rep))
            for i in range(rep):
                for j in range(rep):
                    bn.paste(nm, (i * nm.width, j * nm.height))
            bn.resize((nor_size, nor_size), Image.LANCZOS).save(out_n, quality=85)
    else:
        out_n = os.path.join(TEX, src, "nor.jpg")
    n = im.width
    g = np.asarray(ImageOps.grayscale(im), np.float32)
    g = g / g.mean()
    g = 1 + (g - 1) * contrast
    t = np.array([int(tint[i : i + 2], 16) for i in (1, 3, 5)], np.float32)
    d = np.array([int(dark[i : i + 2], 16) for i in (1, 3, 5)], np.float32)
    col = g[..., None] * t
    blot = _fbm(n, cells, 6, seed)
    thr = np.quantile(blot, 1 - cover)
    m = np.clip((blot - thr) / 0.08 + 0.5, 0, 1)
    fine = _fbm(n, 40, 2, seed + 7)
    m = np.clip(m * (0.55 + 0.9 * fine), 0, 1) * strength
    col = col * (1 - m[..., None]) + (g[..., None] * d) * m[..., None]
    # 輕微的整體明暗起伏（避免一片均勻）
    tone = _fbm(n, cells * 2, 3, seed + 21)
    col *= (0.9 + 0.2 * tone)[..., None]
    if streak > 0:
        s = _fbm(n, 2, 3, seed + 3, stretch=(18, 0.7))
        sm = np.clip((s - 0.6) / 0.3, 0, 1) * streak
        col *= 1 - sm[..., None]
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(out, quality=88)
    return out, out_n


def _img_mat(b, name, img_path, tex_id, tile, rough=None, normal=1.0, nor_path=None):
    """與 Builder.tex 相同的 PBR 材質，但漫反射改用自製貼圖"""
    m = bpy.data.materials.new(f"{b.name}_{name}")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(img_path, check_existing=True)
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    nor = nor_path or os.path.join(TEX, tex_id, "nor.jpg")
    if os.path.exists(nor) and normal > 0:
        ni = nt.nodes.new("ShaderNodeTexImage")
        ni.image = bpy.data.images.load(nor, check_existing=True)
        ni.image.colorspace_settings.name = "Non-Color"
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = normal
        nt.links.new(ni.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    arm = os.path.join(TEX, tex_id, "arm.jpg")
    if os.path.exists(arm) and rough is None:
        ai = nt.nodes.new("ShaderNodeTexImage")
        ai.image = bpy.data.images.load(arm, check_existing=True)
        ai.image.colorspace_settings.name = "Non-Color"
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(ai.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = rough if rough is not None else 0.85
    bsdf.inputs["Metallic"].default_value = 0.0
    return b._register(name, m, tile)


# ---------------------------------------------------------------- 熱帶樹
def _jungle_tree(b, x, y, h, leaves, trunk, spread=1.0):
    """不規則樹冠：十多個小雜訊團塊堆成花椰菜狀輪廓，深淺不一的綠"""
    r = b.rng
    b.cyl(trunk, h * 0.03, h * 0.02, h * 0.42, (x, y, -0.2), seg=5)
    cw = h * 0.55 * spread  # 樹冠半徑
    base_leaf = r.randrange(len(leaves))
    n = r.randint(7, 9)
    for k in range(n):
        a = r.uniform(0, TAU)
        d = math.sqrt(r.uniform(0, 1)) * cw * 0.75
        top = 1 - (d / cw) ** 2  # 中央較高，形成圓頂
        zz = h * (0.36 + 0.44 * top * r.uniform(0.7, 1.1))
        s = cw * r.uniform(0.45, 0.68)
        li = base_leaf if r.random() < 0.6 else r.randrange(len(leaves))
        b.rock(leaves[li], (s * r.uniform(0.9, 1.3), s * r.uniform(0.9, 1.3), s * r.uniform(0.6, 0.85)),
               (x + math.cos(a) * d, y + math.sin(a) * d, zz), rot=(0, 0, r.uniform(0, TAU)),
               rough=0.45, subdiv=2, seed=r.randint(0, 9999), flat_bottom=False, round_=0.9)
    # 林下灌叢：遮住樹幹，讓林緣像一道綠牆
    for k in range(1):
        a = r.uniform(0, TAU)
        d = r.uniform(0.2, 0.6) * cw
        s = cw * r.uniform(0.5, 0.7)
        b.rock(leaves[r.randrange(len(leaves))], (s * 1.2, s * 1.2, s * 0.8), (x + math.cos(a) * d, y + math.sin(a) * d, s * 0.3),
               rot=(0, 0, r.uniform(0, TAU)), rough=0.45, subdiv=2, seed=r.randint(0, 9999), flat_bottom=True, round_=0.9)


# ====================================================================== 奇琴伊察・庫庫爾坎金字塔
def chichen_itza(path):
    b = Builder("ChichenItza", seed=5)
    lime_img, lime_nor = _weathered("sandstone_blocks_05", "limestone", "#dcd6cc", "#5a5650", cover=0.36, strength=0.6, streak=0.3, seed=3, contrast=0.9, rep=2, cells=7)
    stone = _img_mat(b, "limestone", lime_img, "sandstone_blocks_05", 5.0, rough=0.85, nor_path=lime_nor)
    stone2 = _img_mat(b, "limestone_b", lime_img, "sandstone_blocks_05", 4.4, rough=0.85, nor_path=lime_nor)
    stair_img, _ = _weathered("sandstone_blocks_05", "stair", "#b3aea4", "#5a5650", cover=0.3, strength=0.45, streak=0.0, seed=5, contrast=0.8, rep=2, cells=8)
    stair_m = _img_mat(b, "stair", stair_img, "sandstone_blocks_05", 3.2, rough=0.8, nor_path=lime_nor)
    dark = b.color("doorway", "#1d1b18", rough=1.0)
    grass = b.tex("grass", "grass_ground", tile=4.0, tint="#7f9246", rough=0.95, normal=0)
    soil = b.color("soil", "#7a6448", rough=0.95)
    sascab = b.tex("sascab", "gravel_floor", tile=2.5, tint="#bfae8e", rough=0.95, normal=0)
    trunk = b.color("trunk", "#5b4a3a", rough=0.9)
    leaves = [b.color("leaf_a", "#35592a", rough=0.85), b.color("leaf_b", "#43692d", rough=0.85),
              b.color("leaf_c", "#2c4c22", rough=0.85), b.color("leaf_d", "#557a34", rough=0.85)]

    # ---------------- 地面：草坪＋塔周白色碎石小徑
    b.ground_disc(grass, 160, soil, depth=4, rings=20, seg=96)
    b.box_base(sascab, (72, 2.2, 0.06), (0, 40.5, -0.03))
    b.box_base(sascab, (72, 2.2, 0.06), (0, -40.5, -0.03))
    b.box_base(sascab, (2.2, 78, 0.06), (40.5, 0, -0.03))
    b.box_base(sascab, (2.2, 78, 0.06), (-40.5, 0, -0.03))
    b.box_base(sascab, (8, 54, 0.05), (0, 68, -0.035))  # 往北通往聖井的白色大道（sacbé）

    sides = [(0, 1), (-1, 0), (0, -1), (1, 0)]  # 北、西、南、東（外法線）

    def frame(n):
        nx, ny = n
        return Vector((nx, ny, 0)), Vector((-ny, nx, 0))  # 法線、切線

    # ---------------- 九層台階：斜坡牆 talud＋凹板 tablero
    B, TOP = 55.3 / 2, 19.52 / 2
    H = 24.0
    LV = 9
    lh = H / LV
    run = 0.6  # 斜坡牆水平退縮
    step = (B - (TOP + run - 0.18)) / (LV - 1)  # 最上層挑簷外緣恰為頂部平台 19.5 m
    stair_hw = 4.45  # 階梯半寬
    bal_w = 1.15
    clear = stair_hw + bal_w + 0.15  # 階梯區不放凹板
    for k in range(LV):
        z0 = k * lh - (0.03 if k else 0.0)
        W = B - k * step
        h1, h2, h3 = lh * 0.42, lh * 0.46, lh * 0.12
        F = W - run
        st = stone if k % 2 == 0 else stone2
        b.frustum(st, (2 * W, 2 * W), (2 * F, 2 * F), h1 + 0.03, (0, 0, z0))
        zt = z0 + h1 + 0.03
        # 凹板底面（內退 0.2）
        b.box_base(st, (2 * (F - 0.2), 2 * (F - 0.2), h2 + 0.04), (0, 0, zt - 0.02))
        # 凹板上下框
        b.box_base(st, (2 * F, 2 * F, 0.2), (0, 0, zt - 0.02))
        b.box_base(st, (2 * F, 2 * F, 0.2), (0, 0, zt + h2 - 0.18))
        # 頂部挑簷
        b.box_base(st, (2 * (F + 0.18), 2 * (F + 0.18), h3), (0, 0, zt + h2))
        # 立柱分隔成矩形凹板
        for n in sides:
            nv, tv = frame(n)
            a = math.atan2(n[1], n[0])
            span = F - clear
            cnt = max(1, round(span / 4.8))
            for side_sign in (-1, 1):
                for i in range(cnt + 1):
                    u = clear + span * i / cnt
                    w_p = 0.7 if i in (0, cnt) else 0.4
                    if i == cnt:
                        u -= 0.2
                    c = nv * (F - 0.25) + tv * (u * side_sign)
                    b.box_base(st, (0.5, w_p, h2 - 0.2), (c.x, c.y, zt + 0.1), rot=(0, 0, a))

    # ---------------- 四面階梯（91 階）、扶手（alfarda）、北面羽蛇頭
    nsteps = 91
    ub = B + 5.2  # 階梯底緣距中心
    ut = TOP + 0.1
    tr = (ub - ut) / nsteps
    rs = H / nsteps
    for n in sides:
        nv, tv = frame(n)
        a = math.atan2(n[1], n[0])
        R = Matrix.Rotation(a, 4, "Z")

        def P(u, v, z):
            return R @ Vector((u, v, z))

        # 踏步：每階一個方塊，向後、向下延伸以互相交疊（無共面）
        for i in range(nsteps):
            u0 = ub - i * tr
            z0 = i * rs
            c = P(u0 - (tr + 0.3) / 2, 0, 0)
            b.box(stair_m, (tr + 0.3, 2 * stair_hw, rs + 0.3), (c.x, c.y, z0 + rs - (rs + 0.3) / 2), rot=(0, 0, a))
        # 階梯下方填實
        tri = [(ub - 0.05, 0.0), (ut - 0.05, H - 0.05), (ut - 0.05, 0.0)]
        _side_prism(b, stair_m, tri, a, -(stair_hw - 0.05), stair_hw - 0.05)
        # 扶手
        top_off = 0.85
        prof = [(ub + 0.55, 0.0), (ub + 0.55, 1.15), (ut - 0.2, H + top_off), (ut - 1.4, H + top_off), (TOP + 4.0, 0.0)]
        for sgn in (-1, 1):
            vc = sgn * (stair_hw + bal_w / 2 - 0.1)
            _side_prism(b, stone, prof, a, vc - bal_w / 2, vc + bal_w / 2)
            if n == (0, 1):  # 北面：羽蛇頭
                hc = P(ub + 1.6, vc, 0)
                b.rock(stone2, (2.7, 1.55, 1.4), (hc.x, hc.y, 0.98), rot=(0, 0, a), rough=0.2, subdiv=3, seed=7 + sgn, round_=0.75)
                jc = P(ub + 1.9, vc, 0)
                b.rock(stone2, (2.3, 1.4, 0.6), (jc.x, jc.y, 0.29), rot=(0, 0, a), rough=0.12, subdiv=2, seed=17 + sgn, round_=0.6)
                mc = P(ub + 2.75, vc, 0)
                b.box_base(dark, (0.35, 1.0, 0.18), (mc.x, mc.y, 0.56), rot=(0, 0, a))
        # 北面階梯西側塔基的內部金字塔入口（照片中可見的暗門）
        if n == (0, 1):
            dc = P(B - 0.2, -(stair_hw + bal_w + 1.4), 0)
            b.box_base(dark, (0.6, 1.3, 1.9), (dc.x, dc.y, 0.0), rot=(0, 0, a))

    # ---------------- 頂部平台與神廟（約 15 m 見方、高 6 m）
    zt = H
    b.box_base(stone, (2 * TOP, 2 * TOP, 0.25), (0, 0, zt - 0.2))
    tw = 7.4  # 神廟半寬
    z = zt + 0.05
    b.box_base(stone2, (2 * tw + 0.3, 2 * tw + 0.3, 0.35), (0, 0, z))  # 基座線腳
    z += 0.35
    wall_h = 2.75
    # 內部（暗）
    b.box_base(dark, (2 * tw - 1.6, 2 * tw - 1.6, wall_h + 0.1), (0, 0, z - 0.05))
    for n in sides:
        nv, tv = frame(n)
        a = math.atan2(n[1], n[0])
        if n == (0, 1):
            doors = [(-2.45, 1.5), (0.0, 1.5), (2.45, 1.5)]  # 北面三門（中以羽蛇柱分隔）
        else:
            doors = [(0.0, 2.0)]
        dh = 2.25
        edges = [-tw]
        for c0, w0 in doors:
            edges += [c0 - w0 / 2, c0 + w0 / 2]
        edges.append(tw)
        for i in range(0, len(edges), 2):
            u0, u1 = edges[i], edges[i + 1]
            if u1 - u0 < 0.05:
                continue
            c = nv * (tw - 0.45) + tv * ((u0 + u1) / 2)
            b.box_base(stone, (0.9, u1 - u0 + (0.9 if i in (0, len(edges) - 2) else 0.0), wall_h), (c.x, c.y, z), rot=(0, 0, a))
        for c0, w0 in doors:
            c = nv * (tw - 0.45) + tv * c0
            b.box_base(stone, (0.9, w0 + 0.1, wall_h - dh), (c.x, c.y, z + dh), rot=(0, 0, a))
            if n == (0, 1) and c0 != 0:
                pass
        if n == (0, 1):  # 羽蛇柱（兩根）
            for c0 in (-1.225, 1.225):
                c = nv * (tw - 0.3) + tv * c0
                b.box_base(stone2, (0.7, 0.85, dh), (c.x, c.y, z), rot=(0, 0, a))
    z += wall_h
    b.box_base(stone2, (2 * tw + 0.35, 2 * tw + 0.35, 0.22), (0, 0, z))  # 腰線（三段式）
    b.box_base(stone, (2 * tw + 0.15, 2 * tw + 0.15, 0.2), (0, 0, z + 0.22))
    b.box_base(stone2, (2 * tw + 0.35, 2 * tw + 0.35, 0.18), (0, 0, z + 0.42))
    z += 0.6
    fh = 1.75
    b.box_base(stone, (2 * tw - 0.2, 2 * tw - 0.2, fh), (0, 0, z))  # 上部飾帶（凹板）
    for n in sides:
        nv, tv = frame(n)
        a = math.atan2(n[1], n[0])
        for i in range(7):
            u = -tw + 0.3 + (2 * tw - 0.6) * i / 6
            c = nv * (tw - 0.2) + tv * u
            b.box_base(stone2, (0.5, 0.55, fh), (c.x, c.y, z), rot=(0, 0, a))
        # 飾帶中的幾何紋（凸塊）
        for i in range(6):
            u = -tw + 0.3 + (2 * tw - 0.6) * (i + 0.5) / 6
            c = nv * (tw - 0.2) + tv * u
            b.box_base(stone, (0.42, 1.0, 0.55), (c.x, c.y, z + 0.6), rot=(0, 0, a))
    z += fh
    b.box_base(stone2, (2 * tw + 0.4, 2 * tw + 0.4, 0.5), (0, 0, z))  # 頂部挑簷
    z += 0.5
    b.box_base(stone, (2 * tw - 0.2, 2 * tw - 0.2, 0.15), (0, 0, z))
    # 屋頂殘存的小冠飾
    for i in range(-3, 4):
        for n in sides:
            nv, tv = frame(n)
            c = nv * (tw - 0.5) + tv * (i * 2.0)
            b.box_base(stone2, (0.5, 0.5, 0.45), (c.x, c.y, z + 0.1))

    # ---------------- 周圍熱帶林：北、西側是大廣場（開闊草坪），東、南側林帶較近
    def avoid(x, y):
        r = math.hypot(x, y)
        ang = math.degrees(math.atan2(y, x)) % 360  # 0 = 東、90 = 北
        if 95 < ang < 205:  # 西北：大廣場
            return r < 135
        return r < 70

    for x, y in b.scatter(165, 62, 156, avoid=avoid, min_dist=5.5):
        _jungle_tree(b, x, y, b.rng.uniform(11, 18), leaves, trunk, spread=1.15)
    b.export(path)


def _side_prism(b, mi, prof, a, v0, v1):
    """立面輪廓 prof[(u, z)]（逆時針、凸多邊形）沿切線方向 v0→v1 擠出，再繞 Z 旋轉 a"""
    R = Matrix.Rotation(a, 4, "Z")
    # 以 (u, z) 為 XZ 平面，沿 Y（切線）擠出
    bot = [b.bm.verts.new(R @ Vector((u, v0, z))) for u, z in prof]
    top = [b.bm.verts.new(R @ Vector((u, v1, z))) for u, z in prof]
    b.bm.faces.new(bot)
    b.bm.faces.new(list(reversed(top)))
    n = len(prof)
    for i in range(n):
        j = (i + 1) % n
        b.bm.faces.new([bot[j], bot[i], top[i], top[j]])
    b._assign(bot + top, mi)
