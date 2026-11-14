"""himeji 姬路城（白鷺城）寫實模型（尺寸依實測資料，公尺）

- 大天守：石垣高 14.85 m、建物高 31.5 m；外觀 5 重（內部 6 階＋地下 1 階），1 階約 26 × 21 m，逐層收分
- 西小天守、乾小天守、東小天守位於大天守的西側、西北、北側，以 2 層的渡櫓連成「連立式天守」
- 屋頂：自寫網格，多段弧線（反り）屋面、四角上翹、軒先厚度、白漆喰軒裏；瓦片紋理沿屋面坡向
- 千鳥破風、唐破風、入母屋破風；白漆喰牆面上的格子窗
- 石垣：扇之勾配（下部外張、上部近乎垂直的弧形曲線）

座標先以地理方位建模（+Y 北、+X 東），最後整體旋轉 180°，讓南立面朝向預覽相機。
"""

import math
import os

import bmesh
import numpy as np
from mathutils import Matrix, Vector, noise

from lib import TAU, TEX, Builder

GEN_KAWARA = "_gen/kawara_v2"


# ---------------------------------------------------------------- 程式產生的瓦片貼圖
def _gen_kawara():
    """本瓦葺：丸瓦（凸）＋平瓦（凹）交替，丸瓦兩側有白漆喰目地。貼圖 2.4 m 一循環、每列 0.3 m"""
    out = os.path.join(TEX, GEN_KAWARA)
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return GEN_KAWARA
    from PIL import Image

    N, P = 1024, 128
    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    dxr = ((xx + P / 2) % P) - P / 2  # 距最近丸瓦中心
    col = np.floor((xx + P / 2) / P).astype(int) % (N // P)
    cy = yy % P
    course = np.floor(yy / P).astype(int)
    rr, mw = 24.0, 5.0
    a = np.abs(dxr)
    h = 0.22 * (a / (P / 2)) ** 0.8 * 0 + 0.25 * (1 - a / (P / 2))  # 平瓦：靠近丸瓦處較高
    h = h + 0.14 * (cy / P)  # 每列瓦片下緣微微翹起
    mortar = (a >= rr) & (a < rr + mw)
    rnd = np.clip(1 - (dxr / rr) ** 2, 0, 1)
    round_ = a < rr
    h = np.where(round_, 0.42 + 0.58 * np.sqrt(rnd), h)
    h = np.where(mortar, 0.36, h)
    joint = (cy < 3) & ~mortar
    h = np.where(joint, h - 0.1, h)
    tone = rng.uniform(0.9, 1.1, size=(N // P + 1, N // P + 1))
    t = tone[course % tone.shape[0], col]
    fine = rng.normal(0, 4, size=(N, N))
    base = np.stack([96 * t, 100 * t, 106 * t], -1) + fine[..., None]
    base = np.where(round_[..., None], base * 0.93, base)
    base = np.where(mortar[..., None], np.array([226, 225, 219]) + fine[..., None] * 0.5, base)
    base = np.where(joint[..., None], base * 0.6, base)
    gy, gx = np.gradient(h)
    s = 9.0
    nx, ny, nz = -gx * s, gy * s, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nor = np.stack([(nx / ln * 0.5 + 0.5) * 255, (ny / ln * 0.5 + 0.5) * 255, (nz / ln * 0.5 + 0.5) * 255], -1)
    ao = 255 * (0.62 + 0.38 * np.clip(h / 0.9, 0, 1))
    rough = np.where(mortar, 0.85, 0.5) * 255
    arm = np.stack([ao, rough, np.zeros_like(h)], -1)
    os.makedirs(out, exist_ok=True)
    for fn, arr in (("diff", base), ("nor", nor), ("arm", arm)):
        Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(os.path.join(out, fn + ".jpg"), quality=88)
    return GEN_KAWARA


class _HB(Builder):
    """屋頂瓦材質依屋面坡向決定 UV（瓦筋一律沿著下坡方向），其他面用方塊投影"""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.oriented = set()

    def _uv(self):
        uv = self.bm.loops.layers.uv.verify()
        for f in self.bm.faces:
            mi = f.material_index
            tile = self.tiles[mi] if mi < len(self.tiles) else 1.0
            n = f.normal.copy()
            if n.z < 0:
                n = -n
            if mi in self.oriented and n.z > 0.2 and max(abs(n.x), abs(n.y)) > 0.06:
                if abs(n.x) >= abs(n.y):
                    sg = 1 if n.x > 0 else -1
                    for l in f.loops:
                        c = l.vert.co
                        l[uv].uv = (-sg * c.y / tile, sg * c.x / tile)
                else:
                    sg = 1 if n.y > 0 else -1
                    for l in f.loops:
                        c = l.vert.co
                        l[uv].uv = (sg * c.x / tile, sg * c.y / tile)
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
    """屋面斷面（反り）：簷口較平、往上漸陡"""
    return s * (0.4 + 0.6 * s)


# ====================================================================== 姬路城
def himeji(path):
    b = _HB("Himeji", seed=23)
    bm = b.bm
    grass = b.tex("grass", "grass_ground", tile=5.0, tint="#5f8a3a", rough=0.95, normal=0)
    soil = b.color("soil", "#5d4a35", rough=0.95)
    gravel = b.tex("gravel", "gravel_floor", tile=3.0, tint="#cbbfa6", rough=0.95, normal=0)
    stone = b.tex("ishigaki", "japanese_stone_wall", tile=4.2, tint="#a49c8c", gain=1.05, normal=1.2)
    plaster = b.tex("plaster", "plastered_wall_04", tile=4.0, tint="#f6f5f1", gain=1.02, rough=0.85, normal=0)
    roof = b.tex("roof", _gen_kawara(), tile=2.4, normal=1.0)
    b.oriented.add(roof)
    noki = b.color("noki", "#55585d", rough=0.6)  # 軒瓦（簷口瓦當）
    ridge = b.color("ridge", "#6a6d72", rough=0.55)
    win = b.color("window", "#24221f", rough=0.9)
    shachi_m = b.color("shachi", "#3e4145", rough=0.45, metal=0.2)
    trunk_b = b.color("trunk", "#5b4b3b", rough=0.9)
    trunk_p = b.color("pine_trunk", "#6a5241", rough=0.9)
    leaf = [b.color("leaf_l", "#6f9b45", rough=0.8), b.color("leaf_m", "#557f34", rough=0.82), b.color("leaf_d", "#3d6427", rough=0.85)]
    pine = [b.color("pine_l", "#4d6f3b", rough=0.85), b.color("pine_d", "#304e2b", rough=0.88)]

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

    def capture(fn):
        bm.verts.ensure_lookup_table()
        start = len(bm.verts)
        fn()
        bm.verts.ensure_lookup_table()
        return list(bm.verts[start:])

    def place(fn, x, y, z, rot=0.0):
        vs = capture(fn)
        M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(rot, 4, "Z")
        bmesh.ops.transform(bm, matrix=M, verts=vs)

    def sweep(path, w, h, mi, side=None, below=False):
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
        face(list(reversed(rings[0])), mi)
        face(rings[-1], mi)

    # ------------------------------------------------------------ 屋頂：腰屋根（環狀弧形屋面）
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
                    o = Vector((nrm[e][0] + nrm[e - 1][0], nrm[e][1] + nrm[e - 1][1], 0)).normalized()
                else:
                    o = Vector((nrm[e][0], nrm[e][1], 0))
                pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, dc, o))
        return pts

    def skirt(hx0, hy0, hx1, hy1, rise, U, wall_hx, wall_hy, thick=0.5, rows=7, K=12, s_end=1.0, lift_end=1.0):
        """局部座標，簷口高 z=0。由簷口(hx0,hy0)以弧面升到內側(hx1,hy1)，四角上翹 U"""
        Lc = min(7.5, 0.36 * min(2 * hx0, 2 * hy0) + 1.0)
        P = U * 0.55
        rings = []
        for i in range(rows + 1):
            s = s_end * i / rows
            hx = hx0 + (hx1 - hx0) * s
            hy = hy0 + (hy1 - hy0) * s
            z = rise * _g(s)
            fall = max(0.0, 1 - s / lift_end) ** 2
            ring = []
            for x, y, dc, o in ring_pts(hx, hy, K):
                w = max(0.0, 1 - dc / Lc) ** 2.2 * fall
                ring.append(V((x + o.x * P * w, y + o.y * P * w, z + U * w)))
            rings.append(ring)
        strip(rings, roof)
        # 軒先厚度
        low = [V((v.co.x, v.co.y, v.co.z - thick)) for v in rings[0]]
        strip([rings[0], low], noki)
        # 白漆喰軒裏：由軒先下緣斜回牆面
        inner = [V((x, y, 0.15 - thick * 0.2)) for x, y, dc, o in ring_pts(wall_hx, wall_hy, K)]
        strip([low, inner], plaster)
        # 隅棟（四條斜脊）＋鬼瓦
        for e in range(4):
            path = [(r[e * K].co.x, r[e * K].co.y, r[e * K].co.z + 0.05) for r in rings]
            sweep(path, 0.42, 0.32, ridge)
            p0 = rings[0][e * K].co
            b.box(ridge, (0.55, 0.55, 0.75), (p0.x, p0.y, p0.z + 0.3), rot=(0, 0, math.pi / 4))
        return rings

    # ------------------------------------------------------------ 屋頂：入母屋（最上層與渡櫓）
    def irimoya(hx0, hy0, rise, U, wall_hx, wall_hy, sg=0.5, thick=0.5, shachi=0.0, rows_h=5, rows_u=5):
        """局部座標、屋脊沿 X；簷口高 z=0。下段四坡（寄棟），上段兩坡＋左右垂直的妻壁（入母屋破風）"""
        skirt(hx0, hy0, hx0 - hy0 * sg, hy0 * (1 - sg), rise * _g(sg), U, wall_hx, wall_hy, thick=thick, rows=rows_h, K=12,
              lift_end=1.0)
        # 修正：skirt 以線性內縮產生 s∈[0,1]，此處高度曲線需與上段相接 → 上段由 _g 的 sg 起算
        xg = hx0 - hy0 * sg
        e = 0.7
        xs = [-(xg + e)] + [-(xg) + 2 * xg * k / 6 for k in range(7)] + [xg + e]
        z_at = lambda s: rise * _g(s)
        # skirt 內的高度：rise*_g(sg)*_g(s')，與上段不同；改以上段 z 起點對齊
        zb = rise * _g(sg) * _g(1.0)
        tops = {}
        for side in (-1, 1):
            rows = []
            for i in range(rows_u + 1):
                s = sg + (1 - sg) * i / rows_u
                yv = side * hy0 * (1 - s)
                z = zb + (z_at(s) - z_at(sg))
                rows.append([V((x, yv, z)) for x in xs])
            strip(rows if side < 0 else list(reversed(rows)), roof, closed=False)
            bot = [[V((v.co.x, v.co.y, v.co.z - 0.28)) for v in r] for r in rows]
            strip(list(reversed(bot)) if side < 0 else bot, plaster, closed=False)
            for r, rb in ((rows[0], bot[0]),):
                strip([r, rb], noki, closed=False)
            for idx in (0, -1):
                strip([[r[idx] for r in rows], [r[idx] for r in bot]], noki, closed=False)
            tops[side] = rows
            # 破風板（白漆喰）沿山牆斜邊
            for sx in (-1, 1):
                pathb = [(sx * (xg + e - 0.18), r[0].co.y, r[0].co.z - 0.25) for r in rows]
                sweep(pathb, 0.32, 0.62, plaster, side=(1, 0, 0), below=True)
        # 妻壁（白漆喰三角面，略內縮）
        for sx in (-1, 1):
            pts = []
            for side in (-1, 1):
                seq = tops[side] if side < 0 else list(reversed(tops[side]))
                for r in seq:
                    pts.append((r[0].co.y, r[0].co.z - 0.35))
            # 依 y 排序成多邊形（底邊在 zb）
            pts = sorted(set((round(y, 4), round(z, 4)) for y, z in pts))
            poly = [(pts[0][0], zb - 0.6)] + pts + [(pts[-1][0], zb - 0.6)]
            front = [V((sx * xg, y, z)) for y, z in poly]
            back = [V((sx * (xg - 0.4), y, z)) for y, z in poly]
            if sx > 0:
                face(front, plaster)
                face(list(reversed(back)), plaster)
            else:
                face(list(reversed(front)), plaster)
                face(back, plaster)
            n = len(poly)
            for i in range(n):
                j = (i + 1) % n
                face([front[i], front[j], back[j], back[i]], plaster)
            # 懸魚
            b.box(shachi_m, (0.25, 1.0, 1.1), (sx * (xg + 0.1), 0, zb + (rise - zb) * 0.62))
        # 大棟
        zr = zb + (z_at(1.0) - z_at(sg))
        sweep([(-(xg + e + 0.4), 0, zr - 0.15), ((xg + e + 0.4), 0, zr - 0.15)], 0.75, 0.95, ridge)
        if shachi > 0:
            for sx in (-1, 1):
                x = sx * (xg + e + 0.1)
                b.box(shachi_m, (0.5 * shachi, 0.32 * shachi, 1.0 * shachi), (x, 0, zr + 0.75 + 0.45 * shachi), rot=(0, -sx * 0.25, 0))
                b.box(shachi_m, (0.35 * shachi, 0.22 * shachi, 0.65 * shachi), (x + sx * 0.25 * shachi, 0, zr + 0.8 + 1.1 * shachi), rot=(0, sx * 0.6, 0))
        return zr

    # ------------------------------------------------------------ 破風
    def chidori(w, h, depth, ov=0.8, sideov=0.6, thick=0.32):
        """千鳥破風：局部座標，妻面朝 -Y、底邊中點在原點"""
        X = w / 2 + sideov
        Ht = h * X / (w / 2) * 0.93 + 0.2
        zf = lambda a: Ht * (1 - a) * (1 - 0.25 * a)
        prof = [(X * a, zf(abs(a))) for a in [k / 7 - 1 for k in range(15)]]
        front = [V((x, -ov, z)) for x, z in prof]
        back = [V((x, depth, z)) for x, z in prof]
        strip([back, front], roof, closed=False)
        fb = [V((x, -ov, z - thick)) for x, z in prof]
        bb = [V((x, depth, z - thick)) for x, z in prof]
        strip([fb, bb], plaster, closed=False)
        strip([front, fb], noki, closed=False)
        strip([bb, back], noki, closed=False)
        strip([[front[0], back[0]], [fb[0], bb[0]]], noki, closed=False)
        strip([[back[-1], front[-1]], [bb[-1], fb[-1]]], noki, closed=False)
        # 妻壁
        tri = [(-w / 2, -1.2)] + [(x, zf(abs(x) / X) - thick - 0.05) for x in [w / 2 * (k / 5 - 1) for k in range(11)]] + [(w / 2, -1.2)]
        fr = [V((x, 0, z)) for x, z in tri]
        bk = [V((x, depth, z)) for x, z in tri]
        face(list(reversed(fr)), plaster)
        face(bk, plaster)
        n = len(tri)
        for i in range(n):
            j = (i + 1) % n
            face([fr[j], fr[i], bk[i], bk[j]], plaster)
        # 破風板與懸魚
        sweep([(x, -ov + 0.2, zf(abs(x) / X) - thick + 0.02) for x in [X * 0.97 * (k / 7 - 1) for k in range(15)]], 0.34, 0.5, plaster, side=(0, 1, 0), below=True)
        b.box(shachi_m, (0.7, 0.2, 0.9), (0, -ov + 0.3, zf(0) - thick - 0.9))

    def karahafu(w, hk, depth, ov=0.9, thick=0.32):
        """唐破風：中央弓起、兩端反轉下垂的曲線山牆"""
        X = w / 2 + 0.5
        zc = lambda x: 0.55 + hk * ((1 + math.cos(math.pi * x / X)) / 2) ** 0.85
        xs = [X * (k / 10 - 1) for k in range(21)]
        front = [V((x, -ov, zc(x))) for x in xs]
        back = [V((x, depth, zc(x))) for x in xs]
        strip([back, front], roof, closed=False)
        fb = [V((x, -ov, zc(x) - thick)) for x in xs]
        bb = [V((x, depth, zc(x) - thick)) for x in xs]
        strip([fb, bb], plaster, closed=False)
        strip([front, fb], noki, closed=False)
        strip([[front[0], back[0]], [fb[0], bb[0]]], noki, closed=False)
        strip([[back[-1], front[-1]], [bb[-1], fb[-1]]], noki, closed=False)
        sweep([(x, -ov + 0.22, zc(x) - thick + 0.02) for x in xs[1:-1]], 0.38, 0.62, plaster, side=(0, 1, 0), below=True)
        poly = [(-w / 2, -1.0)] + [(x, zc(x) - thick - 0.62) for x in xs if abs(x) <= w / 2] + [(w / 2, -1.0)]
        fr = [V((x, -0.1, z)) for x, z in poly]
        bk = [V((x, depth, z)) for x, z in poly]
        face(list(reversed(fr)), plaster)
        face(bk, plaster)
        for i in range(len(poly)):
            j = (i + 1) % len(poly)
            face([fr[j], fr[i], bk[i], bk[j]], plaster)

    # ------------------------------------------------------------ 牆與窗
    def window(cx, cy, z, nx, ny, w, h, bars=None):
        rot = math.atan2(-nx, ny)  # 局部 +Y = 牆外法線
        def mk():
            b.box_base(win, (w, 0.12, h), (0, -0.0, 0))
            nb = bars or max(3, int(w / 0.2))
            for k in range(nb):
                x = -w / 2 + w * (k + 0.5) / nb
                b.box_base(plaster, (0.07, 0.1, h), (x, 0.05, 0))
            b.box_base(plaster, (w + 0.3, 0.14, 0.12), (0, 0.02, -0.12))
        place(mk, cx, cy, z, rot)

    def walls(cx, cy, z, w, d, h, n_ns, n_ew, wz=0.42, ww=1.0, wh=0.9, skip_ns=0.0, skip_ew=0.0):
        b.box_base(plaster, (w, d, h), (cx, cy, z))
        for side in range(4):
            nx, ny = [(0, -1), (1, 0), (0, 1), (-1, 0)][side]
            L = w if side % 2 == 0 else d
            n = n_ns if side % 2 == 0 else n_ew
            skip = skip_ns if side % 2 == 0 else skip_ew
            for i in range(n):
                off = -L / 2 + 1.4 + (L - 2.8) * (i + 0.5) / n
                if abs(off) < skip:
                    continue
                px = cx + nx * (w / 2) + (-ny) * off
                py = cy + ny * (d / 2) + nx * off
                window(px, py, z + h * wz, nx, ny, ww, wh)

    def lattice_bay(cx, cy, z, nx, ny, w, h):
        rot = math.atan2(-nx, ny)
        def mk():
            b.box_base(plaster, (w + 0.5, 0.75, h + 0.7), (0, 0.3, -0.45))
            b.box_base(win, (w, 0.1, h), (0, 0.7, 0))
            nb = int(w / 0.17)
            for k in range(nb):
                b.box_base(plaster, (0.06, 0.1, h), (-w / 2 + w * (k + 0.5) / nb, 0.76, 0))
        place(mk, cx, cy, z, rot)

    # ------------------------------------------------------------ 石垣（扇之勾配）
    def ishigaki(cx, cy, w, d, h, zb, batter=0.3, p=2.2, rows=10, ring=False, lip=1.0):
        rs = []
        for i in range(rows + 1):
            t = i / rows
            o = batter * h * (1 - t) ** p
            hx, hy = w / 2 + o, d / 2 + o
            z = zb + h * t
            # 角部（算木積）略為外張
            rs.append([V((cx + sx * hx, cy + sy * hy, z)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
        strip(rs, stone)
        top = rs[-1]
        if ring:
            inner_top = [V((cx + sx * (w / 2 - lip), cy + sy * (d / 2 - lip), zb + h)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            inner_bot = [V((cx + sx * (w / 2 - lip), cy + sy * (d / 2 - lip), zb + h - 1.5)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            strip([top, inner_top], stone)
            strip([inner_top, inner_bot], stone)
        else:
            face(top, stone)

    # ------------------------------------------------------------ 天守（多重塔）
    def tower(cx, cy, z, levels, ov=2.1, U=0.85, top_U=1.05, top_rise_k=0.72, shachi=1.6, gables=None, lattice=None):
        """levels: [(w, d, h, n_ns, n_ew)]；gables: {level: [(side, kind, w, h, off)]}"""
        gables = gables or {}
        for k, (w, d, h, n_ns, n_ew) in enumerate(levels):
            last = k == len(levels) - 1
            walls(cx, cy, z, w, d, h + 0.5, n_ns, n_ew, wz=0.38 if not last else 0.3, ww=1.0 if not last else 1.25,
                  wh=0.9 if not last else 1.25)
            if lattice and k in lattice:
                for sgn in (-1, 1):
                    lattice_bay(cx, cy + sgn * d / 2, z + h * 0.32, 0, sgn, lattice[k], 1.5)
            z_e = z + h
            hx0, hy0 = w / 2 + ov, d / 2 + ov
            if not last:
                w2, d2 = levels[k + 1][:2]
                hx1, hy1 = w2 / 2 - 0.2, d2 / 2 - 0.2
                M = min(hx0 - hx1, hy0 - hy1)
                rise = 0.5 * M + 0.35
                place(lambda: skirt(hx0, hy0, hx1, hy1, rise, U, w / 2, d / 2), cx, cy, z_e)
                for side, kind, gw, gh, off in gables.get(k, []):
                    Mx, My = hx0 - hx1, hy0 - hy1
                    Ms = My if side in "SN" else Mx
                    mf = Ms * 0.3
                    zf = z_e + rise * _g(mf / Ms) - 0.25
                    depth = Ms - mf + 0.8
                    if side == "S":
                        pos, rot = (cx + off, cy - (hy0 - mf)), 0.0
                    elif side == "N":
                        pos, rot = (cx - off, cy + (hy0 - mf)), math.pi
                    elif side == "E":
                        pos, rot = (cx + (hx0 - mf), cy + off), math.pi / 2
                    else:
                        pos, rot = (cx - (hx0 - mf), cy - off), -math.pi / 2
                    if kind == "c":
                        place(lambda gw=gw, gh=gh, depth=depth: chidori(gw, gh, depth), pos[0], pos[1], zf, rot)
                    else:
                        place(lambda gw=gw, gh=gh, depth=depth: karahafu(gw, gh, depth), pos[0], pos[1], zf, rot)
                z = z_e + rise - 0.4
            else:
                if w >= d:
                    zr = [0]
                    place(lambda: zr.__setitem__(0, irimoya(hx0, hy0, top_rise_k * hy0 * 1.0, top_U, w / 2, d / 2, shachi=shachi)), cx, cy, z_e)
                else:
                    place(lambda: irimoya(hy0, hx0, top_rise_k * hx0, top_U, d / 2, w / 2, shachi=shachi), cx, cy, z_e, math.pi / 2)
                return z_e

    def corridor(x0, y0, x1, y1, wd, zb, base_h, h1=3.6, h2=3.2):
        """渡櫓：石垣上 2 層，入母屋屋頂"""
        L = math.hypot(x1 - x0, y1 - y0)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        along_x = abs(x1 - x0) >= abs(y1 - y0)
        w, d = (L, wd) if along_x else (wd, L)
        ishigaki(mx, my, w, d, base_h, zb, batter=0.25)
        z = zb + base_h
        walls(mx, my, z, w, d, h1 + 0.5, max(1, int(w / 3.2)), max(1, int(d / 3.2)))
        hx0, hy0 = w / 2 + 1.6, d / 2 + 1.6
        w2, d2 = w - 0.8, d - 0.8
        rise = 0.5 * 1.8 + 0.3
        place(lambda: skirt(hx0, hy0, w2 / 2 - 0.2, d2 / 2 - 0.2, rise, 0.5, w / 2, d / 2, K=10), mx, my, z + h1)
        z2 = z + h1 + rise - 0.4
        walls(mx, my, z2, w2, d2, h2 + 0.5, max(1, int(w2 / 3.0)), max(1, int(d2 / 3.0)))
        if along_x:
            place(lambda: irimoya(w2 / 2 + 1.7, d2 / 2 + 1.7, 0.7 * (d2 / 2 + 1.7), 0.6, w2 / 2, d2 / 2, sg=0.45), mx, my, z2 + h2)
        else:
            place(lambda: irimoya(d2 / 2 + 1.7, w2 / 2 + 1.7, 0.7 * (w2 / 2 + 1.7), 0.6, d2 / 2, w2 / 2, sg=0.45), mx, my, z2 + h2, math.pi / 2)

    def dobei(x0, y0, x1, y1, z, h=2.3):
        """土塀：白壁＋瓦屋根"""
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        b.box_base(plaster, (L, 0.6, h), (mx, my, z - 0.3), rot=(0, 0, ang))
        b.tri_prism(roof, L + 0.4, 1.7, 0.55, (mx, my, z - 0.3 + h - 0.05), rot_z=ang)
        b.box_base(ridge, (L + 0.4, 0.25, 0.22), (mx, my, z - 0.3 + h + 0.45), rot=(0, 0, ang))

    # ================================================================ 地形
    ZP, Z1 = 12.0, 3.0  # 本丸台地、周圍地面
    PX0, PX1, PY0, PY1 = -58.0, 30.0, -32.0, 50.0

    def hill(x, y):
        dx = max(PX0 - x, 0, x - PX1)
        dy = max(PY0 - y, 0, y - PY1)
        d = math.hypot(dx, dy)
        t = min(1.0, max(0.0, (d - 6) / 120))
        base = Z1 * (0.5 + 0.5 * math.cos(math.pi * t))
        return base + 0.8 * noise.noise(Vector((x / 35, y / 35, 0.3))) * min(1, d / 15)

    b.ground_disc(grass, 190, soil, depth=6, height_fn=hill, rings=40, seg=128)
    # 台地：扇之勾配石垣（中空環）＋碎石廣場
    ishigaki((PX0 + PX1) / 2, (PY0 + PY1) / 2, PX1 - PX0, PY1 - PY0, ZP + 0.4 - (Z1 - 1.5), Z1 - 1.5, batter=0.28, ring=True)
    b.box_base(gravel, (PX1 - PX0 - 1.5, PY1 - PY0 - 1.5, 0.3), ((PX0 + PX1) / 2, (PY0 + PY1) / 2, ZP - 0.3))

    # ================================================================ 大天守（5 重 6 階）
    W1, D1 = 26.0, 21.0
    fac = [1.0, 0.92, 0.8, 0.66, 0.47]
    hts = [4.2, 4.3, 4.0, 3.9, 3.7]
    nwin = [(8, 6), (7, 5), (6, 4), (5, 4), (6, 4)]
    lv = [(W1 * f, D1 * f, h, a, c) for f, h, (a, c) in zip(fac, hts, nwin)]
    zk = ZP + 14.85
    ishigaki(0, 0, W1 + 0.4, D1 + 0.4, 14.85 + 0.6, ZP - 0.6, batter=0.3, p=2.3)
    gab = {
        0: [("E", "c", 4.0, 2.2, 0.0), ("W", "c", 4.0, 2.2, 0.0)],
        1: [("S", "k", 7.0, 1.7, 0.0), ("N", "k", 7.0, 1.7, 0.0), ("E", "c", D1 * 0.92 * 0.72, 5.2, 0.0), ("W", "c", D1 * 0.92 * 0.72, 5.2, 0.0)],
        2: [("S", "c", 5.0, 2.6, -3.2), ("S", "c", 5.0, 2.6, 3.2), ("N", "c", 5.0, 2.6, -3.2), ("N", "c", 5.0, 2.6, 3.2),
            ("E", "c", 5.5, 2.9, 0.0), ("W", "c", 5.5, 2.9, 0.0)],
        3: [("S", "c", 7.2, 3.3, 0.0), ("N", "c", 7.2, 3.3, 0.0), ("E", "k", 4.6, 1.3, 0.0), ("W", "k", 4.6, 1.3, 0.0)],
    }
    ztop = tower(0, 0, zk, lv, gables=gab, lattice={1: 5.0}, shachi=1.9)
    print(f"  himeji main keep: stone top {zk:.1f}, top-level eave {ztop:.1f}")

    # ================================================================ 小天守與渡櫓
    small = [  # (cx, cy, w, d, 石垣高, levels)
        (-36.0, 3.0, 15.0, 12.5, 11.0, [(15.0, 12.5, 4.0, 5, 4), (12.6, 10.4, 3.8, 4, 3), (9.6, 8.0, 3.4, 3, 3)]),   # 西小天守
        (-35.0, 31.0, 16.0, 13.5, 11.0, [(16.0, 13.5, 4.2, 5, 4), (13.4, 11.2, 4.0, 4, 3), (10.2, 8.6, 3.6, 3, 3)]),  # 乾小天守
        (4.0, 32.0, 12.5, 10.5, 11.0, [(12.5, 10.5, 3.9, 4, 3), (10.4, 8.8, 3.6, 3, 3), (8.0, 6.8, 3.3, 3, 2)]),     # 東小天守
    ]
    sg_small = {
        0: [("S", "c", 4.2, 2.2, 0.0), ("E", "c", 3.6, 2.0, 0.0), ("N", "c", 4.2, 2.2, 0.0)],
        1: [("S", "k", 3.6, 1.0, 0.0), ("W", "c", 3.4, 1.9, 0.0), ("E", "c", 3.4, 1.9, 0.0)],
    }
    for cx, cy, w, d, bh, levels in small:
        ishigaki(cx, cy, w + 0.4, d + 0.4, bh + 0.6, ZP - 0.6, batter=0.28)
        tower(cx, cy, ZP + bh, levels, ov=1.8, U=0.7, top_U=0.85, shachi=1.2, gables=sg_small)
    corridor(-13.0, 2.0, -28.5, 2.0, 8.0, ZP - 0.6, 11.6)     # イの渡櫓：大天守—西小天守
    corridor(-36.0, 9.25, -36.0, 24.25, 8.0, ZP - 0.6, 11.6)  # ロの渡櫓：西小天守—乾小天守
    corridor(-27.0, 31.5, -2.25, 31.5, 8.0, ZP - 0.6, 11.6)   # ハの渡櫓：乾小天守—東小天守
    corridor(4.0, 10.5, 4.0, 26.75, 8.0, ZP - 0.6, 11.6)      # ニの渡櫓：東小天守—大天守

    # ================================================================ 台地南緣的多聞櫓與土塀
    corridor(-48.0, -28.0, -6.0, -28.0, 6.5, ZP - 0.4, 0.4, h1=3.4, h2=3.0)
    tower(8.0, -26.5, ZP, [(9.5, 8.0, 3.8, 3, 3), (7.6, 6.4, 3.4, 2, 2)], ov=1.6, U=0.6, top_U=0.7, shachi=0.9)
    dobei(14.0, -30.5, 28.5, -30.5, ZP)
    dobei(28.5, -30.5, 28.5, 10.0, ZP)
    dobei(-56.5, -24.0, -56.5, 30.0, ZP)

    # ================================================================ 植栽：黑松與闊葉樹
    def blob(mi, loc, rx, ry, rz, lump=0.3):
        off = Vector((b.rng.uniform(0, 99), b.rng.uniform(0, 99), b.rng.uniform(0, 99)))
        r = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0, matrix=Matrix.Identity(4))
        for v in r["verts"]:
            p = v.co.copy()
            n = noise.noise(p * 1.6 + off) * 0.7 + noise.noise(p * 3.5 + off) * 0.3
            k = 1 + lump * n
            v.co = Vector((loc[0] + p.x * rx * k, loc[1] + p.y * ry * k, loc[2] + p.z * rz * k))
        for f in {f for v in r["verts"] for f in v.link_faces}:
            f.material_index = mi
            f.smooth = True

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

    def broadleaf(x, y, z, h):
        R = h * b.rng.uniform(0.28, 0.36)
        cz = z + h - R * 0.95
        lean = Vector((b.rng.uniform(-1, 1), b.rng.uniform(-1, 1), 0)) * 0.06 * h
        tube([(x, y, z - 0.5), (x + lean.x * 0.5, y + lean.y * 0.5, z + h * 0.3), (x + lean.x, y + lean.y, cz)], h * 0.035, h * 0.018, trunk_b)
        cx, cy = x + lean.x, y + lean.y
        n = b.rng.randint(8, 12)
        for i in range(n):
            a = b.rng.uniform(0, TAU)
            rr = R * math.sqrt(b.rng.uniform(0.05, 1)) * 0.62
            dz = b.rng.uniform(-0.45, 0.55) * R
            br = R * b.rng.uniform(0.42, 0.62)
            mi = leaf[0] if dz > 0.18 * R else (leaf[2] if dz < -0.15 * R else leaf[1])
            if b.rng.random() < 0.25:
                mi = leaf[b.rng.randint(0, 2)]
            blob(mi, (cx + rr * math.cos(a), cy + rr * math.sin(a), cz + dz), br * 1.05, br * 1.05, br * 0.85)

    def pine_tree(x, y, z, h):
        pts = [(x, y, z - 0.5)]
        px, py = x, y
        ang = b.rng.uniform(0, TAU)
        for k in range(1, 5):
            ang += b.rng.uniform(-0.9, 0.9)
            px += math.cos(ang) * h * 0.07
            py += math.sin(ang) * h * 0.07
            pts.append((px, py, z + h * 0.82 * k / 4))
        tube(pts, h * 0.04, h * 0.02, trunk_p)
        npad = b.rng.randint(5, 7)
        for i in range(npad):
            f = 0.42 + 0.58 * i / (npad - 1)
            k = min(3, int(f * 4))
            p0 = Vector(pts[k]).lerp(Vector(pts[k + 1]), f * 4 - k) if k < 4 else Vector(pts[-1])
            a = b.rng.uniform(0, TAU)
            reach = h * (0.32 - 0.22 * f) * b.rng.uniform(0.7, 1.2)
            c = p0 + Vector((math.cos(a) * reach, math.sin(a) * reach, h * 0.04))
            tube([p0, (p0 + c) / 2 + Vector((0, 0, h * 0.03)), c], h * 0.014, h * 0.008, trunk_p, seg=5)
            rpad = h * (0.2 - 0.08 * f) * b.rng.uniform(0.85, 1.15)
            blob(pine[0], (c.x, c.y, c.z + rpad * 0.15), rpad * 1.15, rpad * 1.0, rpad * 0.36, lump=0.35)
            blob(pine[1], (c.x, c.y, c.z - rpad * 0.05), rpad * 1.05, rpad * 0.95, rpad * 0.3, lump=0.3)
        top = Vector(pts[-1])
        blob(pine[0], (top.x, top.y, top.z + h * 0.06), h * 0.15, h * 0.13, h * 0.07, lump=0.35)

    def in_plateau(x, y, m=6):
        return PX0 - m < x < PX1 + m and PY0 - m < y < PY1 + m

    pts = b.scatter(260, 20, 182, min_dist=7.5, avoid=lambda x, y: in_plateau(x, y, 7))
    for i, (x, y) in enumerate(pts):
        z = hill(x, y)
        if b.rng.random() < 0.3:
            pine_tree(x, y, z, b.rng.uniform(7, 11))
        else:
            broadleaf(x, y, z, b.rng.uniform(8, 14))
    # 台地上點綴的松樹
    for x, y in [(-50, -18), (22, -18), (-50, 44), (20, 44), (-20, -18), (24, 20)]:
        pine_tree(x, y, ZP, b.rng.uniform(6, 8))

    # 地理座標 → 南立面朝向相機（+Y）
    bmesh.ops.rotate(bm, verts=bm.verts[:], cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi, 3, "Z"))
    b.export(path)
