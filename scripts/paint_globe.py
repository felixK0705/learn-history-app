"""以程式繪製風格化地球貼圖（參考圖風格：飽和的陸地、明亮的海洋與白色流紋）。

只使用陸地遮罩與高程作為地理輸入（three-globe 套件的 earth-water.png、earth-topology.png），
顏色、地貌、洋流紋路全部由程式產生，不使用任何現成的地球照片貼圖。
輸出：public/textures/earth-painted.jpg
"""
import os

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "node_modules/three-globe/example/img")
W, H = 4096, 2048
rng = np.random.default_rng(7)


def load_gray(name):
    return Image.open(os.path.join(SRC, name)).convert("L").resize((W, H), Image.LANCZOS)


def blur(arr, r):
    im = Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255


def fbm(octaves=6, base=4, persistence=0.55, seed=0):
    """多層雜訊（以放大的隨機格點疊加），左右可接續"""
    g = np.random.default_rng(seed)
    out = np.zeros((H, W), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        n = base * 2**o
        grid = g.random((max(2, n // 2), n)).astype(np.float32)
        grid = np.concatenate([grid, grid[:, :1]], axis=1)  # 水平接續
        im = Image.fromarray((grid * 255).astype(np.uint8)).resize((W + W // n, H), Image.BICUBIC)
        out += amp * np.asarray(im, np.float32)[:, :W] / 255
        total += amp
        amp *= persistence
    return out / total


def mix(a, b, t):
    return a + (b - a) * t[..., None]


def hexc(h):
    return np.array([int(h[i : i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)


water = np.asarray(load_gray("earth-water.png"), np.float32) / 255
land = 1.0 - water
land_soft = blur(land, 1.5)
elev = np.asarray(load_gray("earth-topology.png"), np.float32) / 255

lat = np.linspace(90, -90, H, dtype=np.float32)[:, None] * np.ones((1, W), np.float32)
alat = np.abs(lat)

# ---------- 陸地 ----------
moisture = blur(water, 130) * 0.55 + blur(water, 40) * 0.3 + blur(water, 12) * 0.15  # 靠海越濕潤（內陸乾燥）
n1 = fbm(seed=1)
n2 = fbm(seed=2, base=8)
lon = np.linspace(-180, 180, W, dtype=np.float32)[None, :] * np.ones((H, 1), np.float32)


wlat = lat + (fbm(seed=21, base=4) - 0.5) * 9
wlon = lon + (fbm(seed=22, base=4) - 0.5) * 12


def region(lat0, lat1, lon0, lon1, soft=10.0):
    """經緯度範圍的柔邊遮罩：座標先經雜訊扭曲，形狀較自然"""
    a = np.clip((wlat - lat0 + soft / 2) / soft, 0, 1) * np.clip((lat1 - wlat + soft / 2) / soft, 0, 1)
    b = np.clip((wlon - lon0 + soft / 2) / soft, 0, 1) * np.clip((lon1 - wlon + soft / 2) / soft, 0, 1)
    return np.sqrt(a * b)


# 依實際地理位置標出主要沙漠與草原帶
deserts = [
    (16, 31, -16, 33), (14, 31, 34, 58), (25, 36, 52, 72), (24, 30, 69, 75),  # 撒哈拉、阿拉伯、伊朗高原、塔爾
    (-29, -18, 12, 24), (-31, -19, 117, 143), (-27, -17, -71, -68),  # 喀拉哈里與納米布、澳洲內陸、阿塔卡馬
    (26, 40, -118, -106), (39, 46, 92, 112), (37, 42, 77, 90), (2, 11, 41, 51),  # 北美西南、塔克拉瑪干與戈壁、非洲之角
    (-50, -38, -71, -64), (38, 47, 52, 68),  # 巴塔哥尼亞、中亞
]
savannas = [
    (9, 16, -17, 40), (-18, 8, 26, 41), (-21, -4, -56, -40), (-21, -12, 122, 145), (17, 26, 70, 85), (-34, -28, 14, 31), (40, 50, -110, -97),
]
desert = np.zeros((H, W), np.float32)
for r in deserts:
    desert = np.maximum(desert, region(*r))
desert = np.clip(desert * (0.9 + 0.35 * n2), 0, 1)
savanna = np.zeros((H, W), np.float32)
for r in savannas:
    savanna = np.maximum(savanna, region(*r, soft=8))
savanna = np.clip(savanna - desert * 0.8, 0, 1)
tropic = np.clip(np.exp(-((alat / 13) ** 2)) * (0.6 + moisture), 0, 1)
temperate = np.exp(-(((alat - 47) / 13) ** 2))
boreal = np.exp(-(((alat - 61) / 7) ** 2))
ice = np.clip((alat - 66) / 6, 0, 1) + np.clip((elev - 0.62) * 5, 0, 1)

col = np.ones((H, W, 3), np.float32) * hexc("#5f9a3e")
col = mix(col, np.ones_like(col) * hexc("#2f7d34"), np.clip(tropic * (0.8 + 0.4 * n2), 0, 1))
col = mix(col, np.ones_like(col) * hexc("#6aa044"), np.clip(temperate * 0.7, 0, 1))
col = mix(col, np.ones_like(col) * hexc("#3f6e3c"), np.clip(boreal * 0.8, 0, 1))
col = mix(col, np.ones_like(col) * hexc("#b49a52"), np.clip(savanna * 0.85, 0, 1))
col = mix(col, np.ones_like(col) * hexc("#dba25e"), desert)
col = mix(col, np.ones_like(col) * hexc("#c4703c"), np.clip((desert - 0.6) * 2.0 * n2 * 1.4, 0, 1))  # 紅色砂岩
col = mix(col, np.ones_like(col) * hexc("#a88e6c"), np.clip((elev - 0.35) * 2.2, 0, 1) * 0.7)  # 山地
col = mix(col, np.ones_like(col) * hexc("#f2f6fb"), np.clip(ice, 0, 1))

# 地形陰影（光源西北）
gy, gx = np.gradient(blur(elev, 1.2))
shade = np.clip(1.0 + (-gx * 0.9 + gy * 0.9) * 16, 0.65, 1.4)
col *= shade[..., None]
col *= (0.92 + 0.16 * n1)[..., None]

# ---------- 海洋 ----------
near = blur(land, 26) * 0.6 + blur(land, 8) * 0.4  # 越近陸地越淺
deep = hexc("#0f4fae")
mid = hexc("#1f6cc8")
shallow = hexc("#4fb0ea")
ocean = mix(mix(np.ones((H, W, 3), np.float32) * deep, np.ones((H, W, 3), np.float32) * mid, np.clip(0.35 + fbm(seed=3) * 0.4, 0, 1)),
            np.ones((H, W, 3), np.float32) * shallow, np.clip(near * 1.8, 0, 1))
# 白色流紋（扭曲的緯向條紋）
warp = fbm(seed=4, base=2) * 16 + fbm(seed=5, base=6) * 6 + fbm(seed=9, base=16) * 1.5
phase = lat * 0.16 + np.sin(np.radians(lon) * 3 + fbm(seed=10, base=3) * 6) * 2.2 + warp
streak = np.sin(phase * np.pi)
streak = np.clip((streak - 0.78) / 0.22, 0, 1) ** 1.3
patch = np.clip(fbm(seed=6, base=8) * 2.6 - 1.25, 0, 1)
streak *= patch * (0.6 + 0.6 * np.clip(near * 3, 0, 1))
ocean = mix(ocean, np.ones_like(ocean) * hexc("#dcecff"), np.clip(blur(streak, 2.2) * 0.55, 0, 1))
# 海面明暗起伏
ocean *= (0.9 + 0.2 * fbm(seed=12, base=6))[..., None]
# 海岸白浪
foam = np.clip(blur(land, 9) - land * 0.98, 0, 1)
foam = np.clip(foam * 3.2, 0, 1)
ocean = mix(ocean, np.ones_like(ocean) * hexc("#bfe6ff"), foam * 0.6)

out = mix(ocean, col, np.clip(land_soft, 0, 1))
out = np.clip(out, 0, 1)
Image.fromarray((out * 255).astype(np.uint8)).save(os.path.join(ROOT, "public/textures/earth-painted.jpg"), quality=88, optimize=True)
print("ok")

# ---------- 雲層（程式產生：熱帶輻合帶與中緯度雲帶，帶有旋渦狀扭曲） ----------
CW, CH = 2048, 1024
clat = np.linspace(90, -90, CH, dtype=np.float32)[:, None] * np.ones((1, CW), np.float32)


def fbm_small(seed, base, octaves=6, persistence=0.55):
    g = np.random.default_rng(seed)
    out = np.zeros((CH, CW), np.float32)
    amp = total = 0.0
    amp = 1.0
    for o in range(octaves):
        n = base * 2**o
        grid = g.random((max(2, n // 2), n)).astype(np.float32)
        grid = np.concatenate([grid, grid[:, :1]], axis=1)
        im = Image.fromarray((grid * 255).astype(np.uint8)).resize((CW + CW // n, CH), Image.BICUBIC)
        out += amp * np.asarray(im, np.float32)[:, :CW] / 255
        total += amp
        amp *= persistence
    return out / total


bands = 0.25 * np.exp(-((clat / 9) ** 2)) + 0.3 * np.exp(-(((np.abs(clat) - 52) / 14) ** 2)) + 0.62
c = fbm_small(31, 6, 7) * 0.6 + fbm_small(32, 24, 4) * 0.4
alpha = np.clip((c * bands - 0.33) * 4.0, 0, 1) ** 1.2 * np.clip((80 - np.abs(clat)) / 25, 0, 1)  # 兩極淡出，避免貼圖在極點收束成白色放射紋
rgba = np.zeros((CH, CW, 4), np.uint8)
rgba[..., :3] = 255
rgba[..., 3] = (alpha * 235).astype(np.uint8)
Image.fromarray(rgba, "RGBA").save(os.path.join(ROOT, "public/textures/clouds-painted.png"), optimize=True)
print("clouds ok")
