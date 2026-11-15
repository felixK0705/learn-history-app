"""giza 寫實模型（尺寸依實測資料，公尺）

座標：以古夫金字塔中心為原點，+X 東、+Y 北（依經緯度換算）。
- 古夫：底 230.3 m、原高 146.6 m、現高 138.5 m
- 卡夫拉：底 215.3 m、原高 143.5 m、現高 136.4 m，頂端保留原始石灰岩外殼，地勢高約 10 m
- 孟卡拉：底 102.2 × 104.6 m、原高 65.5 m、現高 61 m
- 獅身人面像：長 73 m、寬 19 m、高 20 m，面向正東，位於鑿出的圍坑中

做法重點：
- 金字塔：逐層石階幾何（每層有不規則退縮與崩角），每層豎面以自產的「石塊排列」貼圖（每層一條帶狀 UV），
  階面以碎石積沙貼圖；卡夫拉頂部為平滑外殼。頂點色做風化色差。
- 地面：以 Delaunay 不規則三角網做自適應解析度（預覽相機前景密、遠處疏），沙丘起伏、車轍（約束邊做出
  銳利邊界的帶狀面）、碎石斑；自產無明顯重複的細沙貼圖；地景延伸到約 2.6 km 並在邊緣淡入地平線色調。
- 自產貼圖以 numpy 程式產生，快取於 blender/textures/_gen/giza_v*/。
"""

import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector, noise
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt

from lib import TAU, TEX, Builder

# 預覽相機（同 build.py CAMS 格式：目標點、方位角、仰角、距離、焦距）
# 依參考照（All Gizah Pyramids，西南方沙丘上平視東北）以特徵點反推相機位置約為 (-687, -1191, 36)
CAMERA = ((-429.0, -540.0, 49.4), 338.4, -1.1, 700.0, 56)

GEN = os.path.join(TEX, "_gen", "giza_v1")


# ====================================================================== 程式產生貼圖（numpy）
def _pnoise(shape, feat, rng):
    """可無縫拼接的高斯濾波雜訊（feat = 特徵尺寸，像素），標準化為平均 0、標準差 1"""
    n, m = shape
    w = rng.standard_normal((n, m))
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(m)[None, :]
    s = feat / 2.0
    g = np.exp(-2 * (np.pi * s) ** 2 * (fx**2 + fy**2))
    r = np.real(np.fft.ifft2(np.fft.fft2(w) * g))
    r -= r.mean()
    return r / (r.std() + 1e-9)


def _pfbm(shape, feat, rng, octaves=4, gain=0.5):
    t = np.zeros(shape)
    a = 1.0
    for _ in range(octaves):
        t += a * _pnoise(shape, feat, rng)
        a *= gain
        feat = max(1.0, feat / 2.0)
    return t / (t.std() + 1e-9)


def _normal_map(h, strength):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength
    nx, ny, nz = -dx, dy, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / ln, ny / ln, nz / ln], -1)
    return (np.clip(n * 0.5 + 0.5, 0, 1) * 255).astype(np.uint8)


def _save(arr, name):
    from PIL import Image

    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(os.path.join(GEN, name), quality=90)


def _rock_detail(size):
    """取 rock_04 的灰階細節作為石面微紋理（平鋪到指定大小）"""
    from PIL import Image

    im = Image.open(os.path.join(TEX, "rock_04", "diff.jpg")).convert("L").resize((1024, 1024))
    a = np.asarray(im, dtype=np.float64) / 255.0
    a = a / a.mean()
    reps = (size[0] // 1024 + 1, size[1] // 1024 + 1)
    return np.tile(a, reps)[: size[0], : size[1]]


def gen_sand(rng):
    """細沙：細粒、小卵石、風紋；低對比、無大尺度斑塊（避免重複感）。1024 px ≈ 4 m"""
    N = 1024
    h = 0.0 * np.zeros((N, N))
    # 風紋：約 10 cm 波長、以雜訊扭曲
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    warp = _pnoise((N, N), 90, rng) * 14 + _pnoise((N, N), 30, rng) * 4
    k = 2 * np.pi * 40 / N  # 40 條／貼圖（整數，確保無縫）
    rip = np.sin(k * (yy + 0.0 * xx) + warp * 0.25)
    rip = np.sign(rip) * np.abs(rip) ** 0.7
    ripamp = 0.5 + 0.5 * _pnoise((N, N), 160, rng)
    h += rip * 0.35 * np.clip(ripamp, 0, 1)
    grain = _pnoise((N, N), 1.3, rng)
    h += grain * 0.25 + _pnoise((N, N), 6, rng) * 0.25
    col_v = 1.0 + 0.035 * grain + 0.02 * _pnoise((N, N), 12, rng) + 0.03 * rip * np.clip(ripamp, 0, 1)
    base = np.array([238, 205, 152], float)
    img = base[None, None, :] * col_v[..., None]
    # 彩色細砂粒（深、淺、偏紅）
    for frac, mul in ((0.006, (0.75, 0.7, 0.66)), (0.012, (1.05, 1.05, 1.07)), (0.004, (0.9, 0.78, 0.66))):
        m = rng.random((N, N)) < frac
        for c in range(3):
            img[..., c] = np.where(m, img[..., c] * mul[c], img[..., c])
    # 小卵石（1–4 cm）
    for _ in range(160):
        cx, cy = rng.integers(0, N, 2)
        r = rng.uniform(2.0, 8.0) * (1.0 if rng.random() < 0.8 else 1.8)
        tone = np.array(rng.choice([(0.82, 0.74, 0.64), (0.74, 0.7, 0.64), (0.95, 0.9, 0.8), (0.86, 0.72, 0.58)]))
        R = int(r + 3)
        ys = (np.arange(cy - R, cy + R + 1)) % N
        xs = (np.arange(cx - R, cx + R + 1)) % N
        gy, gx = np.meshgrid(np.arange(-R, R + 1), np.arange(-R, R + 1), indexing="ij")
        d = np.sqrt((gx * rng.uniform(0.7, 1.3)) ** 2 + gy**2) / r
        mask = np.clip(1.4 - d * 1.4, 0, 1) ** 0.6
        sub = img[np.ix_(ys, xs)]
        sub = sub * (1 - mask[..., None]) + (sub * tone[None, None, :] * (0.9 + 0.2 * rng.random())) * mask[..., None]
        img[np.ix_(ys, xs)] = sub
        hh = h[np.ix_(ys, xs)]
        h[np.ix_(ys, xs)] = hh + mask * 1.2
    _save(img, "sand_diff.jpg")
    _save(_normal_map(h, 1.6), "sand_nor.jpg")


def _blocks_band(W, Hh, rng, detail, wmin, wmax, tone_var=0.1):
    """一條石塊列：回傳 (色值倍率, 高度)；左右無縫"""
    widths = []
    while sum(widths) < W - wmax:
        widths.append(int(rng.uniform(wmin, wmax)))
    rest = W - sum(widths)
    if rest < wmin:
        widths[-1] += rest
    else:
        widths.append(rest)
    off = int(rng.integers(0, W))
    val = np.ones((Hh, W))
    hgt = np.zeros((Hh, W))
    en = _pnoise((Hh, W), 7, rng) * 4.0 + _pnoise((Hh, W), 26, rng) * 5.0 + _pnoise((Hh, W), 2, rng) * 1.2
    yy = np.arange(Hh)[:, None].astype(float)
    x0 = 0
    for w in widths:
        xs = np.arange(w)[None, :].astype(float)
        rad = rng.uniform(10, 30)
        # 距離四邊（以雜訊讓邊緣不規則、崩角）
        nb = rng.standard_normal(4)
        dl = xs + nb[0] * 2 + 3 * np.sin(yy / Hh * 3 + nb[1])
        dr = (w - 1 - xs) + nb[2] * 2 + 3 * np.sin(yy / Hh * 2.3 + nb[3])
        dt = yy - 1 + 2.5 * np.sin(xs / w * 4 + nb[0])
        db = (Hh - 1 - yy) + 2.5 * np.sin(xs / w * 3.3 + nb[2])
        cols = (np.arange(x0, x0 + w) + off) % W
        d = np.minimum(np.minimum(dl, dr), np.minimum(dt, db)) + en[:, cols]
        prof = np.clip(d / rad, 0, 1)
        prof = prof * (2 - prof)
        tone = 1.0 + rng.normal(0, tone_var)
        if rng.random() < 0.12:  # 部分石塊較深（剝落、缺損）
            tone *= rng.uniform(0.7, 0.85)
        val[:, cols] = tone * (0.3 + 0.7 * prof)
        hgt[:, cols] = prof * (0.9 + 0.2 * rng.random())
        x0 += w
    return val, hgt


def gen_blocks(rng):
    """金字塔石材圖集（2048²）：上半 4 條豎面帶（每帶 = 一個幾何石階，內含兩排石塊），下半為階面碎石積沙"""
    W = 2048
    img_v = np.ones((W, W))
    hgt = np.zeros((W, W))
    det = _rock_detail((W, W))
    pits = _pnoise((W, W), 3, rng)
    pits = np.clip(pits - 1.6, 0, None)
    blot = _pfbm((W, W), 200, rng, 3)
    for r in range(4):
        y0 = r * 256
        # 一帶兩排：上排較矮
        split = int(rng.uniform(110, 140))
        for (a, b2) in ((0, split), (split, 256)):
            v, h = _blocks_band(W, b2 - a, rng, det, 170, 430)
            img_v[y0 + a : y0 + b2] = v
            hgt[y0 + a : y0 + b2] = h
        # 幾何石階上緣（磨圓、積沙較亮）與下緣（接縫陰影）
        yy = np.arange(256)[:, None]
        img_v[y0 : y0 + 256] *= 1.0 - 0.28 * np.exp(-((255 - yy) / 7.0))
        img_v[y0 : y0 + 256] *= 1.0 + 0.08 * np.exp(-(yy / 10.0))
    top = img_v[:1024] * (0.7 + 0.3 * det[:1024]) * (1 - 0.35 * pits[:1024]) * (1 + 0.06 * blot[:1024])
    # 階面：沙與碎石
    N2 = 1024
    sandv = 1.0 + 0.05 * _pnoise((N2, W), 2, rng)
    chips = _pfbm((N2, W), 18, rng, 3)
    chip = np.clip((chips - 0.4) * 2, 0, 1)
    bot = sandv * (1 - chip) + chip * (0.78 + 0.25 * det[1024:]) * (0.85 + 0.1 * _pnoise((N2, W), 6, rng))
    gray = np.concatenate([top, bot], 0)
    base_block = np.array([214, 190, 152], float)
    base_sand = np.array([232, 204, 156], float)
    w_sand = np.zeros((W, W))
    w_sand[1024:] = 1 - chip
    # 石面帶點淡黃、灰的色斑
    hue = _pfbm((W, W), 120, rng, 3)
    colb = base_block[None, None, :] * np.stack([1 + 0.015 * hue, 1 + 0.0 * hue, 1 - 0.02 * hue], -1)
    col = colb * (1 - w_sand[..., None]) + base_sand[None, None, :] * w_sand[..., None]
    img = col * gray[..., None]
    _save(img, "block_diff.jpg")
    hgt[:1024] += 0.15 * det[:1024] - 0.6 * pits[:1024]
    hgt[1024:] = chip * 0.8 + 0.1 * _pnoise((N2, W), 3, rng)
    _save(_normal_map(hgt * 6.0, 1.0), "block_nor.jpg")


def gen_casing(rng):
    """卡夫拉頂部外殼：平滑石灰岩、淡淡的層縫、縱向雨痕。1024 px ≈ 6 m"""
    N = 1024
    det = _rock_detail((N, N))
    v = 0.96 + 0.05 * (det - 1) + 0.035 * _pfbm((N, N), 60, rng, 3)
    yy = np.arange(N)[:, None]
    seams = np.zeros((N, N))
    for k in range(6):
        y = int(k * N / 6 + rng.uniform(-8, 8)) % N
        seams += np.exp(-(((yy - y) % N) / 1.6) ** 2)
    v -= 0.08 * seams
    streak = _pnoise((N, N // 8), 6, rng)
    streak = np.repeat(streak, 8, 1)
    streak = np.clip(streak - 0.8, 0, None)
    v -= 0.05 * streak
    pits = np.clip(_pnoise((N, N), 2.5, rng) - 2.0, 0, None)
    v -= 0.25 * pits
    base = np.array([228, 214, 192], float)
    _save(base[None, None, :] * v[..., None], "casing_diff.jpg")
    _save(_normal_map(-seams * 2 - pits * 3 + 0.2 * det, 1.0), "casing_nor.jpg")


def ensure_textures():
    if os.path.exists(os.path.join(GEN, "casing_nor.jpg")):
        return
    os.makedirs(GEN, exist_ok=True)
    rng = np.random.default_rng(7)
    gen_sand(rng)
    gen_blocks(rng)
    gen_casing(rng)
