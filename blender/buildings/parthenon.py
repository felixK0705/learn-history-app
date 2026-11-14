"""parthenon 寫實模型（尺寸依實測資料，公尺）"""

import math

from mathutils import Matrix, Vector, noise

from lib import TAU, Builder


# ====================================================================== 帕德嫩神廟
def parthenon(path):
    b = Builder("Parthenon", seed=11)
    rock = b.tex("acropolis", "gray_rocks", tile=5.0, tint="#b9ab90", normal=1.5)
    weeds = b.color("weeds", "#7c8a45", rough=0.95)
    rock_side = b.tex("acropolis_side", "rock_04", tile=8.0, tint="#a2937a")
    marble = b.tex("marble", "white_sandstone_blocks_02", tile=3.2, tint="#dccaa4", normal=0.8)
    marble_dark = b.tex("marble_weathered", "white_sandstone_blocks_02", tile=3.2, tint="#c4ad86", normal=1.0)
    shadow = b.tex("marble_shadow", "white_sandstone_blocks_02", tile=3.2, tint="#a39377")
    col_m = b.tex("column", "plastered_wall_04", tile=2.5, tint="#d8c7a2", normal=1.4)

    def ground(x, y):
        return 0.6 * noise.noise(Vector((x * 0.04, y * 0.04, 1))) - 0.002 * (x * x + y * y) / 60

    b.ground_disc(rock, 70, rock_side, depth=18, height_fn=ground, rings=36, seg=112)
    L, W = 69.5, 30.9  # 柱座頂面（東西 × 南北）
    z0 = 1.6
    # 基座與三層台階（每層高約 0.51 m）
    b.box_base(marble_dark, (L + 4.4, W + 4.4, z0 - 1.5), (0, 0, -0.2))
    for k in range(3):
        g = (2 - k) * 0.72
        b.box_base(marble_dark if k < 2 else marble, (L + 2 * g, W + 2 * g, 0.51), (0, 0, z0 - 1.53 + k * 0.51))
    z0 = z0 - 1.53 + 1.53
    H = 10.43  # 柱高（含柱頭）
    D0, D1 = 1.905, 1.48
    inset = 0.95

    def column(x, y, h=H, broken=False):
        shaft_h = h - 0.92 if not broken else h
        # 柱身：直線收分＋輕微卷殺，20 道多立克柱槽
        prof = [(D0 / 2 - (D0 - D1) / 2 * f + 0.012 * math.sin(math.pi * f), shaft_h * f) for f in (0, 0.25, 0.5, 0.75, 1.0)]
        b.lathe(col_m, prof, (x, y, z0), seg=60, smooth=False, radial=lambda t: 1 - 0.05 * abs(math.sin(10 * t)) ** 0.6)
        if broken:
            return
        zc = z0 + shaft_h
        b.lathe(col_m, [(D1 / 2, 0), (D1 / 2 * 0.98, 0.12), (D1 / 2 * 1.2, 0.3), (1.0, 0.52), (1.02, 0.6)], (x, y, zc), seg=40)
        b.box_base(marble, (2.05, 2.05, 0.32), (x, y, zc + 0.6))

    xs = [-L / 2 + inset + (L - 2 * inset) * i / 16 for i in range(17)]
    ys = [-W / 2 + inset + (W - 2 * inset) * j / 7 for j in range(8)]
    cols = [(x, ys[0], "S", i) for i, x in enumerate(xs)] + [(x, ys[-1], "N", i) for i, x in enumerate(xs)]
    cols += [(xs[0], y, "W", j) for j, y in enumerate(ys[1:-1])] + [(xs[-1], y, "E", j) for j, y in enumerate(ys[1:-1])]
    south_gap = range(6, 12)  # 1687 年爆炸，南側中段柱列尚未完全修復
    for x, y, side, i in cols:
        if side == "S" and i in south_gap:
            if i in (6, 11):
                column(x, y, h=H * 0.55, broken=True)
            elif i % 2 == 0:
                column(x, y, h=H * 0.25, broken=True)
            continue
        column(x, y)
    # 內側門廊（東西各 6 柱）
    for xx in (xs[1] + 1.6, xs[-2] - 1.6):
        for j in range(6):
            column(xx, ys[1] + (ys[-2] - ys[1]) * j / 5)

    ze = z0 + H
    arch_h, frieze_h, cornice_h = 1.35, 1.35, 0.6

    # 柱楣：外框矩形（不重疊的四段）＋三槽板；南側中段缺口
    ox0, ox1 = -L / 2 + inset - 1.05, L / 2 - inset + 1.05
    oy0, oy1 = -W / 2 + inset - 1.05, W / 2 - inset + 1.05
    dep = 2.1
    gap0, gap1 = xs[6] - 1.0, xs[11] + 1.0

    def layer(z, h, m, grow=0.0, south_gap=True, triglyph=False):
        segs = [((ox0 - grow, ox1 + grow), (oy1 - dep, oy1 + grow))]  # 北
        if south_gap:
            segs += [((ox0 - grow, gap0), (oy0 - grow, oy0 + dep)), ((gap1, ox1 + grow), (oy0 - grow, oy0 + dep))]
        else:
            segs += [((ox0 - grow, ox1 + grow), (oy0 - grow, oy0 + dep))]
        segs += [((ox0 - grow, ox0 + dep), (oy0 + dep, oy1 - dep)), ((ox1 - dep, ox1 + grow), (oy0 + dep, oy1 - dep))]
        for (x0_, x1_), (y0_, y1_) in segs:
            b.box_base(m, (x1_ - x0_, y1_ - y0_, h), ((x0_ + x1_) / 2, (y0_ + y1_) / 2, z))

    layer(ze, arch_h, marble)
    layer(ze + arch_h, frieze_h, marble_dark)
    layer(ze + arch_h + frieze_h, cornice_h, marble, grow=0.3)
    # 三槽板只放在外側立面
    for k in range(64):
        x = ox0 + 0.6 + (ox1 - ox0 - 1.2) * k / 63
        for yy, out in ((oy1, 1), (oy0, -1)):
            if out < 0 and gap0 - 0.5 < x < gap1 + 0.5:
                continue
            b.box_base(shadow, (0.84, 0.1, frieze_h * 0.96), (x, yy + out * 0.04, ze + arch_h))
    for k in range(28):
        y = oy0 + 0.6 + (oy1 - oy0 - 1.2) * k / 27
        for xx, out in ((ox0, -1), (ox1, 1)):
            b.box_base(shadow, (0.1, 0.84, frieze_h * 0.96), (xx + out * 0.04, y, ze + arch_h))
    for sx_ in (-1, 1):
        x0 = sx_ * (L / 2 - inset)
        # 三角山牆（坡度約 13.5°）
        zt = ze + arch_h + frieze_h + cornice_h
        ph = (oy1 - oy0) / 2 * math.tan(math.radians(13.5))
        M = Matrix.Translation((x0, 0, zt)) @ Matrix.Rotation(math.pi / 2, 4, "Z")
        b.profile_wall(marble, [(oy0, 0), (oy1, 0), (0, ph)], 1.9, M)
        # 殘存的山牆雕像（西側較多）
        for k in range(5 if sx_ < 0 else 2):
            yy = (-0.5 + k / 4) * W * 0.6 if sx_ < 0 else (k - 0.5) * 6
            b.rock(marble_dark, (1.0, 1.6, 1.8), (x0 + sx_ * 0.3, yy, zt + 0.9), rough=0.15, seed=k + (10 if sx_ < 0 else 20))

    # 殘破的頂緣：沿柱楣頂部散置高低不一的殘石
    ztop = ze + arch_h + frieze_h + cornice_h
    for k in range(60):
        t = b.rng.random()
        if b.rng.random() < 0.5:
            x = -L / 2 + inset + (L - 2 * inset) * t
            if (-L / 2 + inset + (L - 2 * inset) * 6 / 16 - 1) < x < (-L / 2 + inset + (L - 2 * inset) * 11 / 16 + 1) and b.rng.random() < 0.6:
                continue
            y = (W / 2 - inset) * (1 if b.rng.random() < 0.5 else -1)
        else:
            x = (L / 2 - inset) * (1 if b.rng.random() < 0.5 else -1)
            y = -W / 2 + inset + (W - 2 * inset) * t
        b.rock(marble_dark, (b.rng.uniform(1.2, 2.6), b.rng.uniform(1.0, 1.8), b.rng.uniform(0.3, 0.8)), (x, y, ztop + 0.15), rot=(0, 0, b.rng.random() * 0.3), rough=0.08, seed=200 + k, round_=0.05)
    # 內殿（cella）殘牆：西側後室牆與門
    cw = W - 2 * inset - 4.2
    zc = z0
    for yy in (-cw / 2, cw / 2):
        b.box_base(marble_dark, (14.0, 1.2, 8.5), (-L / 2 + 15, yy, zc))
    b.box_base(marble_dark, (1.2, cw * 0.32, 10.0), (-L / 2 + 8.4, -cw / 2 + cw * 0.16, zc))
    b.box_base(marble_dark, (1.2, cw * 0.32, 10.0), (-L / 2 + 8.4, cw / 2 - cw * 0.16, zc))
    b.box_base(marble_dark, (1.2, cw * 0.36, 2.5), (-L / 2 + 8.4, 0, zc + 7.5))
    b.box_base(marble_dark, (36, 1.0, 1.4), (6, cw / 2, zc))
    b.box_base(marble_dark, (20, 1.0, 0.9), (2, -cw / 2, zc))
    # 散落的石塊與鼓石
    for k in range(220):
        x = b.rng.uniform(-60, 60)
        y = b.rng.uniform(-60, 60)
        if abs(x) < L / 2 + 4 and abs(y) < W / 2 + 4:
            continue
        if math.hypot(x, y) > 62:
            continue
        if b.rng.random() < 0.4:
            b.lathe(marble_dark, [(0.85, 0), (0.85, 0.9)], (x, y, ground(x, y) - 0.1), seg=24, smooth=True, radial=lambda t: 1 - 0.045 * abs(math.sin(10 * t)) ** 0.7)
        else:
            b.rock(marble_dark, (b.rng.uniform(0.8, 3.2), b.rng.uniform(0.6, 1.6), b.rng.uniform(0.4, 1.1)), (x, y, ground(x, y) + 0.2), rot=(0, 0, b.rng.random() * 3), rough=0.07, seed=k, round_=0.06)
    b.export(path)
