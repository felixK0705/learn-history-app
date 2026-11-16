"""合成首頁地球貼圖（參考圖風格：寫實衛星地貌、亮藍海洋、沿海岸流動的白色流紋）。

陸地：NASA Blue Marble「Land shallow topo」（公有領域，Wikimedia Commons），調高飽和並加上地形陰影。
海洋與流紋：程式產生。陸地遮罩與高程取自 three-globe 套件的 earth-water.png、earth-topology.png。
用法：python scripts/paint_globe.py <NASA 圖檔路徑>
輸出：public/textures/earth-painted.jpg、public/textures/clouds-painted.png
"""
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "node_modules/three-globe/example/img")
W, H = 4096, 2048


def gray(path):
    return np.asarray(Image.open(path).convert("L").resize((W, H), Image.LANCZOS), np.float32) / 255


def blur(arr, r):
    im = Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255


def noise(base, seed, octaves=5, persistence=0.55, w=W, h=H):
    """多層雜訊，左右可接續"""
    g = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp = total = 0.0
    amp = 1.0
    for o in range(octaves):
        n = base * 2**o
        grid = g.random((max(2, n // 2), n)).astype(np.float32)
        grid = np.concatenate([grid, grid[:, :1]], axis=1)
        im = Image.fromarray((grid * 255).astype(np.uint8)).resize((w + w // n, h), Image.BICUBIC)
        out += amp * np.asarray(im, np.float32)[:, :w] / 255
        total += amp
        amp *= persistence
    return out / total


def mix(a, b, t):
    return a + (b - a) * t[..., None]


def hexc(h):
    return np.array([int(h[i : i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)


land = 1 - gray(os.path.join(SRC, "earth-water.png"))
elev = gray(os.path.join(SRC, "earth-topology.png"))

# ---------- 陸地：NASA 衛星影像，加飽和、偏暖，並疊上地形陰影 ----------
sat = np.asarray(Image.open(sys.argv[1]).convert("RGB").resize((W, H), Image.LANCZOS), np.float32) / 255
lum = sat.mean(axis=2, keepdims=True)
col = np.clip(lum + (sat - lum) * 1.3, 0, 1)
warm = (1 - lum**3)  # 冰雪等亮白處不上色
col = col**1.3 * (1 + warm * (np.array([1.04, 0.8, 0.7], np.float32) - 1))
col *= 1 - 0.5 * np.clip(lum - 0.3, 0, 1) * warm  # 沙漠壓暗成紅褐色
yellow = np.clip((col[..., 1] - col[..., 2]) * 3, 0, 1) * np.clip((col[..., 0] - 0.35) * 3, 0, 1)
col[..., 1] *= 1 - 0.22 * yellow  # 黃色沙地轉成參考圖的紅褐色
col[..., 0] *= 1 - 0.1 * yellow
lat = np.linspace(90, -90, H, dtype=np.float32)[:, None] * np.ones((1, W), np.float32)
ice = np.clip((np.abs(lat) - 58) / 8, 0, 1) * np.clip((lum[..., 0] - 0.35) * 4, 0, 1)
col = mix(col, np.ones_like(col) * hexc("#eef4fb"), ice)  # 南極、格陵蘭冰原保持白色  # 沙漠偏紅橘、森林偏暖綠
gy, gx = np.gradient(blur(elev, 1.0))
shade = np.clip(1 + (-gx + gy) * 22, 0.55, 1.45)  # 光源西北
col = np.clip(col * shade[..., None], 0, 1)

# ---------- 海洋：深藍到近岸亮藍 ----------
near = blur(land, 40) * 0.5 + blur(land, 12) * 0.5
ocean = mix(np.ones((H, W, 3), np.float32) * hexc("#1450a8"), np.ones((H, W, 3), np.float32) * hexc("#2a78c8"), np.clip(noise(4, 3) * 0.9, 0, 1))
ocean = mix(ocean, np.ones_like(ocean) * hexc("#3d93dc"), np.clip(near * 1.6, 0, 1))

# ---------- 白色流紋：沿海岸等距線流動，經雜訊扭曲並斷續 ----------
dist = 1 - (blur(land, 6) * 0.3 + blur(land, 25) * 0.4 + blur(land, 70) * 0.3)  # 離岸越遠越接近 1
phase = dist * 22 + noise(3, 11) * 8 + noise(12, 12) * 2.5
band = np.clip((np.sin(phase * np.pi) - 0.62) / 0.38, 0, 1) ** 1.3
patch = np.clip(noise(6, 13) * 2.4 - 0.8, 0, 1) * np.clip((1.0 - dist) * 14, 0, 1)
flow = blur(band * patch * (1 - land), 2.2) * 0.7 + blur(band * patch * (1 - land), 9) * 0.6
ocean = mix(ocean, np.ones_like(ocean) * hexc("#e8f3ff"), np.clip(flow * 1.5, 0, 0.95))
ocean = mix(ocean, np.ones_like(ocean) * hexc("#b8daf5"), np.clip(near * 0.35, 0, 0.3))  # 近岸淡淡的白霧
foam = np.clip((blur(land, 5) - land) * 3, 0, 1)
ocean = mix(ocean, np.ones_like(ocean) * hexc("#cfeaff"), foam * 0.7)

out = mix(ocean, col, np.clip(blur(land, 0.8), 0, 1))
Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(os.path.join(ROOT, "public/textures/earth-painted.jpg"), quality=90, optimize=True)
print("earth ok")

# ---------- 雲層：稀疏的薄雲，兩極淡出 ----------
CW, CH = 2048, 1024
clat = np.linspace(90, -90, CH, dtype=np.float32)[:, None] * np.ones((1, CW), np.float32)
c = noise(6, 31, 7, w=CW, h=CH) * 0.6 + noise(24, 32, 4, w=CW, h=CH) * 0.4
bands = 0.2 * np.exp(-((clat / 9) ** 2)) + 0.25 * np.exp(-(((np.abs(clat) - 52) / 14) ** 2)) + 0.6
alpha = np.clip((c * bands - 0.36) * 4.0, 0, 1) ** 1.3 * np.clip((80 - np.abs(clat)) / 25, 0, 1)
rgba = np.zeros((CH, CW, 4), np.uint8)
rgba[..., :3] = 255
rgba[..., 3] = (alpha * 200).astype(np.uint8)
Image.fromarray(rgba, "RGBA").save(os.path.join(ROOT, "public/textures/clouds-painted.png"), optimize=True)
print("clouds ok")
