"""wat-pho 曼谷臥佛寺 四大佛塔（Phra Maha Chedi Si Rajakarn）寫實模型（公尺；+X 東、+Y 北）

- 四座拉瑪王佛塔（各高約 42 m）：方形「ย่อมุมไม้สิบสอง」（每角三折、共十二凸角）平面，
  下段為多層疊澀的基座，上接鐘形塔身（องค์ระฆัง）、寶座、環節狀尖頂（ปล้องไฉน）
- 外表為中國瓷片馬賽克：拉瑪一世綠、拉瑪二世白、拉瑪三世黃、拉瑪四世藍；四面有神龕門（紅門、山牆頂）
- 拉瑪四世藍塔另有一院；周圍迴廊（白牆、橘色琉璃瓦、綠邊）圍出庭院，地面為紅磚
- 院外有數座小佛塔（Phra Chedi Rai）
"""

import math
import os

import numpy as np
from mathutils import Matrix, Vector

from lib import TAU
from buildings.forbidden_city import CnBuilder, gen_paving
from buildings.kinkakuji import GEN, AsiaBuilder, _cloud, _height_to_normal, _save_maps, gen_tiles

# (目標點, 方位角, 仰角, 距離, 焦距)：參考照自南側迴廊外庭院仰望藍塔（拉瑪四世）
CAMERA = ((-8.0, 0.0, 21.0), 9.0, -15.2, 65.0, 34)


def gen_mosaic(name, base, accents, seed=3):
    """瓷片馬賽克：底色上規則排列的小花（多色圓瓣）與水平飾帶；貼圖約 1.6 m 一循環"""
    out = os.path.join(GEN, f"th_mosaic_{name}")
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return out
    from PIL import Image, ImageDraw

    N = 512
    rng = np.random.default_rng(seed)
    im = Image.new("RGB", (N, N), tuple(int(c) for c in base))
    dr = ImageDraw.Draw(im)
    for y in range(0, N, 32):
        if (y // 32) % 4 == 0:
            dr.rectangle([0, y, N, y + 6], fill=tuple(int(c) for c in accents[0]))
    for gy in range(8):
        for gx in range(8):
            cx = gx * 64 + 32 + (gy % 2) * 32
            cy = gy * 64 + 32
            c = accents[rng.integers(len(accents))]
            r = rng.uniform(7, 11)
            for k in range(6):
                a = TAU * k / 6
                px, py = cx + math.cos(a) * r * 0.8, cy + math.sin(a) * r * 0.8
                dr.ellipse([px - r * 0.45, py - r * 0.45, px + r * 0.45, py + r * 0.45], fill=tuple(int(v) for v in c))
            c2 = accents[rng.integers(len(accents))]
            dr.ellipse([cx - r * 0.4, cy - r * 0.4, cx + r * 0.4, cy + r * 0.4], fill=tuple(int(v) for v in c2))
            for _ in range(5):
                px, py = rng.uniform(0, N), rng.uniform(0, N)
                c3 = accents[rng.integers(len(accents))]
                dr.ellipse([px - 3, py - 3, px + 3, py + 3], fill=tuple(int(v) for v in c3))
    a = np.asarray(im, dtype=float)
    a = a * (1 + _cloud(rng, N, 32, 0.25))[..., None] * (1 + rng.uniform(-0.08, 0.08, size=(N // 4, N // 4)).repeat(4, 0).repeat(4, 1))[..., None]
    h = np.asarray(im.convert("L"), dtype=float) / 255
    _save_maps(out, a, _height_to_normal(h * 3, 1.0))
    return out


def redent(s, d, z):
    """十二凸角方形（每角三折）：回傳逆時針點列"""
    pts = []
    for q in range(4):
        c, sn = math.cos(q * math.pi / 2), math.sin(q * math.pi / 2)
        for (x, y) in ((s, -s + 2 * d), (s, s - 2 * d), (s - d, s - 2 * d), (s - d, s - d), (s - 2 * d, s - d), (s - 2 * d, s)):
            pts.append((x * c - y * sn, x * sn + y * c, z))
    return pts


def chedi_profile(H=42.0):
    """依參考照量得的外輪廓 r(z)，下段每 0.8 m 一道疊澀線腳"""
    k = H / 42.0
    tab = [(0, 6.4), (1.5, 6.4), (2.0, 6.0), (6, 5.6), (13, 5.0), (16, 4.4), (19, 3.3), (22, 2.6), (26.5, 1.85), (27.5, 1.6)]

    def r(z):
        for (z0, r0), (z1, r1) in zip(tab, tab[1:]):
            if z <= z1:
                return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
        return tab[-1][1]
    p = [(6.4, 0.0), (6.4, 1.2), (6.1, 1.3), (6.1, 1.6), (6.3, 1.75), (6.3, 2.0)]
    z = 2.0
    while z < 19.0:
        rr = r(z)
        p += [(rr, z + 0.55), (rr - 0.14, z + 0.6), (rr - 0.14, z + 0.68), (r(z + 0.8), z + 0.8)]
        z += 0.8
    while z < 27.5:
        rr = r(z)
        p += [(rr, z + 0.9), (rr * 1.06, z + 1.0), (rr * 1.06, z + 1.1), (r(z + 1.2), z + 1.2)]
        z += 1.2
    p += [(1.6, 27.6), (1.95, 27.7), (1.95, 28.3), (1.35, 28.45)]
    s, z = 1.25, 28.5
    while z < 39.5:
        p += [(s, z), (s * 1.2, z + 0.18), (s * 1.2, z + 0.32), (s, z + 0.5)]
        z += 0.55
        s *= 0.925
    p += [(s * 0.9, z + 0.2), (0.15, 40.8), (0.08, 41.5), (0.02, 42.0)]
    return [(a * k, b * k) for a, b in p]


class ThaiBuilder(CnBuilder):
    def loft(self, mi, profile, cx, cy, z0=0.0, notch=0.11):
        rings = []
        for s, z in profile:
            d = max(0.02, s * notch)
            rings.append([self.V((cx + x, cy + y, z0 + zz)) for x, y, zz in redent(s, d, z)])
        self.face(list(reversed(rings[0])), mi)
        self.strip(rings, mi)
        self.face(rings[-1], mi)

    def chedi(self, mi, cx, cy, H, trim, door, gable):
        k = H / 42.0
        self.loft(mi, chedi_profile(H), cx, cy)
        # 環節間的金色細線（尖頂頂端）
        self.cyl(trim, 0.22 * k, 0.05 * k, 3.5 * k, (cx, cy, 39.0 * k), seg=8)
        self.ico(trim, 0.35 * k, (cx, cy, 39.2 * k), subdiv=1)
        # 四面神龕
        for q in range(4):
            R = Matrix.Translation((cx, cy, 0)) @ Matrix.Rotation(q * math.pi / 2, 4, "Z")
            yf = -(4.6 * k)
            self.place(lambda: self.box_base(mi, (3.6 * k, 2.4 * k, 6.2 * k), (0, yf, 10.4 * k)), R)
            self.place(lambda: self.box_base(trim, (3.9 * k, 2.6 * k, 0.3 * k), (0, yf, 16.6 * k)), R)
            self.place(lambda: self.box_base(trim, (1.9 * k, 0.12 * k, 3.4 * k), (0, yf - 1.22 * k, 11.0 * k)), R)
            self.place(lambda: self.box_base(door, (1.1 * k, 0.16 * k, 2.6 * k), (0, yf - 1.25 * k, 11.2 * k)), R)
            self.place(lambda: self.tri_prism(gable, 3.8 * k, 2.2 * k, 2.4 * k, (0, yf, 16.9 * k), rot_z=math.pi / 2), R)
            self.place(lambda: self.cyl(trim, 0.15 * k, 0.02 * k, 1.4 * k, (0, yf - 1.0 * k, 19.1 * k), seg=6), R)


def wat_pho(path):
    b = ThaiBuilder("WatPho", seed=12)
    mos = {
        "blue": b.gtex("m_blue", gen_mosaic("blue3", (30, 40, 110), [(214, 180, 70), (190, 190, 180), (180, 40, 40), (50, 130, 80), (60, 100, 200), (40, 60, 150)]), tile=1.6, rough=0.4, normal=0.6),
        "green": b.gtex("m_green", gen_mosaic("green3", (112, 84, 62), [(70, 120, 90), (206, 170, 90), (60, 130, 100), (170, 60, 50), (200, 195, 180), (90, 140, 110)], seed=4), tile=1.6, rough=0.45, normal=0.6),
        "yellow": b.gtex("m_yellow", gen_mosaic("yellow", (176, 136, 70), [(214, 186, 100), (90, 120, 150), (170, 60, 50), (230, 225, 210), (80, 120, 80)], seed=5), tile=1.6, rough=0.45, normal=0.6),
        "white": b.gtex("m_white", gen_mosaic("white", (206, 200, 186), [(150, 170, 120), (200, 170, 90), (120, 140, 180), (190, 90, 80)], seed=6), tile=1.6, rough=0.45, normal=0.6),
    }
    gold = b.color("gold", "#c99a3c", rough=0.35, metal=0.5)
    door = b.color("door_red", "#a3161b", rough=0.5)
    wall = b.ptex("wall", "plastered_wall_04", tile=4.0, tint="#e8e4dc", rough=0.85, normal=0.3)
    roof = b.gtex("roof", gen_tiles("th_orange", (212, 112, 40), kind="thai", n_ch=14, n_rows=14, seed=9), tile=2.4, rough=0.4,
                  normal=0.8, oriented=True)
    roof_g = b.color("roof_green", "#3e7e4c", rough=0.5)
    band_r = b.color("band_red", "#a9332a", rough=0.6)
    brick = b.gtex("brick", gen_paving("th_brick", (128, 84, 72), bw=10, bh=20, seed=21, joint=(0.75, 0.72, 0.7)), tile=3.0, rough=0.9,
                   normal=0.5)
    lawn = b.ptex("lawn", "grass_ground", tile=4.0, tint="#5f7f36", rough=0.95, normal=0.4)
    stone = b.ptex("stone", "marble_01", tile=3.0, tint="#cfcac0", rough=0.6, normal=0.3)

    # ---------------- 地面
    b.box_base(brick, (150.0, 170.0, 0.4), (-15.0, 20.0, -0.4))

    # ---------------- 四大佛塔
    b.chedi(mos["blue"], 0.0, 0.0, 42.0, gold, door, mos["blue"])
    b.chedi(mos["green"], -32.0, 6.0, 42.0, gold, door, mos["green"])
    b.chedi(mos["yellow"], -32.0, 38.0, 42.0, gold, door, mos["yellow"])
    b.chedi(mos["white"], -32.0, 70.0, 42.0, gold, door, mos["white"])
    for (x, y) in ((0, 0), (-32, 6), (-32, 38), (-32, 70)):
        b.box_base(stone, (25.0, 25.0, 0.5), (x, y, -0.05))

    # ---------------- 迴廊（白牆＋橘瓦兩坡頂、綠邊、紅帶）
    def gallery(L, depth=4.0, h=3.2):
        b.box_base(stone, (L, depth + 0.6, 0.4), (0, 0, 0))
        b.box_base(wall, (L, depth, h), (0, 0, 0.4))
        b.box_base(band_r, (L + 0.1, depth + 0.1, 0.35), (0, 0, 0.4 + h - 0.6))
        b.box_base(roof_g, (L + 0.2, depth + 1.6, 0.25), (0, 0, 0.4 + h))
        b.tri_prism(roof, L + 0.2, depth + 1.6, 2.6, (0, 0, 0.4 + h + 0.25))
        b.tri_prism(roof_g, L + 0.4, 0.5, 0.25, (0, 0, 0.4 + h + 2.75))

    def run(x0, y0, x1, y1):
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        b.place(lambda: gallery(L), Matrix.Translation(((x0 + x1) / 2, (y0 + y1) / 2, 0)) @ Matrix.Rotation(ang, 4, "Z"))

    # 藍塔院（東）＋三塔院（西）
    run(-16.0, -16.0, 16.0, -16.0)
    run(16.0, -14.0, 16.0, 16.0)
    run(-16.0, 18.0, 16.0, 18.0)
    run(-16.0, -14.0, -16.0, 16.0)
    run(-50.0, -12.0, -18.0, -12.0)
    run(-50.0, 88.0, -14.0, 88.0)
    run(-52.0, -10.0, -52.0, 86.0)
    run(-14.0, 20.0, -14.0, 86.0)

    # ---------------- 院外小佛塔（Phra Chedi Rai）與石燈
    for (x, y, H) in ((28.0, 6.0, 7.0), (-60.0, 20.0, 7.5), (-60.0, 55.0, 7.5), (6.0, 30.0, 6.5),
                      (24.0, 36.0, 7.0), (-6.0, 52.0, 6.5)):
        b.box_base(stone, (H * 0.6, H * 0.6, 0.6), (x, y, 0))
        b.chedi(mos["green"] if (x + y) % 2 else mos["yellow"], x, y, H, gold, door, mos["white"])
    for s in (-1, 1):
        b.box_base(stone, (0.9, 0.9, 1.6), (s * 8.0, -26.0, 0))
        b.cyl(stone, 0.5, 0.05, 1.2, (s * 8.0, -26.0, 1.6), seg=8)
    b.box_base(lawn, (14.0, 5.0, 0.25), (0, -24.0, 0))

    b.export_glb(path)
