"""great_wall 寫實模型（金山嶺段；尺寸依實測資料，公尺）

金山嶺長城：牆高約 5–8 m、頂寬約 5 m（步道約 4 m），外側垛口牆約 1.9 m、內側宇牆約 1 m；
牆身灰褐色明代城磚、下部條石基礎；陡坡處步道為階梯；敵樓約 10 m 見方，
下為條石基座、上為磚砌樓層（每面三個拱窗），頂部垛口，部分敵樓頂上另有磚砌樓櫓與瓦頂。
山體覆滿茂密深綠山林，遠方多層山脊漸次泛藍。
"""

import math
import os
import random

import bpy
from mathutils import Matrix, Vector, noise

from lib import TAU, TEX, Builder


# ---------------------------------------------------------------------- 程式產生的林冠貼圖
def _canopy_textures():
    """俯視林冠：大量重疊的樹冠圓頂（含深色林隙），同時輸出法線貼圖；可無縫重複"""
    import numpy as np
    from PIL import Image

    out_d = os.path.join(TEX, "_tinted", "gw_canopy_diff.jpg")
    out_n = os.path.join(TEX, "_tinted", "gw_canopy_nor.jpg")
    if os.path.exists(out_d) and os.path.exists(out_n):
        return out_d, out_n
    os.makedirs(os.path.dirname(out_d), exist_ok=True)
    N = 1024
    rnd = np.random.default_rng(7)
    H = np.zeros((N, N), np.float32)
    C = np.zeros((N, N, 3), np.float32)
    C[:] = (20, 31, 15)
    pal = np.array([(38, 58, 26), (46, 68, 30), (55, 78, 34), (33, 51, 23), (63, 84, 38), (44, 62, 28), (50, 66, 30)], np.float32)
    light = np.array([-0.45, 0.45, 0.77])
    for _ in range(1500):
        cx, cy = rnd.uniform(0, N, 2)
        r = rnd.uniform(16, 34)
        z0 = rnd.uniform(0, 10)
        col = pal[rnd.integers(len(pal))] * rnd.uniform(0.85, 1.12)
        R = int(r) + 1
        ys = (np.arange(int(cy) - R, int(cy) + R + 1)) % N
        xs = (np.arange(int(cx) - R, int(cx) + R + 1)) % N
        dy = (np.arange(int(cy) - R, int(cy) + R + 1) - cy)[:, None]
        dx = (np.arange(int(cx) - R, int(cx) + R + 1) - cx)[None, :]
        # 不規則邊緣
        ang = np.arctan2(dy, dx)
        rr = r * (1 + 0.12 * np.sin(ang * rnd.integers(3, 7) + rnd.uniform(0, 6)))
        d2 = (dx * dx + dy * dy) / (rr * rr)
        inside = d2 < 1
        h = np.sqrt(np.clip(1 - d2, 0, 1)) * r * 0.55 + z0
        sub = H[np.ix_(ys, xs)]
        m = inside & (h > sub)
        nx, ny = dx / rr, -dy / rr
        nz = np.sqrt(np.clip(1 - nx * nx - ny * ny, 0.05, 1))
        shade = np.clip(nx * light[0] + ny * light[1] + nz * light[2], 0, 1)
        f = (0.62 + 0.5 * shade) * (1 - 0.35 * np.clip(d2 - 0.6, 0, 1))
        newc = col[None, None, :] * f[..., None]
        subc = C[np.ix_(ys, xs)]
        subc[m] = newc[m]
        sub[m] = h[m]
        C[np.ix_(ys, xs)] = subc
        H[np.ix_(ys, xs)] = sub
    # 葉片細節雜訊
    C *= rnd.uniform(0.86, 1.12, (N, N, 1)).astype(np.float32)
    Image.fromarray(np.clip(C, 0, 255).astype(np.uint8)).save(out_d, quality=86)
    gx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) * 0.5
    gy = -(np.roll(H, -1, 0) - np.roll(H, 1, 0)) * 0.5
    k = 0.35
    n = np.dstack([-gx * k, -gy * k, np.ones_like(H)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    Image.fromarray(((n + 1) * 127.5).astype(np.uint8)).save(out_n, quality=90)
    return out_d, out_n


def _img_mat(b, name, diff, nor, tile, rough, strength=1.0):
    m = bpy.data.materials.new(f"{b.name}_{name}")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(diff, check_existing=True)
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    if nor:
        nimg = nt.nodes.new("ShaderNodeTexImage")
        nimg.image = bpy.data.images.load(nor, check_existing=True)
        nimg.image.colorspace_settings.name = "Non-Color"
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = strength
        nt.links.new(nimg.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
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


# ====================================================================== 萬里長城（金山嶺段）
def great_wall(path):
    b = Builder("GreatWall", seed=21)
    bm = b.bm
    cd, cn = _canopy_textures()
    forest = _img_mat(b, "forest", cd, cn, 64.0, 0.95, 0.8)
    rock = b.color("rock", "#6b604c", rough=0.95)
    haze1 = b.color("haze1", "#35554a", rough=1.0)
    haze2 = b.color("haze2", "#4a6c80", rough=1.0)
    brick = b.tex("brick", "brick_wall_006", tile=3.6, tint="#8c8273", normal=0.9)
    stone = b.tex("stone", "large_sandstone_blocks", tile=3.0, tint="#a39b8b", normal=0.0, rough=0.85)
    paving = b.tex("walkway", "white_sandstone_bricks_03", tile=2.0, tint="#9c9585", normal=0.0, rough=0.9)
    dark = b.color("opening", "#211e1b", rough=1.0)
    roof_tile = b.tex("roof_tile", "grey_roof_tiles", tile=1.5, tint="#5b5c5e", normal=0.0, rough=0.7)
    far_wall = b.color("far_wall", "#77756c", rough=0.9)
    crowns = [b.color(f"crown{i}", c, rough=0.9) for i, c in
              enumerate(("#2c4420", "#34502a", "#3b5a26", "#2a3e1f", "#43622c", "#30481f"))]
    R_IN, R = 430.0, 640.0

    # ------------------------------------------------------------------ 地形
    def path_pt(u):
        x = -360 + 720 * u
        y = 60 * math.sin(u * 5.2) + 25 * math.sin(u * 13)
        return x, y

    def ridge_h(u):
        return 72 + 45 * math.sin(u * 7.0 + 0.4) + 18 * math.sin(u * 19)

    samples = [path_pt(i / 400) for i in range(401)]

    def nearest(x, y):
        best, bu = 1e18, 0.0
        for i in range(0, 401, 4):
            px, py = samples[i]
            d = (x - px) ** 2 + (y - py) ** 2
            if d < best:
                best, bu = d, i / 400
        return math.sqrt(best), bu

    def height(x, y):
        d, bu = nearest(x, y)
        h = ridge_h(bu) * math.exp(-((d / 92) ** 1.5))
        p = Vector((x, y, 0))
        # 山稜支脈（ridged noise）與起伏
        rn = 1 - abs(noise.noise(p * 0.0065 + Vector((3, 1, 0))))
        h += 55 * rn ** 3 * min(1.0, d / 60)
        h += 22 * noise.noise(p * 0.006 + Vector((0, 0, 2))) + 7 * noise.noise(p * 0.025 + Vector((0, 0, 5)))
        h += 60 * max(0.0, (y - 120) / 250)  # 相機側較高的前景山
        r = math.hypot(x, y)
        th = math.atan2(y, x)
        # 外圈多層山脊（全周環繞，遠處漸高）
        for c, A, w, s in ((478, 85, 30, 1.0), (535, 120, 28, 2.0), (588, 150, 26, 3.0), (628, 175, 22, 4.0)):
            mod = 0.6 + 0.4 * noise.noise(Vector((math.cos(th) * 3 + s, math.sin(th) * 3, s)))
            # 稜線鋸齒：多頻 ridged noise
            q = Vector((math.cos(th) * 22, math.sin(th) * 22, s * 5))
            jag = 0.7 + 0.45 * (1 - abs(noise.noise(q))) ** 2 + 0.2 * noise.noise(q * 2.7)
            h += A * mod * jag * math.exp(-(((r - c) / w) ** 2))
        if r > R_IN - 40:
            h *= 1.0  # 外圈保留山形
        return max(0.0, h)

    f0 = len(bm.faces)
    b.ground_disc(forest, R, haze2, depth=30, height_fn=height, rings=104, seg=208)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[f0:]:
        if f.material_index != forest:
            continue
        c = f.calc_center_median()
        r = math.hypot(c.x, c.y)
        if r > 562:
            f.material_index = haze2
        elif r > 507:
            f.material_index = haze1
        else:
            f.normal_update()
            n = noise.noise(Vector((c.x * 0.02, c.y * 0.02, 9.0)))
            if n > 0.5 and f.normal.z < 0.8 and r < 470:
                f.material_index = rock

    # ------------------------------------------------------------------ 城牆（連續牆體、條石基礎、雉堞、階梯步道）
    N = 264
    pts = [path_pt(i / N) for i in range(N + 1)]
    g = [height(x, y) for x, y in pts]
    H, Wt, Wb = 7.2, 5.2, 6.6
    gs = [sum(g[max(0, i - 2):i + 3]) / len(g[max(0, i - 2):i + 3]) for i in range(len(g))]
    top = [max(gs[i] + H, g[i] + 5.6) for i in range(len(g))]
    base = [min(g[max(0, i - 1):i + 2]) - 4.0 for i in range(len(g))]
    tang, nrm = [], []
    for i in range(len(pts)):
        a = pts[max(0, i - 1)]
        c = pts[min(len(pts) - 1, i + 1)]
        t = Vector((c[0] - a[0], c[1] - a[1], 0)).normalized()
        tang.append(t)
        nrm.append(Vector((-t.y, t.x, 0)))  # 外側（+左）

    def V(i, off, z):
        p = pts[i]
        return Vector((p[0], p[1], z)) + nrm[i] * off

    def quad(vs, mi, smooth=False):
        f = bm.faces.new([bm.verts.new(v) for v in vs])
        f.material_index = mi
        f.smooth = smooth
        return f

    def strip(i, prof, mats):
        """在第 i→i+1 段之間依剖面點（off, z_fn）建立側面"""
        for k in range(len(prof) - 1):
            (o0, z0), (o1, z1) = prof[k], prof[k + 1]
            quad([V(i, o0, z0(i)), V(i + 1, o0, z0(i + 1)), V(i + 1, o1, z1(i + 1)), V(i, o1, z1(i))], mats[k])

    foot = lambda i: g[i] + 1.4
    o_mid = lambda frac: Wb / 2 + (Wt / 2 - Wb / 2) * frac
    for i in range(len(pts) - 1):
        # 外側面（基礎＋磚牆）
        fo = lambda j: (foot(j) - base[j]) / (top[j] - base[j])
        quad([V(i, Wb / 2, base[i]), V(i + 1, Wb / 2, base[i + 1]), V(i + 1, o_mid(fo(i + 1)), foot(i + 1)), V(i, o_mid(fo(i)), foot(i))], stone)
        quad([V(i, o_mid(fo(i)), foot(i)), V(i + 1, o_mid(fo(i + 1)), foot(i + 1)), V(i + 1, Wt / 2, top[i + 1]), V(i, Wt / 2, top[i])], brick)
        # 內側面
        quad([V(i, -o_mid(fo(i)), foot(i)), V(i + 1, -o_mid(fo(i + 1)), foot(i + 1)), V(i + 1, -Wb / 2, base[i + 1]), V(i, -Wb / 2, base[i])], stone)
        quad([V(i, -Wt / 2, top[i]), V(i + 1, -Wt / 2, top[i + 1]), V(i + 1, -o_mid(fo(i + 1)), foot(i + 1)), V(i, -o_mid(fo(i)), foot(i))], brick)
        # 外側垛口牆（下段連續）與內側宇牆
        for o_out, o_in, hh in ((Wt / 2, Wt / 2 - 0.62, 1.15), (-Wt / 2 + 0.5, -Wt / 2, 1.0)):
            zt = lambda j, hh=hh: top[j] + hh
            zb = lambda j: top[j] - 0.05
            quad([V(i, o_out, zb(i)), V(i + 1, o_out, zb(i + 1)), V(i + 1, o_out, zt(i + 1)), V(i, o_out, zt(i))], brick)
            quad([V(i, o_out, zt(i)), V(i + 1, o_out, zt(i + 1)), V(i + 1, o_in, zt(i + 1)), V(i, o_in, zt(i))], brick)
            quad([V(i, o_in, zt(i)), V(i + 1, o_in, zt(i + 1)), V(i + 1, o_in, zb(i + 1)), V(i, o_in, zb(i))], brick)
        # 步道：坡度大時做成階梯（鋸齒狀踏面＋踢面）
        dt = top[i + 1] - top[i]
        ns = min(14, int(abs(dt) / 0.3))
        wl, wr = -Wt / 2 + 0.3, Wt / 2 - 0.3
        if ns < 1:
            quad([V(i, wl, top[i]), V(i + 1, wl, top[i + 1]), V(i + 1, wr, top[i + 1]), V(i, wr, top[i])], paving)
        else:
            P0, P1 = Vector((*pts[i], 0)), Vector((*pts[i + 1], 0))
            n0, n1 = nrm[i], nrm[i + 1]
            def W(s, o, z):
                p = P0.lerp(P1, s) + n0.lerp(n1, s).normalized() * o
                return Vector((p.x, p.y, z))
            h = dt / ns
            z = top[i]
            for k in range(ns):
                s0, s1 = k / ns, (k + 1) / ns
                if dt > 0:  # 先踢面再踏面
                    quad([W(s0, wl, z), W(s0, wr, z), W(s0, wr, z + h), W(s0, wl, z + h)], stone)
                    quad([W(s0, wl, z + h), W(s0, wr, z + h), W(s1, wr, z + h), W(s1, wl, z + h)], paving)
                else:  # 先踏面再踢面（下坡）
                    quad([W(s0, wl, z), W(s0, wr, z), W(s1, wr, z), W(s1, wl, z)], paving)
                    quad([W(s1, wl, z), W(s1, wr, z), W(s1, wr, z + h), W(s1, wl, z + h)], stone)
                z += h
    # 垛口（每 2.3 m 一個垛）
    acc = 0.0
    for i in range(len(pts) - 1):
        L = (Vector((*pts[i + 1], 0)) - Vector((*pts[i], 0))).length
        s = acc
        while s < L:
            u = s / L
            p = Vector((*pts[i], 0)).lerp(Vector((*pts[i + 1], 0)), u)
            nn = nrm[i].lerp(nrm[i + 1], u).normalized()
            zt = top[i] + (top[i + 1] - top[i]) * u + 1.15
            c = p + nn * (Wt / 2 - 0.31)
            ang = math.atan2(tang[i].y, tang[i].x)
            b.box_base(brick, (1.45, 0.62, 0.95), (c.x, c.y, zt - 0.25), rot=(0, 0, ang))
            s += 2.3
        acc = s - L

    # ------------------------------------------------------------------ 敵樓
    def arch_window(cx, cy, z, a_face, w=1.1, spring=1.45):
        """深色拱窗：a_face 為該面外法線方向角"""
        arc = list(reversed(b.arch_points(w, spring, "round", 8)))[1:-1]
        prof = [(-w / 2, 0), (w / 2, 0), (w / 2, spring)] + arc + [(-w / 2, spring)]
        M = Matrix.Translation((cx, cy, z)) @ Matrix.Rotation(a_face - math.pi / 2, 4, "Z")
        b.profile_wall(dark, prof, 0.4, M)
        # 淺色石框（窗下的窗台）
        b.box_base(stone, (w + 0.4, 0.5, 0.18), (cx, cy, z - 0.18), rot=(0, 0, a_face - math.pi / 2))

    def tower(i, hut):
        cx, cy = pts[i]
        ang = math.atan2(tang[i].y, tang[i].x)
        S = 10.6
        corners = [Vector((cx, cy, 0)) + Matrix.Rotation(ang, 3, "Z") @ Vector((sx * S / 2, sy * S / 2, 0)) for sx in (-1, 1) for sy in (-1, 1)]
        gl = min(height(c.x, c.y) for c in corners)
        gh = max(height(c.x, c.y) for c in corners)
        zf = max(top[i], gh + 3.0)
        b.box_base(stone, (S + 0.3, S + 0.3, gh + 1.8 - (gl - 5)), (cx, cy, gl - 5), rot=(0, 0, ang))
        b.box_base(brick, (S, S, zf + 4.6 - (gh + 1.8)), (cx, cy, gh + 1.8), rot=(0, 0, ang))
        # 拱窗：每面三個（沿牆兩面中間為拱門）
        for side in range(4):
            af = ang + side * math.pi / 2 - math.pi / 2
            nx, ny = math.cos(af), math.sin(af)
            tx, ty = -ny, nx
            for k in (-3.0, 0.0, 3.0):
                px, py = cx + nx * (S / 2 + 0.05) + tx * k, cy + ny * (S / 2 + 0.05) + ty * k
                along = side in (1, 3)
                if along and k == 0.0:
                    arch_window(px, py, zf, af, w=1.6, spring=2.0)
                else:
                    arch_window(px, py, zf + 1.1, af)
            # 下層（條石基座之上）的小窗，表現兩層磚造
            if zf - (gh + 1.8) > 3.2:
                for k in (-2.5, 2.5):
                    px, py = cx + nx * (S / 2 + 0.05) + tx * k, cy + ny * (S / 2 + 0.05) + ty * k
                    arch_window(px, py, zf - 2.6, af, w=0.8, spring=1.0)
        # 腰簷（層間線腳）與頂部垛口
        b.box_base(stone, (S + 0.6, S + 0.6, 0.45), (cx, cy, zf - 0.2), rot=(0, 0, ang))
        b.box_base(brick, (S + 0.7, S + 0.7, 0.5), (cx, cy, zf + 4.6), rot=(0, 0, ang))
        zt = zf + 5.1
        for side in range(4):
            af = ang + side * math.pi / 2
            ox, oy = math.cos(af - math.pi / 2), math.sin(af - math.pi / 2)
            tx, ty = math.cos(af), math.sin(af)
            b.box_base(brick, (S + 0.7, 0.6, 0.8), (cx + ox * (S / 2 + 0.05), cy + oy * (S / 2 + 0.05), zt), rot=(0, 0, af))
            for k in range(5):
                u = -S / 2 + 0.9 + k * (S - 1.8) / 4
                b.box_base(brick, (1.3, 0.6, 0.9), (cx + ox * (S / 2 + 0.05) + tx * u, cy + oy * (S / 2 + 0.05) + ty * u, zt + 0.8), rot=(0, 0, af))
        if hut:  # 樓櫓：磚砌小樓＋灰瓦頂（第二層）
            hs = 6.0
            b.box_base(brick, (hs, hs, 3.6), (cx, cy, zt), rot=(0, 0, ang))
            for side in range(4):
                af = ang + side * math.pi / 2 - math.pi / 2
                nx, ny = math.cos(af), math.sin(af)
                tx, ty = -ny, nx
                for k in (-1.4, 1.4):
                    arch_window(cx + nx * (hs / 2 + 0.05) + tx * k, cy + ny * (hs / 2 + 0.05) + ty * k, zt + 0.9, af, w=0.9, spring=1.2)
            b.hip_roof(roof_tile, hs, hs, 2.6, (cx, cy, zt + 3.6), overhang=0.8, upturn=0.3, rot_z=ang, sag=0.2)

    tower_idx = list(range(10, len(pts) - 5, 25)) + [2, len(pts) - 3]
    for n_, i in enumerate(sorted(set(tower_idx))):
        tower(i, hut=(n_ % 3 == 1))

    # ------------------------------------------------------------------ 遠方山脊上延伸的長城（簡化）
    rc = 535.0
    prev = None
    for k, th in enumerate([math.radians(232 + 1.15 * j) for j in range(88)]):
        x, y = rc * math.cos(th), rc * math.sin(th)
        z = height(x, y)
        cur = (Vector((x, y, z)), th)
        if prev:
            (p0, t0), (p1, t1) = prev, cur
            n0 = Vector((math.cos(t0), math.sin(t0), 0)) * 1.8
            n1 = Vector((math.cos(t1), math.sin(t1), 0)) * 1.8
            up = Vector((0, 0, 3.5))
            dn = Vector((0, 0, -4.0))
            quad([p0 + n0 + dn, p1 + n1 + dn, p1 + n1 + up, p0 + n0 + up], far_wall)
            quad([p0 + n0 + up, p1 + n1 + up, p1 - n1 + up, p0 - n0 + up], far_wall)
            quad([p0 - n0 + up, p1 - n1 + up, p1 - n1 + dn, p0 - n0 + dn], far_wall)
        if k % 9 == 4:
            b.box_base(far_wall, (7, 7, 11), (x, y, z - 5), rot=(0, 0, th))
        prev = cur

    # ------------------------------------------------------------------ 林木（樹冠團塊，嵌入林冠地表形成起伏）
    near = pts[::2]
    rng = b.rng
    step = 9.0
    nx_ = int(2 * 470 / step)
    for ix in range(nx_):
        for iy in range(nx_):
            x = -470 + (ix + rng.random()) * step
            y = -470 + (iy + rng.random()) * step
            r = math.hypot(x, y)
            if r > 470:
                continue
            # 相機側（+Y）前景較密
            p_keep = 0.5 if y > 100 else 0.32
            if rng.random() > p_keep:
                continue
            if any((x - px) ** 2 + (y - py) ** 2 < 10.0 ** 2 for px, py in near):
                continue
            # 一叢 2–3 個相連的樹冠
            mi = rng.choice(crowns)
            for k in range(rng.choice((2, 2, 3))):
                xx, yy = x + rng.uniform(-3, 3), y + rng.uniform(-3, 3)
                z = height(xx, yy)
                s = rng.uniform(3.5, 6.0)
                b.rock(mi if rng.random() < 0.6 else rng.choice(crowns), (s, s * rng.uniform(0.85, 1.15), s * 0.5),
                       (xx, yy, z + s * 0.05), rot=(0, 0, rng.uniform(0, TAU)), rough=0.35, subdiv=1,
                       seed=rng.randint(0, 99999), flat_bottom=False, round_=0.85)
    # 牆邊緊貼的灌木（較小）
    for i in range(0, len(pts), 3):
        for side in (-1, 1):
            if rng.random() < 0.55:
                continue
            o = side * rng.uniform(5.5, 9.0)
            p = V(i, o, 0)
            z = height(p.x, p.y)
            s = rng.uniform(2.5, 4.5)
            b.rock(rng.choice(crowns), (s, s, s * 0.7), (p.x, p.y, z + s * 0.1), rough=0.45, subdiv=1,
                   seed=rng.randint(0, 99999), flat_bottom=False, round_=0.7)
    _export(b, path)
