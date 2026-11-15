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
CAMERA = ((-1.0, 0.0, 7.5), 32.0, 3.0, 38.0, 18.0)

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


# ---------------------------------------------------------------- 主體
def sphinx(path):
    b = Builder("Sphinx", seed=11)
    body_m = b.tex("body", "rock_04", tile=3.5, tint="#bf8c4c", normal=1.6)
    groove = b.tex("groove", "rock_04", tile=3.0, tint="#8f6a40", normal=1.6)
    head_m = b.tex("head", "rock_04", tile=2.5, tint="#bd8b52", normal=1.2)
    clad = b.tex("clad", "sandstone_blocks_05", tile=2.4, tint="#c99d63", normal=1.0)
    floor_m = b.tex("floor", "sand_01", tile=6.0, tint="#cfa870", normal=0.8)
    bedrock = b.tex("bedrock", "rock_04", tile=6.0, tint="#c39a62", normal=1.2)
    wall_m = b.tex("wallm", "sandstone_blocks_05", tile=4.0, tint="#c9a26c", normal=0.9)
    granite = b.tex("granite", "rock_04", tile=1.5, tint="#7d5a4e", normal=0.6)

    # ---- 水平岩層侵蝕：每層上緣硬層外凸、下緣軟層內凹（階梯狀）
    def strata(v, amp, keep_top=0.0):
        z = v.z
        wob = 0.35 * noise.noise(Vector((v.x * 0.06, 0.3, 0.0)))
        layer = 1.15
        ph = (z + wob) / layer
        fr = ph - math.floor(ph)
        step = -1.0 + 2.0 * smooth01(0.05, 0.7, fr)  # 下凹 → 上凸，頂端急收
        if fr > 0.88:
            step = 1.0 - (fr - 0.88) / 0.12 * 1.6
        lid = math.floor(ph)
        strength = 0.7 + 0.6 * (0.5 + 0.5 * noise.noise(Vector((lid * 1.7, v.x * 0.05, 0.0))))
        rnd = noise.noise(Vector((v.x * 0.3, v.y * 0.3, z * 0.7))) * 0.35 + noise.noise(Vector((v.x * 0.08, v.y * 0.1 + 5, z * 0.15))) * 0.6 + noise.noise(Vector((v.x * 0.7, v.y * 0.2, lid * 3.1))) * 0.45 * (abs(noise.noise(Vector((v.x * 0.15, lid * 2.3, 1.0)))) > 0.15)
        d = (step * strength * 0.75 + rnd) * amp * (1.0 - keep_top) * (0.25 + 0.75 * smooth01(2.6, 4.5, z))
        out = Vector((0, v.y, 0))
        if out.length > 1e-6:
            out.normalize()
        return v + out * d

    # ---- 獅身：X 方向放樣（臀部 → 胸前）；高度為背脊高
    tab = [  # x, 半寬, 高
        (-46.0, 3.4, 4.4), (-45.0, 5.6, 7.6), (-43.0, 6.8, 9.4), (-40.0, 7.1, 10.0), (-30.0, 6.8, 10.1),
        (-18.0, 6.5, 9.9), (-8.0, 6.6, 10.0), (-1.0, 6.9, 10.3), (4.0, 7.3, 10.9), (9.0, 7.4, 11.4),
        (12.0, 7.1, 11.2), (14.0, 6.8, 10.8), (15.8, 6.2, 9.2), (16.9, 5.0, 7.0), (17.3, 2.6, 4.0),
    ]
    rings = []
    N = 260
    xs = [tab[0][0] + (tab[-1][0] - tab[0][0]) * i / 90 for i in range(91)]
    for x in xs:
        W, H = lerp_table(tab, x)
        # 背脊頂面保留較平整，側面與胸前層理明顯
        rings.append(section_x(x, W, H, n=N, p=6.0, warp=lambda v, H=H: strata(v, 0.8, 0.6 * smooth01(H * 0.9, H, v.z))))
    faces = loft(b, body_m, rings)
    for f in faces:
        c = f.calc_center_median()
        if c.z < 3.2 and abs(f.normal.z) < 0.8 and c.x > -44:
            f.material_index = clad  # 下層修補石塊
    # 胸前胸甲般的層疊（前胸更明顯的凸出岩層）
    for k, z in enumerate((5.6, 7.0, 8.4)):
        b.rock(body_m, (2.2, 10.5 - k * 0.8, 0.8), (16.2 - k * 0.7, 0, z), rough=0.08, subdiv=3, seed=31 + k, round_=0.6)

    # ---- 頸部（下巴下方）
    hx = 8.6  # 頭部中心 x
    neck = []
    for z, W, D in ((10.0, 3.3, 3.0), (11.5, 2.9, 2.4), (13.0, 2.6, 2.0), (14.6, 2.5, 1.9)):
        neck.append(section_z(z, hx + 0.4, W, D, n=32, p=2.6))
    loft(b, head_m, neck)
    # 胸部隆起：由前胸往上收成頸部（頭部底下不留台階）
    chest = []
    for z, cx, W, D in ((5.0, hx + 2.6, 6.6, 5.6), (8.0, hx + 2.4, 6.5, 5.2), (10.0, hx + 1.9, 5.9, 4.5),
                        (11.4, hx + 1.3, 4.6, 3.5), (12.6, hx + 0.9, 3.2, 2.5), (13.8, hx + 0.8, 2.6, 2.0)):
        chest.append(section_z(z, cx, W, D, n=120, p=2.4, warp=lambda v: strata(v, 0.45)))
    loft(b, body_m, chest)
    b.bm.verts.ensure_lookup_table()
    head_start = len(b.bm.verts)

    # ---- 頭巾（nemes）：水平截面放樣；下方張開到肩膀、上方收成圓頂
    ntab = [  # z, 中心x, 半寬, 半深
        (10.6, hx - 1.6, 5.4, 4.1), (12.0, hx - 1.4, 5.25, 3.5), (13.5, hx - 1.3, 4.75, 3.0),
        (15.0, hx - 1.2, 4.2, 2.6), (16.5, hx - 1.0, 3.65, 2.35), (17.9, hx - 0.8, 3.2, 2.25), (18.4, hx - 0.2, 3.0, 2.75),
        (18.75, hx + 0.2, 2.9, 3.05), (19.5, hx + 0.15, 2.6, 2.8), (20.0, hx - 0.1, 2.0, 2.1), (20.3, hx - 0.3, 1.0, 1.1),
    ]
    nr = []
    for z, cx, W, D in ntab:
        def nw(v, z=z):
            # 頭巾橫條紋（淺凹槽）
            g = 0.06 * math.sin(v.z * TAU / 0.55)
            o = Vector((v.x - hx, v.y, 0))
            return v + (o.normalized() * g if o.length > 1e-6 else Vector())
        nr.append(section_z(z, cx, W, D, n=56, p=3.2, warp=nw))
    loft(b, head_m, nr)

    # ---- 臉：水平截面放樣；中線剖面（下顎→下巴→唇→斷鼻→眉→額）決定前緣，再刻眼窩
    xc_tab = [(13.4, 1.6), (14.1, 3.3), (14.6, 3.6), (15.4, 3.7), (16.5, 3.75), (17.6, 3.8), (18.4, 3.65), (19.15, 3.45)]
    w_tab = [(13.5, 1.25), (14.15, 1.45), (14.8, 1.8), (15.6, 2.0), (19.15, 2.05)]

    def face_x(y, z):
        (xc,) = lerp_table(xc_tab, z)
        (W,) = lerp_table(w_tab, z)
        a = min(1.0, abs(y) / W)
        x = xc - 1.6 * a ** 2.6  # 臉頰往兩側圓弧後收
        eye = math.exp(-((abs(y) - 0.95) / 0.36) ** 2) * math.exp(-((z - 17.2) / 0.3) ** 2)
        x -= 0.42 * eye
        x += 0.12 * math.exp(-((z - 17.72) / 0.14) ** 2) * (1 - a ** 2)  # 眉骨
        nose = math.exp(-(y / 0.45) ** 4) * smooth01(15.6, 15.85, z) * (1 - smooth01(16.9, 17.5, z))
        x += 0.55 * nose  # 鼻樑殘部（鼻頭已斷，斷面平整）
        mouth = math.exp(-(y / 1.05) ** 6)
        x += 0.14 * mouth * math.exp(-((z - 15.3) / 0.15) ** 2) + 0.12 * mouth * math.exp(-((z - 14.9) / 0.15) ** 2)
        x -= 0.12 * mouth * math.exp(-((z - 15.1) / 0.06) ** 2)
        x += 0.07 * math.exp(-((abs(y) - 1.25) / 0.4) ** 2) * math.exp(-((z - 16.3) / 0.5) ** 2)  # 顴骨
        return hx + x

    fr = []
    M = 40
    for k in range(25):
        z = 13.5 + (19.15 - 13.5) * k / 24
        (W,) = lerp_table(w_tab, z)
        ring = [Vector((face_x(-W + 2 * W * i / (M - 1), z), -W + 2 * W * i / (M - 1), z)) for i in range(M)]
        ring.append(Vector((hx + 0.4, W, z)))
        ring.append(Vector((hx + 0.4, -W, z)))
        fr.append(list(reversed(ring)))
    loft(b, head_m, fr)
    # 耳：位於頭巾垂片前、臉兩側
    for sgn in (-1, 1):
        b.rock(head_m, (0.7, 0.35, 1.2), (hx + 1.95, sgn * 2.2, 16.3), rough=0.08, subdiv=2, seed=40 + sgn, round_=0.6)
    # 頭巾垂片（lappets）前緣：自太陽穴到肩膀的厚板
    for sgn in (-1, 1):
        lp = []
        for z, W in ((11.2, 5.1), (13.0, 4.55), (15.0, 3.75), (17.0, 3.0), (18.8, 2.55)):
            x0 = hx + 1.15 + (0.3 if z > 16 else 0.0)
            lp.append([Vector((x0 - 1.6, sgn * (W - 1.5), z)), Vector((x0 + 0.35, sgn * (W - 1.5), z)),
                       Vector((x0 + 0.35, sgn * W, z)), Vector((x0 - 1.6, sgn * (W + 0.05), z))])
        loft(b, head_m, lp, smooth=False)

    # 頭部整體略放大（以頭頂為基準，臉寬約 4.3 m）
    b.bm.verts.ensure_lookup_table()
    top = Vector((hx, 0, 20.3))
    for v in b.bm.verts[head_start:]:
        v.co = top + (v.co - top) * 1.08
    # ---- 前爪（現代小石塊包覆，長約 15 m）與後腿
    for s in (-1, 1):
        ptab = [(10.0, 2.3, 3.2), (16.0, 2.25, 3.1), (28.0, 2.2, 2.9), (30.5, 2.0, 2.6), (31.6, 1.5, 2.0), (32.2, 0.6, 1.0)]
        pr = []
        for i in range(31):
            x = 10.0 + 22.2 * i / 30
            W, H = lerp_table(ptab, x)
            pr.append(section_x(x, W, H, n=32, p=5.0, warp=lambda v, s=s: v + Vector((0, s * 4.6, 0))))
        loft(b, clad, pr)
        # 爪尖的趾縫
        for t in (-0.75, 0.0, 0.75):
            b.box_base(groove, (1.2, 0.12, 1.4), (31.4, s * 4.6 + t, 0.0))
        # 後腿（盤坐於臀側）
        hr2 = []
        for i in range(15):
            x = -44.5 + 20.0 * i / 14
            W, H = lerp_table([(-44.5, 0.8, 2.0), (-41.0, 1.9, 5.0), (-34.0, 1.8, 4.2), (-28.0, 1.2, 2.2), (-24.5, 0.6, 1.2)], x)
            hr2.append(section_x(x, W, H, n=28, p=3.0, warp=lambda v, s=s: strata(v + Vector((0, s * 6.4, 0)), 0.18)))
        loft(b, body_m, hr2)
        # 後爪
        b.rock(clad, (6.0, 2.0, 1.6), (-27.0, s * 7.9, 0.75), rough=0.05, subdiv=2, seed=60 + s, round_=0.5)
    # 尾巴：繞南側臀部
    b.rock(body_m, (10.0, 0.9, 0.7), (-38.0, -7.6, 1.3), rot=(0, 0, 0.1), rough=0.1, subdiv=3, seed=21)
    # 南側下方的修補扶壁石塊（參考照中可見）
    for x, w, h in ((-31.0, 5.5, 2.6), (-16.0, 4.0, 2.2), (-3.0, 4.5, 3.0)):
        b.box_base(clad, (w, 1.6, h), (x, -6.9, 0.0))

    # 兩爪之間的夢之碑（紅花崗岩）與祭壇
    b.box_base(granite, (0.7, 2.6, 3.6), (17.6, 0, 0))
    b.box_base(clad, (3.0, 4.0, 0.9), (24.0, 0, 0))

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
            b.rock(bedrock, (L / n * 1.3, 6.0, hh + 1.0), (cx, cy, hh / 2 - 0.5), rot=(0, 0, ang), rough=0.1, subdiv=3, seed=seed + i, round_=0.1)

    cliff(-62, -58, -62, 56, wall_h, 100)       # 西側
    cliff(-62, 52, 30, 52, wall_h - 0.5, 200)    # 北側
    cliff(-62, -58, -14, -58, wall_h - 1.0, 300)  # 南側（東段較開闊）
    # 北側岩壁上的現代石砌護牆（參考照背景的長牆）
    b.box_base(wall_m, (92, 1.2, 2.4), (-16, 55.5, wall_h - 1.4))
    # 上方台地（實心）
    for sx, sy, w, d, h in ((-79, -2, 30, 124, wall_h - 0.8), (-16, 65, 102, 24, wall_h - 1.2), (-38, -66, 50, 12, wall_h - 1.6)):
        b.box_base(floor_m, (w, d, h + 1.0), (sx, sy, -1.0))
    # 地面散落石塊
    for i in range(26):
        x, y = b.rng.uniform(-55, 50), b.rng.choice([-1, 1]) * b.rng.uniform(14, 40)
        sz = b.rng.uniform(0.4, 1.4)
        b.rock(bedrock, (sz, sz * 0.8, sz * 0.6), (x, y, sz * 0.25), rough=0.15, subdiv=2, seed=400 + i)
    b.export(path)
