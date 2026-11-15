"""motherland 伏爾加格勒「祖國母親在召喚」雕像寫實模型（公尺）

- 位於馬馬耶夫崗頂；女性人像高約 52 m（至頭頂），右手高舉 33 m 長劍，連劍總高約 85 m
- 姿態：左腿向前跨步、右腿在後腳跟抬起；左臂向前側伸展張開手掌；頭向左轉、微仰、張口吶喊；
  頭髮與身後披肩被風高高吹起；貼身長裙前方被風壓貼在腿上（顯出大腿、膝蓋），身後大量縱向衣褶向後飄
- 預力混凝土外表為略帶暖灰的淺灰色、有修補斑駁；立於約 2 m 高的長方形混凝土基座

建模方式：人體與衣物以「符號距離場（SDF）」雕塑——骨盆、胸廓、乳房、三角肌、頸部胸鎖乳突肌、
頭顱／眉骨／顴骨／鼻／張開的下顎與口腔／耳、手臂肌肉、拳頭與五指、腿部等以平滑聯集組合；
衣褶、髮束以程式位移（依環繞角的 |sin| 波形加雜訊扭曲：圓脊、深谷）刻在距離場上；
以 numpy 在窄帶細格（約 0.15 m）上求值，用 surface nets 抽出等值面，再平滑、減面。
飛揚的披肩為參數曲面＋厚度（沿飄動方向的縱褶與波浪），長劍為獨立的稜角幾何。

座標：雕像面向 -Y（前方），+X 為她的左側；基座頂面 z = 2。參考照由正前方偏右手側的坡下仰拍。
"""

import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

from lib import TEX, Builder
from buildings.kinkakuji import GEN, AsiaBuilder, _cloud, _height_to_normal, _save_maps

CAMERA = ((2.0, 0.0, 38.0), -22.0, -20.0, 110.0, 26)

BASE_Z = 2.0
VOX = float(os.environ.get("MOTHERLAND_VOX", "0.15"))


# ====================================================================== SDF 工具（numpy，P 為 (N,3)）
def _len(v):
    return np.sqrt(np.einsum("ij,ij->i", v, v))


def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def cone(P, a, b, ra, rb):
    """圓錐膠囊（兩端半徑不同）近似距離"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ba = b - a
    pa = P - a
    t = np.clip(pa @ ba / (ba @ ba), 0.0, 1.0)
    return _len(pa - t[:, None] * ba) - (ra + (rb - ra) * t)


def ell(P, c, rad, R=None):
    """橢球近似距離（R 為局部軸作為欄的旋轉矩陣）"""
    q = P - np.asarray(c, float)
    if R is not None:
        q = q @ R
    rad = np.asarray(rad, float)
    k0 = _len(q / rad)
    k1 = _len(q / (rad * rad))
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)


def sph(P, c, r):
    return _len(P - np.asarray(c, float)) - r


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def frame_from(fwd, up=(0, 0, 1)):
    """回傳以 (side, fwd, up) 為欄的矩陣"""
    f = np.asarray(fwd, float)
    f /= np.linalg.norm(f)
    u = np.asarray(up, float) - f * (f @ np.asarray(up, float))
    u /= np.linalg.norm(u)
    s = np.cross(f, u)
    return np.stack([s, f, u], 1)


_rng = np.random.default_rng(17)
_LAT = _rng.random((32, 32, 32))


def vnoise(P):
    """週期性值雜訊，輸出約 -1..1"""
    i = np.floor(P).astype(np.int64)
    f = P - i
    f = f * f * (3 - 2 * f)
    out = np.zeros(len(P))
    for ox in (0, 1):
        wx = f[:, 0] if ox else 1 - f[:, 0]
        for oy in (0, 1):
            wy = f[:, 1] if oy else 1 - f[:, 1]
            for oz in (0, 1):
                wz = f[:, 2] if oz else 1 - f[:, 2]
                out += _LAT[(i[:, 0] + ox) % 32, (i[:, 1] + oy) % 32, (i[:, 2] + oz) % 32] * wx * wy * wz
    return out * 2 - 1


def fbm(P, oct_=3):
    v, a, s = 0.0, 0.6, 1.0
    for _ in range(oct_):
        v = v + vnoise(P * s) * a
        s *= 2.03
        a *= 0.5
    return v


# ====================================================================== 姿態（世界座標，腳底 z=0，之後整體抬高至基座頂）
SH_R = np.array([-5.7, -0.6, 43.4])
EL_R = SH_R + 9.4 * np.array([-0.60, -0.10, 0.79]) / np.linalg.norm([-0.60, -0.10, 0.79])
WR_R = EL_R + 7.8 * np.array([-0.38, -0.06, 0.92]) / np.linalg.norm([-0.38, -0.06, 0.92])
FIST = WR_R + 1.6 * (WR_R - EL_R) / np.linalg.norm(WR_R - EL_R)

SH_L = np.array([5.9, -1.3, 42.4])
_dl1 = np.array([0.88, -0.40, -0.16]) / np.linalg.norm([0.88, -0.40, -0.16])
EL_L = SH_L + 9.0 * _dl1
_dl2 = np.array([0.88, -0.44, -0.12]) / np.linalg.norm([0.88, -0.44, -0.12])
WR_L = EL_L + 7.6 * _dl2

HEAD_C = np.array([0.9, -1.4, 49.3])
_yaw, _pitch = math.radians(68), math.radians(14)
HEAD_F = np.array([math.sin(_yaw) * math.cos(_pitch), -math.cos(_yaw) * math.cos(_pitch), math.sin(_pitch)])
HR = frame_from(HEAD_F, (0.05, 0.25, 1.0))   # 頭部局部軸（side, fwd, up）
NECK_B = np.array([0.4, -1.1, 43.6])

HIP_L, KN_L, AN_L, TO_L = np.array([2.4, 0.0, 26.0]), np.array([2.9, -4.6, 14.2]), np.array([3.2, -5.7, 2.0]), np.array([3.5, -9.4, 0.55])
HIP_R, KN_R, AN_R, TO_R = np.array([-2.5, 0.8, 26.0]), np.array([-2.8, -1.0, 13.6]), np.array([-3.0, 4.4, 3.0]), np.array([-3.2, 1.2, 0.55])


def head_sdf(P):
    q = (P - HEAD_C) @ HR          # (s, f, u)
    S = 1.0
    q = q / S
    d = ell(q, (0, -0.35, 0.65), (2.7, 3.1, 2.9))                       # 顱
    d = smin(d, ell(q, (0, 1.2, -0.9), (2.35, 1.9, 2.25)), 0.9)          # 面部
    d = smin(d, ell(q, (0, 1.55, 1.75), (1.95, 1.1, 1.45)), 0.6)          # 額
    d = smin(d, cone(q, (-1.4, 2.3, 0.95), (1.4, 2.3, 0.95), 0.58, 0.58), 0.35)   # 眉骨
    for sx in (-1, 1):
        d = smin(d, sph(q, (sx * 1.55, 1.75, -0.05), 0.75), 0.5)          # 顴骨
        d = smin(d, cone(q, (sx * 1.95, -0.5, -1.0), (sx * 0.7, 1.75, -3.05), 0.72, 0.62), 0.6)  # 下顎骨
        d = smin(d, ell(q, (sx * 2.42, -0.35, 0.05), (0.32, 0.72, 1.0)), 0.25)  # 耳
    d = smin(d, ell(q, (0, 1.85, -3.35), (1.05, 0.95, 0.85)), 0.6)        # 下巴（張口下垂）
    # 鼻
    d = smin(d, cone(q, (0, 2.55, 0.8), (0, 3.45, -0.75), 0.36, 0.52), 0.3)
    for sx in (-1, 1):
        d = smin(d, sph(q, (sx * 0.46, 2.82, -0.72), 0.33), 0.2)
    # 眼窩與眼球
    for sx in (-1, 1):
        d = smax(d, -sph(q, (sx * 0.88, 2.75, 0.3), 0.62), 0.2)
        d = smin(d, sph(q, (sx * 0.88, 2.25, 0.3), 0.6), 0.12)
    # 張開吶喊的口：口腔凹陷＋上下唇
    d = smax(d, -ell(q, (0, 2.6, -1.95), (0.82, 1.15, 0.72)), 0.15)
    d = smin(d, cone(q, (-0.75, 2.38, -1.32), (0.75, 2.38, -1.32), 0.26, 0.26), 0.25)
    d = smin(d, cone(q, (-0.7, 2.2, -2.62), (0.7, 2.2, -2.62), 0.28, 0.28), 0.25)
    return d * S, q


def hair_sdf(P, q):
    """往後飄的頭髮：頭頂髮量＋向後（-f）並略偏右（-s）飛出的髮束；髮束上刻順向髮絲凹槽"""
    S = 1.0
    d = ell(q, (0, -1.1, 1.2), (3.0, 3.6, 3.0))
    d = smin(d, ell(q, (-0.4, -3.0, 0.4), (2.8, 2.9, 2.8)), 1.0)
    locks = [((-1.3, 0.8, 2.4), (-2.0, -4.6, 2.0), 1.15, 0.7), ((0.2, 1.0, 2.8), (-0.4, -5.0, 2.9), 1.2, 0.75),
             ((1.5, 0.6, 2.2), (1.1, -4.6, 1.6), 1.1, 0.7), ((-2.2, -0.6, 1.0), (-3.0, -4.6, -0.2), 1.1, 0.65),
             ((2.2, -0.8, 0.8), (1.7, -4.4, -0.6), 1.0, 0.6), ((-1.6, -1.8, -0.6), (-2.3, -4.6, -2.2), 1.1, 0.6),
             ((1.0, -2.2, -0.8), (0.4, -4.5, -2.4), 1.1, 0.6), ((-2.0, -2.5, 1.5), (-4.2, -6.4, 0.8), 1.0, 0.55),
             ((-1.0, -2.8, -0.2), (-2.8, -6.8, -1.6), 1.0, 0.5), ((0.4, -2.0, 2.4), (-1.6, -6.6, 2.0), 0.9, 0.45)]
    for a, b, ra, rb in locks:
        d = smin(d, cone(q, a, b, ra, rb), 0.9)
    # 不讓頭髮蓋住臉：以臉前的平面切掉
    d = smax(d, (q[:, 1] - (1.2 + 0.35 * np.maximum(q[:, 2], 0))), 0.3)
    d = smax(d, -(q[:, 2] + 1.6 - 0.45 * np.maximum(-q[:, 1], 0)), 0.4)
    groove = np.abs(np.sin(q[:, 0] * 4.2 + q[:, 2] * 1.2 + fbm(q * 0.6) * 1.5))
    d = d - 0.16 * (groove - 0.5)
    return d * S


def arm_sdf(P):
    d = 1e9
    # 右臂（高舉）
    d = smin(d, sph(P, SH_R + (0, 0.3, -0.2), 2.6), 0.6)                     # 三角肌
    d = smin(d, cone(P, SH_R, EL_R, 2.35, 1.55), 0.8)
    mid = SH_R + 0.45 * (EL_R - SH_R)
    d = smin(d, ell(P, mid + (0.2, -0.9, 0), (1.3, 1.25, 2.9), frame_from(EL_R - SH_R, (0, -1, 0))[:, [0, 2, 1]]), 0.6)  # 二頭肌
    d = smin(d, sph(P, EL_R, 1.25), 0.6)
    d = smin(d, cone(P, EL_R, WR_R, 1.75, 1.05), 0.7)
    d = smin(d, ell(P, EL_R + 0.3 * (WR_R - EL_R) + (0, -0.4, 0), (1.25, 1.1, 2.4), frame_from(WR_R - EL_R, (0, -1, 0))[:, [0, 2, 1]]), 0.5)
    # 拳頭：手掌塊＋四指指節＋拇指
    ax = (WR_R - EL_R) / np.linalg.norm(WR_R - EL_R)
    Rf = frame_from(ax, (0, -1, 0))
    s, f, u = Rf[:, 0], Rf[:, 1], Rf[:, 2]       # f = 前臂方向, u = 手背朝前(-Y)
    d = smin(d, ell(P, FIST, (1.3, 1.75, 1.3), Rf), 0.5)
    for k in range(4):
        c = FIST + f * (1.05 - 0.55 * k) - u * 0.15
        d = smin(d, cone(P, c + s * 1.0 + u * 0.6, c - s * 0.9 + u * 0.55, 0.42, 0.42), 0.25)
    d = smin(d, cone(P, FIST + f * 0.2 + s * 1.2 - u * 0.4, FIST + f * 0.9 - s * 0.2 + u * 0.95, 0.42, 0.38), 0.25)
    # 左臂（向前側平伸）
    d = smin(d, sph(P, SH_L + (0, 0.1, 0.1), 2.5), 0.6)
    d = smin(d, cone(P, SH_L, EL_L, 2.25, 1.5), 0.8)
    d = smin(d, sph(P, EL_L, 1.2), 0.6)
    d = smin(d, cone(P, EL_L, WR_L, 1.7, 1.0), 0.7)
    d = smin(d, ell(P, EL_L + 0.28 * (WR_L - EL_L) + (0, 0, 0.35), (1.2, 1.05, 2.3), frame_from(WR_L - EL_L, (0, 0, 1))[:, [0, 2, 1]]), 0.5)
    # 張開的手掌：掌面朝前下，四指張開、略上翹，拇指朝前
    dh = (WR_L - EL_L) / np.linalg.norm(WR_L - EL_L)
    n = np.array([0.15, -0.55, -0.82])
    n = n - dh * (n @ dh)
    n /= np.linalg.norm(n)
    w = np.cross(n, dh)
    pc = WR_L + dh * 1.5
    d = smin(d, ell(P, pc, (1.25, 1.65, 0.5), np.stack([w, dh, n], 1)), 0.45)
    for k, (off, L, spread) in enumerate(((-0.95, 2.3, -0.30), (-0.32, 2.7, -0.10), (0.32, 2.85, 0.08), (0.95, 2.45, 0.26))):
        base = pc + dh * 1.4 + w * off
        dirf = dh + w * spread - n * 0.18
        dirf /= np.linalg.norm(dirf)
        mid = base + dirf * L * 0.55 - n * 0.05
        tip = base + dirf * L - n * 0.25
        d = smin(d, cone(P, base, mid, 0.36, 0.32), 0.2)
        d = smin(d, cone(P, mid, tip, 0.32, 0.26), 0.15)
    tb = pc - dh * 0.5 + w * 0.9
    td = (dh * 0.55 + w * 0.6 - n * 0.6)
    td /= np.linalg.norm(td)
    d = smin(d, cone(P, tb, tb + td * 2.4, 0.45, 0.32), 0.3)
    return d


def torso_sdf(P):
    lean = rot_x(0.16)
    d = ell(P, (0.0, 0.7, 27.4), (5.3, 3.7, 4.1))                                 # 骨盆
    d = smin(d, ell(P, (0.1, -0.3, 32.3), (4.2, 3.0, 3.8), lean), 1.6)           # 腰腹
    d = smin(d, ell(P, (0.3, -1.1, 37.6), (4.8, 3.3, 4.8), lean), 1.6)           # 胸廓
    for sx in (-1, 1):
        d = smin(d, sph(P, (0.3 + sx * 2.1, -3.3, 38.2), 1.45), 1.0)              # 乳房
        d = smin(d, ell(P, (0.3 + sx * 1.9, -2.6, 40.2), (1.9, 1.0, 1.4), lean), 0.8)  # 胸大肌
    d = smin(d, cone(P, SH_R + (0.3, 0.2, 0.0), SH_L + (-0.3, 0.2, 0.0), 1.55, 1.55), 1.3)  # 肩胛／斜方肌
    d = smin(d, ell(P, (0.3, 1.2, 39.5), (4.5, 2.0, 4.2), lean), 1.2)             # 背
    return d


def neck_sdf(P):
    top = HEAD_C - HR[:, 2] * 2.4 - HR[:, 1] * 0.6
    d = cone(P, NECK_B, top, 2.25, 1.85)
    st = np.array([0.4, -2.7, 43.4])
    for sx in (-1, 1):
        ear = HEAD_C - HR[:, 1] * 0.45 - HR[:, 2] * 1.3 + HR[:, 0] * sx * 1.6
        d = smin(d, cone(P, ear, st + (sx * 0.5, 0, 0), 0.55, 0.45), 0.5)            # 胸鎖乳突肌
    return d


def legs_sdf(P, inflate=0.0):
    d = 1e9
    for hip, kn, an, to, br in ((HIP_L, KN_L, AN_L, TO_L, 1.0), (HIP_R, KN_R, AN_R, TO_R, 0.95)):
        d = smin(d, cone(P, hip, kn, 3.1 + inflate, 2.0 + inflate), 1.0)
        th = hip + 0.45 * (kn - hip)
        d = smin(d, ell(P, th + (0, -1.0, 0), (2.3 + inflate, 1.8 + inflate, 4.0), frame_from(kn - hip, (0, -1, 0))[:, [0, 2, 1]]), 0.8)
        d = smin(d, sph(P, kn + (0, -0.4, 0), 1.75 + inflate), 0.6)
        d = smin(d, cone(P, kn, an, 1.9 + inflate, 1.0 + inflate), 0.8)
        cf = kn + 0.3 * (an - kn)
        d = smin(d, ell(P, cf + (0, 0.6, 0), (1.4 + inflate, 1.2 + inflate, 3.0), frame_from(an - kn, (0, 1, 0))[:, [0, 2, 1]]), 0.6)
        d = smin(d, cone(P, an, to, 1.05 * br, 0.75 * br), 0.6)   # 足
    return d


def toes_sdf(P):
    d = 1e9
    for to, an in ((TO_L, AN_L), (TO_R, AN_R)):
        fd = (to - an)
        fd[2] = 0
        fd /= np.linalg.norm(fd)
        side = np.array([-fd[1], fd[0], 0])
        for k, (o, r) in enumerate(((-0.75, 0.42), (-0.25, 0.34), (0.2, 0.32), (0.6, 0.3), (0.95, 0.27))):
            c = to + fd * (0.5 - 0.12 * abs(k - 0)) + side * o
            c[2] = max(r, 0.35)
            d = smin(d, sph(P, c, r), 0.25)
    return d


def dress_sdf(P):
    """長裙：前方貼腿（腿部膨脹 0.3 m），身後向後飄的裙擺；以環繞角 |sin| 刻出深縱褶"""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    t = np.clip((27.0 - z) / 25.0, 0.0, 1.0)
    cx = 1.3 * np.sin(np.pi * t) * t - 0.6 * t ** 3
    cy = 0.6 + 5.0 * t ** 1.3
    rx = 5.1 + 3.4 * t
    ry = 3.3 + 6.2 * t ** 1.1
    qx, qy = (x - cx) / rx, (y - cy) / ry
    lobe = (np.sqrt(qx * qx + qy * qy) - 1.0) * np.minimum(rx, ry) * 0.9
    lobe = smax(lobe, z - 30.0, 1.5)
    d = smin(legs_sdf(P, 0.45), lobe, 1.9)
    d = smin(d, ell(P, (0.0, 0.8, 28.5), (5.6, 4.0, 4.2)), 1.2)
    # 下擺：前方約到腳踝、後方拖到地面
    hem = 1.3 + 0.9 * np.clip(-(y + 2.0) / 6.0, 0, 1) - 0.8 * np.clip((y - 2.0) / 6.0, 0, 1)
    d = smax(d, hem - z, 0.35)
    # 衣褶：環繞後移中心的角度，隨高度扭轉並以雜訊彎曲；下擺處更深
    phi = np.arctan2(x - cx, y - cy)
    warp = 2.2 * fbm(P * np.array([0.09, 0.09, 0.045])) + 0.06 * z
    A = 0.2 + 0.85 * t ** 1.1
    front = np.clip((-(y - cy) / ry + 0.2), 0, 1)   # 前方（貼腿）衣褶較淺、較寬
    nf = 7.5 - 2.5 * front
    folds = np.abs(np.sin(nf * phi + warp))
    fine = np.abs(np.sin(2.3 * nf * phi + 1.7 * warp + 0.9))
    d = d - A * (1 - 0.6 * front) * (folds - 0.55) - 0.18 * A * (fine - 0.6)
    return d


def chiton_sdf(P):
    """上身貼身衣：胸前斜向細褶、腰間一條斜捲的衣帶；右肩以上為裸露肌膚（另行聯集）"""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    d = torso_sdf(P) - 0.25
    # 領口：從左肩斜到右腋下
    neck = z - (41.6 + 0.3 * x)
    d = smax(d, neck, 0.4)
    ang = np.arctan2(x, y + 0.4)
    folds = np.abs(np.sin(5.0 * ang + 0.45 * z + 1.6 * fbm(P * 0.12)))
    d = d - 0.12 * (folds - 0.5)
    # 腰帶捲：沿腰圍的一圈膠囊（左低右高）
    ring = []
    for k in range(18):
        a = math.tau * k / 18
        ring.append((0.1 + 4.05 * math.sin(a), -0.15 - 3.05 * math.cos(a), 31.4 - 1.6 * math.sin(a)))
    for a, b in zip(ring, ring[1:] + ring[:1]):
        d = smin(d, cone(P, a, b, 0.45, 0.45), 0.6)
    roll = np.abs(np.sin(np.arctan2(x, y) * 7.0 + 0.8 * z))
    d = d - 0.08 * roll
    return d


def drape_sdf(P):
    """右肩後垂到右臀側的披肩垂墜部分（縱向大褶）＋左上臂短袖"""
    d = cone(P, (-4.6, 1.6, 42.6), (-7.0, 3.0, 29.0), 2.0, 3.3)
    d = smin(d, cone(P, (-7.0, 3.0, 29.0), (-7.6, 4.2, 22.5), 3.3, 1.3), 1.2)
    d = smin(d, cone(P, (-2.0, 2.4, 42.0), (-5.5, 4.2, 33.0), 1.3, 1.6), 1.0)
    ang = np.arctan2(P[:, 0] + 5.5, P[:, 1] - 2.5)
    fold = np.abs(np.sin(6.0 * ang + 0.12 * P[:, 2] + fbm(P * 0.18)))
    d = d - 0.35 * (fold - 0.5)
    # 左上臂短袖
    sl = cone(P, SH_L + (-0.6, 0.2, 0.4), SH_L + 0.42 * (EL_L - SH_L), 2.8, 2.45)
    sang = np.arctan2(P[:, 1] - SH_L[1], P[:, 2] - SH_L[2])
    sl = sl - 0.14 * (np.abs(np.sin(7 * sang + 0.3 * P[:, 0])) - 0.5)
    sl = smax(sl, -cone(P, SH_L + 0.42 * (EL_L - SH_L) + 0.5 * _dl1, SH_L + 2.0 * _dl1 * 9, 1.4, 1.4), 0.3)
    return smin(d, sl, 0.6)


def figure_sdf(P):
    hd, q = head_sdf(P)
    d = smin(hd, hair_sdf(P, q), 0.35)
    d = smin(d, neck_sdf(P), 0.9)
    skin_torso = torso_sdf(P)
    d = smin(d, skin_torso, 1.0)
    d = smin(d, chiton_sdf(P), 0.15)
    d = smin(d, arm_sdf(P), 0.6)
    d = smin(d, dress_sdf(P), 0.5)
    d = smin(d, drape_sdf(P), 0.6)
    d = smin(d, legs_sdf(P) , 0.3)
    d = smin(d, toes_sdf(P), 0.2)
    # 細微表面起伏（混凝土澆鑄的不平）
    d = d - 0.04 * vnoise(P * 0.9)
    return np.maximum(d, -P[:, 2] - 0.0)


# ====================================================================== 等值面抽取（窄帶 + surface nets）
def sample_grid(fn, lo, hi, h):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    H = h * 4
    nc = np.ceil((hi - lo) / H).astype(int) + 1
    gc = np.stack(np.meshgrid(*[lo[i] + H * np.arange(nc[i]) for i in range(3)], indexing="ij"), -1).reshape(-1, 3)
    Dc = np.concatenate([fn(gc[i:i + 400000]) for i in range(0, len(gc), 400000)]).reshape(nc)
    nf = (nc - 1) * 4 + 1
    # 粗格三線性內插到細格
    F = np.empty(nf, np.float32)
    ix = np.arange(nf[0]) / 4.0
    iy = np.arange(nf[1]) / 4.0
    iz = np.arange(nf[2]) / 4.0
    x0 = np.minimum(np.floor(ix).astype(int), nc[0] - 2)
    y0 = np.minimum(np.floor(iy).astype(int), nc[1] - 2)
    z0 = np.minimum(np.floor(iz).astype(int), nc[2] - 2)
    fx, fy, fz = ix - x0, iy - y0, iz - z0
    for a in range(nf[0]):
        i0, tx = x0[a], fx[a]
        sl = Dc[i0] * (1 - tx) + Dc[i0 + 1] * tx                     # (ny_c, nz_c)
        s2 = sl[y0] * (1 - fy)[:, None] + sl[y0 + 1] * fy[:, None]    # (ny_f, nz_c)
        F[a] = s2[:, z0] * (1 - fz)[None] + s2[:, z0 + 1] * fz[None]
    band = np.abs(F) < H * 1.6
    idx = np.nonzero(band)
    pts = np.stack([lo[0] + h * idx[0], lo[1] + h * idx[1], lo[2] + h * idx[2]], 1)
    vals = np.concatenate([fn(pts[i:i + 300000]) for i in range(0, len(pts), 300000)])
    F[idx] = vals
    print(f"  sdf grid {tuple(nf)}  band pts {len(pts)}", flush=True)
    return F


def surface_nets(F, lo, h):
    inside = F < 0
    nx, ny, nz = F.shape
    cnt = np.zeros((nx - 1, ny - 1, nz - 1), np.uint8)
    for ox in (0, 1):
        for oy in (0, 1):
            for oz in (0, 1):
                cnt += inside[ox:nx - 1 + ox, oy:ny - 1 + oy, oz:nz - 1 + oz]
    act = (cnt > 0) & (cnt < 8)
    ci = np.nonzero(act)
    M = len(ci[0])
    vid = np.full(act.shape, -1, np.int32)
    vid[ci] = np.arange(M, dtype=np.int32)
    acc = np.zeros((M, 3))
    num = np.zeros(M)
    corners = [(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)]
    edges = [(p, q) for p in corners for q in corners if p < q and sum(abs(p[i] - q[i]) for i in range(3)) == 1]
    for p, q in edges:
        fa = F[ci[0] + p[0], ci[1] + p[1], ci[2] + p[2]].astype(float)
        fb = F[ci[0] + q[0], ci[1] + q[1], ci[2] + q[2]].astype(float)
        m = (fa < 0) != (fb < 0)
        t = np.where(m, fa / np.where(m, fa - fb, 1.0), 0.0)
        for k in range(3):
            acc[:, k] += np.where(m, p[k] + t * (q[k] - p[k]), 0.0)
        num += m
    verts = np.stack(ci, 1) + acc / np.maximum(num, 1)[:, None]
    verts = np.asarray(lo) + verts * h
    faces = []
    # x 向邊
    e = inside[:-1, 1:-1, 1:-1] != inside[1:, 1:-1, 1:-1]
    i, j, k = np.nonzero(e)
    j, k = j + 1, k + 1
    q = np.stack([vid[i, j - 1, k - 1], vid[i, j, k - 1], vid[i, j, k], vid[i, j - 1, k]], 1)
    flip = ~inside[i, j, k]
    q[flip] = q[flip][:, ::-1]
    faces.append(q)
    e = inside[1:-1, :-1, 1:-1] != inside[1:-1, 1:, 1:-1]
    i, j, k = np.nonzero(e)
    i, k = i + 1, k + 1
    q = np.stack([vid[i - 1, j, k - 1], vid[i - 1, j, k], vid[i, j, k], vid[i, j, k - 1]], 1)
    flip = ~inside[i, j, k]
    q[flip] = q[flip][:, ::-1]
    faces.append(q)
    e = inside[1:-1, 1:-1, :-1] != inside[1:-1, 1:-1, 1:]
    i, j, k = np.nonzero(e)
    i, j = i + 1, j + 1
    q = np.stack([vid[i - 1, j - 1, k], vid[i, j - 1, k], vid[i, j, k], vid[i - 1, j, k]], 1)
    flip = ~inside[i, j, k]
    q[flip] = q[flip][:, ::-1]
    faces.append(q)
    faces = np.concatenate(faces)
    faces = faces[(faces >= 0).all(1)]
    return verts, faces


def mesh_from_arrays(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.astype(np.float32).ravel())
    me.loops.add(len(faces) * 4)
    me.loops.foreach_set("vertex_index", faces.astype(np.int32).ravel())
    me.polygons.add(len(faces))
    me.polygons.foreach_set("loop_start", np.arange(0, len(faces) * 4, 4, dtype=np.int32))
    me.polygons.foreach_set("loop_total", np.full(len(faces), 4, np.int32))
    me.update(calc_edges=True)
    me.validate()
    return me


def build_figure(b, mi, target_tris=135000):
    lo = (-15.5, -14.0, -0.2)
    hi = (26.0, 15.0, 64.5)
    F = sample_grid(figure_sdf, lo, hi, VOX)
    verts, faces = surface_nets(F, lo, VOX)
    del F
    print(f"  surface nets: {len(verts)} verts, {len(faces)} quads", flush=True)
    me = mesh_from_arrays("figure", verts, faces)
    obj = bpy.data.objects.new("figure", me)
    bpy.context.scene.collection.objects.link(obj)
    sm = obj.modifiers.new("smooth", "SMOOTH")
    sm.factor = 0.5
    sm.iterations = 3
    dec = obj.modifiers.new("dec", "DECIMATE")
    dec.ratio = min(1.0, target_tris / (2.0 * len(faces)))
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(me)
    me2.transform(Matrix.Translation((0, 0, BASE_Z)))
    start_f = len(b.bm.faces)
    b.bm.from_mesh(me2)
    bpy.data.meshes.remove(me2)
    b.bm.faces.ensure_lookup_table()
    for f in b.bm.faces[start_f:]:
        f.material_index = mi
        f.smooth = True


# ====================================================================== 披肩（參數曲面＋厚度）
def cape(b, mi, root, dirs, length, width, up, segs=(36, 22), seed=0, thick=0.55, droop=0.0, rag=0.18):
    """root 起點、dirs 為沿飄動方向的彎曲路徑（數個方向向量逐段內插）、width 寬度、up 寬度方向"""
    nu, nv = segs
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 6.28, 6)
    root = Vector(root)
    D = [Vector(d).normalized() for d in dirs]

    path = [root.copy()]
    NS = 200
    for i in range(NS):
        t = (i + 0.5) / NS
        k = min(len(D) - 2, int(t * (len(D) - 1)))
        f = t * (len(D) - 1) - k
        path.append(path[-1] + D[k].lerp(D[k + 1], f).normalized() * length / NS)

    def center(u):
        x = max(0.0, min(1.0, u)) * NS
        i = min(NS - 1, int(x))
        p = path[i].lerp(path[i + 1], x - i)
        p.z -= droop * u * u
        return p

    top, bot = [], []
    for i in range(nu + 1):
        u = i / nu
        c = center(u)
        tdir = (center(min(1.0, u + 0.03)) - center(max(0.0, u - 0.03))).normalized()
        W = (Vector(up) - tdir * tdir.dot(Vector(up))).normalized()
        N = tdir.cross(W).normalized()
        wv = width * (0.3 + 0.95 * u ** 0.6)
        W = (W * math.cos(0.5 * u) + N * math.sin(0.5 * u)).normalized()
        N = tdir.cross(W).normalized()
        rt, rb = [], []
        for j in range(nv + 1):
            v = j / nv * 2 - 1
            ue = 1 - rag * (0.5 + 0.5 * math.sin(3.3 * v + ph[0])) * (0.6 + 0.4 * math.sin(7 * v + ph[1]))
            uu = min(u, ue)
            cc = center(uu) if uu < u else c
            # 沿飄動方向的縱褶＋旗面波浪
            amp = 0.3 + 0.8 * uu
            off = (amp * 0.55 * math.sin(v * 5.2 + ph[2] + uu * 2.5) + amp * 0.3 * math.sin(v * 10.5 + ph[3] + uu * 5)
                   + 0.18 * math.sin(v * 19 + ph[5] + uu * 7) * uu + 1.3 * uu * math.sin(uu * 7 + v * 1.2 + ph[4]))
            p = cc + W * (v * wv * 0.5) + N * off
            th = thick * (1 - 0.6 * uu)
            rt.append(b.bm.verts.new(p + N * th / 2))
            rb.append(b.bm.verts.new(p - N * th / 2))
        top.append(rt)
        bot.append(rb)
    faces = []
    for i in range(nu):
        for j in range(nv):
            faces.append(b.bm.faces.new([top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]]))
            faces.append(b.bm.faces.new([bot[i][j + 1], bot[i + 1][j + 1], bot[i + 1][j], bot[i][j]]))
    for i in range(nu):
        for j in (0, nv):
            faces.append(b.bm.faces.new([top[i][j], bot[i][j], bot[i + 1][j], top[i + 1][j]]))
    for j in range(nv):
        faces.append(b.bm.faces.new([top[nu][j], top[nu][j + 1], bot[nu][j + 1], bot[nu][j]]))
        faces.append(b.bm.faces.new([top[0][j + 1], top[0][j], bot[0][j], bot[0][j + 1]]))
    for f in faces:
        f.material_index = mi
        f.smooth = True


# ====================================================================== 長劍
def sword(b, mi, fist, tip):
    fist, tip = Vector(fist), Vector(tip)
    d = (tip - fist).normalized()
    xw = Vector((0.15, 1, 0)).cross(d).normalized()     # 劍身寬向
    yw = d.cross(xw)
    R = Matrix((xw, yw, d)).transposed().to_4x4()

    def ring(pts, M):
        return [b.bm.verts.new(M @ Vector(p)) for p in pts]

    def loft(rings, close_top=True):
        fs = [b.bm.faces.new(list(reversed(rings[0])))]
        for a, c in zip(rings, rings[1:]):
            n = len(a)
            for i in range(n):
                j = (i + 1) % n
                fs.append(b.bm.faces.new([a[i], a[j], c[j], c[i]]))
        if close_top:
            fs.append(b.bm.faces.new(rings[-1]))
        for f in fs:
            f.material_index = mi
            f.smooth = False

    M0 = Matrix.Translation(fist) @ R
    # 握柄（穿過拳）與柄頭
    oct_ = [(0.42 * math.cos(math.tau * i / 8), 0.42 * math.sin(math.tau * i / 8)) for i in range(8)]
    loft([ring([(x, y, z) for x, y in oct_], M0) for z in (-3.6, 2.2)])
    loft([ring([(x * 1.5, y * 1.5, z) for x, y in oct_], M0) for z in (-4.3, -3.6)])
    # 護手：長方橫桿
    g = [(-3.4, -0.55), (3.4, -0.55), (3.4, 0.55), (-3.4, 0.55)]
    loft([ring([(x, y, z) for x, y in g], M0) for z in (2.2, 3.15)])
    # 劍身：菱形斷面帶中脊，底寬 2.1 m → 尖端
    L = (tip - fist).length - 3.15
    M1 = Matrix.Translation(fist + d * 3.15) @ R
    sec = lambda w, t: [(w, 0, 0), (w * 0.55, t, 0), (-w * 0.55, t, 0), (-w, 0, 0), (-w * 0.55, -t, 0), (-w * 0.55, -t, 0)]
    rings = []
    for z, w, t in ((0.0, 1.05, 0.34), (L * 0.5, 0.95, 0.30), (L * 0.88, 0.8, 0.26)):
        rings.append(ring([(x, y, zz + z) for x, y, zz in [(w, 0, 0), (w * 0.5, t, 0), (-w * 0.5, t, 0), (-w, 0, 0), (-w * 0.5, -t, 0), (w * 0.5, -t, 0)]], M1))
    apex = b.bm.verts.new(M1 @ Vector((0, 0, L)))
    loft(rings, close_top=False)
    for i in range(6):
        f = b.bm.faces.new([rings[-1][i], rings[-1][(i + 1) % 6], apex])
        f.material_index = mi
    _ = sec


# ====================================================================== 材質
def gen_concrete():
    """略帶暖灰的混凝土：大片修補斑塊、細微斑駁與澆置接縫"""
    out = os.path.join(GEN, "ml_concrete4")
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return out
    from PIL import Image

    N = 1024
    rng = np.random.default_rng(11)
    base = np.array((178, 170, 154), float)
    lum = 1 + _cloud(rng, N, 128, 0.10) + _cloud(rng, N, 24, 0.07) + _cloud(rng, N, 4, 0.05)
    # 修補斑塊：圓角矩形，略深略灰
    yy, xx = np.mgrid[0:N, 0:N]
    patch = np.zeros((N, N))
    for _ in range(26):
        cx, cy = rng.uniform(0, N, 2)
        w, h = rng.uniform(25, 110), rng.uniform(15, 70)
        dx = np.minimum(np.abs(xx - cx), N - np.abs(xx - cx))
        dy = np.minimum(np.abs(yy - cy), N - np.abs(yy - cy))
        m = np.clip(1.0 - np.maximum(dx / w, dy / h), 0, 0.25) * 4
        patch = np.maximum(patch, m * rng.uniform(0.5, 1.0))
    lum = lum - 0.05 * patch * (1 + _cloud(rng, N, 16, 0.6))
    diff = base[None, None] * lum[..., None]
    diff[..., 2] *= 1 - 0.03 * patch
    nor = np.asarray(Image.open(os.path.join(TEX, "plastered_wall_04", "nor.jpg")).convert("RGB").resize((N, N)), float)
    _save_maps(out, diff, nor, size=1024)
    return out


def motherland(path):
    b = AsiaBuilder("Motherland", seed=5)
    concrete = b.gtex("concrete", gen_concrete(), tile=16.0, rough=0.9, normal=0.5)
    steel = b.color("sword", "#8a8276", rough=0.5, metal=0.35)
    base_c = b.ptex("base", "plastered_wall_04", tile=5.0, tint="#c9c4b8", rough=0.85, normal=0.4)
    path_c = b.ptex("path", "gravel_floor", tile=2.5, tint="#a8a296", rough=0.9, normal=0.3)
    grass = b.ptex("grass", "grass_ground", tile=6.0, tint="#6b8a3c", gain=0.95, rough=0.95, normal=0.3)
    soil = b.color("soil", "#6b5a45", rough=0.95)

    # ---------------------------------------------------------------- 山崗頂草坪與基座
    b.ground_disc(grass, 150, soil, depth=25, rings=24, seg=96, height_fn=lambda x, y: -0.0009 * (x * x + y * y))
    b.box_base(path_c, (44.0, 40.0, 0.35), (1.0, 1.5, -0.25))
    b.box_base(base_c, (33.0, 29.0, 0.45), (1.0, 1.5, 0.0))
    b.box_base(base_c, (30.0, 26.0, BASE_Z - 0.45), (1.0, 1.5, 0.45))
    b.box_base(path_c, (5.0, 40.0, 0.3), (-1.0, -38.0, -0.0009 * 38 * 38 - 0.15), rot=(0.06, 0, 0.06))

    build_figure(b, concrete)
    # 身後被風吹起的披肩：上層（肩高、向後偏右平飛）與下層（腰高、向後下垂）
    Z = BASE_Z
    cape(b, concrete, (-3.2, 3.2, Z + 41.0), [(-0.45, 0.85, 0.05), (-0.3, 0.95, 0.1), (-0.2, 0.97, 0.12)], 17.0, 6.0, (0.1, 0.0, 1.0),
         seed=1, thick=0.7, droop=-1.0, rag=0.16)
    cape(b, concrete, (-4.6, 2.8, Z + 35.0), [(-0.5, 0.8, -0.2), (-0.35, 0.9, -0.3), (-0.25, 0.9, -0.45)], 10.5, 4.6, (0.2, 0.0, 1.0),
         seed=2, thick=0.6, droop=0.5, rag=0.22)
    fist = Vector(FIST) + Vector((0, 0, Z))
    tip = fist + Vector((0.52, -0.08, 0.85)).normalized() * 32.5
    sword(b, steel, fist, tip)
    b.export_glb(path)
