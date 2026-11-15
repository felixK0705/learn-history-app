"""hagia_sophia 伊斯坦堡聖索菲亞大教堂（Ayasofya）寫實模型（公尺）

- 中央方形 31 m，四大墩柱撐起直徑約 31–32 m 的淺圓頂，頂高 55.6 m；鼓座一圈 40 扇窗與扶壁肋
- 東西兩側半圓頂（再下為小半圓頂與東端半圓後殿），南北為大拱券內的窗牆（tympanum）
- 本體（含側廊、樓廊）約 77 × 71 m，西側內外兩道前廊；外牆為淡鮭紅灰泥，屋頂與圓頂覆鉛
- 鄂圖曼時期加的四座宣禮塔：東南為紅磚塔（穆罕默德二世），東北細白塔（巴耶濟德二世），
  西南、西北兩座較粗（錫南／穆拉德三世），高約 55–60 m
- 南、北側有巨大斜面扶壁

座標：+X 東、+Y 北，中央圓頂中心在原點。參考照由西南南方、略高處拍攝。
"""

import math

import bmesh
from mathutils import Matrix, Vector, noise

from lib import TAU, Builder

# 目標點、方位角（0 = 從南往北看）、仰角、距離、焦距
CAMERA = ((6, 0, 28), 12, 5, 195, 40)


# ====================================================================== 共用工具（藍色清真寺也會引用）
def mk_face(b, vs, mi, smooth=False):
    f = b.bm.faces.new(vs)
    f.material_index = mi
    f.smooth = smooth
    return f


def capture(b, fn):
    b.bm.verts.ensure_lookup_table()
    start = len(b.bm.verts)
    fn()
    b.bm.verts.ensure_lookup_table()
    return list(b.bm.verts[start:])


def dome(b, mi, R, rise, base, seg=64, ribs=0, rib_amp=0.006, z_skirt=0.0, n=10, power=1.0, top_r=0.0):
    """圓頂（rise 可小於 R 做成扁圓頂）；ribs>0 時加上鉛板接縫稜線"""
    x, y, z = base
    prof = []
    if z_skirt > 0:
        prof.append((R, -z_skirt))
    for i in range(n + 1):
        t = i / n
        a = t * math.pi / 2
        r = R * math.cos(a) ** power
        if top_r and r < top_r:
            r = top_r
        prof.append((r, rise * math.sin(a)))
    if top_r:
        prof.append((0.0, rise))
    else:
        prof[-1] = (0.0, rise)
    radial = (lambda t: 1 + rib_amp * max(0.0, math.cos(t * ribs)) ** 8) if ribs else None
    return b.lathe(mi, prof, (x, y, z), seg=seg, smooth=True, radial=radial)


def half_dome(b, mi, R, rise, center, facing, seg=24, n=8, ribs=0, flat_mi=None):
    """半圓頂（四分之一球殼外形）：facing 為開口所朝方向的角度（弧向 facing+π 方向凸出）"""
    cx, cy, cz = center
    rings = []
    for i in range(n + 1):
        a = (math.pi / 2) * i / n
        r = R * math.cos(a)
        zz = cz + rise * math.sin(a)
        ring = []
        for j in range(seg + 1):
            t = facing + math.pi / 2 + math.pi * j / seg
            rr = r * (1 + (0.006 * max(0.0, math.cos((t - facing) * ribs)) ** 8 if ribs else 0))
            ring.append(b.bm.verts.new((cx + rr * math.cos(t), cy + rr * math.sin(t), zz)))
        rings.append(ring)
    for a_, c_ in zip(rings, rings[1:]):
        for j in range(seg):
            if a_[j] is c_[j]:
                continue
            mk_face(b, [a_[j], a_[j + 1], c_[j + 1], c_[j]], mi, True)
    # 開口面（平的牆）
    pts = [rings[i][0] for i in range(n + 1)] + [rings[i][-1] for i in range(n, -1, -1)]
    uniq = []
    for p in pts:
        if all((p.co - q.co).length > 1e-4 for q in uniq):
            uniq.append(p)
    try:
        mk_face(b, uniq, mi if flat_mi is None else flat_mi)
    except ValueError:
        pass
    # 底面
    mk_face(b, list(reversed(rings[0])), mi if flat_mi is None else flat_mi)


def arched_window(b, mi, w, h, M, depth=0.08, seg=8):
    """半圓頭窗（深色面板），M 為牆面座標：局部 X 水平、Z 垂直、-Y 朝外"""
    r = w / 2
    pts = [(-r, 0), (r, 0)] + [(r * math.cos(math.pi * i / seg), h - r + r * math.sin(math.pi * i / seg)) for i in range(1, seg)]
    pts = [(-r, 0), (r, 0), (r, h - r)] + [(r * math.cos(math.pi * i / seg), h - r + r * math.sin(math.pi * i / seg)) for i in range(1, seg)] + [(-r, h - r)]
    b.profile_wall(mi, pts, depth, M)


def window_row(b, mi, n, x0, x1, z, w, h, y, face_dir=-1, axis="x", depth=0.1):
    """沿牆面排一列窗；axis='x' 時牆面平行 X 軸、位於 y；face_dir=-1 朝 -Y"""
    for k in range(n):
        u = x0 + (x1 - x0) * (k + 0.5) / n
        if axis == "x":
            M = Matrix.Translation((u, y, z)) @ Matrix.Rotation(0 if face_dir < 0 else math.pi, 4, "Z")
        else:
            M = Matrix.Translation((y, u, z)) @ Matrix.Rotation(math.pi / 2 if face_dir > 0 else -math.pi / 2, 4, "Z")
        arched_window(b, mi, w, h, M, depth)


def minaret(b, x, y, H, R, stone, cap, gold, balcony=None, shaft=None, balconies=(0.62,), base_h=None, flutes=16, seg=16,
            cap_h=None, base_sq=True, bands=None, band_mi=None):
    """鄂圖曼鉛筆形宣禮塔：方形底座→多角塔身→陽台（şerefe）→細上段→鉛錐頂＋金色頂飾"""
    balcony = balcony if balcony is not None else stone
    shaft = shaft if shaft is not None else stone
    base_h = base_h if base_h is not None else H * 0.14
    cap_h = cap_h if cap_h is not None else H * 0.16
    if base_sq:
        b.box_base(stone, (R * 2.5, R * 2.5, base_h), (x, y, 0))
        # 由方轉圓的過渡段
        b.lathe(stone, [(R * 1.35, 0), (R * 1.18, base_h * 0.25), (R * 1.05, base_h * 0.32)], (x, y, base_h), seg=seg, smooth=False)
        z0 = base_h + base_h * 0.32
    else:
        z0 = 0.0
    z_top = H - cap_h
    flu = (lambda t: 1 + 0.035 * abs(math.cos(t * flutes / 2))) if flutes else None
    zs = [z0] + [z0 + (z_top - z0) * f for f in balconies] + [z_top]
    radius = R
    for i, (za, zb) in enumerate(zip(zs, zs[1:])):
        mi = shaft if i == 0 else stone
        r_here = radius * (1 - 0.06 * i)
        if bands and i == 0 and band_mi is not None:
            # 紅磚塔身＋白色石帶
            n = bands
            for k in range(n):
                z_a = za + (zb - za) * k / n
                z_b = za + (zb - za) * (k + 1) / n
                b.lathe(shaft, [(r_here, z_a), (r_here, z_b - 0.5)], (x, y, 0), seg=seg, smooth=False, radial=flu)
                b.lathe(band_mi, [(r_here * 1.02, z_b - 0.5), (r_here * 1.02, z_b)], (x, y, 0), seg=seg, smooth=False)
        else:
            b.lathe(mi, [(r_here, za), (r_here * 0.985, zb)], (x, y, 0), seg=seg, smooth=False, radial=flu)
        if i < len(zs) - 2:
            # 陽台：鐘乳石托座（外擴的錐台）＋欄杆
            zb_ = zb
            b.lathe(balcony, [(r_here * 0.98, zb_ - 2.4), (r_here * 1.25, zb_ - 1.4), (r_here * 1.55, zb_ - 0.3), (r_here * 1.62, zb_),
                              (r_here * 1.62, zb_ + 1.05), (r_here * 1.52, zb_ + 1.05), (r_here * 1.52, zb_ + 0.2), (0, zb_ + 0.2)],
                    (x, y, 0), seg=seg * 2, smooth=False)
    # 頂部：細環＋鉛錐頂
    r_top = radius * (1 - 0.06 * (len(zs) - 2)) * 0.985
    b.lathe(stone, [(r_top * 1.08, z_top - 0.1), (r_top * 1.12, z_top + 0.4), (r_top * 1.02, z_top + 0.5)], (x, y, 0), seg=seg, smooth=False)
    b.lathe(cap, [(r_top * 1.04, z_top + 0.5), (r_top * 0.75, z_top + 0.5 + cap_h * 0.35), (r_top * 0.38, z_top + 0.5 + cap_h * 0.75),
                  (0.0, z_top + 0.5 + cap_h * 0.98)], (x, y, 0), seg=seg, smooth=False)
    zf = z_top + 0.5 + cap_h * 0.92
    b.lathe(gold, [(0.12, zf), (0.32, zf + 0.5), (0.1, zf + 0.9), (0.28, zf + 1.4), (0.08, zf + 1.9), (0.22, zf + 2.3), (0.0, zf + 3.0)],
            (x, y, 0), seg=8, smooth=True)


def leaf_blob(b, mi, loc, rx, ry, rz, lump=0.3, subdiv=2):
    """不規則葉團：細分球體＋多層雜訊（菜花狀起伏）"""
    off = Vector((b.rng.uniform(0, 99), b.rng.uniform(0, 99), b.rng.uniform(0, 99)))
    r = bmesh.ops.create_icosphere(b.bm, subdivisions=subdiv, radius=1.0, matrix=Matrix.Identity(4))
    for v in r["verts"]:
        p = v.co.copy()
        n_ = noise.noise(p * 1.4 + off) * 0.55 + noise.noise(p * 3.2 + off) * 0.3 + noise.noise(p * 7.0 + off) * 0.15
        k = 1 + lump * n_
        if p.z < -0.3:
            k *= 0.85 + 0.15 * (1 + p.z)  # 底部略收平
        v.co = Vector((loc[0] + p.x * rx * k, loc[1] + p.y * ry * k, loc[2] + p.z * rz * k))
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mi
        f.smooth = True


def broadleaf(b, x, y, h, leaves, trunk, z=0.0, spread=1.0):
    """闊葉樹：主幹＋數個大葉團（上亮下暗、外輪廓起伏）"""
    rng = b.rng
    R = h * rng.uniform(0.36, 0.44) * spread
    cz = z + h - R * 0.85
    b.cyl(trunk, h * 0.035, h * 0.022, (cz - z) * 0.9, (x, y, z), seg=6)
    n = rng.randint(4, 6)
    for i in range(n):
        a = rng.uniform(0, TAU)
        rr = R * (0.0 if i == 0 else rng.uniform(0.4, 0.62))
        dz = (0.1 * R if i == 0 else rng.uniform(-0.45, 0.2) * R)
        br = R * (0.72 if i == 0 else rng.uniform(0.48, 0.62))
        mi = leaves[1] if i == 0 else leaves[rng.choice((0, 1, 2, 2))]
        leaf_blob(b, mi, (x + rr * math.cos(a), y + rr * math.sin(a), cz + dz), br * rng.uniform(0.95, 1.15), br * rng.uniform(0.95, 1.15),
                  br * 0.85, lump=0.42)


def conifer(b, x, y, h, mats, trunk, z=0.0):
    """雲杉／冷杉：多層下垂的錐形枝層"""
    r0 = h * b.rng.uniform(0.17, 0.22)
    b.cyl(trunk, h * 0.025, h * 0.015, h * 0.2, (x, y, z), seg=5)
    layers = 5
    for k in range(layers):
        t = k / layers
        rr = r0 * (1 - t * 0.82)
        zz = z + h * (0.12 + 0.78 * t)
        mi = mats[min(len(mats) - 1, k * len(mats) // layers)]
        b.lathe(mi, [(rr, zz), (rr * 0.85, zz + h * 0.06), (0.0, zz + h * 0.26)], (x, y, 0), seg=8, smooth=True,
                radial=(lambda tt, s=b.rng.uniform(0, 9): 1 + 0.14 * math.sin(tt * 4 + s)))


# ====================================================================== 聖索菲亞
def hagia_sophia(path):
    b = Builder("HagiaSophia", seed=31)
    bm = b.bm
    plaster = b.tex("plaster", "plastered_wall_04", tile=6.0, tint="#dcab94", gain=1.0, rough=0.9, normal=0.5)
    plaster_d = b.color("plaster_shade", "#cf9c86", rough=0.9)
    recess = b.color("recess", "#bf6f52", rough=0.9)
    stone = b.tex("stone", "white_sandstone_blocks_02", tile=4.0, tint="#d8d3c8", rough=0.85, normal=0.6)
    buttress = b.tex("buttress", "plastered_wall_04", tile=8.0, tint="#cbbfb0", rough=0.9, normal=0.6)
    brick = b.tex("brick", "brick_wall_006", tile=3.0, tint="#b0684e", rough=0.9, normal=0.6)
    lead = b.color("lead", "#a4abaf", rough=0.45, metal=0.35)
    lead_d = b.color("lead_dark", "#5d6469", rough=0.5, metal=0.3)
    win = b.color("window", "#2c2a2a", rough=0.3)
    gold = b.color("gold", "#c9a14a", rough=0.3, metal=0.9)
    trim = b.color("trim", "#e6ddd0", rough=0.7)
    pave = b.tex("pave", "gravel_floor", tile=4.0, tint="#9d978c", rough=0.95, normal=0)
    grass = b.tex("grass", "grass_ground", tile=8.0, tint="#5f7c3c", gain=0.92, rough=0.95, normal=0)
    soil = b.color("soil", "#6b5a45", rough=0.95)
    leaves = [b.color("leaf_l", "#6b8f3e", rough=0.85), b.color("leaf_m", "#4c6e2c", rough=0.88), b.color("leaf_d", "#34521f", rough=0.9)]
    trunk = b.color("trunk", "#5a4a3a", rough=0.9)

    T = lambda x, y, z=0.0: Matrix.Translation((x, y, z))  # noqa: E731
    Rz = lambda a: Matrix.Rotation(a, 4, "Z")  # noqa: E731

    # ---------------------------------------------------------------- 地面
    b.ground_disc(grass, 175, soil, depth=4, rings=20, seg=96)
    b.box_base(pave, (118, 100, 0.1), (-6, 0, 0))
    b.box_base(pave, (18, 180, 0.1), (-70, 0, 0))

    # ---------------------------------------------------------------- 主體量：側廊＋樓廊（約 76 × 71 m）
    XW, XE, YS = -36.0, 40.0, 35.5
    H_AISLE = 23.0
    b.box_base(plaster, (XE - XW, 2 * YS, H_AISLE), ((XW + XE) / 2, 0, 0))
    b.box_base(lead, (XE - XW + 0.8, 2 * YS + 0.8, 0.45), ((XW + XE) / 2, 0, H_AISLE))
    # 側廊屋頂（鉛覆、緩坡）
    for s in (-1, 1):
        y0 = s * YS
        y1 = s * 22.0
        b.profile_wall(lead, [(y0, 0), (y1, 0), (y1, 3.0)] if s < 0 else [(y1, 0), (y0, 0), (y1, 3.0)], XE - XW,
                       Matrix.Translation(((XW + XE) / 2, 0, H_AISLE + 0.45)) @ Matrix.Rotation(-math.pi / 2, 4, "Z"))
    # 側廊外牆兩層窗
    for s in (-1, 1):
        for z, n, w, h in ((3.5, 14, 2.0, 5.0), (12.5, 14, 2.2, 6.0)):
            window_row(b, win, n, XW + 3, XE - 3, z, w, h, s * (YS + 0.05), face_dir=s, depth=0.12)

    # 前廊（西側內外兩道），低於主體
    b.box_base(plaster, (6.0, 2 * YS - 6, 15.0), (XW - 3.0, 0, 0))
    b.box_base(plaster_d, (6.0, 2 * YS - 14, 11.0), (XW - 9.0, 0, 0))
    b.box_base(lead, (6.4, 2 * YS - 5.6, 0.6), (XW - 3.0, 0, 15.0))
    b.box_base(lead, (6.4, 2 * YS - 13.6, 0.6), (XW - 9.0, 0, 11.0))
    window_row(b, win, 9, -YS + 6, YS - 6, 4.0, 1.8, 4.5, XW - 12.05, face_dir=-1, axis="y")
    window_row(b, win, 9, -YS + 6, YS - 6, 9.0, 1.8, 4.0, XW - 6.05, face_dir=-1, axis="y")

    # ---------------------------------------------------------------- 中央方塔：四角墩柱上段＋南北拱窗牆
    S = 15.5             # 中央方形半邊
    Z_ARCH_TOP = 38.6
    Z_PLAT = 40.0
    PW = 8.0             # 墩柱外露寬
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (S + PW / 2 - 1.0), sy * (S + 4.5)
            b.box_base(plaster, (PW, 11.0, Z_PLAT + 3.0), (cx, cy, 0))
            b.box_base(trim, (PW + 0.5, 11.5, 0.5), (cx, cy, Z_PLAT + 3.0))
            # 圓形徽飾
            M = T(cx, cy - sy * 5.55, Z_PLAT - 1.5) @ Rz(0 if sy < 0 else math.pi) @ Matrix.Rotation(math.pi / 2, 4, "X")
            vs = capture(b, lambda: b.cyl(trim, 1.8, 1.8, 0.15, (0, 0, 0), seg=20))
            bmesh.ops.transform(bm, matrix=M, verts=vs)
    # 南北拱窗牆：外拱框＋凹入的窗牆
    for sy in (-1, 1):
        R = Rz(0 if sy < 0 else math.pi)
        yf = S + 9.0  # 拱框外緣
        M = R @ T(0, -yf + 1.2, H_AISLE + 2.5)
        width = 2 * (S - 1.0) + 0.02
        b.arch_frame(plaster, width, Z_PLAT - H_AISLE - 2.5, Z_ARCH_TOP - 13.5 - H_AISLE - 2.5, 27.0, 2.4, M, kind="round")
        # 凹入窗牆（深色系）
        b.profile_wall(recess, [(-14.6, 0), (14.6, 0), (14.6, Z_PLAT - H_AISLE)] + [(-14.6, Z_PLAT - H_AISLE)], 1.0,
                       R @ T(0, -(S + 2.0), H_AISLE))
        # 窗：下層 7 扇、上層 5 扇、拱內半圓 3 扇
        for n, z, w, h, x0, x1 in ((7, 27.5, 1.6, 4.2, -12, 12), (5, 33.0, 1.8, 4.4, -9, 9), (3, 38.0, 1.6, 2.4, -5, 5)):
            for k in range(n):
                u = x0 + (x1 - x0) * (k + 0.5) / n
                arched_window(b, win, w, h, R @ T(u, -(S + 2.55), z), depth=0.12)
    # 圓頂下的方形平台
    b.box_base(plaster_d, (2 * S + 6, 2 * S + 6, Z_PLAT - 30), (0, 0, 30))
    b.box_base(lead, (2 * S + 7, 2 * S + 7, 0.6), (0, 0, Z_PLAT))

    # ---------------------------------------------------------------- 鼓座（40 窗＋扶壁肋）與主圓頂
    Z_DRUM = Z_PLAT + 0.6
    R_DOME = 16.2
    H_DRUM = 5.4
    b.lathe(lead_d, [(R_DOME - 0.3, Z_DRUM), (R_DOME - 0.3, Z_DRUM + H_DRUM)], (0, 0, 0), seg=80, smooth=False)
    for k in range(40):
        a = TAU * (k + 0.5) / 40
        c, s_ = math.cos(a), math.sin(a)
        # 扶壁肋（外伸 1.3 m，上窄）
        b.frustum(lead_d, (1.3, 1.1), (0.7, 0.9), H_DRUM + 0.4, (c * (R_DOME + 0.35), s_ * (R_DOME + 0.35), Z_DRUM), rot_z=a)
        a2 = TAU * k / 40
        M = T(math.cos(a2) * (R_DOME - 0.25), math.sin(a2) * (R_DOME - 0.25), Z_DRUM + 0.7) @ Rz(a2 + math.pi / 2)
        arched_window(b, win, 1.3, 3.8, M, depth=0.1)
    b.lathe(trim, [(R_DOME + 0.3, Z_DRUM + H_DRUM), (R_DOME + 0.45, Z_DRUM + H_DRUM + 0.35), (R_DOME - 0.2, Z_DRUM + H_DRUM + 0.35)],
            (0, 0, 0), seg=80, smooth=False)
    Z_DOME = Z_DRUM + H_DRUM + 0.35
    dome(b, lead, R_DOME + 0.2, 55.6 - Z_DOME, (0, 0, Z_DOME), seg=96, ribs=40, rib_amp=0.004, n=12, power=1.0)
    # 頂飾（金色新月）
    zt = 55.6
    b.lathe(gold, [(0.0, zt - 0.2), (0.6, zt), (0.25, zt + 0.8), (0.55, zt + 1.4), (0.15, zt + 2.0), (0.4, zt + 2.6), (0.0, zt + 3.4)],
            (0, 0, 0), seg=10)
    b.ering(gold, (0.9, 0.12), (1.1, 0.14), zt + 3.4, zt + 3.6, seg=16)  # 粗略的新月環
    bm.verts.ensure_lookup_table()

    # ---------------------------------------------------------------- 東西半圓頂、小半圓頂、後殿
    Z_HD = 33.0
    for sx in (-1, 1):
        # 支撐半圓頂的半圓牆
        b.ering(plaster_d, (S - 0.5, S - 0.5), (S + 0.6, S + 0.6), H_AISLE, Z_HD, seg=48,
                t0=(-math.pi / 2 if sx > 0 else math.pi / 2), t1=(math.pi / 2 if sx > 0 else 3 * math.pi / 2), center=(sx * S, 0))
        half_dome(b, lead, S + 0.7, 9.0, (sx * S, 0, Z_HD), facing=(math.pi if sx > 0 else 0.0), seg=28, n=8, ribs=12, flat_mi=plaster_d)
        # 半圓頂底部的小窗
        for k in range(5):
            a = (-math.pi / 2 + math.pi * (k + 0.5) / 5) if sx > 0 else (math.pi / 2 + math.pi * (k + 0.5) / 5)
            M = T(sx * S + math.cos(a) * (S + 0.62), math.sin(a) * (S + 0.62), Z_HD - 3.6) @ Rz(a + math.pi / 2)
            arched_window(b, win, 1.3, 2.8, M, depth=0.1)
        # 兩側的小半圓頂（exedrae）
        for sy in (-1, 1):
            cx, cy = sx * (S + 6.0), sy * 9.5
            b.lathe(plaster_d, [(6.5, H_AISLE), (6.5, H_AISLE + 3.2)], (cx, cy, 0), seg=24, smooth=False)
            dome(b, lead, 6.7, 3.6, (cx, cy, H_AISLE + 3.2), seg=24, ribs=10, n=6)
    # 東端後殿（半圓）
    b.ering(plaster, (0.01, 0.01), (9.0, 9.0), 0, H_AISLE - 2, seg=32, t0=-math.pi / 2, t1=math.pi / 2, center=(XE, 0))
    half_dome(b, lead, 9.0, 5.0, (XE, 0, H_AISLE - 2), facing=math.pi, seg=16, n=6, flat_mi=plaster)
    for k in range(3):
        a = -math.pi / 3 + math.pi / 3 * k
        M = T(XE + math.cos(a) * 9.05, math.sin(a) * 9.05, 10.0) @ Rz(a + math.pi / 2)
        arched_window(b, win, 1.8, 5.0, M, depth=0.1)

    # ---------------------------------------------------------------- 南北巨型斜扶壁（鄂圖曼加固）
    for sy in (-1, 1):
        for x, L, top, th in ((-20.5, 11.0, 30.0, 7.0), (20.5, 12.0, 31.0, 7.0), (-33.0, 6.0, 17.0, 4.5), (35.0, 7.0, 19.0, 4.5)):
            y0 = sy * YS
            pts = [(0, 0), (L, 0), (L, 3.0), (L * 0.55, top * 0.55), (1.5, top), (0, top)]
            M = T(x, y0, 0) @ Rz(-math.pi / 2 if sy < 0 else math.pi / 2) @ Matrix.Rotation(math.pi / 2, 4, "X")
            b.prism(buttress, pts, -th / 2, th, M)
    # 西南角的低矮附屬建物
    b.box_base(plaster_d, (10, 9, 9), (XW - 4, -YS - 4, 0))
    b.box_base(lead, (10.6, 9.6, 0.5), (XW - 4, -YS - 4, 9))

    # ---------------------------------------------------------------- 四座宣禮塔
    minaret(b, 46.0, -39.0, 52.0, 2.0, trim, lead, gold, shaft=brick, balconies=(0.66,), base_h=12.0, flutes=0, seg=14,
            bands=1, band_mi=trim)   # 東南：紅磚
    minaret(b, 47.0, 38.0, 55.0, 1.6, stone, lead, gold, balconies=(0.66,), base_h=8.0, seg=14)   # 東北：細白
    for y in (-41.0, 41.0):      # 西南、西北：錫南設計，兩層陽台
        minaret(b, -46.0, y, 60.0, 2.2, stone, lead, gold, balconies=(0.50, 0.72), base_h=9.0, seg=16)

    # ---------------------------------------------------------------- 周邊鄂圖曼陵墓（南側，鉛圓頂八角建築）
    for x, y, r in ((-25.0, -62.0, 7.0), (-5.0, -64.0, 6.5), (15.0, -58.0, 5.5)):
        b.lathe(stone, [(r, 0), (r, 9.0)], (x, y, 0), seg=8, smooth=False)
        b.lathe(trim, [(r + 0.3, 9.0), (r + 0.3, 9.6), (r - 0.2, 9.6)], (x, y, 0), seg=8, smooth=False)
        dome(b, lead, r - 0.1, r * 0.7, (x, y, 9.6), seg=32, ribs=16, n=8)
        b.lathe(gold, [(0.15, 9.6 + r * 0.7 - 0.1), (0.25, 9.6 + r * 0.7 + 0.6), (0.0, 9.6 + r * 0.7 + 1.4)], (x, y, 0), seg=6)
        for k in range(8):
            a = TAU * (k + 0.5) / 8
            M = T(x + math.cos(a) * r * 0.93, y + math.sin(a) * r * 0.93, 2.0) @ Rz(a + math.pi / 2)
            arched_window(b, win, 1.2, 3.0, M, depth=0.1)

    # ---------------------------------------------------------------- 樹木
    rng = b.rng
    for x, y in b.scatter(60, 50, 170, min_dist=11,
                          avoid=lambda x, y: (-66 < x < 58 and -50 < y < 50) or (-35 < x < 25 and -72 < y < -52) or abs(x + 70) < 10):
        broadleaf(b, x, y, rng.uniform(13, 20), leaves, trunk)

    b.export(path)
