"""great_wall 萬里長城（金山嶺段）寫實模型（公尺）

- 場景依參考照（自高處俯瞰金山嶺）配置：前景右側長城沿陡峭稜線爬升到山頂後右轉，
  中景山脊上一段長城與敵樓，左側長城自山頂敵樓下降到鞍部再沿谷側蜿蜒，遠方山脊上可見細長的城牆
- 明長城：牆高約 6 m、頂寬約 5 m（步道約 4 m），外側垛口牆（垛口）約 1.8 m、內側宇牆約 1 m，
  灰褐色城磚、下部條石；陡坡處步道為階梯
- 敵樓：約 10 m 見方、兩層磚造（條石基座＋磚砌樓身），每面三個拱窗，頂部垛口，部分敵樓頂上有樓櫓
- 地形：沿長城的陡峭山脊、層層疊疊的遠山（頂點色做大氣透視：越遠越淡越藍灰）；
  植被為程式產生的林冠貼圖 × 頂點色（深淺、裸土、岩塊、霧化），再加上大量低面數的樹叢團塊
"""

import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import TAU, TEX, Builder, tinted_texture

# build.py 的 CAMS 格式：(目標點, 方位角, 仰角, 距離, 焦距)
CAMERA = ((0.0, 582.18, 34.85), 0.0, 14.0, 600.0, 30.0)

CAM = Vector((0.0, 0.0, 180.0))
PITCH = math.radians(14.0)
FOC = 1000 * 30 / 36  # 焦距（像素）
GEN = os.path.join(TEX, "_gen")


def img2world(px, py, depth):
    """參考照像素座標（1000 寬、上緣對齊）＋前向距離 → 世界座標"""
    xc = (px - 500) / FOC * depth
    yc = (375 - py) / FOC * depth
    sp, cp = math.sin(PITCH), math.cos(PITCH)
    return Vector((xc, yc * sp + depth * cp, CAM.z + yc * cp - depth * sp))


# ====================================================================== numpy 雜訊
def _hash(ix, iy, seed):
    n = (ix * 73856093) ^ (iy * 19349663) ^ (seed * 83492791 + 12345)
    n = (n ^ (n >> 13)) * 1274126177
    n = n ^ (n >> 16)
    return (n & 0xFFFFFF).astype(np.float64) / float(0xFFFFFF)


def vnoise(x, y, seed=0):
    xi = np.floor(x).astype(np.int64)
    yi = np.floor(y).astype(np.int64)
    xf, yf = x - xi, y - yi
    u = xf * xf * (3 - 2 * xf)
    v = yf * yf * (3 - 2 * yf)
    a, b = _hash(xi, yi, seed), _hash(xi + 1, yi, seed)
    c, d = _hash(xi, yi + 1, seed), _hash(xi + 1, yi + 1, seed)
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v


def fbm(x, y, octaves=5, seed=0):
    s, w, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        s = s + w * (vnoise(x * 2 ** o, y * 2 ** o, seed + o) * 2 - 1)
        tot += w
        w *= 0.5
    return s / tot


def ridged(x, y, octaves=5, seed=0):
    s, w, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        n = 1 - np.abs(vnoise(x * 2 ** o, y * 2 ** o, seed + 7 * o) * 2 - 1)
        s = s + w * n * n
        tot += w
        w *= 0.5
    return s / tot


# ====================================================================== 程式產生的貼圖
def _canopy_textures():
    """灌叢與小喬木林冠的俯視貼圖（30 m 一循環）：大量大小不一、互相重疊的樹冠，
    每個樹冠有球面明暗（受光自畫面右下，與預覽太陽方向一致）與葉叢顆粒，冠間為深色空隙；
    低彩度（色相由頂點色決定），並輸出法線貼圖；可無縫重複"""
    out_d = os.path.join(GEN, "gw_canopy4_diff.jpg")
    out_n = os.path.join(GEN, "gw_canopy4_nor.jpg")
    if os.path.exists(out_d) and os.path.exists(out_n):
        return out_d, out_n
    from PIL import Image

    os.makedirs(GEN, exist_ok=True)
    N = 1024
    rnd = np.random.default_rng(7)
    H = np.zeros((N, N), np.float32)
    C = np.zeros((N, N, 3), np.float32)
    C[:] = (50, 52, 48)
    # 葉叢顆粒（多尺度、可重複）
    grain = np.zeros((N, N), np.float32)
    for sc, w in ((8, 0.5), (24, 0.3), (64, 0.2)):
        g = rnd.uniform(0, 1, (N // sc, N // sc)).astype(np.float32)
        g = np.array(Image.fromarray((g * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC), np.float32) / 255
        grain += w * g
    L = np.array([0.45, 0.45, 0.77])
    pal = np.array([(228, 228, 222), (214, 218, 210), (238, 236, 228), (204, 208, 200), (242, 240, 230), (220, 222, 214)], np.float32)
    for _ in range(4200):
        cx, cy = rnd.uniform(0, N, 2)
        r = rnd.uniform(14, 40) if rnd.random() < 0.85 else rnd.uniform(40, 64)
        z0 = rnd.uniform(0, 16)
        col = pal[rnd.integers(len(pal))] * rnd.uniform(0.85, 1.05)
        R = int(r) + 2
        ys = (np.arange(int(cy) - R, int(cy) + R + 1)) % N
        xs = (np.arange(int(cx) - R, int(cx) + R + 1)) % N
        dy = (np.arange(int(cy) - R, int(cy) + R + 1) - cy)[:, None]
        dx = (np.arange(int(cx) - R, int(cx) + R + 1) - cx)[None, :]
        ang = np.arctan2(dy, dx)
        rr = r * (1 + 0.16 * np.sin(ang * rnd.integers(4, 9) + rnd.uniform(0, 6)) + 0.08 * np.sin(ang * 15 + rnd.uniform(0, 6)))
        d2 = (dx * dx + dy * dy) / (rr * rr)
        inside = d2 < 1
        nz = np.sqrt(np.clip(1 - d2, 0.0, 1))
        h = nz * r * 0.7 + z0
        sub = H[np.ix_(ys, xs)]
        m = inside & (h > sub)
        nx, ny = dx / rr, dy / rr
        lam = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
        gw = grain[np.ix_(ys, xs)]
        f = (0.38 + 0.62 * lam) * (0.72 + 0.5 * gw) * (0.75 + 0.25 * nz)
        newc = col[None, None, :] * f[..., None]
        subc = C[np.ix_(ys, xs)]
        subc[m] = newc[m]
        sub[m] = h[m]
        C[np.ix_(ys, xs)] = subc
        H[np.ix_(ys, xs)] = sub
    C *= rnd.uniform(0.88, 1.08, (N, N, 1)).astype(np.float32)
    Image.fromarray(np.clip(C, 0, 255).astype(np.uint8)).save(out_d, quality=84)
    Hs = H + grain * 6
    gx = (np.roll(Hs, -1, 1) - np.roll(Hs, 1, 1)) * 0.5
    gy = -(np.roll(Hs, -1, 0) - np.roll(Hs, 1, 0)) * 0.5
    k = 0.25
    n = np.dstack([-gx * k, -gy * k, np.ones_like(H)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    Image.fromarray(((n + 1) * 127.5).astype(np.uint8)).resize((512, 512), Image.LANCZOS).save(out_n, quality=86)
    return out_d, out_n


class _GB(Builder):
    planar = set()

    def _uv(self):
        """植被（地形與樹叢）一律用俯視平面投影，使相鄰面共用 UV、頂點不被拆分；其他面用方塊投影"""
        uv = self.bm.loops.layers.uv.verify()
        for f in self.bm.faces:
            mi = f.material_index
            tile = self.tiles[mi] if mi < len(self.tiles) else 1.0
            if mi in self.planar:
                for l in f.loops:
                    c = l.vert.co
                    l[uv].uv = (c.x / tile, c.y / tile)
                continue
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                c = l.vert.co
                if ax == 2:
                    u, v = c.x, c.y
                elif ax == 0:
                    u, v = c.y, c.z
                else:
                    u, v = c.x, c.z
                l[uv].uv = (u / tile, v / tile)

    def ptex(self, name, tex_id, tile, tint=None, gain=1.0, rough=0.85, normal=1.0, nsize=512, dsize=1024):
        """PBR 貼圖材質（縮小的法線貼圖、固定粗糙度）以控制 GLB 大小"""
        from PIL import Image

        os.makedirs(GEN, exist_ok=True)
        diff = tinted_texture(tex_id, tint, gain)
        if dsize < 1024:
            dp = os.path.join(GEN, f"{os.path.splitext(os.path.basename(diff))[0]}_{dsize}.jpg")
            if not os.path.exists(dp):
                Image.open(diff).resize((dsize, dsize), Image.LANCZOS).save(dp, quality=84)
            diff = dp
        npth = None
        if normal > 0:
            npth = os.path.join(GEN, f"{tex_id}_nor{nsize}.jpg")
            if not os.path.exists(npth):
                Image.open(os.path.join(TEX, tex_id, "nor.jpg")).resize((nsize, nsize), Image.LANCZOS).save(npth, quality=85)
        return self.img_mat(name, diff, npth, tile, rough, normal)

    def img_mat(self, name, diff, nor, tile, rough, strength=1.0, vcol=False):
        m = bpy.data.materials.new(f"{self.name}_{name}")
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        img = nt.nodes.new("ShaderNodeTexImage")
        img.image = bpy.data.images.load(diff, check_existing=True)
        if vcol:
            vc = nt.nodes.new("ShaderNodeVertexColor")
            vc.layer_name = "Col"
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs[0].default_value = 1.0
            nt.links.new(img.outputs["Color"], mix.inputs[6])
            nt.links.new(vc.outputs["Color"], mix.inputs[7])
            nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
        else:
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
        return self._register(name, m, tile)


# ====================================================================== 萬里長城（金山嶺段）
def great_wall(path):
    b = _GB("GreatWall", seed=21)
    bm = b.bm
    col_layer = bm.verts.layers.color.new("Col")
    dome_layer = bm.verts.layers.float_vector.new("dome_n")  # 樹叢的圓頂法線（輸出時寫入自訂法線）
    cd, cn = _canopy_textures()
    veg = b.img_mat("vegetation", cd, cn, 30.0, 0.95, 1.0, vcol=True)
    b.planar = {veg}
    brick = b.ptex("brick", "brick_wall_006", 3.6, tint="#8c7d6b", normal=0.9)
    brick_far = b.color("brick_far", "#9a948a", rough=0.9)
    far_mats = [b.color("far_wall0", "#7e7d77", rough=0.95), b.color("far_wall1", "#6f777b", rough=0.95), b.color("far_wall2", "#66717c", rough=0.95)]
    stone = b.ptex("stone", "large_sandstone_blocks", 3.0, tint="#9e9585", rough=0.88, normal=0, dsize=512)
    paving = b.ptex("walkway", "white_sandstone_bricks_03", 2.0, tint="#9b9384", rough=0.9, normal=0, dsize=512)
    dark = b.color("opening", "#1f1c19", rough=1.0)
    roof_tile = b.ptex("roof_tile", "grey_roof_tiles", 1.5, tint="#5b5c5e", rough=0.7, normal=0, dsize=512)
    rng = b.rng

    # ------------------------------------------------------------------ 長城路線（參考照像素座標＋距離）
    def smooth_path(ctrl, step=2.0):
        """Catmull-Rom 平滑後依水平距離重新取樣"""
        P = [img2world(*c) for c in ctrl]
        pts = []
        for i in range(len(P) - 1):
            p0, p1, p2, p3 = P[max(0, i - 1)], P[i], P[i + 1], P[min(len(P) - 1, i + 2)]
            for k in range(12):
                t = k / 12
                t2, t3 = t * t, t * t * t
                pts.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
        pts.append(P[-1])
        out = [pts[0]]
        acc = 0.0
        for a, c in zip(pts, pts[1:]):
            L = (Vector((c.x - a.x, c.y - a.y))).length
            acc += L
            if acc >= step:
                out.append(c)
                acc = 0.0
        if (out[-1] - pts[-1]).length > 0.5:
            out.append(pts[-1])
        return out

    WALL_A = [(1060, 590, 158), (1000, 532, 176), (900, 482, 200), (812, 440, 230), (762, 410, 250), (746, 375, 268),
              (742, 300, 310), (745, 240, 350), (752, 206, 376), (800, 191, 402), (852, 184, 432), (905, 186, 470)]
    WALL_B = [(700, 270, 630), (655, 266, 640), (590, 262, 652), (520, 258, 662), (452, 254, 672), (420, 260, 678), (392, 266, 684)]
    WALL_C = [(176, 250, 850), (173, 280, 820), (164, 312, 790), (128, 336, 770), (100, 356, 752), (90, 384, 736), (110, 398, 724),
              (170, 401, 716), (232, 395, 712), (275, 362, 714), (297, 334, 720)]
    walls = {"A": smooth_path(WALL_A), "B": smooth_path(WALL_B), "C": smooth_path(WALL_C)}
    H_WALL = {"A": 6.5, "B": 6.0, "C": 6.0}

    # ------------------------------------------------------------------ 地形高度（numpy 向量化）
    def seg_query(X, Y, P):
        """點到折線的最近距離與參數（區段索引＋t）"""
        A = P[:-1]
        B = P[1:]
        E = B - A
        L2 = np.maximum((E ** 2).sum(1), 1e-9)
        best_d = np.full(X.shape, 1e18)
        best_i = np.zeros(X.shape, np.int64)
        best_t = np.zeros(X.shape)
        for k in range(0, len(A), 64):
            a, e, l2 = A[k:k + 64], E[k:k + 64], L2[k:k + 64]
            t = np.clip(((X[:, None] - a[None, :, 0]) * e[None, :, 0] + (Y[:, None] - a[None, :, 1]) * e[None, :, 1]) / l2[None, :], 0, 1)
            dx = a[None, :, 0] + e[None, :, 0] * t - X[:, None]
            dy = a[None, :, 1] + e[None, :, 1] * t - Y[:, None]
            d2 = dx * dx + dy * dy
            j = d2.argmin(1)
            dj = d2[np.arange(len(X)), j]
            m = dj < best_d
            best_d = np.where(m, dj, best_d)
            best_i = np.where(m, j + k, best_i)
            best_t = np.where(m, t[np.arange(len(X)), j], best_t)
        return np.sqrt(best_d), best_i, best_t

    feats = []  # (P(K,2), crest(K), slope, w0, is_wall)
    for key, pts in walls.items():
        P = np.array([(p.x, p.y) for p in pts])
        crest = np.array([p.z - H_WALL[key] for p in pts])
        # 山脊向兩端延伸（長城所在稜線不在路線端點突然中斷）
        ext = []
        ends = {"A": (True, True), "B": (True, False), "C": (True, False)}[key]
        for (end, sgn), use in zip(((0, -1), (-1, 1)), ends):
            d = P[end] - P[end + (1 if end == 0 else -1)]
            d = d / np.linalg.norm(d)
            ext.append([(P[end] + d * s, crest[end] - 0.35 * s) for s in ((40, 90, 160) if use else (6, 12, 18))])
        P = np.vstack([np.array([e[0] for e in reversed(ext[0])]), P, np.array([e[0] for e in ext[1]])])
        crest = np.concatenate([[e[1] for e in reversed(ext[0])], crest, [e[1] for e in ext[1]]])
        feats.append((P, crest, {"A": 0.78, "B": 0.62, "C": 0.55}[key], 9.0, True))

    # 遠方層層山脊（稜線在平面上蜿蜒，稜高起伏）
    def range_line(y0, amp, freq, phase, h0, hamp, seed, x0=-1500, x1=1500, n=220):
        xs = np.linspace(x0, x1, n)
        ys = y0 + amp * np.sin(xs / freq + phase) + 0.5 * amp * np.sin(xs / (freq * 0.43) + 2 * phase)
        hn = 0.6 * ridged(xs / 330.0, np.full(n, seed * 3.1), 3, seed) + 0.4 * (fbm(xs / 95.0, np.full(n, seed * 1.7), 4, seed + 5) * 0.5 + 0.5)
        hs = h0 + hamp * (hn - 0.45) * 2.4 + 0.3 * hamp * np.sin(xs / 610 + seed)
        return np.stack([xs, ys], 1), hs

    ranges = [
        range_line(1080, 70, 260, 0.3, 105, 55, 3),
        range_line(1360, 80, 300, 1.4, 165, 70, 5),
        range_line(1680, 90, 340, 2.2, 230, 75, 9),
        range_line(2020, 60, 420, 0.9, 320, 80, 13),
    ]
    for (P, hs), sl in zip(ranges, (0.95, 0.9, 0.85, 0.8)):
        feats.append((P, hs, sl, 14.0, False))
    # 左側谷地（左方長城下降後沿谷側蜿蜒）
    valley = np.array([(-520.0, 760.0, -28.0), (-380.0, 720.0, -24.0), (-260.0, 690.0, -22.0), (-170.0, 640.0, -16.0),
                       (-150.0, 520.0, -8.0), (-200.0, 380.0, 0.0), (-330.0, 300.0, 4.0)])
    valley2 = np.array([(-480.0, 560.0, -6.0), (-300.0, 520.0, -10.0), (-150.0, 560.0, -12.0), (-40.0, 600.0, -8.0)])
    valley3 = np.array([(-470.0, 655.0, -36.0), (-330.0, 645.0, -33.0), (-200.0, 628.0, -28.0), (-110.0, 600.0, -20.0)])

    def height(X, Y, with_feat=False):
        X = np.asarray(X, np.float64)
        Y = np.asarray(Y, np.float64)
        dcam = np.hypot(X, Y)
        far = np.clip((Y - 250) / 1500, 0, 1)
        # 基底：山體支脈（ridged noise，遠處較高）
        hb = -18 + (55 + 120 * far) * ridged(X / 520 + 3.3, Y / 330 + 1.7, 5, 1) + 40 * fbm(X / 900, Y / 900, 3, 2) + 60 * far
        # 前景左側相機所在山體
        r = np.hypot((X + 330) / 1.2, Y - 90)
        hb = np.maximum(hb, 72 * np.clip(1 - r / 260, 0, 1) ** 1.4 + 6 * fbm(X / 60, Y / 60, 3, 4))
        dv, iv, tv = seg_query(X, Y, valley[:, :2])
        vf = valley[iv, 2] + (valley[np.minimum(iv + 1, len(valley) - 1), 2] - valley[iv, 2]) * tv
        hb = np.minimum(hb, vf + 0.5 * dv + 8 * fbm(X / 70, Y / 70, 3, 29) * np.clip(dv / 40, 0, 1))
        dv, iv, tv = seg_query(X, Y, valley2[:, :2])
        vf = valley2[iv, 2] + (valley2[np.minimum(iv + 1, len(valley2) - 1), 2] - valley2[iv, 2]) * tv
        hb = np.minimum(hb, vf + 0.42 * dv + 6 * fbm(X / 70, Y / 70, 3, 33) * np.clip(dv / 40, 0, 1))
        dv, iv, tv = seg_query(X, Y, valley3[:, :2])
        vf = valley3[iv, 2] + (valley3[np.minimum(iv + 1, len(valley3) - 1), 2] - valley3[iv, 2]) * tv
        hb = np.minimum(hb, vf + 0.38 * dv)
        h = hb
        wall_caps = []
        for P, crest, slope, w0, is_wall in feats:
            d, i, t = seg_query(X, Y, P)
            c = crest[i] + (crest[np.minimum(i + 1, len(crest) - 1)] - crest[i]) * t
            sl = slope * (1 + 0.35 * fbm(X / 140, Y / 140, 3, 11 if is_wall else 17))
            hr = c - sl * (np.sqrt(d * d + w0 * w0) - w0)
            hr += np.clip(d / 30, 0, 1) * 10 * fbm(X / 80, Y / 80, 4, 23)  # 坡面上的沖溝與小支脈
            k = 14.0
            h = (h + hr + np.sqrt((h - hr) ** 2 + k * k)) / 2  # 平滑取大
            if is_wall:
                wall_caps.append((d, c))
        for d, c in wall_caps:
            cap = c + np.maximum(0, d - 4.0) * 0.9
            h = np.minimum(h, np.where(d < 4.0, c - 0.15, cap))
        return h

    # ------------------------------------------------------------------ 地形網格（以相機正下方為中心的極座標網格，相機前方較密）
    XMIN, XMAX, YMIN, YMAX = -1350.0, 1350.0, -260.0, 2200.0

    def r_bound(th):
        c, s = math.cos(th), math.sin(th)
        ts = []
        if c > 1e-9:
            ts.append(XMAX / c)
        if c < -1e-9:
            ts.append(XMIN / c)
        if s > 1e-9:
            ts.append(YMAX / s)
        if s < -1e-9:
            ts.append(YMIN / s)
        return min(ts)

    angs = []
    a = math.radians(90 - 40)
    while a < math.radians(90 + 40):
        angs.append(a)
        a += math.radians(0.45)
    a2 = math.radians(90 + 40)
    while a2 < math.radians(90 - 40) + TAU - 1e-6:
        angs.append(a2)
        a2 += math.radians(3.5)
    angs = sorted(set(round(x, 6) for x in angs))
    NA = len(angs)
    NRING = 190
    R0 = 30.0
    th = np.array(angs)
    Rb = np.array([r_bound(t) for t in angs])
    tk = np.linspace(0, 1, NRING + 1)
    RR = R0 * (Rb[None, :] / R0) ** tk[:, None]
    GX = RR * np.cos(th)[None, :]
    GY = RR * np.sin(th)[None, :]
    GZ = height(GX.ravel(), GY.ravel()).reshape(GX.shape)
    # 相機下方中心點
    zc = float(height(np.array([0.0]), np.array([0.0]))[0])

    # ------------------------------------------------------------------ 頂點色：植被深淺、裸土、岩塊、大氣透視
    def veg_colors(X, Y, Z, dzdx, dzdy, curv):
        slope = np.hypot(dzdx, dzdy)
        n1 = fbm(X / 160, Y / 160, 4, 31)
        n2 = fbm(X / 45, Y / 45, 3, 37)
        deep = np.array([0.16, 0.29, 0.10])
        mid = np.array([0.25, 0.40, 0.13])
        yel = np.array([0.36, 0.49, 0.17])
        t = np.clip(0.5 + 0.9 * n1 + 0.25 * n2 + 0.02 * curv, 0, 1)
        col = np.where(t[:, None] < 0.5, deep + (mid - deep) * (t[:, None] / 0.5), mid + (yel - mid) * ((t[:, None] - 0.5) / 0.5))
        # 背光的沖溝較暗、稜線較亮
        col *= np.clip(1 + 0.02 * curv, 0.62, 1.18)[:, None]
        # 裸土（黃褐小斑塊、小徑）與陡坡岩塊
        bare = np.clip((fbm(X / 26, Y / 26, 4, 41) - 0.22) * 4, 0, 1) * np.clip((slope - 0.2) * 2, 0, 1) * 0.9
        rockm = np.clip((slope - 1.05) * 2.5, 0, 1) * np.clip(fbm(X / 35, Y / 35, 3, 43) * 3 + 0.6, 0, 1)
        col = col * (1 - bare[:, None]) + np.array([0.66, 0.58, 0.46]) * bare[:, None]
        col = col * (1 - rockm[:, None] * 0.8) + np.array([0.56, 0.53, 0.48]) * rockm[:, None] * 0.8
        # 大氣透視
        d = np.sqrt(X * X + Y * Y + (Z - CAM.z) ** 2)
        a = 1 - np.exp(-((d / 1150.0) ** 1.8))
        u = np.clip((d - 900) / 1100, 0, 1)[:, None]
        haze = np.array([0.20, 0.40, 0.38]) * (1 - u) + np.array([0.21, 0.29, 0.44]) * u
        col = col * (1 - a[:, None]) + haze * a[:, None]
        return np.clip(col, 0, 1)

    def grad(X, Y, e=2.0):
        hx = (height(X + e, Y) - height(X - e, Y)) / (2 * e)
        hy = (height(X, Y + e) - height(X, Y - e)) / (2 * e)
        return hx, hy

    def curvature(X, Y, e=12.0):
        h0 = height(X, Y)
        return (height(X + e, Y) + height(X - e, Y) + height(X, Y + e) + height(X, Y - e) - 4 * h0) / (e * e) * -400.0

    Xf, Yf, Zf = GX.ravel(), GY.ravel(), GZ.ravel()
    dzdx, dzdy = grad(Xf, Yf)
    curv = curvature(Xf, Yf)
    COL = veg_colors(Xf, Yf, Zf, dzdx, dzdy, curv).reshape(GX.shape + (3,))

    # 建立地形
    grid = []
    for i in range(NRING + 1):
        row = []
        for j in range(NA):
            v = bm.verts.new((GX[i, j], GY[i, j], GZ[i, j]))
            c = COL[i, j]
            v[col_layer] = (float(c[0]), float(c[1]), float(c[2]), 1.0)
            row.append(v)
        grid.append(row)
    center = bm.verts.new((0, 0, zc))
    c0 = COL[0].mean(0)
    center[col_layer] = (float(c0[0]), float(c0[1]), float(c0[2]), 1.0)

    def face(vs, mi, smooth=False):
        f = bm.faces.new(vs)
        f.material_index = mi
        f.smooth = smooth
        return f

    for j in range(NA):
        k = (j + 1) % NA
        face([center, grid[0][j], grid[0][k]], veg, True)
    for i in range(NRING):
        for j in range(NA):
            k = (j + 1) % NA
            face([grid[i][j], grid[i + 1][j], grid[i + 1][k], grid[i][k]], veg, True)
    # 地形外緣側面
    edge = grid[-1]
    bot = [bm.verts.new((v.co.x, v.co.y, -60.0)) for v in edge]
    for v in bot:
        v[col_layer] = (0.35, 0.33, 0.3, 1.0)
    for j in range(NA):
        k = (j + 1) % NA
        face([edge[k], edge[j], bot[j], bot[k]], veg)
    face(list(reversed(bot)), veg)

    # ------------------------------------------------------------------ 城牆（連續牆體、條石基礎、垛口、宇牆、階梯步道）
    def quad(vs, mi):
        return face([bm.verts.new(v) for v in vs], mi)

    def build_wall(pts, Htop_off, near=True, outer_sign=1):
        n = len(pts)
        P = [Vector((p.x, p.y, 0)) for p in pts]
        top = [p.z for p in pts]
        # 步道高度平滑
        top = [sum(top[max(0, i - 2):i + 3]) / len(top[max(0, i - 2):i + 3]) for i in range(n)]
        G = height(np.array([p.x for p in P]), np.array([p.y for p in P]))
        tang, nrm = [], []
        for i in range(n):
            a, c = P[max(0, i - 1)], P[min(n - 1, i + 1)]
            t = (c - a).normalized()
            tang.append(t)
            nrm.append(Vector((-t.y, t.x, 0)) * outer_sign)
        Wt, Wb = 5.0, 6.2
        mtl = brick if near else brick_far
        mts = stone if near else brick_far
        mtp = paving if near else brick_far

        def V(i, off, z):
            return P[i] + nrm[i] * off + Vector((0, 0, z))

        base = [min(G[max(0, i - 1):i + 2]) - 5.0 for i in range(n)]
        foot = [G[i] + 1.6 for i in range(n)]
        for i in range(n - 1):
            for sgn in (1, -1):
                fo0 = (foot[i] - base[i]) / max(1e-3, top[i] - base[i])
                fo1 = (foot[i + 1] - base[i + 1]) / max(1e-3, top[i + 1] - base[i + 1])
                om0 = Wb / 2 + (Wt / 2 - Wb / 2) * min(1, max(0, fo0))
                om1 = Wb / 2 + (Wt / 2 - Wb / 2) * min(1, max(0, fo1))
                a = [V(i, sgn * Wb / 2, base[i]), V(i + 1, sgn * Wb / 2, base[i + 1]), V(i + 1, sgn * om1, foot[i + 1]), V(i, sgn * om0, foot[i])]
                c = [V(i, sgn * om0, foot[i]), V(i + 1, sgn * om1, foot[i + 1]), V(i + 1, sgn * Wt / 2, top[i + 1]), V(i, sgn * Wt / 2, top[i])]
                quad(a if sgn > 0 else list(reversed(a)), mts)
                quad(c if sgn > 0 else list(reversed(c)), mtl)
            # 外側垛口牆（連續下段 1.15 m）與內側宇牆（1.0 m）
            for o_out, o_in, hh in ((Wt / 2, Wt / 2 - 0.6, 1.15), (-Wt / 2 + 0.45, -Wt / 2, 1.0)):
                zt0, zt1 = top[i] + hh, top[i + 1] + hh
                zb0, zb1 = top[i] - 0.05, top[i + 1] - 0.05
                quad([V(i, o_out, zb0), V(i + 1, o_out, zb1), V(i + 1, o_out, zt1), V(i, o_out, zt0)], mtl)
                quad([V(i, o_out, zt0), V(i + 1, o_out, zt1), V(i + 1, o_in, zt1), V(i, o_in, zt0)], mtl)
                quad([V(i, o_in, zt0), V(i + 1, o_in, zt1), V(i + 1, o_in, zb1), V(i, o_in, zb0)], mtl)
            # 步道：坡度大時為階梯
            dt = top[i + 1] - top[i]
            L = (P[i + 1] - P[i]).length
            ns = min(12, int(abs(dt) / 0.28)) if abs(dt) / max(L, 1e-3) > 0.12 else 0
            wl, wr = -Wt / 2 + 0.45, Wt / 2 - 0.6
            if ns < 1:
                quad([V(i, wl, top[i]), V(i + 1, wl, top[i + 1]), V(i + 1, wr, top[i + 1]), V(i, wr, top[i])], mtp)
            else:
                h = dt / ns
                z = top[i]

                def W(s, o, zz):
                    p = P[i].lerp(P[i + 1], s) + nrm[i].lerp(nrm[i + 1], s).normalized() * o
                    return Vector((p.x, p.y, zz))
                for k in range(ns):
                    s0, s1 = k / ns, (k + 1) / ns
                    if dt > 0:
                        quad([W(s0, wl, z), W(s0, wr, z), W(s0, wr, z + h), W(s0, wl, z + h)], mts)
                        quad([W(s0, wl, z + h), W(s0, wr, z + h), W(s1, wr, z + h), W(s1, wl, z + h)], mtp)
                    else:
                        quad([W(s0, wl, z), W(s0, wr, z), W(s1, wr, z), W(s1, wl, z)], mtp)
                        quad([W(s1, wl, z), W(s1, wr, z), W(s1, wr, z + h), W(s1, wl, z + h)], mts)
                    z += h
        # 垛（每 2.2 m 一個，寬 1.6 m、高 0.75 m）
        if near:
            acc = 0.0
            for i in range(n - 1):
                L = (P[i + 1] - P[i]).length
                s = acc
                while s < L:
                    u = s / L
                    p = P[i].lerp(P[i + 1], u)
                    nn = nrm[i].lerp(nrm[i + 1], u).normalized()
                    zt = top[i] + (top[i + 1] - top[i]) * u + 1.15
                    c = p + nn * (Wt / 2 - 0.3)
                    ang = math.atan2(tang[i].y, tang[i].x)
                    b.box_base(mtl, (1.6, 0.64, 0.8), (c.x, c.y, zt - 0.05), rot=(0, 0, ang))
                    s += 2.2
                acc = s - L
        # 牆端封口（斷面多邊形）
        for i, sg in ((0, -1), (n - 1, 1)):
            prof = [(-Wb / 2, base[i]), (Wb / 2, base[i]), (Wt / 2, top[i]), (Wt / 2, top[i] + 1.15), (Wt / 2 - 0.6, top[i] + 1.15),
                    (Wt / 2 - 0.6, top[i]), (-Wt / 2 + 0.45, top[i]), (-Wt / 2 + 0.45, top[i] + 1.0), (-Wt / 2, top[i] + 1.0)]
            vs = [V(i, o, z) for o, z in prof]
            face([bm.verts.new(v) for v in (vs if sg > 0 else list(reversed(vs)))], mts)
        return P, top, tang, nrm, G

    # ------------------------------------------------------------------ 敵樓
    def arch_window(cx, cy, z, a_face, w=1.0, spring=1.3, depth=0.3):
        arc = list(reversed(b.arch_points(w, spring, "round", 8)))[1:-1]
        prof = [(-w / 2, 0), (w / 2, 0), (w / 2, spring)] + arc + [(-w / 2, spring)]
        M = Matrix.Translation((cx, cy, z)) @ Matrix.Rotation(a_face - math.pi / 2, 4, "Z")
        b.profile_wall(dark, prof, depth, M)

    def tower(p, ang, ztop, hut=False, S=10.5, near=True):
        """p：中心（平面）、ang：沿牆方向、ztop：步道高度"""
        mtl = brick if near else brick_far
        mts = stone if near else brick_far
        corners = [p + Matrix.Rotation(ang, 3, "Z") @ Vector((sx * S / 2, sy * S / 2, 0)) for sx in (-1, 1) for sy in (-1, 1)]
        gz = height(np.array([c.x for c in corners]), np.array([c.y for c in corners]))
        gl, gh = float(gz.min()), float(gz.max())
        z_floor = ztop  # 樓內地面與步道同高
        z_body = ztop + 4.8
        b.box_base(mts, (S + 0.4, S + 0.4, max(1.0, gh + 2.2 - (gl - 6))), (p.x, p.y, gl - 6), rot=(0, 0, ang))
        b.box_base(mtl, (S, S, z_body - (gh + 2.2)), (p.x, p.y, gh + 2.2), rot=(0, 0, ang))
        for side in range(4):
            af = ang + side * math.pi / 2 - math.pi / 2
            nx, ny = math.cos(af), math.sin(af)
            tx, ty = -ny, nx
            for k in (-3.0, 0.0, 3.0):
                px, py = p.x + nx * (S / 2 + 0.02) + tx * k, p.y + ny * (S / 2 + 0.02) + ty * k
                if side in (1, 3) and k == 0.0:
                    arch_window(px, py, z_floor, af, w=1.5, spring=1.9)
                else:
                    arch_window(px, py, z_floor + 1.1, af)
            if z_floor - (gh + 2.2) > 3.5:  # 下層小窗（兩層樓）
                for k in (-2.4, 2.4):
                    arch_window(p.x + nx * (S / 2 + 0.02) + tx * k, p.y + ny * (S / 2 + 0.02) + ty * k, z_floor - 2.8, af, w=0.75, spring=0.95)
        # 層間線腳、頂部平台與垛口
        b.box_base(mts, (S + 0.5, S + 0.5, 0.4), (p.x, p.y, z_floor - 0.35), rot=(0, 0, ang))
        b.box_base(mtl, (S + 0.6, S + 0.6, 0.45), (p.x, p.y, z_body), rot=(0, 0, ang))
        zt = z_body + 0.45
        for side in range(4):
            af = ang + side * math.pi / 2
            ox, oy = math.cos(af - math.pi / 2), math.sin(af - math.pi / 2)
            tx, ty = math.cos(af), math.sin(af)
            ln_ = S + 0.6 if side % 2 == 0 else S - 0.52  # 兩側較短，轉角不重疊
            b.box_base(mtl, (ln_, 0.55, 0.8), (p.x + ox * (S / 2 + 0.02), p.y + oy * (S / 2 + 0.02), zt), rot=(0, 0, af))
            for k in range(5):
                u = -S / 2 + 0.9 + k * (S - 1.8) / 4
                b.box_base(mtl, (1.3, 0.55, 0.8), (p.x + ox * (S / 2 + 0.02) + tx * u, p.y + oy * (S / 2 + 0.02) + ty * u, zt + 0.8), rot=(0, 0, af))
        if hut:
            hs = 5.6
            b.box_base(mtl, (hs, hs, 3.4), (p.x, p.y, zt), rot=(0, 0, ang))
            for side in range(4):
                af = ang + side * math.pi / 2 - math.pi / 2
                nx, ny = math.cos(af), math.sin(af)
                arch_window(p.x + nx * (hs / 2 + 0.02), p.y + ny * (hs / 2 + 0.02), zt + 0.8, af, w=0.9, spring=1.2)
            b.hip_roof(roof_tile, hs, hs, 2.4, (p.x, p.y, zt + 3.4), overhang=0.7, upturn=0.25, rot_z=ang, sag=0.2)

    near_pts = []
    for key, pts in walls.items():
        P, top, tang, nrm, G = build_wall(pts, 0.0, near=(key == "A" or key == "B"), outer_sign=1 if key != "A" else -1)
        near_pts += [(p.x, p.y) for p in P]
        n = len(P)
        # 敵樓位置（依參考照）
        if key == "A":
            idx = [min(range(n), key=lambda i: (P[i] - img2world(762, 410, 250).to_2d().to_3d()).length),
                   min(range(n), key=lambda i: (P[i] - img2world(752, 206, 376).to_2d().to_3d()).length),
                   min(range(n), key=lambda i: (P[i] - img2world(852, 184, 432).to_2d().to_3d()).length)]
            huts = (False, False, True)
        elif key == "B":
            idx = [n - 2, n // 3]
            huts = (True, False)
        else:
            idx = [1, min(range(n), key=lambda i: (P[i] - img2world(128, 336, 770).to_2d().to_3d()).length), n - 2]
            huts = (False, False, False)
        for i, hut in zip(idx, huts):
            ang = math.atan2(tang[i].y, tang[i].x)
            tower(P[i], ang, top[i], hut=hut, near=(key != "C"))

    # ------------------------------------------------------------------ 遠方山脊上的長城（沿稜線、簡化斷面）
    def far_wall(rng_idx, x0, x1, w=4.5, hgt=4.5, every=11):
        mfw = far_mats[min(rng_idx, 2)]
        P, hs = ranges[rng_idx]
        sel = (P[:, 0] >= x0) & (P[:, 0] <= x1)
        Q = P[sel]
        if len(Q) < 2:
            return
        # 加密
        dense = []
        for a, c in zip(Q, Q[1:]):
            for k in range(4):
                dense.append(a + (c - a) * k / 4)
        dense.append(Q[-1])
        Q = np.array(dense)
        Zg = height(Q[:, 0], Q[:, 1])
        prev = None
        for k, (q, zg) in enumerate(zip(Q, Zg)):
            cur = Vector((q[0], q[1], zg))
            if prev is not None:
                t = (cur - prev).to_2d().normalized()
                nn = Vector((-t.y, t.x, 0)) * (w / 2)
                up = Vector((0, 0, hgt))
                dn = Vector((0, 0, -5.0))
                quad([prev + nn + dn, cur + nn + dn, cur + nn + up, prev + nn + up], mfw)
                quad([prev + nn + up, cur + nn + up, cur - nn + up, prev - nn + up], mfw)
                quad([prev - nn + up, cur - nn + up, cur - nn + dn, prev - nn + dn], mfw)
                if k % every == 0:
                    b.box_base(mfw, (8, 8, hgt + 9), (q[0], q[1], zg - 5), rot=(0, 0, math.atan2(t.y, t.x)))
            prev = cur

    far_wall(0, -520, -150, w=3.2, hgt=3.0)
    far_wall(0, 120, 520, w=3.2, hgt=3.0)
    far_wall(1, -300, 40, w=3.6, hgt=3.4, every=9)
    far_wall(1, 180, 480, w=3.6, hgt=3.4, every=9)

    # ------------------------------------------------------------------ 樹叢團塊（成群的低面數樹冠；頂點色隨地表植被、較深）
    near_arr = np.array(near_pts)
    rs = np.random.default_rng(5)
    NC = 3600
    dep = 105 + 680 * rs.uniform(0, 1, NC) ** 2.0
    lat = rs.uniform(-0.64, 0.64, NC) * dep
    grove = fbm(lat / 90, dep / 90, 3, 51)
    keep = rs.uniform(0, 1, NC) < np.clip(0.5 + 1.4 * grove + 0.35 * (dep < 420), 0.3, 1)
    GXc, GYc = lat[keep], dep[keep]
    pts = []
    for gx_, gy_ in zip(GXc, GYc):
        dd = math.hypot(gx_, gy_)
        rc = rs.uniform(3, 8) * (1 + dd / 600)
        for _ in range(rs.integers(2, 9)):
            a_ = rs.uniform(0, TAU)
            r_ = rc * math.sqrt(rs.uniform(0, 1))
            pts.append((gx_ + r_ * math.cos(a_), gy_ + r_ * math.sin(a_)))
    pts = np.array(pts)
    CX, CY = pts[:, 0], pts[:, 1]
    CZ = height(CX, CY)
    dw, _, _ = seg_query(CX, CY, near_arr)
    hx, hy = grad(CX, CY, 3.0)
    cv = curvature(CX, CY)
    slope = np.hypot(hx, hy)
    keep = (dw > 5.5) & (slope < 1.35)
    CX, CY, CZ, hx, hy, cv = CX[keep], CY[keep], CZ[keep], hx[keep], hy[keep], cv[keep]
    CC = veg_colors(CX, CY, CZ, hx, hy, cv)
    dd_all = np.sqrt(CX * CX + CY * CY + (CZ - CAM.z) ** 2)
    hz = 1 - np.exp(-((dd_all / 1150.0) ** 1.8))
    for x, y, z, c, dd, hzv in zip(CX, CY, CZ, CC, np.hypot(CX, CY), hz):
        s_ = (1.0 + 1.5 * rs.uniform(0, 1) ** 1.5) * (1 + dd / 650)
        hgt = s_ * rs.uniform(0.55, 0.85)
        rot = rs.uniform(0, TAU)
        ring = []
        for k in range(6):
            a_ = rot + TAU * k / 6
            rr = s_ * rs.uniform(0.75, 1.15)
            ring.append(bm.verts.new((x + rr * math.cos(a_), y + rr * math.sin(a_), z - hgt * 0.25)))
        topv = bm.verts.new((x + rs.uniform(-0.25, 0.25) * s_, y + rs.uniform(-0.25, 0.25) * s_, z + hgt))
        for v in ring:
            rd = Vector((v.co.x - x, v.co.y - y, 0)).normalized()
            v[dome_layer] = (rd * 0.8 + Vector((0, 0, 0.6))).normalized()
        topv[dome_layer] = Vector((rs.uniform(-0.15, 0.15), rs.uniform(-0.15, 0.15), 1)).normalized()
        # 喬木比灌叢深綠（霧化後差異變小）
        k_ = rs.uniform(0.62, 0.95) * (1 - hzv) + hzv
        cc = [float(min(1, v * k_)) for v in c]
        for v in ring:
            v[col_layer] = (c[0], c[1], c[2], 1.0)
        topv[col_layer] = (min(1, cc[0] * 1.15), min(1, cc[1] * 1.15), min(1, cc[2] * 1.1), 1.0)
        for k in range(6):
            face([ring[k], ring[(k + 1) % 6], topv], veg, True)
    print(f"  great-wall: {len(CX)} tree clumps")

    # 非植被面的頂點色設為白（不影響其他材質）
    for v in bm.verts:
        if v[col_layer][3] < 0.5 or all(x == 0 for x in v[col_layer][:3]):
            v[col_layer] = (1.0, 1.0, 1.0, 1.0)
    _export(b, path, veg)


def _export(b, path, veg_mi):
    obj = b.build_object()
    me = obj.data
    # 遠處地形的法線往「朝上、朝相機」傾斜，降低明暗對比（大氣散射使遠山顯得平淡）
    nl = len(me.loops)
    ln = np.zeros(nl * 3)
    me.corner_normals.foreach_get("vector", ln)
    ln = ln.reshape(-1, 3)
    lv = np.zeros(nl, np.int64)
    me.loops.foreach_get("vertex_index", lv)
    co = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    pm = np.zeros(len(me.polygons), np.int64)
    me.polygons.foreach_get("material_index", pm)
    ls = np.zeros(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.zeros(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_total", lt)
    loop_mat = np.repeat(pm, lt)
    # 樹叢：以圓頂法線取代（6 面錐體看起來圓潤）
    if "dome_n" in me.attributes:
        dn = np.zeros(len(me.vertices) * 3)
        me.attributes["dome_n"].data.foreach_get("vector", dn)
        dn = dn.reshape(-1, 3)[lv]
        has = np.linalg.norm(dn, axis=1) > 0.5
        ln = np.where(has[:, None], dn, ln)
        me.attributes.remove(me.attributes["dome_n"])
    p = co[lv]
    d = np.sqrt(p[:, 0] ** 2 + p[:, 1] ** 2 + (p[:, 2] - CAM.z) ** 2)
    w = 0.85 * (1 - np.exp(-((d / 1100.0) ** 1.6))) * (loop_mat == veg_mi)
    tgt = np.array([0.0, -0.45, 0.89])
    tgt /= np.linalg.norm(tgt)
    nn = ln * (1 - w[:, None]) + tgt[None, :] * w[:, None]
    nn /= np.linalg.norm(nn, axis=1, keepdims=True)
    me.normals_split_custom_set([tuple(v) for v in nn])
    # 依材質分離物件，只有植被保留頂點色（減少 GLB 大小）
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="MATERIAL")
    bpy.ops.object.mode_set(mode="OBJECT")
    for o in list(bpy.context.scene.objects):
        if o.type != "MESH" or not o.data.polygons:
            continue
        if o.data.polygons[0].material_index != veg_mi and "Col" in o.data.color_attributes:
            o.data.color_attributes.remove(o.data.color_attributes["Col"])
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_apply=True, export_yup=True,
                              export_image_format="JPEG", export_jpeg_quality=82, export_all_vertex_colors=False)
