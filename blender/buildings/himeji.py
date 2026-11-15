"""himeji 姬路城（白鷺城）寫實模型（尺寸依實測資料，公尺；+X 東、+Y 北）

- 大天守：石垣約 15 m、建物高 31.5 m；外觀 5 重（內部 6 階），1 階約 26 × 21 m，逐層收分
- 屋頂全部自寫網格：屋面為多段弧線（下凹的「反り」：簷口平緩、往上漸陡）、四隅軒先上翹並外張、
  軒先有瓦當線＋白漆喰茅負的厚度、白漆喰軒裏斜回牆面；瓦筋（丸瓦）方向一律順著屋面下坡
- 千鳥破風（三角形山牆、破風板、懸魚）、唐破風（中央弓起的曲線山牆）、入母屋破風；大棟兩端有鯱
- 窗為黑底白格子窗；2 階南面中央有出格子窗
- 西小天守、乾小天守、東小天守以 2 層渡櫓連成連立式天守；前景為扇之勾配石垣上的白壁瓦頂櫓群
- 樹木：枝幹＋大量帶透明葉片貼圖的葉簇卡片（alpha mask），內含深色樹冠核心

預覽相機（參考照：自西南南方略仰視）：見 CAMERA。
"""

import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, noise

from lib import TAU, TEX, Builder

# build.py 的 CAMS 格式：(目標點, 方位角, 仰角, 距離, 焦距)
CAMERA = ((5.8, -7.4, 40.3), -22.9, -14.0, 160, 50)

GEN = os.path.join(TEX, "_gen")


# ====================================================================== 程式產生的貼圖
def _gen_kawara():
    """本瓦葺：丸瓦（凸）＋平瓦（凹）交替，丸瓦兩側有白漆喰；貼圖 2.4 m 一循環（丸瓦間距 0.3 m）"""
    out = os.path.join(GEN, "himeji_kawara3")
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return out
    from PIL import Image

    N, P = 1024, 128
    rng = np.random.default_rng(11)
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    dxr = ((xx + P / 2) % P) - P / 2
    col = np.floor((xx + P / 2) / P).astype(int) % (N // P)
    RW = 120  # 每列瓦片 0.28 m
    cy = yy % RW
    course = np.floor(yy / RW).astype(int)
    rr, mw = 25.0, 4.0
    a = np.abs(dxr)
    h = 0.28 * (1 - a / (P / 2)) + 0.12 * (cy / RW)
    mortar = (a >= rr) & (a < rr + mw)
    rnd = np.clip(1 - (dxr / rr) ** 2, 0, 1)
    round_ = a < rr
    h = np.where(round_, 0.45 + 0.55 * np.sqrt(rnd) + 0.1 * (cy / RW), h)
    h = np.where(mortar, 0.38, h)
    joint = cy < 4
    h = np.where(joint, h - 0.12, h)
    tone = rng.uniform(0.9, 1.08, size=(N // RW + 2, N // P + 1))
    t = tone[course % tone.shape[0], col]
    fine = rng.normal(0, 3.5, size=(N, N))
    base = np.stack([104 * t, 108 * t, 114 * t], -1) + fine[..., None]
    base = np.where(round_[..., None], base * (0.9 + 0.16 * np.sqrt(rnd))[..., None], base)
    base = np.where(mortar[..., None], np.array([214, 213, 207]) + fine[..., None] * 0.5, base)
    base = np.where((joint & ~mortar)[..., None], base * 0.62, base)
    gy, gx = np.gradient(h)
    s = 10.0
    nx, ny, nz = -gx * s, gy * s, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nor = np.stack([(nx / ln * 0.5 + 0.5) * 255, (ny / ln * 0.5 + 0.5) * 255, (nz / ln * 0.5 + 0.5) * 255], -1)
    ao = 255 * (0.6 + 0.4 * np.clip(h / 0.9, 0, 1))
    rough = np.where(mortar, 0.85, 0.42) * 255
    arm = np.stack([ao, rough, np.zeros_like(h)], -1)
    os.makedirs(out, exist_ok=True)
    for fn, arr in (("diff", base), ("nor", nor), ("arm", arm)):
        Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(os.path.join(out, fn + ".jpg"), quality=88)
    return out


def _gen_window():
    """格子窗：黑底、白色直格子（每 0.8 m 貼圖 4 根）"""
    out = os.path.join(GEN, "himeji_window.jpg")
    if os.path.exists(out):
        return out
    from PIL import Image

    N = 256
    xx = np.arange(N)[None, :].repeat(N, 0)
    yy = np.arange(N)[:, None].repeat(N, 1)
    bar = (xx % 64) < 13
    img = np.zeros((N, N, 3)) + np.array([24, 23, 22])
    shade = 0.82 + 0.18 * ((xx % 64) / 13.0)
    img = np.where(bar[..., None], np.array([232, 230, 224]) * np.clip(shade, 0, 1)[..., None], img)
    img += np.random.default_rng(3).normal(0, 3, (N, N))[..., None] * (yy >= 0)[..., None]
    os.makedirs(GEN, exist_ok=True)
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(out, quality=90)
    return out


def _gen_leaves(kind):
    """葉簇卡片貼圖（RGBA PNG）：許多小葉片疊成的一叢枝葉，邊緣不規則、透明"""
    out = os.path.join(GEN, f"himeji_leaf_{kind}.png")
    if os.path.exists(out):
        return out
    from PIL import Image, ImageDraw

    S = 1024
    rng = np.random.default_rng({"broad": 5, "light": 9, "pine": 13, "shrub": 17}[kind])
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    if kind == "pine":
        pal = [(36, 58, 30), (46, 72, 36), (58, 86, 42), (30, 48, 26), (70, 96, 50)]
        # 枝條
        for _ in range(7):
            a = rng.uniform(0, TAU)
            r = rng.uniform(0.25, 0.42) * S
            dr.line([(S / 2, S / 2), (S / 2 + math.cos(a) * r, S / 2 + math.sin(a) * r)], fill=(70, 55, 40, 255), width=7)
        for _ in range(1400):
            r = S * 0.4 * math.sqrt(rng.uniform(0, 1))
            a = rng.uniform(0, TAU)
            cx, cy = S / 2 + r * math.cos(a), S / 2 + r * math.sin(a) * 0.8
            c = pal[rng.integers(len(pal))]
            k = rng.uniform(0.8, 1.15)
            col = tuple(int(min(255, v * k)) for v in c) + (255,)
            for _ in range(5):
                b = rng.uniform(0, TAU)
                L = rng.uniform(18, 34)
                dr.line([(cx, cy), (cx + math.cos(b) * L, cy + math.sin(b) * L)], fill=col, width=3)
    else:
        pal = {"broad": [(52, 86, 30), (66, 102, 36), (82, 118, 42), (44, 72, 26), (98, 130, 50)],
               "light": [(88, 128, 44), (106, 146, 52), (124, 160, 62), (76, 112, 38), (140, 170, 70)],
               "shrub": [(70, 108, 36), (86, 126, 44), (104, 140, 52), (58, 92, 30), (120, 152, 60)]}[kind]
        n = 2600 if kind != "shrub" else 3400
        # 細枝
        for _ in range(9):
            a = rng.uniform(0, TAU)
            r = rng.uniform(0.2, 0.4) * S
            dr.line([(S / 2, S / 2), (S / 2 + math.cos(a) * r, S / 2 + math.sin(a) * r)], fill=(80, 64, 46, 255), width=5)
        order = np.argsort(rng.uniform(0, 1, n))
        for i in range(n):
            r = S * 0.44 * math.sqrt(rng.uniform(0, 1)) * (1 + 0.15 * math.sin(i))
            a = rng.uniform(0, TAU)
            cx, cy = S / 2 + r * math.cos(a), S / 2 + r * math.sin(a)
            # 上方（v 小）葉片較亮：模擬受光
            lit = 1.0 + 0.18 * (S / 2 - cy) / (S / 2) + rng.uniform(-0.12, 0.12)
            c = pal[(i * 7 + int(order[i])) % len(pal)]
            col = tuple(int(min(255, max(0, v * lit))) for v in c) + (255,)
            L = rng.uniform(22, 38) if kind != "shrub" else rng.uniform(14, 24)
            W = L * rng.uniform(0.38, 0.55)
            b = rng.uniform(0, TAU)
            ca, sa = math.cos(b), math.sin(b)
            pts = []
            for k in range(10):
                t = k / 9 * math.pi
                lx = -L / 2 + L * k / 9
                ly = W / 2 * math.sin(t)
                pts.append((cx + lx * ca - ly * sa, cy + lx * sa + ly * ca))
            for k in range(9, -1, -1):
                t = k / 9 * math.pi
                lx = -L / 2 + L * k / 9
                ly = -W / 2 * math.sin(t)
                pts.append((cx + lx * ca - ly * sa, cy + lx * sa + ly * ca))
            dr.polygon(pts, fill=col)
    im = im.resize((512, 512), Image.LANCZOS)
    # 半透明邊緣→二值（alpha mask 0.5 門檻），顏色往外擴避免黑邊
    arr = np.array(im).astype(np.float32)
    a = arr[..., 3:4] / 255.0
    rgb = np.where(a > 0.05, arr[..., :3] / np.maximum(a, 0.05), 0)
    mean = rgb[a[..., 0] > 0.5].mean(0)
    rgb = np.where(a > 0.05, rgb, mean)
    alpha = np.where(a[..., 0] > 0.45, 255, 0)
    os.makedirs(GEN, exist_ok=True)
    Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha]).astype(np.uint8), "RGBA").save(out)
    return out


# ====================================================================== Builder：屋瓦依屋面坡向決定 UV、葉片卡片用 0–1 UV
class _HB(Builder):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.oriented = set()
        self.cards = set()
        self.rot_layer = self.bm.faces.layers.int.new("roofrot")
        self.card_uv = {}

    def alpha_mat(self, name, png, rough=0.75):
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

    def img_mat(self, name, path, tile, rough=0.8):
        m = bpy.data.materials.new(f"{self.name}_{name}")
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        img = nt.nodes.new("ShaderNodeTexImage")
        img.image = bpy.data.images.load(path, check_existing=True)
        nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = rough
        return self._register(name, m, tile)

    def _uv(self):
        uv = self.bm.loops.layers.uv.verify()
        rl = self.rot_layer
        for f in self.bm.faces:
            mi = f.material_index
            tile = self.tiles[mi] if mi < len(self.tiles) else 1.0
            if mi in self.cards:
                for l, c in zip(f.loops, self.card_uv.get(len(f.verts), ((0, 0), (1, 0), (1, 1), (0, 1)))):
                    l[uv].uv = c
                continue
            n = f.normal.copy()
            if n.z < 0:
                n = -n
            if mi in self.oriented and n.z > 0.15 and math.hypot(n.x, n.y) > 0.04:
                # 下坡方向（平面）取最接近的建物主軸方向，瓦筋沿此方向
                base = math.radians(f[rl])
                ang = math.atan2(n.y, n.x)
                k = round((ang - base) / (math.pi / 2))
                a = base + k * math.pi / 2
                d = Vector((math.cos(a), math.sin(a), 0))
                t = Vector((-d.y, d.x, 0))
                for l in f.loops:
                    c = l.vert.co
                    l[uv].uv = (c.dot(t) / tile, -c.dot(d) / tile)
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


def _g(s):
    """屋面斷面（反り）：簷口平緩、往上漸陡"""
    return 0.38 * s + 0.62 * s * s


# ====================================================================== 姬路城
def himeji(path):
    b = _HB("Himeji", seed=23)
    bm = b.bm
    rl = b.rot_layer
    # ---------------------------------------------------------------- 材質
    grass = b.tex("grass", "grass_ground", tile=4.0, tint="#5d7f37", rough=0.95, normal=0.6)
    soil = b.tex("soil", "rock_ground", tile=4.0, tint="#6f6150", rough=0.95, normal=0.5)
    gravel = b.tex("gravel", "gravel_floor", tile=3.0, tint="#c9c0ad", rough=0.95, normal=0.4)
    stone = b.tex("ishigaki", "japanese_stone_wall", tile=5.0, tint="#a39a8a", gain=1.0, normal=1.2)
    plaster = b.tex("plaster", "plastered_wall_04", tile=5.0, tint="#f3f1ea", gain=1.03, rough=0.88, normal=0.25)
    soffit = b.color("soffit", "#ecebe5", rough=0.9)
    roof = b.tex("roof", _gen_kawara(), tile=2.4, normal=1.0)
    b.oriented.add(roof)
    noki = b.color("noki", "#4a4d52", rough=0.5)  # 軒瓦（瓦當）與破風邊瓦
    ridge = b.color("ridge", "#5c6066", rough=0.45)
    win = b.img_mat("window", _gen_window(), 0.8, rough=0.6)
    dark = b.color("dark", "#1e1d1b", rough=0.9)
    shachi_m = b.color("shachi", "#45484c", rough=0.4, metal=0.3)
    bark = b.color("bark", "#4e4236", rough=0.95)
    pbark = b.color("pine_bark", "#5b4636", rough=0.95)
    core_b = b.color("crown_core", "#2a4019", rough=0.95)
    core_p = b.color("pine_core", "#1f3218", rough=0.95)
    lf_broad = b.alpha_mat("leaf_broad", _gen_leaves("broad"))
    lf_light = b.alpha_mat("leaf_light", _gen_leaves("light"))
    lf_pine = b.alpha_mat("leaf_pine", _gen_leaves("pine"), rough=0.8)
    lf_shrub = b.alpha_mat("leaf_shrub", _gen_leaves("shrub"))

    def V(p):
        return bm.verts.new(p)

    def face(vs, mi, smooth=False):
        f = bm.faces.new(vs)
        f.material_index = mi
        f.smooth = smooth
        return f

    def strip(rows, mi, closed=True, smooth=False):
        for a, c in zip(rows, rows[1:]):
            n = len(a)
            for i in range(n if closed else n - 1):
                j = (i + 1) % n
                face([a[i], a[j], c[j], c[i]], mi, smooth)

    def place(fn, x, y, z, rot=0.0):
        """在局部座標建模後移到 (x,y,z) 並繞 Z 旋轉；記錄屋瓦的建物方向"""
        bm.verts.ensure_lookup_table()
        start = len(bm.verts)
        out = fn()
        bm.verts.ensure_lookup_table()
        vs = list(bm.verts[start:])
        M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, "Z")
        bmesh.ops.transform(bm, matrix=M, verts=vs)
        deg = int(round(math.degrees(rot))) % 360
        for f in {f for v in vs for f in v.link_faces}:
            f[rl] = deg
        return out

    def sweep(path, w, h, mi, side=None, below=False, caps=True):
        """沿折線掃出矩形斷面（屋脊、破風板）"""
        rings = []
        n = len(path)
        for k, p in enumerate(path):
            p = Vector(p)
            t = (Vector(path[min(k + 1, n - 1)]) - Vector(path[max(k - 1, 0)])).normalized()
            s = Vector(side) if side else t.cross(Vector((0, 0, 1)))
            s = s - t * s.dot(t)
            if s.length < 1e-5:
                s = Vector((1, 0, 0))
            s.normalize()
            u = s.cross(t).normalized()
            if u.z < 0:
                u = -u
            z0, z1 = (-h, 0.0) if below else (0.0, h)
            rings.append([V(p - s * w / 2 + u * z0), V(p + s * w / 2 + u * z0), V(p + s * w / 2 + u * z1), V(p - s * w / 2 + u * z1)])
        strip(rings, mi)
        if caps:
            face(list(reversed(rings[0])), mi)
            face(rings[-1], mi)

    # ---------------------------------------------------------------- 屋頂：環狀弧形屋面（腰屋根）
    def ring_pts(hx, hy, K):
        corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
        nrm = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        pts = []
        for e in range(4):
            (x0, y0), (x1, y1) = corners[e], corners[(e + 1) % 4]
            L = math.hypot(x1 - x0, y1 - y0)
            for j in range(K):
                t = 0.5 - 0.5 * math.cos(math.pi * j / K)
                dc = min(t, 1 - t) * L
                if j == 0:
                    o = Vector((nrm[e][0] + nrm[e - 1][0], nrm[e][1] + nrm[e - 1][1], 0))
                else:
                    o = Vector((nrm[e][0], nrm[e][1], 0))
                pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, dc, o))
        return pts

    def skirt(wx, wy, ix, iy, ov, rise, U, rows=8, K=14, s_end=1.0, thick=0.55, hips=True, onigawara=True):
        """局部座標：z=0 為下層牆頂。簷口（牆外 ov）由 z=-0.3 以下凹弧面升到內框 (ix,iy)。
        四隅上翹 U、外張；含軒先厚度、白漆喰軒裏、隅棟與鬼瓦。回傳各列環"""
        ex, ey = wx + ov, wy + ov
        Lc = min(7.0, 0.42 * min(2 * ex, 2 * ey))
        F = U * 0.7
        ze = -0.3
        rings = []
        for i in range(rows + 1):
            s = s_end * i / rows
            hx = ex + (ix - ex) * s
            hy = ey + (iy - ey) * s
            z = ze + rise * _g(s)
            fall = max(0.0, 1 - s / max(s_end, 1e-6) * 1.15) ** 1.6
            ring = []
            for x, y, dc, o in ring_pts(hx, hy, K):
                w = max(0.0, 1 - dc / Lc) ** 2.0 * fall
                ring.append(V((x + o.x * F * w, y + o.y * F * w, z + U * w)))
            rings.append(ring)
        strip(rings, roof)
        # 軒先：瓦當線（深灰）＋白漆喰茅負
        tl = 0.2
        low1 = [V((v.co.x, v.co.y, v.co.z - tl)) for v in rings[0]]
        strip([rings[0], low1], noki)
        low2 = []
        for v, (x, y, dc, o) in zip(rings[0], ring_pts(ex, ey, K)):
            low2.append(V((v.co.x - o.x * 0.06, v.co.y - o.y * 0.06, v.co.z - thick)))
        strip([low1, low2], plaster)
        # 軒裏：由軒先下緣斜回牆面（白漆喰）
        inner = [V((x, y, 0.05)) for x, y, dc, o in ring_pts(wx, wy, K)]
        strip([low2, inner], soffit)
        if hips:
            for e in range(4):
                path = [(r[e * K].co.x, r[e * K].co.y, r[e * K].co.z + 0.02) for r in rings]
                sweep(path, 0.55, 0.16, plaster, caps=False)
                sweep([(x, y, z + 0.1) for x, y, z in path], 0.36, 0.34, ridge)
                if onigawara:
                    p0 = rings[0][e * K].co
                    b.box(ridge, (0.5, 0.5, 0.75), (p0.x, p0.y, p0.z + 0.42), rot=(0, 0, math.atan2(p0.y, p0.x)))
        return rings

    def gable_wall(prof, x, depth, bottom, mi=None):
        """垂直三角山牆（YZ 平面多邊形），prof=[(y,z)...] 由左到右的上緣"""
        mi = plaster if mi is None else mi
        poly = [(prof[0][0], bottom)] + list(prof) + [(prof[-1][0], bottom)]
        fr = [V((x, y, z)) for y, z in poly]
        bk = [V((x - depth, y, z)) for y, z in poly]
        face(fr, mi)
        face(list(reversed(bk)), mi)
        n = len(poly)
        for i in range(n):
            j = (i + 1) % n
            face([fr[i], bk[i], bk[j], fr[j]], mi)

    def irimoya(wx, wy, ov, rise, U, sg=0.5, shachi=0.0, rows_h=6, rows_u=6, K=14, thick=0.55):
        """入母屋：局部座標、屋脊沿 X；下段四坡＋上段兩坡、左右垂直妻壁（入母屋破風）"""
        ex, ey = wx + ov, wy + ov
        ridge_hx = max(0.6, ex - ey)
        skirt(wx, wy, ridge_hx, 0.0, ov, rise, U, rows=rows_h, K=K, s_end=sg, thick=thick)
        ze = -0.3
        xg = ex + (ridge_hx - ex) * sg  # 妻壁位置
        e = 0.9  # 上段屋面伸出妻壁
        xs = [-(xg + e)] + [-xg + 2 * xg * k / 8 for k in range(9)] + [xg + e]
        sides = {}
        for side in (-1, 1):
            rows = []
            for i in range(rows_u + 1):
                s = sg + (1 - sg) * i / rows_u
                yv = side * ey * (1 - s)
                z = ze + rise * _g(s)
                rows.append([V((x, yv, z)) for x in xs])
            strip(rows if side < 0 else list(reversed(rows)), roof, closed=False)
            # 上段屋面下側（妻壁外伸出部分的白色軒裏）
            bot = [[V((v.co.x, v.co.y, v.co.z - 0.3)) for v in r] for r in rows]
            strip(list(reversed(bot)) if side < 0 else bot, soffit, closed=False)
            for idx in (0, -1):
                strip([[r[idx] for r in rows], [r[idx] for r in bot]], noki, closed=False)
            strip([rows[0], bot[0]], noki, closed=False)
            sides[side] = rows
        # 妻壁（白漆喰）＋破風板＋懸魚
        prof = []
        for side in (-1, 1):
            seq = sides[side] if side < 0 else list(reversed(sides[side]))
            for r in seq:
                prof.append((r[0].co.y, r[0].co.z - 0.42))
        prof = sorted(set((round(y, 4), round(z, 4)) for y, z in prof))
        zb = ze + rise * _g(sg) - 0.5
        for sx in (-1, 1):
            if sx > 0:
                gable_wall(prof, xg, 0.4, zb)
            else:
                gable_wall([(y, z) for y, z in reversed(prof)], -xg + 0.4, 0.4, zb)
                # 方向修正：-X 側的面法線由 recalc 處理
            pb = [(sx * (xg + e - 0.12), y, z + 0.4) for y, z in prof]
            sweep(pb, 0.3, 0.55, plaster, side=(1, 0, 0), below=True)
            b.box(plaster, (0.3, 1.1, 1.0), (sx * (xg + e - 0.1), 0, prof[len(prof) // 2][1] - 0.8))
        # 大棟：白漆喰の熨斗瓦＋灰色冠瓦
        zr = ze + rise
        L = xg + e + 0.3
        b.box(plaster, (2 * L, 0.7, 0.45), (0, 0, zr + 0.12))
        b.box(ridge, (2 * L + 0.1, 0.5, 0.45), (0, 0, zr + 0.5))
        if shachi > 0:
            for sx in (-1, 1):
                fish(sx * (L - 0.15), 0, zr + 0.7, sx, shachi)
        return zr

    def fish(x, y, z, sx, sc):
        """鯱：魚身向上彎、尾鰭朝天"""
        pts = [(x, y, z), (x - sx * 0.15 * sc, y, z + 0.45 * sc), (x - sx * 0.1 * sc, y, z + 0.9 * sc), (x + sx * 0.2 * sc, y, z + 1.25 * sc)]
        rs = []
        for k, p in enumerate(pts):
            r = sc * (0.28, 0.32, 0.22, 0.1)[k]
            rs.append([V((p[0] + r * math.cos(TAU * i / 6), p[1] + r * math.sin(TAU * i / 6) * 0.75, p[2])) for i in range(6)])
        strip(rs, shachi_m, smooth=True)
        face(rs[-1], shachi_m)
        tip = pts[-1]
        for d in (-1, 1):
            face([V(tip), V((tip[0] + sx * 0.45 * sc, tip[1] + d * 0.12 * sc, tip[2] + 0.35 * sc)),
                  V((tip[0] + sx * 0.1 * sc, tip[1] + d * 0.05 * sc, tip[2] + 0.5 * sc))], shachi_m)

    # ---------------------------------------------------------------- 破風
    def chidori(w, h, depth, ov=0.9, sideov=0.7, thick=0.5):
        """千鳥破風：局部座標，妻面朝 -Y、底邊中點在原點；屋面向 +Y 延伸 depth"""
        X = w / 2 + sideov
        zf = lambda u: h * (1 - u) ** 1.18 + 0.25 * max(0.0, u - 0.85) / 0.15
        us = [k / 8 for k in range(9)]
        prof = [(-X * u, zf(u)) for u in reversed(us)] + [(X * u, zf(u)) for u in us[1:]]
        front = [V((x, -ov, z)) for x, z in prof]
        back = [V((x, depth, z)) for x, z in prof]
        strip([back, front], roof, closed=False)
        fb = [V((x, -ov, z - thick)) for x, z in prof]
        bb = [V((x, depth, z - thick)) for x, z in prof]
        strip([fb, bb], soffit, closed=False)
        strip([front, fb], noki, closed=False)
        for i in (0, -1):
            strip([[front[i], back[i]], [fb[i], bb[i]]], noki, closed=False)
        # 破風板（白漆喰，沿兩斜邊，稍突出）
        sweep([(x, -ov - 0.05, z - 0.18) for x, z in prof[1:-1]], 0.3, 0.6, plaster, side=(0, 1, 0), below=True)
        # 妻壁
        tri = [(x, zf(abs(x) / X) - thick - 0.4) for x in [w / 2 * (k / 5 - 1) for k in range(11)]]
        poly = [(-w / 2, -2.0)] + tri + [(w / 2, -2.0)]
        fr = [V((x, 0, z)) for x, z in poly]
        bk = [V((x, depth, z)) for x, z in poly]
        face(list(reversed(fr)), plaster)
        face(bk, plaster)
        for i in range(len(poly)):
            j = (i + 1) % len(poly)
            face([fr[j], fr[i], bk[i], bk[j]], plaster)
        # 懸魚與棟端
        b.box(plaster, (0.9, 0.25, 1.0), (0, -ov - 0.08, zf(0) - thick - 0.95))
        b.box(ridge, (0.45, 0.6, 0.55), (0, -ov + 0.2, zf(0) + 0.15))

    def karahafu(w, hk, depth, ov=0.7, thick=0.5):
        """唐破風：中央弓起、兩端反轉下垂的曲線山牆"""
        X = w / 2 + 0.6
        zc = lambda x: hk * ((1 + math.cos(math.pi * min(1.0, abs(x) / X))) / 2) ** 0.8 + 0.15 * (abs(x) / X) ** 6
        xs = [X * (k / 10 - 1) for k in range(21)]
        front = [V((x, -ov, zc(x))) for x in xs]
        back = [V((x, depth, zc(x))) for x in xs]
        strip([back, front], roof, closed=False)
        fb = [V((x, -ov, zc(x) - thick)) for x in xs]
        bb = [V((x, depth, zc(x) - thick)) for x in xs]
        strip([fb, bb], soffit, closed=False)
        strip([front, fb], noki, closed=False)
        for i in (0, -1):
            strip([[front[i], back[i]], [fb[i], bb[i]]], noki, closed=False)
        sweep([(x, -ov - 0.05, zc(x) - 0.18) for x in xs[1:-1]], 0.3, 0.62, plaster, side=(0, 1, 0), below=True)
        poly = [(-w / 2, -1.5)] + [(x, zc(x) - thick - 0.5) for x in xs if abs(x) <= w / 2] + [(w / 2, -1.5)]
        fr = [V((x, -0.05, z)) for x, z in poly]
        bk = [V((x, depth, z)) for x, z in poly]
        face(list(reversed(fr)), plaster)
        face(bk, plaster)
        for i in range(len(poly)):
            j = (i + 1) % len(poly)
            face([fr[j], fr[i], bk[i], bk[j]], plaster)

    # ---------------------------------------------------------------- 牆與窗
    def window(w, h):
        """局部：窗面朝 -Y，底邊中點在原點"""
        b.box_base(win, (w, 0.14, h), (0, 0, 0))
        b.box_base(plaster, (w + 0.24, 0.2, 0.12), (0, -0.02, -0.12))

    def walls(w, d, h, z, n_ns, n_ew, wz=0.36, ww=1.0, wh=0.95, pair=False, skip=0.0, skip_sides=()):
        """局部：中心原點、底面 z；白漆喰牆＋各面格子窗"""
        b.box_base(plaster, (w, d, h), (0, 0, z))
        for side in range(4):
            nx, ny = [(0, -1), (1, 0), (0, 1), (-1, 0)][side]
            L = w if side % 2 == 0 else d
            n = n_ns if side % 2 == 0 else n_ew
            if n <= 0:
                continue
            for i in range(n):
                off = -L / 2 + 1.3 + (L - 2.6) * (i + 0.5) / n
                if abs(off) < skip and side in skip_sides:
                    continue
                offs = (off - 0.62, off + 0.62) if pair else (off,)
                for o in offs:
                    px = nx * (w / 2 + 0.02) + (-ny) * o
                    py = ny * (d / 2 + 0.02) + nx * o
                    rot = math.atan2(-nx, ny) + math.pi
                    M = Matrix.Translation((px, py, z + h * wz)) @ Matrix.Rotation(rot, 4, "Z")
                    bm.verts.ensure_lookup_table()
                    st = len(bm.verts)
                    window(ww, wh)
                    bm.verts.ensure_lookup_table()
                    bmesh.ops.transform(bm, matrix=M, verts=list(bm.verts[st:]))

    def lattice_bay(w, h, z, y_face):
        """出格子：白漆喰外框＋格子（局部，朝 -Y）"""
        b.box_base(plaster, (w + 0.6, 0.9, h + 0.9), (0, y_face - 0.35, z - 0.5))
        b.box_base(win, (w, 0.12, h), (0, y_face - 0.82, z))

    # ---------------------------------------------------------------- 石垣（扇之勾配）
    def ishigaki_poly(poly, z_bot, z_top, batter=0.3, p=2.4, rows=9, cap=None, inset_top=0.0):
        """沿逆時針多邊形的外側做扇形弧線石垣，cap 指定頂面材質"""
        n = len(poly)
        H = z_top - z_bot
        # 各頂點的外法線（角平分）
        outs = []
        for i in range(n):
            a, c, d = Vector((*poly[i - 1], 0)), Vector((*poly[i], 0)), Vector((*poly[(i + 1) % n], 0))
            e1 = (c - a).normalized()
            e2 = (d - c).normalized()
            n1 = Vector((e1.y, -e1.x, 0))
            n2 = Vector((e2.y, -e2.x, 0))
            m = (n1 + n2).normalized()
            outs.append(m / max(0.35, m.dot(n1)))
        rs = []
        for i in range(rows + 1):
            t = i / rows
            o = batter * H * (1 - t) ** p
            z = z_bot + H * t
            rs.append([V((poly[k][0] + outs[k].x * o, poly[k][1] + outs[k].y * o, z)) for k in range(n)])
        strip(rs, stone)
        if cap is not None:
            # 頂面（多邊形；以中心扇形三角化）
            cx = sum(q[0] for q in poly) / n
            cy = sum(q[1] for q in poly) / n
            c = V((cx, cy, z_top))
            for k in range(n):
                face([rs[-1][k], rs[-1][(k + 1) % n], c], cap)
        return rs

    # ---------------------------------------------------------------- 天守（多重塔）
    def tower(cx, cy, z, levels, ov=2.0, U=1.0, top_U=1.25, shachi=1.6, gables=None, lattice=None, rot=0.0, rise_k=0.6,
              win_pair=None):
        """levels: [(w, d, h, n_ns, n_ew)]；gables: {level: [(side, kind, w, h, off)]}"""
        gables = gables or {}
        win_pair = win_pair or set()

        def build():
            zz = z
            for k, (w, d, h, n_ns, n_ew) in enumerate(levels):
                last = k == len(levels) - 1
                walls(w, d, h + 0.45, zz - 0.45, n_ns, n_ew, wz=0.4 if not last else 0.33, ww=0.95 if not last else 1.2,
                      wh=0.95 if not last else 1.3, pair=k in win_pair, skip=3.2 if lattice and k in lattice else 0.0,
                      skip_sides=(0, 2))
                if lattice and k in lattice:
                    for sgn in (-1, 1):
                        def lb(sgn=sgn):
                            lattice_bay(lattice[k], 1.5, 0, 0)
                        place(lb, 0, sgn * (d / 2 + 0.02), zz + h * 0.3, 0.0 if sgn < 0 else math.pi)
                z_e = zz + h
                if not last:
                    w2, d2 = levels[k + 1][:2]
                    ix, iy = w2 / 2 + 0.03, d2 / 2 + 0.03
                    run = min(w / 2 + ov - ix, d / 2 + ov - iy)
                    rise = rise_k * run + 0.3
                    place(lambda: skirt(w / 2, d / 2, ix, iy, ov, rise, U), 0, 0, z_e)
                    for side, kind, gw, gh, off in gables.get(k, []):
                        runs = (d / 2 + ov - iy) if side in "SN" else (w / 2 + ov - ix)
                        mf = 0.3
                        zf = z_e - 0.3 + rise * _g(mf) + 0.1
                        depth = runs * (1 - mf) + 0.6
                        half = (d / 2 + ov) if side in "SN" else (w / 2 + ov)
                        rr = half - runs * mf
                        if side == "S":
                            pos, rr_ = (off, -rr), 0.0
                        elif side == "N":
                            pos, rr_ = (-off, rr), math.pi
                        elif side == "E":
                            pos, rr_ = (rr, off), math.pi / 2
                        else:
                            pos, rr_ = (-rr, -off), -math.pi / 2
                        if kind == "c":
                            place(lambda gw=gw, gh=gh, depth=depth: chidori(gw, gh, depth), pos[0], pos[1], zf, rr_)
                        elif kind == "k":
                            # 唐破風在簷口
                            half_e = half
                            pe = {"S": (off, -half_e), "N": (-off, half_e), "E": (half_e, off), "W": (-half_e, -off)}[side]
                            place(lambda gw=gw, gh=gh: karahafu(gw, gh, runs * 0.55), pe[0], pe[1], z_e - 0.3, rr_)
                        else:  # 大入母屋破風
                            place(lambda gw=gw, gh=gh, depth=depth: chidori(gw, gh, depth * 1.2, ov=1.2, sideov=1.0, thick=0.6),
                                  pos[0], pos[1], zf - 0.4, rr_)
                    zz = z_e - 0.3 + rise
                else:
                    if w >= d:
                        place(lambda: irimoya(w / 2, d / 2, ov + 0.2, rise_k * 1.25 * (d / 2 + ov), top_U, shachi=shachi), 0, 0, z_e)
                    else:
                        place(lambda: irimoya(d / 2, w / 2, ov + 0.2, rise_k * 1.25 * (w / 2 + ov), top_U, shachi=shachi), 0, 0, z_e,
                              math.pi / 2)
                    return z_e

        return place(build, cx, cy, 0, rot)

    def yagura(cx, cy, z, L, D, h1, rot, h2=None, L2=None, front_chidori=(), ov=1.5, n_win=None, base_z=None):
        """櫓／多聞櫓：1–2 層白壁＋入母屋頂；front_chidori 在正面屋頂加千鳥破風；base_z 時下方加石垣台"""
        if base_z is not None:
            c0, s0 = math.cos(rot), math.sin(rot)
            hw, hd = L / 2 + 0.3, D / 2 + 0.3
            poly = [(cx + c0 * u - s0 * v, cy + s0 * u + c0 * v) for u, v in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))]
            ishigaki_poly(poly, base_z, z, batter=0.22, cap=gravel)

        # irimoya 以 z=0 為牆頂，因此分兩段放置
        if not h2:
            def b1():
                nw = n_win or max(2, int(L / 4.2))
                walls(L, D, h1 + 0.45, -h1 - 0.45, nw, max(1, int(D / 4)), wz=0.42, ww=1.0, wh=0.85, pair=True)
                irimoya(L / 2, D / 2, ov, 0.62 * (D / 2 + ov), 0.75)
            place(b1, cx, cy, z + h1, rot)
        else:
            L2_ = L2 or L * 0.6
            D2 = D - 1.2
            xo = (L - L2_) / 2
            run = D / 2 + ov - (D2 / 2 + 0.03)
            rise = 0.55 * run + 0.3

            def b1():
                nw = n_win or max(2, int(L / 4.2))
                walls(L, D, h1 + 0.45, -h1 - 0.45, nw, max(1, int(D / 4)), wz=0.42, ww=1.0, wh=0.85, pair=True)
                rs = skirt(L / 2, D / 2, L / 2 - 0.4, D2 / 2 + 0.03, ov, rise, 0.6, rows=6, K=12)
                face(list(rs[-1]), roof)
            place(b1, cx, cy, z + h1, rot)
            c, s_ = math.cos(rot), math.sin(rot)

            def b2():
                walls(L2_, D2, h2 + 0.45, -h2 - 0.45, max(2, int(L2_ / 4)), 1, wz=0.42, ww=1.0, wh=0.85, pair=True)
                irimoya(L2_ / 2, D2 / 2, ov, 0.62 * (D2 / 2 + ov), 0.85, shachi=0.9)
            place(b2, cx + c * xo, cy + s_ * xo, z + h1 - 0.3 + rise + h2, rot)
        for (u, gw, gh) in front_chidori:
            c, s_ = math.cos(rot), math.sin(rot)
            run = D / 2 + ov
            mf = 0.3
            zf = z + h1 - 0.3 + 0.62 * (D / 2 + ov) * _g(mf) + 0.1
            px, py = u, -(D / 2 + ov) + run * mf
            place(lambda gw=gw, gh=gh: chidori(gw, gh, run * 0.6, ov=0.8, sideov=0.6), cx + c * px - s_ * py, cy + s_ * px + c * py, zf, rot)

    def dobei(p0, p1, z, h=2.4):
        """土塀：白壁＋小瓦頂（兩坡）"""
        x0, y0 = p0
        x1, y1 = p1
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)

        def mk():
            b.box_base(plaster, (L, 0.55, h), (0, 0, -0.3))
            # 兩坡瓦頂
            for sgn in (-1, 1):
                a = [V((-L / 2 - 0.2, 0, h + 0.35)), V((L / 2 + 0.2, 0, h + 0.35))]
                c2 = [V((-L / 2 - 0.2, sgn * 0.95, h - 0.15)), V((L / 2 + 0.2, sgn * 0.95, h - 0.15))]
                face([a[0], a[1], c2[1], c2[0]], roof)
                c3 = [V((-L / 2 - 0.2, sgn * 0.95, h - 0.3)), V((L / 2 + 0.2, sgn * 0.95, h - 0.3))]
                face([c2[0], c2[1], c3[1], c3[0]], noki)
                c4 = [V((-L / 2 - 0.2, sgn * 0.28, h - 0.3)), V((L / 2 + 0.2, sgn * 0.28, h - 0.3))]
                face([c3[0], c3[1], c4[1], c4[0]], soffit)
            b.box(ridge, (L + 0.5, 0.36, 0.3), (0, 0, h + 0.42))
        place(mk, (x0 + x1) / 2, (y0 + y1) / 2, z, ang)

    # ================================================================ 地形與台地
    Z_COURT = 24.5   # 備前丸（中庭）
    Z_UP = 40.3      # 小天守群所在的上段
    # 中庭外圍（逆時針），南緣即前景石垣線
    court = [(-36.0, -25.0), (26.0, -52.0), (48.0, 8.0), (22.0, 64.0), (-62.0, 62.0), (-60.0, -14.0)]
    beta = math.radians(22.9)

    def court_dist(x, y):
        """點到中庭多邊形的距離（外為正）"""
        p = Vector((x, y))
        inside = True
        best = 1e9
        n = len(court)
        for i in range(n):
            a, c = Vector(court[i]), Vector(court[(i + 1) % n])
            e = c - a
            t = max(0.0, min(1.0, (p - a).dot(e) / e.length_squared))
            best = min(best, (a + e * t - p).length)
            if (e.x * (p.y - a.y) - e.y * (p.x - a.x)) < 0:
                inside = False
        return -best if inside else best

    def terrain_h(x, y):
        d = court_dist(x, y)
        if d < 0:
            return Z_COURT - 6.0
        t = min(1.0, d / 115.0)
        h = 12.6 * (1 - t) ** 1.25 - 1.0
        h += 0.8 * noise.noise(Vector((x / 30, y / 30, 0.7))) * min(1.0, d / 20)
        return h

    # 地形網格（相機前方較密）
    R = 230.0
    NR, NA = 46, 140
    grid = []
    for i in range(NR + 1):
        r = R * (i / NR) ** 1.25
        row = []
        for j in range(NA if i else 1):
            a = TAU * j / NA
            x, y = r * math.cos(a), r * math.sin(a)
            row.append(V((x, y, terrain_h(x, y))))
        grid.append(row)
    for j in range(NA):
        face([grid[0][0], grid[1][j], grid[1][(j + 1) % NA]], grass, True)
    for i in range(1, NR):
        for j in range(NA):
            k = (j + 1) % NA
            face([grid[i][j], grid[i + 1][j], grid[i + 1][k], grid[i][k]], grass, True)
    edge = grid[-1]
    bot = [V((v.co.x, v.co.y, -6)) for v in edge]
    for j in range(NA):
        k = (j + 1) % NA
        face([edge[k], edge[j], bot[j], bot[k]], soil)
    face(list(reversed(bot)), soil)
    # 坡面上的裸土
    for f in bm.faces:
        if f.material_index == grass:
            c = f.calc_center_median()
            if noise.noise(Vector((c.x / 18, c.y / 18, 3.1))) > 0.35:
                f.material_index = soil

    # 中庭石垣（扇之勾配）＋碎石頂面
    ishigaki_poly(court, 8.0, Z_COURT, batter=0.3, cap=gravel)
    # 上段（小天守群）：L 形兩段
    up1 = [(-56.0, -2.0), (-14.5, -4.0), (-14.5, 13.0), (-56.0, 14.0)]
    up2 = [(-58.0, 13.0), (16.0, 13.0), (18.0, 56.0), (-58.0, 56.0)]
    ishigaki_poly(up1, Z_COURT - 1.0, Z_UP, batter=0.28, cap=gravel)
    ishigaki_poly(up2, Z_COURT - 1.0, Z_UP + 0.35, batter=0.28, cap=gravel)

    # ================================================================ 大天守（5 重 6 階）
    W1, D1 = 26.0, 21.0
    lv = [(26.0, 21.0, 4.7, 9, 7), (23.6, 18.6, 4.4, 8, 6), (20.2, 15.4, 4.0, 7, 5), (16.8, 12.4, 3.9, 6, 4), (13.0, 9.6, 3.9, 5, 4)]
    ZK = Z_UP + 0.55  # 天守台石垣頂
    ishigaki_poly([(-W1 / 2 - 0.3, -D1 / 2 - 0.3), (W1 / 2 + 0.3, -D1 / 2 - 0.3), (W1 / 2 + 0.3, D1 / 2 + 0.3), (-W1 / 2 - 0.3, D1 / 2 + 0.3)],
                  Z_COURT - 1.0, ZK, batter=0.3, p=2.3, cap=gravel)
    gab = {
        0: [("S", "c", 5.0, 2.6, -6.0), ("S", "c", 5.0, 2.6, 6.0), ("N", "c", 5.0, 2.6, 0.0)],
        1: [("S", "k", 6.6, 1.6, 0.0), ("N", "k", 6.6, 1.6, 0.0), ("E", "b", 13.0, 7.2, 0.0), ("W", "b", 13.0, 7.2, 0.0)],
        2: [("S", "c", 5.4, 2.8, -4.4), ("S", "c", 5.4, 2.8, 4.4), ("N", "c", 5.4, 2.8, -4.4), ("N", "c", 5.4, 2.8, 4.4),
            ("E", "k", 4.4, 1.3, 0.0), ("W", "k", 4.4, 1.3, 0.0)],
        3: [("S", "c", 7.6, 3.6, 0.0), ("N", "c", 7.6, 3.6, 0.0), ("E", "c", 4.8, 2.5, 0.0), ("W", "c", 4.8, 2.5, 0.0)],
    }
    tower(0, 0, ZK, lv, ov=2.1, U=1.05, top_U=1.35, gables=gab, lattice={1: 5.2}, shachi=2.0, win_pair={0, 1, 2, 3})

    # ================================================================ 小天守與渡櫓
    smalls = [
        (-21.0, 22.0, Z_UP + 0.35, [(15.0, 12.6, 4.0, 4, 3), (12.4, 10.2, 3.8, 3, 3), (9.6, 7.8, 3.5, 3, 2)]),   # 西小天守
        (-38.0, 40.0, Z_UP + 0.35, [(16.0, 13.4, 4.2, 4, 3), (13.2, 10.8, 3.9, 3, 3), (10.2, 8.2, 3.6, 3, 2)]),  # 乾小天守
        (4.0, 38.0, Z_UP + 0.35, [(12.6, 10.6, 3.9, 3, 3), (10.4, 8.6, 3.6, 3, 2), (8.0, 6.6, 3.3, 2, 2)]),     # 東小天守
    ]
    sgab = {
        0: [("S", "c", 4.4, 2.3, 0.0), ("E", "c", 3.8, 2.0, 0.0), ("W", "c", 3.8, 2.0, 0.0)],
        1: [("S", "k", 3.8, 1.0, 0.0), ("W", "c", 3.4, 1.9, 0.0)],
    }
    for cx, cy, zb, levels in smalls:
        w, d = levels[0][:2]
        ishigaki_poly([(cx - w / 2 - 0.3, cy - d / 2 - 0.3), (cx + w / 2 + 0.3, cy - d / 2 - 0.3), (cx + w / 2 + 0.3, cy + d / 2 + 0.3),
                       (cx - w / 2 - 0.3, cy + d / 2 + 0.3)], zb - 1.0, zb + 2.2, batter=0.15, cap=gravel)
        tower(cx, cy, zb + 2.2, levels, ov=1.8, U=0.8, top_U=1.0, shachi=1.25, gables=sgab, win_pair={0})
    # 渡櫓（2 層）
    yagura(-14.0, 14.5, Z_UP + 0.35, 10.0, 7.5, 3.6, math.radians(45), h2=3.2, L2=7.0, base_z=Z_COURT - 1.0)            # イ：大天守—西小天守
    yagura(-29.5, 31.0, Z_UP + 0.35, 14.0, 7.5, 3.6, math.radians(64), h2=3.2, L2=10.0, base_z=Z_COURT - 1.0)           # ロ：西小天守—乾小天守
    yagura(-17.0, 41.0, Z_UP + 0.35, 22.0, 7.5, 3.6, 0.0, h2=3.2, L2=16.0, base_z=Z_COURT - 1.0)                        # ハ：乾小天守—東小天守
    yagura(3.0, 22.0, Z_UP + 0.35, 12.0, 7.5, 3.6, math.radians(90), h2=3.2, L2=8.0, base_z=Z_COURT - 1.0)              # ニ：東小天守—大天守

    # ================================================================ 前景：前方石垣上的櫓群（面向相機）
    rot_f = -beta
    c_, s_ = math.cos(rot_f), math.sin(rot_f)

    def along(u, v=0.0):
        """前景石垣線上的點：u 沿線、v 往內（北）"""
        x0, y0 = court[0]
        return (x0 + c_ * u - s_ * v, y0 + s_ * u + c_ * v)

    # 左：長多聞櫓（1 層，左端千鳥破風）
    p = along(14.0, 4.6)
    yagura(p[0], p[1], Z_COURT, 26.0, 8.0, 4.6, rot_f, front_chidori=((-9.5, 4.2, 2.4),), n_win=6)
    # 右：2 層櫓（右端入母屋破風）
    p = along(43.0, 4.4)
    yagura(p[0], p[1], Z_COURT, 30.0, 7.8, 4.4, rot_f, h2=3.8, L2=15.0)
    # 土塀
    dobei(along(0.5, 1.0), along(1.0, 1.0), Z_COURT)
    # 石垣下方的低櫓（瓦頂線）
    for u0, u1 in ((24.0, 48.0),):
        a0, a1 = along(u0, -7.5), along(u1, -7.5)
        dobei(a0, a1, terrain_h(*along((u0 + u1) / 2, -7.5)) + 0.2, h=2.8)

    # ================================================================ 樹木（葉簇卡片）
    rng = b.rng

    def tube(path, r0, r1, mi, seg=6):
        rings = []
        n = len(path)
        for k, p in enumerate(path):
            p = Vector(p)
            t = (Vector(path[min(k + 1, n - 1)]) - Vector(path[max(k - 1, 0)])).normalized()
            a = t.orthogonal().normalized()
            c = t.cross(a)
            r = r0 + (r1 - r0) * k / (n - 1)
            rings.append([V(p + (a * math.cos(TAU * i / seg) + c * math.sin(TAU * i / seg)) * r) for i in range(seg)])
        strip(rings, mi, smooth=True)
        face(rings[-1], mi)

    def blob(mi, loc, rx, ry, rz, lump=0.3, sub=1):
        off = Vector((rng.uniform(0, 99), rng.uniform(0, 99), rng.uniform(0, 99)))
        r = bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=1.0, matrix=Matrix.Identity(4))
        for v in r["verts"]:
            q = v.co.copy()
            n = noise.noise(q * 1.6 + off) * 0.7 + noise.noise(q * 3.5 + off) * 0.3
            k = 1 + lump * n
            v.co = Vector((loc[0] + q.x * rx * k, loc[1] + q.y * ry * k, loc[2] + q.z * rz * k))
        for f in {f for v in r["verts"] for f in v.link_faces}:
            f.material_index = mi
            f.smooth = True

    def card(mi, c, nrm, size, spin):
        """一片葉簇卡片：中心 c、法線 nrm、邊長 size"""
        n = Vector(nrm).normalized()
        a = n.orthogonal().normalized()
        bb = n.cross(a)
        ca, sa = math.cos(spin), math.sin(spin)
        u = (a * ca + bb * sa) * size / 2
        v = (bb * ca - a * sa) * size / 2
        c = Vector(c)
        face([V(c - u - v), V(c + u - v), V(c + u + v), V(c - u + v)], mi)

    def crown(cx, cy, cz, rx, rz, mats, core, n_cards, csize, flat=1.0):
        """樹冠：深色核心＋分布在橢球表層、大致朝外的葉簇卡片"""
        blob(core, (cx, cy, cz), rx * 0.78, rx * 0.78, rz * 0.72 * flat, lump=0.35)
        for _ in range(n_cards):
            d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1) * 0.8 + 0.25)).normalized()
            rr = rng.uniform(0.72, 1.02)
            pnt = (cx + d.x * rx * rr, cy + d.y * rx * rr, cz + d.z * rz * rr * flat)
            nrm = (d + Vector((rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), rng.uniform(-0.2, 0.6)))).normalized()
            mi = mats[0] if d.z > 0.25 or rng.random() < 0.3 else mats[min(1, len(mats) - 1)]
            card(mi, pnt, nrm, csize * rng.uniform(0.8, 1.25), rng.uniform(0, TAU))

    def broadleaf(x, y, z, h, light=False, spread=1.0, detail=1.0):
        R_ = h * rng.uniform(0.3, 0.38) * spread
        cz = z + h - R_ * 0.9
        lean = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)) * 0.05 * h
        tube([(x, y, z - 0.6), (x + lean.x * 0.5, y + lean.y * 0.5, z + h * 0.3), (x + lean.x, y + lean.y, cz - R_ * 0.2)], h * 0.03, h * 0.016, bark)
        # 主枝
        for _ in range(4):
            a = rng.uniform(0, TAU)
            p0 = Vector((x + lean.x * 0.6, y + lean.y * 0.6, z + h * 0.42))
            p1 = Vector((x + lean.x + math.cos(a) * R_ * 0.6, y + lean.y + math.sin(a) * R_ * 0.6, cz))
            tube([p0, (p0 + p1) / 2 + Vector((0, 0, h * 0.04)), p1], h * 0.014, h * 0.007, bark, seg=5)
        mats = (lf_light, lf_broad) if light else (lf_broad, lf_broad)
        n = rng.randint(5, 8)
        for i in range(n):
            a = rng.uniform(0, TAU)
            rr = R_ * math.sqrt(rng.uniform(0.0, 1)) * 0.55
            dz = rng.uniform(-0.35, 0.45) * R_
            br = R_ * rng.uniform(0.45, 0.62)
            nc = int(16 + 30 * (br / 3.0))
            crown(x + lean.x + rr * math.cos(a), y + lean.y + rr * math.sin(a), cz + dz, br, br * 0.85, mats, core_b,
                  int(min(nc, 60) * detail), br * (0.95 if detail >= 1 else 1.3))

    def pine_tree(x, y, z, h):
        pts = [(x, y, z - 0.5)]
        px, py = x, y
        ang = rng.uniform(0, TAU)
        for k in range(1, 5):
            ang += rng.uniform(-0.9, 0.9)
            px += math.cos(ang) * h * 0.08
            py += math.sin(ang) * h * 0.08
            pts.append((px, py, z + h * 0.85 * k / 4))
        tube(pts, h * 0.04, h * 0.02, pbark)
        npad = rng.randint(5, 7)
        for i in range(npad):
            f = 0.35 + 0.65 * i / (npad - 1)
            k = min(3, int(f * 4))
            p0 = Vector(pts[k]).lerp(Vector(pts[k + 1]), f * 4 - k) if k < 4 else Vector(pts[-1])
            a = rng.uniform(0, TAU)
            reach = h * (0.34 - 0.22 * f) * rng.uniform(0.7, 1.2)
            c = p0 + Vector((math.cos(a) * reach, math.sin(a) * reach, h * 0.03))
            tube([p0, (p0 + c) / 2 + Vector((0, 0, h * 0.03)), c], h * 0.014, h * 0.008, pbark, seg=5)
            rp = h * (0.22 - 0.09 * f) * rng.uniform(0.85, 1.15)
            # 雲狀枝葉層：扁平核心＋大致水平的針葉卡片
            blob(core_p, (c.x, c.y, c.z + rp * 0.05), rp * 0.85, rp * 0.8, rp * 0.22, lump=0.3)
            for _ in range(int(10 + 10 * rp)):
                a2 = rng.uniform(0, TAU)
                r2 = rp * math.sqrt(rng.uniform(0, 1))
                card(lf_pine, (c.x + r2 * math.cos(a2), c.y + r2 * math.sin(a2), c.z + rp * rng.uniform(0.0, 0.3)),
                     (rng.uniform(-0.35, 0.35), rng.uniform(-0.35, 0.35), 1), rp * rng.uniform(0.7, 1.0), rng.uniform(0, TAU))

    def shrub(x, y, z, r):
        crown(x, y, z + r * 0.45, r, r * 0.6, (lf_shrub, lf_light), core_b, int(14 + 10 * r), r * 0.9, flat=1.0)

    C = Vector((-54.7, -150.4, 0))
    fwd = Vector((math.sin(beta), math.cos(beta), 0))
    rgt = Vector((math.cos(beta), -math.sin(beta), 0))

    def cam_pt(depth, lateral):
        p = C + fwd * depth + rgt * lateral
        return p.x, p.y

    # 參考照中的主要樹木（相機座標：距離、橫向、樹高）
    hero = [
        (58, 15, 19, "b"), (52, 24, 16, "b"), (66, 6, 15, "l"),                # 右側大樹（樟樹）
        (88, -4, 15, "l"), (95, -14, 14, "l"), (82, 4, 12, "b"),               # 中央闊葉樹（遮住石垣下部）
        (40, -14, 9, "l"), (34, -22, 7, "l"), (46, -28, 11, "l"), (62, -36, 14, "l"),  # 左側
        (75, -26, 13, "b"), (105, -30, 16, "b"), (100, 18, 12, "b"),
    ]
    for dep, lat, h, k in hero:
        x, y = cam_pt(dep, lat)
        broadleaf(x, y, terrain_h(x, y), h, light=(k == "l"), spread=1.15)
    for dep, lat, h in ((38, 5, 6.0), (44, 10, 7.0), (35, -2, 5.0), (50, 1, 6.5)):
        x, y = cam_pt(dep, lat)
        pine_tree(x, y, terrain_h(x, y), h)
    for dep, lat, r in ((22, -12, 2.2), (25, -8, 2.6), (28, -16, 2.4), (24, -3, 1.8), (30, 2, 2.0), (27, 8, 2.2), (32, 12, 2.4),
                        (20, -18, 2.0), (35, -10, 2.8)):
        x, y = cam_pt(dep, lat)
        shrub(x, y, terrain_h(x, y), r)
    # 外圍林木（網站環視時的周邊樹林）
    pts = b.scatter(70, 70, 215, min_dist=13.0, avoid=lambda x, y: court_dist(x, y) < 6 or
                    (C - Vector((x, y, 0))).length < 30)
    for x, y in pts:
        h = rng.uniform(9, 15)
        if rng.random() < 0.25:
            pine_tree(x, y, terrain_h(x, y), h * 0.6)
        else:
            broadleaf(x, y, terrain_h(x, y), h, light=rng.random() < 0.4, detail=0.35)
    # 中庭與上段的松樹
    for x, y in ((-30.0, -12.0), (14.0, -30.0), (30.0, -10.0)):
        pine_tree(x, y, Z_COURT, 6.5)

    # 卡片的 UV（四邊形 0–1）
    b.card_uv[4] = ((0, 0), (1, 0), (1, 1), (0, 1))
    _export(b, path)


def _export(b, path):
    b.build_object()
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_apply=True, export_yup=True,
                              export_image_format="AUTO", export_jpeg_quality=82)
