"""把國界線直接畫進地球貼圖（public/textures/earth-painted.jpg → earth-map.jpg）。
國界改成貼圖的一部分後，網頁不必再為每個國家建立 3D 線條物件，縮放旋轉更流暢。"""
import json, os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
base = Image.open(os.path.join(ROOT, "public/textures/earth-painted.jpg")).convert("RGB")
W, H = base.size
SS = 2  # 先以兩倍解析度繪製再縮小，線條平滑
layer = Image.new("L", (W * SS, H * SS), 0)
draw = ImageDraw.Draw(layer)
geo = json.load(open(os.path.join(ROOT, "public/data/countries.json")))


def xy(lng, lat):
    return ((lng + 180) / 360 * W * SS, (90 - lat) / 180 * H * SS)


for f in geo["features"]:
    g = f["geometry"]
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    for poly in polys:
        for ring in poly:
            pts = [xy(lng, lat) for lng, lat in ring]
            # 跨越換日線的線段不畫（避免橫貫整張圖）
            seg = [pts[0]]
            for a, b in zip(pts, pts[1:]):
                if abs(a[0] - b[0]) > W * SS / 2:
                    if len(seg) > 1:
                        draw.line(seg, fill=255, width=3 * SS // 2 + 1)
                    seg = [b]
                else:
                    seg.append(b)
            if len(seg) > 1:
                draw.line(seg, fill=255, width=3 * SS // 2 + 1)

mask = layer.resize((W, H), Image.LANCZOS).point(lambda v: int(v * 0.6))
white = Image.new("RGB", (W, H), (240, 246, 255))
base.paste(white, (0, 0), mask)
base.save(os.path.join(ROOT, "public/textures/earth-map.jpg"), quality=88, optimize=True)
print("ok", W, H)
