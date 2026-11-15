"""forbidden-city 北京故宮 太和殿與太和殿廣場 寫實模型（公尺；+X 東、+Y 北）

- 太和殿：面闊 11 間（約 64 m）、進深 5 間（約 37 m），重簷廡殿頂，黃琉璃瓦，殿高約 26.9 m（連台基 35 m）
- 坐落於三層漢白玉須彌座台基（三台，總高約 8.1 m），每層有欄板望柱；南面中央三出陛（中為御路石）
- 三台上另有中和殿（方形單簷攢尖）與保和殿（重簷歇山），北側在主相機後方
- 廣場：磚墁地面＋中央御路；東體仁閣、西弘義閣（台基上兩層樓閣，單簷歇山）、紅牆廊廡、隨牆門
- 色彩：朱紅柱與牆、青綠旋子彩畫、金黃琉璃瓦、漢白玉台基、灰褐色廣場磚

本檔另提供中式殿堂工具（歇山頂、斗栱帶、隔扇門），供德壽宮模組共用。
"""

import math
import os

import numpy as np
from mathutils import Matrix, Vector

from lib import TAU
from buildings.kinkakuji import GEN, AsiaBuilder, _cloud, _height_to_normal, _save_maps, gen_tiles

# (目標點, 方位角, 仰角, 距離, 焦距)：參考照自太和殿廣場南側、中軸略偏東，平視
CAMERA = ((4.0, 0.0, 10.0), 3.0, -2.2, 200.0, 36)


# ====================================================================== 程式貼圖
def gen_paving(name, color, seed=4, bw=10, bh=20, joint=(0.72, 0.72, 0.72), herring=False):
    """磚墁地面（u, v 平面）：bw×bh 塊錯縫磚，貼圖代表一個循環"""
    out = os.path.join(GEN, f"cn_pave_{name}")
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return out
    N = 1024
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    RH = N / bh
    row = np.floor(yy / RH).astype(int)
    RW = N / bw
    sx = xx + (row % 2) * RW / 2
    col = np.floor(sx / RW).astype(int)
    lx, ly = sx % RW, yy % RH
    jt = (lx < 3) | (ly < 3)
    tone = rng.uniform(-0.10, 0.10, size=(bh + 2, bw + 2))[row % (bh + 2), col % (bw + 2)]
    lum = 1 + tone + _cloud(rng, N, 64, 0.12) + _cloud(rng, N, 4, 0.10)
    base = np.array(color, float)
    diff = base[None, None] * lum[..., None]
    diff = np.where(jt[..., None], diff * np.array(joint)[None, None], diff)
    h = np.where(jt, 0.0, 1.0) + _cloud(rng, N, 4, 0.2)
    _save_maps(out, diff, _height_to_normal(h * 2, 1.0), size=512)
    return out


def gen_lattice(name, frame, slat, seed=2):
    """隔扇門心：菱花格（斜交格）＋框，u 水平、v 垂直；貼圖 1 m 見方"""
    out = os.path.join(GEN, f"cn_lattice_{name}")
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return out
    N = 512
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    P = N / 6
    d1 = np.abs(((xx + yy) % P) - P / 2)
    d2 = np.abs(((xx - yy) % P) - P / 2)
    d3 = np.abs((xx % P) - P / 2)
    m = (d1 < 5) | (d2 < 5) | (d3 < 4)
    holes = ~m
    fr, sl = np.array(frame, float), np.array(slat, float)
    diff = np.where(m[..., None], sl[None, None], fr[None, None] * 0.35)
    h = np.where(m, 1.0, 0.0)
    _save_maps(out, diff, _height_to_normal(h * 3, 1.0))
    return out


def gen_caihua(name, seed=5):
    """旋子彩畫額枋：青綠相間的旋花、金線；u 水平、v 垂直，貼圖 2 m 見方（內含上下兩條枋）"""
    out = os.path.join(GEN, f"cn_caihua_{name}")
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return out
    N = 512
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:N, 0:N].astype(float)
    blue = np.array((38, 84, 120), float)
    green = np.array((48, 112, 92), float)
    gold = np.array((214, 170, 80), float)
    band = (yy // (N / 4)).astype(int)
    diff = np.where((band % 2 == 0)[..., None], blue[None, None], green[None, None])
    # 旋花（圓形花紋）
    P = N / 4
    cx = (xx % P) - P / 2
    cy = (yy % P) - P / 2
    r = np.sqrt(cx * cx + cy * cy)
    ring = (np.abs(r - P * 0.32) < 3) | (np.abs(r - P * 0.18) < 3)
    diff = np.where(ring[..., None], np.array((235, 235, 225), float)[None, None], diff)
    gl = (yy % P < 4) | (np.abs((xx % (N / 2)) - 2) < 3)
    diff = np.where(gl[..., None], gold[None, None], diff)
    diff = diff * (1 + _cloud(rng, N, 32, 0.12))[..., None]
    _save_maps(out, diff)
    return out


# ====================================================================== 中式殿堂工具
class CnBuilder(AsiaBuilder):
    def mats_cn(self, roof_rgb=(186, 124, 36), roof_name="cn_yellow3"):
        m = {}
        m["tile"] = self.gtex("tile", gen_tiles(roof_name, roof_rgb, kind="kawara", n_ch=10, n_rows=10, seed=7), tile=3.2,
                              rough=0.35, normal=0.8, oriented=True)
        m["ridge"] = self.color("ridge", "#b97f28", rough=0.35)
        m["red"] = self.ptex("redwall", "plastered_wall_04", tile=4.0, tint="#a83a2c", rough=0.85, normal=0.4)
        m["col"] = self.color("column", "#962a20", rough=0.55)
        m["door"] = self.gtex("door", gen_lattice("red", (150, 46, 34), (176, 70, 46)), tile=1.0, rough=0.6, normal=0.5)
        m["cai"] = self.gtex("caihua", gen_caihua("a"), tile=2.0, rough=0.6, normal=0.0)
        m["blue"] = self.color("blue", "#2c5a78", rough=0.6)
        m["green"] = self.color("green", "#3c7a5e", rough=0.6)
        m["gold"] = self.color("gilt", "#d9ad4f", rough=0.35, metal=0.4)
        m["marble"] = self.ptex("marble", "marble_01", tile=3.0, tint="#d4c7ab", rough=0.6, normal=0.4)
        m["marble_d"] = self.ptex("marble_d", "marble_01", tile=3.0, tint="#bcae92", rough=0.65, normal=0.4)
        m["dark"] = self.color("dark", "#2a1712", rough=0.9)
        return m

    # -------------------------------------------------- 歇山／廡殿屋頂
    def cn_roof(self, M, cx, cy, eave, ze, wall, zw, kind, zr, ridge_len=None, U=0.9, P=0.6, rows=10, gamma=0.55,
                hip_w=0.5, hip_h=0.45, ridge_h=1.2, beasts=True):
        """kind: 'hip' 廡殿、'hipgable' 歇山、'pyramid' 攢尖、'skirt' 腰簷（重簷下層）。
        eave=(A,B) 簷口半寬半深、ze 簷口高；wall=(Aw,Bw) 牆線、zw 牆線高（簷下天花回接處）；zr 屋脊高（skirt 時為上緣高）"""
        A, B = eave
        Aw, Bw = wall
        kw = dict(center=(cx, cy), U=U, P=P, K=(22, 14), rows=rows, soffit=M["blue"], wall=(Aw, Bw, zw), thick=0.45,
                  fascia=M["ridge"], gamma=gamma, corner_len=min(A, B) * 0.55)
        if kind == "skirt":
            top = (Aw + 0.3, Bw + 0.3)
            self.roof_skirt(M["tile"], eave, top, ze, zr, hips=M["ridge"], hip_w=hip_w, hip_h=hip_h, **kw)
            return
        if kind == "hip":
            rl = ridge_len if ridge_len is not None else max(0.5, A - B)
            self.roof_skirt(M["tile"], eave, (rl, 0.25), ze, zr, hips=M["ridge"], hip_w=hip_w, hip_h=hip_h, **kw)
            self.box_base(M["ridge"], (2 * rl + 0.6, 0.9, ridge_h), (cx, cy, zr - 0.2))
            for s in (-1, 1):  # 正吻
                h = ridge_h * 2.6
                self.box_base(M["ridge"], (0.9, 0.95, h), (cx + s * (rl + 0.1), cy, zr - 0.2))
                self.box_base(M["ridge"], (0.6, 1.0, h * 0.35), (cx + s * (rl - 0.45), cy, zr + h * 0.45))
                self.box_base(M["ridge"], (0.35, 0.5, h * 0.3), (cx + s * (rl + 0.55), cy, zr + h * 0.55))
            return
        if kind == "pyramid":
            self.roof_skirt(M["tile"], eave, (0.2, 0.2), ze, zr, hips=M["ridge"], hip_w=hip_w, hip_h=hip_h, **kw)
            self.lathe(M["gold"], [(0, 0), (0.9, 0), (1.0, 0.4), (0.7, 1.0), (0.85, 1.6), (0.5, 2.3), (0.25, 3.0), (0, 3.4)],
                       (cx, cy, zr - 0.3), seg=12, smooth=True)
            return
        # 歇山：下段四坡收至山花位置，上段兩坡＋山花
        rl = ridge_len if ridge_len is not None else A * 0.62
        zm = ze + (zr - ze) * 0.45
        Bm = B * 0.5
        self.roof_skirt(M["tile"], eave, (rl + 0.4, Bm), ze, zm, hips=M["ridge"], hip_w=hip_w, hip_h=hip_h, **kw)
        # 上段：兩坡（以三角稜柱表示，坡面瓦材質），山花（紅）
        h = zr - zm
        self.tri_prism(M["tile"], 2 * rl + 0.8, 2 * Bm + 0.6, h + 0.2, (cx, cy, zm - 0.2))
        for s in (-1, 1):
            self.tri_prism(M["red"], 0.3, 2 * Bm - 0.4, h - 0.3, (cx + s * (rl + 0.1), cy, zm - 0.1))
            self.tri_prism(M["gold"], 0.12, 2 * Bm - 1.0, h - 0.9, (cx + s * (rl + 0.3), cy, zm + 0.2))
        self.box_base(M["ridge"], (2 * rl + 1.2, 0.8, ridge_h), (cx, cy, zr - 0.15))
        for s in (-1, 1):
            hh = ridge_h * 2.3
            self.box_base(M["ridge"], (0.8, 0.85, hh), (cx + s * (rl + 0.3), cy, zr - 0.15))
            self.box_base(M["ridge"], (0.5, 0.9, hh * 0.3), (cx + s * (rl - 0.2), cy, zr + hh * 0.5))
            # 垂脊（山花兩側沿坡而下）
            for t in (-1, 1):
                p0 = Vector((cx + s * (rl + 0.45), cy, zr))
                p1 = Vector((cx + s * (rl + 0.45), cy + t * (Bm + 0.35), zm - 0.1))
                self.sweep([p0, p1], 0.45, 0.4, M["ridge"])

    # -------------------------------------------------- 殿身
    def cn_body(self, M, cx, cy, z0, xs, ys, h_col, r_col=0.5, front="doors", sides="wall", back="wall",
                open_porch=False, end_wall_bays=1, beam_h=1.4):
        """柱網 xs × ys（中心座標的偏移），四周柱、牆或隔扇；柱頂額枋彩畫帶；回傳牆頂高"""
        X0, X1, Y0, Y1 = xs[0], xs[-1], ys[0], ys[-1]
        # 柱
        for i, x in enumerate(xs):
            for j, y in enumerate(ys):
                if i in (0, len(xs) - 1) or j in (0, len(ys) - 1):
                    self.cyl(M["col"], r_col, r_col * 0.92, h_col, (cx + x, cy + y, z0), seg=12, smooth=True)
                    self.cyl(M["marble"], r_col * 1.45, r_col * 1.3, 0.25, (cx + x, cy + y, z0), seg=12)

        def fill(p0, p1, kind, inset):
            x0, y0 = p0
            x1, y1 = p1
            L = math.hypot(x1 - x0, y1 - y0)
            ang = math.atan2(y1 - y0, x1 - x0)
            nx, ny = math.sin(ang), -math.cos(ang)
            mx, my = (x0 + x1) / 2 - nx * inset, (y0 + y1) / 2 - ny * inset
            R = Matrix.Translation((cx + mx, cy + my, 0)) @ Matrix.Rotation(ang, 4, "Z")
            w = L - 2 * r_col * 0.9
            hb = h_col - beam_h
            if kind == "wall":
                self.place(lambda: self.box_base(M["red"], (w + 0.1, 0.7, hb), (0, 0, z0)), R)
                self.place(lambda: self.box_base(M["marble_d"], (w + 0.12, 0.75, 1.0), (0, 0, z0)), R)
            elif kind == "doors":
                self.place(lambda: self.box_base(M["door"], (w, 0.25, hb), (0, 0, z0)), R)
                self.place(lambda: self.box_base(M["col"], (w + 0.05, 0.3, hb * 0.28), (0, 0, z0)), R)
                n = 4 if w > 3.5 else 2
                for k in range(n + 1):
                    u = -w / 2 + w * k / n
                    self.place(lambda u=u: self.box_base(M["col"], (0.16, 0.32, hb), (u, 0, z0)), R)
                self.place(lambda: self.box_base(M["col"], (w, 0.32, 0.25), (0, 0, z0 + hb * 0.62)), R)
                self.place(lambda: self.box_base(M["col"], (w, 0.32, 0.25), (0, 0, z0 + hb - 0.25)), R)
                self.place(lambda: self.box_base(M["gold"], (w * 0.25, 0.36, 0.12), (0, 0, z0 + hb * 0.62 + 0.06)), R)
            elif kind == "window":
                self.place(lambda: self.box_base(M["red"], (w + 0.1, 0.6, hb * 0.35), (0, 0, z0)), R)
                self.place(lambda: self.box_base(M["door"], (w, 0.25, hb * 0.65), (0, 0, z0 + hb * 0.35)), R)

        inset_f = 1.8 if open_porch else 0.0
        nb = len(xs) - 1
        for i in range(nb):  # 南（前）
            k = front if (end_wall_bays <= i < nb - end_wall_bays) else "wall"
            fill((xs[i], Y0), (xs[i + 1], Y0), k, inset_f if k != "wall" else 0.0)
        for i in range(nb):  # 北
            fill((xs[nb - i], Y1), (xs[nb - i - 1], Y1), back if back != "doors" or (end_wall_bays <= i < nb - end_wall_bays) else "wall", 0.0)
        for j in range(len(ys) - 1):
            fill((X1, ys[j]), (X1, ys[j + 1]), sides, 0.0)
            fill((X0, ys[len(ys) - 1 - j]), (X0, ys[len(ys) - 2 - j]), sides, 0.0)
        # 額枋彩畫帶＋平板枋
        zt = z0 + h_col
        W, D = X1 - X0, Y1 - Y0
        mx, my = cx + (X0 + X1) / 2, cy + (Y0 + Y1) / 2
        self.box_base(M["cai"], (W + 0.2, D + 0.2, beam_h), (mx, my, zt - beam_h))
        self.box_base(M["green"], (W + 0.5, D + 0.5, 0.3), (mx, my, zt))
        return zt + 0.3

    def dougong(self, M, cx, cy, W, D, z, h=1.1, spacing=1.6, out=0.9):
        """斗栱帶：沿四周排列的斗栱（簡化為三層出挑木塊，青綠相間）"""
        self.box_base(M["blue"], (W + 0.3, D + 0.3, h), (cx, cy, z))
        for (L, horiz, s) in ((W, True, -1), (W, True, 1), (D, False, -1), (D, False, 1)):
            n = max(2, int(L / spacing))
            for k in range(n + 1):
                t = -L / 2 + L * k / n
                for lv in range(3):
                    o = 0.15 + out * (lv + 1) / 3
                    sz = 0.45 + 0.25 * lv
                    mi = M["green"] if lv % 2 == 0 else M["blue"]
                    if horiz:
                        self.box_base(mi, (sz, o * 2, h / 3), (cx + t, cy + s * (D / 2), z + h * lv / 3))
                    else:
                        self.box_base(mi, (o * 2, sz, h / 3), (cx + s * (W / 2), cy + t, z + h * lv / 3))
        self.box_base(M["cai"], (W + 2 * out + 0.4, D + 2 * out + 0.4, 0.3), (cx, cy, z + h))

    def balustrade(self, M, pts, z, h=1.2, spacing=1.5, closed=True, skip=None):
        """漢白玉欄桿：望柱（帶柱頭）＋欄板；pts 為逆時針多邊形"""
        n = len(pts)
        for i in range(n if closed else n - 1):
            p0, p1 = Vector((*pts[i], 0)), Vector((*pts[(i + 1) % n], 0))
            L = (p1 - p0).length
            ang = math.atan2(p1.y - p0.y, p1.x - p0.x)
            k = max(1, int(round(L / spacing)))
            for j in range(k):
                a = p0 + (p1 - p0) * (j / k)
                c = p0 + (p1 - p0) * ((j + 0.5) / k)
                if skip and skip(c.x, c.y):
                    continue
                self.box_base(M["marble"], (0.24, 0.24, h), (a.x, a.y, z))
                self.box_base(M["marble"], (0.3, 0.3, 0.35), (a.x, a.y, z + h))
                self.place(lambda L=L, k=k: self.box_base(M["marble"], (L / k - 0.26, 0.14, h * 0.72), (0, 0, z + 0.05)),
                           Matrix.Translation((c.x, c.y, 0)) @ Matrix.Rotation(ang, 4, "Z"))


def stairs(b, mi, x, y0, y1, z0, z1, w, steps=None, ramp_mi=None, ramp_w=0.0):
    """往南下的階梯：從 (x, y1, z1) 下到 (x, y0, z0)；中央可有御路石（斜坡板）"""
    n = steps or max(3, int((z1 - z0) / 0.16))
    for k in range(n):
        t = k / n
        zz = z0 + (z1 - z0) * (k + 1) / n
        yy = y0 + (y1 - y0) * t
        b.box_base(mi, (w, y1 - yy, (z1 - z0) / n), (x, (yy + y1) / 2, zz - (z1 - z0) / n))
    if ramp_mi is not None and ramp_w > 0:
        # 御路：中央斜面石板
        L = math.hypot(y1 - y0, z1 - z0)
        ang = math.atan2(z1 - z0, y1 - y0)
        b.place(lambda: b.box(ramp_mi, (ramp_w, L, 0.35), (0, 0, 0)),
                Matrix.Translation((x, (y0 + y1) / 2, (z0 + z1) / 2 + 0.2)) @ Matrix.Rotation(ang, 4, "X"))
    # 兩側垂帶石
    for s in (-1, 1):
        L = math.hypot(y1 - y0, z1 - z0)
        ang = math.atan2(z1 - z0, y1 - y0)
        b.place(lambda: b.box(mi, (0.6, L, 0.9), (0, 0, 0)),
                Matrix.Translation((x + s * (w / 2 + 0.3), (y0 + y1) / 2, (z0 + z1) / 2 + 0.25)) @ Matrix.Rotation(ang, 4, "X"))


# ====================================================================== 故宮
def forbidden_city(path):
    b = CnBuilder("ForbiddenCity", seed=8)
    M = b.mats_cn()
    pave = b.gtex("pave", gen_paving("square3", (112, 101, 90), bw=8, bh=16), tile=4.0, rough=0.9, normal=0.5)
    slab = b.gtex("slab", gen_paving("slab2", (146, 138, 126), bw=2, bh=4, seed=9), tile=4.0, rough=0.8, normal=0.4)

    # ---------------- 廣場地面（矩形；中央御路）
    SX, SY0, SY1 = 105.0, -215.0, 210.0
    b.box_base(pave, (2 * SX + 30, SY1 - SY0, 0.6), (0, (SY0 + SY1) / 2, -0.6))
    b.box_base(slab, (8.0, -60 - SY0, 0.06), (0, (SY0 - 60) / 2, 0.0))
    for s in (-1, 1):
        b.box_base(slab, (1.0, -60 - SY0, 0.07), (s * 5.2, (SY0 - 60) / 2, 0.0))

    # ---------------- 三台（三層漢白玉台基，前端有月台）
    tiers = [  # (前段半寬, 南緣, 寬段起點, 寬段半寬, 北緣, z0, z1)
        (47.0, -64.0, -30.0, 64.0, 196.0, 0.0, 2.75),
        (43.0, -58.0, -26.0, 59.0, 190.0, 2.75, 5.45),
        (39.0, -52.0, -22.0, 54.0, 184.0, 5.45, 8.13),
    ]

    def outline(hf, y0, yb, hw, y1, d=0.0):
        return [(-hf - d, y0 - d), (hf + d, y0 - d), (hf + d, yb - d), (hw + d, yb - d), (hw + d, y1 + d), (-hw - d, y1 + d),
                (-hw - d, yb - d), (-hf - d, yb - d)]
    for (hf, y0, yb, hw, y1, z0, z1) in tiers:
        b.prism(M["marble_d"], outline(hf, y0, yb, hw, y1), z0, z1 - z0 - 0.36)
        b.prism(M["marble"], outline(hf, y0, yb, hw, y1, 0.25), z0 + 0.15, 0.25)
        b.prism(M["marble"], outline(hf, y0, yb, hw, y1, 0.25), z1 - 0.36, 0.36)
        pts = outline(hf, y0, yb, hw, y1, -0.3)
        b.balustrade(M, pts, z1, h=1.15, spacing=1.5,
                     skip=lambda x, y, y0=y0, y1=y1: (abs(x) < 11 and abs(y - y0) < 2) or (abs(abs(x) - 30) < 3.5 and abs(y - y0) < 2)
                     or (abs(x) < 9 and abs(y - y1) < 2))
    # 南面階梯：中央三出陛（帶御路）、兩側各一
    for k, (hf, y0, yb, hw, y1, z0, z1) in enumerate(tiers):
        run = (z1 - z0) / 0.16 * 0.32
        stairs(b, M["marble"], 0, y0 - run, y0 + 0.1, z0, z1, 7.0, ramp_mi=M["marble_d"], ramp_w=3.2)
        for s in (-1, 1):
            stairs(b, M["marble"], s * 8.2, y0 - run, y0 + 0.1, z0, z1, 3.2)
            stairs(b, M["marble"], s * 30, y0 - run, y0 + 0.1, z0, z1, 5.0)
    ZT = 8.13

    # ---------------- 太和殿
    xs = [-30.0 + 60.0 * i / 11 for i in range(12)]
    ys = [-16.5 + 33.0 * j / 5 for j in range(6)]
    b.box_base(M["marble"], (64.0, 37.5, 0.5), (0, 0, ZT))
    Z0 = ZT + 0.5
    zt = b.cn_body(M, 0, 0, Z0, xs, ys, 9.0, r_col=0.53, front="doors", sides="wall", back="doors", end_wall_bays=1)
    # 下簷斗栱、下簷（腰簷）
    b.dougong(M, 0, 0, 60.4, 33.4, zt, h=1.2)
    zd = zt + 1.5
    UW, UD = 27.0, 13.6  # 上層殿身半寬、半深
    b.cn_roof(M, 0, 0, (34.0, 20.8), zd, (30.6, 17.0), zd - 0.6, "skirt", zd + 3.0, U=0.9, P=0.7, rows=6, hip_w=0.45, hip_h=0.4)
    # 上層殿身（短柱、彩畫、斗栱）＋匾
    b.box_base(M["red"], (2 * UW, 2 * UD, 1.8), (0, 0, zd + 2.0))
    b.box_base(M["cai"], (2 * UW + 0.2, 2 * UD + 0.2, 1.0), (0, 0, zd + 2.8))
    b.dougong(M, 0, 0, 2 * UW, 2 * UD, zd + 3.8, h=0.9)
    b.box_base(M["blue"], (3.0, 0.3, 3.6), (0, -UD - 1.6, zd + 1.6))
    b.box_base(M["gold"], (3.4, 0.25, 4.0), (0, -UD - 1.5, zd + 1.4))
    zu = zd + 4.9
    b.cn_roof(M, 0, 0, (UW + 5.4, UD + 5.2), zu, (UW + 0.4, UD + 0.4), zu - 0.6, "hip", zu + 10.8, ridge_len=17.5,
              U=1.1, P=0.8, rows=12, gamma=0.6, hip_w=0.55, hip_h=0.5, ridge_h=1.5)

    # ---------------- 中和殿（方形攢尖）、保和殿（重簷歇山）
    cy = 62.0
    b.box_base(M["marble"], (26, 26, 0.5), (0, cy, ZT))
    xz = [-10.5 + 21 * i / 5 for i in range(6)]
    zt2 = b.cn_body(M, 0, cy, Z0, xz, xz, 6.5, r_col=0.4, front="doors", sides="doors", back="doors", end_wall_bays=1, beam_h=1.1)
    b.dougong(M, 0, cy, 21.4, 21.4, zt2, h=0.8, spacing=1.5, out=0.7)
    b.cn_roof(M, 0, cy, (15.2, 15.2), zt2 + 1.1, (11.3, 11.3), zt2 + 0.6, "pyramid", zt2 + 9.5, U=0.7, P=0.5, rows=10, gamma=0.55)
    cy = 120.0
    b.box_base(M["marble"], (52, 26, 0.5), (0, cy, ZT))
    xb = [-23.0 + 46 * i / 9 for i in range(10)]
    yb = [-10.0 + 20 * j / 5 for j in range(6)]
    zt3 = b.cn_body(M, 0, cy, Z0, xb, yb, 7.5, r_col=0.45, front="doors", sides="wall", back="doors", end_wall_bays=1, beam_h=1.2)
    b.dougong(M, 0, cy, 46.4, 20.4, zt3, h=0.9)
    zd3 = zt3 + 1.2
    b.cn_roof(M, 0, cy, (27.0, 14.2), zd3, (23.6, 10.6), zd3 - 0.5, "skirt", zd3 + 2.4, U=0.7, P=0.5, rows=6, hip_w=0.4, hip_h=0.35)
    b.box_base(M["red"], (40, 16, 2.6), (0, cy, zd3 + 1.6))
    b.dougong(M, 0, cy, 40, 16, zd3 + 4.2, h=0.8)
    b.cn_roof(M, 0, cy, (24.5, 12.4), zd3 + 5.2, (20.4, 8.4), zd3 + 4.7, "hipgable", zd3 + 12.0, ridge_len=14.0,
              U=0.9, P=0.6, rows=10)

    # ---------------- 紅牆與隨牆門（太和殿兩側接東西廡）
    def red_wall(x0, y0, x1, y1, h=7.0, t=1.4):
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        R = Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, 0)) @ Matrix.Rotation(ang, 4, "Z")
        b.place(lambda: b.box_base(M["red"], (L, t, h), (0, 0, 0)), R)
        b.place(lambda: b.box_base(M["marble_d"], (L + 0.05, t + 0.1, 0.8), (0, 0, 0)), R)
        b.place(lambda: b.box_base(M["green"], (L + 0.2, t + 0.4, 0.4), (0, 0, h)), R)
        b.place(lambda: b.tri_prism(M["tile"], L + 0.4, t + 1.6, 1.1, (0, 0, h + 0.35)), R)
    for s in (-1, 1):
        red_wall(s * 54.5, 8.0, s * 66.0, 8.0, h=12.0)
        red_wall(s * 98.0, 8.0, s * 104.0, 8.0, h=12.0)
        # 中左門／中右門：台基上 5 間單簷歇山門殿（太和殿兩側）
        gx = s * 82.0
        b.box_base(M["marble_d"], (32.0, 16.0, 2.6), (gx, 8.0, 0))
        b.box_base(M["marble"], (32.3, 16.3, 0.3), (gx, 8.0, 2.4))
        b.box_base(M["red"], (26.0, 9.0, 7.0), (gx, 8.0, 2.7))
        for k in range(6):
            xx = gx - 13.0 + 26.0 * k / 5
            for yy in (8.0 - 5.2, 8.0 + 5.2):
                b.cyl(M["col"], 0.36, 0.33, 7.0, (xx, yy, 2.7), seg=10)
        for k in range(5):
            xx = gx - 13.0 + 26.0 * (k + 0.5) / 5
            b.box_base(M["door"] if k != 2 else M["dark"], (4.0, 0.2, 5.6), (xx, 8.0 - 4.6, 2.7))
        b.box_base(M["cai"], (27.2, 11.2, 1.0), (gx, 8.0, 9.2))
        b.dougong(M, gx, 8.0, 27.2, 11.2, 10.2, h=0.7, spacing=1.7, out=0.6)
        b.cn_roof(M, gx, 8.0, (17.4, 8.6), 11.1, (14.0, 6.0), 10.8, "hipgable", 18.6, ridge_len=10.0, U=0.7, P=0.5, rows=8)

    # ---------------- 東西廡（紅牆廊屋）＋體仁閣／弘義閣
    def gallery(x, y0, y1, depth=9.0, h=6.0, face=1):
        """face：面向廣場方向（+1 朝東、-1 朝西）"""
        L = y1 - y0
        ym = (y0 + y1) / 2
        b.box_base(M["marble_d"], (depth + 1.0, L + 1.0, 0.9), (x, ym, 0))
        b.box_base(M["red"], (depth - 2.0, L, h), (x - face * 1.0, ym, 0.9))
        n = int(L / 4.2)
        for k in range(n + 1):
            y = y0 + L * k / n
            b.cyl(M["col"], 0.28, 0.26, h, (x + face * (depth / 2 - 0.4), y, 0.9), seg=8)
        b.box_base(M["cai"], (depth + 0.2, L + 0.2, 0.9), (x, ym, 0.9 + h - 0.6))
        b.cn_roof(M, x, ym, ((depth / 2 + 1.8), L / 2 + 1.8), 0.9 + h + 0.2, (depth / 2, L / 2), 0.9 + h, "hip",
                  0.9 + h + 3.6, ridge_len=max(0.5, L / 2 - 2.0), U=0.3, P=0.2, rows=5, hip_w=0.3, hip_h=0.3, ridge_h=0.6)

    def pavilion():
        """體仁閣／弘義閣（局部座標：長邊沿 X、正面朝 -Y）：高台基上 9 間 × 3 間兩層樓閣，單簷歇山"""
        L, D = 40.0, 15.0
        b.box_base(M["marble_d"], (L + 6, D + 6, 3.2), (0, 0, 0))
        b.box_base(M["marble"], (L + 6.3, D + 6.3, 0.3), (0, 0, 3.0))
        zf = 3.3
        xsp = [-L / 2 + L * i / 9 for i in range(10)]
        b.box_base(M["red"], (L, D, 6.5), (0, 0.6, zf))
        for xx in xsp:
            for yy in (-D / 2 - 0.6, D / 2):
                b.cyl(M["col"], 0.38, 0.35, 6.5, (xx, yy, zf), seg=10)
        for i in range(9):
            xx = (xsp[i] + xsp[i + 1]) / 2
            b.box_base(M["door"], (L / 9 - 0.9, 0.2, 5.4), (xx, -D / 2 + 0.55, zf))
        b.box_base(M["cai"], (L + 0.4, D + 1.6, 1.0), (0, 0, zf + 5.5))
        b.cn_roof(M, 0, 0, (L / 2 + 2.6, D / 2 + 2.6), zf + 6.7, (L / 2, D / 2), zf + 6.4, "skirt", zf + 8.2,
                  U=0.4, P=0.3, rows=5, hip_w=0.35, hip_h=0.3)
        b.box_base(M["red"], (L - 1.0, D - 1.0, 5.0), (0, 0, zf + 8.0))
        for xx in xsp:
            for yy in (-D / 2, D / 2):
                b.cyl(M["col"], 0.32, 0.3, 5.0, (xx * 1.03, yy * 1.1, zf + 8.0), seg=8)
        b.box_base(M["col"], (L + 1.6, D + 1.4, 0.8), (0, 0, zf + 8.0))
        b.box_base(M["cai"], (L + 1.8, D + 1.6, 0.9), (0, 0, zf + 12.4))
        b.dougong(M, 0, 0, L + 1.8, D + 1.6, zf + 13.3, h=0.8, spacing=1.8, out=0.7)
        b.cn_roof(M, 0, 0, (L / 2 + 4.4, D / 2 + 4.2), zf + 14.4, (L / 2 + 0.9, D / 2 + 0.8), zf + 14.0, "hipgable",
                  zf + 21.0, ridge_len=L / 2 - 2.0, U=0.8, P=0.6, rows=10)

    for s in (-1, 1):
        gallery(s * 101.0, -205.0, -140.0, face=-s)
        gallery(s * 101.0, -80.0, -8.0, face=-s)
        b.place(pavilion, Matrix.Translation((s * 98.0, -110.0, 0)) @ Matrix.Rotation(-s * math.pi / 2, 4, "Z"))

    b.export_glb(path)
