"""angkor_wat 寫實模型（尺寸依實測資料，公尺）

座標：寺院中心為原點，+X 東、+Y 北。
- 外圍城牆 1025 × 800 m（紅土石），外有寬約 190 m 的護城河；西側參道長約 350 m
- 第三層迴廊（外迴廊）東西 187 m × 南北 215 m，台基約 3.5 m；外側為雙排柱廊（主廊＋半廊）
- 十字迴廊（Preah Poan）位於西門與第二層之間
- 第二層 115 × 100 m，高出約 7 m；四角有殘缺的角塔
- 中央層（Bakan）60 × 60 m，高台再高約 13 m；五座蓮花苞塔，中央塔頂距地面約 65 m，角塔約 52 m
- 參道北側的倒影池（蓮花池），參考照即由北池西岸隔水東望

預覽相機（參考照反推）：由北倒影池西岸 (-434.1, 90)、離水面約 2.1 m，朝方位 100.75° 平視，等效焦距約 65 mm。
"""

import math

from mathutils import Matrix, Vector, noise
from mathutils.geometry import delaunay_2d_cdt

from lib import TAU, Builder

# 預覽相機（同 build.py CAMS 格式：目標點、方位角、仰角、距離、焦距）
CAMERA = ((-11.7, 9.8, 4.18), 259.25, -0.37, 430.0, 65)
CAM_XY = (-434.1, 90.0)
HEAD = math.radians(100.75)

# 主要高程
Z3 = 3.5  # 第三層迴廊地坪
Z2 = 10.5  # 第二層地坪
ZC = 23.5  # 中央層地坪
POND = (-421.0, -330.0, 22.0, 122.0)  # 北倒影池 x0, x1, y0, y1（南池對稱）
WATER_Z = -0.7


# ====================================================================== 水面漣漪法線貼圖（numpy 產生，快取）
def water_normal():
    import os

    import numpy as np
    from PIL import Image

    from lib import TEX

    out_dir = os.path.join(TEX, "_gen", "angkor_v1")
    out = os.path.join(out_dir, "water_nor.jpg")
    if os.path.exists(out):
        return out
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(3)
    N = 512
    fy = np.fft.fftfreq(N)[:, None]
    fx = np.fft.fftfreq(N)[None, :]
    h = np.zeros((N, N))
    for feat, amp, stretch in ((40, 1.0, 3.0), (14, 0.5, 2.0), (5, 0.2, 1.0)):
        w = rng.standard_normal((N, N))
        s = feat / 2.0
        g = np.exp(-2 * (np.pi * s) ** 2 * ((fx * stretch) ** 2 + fy**2))
        r = np.real(np.fft.ifft2(np.fft.fft2(w) * g))
        h += amp * r / (r.std() + 1e-9)
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * 0.35
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * 0.35
    n = np.stack([-dx, dy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    Image.fromarray((np.clip(n * 0.5 + 0.5, 0, 1) * 255).astype(np.uint8)).save(out, quality=90)
    return out


def lotus_carpet():
    """蓮葉地毯貼圖（1024² ≈ 5 m）：底色、粗糙度（G）、法線；葉間為深色水面（低粗糙度可反射天空）"""
    import os

    import numpy as np
    from PIL import Image

    from lib import TEX

    out_dir = os.path.join(TEX, "_gen", "angkor_v8")
    names = [os.path.join(out_dir, f"lotus_{k}.jpg") for k in ("diff", "rough", "nor")]
    if all(os.path.exists(n) for n in names):
        return names
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(11)
    N = 1024
    col = np.zeros((N, N, 3))
    col[:] = np.array([18, 24, 26], float)
    rough = np.full((N, N), 70.0)
    h = np.zeros((N, N))
    yy, xx = np.mgrid[0:N, 0:N]
    for i in range(1300):
        cx, cy = rng.uniform(0, N, 2)
        r = rng.uniform(26, 70)
        R = int(r + 2)
        ys = (np.arange(int(cy) - R, int(cy) + R + 1)) % N
        xs = (np.arange(int(cx) - R, int(cx) + R + 1)) % N
        gy, gx = np.meshgrid(np.arange(int(cy) - R, int(cy) + R + 1) - cy, np.arange(int(cx) - R, int(cx) + R + 1) - cx, indexing="ij")
        d = np.sqrt(gx * gx + gy * gy) / r
        ang = np.arctan2(gy, gx)
        a0 = rng.uniform(-np.pi, np.pi)
        notch = np.abs(((ang - a0 + np.pi) % (2 * np.pi)) - np.pi) < 0.22 * (d > 0.05)
        m = (d < 1.0) & ~notch
        old = rng.random() < 0.35
        base = np.array([74, 80, 34], float) * rng.uniform(0.65, 1.15)
        if old:
            base = base * np.array([1.5, 1.15, 0.7]) * rng.uniform(0.8, 1.1)
        shade = (0.85 + 0.25 * (1 - d)) * (1 + 0.05 * np.cos(ang * 18))  # 葉脈
        rim = np.clip((d - 0.9) * 10, 0, 1)
        c = base[None, None, :] * shade[..., None] * (1 - 0.3 * rim[..., None])
        sub = col[np.ix_(ys, xs)]
        sub[m] = c[m]
        col[np.ix_(ys, xs)] = sub
        rs = rough[np.ix_(ys, xs)]
        rs[m] = 255
        rough[np.ix_(ys, xs)] = rs
        hs = h[np.ix_(ys, xs)]
        hs[m] = np.maximum(hs[m], 1.0 + 0.6 * (1 - d[m]) ** 0.5 + rng.uniform(0, 0.5))
        h[np.ix_(ys, xs)] = hs
    # 粉紅花點
    for i in range(35):
        cx, cy = rng.integers(0, N, 2)
        r = rng.uniform(5, 10)
        m = ((xx - cx) ** 2 + (yy - cy) ** 2) < r * r
        col[m] = np.array([215, 110, 140]) * rng.uniform(0.8, 1.1)
        rough[m] = 150
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * 1.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * 1.5
    n = np.stack([-dx, dy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(names[0], quality=90)
    arm = np.stack([np.full((N, N), 255.0), rough, np.zeros((N, N))], -1)
    Image.fromarray(arm.astype(np.uint8)).save(names[1], quality=92)
    Image.fromarray((np.clip(n * 0.5 + 0.5, 0, 1) * 255).astype(np.uint8)).save(names[2], quality=90)
    return names


def carpet_mat(b):
    import bpy

    diff, rgh, nor = lotus_carpet()
    m = bpy.data.materials.new("AngkorWat_lotus_carpet")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(diff, check_existing=True)
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    aimg = nt.nodes.new("ShaderNodeTexImage")
    aimg.image = bpy.data.images.load(rgh, check_existing=True)
    aimg.image.colorspace_settings.name = "Non-Color"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(aimg.outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    nimg = nt.nodes.new("ShaderNodeTexImage")
    nimg.image = bpy.data.images.load(nor, check_existing=True)
    nimg.image.colorspace_settings.name = "Non-Color"
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = 0.6
    nt.links.new(nimg.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return b._register("lotus_carpet", m, 5.0)


def water_mat(b):
    import bpy

    m = bpy.data.materials.new("AngkorWat_water")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.012, 0.018, 0.017, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.06
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(water_normal(), check_existing=True)
    img.image.colorspace_settings.name = "Non-Color"
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.inputs["Strength"].default_value = 0.18
    nt.links.new(img.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    return b._register("water", m, 6.0)


# ====================================================================== 共用工具
class AWBuilder(Builder):
    """純色材質的面給固定 UV，避免 glTF 依投影軸切開頂點（減少頂點數與檔案大小）"""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.plain = set()

    def color(self, name, hex_color, rough=0.7, metal=0.0, alpha=1.0):
        new = name not in self._cache
        mi = super().color(name, hex_color, rough, metal, alpha)
        if new:
            self.plain.add(mi)
        return mi

    def _uv(self):
        uv = self.bm.loops.layers.uv.verify()
        for f in self.bm.faces:
            if f.material_index in self.plain:
                for l in f.loops:
                    l[uv].uv = (0.5, 0.5)
                continue
            tile = self.tiles[f.material_index] if f.material_index < len(self.tiles) else 1.0
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


def n2(x, y, s, seed=0.0):
    return noise.noise(Vector((x * s + seed, y * s - seed * 0.7, seed * 0.31)))


def n3(p, s, seed=0.0):
    return noise.noise(Vector((p.x * s + seed, p.y * s - seed * 0.7, p.z * s + seed * 0.31)))


def fbm(x, y, s, octaves=4, seed=0.0):
    t, a, f = 0.0, 1.0, s
    for i in range(octaves):
        t += a * n2(x, y, f, seed + i * 17.3)
        a *= 0.5
        f *= 2.03
    return t


def smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def clamp01(c):
    return (min(1.0, max(0.0, c[0])), min(1.0, max(0.0, c[1])), min(1.0, max(0.0, c[2])), 1.0)


class Painter:
    """lib.Builder 網格的頂點色（每個面角）；材質以 Multiply 混入，glTF 輸出為 COLOR_0"""

    def __init__(self, b):
        self.b = b
        self.cl = b.bm.loops.layers.color.new("Col")
        self.mark = b.bm.faces.layers.int.new("painted")

    def pv(self, verts, fn):
        cl, mk = self.cl, self.mark
        for f in {f for v in verts for f in v.link_faces}:
            f[mk] = 1
            for l in f.loops:
                l[cl] = clamp01(fn(f, l.vert.co))

    def paint_faces(self, faces, fn):
        cl, mk = self.cl, self.mark
        for f in faces:
            f[mk] = 1
            for l in f.loops:
                l[cl] = clamp01(fn(f, l.vert.co))

    def finish(self, default_fn):
        """未上色的面依材質套用 default_fn(face, co)；再把頂點色接進所有材質"""
        cl, mk = self.cl, self.mark
        for f in self.b.bm.faces:
            if not f[mk]:
                for l in f.loops:
                    l[cl] = clamp01(default_fn(f, l.vert.co))
        self.b.bm.faces.layers.int.remove(mk)
        for m in self.b.mats:
            nt = m.node_tree
            bsdf = nt.nodes["Principled BSDF"]
            links = bsdf.inputs["Base Color"].links
            vc = nt.nodes.new("ShaderNodeVertexColor")
            vc.layer_name = "Col"
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs["Factor"].default_value = 1.0
            if links:
                nt.links.new(links[0].from_socket, mix.inputs[6])
            else:
                mix.inputs[6].default_value = bsdf.inputs["Base Color"].default_value[:]
            nt.links.new(vc.outputs["Color"], mix.inputs[7])
            nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])


# ====================================================================== 高棉塔（prasat）
def redent(k=3, s=0.085):
    """單位正方形（半寬 1）四角各凹 k 階的十字形平面，逆時針；回傳 (點列, 凸角索引)"""
    q = [(1.0, 0.0), (1.0, 1.0 - k * s)]
    for i in range(1, k + 1):
        q.append((1.0 - i * s, 1.0 - (k - i + 1) * s))
        q.append((1.0 - i * s, 1.0 - (k - i) * s))
    # q 由 (1,0) 走到 (1-ks, 1)；鏡射得到完整一圈
    quad1 = q
    pts = []
    for rot in range(4):
        c, s_ = [(1, 0), (0, 1), (-1, 0), (0, -1)][rot]
        for x, y in quad1:
            pts.append((x * c - y * s_, x * s_ + y * c))
    # 凸角：每象限的 (1,1-ks) 與階梯外凸點
    convex = []
    n = len(quad1)
    for rot in range(4):
        base = rot * n
        convex.append(base + 1)
        for i in range(1, k + 1):
            convex.append(base + 2 * i)
    return pts, convex


SEC, SEC_CONVEX = redent(2, 0.11)
SEC_MID = [i * len(SEC) // 4 for i in range(4)]


def ring_stack(b, mi, cx, cy, prof, rot=0.0, cap_top=True, apex=None):
    """以 redent 平面依 prof [(半寬, z)] 疊出塔身；回傳全部頂點"""
    c, s = math.cos(rot), math.sin(rot)
    rings = []
    for w, z in prof:
        rings.append([b.bm.verts.new((cx + w * (x * c - y * s), cy + w * (x * s + y * c), z)) for x, y in SEC])
    n = len(SEC)
    b.bm.faces.new(list(reversed(rings[0])))
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            b.bm.faces.new([r0[i], r0[j], r1[j], r1[i]])
    allv = [v for r in rings for v in r]
    if apex is not None:
        a = b.bm.verts.new((cx, cy, apex))
        for i in range(n):
            b.bm.faces.new([rings[-1][i], rings[-1][(i + 1) % n], a])
        allv.append(a)
    elif cap_top:
        b.bm.faces.new(rings[-1])
    b._assign(allv, mi)
    return allv


def prasat(b, mi, cx, cy, z0, H, w, tiers=6, ruined_at=None, porch=True, seed=0):
    """蓮花苞形塔：台座 → 塔身（四面門廊）→ 逐層收分的塔頂（每層有簷口與尖瓣飾）→ 蓮苞頂
    H 為自 z0 起算的總高；w 為塔身半寬。ruined_at 若給定（0–1），塔頂於該比例處崩毀。"""
    rng = b.rng
    verts = []
    prof = []
    # 台座：三層線腳
    for sc, dz in ((1.3, 0.0), (1.3, 0.06), (1.2, 0.08), (1.2, 0.14)):
        prof.append((w * sc, z0 + H * dz * 0.6))
    zb = z0 + H * 0.084
    zt = z0 + H * 0.3  # 塔身頂
    prof += [(w * 1.0, zb), (w * 1.0, zt - H * 0.03), (w * 1.07, zt - H * 0.025), (w * 1.07, zt - H * 0.012), (w * 1.12, zt - H * 0.008), (w * 1.12, zt)]
    # 塔頂：逐層收分（蓮苞輪廓）
    top_z = z0 + H * 0.9
    span = top_z - zt
    hs = [0.86**i for i in range(tiers)]
    tot = sum(hs)
    z = zt
    cut = None
    tier_levels = []
    for i in range(tiers):
        h = span * hs[i] / tot
        f0 = (z - zt) / span
        f1 = (z + h - zt) / span
        s0 = 0.98 * (1 - f0**1.7) ** 0.62 + 0.18 * f0
        s1 = 0.98 * (1 - f1**1.7) ** 0.62 + 0.18 * f1
        s1 = max(s1, 0.2)
        # 每層：退縮的腰 → 主帶 → 外挑簷口 → 再退
        seg = [(w * s0 * 0.92, z), (w * s0 * 0.97, z + h * 0.15), (w * s0 * 0.97, z + h * 0.62),
               (w * s0 * 1.05, z + h * 0.66), (w * s0 * 1.05, z + h * 0.8), (w * (s0 + s1) * 0.47, z + h * 0.88)]
        if ruined_at is not None and (z + h - z0) / H > ruined_at:
            cut = z + h * 0.62
            prof += [p for p in seg if p[1] <= cut + 1e-6]
            if prof[-1][1] < cut:
                prof.append((prof[-1][0], cut))
            break
        prof += seg
        tier_levels.append((z + h * 0.8, w * s0 * 1.04, h))
        z += h
    if cut is None:
        # 蓮苞頂
        sz = w * 0.2
        prof += [(sz * 1.15, top_z + H * 0.015), (sz * 1.3, top_z + H * 0.04), (sz * 0.9, top_z + H * 0.075)]
        verts += ring_stack(b, mi, cx, cy, prof, apex=z0 + H)
    else:
        verts += ring_stack(b, mi, cx, cy, prof, cap_top=True)
        # 崩毀頂端：不規則石塊堆
        wt = prof[-1][0]
        for _ in range(7):
            ox, oy = rng.uniform(-0.7, 0.7) * wt, rng.uniform(-0.7, 0.7) * wt
            sz = wt * rng.uniform(0.35, 0.7)
            verts += b.rock(mi, (sz, sz * rng.uniform(0.7, 1.2), sz * 0.6), (cx + ox, cy + oy, cut + sz * 0.15), rot=(0, 0, rng.uniform(0, TAU)),
                            rough=0.12, subdiv=1, seed=rng.randint(0, 999), round_=0.15)
    # 尖瓣飾（antefix）：每層簷口上，立於凸角與各面中央
    for zl, wl, h in tier_levels:
        hh = h * 0.72
        for idx in list(SEC_CONVEX) + SEC_MID:
            x, y = SEC[idx]
            ang = math.atan2(y, x)
            r = 1.0 if idx in SEC_MID else 0.97
            px, py = cx + x * wl * r, cy + y * wl * r
            verts += b.tri_prism(mi, h * 0.06, wl * 0.1, hh, (px, py, zl), rot_z=ang)
    # 四面門廊（塔身外凸的山牆門）
    if porch:
        for k in range(4):
            a = k * TAU / 4
            c, s = math.cos(a), math.sin(a)
            d = w * 1.0
            M = Matrix.Translation((cx + c * (d + w * 0.25), cy + s * (d + w * 0.25), zb)) @ Matrix.Rotation(a, 4, "Z")
            hp = (zt - zb) * 0.72
            ww = w * 0.55
            # 門廊身與三角山牆（尖拱輪廓）
            verts += b.box(mi, (w * 0.5, ww * 2, hp), tuple(M @ Vector((0, 0, hp / 2))))
            verts += b.profile_wall(mi, [(-ww * 1.1, hp), (ww * 1.1, hp), (ww * 0.5, hp + w * 0.55), (0, hp + w * 0.9), (-ww * 0.5, hp + w * 0.55)],
                                    w * 0.6, M @ Matrix.Rotation(math.pi / 2, 4, "Z"))
            # 門洞（深色凹入）
            verts += b.box(b.color("void", "#1c1712", rough=1.0), (0.12, ww * 0.7, hp * 0.62), tuple(M @ Vector((w * 0.25 + 0.03, 0, hp * 0.31))))
    return verts


# ====================================================================== 迴廊
def frame(x0, y0, x1, y1):
    """沿線段的局部座標：u 向外（右手側）、v 向上；回傳 (矩陣, 長度)"""
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    ang = math.atan2(dy, dx)
    M = Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, 0)) @ Matrix.Rotation(ang - math.pi / 2, 4, "Z")
    return M, L


def extrude(b, mi, pts_uv, x0, y0, x1, y1, z0, inset=0.0):
    """剖面（u 橫向、v 高）沿線段擠出。u 正向為行進方向右側"""
    M, L = frame(x0, y0, x1, y1)
    M = Matrix.Translation((0, 0, z0)) @ M
    # profile_wall：剖面在局部 XZ、沿局部 Y 擠出；frame 已使局部 Y = 行進方向
    return b.profile_wall(mi, list(pts_uv), L - 2 * inset, M)


def vault(hw, h, n=6):
    """疊澀拱頂剖面（上緣外凸），半寬 hw、高 h"""
    pts = []
    for i in range(n + 1):
        t = i / n
        a = math.pi * t
        u = -hw * math.cos(a)
        v = h * math.sin(a) ** 0.75
        pts.append((u, v))
    return pts


def gallery(b, mats, x0, y0, x1, y1, z0, kind="outer", hw=4.5, windows=True):
    """一段迴廊。kind：outer（第三層：內牆＋主廊柱列＋外側半廊柱列）、
    inner（第二層／中央：外牆有窗、內側柱列）。行進方向右手側為外側。"""
    stone, roof, dark = mats["stone"], mats["roof"], mats["void"]
    M, L = frame(x0, y0, x1, y1)
    d = Vector(((x1 - x0) / L, (y1 - y0) / L, 0))
    nrm = Vector((d.y, -d.x, 0))  # 右手側（外側）
    vs = []

    def at(t, u):
        p = Vector((x0, y0, 0)) + d * t + nrm * u
        return p

    if kind == "outer":
        # 主廊：內牆（u -2.8..-2.0）、柱列 A（u +1.0）、半廊柱列 B（u +3.6）
        vs += extrude(b, stone, [(-2.9, 0), (-1.9, 0), (-1.9, hw), (-2.9, hw)], x0, y0, x1, y1, z0)
        # 主廊地坪下的深色內牆面（自柱間可見陰影）
        vs += extrude(b, dark, [(-1.9, 0.05), (-1.82, 0.05), (-1.82, hw - 0.4), (-1.9, hw - 0.4)], x0, y0, x1, y1, z0, inset=0.5)
        # 主拱頂（含簷）
        ridge = vault(2.6, 2.6)
        vs += extrude(b, roof, [(-3.1, hw), (1.6, hw), (1.6, hw + 0.45)] + [(u - 0.75, hw + 0.45 + v) for u, v in reversed(ridge)][1:-1] + [(-3.1, hw + 0.45)],
                      x0, y0, x1, y1, z0)
        # 屋脊飾帶
        vs += extrude(b, roof, [(-0.95, hw + 3.0), (-0.55, hw + 3.0), (-0.55, hw + 3.25), (-0.95, hw + 3.25)], x0, y0, x1, y1, z0)
        # 柱列 A 與楣樑
        vs += extrude(b, stone, [(0.55, hw - 0.55), (1.45, hw - 0.55), (1.45, hw), (0.55, hw)], x0, y0, x1, y1, z0)
        n = int(L / 3.4)
        for i in range(n):
            p = at((i + 0.5) * L / n, 1.0)
            vs += b.box(stone, (0.75, 0.75, hw - 0.55), (p.x, p.y, z0 + (hw - 0.55) / 2), rot=(0, 0, math.atan2(d.y, d.x)))
        # 半廊：外柱列 B 與斜屋頂（半拱）
        hb = hw - 1.4
        vs += extrude(b, stone, [(3.2, hb - 0.45), (4.0, hb - 0.45), (4.0, hb), (3.2, hb)], x0, y0, x1, y1, z0)
        nb = int(L / 4.6)
        for i in range(nb):
            p = at((i + 0.5) * L / nb, 3.6)
            vs += b.box(stone, (0.55, 0.55, hb - 0.45), (p.x, p.y, z0 + (hb - 0.45) / 2), rot=(0, 0, math.atan2(d.y, d.x)))
        vs += extrude(b, roof, [(1.3, hw - 0.1), (4.3, hb), (4.3, hb + 0.35), (2.6, hb + 1.1), (1.3, hw + 0.75)], x0, y0, x1, y1, z0)
    else:
        # 外牆（u +1.2..+2.0）帶窗洞、內側柱列（u -2.2）
        vs += extrude(b, stone, [(1.2, 0), (2.0, 0), (2.0, hw), (1.2, hw)], x0, y0, x1, y1, z0)
        n = int(L / 4.0)
        for i in range(n):
            p = at((i + 0.5) * L / n, 2.02)
            # 窗洞（深色）＋ 欄杆窗柱
            if windows:
                vs += b.box(dark, (2.0, 0.06, 1.7), (p.x, p.y, z0 + hw * 0.52), rot=(0, 0, math.atan2(d.y, d.x)))
        vs += extrude(b, stone, [(-2.6, hw - 0.5), (-1.8, hw - 0.5), (-1.8, hw), (-2.6, hw)], x0, y0, x1, y1, z0)
        for i in range(int(L / 3.2)):
            p = at((i + 0.5) * L / int(L / 3.2), -2.2)
            vs += b.box(stone, (0.7, 0.7, hw - 0.5), (p.x, p.y, z0 + (hw - 0.5) / 2), rot=(0, 0, math.atan2(d.y, d.x)))
        ridge = vault(2.5, 2.5)
        vs += extrude(b, roof, [(-2.9, hw), (2.3, hw), (2.3, hw + 0.4)] + [(u - 0.2, hw + 0.4 + v) for u, v in reversed(ridge)][1:-1] + [(-2.9, hw + 0.4)],
                      x0, y0, x1, y1, z0)
        vs += extrude(b, roof, [(-0.4, hw + 2.85), (0.0, hw + 2.85), (0.0, hw + 3.1), (-0.4, hw + 3.1)], x0, y0, x1, y1, z0)
        # 內側半廊斜頂
        vs += extrude(b, roof, [(-3.0, hw - 0.6), (-1.5, hw + 0.3), (-1.5, hw + 0.7), (-3.0, hw - 0.25)], x0, y0, x1, y1, z0)
    return vs


def plinth(b, mi, x0, y0, x1, y1, z0, z1, steps=4, out=0.6):
    """層層外凸的台基線腳（矩形）"""
    vs = []
    h = (z1 - z0) / steps
    for i in range(steps):
        e = out * (steps - i - 1) * 0.6 + (0.25 if i % 2 else 0.0)
        vs += b.box_base(mi, (x1 - x0 + 2 * e, y1 - y0 + 2 * e, h + 0.02), ((x0 + x1) / 2, (y0 + y1) / 2, z0 + i * h))
    return vs


def pavilion(b, mats, cx, cy, z0, w, hw, tower_h=None, ruined=0.55, rot=0.0, seed=0):
    """十字形門亭／角亭：兩段交叉的高拱頂＋三角山牆，可帶殘塔"""
    stone, roof = mats["stone"], mats["roof"]
    vs = []
    for k in range(2):
        a = rot + k * math.pi / 2
        ca, sa = math.cos(a), math.sin(a)
        x0, y0, x1, y1 = cx - ca * w, cy - sa * w, cx + ca * w, cy + sa * w
        vs += extrude(b, stone, [(-3.4, 0), (3.4, 0), (3.4, hw + 0.8), (-3.4, hw + 0.8)], x0, y0, x1, y1, z0)
        ridge = vault(3.8, 3.4)
        vs += extrude(b, roof, [(-3.9, hw + 0.8), (3.9, hw + 0.8)] + [(u, hw + 0.8 + v) for u, v in reversed(ridge)][1:-1], x0, y0, x1, y1, z0)
        # 兩端尖拱山牆
        for sgn in (-1, 1):
            px, py = cx + ca * w * sgn, cy + sa * w * sgn
            M = Matrix.Translation((px, py, z0)) @ Matrix.Rotation(a + math.pi / 2, 4, "Z")
            vs += b.profile_wall(stone, [(-3.6, hw + 0.6), (3.6, hw + 0.6), (1.5, hw + 3.2), (0, hw + 4.8), (-1.5, hw + 3.2)], 0.6, M)
            # 入口門洞
            vs += b.box(mats["void"], (0.1, 2.0, hw * 0.65), (px + ca * 0.32 * sgn, py + sa * 0.32 * sgn, z0 + hw * 0.33), rot=(0, 0, a))
    if tower_h:
        vs += prasat(b, stone, cx, cy, z0 + hw * 0.6, tower_h, 3.6, tiers=5, ruined_at=ruined, porch=False, seed=seed)
    return vs


# ====================================================================== 植物
def sugar_palm(b, P, x, y, z, h, crown=3.0, tint=1.0):
    """糖棕：細長樹幹＋濃密的球形扇葉樹冠（每片扇葉為放射狀摺扇）"""
    rng = b.rng
    trunk = b.color("palm_trunk", "#6e6352", rough=0.9)
    leaf = b.color("palm_leaf", "#56632f", rough=0.75)
    lean = (rng.uniform(-0.02, 0.02) * h, rng.uniform(-0.02, 0.02) * h)
    vs = b.cyl(trunk, 0.34, 0.24, h, (x, y, z - 0.3), seg=6)
    for v in vs:
        t = (v.co.z - z) / h
        v.co.x += lean[0] * t * t
        v.co.y += lean[1] * t * t
    tx, ty, tz = x + lean[0], y + lean[1], z + h
    tone = rng.uniform(0.8, 1.1) * tint
    P.pv(vs, lambda f, co: (0.85 * tone, 0.82 * tone, 0.78 * tone))
    lv = []
    nleaf = int(10 + crown * 7)
    lt = rng.uniform(0.8, 1.15) * tint
    for i in range(nleaf):
        # 葉柄末端在球面上，扇面朝外張開
        az = rng.uniform(0, TAU)
        el = math.asin(rng.uniform(-0.75, 0.98))
        dirv = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))
        L = crown * rng.uniform(0.85, 1.05)
        base = Vector((tx, ty, tz))
        mid = base + dirv * L * 0.35
        side = dirv.cross(Vector((0, 0, 1)))
        if side.length < 1e-3:
            side = Vector((1, 0, 0))
        side.normalize()
        up = side.cross(dirv).normalized()
        R = L * 0.55
        center = b.bm.verts.new(base + dirv * L * 0.15)
        rim = []
        for k in range(9):
            a = -1.5 + 3.0 * k / 8
            rr = R * (1.0 if k % 2 == 0 else 0.62)
            p = mid + (dirv * math.cos(a) + side * math.sin(a)) * rr + up * (-0.3 * rr * (1 - math.cos(a)) + rng.uniform(-0.1, 0.1) * R)
            rim.append(b.bm.verts.new(p))
        for k in range(8):
            f = b.bm.faces.new([center, rim[k], rim[k + 1]])
            f.material_index = leaf
            f.smooth = True
        lv += [center] + rim
    P.pv(lv, lambda f, co: (lt * (0.82 + 0.18 * n3(co, 0.7)), lt * (0.9 + 0.12 * n3(co, 0.7, 3)), lt * 0.72))
    # 樹冠下的枯葉裙
    dead = b.color("palm_dead", "#7a6440", rough=0.9)
    for i in range(4):
        az = rng.uniform(0, TAU)
        p = Vector((tx + math.cos(az) * 0.7, ty + math.sin(az) * 0.7, tz - 0.9))
        vs2 = b.box(dead, (0.25, crown * 0.35, crown * 0.6), tuple(p), rot=(0.3 * math.cos(az), 0.3 * math.sin(az), az))
        P.pv(vs2, lambda f, co: (0.9, 0.85, 0.75))


def broad_tree(b, P, x, y, z, h, tint=1.0, blobs=7, sub=1):
    """闊葉樹：多個不規則葉團（大小不一、下方較暗）"""
    rng = b.rng
    trunk = b.color("trunk", "#4f4234", rough=0.9)
    leaf = b.color("foliage", "#3d5a26", rough=0.8)
    vs = b.cyl(trunk, h * 0.035, h * 0.022, h * 0.6, (x, y, z - 0.3), seg=5)
    P.pv(vs, lambda f, co: (0.8, 0.78, 0.74))
    lv = []
    n = blobs * 2
    zc = z + h * 0.68
    for k in range(n):
        a = rng.uniform(0, TAU)
        rr = rng.uniform(0, 0.3) * h
        r = h * rng.uniform(0.11, 0.2)
        zz = zc + rng.uniform(-0.15, 0.22) * h - rr * 0.3
        lv += b.rock(leaf, (r * 2, r * 2, r * 1.5), (x + rr * math.cos(a), y + rr * math.sin(a), zz), rough=0.45, subdiv=sub,
                     seed=rng.randint(0, 9999), flat_bottom=False, round_=0.8)
    t = rng.uniform(0.75, 1.15) * tint
    top = z + h

    def col(f, co):
        sh = 0.6 + 0.4 * smooth(z + h * 0.45, top, co.z)
        v = t * sh
        return (v * (0.85 + 0.2 * n3(co, 0.5)), v * (0.9 + 0.15 * n3(co, 0.5, 2)), v * (0.8 + 0.1 * n3(co, 0.5, 4)))

    P.pv(lv, col)


# ====================================================================== 地形
OUTER = (512.5, 400.0)  # 外圍城牆半寬
MOAT = (30.0, 220.0)  # 護城河自城牆外起算的內、外緣距離
GROUND_R = 1300.0


def rect_dist(x, y, x0, x1, y0, y1):
    """到矩形的距離（內部為負）"""
    dx = max(x0 - x, x - x1)
    dy = max(y0 - y, y - y1)
    if dx <= 0 and dy <= 0:
        return max(dx, dy)
    return math.hypot(max(dx, 0), max(dy, 0))


def ponds():
    x0, x1, y0, y1 = POND
    return [(x0, x1, y0, y1), (x0, x1, -y1, -y0)]


def moat_d(x, y):
    """>0 表示在護城河水域內（以圓角矩形環近似）"""
    ex, ey = OUTER
    d = rect_dist(x, y, -ex, ex, -ey, ey)  # 到城牆的外距離
    if x < 0 and abs(y) < 7:
        return -1.0  # 西側參道堤
    return min(d - MOAT[0], MOAT[1] - d)


def height(x, y):
    z = 0.25 * fbm(x, y, 0.01, 2, 3.0) + 0.1 * n2(x, y, 0.06, 1.0)
    # 參考照拍攝處：北池西岸為接近水面的低平紅土岸
    x0, x1, y0, y1 = POND
    wb = smooth(30.0, 8.0, rect_dist(x, y, x0 - 40, x0 + 2, y0 - 25, y1 + 25))
    z = z * (1 - wb) + (-0.42 + 0.06 * n2(x, y, 0.4, 2.0) + 0.05 * n2(x, y, 1.6, 7.0)) * wb
    for p in ponds():
        d = rect_dist(x, y, *p)
        if d < 4:
            z = min(z, -2.0 + 2.2 * smooth(-1.5, 1.5, d))
    m = moat_d(x, y)
    if m > -6:
        z = min(z, -3.2 + 3.2 * smooth(6.0, -6.0, m) * 0 + (-0.0) if m > 0 else z * smooth(-6, 0, -m) + (-1.8) * smooth(0, -6, m))
        if m > 0:
            z = -3.2
    # 遠處微微起伏、往地平線略降（遮住地景邊緣）
    r = math.hypot(x, y)
    z -= 6.0 * smooth(0.8 * GROUND_R, GROUND_R, r)
    return z


def spacing(x, y):
    dx, dy = x - CAM_XY[0], y - CAM_XY[1]
    d = math.hypot(dx, dy) + 1e-6
    cosang = (dx * math.sin(HEAD) + dy * math.cos(HEAD)) / d
    if cosang > math.cos(math.radians(26)):
        s = 0.03 * d
    elif cosang > math.cos(math.radians(45)):
        s = 0.05 * d
    else:
        s = 0.09 * d
    s = min(max(s, 0.8), 120.0)
    for p in ponds():
        dd = rect_dist(x, y, *p)
        if -2 < dd < 6:
            s = min(s, 2.5 + 0.3 * abs(dd))
    m = moat_d(x, y)
    if -10 < m < 8:
        s = min(s, 10.0)
    r = math.hypot(x, y)
    if r < 140:
        s = min(s, 12.0)
    return s


def build_ground(b, P, mats):
    rng = b.rng
    grass, soil = mats["grass"], mats["soil"]
    pts = []
    half = GROUND_R + 10

    def rec(x0, y0, size, depth):
        cxm, cym = x0 + size / 2, y0 + size / 2
        if math.hypot(cxm, cym) - size * 0.71 > GROUND_R:
            return
        sp = min(spacing(cxm, cym), *(spacing(x0 + a * size, y0 + c * size) for a in (0, 1) for c in (0, 1)))
        if size > sp * 1.7 and depth < 16:
            h = size / 2
            for a in (0, 1):
                for c in (0, 1):
                    rec(x0 + a * h, y0 + c * h, h, depth + 1)
            return
        px = cxm + rng.uniform(-0.35, 0.35) * size
        py = cym + rng.uniform(-0.35, 0.35) * size
        if math.hypot(px, py) < GROUND_R - 3:
            pts.append((px, py))

    rec(-half, -half, 2 * half, 0)
    for i in range(400):
        a = TAU * i / 400
        pts.append((GROUND_R * math.cos(a), GROUND_R * math.sin(a)))
    res = delaunay_2d_cdt([Vector(p) for p in pts], [], [], 0, 1e-4)
    vco, faces = res[0], res[2]
    bv = [b.bm.verts.new((p.x, p.y, height(p.x, p.y))) for p in vco]
    gf, sf = [], []
    for f in faces:
        vs = [bv[i] for i in f]
        a, c, d = vs[0].co, vs[1].co, vs[2].co
        if (c.x - a.x) * (d.y - a.y) - (c.y - a.y) * (d.x - a.x) < 0:
            vs.reverse()
        try:
            face = b.bm.faces.new(vs)
        except ValueError:
            continue
        face.smooth = True
        cx = sum(v.co.x for v in vs) / 3
        cy = sum(v.co.y for v in vs) / 3
        near_cam = math.hypot(cx - CAM_XY[0], cy - CAM_XY[1])
        pd = min(rect_dist(cx, cy, *p) for p in ponds())
        near_bank = (pd < 2.5 + 2.0 * n2(cx, cy, 0.15, 2.0) and cx < POND[0] + 4) or (cx < POND[0] + 1 and POND[2] - 30 < cy < POND[3] + 30 and cx > CAM_XY[0] - 25)
        is_soil = near_bank or near_cam < 13.0 + 4 * n2(cx, cy, 0.2, 5.0)
        face.material_index = soil if is_soil else grass
        (sf if is_soil else gf).append(face)

    def gcol(f, co):
        x, y = co.x, co.y
        a = fbm(x, y, 0.02, 3, 4.0)
        dry = smooth(-0.3, 0.6, fbm(x, y, 0.006, 3, 9.0))
        r = 0.92 + 0.08 * a + 0.1 * dry
        g = 0.92 + 0.06 * a - 0.03 * dry
        bb = 0.3 + 0.05 * a - 0.08 * dry
        k = smooth(0.75 * GROUND_R, GROUND_R, math.hypot(x, y))
        return (r * (1 - k) + 0.8 * k, g * (1 - k) + 0.85 * k, bb * (1 - k) + 0.9 * k)

    def scol(f, co):
        a = n2(co.x, co.y, 0.3, 1.0) + 0.8 * n2(co.x, co.y, 1.3, 6.0) + 0.6 * n2(co.x, co.y, 0.08, 9.0)
        wet = smooth(-0.32, -0.62, co.z)
        v = 0.92 + 0.09 * a
        return (0.8 * v * (1 - 0.35 * wet), 0.62 * v * (1 - 0.4 * wet), 0.12 * v * (1 - 0.4 * wet))

    P.paint_faces(gf, gcol)
    P.paint_faces(sf, scol)


# ====================================================================== 主體
def angkor_wat(path):
    b = AWBuilder("AngkorWat", seed=9)
    P = Painter(b)
    rng = b.rng
    mats = {
        "grass": b.tex("grass", "grass_ground", tile=5.0, tint="#6c6a0a", normal=0, rough=0.95),
        "soil": b.tex("soil", "dirt", tile=2.5, tint="#ff9800", normal=0, rough=0.95),
        "stone": b.tex("sandstone", "large_sandstone_blocks_01", tile=3.2, tint="#a89070", normal=1.0, rough=0.85),
        "roof": b.tex("roof", "grey_roof_tiles", tile=1.8, tint="#7e6040", normal=0, rough=0.85),
        "laterite": b.tex("laterite", "old_sandstone_02", tile=3.0, tint="#8e6a4e", normal=0, rough=0.9),
        "void": b.color("void", "#6a5440", rough=1.0),
    }
    mats["water"] = water_mat(b)
    stone, roof, lat = mats["stone"], mats["roof"], mats["laterite"]
    # 草地、紅土：降低鏡面反射（避免低角度時被天空反光洗白、去飽和）
    for k in ("grass", "soil"):
        b.mats[mats[k]].node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.12

    # ------------------------------------------------------------ 地景與水域
    build_ground(b, P, mats)
    carpet = carpet_mat(b)
    for k, (x0, x1, y0, y1) in enumerate(ponds()):
        # 近岸（西側）開闊水面，其後為蓮葉地毯；兩者在同一水平面上相接
        xs = x0 + 6.2 if k == 0 else x0 + 25
        for (ax, bx2, mi) in ((x0 - 1.5, xs, mats["water"]), (xs, x1 + 1.5, carpet)):
            vs = [b.bm.verts.new((ax, y0 - 1.5, WATER_Z)), b.bm.verts.new((bx2, y0 - 1.5, WATER_Z)),
                  b.bm.verts.new((bx2, y1 + 1.5, WATER_Z)), b.bm.verts.new((ax, y1 + 1.5, WATER_Z))]
            f = b.bm.faces.new(vs)
            f.material_index = mi
            P.pv(vs, lambda f, co: (1, 1, 1))
    ex, ey = OUTER
    m0, m1 = MOAT[0] - 2, MOAT[1] + 2
    for (ax, ay, bx2, by2) in ((-ex - m1, ey + m0, ex + m1, ey + m1), (-ex - m1, -ey - m1, ex + m1, -ey - m0),
                               (ex + m0, -ey - m0, ex + m1, ey + m0), (-ex - m1, 7.5, -ex - m0, ey + m0), (-ex - m1, -ey - m0, -ex - m0, -7.5)):
        vs = b.box(mats["water"], (bx2 - ax, by2 - ay, 0.02), ((ax + bx2) / 2, (ay + by2) / 2, -0.9))
        P.pv(vs, lambda f, co: (1, 1, 1))

    # ------------------------------------------------------------ 外圍城牆、西門、參道
    for (ax, ay, bx2, by2) in ((-ex, ey - 1, ex, ey + 1), (-ex, -ey - 1, ex, -ey + 1), (ex - 1, -ey, ex + 1, ey)):
        b.box_base(lat, (bx2 - ax, by2 - ay, 4.5), ((ax + bx2) / 2, (ay + by2) / 2, -0.5))
    for sgn in (-1, 1):
        b.box_base(lat, (2, ey - 118, 4.5), (-ex, sgn * (118 + (ey - 118) / 2), -0.5))
    # 西門（長約 235 m 的門廊，三座殘塔）
    gallery(b, mats, -ex, 118, -ex, 18, 0.0, kind="inner", hw=4.2, windows=False)
    gallery(b, mats, -ex, -18, -ex, -118, 0.0, kind="inner", hw=4.2, windows=False)
    for yy, th in ((0, 18), (40, 13), (-40, 13)):
        pavilion(b, mats, -ex, yy, 0.0, 9 if yy == 0 else 7, 5.0, tower_h=th, ruined=0.3, seed=yy)
    # 參道（高 1.5 m、寬 9.5 m，兩側那伽欄杆）
    b.box_base(lat, (400, 9.5, 2.0), (-312, 0, -0.5))
    for sgn in (-1, 1):
        extrude(b, stone, [(-0.3, 0), (0.3, 0), (0.3, 0.6), (0.18, 0.8), (-0.18, 0.8), (-0.3, 0.6)], -510, sgn * 4.5, -115, sgn * 4.5, 1.5)
        for xx in range(-505, -115, 6):
            b.box_base(stone, (0.35, 0.35, 0.95), (xx, sgn * 4.5, 1.45))
    # 榮譽台（十字形高台）
    b.box_base(stone, (26, 9.5, 2.6), (-104, 0, -0.5))
    b.box_base(stone, (9.5, 30, 2.6), (-104, 0, -0.5))

    # ------------------------------------------------------------ 第三層：台基與外迴廊
    X3, Y3 = 93.5, 107.5
    plinth(b, lat, -X3 - 6, -Y3 - 6, X3 + 6, Y3 + 6, -0.6, Z3, steps=4, out=0.5)
    gw = 6.0  # 迴廊端點留給門亭的半寬
    segs = []
    # 西側（往南走，右手側＝西）：留出西門建築群 y∈[-48, 48]
    segs += [(-X3, Y3 - gw, -X3, 48), (-X3, -48, -X3, -Y3 + gw)]
    segs += [(-X3 + gw, -Y3, -12, -Y3), (12, -Y3, X3 - gw, -Y3)]  # 南
    segs += [(X3, -Y3 + gw, X3, -12), (X3, 12, X3, Y3 - gw)]  # 東
    segs += [(X3 - gw, Y3, 12, Y3), (-12, Y3, -X3 + gw, Y3)]  # 北
    for a in segs:
        gallery(b, mats, *a, Z3, kind="outer", hw=4.6)
    for cx_, cy_ in ((-X3, -Y3), (-X3, Y3), (X3, -Y3), (X3, Y3)):
        pavilion(b, mats, cx_, cy_, Z3, 7.5, 5.4)
    for cx_, cy_, r_ in ((0, -Y3, 0), (X3, 0, 0), (0, Y3, 0)):
        pavilion(b, mats, cx_, cy_, Z3, 9, 5.8)
    # 西門建築群：中央門亭（殘塔）＋兩側門亭（殘塔）＋連接的高迴廊
    pavilion(b, mats, -X3, 0, Z3, 11, 6.6, tower_h=24, ruined=0.5, seed=1)
    for sgn in (-1, 1):
        pavilion(b, mats, -X3, sgn * 34, Z3, 8, 6.0, tower_h=18, ruined=0.45, seed=2 + sgn)
        ya, yb = (11, 26) if sgn > 0 else (-26, -11)
        gallery(b, mats, -X3, yb, -X3, ya, Z3, kind="outer", hw=5.4)
        ya, yb = (42, 48) if sgn > 0 else (-48, -42)
        gallery(b, mats, -X3, yb, -X3, ya, Z3, kind="outer", hw=5.0)

    # ------------------------------------------------------------ 十字迴廊（Preah Poan）
    zc0 = Z3 + 1.2
    b.box_base(stone, (36, 64, 1.25), (-75.5, 0, Z3 - 0.05))
    for a in ((-88, 0, -60, 0), (-75.5, -30, -75.5, 30), (-88, 30, -60, 30), (-60, -30, -88, -30)):
        gallery(b, mats, *a, zc0, kind="inner", hw=4.4)

    # ------------------------------------------------------------ 第二層
    X2, Y2 = 57.5, 50.0
    plinth(b, lat, -X2 - 4, -Y2 - 4, X2 + 4, Y2 + 4, Z3 - 0.2, Z2, steps=5, out=0.6)
    for a in ((-X2, Y2 - 5, -X2, 6), (-X2, -6, -X2, -Y2 + 5), (-X2 + 5, -Y2, X2 - 5, -Y2), (X2, -Y2 + 5, X2, Y2 - 5), (X2 - 5, Y2, -X2 + 5, Y2)):
        gallery(b, mats, *a, Z2, kind="inner", hw=4.4)
    pavilion(b, mats, -X2, 0, Z2, 7, 5.4)
    for cx_, cy_ in ((-X2, -Y2), (-X2, Y2), (X2, -Y2), (X2, Y2)):
        pavilion(b, mats, cx_, cy_, Z2, 5.5, 5.0, tower_h=26, ruined=0.6, seed=int(cx_ + cy_))
    # 西側階梯（第三層 → 第二層）
    stair(b, stone, -X2 - 4, 0, Z3, Z2, 8.0, "W")

    # ------------------------------------------------------------ 中央層（Bakan）
    tiers = [(76, 70), (72, 66), (68, 62), (64, 60)]
    zt = Z2 - 0.2
    th = (ZC - zt) / len(tiers)
    for wx, wy in tiers:
        plinth(b, lat, -wx / 2, -wx / 2, wx / 2, wx / 2, zt, zt + th, steps=3, out=0.4)
        zt += th
    for side in "WESN":
        for off in (-22, 0, 22):
            stair(b, stone, 0, off, Z2, ZC, 4.0, side, start=38.0)
    XC = 30.0
    for a in ((-XC, XC - 4, -XC, 5), (-XC, -5, -XC, -XC + 4), (-XC + 4, -XC, -5, -XC), (5, -XC, XC - 4, -XC), (XC, -XC + 4, XC, -5),
              (XC, 5, XC, XC - 4), (XC - 4, XC, 5, XC), (-5, XC, -XC + 4, XC)):
        gallery(b, mats, *a, ZC, kind="inner", hw=4.8)
    for cx_, cy_ in ((-XC, 0), (XC, 0), (0, -XC), (0, XC)):
        pavilion(b, mats, cx_, cy_, ZC, 5.5, 5.6)
    # 十字連廊（中央塔 → 四面門亭）
    for a in ((-XC + 5, 0, -9, 0), (9, 0, XC - 5, 0), (0, -XC + 5, 0, -9), (0, 9, 0, XC - 5)):
        gallery(b, mats, *a, ZC, kind="inner", hw=5.2)
    # 五座蓮花苞塔
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box_base(stone, (11, 11, 2.0), (sx * XC, sy * XC, ZC))
            prasat(b, stone, sx * XC, sy * XC, ZC + 2.0, 52.0 - ZC - 2.0, 3.9, tiers=6, seed=sx * 3 + sy)
    plinth(b, lat, -12, -12, 12, 12, ZC, ZC + 3.0, steps=3, out=0.4)
    prasat(b, stone, 0, 0, ZC + 3.0, 65.0 - ZC - 3.0, 5.6, tiers=7, seed=7)

    # ------------------------------------------------------------ 蓮花池：蓮葉與花
    lotus(b, P, rng)

    # ------------------------------------------------------------ 植物
    plant(b, P, rng)

    # ------------------------------------------------------------ 石材頂點色：灰褐砂岩＋黑色青苔斑、下部較深
    def default(f, co):
        mi = f.material_index
        if mi in (stone, roof, lat):
            moss = smooth(0.1, 0.65, n3(co, 0.12, 2.0) + 0.5 * n3(co, 0.5, 5.0))
            low = smooth(Z2 + 6, 0.0, co.z) * 0.18
            streak = smooth(0.2, 0.8, noise.noise(Vector((co.x * 0.6, co.y * 0.6, co.z * 0.05)))) * 0.25
            v = 1.0 - 0.32 * moss - low - streak
            warm = 1.0 + 0.06 * n3(co, 0.03, 7.0)
            if mi == roof:
                v *= 0.95
            return (v * warm * 1.05, v * (0.97 + 0.02 * warm), v * 0.86)
        return (1.0, 1.0, 1.0)

    P.finish(default)
    b.export(path)


def stair(b, mi, cx, cy, z0, z1, width, side, start=None):
    """陡梯（鋸齒剖面擠出）。side：梯面朝向（W 表示由西側登上，梯腳在西）"""
    h = z1 - z0
    nsteps = max(4, int(h / 0.32))
    run = h / math.tan(math.radians(62 if start else 45))
    pts = [(0.0, 0.0)]
    for i in range(nsteps):
        u0 = run * i / nsteps
        pts.append((u0, h * (i + 1) / nsteps))
        pts.append((u0 + run / nsteps, h * (i + 1) / nsteps))
    pts.append((run + 1.0, h))
    pts.append((run + 1.0, 0.0))
    # 方向：u 由梯腳往內（朝塔中心）
    dirs = {"W": (1, 0), "E": (-1, 0), "S": (0, 1), "N": (0, -1)}
    dx, dy = dirs[side]
    if start is not None:
        # 中央層：梯腳位於高台外緣 start 處，cy 為沿邊的偏移量
        bx0, by0 = (-dx * start, cy) if side in "WE" else (cy, -dy * start)
    else:
        bx0, by0 = cx, cy
    # profile_wall：剖面在局部 XZ（u→X），沿局部 Y 擠出 width；旋轉使 X 指向登梯方向
    M = Matrix.Translation((bx0, by0, z0)) @ Matrix.Rotation(math.atan2(dy, dx), 4, "Z")
    return b.profile_wall(mi, pts, width, M)


def lotus(b, P, rng):
    """蓮葉（浮水的睡蓮葉＋挺水的蓮葉，後者高出水面且傾斜、略呈碗狀）與粉紅花苞"""
    leaf_m = b.color("lotus_leaf", "#56552a", rough=0.9)
    b.mats[leaf_m].node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.25
    flower_m = b.color("lotus_flower", "#d96f8f", rough=0.5)
    for (x0, x1, y0, y1) in ponds():
        north = y0 > 0
        n = 5600 if north else 300
        for _ in range(n):
            if north:
                # 立體浮葉集中在預覽相機視野內的近中景（更遠處交給蓮葉地毯貼圖）
                dcam = 13.0 + 60.0 * rng.random() ** 2.0
                a = HEAD + math.radians(rng.uniform(-25, 25))
                x, y = CAM_XY[0] + math.sin(a) * dcam, CAM_XY[1] + math.cos(a) * dcam
                if not (x0 + 0.5 < x < x1 - 0.5 and y0 + 0.5 < y < y1 - 0.5):
                    continue
            else:
                x = rng.uniform(x0 + 0.8, x1 - 0.8)
                y = rng.uniform(y0 + 0.8, y1 - 0.8)
            # 參考照：近岸留出一片開闊水面（倒影），遠處蓮葉密集
            dist = x - x0
            dens = smooth(4.5, 7.0, dist) * (1.0 - 0.4 * smooth(25, 50, dist)) + 0.008
            if rng.random() > dens * (0.7 + 0.5 * max(0.0, n2(x, y, 0.08, 4.0))):
                continue
            raised = dist > 6.2 and rng.random() < 0.08
            r = rng.uniform(0.25, 0.45) if raised else rng.uniform(0.2, 0.4)
            z = WATER_Z + (rng.uniform(0.1, 0.5) if raised else 0.05)
            tilt = rng.uniform(0.02, 0.12) if raised else 0.0
            tdir = rng.uniform(0, TAU)
            a0 = rng.uniform(0, TAU)
            cup = r * (0.25 if raised else 0.0)
            M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(tilt, 4, Vector((math.cos(tdir), math.sin(tdir), 0)))
            c = b.bm.verts.new(M @ Vector((0, 0, 0)))
            rim = []
            for k in range(7):
                a = a0 + 0.35 + (TAU - 0.7) * k / 6 if not raised else a0 + TAU * k / 7
                rr = r * rng.uniform(0.9, 1.05)
                rim.append(b.bm.verts.new(M @ Vector((rr * math.cos(a), rr * math.sin(a), cup + rng.uniform(0.0, 0.02)))))
            fs = []
            for k in range(6 if not raised else 7):
                f = b.bm.faces.new([c, rim[k], rim[(k + 1) % 7]])
                f.material_index = leaf_m
                f.smooth = True
                fs.append(f)
            t = rng.uniform(0.7, 1.15)
            yel = rng.uniform(0, 0.4) if rng.random() < 0.3 else 0.0
            P.paint_faces(fs, lambda f, co: (t * (1 + yel * 0.9), t * (1 + yel * 0.25), t * (1 - yel)))
        # 花苞（粉紅）：直接立在水面上的小錐體
        nf = 260 if north else 80
        for _ in range(nf):
            x = rng.uniform(x0 + 2, x1 - 1)
            y = rng.uniform(y0 + 1, y1 - 1)
            if rng.random() > smooth(4, 12, x - x0):
                continue
            hgt = rng.uniform(0.3, 0.8)
            vs = b.cone(flower_m, rng.uniform(0.05, 0.08), rng.uniform(0.12, 0.2), (x, y, WATER_Z + hgt), seg=4)
            vs += b.cone(leaf_m, 0.015, hgt, (x, y, WATER_Z - 0.02), seg=3)
            t = rng.uniform(0.85, 1.1)
            P.pv(vs, lambda f, co: (t, t, t))


def plant(b, P, rng):
    """依參考照擺放糖棕與林木；其餘散植於寺院外圍與護城河外"""
    fx, fy = math.sin(HEAD), math.cos(HEAD)

    def cam_pos(off_deg, d):
        a = HEAD + math.radians(off_deg)
        return CAM_XY[0] + math.sin(a) * d, CAM_XY[1] + math.cos(a) * d

    # 參考照中的高大糖棕（左右各一）
    for off, d, h in ((-11.4, 250, 26), (12.3, 262, 27)):
        x, y = cam_pos(off, d)
        sugar_palm(b, P, x, y, height(x, y), h, crown=2.6)
    # 迴廊前的中型扇葉棕櫚群
    for off, d, h in ((-6.2, 300, 13.5), (-3.5, 302, 14.0), (-1.4, 306, 12.5), (-0.4, 304, 13.0), (3.6, 108, 9.0)):
        x, y = cam_pos(off, d)
        sugar_palm(b, P, x, y, height(x, y), h, crown=4.4 if d > 200 else 4.2)
    # 右側參道旁的棕櫚叢
    for k in range(9):
        off = rng.uniform(9.0, 17.0)
        d = rng.uniform(210, 260)
        x, y = cam_pos(off, d)
        if abs(y) < 8:
            y = 8.5 if y > 0 else -8.5
        sugar_palm(b, P, x, y, height(x, y), rng.uniform(13, 18), crown=3.6)
    # 左側遠處的闊葉樹
    for k in range(6):
        x, y = cam_pos(rng.uniform(-16, -13.5), rng.uniform(330, 380))
        broad_tree(b, P, x, y, height(x, y), rng.uniform(16, 22), blobs=7, sub=1)
    # 寺院外圍（城牆內）散植的樹，避開迴廊、參道與水池
    placed = 0
    tries = 0
    while placed < 46 and tries < 4000:
        tries += 1
        x, y = rng.uniform(-500, 500), rng.uniform(-390, 390)
        if abs(x) < 125 and abs(y) < 135:
            continue
        if x < -100 and abs(y) < 16:
            continue
        if any(rect_dist(x, y, *p) < 6 for p in ponds()):
            continue
        if math.hypot(x - CAM_XY[0], y - CAM_XY[1]) < 60:
            continue
        # 不擋住參考照視線（相機前方的狹長扇形）
        dx, dy = x - CAM_XY[0], y - CAM_XY[1]
        dd = math.hypot(dx, dy)
        if dd < 470 and (dx * fx + dy * fy) / dd > math.cos(math.radians(17)) and not (dx * fx + dy * fy > 380):
            continue
        if rng.random() < 0.3:
            sugar_palm(b, P, x, y, height(x, y), rng.uniform(12, 24), crown=rng.uniform(2.2, 2.8))
        else:
            broad_tree(b, P, x, y, height(x, y), rng.uniform(12, 22), blobs=4, sub=1)
        placed += 1
    # 護城河外的林帶（低面數）
    for k in range(90):
        a = rng.uniform(0, TAU)
        r = rng.uniform(780, 1150)
        x, y = r * math.cos(a) * 1.05, r * math.sin(a) * 0.95
        if moat_d(x, y) > -15:
            continue
        broad_tree(b, P, x, y, height(x, y), rng.uniform(16, 28), blobs=2, sub=1)
    # 寺院後方（東側）的樹林，形成天際線
    for k in range(45):
        x, y = rng.uniform(140, 480), rng.uniform(-360, 360)
        if abs(y) < 10:
            continue
        broad_tree(b, P, x, y, height(x, y), rng.uniform(18, 28), blobs=3, sub=1)
