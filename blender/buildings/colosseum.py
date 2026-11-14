"""colosseum 寫實模型（尺寸依實測資料，公尺）

現況重點（以 x = 東、y = 北）：
- 外環 189 × 156 m、高 48 m；80 個開間；三層拱廊（多立克／愛奧尼克／科林斯半露柱）＋閣樓（科林斯壁柱、隔間方窗、托架）
- 北側外環約 31 個開間仍完整；兩端是 19 世紀的磚造扶壁：
  東端 Stern（1807）＝斜坡狀三角形實心楔體、末端拱洞以磚封填；西端 Valadier（1820s）＝磚造仿拱廊、頂部斜切遞降
- 南側外環已崩塌，露出第二環：兩層拱廊＋上方開方窗的磚牆
- 內部：座席已消失，只剩磚造放射牆、同心拱廊牆與部分斜向拱頂；中央競技場地下室（hypogeum）外露，東側有重建的木地板
- 石灰華為暖橘米色、帶深色風化斑與中世紀被挖走鐵榫留下的孔洞
"""

import hashlib
import math
import os

import bpy
from mathutils import Matrix, Vector

from lib import TAU, TEX, Builder

N_BAYS = 80
A, B = 94.0, 78.0          # 外環中線半軸（外緣 189 × 156 m）
T = 2.4                     # 外環牆厚
TIERS = [(0.0, 10.5), (10.5, 11.85), (22.35, 11.6)]
ZA, ZTOP = 33.95, 48.0      # 閣樓底、頂
INTACT = range(6, 37)       # 北側完整的外環開間（31 間）
A_IN, B_IN = 41.5, 25.0     # 競技場（83 × 50 m）


# ---------------------------------------------------------------------- 自製貼圖（暖色石灰華＋風化斑）
def _noise(np, rng, size, cells):
    """可無縫拼接的低頻雜訊（0–1）"""
    from PIL import Image

    a = (rng.random((cells, cells)) * 255).astype("uint8")
    im = Image.fromarray(a)
    big = Image.new("L", (cells * 3, cells * 3))
    for i in range(3):
        for j in range(3):
            big.paste(im, (i * cells, j * cells))
    big = big.resize((size * 3, size * 3), Image.BICUBIC)
    return np.asarray(big.crop((size, size, 2 * size, 2 * size)), dtype=np.float32) / 255.0


def _custom_diffuse(key, src, tint, contrast=1.0, blotch=0.0, holes=0, streak=0.0, chroma=0.0, seed=1, gain=1.0):
    import numpy as np
    from PIL import Image

    h = hashlib.md5(repr((key, src, tint, contrast, blotch, holes, streak, chroma, seed, gain)).encode()).hexdigest()[:10]
    out_dir = os.path.join(TEX, "_tinted")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"co_{key}_{h}.jpg")
    if os.path.exists(out):
        return out
    im = np.asarray(Image.open(os.path.join(TEX, src, "diff.jpg")).convert("RGB"), dtype=np.float32) / 255.0
    size = im.shape[0]
    lum = im @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    rel = lum / lum.mean()
    rel = np.clip(rel, 0.05, 3.0) ** contrast
    col = np.array([int(tint.lstrip("#")[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=np.float32)
    rgb = rel[..., None] * col[None, None, :]
    if chroma > 0:  # 保留一點原圖色彩變化
        orig = im / np.maximum(lum[..., None], 1e-3) * lum.mean()
        rgb = rgb * (1 - chroma) + orig * col.mean() / max(orig.mean(), 1e-3) * rel[..., None] * chroma
    rng = np.random.default_rng(seed)
    if blotch > 0:  # 大小不一的深色風化斑
        n = 0.55 * _noise(np, rng, size, 4) + 0.3 * _noise(np, rng, size, 9) + 0.15 * _noise(np, rng, size, 23)
        m = np.clip((n - 0.48) / 0.2, 0, 1)
        dark = 1 - blotch * m
        warm = np.stack([dark, dark * 0.97, dark * 0.93], -1)
        rgb = rgb * warm
        light = np.clip((0.42 - n) / 0.2, 0, 1) * blotch * 0.35
        rgb = rgb * (1 + light[..., None])
    if streak > 0:  # 垂直雨水污痕
        cols = _noise(np, rng, size, 37)[0:1, :]
        s = np.clip((cols - 0.55) / 0.25, 0, 1) * _noise(np, rng, size, 3)
        rgb = rgb * (1 - streak * s[..., None] * np.array([1, 0.98, 0.95], dtype=np.float32))
    if holes > 0:  # 中世紀挖鐵榫留下的孔洞
        yy, xx = np.mgrid[0:size, 0:size]
        for _ in range(holes):
            cx, cy = rng.integers(0, size, 2)
            r = rng.uniform(5, 13)
            dx = (xx - cx + size // 2) % size - size // 2
            dy = (yy - cy + size // 2) % size - size // 2
            d = np.sqrt(dx * dx + (dy * 1.3) ** 2) / r
            rgb = rgb * (1 - 0.75 * np.clip(1.2 - d, 0, 1)[..., None])
    rgb = np.clip(rgb * gain, 0, 1)
    Image.fromarray((rgb * 255).astype("uint8")).save(out, quality=86)
    return out


def _small_map(src, kind, size=512):
    """縮小法線／ARM 貼圖以控制 GLB 體積"""
    from PIL import Image

    out = os.path.join(TEX, "_tinted", f"{src}_{kind}{size}.jpg")
    if not os.path.exists(out):
        im = Image.open(os.path.join(TEX, src, f"{kind}.jpg")).convert("RGB")
        im.resize((size, size), Image.LANCZOS).save(out, quality=88)
    return out


def _mat(b, name, diff_path, src, tile, normal=1.0, rough=None, nsize=512):
    if name in b._cache:
        return b._cache[name]
    m = bpy.data.materials.new(f"{b.name}_{name}")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(diff_path, check_existing=True)
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    if normal > 0 and os.path.exists(os.path.join(TEX, src, "nor.jpg")):
        nimg = nt.nodes.new("ShaderNodeTexImage")
        nimg.image = bpy.data.images.load(_small_map(src, "nor", nsize), check_existing=True)
        nimg.image.colorspace_settings.name = "Non-Color"
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = normal
        nt.links.new(nimg.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = rough if rough is not None else 0.85
    bsdf.inputs["Metallic"].default_value = 0.0
    return b._register(name, m, tile)


# ---------------------------------------------------------------------- 幾何工具
def _ell(a, b, t):
    return a * math.cos(t), b * math.sin(t)


def _bay_t(i):
    return TAU * i / N_BAYS


def _chord(a, b, i, overlap=0.0):
    """第 i 個開間在橢圓 (a, b) 上的弦：中心、切線角、長度、外法線"""
    x0, y0 = _ell(a, b, _bay_t(i))
    x1, y1 = _ell(a, b, _bay_t(i + 1))
    L = math.hypot(x1 - x0, y1 - y0)
    tx, ty = (x1 - x0) / L, (y1 - y0) / L
    return Vector(((x0 + x1) / 2, (y0 + y1) / 2, 0)), math.atan2(ty, tx), L + overlap, Vector((ty, -tx, 0)), Vector((tx, ty, 0))


def _arch_frame(b, mi, width, height, spring, opening, depth, M, seg=8):
    """同 lib.arch_frame，但可指定拱弧分段數（減面）"""
    w, o = width / 2, opening / 2
    arc = b.arch_points(opening, spring, seg=seg)
    b.profile_wall(mi, [(-w, 0), (-o, 0), (-o, spring), (-w, spring)], depth, M)
    b.profile_wall(mi, [(o, 0), (w, 0), (w, spring), (o, spring)], depth, M)
    mid = len(arc) // 2
    left, right, apex = arc[: mid + 1], arc[mid:], arc[mid]
    b.profile_wall(mi, [(-w, spring), (-o, spring)] + left[1:] + [(apex[0], height), (-w, height)], depth, M)
    b.profile_wall(mi, [(apex[0], apex[1])] + right[1:-1] + [(o, spring), (w, spring), (w, height), (apex[0], height)], depth, M)


def _hexa(b, mi, pts):
    """8 點六面體：前 4 點為底（逆時針），後 4 點為頂"""
    vs = [b.bm.verts.new(p) for p in pts]
    for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
        b.bm.faces.new([vs[k] for k in f])
    b._assign(vs, mi)
    return vs


def _ring_pt(d, t, z, extra=0.0):
    x, y = _ell(A - d + extra, B - d + extra, t)
    return Vector((x, y, z))


# ====================================================================== 羅馬競技場
def colosseum(path):
    b = Builder("Colosseum", seed=13)
    rng = b.rng

    # ------------------------------------------------ 材質
    tv_src = "large_sandstone_blocks_01"
    trav = _mat(b, "travertine", _custom_diffuse("trav", tv_src, "#d9ad8a", contrast=0.5, blotch=0.2, holes=14, streak=0.15, seed=3, gain=1.0), tv_src, 3.6, normal=1.1)
    trav_w = _mat(b, "travertine_weathered", _custom_diffuse("travw", tv_src, "#c99f80", contrast=0.55, blotch=0.28, holes=20, streak=0.25, seed=7, gain=1.0), tv_src, 3.6, normal=1.1)
    trav_lt = _mat(b, "travertine_light", _custom_diffuse("travl", tv_src, "#e0bc9c", contrast=0.45, blotch=0.14, holes=6, streak=0.08, seed=11, gain=1.0), tv_src, 3.6, normal=1.0)
    br_src = "broken_brick_wall"
    brick = _mat(b, "brick", _custom_diffuse("brick", br_src, "#a97c68", contrast=0.75, blotch=0.2, chroma=0.0, seed=5), br_src, 2.4, normal=1.0)
    brick_d = _mat(b, "brick_old", _custom_diffuse("brickd", br_src, "#957060", contrast=0.8, blotch=0.25, chroma=0.0, seed=9), br_src, 2.4, normal=1.0)
    gr_src = "rock_ground"
    ground = _mat(b, "ground", _custom_diffuse("ground", gr_src, "#806654", contrast=0.6, blotch=0.0, seed=4), gr_src, 7.0, normal=0.6)
    grass = _mat(b, "grass", _custom_diffuse("grass", "grass_ground", "#62743a", contrast=1.0, blotch=0.25, chroma=0.3, seed=2), "grass_ground", 6.0, normal=0.6)
    wood = b.color("arena_floor", "#8d6c4c", rough=0.85)
    dark = b.color("void", "#2b231d", rough=1.0)

    # ------------------------------------------------ 地面（含競技場地下室凹坑）
    PIT = -4.6
    b.ering(ground, (A_IN, B_IN), (175, 175), -5.0, 0.0, seg=128)
    b.ering(brick_d, (0.01, 0.01), (A_IN, B_IN), -5.2, PIT, seg=64)  # 地下室地面
    b.ering(brick_d, (A_IN - 0.8, B_IN - 0.8), (A_IN + 0.1, B_IN + 0.1), PIT, -0.3, seg=128)  # 地下室外圍牆
    # 西南側草坪
    b.ering(grass, (128, 112), (172, 172), 0.0, 0.05, seg=128, t0=math.radians(185), t1=math.radians(262))
    b.ering(grass, (124, 108), (172, 172), 0.0, 0.05, seg=128, t0=math.radians(275), t1=math.radians(300))

    def tier_arcade(mi, a_, b_, i, z, hp, opening, spring, depth, ov=0.12, seg=8):
        c, phi, L, n_out, tdir = _chord(a_, b_, i, ov)
        M = Matrix.Translation(c + Vector((0, 0, z))) @ Matrix.Rotation(phi, 4, "Z")
        _arch_frame(b, mi, L, hp, spring, opening, depth, M, seg=seg)
        return c, phi, L, n_out, tdir

    # ================================================= 外環（北側完整段）
    ENT = [1.75, 1.6, 1.6]
    for i in INTACT:
        mi = trav if rng.random() < 0.6 else (trav_w if rng.random() < 0.6 else trav_lt)
        # 東端最後兩間：Stern 以磚封填拱洞
        filled = i in (6, 7)
        for k, (z, h) in enumerate(TIERS):
            hp = h - ENT[k]
            spring = 4.95 if k == 0 else 6.0
            o = 4.2
            c, phi, L, n_out, tdir = tier_arcade(mi, A, B, i, z, hp, o, spring, T)
            face = c + n_out * (T / 2)
            # 拱緣飾帶（archivolt）、拱心石、拱墩
            arc = b.arch_points(o + 0.9, spring, seg=4)
            arc_in = b.arch_points(o, spring, seg=4)
            Mf = Matrix.Translation(face + n_out * 0.06 + Vector((0, 0, z))) @ Matrix.Rotation(phi, 4, "Z")
            for (p0, p1, q0, q1) in zip(arc, arc[1:], arc_in, arc_in[1:]):
                b.profile_wall(mi, [p0, q0, q1, p1], 0.16, Mf)
            kz = z + spring + o / 2 - 0.15
            b.profile_wall(trav_lt, [(-0.32, 0), (0.32, 0), (0.42, 1.05), (-0.42, 1.05)], 0.34, Matrix.Translation(face + n_out * 0.1 + Vector((0, 0, kz))) @ Matrix.Rotation(phi, 4, "Z"))
            for s in (-1, 1):
                ip = face + n_out * 0.05 + tdir * s * (o / 2 + 0.3)
                b.box_base(mi, (0.62, 0.22, 0.38), (ip.x, ip.y, z + spring - 0.38), rot=(0, 0, phi))
            if filled:
                fz = z + 0.0
                pc = c - n_out * 0.35
                b.box_base(brick, (o + 0.1, 0.9, spring), (pc.x, pc.y, fz), rot=(0, 0, phi))
                Mi = Matrix.Translation(pc + Vector((0, 0, z))) @ Matrix.Rotation(phi, 4, "Z")
                b.profile_wall(brick, [(-o / 2 - 0.05, spring)] + b.arch_points(o + 0.1, spring, seg=8)[1:-1] + [(o / 2 + 0.05, spring)], 0.9, Mi)
            # 拱廊內的頂板（環形走廊的拱頂）
        # 半露柱（位於開間界線）
        t = _bay_t(i)
        nx, ny = math.cos(t) / A, math.sin(t) / B
        nl = math.hypot(nx, ny)
        nrm = Vector((nx / nl, ny / nl, 0))
        tang = Vector((-nrm.y, nrm.x, 0))
        phi_c = math.atan2(tang.y, tang.x)
        pts = [t]
        if i == INTACT[-1]:
            pts.append(_bay_t(i + 1))
        for tc in pts:
            nx, ny = math.cos(tc) / A, math.sin(tc) / B
            nl = math.hypot(nx, ny)
            nrm = Vector((nx / nl, ny / nl, 0))
            px, py = _ell(A, B, tc)
            base = Vector((px, py, 0)) + nrm * (T / 2 + 0.22)
            for k, (z, h) in enumerate(TIERS):
                hp = h - ENT[k]
                ped = 0.0 if k == 0 else 1.55
                if ped:
                    pb = base + nrm * 0.15
                    b.box_base(mi, (1.55, 0.95, ped), (pb.x, pb.y, z), rot=(0, 0, phi_c))
                b.box_base(trav_lt, (1.35, 1.05, 0.32), (base.x, base.y, z + ped), rot=(0, 0, phi_c))
                ch = 0.45 if k == 0 else 0.85
                b.cyl(mi, 0.6, 0.53, hp - ped - 0.32 - ch, (base.x, base.y, z + ped + 0.32), seg=10, smooth=True)
                if k == 0:
                    b.cyl(trav_lt, 0.55, 0.72, ch * 0.5, (base.x, base.y, z + hp - ch), seg=10, smooth=True)
                    b.box_base(trav_lt, (1.5, 1.2, ch * 0.5), (base.x, base.y, z + hp - ch * 0.5), rot=(0, 0, phi_c))
                else:
                    b.cyl(trav_lt, 0.55, 0.85, ch, (base.x, base.y, z + hp - ch), seg=10, smooth=True)
                    b.box_base(trav_lt, (1.75, 1.3, 0.2), (base.x, base.y, z + hp - 0.2), rot=(0, 0, phi_c))
            # 閣樓壁柱
            pb = Vector((px, py, 0)) + nrm * (T / 2 + 0.2)
            b.box_base(trav, (1.0, 0.5, 8.5), (pb.x, pb.y, ZA + 2.1), rot=(0, 0, phi_c))
            b.box_base(trav_lt, (1.2, 0.5, 0.7), (pb.x, pb.y, ZA + 10.6), rot=(0, 0, phi_c))

        # 閣樓：實牆，隔間開方窗、三個托架
        c, phi, L, n_out, tdir = _chord(A, B, i, 0.12)
        hA = ZTOP - ZA - 1.4
        if i % 2 == 0:
            ww, wz0, wz1 = 1.5, 3.7, 6.2
            b.box_base(mi, (L, T, wz0), (c.x, c.y, ZA), rot=(0, 0, phi))
            b.box_base(mi, (L, T, hA - wz1), (c.x, c.y, ZA + wz1), rot=(0, 0, phi))
            side = (L - ww) / 2
            for s in (-1, 1):
                p = c + tdir * s * (ww / 2 + side / 2)
                b.box_base(mi, (side, T, wz1 - wz0), (p.x, p.y, ZA + wz0), rot=(0, 0, phi))
            # 窗框
            fp = c + n_out * (T / 2)
            b.box_base(trav_lt, (ww + 0.5, 0.2, 0.25), (fp.x, fp.y, ZA + wz0 - 0.25), rot=(0, 0, phi))
            b.box_base(dark, (ww, 0.1, wz1 - wz0), (c.x - n_out.x * (T / 2 - 0.05), c.y - n_out.y * (T / 2 - 0.05), ZA + wz0), rot=(0, 0, phi))
        else:
            b.box_base(mi, (L, T, hA), (c.x, c.y, ZA), rot=(0, 0, phi))
        for s in (-1, 0, 1):
            p = c + n_out * (T / 2 + 0.25) + tdir * s * (L * 0.3)
            b.box_base(trav_lt, (0.42, 0.5, 0.55), (p.x, p.y, ZA + 9.9), rot=(0, 0, phi))
        # 頂部（略為殘缺）
        top_h = 1.4 - (rng.random() * 0.7 if rng.random() < 0.35 else 0)
        b.box_base(mi, (L, T, top_h), (c.x, c.y, ZA + hA), rot=(0, 0, phi))

    t_e0, t_e1 = _bay_t(INTACT[0]), _bay_t(INTACT[-1] + 1)
    # 各層柱楣＋簷口（連續環帶）
    for k, (z, h) in enumerate(TIERS):
        hp = h - ENT[k]
        b.ering(trav, (A - T / 2, B - T / 2), (A + T / 2 + 0.45, B + T / 2 + 0.45), z + hp, z + h - 0.45, seg=480, t0=t_e0, t1=t_e1)
        b.ering(trav_lt, (A - T / 2, B - T / 2), (A + T / 2 + 0.85, B + T / 2 + 0.85), z + h - 0.45, z + h, seg=480, t0=t_e0, t1=t_e1)
    # 閣樓底座帶、頂簷
    b.ering(trav, (A + T / 2 - 0.15, B + T / 2 - 0.15), (A + T / 2 + 0.25, B + T / 2 + 0.25), ZA, ZA + 2.1, seg=480, t0=t_e0, t1=t_e1)
    b.ering(trav_lt, (A + T / 2 - 0.15, B + T / 2 - 0.15), (A + T / 2 + 0.5, B + T / 2 + 0.5), ZA + 11.3, ZA + 11.85, seg=480, t0=t_e0, t1=t_e1)
    # 外環與第二環之間的環形走廊拱頂（樓板）
    A2, B2 = A - 7.0, B - 7.0
    for zf in (10.5, 22.35, ZA):
        b.ering(brick_d, (A2 + 0.95, B2 + 0.95), (A - T / 2 + 0.05, B - T / 2 + 0.05), zf - 0.9, zf - 0.02, seg=480, t0=t_e0, t1=t_e1)

    # ================================================= 兩端扶壁
    # 東端 Stern 扶壁（1807）：斜坡狀三角形實心磚楔，往東延伸 4 間、由 48 m 降到地面
    def wedge_bay(mi, i, d_in, d_out, z_a, z_b, zb=0.0):
        t0, t1 = _bay_t(i), _bay_t(i + 1)
        pts = [_ring_pt(0, t0, zb, -d_in), _ring_pt(0, t0, zb, d_out), _ring_pt(0, t1, zb, d_out), _ring_pt(0, t1, zb, -d_in)]
        top = [p.copy() for p in pts]
        top[0].z = top[1].z = z_a
        top[2].z = top[3].z = z_b
        _hexa(b, mi, pts + top)

    hs = [48.0 - 0.6, 37.0, 25.5, 13.5, 1.2]
    for k, i in enumerate((5, 4, 3, 2)):
        d_out = T / 2 + 0.6 + 1.6 * (k + 1) / 4
        wedge_bay(brick, i, T / 2 + 0.6, d_out, hs[k + 1], hs[k])
        # 楔體表面的盲拱輪廓（凸出的磚帶）
    # 楔體頂端的石灰華壓頂
    for k, i in enumerate((5, 4, 3, 2)):
        t0, t1 = _bay_t(i), _bay_t(i + 1)
        d_out = T / 2 + 0.6 + 1.6 * (k + 1) / 4
        p = [_ring_pt(0, t0, 0, -(T / 2 + 0.7)), _ring_pt(0, t0, 0, d_out + 0.1), _ring_pt(0, t1, 0, d_out + 0.1), _ring_pt(0, t1, 0, -(T / 2 + 0.7))]
        q = [v.copy() for v in p]
        p[0].z = p[1].z = hs[k + 1] - 0.05
        p[2].z = p[3].z = hs[k] - 0.05
        for v, zz in zip(q, (hs[k + 1], hs[k + 1], hs[k], hs[k])):
            v.z = zz + 0.45
        _hexa(b, trav_w, p + q)

    # 西端 Valadier 扶壁（1820s）：末兩間以磚仿砌拱廊，頂部斜切：由閣樓頂 48 m 斜降至第二層簷口 22.35 m
    i_v = INTACT[-1] + 1
    z_mid = 35.0
    for ii, ntier in ((i_v, 3), (i_v + 1, 2)):
        c, phi, L, n_out, tdir = _chord(A, B, ii, 0.12)
        for k, (z, h) in enumerate(TIERS[:ntier]):
            hp = h - ENT[k]
            tier_arcade(brick, A, B, ii, z, hp, 4.2, 4.95 if k == 0 else 6.0, T)
            b.box_base(trav_w if k < 2 else brick, (L, T + 0.7, ENT[k]), (c.x, c.y, z + hp), rot=(0, 0, phi))
            # 磚砌壁柱
            pp = c + n_out * (T / 2 + 0.25) + tdir * (L / 2 - 0.1)
            b.box_base(brick, (1.1, 0.5, hp), (pp.x, pp.y, z), rot=(0, 0, phi))
    wedge_bay(brick, i_v, T / 2, T / 2 + 0.2, 47.4, z_mid, zb=ZA)
    wedge_bay(brick, i_v + 1, T / 2, T / 2 + 0.2, z_mid, 22.9, zb=22.35)

    # 南側崩塌段：外環只剩地面上的石灰華基座與零星殘墩
    b.ering(trav_w, (A - T / 2 - 0.4, B - T / 2 - 0.4), (A + T / 2 + 0.6, B + T / 2 + 0.6), 0.0, 0.15, seg=480, t0=_bay_t(i_v + 2), t1=_bay_t(INTACT[0] - 4) + TAU)
    for i in range(i_v + 3, INTACT[0] - 4 + N_BAYS):
        if rng.random() < 0.12:
            c, phi, L, n_out, tdir = _chord(A, B, i % N_BAYS)
            p = c - tdir * L / 2
            b.box_base(trav_w, (1.6, T * 0.9, rng.uniform(0.4, 1.2)), (p.x, p.y, 0.15), rot=(0, 0, phi))

    # ================================================= 第二環（南側露出：兩層拱廊＋開窗磚牆）
    T2 = 2.0
    for i in range(N_BAYS):
        hidden = i in INTACT
        c, phi, L, n_out, tdir = _chord(A2, B2, i, 0.1)
        m1 = trav_w if rng.random() < 0.75 else trav
        tier_arcade(m1, A2, B2, i, 0.0, 9.3, 3.9, 4.8, T2, seg=6)
        m2 = brick if rng.random() < 0.45 else trav_w
        tier_arcade(m2, A2, B2, i, 10.5, 10.6, 3.6, 5.4, T2, seg=6)
        # 第三層：磚牆＋方窗
        top = 34.0 if hidden else 22.35 + rng.uniform(8.0, 10.0) - (rng.uniform(2, 5) if rng.random() < 0.15 else 0)
        h3 = top - 22.35
        wz0, wz1, ww = 2.4, 4.9, 1.3
        if hidden:
            b.box_base(brick_d, (L, T2, h3), (c.x, c.y, 22.35), rot=(0, 0, phi))
            continue
        b.box_base(brick, (L, T2, wz0), (c.x, c.y, 22.35), rot=(0, 0, phi))
        side = (L - ww) / 2
        for s in (-1, 1):
            p = c + tdir * s * (ww / 2 + side / 2)
            b.box_base(brick, (side, T2, wz1 - wz0), (p.x, p.y, 22.35 + wz0), rot=(0, 0, phi))
        if h3 > wz1:
            b.box_base(brick, (L, T2, h3 - wz1), (c.x, c.y, 22.35 + wz1), rot=(0, 0, phi))
    # 第二環的層間石帶
    for z0_, z1_ in ((9.3, 10.5), (21.1, 22.35)):
        b.ering(trav, (A2 - T2 / 2, B2 - T2 / 2), (A2 + T2 / 2 + 0.25, B2 + T2 / 2 + 0.25), z0_, z1_, seg=480)

    # ================================================= 內部：磚造放射牆、同心拱廊牆、殘存斜拱頂
    def zprof(d):
        """座席底下結構的頂面高度（由第二環 31 m 斜降到競技場邊 5 m）"""
        return 31.0 - (d - 8.0) * (26.0 / 44.5)

    rings_d = [14.0, 22.0, 31.0, 41.0]
    for d in rings_d:
        a_, b_ = A - d, B - d
        for i in range(N_BAYS):
            c, phi, L, n_out, tdir = _chord(a_, b_, i, 0.1)
            Ht = zprof(d) + 1.2 - (rng.uniform(1.5, 5.0) if rng.random() < 0.3 else rng.uniform(0, 1.2))
            mi = brick if rng.random() < 0.7 else brick_d
            o = min(3.4, L * 0.6)
            h1 = min(10.5, Ht)
            tier_arcade(trav_w if d < 20 else mi, a_, b_, i, 0.0, h1, o, max(1.0, h1 - o / 2 - 1.8), 1.4, seg=4)
            if Ht - h1 > 0.5:
                if Ht - h1 > 6 and rng.random() < 0.6:
                    tier_arcade(mi, a_, b_, i, h1, Ht - h1, o * 0.8, max(1.0, Ht - h1 - o * 0.4 - 1.5), 1.4, seg=4)
                else:
                    b.box_base(mi, (L, 1.4, Ht - h1), (c.x, c.y, h1), rot=(0, 0, phi))
    # 放射牆：沿開間界線，從第二環內側到競技場邊，頂面依斜坡逐段下降
    seg_d = [8.0] + rings_d + [52.0]
    vault_runs = {}
    for i in range(N_BAYS):
        t = _bay_t(i)
        mi = brick if rng.random() < 0.65 else brick_d
        for d0, d1 in zip(seg_d, seg_d[1:]):
            z0_ = zprof(d0) - rng.uniform(0, 1.5)
            z1_ = zprof(d1) - rng.uniform(0, 1.0)
            p0, p1 = _ring_pt(d0, t, 0), _ring_pt(d1, t, 0)
            dirv = (p1 - p0).normalized()
            side = Vector((-dirv.y, dirv.x, 0)) * 0.5
            pts = [p0 - side, p1 - side, p1 + side, p0 + side]
            top = [p.copy() for p in pts]
            top[0].z = top[3].z = z0_
            top[1].z = top[2].z = z1_
            _hexa(b, mi, pts + top)
    # 斜向拱頂殘段（座席的底座），約一半的開間仍存
    for i in range(N_BAYS):
        if rng.random() < 0.45:
            continue
        t0, t1 = _bay_t(i), _bay_t(i + 1)
        for d0, d1 in zip(seg_d[1:], seg_d[2:]):
            if rng.random() < 0.35:
                continue
            z0_, z1_ = zprof(d0) - 1.6, zprof(d1) - 1.6
            pts = [_ring_pt(d0, t0, z0_ - 0.8), _ring_pt(d1, t0, z1_ - 0.8), _ring_pt(d1, t1, z1_ - 0.8), _ring_pt(d0, t1, z0_ - 0.8)]
            top = [_ring_pt(d0, t0, z0_), _ring_pt(d1, t0, z1_), _ring_pt(d1, t1, z1_), _ring_pt(d0, t1, z0_)]
            _hexa(b, brick_d if rng.random() < 0.5 else brick, pts + top)
    # 東側重建的一小段石灰華座席
    for s in range(6):
        d = 45.0 + s * 1.15
        b.ering(trav_lt, (A - d - 1.2, B - d - 1.2), (A - d, B - d), 0.0, zprof(d) - 0.2, seg=240, t0=math.radians(-14), t1=math.radians(14))

    # ================================================= 競技場：牆（podium）與地下室
    b.ering(trav_w, (A_IN, B_IN), (A_IN + 1.6, B_IN + 1.6), 0.0, 4.2, seg=160)
    b.ering(trav_lt, (A_IN - 0.15, B_IN - 0.15), (A_IN + 1.75, B_IN + 1.75), 4.2, 4.55, seg=160)
    # 地下室牆（與長軸平行的通道牆＋橫向隔牆）
    wall_top = -0.5
    for yv in (-21.5, -17.5, -13.5, -9.5, -5.5, -1.6, 1.6, 5.5, 9.5, 13.5, 17.5, 21.5):
        half = A_IN * math.sqrt(max(0.0, 1 - (yv / B_IN) ** 2)) - 0.8
        if half < 2:
            continue
        x = -half
        while x < half:
            seglen = min(half - x, rng.uniform(5, 14))
            if rng.random() < 0.85:
                b.box_base(brick_d if rng.random() < 0.6 else brick, (seglen, 0.8, wall_top - PIT - rng.uniform(0, 1.6)), (x + seglen / 2, yv, PIT))
            x += seglen + rng.uniform(0.8, 2.0)
    for xv in [-36 + 4.0 * k for k in range(19)]:
        half = B_IN * math.sqrt(max(0.0, 1 - (xv / A_IN) ** 2)) - 0.8
        if half < 2:
            continue
        for yv0, yv1 in ((-half, -1.6), (1.6, half)):
            for k in range(int((yv1 - yv0) / 4.0)):
                if rng.random() < 0.55:
                    y0 = yv0 + k * 4.0 + 0.4
                    b.box_base(brick_d, (0.7, 3.2, wall_top - PIT - rng.uniform(0.3, 2.0)), (xv, y0 + 1.6, PIT))
    # 東端重建的木地板
    xs0 = 16.0
    poly = [(xs0, -B_IN * math.sqrt(1 - (xs0 / A_IN) ** 2) + 0.05)]
    for k in range(1, 16):
        tt = -math.acos(xs0 / A_IN) + 2 * math.acos(xs0 / A_IN) * k / 16
        poly.append((A_IN * math.cos(tt) - 0.05, B_IN * math.sin(tt)))
    poly.append((xs0, B_IN * math.sqrt(1 - (xs0 / A_IN) ** 2) - 0.05))
    b.prism(wood, poly, -0.45, 0.35)

    # ================================================= 植被：石松（傘松）與絲柏
    pine_c = [b.color("pine_dark", "#33461f", rough=0.9), b.color("pine_mid", "#415a27", rough=0.9), b.color("pine_light", "#536b30", rough=0.9)]
    trunk = b.color("trunk", "#5b4636", rough=0.95)
    cyp = b.color("cypress", "#2b3f22", rough=0.9)

    def stone_pine(x, y, h):
        lean = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)).normalized() * h * 0.12
        top = Vector((x, y, 0)) + lean + Vector((0, 0, h * 0.78))
        d = top - Vector((x, y, 0))
        rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_euler()
        b.cyl(trunk, h * 0.03, h * 0.02, d.length, (x, y, 0), seg=6, rot=tuple(rot))
        # 分枝：主幹頂端分出 3 枝
        for k in range(3):
            a = TAU * k / 3 + rng.random()
            tip = top + Vector((math.cos(a), math.sin(a), 0)) * h * 0.2 + Vector((0, 0, h * 0.05))
            dv = tip - top
            b.cyl(trunk, h * 0.014, h * 0.009, dv.length, tuple(top - Vector((0, 0, h * 0.02))), seg=5, rot=tuple(Vector((0, 0, 1)).rotation_difference(dv.normalized()).to_euler()))
        # 傘狀樹冠：多個扁平不規則團塊，深淺交錯
        for k in range(10):
            a = TAU * k / 9 + rng.random() * 0.6
            r = h * (0.05 if k == 0 else rng.uniform(0.16, 0.3))
            cx, cy = top.x + r * math.cos(a), top.y + r * math.sin(a)
            w = h * rng.uniform(0.2, 0.3)
            zc = top.z + h * 0.1 - (r / h) ** 2 * h * 0.5 + rng.uniform(-0.02, 0.03) * h
            b.rock(pine_c[rng.randrange(3)], (w, w * rng.uniform(0.75, 1.1), h * rng.uniform(0.12, 0.17)), (cx, cy, zc), rot=(0, 0, rng.random() * 3), rough=0.5, subdiv=2, seed=rng.randint(0, 9999), flat_bottom=False, round_=0.75)

    def cypress(x, y, h):
        b.cyl(trunk, 0.25, 0.2, 1.5, (x, y, 0), seg=6)
        sd = rng.random() * 10
        b.lathe(cyp, [(0.0, 0.8), (h * 0.08, 1.5), (h * 0.11, h * 0.3), (h * 0.095, h * 0.6), (h * 0.05, h * 0.88), (0, h)], (x, y, 0), seg=10, smooth=True,
                radial=lambda t, sd=sd: 1 + 0.12 * math.sin(3 * t + sd) + 0.08 * math.sin(7 * t + sd * 2))

    def ok(x, y):
        return (x / 112) ** 2 + (y / 97) ** 2 > 1
    def sector(x, y, lo, hi):
        a = math.degrees(math.atan2(y, x)) % 360
        return lo <= a <= hi
    # 傘松：東北（Oppio 丘）與南側（Palatino 丘方向）；西側為空曠的廣場
    for x, y in b.scatter(9, 120, 170, avoid=lambda x, y: not ok(x, y) or not sector(x, y, 20, 80), min_dist=15):
        stone_pine(x, y, rng.uniform(15, 21))
    for x, y in b.scatter(8, 125, 170, avoid=lambda x, y: not ok(x, y) or not sector(x, y, 235, 300), min_dist=15):
        stone_pine(x, y, rng.uniform(14, 20))
    for x, y in b.scatter(6, 115, 160, avoid=lambda x, y: not ok(x, y) or not sector(x, y, 205, 235), min_dist=7):
        cypress(x, y, rng.uniform(14, 19))

    b.export(path)
