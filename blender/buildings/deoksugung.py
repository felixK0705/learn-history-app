"""deoksugung 首爾德壽宮 中和殿 寫實模型（公尺；+X 東、+Y 北）

- 中和殿（1906 年重建）：單層、正面 5 間 × 側面 4 間，單簷歇山頂（팔작지붕），灰色本瓦、白色灰漿屋脊，
  簷角大幅起翹；朱褐色柱、綠色丹青、正面黃色花格門
- 二層石造月台（월대），正面中央三道石階、中央踏道（답도）；四角石獸、鼎形香爐
- 前庭：花崗岩薄石（박석）不規則鋪面、中央三道御路（삼도）、兩側品階石（품계석）各 12 座
- 周邊行閣（迴廊）屋頂與松樹、闊葉樹
"""

import math

from mathutils import Matrix

from buildings.forbidden_city import CnBuilder, gen_lattice, gen_paving, stairs
import os

import numpy as np

from buildings.kinkakuji import GEN, _cloud, _height_to_normal, _save_maps, gen_canopy, gen_leaves, gen_tiles


def gen_bakseok(name, color, seed=5):
    """薄石鋪面：不規則大小的長方形花崗岩板（列高、板寬皆隨機），色調斑駁"""
    out = os.path.join(GEN, f"kr_bakseok_{name}")
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return out
    N = 1024
    rng = np.random.default_rng(seed)
    lum = np.zeros((N, N))
    hgt = np.ones((N, N))
    y = 0
    while y < N:
        rh = int(rng.uniform(70, 150)) if N - y > 160 else N - y
        x = int(rng.uniform(0, 120))
        widths = []
        while sum(widths) < N:
            widths.append(int(rng.uniform(90, 260)))
        widths[-1] -= sum(widths) - N
        for w in widths:
            t = rng.uniform(-0.16, 0.16)
            xs = (np.arange(x, x + w) % N)
            lum[y:y + rh, xs] = t
            hgt[y:y + rh, xs] = 1 + rng.uniform(-0.15, 0.15)
            hgt[y:y + 3, xs] = 0
            hgt[y:y + rh, xs[:3]] = 0
            x += w
        y += rh
    base = np.array(color, float)
    L = 1 + lum + _cloud(rng, N, 48, 0.14) + _cloud(rng, N, 4, 0.12)
    diff = base[None, None] * L[..., None]
    diff = np.where((hgt < 0.01)[..., None], diff * 0.62, diff)
    hue = _cloud(rng, N, 128, 0.08)
    diff[..., 0] *= 1 + hue
    diff[..., 2] *= 1 - hue
    _save_maps(out, diff, _height_to_normal(hgt * 2 + _cloud(rng, N, 4, 0.3), 1.0), size=512)
    return out

# (目標點, 方位角, 仰角, 距離, 焦距)：參考照自中和門內、御路上偏西處平視
CAMERA = ((-11.0, 0.0, 4.6), 9.5, -2.7, 64.0, 28)


def deoksugung(path):
    b = CnBuilder("Deoksugung", seed=21)
    M = b.mats_cn(roof_rgb=(96, 98, 100), roof_name="kr_grey")
    M["tile"] = b.gtex("tile_kr", gen_tiles("kr_grey3", (62, 64, 66), kind="kawara", n_ch=8, n_rows=12, seed=17), tile=2.6,
                       rough=0.75, normal=1.0, oriented=True)
    M["ridge"] = b.color("ridge_kr", "#a8a49c", rough=0.8)
    M["col"] = b.color("column_kr", "#7a2b20", rough=0.6)
    M["red"] = b.ptex("redwall_kr", "plastered_wall_04", tile=4.0, tint="#8a3a2c", rough=0.85, normal=0.4)
    M["door"] = b.gtex("door_kr", gen_lattice("kr", (190, 140, 60), (214, 168, 78)), tile=0.9, rough=0.6, normal=0.5)
    M["green"] = b.color("green_kr", "#3f8a6c", rough=0.6)
    M["blue"] = b.color("blue_kr", "#22433a", rough=0.7)
    M["marble"] = b.ptex("granite", "large_sandstone_blocks", tile=3.0, tint="#aaa392", rough=0.8, normal=0.3)
    M["marble_d"] = b.ptex("granite_d", "large_sandstone_blocks", tile=3.0, tint="#9c9584", rough=0.8, normal=0.3)
    M["fascia"] = b.color("fascia_kr", "#45474a", rough=0.8)
    M["thick"] = 0.3
    rank = b.color("rankstone", "#aea897", rough=0.8)
    bakseok = b.gtex("bakseok", gen_bakseok("a", (128, 123, 114)), tile=7.0,
                     rough=0.85, normal=0.6)
    path_m = b.gtex("path", gen_bakseok("p", (132, 127, 118), seed=8), tile=4.0,
                    rough=0.85, normal=0.6)
    curb = b.color("curb", "#8f897d", rough=0.8)
    grass = b.gtex("grass", gen_canopy("lawn", (92, 120, 58), seed=4), tile=4.0, rough=0.95, normal=0.3)
    lf_pine = b.alpha_mat("leaf_pine", gen_leaves("pine"), rough=0.8)
    lf_dark = b.alpha_mat("leaf_dark", gen_leaves("dark"), rough=0.8)
    lf_broad = b.alpha_mat("leaf_broad", gen_leaves("broad"))
    lf_light = b.alpha_mat("leaf_light", gen_leaves("light"))
    core_p = b.gtex("core_pine", gen_canopy("pine", (66, 92, 42), seed=3), tile=2.2, rough=0.9, normal=1.0)
    core_b = b.gtex("core_broad", gen_canopy("broad", (104, 136, 50), seed=5), tile=3.0, rough=0.9, normal=1.0)
    bark = b.color("bark", "#5a4636", rough=0.9)
    bark_r = b.color("bark_pine", "#6b4a38", rough=0.9)

    # ---------------- 地面：前庭薄石＋周圍草地
    b.box_base(grass, (150.0, 150.0, 0.4), (0, -10.0, -0.45))
    b.box_base(bakseok, (74.0, 96.0, 0.4), (0, -31.0, -0.38))
    # 三道：中央（略高）＋兩側，邊緣石
    YP0, YP1 = -78.0, -17.0
    b.box_base(path_m, (2.6, YP1 - YP0, 0.12), (0, (YP0 + YP1) / 2, 0.02))
    for s in (-1, 1):
        b.box_base(path_m, (2.2, YP1 - YP0, 0.07), (s * 2.5, (YP0 + YP1) / 2, 0.02))
        b.box_base(curb, (0.35, YP1 - YP0, 0.16), (s * 1.45, (YP0 + YP1) / 2, 0.02))
        b.box_base(curb, (0.35, YP1 - YP0, 0.12), (s * 3.75, (YP0 + YP1) / 2, 0.02))
    # 品階石：兩側各 12 座
    for s in (-1, 1):
        for k in range(12):
            y = -21.5 - k * 3.6
            x = s * 9.5
            b.box_base(rank, (1.0, 0.75, 0.2), (x, y, 0.02))
            b.box_base(rank, (0.42, 0.3, 0.75), (x, y, 0.22))
            b.box_base(rank, (0.46, 0.34, 0.1), (x, y, 0.95))

    # ---------------- 月台（二層石台）
    T1 = (25.0, -17.0, 13.0, 0.0, 1.3)   # 半寬、南緣、北緣、z0、z1
    T2 = (20.0, -12.0, 10.5, 1.3, 2.45)
    for (hw, y0, y1, z0, z1) in (T1, T2):
        b.box_base(M["marble_d"], (2 * hw, y1 - y0, z1 - z0), (0, (y0 + y1) / 2, z0))
        b.box_base(M["marble"], (2 * hw + 0.3, y1 - y0 + 0.3, 0.22), (0, (y0 + y1) / 2, z1 - 0.22))
        # 石台立面的分塊線
        n = int(2 * hw / 2.4)
        for k in range(n + 1):
            x = -hw + 2 * hw * k / n
            b.box_base(M["marble"], (0.12, 0.08, z1 - z0 - 0.25), (x, y0 - 0.02, z0))
        # 正面三道石階
        run = (z1 - z0) / 0.18 * 0.34
        stairs(b, M["marble"], 0, y0 - run, y0 + 0.05, z0, z1, 3.4, ramp_mi=M["marble_d"], ramp_w=1.6)
        for s in (-1, 1):
            stairs(b, M["marble"], s * 3.6, y0 - run, y0 + 0.05, z0, z1, 2.6)
            stairs(b, M["marble"], s * (hw - 4.0), y0 - run, y0 + 0.05, z0, z1, 2.6)
            # 石獸（階側）
            b.blob(M["marble"], (s * 2.0, y0 - run * 0.4, z1 + 0.15), 0.35, 0.55, 0.45, lump=0.25, sub=1)
            b.box_base(M["marble_d"], (0.7, 1.0, 0.3), (s * 2.0, y0 - run * 0.4, z1 - 0.2))
    ZB = T2[4]
    # 香爐（鼎）
    for s in (-1, 1):
        b.box_base(M["marble"], (1.0, 1.0, 0.5), (s * 15.0, -10.0, ZB))
        b.lathe(b.color("bronze", "#3b3a33", rough=0.5, metal=0.6), [(0, 0), (0.45, 0.05), (0.6, 0.45), (0.5, 0.75), (0.55, 0.85), (0, 0.85)],
                (s * 15.0, -10.0, ZB + 0.5), seg=12)

    # ---------------- 中和殿：5 間 × 4 間
    xs = [-11.6, -7.4, -3.0, 3.0, 7.4, 11.6]
    ys = [-7.6, -3.9, 0.0, 3.9, 7.6]
    b.box_base(M["marble"], (25.6, 17.6, 0.35), (0, 0, ZB))
    Z0 = ZB + 0.35
    zt = b.cn_body(M, 0, 0, Z0, xs, ys, 5.6, r_col=0.36, front="doors", sides="window", back="window", end_wall_bays=0, beam_h=1.2)
    # 門上橫窗（黃色）
    b.box_base(M["door"], (23.0, 0.2, 0.7), (0, -7.62, Z0 + 4.4 - 0.05))
    # 匾額
    b.box_base(b.color("plaque", "#2a2a2a", rough=0.6), (3.2, 0.25, 1.1), (0, -7.95, zt - 0.3))
    b.box_base(M["gold"], (2.6, 0.27, 0.7), (0, -7.97, zt - 0.1))
    b.dougong(M, 0, 0, 23.6, 15.6, zt, h=0.6, spacing=1.3, out=0.7)
    zr0 = zt + 0.75
    b.cn_roof(M, 0, 0, (17.2, 12.8), zr0, (12.4, 8.4), zr0 - 0.5, "hipgable", zr0 + 8.0, ridge_len=10.2,
              U=1.7, P=1.2, rows=12, gamma=0.62, hip_w=0.45, hip_h=0.5, ridge_h=1.0)
    # 屋脊上的雜像（小石獸）
    for s in (-1, 1):
        for k in range(5):
            t = 0.15 + 0.12 * k
            b.box_base(M["ridge"], (0.25, 0.25, 0.35), (s * (12.4 + 4.5 * t), -12.0 + 9.0 * t, zr0 + 0.6 + 3.0 * t))

    # ---------------- 周邊行閣（東西迴廊）與後方殿閣屋頂
    def haenggak(L, depth=5.0, h=3.0):
        b.box_base(M["marble_d"], (L + 0.6, depth + 0.6, 0.5), (0, 0, 0))
        b.box_base(M["red"], (L, depth - 1.6, h), (0, 0.8, 0.5))
        n = int(L / 2.8)
        for k in range(n + 1):
            b.cyl(M["col"], 0.18, 0.17, h, (-L / 2 + L * k / n, -depth / 2 + 0.3, 0.5), seg=8)
        b.box_base(M["green"], (L + 0.2, depth + 0.2, 0.5), (0, 0, 0.5 + h - 0.4))
        b.cn_roof(M, 0, 0, (L / 2 + 1.4, depth / 2 + 1.4), 0.5 + h + 0.1, (L / 2, depth / 2), 0.5 + h - 0.1, "hip",
                  0.5 + h + 2.4, ridge_len=max(0.5, L / 2 - 1.0), U=0.35, P=0.25, rows=5, hip_w=0.25, hip_h=0.3, ridge_h=0.5)
    for s in (-1, 1):
        if s > 0:
            b.place(lambda: haenggak(40.0), Matrix.Translation((s * 36.0, -22.0, 0)) @ Matrix.Rotation(-s * math.pi / 2, 4, "Z"))
        b.place(lambda: haenggak(22.0), Matrix.Translation((s * 23.0, 18.0, 0)))
    b.place(lambda: haenggak(30.0, depth=7.0, h=3.6), Matrix.Translation((0, 26.0, 0)))

    # ---------------- 樹木
    pine_m = (lf_pine, lf_dark)
    for (x, y, h) in ((-31.0, 6.0, 11.0), (-40.0, -6.0, 9.0), (-29.0, -48.0, 8.0), (33.0, 8.0, 9.0), (40.0, -50.0, 8.5)):
        b.pine(x, y, 0.0, h, pine_m, core_p, bark_r, spread=1.3, pads=7)
    for (x, y, h) in ((-26.0, 10.0, 17.0), (31.0, 30.0, 12.0), (-42.0, 25.0, 13.0), (44.0, -8.0, 11.0), (-45.0, -35.0, 12.0)):
        b.broadleaf(x, y, 0.0, h, (lf_light, lf_broad), core_b, bark, R=h * 0.42, n_blobs=7, cap=80)
    # 後方與西側的樹林
    for k in range(16):
        x = -48.0 + 96.0 * k / 15 + b.rng.uniform(-2, 2)
        y = 40.0 + b.rng.uniform(-3, 6)
        h = b.rng.uniform(11, 17)
        if b.rng.random() < 0.4:
            b.pine(x, y, 0.0, h, pine_m, core_p, bark_r, spread=1.1, pads=6)
        else:
            b.broadleaf(x, y, 0.0, h, (lf_light, lf_broad), core_b, bark, R=h * 0.4, n_blobs=6, cap=60)
    for (x, y, h) in ((-50.0, -20.0, 13.0), (-52.0, 5.0, 15.0), (-36.0, 30.0, 14.0)):
        b.broadleaf(x, y, 0.0, h, (lf_light, lf_broad), core_b, bark, R=h * 0.4, n_blobs=6, cap=60)

    b.export_glb(path)
