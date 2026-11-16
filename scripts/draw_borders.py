"""把國界線直接畫進地球貼圖（public/textures/earth-painted.jpg → earth-map.jpg）。
國界改成貼圖的一部分後，網頁不必再為每個國家建立 3D 線條物件，縮放旋轉更流暢。"""
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
base = Image.open(os.path.join(ROOT, "public/textures/earth-painted.jpg")).convert("RGB")
W, H = base.size
SS = 2  # 先以兩倍解析度繪製再縮小，線條平滑
LINE = 4 * SS  # 縮小後約 4px，地球縮小時國界仍清楚可見
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
                        draw.line(seg, fill=255, width=LINE)
                    seg = [b]
                else:
                    seg.append(b)
            if len(seg) > 1:
                draw.line(seg, fill=255, width=LINE)

mask = layer.resize((W, H), Image.LANCZOS)
# 先鋪一圈半透明深色描邊，再畫白線：在淺色沙漠、雪地或雲下都看得清楚
shadow = mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.5)).point(lambda v: int(v * 0.45))
base.paste(Image.new("RGB", (W, H), (10, 30, 60)), (0, 0), shadow)
base.paste(Image.new("RGB", (W, H), (250, 252, 255)), (0, 0), mask.point(lambda v: int(v * 0.9)))
# 換日線兩側 48px 漸變，貼圖左右接縫看不出來
a = np.asarray(base, np.float32)
k = 48
edge = (a[:, :1] + a[:, -1:]) / 2
w = (1 - np.arange(k, dtype=np.float32) / k)[None, :, None]
a[:, :k] = a[:, :k] * (1 - w) + edge * w
a[:, -k:] = a[:, -k:] * (1 - w[:, ::-1]) + edge * w[:, ::-1]
base = Image.fromarray(a.astype(np.uint8))
base.save(os.path.join(ROOT, "public/textures/earth-map.jpg"), quality=88, optimize=True)
print("ok", W, H)
