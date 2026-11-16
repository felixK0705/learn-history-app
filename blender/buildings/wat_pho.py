"""wat-pho 曼谷臥佛寺 四大佛塔（Phra Maha Chedi Si Rajakarn）寫實模型（公尺；+X 東、+Y 北）

- 四座拉瑪王佛塔（各高約 42 m）：平面為「ย่อมุมไม้สิบสอง」十二凸角方形（每角兩次內折、共 12 個外角），
  由下而上：方形台基 → 多層逐漸內收的凸角疊澀台座 → 鐘形塔身（องค์ระฆัง，平面仍為凸角十字、輪廓為鐘形曲線）
  → 寶座（บัลลังก์）→ 一圈小柱（เสาหาน）→ 多層環節細長尖頂（ปล้องไฉน）→ 蕉蕾形針頂與寶珠
- 塔身以「輪廓曲線 s(z) × 凸角十字平面」逐環放樣（lathe 式）生成；尖頂環節以旋轉體生成
- 外表為中國瓷片馬賽克：拉瑪一世綠、拉瑪二世白、拉瑪三世黃、拉瑪四世藍；藍塔四面有拱形神龕（紅門、尖拱山牆）
- 藍塔自成一院；迴廊為白牆、橘色琉璃瓦雙層屋頂、綠色邊框；庭院紅磚地、草坪、造型樹、棕櫚與石燈柱
"""

import math
import os

import numpy as np
from mathutils import Matrix, Vector

from lib import TAU
from buildings.forbidden_city import gen_paving
from buildings.kinkakuji import GEN, AsiaBuilder, _cloud, _height_to_normal, _save_maps, gen_tiles

# (目標點, 方位角, 仰角, 距離, 焦距)：參考照自藍塔院南側迴廊外的小庭院仰望
CAMERA = ((-4.0, 2.0, 20.0), 2.0, -17.0, 60.0, 26)


# ====================================================================== 貼圖
def _wrap_ellipse(dr, N, cx, cy, r, fill):
    for ox in (-N, 0, N):
        for oy in (-N, 0, N):
            x, y = cx + ox, cy + oy
            if -r <= x <= N + r and -r <= y <= N + r:
                dr.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def _flower(dr, N, cx, cy, r, petal, center, n=6):
    for k in range(n):
        a = TAU * k / n
        _wrap_ellipse(dr, N, cx + math.cos(a) * r * 0.62, cy + math.sin(a) * r * 0.62, r * 0.42, petal)
    _wrap_ellipse(dr, N, cx, cy, r * 0.36, center)


def gen_mosaic(name, base, line, flowers, seed=3):
    """瓷片馬賽克：底色上的菱形格線、格點六瓣花、格心小花，及碎瓷片色差；貼圖約 2 m 一循環"""
    out = os.path.join(GEN, f"wp_mosaic_{name}")
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return out
    from PIL import Image, ImageDraw

    N = 512
    rng = np.random.default_rng(seed)
    im = Image.new("RGB", (N, N), tuple(base))
    dr = ImageDraw.Draw(im)
    P = 64
    for k in range(-N // P, 2 * N // P + 1):  # 菱形格線（45°，週期 P 可整除 N → 無縫）
        x0 = k * P
        dr.line([(x0, 0), (x0 + N, N)], fill=tuple(line), width=3)
        dr.line([(x0, N), (x0 + N, 0)], fill=tuple(line), width=3)
    for gy in range(N // P * 2):
        for gx in range(N // P):
            cx = gx * P + (gy % 2) * P / 2
            cy = gy * P / 2
            if gy % 2 == 0:  # 格點：大花
                c = flowers[rng.integers(len(flowers))]
                c2 = flowers[rng.integers(len(flowers))]
                _flower(dr, N, cx, cy, rng.uniform(11, 14), tuple(c), tuple(c2))
            else:  # 格心：小花
                c = flowers[rng.integers(len(flowers))]
                _flower(dr, N, cx + P / 2, cy, rng.uniform(5, 7), tuple(c), tuple(line), n=4)
    for _ in range(260):  # 零星碎瓷點
        c = flowers[rng.integers(len(flowers))]
        _wrap_ellipse(dr, N, rng.uniform(0, N), rng.uniform(0, N), 2.2, tuple(c))
    a = np.asarray(im, dtype=float)
    shard = rng.uniform(-0.10, 0.10, size=(N // 4, N // 4)).repeat(4, 0).repeat(4, 1)
    a = a * (1 + _cloud(rng, N, 48, 0.22) + shard)[..., None]
    h = np.asarray(im.convert("L"), dtype=float) / 255
    h = np.abs(h - np.asarray(Image.new("L", (N, N), int(np.mean(base))), dtype=float) / 255) + shard * 0.5
    _save_maps(out, a, _height_to_normal(h * 4, 1.0))
    return out


def gen_band(name, base, stripe, flowers, seed=7):
    """疊澀線腳用的橫向飾帶：金／橘細線、色帶與一排小花（v 方向為垂直）"""
    out = os.path.join(GEN, f"wp_band_{name}")
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return out
    from PIL import Image, ImageDraw

    N = 512
    rng = np.random.default_rng(seed)
    im = Image.new("RGB", (N, N), tuple(base))
    dr = ImageDraw.Draw(im)
    rows = [(0, 20, (214, 176, 84)), (20, 70, tuple(stripe)), (70, 82, (225, 220, 205)), (190, 204, (170, 50, 40)),
            (204, 256, tuple(stripe)), (256, 268, (214, 176, 84)), (380, 392, (225, 220, 205)), (392, 450, (190, 105, 50)),
            (450, 462, (214, 176, 84))]
    for y0, y1, c in rows:
        dr.rectangle([0, y0, N, y1], fill=c)
    for y in (136, 324):
        for x in range(0, N, 32):
            c = flowers[rng.integers(len(flowers))]
            _flower(dr, N, x + 16, y, 13, tuple(c), (214, 176, 84))
    for y in (45, 230, 421):
        for x in range(0, N, 16):
            c = flowers[rng.integers(len(flowers))]
            _wrap_ellipse(dr, N, x + 8, y, 4, tuple(c))
    a = np.asarray(im, dtype=float)
    shard = rng.uniform(-0.09, 0.09, size=(N // 4, N // 4)).repeat(4, 0).repeat(4, 1)
    a = a * (1 + _cloud(rng, N, 48, 0.18) + shard)[..., None]
    h = np.asarray(im.convert("L"), dtype=float) / 255 + shard
    _save_maps(out, a, _height_to_normal(h * 3, 1.0))
    return out


# ====================================================================== 幾何
def plan(s, d):
    """十二凸角方形平面（每角兩次內折）：20 點，逆時針"""
    quad = [(s, s - 2 * d), (s - d, s - 2 * d), (s - d, s - d), (s - 2 * d, s - d), (s - 2 * d, s)]
    pts = []
    for q in range(4):
        c, sn = math.cos(q * math.pi / 2), math.sin(q * math.pi / 2)
        pts += [(x * c - y * sn, x * sn + y * c) for x, y in quad]
    return pts


class Prof:
    """塔身輪廓：一串 (s, z, 材質) 環；相鄰兩環之間的面使用前一環的材質"""

    def __init__(self):
        self.rings = []

    def add(self, s, z, mi):
        self.rings.append((s, z, mi))

    def tier(self, s, z0, h, body, band, lip=0.16):
        """一層疊澀：底部內凹頸 → 牆面 → 外凸線腳 → 頂面內收"""
        self.add(s - 0.10, z0, band)
        self.add(s - 0.10, z0 + 0.14 * h, band)
        self.add(s, z0 + 0.16 * h, body)
        self.add(s, z0 + 0.66 * h, band)
        self.add(s + lip, z0 + 0.70 * h, band)
        self.add(s + lip, z0 + 0.94 * h, band)
        self.add(s - 0.02, z0 + h, band)

    def curve(self, fn, z0, z1, n, mi):
        for k in range(n + 1):
            z = z0 + (z1 - z0) * k / n
            self.add(fn(z), z, mi)


class ThaiBuilder(AsiaBuilder):
    def loft(self, prof, cx, cy, notch=0.16, dmax=1.25, W=1.0):
        rings = []
        for s, z, mi in prof.rings:
            s *= W
            d = min(dmax, max(0.03, s * notch))
            rings.append(([self.V((cx + x, cy + y, z)) for x, y in plan(s, d)], mi))
        self.face(list(reversed(rings[0][0])), rings[0][1])
        for (a, mi), (c, _) in zip(rings, rings[1:]):
            n = len(a)
            for i in range(n):
                j = (i + 1) % n
                self.face([a[i], a[j], c[j], c[i]], mi)
        self.face(rings[-1][0], rings[-1][1])

    def turn(self, mi, profile, cx, cy, seg=16, smooth=True, cap=True):
        """旋轉體（自建頂點）"""
        rings = []
        for r, z in profile:
            if r < 1e-4:
                rings.append([self.V((cx, cy, z))])
            else:
                rings.append([self.V((cx + r * math.cos(TAU * i / seg), cy + r * math.sin(TAU * i / seg), z)) for i in range(seg)])
        for a, c in zip(rings, rings[1:]):
            if len(a) == 1:
                for i in range(seg):
                    self.face([a[0], c[i], c[(i + 1) % seg]], mi, smooth)
            elif len(c) == 1:
                for i in range(seg):
                    self.face([a[i], a[(i + 1) % seg], c[0]], mi, smooth)
            else:
                for i in range(seg):
                    j = (i + 1) % seg
                    self.face([a[i], a[j], c[j], c[i]], mi, smooth)
        if cap and len(rings[0]) > 1:
            self.face(list(reversed(rings[0])), mi)

    def bx(self, mi, size, center, M=None):
        """長方體（自建頂點，可帶矩陣）"""
        M = M or Matrix.Identity(4)
        sx, sy, sz = (v / 2 for v in size)
        cx, cy, cz = center
        p = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz), (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
        v = [self.V(M @ Vector((cx + a, cy + b, cz + c))) for a, b, c in p]
        for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
            self.face([v[i] for i in f], mi)

    def slab(self, mi, outline_xz, y0, y1, M):
        """XZ 平面輪廓（逆時針）沿 Y 擠出：用於尖拱山牆"""
        a = [self.V(M @ Vector((x, y0, z))) for x, z in outline_xz]
        c = [self.V(M @ Vector((x, y1, z))) for x, z in outline_xz]
        self.face(a, mi)
        self.face(list(reversed(c)), mi)
        n = len(a)
        for i in range(n):
            j = (i + 1) % n
            self.face([a[j], a[i], c[i], c[j]], mi)

    # ------------------------------------------------------------------ 佛塔
    def spire(self, cx, cy, z0, z1, r0, n, mi, gold, ball_z=None):
        """環節尖頂（ปล้องไฉน）＋針頂（ปลี）＋寶珠"""
        p = [(r0 * 1.15, z0), (r0 * 1.2, z0 + 0.25)]
        H = (z1 - z0) * 0.78
        z = z0 + 0.25
        for k in range(n):
            t = k / n
            r = r0 * (1 - 0.72 * t)
            h = H / n
            p += [(r * 0.86, z), (r * 1.08, z + 0.35 * h), (r * 1.04, z + 0.62 * h), (r * 0.84, z + h)]
            z += h
        rt = p[-1][0]
        p += [(rt * 0.95, z + 0.4), (rt * 0.6, z + (z1 - z) * 0.55), (rt * 0.35, z1 - 1.0), (0.0, z1 - 0.6)]
        self.turn(mi, p, cx, cy, seg=16)
        bz = z1 - 0.75
        self.turn(gold, [(0.0, bz - 0.3), (0.2, bz - 0.2), (0.27, bz), (0.2, bz + 0.2), (0.06, bz + 0.3), (0.04, z1 - 0.1), (0.0, z1)],
                  cx, cy, seg=12)

    def colonnade(self, cx, cy, z0, h, r, mi, dark, n=12):
        """寶座上方一圈小柱（เสาหาน）"""
        self.turn(dark, [(r * 0.68, z0), (r * 0.68, z0 + h)], cx, cy, seg=12, smooth=False)
        self.turn(mi, [(r * 1.08, z0 - 0.18), (r * 1.08, z0), (0.0, z0)], cx, cy, seg=16, smooth=False)
        self.turn(mi, [(r * 1.12, z0 + h), (r * 1.12, z0 + h + 0.2), (0.0, z0 + h + 0.2)], cx, cy, seg=16, smooth=False)
        w = r * TAU / n * 0.42
        for k in range(n):
            a = TAU * (k + 0.5) / n
            M = Matrix.Translation((cx, cy, 0)) @ Matrix.Rotation(a, 4, "Z")
            self.bx(mi, (w, w, h), (r * 0.9, 0, z0 + h / 2), M)

    def niche(self, cx, cy, q, s_face, k, body, frame, gold, door, z0, wk=1.0):
        """拱形神龕（ซุ้มคูหา）：凸出的龕身、金框紅門、層疊尖拱山牆（ซุ้มบันแถลง）與小尖頂"""
        M = Matrix.Translation((cx, cy, 0)) @ Matrix.Rotation(q * math.pi / 2, 4, "Z")
        yf = -s_face - 0.7 * k
        W, Hn = 4.4 * k * wk, 7.6 * k
        self.bx(body, (W, 2.0 * k, Hn), (0, yf + 1.0 * k, z0 + Hn / 2), M)
        for sx in (-1, 1):  # 兩側壁柱
            self.bx(body, (0.55 * k, 0.4 * k, Hn), (sx * (W / 2 - 0.27 * k), yf - 0.15 * k, z0 + Hn / 2), M)
        self.bx(frame, (W + 0.4 * k, 2.4 * k, 0.45 * k), (0, yf + 0.9 * k, z0 + 0.22 * k), M)  # 龕座線腳
        self.bx(frame, (W + 0.3 * k, 2.3 * k, 0.35 * k), (0, yf + 0.9 * k, z0 + Hn), M)       # 楣
        self.bx(gold, (1.9 * k, 0.16 * k, 3.6 * k), (0, yf - 0.06 * k, z0 + 1.0 * k + 1.8 * k), M)  # 金框
        self.bx(door, (1.15 * k, 0.12 * k, 2.95 * k), (0, yf - 0.16 * k, z0 + 1.15 * k + 1.47 * k), M)
        zt = z0 + Hn + 0.35 * k
        # 尖拱山牆：外層金邊、內層馬賽克，略呈火焰尖頂（兩側內凹曲線）
        for (wb, ht, y0, y1, mi) in ((W + 0.6 * k, 5.6 * k, yf - 0.05 * k, yf + 1.9 * k, frame),
                                     (W - 0.2 * k, 4.7 * k, yf - 0.25 * k, yf - 0.05 * k, body),
                                     (W - 1.3 * k, 3.2 * k, yf - 0.4 * k, yf - 0.25 * k, gold)):
            pts = [(-wb / 2, zt), (wb / 2, zt)]
            for i in range(1, 9):
                t = i / 9
                x = wb / 2 * (1 - t) ** 1.5
                pts.append((x, zt + ht * t))
            pts.append((0, zt + ht))
            for i in range(8, 0, -1):
                t = i / 9
                pts.append((-wb / 2 * (1 - t) ** 1.5, zt + ht * t))
            self.slab(mi, pts, y0, y1, M)
        self.turn(gold, [(0.0, zt + 5.2 * k), (0.16 * k, zt + 5.3 * k), (0.03 * k, zt + 7.0 * k), (0.0, zt + 7.1 * k)],
                  *(M @ Vector((0, yf + 0.8 * k, 0))).xy, seg=8)
        for sx in (-1, 1):  # 山牆兩端翹起的鴟尾狀飾件
            self.turn(gold, [(0.0, zt), (0.12 * k, zt + 0.1 * k), (0.02 * k, zt + 0.9 * k), (0.0, zt + 1.0 * k)],
                      *(M @ Vector((sx * (W / 2 + 0.15 * k), yf - 0.05 * k, 0))).xy, seg=6)

    def chedi(self, cx, cy, kind, body, band, gold, dark, door=None, H=42.0):
        k = H / 42.0
        P = Prof()
        if kind == "blue":
            # 方形台基
            P.add(8.6 * k, 0.0, band)
            P.add(8.6 * k, 0.9 * k, band)
            P.add(7.6 * k, 0.9 * k, band)
            # 下段陡收台座 z 0.9–6.5
            for i, (s, h) in enumerate(((7.3, 1.4), (6.95, 1.4), (6.6, 1.4), (6.3, 1.4))):
                P.tier(s * k, (0.9 + 1.4 * i) * k, h * k, body, band, lip=0.2 * k)
            # 主塔身（近乎垂直，四面神龕）z 6.5–14
            P.add(6.0 * k, 6.5 * k, body)
            P.add(5.75 * k, 13.6 * k, band)
            P.add(6.05 * k, 13.7 * k, band)
            P.add(6.05 * k, 14.1 * k, band)
            # 上段疊澀 z 14.1–20.5
            for i in range(9):
                P.tier((5.5 - 0.29 * i) * k, (14.1 + 0.711 * i) * k, 0.711 * k, band, band, lip=0.13 * k)
            # 鐘形塔身 z 20.5–25.6（下緣外撇、上緣圓肩）
            P.add(3.2 * k, 20.5 * k, band)
            P.add(3.2 * k, 20.75 * k, body)
            P.curve(lambda z: k * (3.05 - 1.1 * max(0.0, (z / k - 20.75) / 4.6) ** 1.25), 20.75 * k, 25.35 * k, 10, body)
            P.add(2.05 * k, 25.6 * k, band)
            # 寶座（บัลลังก์）
            P.add(1.75 * k, 25.6 * k, band)
            P.add(1.75 * k, 26.1 * k, band)
            P.add(2.0 * k, 26.2 * k, band)
            P.add(2.0 * k, 26.55 * k, band)
            P.add(1.5 * k, 26.6 * k, band)
            zc, rc, zs = 26.6, 1.45, 28.2
        else:
            P.add(8.4 * k, 0.0, band)
            P.add(8.4 * k, 0.9 * k, band)
            P.add(7.5 * k, 0.9 * k, band)
            sizes = (7.2, 6.75, 6.3, 5.85, 5.4, 4.95, 4.5, 4.05)
            for i, s in enumerate(sizes):
                P.tier(s * k, (0.9 + 1.55 * i) * k, 1.55 * k, body, band, lip=0.26 * k)
            zb = 0.9 + 1.55 * len(sizes)     # ≈ 13.3
            # 鐘形塔身：下緣外撇、腰身內凹，上收至肩部
            P.add(3.9 * k, zb * k, band)
            P.add(3.9 * k, (zb + 0.4) * k, band)
            P.add(3.7 * k, (zb + 0.45) * k, body)

            def bell(z):
                t = min(1.0, max(0.0, (z / k - zb - 0.45) / (22.0 - zb - 0.45)))
                return k * (2.05 + 1.65 * (1 - t) ** 1.7 + 0.32 * math.sin(math.pi * t) ** 1.5 * t)
            P.curve(bell, (zb + 0.45) * k, 22.0 * k, 12, body)
            P.add(2.3 * k, 22.0 * k, band)
            P.add(2.3 * k, 22.25 * k, band)
            P.add(2.05 * k, 22.3 * k, band)
            P.add(2.05 * k, 22.8 * k, band)
            P.add(2.4 * k, 22.9 * k, band)
            P.add(2.4 * k, 23.25 * k, band)
            P.add(1.55 * k, 23.3 * k, band)
            zc, rc, zs = 23.3, 1.55, 25.0
        W = 0.8
        self.loft(P, cx, cy, W=W)
        self.colonnade(cx, cy, zc * k, (zs - zc - 0.4) * k, rc * k * W, body, dark)
        self.spire(cx, cy, (zs - 0.2) * k, H, 1.3 * k * W, 28, body, gold)
        if door is not None:
            for q in range(4):
                self.niche(cx, cy, q, 6.0 * k * W, k, body, band, gold, door, 6.5 * k, wk=0.82)


# ====================================================================== 場景
def wat_pho(path):
    b = ThaiBuilder("WatPho", seed=12)
    fl_common = [(232, 228, 214), (222, 184, 70), (176, 44, 40), (56, 138, 92), (96, 146, 214)]
    mos = {
        "blue": gen_mosaic("blue4", (22, 34, 98), (150, 168, 76), [(232, 228, 214), (222, 190, 80), (196, 92, 110), (232, 228, 214), (90, 160, 120)], seed=3),
        "green": gen_mosaic("green4", (46, 104, 84), (196, 124, 70), [(232, 228, 214), (222, 184, 70), (176, 44, 40), (70, 100, 180), (206, 118, 66)], seed=4),
        "yellow": gen_mosaic("yellow4", (196, 150, 62), (92, 132, 92), [(236, 232, 216), (176, 44, 40), (70, 100, 180), (56, 138, 92), (150, 90, 40)], seed=5),
        "white": gen_mosaic("white4", (222, 218, 204), (122, 156, 108), [(222, 184, 70), (56, 138, 92), (96, 146, 214), (176, 64, 50), (150, 170, 120)], seed=6),
    }
    bands = {
        "blue": gen_band("blue4", (40, 34, 80), (88, 40, 60), fl_common, seed=7),
        "green": gen_band("green4", (110, 56, 46), (52, 104, 84), fl_common, seed=8),
        "yellow": gen_band("yellow4", (184, 132, 58), (150, 70, 44), fl_common, seed=9),
        "white": gen_band("white4", (220, 214, 198), (120, 156, 108), fl_common, seed=10),
    }
    M = {c: b.gtex(f"m_{c}", mos[c], tile=4.0, rough=0.32, normal=0.7) for c in mos}
    B = {c: b.gtex(f"b_{c}", bands[c], tile=1.4, rough=0.35, normal=0.6) for c in bands}
    gold = b.color("gold", "#c99a3c", rough=0.3, metal=0.7)
    dark = b.color("dark", "#2a2622", rough=0.8)
    door = b.color("door_red", "#a3161b", rough=0.5)
    wall = b.ptex("wall", "plastered_wall_04", tile=4.0, tint="#ece9e2", rough=0.85, normal=0.3)
    roof = b.gtex("roof", gen_tiles("th_orange", (212, 112, 40), kind="thai", n_ch=14, n_rows=14, seed=9), tile=2.4, rough=0.4,
                  normal=0.8, oriented=True)
    roof_g = b.color("roof_green", "#2f6e46", rough=0.5)
    band_r = b.color("band_red", "#a9332a", rough=0.6)
    band_w = b.color("band_white", "#e6e2d8", rough=0.6)
    brick = b.gtex("brick", gen_paving("th_brick", (128, 84, 72), bw=10, bh=20, seed=21, joint=(0.75, 0.72, 0.7)), tile=3.0, rough=0.9,
                   normal=0.5)
    lawn = b.ptex("lawn", "grass_ground", tile=4.0, tint="#5f7f36", rough=0.95, normal=0.4)
    stone = b.ptex("stone", "marble_01", tile=3.0, tint="#cfcac0", rough=0.6, normal=0.3)
    leaf = b.color("leaf", "#3d6a2c", rough=0.85)
    leaf2 = b.color("leaf2", "#55803a", rough=0.85)
    trunk = b.color("trunk", "#6b5a48", rough=0.9)

    # ---------------- 地面
    b.bx(brick, (130.0, 175.0, 0.4), (-15.0, 5.0, -0.2))

    # ---------------- 四大佛塔
    b.chedi(0.0, 0.0, "blue", M["blue"], B["blue"], gold, dark, door=door)
    b.chedi(-24.5, 6.0, "std", M["green"], B["green"], gold, dark)
    b.chedi(-15.0, 48.0, "std", M["yellow"], B["yellow"], gold, dark)
    b.chedi(-34.0, 40.0, "std", M["white"], B["white"], gold, dark)

    # ---------------- 迴廊（白牆＋雙層橘瓦屋頂、綠邊、紅白飾帶）
    def gallery(x0, y0, x1, y1, depth=5.0, h=3.0):
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        T = Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, 0)) @ Matrix.Rotation(ang, 4, "Z")
        rot = math.degrees(ang) + 90
        hd = depth / 2
        b.bx(stone, (L + 0.6, depth + 0.6, 0.35), (0, 0, 0.175), T)
        b.bx(wall, (L, depth, h), (0, 0, 0.35 + h / 2), T)
        zt = 0.35 + h
        b.bx(band_r, (L + 0.06, depth + 0.06, 0.22), (0, 0, zt - 0.5), T)
        # 下層披簷：從牆頂向外下斜
        for sy in (-1, 1):
            o = [T @ Vector((-L / 2 - 0.3, sy * (hd + 1.1), zt - 0.35)), T @ Vector((L / 2 + 0.3, sy * (hd + 1.1), zt - 0.35)),
                 T @ Vector((L / 2 + 0.3, sy * (hd - 0.2), zt + 0.5)), T @ Vector((-L / 2 - 0.3, sy * (hd - 0.2), zt + 0.5))]
            vs = [b.V(p) for p in (o if sy < 0 else list(reversed(o)))]
            b.face(vs, roof, rot=rot)
            b.bx(roof_g, (L + 0.7, 0.25, 0.18), (0, sy * (hd + 1.15), zt - 0.38), T)
        # 披簷與主屋頂之間的紅白飾帶
        b.bx(band_w, (L + 0.4, depth - 0.2, 0.25), (0, 0, zt + 0.62), T)
        b.bx(band_r, (L + 0.4, depth - 0.3, 0.2), (0, 0, zt + 0.85), T)
        # 主屋頂（兩坡）
        zr, ridge = zt + 0.95, zt + 2.6
        for sy in (-1, 1):
            o = [T @ Vector((-L / 2 - 0.3, sy * (hd + 0.2), zr)), T @ Vector((L / 2 + 0.3, sy * (hd + 0.2), zr)),
                 T @ Vector((L / 2 + 0.3, 0, ridge)), T @ Vector((-L / 2 - 0.3, 0, ridge))]
            vs = [b.V(p) for p in (o if sy < 0 else list(reversed(o)))]
            b.face(vs, roof, rot=rot)
            b.bx(roof_g, (L + 0.7, 0.3, 0.16), (0, sy * (hd + 0.25), zr - 0.05), T)
        # 屋脊、兩端山牆封板
        b.bx(roof_g, (L + 0.7, 0.4, 0.3), (0, 0, ridge + 0.05), T)
        for sx in (-1, 1):
            b.slab(wall, [(-hd - 0.2, zr), (hd + 0.2, zr), (0, ridge)], sx * (L / 2 + 0.25) - 0.1, sx * (L / 2 + 0.25) + 0.1,
                   T @ Matrix.Rotation(math.pi / 2, 4, "Z"))

    # 南側長迴廊（藍塔院與三塔院共用），其餘迴廊夾在其間，避免牆面重疊
    gallery(-62.5, -16.0, 40.0, -16.0)
    gallery(-14.0, -13.5, -14.0, 13.5)
    gallery(14.0, -13.5, 14.0, 13.5)
    gallery(-16.5, 16.0, 16.5, 16.0)
    gallery(-60.0, -13.5, -60.0, 82.5)
    gallery(-62.5, 85.0, -15.5, 85.0)
    gallery(-4.0, 20.5, -4.0, 82.5)
    gallery(-42.0, -18.5, -42.0, -40.0)
    # 遠處的佛殿（參考照右側）：南北向，山牆朝南
    b.bx(wall, (14.0, 30.0, 9.0), (36.0, 28.0, 4.5))
    for sx in (-1, 1):
        o = [Vector((36.0 + sx * 8.0, 12.0, 8.6)), Vector((36.0 + sx * 8.0, 44.0, 8.6)), Vector((36.0, 44.0, 17.5)), Vector((36.0, 12.0, 17.5))]
        b.face([b.V(p) for p in (o if sx > 0 else list(reversed(o)))], roof, rot=0)
    b.slab(gold, [(-8.4, 8.4), (8.4, 8.4), (0.0, 17.9)], -0.35, 0.0, Matrix.Translation((36.0, 12.0, 0)))
    b.slab(door, [(-6.8, 9.1), (6.8, 9.1), (0.0, 16.4)], -0.5, -0.35, Matrix.Translation((36.0, 12.0, 0)))
    b.slab(gold, [(-3.5, 10.0), (3.5, 10.0), (0.0, 13.8)], -0.6, -0.5, Matrix.Translation((36.0, 12.0, 0)))
    for sx in (-1, 1):
        b.turn(gold, [(0.0, 8.4), (0.25, 8.6), (0.08, 10.6), (0.0, 10.8)], 36.0 + sx * 8.2, 11.8, seg=6)
    b.turn(gold, [(0.0, 17.6), (0.25, 17.8), (0.08, 20.0), (0.0, 20.2)], 36.0, 11.8, seg=6)

    # ---------------- 前景庭院：草坪花壇、石燈柱、造型樹、棕櫚
    b.bx(stone, (15.0, 7.6, 0.4), (-2.0, -24.5, 0.2))
    b.bx(lawn, (14.4, 7.0, 0.5), (-2.0, -24.5, 0.25))
    for sx in (-9.6, 5.6):
        b.bx(stone, (0.9, 0.9, 1.5), (sx, -29.0, 0.75))
        b.bx(stone, (1.1, 1.1, 0.2), (sx, -29.0, 1.6))
        b.turn(stone, [(0.5, 1.7), (0.42, 2.0), (0.1, 2.5), (0.0, 2.6)], sx, -29.0, seg=8, smooth=False)
    for (x, y) in ((-8.0, -22.5), (4.0, -22.5)):
        b.turn(trunk, [(0.12, 0.5), (0.1, 2.2)], x, y, seg=6)
        for (dx, dz, r) in ((0.0, 1.0, 0.7), (0.6, 1.9, 0.6), (-0.4, 2.6, 0.55), (0.1, 3.2, 0.45)):
            b.blob(leaf, (x + dx, y, dz), r * 1.2, r, r * 0.85, lump=0.25, sub=2)
    for i, (x, y, h) in enumerate(((-6.0, -21.6, 5.5), (-3.5, -21.4, 6.3), (0.5, -21.8, 5.8), (2.5, -21.3, 4.8), (-1.5, -22.4, 4.0))):
        b.turn(trunk, [(0.17, 0.5), (0.12, h)], x, y, seg=6)
        for f in range(14):
            a = TAU * f / 14 + i
            L = 1.9 + 0.6 * ((f * 7) % 5) / 4
            up = 0.4 + 0.8 * ((f * 3) % 4) / 3
            pts = [(x + math.cos(a) * L * t, y + math.sin(a) * L * t, h + up * t - 1.9 * t ** 2.2) for t in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)]
            b.sweep(pts, 0.32, 0.03, leaf2 if f % 2 else leaf)
    b.export_glb(path)
