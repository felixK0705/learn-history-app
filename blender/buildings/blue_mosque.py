"""blue_mosque 伊斯坦堡蘇丹艾哈邁德清真寺（藍色清真寺）寫實模型（公尺）

- 禮拜殿約 56 × 56 m（兩側另有雙層拱廊，總寬約 66 m）；中央圓頂直徑 23.5 m、頂高約 43 m，
  坐落在 28 窗鼓座上；四座半圓頂向四方層層落下，每座半圓頂外緣再帶三座小半圓頂（exedra）
- 禮拜殿四角各一座小圓頂；中央方形四角為八角形「重力塔」（頂上小圓頂），半圓頂與角圓頂之間另有小八角塔
- 外牆三層拱窗、扶壁與簷口；六座宣禮塔高約 64 m：殿身四角各一（三層陽台），前庭外側兩角各一（兩層陽台）
- 前庭（avlu）與殿身等寬，四周為帶小圓頂的拱廊，中央有六角淨身亭；外圍有低矮的院牆與公園
- 外觀為淺灰石灰岩、鉛覆圓頂（藍灰色、帶接縫稜線）

座標：禮拜殿中心在原點，+X 為東北（蘇丹艾哈邁德公園方向，參考照拍攝側），
+Y 為西北（前庭方向），-Y 為東南（朝拜牆）。
"""

import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

from lib import TAU, TEX, Builder, tinted_texture

# 目標點、方位角（0 = 從 -Y 往 +Y 看；90 = 從 +X 公園方向看）、仰角、距離、焦距
CAMERA = ((12.9, 0.5, 29.9), 104.5, -9.0, 180.0, 60)

GEN = os.path.join(TEX, "_gen", "bluemosque_v1")


# ====================================================================== 自產貼圖
def _gen_textures():
    """葉面斑駁貼圖：許多小葉片橢圓斑點（亮暗交錯），依各種綠色上色；可無縫重複"""
    import numpy as np
    from PIL import Image, ImageFilter

    variants = {"leaf_l": "#86a64c", "leaf_m": "#62873a", "leaf_d": "#41602a", "cypress": "#3a5130"}
    if all(os.path.exists(os.path.join(GEN, k, "diff.jpg")) for k in variants):
        return
    rng = np.random.default_rng(7)
    N = 512
    lum = np.full((N, N), 0.28, np.float32)
    yy, xx = np.mgrid[0:N, 0:N]
    for layer, (n, lv) in enumerate(((1600, 0.55), (1500, 0.85), (900, 1.25))):
        for _ in range(n):
            cx, cy = rng.integers(0, N, 2)
            r = rng.uniform(3, 9)
            x0, x1 = max(0, int(cx - r - 1)), min(N, int(cx + r + 2))
            y0, y1 = max(0, int(cy - r - 1)), min(N, int(cy + r + 2))
            ang = rng.uniform(0, math.pi)
            dx = xx[y0:y1, x0:x1] - cx
            dy = yy[y0:y1, x0:x1] - cy
            u = dx * math.cos(ang) + dy * math.sin(ang)
            v = -dx * math.sin(ang) + dy * math.cos(ang)
            m = (u / r) ** 2 + (v / (r * 0.55)) ** 2 < 1
            lum[y0:y1, x0:x1][m] = lv * rng.uniform(0.85, 1.15)
    rolled = np.roll(np.roll(lum, N // 2, 0), N // 2, 1)
    w = np.clip(np.minimum(np.minimum(xx, N - 1 - xx), np.minimum(yy, N - 1 - yy)) / 48.0, 0, 1)
    lum = lum * w + rolled * (1 - w)
    lum = lum / lum.mean()
    for name, hexc in variants.items():
        d = os.path.join(GEN, name)
        os.makedirs(d, exist_ok=True)
        c = np.array([int(hexc[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
        img = np.clip(lum[..., None] * c[None, None, :], 0, 255).astype(np.uint8)
        Image.fromarray(img).filter(ImageFilter.GaussianBlur(0.6)).save(os.path.join(d, "diff.jpg"), quality=90)


def gen_leaf_png(kind):
    """葉簇卡片貼圖（RGBA PNG）：數個小葉叢（深色葉間陰影＋多層亮暗葉片），叢間留空隙"""
    import numpy as np
    from PIL import Image, ImageDraw

    out = os.path.join(GEN, f"leafcard_{kind}.png")
    if os.path.exists(out):
        return out
    os.makedirs(GEN, exist_ok=True)
    S = 1024
    rng = np.random.default_rng({"broad": 5, "light": 9, "dark": 13}[kind])
    pal = {"broad": [(74, 106, 36), (88, 122, 42), (104, 138, 48), (64, 94, 32), (118, 150, 56)],
           "light": [(118, 150, 50), (136, 166, 58), (152, 180, 66), (104, 138, 44), (168, 192, 76)],
           "dark": [(52, 78, 30), (62, 90, 34), (74, 102, 38), (46, 70, 28), (84, 112, 44)]}[kind]
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    subs = []
    for _ in range(8):
        a = rng.uniform(0, TAU)
        r = S * rng.uniform(0.04, 0.3)
        subs.append((S / 2 + r * math.cos(a), S / 2 + r * math.sin(a), S * rng.uniform(0.11, 0.17)))
    for sx, sy, sr in subs:
        dr.line([(S / 2, S / 2), (sx, sy)], fill=(84, 68, 50, 255), width=5)
    for sx, sy, sr in subs:
        dk = tuple(int(v * 0.35) for v in pal[0]) + (255,)
        pts = [(sx + sr * 0.85 * (1 + 0.12 * math.sin(TAU * j / 24 * 5 + sx)) * math.cos(TAU * j / 24),
                sy + sr * 0.85 * (1 + 0.12 * math.sin(TAU * j / 24 * 5 + sx)) * math.sin(TAU * j / 24)) for j in range(24)]
        dr.polygon(pts, fill=dk)
    Lr = (62, 100)
    for layer in range(3):
        for sx, sy, sr in subs:
            base = pal[rng.integers(len(pal))]
            la = sum(Lr) / 2
            nleaf = int(1.1 * math.pi * sr * sr / (la * la * 0.3) * (1.0 if layer < 2 else 0.7))
            for _ in range(nleaf):
                rr = sr * math.sqrt(rng.uniform(0, 1))
                aa = rng.uniform(0, TAU)
                px, py = sx + rr * math.cos(aa), sy + rr * math.sin(aa)
                lit = (0.55, 0.78, 1.0)[layer] * (1 + 0.3 * (sy - py) / sr + 0.12 * (px - sx) / sr) * rng.uniform(0.78, 1.15)
                col = tuple(int(min(255, max(0, v * lit))) for v in base) + (255,)
                L = rng.uniform(*Lr)
                W = L * rng.uniform(0.45, 0.6)
                bb = rng.uniform(0, TAU)
                ca, sa = math.cos(bb), math.sin(bb)
                pts = [(px + L * (j / 9) * ca - W / 2 * math.sin(math.pi * j / 9) * sa, py + L * (j / 9) * sa + W / 2 * math.sin(math.pi * j / 9) * ca)
                       for j in range(10)]
                pts += [(px + L * (j / 9) * ca + W / 2 * math.sin(math.pi * j / 9) * sa, py + L * (j / 9) * sa - W / 2 * math.sin(math.pi * j / 9) * ca)
                        for j in range(9, -1, -1)]
                dr.polygon(pts, fill=col)
    im = im.resize((512, 512), Image.LANCZOS)
    arr = np.array(im).astype(np.float32)
    a = arr[..., 3:4] / 255.0
    rgb = np.where(a > 0.05, arr[..., :3] / np.maximum(a, 0.05), 0)
    mean = rgb[a[..., 0] > 0.5].mean(0)
    rgb = np.where(a > 0.05, rgb, mean)
    alpha = np.where(a[..., 0] > 0.45, 255, 0)
    Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha]).astype(np.uint8), "RGBA").save(out, optimize=True)
    return out


def gen_frond_png():
    """棕櫚羽狀葉貼圖（RGBA）：u 沿葉軸（可橫向無縫重複）、v 由葉軸（下緣）到葉緣（上緣）；斜向細長小葉"""
    import numpy as np
    from PIL import Image, ImageDraw

    out = os.path.join(GEN, "frond.png")
    if os.path.exists(out):
        return out
    os.makedirs(GEN, exist_ok=True)
    W, H = 512, 256
    rng = np.random.default_rng(3)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    pal = [(96, 124, 48), (110, 138, 54), (84, 110, 42), (122, 148, 60)]
    n = 14
    for k in range(n):
        x0 = W * (k + rng.uniform(-0.15, 0.15)) / n
        c = pal[rng.integers(len(pal))]
        L = rng.uniform(0.85, 1.0)
        for off in (-W, 0, W):
            pts = []
            for j in range(9):
                t = j / 8
                x = x0 + off + 70 * t + 12 * t * t
                y = H - 4 - (H - 10) * t * L
                pts.append((x, y))
            for j in range(8, -1, -1):
                t = j / 8
                wdt = 9 * math.sin(math.pi * min(1, t * 1.1 + 0.05))
                pts.append((pts[j][0] + wdt, pts[j][1] + wdt * 0.3))
            dr.polygon(pts, fill=c + (255,))
    dr.rectangle([0, H - 6, W, H], fill=(124, 120, 72, 255))
    arr = np.array(im)
    rgb = arr[..., :3].astype(np.float32)
    a = arr[..., 3]
    mean = rgb[a > 128].mean(0)
    rgb[a < 128] = mean
    Image.fromarray(np.dstack([rgb.astype(np.uint8), np.where(a > 128, 255, 0).astype(np.uint8)]), "RGBA").save(out, optimize=True)
    return out


class CardBuilder(Builder):
    """Builder 擴充：透明葉簇卡片材質（alpha mask，UV 0–1）"""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.cards = set()

    def alpha_mat(self, name, png, rough=0.8):
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

    def ptex(self, name, tex_id, tile, tint=None, gain=1.0, rough=0.85, normal=0.0, dsize=1024, nsize=512):
        """PBR 貼圖（可縮小的漫反射、512 法線、固定粗糙度）以控制 GLB 大小"""
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
        if normal > 0:
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

    def _uv(self):
        super()._uv()
        uv = self.bm.loops.layers.uv.verify()
        for f in self.bm.faces:
            if f.material_index in self.cards and len(f.verts) == 4:
                for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                    l[uv].uv = c


def leaf_card(b, mi, c, nrm, size, spin):
    n = Vector(nrm).normalized()
    a = n.orthogonal().normalized()
    bb = n.cross(a)
    ca, sa = math.cos(spin), math.sin(spin)
    u = (a * ca + bb * sa) * size / 2
    v = (bb * ca - a * sa) * size / 2
    c = Vector(c)
    vs = [b.bm.verts.new(c - u - v), b.bm.verts.new(c + u - v), b.bm.verts.new(c + u + v), b.bm.verts.new(c - u + v)]
    mk_face(b, vs, mi)


def crown(b, cx, cy, cz, rx, rz, mats, core, csize, density=1.0):
    """樹冠團塊：深色核心＋分布在橢球表層、大致朝外的葉簇卡片"""
    rng = b.rng
    leaf_blob(b, core, (cx, cy, cz), rx * 0.8, rx * 0.8, rz * 0.78, lump=0.35, subdiv=1)
    area = 4 * math.pi * ((2 * rx * rx + rz * rz) / 3)
    n = int(min(420, density * 2.4 * area / (csize * csize)))
    for _ in range(n):
        d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1) * 0.9 + 0.25)).normalized()
        rr = rng.uniform(0.8, 1.04)
        p = (cx + d.x * rx * rr, cy + d.y * rx * rr, cz + d.z * rz * rr)
        nrm = (d + Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), rng.uniform(0.0, 0.35)))).normalized()
        mi = mats[0] if (d.z > 0.1 or rng.random() < 0.3) else mats[-1]
        leaf_card(b, mi, p, nrm, csize * rng.uniform(0.8, 1.2), rng.uniform(0, TAU))


def card_tree(b, x, y, h, mats, core, trunk, R_=None, z=0.0, cs=1.6, nblob=None):
    """闊葉樹：樹幹＋分枝＋ 5–8 個葉簇團塊（下緣低垂、外輪廓破碎）"""
    rng = b.rng
    R_ = R_ or h * rng.uniform(0.32, 0.4)
    cz = z + h - R_ * 0.95
    rz = min(R_ * 0.95, (cz - z) * 0.95 + R_ * 0.3)
    b.cyl(trunk, max(0.14, h * 0.028), max(0.08, h * 0.016), (cz - z) * 0.95, (x, y, z), seg=6)
    for _ in range(3):
        th = rng.uniform(0, TAU)
        b.cyl(trunk, h * 0.013, h * 0.006, R_ * 0.75, (x, y, z + (cz - z) * 0.6), seg=4, rot=(math.cos(th) * 0.8, math.sin(th) * 0.8, 0))
    n = nblob or rng.randint(5, 8)
    for _ in range(n):
        a = rng.uniform(0, TAU)
        rr = R_ * math.sqrt(rng.uniform(0.0, 1)) * 0.6
        dz = rng.uniform(-0.45, 0.45) * rz
        br = R_ * rng.uniform(0.42, 0.6)
        crown(b, x + rr * math.cos(a), y + rr * math.sin(a), cz + dz, br, br * 0.85, mats, core, min(cs, br * 0.9))


# ====================================================================== 共用造型
def mk_face(b, vs, mi, smooth=False):
    f = b.bm.faces.new(vs)
    f.material_index = mi
    f.smooth = smooth
    return f


def dome(b, mi, R, rise, base, seg=64, ribs=0, rib_amp=0.006, n=10, power=1.0):
    """圓頂（rise 可小於 R 做成扁圓頂）；ribs>0 時加上鉛板接縫稜線"""
    x, y, z = base
    prof = []
    for i in range(n + 1):
        a = (i / n) * math.pi / 2
        prof.append((R * math.cos(a) ** power, rise * math.sin(a)))
    prof[-1] = (0.0, rise)
    radial = (lambda t: 1 + rib_amp * max(0.0, math.cos(t * ribs)) ** 8) if ribs else None
    return b.lathe(mi, prof, (x, y, z), seg=seg, smooth=True, radial=radial)


def half_dome(b, mi, R, rise, center, facing, seg=24, n=8, ribs=0, flat_mi=None):
    """半圓頂：facing 為開口（平面）所朝方向，弧面朝 facing+π 凸出"""
    cx, cy, cz = center
    rings = []
    for i in range(n + 1):
        a = (math.pi / 2) * i / n
        r = R * math.cos(a)
        zz = cz + rise * math.sin(a)
        ring = []
        for j in range(seg + 1):
            t = facing + math.pi / 2 + math.pi * j / seg
            rr = r * (1 + (0.007 * max(0.0, math.cos((t - facing) * ribs)) ** 8 if ribs else 0))
            ring.append(b.bm.verts.new((cx + rr * math.cos(t), cy + rr * math.sin(t), zz)))
        rings.append(ring)
    for a_, c_ in zip(rings, rings[1:]):
        for j in range(seg):
            mk_face(b, [a_[j], a_[j + 1], c_[j + 1], c_[j]], mi, True)
    pts = [rings[i][0] for i in range(n + 1)] + [rings[i][-1] for i in range(n, -1, -1)]
    uniq = []
    for p in pts:
        if all((p.co - q.co).length > 1e-4 for q in uniq):
            uniq.append(p)
    try:
        mk_face(b, uniq, mi if flat_mi is None else flat_mi)
    except ValueError:
        pass
    mk_face(b, list(reversed(rings[0])), mi if flat_mi is None else flat_mi)


def pointed_pts(w, h, seg=5):
    """雙心尖拱窗輪廓（底寬 w、總高 h）；與 lib.arch_points(kind="pointed") 同曲率"""
    r = w / 2
    R = w * 0.8
    a_top = math.acos((R - r) / R)
    s = h - R * math.sin(a_top)
    right = [(r - R + R * math.cos(a_top * i / seg), s + R * math.sin(a_top * i / seg)) for i in range(1, seg)]
    left = [(-x, y) for x, y in reversed(right)]
    return [(-r, 0), (r, 0), (r, s)] + right + [(0.0, h)] + left + [(-r, s)]


def arch_window(b, win, frame, w, h, M, depth=0.1, frame_w=0.35, frame_d=0.45, kind="pointed"):
    """深色窗面＋淺色石框輪廓（窗形石板襯在窗後、略大一圈）；M：局部 X 水平、Z 垂直、-Y 朝外"""
    def shape(ww, hh):
        if kind == "pointed":
            return pointed_pts(ww, hh, seg=5)
        r = ww / 2
        return [(-r, 0), (r, 0), (r, hh - r)] + [(r * math.cos(math.pi * i / 6), hh - r + r * math.sin(math.pi * i / 6)) for i in range(1, 6)] + [(-r, hh - r)]
    if frame is not None and frame_w > 0:
        b.profile_wall(frame, [(x, y - frame_w * 0.4) for x, y in shape(w + 2 * frame_w, h + frame_w * 1.4)], frame_d * 0.6, M)
        b.profile_wall(win, shape(w, h), frame_d * 0.6 + 0.08, M)
    else:
        b.profile_wall(win, shape(w, h), depth, M)


def oct_prism(b, mi, R, z0, z1, cx, cy, rot=math.pi / 8):
    pts = [(cx + R * math.cos(rot + TAU * k / 8), cy + R * math.sin(rot + TAU * k / 8)) for k in range(8)]
    b.prism(mi, pts, z0, z1 - z0)


def finial(b, gold, x, y, z, s=1.0):
    b.lathe(gold, [(0.1 * s, z), (0.28 * s, z + 0.45 * s), (0.1 * s, z + 0.85 * s), (0.24 * s, z + 1.3 * s), (0.07 * s, z + 1.75 * s),
                   (0.2 * s, z + 2.15 * s), (0.0, z + 2.9 * s)], (x, y, 0), seg=8, smooth=True)


def minaret(b, x, y, H, R, stone, cap, gold, balcony, balconies, base_h, base_w, seg=16, cap_h=13.0, flutes=16):
    """鄂圖曼鉛筆形宣禮塔：方形底座→多角塔身（帶溝槽）→鐘乳石托座陽台→細上段→鉛錐頂＋金色頂飾"""
    b.box_base(stone, (base_w, base_w, base_h), (x, y, 0))
    b.box_base(stone, (base_w + 0.4, base_w + 0.4, 0.5), (x, y, base_h - 0.5))
    b.lathe(stone, [(R * 1.45, base_h), (R * 1.25, base_h + 0.8), (R * 1.08, base_h + 1.6)], (x, y, 0), seg=seg, smooth=False)
    z0 = base_h + 1.6
    z_top = H - cap_h
    flu = (lambda t: 1 + 0.04 * abs(math.cos(t * flutes / 2)))
    zs = [z0] + [z0 + (z_top - z0) * f for f in balconies] + [z_top]
    r_here = R
    for i, (za, zb) in enumerate(zip(zs, zs[1:])):
        r_here = R * (1 - 0.07 * i)
        b.lathe(stone, [(r_here, za), (r_here * 0.985, zb)], (x, y, 0), seg=seg, smooth=False, radial=flu)
        if i < len(zs) - 2:
            # 陽台：鐘乳石托座（逐層外擴）＋實心欄板
            prof = [(r_here * 0.99, zb - 2.6)]
            for k in range(3):
                t = (k + 1) / 3
                prof += [(r_here * (1.0 + 0.5 * t ** 0.8), zb - 2.6 + 2.4 * t - 0.45), (r_here * (1.0 + 0.5 * t ** 0.8), zb - 2.6 + 2.4 * t)]
            prof += [(r_here * 1.55, zb - 0.1), (r_here * 1.55, zb + 1.05), (r_here * 1.47, zb + 1.05), (r_here * 1.47, zb + 0.15), (0, zb + 0.15)]
            b.lathe(balcony, prof, (x, y, 0), seg=seg * 2, smooth=False)
    r_top = r_here * 0.985
    b.lathe(stone, [(r_top * 1.1, z_top - 0.1), (r_top * 1.14, z_top + 0.45), (r_top * 1.03, z_top + 0.55)], (x, y, 0), seg=seg, smooth=False)
    b.lathe(cap, [(r_top * 1.05, z_top + 0.55), (r_top * 0.8, z_top + 0.55 + cap_h * 0.3), (r_top * 0.42, z_top + 0.55 + cap_h * 0.72),
                  (0.0, z_top + 0.55 + cap_h * 0.98)], (x, y, 0), seg=seg, smooth=True)
    finial(b, gold, x, y, z_top + 0.55 + cap_h * 0.93, 1.1)


# ---------------------------------------------------------------------- 植栽
def leaf_blob(b, mi, loc, rx, ry, rz, lump=0.35, subdiv=1):
    off = Vector((b.rng.uniform(0, 99), b.rng.uniform(0, 99), b.rng.uniform(0, 99)))
    r = bmesh.ops.create_icosphere(b.bm, subdivisions=subdiv, radius=1.0, matrix=Matrix.Identity(4))
    for v in r["verts"]:
        p = v.co.copy()
        n_ = noise.noise(p * 1.5 + off) * 0.5 + noise.noise(p * 3.4 + off) * 0.32 + noise.noise(p * 7.0 + off) * 0.22
        k = 1 + lump * n_
        if p.z < -0.2:
            k *= 0.8 + 0.2 * (1 + p.z)
        v.co = Vector((loc[0] + p.x * rx * k, loc[1] + p.y * ry * k, loc[2] + p.z * rz * k))
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mi
        f.smooth = True


def plane_tree(b, x, y, h, leaves, trunk, spread=1.0, sub=2):
    """闊葉樹（懸鈴木／椴樹）：主幹分叉＋數個大葉團（多層雜訊起伏、外輪廓破碎），上亮下暗"""
    rng = b.rng
    R = h * rng.uniform(0.3, 0.38) * spread
    Rz = h * rng.uniform(0.3, 0.36)
    cz = h - Rz
    b.cyl(trunk, h * 0.028, h * 0.02, cz * 0.9, (x, y, 0), seg=6)
    for _ in range(4):
        th = rng.uniform(0, TAU)
        b.cyl(trunk, h * 0.014, h * 0.006, R * 0.8, (x, y, cz * 0.6), seg=4, rot=(math.cos(th) * 0.75, math.sin(th) * 0.75, 0))
    leaf_blob(b, leaves[2], (x, y, cz - Rz * 0.1), R * 0.85, R * 0.85, Rz * 0.75, lump=0.35, subdiv=sub)
    for _ in range(rng.randint(6, 9)):
        th = rng.uniform(0, TAU)
        ph = rng.uniform(-0.3, 1.2)
        px, py, pz = math.cos(th) * math.cos(ph), math.sin(th) * math.cos(ph), math.sin(ph)
        br = R * rng.uniform(0.38, 0.55)
        mi = leaves[0] if pz > 0.45 else (leaves[2] if pz < 0.0 else leaves[1])
        leaf_blob(b, mi, (x + px * R * 0.6, y + py * R * 0.6, cz + pz * Rz * 0.6), br, br * rng.uniform(0.8, 1.2), br * 0.8, lump=0.6,
                  subdiv=sub)


def cypress(b, x, y, h, mi, trunk):
    r = h * b.rng.uniform(0.09, 0.12)
    b.cyl(trunk, r * 0.25, r * 0.2, h * 0.12, (x, y, 0), seg=5)
    off = b.rng.uniform(0, 9)
    b.lathe(mi, [(0, h * 0.05), (r * 0.8, h * 0.1), (r, h * 0.3), (r * 0.85, h * 0.6), (r * 0.45, h * 0.85), (0, h)],
            (x, y, 0), seg=10, smooth=True, radial=lambda t: 1 + 0.12 * math.sin(t * 5 + off) + 0.06 * math.sin(t * 11 + off))


def palm(b, x, y, h, frond, frond_d, trunk):
    """加那利海棗：粗幹（葉痕環紋）＋球狀樹冠，三層羽狀葉（中肋 V 形折、葉尖下垂、葉緣鋸齒）"""
    rng = b.rng
    bm = b.bm
    n_ring = 10
    for k in range(n_ring):
        z0 = h * k / n_ring
        r0 = 0.62 - 0.12 * k / n_ring
        b.lathe(trunk, [(r0 * 0.97, z0), (r0 * 1.03, z0 + h / n_ring * 0.6), (r0 * 0.97, z0 + h / n_ring)], (x, y, 0), seg=10, smooth=True)
    b.ico(trunk, 1.0, (x, y, h + 0.2), subdiv=1)
    for tier, (n, lift, dr) in enumerate(((9, 1.8, 0.2), (13, 0.9, 0.5), (15, 0.0, 0.95), (12, -0.6, 1.3))):
        for k in range(n):
            a = TAU * (k + 0.5 * tier) / n + rng.uniform(-0.12, 0.12)
            droop = dr + rng.uniform(-0.1, 0.15)
            L = rng.uniform(4.8, 6.2)
            mid, lft, rgt = [], [], []
            ns = 10
            for i in range(ns):
                u = i / (ns - 1)
                r = L * u * math.cos(droop * u * 0.8)
                z = h + 0.4 + lift * (1 - u) + 1.2 * math.sin(math.pi * u * 0.5) * (1 - droop * 0.7) - droop * 3.0 * u * u
                w = 0.8 * math.sin(math.pi * min(1.0, u * 1.05 + 0.04)) * (0.75 if i % 2 else 1.0)
                cx, cy = x + math.cos(a) * r, y + math.sin(a) * r
                mid.append(bm.verts.new((cx, cy, z)))
                lft.append(bm.verts.new((cx - math.sin(a) * w, cy + math.cos(a) * w, z - 0.4 * w)))
                rgt.append(bm.verts.new((cx + math.sin(a) * w, cy - math.cos(a) * w, z - 0.4 * w)))
            mi = frond if tier < 2 else frond_d
            for i in range(ns - 1):
                for side in (lft, rgt):
                    mk_face(b, [mid[i], mid[i + 1], side[i + 1], side[i]], mi, True)


# ====================================================================== 主體
def blue_mosque(path):
    _gen_textures()
    b = CardBuilder("BlueMosque", seed=43)
    stone = b.ptex("stone", "white_sandstone_blocks_02", tile=3.0, tint="#928f87", rough=0.85, normal=0.7)
    stone_w = b.color("stone_w", "#a6a39a", rough=0.8)
    stone_d = b.color("stone_d", "#85827a", rough=0.85)
    wall_old = b.ptex("wall_old", "stone_wall_04", tile=4.0, tint="#9a958a", rough=0.9, normal=0.8, dsize=512)
    lead = b.color("lead", "#6c757c", rough=0.62, metal=0.08)
    lead_d = b.color("lead_d", "#60686e", rough=0.65, metal=0.08)
    win = b.color("window", "#2b2f36", rough=0.3)
    gold = b.color("gold", "#cda24a", rough=0.3, metal=0.9)
    pave = b.ptex("pave", "square_cobblestone", tile=3.0, tint="#a39d92", rough=0.9, normal=0.5, dsize=512)
    court = b.color("court", "#cdc9c0", rough=0.6)
    asphalt = b.ptex("asphalt", "asphalt_02", tile=6.0, tint="#6f6d6a", rough=0.9, dsize=512)
    grass = b.ptex("grass", "grass_ground", tile=6.0, tint="#6a8a3e", gain=0.95, rough=0.95, dsize=512)
    soil = b.color("soil", "#6b5a45", rough=0.95)
    lf_light = b.alpha_mat("leaf_light", gen_leaf_png("light"))
    lf_broad = b.alpha_mat("leaf_broad", gen_leaf_png("broad"))
    core = b.color("leaf_core", "#2e4420", rough=0.9)
    mats_a = (lf_light, lf_broad)
    mats_b = (lf_broad, lf_broad)
    cyp = b.color("cypress", "#33482b", rough=0.9)
    trunk = b.color("trunk", "#6a5848", rough=0.9)
    frond = b.alpha_mat("palm_frond", gen_frond_png(), rough=0.75)
    frond_d = frond
    palm_tr = b.color("palm_trunk", "#8b7457", rough=0.95)
    lamp = b.color("lamp", "#2d2d2d", rough=0.5, metal=0.6)

    T = lambda x, y, z=0.0: Matrix.Translation((x, y, z))  # noqa: E731
    Rz = lambda a: Matrix.Rotation(a, 4, "Z")  # noqa: E731

    def facing(nx, ny):
        """牆面外法線 (nx, ny) → 局部座標（-Y 朝外）旋轉角"""
        return math.atan2(ny, nx) + math.pi / 2

    def wall_windows(p0, p1, normal, z, n, w, h, kind="pointed", frame=stone_w, fw=0.3, skip=()):
        p0, p1 = Vector(p0), Vector(p1)
        ang = facing(*normal)
        for k in range(n):
            if k in skip:
                continue
            p = p0 + (p1 - p0) * ((k + 0.5) / n)
            M = T(p.x + normal[0] * 0.02, p.y + normal[1] * 0.02, z) @ Rz(ang)
            arch_window(b, win, frame, w, h, M, depth=0.14, frame_w=fw, frame_d=0.4, kind=kind)

    # ---------------------------------------------------------------- 地面
    b.ground_disc(grass, 175, soil, depth=3, rings=18, seg=96)
    # 外院（院牆內）石板鋪面
    PX0, PX1, PY0, PY1 = -52.0, 52.0, -48.0, 112.0
    b.box_base(pave, (PX1 - PX0, PY1 - PY0, 0.12), ((PX0 + PX1) / 2, (PY0 + PY1) / 2, 0))
    # 公園步道與廣場（院牆外）
    b.box_base(pave, (20.0, PY1 - PY0 + 40, 0.1), (PX1 + 12, (PY0 + PY1) / 2, 0))
    b.box_base(asphalt, (12.0, 340, 0.08), (PX0 - 10, 30, 0))
    for (cx, cy, w, d) in ((120, 30, 7, 230), (95, -20, 60, 6), (95, 75, 60, 6), (150, 30, 6, 200)):
        b.box_base(pave, (w, d, 0.1), (cx, cy, 0))
    # ---------------------------------------------------------------- 外院院牆（帶方窗的低牆）
    for (x0, y0, x1, y1, nrm) in ((PX1, PY0, PX1, PY1, (1, 0)), (PX0, PY0, PX0, PY1, (-1, 0)), (PX0, PY0, PX1, PY0, (0, -1)),
                                  (PX0, PY1, PX1, PY1, (0, 1))):
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        b.box_base(wall_old, (L + 1.4, 1.4, 4.2), (cx, cy, 0), rot=(0, 0, ang))
        b.box_base(stone_w, (L + 1.8, 1.8, 0.35), (cx, cy, 4.2), rot=(0, 0, ang))
        n = int(L / 5.5)
        for k in range(n):
            t = (k + 0.5) / n
            px, py = x0 + (x1 - x0) * t + nrm[0] * 0.72, y0 + (y1 - y0) * t + nrm[1] * 0.72
            if abs(py - 30) < 6 and nrm[1] == 0 and nrm[0] > 0:
                continue
            b.box_base(win, (1.4, 0.12, 1.8), (px, py, 1.3), rot=(0, 0, ang))
            b.box_base(stone_w, (1.9, 0.2, 0.22), (px, py, 3.1), rot=(0, 0, ang))
    # 東北側院門
    b.box_base(stone, (2.4, 9.0, 8.0), (PX1, 30, 0))
    arch_window(b, win, stone_w, 4.0, 6.4, T(PX1 + 1.22, 30, 0) @ Rz(facing(1, 0)), depth=0.1, frame_w=0.5)

    # ---------------------------------------------------------------- 禮拜殿殿身
    HX = 28.0             # 殿身半寬（56 × 56）
    H_W = 15.5            # 外牆高
    b.box_base(stone, (2 * HX, 2 * HX, H_W), (0, 0, 0))
    b.box_base(stone_w, (2 * HX + 1.0, 2 * HX + 1.0, 0.7), (0, 0, H_W - 0.2))     # 簷口
    b.box_base(lead_d, (2 * HX - 1.0, 2 * HX - 1.0, 0.5), (0, 0, H_W + 0.5))
    b.box_base(stone, (2 * HX + 0.3, 2 * HX + 0.3, 0.5), (0, 0, 0))                # 勒腳
    # 四面外牆：扶壁分出五開間，每開間三層拱窗
    for nrm in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = nrm
        tx, ty = -ny, nx
        for k in range(6):
            u = -HX + 2 * HX * k / 5
            px, py = nx * (HX + 0.5) + tx * u, ny * (HX + 0.5) + ty * u
            b.box_base(stone_d, (1.0 + abs(tx) * 1.4, 1.0 + abs(ty) * 1.4, H_W - 0.2), (px, py, 0))
        p0 = (nx * HX - tx * (HX - 1.5), ny * HX - ty * (HX - 1.5))
        p1 = (nx * HX + tx * (HX - 1.5), ny * HX + ty * (HX - 1.5))
        if nrm == (0, 1):
            continue   # 前庭側另做
        wall_windows(p0, p1, nrm, 1.4, 10, 1.5, 3.4, kind="round")
        wall_windows(p0, p1, nrm, 6.4, 10, 1.4, 3.2)
        wall_windows(p0, p1, nrm, 11.0, 10, 1.2, 2.8)
        # 層間石帶
        b.box_base(stone_w, (abs(tx) * 2 * HX + 0.6, abs(ty) * 2 * HX + 0.6, 0.35), (nx * HX, ny * HX, 5.6))
        b.box_base(stone_w, (abs(tx) * 2 * HX + 0.6, abs(ty) * 2 * HX + 0.6, 0.3), (nx * HX, ny * HX, 10.3))
    # 兩側（±X）雙層拱廊（東北側在參考照前方）
    for sx in (-1, 1):
        x_out = sx * (HX + 5.5)
        y0, y1 = -HX + 4, HX - 4
        n = 9
        bw = (y1 - y0) / n
        for k in range(n):
            y = y0 + bw * (k + 0.5)
            for zb, hh, op in ((0.0, 5.8, 0.66), (5.8, 5.2, 0.6)):
                M = T(x_out, y, zb) @ Rz(facing(sx, 0))
                b.arch_frame(stone, bw, hh, hh * 0.55, bw * op, 0.9, M, kind="pointed")
            # 拱內深色（迴廊陰影）
            b.box_base(win, (0.2, bw * 0.8, 10.0), (sx * (HX + 0.2), y, 0.5))
        b.box_base(stone_w, (1.2, y1 - y0 + 0.4, 0.5), (x_out, 0, 5.6))
        b.box_base(stone_w, (6.4, y1 - y0 + 1.2, 0.5), (sx * (HX + 3.0), 0, 11.0))
        # 單坡鉛屋頂
        Mr = T(sx * (HX + 3.0), 0, 11.5)
        w2 = 3.2
        pts = [(-w2, 0), (w2, 0), (w2, 0.3), (-w2, 1.6)] if sx > 0 else [(-w2, 0), (w2, 0), (w2, 1.6), (-w2, 0.3)]
        b.profile_wall(lead, pts, y1 - y0 + 1.2, Mr)
        for yy in (y0, y1):   # 端牆
            b.box_base(stone, (6.0, 0.9, 11.0), (sx * (HX + 3.0), yy + (0.45 if yy == y0 else -0.45), 0))

    # ---------------------------------------------------------------- 中央方形、半圓頂、小半圓頂、角圓頂
    A = 11.75             # 主圓頂半徑（直徑 23.5 m）
    Z_HD = 22.4           # 半圓頂起拱
    HD_RISE = 8.2
    Z_DR = 31.0           # 鼓座底
    b.box_base(stone_d, (2 * A + 1.0, 2 * A + 1.0, Z_DR + 0.4 - H_W), (0, 0, H_W))
    for ang_d in (0, 90, 180, 270):
        a = math.radians(ang_d)
        c, s = round(math.cos(a)), round(math.sin(a))
        cx, cy = c * A, s * A
        t0 = a - math.pi / 2
        # 半圓頂下的半圓鼓牆（一圈窗）
        b.ering(stone, (A - 0.9, A - 0.9), (A, A), H_W, Z_HD + 0.3, seg=48, t0=t0, t1=t0 + math.pi, center=(cx, cy))
        b.ering(stone_w, (A - 0.1, A - 0.1), (A + 0.25, A + 0.25), Z_HD - 0.1, Z_HD + 0.3, seg=48, t0=t0, t1=t0 + math.pi, center=(cx, cy))
        for k in range(9):
            t = t0 + math.pi * (k + 0.5) / 9
            M = T(cx + math.cos(t) * A, cy + math.sin(t) * A, Z_HD - 2.95) @ Rz(t + math.pi / 2)
            arch_window(b, win, stone_w, 1.0, 2.4, M, depth=0.12, frame_w=0.22, frame_d=0.3, kind="round")
        # 半圓頂邊緣的扶壁小墩
        for k in range(10):
            t = t0 + math.pi * k / 9
            px, py = cx + math.cos(t) * (A + 0.25), cy + math.sin(t) * (A + 0.25)
            b.box_base(stone_d, (0.7, 0.7, Z_HD + 0.2 - H_W), (px, py, H_W), rot=(0, 0, t))
        half_dome(b, lead, A + 0.25, HD_RISE, (cx, cy, Z_HD + 0.3), facing=a + math.pi, seg=40, n=10, ribs=18, flat_mi=stone_d)
        # 三座小半圓頂（exedra）：位於半圓頂外緣
        for k, dt in enumerate((-0.82, 0.0, 0.82)):
            t = a + dt
            R_e = 4.6 if k == 1 else 4.0
            ex, ey = cx + math.cos(t) * (A + 0.2), cy + math.sin(t) * (A + 0.2)
            te0 = t - math.pi / 2
            b.ering(stone, (R_e - 0.5, R_e - 0.5), (R_e + 0.3, R_e + 0.3), H_W, H_W + 2.4, seg=24, t0=te0, t1=te0 + math.pi, center=(ex, ey))
            for j in range(5):
                tj = te0 + math.pi * (j + 0.5) / 5
                M = T(ex + math.cos(tj) * (R_e + 0.3), ey + math.sin(tj) * (R_e + 0.3), H_W + 0.45) @ Rz(tj + math.pi / 2)
                arch_window(b, win, None, 0.75, 1.55, M, depth=0.1, kind="round")
            half_dome(b, lead, R_e + 0.45, R_e * 0.82, (ex, ey, H_W + 2.4), facing=t + math.pi, seg=20, n=7, ribs=10, flat_mi=stone_d)
    # 四角小圓頂（殿身四角）
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * 20.8, sy * 20.8
            oct_prism(b, stone, 5.6, H_W, H_W + 3.3, cx, cy)
            oct_prism(b, stone_w, 5.9, H_W + 3.3, H_W + 3.7, cx, cy)
            for k in range(8):
                t = TAU * k / 8
                rr = 5.6 * math.cos(math.pi / 8)
                M = T(cx + math.cos(t) * rr, cy + math.sin(t) * rr, H_W + 0.7) @ Rz(t + math.pi / 2)
                arch_window(b, win, None, 0.9, 1.9, M, depth=0.1, kind="round")
            dome(b, lead, 5.5, 4.4, (cx, cy, H_W + 3.7), seg=32, ribs=14, n=8)
            finial(b, gold, cx, cy, H_W + 7.9, 0.8)
    # 半圓頂與角圓頂之間的小八角塔
    for sx in (-1, 1):
        for sy in (-1, 1):
            for (cx, cy) in ((sx * 13.6, sy * 25.6), (sx * 25.6, sy * 13.6)):
                oct_prism(b, stone, 1.5, H_W, H_W + 6.0, cx, cy)
                oct_prism(b, stone_w, 1.75, H_W + 6.0, H_W + 6.4, cx, cy)
                dome(b, lead, 1.5, 1.6, (cx, cy, H_W + 6.4), seg=12, n=5)
                finial(b, gold, cx, cy, H_W + 7.8, 0.5)
    # 重力塔：中央方形四角的八角形塔
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * (A + 0.6), sy * (A + 0.6)
            oct_prism(b, stone, 2.7, H_W, Z_DR - 1.2, cx, cy)
            oct_prism(b, stone_w, 3.0, Z_DR - 1.2, Z_DR - 0.8, cx, cy)
            oct_prism(b, stone, 2.3, Z_DR - 0.8, Z_DR + 0.2, cx, cy)
            for k in range(8):
                t = TAU * k / 8 + math.pi / 8 * 0
                rr = 2.7 * math.cos(math.pi / 8)
                M = T(cx + math.cos(t) * rr, cy + math.sin(t) * rr, Z_DR - 4.8) @ Rz(t + math.pi / 2)
                if (math.cos(t) * sx < -0.3) or (math.sin(t) * sy < -0.3):
                    continue
                arch_window(b, win, None, 0.75, 2.4, M, depth=0.1, kind="round")
            dome(b, lead, 2.3, 2.2, (cx, cy, Z_DR + 0.2), seg=16, n=6, ribs=8)
            finial(b, gold, cx, cy, Z_DR + 2.2, 0.8)

    # 鼓座（28 窗、扶壁）與主圓頂
    H_DR = 4.6
    RD = A + 0.6
    b.lathe(stone, [(RD, Z_DR), (RD, Z_DR + H_DR)], (0, 0, 0), seg=56, smooth=False)
    for k in range(28):
        t = TAU * (k + 0.5) / 28
        M = T(math.cos(t) * RD, math.sin(t) * RD, Z_DR + 0.9) @ Rz(t + math.pi / 2)
        arch_window(b, win, None, 1.1, 2.9, M, depth=0.12, kind="round")
        t2 = TAU * k / 28
        b.frustum(stone_w, (1.3, 0.9), (0.7, 0.8), H_DR - 0.2, (math.cos(t2) * (RD + 0.45), math.sin(t2) * (RD + 0.45), Z_DR), rot_z=t2)
    b.lathe(stone_w, [(RD + 1.0, Z_DR + H_DR), (RD + 1.2, Z_DR + H_DR + 0.45), (RD + 0.2, Z_DR + H_DR + 0.45)], (0, 0, 0), seg=56, smooth=False)
    Z_DM = Z_DR + H_DR + 0.45
    dome(b, lead, RD + 0.9, 43.4 - Z_DM, (0, 0, Z_DM), seg=112, ribs=28, rib_amp=0.008, n=14, power=0.85)
    b.lathe(gold, [(0.0, 43.2), (0.6, 43.4), (0.75, 44.0), (0.3, 44.6), (0.6, 45.4), (0.18, 46.2), (0.42, 46.9), (0.1, 47.8), (0.0, 49.2)],
            (0, 0, 0), seg=12)

    # ---------------------------------------------------------------- 前庭（+Y）：外牆、拱廊、小圓頂、淨身亭
    CY0, CY1 = HX, HX + 62.0
    CW = HX
    b.box_base(court, (2 * CW, CY1 - CY0, 0.45), (0, (CY0 + CY1) / 2, 0))
    # 前庭與殿身之間的立面（殿身北牆）：大門＋拱窗
    p0, p1 = (-HX + 1.5, HX), (HX - 1.5, HX)
    wall_windows(p0, p1, (0, 1), 11.0, 10, 1.2, 2.8)
    # 前庭外牆（帶窗）
    for (cx, cy, w, d, nrm) in ((0, CY1 - 0.9, 2 * CW, 1.8, (0, 1)), (-CW + 0.9, (CY0 + CY1) / 2, 1.8, CY1 - CY0, (-1, 0)),
                                (CW - 0.9, (CY0 + CY1) / 2, 1.8, CY1 - CY0, (1, 0))):
        b.box_base(stone, (w, d, 8.6), (cx, cy, 0))
        b.box_base(stone_w, (w + 0.6, d + 0.6, 0.5), (cx, cy, 8.4))
        if nrm[0] != 0:
            x = nrm[0] * CW
            wall_windows((x, CY0 + 3), (x, CY1 - 3), nrm, 1.6, 9, 1.4, 2.4, kind="round")
            wall_windows((x, CY0 + 3), (x, CY1 - 3), nrm, 5.2, 9, 1.0, 2.0)
            for k in range(10):   # 扶壁
                y = CY0 + 1 + (CY1 - CY0 - 2) * k / 9
                b.box_base(stone_d, (2.6, 1.0, 8.4), (x + nrm[0] * 0.3, y, 0))
        else:
            wall_windows((-CW + 3, CY1), (CW - 3, CY1), nrm, 1.6, 8, 1.4, 2.4, kind="round", skip=(3, 4))
    # 西北正門（高起的門樓＋小圓頂）
    b.box_base(stone, (11.0, 5.0, 14.5), (0, CY1, 0))
    b.box_base(stone_w, (11.6, 5.6, 0.6), (0, CY1, 14.3))
    arch_window(b, win, stone_w, 4.4, 8.6, T(0, CY1 + 2.52, 0.4) @ Rz(facing(0, 1)), depth=0.12, frame_w=0.6)
    dome(b, lead, 2.6, 2.2, (0, CY1, 14.9), seg=20, n=6)
    # 拱廊：內側一圈開間、每開間一座小圓頂
    bay = 6.2
    D = 6.4               # 拱廊進深
    cells = []
    nx_ = int(round(2 * CW / bay))
    bwx = 2 * CW / nx_
    for i in range(nx_):
        cells.append((-CW + bwx * (i + 0.5), CY1 - D / 2, bwx))
        cells.append((-CW + bwx * (i + 0.5), CY0 + D / 2, bwx))
    ny_ = int(round((CY1 - CY0 - 2 * D) / bay))
    bwy = (CY1 - CY0 - 2 * D) / ny_
    for j in range(ny_):
        y = CY0 + D + bwy * (j + 0.5)
        cells.append((-CW + D / 2, y, bwy))
        cells.append((CW - D / 2, y, bwy))
    for x, y, bw in cells:
        b.box_base(stone, (bw + 0.05, D, 1.3), (x, y, 7.3))
        b.lathe(stone, [(bw * 0.4, 8.6), (bw * 0.4, 9.3)], (x, y, 0), seg=16, smooth=False)
        dome(b, lead, bw * 0.43, bw * 0.34, (x, y, 9.3), seg=20, n=6, ribs=8)
        finial(b, gold, x, y, 9.3 + bw * 0.33, 0.45)
    # 拱廊內側立面（柱＋尖拱）
    ix0, ix1, iy0, iy1 = -CW + D, CW - D, CY0 + D, CY1 - D
    for (ax, ay, L, nrm) in ((ix0, (iy0 + iy1) / 2, iy1 - iy0, (1, 0)), (ix1, (iy0 + iy1) / 2, iy1 - iy0, (-1, 0)),
                             ((ix0 + ix1) / 2, iy1, ix1 - ix0, (0, -1)), ((ix0 + ix1) / 2, iy0, ix1 - ix0, (0, 1))):
        n = max(1, round(L / bay))
        for k in range(n):
            u = -L / 2 + L * (k + 0.5) / n
            ang = facing(*nrm)
            M = T(ax, ay, 0.45) @ Rz(ang) @ T(u, 0, 0)
            b.arch_frame(stone, L / n, 7.0, 3.8, L / n * 0.72, 0.9, M, kind="pointed")
        # 拱廊後的陰影面
        b.box_base(win, (abs(nrm[1]) * L + 0.2, abs(nrm[0]) * L + 0.2, 6.8), (ax - nrm[0] * (D - 1.2), ay - nrm[1] * (D - 1.2), 0.45))
    # 淨身亭（六角）
    fy = (CY0 + CY1) / 2
    for k in range(6):
        t = TAU * k / 6
        b.cyl(court, 0.35, 0.35, 4.6, (math.cos(t) * 3.4, fy + math.sin(t) * 3.4, 0.45), seg=8)
    b.lathe(stone_w, [(4.3, 5.0), (4.3, 5.8)], (0, fy, 0), seg=6, smooth=False)
    dome(b, lead, 4.0, 3.0, (0, fy, 5.8), seg=24, n=6)
    finial(b, gold, 0, fy, 8.7, 0.6)

    # ---------------------------------------------------------------- 六座宣禮塔
    for sx in (-1, 1):
        for y in (-HX - 2.0, HX + 2.0):
            minaret(b, sx * (HX + 2.0), y, 64.0, 1.32, stone, lead, gold, stone_w, balconies=(0.48, 0.66, 0.84), base_h=H_W + 1.5,
                    base_w=5.4, seg=16, cap_h=13.0)
        minaret(b, sx * (CW + 1.5), CY1 + 1.5, 60.0, 1.28, stone, lead, gold, stone_w, balconies=(0.58, 0.82), base_h=10.0,
                base_w=5.0, seg=16, cap_h=12.0)

    # ---------------------------------------------------------------- 植栽與街燈
    rng = b.rng

    def tree_ok(x, y):
        return not (PX0 - 3 < x < PX1 + 3 and PY0 - 3 < y < PY1 + 3)

    # 院內（殿身兩側）幾棵懸鈴木
    for x, y in ((44, -30), (44, 2), (44, 64), (44, 96), (-44, -20), (-44, 50), (30, -40), (-30, -42)):
        card_tree(b, x, y, rng.uniform(13, 16), mats_a, core, trunk)
    # 院牆外公園：依參考照畫面位置擺放前景樹與棕櫚（以相機視線換算：前方距離 D、畫面橫向 tan 值 s）
    (tx_, ty_, tz_), az_, el_, dist_, _ = CAMERA
    a_, e_ = math.radians(az_), math.radians(el_)
    cam = Vector((tx_ + math.sin(a_) * math.cos(e_) * dist_, ty_ - math.cos(a_) * math.cos(e_) * dist_, 0))
    fwd = Vector((-math.sin(a_), math.cos(a_), 0))
    rgt = Vector((fwd.y, -fwd.x, 0))

    def at(D, s_):
        p = cam + fwd * D + rgt * (s_ * D)
        return p.x, p.y

    for D, s_, h in ((116, -0.27, 11), (112, -0.15, 18), (104, -0.02, 17), (122, 0.04, 12), (114, 0.1, 13), (110, 0.18, 12),
                     (104, 0.26, 14), (96, 0.33, 12), (128, -0.33, 13), (134, 0.22, 11)):
        x, y = at(D, s_)
        card_tree(b, x, y, h, mats_a, core, trunk)
    for D, s_, h in ((62, -0.06, 9.5), (88, 0.14, 8.0), (96, -0.21, 8.5)):
        x, y = at(D, s_)
        palm(b, x, y, h, frond, frond_d, palm_tr)
    for x, y in ((62, -70), (-60, -60), (-62, 30), (-58, 100), (60, 130)):
        cypress(b, x, y, rng.uniform(13, 17), cyp, trunk)
    for x, y in b.scatter(30, 70, 170, min_dist=13, avoid=lambda x, y: (not tree_ok(x, y)) or (x > 60 and -60 < y < 110) or x > 150):
        card_tree(b, x, y, rng.uniform(12, 18), mats_b, core, trunk, cs=2.4, nblob=4)
    # 街燈
    for y in range(-40, 116, 16):
        b.cyl(lamp, 0.09, 0.07, 4.2, (PX1 + 4.0, y, 0), seg=6)
        b.ico(b.color("lamp_glass", "#e8e2cf", rough=0.3), 0.32, (PX1 + 4.0, y, 4.45), subdiv=1)

    b.export(path)
