"""由 NASA Blue Marble（公有領域，隨 three-globe 套件提供）產生參考圖風格的明亮地球貼圖。

輸出：public/textures/earth-vivid.jpg、clouds.png、earth-topology.png、earth-water.png
"""
import os
import shutil

from PIL import Image, ImageChops, ImageEnhance, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "node_modules/three-globe/example/img")
OUT = os.path.join(ROOT, "public/textures")
os.makedirs(OUT, exist_ok=True)

earth = Image.open(os.path.join(SRC, "earth-blue-marble.jpg")).convert("RGB")
water = Image.open(os.path.join(SRC, "earth-water.png")).convert("L").resize(earth.size)
# 海洋遮罩柔化，避免海岸線生硬
mask = water.filter(ImageFilter.GaussianBlur(3))

# 陸地：提高飽和與亮度
land = ImageEnhance.Color(earth).enhance(1.35)
land = ImageEnhance.Brightness(land).enhance(1.12)
land = ImageEnhance.Contrast(land).enhance(1.08)

# 海洋：保留原圖深淺（洋流、淺海），重新上色成鮮明的藍綠
lum = ImageEnhance.Contrast(earth.convert("L")).enhance(1.6)
deep = Image.new("RGB", earth.size, (18, 92, 196))
shallow = Image.new("RGB", earth.size, (64, 176, 236))
ocean = Image.composite(shallow, deep, lum.point(lambda v: min(255, int(v * 2.2))))
# 近海岸的淺海帶
coast = ImageChops.subtract(mask.filter(ImageFilter.GaussianBlur(14)), mask.filter(ImageFilter.MinFilter(9)))
ocean = Image.composite(Image.new("RGB", earth.size, (92, 205, 242)), ocean, coast.point(lambda v: min(255, v * 3)))

out = Image.composite(ocean, land, mask)
out.save(os.path.join(OUT, "earth-vivid.jpg"), quality=86, optimize=True)

clouds = Image.open(os.path.join(ROOT, "node_modules/globe.gl/example/clouds/clouds.png")).convert("RGBA").resize((2048, 1024), Image.LANCZOS)
clouds.save(os.path.join(OUT, "clouds.png"), optimize=True)
for f in ("earth-topology.png", "earth-water.png"):
    shutil.copy(os.path.join(SRC, f), os.path.join(OUT, f))
print("ok", {f: os.path.getsize(os.path.join(OUT, f)) // 1024 for f in os.listdir(OUT)})
