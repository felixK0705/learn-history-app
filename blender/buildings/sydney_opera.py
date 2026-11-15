"""sydney-opera 雪梨歌劇院（1973）寫實模型（公尺；+Y 北＝便利朗角尖端，水面 z=0）

- 基座（podium）：長約 183 m、寬約 120 m，粉褐色花崗岩預鑄板；南側紀念大階梯、四周臨水步道
- 殼體（shells）：全部取自同一族球面的「球面三角形」——每片帆由兩個鏡射的球面三角形沿脊線接合
  （伍重的球面解法）；外覆白色與奶油色兩種瓷磚組成的人字紋
- 西側音樂廳（Concert Hall）3 片朝北的帆＋1 片朝南的帆、東側瓊・蘇莎蘭劇院同樣配置但略小；
  西南角便利朗餐廳 2 片小帆；最高點約海拔 67 m
- 帆口為傾斜的深茶色玻璃牆；殼下的大廳量體與玻璃帶
- 周圍港灣水面（半徑 450 m 內），南側植物園樹林
"""

import math
import os

import numpy as np
from mathutils import Matrix, Vector

from lib import TAU
from buildings.forbidden_city import CnBuilder, gen_paving
from buildings.kinkakuji import GEN, _cloud, _height_to_normal, _save_maps, gen_canopy, gen_leaves

# (目標點, 方位角, 仰角, 距離, 焦距)：參考照自西側港灣水面（北端在左）平視
CAMERA = ((0.0, -8.0, 28.0), -86.0, -2.6, 400.0, 46)


def gen_tiles_sail(name, seed=3):
    """帆面瓷磚：亮白光面磚與奶油色霧面磚組成的人字紋（chevron），細縫；貼圖 2.4 m 一循環"""
    out = os.path.join(GEN, f"so_tiles_{name}")
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return out
    N = 512
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    P = N / 8
    u = xx % P
    v = (yy + np.abs(u - P / 2)) % P
    tile = (np.floor((yy + np.abs(u - P / 2)) / (P / 4)) % 4 == 0)
    base = np.where(tile[..., None], np.array((226, 218, 196), float)[None, None], np.array((244, 241, 232), float)[None, None])
    jt = ((xx % (P / 4)) < 1.5) | ((v % (P / 4)) < 1.5)
    diff = base * (1 + _cloud(rng, N, 32, 0.04))[..., None]
    diff = np.where(jt[..., None], diff * 0.86, diff)
    _save_maps(out, diff, _height_to_normal(np.where(jt, 0.0, 1.0), 1.0))
    return out


def circumsphere(pts):
    """四點外接球心"""
    p0 = np.array(pts[0])
    A = np.array([2 * (np.array(p) - p0) for p in pts[1:]])
    bvec = np.array([np.dot(p, p) - np.dot(p0, p0) for p in map(np.array, pts[1:])])
    c = np.linalg.solve(A, bvec)
    return Vector(c), float(np.linalg.norm(c - p0))


class SailBuilder(CnBuilder):
    def sph_tri(self, mi, C, R, a, b_, c, n=28, flip=False):
        """球面三角形（頂點方向自球心 C 以 a,b,c 方向插值、半徑 R）；回傳邊界點列（a→c、a→b）"""
        da, db, dc = (Vector(a) - C).normalized(), (Vector(b_) - C).normalized(), (Vector(c) - C).normalized()
        grid = {}
        for i in range(n + 1):
            for j in range(n + 1 - i):
                d = (da * (n - i - j) + db * i + dc * j) / n
                grid[(i, j)] = self.V(C + d.normalized() * R)
        for i in range(n):
            for j in range(n - i):
                tri = [grid[(i, j)], grid[(i + 1, j)], grid[(i, j + 1)]]
                self.face(list(reversed(tri)) if flip else tri, mi, smooth=True)
                if i + j < n - 1:
                    tri = [grid[(i + 1, j)], grid[(i + 1, j + 1)], grid[(i, j + 1)]]
                    self.face(list(reversed(tri)) if flip else tri, mi, smooth=True)
        return [grid[(0, j)].co.copy() for j in range(n + 1)]

    def sail(self, tile, under, glass, T, B, half_w, front_y, zb, cx, facing=1, thick=0.9):
        """一片帆：T 尖端 (y, z)、B 後方脊線落點 y、half_w 前緣底部半寬、front_y 帆口底部 y、zb 底部高度。
        facing=+1 朝北（帆口在 +Y 側），-1 朝南"""
        Tp = Vector((cx, T[0], T[1]))
        Bp = Vector((cx, B, zb))
        S1 = Vector((cx - half_w, front_y, zb))
        S2 = Vector((cx + half_w, front_y, zb))
        def bez(p0, k, p1, t):
            return p0 * (1 - t) ** 2 + k * 2 * t * (1 - t) + p1 * t * t
        L = abs(T[0] - B)
        Kr = Vector((cx, B + facing * 0.30 * L, T[1] * 0.97 + zb * 0.03))   # 脊線：自後方陡升、向前彎至尖端
        edges = []
        NU, NV = 26, 12
        for S in (S1, S2):
            side = -1 if S.x < cx else 1
            mid = (Tp + S) / 2
            Km = mid + Vector((side * 0.10 * half_w, facing * 0.10 * (Tp - S).length, 0))     # 帆口：略向前外凸
            rows = []
            for i in range(NU + 1):
                u = i / NU
                m = bez(Tp, Km, S, u)
                r = bez(Tp, Kr, Bp, u)
                row = []
                for j in range(NV + 1):
                    v = j / NV
                    p = m * (1 - v) + r * v
                    bulge = 4 * v * (1 - v) * u * (1 - 0.35 * u) * 0.16 * half_w
                    p = p + Vector((side * bulge, 0, bulge * 0.35))
                    row.append(p)
                rows.append(row)
            for (mi, off, flip) in ((tile, 0.0, side > 0), (under, -side * thick, side < 0)):
                vr = [[self.V(Vector((p.x + off * (1 - j / NV), p.y, p.z))) for j, p in enumerate(row)] for row in rows]
                for i in range(NU):
                    for j in range(NV):
                        q = [vr[i][j], vr[i + 1][j], vr[i + 1][j + 1], vr[i][j + 1]]
                        if i == 0:
                            q = [vr[0][0], vr[1][j], vr[1][j + 1]]
                        self.face(list(reversed(q)) if flip else q, mi, smooth=True)
            e = [row[0] for row in rows]
            for p, q in zip(e, e[1:]):
                self.face([self.V(p), self.V(q), self.V(q + Vector((-side * thick, 0, 0))), self.V(p + Vector((-side * thick, 0, 0)))], tile)
            edges.append(e)
        e1, e2 = edges
        # 帆口玻璃牆：自尖端扇形至底部（略內縮）
        inset = Vector((0, -facing * 3.0, 0))
        ring = [p + inset for p in e1[::-1][:-1]] + [p + inset for p in e2]
        ring = [Vector((p.x, p.y, max(p.z, zb))) for p in ring]
        top = self.V(Tp + inset * 1.2 - Vector((0, 0, 2.0)))
        vs = [self.V(p) for p in ring]
        for p, q in zip(vs, vs[1:]):
            self.face([top, p, q], glass)


def sydney_opera(path):
    b = SailBuilder("SydneyOpera", seed=4)
    tile = b.gtex("tiles", gen_tiles_sail("a"), tile=2.4, rough=0.25, normal=0.3)
    under = b.color("rib", "#cfc6b4", rough=0.7)
    glass = b.color("glass", "#2a2018", rough=0.08, metal=0.3)
    podium = b.gtex("podium", gen_paving("so_granite2", (190, 160, 128), bw=3, bh=6, seed=8, joint=(0.8, 0.78, 0.76)), tile=4.0,
                    rough=0.7, normal=0.3)
    podium_d = b.color("podium_d", "#a98a6c", rough=0.7)
    paving = b.gtex("pave", gen_paving("so_pave2", (176, 160, 138), bw=6, bh=12, seed=9), tile=4.0, rough=0.8, normal=0.3)
    bronze = b.color("bronze", "#6a4a36", rough=0.5, metal=0.3)
    water = b.color("water", "#0e2f4f", rough=0.38)
    lf_broad = b.alpha_mat("leaf_broad", gen_leaves("broad"))
    lf_dark = b.alpha_mat("leaf_dark", gen_leaves("dark"))
    core_b = b.gtex("core_broad", gen_canopy("broad", (70, 100, 44), seed=5), tile=3.0, rough=0.9, normal=1.0)
    bark = b.color("bark", "#5a4636", rough=0.9)
    grass = b.ptex("grass", "grass_ground", tile=4.0, tint="#5d8436", rough=0.95, normal=0.4)

    # ---------------- 港灣水面＋南岸
    n = 96
    ring = [b.V((450 * math.cos(TAU * i / n), 450 * math.sin(TAU * i / n) - 20, 0.0)) for i in range(n)]
    b.face(ring, water)
    b.box_base(grass, (300.0, 140.0, 4.0), (60.0, -185.0, -1.0))

    # ---------------- 基座：臨水步道（低）＋主基座（高）＋南側紀念大階梯
    walk = [(-62, -110), (62, -110), (62, 40), (40, 95), (-40, 95), (-62, 40)]
    b.prism(podium_d, walk, -1.0, 4.0)
    b.prism(paving, [(x * 0.995, y * 0.995) for x, y in walk], 3.0, 0.05)
    main = [(-56, -78), (56, -78), (56, 38), (36, 86), (-36, 86), (-56, 38)]
    b.prism(podium, main, 3.0, 10.0)
    b.prism(paving, [(x * 0.99, y * 0.99) for x, y in main], 13.0, 0.05)
    # 大階梯（南面，自步道 z=3 升至 z=13）
    for k in range(25):
        z = 3.0 + 10.0 * (k + 1) / 25
        y0 = -110.0 + 32.0 * k / 25
        b.box_base(podium, (96.0, (-78.0) - y0, 10.0 / 25), (0, (y0 - 78.0) / 2, z - 10.0 / 25))
    # 兩廳的上層平台（殼下量體）＋玻璃帶
    for cx in (-24.0, 24.0):
        b.box_base(podium, (44.0, 120.0, 8.0), (cx, -4.0, 13.0))
        b.box_base(glass, (44.2, 118.0, 1.4), (cx, -4.0, 18.0))
        b.box_base(bronze, (44.4, 3.0, 2.0), (cx, 57.0, 19.0))
        b.box_base(glass, (40.0, 6.0, 4.0), (cx, 58.0, 13.2))
    # 基座立面細部：玻璃帶、橫向分隔線、側面斜坡梯、北端階梯狀前廳
    for s_ in (-1, 1):
        b.box_base(glass, (0.4, 70.0, 2.6), (s_ * 56.1, -20.0, 5.0))
        b.box_base(podium_d, (0.5, 130.0, 0.35), (s_ * 56.15, -16.0, 9.0))
        b.box_base(glass, (0.4, 34.0, 2.2), (s_ * 56.1, 55.0, 5.2))
        for k in range(14):
            b.box_base(podium_d, (0.6, 0.4, 3.6), (s_ * 56.2, -54.0 + k * 5.0, 4.4))
        # 斜坡式外梯（自步道升至平台）
        L = math.hypot(30.0, 10.0)
        b.place(lambda: b.box(podium_d, (2.6, L, 0.8), (0, 0, 0)),
                Matrix.Translation((s_ * 57.4, 22.0, 8.0)) @ Matrix.Rotation(-math.atan2(10.0, 30.0), 4, "X"))
    for k, (hw, y0, y1, z) in enumerate(((30.0, 62.0, 78.0, 16.0), (24.0, 66.0, 74.0, 18.5))):
        for cx in (-24.0, 24.0):
            b.box_base(podium, (2 * hw * 0.7, y1 - y0, z - 13.0), (cx, (y0 + y1) / 2, 13.0))
            b.box_base(bronze, (2 * hw * 0.7 + 0.2, 1.0, 1.4), (cx, y1 + 0.3, z - 1.6))
    ZB = 21.0

    # ---------------- 帆（音樂廳：西；劇院：東，略小）
    def hall(cx, k, dy):
        Z = lambda z: ZB + (z - ZB) * k * 1.1  # noqa: E731
        b.sail(tile, under, glass, (57.5 + dy, Z(46.5)), 18.0 + dy, 13.0 * k, 36.0 + dy, ZB, cx, 1)
        b.sail(tile, under, glass, (33.0 + dy, Z(55.5)), -4.0 + dy, 17.0 * k, 14.0 + dy, ZB, cx, 1)
        b.sail(tile, under, glass, (14.5 + dy, Z(66.0)), -27.0 + dy, 21.0 * k, -8.0 + dy, ZB, cx, 1)
        b.sail(tile, under, glass, (-58.0 + dy, Z(41.0)), -24.0 + dy, 17.0 * k, -50.0 + dy, ZB, cx, -1)
    hall(-24.0, 1.0, 0.0)
    hall(24.0, 0.86, 4.0)
    # 便利朗餐廳（西南角，兩片小帆背對背）
    b.box_base(podium, (26.0, 50.0, 2.0), (-30.0, -80.0, 13.0))
    b.sail(tile, under, glass, (-60.0, 28.0), -79.0, 9.0, -66.0, 15.0, -30.0, 1)
    b.sail(tile, under, glass, (-101.0, 28.5), -75.0, 9.5, -93.0, 15.0, -30.0, -1)

    # ---------------- 南岸植物園的樹
    rng = b.rng
    for _ in range(18):
        x, y = rng.uniform(50, 190), rng.uniform(-240, -125)
        h = rng.uniform(12, 20)
        b.broadleaf(x, y, 1.0, h, (lf_broad, lf_dark), core_b, bark, R=h * 0.4, n_blobs=5, cap=50)

    b.export_glb(path)
