"""colosseum 寫實模型（尺寸依實測資料，公尺）"""

import math

from mathutils import Matrix, Vector, noise

from lib import TAU, Builder


def _ellipse_frame(a, b, t):
    """橢圓上一點與其外法線角度"""
    x, y = a * math.cos(t), b * math.sin(t)
    ang = math.atan2(math.sin(t) / b, math.cos(t) / a)
    return x, y, ang



# ====================================================================== 羅馬競技場
def colosseum(path):
    b = Builder("Colosseum", seed=13)
    pave = b.tex("paving", "gravel_floor", tile=3.0, tint="#a39a8a")
    soil = b.color("soil", "#6b5a45", rough=0.95)
    trav = b.tex("travertine", "sandstone_blocks_05", tile=3.0, tint="#c8a882", normal=1.2)
    trav_dark = b.tex("travertine_dark", "sandstone_blocks_05", tile=3.0, tint="#9f8466", normal=1.2)
    brick = b.tex("brick", "castle_brick_02_red", tile=2.2, tint="#a66549")
    wood = b.color("arena_floor", "#8a6a4a", rough=0.8)
    grass = b.tex("grass", "grass_ground", tile=4.0, tint="#5f7f36")

    b.ground_disc(pave, 170, soil, depth=4, rings=20, seg=128)
    b.ering(grass, (125, 110), (150, 135), 0.0, 0.05, seg=128, t0=math.radians(200), t1=math.radians(330))
    A, B_ = 94.5, 78.0  # 外環半軸（189 × 156 m）
    T = 2.4
    tiers = [(0.0, 10.5), (10.5, 11.85), (22.35, 11.6)]
    n = 80
    intact = (math.radians(25), math.radians(165))  # 北側外環仍完整

    def in_intact(t):
        t = t % TAU
        return intact[0] <= t <= intact[1]

    def arcade_ring(a, bb, depth, tiers_, keep, half_col=True, opening=4.2):
        for i in range(n):
            t = TAU * (i + 0.5) / n
            if not keep(t):
                continue
            x, y, ang = _ellipse_frame(a, bb, t)
            chord = 2 * math.hypot(a * math.sin(t), bb * math.cos(t)) * math.sin(math.pi / n) + 0.15
            for k, (z, h) in enumerate(tiers_):
                M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(ang - math.pi / 2, 4, "Z")
                b.arch_frame(trav, chord, h - 1.2, (h - 1.2) * 0.6, opening, depth, M)
                # 樓層之間的簷帶
                b.box_base(trav_dark, (chord, depth + 0.6, 1.2), (x, y, z + h - 1.2), rot=(0, 0, ang - math.pi / 2))
                if half_col:
                    # 半露柱（多立克／愛奧尼克／科林斯）
                    xx = x + math.cos(ang) * depth / 2
                    yy = y + math.sin(ang) * depth / 2
                    px = xx + math.cos(ang - math.pi / 2) * chord / 2
                    py = yy + math.sin(ang - math.pi / 2) * chord / 2
                    b.cyl(trav, 0.55, 0.5, h - 1.6, (px, py, z), seg=10)
                    b.box_base(trav_dark, (1.3, 1.3, 0.4), (px, py, z + h - 1.6), rot=(0, 0, ang))

    # 外環：北側完整三層拱廊＋頂層實牆
    arcade_ring(A, B_, T, tiers, in_intact)
    za = 34.0
    for i in range(n):
        t = TAU * (i + 0.5) / n
        if not in_intact(t):
            continue
        x, y, ang = _ellipse_frame(A, B_, t)
        chord = 2 * math.hypot(A * math.sin(t), B_ * math.cos(t)) * math.sin(math.pi / n) + 0.15
        b.box_base(trav, (chord, T, 14.0), (x, y, za), rot=(0, 0, ang - math.pi / 2))
        xx = x + math.cos(ang) * (T / 2 + 0.05)
        yy = y + math.sin(ang) * (T / 2 + 0.05)
        if i % 2 == 0:
            b.box_base(b.color("window", "#3a2e24", rough=1.0), (1.4, 0.2, 2.4), (xx, yy, za + 5.0), rot=(0, 0, ang - math.pi / 2))
        # 壁柱與頂部托架
        px = xx + math.cos(ang - math.pi / 2) * chord / 2
        py = yy + math.sin(ang - math.pi / 2) * chord / 2
        b.box_base(trav_dark, (1.0, 0.5, 13.0), (px, py, za), rot=(0, 0, ang - math.pi / 2))
        b.box_base(trav_dark, (0.6, 0.9, 0.6), (xx, yy, za + 12.0), rot=(0, 0, ang - math.pi / 2))
    # 崩塌端的磚造扶壁（19 世紀加固）
    for t in intact:
        x, y, ang = _ellipse_frame(A, B_, t)
        tx, ty = -math.sin(ang), math.cos(ang)
        sgn = -1 if t == intact[0] else 1
        for k in range(5):
            h = 48 - k * 8
            b.box_base(brick, (6.0, T + 1.5, h), (x + tx * sgn * (2 + k * 4.5), y + ty * sgn * (2 + k * 4.5), 0), rot=(0, 0, ang - math.pi / 2))
    # 外環崩塌處：殘存的一層拱基與斷牆
    def ruined_low(t):
        return not in_intact(t)

    for i in range(n):
        t = TAU * (i + 0.5) / n
        if not ruined_low(t):
            continue
        x, y, ang = _ellipse_frame(A, B_, t)
        b.box_base(trav_dark, (2.0, T, b.rng.uniform(0.5, 3.5)), (x, y, 0), rot=(0, 0, ang - math.pi / 2))

    # 第二環（內側拱廊，外環崩塌後露出）：兩層，略低
    A2, B2 = A - 11.5, B_ - 11.5
    arcade_ring(A2, B2, 2.0, [(0.0, 10.5), (10.5, 11.0)], lambda t: True, half_col=False, opening=3.6)
    b.ering(brick, (A2 - 1.0, B2 - 1.0), (A2 + 1.0, B2 + 1.0), 21.5, 25.5, seg=160, t0=math.radians(170), t1=math.radians(380))
    # 環形拱廊之間的放射牆（磚造）
    for i in range(n):
        t = TAU * (i + 0.5) / n
        x1, y1, ang = _ellipse_frame(A - 1.5, B_ - 1.5, t)
        x2, y2, _ = _ellipse_frame(A2 + 1.0, B2 + 1.0, t)
        h = 21.5 if in_intact(t) else 10.0 + 6 * abs(math.sin(i))
        L = math.hypot(x1 - x2, y1 - y2)
        b.box_base(brick, (L, 1.0, h), ((x1 + x2) / 2, (y1 + y2) / 2, 0), rot=(0, 0, ang))

    # 看台（座席已大多消失，露出磚造拱頂結構，呈階梯狀上升）
    rings = [((44.0, 27.0), (52.0, 35.0), 4.5), ((52.0, 35.0), (60.0, 43.0), 9.0), ((60.0, 43.0), (68.0, 51.0), 13.5), ((68.0, 51.0), (A2 - 1.0, B2 - 1.0), 18.0)]
    for inner, outer, h in rings:
        b.ering(brick, inner, outer, 0, h, seg=128)
        b.ering(trav_dark, inner, (inner[0] + 1.2, inner[1] + 1.2), h, h + 0.6, seg=128)
    # 重建的東側座席
    b.ering(trav, (52.0, 35.0), (68.0, 51.0), 13.5, 14.2, seg=64, t0=math.radians(-25), t1=math.radians(25))
    # 競技場：西側露出地下室（hypogeum）牆體、東側重建木地板
    a_in, b_in = 41.5, 24.0
    b.ering(trav_dark, (a_in - 0.01, b_in - 0.01), (44.0, 27.0), 0, 4.5, seg=96)
    for k in range(18):
        x = -a_in + 2 + k * 3.4
        if x > a_in * 0.35:
            break
        hy = b_in * math.sqrt(max(0, 1 - (x / a_in) ** 2)) - 0.5
        b.box_base(brick, (0.7, 2 * hy, 3.8), (x, 0, 0))
    for y in (-14, -7, 0, 7, 14):
        b.box_base(brick, (a_in * 1.3, 0.6, 3.8), (-a_in * 0.3, y, 0))
    b.ering(wood, (0.01, 0.01), (a_in, b_in), 3.6, 4.0, seg=64, t0=math.radians(-60), t1=math.radians(60))
    # 周圍石松
    for x, y in b.scatter(18, 115, 165, min_dist=10):
        hgt = b.rng.uniform(14, 20)
        b.cyl(b.color("trunk", "#5a4330"), 0.4, 0.3, hgt * 0.75, (x, y, 0), seg=7)
        b.rock(b.color("pine_canopy", "#3e5a2a", rough=0.9), (hgt * 0.7, hgt * 0.7, hgt * 0.22), (x, y, hgt * 0.82), rough=0.3, subdiv=2, seed=int(x * 7), flat_bottom=False)
    b.export(path)
