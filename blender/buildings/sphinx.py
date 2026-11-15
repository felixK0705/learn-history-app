"""sphinx 吉薩獅身人面像寫實模型（公尺；長 73、寬 19、高 20，面向正東 = +X）

獅身由石灰岩床直接雕出，水平層理風化成一圈圈凹凸的岩層；下半部與前爪為後世修補的小石塊包覆。
頭戴條紋頭巾（nemes），兩側垂片向肩膀張開；臉寬約 4.1 m，鼻已斷。
"""

import ast
import math
import os

from mathutils import Vector, noise

from lib import TAU, Builder

# 目標點、方位角、仰角、距離、焦距（對應參考照：東南側地面視角，頭朝右）
CAMERA = ((-2.0, 0.0, 8.0), 16.0, 3.0, 44.0, 20.0)

if os.environ.get("TL_CAM"):  # 開發用：覆寫預覽相機
    CAMERA = ast.literal_eval(os.environ["TL_CAM"])


# ---------------------------------------------------------------- 共用工具（moai.py 也會使用）
def loft(b, mi, rings, smooth=True, cap=True):
    """依序連接多個同點數截面環；兩端以中心點扇形封口"""
    vr = [[b.bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    faces = []
    for a, c in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append(b.bm.faces.new([a[i], a[j], c[j], c[i]]))
    if cap:
        for ring, rev in ((vr[0], True), (vr[-1], False)):
            cen = sum((v.co for v in ring), Vector()) / n
            cv = b.bm.verts.new(cen)
            for i in range(n):
                j = (i + 1) % n
                faces.append(b.bm.faces.new([ring[j], ring[i], cv] if rev else [ring[i], ring[j], cv]))
    for f in faces:
        f.material_index = mi
        f.smooth = smooth
    return faces


def section_x(x, W, H, z0=0.0, n=40, p=4.0, warp=None):
    """垂直於 X 軸的圓角矩形截面（YZ 平面），底部壓平於 z0"""
    pts = []
    for i in range(n):
        t = TAU * i / n
        c, s = math.cos(t), math.sin(t)
        y = W * math.copysign(abs(c) ** (2 / p), c)
        z = z0 + H / 2 + H / 2 * math.copysign(abs(s) ** (2 / p), s)
        z = max(z, z0)
        v = Vector((x, y, z))
        if warp:
            v = warp(v)
        pts.append(v)
    return pts


def section_z(z, cx, W, D, n=40, p=3.0, front=1.0, warp=None):
    """水平截面（XY 平面）：W 為半寬（Y），D 為半深（X）；front 為前緣伸長倍率"""
    pts = []
    for i in range(n):
        t = TAU * i / n
        c, s = math.cos(t), math.sin(t)
        x = D * math.copysign(abs(c) ** (2 / p), c)
        if x > 0:
            x *= front
        y = W * math.copysign(abs(s) ** (2 / p), s)
        v = Vector((cx + x, y, z))
        if warp:
            v = warp(v)
        pts.append(v)
    return pts


def lerp_table(tab, x):
    if x <= tab[0][0]:
        return tab[0][1:]
    for a, c in zip(tab, tab[1:]):
        if a[0] <= x <= c[0]:
            k = (x - a[0]) / (c[0] - a[0])
            k = k * k * (3 - 2 * k)
            return tuple(av + (cv - av) * k for av, cv in zip(a[1:], c[1:]))
    return tab[-1][1:]


def smooth01(e0, e1, x):
    k = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return k * k * (3 - 2 * k)


# ================================================================ 雕塑工具（SDF 隱函數建模 → Surface Nets 網格）
# rushmore.py、christ_redeemer.py 也會使用。全部以 numpy 向量化計算。
import numpy as np  # noqa: E402
import bpy  # noqa: E402


def _hash(ix, iy, iz, seed):
    h = (ix.astype(np.int64) * 73856093) ^ (iy.astype(np.int64) * 19349663) ^ (iz.astype(np.int64) * 83492791) ^ np.int64(seed * 2654435761 % (1 << 31))
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF).astype(np.float32) / np.float32(0xFFFFFF)


def vnoise(x, y, z=None, seed=0):
    """數值雜訊，範圍約 -1..1（z 省略時為 2D，較快）"""
    x = np.asarray(x, dtype=np.float32)
    y = np.asarray(y, dtype=np.float32)
    ix, iy = np.floor(x), np.floor(y)
    fx, fy = x - ix, y - iy
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    ix, iy = ix.astype(np.int64), iy.astype(np.int64)
    if z is None:
        z0 = np.zeros_like(ix)
        a = _hash(ix, iy, z0, seed)
        b = _hash(ix + 1, iy, z0, seed)
        c = _hash(ix, iy + 1, z0, seed)
        d = _hash(ix + 1, iy + 1, z0, seed)
        return ((a + (b - a) * ux) * (1 - uy) + (c + (d - c) * ux) * uy) * 2.0 - 1.0
    z = np.asarray(z, dtype=np.float32)
    iz = np.floor(z)
    fz = z - iz
    uz = fz * fz * (3 - 2 * fz)
    iz = iz.astype(np.int64)
    out = 0.0
    for dx in (0, 1):
        wx = ux if dx else 1 - ux
        for dy in (0, 1):
            wy = uy if dy else 1 - uy
            for dz in (0, 1):
                wz = uz if dz else 1 - uz
                out = out + wx * wy * wz * _hash(ix + dx, iy + dy, iz + dz, seed)
    return out * 2.0 - 1.0


def fbm(x, y, z=None, octaves=4, seed=0, lac=2.0, gain=0.5):
    amp, f, s, norm = 1.0, 1.0, 0.0, 0.0
    for o in range(octaves):
        s = s + amp * vnoise(x * f, y * f, None if z is None else z * f, seed + o * 17)
        norm += amp
        amp *= gain
        f *= lac
    return s / norm


def worley(x, y, seed=0, jitter=0.9, return_id=False, period=None):
    """2D Worley：回傳 (F1, F2)，單位為格；return_id 時另回傳最近胞元的亂數 0..1"""
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    ix, iy = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    f1 = np.full(x.shape, 9.0)
    f2 = np.full(x.shape, 9.0)
    cid = np.zeros(x.shape, np.float32)
    z0 = np.zeros_like(ix)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            cx, cy = ix + dx, iy + dy
            hx, hy = (cx % period, cy % period) if period else (cx, cy)
            px = cx + 0.5 + jitter * (_hash(hx, hy, z0, seed) - 0.5)
            py = cy + 0.5 + jitter * (_hash(hx, hy, z0 + 7, seed) - 0.5)
            d = np.sqrt((x - px) ** 2 + (y - py) ** 2)
            f2 = np.where(d < f1, f1, np.minimum(f2, d))
            if return_id:
                cid = np.where(d < f1, _hash(hx, hy, z0 + 13, seed), cid)
            f1 = np.minimum(f1, d)
    if return_id:
        return f1, f2, cid
    return f1, f2


class SDF:
    """以 (X, Y, Z) 陣列計算距離場；所有運算回傳新陣列。"""

    def __init__(self, X, Y, Z):
        self.X, self.Y, self.Z = X, Y, Z

    @staticmethod
    def rot(yaw=0.0, pitch=0.0, roll=0.0):
        cy, sy, cp, sp, cr, sr = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch), math.cos(roll), math.sin(roll)
        Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
        Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
        Ry = np.array([[cr, 0, sr], [0, 1, 0], [-sr, 0, cr]])
        return Rz @ Rx @ Ry

    def local(self, center, R=None, scale=1.0):
        """回傳區域座標系中的 SDF 物件（R 為區域→世界旋轉，scale 為區域單位長）"""
        X, Y, Z = self.X - center[0], self.Y - center[1], self.Z - center[2]
        if R is not None:
            X, Y, Z = (R[0, 0] * X + R[1, 0] * Y + R[2, 0] * Z, R[0, 1] * X + R[1, 1] * Y + R[2, 1] * Z, R[0, 2] * X + R[1, 2] * Y + R[2, 2] * Z)
        return SDF(X / scale, Y / scale, Z / scale)

    def ell(self, c, r):
        x, y, z = (self.X - c[0]) / r[0], (self.Y - c[1]) / r[1], (self.Z - c[2]) / r[2]
        k0 = np.sqrt(x * x + y * y + z * z)
        k1 = np.sqrt((x / r[0]) ** 2 + (y / r[1]) ** 2 + (z / r[2]) ** 2)
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)

    def sphere(self, c, r):
        return np.sqrt((self.X - c[0]) ** 2 + (self.Y - c[1]) ** 2 + (self.Z - c[2]) ** 2) - r

    def cap(self, a, b, ra, rb=None):
        """兩端半徑可不同的膠囊"""
        rb = ra if rb is None else rb
        a, b = np.asarray(a, float), np.asarray(b, float)
        ba = b - a
        L2 = float(ba @ ba)
        px, py, pz = self.X - a[0], self.Y - a[1], self.Z - a[2]
        h = np.clip((px * ba[0] + py * ba[1] + pz * ba[2]) / L2, 0.0, 1.0)
        dx, dy, dz = px - ba[0] * h, py - ba[1] * h, pz - ba[2] * h
        return np.sqrt(dx * dx + dy * dy + dz * dz) - (ra + (rb - ra) * h)

    def box(self, c, half, r=0.0):
        qx = np.abs(self.X - c[0]) - (half[0] - r)
        qy = np.abs(self.Y - c[1]) - (half[1] - r)
        qz = np.abs(self.Z - c[2]) - (half[2] - r)
        out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(qz, 0) ** 2)
        return out + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0.0) - r

    def plane(self, n, d):
        """n·p - d（n 指向外側）"""
        n = np.asarray(n, float)
        n = n / np.linalg.norm(n)
        return self.X * n[0] + self.Y * n[1] + self.Z * n[2] - d


def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def cr_interp(x, xs, ys):
    """Catmull-Rom 平滑內插（numpy 版 lerp_table，端點外取常數）"""
    xs = np.asarray(xs, float)
    ys = np.asarray(ys, float)
    x = np.clip(x, xs[0], xs[-1])
    i = np.clip(np.searchsorted(xs, x) - 1, 0, len(xs) - 2)
    x0, x1 = xs[i], xs[i + 1]
    y0, y1 = ys[i], ys[i + 1]
    ym = ys[np.maximum(i - 1, 0)]
    yp = ys[np.minimum(i + 2, len(xs) - 1)]
    xm = xs[np.maximum(i - 1, 0)]
    xp = xs[np.minimum(i + 2, len(xs) - 1)]
    h = x1 - x0
    m0 = (y1 - ym) / np.maximum(x1 - xm, 1e-9) * h
    m1 = (yp - y0) / np.maximum(xp - x0, 1e-9) * h
    t = (x - x0) / h
    t2, t3 = t * t, t * t * t
    return (2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * m1


def g2(a, b, sa, sb):
    """二維高斯"""
    return np.exp(-((a / sa) ** 2 + (b / sb) ** 2))


FACE_DEFAULT = dict(
    # 中線輪廓（不含鼻、唇）：z → 前凸量 D（臉朝 -y，表面 y = -D）
    prof=[(-0.08, 0.2), (0.0, 0.39), (0.05, 0.445), (0.09, 0.455), (0.14, 0.425), (0.19, 0.43), (0.25, 0.435),
          (0.31, 0.43), (0.4, 0.408), (0.5, 0.402), (0.535, 0.412), (0.575, 0.445), (0.65, 0.435), (0.75, 0.41),
          (0.85, 0.365), (0.95, 0.27)],
    # 正面輪廓半寬
    wf=[(-0.08, 0.07), (0.0, 0.115), (0.06, 0.17), (0.15, 0.245), (0.25, 0.29), (0.35, 0.315), (0.5, 0.335),
        (0.65, 0.33), (0.8, 0.295), (0.95, 0.18)],
    # 輪廓邊緣處的前凸量
    side=[(-0.08, 0.12), (0.0, 0.26), (0.1, 0.22), (0.2, 0.14), (0.3, 0.05), (0.5, 0.0), (0.7, 0.02), (0.85, 0.1), (0.95, 0.15)],
    p=3.0,
    eye=(0.13, 0.495, 0.085, 0.08),    # x, z, 眼窩深, 眼球凸
    brow=0.025,
    nose=(0.09, 0.345, 0.045, 0.072, 0.078),  # 鼻尖前凸, 鼻尖 z, 鼻樑寬, 鼻頭寬, 鼻翼寬
    mouth=(0.215, 0.11, 0.04),         # z, 半寬, 嘴縫深
    lips=(0.03, 0.03),
    pupil=0.022,
    cranium=((0, 0.13, 0.6), (0.335, 0.42, 0.42)),
    ears=True,
    neck=((0, 0.05, 0.25), (0, 0.12, -0.45), 0.2, 0.26),
)


def face_depth(X, Z, P):
    """臉部前凸量 D(x, z)（頭高 = 1 的局部單位）"""
    ax = np.abs(X)
    Dm = cr_interp(Z, *zip(*P["prof"]))
    Wf = cr_interp(Z, *zip(*P["wf"]))
    Ds = cr_interp(Z, *zip(*P["side"]))
    u = np.clip(ax / Wf, 0, 1.6)
    D = Dm - (Dm - Ds) * u ** P["p"]
    ex, ez, edep, eball = P["eye"]
    ex_ = ax - ex
    # 眼窩：眉骨下方深凹，眼球圓凸，上眼瞼邊緣銳利、下眼瞼淺脊
    D = D - edep * g2(ex_, Z - ez - 0.02, 0.095, 0.05)
    em = np.exp(-(ex_ / 0.06) ** 4)
    D = D + eball * em * np.exp(-((Z - ez) / 0.036) ** 2)
    lid = np.clip((Z - ez - 0.006) / 0.008, 0, 1) * np.clip(1 - (Z - ez - 0.03) / 0.02, 0, 1)
    D = D + 0.016 * lid * np.exp(-(ex_ / 0.065) ** 4)
    D = D + 0.008 * em * np.exp(-((Z - ez + 0.034) / 0.009) ** 2)       # 下眼瞼
    D = D - P.get("pupil", 0.0) * g2(ex_, Z - ez + 0.002, 0.014, 0.014)  # 瞳孔凹洞
    D = D - 0.02 * g2(ax - 0.06, Z - ez, 0.022, 0.03)                    # 內眼角
    D = D + P["brow"] * g2(ax - 0.12, Z - 0.572, 0.115, 0.028)           # 眉骨
    D = D + 0.022 * g2(ax - 0.2, Z - 0.42, 0.075, 0.05)                  # 顴骨
    nl, nz, bw, tw, aw = P["nose"]
    t = np.clip((0.54 - Z) / (0.54 - nz), 0, 1)
    nprof = np.where(Z >= nz, nl * t ** 1.05, nl * np.clip(1 - (nz - Z) / 0.04, 0, 1) ** 0.7)
    w = bw + (tw - bw) * t ** 1.8
    D = D + nprof * np.exp(-(X / w) ** 4)
    D = D + 0.016 * g2(X, Z - nz - 0.012, tw * 0.75, 0.028)                 # 鼻頭
    D = D + 0.06 * g2(ax - aw * 0.75, Z - nz + 0.002, 0.036, 0.032)          # 鼻翼
    D = D - 0.03 * g2(ax - aw * 0.4, Z - nz + 0.032, 0.03, 0.012)            # 鼻孔下緣
    # 法令紋：鼻翼外側 → 嘴角
    mz, mw, mdep = P["mouth"]
    ax0, az0, ax1, az1 = aw * 1.1, nz + 0.01, mw * 1.12, mz - 0.015
    vx, vz = ax1 - ax0, az1 - az0
    h = np.clip(((ax - ax0) * vx + (Z - az0) * vz) / (vx * vx + vz * vz), 0, 1)
    dist = np.sqrt((ax - ax0 - h * vx) ** 2 + (Z - az0 - h * vz) ** 2)
    D = D - 0.022 * np.exp(-(dist / 0.014) ** 2)
    D = D + 0.012 * np.exp(-((dist + 0.02) / 0.03) ** 2) * (ax < ax0 + h * vx)  # 法令紋內側的上唇隆起
    up, lo = P["lips"]
    lm = np.clip(1 - (ax / mw) ** 2, 0, 1)
    D = D + up * lm * np.exp(-((Z - mz - 0.026) / 0.02) ** 2)
    D = D + lo * lm * np.exp(-((Z - mz + 0.026) / 0.019) ** 2)
    D = D - mdep * np.clip(1 - (ax / (mw * 1.05)) ** 4, 0, 1) * np.exp(-((Z - mz) / 0.007) ** 2)
    D = D - 0.025 * g2(ax - mw, Z - mz, 0.018, 0.018)                # 嘴角
    D = D - 0.012 * g2(X, Z - mz - 0.06, 0.013, 0.022)               # 人中
    D = D - 0.015 * g2(X, Z - mz + 0.075, 0.07, 0.018)               # 頦唇溝
    return D, Wf


def face_head(S, P):
    """寫實頭像 SDF（頭高 = 1：下巴底 z=0、頭頂 z=1，耳朵平面 y=0，臉朝 -y）"""
    X, Y, Z = S.X, S.Y, S.Z
    D, Wf = face_depth(X, Z, P)
    face = -(Y + D) * 0.7
    face = smax(face, np.abs(X) - Wf, 0.04)
    face = smax(face, Y - 0.16, 0.05)
    face = smax(face, Z - 0.9, 0.1)
    face = smax(face, -0.1 - Z, 0.03)
    c, r = P["cranium"]
    d = smin(S.ell(c, r), face, 0.035)
    if P.get("ears"):
        for sx in (-1, 1):
            d = smin(d, S.ell((sx * 0.325, 0.04, 0.45), (0.04, 0.085, 0.13)), 0.02)
    if P.get("neck"):
        a, b, ra, rb = P["neck"]
        d = smin(d, S.cap(a, b, ra, rb), 0.06)
    return d


def surface_nets(F, origin, step, smooth_iter=1):
    """F[i,j,k] 為格點值（<0 內部）；回傳 (頂點 Nx3, 四邊形 Mx4)"""
    F = F.astype(np.float32)
    nx, ny, nz = F.shape
    inside = F < 0
    cx, cy, cz = nx - 1, ny - 1, nz - 1
    acc = np.zeros((cx * cy * cz, 3), np.float64)
    cnt = np.zeros(cx * cy * cz, np.float64)

    def cell_id(i, j, k):
        return (i * cy + j) * cz + k

    edges = []
    for ax in range(3):
        sl0 = [slice(None)] * 3
        sl1 = [slice(None)] * 3
        sl0[ax] = slice(0, -1)
        sl1[ax] = slice(1, None)
        f0, f1 = F[tuple(sl0)], F[tuple(sl1)]
        cross = inside[tuple(sl0)] != inside[tuple(sl1)]
        idx = np.nonzero(cross)
        a, c = f0[idx], f1[idx]
        t = a / (a - c)
        pos = np.stack(idx, 1).astype(np.float64)
        pos[:, ax] += t
        edges.append((ax, idx, pos, a < 0))
        # 每條邊屬於相鄰 4 個格子
        o = [q for q in range(3) if q != ax]
        for d1 in (0, -1):
            for d2 in (0, -1):
                ci = [idx[0].copy(), idx[1].copy(), idx[2].copy()]
                ci[o[0]] = ci[o[0]] + d1
                ci[o[1]] = ci[o[1]] + d2
                ok = (ci[0] >= 0) & (ci[0] < cx) & (ci[1] >= 0) & (ci[1] < cy) & (ci[2] >= 0) & (ci[2] < cz)
                cid = cell_id(ci[0][ok], ci[1][ok], ci[2][ok])
                for q in range(3):
                    acc[:, q] += np.bincount(cid, weights=pos[ok, q], minlength=acc.shape[0])
                cnt += np.bincount(cid, minlength=acc.shape[0])
    active = cnt > 0
    vid = np.full(cnt.shape[0], -1, np.int64)
    vid[active] = np.arange(active.sum())
    V = acc[active] / cnt[active, None]
    quads = []
    for ax, idx, pos, neg in edges:
        o = [q for q in range(3) if q != ax]
        ok = (idx[o[0]] > 0) & (idx[o[0]] < [nx, ny, nz][o[0]] - 1) & (idx[o[1]] > 0) & (idx[o[1]] < [nx, ny, nz][o[1]] - 1)
        ii = [idx[0][ok], idx[1][ok], idx[2][ok]]
        ng = neg[ok]

        def cc(d1, d2):
            c = [ii[0].copy(), ii[1].copy(), ii[2].copy()]
            c[o[0]] = c[o[0]] + d1
            c[o[1]] = c[o[1]] + d2
            return vid[cell_id(*c)]

        q = np.stack([cc(-1, -1), cc(0, -1), cc(0, 0), cc(-1, 0)], 1)
        # 方向：負值（內部）在邊的起點時翻轉
        flip = ~ng if ax != 1 else ng
        q[flip] = q[flip][:, ::-1]
        quads.append(q)
    Q = np.concatenate(quads, 0)
    # 輕度拉普拉斯平滑（去除體素階梯）
    for _ in range(smooth_iter):
        nb = np.zeros_like(V)
        nc = np.zeros(len(V))
        for s in range(4):
            a, c = Q[:, s], Q[:, (s + 1) % 4]
            np.add.at(nb, a, V[c])
            np.add.at(nb, c, V[a])
            np.add.at(nc, a, 1)
            np.add.at(nc, c, 1)
        V = V * 0.5 + 0.5 * nb / np.maximum(nc, 1)[:, None]
    V = V * step + np.asarray(origin, float)
    return V, Q


def grid3(lo, hi, step):
    xs = np.arange(lo[0], hi[0] + step * 0.5, step)
    ys = np.arange(lo[1], hi[1] + step * 0.5, step)
    zs = np.arange(lo[2], hi[2] + step * 0.5, step)
    X, Y, Z = np.meshgrid(xs.astype(np.float32), ys.astype(np.float32), zs.astype(np.float32), indexing="ij")
    return SDF(X, Y, Z), (xs[0], ys[0], zs[0])


def face_normals(V, Q):
    a = V[Q[:, 2]] - V[Q[:, 0]]
    c = V[Q[:, 3]] - V[Q[:, 1]]
    n = np.cross(a, c)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def box_uv(V, Q, tile, N=None):
    """依面法線做方塊投影 UV（每個角點一組）"""
    N = face_normals(V, Q) if N is None else N
    ax = np.argmax(np.abs(N), 1)
    P = V[Q]  # M,4,3
    u = np.where(ax[:, None] == 0, P[..., 1], P[..., 0])
    v = np.where(ax[:, None] == 2, P[..., 1], P[..., 2])
    tile = np.broadcast_to(np.asarray(tile, float), (len(Q),))[:, None]
    return np.stack([u / tile, v / tile], -1)


def mesh_object(name, V, Q, mats, mat_idx=None, uv=None, smooth=True, decimate=None):
    """以 numpy 陣列建立 Blender 物件（四邊形面），可附 Decimate 修改器（匯出時套用）"""
    V = np.asarray(V, np.float32)
    Q = np.asarray(Q, np.int64)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.ravel())
    nl = Q.shape[1]
    me.loops.add(len(Q) * nl)
    me.loops.foreach_set("vertex_index", Q.ravel().astype(np.int32))
    me.polygons.add(len(Q))
    me.polygons.foreach_set("loop_start", np.arange(0, len(Q) * nl, nl, dtype=np.int32))
    if uv is not None:
        lay = me.uv_layers.new(name="UVMap")
        lay.data.foreach_set("uv", np.asarray(uv, np.float32).ravel())
    for m in mats:
        me.materials.append(m)
    if mat_idx is not None:
        me.polygons.foreach_set("material_index", np.asarray(mat_idx, np.int32))
    me.polygons.foreach_set("use_smooth", np.full(len(Q), bool(smooth)))
    me.update(calc_edges=True)
    me.validate()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    if decimate:
        mod = obj.modifiers.new("dec", "DECIMATE")
        mod.ratio = decimate
        mod.use_collapse_triangulate = True
    return obj


def img_mat(name, diff_path, nor_path=None, rough=0.85, nor_strength=1.0, arm_path=None):
    """以自製貼圖建立 PBR 材質"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(diff_path, check_existing=True)
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    if nor_path:
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(nor_path, check_existing=True)
        n.image.colorspace_settings.name = "Non-Color"
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = nor_strength
        nt.links.new(n.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if arm_path:
        a = nt.nodes.new("ShaderNodeTexImage")
        a.image = bpy.data.images.load(arm_path, check_existing=True)
        a.image.colorspace_settings.name = "Non-Color"
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(a.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = 0.0
    return m


def gray_tex(tex_id, size=None):
    """讀取 Poly Haven 漫反射貼圖並轉成 0..1 灰階陣列（平均 0.5）"""
    from PIL import Image

    from lib import TEX

    im = Image.open(os.path.join(TEX, tex_id, "diff.jpg")).convert("L")
    if size:
        im = im.resize((size, size), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255.0
    return a / max(a.mean(), 1e-3) * 0.5


def tile_sample(img, u, v):
    """以重複方式取樣影像（u,v 以影像寬為 1 的單位）"""
    h, w = img.shape[:2]
    x = (np.asarray(u) * w).astype(np.int64) % w
    y = (np.asarray(v) * h).astype(np.int64) % h
    return img[y, x]


def blur(a, r):
    """快速盒狀模糊（多次近似高斯），r 為像素半徑"""
    r = int(max(1, r))
    out = a.astype(np.float32)
    for _ in range(3):
        for ax in (0, 1):
            c = np.cumsum(np.pad(out, [(r + 1, r) if q == ax else (0, 0) for q in range(out.ndim)], mode="edge"), axis=ax)
            hi = np.take(c, np.arange(2 * r + 1, c.shape[ax]), axis=ax)
            lo = np.take(c, np.arange(0, c.shape[ax] - 2 * r - 1), axis=ax)
            out = (hi - lo) / (2 * r + 1)
    return out


def normal_from_height(h, strength=1.0):
    """高度圖 → OpenGL 法線貼圖（uint8 RGB）"""
    gy, gx = np.gradient(h.astype(np.float32))
    nx, ny, nz = -gx * strength, gy * strength, np.ones_like(gx)
    L = np.sqrt(nx * nx + ny * ny + nz * nz)
    return (np.stack([nx / L, ny / L, nz / L], -1) * 127.5 + 127.5).clip(0, 255).astype(np.uint8)


def save_img(arr, path, quality=88):
    from PIL import Image

    os.makedirs(os.path.dirname(path), exist_ok=True)
    a = np.asarray(arr)
    if a.dtype != np.uint8:
        a = (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(a).save(path, quality=quality)
    return path


# ---------------------------------------------------------------- 獅身人面像 SDF
HEAD_C = (10.6, 0.0, 14.3)   # 頭部局部原點（下巴底、耳朵平面）
HEAD_H = 5.9                 # 下巴到頭頂


def strata(X, Y, Z, amp=1.0):
    """水平岩層侵蝕：每層中段外凸、層界內凹（像疊起的軟墊），各層強度不同；回傳外凸量（公尺）"""
    zw = Z + 0.45 * fbm(X * 0.04, Y * 0.04, None, 3, seed=301)
    # 層厚不一：以單調扭曲讓層距在 0.6–1.8 m 之間變化
    zq = zw + 0.55 * np.sin(zw * 0.83 + 0.4) + 0.3 * np.sin(zw * 2.1 + 1.7)
    T = 1.15
    i = np.floor(zq / T)
    f = zq / T - i
    hard = 0.55 + 0.45 * _hash(i.astype(np.int64), i.astype(np.int64) * 0 + 3, i.astype(np.int64) * 0, 77)
    prof = np.sqrt(np.clip(1 - (2 * f - 1) ** 2, 0, 1)) ** 0.8 - 0.62
    rough = 0.22 * fbm(X * 0.35, Y * 0.35, Z * 0.8, 3, seed=302) + 0.12 * fbm(X * 1.2, Y * 1.2, Z * 1.5, 2, seed=303)
    # 局部崩落的凹洞
    pit = np.clip(fbm(X * 0.12, Z * 0.25, Y * 0.1, 3, seed=304) - 0.25, 0, 1) * 1.2
    return amp * (hard * prof * 0.95 + rough - pit)


def body_sdf(S):
    X, Y, Z = S.X, S.Y, S.Z
    xs = [-46.5, -45.0, -42.5, -38.0, -28.0, -15.0, -3.0, 5.0, 10.0, 13.5, 16.0, 17.6]
    W = cr_interp(X, xs, [2.5, 5.2, 6.6, 7.0, 6.8, 6.6, 6.7, 7.0, 7.0, 6.6, 5.6, 3.4])
    Hb = cr_interp(X, xs, [4.5, 7.4, 9.2, 9.8, 9.9, 9.9, 10.1, 10.6, 11.0, 10.8, 9.2, 5.5])
    hc = Hb / 2
    p = 3.2
    rn = (np.abs(Y / W) ** p + np.abs((Z - hc) / hc) ** p) ** (1 / p)
    d = (rn - 1.0) * np.minimum(W, hc) * 0.85
    d = smax(d, X - 17.8, 0.8)
    d = smax(d, -46.8 - X, 0.8)
    # 胸前（圓鼓的胸膛往上收成頸部）
    d = smin(d, S.ell((11.5, 0, 6.8), (5.6, 6.6, 6.6)), 1.0)
    d = smin(d, S.cap((10.2, 0, 9.0), (10.6, 0, 15.5), 3.0, 2.4), 1.2)
    # 後腿（盤坐在臀側）
    for sy in (-1, 1):
        d = smin(d, S.ell((-36.5, sy * 6.6, 3.3), (8.5, 1.7, 3.4)), 0.8)
        d = smin(d, S.ell((-28.5, sy * 7.6, 1.0), (4.5, 1.3, 1.1)), 0.5)
    # 尾巴：沿南側（-y）臀部繞到身側
    d = smin(d, S.cap((-45.5, -4.5, 1.6), (-40.0, -7.7, 1.0), 0.55, 0.5), 0.3)
    d = smin(d, S.cap((-40.0, -7.7, 1.0), (-31.0, -8.0, 0.85), 0.5, 0.45), 0.3)
    # 岩層侵蝕（下段 2.8 m 為修補石塊包覆 → 平整）
    clad = np.clip((Z - 2.4) / 1.0, 0, 1)
    top = np.clip((Hb - Z) / 1.6, 0, 1)
    d = d - strata(X, Y, Z, 1.0) * clad * (0.3 + 0.7 * top)
    # 前爪（後世小石塊包覆，圓角長方體）
    for sy in (-1, 1):
        paw = S.box((22.0, sy * 4.5, 1.45), (10.8, 2.25, 1.45), 1.1)
        paw = smin(paw, S.ell((12.5, sy * 4.6, 3.0), (4.5, 2.6, 3.2)), 0.8)
        d = smin(d, paw, 0.6)
    d = smax(d, -Z - 0.2, 0.1)
    return d


def nemes_head_sdf(S):
    """頭部：寫實臉（斷鼻）＋條紋頭巾（nemes）；局部單位頭高 = 1，臉朝 -y"""
    X, Y, Z = S.X, S.Y, S.Z
    P = dict(FACE_DEFAULT)
    P["wf"] = [(z, w * 1.08) for z, w in P["wf"]]
    P["nose"] = (0.025, 0.36, 0.05, 0.075, 0.08)       # 鼻頭已斷
    P["mouth"] = (0.215, 0.13, 0.03)
    P["lips"] = (0.035, 0.035)
    P["eye"] = (0.135, 0.5, 0.075, 0.07)
    P["brow"] = 0.015
    P["pupil"] = 0.0
    P["ears"] = False
    P["cranium"] = ((0, 0.12, 0.58), (0.36, 0.44, 0.4))
    P["neck"] = ((0, 0.1, 0.25), (0, 0.15, -0.6), 0.26, 0.34)
    d = face_head(S, P)
    # 斷鼻的粗糙斷面
    d = d + 0.012 * np.exp(-((X / 0.07) ** 2 + ((Z - 0.4) / 0.08) ** 2)) * fbm(X * 40, Z * 40, None, 2, seed=311)
    # 大耳朵（位於頭巾垂片前方）
    for sx in (-1, 1):
        ear = S.ell((sx * 0.37, -0.02, 0.47), (0.05, 0.1, 0.15))
        ear = smax(ear, -S.ell((sx * 0.4, -0.04, 0.47), (0.03, 0.06, 0.1)), 0.01)
        d = smin(d, ear, 0.02)
    # 頭巾（nemes）：側視為三角形──平頂、前緣在臉頰後方垂直落到胸前、後緣自頭頂斜向後下到肩背；
    # 正視時自太陽穴向外張開到肩膀。水平截面為圓角矩形。
    zc = np.clip(Z, -0.7, 1.0)
    w = 0.41 + 0.40 * np.clip((0.62 - zc) / 1.0, 0, 1) ** 1.2
    yf = -0.2 + 0.08 * np.clip((0.5 - zc) / 1.0, 0, 1)
    yb = 0.46 + 0.5 * np.clip((0.9 - zc) / 1.6, 0, 1)
    yc, hd = (yf + yb) / 2, (yb - yf) / 2
    rn = (np.abs(X / w) ** 4 + np.abs((Y - yc) / hd) ** 4) ** 0.25
    nem = (rn - 1.0) * np.minimum(w, hd)
    nem = smax(nem, Z - 0.98, 0.06)
    nem = smax(nem, -0.72 - Z, 0.05)
    # 頭巾前緣：額上頭帶，眉上方切齊
    front = -(Y + 0.405 - 0.55 * np.clip(0.72 - Z, 0, 1) - 0.02 * np.clip((np.abs(X) - 0.3) / 0.1, 0, 1))
    top = smax(S.ell((0, 0.1, 0.7), (0.43, 0.53, 0.36)), front, 0.02)
    nem = smin(nem, top, 0.06)
    band = smax(S.ell((0, -0.04, 0.715), (0.425, 0.385, 0.035)), -(Y + 0.415), 0.01)
    nem = smin(nem, band, 0.015)
    # 條紋（側面垂片上較明顯，已嚴重風化）
    stripes = 0.003 * np.sin(Z * TAU / 0.08) * np.clip((np.abs(X) - 0.42) / 0.08, 0, 1) * np.clip((Y - yf - 0.04) / 0.06, 0, 1)
    nem = nem + stripes
    # 臉的區域挖空頭巾（臉在頭巾開口中）
    hole = smax(np.abs(X) - 0.33, Z - 0.7, 0.05)
    hole = smax(hole, -(Y + 0.6), 0.02)
    hole = smax(hole, Y + 0.05, 0.05)
    nem = smax(nem, -hole, 0.04)
    d = smin(d, nem, 0.025)
    # 風化
    d = d + 0.004 * fbm(X * 18, Y * 18, Z * 18, 3, seed=312)
    return d


def small_mat(name, tex_id, tint, nor_size=512, rough=0.9, nor_strength=1.0):
    """自訂材質：調色漫反射（1K）＋縮小的法線貼圖（控制 GLB 大小）"""
    from PIL import Image

    from lib import TEX, tinted_texture

    diff = tinted_texture(tex_id, tint)
    out = os.path.join(TEX, "_gen", "small")
    os.makedirs(out, exist_ok=True)
    nor = os.path.join(out, f"{tex_id}_nor{nor_size}.jpg")
    if not os.path.exists(nor):
        Image.open(os.path.join(TEX, tex_id, "nor.jpg")).resize((nor_size, nor_size), Image.LANCZOS).save(nor, quality=85)
    return img_mat(name, diff, nor, rough=rough, nor_strength=nor_strength)


def sphinx(path):
    b = Builder("Sphinx", seed=11)
    m_body = small_mat("Sphinx_body", "cliff_side", "#c79f6b", nor_strength=1.4)
    m_bodyd = small_mat("Sphinx_bodyd", "cliff_side", "#a47c50", nor_strength=1.4)
    m_head = small_mat("Sphinx_head", "rock_04", "#bf9361", nor_strength=1.0)
    m_clad = small_mat("Sphinx_clad", "sandstone_blocks_05", "#d3b07c", nor_strength=1.0)
    clad = b.tex("clad", "sandstone_blocks_05", tile=2.2, tint="#d3b07c", normal=1.0, rough=0.9)
    floor_m = b.tex("floor", "sand_01", tile=6.0, tint="#d5b07a", normal=0.8)
    bedrock = b.tex("bedrock", "cliff_side", tile=8.0, tint="#c39b6a", normal=1.2)
    wall_m = b.tex("wallm", "sandstone_blocks_05", tile=4.0, tint="#c39c6a", normal=0.9)
    granite = b.color("granite", "#5e463e", rough=0.5)
    pyr_m = b.tex("pyr", "sandstone_blocks_05", tile=5.0, tint="#a5865f", normal=1.2, rough=0.95)
    casing = b.tex("casing", "sandstone_blocks_05", tile=8.0, tint="#c4b08b", normal=0.3)

    # ---- 獅身（含前爪、後腿、尾巴）
    S, o = grid3((-47.5, -9.6, -0.4), (34.0, 9.6, 16.5), 0.2)
    F = body_sdf(S)
    V, Q = surface_nets(F, o, 0.2)
    C = V[Q].mean(1)
    N = face_normals(V, Q)
    paw_zone = (C[:, 0] > 13.5) & (np.abs(C[:, 1]) > 2.0) & (C[:, 2] < 3.4)
    low = (C[:, 2] < 2.7) & (np.abs(N[:, 2]) < 0.8)
    rec = (strata(C[:, 0], C[:, 1], C[:, 2]) < -0.2)
    mi = np.where(paw_zone | low, 1, np.where(rec, 2, 0))
    tiles = np.array([7.0, 2.2, 7.0])[mi]
    mesh_object("SphinxBody", V, Q, [m_body, m_clad, m_bodyd], mi, box_uv(V, Q, tiles, N), decimate=0.42)

    # ---- 頭部（頭巾、臉）
    R = SDF.rot(math.pi / 2, 0.0)
    H = HEAD_H
    corners = np.array([[x, y, z] for x in (-0.88, 0.88) for y in (-0.6, 1.3) for z in (-0.75, 1.08)]) * H
    Wc = corners @ R.T + np.asarray(HEAD_C)
    S2, o2 = grid3(Wc.min(0), Wc.max(0), 0.07)
    F2 = nemes_head_sdf(S2.local(HEAD_C, R, H)) * H
    V2, Q2 = surface_nets(F2, o2, 0.07)
    mesh_object("SphinxHead", V2, Q2, [m_head], None, box_uv(V2, Q2, 2.5), decimate=0.45)

    # 兩爪之間的夢之碑（紅花崗岩）與祭壇
    b.box_base(granite, (0.8, 2.6, 3.6), (18.4, 0, 0))
    b.box_base(clad, (3.0, 4.0, 0.9), (25.0, 0, 0))
    # 南側下方的修補扶壁石塊（參考照中可見）
    for x, w, h in ((-31.0, 5.5, 2.6), (-16.0, 4.0, 2.2), (-3.0, 4.5, 3.0)):
        b.box_base(clad, (w, 1.8, h), (x, -7.2, 0.0))

    # ---- 圍場：岩床地面、三面岩壁與上方台地（只做適量周邊）
    b.box_base(floor_m, (150, 128, 1.0), (5, -2, -1.0))
    wall_h = 7.0

    def cliff(x0, y0, x1, y1, h, seed):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(2, int(L / 9))
        ang = math.atan2(y1 - y0, x1 - x0)
        for i in range(n):
            k = (i + 0.5) / n
            cx, cy = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
            hh = h * (0.92 + 0.12 * b.rng.random())
            b.rock(bedrock, (L / n * 1.3, 6.0, hh + 1.0), (cx, cy, hh / 2 - 0.5), rot=(0, 0, ang), rough=0.06, subdiv=3, seed=seed + i, round_=0.05)

    cliff(-62, -58, -62, 56, wall_h, 100)       # 西側
    cliff(-62, 52, 30, 52, wall_h - 0.5, 200)    # 北側
    cliff(-62, -58, -14, -58, wall_h - 1.0, 300)  # 南側（東段較開闊）
    b.box_base(wall_m, (92, 1.2, 2.4), (-16, 55.5, wall_h - 1.4))
    for sx, sy, w, d, h in ((-79, -2, 30, 124, wall_h - 0.8), (-16, 72, 102, 38, wall_h - 1.2), (-38, -66, 50, 12, wall_h - 1.6)):
        b.box_base(floor_m, (w, d, h + 1.0), (sx, sy, -1.0))
    # ---- 背景：卡夫拉金字塔（縮小置於圍場西北方作為剪影，頂端保留外殼石）
    px, py, base, ph = 2.0, 76.0, 46.0, 30.0
    b.frustum(pyr_m, (base, base), (base * 0.18, base * 0.18), ph * 0.82, (px, py, wall_h - 1.2))
    b.frustum(casing, (base * 0.18, base * 0.18), (0.05, 0.05), ph * 0.18, (px, py, wall_h - 1.2 + ph * 0.82))
    # 地面散落石塊
    for i in range(26):
        x, y = b.rng.uniform(-55, 50), b.rng.choice([-1, 1]) * b.rng.uniform(14, 40)
        sz = b.rng.uniform(0.4, 1.4)
        b.rock(bedrock, (sz, sz * 0.8, sz * 0.6), (x, y, sz * 0.25), rough=0.15, subdiv=2, seed=400 + i)
    b.export(path)
