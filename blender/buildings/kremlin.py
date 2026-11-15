"""kremlin 莫斯科紅場：聖瓦西里主教座堂、救世主塔（斯帕斯卡亞塔）與克里姆林宮東牆寫實模型（公尺）

- 聖瓦西里主教座堂（1555–61）：中央帳篷頂教堂高約 47.5 m，四周四座大（東西南北）與四座小（斜角）禮拜堂，
  各頂一座彩繪洋蔥頂（菱格、鋸齒條紋、螺旋條紋、魚鱗紋）；建於約 7 m 高的紅磚台基與迴廊上；東南角鐘樓（綠色帳篷頂）
- 救世主塔：方形紅磚塔身 → 白石哥德式層 → 鐘面層（直徑約 6 m 的鐘）→ 八角層 → 綠帳篷尖頂與紅星，總高 71 m
- 克里姆林宮東牆：紅磚、燕尾形雉堞，牆高約 12 m；沿牆有沙皇塔、警鐘塔、康斯坦丁－葉連娜塔、元老院塔、
  東南角圓形的別克列米舍夫塔；牆前列寧墓（紅黑花崗岩階梯體）；廣場對面古姆百貨的一段
- 地面：紅場的灰色石塊路面、牆前草坪

座標：+X 東、+Y 北，聖瓦西里中心在原點。參考照由南方（瓦西里斜坡）向北拍攝，左側為救世主塔。
"""

import math

from mathutils import Matrix, Vector

from lib import TAU, Builder

from .hagia_sophia import broadleaf, foliage_mats

CAMERA = ((-17.8, -6.9, 22.4), 32.5, -11.7, 102.2, 26)

S0 = Vector((-113.0, 0.0, 0.0))                  # 救世主塔（與聖瓦西里同緯度，正西約 113 m）
# 兩段牆：往西北（紅場一側，元老院塔方向）與往南南東（往別克列米舍夫塔）；V 皆指向牆外（廣場一側）
FRAMES = {
    "nw": (Vector((-0.68, 0.733, 0)).normalized(), Vector((0.733, 0.68, 0)).normalized()),
    "sse": (Vector((-0.284, 0.959, 0)).normalized(), Vector((0.959, 0.284, 0)).normalized()),
}
U, V = FRAMES["nw"]
ANG_U = math.atan2(U.y, U.x)


def use(fr):
    global U, V, ANG_U
    U, V = FRAMES[fr]
    ANG_U = math.atan2(U.y, U.x)


def W(u, v, z=0.0):
    p = S0 + U * u + V * v
    return (p.x, p.y, z)


# ====================================================================== 共用造型
def onion(b, cx, cy, z0, R, H, mats, pattern, seg=32, n=18, neck=0.72):
    """洋蔥頂：自訂經緯格，每格依 pattern(i, j) 選材質（做出螺旋、鋸齒、菱格、魚鱗）"""
    prof = [(neck, 0.0), (0.9, 0.05), (1.0, 0.17), (0.99, 0.3), (0.9, 0.43), (0.72, 0.56), (0.5, 0.68), (0.3, 0.79),
            (0.16, 0.88), (0.08, 0.94), (0.03, 0.985)]
    # 以弧長均勻重新取樣成 n 段
    import bisect

    L = [0.0]
    for (r0, z0_), (r1, z1_) in zip(prof, prof[1:]):
        L.append(L[-1] + math.hypot((r1 - r0) * R, (z1_ - z0_) * H))
    pts = []
    for k in range(n + 1):
        s = L[-1] * k / n
        i = min(len(prof) - 2, max(0, bisect.bisect_right(L, s) - 1))
        t = (s - L[i]) / max(1e-9, L[i + 1] - L[i])
        r = prof[i][0] + (prof[i + 1][0] - prof[i][0]) * t
        z = prof[i][1] + (prof[i + 1][1] - prof[i][1]) * t
        pts.append((r * R, z * H))
    rings = []
    for r, z in pts:
        rings.append([b.bm.verts.new((cx + r * math.cos(TAU * i / seg), cy + r * math.sin(TAU * i / seg), z0 + z)) for i in range(seg)])
    apex = b.bm.verts.new((cx, cy, z0 + H))
    for j in range(n):
        for i in range(seg):
            f = b.bm.faces.new([rings[j][i], rings[j][(i + 1) % seg], rings[j + 1][(i + 1) % seg], rings[j + 1][i]])
            f.material_index = mats[pattern(i, j) % len(mats)]
            f.smooth = True
    for i in range(seg):
        f = b.bm.faces.new([rings[n][i], rings[n][(i + 1) % seg], apex])
        f.material_index = mats[pattern(i, n) % len(mats)]
        f.smooth = True
    f = b.bm.faces.new(list(reversed(rings[0])))
    f.material_index = mats[0]
    return z0 + H


def cross(b, mi, x, y, z, h=2.6):
    b.box_base(mi, (0.16, 0.16, h), (x, y, z))
    b.box_base(mi, (1.1, 0.12, 0.12), (x, y, z + h * 0.72))
    b.box_base(mi, (0.7, 0.1, 0.1), (x, y, z + h * 0.45), rot=(0, 0, 0.0))


def oct_shaft(b, mi, R, z0, z1, cx, cy, rot=math.pi / 8):
    pts = [(cx + R * math.cos(rot + TAU * k / 8), cy + R * math.sin(rot + TAU * k / 8)) for k in range(8)]
    b.prism(mi, pts, z0, z1 - z0)


def kokoshniks(b, mi, cx, cy, z, R, n, w, h, depth=0.5, rot=0.0, kind="keel"):
    """一圈山牆形裝飾（kokoshnik）：圓拱或龍骨拱"""
    for k in range(n):
        a = rot + TAU * k / n
        M = Matrix.Translation((cx + math.cos(a) * R, cy + math.sin(a) * R, z)) @ Matrix.Rotation(a + math.pi / 2, 4, "Z")
        pts = [(-w / 2, 0), (w / 2, 0)]
        m = 8
        for i in range(1, m):
            t = math.pi * i / m
            x = w / 2 * math.cos(t)
            y = h * 0.7 * math.sin(t)
            if kind == "keel":
                y += h * 0.3 * max(0.0, 1 - abs(x) / (w / 2)) ** 2
            pts.append((x, y))
        if kind == "keel":
            pts.insert(2 + m // 2 - 1, (0.0, h))
            pts = [(-w / 2, 0), (w / 2, 0)] + sorted(pts[2:], key=lambda p: -p[0])
        b.profile_wall(mi, pts, depth, M)


def tent(b, mi, R, z0, h, cx, cy, sides=8, r_top=0.4, rot=math.pi / 8):
    b.lathe(mi, [(R, z0), (r_top, z0 + h)], (cx, cy, 0), seg=sides, smooth=False, rot_offset=rot)


def merlons(b, mi, p0, p1, z, spacing=3.4, w=1.7, h=2.3, depth=0.9):
    """燕尾形雉堞列（p0→p1 為牆外緣線）"""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    ang = math.atan2(d.y, d.x)
    n = max(1, int(L / spacing))
    for k in range(n):
        p = p0 + d * ((k + 0.5) / n)
        M = Matrix.Translation((p.x, p.y, z)) @ Matrix.Rotation(ang, 4, "Z")
        b.profile_wall(mi, [(-w / 2, 0), (w / 2, 0), (w / 2, h), (0, h - 0.75), (-w / 2, h)], depth, M)


# ====================================================================== 主體
def kremlin(path):
    b = Builder("Kremlin", seed=29)
    brick = b.tex("brick", "brick_wall_006", tile=2.5, tint="#9a3a2c", rough=0.85, normal=0.7)
    brick_sb = b.tex("brick_sb", "brick_wall_006", tile=2.0, tint="#b44a36", rough=0.85, normal=0.6)
    white = b.color("white_stone", "#efe7da", rough=0.7)
    cream = b.color("cream", "#e8d9b8", rough=0.75)
    green = b.color("green_roof", "#3f7650", rough=0.5, metal=0.2)
    green_d = b.color("green_dark", "#2f5f3e", rough=0.5, metal=0.2)
    gold = b.color("gold", "#d8aa42", rough=0.25, metal=1.0)
    gold_d = b.color("gold_d", "#a87d2a", rough=0.3, metal=1.0)
    red = b.color("dome_red", "#b8322a", rough=0.45)
    pink = b.color("dome_pink", "#d85f6d", rough=0.45)
    wpink = b.color("dome_white", "#f1e8e2", rough=0.45)
    dgreen = b.color("dome_green", "#2e7a4a", rough=0.45)
    lgreen = b.color("dome_lgreen", "#8fbf6a", rough=0.45)
    yellow = b.color("dome_yellow", "#e3c55c", rough=0.45)
    blue = b.color("dome_blue", "#3a62a6", rough=0.45)
    orange = b.color("tent_orange", "#d0663e", rough=0.6)
    win = b.color("window", "#2c2a2b", rough=0.35)
    clock = b.color("clock_face", "#1d2840", rough=0.4)
    ruby = b.color("ruby", "#c4182a", rough=0.15, metal=0.2)
    granite = b.color("granite_red", "#5a2c28", rough=0.4)
    granite_k = b.color("granite_black", "#2a2627", rough=0.35)
    cobble = b.tex("cobble", "gravel_floor", tile=2.5, tint="#7c7975", rough=0.85, normal=0.6)
    curb = b.tex("curb", "large_sandstone_blocks", tile=3.0, tint="#a39d91", rough=0.85, normal=0.6)
    grass = b.tex("grass", "grass_ground", tile=5.0, tint="#5d7a3a", gain=0.9, rough=0.95, normal=0)
    soil = b.color("soil", "#6b5a45", rough=0.95)
    plaster = b.tex("plaster", "plastered_wall_04", tile=6.0, tint="#e2d6b8", rough=0.85, normal=0.5)
    leaves = foliage_mats(b)
    trunk = b.color("trunk", "#5a4a3a", rough=0.9)

    T = lambda x, y, z=0.0: Matrix.Translation((x, y, z))  # noqa: E731
    Rz = lambda a: Matrix.Rotation(a, 4, "Z")  # noqa: E731

    # ---------------------------------------------------------------- 地面
    b.ground_disc(cobble, 250, soil, depth=3, rings=12, seg=80)
    # 牆前草坪帶
    for fr, u0, u1 in (("sse", -280, -8), ("nw", 8, 150)):
        use(fr)
        c = W((u0 + u1) / 2, 6.0)
        b.box_base(grass, (u1 - u0, 9.0, 0.08), c, rot=(0, 0, ANG_U))

    # ---------------------------------------------------------------- 克里姆林牆
    WALL_H, WALL_T = 12.0, 4.5

    def wall_seg(ua, ub):
        c = W((ua + ub) / 2, -WALL_T / 2)
        b.box_base(brick, (ub - ua, WALL_T, WALL_H), c, rot=(0, 0, ANG_U))
        b.box_base(white, (ub - ua, 0.4, 0.35), (c[0] + V.x * 2.4, c[1] + V.y * 2.4, 2.0), rot=(0, 0, ANG_U))
        merlons(b, brick, W(ua, 0.0), W(ub, 0.0), WALL_H)
        merlons(b, brick, W(ub, -WALL_T), W(ua, -WALL_T), WALL_H, spacing=4.5, h=1.6)

    towers = {"spasskaya": 0.0, "senate": 167.0, "tsar": -30.0, "nabat": -70.0, "konst": -176.0}
    use("sse")
    for ua, ub in ((-282, -183), (-169, -75), (-65, -7)):
        wall_seg(ua, ub)
    use("nw")
    for ua, ub in ((7, 162), (172, 235)):
        wall_seg(ua, ub)

    def tower(u, w, h_body, tiers, roof_h, star=False, roof_mi=green, round_=False):
        cx, cy, _ = W(u, -WALL_T / 2 + 0.5)
        if round_:
            b.lathe(brick, [(w / 2, 0), (w / 2 * 0.92, h_body)], (cx, cy, 0), seg=24, smooth=False)
            b.lathe(white, [(w / 2 * 0.95, h_body - 0.6), (w / 2 + 0.6, h_body), (w / 2 * 0.9, h_body)], (cx, cy, 0), seg=24, smooth=False)
            z = h_body
            r = w / 2 * 0.75
            b.lathe(brick, [(r, z), (r, z + 6.0)], (cx, cy, 0), seg=8, smooth=False)
            tent(b, roof_mi, r + 0.4, z + 6.0, roof_h, cx, cy, sides=8)
            return
        b.box_base(brick, (w, w, h_body), (cx, cy, 0), rot=(0, 0, ANG_U))
        b.box_base(white, (w + 0.8, w + 0.8, 0.5), (cx, cy, h_body - 2.4), rot=(0, 0, ANG_U))
        z = h_body
        ww = w
        for th, shrink in tiers:
            ww = ww * shrink
            b.box_base(brick, (ww, ww, th), (cx, cy, z), rot=(0, 0, ANG_U))
            b.box_base(white, (ww + 0.5, ww + 0.5, 0.35), (cx, cy, z + th - 0.35), rot=(0, 0, ANG_U))
            for s in (-1, 1):
                for t in (-1, 1):
                    q = Vector((cx, cy, 0)) + U * (s * ww / 2) + V * (t * ww / 2)
                    b.cone(white, 0.35, 2.0, (q.x, q.y, z + th), seg=4)
            z += th
        tent(b, roof_mi, ww * 0.62, z, roof_h, cx, cy, sides=8)
        zt = z + roof_h
        if star:
            b.cyl(gold, 0.15, 0.15, 2.0, (cx, cy, zt), seg=6)
            star_shape(b, ruby, gold, cx, cy, zt + 3.0, 1.8)
        else:
            b.ico(gold, 0.35, (cx, cy, zt + 0.3), subdiv=1)
            b.box_base(gold, (0.1, 0.1, 1.8), (cx, cy, zt + 0.5))

    # 元老院塔、沙皇塔、警鐘塔、康斯坦丁塔
    use("nw")
    tower(towers["senate"], 9.0, 16.0, [(6.0, 0.8)], 10.0)
    use("sse")
    tower(towers["nabat"], 8.0, 15.0, [(5.0, 0.82), (4.0, 0.8)], 9.0)
    tower(towers["konst"], 11.0, 17.0, [(6.0, 0.8)], 11.0)
    # 沙皇塔：牆上的小帳篷亭
    cx, cy, _ = W(towers["tsar"], -1.5)
    b.box_base(brick, (4.0, 4.0, 2.5), (cx, cy, WALL_H), rot=(0, 0, ANG_U))
    for s in (-1, 1):
        for t in (-1, 1):
            q = Vector((cx, cy, 0)) + U * (s * 1.7) + V * (t * 1.7)
            b.box_base(white, (0.4, 0.4, 3.2), (q.x, q.y, WALL_H + 2.5))
    tent(b, green, 3.0, WALL_H + 5.7, 4.5, cx, cy, sides=4, rot=ANG_U + math.pi / 4)
    b.ico(gold, 0.3, (cx, cy, WALL_H + 10.4), subdiv=1)
    # 別克列米舍夫塔（東南角圓塔）與轉向河岸的牆
    tower(-289.0, 14.0, 26.0, [], 17.0, round_=True)
    p_c = Vector(W(-289.0, -WALL_T / 2))
    a0 = p_c + Vector((-8, 0, 0))
    a1 = p_c + Vector((-75, 0, 0))
    mid = (a0 + a1) / 2
    b.box_base(brick, ((a1 - a0).length, WALL_T, WALL_H), (mid.x, mid.y, 0))
    merlons(b, brick, a1 + Vector((0, -WALL_T / 2, 0)), a0 + Vector((0, -WALL_T / 2, 0)), WALL_H)
    use("nw")

    # ---------------------------------------------------------------- 救世主塔
    sx, sy, _ = W(0.0, -1.5)
    SW_ = 13.0
    rot = (0, 0, ANG_U)
    b.box_base(brick, (SW_, SW_ + 3.0, 26.0), (sx, sy, 0), rot=rot)
    # 城門（朝廣場）
    gx, gy, _ = W(0.0, 0.05)
    Mg = T(gx, gy, 0) @ Rz(ANG_U)
    b.profile_wall(win, [(-2.4, 0), (2.4, 0), (2.4, 6.0), (0, 8.4), (-2.4, 6.0)], 0.2, Mg @ T(0, 1.4 + (SW_ + 3) / 2 - 1.5, 0))
    gx, gy, _ = W(0.0, (SW_ + 3.0) / 2 - 1.5 + 0.02)
    Mg = T(gx, gy, 0) @ Rz(ANG_U + math.pi)
    b.profile_wall(win, [(-2.4, 0), (2.4, 0), (2.4, 6.0), (0, 8.4), (-2.4, 6.0)], 0.2, Mg)
    b.profile_wall(white, [(-3.2, 0), (3.2, 0), (3.2, 7.0), (0, 10.2), (-3.2, 7.0)], 0.4, Mg @ T(0, 0.15, 0))
    b.box_base(white, (SW_ + 1.0, SW_ + 4.0, 0.6), (sx, sy, 22.0), rot=rot)
    b.box_base(white, (SW_ + 1.4, SW_ + 4.4, 1.2), (sx, sy, 24.8), rot=rot)
    for s in (-1, 1):  # 白石小尖塔（門樓上方四角）
        for t in (-1, 1):
            q = Vector((sx, sy, 0)) + U * (s * (SW_ / 2)) + V * (t * (SW_ + 3) / 2)
            b.box_base(white, (0.9, 0.9, 3.0), (q.x, q.y, 26.0))
            b.cone(white, 0.6, 3.0, (q.x, q.y, 29.0), seg=4)
            b.ico(gold, 0.25, (q.x, q.y, 32.1), subdiv=1)
    # 第二層（白石哥德式、紅磚）
    b.box_base(brick, (11.6, 11.6, 10.0), (sx, sy, 26.0), rot=rot)
    for f in range(4):
        a = ANG_U + f * math.pi / 2
        Mf = T(sx, sy, 0) @ Rz(a) @ T(0, -5.82, 0)
        for u in (-3.2, 0.0, 3.2):
            b.profile_wall(white, [(-1.0, 0), (1.0, 0), (1.0, 5.0), (0, 6.6), (-1.0, 5.0)], 0.3, Mf @ T(u, 0, 28.0))
            b.profile_wall(win, [(-0.6, 0), (0.6, 0), (0.6, 4.2), (0, 5.5), (-0.6, 4.2)], 0.1, Mf @ T(u, -0.18, 28.4))
    b.box_base(white, (12.4, 12.4, 0.8), (sx, sy, 35.8), rot=rot)
    for s in (-1, 1):
        for t in (-1, 1):
            q = Vector((sx, sy, 0)) + U * (s * 5.6) + V * (t * 5.6)
            b.cyl(white, 0.55, 0.45, 4.5, (q.x, q.y, 36.6), seg=8)
            b.cone(white, 0.5, 2.5, (q.x, q.y, 41.1), seg=8)
            b.ico(gold, 0.2, (q.x, q.y, 43.7), subdiv=1)
    # 鐘面層
    b.box_base(brick, (10.4, 10.4, 12.0), (sx, sy, 36.6), rot=rot)
    for f in range(4):
        a = ANG_U + f * math.pi / 2
        for mi, r, th, off in ((white, 3.75, 0.25, 0.0), (gold, 3.3, 0.35, 0.05), (clock, 3.0, 0.4, 0.1)):
            vs = b.cyl(mi, r, r, th, (0, 0, 0), seg=28)
            import bmesh

            M = T(sx, sy, 42.6) @ Rz(a) @ T(0, -5.22 - off, 0) @ Matrix.Rotation(math.pi / 2, 4, "X")
            bmesh.ops.transform(b.bm, matrix=M, verts=vs)
        for k in range(12):  # 金色時標
            t_ = TAU * k / 12
            p = Matrix.Translation((0, 0, 0)) @ T(sx, sy, 42.6) @ Rz(a) @ Vector((math.cos(t_) * 2.6, -5.72, math.sin(t_) * 2.6))
            b.box_base(gold, (0.25, 0.25, 0.25), (p.x, p.y, p.z - 0.12))
        # 指針
        p = T(sx, sy, 42.6) @ Rz(a) @ Vector((0, -5.75, 0))
        b.box_base(gold, (0.2, 0.15, 2.2), (p.x, p.y, p.z), rot=(0, 0, a))
    b.box_base(white, (11.2, 11.2, 1.0), (sx, sy, 48.6), rot=rot)
    for s in (-1, 1):
        for t in (-1, 1):
            q = Vector((sx, sy, 0)) + U * (s * 4.9) + V * (t * 4.9)
            b.cyl(white, 0.45, 0.4, 3.0, (q.x, q.y, 49.6), seg=8)
            b.cone(white, 0.42, 2.6, (q.x, q.y, 52.6), seg=8)
            b.ico(gold, 0.2, (q.x, q.y, 55.3), subdiv=1)
    # 八角鐘樓層
    oct_shaft(b, brick, 4.9, 49.6, 57.5, sx, sy, rot=ANG_U + math.pi / 8)
    for k in range(8):
        a = ANG_U + TAU * k / 8
        M = T(sx + math.cos(a) * 4.55, sy + math.sin(a) * 4.55, 51.0) @ Rz(a + math.pi / 2)
        b.profile_wall(win, [(-1.2, 0), (1.2, 0), (1.2, 3.6), (0, 5.0), (-1.2, 3.6)], 0.15, M)
        b.profile_wall(white, [(-0.25, 0), (0.25, 0), (0.25, 6.0), (-0.25, 6.0)], 0.4, T(sx + math.cos(a + math.pi / 8) * 4.6,
                       sy + math.sin(a + math.pi / 8) * 4.6, 50.0) @ Rz(a + math.pi / 8 + math.pi / 2))
    oct_shaft(b, white, 5.2, 57.5, 58.3, sx, sy, rot=ANG_U + math.pi / 8)
    oct_shaft(b, brick, 4.3, 58.3, 61.0, sx, sy, rot=ANG_U + math.pi / 8)
    kokoshniks(b, white, sx, sy, 60.6, 4.1, 8, 2.6, 1.6, depth=0.3, rot=ANG_U, kind="round")
    tent(b, green, 4.0, 61.0, 6.6, sx, sy, sides=8, r_top=0.5, rot=ANG_U + math.pi / 8)
    for k in range(8):   # 帳篷頂金色稜線
        a = ANG_U + math.pi / 8 + TAU * k / 8
        p0 = Vector((sx + math.cos(a) * 4.0, sy + math.sin(a) * 4.0, 61.0))
        p1 = Vector((sx + math.cos(a) * 0.5, sy + math.sin(a) * 0.5, 67.6))
        from .louvre import bar

        bar(b, gold_d, p0, p1, 0.18)
    b.cyl(gold, 0.35, 0.2, 1.4, (sx, sy, 67.4), seg=8)
    star_shape(b, ruby, gold, sx, sy, 70.0, 1.9, ang=ANG_U)

    # ---------------------------------------------------------------- 列寧墓
    mx, my, _ = W(167.0, 14.0)
    for k, (w, d, h) in enumerate(((26.0, 14.0, 3.6), (20.0, 11.0, 2.6), (15.0, 8.5, 2.4), (10.0, 6.5, 2.2), (6.0, 4.6, 1.6))):
        z = sum(x[2] for x in ((26.0, 14.0, 3.6), (20.0, 11.0, 2.6), (15.0, 8.5, 2.4), (10.0, 6.5, 2.2), (6.0, 4.6, 1.6))[:k])
        b.box_base(granite if k % 2 == 0 else granite_k, (w, d, h), (mx, my, z), rot=(0, 0, ANG_U))
    b.box_base(granite_k, (30.0, 2.0, 0.6), W(167.0, 6.0, 0), rot=(0, 0, ANG_U))

    # ---------------------------------------------------------------- 古姆百貨（廣場東北側一段）
    gu0, gu1 = 40.0, 175.0
    c = W((gu0 + gu1) / 2, 75.0 + 30.0)
    b.box_base(plaster, (gu1 - gu0, 60.0, 21.0), c, rot=(0, 0, ANG_U))
    b.box_base(green_d, (gu1 - gu0 + 1.0, 61.0, 0.6), (c[0], c[1], 21.0), rot=(0, 0, ANG_U))
    for k in range(int((gu1 - gu0) / 4.2)):
        u = gu0 + 2.1 + 4.2 * k
        for z in (3.0, 9.0, 14.5):
            q = W(u, 74.95)
            b.box_base(win, (1.6, 0.12, 3.6 if z < 5 else 2.8), (q[0], q[1], z), rot=(0, 0, ANG_U))
    for u in (60.0, 110.0, 160.0):
        q = W(u, 76.0)
        b.box_base(plaster, (12.0, 4.0, 27.0), (q[0], q[1], 0), rot=(0, 0, ANG_U))
        tent(b, green_d, 5.0, 27.0, 6.0, q[0], q[1], sides=4, rot=ANG_U + math.pi / 4)

    # ---------------------------------------------------------------- 聖瓦西里主教座堂
    st_basil(b, brick_sb, white, cream, green, green_d, gold, orange, win, curb,
             {"red": red, "pink": pink, "white": wpink, "green": dgreen, "lgreen": lgreen, "yellow": yellow, "blue": blue,
              "gold": gold, "gold_d": gold_d})

    # ---------------------------------------------------------------- 樹
    rng = b.rng
    for x, y in ((-62, -22), (-70, 8), (40, -40), (52, -10), (-52, -48), (64, 22)):
        broadleaf(b, x, y, rng.uniform(12, 16), leaves, trunk)

    b.export(path)


def star_shape(b, mi, rim, x, y, z, R, ang=0.0):
    """克里姆林紅星：五角星（雙面錐形厚度）"""
    pts = []
    for k in range(10):
        r = R if k % 2 == 0 else R * 0.42
        t = math.pi / 2 + TAU * k / 10
        pts.append((r * math.cos(t), r * math.sin(t)))
    M = Matrix.Translation((x, y, z)) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "X")
    c_f = b.bm.verts.new(M @ Vector((0, 0, 0.45)))
    c_b = b.bm.verts.new(M @ Vector((0, 0, -0.45)))
    ring = [b.bm.verts.new(M @ Vector((px, py, 0))) for px, py in pts]
    for i in range(10):
        j = (i + 1) % 10
        for c, order in ((c_f, (ring[i], ring[j])), (c_b, (ring[j], ring[i]))):
            f = b.bm.faces.new([order[0], order[1], c])
            f.material_index = mi
            f.smooth = False


def st_basil(b, brick, white, cream, green, green_d, gold, orange, win, curb, dm):
    T = lambda x, y, z=0.0: Matrix.Translation((x, y, z))  # noqa: E731
    # 台基與擋土牆（瓦西里斜坡一側較高）
    b.box_base(curb, (66.0, 60.0, 2.6), (0, -2.0, 0))
    b.box_base(white, (66.6, 60.6, 0.4), (0, -2.0, 2.6))
    # 台基層（podklet）：紅磚＋白色拱廊
    Z0 = 3.0
    PH = 6.0
    base = [(-24, -16), (-16, -24), (16, -24), (24, -16), (24, 16), (16, 24), (-16, 24), (-24, 16)]
    b.prism(brick, base, Z0, PH)
    b.prism(white, [(x * 1.02, y * 1.02) for x, y in base], Z0 + PH, 0.5)
    for (xa, ya), (xb, yb) in zip(base, base[1:] + base[:1]):
        L = math.hypot(xb - xa, yb - ya)
        ang = math.atan2(yb - ya, xb - xa)
        n = max(1, int(L / 4.0))
        for k in range(n):
            t = (k + 0.5) / n
            px, py = xa + (xb - xa) * t, ya + (yb - ya) * t
            nx, ny = math.sin(ang), -math.cos(ang)
            M = T(px + nx * 0.03, py + ny * 0.03, Z0 + 0.6) @ Matrix.Rotation(ang, 4, "Z")
            b.profile_wall(white, [(-1.5, 0), (1.5, 0), (1.5, 3.4), (0, 4.6), (-1.5, 3.4)], 0.2, M)
            b.profile_wall(win, [(-1.1, 0), (1.1, 0), (1.1, 3.1), (0, 4.1), (-1.1, 3.1)], 0.1, M @ T(0, -0.12, 0.1))
    # 迴廊屋頂（綠色金屬）
    Z1 = Z0 + PH + 0.5

    def chapel(cx, cy, R, h, drum_r, drum_h, dome_R, dome_H, mats, pattern, koko=True, sides=8):
        oct_shaft(b, brick, R, Z1, Z1 + h, cx, cy)
        oct_shaft(b, white, R + 0.25, Z1 + h * 0.45, Z1 + h * 0.45 + 0.4, cx, cy)
        oct_shaft(b, white, R + 0.3, Z1 + h - 0.5, Z1 + h, cx, cy)
        for k in range(8):   # 窗
            a = TAU * k / 8
            M = T(cx + math.cos(a) * (R * math.cos(math.pi / 8) + 0.03), cy + math.sin(a) * (R * math.cos(math.pi / 8) + 0.03),
                  Z1 + h * 0.58) @ Matrix.Rotation(a + math.pi / 2, 4, "Z")
            b.profile_wall(white, [(-0.75, 0), (0.75, 0), (0.75, 2.2), (0, 2.9), (-0.75, 2.2)], 0.2, M)
            b.profile_wall(win, [(-0.45, 0.15), (0.45, 0.15), (0.45, 2.0), (0, 2.5), (-0.45, 2.0)], 0.1, M @ T(0, -0.12, 0))
        z = Z1 + h
        if koko:
            kokoshniks(b, white, cx, cy, z, R * math.cos(math.pi / 8) - 0.2, 8, R * 0.72, R * 0.45, depth=0.4, kind="keel")
            kokoshniks(b, brick, cx, cy, z + R * 0.3, R * math.cos(math.pi / 8) - 0.9, 8, R * 0.62, R * 0.4, depth=0.35,
                       rot=math.pi / 8, kind="keel")
        b.lathe(green_d, [(R * 0.95, z), (drum_r + 0.3, z + R * 0.55)], (cx, cy, 0), seg=8, smooth=False, rot_offset=math.pi / 8)
        zd = z + R * 0.5
        b.lathe(brick, [(drum_r, zd), (drum_r, zd + drum_h)], (cx, cy, 0), seg=16, smooth=False)
        b.lathe(white, [(drum_r + 0.15, zd + drum_h * 0.35), (drum_r + 0.15, zd + drum_h * 0.42)], (cx, cy, 0), seg=16, smooth=False)
        for k in range(8):
            a = TAU * (k + 0.5) / 8
            b.box_base(white, (0.28, 0.28, drum_h), (cx + math.cos(a) * (drum_r + 0.05), cy + math.sin(a) * (drum_r + 0.05), zd))
            M = T(cx + math.cos(a + TAU / 16) * (drum_r + 0.02), cy + math.sin(a + TAU / 16) * (drum_r + 0.02), zd + drum_h * 0.48) @ \
                Matrix.Rotation(a + TAU / 16 + math.pi / 2, 4, "Z")
            b.profile_wall(win, [(-0.3, 0), (0.3, 0), (0.3, 1.2), (0, 1.5), (-0.3, 1.2)], 0.1, M)
        b.lathe(white, [(drum_r + 0.25, zd + drum_h), (drum_r + 0.4, zd + drum_h + 0.3), (drum_r * 0.8, zd + drum_h + 0.3)], (cx, cy, 0),
                seg=16, smooth=False)
        zt = onion(b, cx, cy, zd + drum_h + 0.2, dome_R, dome_H, mats, pattern, seg=32, n=18, neck=drum_r * 0.8 / dome_R)
        b.lathe(gold, [(0.25, zt - 0.2), (0.35, zt + 0.3), (0.12, zt + 0.6)], (cx, cy, 0), seg=8)
        cross(b, gold, cx, cy, zt + 0.5, h=3.0)

    spiral = lambda tw, w: (lambda i, j: (i + int(j * tw)) // w)  # noqa: E731
    zigzag = lambda i, j: (j + abs((i % 4) - 2)) // 2  # noqa: E731
    diamond = lambda i, j: ((i + j) // 2 + (i - j) // 2)  # noqa: E731
    scales = lambda i, j: (j + (i % 2)) // 1  # noqa: E731

    # 四大禮拜堂：南（正面，粉白鋸齒）、西（紅綠菱格）、東（綠黃螺旋）、北（紅白綠）
    for (dx, dy), mats, pat in (((0, -15.5), [dm["pink"], dm["white"]], zigzag),
                                ((-15.5, 0), [dm["red"], dm["green"]], diamond),
                                ((15.5, 0), [dm["green"], dm["yellow"], dm["green"], dm["lgreen"]], spiral(0.9, 2)),
                                ((0, 15.5), [dm["red"], dm["white"], dm["green"]], spiral(1.2, 2))):
        chapel(dx, dy, 5.0, 15.0, 3.3, 6.5, 5.0, 9.2, mats, pat)
    # 四小禮拜堂（斜角）
    for (dx, dy), mats, pat in (((-11.5, -11.5), [dm["gold"], dm["gold_d"]], scales),
                                ((11.5, -11.5), [dm["green"], dm["white"]], spiral(0.8, 2)),
                                ((11.5, 11.5), [dm["blue"], dm["white"]], spiral(-0.8, 2)),
                                ((-11.5, 11.5), [dm["yellow"], dm["green"], dm["red"]], spiral(1.0, 2))):
        chapel(dx, dy, 3.4, 10.0, 2.4, 4.4, 3.6, 6.8, mats, pat)
    # 中央帳篷頂教堂（代禱教堂）
    oct_shaft(b, brick, 7.6, Z1, Z1 + 25.0, 0, 0)
    oct_shaft(b, white, 7.9, Z1 + 12.0, Z1 + 12.5, 0, 0)
    for z, n, rr, w, h, rot in ((Z1 + 25.0, 8, 6.7, 5.0, 2.6, 0.0), (Z1 + 27.0, 8, 6.0, 4.2, 2.3, math.pi / 8),
                                (Z1 + 28.8, 8, 5.4, 3.6, 2.0, 0.0)):
        kokoshniks(b, white if rot == 0 else brick, 0, 0, z, rr, n, w, h, depth=0.5, rot=rot, kind="keel")
    oct_shaft(b, brick, 6.2, Z1 + 25.0, Z1 + 31.0, 0, 0)
    oct_shaft(b, white, 6.5, Z1 + 31.0, Z1 + 31.6, 0, 0)
    ZT = Z1 + 31.6
    TH = 15.0
    tent(b, orange, 5.9, ZT, TH, 0, 0, sides=8, r_top=1.4)
    for k in range(8):           # 帳篷白色稜線與菱形網紋
        a = math.pi / 8 + TAU * k / 8
        from .louvre import bar

        p0 = Vector((math.cos(a) * 5.95, math.sin(a) * 5.95, ZT))
        p1 = Vector((math.cos(a) * 1.45, math.sin(a) * 1.45, ZT + TH))
        bar(b, white, p0, p1, 0.35)
        for t in (0.25, 0.5, 0.75):
            q0 = p0.lerp(p1, t)
            a2 = math.pi / 8 + TAU * (k + 1) / 8
            q1 = Vector((math.cos(a2) * 5.95, math.sin(a2) * 5.95, ZT)).lerp(Vector((math.cos(a2) * 1.45, math.sin(a2) * 1.45, ZT + TH)), t)
            bar(b, cream, q0 * 1.0 + Vector((0, 0, 0)), q1, 0.18)
    zl = ZT + TH
    oct_shaft(b, white, 1.8, zl, zl + 2.2, 0, 0)
    onion(b, 0, 0, zl + 2.2, 1.9, 3.2, [dm["gold"], dm["gold_d"]], lambda i, j: j // 3, seg=24, n=10, neck=0.7)
    cross(b, gold, 0, 0, zl + 5.3, h=2.8)
    # 鐘樓（東南角）
    bx, by = 24.0, -5.0
    b.box_base(brick, (6.5, 6.5, Z1 + 6.0 - Z0), (bx, by, Z0))
    b.box_base(white, (7.0, 7.0, 0.5), (bx, by, Z1 + 6.0))
    oct_shaft(b, brick, 4.4, Z1 + 6.5, Z1 + 8.5, bx, by)
    for k in range(8):           # 開敞鐘樓的柱
        a = math.pi / 8 + TAU * k / 8
        b.box_base(white, (0.6, 0.6, 6.0), (bx + math.cos(a) * 3.9, by + math.sin(a) * 3.9, Z1 + 8.5))
    oct_shaft(b, win, 3.5, Z1 + 8.5, Z1 + 14.5, bx, by)
    oct_shaft(b, white, 4.6, Z1 + 14.5, Z1 + 15.3, bx, by)
    kokoshniks(b, white, bx, by, Z1 + 15.3, 3.9, 8, 2.6, 1.3, depth=0.3, kind="round")
    tent(b, green, 4.1, Z1 + 15.3, 9.0, bx, by, sides=8, r_top=0.6)
    for z in (Z1 + 18.0, Z1 + 21.0):   # 帳篷上的小老虎窗
        rr = 4.1 - (z - Z1 - 15.3) / 9.0 * 3.5
        for k in range(4):
            a = TAU * k / 4
            M = T(bx + math.cos(a) * rr, by + math.sin(a) * rr, z) @ Matrix.Rotation(a + math.pi / 2, 4, "Z")
            b.profile_wall(white, [(-0.4, 0), (0.4, 0), (0.4, 0.8), (0, 1.2), (-0.4, 0.8)], 0.5, M)
    zt = Z1 + 24.3
    onion(b, bx, by, zt, 0.9, 1.6, [dm["gold"]], lambda i, j: 0, seg=16, n=8, neck=0.6)
    cross(b, gold, bx, by, zt + 1.6, h=1.8)
    # 西、北側門廊小帳篷
    for px, py in ((-23.0, -8.0), (-8.0, 23.0)):
        b.box_base(brick, (4.5, 4.5, 4.0), (px, py, Z1))
        tent(b, green, 3.0, Z1 + 4.0, 4.5, px, py, sides=4, rot=math.pi / 4)
        onion(b, px, py, Z1 + 8.4, 0.6, 1.1, [dm["gold"]], lambda i, j: 0, seg=12, n=6)
    # 迴廊（低矮、綠頂）連接各禮拜堂
    for (xa, ya), (xb, yb) in zip(base, base[1:] + base[:1]):
        mx, my = (xa + xb) / 2 * 0.86, (ya + yb) / 2 * 0.86
        L = math.hypot(xb - xa, yb - ya) * 0.86
        ang = math.atan2(yb - ya, xb - xa)
        b.box_base(brick, (L, 3.0, 3.2), (mx, my, Z1), rot=(0, 0, ang))
        b.box_base(green_d, (L + 0.4, 3.6, 0.4), (mx, my, Z1 + 3.2), rot=(0, 0, ang))
