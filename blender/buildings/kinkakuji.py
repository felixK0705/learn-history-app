"""kinkakuji 京都金閣寺（鹿苑寺舍利殿）＋鏡湖池 寫實模型（公尺；+X 東、+Y 北）

- 舍利殿：三層，初層「法水院」寢殿造（素木柱、白壁、蔀戶）、二層「潮音洞」武家造（外貼金箔、
  四周勾欄）、三層「究竟頂」禪宗佛殿造（3 間四方、花頭窗、全金箔）；初層・二層 正面 5 間 × 側面 4 間
- 屋頂為柿葺（薄木片疊葺，暗紫褐色），二層屋頂為寄棟、頂層為寶形造（方錐）＋金銅鳳凰
- 西側突出的釣殿「漱清」，立於池中石上
- 南側為鏡湖池：葦原島（松樹）、數座岩島；周圍松、楓與闊葉樹

本檔另外提供東亞木構建築共用工具（曲面屋頂、瓦貼圖、樹木），供紫禁城、德壽宮、臥佛寺模組共用。
"""

import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, noise

from lib import TAU, TEX, Builder, tinted_texture

# (目標點, 方位角, 仰角, 距離, 焦距)：參考照自池南岸（東南南）隔水眺望
CAMERA = ((1.5, 0.0, 5.6), 22.0, -3.0, 38.0, 28)

GEN = os.path.join(TEX, "_gen")


# ====================================================================== 共用：程式產生的貼圖
def _save_maps(out, diff, nor=None, arm=None, size=None):
    from PIL import Image

    os.makedirs(out, exist_ok=True)
    for fn, arr in (("diff", diff), ("nor", nor)):
        if arr is None:
            continue
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        if size:
            im = im.resize((size, size), Image.LANCZOS)
        im.save(os.path.join(out, fn + ".jpg"), quality=86)


def _height_to_normal(h, k):
    gy, gx = np.gradient(h)
    nx, ny, nz = -gx * k, gy * k, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([(nx / ln * 0.5 + 0.5) * 255, (ny / ln * 0.5 + 0.5) * 255, (nz / ln * 0.5 + 0.5) * 255], -1)


def _cloud(rng, N, scale, amp):
    from PIL import Image, ImageFilter

    small = rng.normal(0, 1, size=(max(2, N // scale), max(2, N // scale)))
    im = Image.fromarray(((small - small.min()) / (np.ptp(small) + 1e-9) * 255).astype(np.uint8))
    im = im.resize((N, N), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(max(1, scale / 3)))
    return (np.asarray(im, dtype=float) / 255 - 0.5) * amp


def gen_tiles(name, color, kind="kawara", seed=3, n_ch=8, n_rows=8, extra=None):
    """屋瓦貼圖（u 沿簷口、v 沿下坡）。kind: kawara 筒瓦＋板瓦、shingle 木片疊葺、thai 泰式魚鱗瓦。
    color 為主色 (r,g,b)；extra 可給 {'joint': (r,g,b)}。每張貼圖代表 n_ch 條瓦溝 × n_rows 列"""
    out = os.path.join(GEN, f"asia_{name}")
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return out
    N = 1024
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    base = np.array(color, dtype=float)
    lum = _cloud(rng, N, 64, 0.10) + _cloud(rng, N, 8, 0.05)
    if kind == "kawara":
        P = N / n_ch
        RW = N / n_rows
        dxr = ((xx + P / 2) % P) - P / 2
        cy = yy % RW
        a = np.abs(dxr)
        rr = P * 0.2
        rnd = np.clip(1 - (dxr / rr) ** 2, 0, 1)
        h = 0.25 * (1 - a / (P / 2)) + 0.1 * (cy / RW)
        round_ = a < rr
        h = np.where(round_, 0.5 + 0.5 * np.sqrt(rnd) + 0.08 * (cy / RW), h)
        joint = cy < RW * 0.04
        h = np.where(joint, h - 0.15, h)
        shade = np.where(round_, 0.92 + 0.22 * (dxr / rr), 0.80 + 0.12 * (cy / RW))
        shade = np.where(joint & round_, shade * 0.62, shade)
        shade = np.where((a > rr) & (a < rr * 1.25), shade * 0.6, shade)
        col = np.floor((xx + P / 2) / P).astype(int)
        crs = np.floor(yy / RW).astype(int)
        tone = rng.uniform(-0.06, 0.06, size=(64, 64))[crs % 64, col % 64]
        diff = base[None, None, :] * (shade + lum + tone)[..., None]
        nor = _height_to_normal(h * 6, 1.0)
    elif kind == "shingle":
        RW = N / n_rows
        cy = yy % RW
        crs = np.floor(yy / RW).astype(int)
        # 細木片（縱向紋）
        sw = N / 64
        sx = np.floor((xx + (crs % 2) * sw * 0.5) / sw).astype(int)
        tone = rng.uniform(-0.12, 0.12, size=(256, 64))[crs % 256, sx % 64]
        grain = _cloud(rng, N, 2, 0.08)
        shade = 0.72 + 0.32 * (cy / RW) ** 0.6
        edge = cy < RW * 0.06
        shade = np.where(edge, 0.48, shade)
        diff = base[None, None, :] * (shade + tone + grain + lum * 0.6)[..., None]
        h = cy / RW + np.where(edge, -0.3, 0)
        nor = _height_to_normal(h * 4, 1.0)
    else:  # thai：上釉魚鱗瓦（圓尾）
        P = N / n_ch
        RW = N / n_rows
        crs = np.floor(yy / RW).astype(int)
        lx = (xx + (crs % 2) * P / 2) % P - P / 2
        cy = yy % RW
        edge_y = RW * (0.78 + 0.22 * np.sqrt(np.clip(1 - (lx / (P / 2)) ** 2, 0, 1)))
        inside = cy < edge_y
        shade = np.where(inside, 0.80 + 0.30 * (cy / RW), 0.55)
        rim = inside & (cy > edge_y - RW * 0.08)
        shade = np.where(rim, 1.12, shade)
        sep = np.abs(lx) > P / 2 - 2.5
        shade = np.where(sep, 0.55, shade)
        tone = rng.uniform(-0.05, 0.05, size=(64, 64))[crs % 64, np.floor((xx + (crs % 2) * P / 2) / P).astype(int) % 64]
        diff = base[None, None, :] * (shade + tone + lum * 0.5)[..., None]
        h = np.where(inside, cy / RW, 0) + np.where(sep, -0.2, 0)
        nor = _height_to_normal(h * 4, 1.0)
    _save_maps(out, diff, nor)
    return out


def gen_leaves(kind):
    """葉簇卡片貼圖（RGBA PNG）：kind=broad/light/pine/maple/palm/shrub/dark"""
    out = os.path.join(GEN, f"asia_leaf3_{kind}.png")
    if os.path.exists(out):
        return out
    from PIL import Image, ImageDraw

    S = 1024
    rng = np.random.default_rng(abs(hash(kind)) % 1000)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    if kind in ("pine", "dark"):
        pal = ([(48, 74, 34), (60, 90, 40), (74, 106, 46), (40, 62, 30), (88, 120, 54)] if kind == "pine"
               else [(34, 58, 30), (44, 70, 36), (54, 82, 40), (30, 50, 26), (62, 92, 46)])
        for _ in range(8):
            a = rng.uniform(0, TAU)
            r = rng.uniform(0.25, 0.42) * S
            dr.line([(S / 2, S / 2), (S / 2 + math.cos(a) * r, S / 2 + math.sin(a) * r)], fill=(84, 64, 48, 255), width=8)
        for layer in range(3):
            for _ in range(800):
                r = S * 0.43 * math.sqrt(rng.uniform(0, 1))
                a = rng.uniform(0, TAU)
                cx, cy = S / 2 + r * math.cos(a), S / 2 + r * math.sin(a) * 0.8
                c = pal[rng.integers(len(pal))]
                k = (0.68 + 0.2 * layer) * rng.uniform(0.85, 1.15) * (1 + 0.25 * (S / 2 - cy) / S)
                col = tuple(int(min(255, v * k)) for v in c) + (255,)
                for _ in range(8):
                    b = rng.uniform(0, TAU)
                    L = rng.uniform(26, 48)
                    dr.line([(cx, cy), (cx + math.cos(b) * L, cy + math.sin(b) * L)], fill=col, width=3)
    elif kind == "palm":
        pal = [(70, 110, 40), (86, 126, 46), (60, 96, 34), (100, 138, 52)]
        for _ in range(9):
            a = rng.uniform(0, TAU)
            L = S * rng.uniform(0.35, 0.47)
            ex, ey = S / 2 + math.cos(a) * L, S / 2 + math.sin(a) * L
            dr.line([(S / 2, S / 2), (ex, ey)], fill=(96, 110, 52, 255), width=6)
            c = pal[rng.integers(len(pal))]
            for k in range(40):
                t = 0.12 + 0.88 * k / 40
                px, py = S / 2 + (ex - S / 2) * t, S / 2 + (ey - S / 2) * t
                ll = S * 0.12 * math.sin(math.pi * min(1, t * 1.1))
                for sgn in (-1, 1):
                    bb = a + sgn * 1.0
                    col = tuple(int(v * rng.uniform(0.8, 1.15)) for v in c) + (255,)
                    dr.line([(px, py), (px + math.cos(bb) * ll, py + math.sin(bb) * ll)], fill=col, width=5)
    else:
        pal = {"broad": [(70, 104, 34), (84, 120, 40), (100, 136, 46), (60, 92, 30), (116, 150, 54)],
               "light": [(134, 168, 52), (152, 184, 60), (170, 198, 70), (118, 152, 46), (186, 206, 82)],
               "maple": [(132, 172, 56), (152, 188, 64), (170, 200, 74), (116, 158, 48), (186, 210, 86)],
               "shrub": [(84, 120, 40), (100, 136, 46), (116, 150, 54), (72, 106, 36), (128, 160, 60)]}[kind]
        Lr = (70, 110) if kind != "shrub" else (48, 72)
        subs = []
        for _ in range(13):
            a = rng.uniform(0, TAU)
            r = S * rng.uniform(0.04, 0.34)
            subs.append((S / 2 + r * math.cos(a), S / 2 + r * math.sin(a), S * rng.uniform(0.07, 0.12)))
        for sx, sy, sr in subs:
            dr.line([(S / 2, S / 2), (sx, sy)], fill=(84, 68, 50, 255), width=5)
        for sx, sy, sr in subs:
            dk = tuple(int(v * 0.34) for v in pal[0]) + (255,)
            pts = [(sx + sr * 0.86 * (1 + 0.12 * math.sin(TAU * j / 24 * 5 + sx)) * math.cos(TAU * j / 24),
                    sy + sr * 0.86 * (1 + 0.12 * math.sin(TAU * j / 24 * 5 + sx)) * math.sin(TAU * j / 24)) for j in range(24)]
            dr.polygon(pts, fill=dk)
        for layer in range(3):
            for sx, sy, sr in subs:
                base = pal[rng.integers(len(pal))]
                la = (Lr[0] + Lr[1]) / 2
                nleaf = int(1.1 * math.pi * sr * sr / (la * la * 0.48 * 0.6) * (1.0 if layer < 2 else 0.7))
                for _ in range(nleaf):
                    rr = sr * math.sqrt(rng.uniform(0, 1))
                    aa = rng.uniform(0, TAU)
                    px, py = sx + rr * math.cos(aa), sy + rr * math.sin(aa)
                    lit = (0.5, 0.75, 1.0)[layer] * (1 + 0.35 * (sy - py) / sr + 0.15 * (px - sx) / sr) * rng.uniform(0.75, 1.18)
                    col = tuple(int(min(255, max(0, v * lit))) for v in base) + (255,)
                    L = rng.uniform(*Lr)
                    W = L * rng.uniform(0.42, 0.55)
                    bang = rng.uniform(0, TAU)
                    ca, sa = math.cos(bang), math.sin(bang)
                    pts = []
                    for j in range(10):
                        u = j / 9
                        pts.append((px + L * u * ca - W / 2 * math.sin(math.pi * u) * sa, py + L * u * sa + W / 2 * math.sin(math.pi * u) * ca))
                    for j in range(9, -1, -1):
                        u = j / 9
                        pts.append((px + L * u * ca + W / 2 * math.sin(math.pi * u) * sa, py + L * u * sa - W / 2 * math.sin(math.pi * u) * ca))
                    dr.polygon(pts, fill=col)
    im = im.resize((512, 512), Image.LANCZOS)
    arr = np.array(im).astype(np.float32)
    a = arr[..., 3:4] / 255.0
    rgb = np.where(a > 0.05, arr[..., :3] / np.maximum(a, 0.05), 0)
    mean = rgb[a[..., 0] > 0.5].mean(0)
    rgb = np.where(a > 0.05, rgb, mean)
    alpha = np.where(a[..., 0] > 0.45, 255, 0)
    os.makedirs(GEN, exist_ok=True)
    Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha]).astype(np.uint8), "RGBA").quantize(
        colors=128, method=Image.Quantize.FASTOCTREE).save(out, optimize=True)
    return out


def gen_canopy(name, color, seed=7):
    """樹冠表面貼圖（無縫）：大量不規則葉叢印記，左上受光、右下落影；color 為平均色"""
    out = os.path.join(GEN, f"asia_canopy_{name}")
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return out
    from PIL import Image, ImageDraw, ImageFilter

    N = 1024
    rng = np.random.default_rng(seed)
    hgt = Image.new("L", (N, N), 0)
    lum = Image.new("L", (N, N), 90)
    dh, dl = ImageDraw.Draw(hgt), ImageDraw.Draw(lum)
    for k in range(2600):
        cx, cy = rng.uniform(0, N), rng.uniform(0, N)
        r = rng.uniform(16, 42)
        nlob = rng.integers(7, 12)
        ph = rng.uniform(0, TAU)
        def poly(scale, ox=0.0, oy=0.0):
            return [(cx + ox + r * scale * (1 + 0.28 * math.sin(nlob * TAU * j / 40 + ph) + rng.uniform(-0.1, 0.1)) * math.cos(TAU * j / 40),
                     cy + oy + r * scale * (1 + 0.28 * math.sin(nlob * TAU * j / 40 + ph) + rng.uniform(-0.1, 0.1)) * math.sin(TAU * j / 40)) for j in range(40)]
        base = rng.uniform(0.75, 1.15)
        h0 = int(40 + 200 * k / 2600)
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                if not (-60 < cx + ox < N + 60 and -60 < cy + oy < N + 60):
                    continue
                dl.polygon(poly(1.05, ox + r * 0.35, oy + r * 0.35), fill=int(35 * base))
                for t in range(5):
                    sc = 1.0 - t * 0.17
                    dl.polygon(poly(sc, ox - r * 0.12 * t, oy - r * 0.12 * t), fill=int(min(255, (110 + 28 * t) * base)))
                dh.polygon(poly(1.0, ox, oy), fill=h0)
    lum = lum.filter(ImageFilter.GaussianBlur(1.2))
    L = np.asarray(lum, dtype=float) / 160.0
    L = L * (1 + _cloud(rng, N, 128, 0.25))
    base = np.array(color, dtype=float)
    hue = _cloud(rng, N, 96, 0.18)
    diff = np.stack([base[0] * L * (1 + hue * 0.8), base[1] * L * (1 + hue * 0.3), base[2] * L * (1 - hue * 0.5)], -1)
    H = np.asarray(hgt.filter(ImageFilter.GaussianBlur(2.0)), dtype=float) / 255.0 + np.asarray(lum, dtype=float) / 600.0
    _save_maps(out, diff, _height_to_normal(H * 18, 1.0), size=512)
    return out


# ====================================================================== 共用：Builder 擴充
class AsiaBuilder(Builder):
    """屋瓦材質依屋面下坡方向決定 UV（瓦溝順坡）；葉片卡片用 0–1 UV；小尺寸貼圖控制 GLB 大小"""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.oriented = set()
        self.cards = set()
        self.rot_layer = self.bm.faces.layers.int.new("roofrot")

    # ---------------------------------------------------------- 材質
    def alpha_mat(self, name, png, rough=0.75):
        if name in self._cache:
            return self._cache[name]
        m = bpy.data.materials.new(f"{self.name}_{name}")
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        img = nt.nodes.new("ShaderNodeTexImage")
        img.image = bpy.data.images.load(png, check_existing=True)
        nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
        r = nt.nodes.new("ShaderNodeMath")
        r.operation = "ROUND"
        nt.links.new(img.outputs["Alpha"], r.inputs[0])
        nt.links.new(r.outputs[0], bsdf.inputs["Alpha"])
        bsdf.inputs["Roughness"].default_value = rough
        m.surface_render_method = "DITHERED"
        idx = self._register(name, m, 1.0)
        self.cards.add(idx)
        return idx

    def gtex(self, name, folder, tile, rough=0.8, normal=0.8, metal=0.0, oriented=False, size=None):
        """程式產生貼圖（folder 內 diff/nor.jpg）"""
        if name in self._cache:
            return self._cache[name]
        m = bpy.data.materials.new(f"{self.name}_{name}")
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        img = nt.nodes.new("ShaderNodeTexImage")
        img.image = bpy.data.images.load(os.path.join(folder, "diff.jpg"), check_existing=True)
        nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
        npth = os.path.join(folder, "nor.jpg")
        if normal > 0 and os.path.exists(npth):
            nimg = nt.nodes.new("ShaderNodeTexImage")
            nimg.image = bpy.data.images.load(npth, check_existing=True)
            nimg.image.colorspace_settings.name = "Non-Color"
            nmap = nt.nodes.new("ShaderNodeNormalMap")
            nmap.inputs["Strength"].default_value = normal
            nt.links.new(nimg.outputs["Color"], nmap.inputs["Color"])
            nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        idx = self._register(name, m, tile)
        if oriented:
            self.oriented.add(idx)
        return idx

    def ptex(self, name, tex_id, tile, tint=None, gain=1.0, rough=0.85, normal=0.8, nsize=512, dsize=512):
        """Poly Haven 貼圖（縮小版，固定粗糙度）"""
        if name in self._cache:
            return self._cache[name]
        from PIL import Image

        os.makedirs(GEN, exist_ok=True)
        diff = tinted_texture(tex_id, tint, gain)
        if dsize < 1024:
            dp = os.path.join(GEN, f"{os.path.splitext(os.path.basename(diff))[0]}_{dsize}.jpg")
            if not os.path.exists(dp):
                Image.open(diff).resize((dsize, dsize), Image.LANCZOS).save(dp, quality=84)
            diff = dp
        m = bpy.data.materials.new(f"{self.name}_{name}")
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        img = nt.nodes.new("ShaderNodeTexImage")
        img.image = bpy.data.images.load(diff, check_existing=True)
        nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
        if normal > 0 and os.path.exists(os.path.join(TEX, tex_id, "nor.jpg")):
            npth = os.path.join(GEN, f"{tex_id}_nor{nsize}.jpg")
            if not os.path.exists(npth):
                Image.open(os.path.join(TEX, tex_id, "nor.jpg")).resize((nsize, nsize), Image.LANCZOS).save(npth, quality=85)
            nimg = nt.nodes.new("ShaderNodeTexImage")
            nimg.image = bpy.data.images.load(npth, check_existing=True)
            nimg.image.colorspace_settings.name = "Non-Color"
            nmap = nt.nodes.new("ShaderNodeNormalMap")
            nmap.inputs["Strength"].default_value = normal
            nt.links.new(nimg.outputs["Color"], nmap.inputs["Color"])
            nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
        bsdf.inputs["Roughness"].default_value = rough
        return self._register(name, m, tile)

    # ---------------------------------------------------------- 低階網格
    def V(self, p):
        return self.bm.verts.new(p)

    def face(self, vs, mi, smooth=False, rot=0):
        f = self.bm.faces.new(vs)
        f.material_index = mi
        f.smooth = smooth
        if rot:
            f[self.rot_layer] = int(rot)
        return f

    def strip(self, rows, mi, closed=True, smooth=False, rot=0):
        for a, c in zip(rows, rows[1:]):
            n = len(a)
            for i in range(n if closed else n - 1):
                j = (i + 1) % n
                self.face([a[i], a[j], c[j], c[i]], mi, smooth, rot)

    def capture(self, fn):
        self.bm.verts.ensure_lookup_table()
        start = len(self.bm.verts)
        fn()
        self.bm.verts.ensure_lookup_table()
        return list(self.bm.verts[start:])

    def place(self, fn, M):
        vs = self.capture(fn)
        bmesh.ops.transform(self.bm, matrix=M, verts=vs)
        return vs

    def sweep(self, path, w, h, mi, up=(0, 0, 1), caps=True, smooth=False):
        """沿路徑掃出矩形斷面（寬 w、高 h，底面貼齊路徑）"""
        rings = []
        n = len(path)
        upv = Vector(up)
        for k, p in enumerate(path):
            p = Vector(p)
            t = (Vector(path[min(k + 1, n - 1)]) - Vector(path[max(k - 1, 0)])).normalized()
            s = t.cross(upv)
            if s.length < 1e-6:
                s = Vector((1, 0, 0))
            s.normalize()
            u = s.cross(t).normalized()
            rings.append([self.V(p - s * w / 2), self.V(p + s * w / 2), self.V(p + s * w / 2 + u * h), self.V(p - s * w / 2 + u * h)])
        self.strip(rings, mi, smooth=smooth)
        if caps:
            self.face(list(reversed(rings[0])), mi)
            self.face(rings[-1], mi)
        return rings

    def tube(self, path, r0, r1, mi, seg=6, cap=True):
        rings = []
        n = len(path)
        for k, p in enumerate(path):
            p = Vector(p)
            t = (Vector(path[min(k + 1, n - 1)]) - Vector(path[max(k - 1, 0)])).normalized()
            a = t.orthogonal().normalized()
            c = t.cross(a)
            r = r0 + (r1 - r0) * k / max(1, n - 1)
            rings.append([self.V(p + (a * math.cos(TAU * i / seg) + c * math.sin(TAU * i / seg)) * r) for i in range(seg)])
        self.strip(rings, mi, smooth=True)
        if cap:
            self.face(rings[-1], mi)
        return rings

    def blob(self, mi, loc, rx, ry, rz, lump=0.3, sub=1, smooth=True):
        off = Vector((self.rng.uniform(0, 99), self.rng.uniform(0, 99), self.rng.uniform(0, 99)))
        r = bmesh.ops.create_icosphere(self.bm, subdivisions=sub, radius=1.0, matrix=Matrix.Identity(4))
        for v in r["verts"]:
            q = v.co.copy()
            nn = noise.noise(q * 1.6 + off) * 0.7 + noise.noise(q * 3.5 + off) * 0.3
            k = 1 + lump * nn
            v.co = Vector((loc[0] + q.x * rx * k, loc[1] + q.y * ry * k, loc[2] + q.z * rz * k))
        for f in {f for v in r["verts"] for f in v.link_faces}:
            f.material_index = mi
            f.smooth = smooth
        return r["verts"]

    def card(self, mi, c, nrm, size, spin):
        n = Vector(nrm).normalized()
        a = n.orthogonal().normalized()
        bb = n.cross(a)
        ca, sa = math.cos(spin), math.sin(spin)
        u = (a * ca + bb * sa) * size / 2
        v = (bb * ca - a * sa) * size / 2
        c = Vector(c)
        self.face([self.V(c - u - v), self.V(c + u - v), self.V(c + u + v), self.V(c - u + v)], mi)

    # ---------------------------------------------------------- 樹木
    def crown(self, cx, cy, cz, rx, rz, mats, core, csize, density=1.0, cap=140):
        """樹冠團塊：深色核心＋分布在橢球表層、大致朝外的葉簇卡片"""
        rng = self.rng
        self.blob(core, (cx, cy, cz), rx * 0.92, rx * 0.92, rz * 0.9, lump=0.4, sub=2 if rx > 2.2 else 1)
        area = 4 * math.pi * ((2 * rx * rx + rz * rz) / 3)
        n = int(min(cap, density * 1.2 * area / (csize * csize)))
        for _ in range(n):
            d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1) * 0.9 + 0.25)).normalized()
            rr = rng.uniform(0.92, 1.08)
            p = (cx + d.x * rx * rr, cy + d.y * rx * rr, cz + d.z * rz * rr)
            nrm = (d + Vector((rng.uniform(-0.22, 0.22), rng.uniform(-0.22, 0.22), rng.uniform(0.0, 0.35)))).normalized()
            mi = mats[0] if (d.z > 0.05 or rng.random() < 0.3) else mats[-1]
            self.card(mi, p, nrm, csize * rng.uniform(0.8, 1.2), rng.uniform(0, TAU))

    def broadleaf(self, x, y, z, h, mats, core, bark, R=None, n_blobs=None, cs=None, cap=160):
        rng = self.rng
        R = R or h * 0.4
        cz = z + h - R * 0.95
        rz = min(R * 0.95, (cz - z) * 0.95 + R * 0.3)
        self.tube([(x, y, z - 0.4), (x + rng.uniform(-0.3, 0.3), y + rng.uniform(-0.3, 0.3), z + (cz - z) * 0.5), (x, y, cz)],
                  max(0.1, h * 0.028), max(0.05, h * 0.014), bark)
        n = n_blobs or rng.randint(5, 8)
        cs = cs or 0.85
        for i in range(n):
            a = rng.uniform(0, TAU)
            rr = R * math.sqrt(rng.uniform(0.0, 1)) * 0.6
            dz = rng.uniform(-0.5, 0.45) * rz
            br = R * rng.uniform(0.42, 0.6)
            self.crown(x + rr * math.cos(a), y + rr * math.sin(a), cz + dz, br, br * 0.85, mats, core, min(cs, br * 0.9), cap=cap)

    def pine(self, x, y, z, h, mats, core, bark, lean=None, pads=None, spread=1.0):
        """日式黑松：彎曲樹幹、水平展開的扁平枝葉團（雲片）"""
        rng = self.rng
        ang = lean if lean is not None else rng.uniform(0, TAU)
        tilt = rng.uniform(0.15, 0.4)
        pts = [(x, y, z - 0.3)]
        px, py = x, y
        for k in range(1, 6):
            t = k / 5
            ang += rng.uniform(-0.5, 0.5)
            px += math.cos(ang) * h * tilt * 0.2
            py += math.sin(ang) * h * tilt * 0.2
            pts.append((px, py, z + h * 0.82 * t))
        self.tube(pts, max(0.12, h * 0.035), max(0.05, h * 0.012), bark, seg=7)
        n = pads or rng.randint(4, 7)
        for i in range(n):
            t = 0.35 + 0.65 * (i / max(1, n - 1))
            k = min(5, int(t * 5))
            bx, by, bz = pts[k]
            a = rng.uniform(0, TAU)
            L = h * spread * rng.uniform(0.15, 0.32) * (1.15 - 0.5 * t)
            ex, ey, ez = bx + math.cos(a) * L, by + math.sin(a) * L, bz + rng.uniform(-0.05, 0.12) * h
            self.tube([(bx, by, bz), ((bx + ex) / 2, (by + ey) / 2, (bz + ez) / 2 + 0.2), (ex, ey, ez)], max(0.05, h * 0.012), 0.04, bark, seg=5, cap=False)
            pr = h * spread * rng.uniform(0.13, 0.2) * (1.2 - 0.45 * t)
            self.crown(ex, ey, ez + pr * 0.15, pr, pr * 0.38, mats, core, min(pr * 0.4, 0.7), cap=90)
        tx, ty, tz = pts[-1]
        pr = h * spread * 0.17
        self.crown(tx, ty, tz + pr * 0.2, pr, pr * 0.45, mats, core, min(pr * 0.4, 0.7), cap=90)

    def conifer(self, x, y, z, h, mats, core, bark, r=None):
        """杉／檜：細長圓錐樹冠"""
        rng = self.rng
        r = r or h * 0.2
        self.tube([(x, y, z - 0.3), (x, y, z + h * 0.9)], max(0.1, h * 0.02), 0.05, bark, seg=6)
        n = 5
        for i in range(n):
            t = i / (n - 1)
            rr = r * (1 - 0.8 * t)
            self.crown(x + rng.uniform(-0.2, 0.2), y + rng.uniform(-0.2, 0.2), z + h * (0.32 + 0.6 * t), rr, h * 0.14, mats, core, min(1.0, rr * 0.5), cap=110)

    # ---------------------------------------------------------- 東亞曲面屋頂
    def roof_skirt(self, mi, eave, top, ze, zt, center=(0, 0), U=0.6, P=0.4, K=(16, 12), rows=8,
                   soffit=None, wall=None, thick=0.35, fascia=None, cap=None, corner_len=None, gamma=0.45,
                   rot=0.0, hips=None, hip_w=0.35, hip_h=0.3, rise_mid=0.0):
        """一段曲面屋面：由簷口矩形 eave=(半寬A,半深B) 收至頂部矩形 top=(At,Bt)，高度 ze→zt。
        斷面為下凹曲線（簷口平緩、往上漸陡）；四隅起翹 U（公尺）並外張 P。
        soffit/wall=(Aw,Bw,zw) 時做出簷下天花（斜回牆面）；thick 為簷口厚度。
        hips 給材質時沿四條戧脊掃出垂脊。回傳 (各環點列, 角點路徑)。"""
        A, B = eave
        At, Bt = top
        cx, cy = center
        Mr = Matrix.Rotation(rot, 4, "Z")
        Lc = corner_len or min(A, B) * 0.75
        KA, KB = K

        def edge_params(n):
            # 兩端較密（翹角處需要較多點）
            return [0.5 - 0.5 * math.cos(math.pi * i / n) for i in range(n)]

        tA, tB = edge_params(KA), edge_params(KB)

        def ring(a, b, z, s, lift=True):
            corners = [(-a, -b), (a, -b), (a, b), (-a, b)]
            pts = []
            for e in range(4):
                (x0, y0), (x1, y1) = corners[e], corners[(e + 1) % 4]
                L = math.hypot(x1 - x0, y1 - y0)
                ts = tA if e % 2 == 0 else tB
                for t in ts:
                    x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                    dist = min(t, 1 - t) * L
                    c = max(0.0, 1 - dist / Lc) ** 2 if lift else 0.0
                    sl = (1 - s) ** 1.6
                    zz = z + U * c * sl + rise_mid * (1 - c) * 0.0
                    # 外張：沿角的對角方向
                    kx = (1 if x > 0 else -1) if abs(x) > 1e-9 else 0
                    ky = (1 if y > 0 else -1) if abs(y) > 1e-9 else 0
                    push = P * c * (1 - s)
                    if e % 2 == 0:
                        y += ky * push * 0.5
                        x += kx * push * (1 if dist < Lc else 0) * 0.5
                    else:
                        x += kx * push * 0.5
                        y += ky * push * (1 if dist < Lc else 0) * 0.5
                    p = Mr @ Vector((x, y, zz))
                    pts.append((cx + p.x, cy + p.y, p.z))
            return pts

        def g(s):
            return (1 - gamma) * s + gamma * s * s

        rings_p = []
        for j in range(rows + 1):
            s = j / rows
            a = A + (At - A) * s
            b = B + (Bt - B) * s
            rings_p.append(ring(a, b, ze + (zt - ze) * g(s), s))
        rings_v = [[self.V(p) for p in r] for r in rings_p]
        rdeg = int(round(math.degrees(rot)))
        self.strip(rings_v, mi, rot=rdeg)
        n = len(rings_p[0])
        # 簷口厚度＋簷下天花
        low = [self.V((p[0], p[1], p[2] - thick)) for p in rings_p[0]]
        fm = fascia if fascia is not None else mi
        for i in range(n):
            j = (i + 1) % n
            self.face([low[i], low[j], rings_v[0][j], rings_v[0][i]], fm)
        if wall is not None:
            Aw, Bw, zw = wall
            # 牆線環：與簷口環同樣參數化（牆角不起翹）
            wr = []
            for p, q in zip(ring(Aw, Bw, zw, 1.0, lift=False), rings_p[0]):
                wr.append(self.V(p))
            self.strip([wr, low], soffit if soffit is not None else fm)
        else:
            self.face(list(reversed(low)), soffit if soffit is not None else fm)
        if cap is not None:
            self.face(rings_v[-1], cap)
        corner_idx = [0, KA, KA + KB, 2 * KA + KB]
        paths = [[r[ci] for r in rings_p] for ci in corner_idx]
        if hips is not None:
            for path in paths:
                self.sweep([(p[0], p[1], p[2] - 0.05) for p in path], hip_w, hip_h, hips)
        return rings_p, paths

    # ---------------------------------------------------------- 輸出
    def _uv(self):
        uv = self.bm.loops.layers.uv.verify()
        rl = self.rot_layer
        for f in self.bm.faces:
            mi = f.material_index
            tile = self.tiles[mi] if mi < len(self.tiles) else 1.0
            if mi in self.cards:
                for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                    l[uv].uv = c
                continue
            n = f.normal.copy()
            if n.z < 0:
                n = -n
            if mi in self.oriented and n.z > 0.12 and math.hypot(n.x, n.y) > 0.04:
                base = math.radians(f[rl])
                ang = math.atan2(n.y, n.x)
                k = round((ang - base) / (math.pi / 2))
                a = base + k * math.pi / 2
                d = Vector((math.cos(a), math.sin(a), 0))
                t = Vector((-d.y, d.x, 0))
                for l in f.loops:
                    c = l.vert.co
                    l[uv].uv = (c.dot(t) / tile, -(c.dot(d) * 0.6 - c.z * 0.8) / tile)
                continue
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

    def export_glb(self, path):
        self.build_object()
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_apply=True, export_yup=True,
                                  export_image_format="AUTO", export_jpeg_quality=82)


# ====================================================================== 金閣寺
def kinkakuji(path):
    b = AsiaBuilder("Kinkakuji", seed=31)
    rng = b.rng
    V, face = b.V, b.face

    # ---------------- 材質
    grass = b.ptex("moss", "grass_ground", tile=4.0, tint="#6f8a3c", rough=0.95, normal=0.5)
    soil = b.ptex("soil", "gravel_floor", tile=3.0, tint="#9a8466", rough=0.95, normal=0.6)
    bank = b.color("bank", "#5d5140", rough=0.95)
    water = b.color("water", "#8c8a63", rough=0.07)
    rockm = b.ptex("rock", "rock_04", tile=2.5, tint="#8b7f74", rough=0.85, normal=1.0)
    rockp = b.ptex("rock_p", "rock_04", tile=2.5, tint="#9a7c78", rough=0.85, normal=1.0)
    stone = b.ptex("stone", "gray_rocks", tile=2.0, tint="#a39f96", rough=0.85, normal=0.6)
    gold = b.color("gold", "#f4c64e", rough=0.34, metal=0.35)
    gold_d = b.color("gold_shade", "#d0a23a", rough=0.4, metal=0.3)
    wood = b.color("wood", "#3e2b20", rough=0.75)
    wood_l = b.color("wood_light", "#5b4433", rough=0.75)
    plaster = b.color("plaster", "#ece7da", rough=0.85)
    dark = b.color("dark", "#1d1612", rough=0.9)
    shingle = b.gtex("shingle", gen_tiles("kokera2", (84, 54, 48), kind="shingle", n_rows=24, seed=5), tile=3.0,
                     rough=0.85, normal=0.7, oriented=True)
    shingle_e = b.color("shingle_edge", "#4c342c", rough=0.85)
    lf_pine = b.alpha_mat("leaf_pine", gen_leaves("pine"), rough=0.8)
    lf_dark = b.alpha_mat("leaf_dark", gen_leaves("dark"), rough=0.8)
    lf_broad = b.alpha_mat("leaf_broad", gen_leaves("broad"))
    lf_light = b.alpha_mat("leaf_light", gen_leaves("light"))
    lf_maple = b.alpha_mat("leaf_maple", gen_leaves("maple"))
    core_p = b.gtex("core_pine", gen_canopy("pine", (66, 92, 42), seed=3), tile=2.2, rough=0.9, normal=1.0)
    core_b = b.gtex("core_broad", gen_canopy("broad", (104, 136, 50), seed=5), tile=3.0, rough=0.9, normal=1.0)
    bark = b.color("bark", "#5a4636", rough=0.9)
    bark_r = b.color("bark_pine", "#6b4a38", rough=0.9)

    # ---------------- 地形：鏡湖池在南、建物在池北岸；西側池水繞到漱清下方
    R_G = 40.0
    W_Z = -0.45  # 水面

    def pond_d(x, y):
        """>0 表示在池內（值越大越深）"""
        d1 = -(y + 5.4) + 0.5 * math.sin(x * 0.35) + 0.35 * math.sin(x * 0.9 + 1)  # 主池（建物南側）
        d1 = min(d1, (27.0 - x) * 0.5)  # 東岸
        d2 = min(-(x + 7.6), 2.0 - y, (x + 24.0))  # 西側入江（漱清下）
        d = max(d1, d2)
        # 島：葦原島（西南，長形、低）、數座小岩島
        for ix, iy, rx, ry in ((-9.5, -13.0, 7.0, 3.0), (7.5, -13.0, 2.0, 1.6), (-17.0, -9.5, 2.2, 1.6), (15.0, -21.0, 2.4, 1.8)):
            q = math.hypot((x - ix) / rx, (y - iy) / ry)
            d = min(d, (q - 1.0) * 2.5)
        return d

    def terrain_h(x, y):
        d = pond_d(x, y)
        r = math.hypot(x, y)
        base = 0.0 + 0.04 * noise.noise(Vector((x * 0.2, y * 0.2, 0.3)))
        # 北側與東西兩側緩坡上升（背後山林）
        base += max(0.0, (y - 10) * 0.08) + max(0.0, (r - 24) * 0.12)
        if d > 0:
            return max(-1.2, -0.3 - d * 0.6)
        # 島與岸：靠水處低平
        return min(base, 0.15 + max(0.0, -d - 0.5) * 0.25) if d > -4 else base

    b.ground_disc(grass, R_G, bank, depth=2.0, seg=120, rings=40, height_fn=terrain_h)
    # 水面（圓形，地形高於水面處自然遮蔽）
    wr = [V((R_G * 0.985 * math.cos(TAU * i / 120), R_G * 0.985 * math.sin(TAU * i / 120), W_Z)) for i in range(120)]
    face(wr, water)
    # 建物周圍的白砂／土面
    b.prism(soil, [(-9.5, -5.0), (9.5, -5.0), (9.5, 7.5), (-9.5, 7.5)], -0.1, 0.13)

    # ---------------- 建物尺寸（初層 5 間 × 4 間）
    HX, HY = 5.8, 4.4          # 初層・二層 牆線半寬（東西）、半深（南北）
    Z_F1, Z_W1 = 0.75, 3.55    # 初層 地板、天井
    Z_F2, Z_W2 = 3.85, 6.05    # 二層 地板、牆頂
    H3 = 2.7                    # 三層半寬
    Z_F3, Z_W3 = 7.35, 9.05

    # 基壇（石）
    b.box_base(stone, (2 * HX + 1.6, 2 * HY + 1.6, 0.35), (0, 0, -0.1))
    # 初層：束石上的柱、地板、緣側
    xs = [-HX + 2 * HX * i / 5 for i in range(6)]
    ys = [-HY + 2 * HY * i / 4 for i in range(5)]
    b.box_base(wood, (2 * HX + 1.0, 2 * HY + 1.0, 0.18), (0, 0, Z_F1 - 0.18))      # 緣側
    b.box_base(dark, (2 * HX - 0.2, 2 * HY - 0.2, Z_F1 - 0.25), (0, 0, 0.25))       # 床下（暗）
    for x in xs:
        for y in (ys[0], ys[-1]):
            b.box_base(wood, (0.26, 0.26, Z_W1 - 0.25), (x, y, 0.25))
    for y in ys[1:-1]:
        for x in (xs[0], xs[-1]):
            b.box_base(wood, (0.26, 0.26, Z_W1 - 0.25), (x, y, 0.25))
    # 緣側外的低欄
    for s in (-1, 1):
        b.box_base(wood, (2 * HX + 1.0, 0.08, 0.08), (0, s * (HY + 0.45), Z_F1 + 0.55))
        b.box_base(wood, (0.08, 2 * HY + 1.0, 0.08), (s * (HX + 0.45), 0, Z_F1 + 0.55))
        for k in range(12):
            b.box_base(wood, (0.07, 0.07, 0.55), (-HX - 0.45 + (2 * HX + 0.9) * k / 11, s * (HY + 0.45), Z_F1))
    # 初層壁面：南面為蔀戶（上半黑格子、下半板），東面白壁，北・西面板壁＋白壁
    def bay_fill(p0, p1, kind):
        x0, y0 = p0
        x1, y1 = p1
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        out = Vector((math.sin(ang), -math.cos(ang), 0))  # 外側法線（逆時針走向的右手側）
        M = Matrix.Translation((mx - out.x * 0.05, my - out.y * 0.05, 0)) @ Matrix.Rotation(ang, 4, "Z")
        w = L - 0.26
        def panel(mi, z0, z1, d=0.08, off=0.0):
            vs = b.capture(lambda: b.box_base(mi, (w, d, z1 - z0), (0, 0, z0)))
            bmesh.ops.transform(b.bm, matrix=Matrix.Translation((mx + out.x * off, my + out.y * off, 0)) @ Matrix.Rotation(ang, 4, "Z"), verts=vs)
        if kind == "shitomi":
            panel(wood_l, Z_F1, Z_F1 + 1.0, 0.1)
            panel(dark, Z_F1 + 1.0, Z_W1 - 0.3, 0.06, -0.05)
            # 格子
            n = max(4, int(w / 0.22))
            for i in range(n + 1):
                u = -w / 2 + w * i / n
                vs = b.capture(lambda u=u: b.box_base(wood, (0.04, 0.06, Z_W1 - 0.3 - Z_F1 - 1.0), (u, 0, Z_F1 + 1.0)))
                bmesh.ops.transform(b.bm, matrix=Matrix.Translation((mx + out.x * 0.02, my + out.y * 0.02, 0)) @ Matrix.Rotation(ang, 4, "Z"), verts=vs)
            for k in range(1, 7):
                z = Z_F1 + 1.0 + (Z_W1 - 0.3 - Z_F1 - 1.0) * k / 7
                vs = b.capture(lambda z=z: b.box_base(wood, (w, 0.06, 0.04), (0, 0, z)))
                bmesh.ops.transform(b.bm, matrix=Matrix.Translation((mx + out.x * 0.02, my + out.y * 0.02, 0)) @ Matrix.Rotation(ang, 4, "Z"), verts=vs)
            panel(wood, Z_W1 - 0.3, Z_W1, 0.1)
        elif kind == "white":
            panel(wood_l, Z_F1, Z_F1 + 0.35, 0.1)
            panel(plaster, Z_F1 + 0.35, Z_W1 - 0.45, 0.08)
            panel(wood, Z_F1 + 1.8, Z_F1 + 1.92, 0.12, 0.02)
            panel(plaster, Z_W1 - 0.45, Z_W1 - 0.12, 0.08)
            panel(wood, Z_W1 - 0.5, Z_W1 - 0.4, 0.12, 0.02)
        elif kind == "open":
            panel(dark, Z_F1, Z_W1 - 0.3, 0.05, -0.6)
            panel(wood, Z_W1 - 0.3, Z_W1, 0.1)
        else:  # board
            panel(wood_l, Z_F1, Z_W1, 0.1)

    corners = [(-HX, -HY), (HX, -HY), (HX, HY), (-HX, HY)]
    for i in range(5):  # 南
        bay_fill((xs[i], -HY), (xs[i + 1], -HY), "open" if i in (2,) else "shitomi")
    for i in range(4):  # 東
        bay_fill((HX, ys[i]), (HX, ys[i + 1]), "white")
    for i in range(5):  # 北
        bay_fill((xs[5 - i], HY), (xs[4 - i], HY), "board" if i % 2 else "white")
    for i in range(4):  # 西
        bay_fill((-HX, ys[4 - i]), (-HX, ys[3 - i]), "shitomi" if i in (1, 2) else "white")
    # 初層頂部長押、二層樓板下的腕木（出挑托架）
    b.box_base(wood, (2 * HX + 0.3, 2 * HY + 0.3, 0.3), (0, 0, Z_W1))
    BAL = 0.85
    for x in xs:
        for s in (-1, 1):
            b.box_base(wood, (0.16, BAL + 0.3, 0.2), (x, s * (HY + BAL / 2), Z_W1 + 0.05))
    for y in ys:
        for s in (-1, 1):
            b.box_base(wood, (BAL + 0.3, 0.16, 0.2), (s * (HX + BAL / 2), y, Z_W1 + 0.05))

    # ---------------- 二層（金箔）＋勾欄
    b.box_base(wood, (2 * (HX + BAL), 2 * (HY + BAL), 0.2), (0, 0, Z_F2 - 0.2))   # 縁板
    b.box_base(gold_d, (2 * (HX + BAL) + 0.04, 2 * (HY + BAL) + 0.04, 0.12), (0, 0, Z_F2 - 0.3))
    b.box_base(gold, (2 * HX, 2 * HY, Z_W2 - Z_F2), (0, 0, Z_F2))
    def railing(hx, hy, z, h, mi, n_per_m=1.2, post=0.09):
        for s in (-1, 1):
            for (L, xy, horiz) in ((2 * hx, (0, s * hy), True), (2 * hy, (s * hx, 0), False)):
                sz = (L + post, post, post) if horiz else (post, L + post, post)
                b.box_base(mi, sz, (xy[0], xy[1], z + h - post))
                b.box_base(mi, sz, (xy[0], xy[1], z + h * 0.45))
                b.box_base(mi, (sz[0] * (1 if horiz else 1), sz[1], 0.06), (xy[0], xy[1], z + 0.05))
                n = max(2, int(L * n_per_m))
                for k in range(n + 1):
                    t = -L / 2 + L * k / n
                    p = (t, xy[1]) if horiz else (xy[0], t)
                    b.box_base(mi, (post, post, h), (p[0], p[1], z))
    railing(HX + BAL - 0.1, HY + BAL - 0.1, Z_F2, 0.85, gold)
    # 二層壁面細節：柱、長押、格子窗（金）
    for x in xs:
        for y in (-HY, HY):
            b.box_base(gold_d, (0.24, 0.24, Z_W2 - Z_F2), (x, y, Z_F2))
    for y in ys:
        for x in (-HX, HX):
            b.box_base(gold_d, (0.24, 0.24, Z_W2 - Z_F2), (x, y, Z_F2))
    for s in (-1, 1):
        for z in (Z_F2 + 0.25, Z_W2 - 0.45):
            b.box_base(gold_d, (2 * HX + 0.1, 0.08, 0.1), (0, s * (HY + 0.02), z))
            b.box_base(gold_d, (0.08, 2 * HY + 0.1, 0.1), (s * (HX + 0.02), 0, z))
        # 格子窗（南北面中央 3 間、東西面中央 2 間）
        for i in range(1, 4):
            x0, x1 = xs[i] + 0.2, xs[i + 1] - 0.2
            for k in range(9):
                x = x0 + (x1 - x0) * k / 8
                b.box_base(gold_d, (0.04, 0.05, 1.5), (x, s * (HY + 0.03), Z_F2 + 0.45))
            for k in range(6):
                b.box_base(gold_d, (x1 - x0, 0.05, 0.04), ((x0 + x1) / 2, s * (HY + 0.03), Z_F2 + 0.45 + 1.5 * k / 5))
        for i in range(1, 3):
            y0, y1 = ys[i] + 0.2, ys[i + 1] - 0.2
            for k in range(8):
                y = y0 + (y1 - y0) * k / 7
                b.box_base(gold_d, (0.05, 0.04, 1.5), (s * (HX + 0.03), y, Z_F2 + 0.45))
            for k in range(6):
                b.box_base(gold_d, (0.05, y1 - y0, 0.04), (s * (HX + 0.03), (y0 + y1) / 2, Z_F2 + 0.45 + 1.5 * k / 5))
    # 斗栱帶（簡化為金色出挑方木）
    b.box_base(gold_d, (2 * HX + 0.5, 2 * HY + 0.5, 0.25), (0, 0, Z_W2 - 0.5))

    # ---------------- 二層屋頂（寄棟柿葺，上接三層縁）
    OV = 2.55
    b.roof_skirt(shingle, (HX + OV, HY + OV), (H3 + 0.75, H3 + 0.75), 5.75, Z_F3 - 0.12, U=0.55, P=0.5, K=(18, 14), rows=10,
                 soffit=gold, wall=(HX + 0.3, HY + 0.3, Z_W2 - 0.25), thick=0.42, fascia=shingle_e, gamma=0.55,
                 hips=shingle_e, hip_w=0.22, hip_h=0.12, corner_len=3.2)
    # ---------------- 三層（究竟頂）
    b.box_base(wood, (2 * (H3 + 0.75), 2 * (H3 + 0.75), 0.18), (0, 0, Z_F3 - 0.18))
    b.box_base(gold, (2 * H3, 2 * H3, Z_W3 - Z_F3), (0, 0, Z_F3))
    railing(H3 + 0.65, H3 + 0.65, Z_F3, 0.7, gold)
    x3 = [-H3 + 2 * H3 * i / 3 for i in range(4)]
    for s in (-1, 1):
        for x in x3:
            b.box_base(gold_d, (0.2, 0.2, Z_W3 - Z_F3), (x, s * H3, Z_F3))
            b.box_base(gold_d, (0.2, 0.2, Z_W3 - Z_F3), (s * H3, x, Z_F3))
        b.box_base(gold_d, (2 * H3 + 0.1, 0.08, 0.1), (0, s * (H3 + 0.02), Z_W3 - 0.4))
        b.box_base(gold_d, (0.08, 2 * H3 + 0.1, 0.1), (s * (H3 + 0.02), 0, Z_W3 - 0.4))
    # 花頭窗（兩側間）＋中央桟唐戶
    def katomado(M):
        prof = []
        w, h0, h1 = 0.62, 0.0, 1.0
        prof += [(-w / 2, h0), (w / 2, h0), (w / 2, h1)]
        for k in range(1, 12):
            t = k / 12
            a = math.pi * t
            x = w / 2 * math.cos(a)
            y = h1 + 0.28 * math.sin(a) + 0.07 * math.sin(3 * a) ** 2
            prof.append((x, y))
        prof.append((-w / 2, h1))
        b.profile_wall(dark, prof, 0.04, M)
        b.profile_wall(gold_d, [(-0.03, h0), (0.03, h0), (0.03, h1 + 0.3), (-0.03, h1 + 0.3)], 0.06, M @ Matrix.Translation((0, -0.01, 0)))
    for side in range(4):
        R = Matrix.Rotation(side * math.pi / 2, 4, "Z")
        for k, u in enumerate([(x3[i] + x3[i + 1]) / 2 for i in range(3)]):
            M = R @ Matrix.Translation((u, -H3 - 0.02, Z_F3 + 0.3))
            if k == 1:
                b.profile_wall(gold_d, [(-0.55, 0), (0.55, 0), (0.55, 1.35), (-0.55, 1.35)], 0.05, M)
                for i in range(7):
                    b.profile_wall(gold, [(-0.55 + 1.1 * i / 6 - 0.02, 0), (-0.55 + 1.1 * i / 6 + 0.02, 0), (-0.55 + 1.1 * i / 6 + 0.02, 1.35), (-0.55 + 1.1 * i / 6 - 0.02, 1.35)], 0.08, M)
            else:
                katomado(M)
    b.box_base(gold_d, (2 * H3 + 0.5, 2 * H3 + 0.5, 0.22), (0, 0, Z_W3 - 0.05))

    # ---------------- 頂層屋頂（寶形造）＋鳳凰
    OV3 = 2.45
    Z_PK = 11.25
    b.roof_skirt(shingle, (H3 + OV3, H3 + OV3), (0.08, 0.08), 8.8, Z_PK, U=0.5, P=0.45, K=(16, 16), rows=12,
                 soffit=gold, wall=(H3 + 0.25, H3 + 0.25, Z_W3 + 0.15), thick=0.4, fascia=shingle_e, gamma=0.6,
                 hips=shingle_e, hip_w=0.2, hip_h=0.12, corner_len=2.6)
    # 露盤・伏鉢・鳳凰
    b.box_base(gold, (0.5, 0.5, 0.18), (0, 0, Z_PK - 0.12))
    b.lathe(gold, [(0, 0), (0.22, 0), (0.24, 0.12), (0.12, 0.25), (0.06, 0.3), (0.06, 0.5), (0, 0.5)], (0, 0, Z_PK + 0.05), seg=12)
    # 鳳凰：身體＋雙翼＋尾羽
    zb = Z_PK + 0.55
    b.ico(gold, 0.16, (0, 0.0, zb + 0.25), subdiv=1, scale=(0.9, 1.6, 1.0))
    b.ico(gold, 0.08, (0, -0.24, zb + 0.5), subdiv=1)
    b.tube([(0, -0.1, zb + 0.28), (0, -0.2, zb + 0.42), (0, -0.24, zb + 0.5)], 0.06, 0.04, gold, seg=6)
    for s in (-1, 1):
        b.prism(gold, [(0, -0.1), (0.05, 0.1), (0, 0.2), (-0.05, 0.1)], 0, 0.02,
                Matrix.Translation((s * 0.1, 0, zb + 0.3)) @ Matrix.Rotation(s * 0.5, 4, "Y") @ Matrix.Scale(3.2, 4))
    b.tube([(0, 0.18, zb + 0.25), (0, 0.4, zb + 0.32), (0, 0.6, zb + 0.6)], 0.07, 0.02, gold, seg=6)
    b.cyl(gold, 0.03, 0.03, 0.3, (0, 0, zb), seg=6)

    # ---------------- 釣殿「漱清」（西側，伸入池中）
    SX0, SX1, SY0, SY1 = -HX - 3.4, -HX, -2.6, 0.2
    for x in (SX0, (SX0 + SX1) / 2, SX1 - 0.3):
        for y in (SY0, SY1):
            b.box_base(wood, (0.2, 0.2, Z_F1 + 2.6 - W_Z), (x, y, W_Z - 0.05))
            b.rock(rockm, (0.7, 0.7, 0.45), (x, y, W_Z - 0.05), seed=rng.randint(0, 999), round_=0.6)
    b.box_base(wood_l, (SX1 - SX0 + 0.3, SY1 - SY0 + 0.3, 0.15), ((SX0 + SX1) / 2, (SY0 + SY1) / 2, Z_F1 - 0.15))
    for y in (SY0, SY1):
        b.box_base(wood, (SX1 - SX0, 0.08, 0.08), ((SX0 + SX1) / 2, y, Z_F1 + 0.8))
        b.box_base(wood_l, (SX1 - SX0, 0.04, 0.5), ((SX0 + SX1) / 2, y, Z_F1 + 0.2))
    b.box_base(wood, (0.08, SY1 - SY0, 0.08), (SX0, (SY0 + SY1) / 2, Z_F1 + 0.8))
    b.box_base(wood_l, (0.04, SY1 - SY0, 0.5), (SX0, (SY0 + SY1) / 2, Z_F1 + 0.2))
    b.roof_skirt(shingle, ((SX1 - SX0) / 2 + 1.1, (SY1 - SY0) / 2 + 1.1), ((SX1 - SX0) / 2 - 0.4, 0.05), Z_F1 + 2.45, Z_F1 + 3.6,
                 center=((SX0 + SX1) / 2 - 0.2, (SY0 + SY1) / 2), U=0.3, P=0.2, K=(10, 8), rows=6, soffit=wood,
                 wall=((SX1 - SX0) / 2, (SY1 - SY0) / 2, Z_F1 + 2.65), thick=0.3, fascia=shingle_e, gamma=0.5, corner_len=1.2)
    b.box_base(shingle_e, (SX1 - SX0 - 0.6, 0.3, 0.25), ((SX0 + SX1) / 2 - 0.2, (SY0 + SY1) / 2, Z_F1 + 3.55))

    # ---------------- 池岸石組・岩島
    def shore_rocks(n, test):
        pts = []
        tries = 0
        while len(pts) < n and tries < n * 200:
            tries += 1
            x, y = rng.uniform(-R_G, R_G), rng.uniform(-R_G, R_G)
            if math.hypot(x, y) > R_G - 2:
                continue
            d = pond_d(x, y)
            if not test(d):
                continue
            if any((x - px) ** 2 + (y - py) ** 2 < 1.4 for px, py in pts):
                continue
            pts.append((x, y))
        return pts
    for x, y in shore_rocks(70, lambda d: -0.9 < d < 0.5):
        s = rng.uniform(0.6, 1.5)
        z = max(W_Z, terrain_h(x, y)) - 0.25
        b.rock(rockm if rng.random() < 0.7 else rockp, (s * rng.uniform(1.0, 1.6), s, s * rng.uniform(0.5, 0.8)), (x, y, z),
               rot=(0, 0, rng.uniform(0, TAU)), seed=rng.randint(0, 999), round_=0.5, rough=0.22)
    # 池中的立石（參考照前景大石）
    for (x, y, s) in ((4.0, -27.0, 1.6), (-1.5, -22.5, 0.9), (9.5, -18.5, 0.8), (-14.0, -20.0, 1.0), (16.0, -12.5, 0.7)):
        b.rock(rockp, (s * 1.6, s * 1.2, s * 1.1), (x, y, W_Z - 0.4), rot=(0, 0, rng.uniform(0, TAU)), seed=rng.randint(0, 999), round_=0.55, rough=0.2)

    # ---------------- 植栽
    pine_m = (lf_pine, lf_dark)
    # 葦原島與池畔的松
    for (x, y, h) in ((-11.0, -12.5, 5.5), (-7.0, -13.8, 4.2), (-13.5, -14.0, 4.5), (-4.0, -12.8, 3.4), (7.5, -13.0, 3.6),
                      (-17.0, -9.5, 4.0), (15.0, -21.0, 3.6), (10.5, -3.5, 4.5), (-12.0, 4.0, 5.0), (13.0, 2.0, 6.0)):
        b.pine(x, y, terrain_h(x, y), h, pine_m, core_p, bark_r, spread=1.6, pads=rng.randint(6, 8))
    # 背後的林（北、東、西）
    occupied = []
    for _ in range(160):
        a = rng.uniform(-0.25 * math.pi, 1.25 * math.pi)
        r = rng.uniform(12.0, 38.0)
        x, y = r * math.cos(a), r * math.sin(a)
        if pond_d(x, y) > -1.0 or (abs(x) < 10.5 and -6 < y < 9.5):
            continue
        if any((x - px) ** 2 + (y - py) ** 2 < 20 for px, py in occupied):
            continue
        occupied.append((x, y))
        z = terrain_h(x, y)
        k = rng.random()
        if k < 0.3:
            b.conifer(x, y, z, rng.uniform(13, 19), (lf_dark, lf_dark), core_p, bark)
        elif k < 0.55:
            b.pine(x, y, z, rng.uniform(8, 12), pine_m, core_p, bark_r, spread=1.0)
        elif k < 0.75:
            hh = rng.uniform(8, 12)
            b.broadleaf(x, y, z, hh, (lf_maple, lf_light), core_b, bark, R=hh * 0.48, n_blobs=7, cap=70)
        else:
            hh = rng.uniform(10, 15)
            b.broadleaf(x, y, z, hh, (lf_light, lf_broad), core_b, bark, R=hh * 0.45, n_blobs=7, cap=70)
    # 低灌木（刈込）
    for _ in range(70):
        a = rng.uniform(-0.3 * math.pi, 1.3 * math.pi)
        r = rng.uniform(9.0, 36.0)
        x, y = r * math.cos(a), r * math.sin(a)
        if pond_d(x, y) > -0.8 or (abs(x) < 9.8 and -5.5 < y < 8.5):
            continue
        rr = rng.uniform(0.8, 1.8) * (1.0 if r < 20 else 1.6)
        b.crown(x, y, terrain_h(x, y) + rr * 0.4, rr, rr * 0.6, (lf_light, lf_broad), core_b, 0.8, cap=40)

    b.export_glb(path)
