"""giza 寫實模型（尺寸依實測資料，公尺）

座標：以古夫金字塔中心為原點，+X 東、+Y 北（依經緯度換算）。
- 古夫：底 230.3 m、原高 146.6 m、現高 138.5 m
- 卡夫拉：底 215.3 m、原高 143.5 m、現高 136.4 m，頂端保留原始石灰岩外殼，地勢高約 10 m
- 孟卡拉：底 102.2 × 104.6 m、原高 65.5 m、現高 61 m
- 獅身人面像：長 73 m、寬 19 m、高 20 m，面向正東，位於鑿出的圍坑中

做法重點：
- 金字塔：逐層石階幾何（每層有不規則退縮與崩角），每層豎面以自產的「石塊排列」貼圖（每層一條帶狀 UV），
  階面以碎石積沙貼圖；卡夫拉頂部為平滑外殼。頂點色做風化色差。
- 地面：以 Delaunay 不規則三角網做自適應解析度（預覽相機前景密、遠處疏），沙丘起伏、車轍（約束邊做出
  銳利邊界的帶狀面）、碎石斑；自產無明顯重複的細沙貼圖；地景延伸到約 2.6 km 並在邊緣淡入地平線色調。
- 自產貼圖以 numpy 程式產生，快取於 blender/textures/_gen/giza_v*/。
"""

import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector, noise
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt

from lib import TAU, TEX, Builder

# 預覽相機（同 build.py CAMS 格式：目標點、方位角、仰角、距離、焦距）
# 依參考照（All Gizah Pyramids，西南方沙丘上平視東北）以特徵點反推相機位置約為 (-760, -1290, 30)；為看到王后金字塔腳下的沙地，改用略高的 42 m
CAMERA = ((-458.7, -658.8, 54.2), 334.5, -1.0, 700.0, 78)

GEN = os.path.join(TEX, "_gen", "giza_v1")


# ====================================================================== 程式產生貼圖（numpy）
def _pnoise(shape, feat, rng):
    """可無縫拼接的高斯濾波雜訊（feat = 特徵尺寸，像素），標準化為平均 0、標準差 1"""
    n, m = shape
    w = rng.standard_normal((n, m))
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(m)[None, :]
    s = feat / 2.0
    g = np.exp(-2 * (np.pi * s) ** 2 * (fx**2 + fy**2))
    r = np.real(np.fft.ifft2(np.fft.fft2(w) * g))
    r -= r.mean()
    return r / (r.std() + 1e-9)


def _pfbm(shape, feat, rng, octaves=4, gain=0.5):
    t = np.zeros(shape)
    a = 1.0
    for _ in range(octaves):
        t += a * _pnoise(shape, feat, rng)
        a *= gain
        feat = max(1.0, feat / 2.0)
    return t / (t.std() + 1e-9)


def _normal_map(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength
    nx, ny, nz = -dx, dy, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / ln, ny / ln, nz / ln], -1)
    return (np.clip(n * 0.5 + 0.5, 0, 1) * 255).astype(np.uint8)


def _save(arr, name):
    from PIL import Image

    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(os.path.join(GEN, name), quality=90)


def _rock_detail(size):
    """取 rock_04 的灰階細節作為石面微紋理（平鋪到指定大小）"""
    from PIL import Image

    im = Image.open(os.path.join(TEX, "rock_04", "diff.jpg")).convert("L").resize((1024, 1024))
    a = np.asarray(im, dtype=np.float64) / 255.0
    a = a / a.mean()
    reps = (size[0] // 1024 + 1, size[1] // 1024 + 1)
    return np.tile(a, reps)[: size[0], : size[1]]


def gen_sand(rng):
    """細沙：細粒、小卵石、風紋、踩踏斑；低對比、無大尺度斑塊（避免重複感）。1024 px ≈ 6 m"""
    N = 1024
    h = 0.0 * np.zeros((N, N))
    # 風紋：約 10 cm 波長、以雜訊扭曲
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    warp = _pnoise((N, N), 90, rng) * 14 + _pnoise((N, N), 30, rng) * 4
    k = 2 * np.pi * 40 / N  # 40 條／貼圖（整數，確保無縫）
    rip = np.sin(k * (yy + 0.0 * xx) + warp * 0.25)
    rip = np.sign(rip) * np.abs(rip) ** 0.7
    ripamp = 0.5 + 0.5 * _pnoise((N, N), 160, rng)
    h += rip * 0.35 * np.clip(ripamp, 0, 1)
    grain = _pnoise((N, N), 1.3, rng)
    h += grain * 0.25 + _pnoise((N, N), 6, rng) * 0.25
    trample = np.clip(_pfbm((N, N), 40, rng, 3) - 0.3, 0, None)
    h -= trample * 0.6
    col_v = 1.0 + 0.035 * grain + 0.025 * _pnoise((N, N), 12, rng) + 0.035 * rip * np.clip(ripamp, 0, 1) - 0.05 * trample
    base = np.array([242, 196, 104], float)
    img = base[None, None, :] * col_v[..., None]
    # 彩色細砂粒（深、淺、偏紅）
    for frac, mul in ((0.006, (0.75, 0.7, 0.66)), (0.012, (1.05, 1.05, 1.07)), (0.004, (0.9, 0.78, 0.66))):
        m = rng.random((N, N)) < frac
        for c in range(3):
            img[..., c] = np.where(m, img[..., c] * mul[c], img[..., c])
    # 小卵石（1–4 cm）
    for _ in range(700):
        cx, cy = rng.integers(0, N, 2)
        r = rng.uniform(1.2, 3.5) * (1.0 if rng.random() < 0.85 else 2.0)
        tone = np.array(rng.choice([(0.82, 0.74, 0.64), (0.74, 0.7, 0.64), (0.95, 0.9, 0.8), (0.86, 0.72, 0.58)]))
        R = int(r + 3)
        ys = (np.arange(cy - R, cy + R + 1)) % N
        xs = (np.arange(cx - R, cx + R + 1)) % N
        gy, gx = np.meshgrid(np.arange(-R, R + 1), np.arange(-R, R + 1), indexing="ij")
        d = np.sqrt((gx * rng.uniform(0.7, 1.3)) ** 2 + gy**2) / r
        mask = np.clip(1.4 - d * 1.4, 0, 1) ** 0.6
        sub = img[np.ix_(ys, xs)]
        sub = sub * (1 - mask[..., None]) + (sub * tone[None, None, :] * (0.9 + 0.2 * rng.random())) * mask[..., None]
        img[np.ix_(ys, xs)] = sub
        hh = h[np.ix_(ys, xs)]
        h[np.ix_(ys, xs)] = hh + mask * 1.2
    _save(img, "sand_diff.jpg")
    _save(_normal_map(h, 1.6), "sand_nor.jpg")


def _blocks_band(W, Hh, rng, detail, wmin, wmax, tone_var=0.1):
    """一條石塊列：回傳 (色值倍率, 高度)；左右無縫"""
    widths = []
    while sum(widths) < W - wmax:
        widths.append(int(rng.uniform(wmin, wmax)))
    rest = W - sum(widths)
    if rest < wmin:
        widths[-1] += rest
    else:
        widths.append(rest)
    off = int(rng.integers(0, W))
    val = np.ones((Hh, W))
    hgt = np.zeros((Hh, W))
    en = _pnoise((Hh, W), 7, rng) * 2.2 + _pnoise((Hh, W), 26, rng) * 2.5 + _pnoise((Hh, W), 2, rng) * 0.8 + 2.0
    yy = np.arange(Hh)[:, None].astype(float)
    x0 = 0
    for w in widths:
        xs = np.arange(w)[None, :].astype(float)
        rad = rng.uniform(8, 22)
        # 距離四邊（以雜訊讓邊緣不規則、崩角）
        nb = rng.standard_normal(4)
        dl = xs + nb[0] * 2 + 3 * np.sin(yy / Hh * 3 + nb[1])
        dr = (w - 1 - xs) + nb[2] * 2 + 3 * np.sin(yy / Hh * 2.3 + nb[3])
        dt = yy - 1 + 2.5 * np.sin(xs / w * 4 + nb[0])
        db = (Hh - 1 - yy) + 2.5 * np.sin(xs / w * 3.3 + nb[2])
        cols = (np.arange(x0, x0 + w) + off) % W
        d = np.minimum(np.minimum(dl, dr), np.minimum(dt, db)) + en[:, cols]
        prof = np.clip(d / rad, 0, 1)
        prof = prof * (2 - prof)
        tone = 1.0 + rng.normal(0, tone_var)
        if rng.random() < 0.12:  # 部分石塊較深（剝落、缺損）
            tone *= rng.uniform(0.7, 0.85)
        val[:, cols] = tone * (0.42 + 0.58 * prof)
        hgt[:, cols] = prof * (0.9 + 0.2 * rng.random())
        x0 += w
    return val, hgt


def gen_blocks(rng):
    """金字塔石材圖集（2048²）：上半 4 條豎面帶（每帶 = 一個幾何石階，內含兩排石塊），下半為階面碎石積沙"""
    W = 2048
    img_v = np.ones((W, W))
    hgt = np.zeros((W, W))
    det = _rock_detail((W, W))
    pits = _pnoise((W, W), 3, rng)
    pits = np.clip(pits - 1.6, 0, None)
    blot = _pfbm((W, W), 200, rng, 3)
    for r in range(4):
        y0 = r * 256
        # 一帶兩排：上排較矮
        split = int(rng.uniform(110, 140))
        for (a, b2) in ((0, split), (split, 256)):
            v, h = _blocks_band(W, b2 - a, rng, det, 170, 430)
            img_v[y0 + a : y0 + b2] = v
            hgt[y0 + a : y0 + b2] = h
        # 幾何石階上緣（磨圓、積沙較亮）與下緣（接縫陰影）
        yy = np.arange(256)[:, None]
        img_v[y0 : y0 + 256] *= 1.0 - 0.38 * np.exp(-((255 - yy) / 16.0))
        img_v[y0 : y0 + 256] *= 1.0 + 0.08 * np.exp(-(yy / 10.0))
    top = img_v[:1024] * (0.7 + 0.3 * det[:1024]) * (1 - 0.35 * pits[:1024]) * (1 + 0.06 * blot[:1024])
    # 階面：沙與碎石
    N2 = 1024
    sandv = 1.0 + 0.05 * _pnoise((N2, W), 2, rng)
    chips = _pfbm((N2, W), 18, rng, 3)
    chip = np.clip((chips - 0.4) * 2, 0, 1)
    bot = sandv * (1 - chip) + chip * (0.78 + 0.25 * det[1024:]) * (0.85 + 0.1 * _pnoise((N2, W), 6, rng))
    gray = np.concatenate([top, bot], 0)
    base_block = np.array([208, 193, 168], float)
    base_sand = np.array([232, 204, 156], float)
    w_sand = np.zeros((W, W))
    w_sand[1024:] = 1 - chip
    # 石面帶點淡黃、灰的色斑
    hue = _pfbm((W, W), 120, rng, 3)
    colb = base_block[None, None, :] * np.stack([1 + 0.015 * hue, 1 + 0.0 * hue, 1 - 0.02 * hue], -1)
    col = colb * (1 - w_sand[..., None]) + base_sand[None, None, :] * w_sand[..., None]
    img = col * gray[..., None]
    _save(img, "block_diff.jpg")
    hgt[:1024] += 0.15 * det[:1024] - 0.6 * pits[:1024]
    hgt[1024:] = chip * 0.8 + 0.1 * _pnoise((N2, W), 3, rng)
    from PIL import Image

    Image.fromarray(_normal_map(hgt * 6.0, 1.0)).resize((1024, 1024), Image.LANCZOS).save(os.path.join(GEN, "block_nor.jpg"), quality=88)


def gen_casing(rng):
    """卡夫拉頂部外殼：平滑石灰岩、淡淡的層縫、縱向雨痕。1024 px ≈ 6 m"""
    N = 1024
    det = _rock_detail((N, N))
    v = 0.96 + 0.05 * (det - 1) + 0.035 * _pfbm((N, N), 60, rng, 3)
    yy = np.arange(N)[:, None]
    seams = np.zeros((N, N))
    for k in range(6):
        y = int(k * N / 6 + rng.uniform(-8, 8)) % N
        seams += np.exp(-(((yy - y) % N) / 1.6) ** 2)
    v -= 0.08 * seams
    streak = _pnoise((N, N // 8), 6, rng)
    streak = np.repeat(streak, 8, 1)
    streak = np.clip(streak - 0.8, 0, None)
    v -= 0.05 * streak
    pits = np.clip(_pnoise((N, N), 2.5, rng) - 2.0, 0, None)
    v -= 0.25 * pits
    base = np.array([186, 172, 154], float)
    _save(base[None, None, :] * v[..., None], "casing_diff.jpg")
    _save(_normal_map(-seams * 2 - pits * 3 + 0.2 * det, 1.0), "casing_nor.jpg")


def ensure_textures():
    if os.path.exists(os.path.join(GEN, "casing_nor.jpg")):
        return
    os.makedirs(GEN, exist_ok=True)
    rng = np.random.default_rng(7)
    gen_sand(rng)
    gen_blocks(rng)
    gen_casing(rng)


# ====================================================================== 共用工具
def n2(x, y, s, seed=0.0):
    return noise.noise(Vector((x * s + seed, y * s - seed * 0.7, seed * 0.31)))


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


def make_mat(name, diff, nor=None, nor_strength=1.0, rough=0.9):
    """貼圖 × 頂點色（glTF 輸出為 baseColorTexture + COLOR_0）"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(diff, check_existing=True)
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    nt.links.new(img.outputs["Color"], mix.inputs[6])
    nt.links.new(vc.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    if nor:
        nimg = nt.nodes.new("ShaderNodeTexImage")
        nimg.image = bpy.data.images.load(nor, check_existing=True)
        nimg.image.colorspace_settings.name = "Non-Color"
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nmap.inputs["Strength"].default_value = nor_strength
        nt.links.new(nimg.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = rough
    return m


class Acc:
    """自帶 UV 與頂點色的網格累加器（與 lib.Builder 的世界投影 UV 分開）"""

    def __init__(self, name, mats):
        self.name = name
        self.mats = mats
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.col = self.bm.loops.layers.color.new("Col")

    def v(self, co):
        return self.bm.verts.new(co)

    def face(self, verts, mi, uvs, cols, smooth_=False):
        try:
            f = self.bm.faces.new(verts)
        except ValueError:
            return None
        f.material_index = mi
        f.smooth = smooth_
        for l, uv, c in zip(f.loops, uvs, cols):
            l[self.uv].uv = uv
            l[self.col] = clamp01(c)
        return f

    def finish(self):
        self.bm.normal_update()
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(obj)
        return obj


class Painter:
    """lib.Builder 網格的頂點色（每個面角）；材質以 Multiply 混入貼圖，glTF 輸出為 COLOR_0"""

    def __init__(self, b):
        self.b = b
        self.cl = b.bm.loops.layers.color.new("Col")
        self.mark = b.bm.faces.layers.int.new("painted")

    def faces_of(self, verts):
        return {f for v in verts for f in v.link_faces}

    def paint(self, faces, fn):
        cl, mk = self.cl, self.mark
        for f in faces:
            f[mk] = 1
            for l in f.loops:
                l[cl] = clamp01(fn(f, l.vert.co))

    def pv(self, verts, fn):
        self.paint(self.faces_of(verts), fn)

    def finish(self):
        cl, mk = self.cl, self.mark
        for f in self.b.bm.faces:
            if not f[mk]:
                for l in f.loops:
                    l[cl] = (1.0, 1.0, 1.0, 1.0)
        self.b.bm.faces.layers.int.remove(mk)
        for m in self.b.mats:
            nt = m.node_tree
            bsdf = nt.nodes["Principled BSDF"]
            links = bsdf.inputs["Base Color"].links
            vc = nt.nodes.new("ShaderNodeVertexColor")
            vc.layer_name = "Col"
            if links:
                src = links[0].from_socket
                mix = nt.nodes.new("ShaderNodeMix")
                mix.data_type = "RGBA"
                mix.blend_type = "MULTIPLY"
                mix.inputs["Factor"].default_value = 1.0
                nt.links.new(src, mix.inputs[6])
                nt.links.new(vc.outputs["Color"], mix.inputs[7])
                nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
            else:
                nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])


# ====================================================================== 場址配置
KH = (0.0, 0.0, 230.3, 230.3)
KF = (-328.0, -344.0, 215.3, 215.3)
MK = (-569.0, -743.0, 102.2, 104.6)
SPH = (330.0, -432.0)
CAM_XY = (-760.0, -1290.0)  # 參考照拍攝位置（相機）
HEAD = math.radians(25.5)  # 相機朝向（由北往東）
CX, CY, RAD = -250.0, -450.0, 2600.0  # 地景圓心與半徑
MKQ = [(-522.0, -846.0), (-580.0, -846.0), (-636.0, -846.0)]  # 孟卡拉王后金字塔 G3-a/b/c


def trend(x, y):
    # 高原往東南緩降，東側為下降到尼羅河谷的崖坡
    return -0.017 * (x + 0.35 * y) - 14.0 * smooth(250, 520, x) - 4.0 * smooth(-900, -1300, y)


def heaps():
    """參考照右下的採石場廢料堆：(x, y, 半徑, 高)"""
    fx, fy = math.sin(HEAD), math.cos(HEAD)
    rx, ry = math.cos(HEAD), -math.sin(HEAD)
    return [(CAM_XY[0] + L * rx + F * fx, CAM_XY[1] + L * ry + F * fy, R, h) for L, F, R, h in ((45, 300, 28, 6.0), (95, 345, 24, 5.0), (-25, 265, 14, 2.5))]


HEAPS = []


def foot_dist(x, y):
    """到最近金字塔基座邊緣的距離（內部為負）"""
    best = 1e9
    for cx, cy, w, d in (KH, KF, MK):
        best = min(best, max(abs(x - cx) - w / 2, abs(y - cy) - d / 2))
    for qx, qy in MKQ:
        best = min(best, max(abs(x - qx), abs(y - qy)) - 21)
    return best


# ====================================================================== 地形
class Terrain:
    def __init__(self, rng):
        self.rng = rng
        HEAPS[:] = heaps()
        self.pads = []
        self.zKH = self.pad(KH[0], KH[1], 130, 130, 90)
        self.zKF = self.pad(KF[0], KF[1], 122, 122, 90, extra=3.0)
        self.zMK = self.pad(MK[0], MK[1], 62, 64, 70)
        self.zQ = [self.pad(qx, qy, 26, 26, 40) for qx, qy in MKQ]
        sx, sy = SPH
        self.floor_z = trend(sx, sy) - 8.5

    def pad(self, cx, cy, hx, hy, ramp, extra=0.0):
        z = trend(cx, cy) + extra
        self.pads.append((cx, cy, hx, hy, z, ramp))
        return z

    def hollow(self, x, y):
        lx, ly = x - SPH[0], y - SPH[1]
        return -55 < lx < 46 and -26 < ly < 26

    def mound(self, x, y):
        """金字塔腳下的碎石沙堆"""
        t = 0.0
        for (cx, cy, w, d), h in ((KH, 5.0), (KF, 4.5), (MK, 4.0)):
            e = max(abs(x - cx) - w / 2, abs(y - cy) - d / 2)
            if -12 < e < 60:
                t += h * math.exp(-((e - 4) / 13.0) ** 2) * (0.7 + 0.5 * n2(x, y, 0.05, 3.0))
        for qx, qy in MKQ:
            e = max(abs(x - qx), abs(y - qy)) - 21
            if -8 < e < 30:
                t += 2.2 * math.exp(-((e - 2) / 8.0) ** 2) * (0.7 + 0.5 * n2(x, y, 0.08, 5.0))
        for hx, hy, R, h in HEAPS:
            d2 = ((x - hx) / (R * 1.6)) ** 2 + ((y - hy) / (R * 0.8)) ** 2
            if d2 < 4:
                t += h * math.exp(-d2 * 1.3) * (0.8 + 0.3 * n2(x, y, 0.1, 2.0))
        return t

    def height(self, x, y):
        z = trend(x, y)
        # 各向異性沙丘（盛行風西北→東南，脊線垂直風向）
        a = math.radians(35)
        u = x * math.cos(a) + y * math.sin(a)
        v = -x * math.sin(a) + y * math.cos(a)
        ridge = 1.0 - abs(fbm(u * 0.3, v, 0.02, 2, 4.2))
        dunes = 2.8 * fbm(u * 0.35, v, 0.01, 3, 1.7) + 2.6 * ridge * ridge + 0.5 * n2(u * 0.5, v, 0.06, 8.0)
        rolling = 6.0 * fbm(x, y, 0.0016, 3, 1.1)
        w = 1.0
        for cx, cy, hx, hy, pz, ramp in self.pads:
            e = max(abs(x - cx) - hx, abs(y - cy) - hy)
            if e < ramp:
                k = smooth(0, ramp, e)
                z = z * k + pz * (1 - k)
            w = min(w, smooth(0, ramp * 2.5, e))
        # 參考照拍攝處：西南方較高的沙丘
        dc = math.hypot(x - CAM_XY[0], y - CAM_XY[1])
        z += 2.0 * math.exp(-(dc / 200.0) ** 2)
        lx, ly = x - SPH[0], y - SPH[1]
        if self.hollow(x, y):
            return self.floor_z
        east = smooth(70, 30, abs(ly + 15)) * smooth(30, 50, lx) * smooth(230, 130, lx)
        z = z * (1 - east) + (self.floor_z + 0.3) * east
        w = min(w, 1 - east, min(1.0, max(0.0, (math.hypot(lx, ly) - 70) / 120)))
        return z + (dunes + rolling) * (0.2 + 0.8 * w) + self.mound(x, y)

    def spacing(self, x, y):
        dx, dy = x - CAM_XY[0], y - CAM_XY[1]
        d = math.hypot(dx, dy) + 1e-6
        cosang = (dx * math.sin(HEAD) + dy * math.cos(HEAD)) / d
        if cosang > math.cos(math.radians(33)):
            s = 0.017 * d
        elif cosang > math.cos(math.radians(50)):
            s = 0.035 * d
        else:
            s = 0.07 * d
        s = min(max(s, 1.6), 110.0)
        e = foot_dist(x, y)
        if e < 0:
            s = max(s, 25.0) if e < -15 else min(s, 6.0)
        else:
            s = min(s, 5.0 + 0.12 * e)
        ls = math.hypot(x - SPH[0], y - SPH[1])
        s = min(s, 4.0 + 0.1 * max(0.0, ls - 60))
        return s

    def tracks(self):
        """車轍：相機座標系（側向 L、前方 F）的控制點 → 世界座標折線"""
        fx, fy = math.sin(HEAD), math.cos(HEAD)
        rx, ry = math.cos(HEAD), -math.sin(HEAD)
        defs = [
            [(-420, 120), (-200, 165), (-40, 200), (120, 215), (300, 200), (520, 240)],
            [(-300, 300), (-120, 260), (60, 280), (200, 330), (380, 420)],
            [(-160, 95), (-60, 140), (30, 190), (90, 260), (160, 345)],
            [(250, 130), (180, 190), (150, 260), (175, 330), (260, 420)],
        ]
        out = []
        for ctrl in defs:
            pts = [Vector((CAM_XY[0] + L * rx + F * fx, CAM_XY[1] + L * ry + F * fy)) for L, F in ctrl]
            # Catmull-Rom 取樣
            P = [pts[0]] + pts + [pts[-1]]
            line = []
            for i in range(1, len(P) - 2):
                p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
                L = (p2 - p1).length
                n = max(2, int(L / 2.5))
                for k in range(n):
                    t = k / n
                    t2, t3 = t * t, t * t * t
                    q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
                    line.append(q)
            line.append(pts[-1])
            out.append(line)
        return out

    def build(self, acc, mi):
        rng = self.rng
        pts = []
        # 四分樹自適應取點
        half = RAD + 20

        def rec(x0, y0, size, depth):
            cxm, cym = x0 + size / 2, y0 + size / 2
            if math.hypot(cxm - CX, cym - CY) - size * 0.71 > RAD:
                return
            s = min(self.spacing(cxm, cym), *(self.spacing(x0 + a * size, y0 + c * size) for a in (0, 1) for c in (0, 1)))
            if size > s * 1.7 and depth < 14:
                h = size / 2
                for a in (0, 1):
                    for c in (0, 1):
                        rec(x0 + a * h, y0 + c * h, h, depth + 1)
                return
            px = cxm + rng.uniform(-0.35, 0.35) * size
            py = cym + rng.uniform(-0.35, 0.35) * size
            if math.hypot(px - CX, py - CY) < RAD - 5:
                pts.append((px, py))

        rec(CX - half, CY - half, 2 * half, 0)
        # 外緣圓
        nb = 360
        for i in range(nb):
            a = TAU * i / nb
            pts.append((CX + RAD * math.cos(a), CY + RAD * math.sin(a)))
        # 車轍約束邊
        tracks = self.tracks()
        tagged = {}
        edges = []
        cl_pts = [q for line in tracks for q in line]
        # 移除太靠近車轍中線的隨機點（避免切碎轍面）
        grid = {}
        for q in cl_pts:
            grid.setdefault((int(q.x // 4), int(q.y // 4)), []).append(q)

        def near_track(x, y):
            gx, gy = int(x // 4), int(y // 4)
            for i in (-1, 0, 1):
                for j in (-1, 0, 1):
                    for q in grid.get((gx + i, gy + j), ()):
                        if (q.x - x) ** 2 + (q.y - y) ** 2 < 2.6**2:
                            return True
            return False

        pts = [p for p in pts if not near_track(*p)]
        verts = [Vector(p) for p in pts]
        self.ruts = []
        for ti, line in enumerate(tracks):
            for side_off in (-0.85, 0.85):
                for bound in (-0.21, 0.21):
                    start = len(verts)
                    for k, q in enumerate(line):
                        a = line[min(k + 1, len(line) - 1)] - line[max(k - 1, 0)]
                        nrm = Vector((-a.y, a.x)).normalized()
                        verts.append(q + nrm * (side_off + bound))
                        tagged[len(verts) - 1] = (ti, side_off)
                    for k in range(len(line) - 1):
                        edges.append((start + k, start + k + 1))
        res = delaunay_2d_cdt(verts, edges, [], 0, 1e-4)
        vco, _, faces, orig_v = res[0], res[1], res[2], res[3]
        vtag = [None] * len(vco)
        for i, ov in enumerate(orig_v):
            for o in ov:
                if o in tagged:
                    vtag[i] = tagged[o]
        hz = [self.height(p.x, p.y) for p in vco]
        bv = [acc.v((p.x, p.y, z)) for p, z in zip(vco, hz)]
        self.n_faces = 0

        def col(x, y, z, rut):
            big = fbm(x, y, 0.003, 3, 2.0)
            v = 0.93 + 0.07 * big + 0.03 * n2(x, y, 0.05, 3.0) + 0.02 * n2(x, y, 0.2, 5.0)
            r, g, b = v, v * (0.985 + 0.015 * big), v * (0.97 + 0.03 * big)
            # 碎石、礫石斑（灰褐）
            hp = max([math.exp(-(((x - hx) / (R * 1.6)) ** 2 + ((y - hy) / (R * 0.8)) ** 2)) for hx, hy, R, _ in HEAPS] + [0.0])
            grav = smooth(0.15, 0.75, fbm(x, y, 0.012, 3, 9.0) + 0.6 * math.exp(-max(0.0, foot_dist(x, y)) / 45.0) + 1.2 * hp)
            grav *= 0.55
            r, g, b = r * (1 - grav) + 0.8 * grav, g * (1 - grav) + 0.74 * grav, b * (1 - grav) + 0.66 * grav
            if rut:
                r, g, b = r * 0.82, g * 0.78, b * 0.74
            # 遠處淡入地平線（偏淡、去飽和）
            dd = math.hypot(x - CX, y - CY) / RAD
            k = smooth(0.7, 1.0, dd)
            r, g, b = r * (1 - k) + 0.97 * k, g * (1 - k) + 0.95 * k, b * (1 - k) + 0.93 * k
            return (r, g, b)

        for f in faces:
            vs = [bv[i] for i in f]
            # 逆時針朝上
            a, c, d = vs[0].co, vs[1].co, vs[2].co
            if (c.x - a.x) * (d.y - a.y) - (c.y - a.y) * (d.x - a.x) < 0:
                f = list(reversed(f))
                vs = [bv[i] for i in f]
            tags = [vtag[i] for i in f]
            rut = tags[0] is not None and all(t == tags[0] for t in tags)
            if rut:
                # 需同時含兩側邊界點（避免沿同一條邊的狹長三角形誤判）
                pass
            uvs = [(v.co.x / 6.0, v.co.y / 6.0) for v in vs]
            cols = [col(v.co.x, v.co.y, v.co.z, rut) for v in vs]
            acc.face(vs, mi, uvs, cols, smooth_=True)
        # 外緣裙邊（往下 12 m）
        tf = list(acc.bm.faces)
        for f in tf:
            for e in f.edges:
                if len(e.link_faces) == 1:
                    v1, v2 = e.verts
                    # 依面的迴圈方向決定裙邊順序
                    for l in f.loops:
                        if l.edge is e:
                            v1, v2 = l.vert, l.link_loop_next.vert
                    b1 = acc.v((v1.co.x, v1.co.y, v1.co.z - 12))
                    b2 = acc.v((v2.co.x, v2.co.y, v2.co.z - 12))
                    acc.face([v2, v1, b1, b2], mi, [(0, 0), (1, 0), (1, 0.2), (0, 0.2)], [(0.9, 0.86, 0.8)] * 4)
        self.bvh = BVHTree.FromBMesh(acc.bm)

    def ground(self, x, y):
        hit = self.bvh.ray_cast(Vector((x, y, 800.0)), Vector((0, 0, -1)))
        if hit[0] is None:
            return self.height(x, y)
        return hit[0].z


# ====================================================================== 逐層石階金字塔
def step_pyramid(A, rng, cx, cy, z0, bx, by, H, H_now, course, seg, amp, seed, tone, casing_from=None, inset=0.8,
                 base_dark=None, haze=0.0, MB=0, MC=1):
    """A: Acc；MB 石塊圖集材質、MC 外殼材質。tone = 整座的頂點色倍率"""
    hx0, hy0 = bx / 2, by / 2
    slope_x, slope_y = hx0 / H, hy0 / H
    zs = [-3.0]
    z = 0.0
    while z < H_now - 0.3:
        zs.append(z)
        z += course * rng.uniform(0.8, 1.2)
    zs.append(H_now)
    if casing_from is not None:
        zs = [zz for zz in zs if zz < casing_from + 10] + [casing_from + 10]
    n = len(zs)
    per = []
    for s in range(4):
        for j in range(seg):
            t = 0.5 - 0.5 * math.cos(math.pi * j / seg)  # 角落附近取樣較密
            per.append((s, t))
    m = len(per)
    sideL = [bx, by, bx, by]
    arc = [sum(sideL[:s]) + t * sideL[s] for s, t in per]
    arc_end = sum(sideL)

    def base_pt(s, t, hx, hy):
        corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
        a, c = corners[s], corners[(s + 1) % 4]
        return a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t

    normals = [(0, -1), (1, 0), (0, 1), (-1, 0)]

    def erosion(k, s, t):
        z = zs[k]
        px, py = base_pt(s, t, hx0, hy0)
        e = amp * (0.55 + 0.45 * fbm(px, py + z * 2.0, 0.035, 2, seed))
        e += amp * 0.9 * max(0.0, fbm(px * 0.7, z, 0.06, 2, seed + 5)) ** 2 * 3
        dc = min(t, 1 - t) * sideL[s]
        e += amp * 4.5 * max(0.0, 1 - dc / 18.0) ** 1.5 * (0.4 + 1.0 * rng.random())
        return e

    D = [[0.0] * m for _ in range(n)]
    for k in range(n - 1, -1, -1):
        tread = (zs[k + 1] - max(zs[k], 0) if k < n - 1 else course) * slope_x
        tread = max(tread, 0.05)
        for q, (s, t) in enumerate(per):
            d = erosion(k, s, t) + rng.uniform(0, 0.6) * course * slope_x
            if rng.random() < 0.1:
                d += course * slope_x * rng.uniform(0.8, 2.0)
            if k < n - 1:
                d = min(d, D[k + 1][q] + tread * 0.92)
            if k == 0:
                d = min(d, 0.6)
            D[k][q] = d

    rings = []
    for k in range(n):
        z = zs[k]
        hx = hx0 - slope_x * max(z, 0) - inset
        hy = hy0 - slope_y * max(z, 0) - inset
        if z < 0:
            hx, hy = hx0 - inset + 0.3, hy0 - inset + 0.3
        ring = []
        for q, (s, t) in enumerate(per):
            px, py = base_pt(s, t, hx, hy)
            d = D[k][q]
            nx, ny = normals[s]
            if t == 0:
                pnx, pny = normals[(s - 1) % 4]
                px -= (nx + pnx) * d * 0.75
                py -= (ny + pny) * d * 0.75
            else:
                px -= nx * d
                py -= ny * d
            ring.append((cx + px, cy + py))
        rings.append(ring)

    course_tone = [rng.uniform(0.88, 1.04) for _ in range(n)]
    uoff = [rng.uniform(0, 8) for _ in range(n)]
    vr = [[rng.uniform(0.86, 1.06) for _ in range(m)] for _ in range(n)]
    tr, tg, tb = tone

    def col(k, q, x, y, z, top):
        lx, ly = x - cx, y - cy
        zz = z - z0
        blot = fbm(lx + zz * 0.5, ly - zz * 0.3, 0.02, 3, seed + 2)
        v = course_tone[k] * vr[k][q] * (0.93 + 0.08 * blot)
        streak = max(0.0, fbm(lx * 0.08 + ly * 0.08, zz * 0.012, 0.9, 2, seed + 9)) * 0.12
        v *= 1 - streak
        r, g, b = tr * v, tg * v, tb * v
        if top:  # 階面積沙
            r, g, b = r * 1.1, g * 1.07, b * 1.0
        else:
            r, g, b = r * 0.9, g * 0.9, b * 0.9
        if base_dark and zz < base_dark[0]:
            c = base_dark[1]
            kk = (1 - zz / base_dark[0]) * 0.8
            r, g, b = r * (1 - kk) + c[0] * kk, g * (1 - kk) + c[1] * kk, b * (1 - kk) + c[2] * kk
        if zz < 4:  # 底部沾沙
            kk = (1 - max(zz, 0) / 4) * 0.3
            r, g, b = r * (1 - kk) + 0.98 * kk, g * (1 - kk) + 0.88 * kk, b * (1 - kk) + 0.7 * kk
        if haze:
            r, g, b = r * (1 - haze) + 0.95 * haze, g * (1 - haze) + 0.95 * haze, b * (1 - haze) + 0.96 * haze
        return (r, g, b)

    # 豎面與階面各自一組頂點（平滑著色只在同一列內平均，石階邊仍銳利；glTF 匯出時可共用頂點）
    for k in range(n - 1):
        r_ = k % 4
        v_lo, v_hi = 1 - (r_ + 1) / 8 + 0.002, 1 - r_ / 8 - 0.002
        z_a, z_b = z0 + zs[k], z0 + zs[k + 1]
        RA = [A.v((x, y, z_a)) for x, y in rings[k]]
        RB = [A.v((x, y, z_b)) for x, y in rings[k]]
        TA = [A.v((x, y, z_b)) for x, y in rings[k]]
        TB = [A.v((x, y, z_b)) for x, y in rings[k + 1]]
        cA = [col(k, q, x, y, z_a, False) for q, (x, y) in enumerate(rings[k])]
        cB = [col(k, q, x, y, z_b, False) for q, (x, y) in enumerate(rings[k])]
        tA = [col(k, q, x, y, z_b, True) for q, (x, y) in enumerate(rings[k])]
        tB = [col(k + 1, q, x, y, z_b, True) for q, (x, y) in enumerate(rings[k + 1])]
        dd = [0.01 + min(math.hypot(x2 - x1, y2 - y1), 3.8) / 8 for (x1, y1), (x2, y2) in zip(rings[k], rings[k + 1])]
        for q in range(m):
            r = (q + 1) % m
            a0 = arc[q] / 8 + uoff[k]
            a1 = (arc[r] if r else arc_end) / 8 + uoff[k]
            A.face([RA[q], RA[r], RB[r], RB[q]], MB, [(a0, v_lo), (a1, v_lo), (a1, v_hi), (a0, v_hi)], [cA[q], cA[r], cB[r], cB[q]], True)
            A.face([TA[q], TA[r], TB[r], TB[q]], MB, [(a0, 0.01), (a1, 0.01), (a1, dd[r]), (a0, dd[q])], [tA[q], tA[r], tB[r], tB[q]], True)
    if casing_from is None:
        top = [A.v((x, y, z0 + zs[-1])) for x, y in rings[-1]]
        A.face(top, MB, [((x - cx) / 8, 0.01 + min(abs(y - cy), 3.0) / 8) for x, y in rings[-1]],
               [col(n - 1, q, x, y, z0 + zs[-1], True) for q, (x, y) in enumerate(rings[-1])], True)
        return

    # 卡夫拉頂部原始外殼（平滑、偏亮），下緣不規則
    V = 10
    cs = 40  # 外殼周長取樣（每邊），下緣較細碎
    cper = [(sd, j / cs) for sd in range(4) for j in range(cs)]
    cm = len(cper)
    carc = [sum(sideL[:sd]) + t * sideL[sd] for sd, t in cper]
    zl = []
    for q, (sd, t) in enumerate(cper):
        z = casing_from + 2.2 * fbm(sd * 9.0 + t * 7.0, 0, 0.9, 2, seed + 3) + 1.0 * math.sin(t * TAU * 1.5 + sd)
        z += rng.uniform(-1.2, 1.2) + (course * rng.randint(1, 3) if rng.random() < 0.15 else 0)
        zl.append(round(z / course) * course)  # 依石層高度量化，邊緣呈階梯狀崩落
    ztop = H_now
    cring = []
    for vv in range(V + 1):
        f = (vv / V) ** 0.8
        ring = []
        for q, (sd, t) in enumerate(cper):
            z = zl[q] + (ztop - zl[q]) * f
            hx, hy = hx0 - slope_x * z, hy0 - slope_y * z
            px, py = base_pt(sd, t, hx, hy)
            ring.append(A.v((cx + px, cy + py, z0 + z)))
        cring.append(ring)

    def ccol(co):
        x, y, z = co.x - cx, co.y - cy, co.z - z0
        v = 0.86 + 0.08 * fbm(x + y, z, 0.05, 3, 4)
        streak = 0.12 * max(0.0, fbm((x + y) * 0.25, z * 0.02, 0.2, 2, 7))
        low = 0.1 * max(0.0, 1 - (z - casing_from) / 12.0)
        r, g, b = v * (0.96 - streak - low), v * (0.92 - streak - low), v * (0.86 - streak * 1.2 - low * 1.2)
        if haze:
            r, g, b = r * (1 - haze) + 0.95 * haze, g * (1 - haze) + 0.95 * haze, b * (1 - haze) + 0.96 * haze
        return (r, g, b)

    def cu(q):
        return (carc[q] if q < cm else sum(sideL)) / 6.0

    for vv in range(V):
        for q in range(cm):
            r = (q + 1) % cm
            vs = [cring[vv][q], cring[vv][r], cring[vv + 1][r], cring[vv + 1][q]]
            us = [cu(q), cu(r if r else cm), cu(r if r else cm), cu(q)]
            A.face(vs, MC, [(u, v.co.z / 6.0) for u, v in zip(us, vs)], [ccol(v.co) for v in vs])
    A.face(cring[-1], MC, [(v.co.x / 6, v.co.y / 6) for v in cring[-1]], [ccol(v.co) for v in cring[-1]])
    # 外殼下緣厚度：往內收到核心石階（斷面）
    lip = []
    for q, (sd, t) in enumerate(cper):
        z = zl[q]
        hx, hy = hx0 - slope_x * z - inset - 1.2, hy0 - slope_y * z - inset - 1.2
        px, py = base_pt(sd, t, hx, hy)
        lip.append(A.v((cx + px, cy + py, z0 + z)))
    for q in range(cm):
        r = (q + 1) % cm
        vs = [lip[q], lip[r], cring[0][r], cring[0][q]]
        A.face(vs, MC, [(cu(q), 0), (cu(r if r else cm), 0), (cu(r if r else cm), 0.2), (cu(q), 0.2)],
               [tuple(c * 0.75 for c in ccol(v.co)) for v in vs])


# ====================================================================== 獅身人面像
def loft(b, mi, sections, cap_start=True, cap_end=True):
    """以等點數的封閉截面依序相連；回傳頂點"""
    vr = [[b.bm.verts.new(p) for p in sec] for sec in sections]
    n = len(sections[0])
    faces = []
    for a, c in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append(b.bm.faces.new([a[i], a[j], c[j], c[i]]))
    if cap_start:
        faces.append(b.bm.faces.new(list(reversed(vr[0]))))
    if cap_end:
        faces.append(b.bm.faces.new(vr[-1]))
    for f in faces:
        f.material_index = mi
        f.smooth = True
    return [v for r in vr for v in r], faces


def build_sphinx(b, P, stone, rockm, sx, sy, fz, height):
    """面向 +X（東）。局部座標：x 前後、y 左右、z 自坑底起算"""
    rng = b.rng

    def W(x, y, z):
        return Vector((sx + x, sy + y, fz + z))

    def section(x, hw, h, n=20, bottom=-1.0, squ=2.6):
        """圓角矩形（超橢圓）截面，底部埋入地面"""
        pts = []
        for i in range(n):
            a = TAU * i / n
            c, s = math.cos(a), math.sin(a)
            yy = hw * math.copysign(abs(c) ** (2 / squ), c)
            zz = (h / 2) * math.copysign(abs(s) ** (2 / squ), s) + h / 2
            zz = max(zz, bottom)
            pts.append((x, yy, zz))
        return pts

    def erode(co_local):
        x, y, z = co_local
        # 水平風化層紋：較軟岩層被侵蝕成凹槽
        g = 0.28 * (0.5 + 0.5 * math.sin(z * TAU / 1.7 + 1.5 * noise.noise(Vector((x * 0.08, y * 0.08, z * 0.1)))))
        g += 0.12 * noise.noise(Vector((x * 0.4, y * 0.4, z * 0.4)))
        return g

    # 身體（臀 → 胸），長約 56 m
    prof = [(-46, 4.5, 6.0), (-44, 7.2, 9.0), (-40, 8.6, 11.0), (-34, 9.3, 12.0), (-27, 9.0, 11.6), (-18, 8.4, 11.2),
            (-8, 8.4, 11.6), (0, 8.9, 12.4), (5, 9.2, 13.0), (9, 8.8, 13.2), (11, 7.6, 12.6), (12, 5.5, 11.0)]
    secs = []
    for x, hw, h in prof:
        sec = []
        for (px, py, pz) in section(x, hw, h):
            r = erode((px, py, pz))
            k = 1 - r / max(hw, 1.0)
            sec.append(W(px, py * k, pz - (r * 0.5 if pz > h * 0.8 else 0)))
        secs.append(sec)
    vs, fs = loft(b, stone, secs)

    def body_col(f, co):
        z = co.z - fz
        n = noise.noise(Vector(((co.x - sx) * 0.2, (co.y - sy) * 0.2, z * 0.3)))
        band = 0.06 * math.sin(z * TAU / 1.7)
        if z < 3.0:  # 下段的後世修補石塊，較淺黃
            return (0.98 + 0.02 * n, 0.9 + 0.03 * n, 0.74)
        v = 0.9 + 0.05 * n + band
        return (v * 1.0, v * 0.82, v * 0.62)

    P.paint(fs, body_col)
    # 尾巴（沿右臀側盤繞）
    tail = []
    for i in range(10):
        t = i / 9
        tail.append((-44 + t * 10, -8.2 - 0.6 * math.sin(t * math.pi), 0.8 + 0.3 * t))
    for i in range(9):
        a, c = Vector(tail[i]), Vector(tail[i + 1])
        vs = b.cyl(stone, 0.55, 0.5, (c - a).length, tuple(W(*a)), seg=8, rot=(0, math.pi / 2, math.atan2(c.y - a.y, c.x - a.x)))
        P.pv(vs, body_col)

    # 前爪（長約 15 m），兩爪間為圖特摩斯四世的夢境石碑
    for side in (-1, 1):
        cy = side * 4.6
        secs = []
        for x, hw, h in ((9, 2.0, 3.6), (14, 1.9, 2.9), (20, 1.8, 2.5), (25, 1.8, 2.3), (27.0, 1.5, 2.0), (27.8, 0.9, 1.4)):
            secs.append([W(px, py + cy, pz) for (px, py, pz) in section(x, hw, h, n=14, squ=3.0)])
        vs, fs = loft(b, stone, secs)
        P.paint(fs, lambda f, co: (0.97, 0.88, 0.72))
        # 腳趾
        for k in range(4):
            vs = b.rock(stone, (1.4, 0.8, 0.9), tuple(W(27.6, cy + (k - 1.5) * 0.85, 0.45)), rough=0.05, subdiv=1, seed=k + 40 + side)
            P.pv(vs, lambda f, co: (0.95, 0.86, 0.7))
    vs = b.box_base(b.color("stela", "#5e504c", rough=0.5), (0.7, 4.0, 3.6), tuple(W(11.8, 0, 0)))
    # 頸
    neck = [section(x, hw, h) for x, hw, h in ((4, 4.0, 15.0), (8, 3.8, 15.5), (10.5, 3.4, 15.0))]
    vs, fs = loft(b, stone, [[W(*p) for p in s] for s in neck])
    P.paint(fs, body_col)

    # 頭巾（nemes）：以水平截面堆疊，下段兩側垂片張開至肩
    def nemes_sec(z, hw_back, hw_front, x_back, x_front, n=24):
        xc, hd = (x_back + x_front) / 2, (x_front - x_back) / 2
        pts = []
        for i in range(n):
            a = TAU * i / n
            c, s = math.cos(a), math.sin(a)
            hw = hw_front if c > 0 else hw_back
            xx = xc + hd * math.copysign(abs(c) ** (2 / 3.2), c)
            yy = hw * math.copysign(abs(s) ** (2 / 3.2), s)
            pts.append(W(xx, yy, z))
        return pts

    levels = [(11.0, 6.4, 5.6, 1.5, 11.0), (12.5, 6.1, 5.4, 1.8, 11.2), (14.0, 5.0, 4.8, 2.4, 11.3), (15.5, 4.1, 4.0, 2.8, 11.2),
              (17.0, 3.7, 3.6, 3.1, 11.0), (18.5, 3.5, 3.3, 3.4, 10.8), (19.4, 3.1, 2.8, 3.8, 10.4), (20.0, 2.2, 1.8, 4.6, 9.6)]
    secs = [nemes_sec(*lv) for lv in levels]
    vs, fs = loft(b, stone, secs)

    def head_col(f, co):
        z = co.z - fz
        n = noise.noise(Vector(((co.x - sx) * 0.5, (co.y - sy) * 0.5, z * 0.5)))
        # 頭巾上殘存的條紋
        stripe = 0.05 * (1 if math.sin(z * TAU / 0.9) > 0 else -1)
        v = 0.86 + 0.05 * n + stripe
        return (v, v * 0.84, v * 0.68)

    P.paint(fs, head_col)
    # 臉：自頭巾前方突出（寬 4.1 m、高約 5 m），鼻已缺損
    face = []
    for z, hw, xf in ((12.4, 1.2, 12.0), (13.0, 1.7, 12.6), (14.0, 2.05, 12.9), (15.2, 2.1, 13.0), (16.4, 2.1, 13.1),
                      (17.4, 2.05, 13.1), (18.3, 1.9, 12.7), (18.9, 1.5, 12.0)):
        sec = []
        n = 16
        for i in range(n):
            a = TAU * i / n
            c, s = math.cos(a), math.sin(a)
            xx = 10.6 + (xf - 10.6) * (0.5 + 0.5 * c) ** 0.6 if c > -1 else 10.6
            yy = hw * s * (0.85 + 0.15 * abs(c))
            sec.append(W(xx, yy, z))
        face.append(sec)
    vs, fs = loft(b, stone, face)

    def face_col(f, co):
        z = co.z - fz
        y = co.y - sy
        x = co.x - sx
        v = 0.9 + 0.04 * noise.noise(Vector((x, y, z)))
        # 眼窩、口部陰影
        if 16.3 < z < 17.0 and 0.5 < abs(y) < 1.5 and x > 12.6:
            v *= 0.62
        if 14.3 < z < 14.6 and abs(y) < 0.9 and x > 12.6:
            v *= 0.7
        return (v, v * 0.83, v * 0.66)

    P.paint(fs, face_col)
    # 眉骨、殘鼻、耳
    vs = b.box(stone, (0.5, 3.6, 0.35), tuple(W(13.05, 0, 17.25)))
    P.pv(vs, face_col)
    vs = b.frustum(stone, (0.9, 0.9), (0.4, 0.5), 0.5, tuple(W(13.0, 0, 15.2)), rot_z=0)
    P.pv(vs, face_col)
    for s in (-1, 1):
        vs = b.rock(stone, (1.0, 0.5, 1.6), tuple(W(11.0, s * 2.35, 16.2)), rough=0.05, subdiv=1, seed=60 + s)
        P.pv(vs, face_col)

    # 圍坑岩壁（北、南、西側），頂與周圍高原同高
    def cliff(x0, x1, y0, y1):
        cxl, cyl = (x0 + x1) / 2, (y0 + y1) / 2
        top = max(height(sx + cxl + dx, sy + cyl + dy) for dx in (-(x1 - x0) / 2, 0, (x1 - x0) / 2) for dy in (-(y1 - y0) / 2, (y1 - y0) / 2))
        hgt = top - fz + 3.0
        vs = b.rock(rockm, (x1 - x0, y1 - y0, hgt + 2.0), tuple(W(cxl, cyl, hgt / 2 - 2.5)), rough=0.06, subdiv=4,
                    seed=rng.randint(0, 999), round_=0.06)

        def col(f, co):
            z = co.z - fz
            v = 0.86 + 0.06 * math.sin(z * TAU / 1.4) + 0.05 * noise.noise(Vector((co.x * 0.2, co.y * 0.2, z * 0.3)))
            return (v, v * 0.86, v * 0.7)

        P.pv(vs, col)

    cliff(-66, 34, 22.0, 40)
    cliff(-66, 34, -40, -22.0)
    cliff(-68, -51.5, -30, 30)


# ====================================================================== 主體
def giza(path):
    ensure_textures()
    b = Builder("Giza", seed=3)
    P = Painter(b)
    rng = b.rng
    stone = b.tex("stone", "rock_04", tile=3.0, tint="#d9c39c", normal=0, rough=0.9)
    granite = b.color("granite", "#6e5a52", rough=0.6)
    m_sand = make_mat("Giza_sand", os.path.join(GEN, "sand_diff.jpg"), os.path.join(GEN, "sand_nor.jpg"), 0.7, 0.95)
    m_block = make_mat("Giza_blocks", os.path.join(GEN, "block_diff.jpg"), os.path.join(GEN, "block_nor.jpg"), 1.0, 0.9)
    m_casing = make_mat("Giza_casing", os.path.join(GEN, "casing_diff.jpg"), os.path.join(GEN, "casing_nor.jpg"), 0.6, 0.75)

    # ------------------------------------------------------------ 地形
    T = Terrain(rng)
    ter = Acc("GizaGround", [m_sand])
    T.build(ter, 0)
    print('terrain verts', len(ter.bm.verts), 'faces', len(ter.bm.faces))
    ground = T.ground

    # ------------------------------------------------------------ 金字塔
    pyr = Acc("GizaKhufu", [m_block, m_casing])
    accs = [pyr]
    # 古夫（外殼全失，露出逐層石階；頂部約 10 m 平台）
    step_pyramid(pyr, rng, KH[0], KH[1], T.zKH, KH[2], KH[3], 146.6, 138.5, 1.4, 16, 1.0, 1.0,
                 tone=(0.84, 0.82, 0.8), haze=0.3)
    # 卡夫拉（頂部保留外殼）
    pyr = Acc("GizaKhafre", [m_block, m_casing])
    accs.append(pyr)
    step_pyramid(pyr, rng, KF[0], KF[1], T.zKF, KF[2], KF[3], 143.5, 136.4, 1.35, 16, 0.9, 2.0, casing_from=100.0, inset=1.2,
                 tone=(0.8, 0.76, 0.72), haze=0.12)
    # 孟卡拉（底部殘留紅色花崗岩外殼）
    pyr = Acc("GizaMenkaure", [m_block, m_casing])
    accs.append(pyr)
    step_pyramid(pyr, rng, MK[0], MK[1], T.zMK, MK[2], MK[3], 65.5, 61.0, 1.1, 18, 0.9, 3.0, tone=(0.74, 0.67, 0.6),
                 base_dark=(8.0, (0.55, 0.45, 0.4)))
    # 古夫的三座王后金字塔（G1-a/b/c，東側由北而南，已嚴重崩毀）
    for k, (qx, qy, qb, qh, now) in enumerate([(168, -12, 49.5, 30.2, 19.0), (163, -64, 49.0, 30.0, 17.5), (158, -113, 46.3, 29.6, 21.5)]):
        step_pyramid(pyr, rng, qx, qy, trend(qx, qy), qb, qb, qh, now, 1.4, 8, 1.4, 10.0 + k, tone=(0.88, 0.8, 0.7), haze=0.15)
    # 孟卡拉的三座王后金字塔：G3-a 為真金字塔（嚴重崩毀），G3-b / G3-c 為四層階梯
    qx, qy = MKQ[0]
    step_pyramid(pyr, rng, qx, qy, T.zQ[0], 44.3, 44.3, 28.4, 20.5, 0.9, 10, 1.6, 20.0, tone=(0.82, 0.72, 0.6))
    for k, (qx, qy) in enumerate(MKQ[1:]):
        zt = T.zQ[k + 1]
        tiers = [(33.0, 31.5, 5.2), (25.8, 24.6, 4.6), (19.0, 18.0, 4.2), (12.6, 11.8, 3.6)][: 4 if k else 4]
        for ti, (w, d, h) in enumerate(tiers):
            if k == 0 and ti == 3:
                h *= 0.6  # G3-b 頂層殘缺
            step_pyramid(pyr, rng, qx, qy, zt, w, d, h * 9.0, h, 0.72, 8, 1.3, 30.0 + k * 4 + ti, inset=0.0,
                         tone=(0.84 - 0.02 * ti, 0.75 - 0.02 * ti, 0.63 - 0.02 * ti))
            zt += h

    # ------------------------------------------------------------ 碎石塊（崩落石塊堆）
    def block(x, y, size, tone, sink=0.3):
        z = ground(x, y)
        sc = (size * rng.uniform(0.9, 1.7), size * rng.uniform(0.7, 1.1), size * rng.uniform(0.45, 0.8))
        vs = b.box(stone, sc, (x, y, z + sc[2] * (0.5 - sink)), rot=(rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), rng.uniform(0, TAU)))
        for v in vs:
            v.co.x += rng.uniform(-0.12, 0.12) * sc[0]
            v.co.y += rng.uniform(-0.12, 0.12) * sc[1]
            v.co.z += rng.uniform(-0.1, 0.1) * sc[2]
        t = rng.uniform(0.82, 1.06)
        P.pv(vs, lambda f, co: (tone[0] * t, tone[1] * t, tone[2] * t))

    def ring_pts(cx, cy, hw, hd, cnt, spread, inner=-2.0):
        for _ in range(cnt):
            s = rng.randrange(4)
            t = rng.uniform(-1.05, 1.05)
            off = inner + rng.uniform(0, 1) ** 2.2 * spread
            if s == 0:
                yield cx + t * hw, cy - hd - off, off
            elif s == 1:
                yield cx + hw + off, cy + t * hd, off
            elif s == 2:
                yield cx + t * hw, cy + hd + off, off
            else:
                yield cx - hw - off, cy + t * hd, off

    for (cx, cy, w, d), cnt, tone in ((KH, 200, (0.86, 0.8, 0.7)), (KF, 220, (0.84, 0.78, 0.68)), (MK, 420, (0.78, 0.68, 0.56))):
        for x, y, off in ring_pts(cx, cy, w / 2, d / 2, cnt, 30):
            block(x, y, rng.uniform(0.5, 1.6) * (1.5 if off < 5 else 1.0), tone)
    for qx, qy in MKQ:
        for x, y, off in ring_pts(qx, qy, 17, 17, 170, 14, inner=-1.0):
            block(x, y, rng.uniform(0.4, 1.3) * (1.4 if off < 4 else 1.0), (0.8, 0.68, 0.54))
    # 沙漠中散布的碎石
    for _ in range(300):
        a = rng.uniform(0, TAU)
        r = math.sqrt(rng.uniform(0, 1)) * 1400
        x, y = CX + r * math.cos(a), CY + r * math.sin(a)
        if foot_dist(x, y) < 6 or (abs(x - SPH[0]) < 110 and abs(y - SPH[1]) < 90):
            continue
        block(x, y, rng.uniform(0.3, 0.9), (0.84, 0.76, 0.64), sink=0.4)

    # ------------------------------------------------------------ 馬斯塔巴墓群（南北向長方、外牆內傾）
    def mastaba(x, y, w, d, h):
        z = ground(x, y) - 1.2
        vs = b.frustum(stone, (w, d), (w - h * 0.45, d - h * 0.45), h + 1.2, (x, y, z), rot_z=rng.uniform(-0.01, 0.01))
        tone = rng.uniform(0.8, 0.95)
        P.pv(vs, lambda f, co: (tone * (0.98 + 0.03 * n2(co.x, co.z, 0.5)), tone * 0.9, tone * 0.78))

    for gx0, gy0, ni, nj in ((-175, -40, 7, 9), (205, -130, 4, 7)):
        for i in range(ni):
            for j in range(nj):
                if rng.random() < 0.22:
                    continue
                x = gx0 - i * 34 if gx0 < 0 else gx0 + i * 30
                y = gy0 + j * 30 + rng.uniform(-3, 3)
                mastaba(x, y, rng.uniform(9, 13), rng.uniform(18, 26), rng.uniform(2.5, 6.5))

    # ------------------------------------------------------------ 神廟、參道
    sx, sy = SPH
    floor_z = T.floor_z

    def ruin(x, y, w, d, h, rot=0.0, tone=(0.86, 0.79, 0.68)):
        z = min(ground(x + dx, y + dy) for dx in (-w / 2, w / 2) for dy in (-d / 2, d / 2)) - 0.5
        vs = b.box_base(stone, (w, d, h + 1.0), (x, y, z), rot=(0, 0, rot))
        P.pv(vs, lambda f, co: tone)

    for dx, dy, w, d, h in ((0, 0, 50, 56, 4.5), (-38, 0, 20, 70, 6), (34, 0, 18, 30, 5)):
        ruin(KF[0] + 107.7 + 32 + dx, KF[1] + dy, w, d, h)
    ruin(MK[0] + 51 + 30, MK[1], 40, 48, 3.5)
    p0 = Vector((KF[0] + 107.7 + 58, KF[1] - 6))
    p1 = Vector((sx + 52, sy - 52))
    N = 40
    for i in range(N):
        a = p0.lerp(p1, i / N)
        c = p0.lerp(p1, (i + 1) / N)
        mid = (a + c) / 2
        L = (c - a).length + 0.4
        ang = math.atan2(c.y - a.y, c.x - a.x)
        z = min(ground(a.x, a.y), ground(c.x, c.y)) - 1.0
        vs = b.box_base(stone, (L, 6.0, 2.4), (mid.x, mid.y, z), rot=(0, 0, ang))
        P.pv(vs, lambda f, co: (0.88, 0.81, 0.7))
    ruin(sx + 58, sy - 50, 45, 45, 10.5)
    ruin(sx + 55, sy + 8, 46, 40, 6.5)
    b.box_base(granite, (20, 12, 0.6), (sx + 58, sy - 50, floor_z + 10.5 - 0.5))

    # ------------------------------------------------------------ 獅身人面像
    build_sphinx(b, P, stone, stone, sx, sy, floor_z, T.height)

    # ------------------------------------------------------------ 石灰岩露頭與採石場殘丘（參考照右下）
    for x, y, L, Wd, H, rot in ((-360, -820, 70, 22, 5.0, 0.3), (-300, -760, 45, 16, 4.0, -0.4), (-420, -900, 55, 18, 3.5, 0.1),
                                (-180, -700, 60, 20, 4.5, 0.6), (-900, -700, 80, 24, 4.0, 0.2), (-1000, -980, 60, 18, 3.0, -0.3)):
        z = ground(x, y)
        vs = b.rock(stone, (L, Wd, H * 2), (x, y, z - H * 0.55), rot=(0, 0, rot), rough=0.45, subdiv=3, seed=rng.randint(0, 9999), round_=0.2)
        P.pv(vs, lambda f, co: (0.78 + 0.08 * n2(co.x, co.y, 0.2), 0.68 + 0.07 * n2(co.x, co.y, 0.2), 0.55))

    # 參考照右下：採石場廢料堆（沙丘上覆深色碎石）
    fx, fy = math.sin(HEAD), math.cos(HEAD)
    rx, ry = math.cos(HEAD), -math.sin(HEAD)
    for (x0, y0, R0, _), cnt in zip(HEAPS, (160, 120, 90)):
        for _ in range(cnt):
            a = rng.uniform(0, TAU)
            r = R0 * math.sqrt(rng.uniform(0, 1))
            x, y = x0 + r * math.cos(a) * 1.6, y0 + r * math.sin(a) * 0.8
            block(x, y, rng.uniform(0.4, 1.4), (0.72, 0.64, 0.54), sink=0.35)

    ter.finish()
    for a in accs:
        a.finish()
    P.finish()
    b.export(path)
