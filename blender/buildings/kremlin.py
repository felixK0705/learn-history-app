"""kremlin 莫斯科紅場：聖瓦西里主教座堂、救世主塔（斯帕斯卡亞塔）與克里姆林宮東牆寫實模型（公尺）

- 聖瓦西里主教座堂（1555–61）：九座教堂緊密聚成一簇——中央帳篷頂的代禱教堂（頂高約 61 m），
  四方四座大禮拜堂（八角塔身＋層疊山牆＋細高鼓座＋彩繪洋蔥頂，頂高約 39–41 m）、斜角四座小禮拜堂（約 30 m）；
  全部立在約 6 m 高的紅磚台基（白色拱形開口）上，外圈為綠色金屬屋頂的迴廊（頂約 10.5 m），
  西南、西北兩處帶綠色帳篷頂的階梯門廊；東南角鐘樓（綠帳篷頂）
- 洋蔥頂花紋照實景：南＝粉紅白鋸齒、西＝紅綠菱格、東＝綠黃螺旋、北＝藍白螺旋，小圓頂為金、綠、藍、黃綠
- 救世主塔：方形紅磚塔身（約 13 m 見方）→ 白石哥德式層 → 鐘面層（鐘徑約 6 m）→ 八角鐘樓 → 綠色細高帳篷尖頂與紅星，總高 71 m
- 克里姆林宮東牆：紅磚、燕尾形雉堞，隨地勢階梯下降；沿牆有沙皇塔、警鐘塔、康斯坦丁－葉連娜塔、元老院塔、
  東南角圓形的別克列米舍夫塔；牆前草坪帶；列寧墓；廣場東側古姆百貨一段
- 地面：紅場灰色石塊鋪面；大教堂南側為擋土石牆，牆下瓦西里斜坡的柏油路往莫斯科河方向下降；教堂周邊草坪、矮圍牆與樹

座標：+X 東、+Y 北，聖瓦西里中心在原點。參考照由南方（瓦西里斜坡）向北拍攝，左側為救世主塔。
"""

import math
import os

from mathutils import Matrix, Vector

from lib import TAU

from .blue_mosque import CardBuilder, card_tree, gen_leaf_png, mk_face

# 目標點、方位角（0 = 從南往北看）、仰角、距離、焦距
CAMERA = ((-23.2, -13.2, 29.9), 39.8, -6.1, 280.0, 77)

GEN_DIR = "_gen/kremlin_v2"
S0 = Vector((-113.0, 0.0, 0.0))                  # 救世主塔（與聖瓦西里同緯度，正西約 113 m）
# 兩段牆：往西北（元老院塔方向）與往南南東（往別克列米舍夫塔）；V 皆指向牆外（廣場一側）
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


# ====================================================================== 地形
Y_EDGE = -27.0           # 大教堂台地南緣（擋土牆線）
STEP_X0, STEP_X1 = -52.0, 48.0


def step_amp(x):
    """擋土牆處的落差（公尺）：教堂南側約 3.4 m，往兩端漸收"""
    if STEP_X0 <= x <= STEP_X1:
        return 3.4
    d = (STEP_X0 - x) if x < STEP_X0 else (x - STEP_X1)
    return max(0.0, 3.4 * (1 - d / 22.0))


def ground_h(x, y):
    """地面高度：紅場與教堂台地為 0；往南（莫斯科河方向）為瓦西里斜坡"""
    if y >= Y_EDGE:
        return 0.0
    s = Y_EDGE - y
    a = step_amp(x)
    k = min(1.0, s / 0.6)
    return -(a * k) - 0.012 * s


# ====================================================================== 自產貼圖
def _gen_textures():
    """帳篷頂（橘紅底、白色菱格線、綠黃小菱形）貼圖"""
    import numpy as np
    from PIL import Image, ImageDraw

    from lib import TEX

    d = os.path.join(TEX, GEN_DIR, "tent")
    if os.path.exists(os.path.join(d, "diff.jpg")):
        return
    os.makedirs(d, exist_ok=True)
    N = 512
    im = Image.new("RGB", (N, N), (196, 92, 62))
    dr = ImageDraw.Draw(im)
    rng = np.random.default_rng(5)
    for _ in range(4000):   # 磚面雜色
        x, y = rng.integers(0, N, 2)
        c = int(rng.integers(-18, 18))
        dr.rectangle([x, y, x + 6, y + 3], fill=(196 + c, 92 + c // 2, 62 + c // 3))
    n = 4
    s = N // n
    for i in range(n + 1):
        for j in range(n + 1):
            cx, cy = i * s, j * s
            # 菱形內的綠、黃小菱形
            col = (64, 132, 82) if (i + j) % 2 == 0 else (222, 186, 82)
            q = s * 0.18
            dr.polygon([(cx + s / 2, cy + s / 2 - q), (cx + s / 2 + q, cy + s / 2), (cx + s / 2, cy + s / 2 + q), (cx + s / 2 - q, cy + s / 2)], fill=col)
    for k in range(-n, 2 * n + 1):   # 白色斜格線
        dr.line([(k * s, 0), (k * s + N, N)], fill=(236, 228, 214), width=9)
        dr.line([(k * s, N), (k * s + N, 0)], fill=(236, 228, 214), width=9)
    im.save(os.path.join(d, "diff.jpg"), quality=88)


# ====================================================================== 共用造型
def bar(b, mi, p0, p1, w, h=None):
    """兩點之間的方形斷面細桿"""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    if L < 1e-6:
        return
    q = d.to_track_quat("Z", "Y")
    M = Matrix.Translation(p0) @ q.to_matrix().to_4x4() @ Matrix.Translation((0, 0, L / 2))
    vs = b.box(mi, (w, h or w, L), (0, 0, 0))
    import bmesh

    bmesh.ops.transform(b.bm, matrix=M, verts=vs)


def onion(b, cx, cy, z0, R, H, mats, pattern, seg=32, n=18, neck=0.72):
    """洋蔥頂：自訂經緯格，每格依 pattern(i, j) 選材質（螺旋、鋸齒、菱格、魚鱗）"""
    import bisect

    prof = [(neck, 0.0), (0.88, 0.05), (0.99, 0.15), (1.0, 0.24), (0.95, 0.35), (0.82, 0.47), (0.62, 0.59), (0.4, 0.7), (0.22, 0.8),
            (0.11, 0.89), (0.05, 0.95), (0.02, 0.99)]
    L = [0.0]
    for (r0, z0_), (r1, z1_) in zip(prof, prof[1:]):
        L.append(L[-1] + math.hypot((r1 - r0) * R, (z1_ - z0_) * H))
    pts = []
    for k in range(n + 1):
        s = L[-1] * k / n
        i = min(len(prof) - 2, max(0, bisect.bisect_right(L, s) - 1))
        t = (s - L[i]) / max(1e-9, L[i + 1] - L[i])
        pts.append(((prof[i][0] + (prof[i + 1][0] - prof[i][0]) * t) * R, (prof[i][1] + (prof[i + 1][1] - prof[i][1]) * t) * H))
    rings = [[b.bm.verts.new((cx + r * math.cos(TAU * i / seg), cy + r * math.sin(TAU * i / seg), z0 + z)) for i in range(seg)] for r, z in pts]
    apex = b.bm.verts.new((cx, cy, z0 + H))
    for j in range(n):
        for i in range(seg):
            mk_face(b, [rings[j][i], rings[j][(i + 1) % seg], rings[j + 1][(i + 1) % seg], rings[j + 1][i]], mats[pattern(i, j) % len(mats)], True)
    for i in range(seg):
        mk_face(b, [rings[n][i], rings[n][(i + 1) % seg], apex], mats[pattern(i, n) % len(mats)], True)
    mk_face(b, list(reversed(rings[0])), mats[0])
    return z0 + H


def cross(b, mi, x, y, z, h=2.6):
    b.box_base(mi, (0.14, 0.14, h), (x, y, z))
    b.box_base(mi, (1.0, 0.11, 0.11), (x, y, z + h * 0.72))
    b.box_base(mi, (0.6, 0.1, 0.1), (x, y, z + h * 0.48))


def oct_prism(b, mi, R, z0, z1, cx, cy, rot=math.pi / 8):
    pts = [(cx + R * math.cos(rot + TAU * k / 8), cy + R * math.sin(rot + TAU * k / 8)) for k in range(8)]
    b.prism(mi, pts, z0, z1 - z0)


def keel_pts(w, h, kind="keel", m=10):
    """山牆（kokoshnik）輪廓：圓拱或龍骨拱（頂端尖起）"""
    pts = [(-w / 2, 0), (w / 2, 0)]
    h0 = h * (0.62 if kind == "keel" else 1.0)
    for i in range(1, m):
        t = math.pi * i / m
        y = h0 * math.sin(t) + (h - h0) * math.sin(t) ** 10
        pts.append((w / 2 * math.cos(t), y))
    return pts


def kokoshnik_ring(b, outer, inner, cx, cy, z, R, n, w, h, rot=0.0, kind="keel", depth=0.45):
    """一圈山牆裝飾：外框（白）＋內嵌色面（綠／黃／磚）"""
    for k in range(n):
        a = rot + TAU * k / n
        M = Matrix.Translation((cx + math.cos(a) * R, cy + math.sin(a) * R, z)) @ Matrix.Rotation(a + math.pi / 2, 4, "Z")
        b.profile_wall(outer, keel_pts(w, h, kind), depth, M)
        if inner is not None:
            mi = inner[k % len(inner)]
            Mi = M @ Matrix.Translation((0, -0.1, h * 0.1))
            b.profile_wall(mi, keel_pts(w * 0.74, h * 0.74, kind), depth, Mi)


def tent(b, mi, R, z0, h, cx, cy, sides=8, r_top=0.4, rot=math.pi / 8):
    b.lathe(mi, [(R, z0), (r_top, z0 + h), (0.0, z0 + h)], (cx, cy, 0), seg=sides, smooth=False, rot_offset=rot)


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


def star_shape(b, mi, x, y, z, R, ang=0.0):
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
        mk_face(b, [ring[i], ring[j], c_f], mi)
        mk_face(b, [ring[j], ring[i], c_b], mi)


def loft(b, mi, ring0, ring1, cap=True):
    """兩圈等點數的 3D 折線之間鋪面（ring1 在上，可加頂蓋）"""
    v0 = [b.bm.verts.new(p) for p in ring0]
    v1 = [b.bm.verts.new(p) for p in ring1]
    n = len(v0)
    for i in range(n):
        j = (i + 1) % n
        mk_face(b, [v0[i], v0[j], v1[j], v1[i]], mi)
    if cap:
        mk_face(b, v1, mi)


# ====================================================================== 主體
def kremlin(path):
    _gen_textures()
    b = CardBuilder("Kremlin", seed=29)
    brick = b.ptex("brick", "brick_wall_006", tile=2.6, tint="#a8402f", rough=0.85, normal=0.7)
    brick_sb = b.ptex("brick_sb", "brick_wall_006", tile=1.8, tint="#c4553f", rough=0.85, normal=0.5)
    white = b.color("white_stone", "#ece4d6", rough=0.7)
    cream = b.color("cream", "#e6d7b4", rough=0.75)
    green = b.color("green_roof", "#3d7a55", rough=0.5, metal=0.2)
    green_d = b.color("green_dark", "#2f6446", rough=0.5, metal=0.2)
    gold = b.color("gold", "#d9ab45", rough=0.25, metal=1.0)
    gold_d = b.color("gold_d", "#a87d2a", rough=0.3, metal=1.0)
    win = b.color("window", "#2b2829", rough=0.35)
    clock = b.color("clock_face", "#1b1f2a", rough=0.4)
    ruby = b.color("ruby", "#c4182a", rough=0.15, metal=0.2)
    granite = b.color("granite_red", "#5a2c28", rough=0.4)
    granite_k = b.color("granite_black", "#2a2627", rough=0.35)
    cobble = b.ptex("cobble", "square_cobblestone", tile=3.2, tint="#7f7c78", rough=0.85, normal=0.6, dsize=512)
    asphalt = b.ptex("asphalt", "asphalt_02", tile=6.0, tint="#5f5e5c", rough=0.9, dsize=512)
    curb = b.ptex("curb", "large_sandstone_blocks", tile=3.0, tint="#a29d92", rough=0.85, normal=0.6, dsize=512)
    grass = b.ptex("grass", "grass_ground", tile=5.0, tint="#5f8a3a", gain=0.95, rough=0.95, dsize=512)
    plaster = b.ptex("plaster", "plastered_wall_04", tile=6.0, tint="#e2d3ad", rough=0.85, dsize=512)
    tent_mi = b.ptex("tent", f"{GEN_DIR}/tent", tile=4.0, rough=0.6)
    lf_light = b.alpha_mat("leaf_light", gen_leaf_png("light"))
    lf_broad = b.alpha_mat("leaf_broad", gen_leaf_png("broad"))
    core = b.color("leaf_core", "#2e4420", rough=0.9)
    trunk = b.color("trunk", "#5a4a3a", rough=0.9)
    dm = {
        "red": b.color("dome_red", "#b82e2a", rough=0.4),
        "pink": b.color("dome_pink", "#d9667a", rough=0.4),
        "white": b.color("dome_white", "#f2ebe4", rough=0.4),
        "green": b.color("dome_green", "#2f7a4c", rough=0.4),
        "lgreen": b.color("dome_lgreen", "#88b864", rough=0.4),
        "yellow": b.color("dome_yellow", "#e4c25a", rough=0.4),
        "blue": b.color("dome_blue", "#2f5fa6", rough=0.4),
        "gold": gold, "gold_d": gold_d,
    }

    T = lambda x, y, z=0.0: Matrix.Translation((x, y, z))  # noqa: E731
    Rz = lambda a: Matrix.Rotation(a, 4, "Z")  # noqa: E731

    # ---------------------------------------------------------------- 地面（紅場台地＋瓦西里斜坡，網格貼合地形）
    RAD = 250.0
    xs = sorted(set([-RAD + 10 * i for i in range(51)] + [STEP_X0, STEP_X1, STEP_X0 - 22, STEP_X1 + 22]))
    ys = sorted(set([-RAD + 10 * i for i in range(51)] + [Y_EDGE, Y_EDGE - 0.6, Y_EDGE - 12, Y_EDGE - 24]))
    grid = []
    for y in ys:
        row = []
        for x in xs:
            r = math.hypot(x, y)
            px, py = (x, y) if r <= RAD else (x * RAD / r, y * RAD / r)
            row.append(b.bm.verts.new((px, py, ground_h(px, py))))
        grid.append(row)
    # 前景道路（依參考照：相機前方約 55–95 m 的一條柏油路），其餘斜坡為石塊鋪面
    (tx_, ty_, tz_), az_, el_, dist_, _ = CAMERA
    a_, e_ = math.radians(az_), math.radians(el_)
    CAM = Vector((tx_ + math.sin(a_) * math.cos(e_) * dist_, ty_ - math.cos(a_) * math.cos(e_) * dist_, tz_ + math.sin(e_) * dist_))
    FWD = Vector((-math.sin(a_), math.cos(a_), 0))
    RGT = Vector((FWD.y, -FWD.x, 0))

    def fdist(x, y):
        return (Vector((x, y, 0)) - Vector((CAM.x, CAM.y, 0))).dot(FWD)

    road = lambda x, y: y < Y_EDGE - 1 and 52 < fdist(x, y) < 96  # noqa: E731
    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            area = ((q[2].co - q[0].co).cross(q[3].co - q[1].co)).length / 2
            if area < 0.05:
                continue
            cxm, cym = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            try:
                mk_face(b, q, asphalt if road(cxm, cym) else cobble)
            except ValueError:
                pass
    # 道路標線與路邊護柱
    line = b.color("road_line", "#e8e6df", rough=0.6)
    bollard = b.color("bollard", "#cfc8b8", rough=0.8)
    for k in range(-14, 15):
        for dd, dash in ((74.0, True), (55.0, False), (93.0, False)):
            if dash and k % 2:
                continue
            p = Vector((CAM.x, CAM.y, 0)) + FWD * dd + RGT * (k * 6.0)
            if math.hypot(p.x, p.y) > 245:
                continue
            b.box_base(line, (5.9 if not dash else 3.0, 0.18, 0.04), (p.x, p.y, ground_h(p.x, p.y) + 0.005), rot=(0, 0, math.atan2(RGT.y, RGT.x)))
    for k in range(-40, 41):
        p = Vector((CAM.x, CAM.y, 0)) + FWD * 97.5 + RGT * (k * 2.8)
        if math.hypot(p.x, p.y) > 245 or p.y > Y_EDGE - 2:
            continue
        b.box_base(bollard, (0.45, 0.45, 0.55), (p.x, p.y, ground_h(p.x, p.y) - 0.05))

    # ---------------------------------------------------------------- 擋土石牆（教堂南側）＋護欄
    xa = STEP_X0 - 22
    seg_n = 34
    for k in range(seg_n):
        x0 = xa + (STEP_X1 + 22 - xa) * k / seg_n
        x1 = xa + (STEP_X1 + 22 - xa) * (k + 1) / seg_n
        xm = (x0 + x1) / 2
        a = step_amp(xm)
        zb = ground_h(xm, Y_EDGE - 2.0) - 0.5
        if a <= 0.05:
            continue
        b.box_base(curb, (x1 - x0 + 0.02, 1.4, 1.1 - zb), (xm, Y_EDGE - 0.3, zb))
        b.box_base(white, (x1 - x0 + 0.02, 1.6, 0.18), (xm, Y_EDGE - 0.3, 1.1))
    # ---------------------------------------------------------------- 教堂周邊：草坪、矮石牆、鐵欄
    def lawn(x0, y0, x1, y1, wall=True):
        b.box_base(grass, (x1 - x0, y1 - y0, 0.12), ((x0 + x1) / 2, (y0 + y1) / 2, 0.0))
        if wall:
            for (cx, cy, w, d) in (((x0 + x1) / 2, y0, x1 - x0 + 0.5, 0.5), ((x0 + x1) / 2, y1, x1 - x0 + 0.5, 0.5),
                                   (x0, (y0 + y1) / 2, 0.5, y1 - y0 + 0.5), (x1, (y0 + y1) / 2, 0.5, y1 - y0 + 0.5)):
                b.box_base(curb, (w, d, 0.55), (cx, cy, 0.0))

    lawn(-50, -25.5, -27, -10)
    lawn(27, -25.5, 46, -6)
    lawn(28, 4, 46, 26)
    lawn(-48, 4, -30, 24)
    # 教堂外圈低矮鐵欄
    fence = b.color("fence", "#2a2a2a", rough=0.5, metal=0.6)
    for (x0, y0, x1, y1) in ((-26, -25, 26, -25), (26, -25, 26, 26), (-26, 26, 26, 26), (-26, -25, -26, 26)):
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.atan2(y1 - y0, x1 - x0)
        b.box_base(fence, (L, 0.08, 0.08), ((x0 + x1) / 2, (y0 + y1) / 2, 1.1), rot=(0, 0, ang))
        for k in range(int(L / 3) + 1):
            t = k / max(1, int(L / 3))
            b.box_base(fence, (0.12, 0.12, 1.2), (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, 0.0))

    # 牆前草坪帶（克里姆林牆下）
    for fr, u0, u1 in (("sse", -150, -8), ("nw", 8, 150)):
        use(fr)
        for k in range(10):
            ua = u0 + (u1 - u0) * k / 10
            ub = u0 + (u1 - u0) * (k + 1) / 10
            c = W((ua + ub) / 2, 7.0)
            zb = ground_h(c[0], c[1])
            b.box_base(grass, (ub - ua + 0.05, 9.0, 0.3), (c[0], c[1], zb - 0.15), rot=(0, 0, ANG_U))

    # ---------------------------------------------------------------- 克里姆林牆（隨地勢分段）
    WALL_H, WALL_T = 12.5, 4.5

    def wall_seg(ua, ub, step=18.0):
        n = max(1, int(round((ub - ua) / step)))
        for k in range(n):
            u0 = ua + (ub - ua) * k / n
            u1 = ua + (ub - ua) * (k + 1) / n
            c = W((u0 + u1) / 2, -WALL_T / 2)
            zg = ground_h(*W((u0 + u1) / 2, 2.0)[:2])
            zb = zg - 6.0
            b.box_base(brick, (u1 - u0 + 0.02, WALL_T, WALL_H + zg - zb), (c[0], c[1], zb), rot=(0, 0, ANG_U))
            merlons(b, brick, W(u0, 0.0), W(u1, 0.0), zg + WALL_H)
            merlons(b, brick, W(u1, -WALL_T), W(u0, -WALL_T), zg + WALL_H, spacing=4.5, h=1.6)
            b.box_base(white, (u1 - u0 + 0.02, 0.35, 0.3), (c[0] + V.x * 2.35, c[1] + V.y * 2.35, zg + 1.6), rot=(0, 0, ANG_U))

    use("sse")
    for ua, ub in ((-282, -183), (-169, -75), (-65, -7)):
        wall_seg(ua, ub)
    use("nw")
    for ua, ub in ((7, 162), (172, 235)):
        wall_seg(ua, ub)

    def tower(u, w, h_body, tiers, roof_h, roof_mi=green, round_=False):
        cx, cy, _ = W(u, -WALL_T / 2 + 0.5)
        zg = ground_h(*W(u, 3.0)[:2])
        if round_:
            b.lathe(brick, [(w / 2, zg - 6), (w / 2 * 0.92, zg + h_body)], (cx, cy, 0), seg=24, smooth=False)
            b.lathe(white, [(w / 2 * 0.95, zg + h_body - 0.6), (w / 2 + 0.6, zg + h_body), (w / 2 * 0.9, zg + h_body)], (cx, cy, 0), seg=24,
                    smooth=False)
            z = zg + h_body
            r = w / 2 * 0.62
            b.lathe(brick, [(r, z), (r, z + 6.0)], (cx, cy, 0), seg=8, smooth=False)
            tent(b, roof_mi, r + 0.3, z + 6.0, roof_h, cx, cy, sides=8, r_top=0.3)
            b.ico(gold, 0.35, (cx, cy, z + 6.0 + roof_h + 0.3), subdiv=1)
            return
        b.box_base(brick, (w, w, h_body + 6), (cx, cy, zg - 6), rot=(0, 0, ANG_U))
        b.box_base(white, (w + 0.6, w + 0.6, 0.45), (cx, cy, zg + h_body - 2.6), rot=(0, 0, ANG_U))
        merlons(b, brick, W(u - w / 2 + 0.2, -WALL_T / 2 + 0.5 + w / 2), W(u + w / 2 - 0.2, -WALL_T / 2 + 0.5 + w / 2), zg + h_body, spacing=2.4,
                w=1.3, h=1.8)
        z = zg + h_body
        ww = w
        for th, shrink in tiers:
            ww = ww * shrink
            b.box_base(brick, (ww, ww, th), (cx, cy, z), rot=(0, 0, ANG_U))
            b.box_base(white, (ww + 0.5, ww + 0.5, 0.35), (cx, cy, z + th - 0.35), rot=(0, 0, ANG_U))
            for s in (-1, 1):
                for t in (-1, 1):
                    q = Vector((cx, cy, 0)) + U * (s * ww / 2) + V * (t * ww / 2)
                    b.cone(white, 0.3, 1.8, (q.x, q.y, z + th), seg=4)
            z += th
        tent(b, roof_mi, ww * 0.58, z, roof_h, cx, cy, sides=8, r_top=0.25)
        zt = z + roof_h
        b.ico(gold, 0.32, (cx, cy, zt + 0.25), subdiv=1)
        b.box_base(gold, (0.1, 0.1, 1.6), (cx, cy, zt + 0.45))

    use("nw")
    tower(167.0, 9.0, 17.0, [(6.0, 0.8)], 11.0)                 # 元老院塔
    use("sse")
    tower(-70.0, 8.0, 16.0, [(5.0, 0.82), (4.5, 0.8)], 10.0)    # 警鐘塔
    tower(-176.0, 11.0, 18.0, [(6.0, 0.8)], 12.0)               # 康斯坦丁－葉連娜塔
    tower(-289.0, 14.0, 27.0, [], 17.0, round_=True)            # 別克列米舍夫塔
    # 沙皇塔：牆上的小帳篷亭
    cx, cy, _ = W(-30.0, -1.5)
    zg = ground_h(*W(-30.0, 3.0)[:2]) + WALL_H
    b.box_base(brick, (4.0, 4.0, 2.5), (cx, cy, zg), rot=(0, 0, ANG_U))
    for s in (-1, 1):
        for t in (-1, 1):
            q = Vector((cx, cy, 0)) + U * (s * 1.7) + V * (t * 1.7)
            b.box_base(white, (0.4, 0.4, 3.2), (q.x, q.y, zg + 2.5))
    tent(b, green, 3.0, zg + 5.7, 5.0, cx, cy, sides=4, r_top=0.15, rot=ANG_U + math.pi / 4)
    b.ico(gold, 0.3, (cx, cy, zg + 10.9), subdiv=1)

    # ---------------------------------------------------------------- 救世主塔
    use("nw")
    spasskaya(b, brick, white, green, gold, gold_d, win, clock, ruby, T, Rz)

    # ---------------------------------------------------------------- 列寧墓
    mx, my, _ = W(167.0, 14.0)
    tiers = ((26.0, 14.0, 3.6), (20.0, 11.0, 2.6), (15.0, 8.5, 2.4), (10.0, 6.5, 2.2), (6.0, 4.6, 1.6))
    z = 0.0
    for k, (w, d, h) in enumerate(tiers):
        b.box_base(granite if k % 2 == 0 else granite_k, (w, d, h), (mx, my, z), rot=(0, 0, ANG_U))
        z += h

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
        tent(b, green_d, 5.0, 27.0, 6.0, q[0], q[1], sides=4, r_top=0.2, rot=ANG_U + math.pi / 4)

    # ---------------------------------------------------------------- 聖瓦西里主教座堂
    st_basil(b, brick_sb, white, cream, green, green_d, gold, tent_mi, win, curb, dm, T, Rz)

    # ---------------------------------------------------------------- 樹（教堂兩側與牆前）
    rng = b.rng
    mats = (lf_light, lf_broad)
    H_ = 18.0 / CAMERA[4]

    def at_screen(px, top_py, D):
        """參考照畫面位置（1280×853 像素）＋前方距離 D → 世界座標與樹高"""
        xt = (px / 1280 - 0.5) * 2 * H_
        yt = (0.5 - top_py / 853) * 2 * (853 / 1280) * H_
        p = Vector((CAM.x, CAM.y, 0)) + FWD * D + RGT * (xt * D)
        zg = ground_h(p.x, p.y)
        top = CAM.z + D * math.tan(math.radians(-el_) + math.atan(yt))
        return p.x, p.y, zg, top - zg

    for px, py, D in ((360, 430, 300), (470, 545, 318), (880, 385, 262), (1120, 470, 250), (1200, 520, 238), (720, 505, 262), (790, 520, 258),
                      (300, 560, 330)):
        x, y, zg, h = at_screen(px, py, D)
        card_tree(b, x, y, max(6.0, h), mats, core, trunk, z=zg)
    for x, y, h in ((-40, 12, 14), (-44, 22, 12), (40, 14, 14), (34, 24, 12), (-36, -18, 13)):
        card_tree(b, x, y, h, mats, core, trunk, z=ground_h(x, y))
    use("sse")
    for u in (-120, -100, -46, -20):
        x, y, _ = W(u, 11.0)
        card_tree(b, x, y, rng.uniform(9, 12), mats, core, trunk, z=ground_h(x, y))
    use("nw")
    for u in (30, 60, 120):
        x, y, _ = W(u, 11.0)
        card_tree(b, x, y, rng.uniform(9, 11), mats, core, trunk, z=ground_h(x, y))

    b.export(path)


def spasskaya(b, brick, white, green, gold, gold_d, win, clock, ruby, T, Rz):
    """救世主塔：塔身 13 m 見方、總高 71 m（各層高度依參考照比例）"""
    import bmesh

    sx, sy, _ = W(0.0, -1.5)
    rot = (0, 0, ANG_U)
    zg = 0.0
    SW_ = 12.4

    def corners(half, z, fn):
        for s in (-1, 1):
            for t in (-1, 1):
                q = Vector((sx, sy, 0)) + U * (s * half) + V * (t * half)
                fn(q.x, q.y, z)

    def face_M(f, off, z):
        a = ANG_U + f * math.pi / 2
        return T(sx, sy, z) @ Rz(a) @ T(0, -off, 0)

    # 塔身 0–28.5
    b.box_base(brick, (SW_, SW_, 28.5 + 6), (sx, sy, zg - 6), rot=rot)
    b.box_base(white, (SW_ + 0.5, SW_ + 0.5, 0.5), (sx, sy, 9.5), rot=rot)
    # 城門（朝廣場與朝內）
    for f in (1, 3):
        M = face_M(f, SW_ / 2 + 0.02, 0.0)
        b.profile_wall(white, [(-3.0, 0), (3.0, 0), (3.0, 6.6), (0, 9.6), (-3.0, 6.6)], 0.3, M)
        b.profile_wall(win, [(-2.3, 0), (2.3, 0), (2.3, 6.0), (0, 8.4), (-2.3, 6.0)], 0.4, M)
    # 塔身窗與白框
    for f in range(4):
        for u in (-3.2, 3.2):
            for z in (13.0, 20.0):
                M = face_M(f, SW_ / 2 + 0.02, z)
                b.profile_wall(white, [(-0.9, -0.3), (0.9, -0.3), (0.9, 2.4), (0, 3.4), (-0.9, 2.4)], 0.3, M @ T(u, 0, 0))
                b.profile_wall(win, [(-0.55, 0), (0.55, 0), (0.55, 2.2), (0, 3.0), (-0.55, 2.2)], 0.36, M @ T(u, 0, 0))
    b.box_base(white, (SW_ + 0.8, SW_ + 0.8, 0.6), (sx, sy, 27.4), rot=rot)
    b.box_base(white, (SW_ + 1.2, SW_ + 1.2, 0.8), (sx, sy, 28.3), rot=rot)
    # 第二層（白石哥德式拱廊＋四角白尖塔）28.5–35
    b.box_base(brick, (11.4, 11.4, 6.5), (sx, sy, 28.5), rot=rot)
    for f in range(4):
        M = face_M(f, 5.72, 29.2)
        for u in (-3.4, 0.0, 3.4):
            b.profile_wall(white, [(-1.3, 0), (1.3, 0), (1.3, 3.5), (0, 5.4), (-1.3, 3.5)], 0.3, M @ T(u, 0, 0))
            b.profile_wall(win, [(-0.75, 0.3), (0.75, 0.3), (0.75, 3.3), (0, 4.6), (-0.75, 3.3)], 0.36, M @ T(u, 0, 0))
    corners(SW_ / 2 + 0.1, 29.1, lambda x, y, z: (b.box_base(white, (1.0, 1.0, 3.4), (x, y, z)), b.cone(white, 0.75, 4.6, (x, y, z + 3.4), seg=8),
                                                  b.ico(gold, 0.26, (x, y, z + 8.1), subdiv=1)))
    b.box_base(white, (12.2, 12.2, 0.7), (sx, sy, 34.8), rot=rot)
    # 鐘面層 35.5–45
    b.box_base(brick, (10.4, 10.4, 9.5), (sx, sy, 35.5), rot=rot)
    for f in range(4):
        a = ANG_U + f * math.pi / 2
        for mi, r, th, off in ((white, 3.55, 0.25, 0.0), (gold, 3.2, 0.32, 0.05), (clock, 2.95, 0.38, 0.1)):
            vs = b.cyl(mi, r, r, th, (0, 0, 0), seg=28)
            M = T(sx, sy, 40.2) @ Rz(a) @ T(0, -5.22 - off, 0) @ Matrix.Rotation(math.pi / 2, 4, "X")
            bmesh.ops.transform(b.bm, matrix=M, verts=vs)
        for k in range(12):   # 金色時標
            t_ = TAU * k / 12
            p = T(sx, sy, 40.2) @ Rz(a) @ Vector((math.cos(t_) * 2.55, -5.72, math.sin(t_) * 2.55))
            b.box_base(gold, (0.3, 0.3, 0.3), (p.x, p.y, p.z - 0.15), rot=(0, 0, a))
        for ang, L in ((0.55, 1.6), (2.2, 2.3)):   # 時針、分針
            p0 = T(sx, sy, 40.2) @ Rz(a) @ Vector((0, -5.74, 0))
            p1 = T(sx, sy, 40.2) @ Rz(a) @ Vector((math.cos(ang) * L, -5.74, math.sin(ang) * L))
            bar(b, gold, p0, p1, 0.18)
    b.box_base(white, (11.0, 11.0, 0.8), (sx, sy, 44.8), rot=rot)
    corners(5.0, 45.6, lambda x, y, z: (b.cyl(white, 0.45, 0.4, 2.4, (x, y, z), seg=8), b.cone(white, 0.42, 3.4, (x, y, z + 2.4), seg=8),
                                        b.ico(gold, 0.22, (x, y, z + 6.0), subdiv=1)))
    # 八角鐘樓 45.6–52.6
    oct_prism(b, brick, 4.5, 45.6, 52.6, sx, sy, rot=ANG_U + math.pi / 8)
    for k in range(8):
        a = ANG_U + TAU * k / 8
        rr = 4.5 * math.cos(math.pi / 8)
        M = T(sx + math.cos(a) * rr, sy + math.sin(a) * rr, 46.6) @ Rz(a + math.pi / 2)
        b.profile_wall(white, [(-1.35, 0), (1.35, 0), (1.35, 3.4), (0, 4.8), (-1.35, 3.4)], 0.3, M)
        b.profile_wall(win, [(-0.95, 0.2), (0.95, 0.2), (0.95, 3.2), (0, 4.3), (-0.95, 3.2)], 0.36, M)
        q = Vector((sx + math.cos(a + math.pi / 8) * 4.5, sy + math.sin(a + math.pi / 8) * 4.5, 45.6))
        b.box_base(white, (0.45, 0.45, 7.0), (q.x, q.y, 45.6))
    oct_prism(b, white, 4.85, 52.6, 53.4, sx, sy, rot=ANG_U + math.pi / 8)
    kokoshnik_ring(b, white, None, sx, sy, 53.4, 4.0, 8, 2.4, 1.3, rot=ANG_U, kind="round", depth=0.3)
    # 綠色細高帳篷尖頂 53.4–66.6＋金色稜線、小老虎窗
    TH = 13.2
    tent(b, green, 3.9, 53.4, TH, sx, sy, sides=8, r_top=0.3, rot=ANG_U + math.pi / 8)
    for k in range(8):
        a = ANG_U + math.pi / 8 + TAU * k / 8
        bar(b, gold_d, (sx + math.cos(a) * 3.92, sy + math.sin(a) * 3.92, 53.4), (sx + math.cos(a) * 0.32, sy + math.sin(a) * 0.32, 53.4 + TH), 0.16)
    for z, n in ((56.0, 4), (59.4, 4)):
        rr = 3.9 * (1 - (z - 53.4) / TH) * math.cos(math.pi / 8) + 0.05
        for k in range(n):
            a = ANG_U + TAU * k / n
            M = T(sx + math.cos(a) * rr, sy + math.sin(a) * rr, z) @ Rz(a + math.pi / 2)
            b.profile_wall(white, [(-0.35, 0), (0.35, 0), (0.35, 0.8), (0, 1.25), (-0.35, 0.8)], 0.7, M)
    b.cyl(gold, 0.32, 0.18, 1.4, (sx, sy, 66.4), seg=8)
    b.ico(gold, 0.42, (sx, sy, 67.3), subdiv=1)
    star_shape(b, ruby, sx, sy, 69.5, 1.85, ang=ANG_U + math.pi / 4)


def st_basil(b, brick, white, cream, green, green_d, gold, tent_mi, win, curb, dm, T, Rz):
    Z0 = 0.0
    PH = 6.0             # 台基（podklet）高
    GH = 10.5            # 迴廊外牆頂
    a_c, a_d = 20.5, 19.5

    # 台基＋迴廊外輪廓：八邊形（四正向面寬、斜向面接小禮拜堂）
    s2 = math.sqrt(2)
    xk = a_d * s2 - a_c
    base = [(xk, -a_c), (a_c, -xk), (a_c, xk), (xk, a_c), (-xk, a_c), (-a_c, xk), (-a_c, -xk), (-xk, -a_c)]
    b.prism(brick, base, Z0 - 1.0, PH + 1.0)
    b.prism(white, [(x * 1.012, y * 1.012) for x, y in base], PH - 0.1, 0.45)
    b.prism(brick, [(x * 0.985, y * 0.985) for x, y in base], PH + 0.35, GH - PH - 0.35)
    b.prism(white, [(x * 1.006, y * 1.006) for x, y in base], GH - 0.45, 0.45)
    b.prism(white, [(x * 1.008, y * 1.008) for x, y in base], Z0, 0.5)
    for (xa, ya), (xb, yb) in zip(base, base[1:] + base[:1]):
        L = math.hypot(xb - xa, yb - ya)
        ang = math.atan2(yb - ya, xb - xa)
        nx, ny = math.sin(ang), -math.cos(ang)
        # 台基：白框拱形開口
        n = max(1, int(L / 4.6))
        for k in range(n):
            t = (k + 0.5) / n
            px, py = xa + (xb - xa) * t, ya + (yb - ya) * t
            M = T(px + nx * 0.02, py + ny * 0.02, Z0 + 0.6) @ Rz(ang)
            b.profile_wall(white, [(-1.5, 0), (1.5, 0), (1.5, 2.9), (0, 4.4), (-1.5, 2.9)], 0.3, M)
            b.profile_wall(win, [(-1.05, 0.1), (1.05, 0.1), (1.05, 2.7), (0, 3.8), (-1.05, 2.7)], 0.36, M)
        # 迴廊：成對小窗＋白色壁柱
        n = max(1, int(L / 3.2))
        for k in range(n):
            t = (k + 0.5) / n
            px, py = xa + (xb - xa) * t, ya + (yb - ya) * t
            M = T(px + nx * (-0.12), py + ny * (-0.12), PH + 1.2) @ Rz(ang)
            b.profile_wall(white, [(-0.85, 0), (0.85, 0), (0.85, 2.0), (0, 2.9), (-0.85, 2.0)], 0.3, M)
            b.profile_wall(win, [(-0.5, 0.15), (0.5, 0.15), (0.5, 1.9), (0, 2.5), (-0.5, 1.9)], 0.36, M)
        for k in range(n + 1):
            t = k / n
            px, py = xa + (xb - xa) * t, ya + (yb - ya) * t
            b.box_base(white, (0.35, 0.35, GH - PH - 0.8), (px - nx * 0.05, py - ny * 0.05, PH + 0.35), rot=(0, 0, ang))
    # 迴廊綠色斜屋頂（外緣 10.5 m → 內圈 12.3 m）
    ring0 = [(x * 1.01, y * 1.01, GH) for x, y in base]
    ring1 = [(x * 0.72, y * 0.72, GH + 1.8) for x, y in base]
    loft(b, green, ring0, ring1)

    Z1 = GH - 0.5        # 禮拜堂塔身起點（被迴廊屋頂包住的部分不可見）

    def chapel(cx, cy, R, top, drum_r, drum_h, dome_R, dome_H, mats, pattern, tiers=2, chevrons=True):
        """禮拜堂：八角塔身（白壁柱、窗、白色人字紋）→ 層疊山牆 → 細高鼓座（白色小拱廊）→ 洋蔥頂＋十字架"""
        ap = R * math.cos(math.pi / 8)
        oct_prism(b, brick, R, Z1, top, cx, cy)
        for z in (Z1 + (top - Z1) * 0.42, top - 0.45):
            oct_prism(b, white, R + 0.22, z, z + 0.45, cx, cy)
        for k in range(8):
            a = TAU * k / 8
            q = (cx + math.cos(a + math.pi / 8) * R, cy + math.sin(a + math.pi / 8) * R)
            b.box_base(white, (0.4, 0.4, top - Z1 - 2.6), (q[0], q[1], Z1 + 2.2), rot=(0, 0, a + math.pi / 8))
            M = T(cx + math.cos(a) * (ap + 0.02), cy + math.sin(a) * (ap + 0.02), Z1 + (top - Z1) * 0.52) @ Rz(a + math.pi / 2)
            wh = min(2.6, (top - Z1) * 0.28)
            b.profile_wall(white, [(-0.75, -0.2), (0.75, -0.2), (0.75, wh * 0.72), (0, wh * 1.1), (-0.75, wh * 0.72)], 0.3, M)
            b.profile_wall(win, [(-0.42, 0), (0.42, 0), (0.42, wh * 0.68), (0, wh * 0.95), (-0.42, wh * 0.68)], 0.36, M)
            if chevrons:   # 白色人字紋（塔身下段）
                zc = Z1 + 2.6
                fw = 2 * R * math.sin(math.pi / 8) * 0.8
                for d in (-1, 1):
                    p0 = T(cx + math.cos(a) * (ap + 0.05), cy + math.sin(a) * (ap + 0.05), zc) @ Rz(a + math.pi / 2) @ Vector((d * fw / 2, 0, 0))
                    p1 = T(cx + math.cos(a) * (ap + 0.05), cy + math.sin(a) * (ap + 0.05), zc) @ Rz(a + math.pi / 2) @ Vector((0, 0, 2.2))
                    bar(b, white, p0, p1, 0.22)
        # 層疊山牆（白框＋綠／黃內面），上層錯開 22.5°
        z = top
        inner = [dm["green"], dm["yellow"]]
        for t in range(tiers):
            rr = ap * (1 - 0.16 * t) - 0.1
            w = 2 * R * math.sin(math.pi / 8) * (1.05 - 0.12 * t)
            h = w * 0.62
            oct_prism(b, brick, R * (1 - 0.16 * t), z, z + h * 0.55, cx, cy)
            kokoshnik_ring(b, white, inner, cx, cy, z, rr, 8, w, h, rot=(math.pi / 8 if t % 2 else 0.0), kind="keel", depth=0.4)
            z += h * 0.55
        # 收頂的綠色八角斜面
        b.lathe(green_d, [(R * (1 - 0.16 * tiers) + 0.1, z), (drum_r + 0.25, z + R * 0.3), (drum_r * 0.5, z + R * 0.3)], (cx, cy, 0), seg=8,
                smooth=False, rot_offset=math.pi / 8)
        zd = z + R * 0.3 - 0.05
        b.lathe(brick, [(drum_r, zd), (drum_r * 0.97, zd + drum_h)], (cx, cy, 0), seg=16, smooth=False)
        b.lathe(white, [(drum_r + 0.12, zd + drum_h * 0.3), (drum_r + 0.12, zd + drum_h * 0.36)], (cx, cy, 0), seg=16, smooth=False)
        for k in range(8):
            a = TAU * (k + 0.5) / 8
            b.box_base(white, (0.24, 0.24, drum_h * 0.62), (cx + math.cos(a) * (drum_r + 0.02), cy + math.sin(a) * (drum_r + 0.02), zd + drum_h * 0.36))
            am = a + TAU / 16
            M = T(cx + math.cos(am) * (drum_r - 0.02), cy + math.sin(am) * (drum_r - 0.02), zd + drum_h * 0.42) @ Rz(am + math.pi / 2)
            b.profile_wall(white, [(-0.42, 0), (0.42, 0), (0.42, drum_h * 0.36), (0, drum_h * 0.5), (-0.42, drum_h * 0.36)], 0.22, M)
            b.profile_wall(win, [(-0.24, 0.05), (0.24, 0.05), (0.24, drum_h * 0.32), (0, drum_h * 0.42), (-0.24, drum_h * 0.32)], 0.28, M)
        b.lathe(white, [(drum_r + 0.2, zd + drum_h), (drum_r + 0.35, zd + drum_h + 0.3), (drum_r * 0.85, zd + drum_h + 0.3)], (cx, cy, 0),
                seg=16, smooth=False)
        b.lathe(gold, [(drum_r * 0.86, zd + drum_h + 0.3), (drum_r * 0.86, zd + drum_h + 0.55), (drum_r * 0.7, zd + drum_h + 0.55)], (cx, cy, 0),
                seg=16, smooth=False)
        zt = onion(b, cx, cy, zd + drum_h + 0.5, dome_R, dome_H, mats, pattern, seg=32, n=18, neck=drum_r * 0.75 / dome_R)
        b.lathe(gold, [(0.22, zt - 0.25), (0.3, zt + 0.2), (0.1, zt + 0.5)], (cx, cy, 0), seg=8)
        cross(b, gold, cx, cy, zt + 0.4, h=dome_H * 0.38)
        return zt

    spiral = lambda tw, w: (lambda i, j: (i + int(j * tw)) // w)  # noqa: E731
    zigzag = lambda i, j: (j // 2 + (abs((i % 6) - 3) // 1)) // 2  # noqa: E731
    diamond = lambda i, j: ((i + j) // 3 + (i - j) // 3) % 2  # noqa: E731
    scales = lambda i, j: ((i + (j % 2)) // 1 + j) % 2  # noqa: E731

    D_BIG, D_SMALL = 15.0, 15.0
    # 中央代禱教堂（先建，四周禮拜堂會遮住下段）
    RC = 7.2
    oct_prism(b, brick, RC, Z1, 30.5, 0, 0)
    oct_prism(b, white, RC + 0.25, 18.5, 18.9, 0, 0)
    for k in range(8):
        a = TAU * k / 8
        q = (math.cos(a + math.pi / 8) * RC, math.sin(a + math.pi / 8) * RC)
        b.box_base(white, (0.45, 0.45, 27.5 - 13.0), (q[0], q[1], 13.0), rot=(0, 0, a + math.pi / 8))
        ap = RC * math.cos(math.pi / 8)
        M = T(math.cos(a) * (ap + 0.02), math.sin(a) * (ap + 0.02), 21.5) @ Rz(a + math.pi / 2)
        b.profile_wall(white, [(-0.9, -0.2), (0.9, -0.2), (0.9, 2.4), (0, 3.4), (-0.9, 2.4)], 0.3, M)
        b.profile_wall(win, [(-0.5, 0), (0.5, 0), (0.5, 2.2), (0, 2.9), (-0.5, 2.2)], 0.36, M)
    # 三層山牆
    z = 27.5
    for t in range(3):
        rr = RC * (1 - 0.1 * t) * math.cos(math.pi / 8) - 0.1
        w = 2 * RC * math.sin(math.pi / 8) * (1.0 - 0.1 * t)
        h = w * 0.55
        oct_prism(b, brick, RC * (1 - 0.1 * t), z, z + h * 0.6, 0, 0)
        kokoshnik_ring(b, white, [dm["green"], dm["yellow"], brick], 0, 0, z, rr, 8, w, h, rot=(math.pi / 8 if t % 2 else 0.0), kind="keel")
        z += h * 0.6
    # 八角鼓（白色星形裝飾帶）
    RT = RC * 0.74
    oct_prism(b, brick, RT, z, z + 3.0, 0, 0)
    for k in range(8):
        a = TAU * k / 8
        ap = RT * math.cos(math.pi / 8)
        M = T(math.cos(a) * (ap + 0.02), math.sin(a) * (ap + 0.02), z + 0.6) @ Rz(a + math.pi / 2)
        b.profile_wall(white, [(-1.1, 0), (1.1, 0), (1.1, 1.2), (0, 1.9), (-1.1, 1.2)], 0.25, M)
        b.profile_wall(dm["green"], [(-0.6, 0.25), (0.6, 0.25), (0.6, 1.0), (0, 1.5), (-0.6, 1.0)], 0.32, M)
    z += 3.0
    oct_prism(b, white, RT + 0.3, z, z + 0.5, 0, 0)
    z += 0.5
    # 帳篷頂（橘紅＋白色菱格）＋白色稜線＋小老虎窗
    ZT, TH = z, 15.5
    RTT = RT + 0.1
    tent(b, tent_mi, RTT, ZT, TH, 0, 0, sides=8, r_top=1.25)
    for k in range(8):
        a = math.pi / 8 + TAU * k / 8
        bar(b, white, (math.cos(a) * (RTT + 0.02), math.sin(a) * (RTT + 0.02), ZT), (math.cos(a) * 1.3, math.sin(a) * 1.3, ZT + TH), 0.3)
    for zz, n in ((ZT + 1.2, 8), (ZT + 4.2, 8), (ZT + 7.2, 8)):
        rr = (RTT + (1.25 - RTT) * (zz - ZT) / TH) * math.cos(math.pi / 8) + 0.05
        for k in range(n):
            a = TAU * k / n
            M = T(math.cos(a) * rr, math.sin(a) * rr, zz) @ Rz(a + math.pi / 2)
            b.profile_wall(white, [(-0.45, 0), (0.45, 0), (0.45, 0.9), (0, 1.4), (-0.45, 0.9)], 0.7, M)
            b.profile_wall(dm["green"], [(-0.28, 0.12), (0.28, 0.12), (0.28, 0.8), (0, 1.15), (-0.28, 0.8)], 0.78, M)
    zl = ZT + TH
    oct_prism(b, white, 1.6, zl, zl + 0.4, 0, 0)
    oct_prism(b, brick, 1.35, zl + 0.4, zl + 3.2, 0, 0)
    oct_prism(b, white, 1.55, zl + 3.2, zl + 3.5, 0, 0)
    zt = onion(b, 0, 0, zl + 3.5, 2.0, 4.0, [dm["gold"], dm["gold_d"]], lambda i, j: (j // 3) % 2 if j < 6 else 0, seg=24, n=12, neck=0.65)
    cross(b, gold, 0, 0, zt + 0.1, h=2.9)

    # 四大禮拜堂：南＝粉白鋸齒、西＝紅綠菱格、東＝綠黃螺旋、北＝藍白螺旋
    for (dx, dy), top, mats, pat, dr_h, dH in (((0, -D_BIG), 25.0, [dm["pink"], dm["white"], dm["pink"], dm["red"]], zigzag, 6.0, 8.6),
                                              ((-D_BIG, 0), 24.0, [dm["red"], dm["green"], dm["yellow"]], diamond, 5.4, 8.0),
                                              ((D_BIG, 0), 26.0, [dm["green"], dm["yellow"], dm["green"], dm["white"]], spiral(0.85, 2), 6.4, 8.8),
                                              ((0, D_BIG), 25.0, [dm["blue"], dm["white"]], spiral(-1.0, 2), 6.0, 8.6)):
        chapel(dx, dy, 4.5, top, 2.7, dr_h, 3.5, dH, mats, pat, tiers=2)
    # 四小禮拜堂（斜角）
    q = D_SMALL / math.sqrt(2)
    for (dx, dy), mats, pat in (((-q, -q), [dm["yellow"], dm["green"]], scales),
                                ((q, -q), [dm["green"], dm["white"], dm["lgreen"]], spiral(0.6, 2)),
                                ((q, q), [dm["blue"], dm["green"], dm["yellow"]], spiral(-0.8, 2)),
                                ((-q, q), [dm["yellow"], dm["green"]], diamond)):
        chapel(dx, dy, 3.2, 18.5, 2.0, 4.0, 2.6, 5.6, mats, pat, tiers=2, chevrons=False)

    # 鐘樓（東南角，台基外側）
    bx, by = 24.0, -13.0
    b.box_base(brick, (7.0, 7.0, GH + 2.5 + 1.0), (bx, by, -1.0))
    b.box_base(white, (7.5, 7.5, 0.5), (bx, by, GH + 2.5))
    for f in range(4):
        a = f * math.pi / 2
        M = T(bx, by, 2.0) @ Rz(a) @ T(0, -3.52, 0)
        b.profile_wall(white, [(-1.2, 0), (1.2, 0), (1.2, 3.0), (0, 4.2), (-1.2, 3.0)], 0.3, M)
        b.profile_wall(win, [(-0.8, 0.2), (0.8, 0.2), (0.8, 2.8), (0, 3.7), (-0.8, 2.8)], 0.36, M)
    z = GH + 3.0
    oct_prism(b, brick, 3.6, z, z + 2.5, bx, by)
    oct_prism(b, white, 3.85, z + 2.5, z + 2.9, bx, by)
    z += 2.9
    for k in range(8):           # 開敞鐘樓
        a = math.pi / 8 + TAU * k / 8
        b.box_base(white, (0.6, 0.6, 6.0), (bx + math.cos(a) * 3.2, by + math.sin(a) * 3.2, z))
    oct_prism(b, win, 2.8, z, z + 6.0, bx, by)
    z += 6.0
    oct_prism(b, white, 3.85, z, z + 0.7, bx, by)
    kokoshnik_ring(b, white, [dm["green"]], bx, by, z + 0.7, 3.1, 8, 2.3, 1.3, kind="round", depth=0.3)
    z += 0.7
    tent(b, green, 3.5, z, 10.5, bx, by, sides=8, r_top=0.45)
    for zz in (z + 2.4, z + 5.0):   # 帳篷上的小老虎窗
        rr = 3.5 - (zz - z) / 10.5 * 3.05
        for k in range(4):
            a = TAU * k / 4 + math.pi / 8
            M = T(bx + math.cos(a) * rr * math.cos(math.pi / 8), by + math.sin(a) * rr * math.cos(math.pi / 8), zz) @ Rz(a + math.pi / 2)
            b.profile_wall(white, [(-0.35, 0), (0.35, 0), (0.35, 0.8), (0, 1.2), (-0.35, 0.8)], 0.6, M)
    zt = z + 10.5
    zt = onion(b, bx, by, zt - 0.1, 0.9, 1.7, [dm["gold"]], lambda i, j: 0, seg=16, n=8, neck=0.6)
    cross(b, gold, bx, by, zt, h=1.8)

    # 西南、西北階梯門廊：綠色雙帳篷頂
    for (px, py, sgn) in ((-11.5, -a_c, -1), (-11.5, a_c, 1)):
        cy = py + sgn * 2.4
        b.box_base(brick, (9.0, 5.0, GH + 1.0), (px, cy, -1.0))
        b.box_base(white, (9.4, 5.4, 0.4), (px, cy, GH))
        M = T(px, cy + sgn * 2.52, 0.0) @ Rz(0 if sgn < 0 else math.pi)
        b.profile_wall(white, [(-2.2, 0), (2.2, 0), (2.2, 4.2), (0, 6.4), (-2.2, 4.2)], 0.3, M)
        b.profile_wall(win, [(-1.6, 0), (1.6, 0), (1.6, 4.0), (0, 5.8), (-1.6, 4.0)], 0.36, M)
        for dx in (-2.2, 2.2):
            b.box_base(brick, (3.6, 3.6, 2.4), (px + dx, cy, GH + 0.4))
            b.box_base(white, (3.9, 3.9, 0.3), (px + dx, cy, GH + 2.8))
            tent(b, green, 2.45, GH + 3.1, 6.0, px + dx, cy, sides=4, r_top=0.12, rot=math.pi / 4)
            zt = onion(b, px + dx, cy, GH + 8.9, 0.5, 1.0, [dm["gold"]], lambda i, j: 0, seg=12, n=6)
            cross(b, gold, px + dx, cy, zt, h=1.2)
        # 階梯（沿立面往西下降）
        for k in range(18):
            zt_ = PH - k * PH / 18
            x0 = px - 4.5 - (k + 1) * 0.75
            b.box_base(white if k % 6 == 0 else curb, (0.78, 3.0, max(0.05, zt_)), (x0 + 0.375, cy, 0.0))
        b.box_base(brick, (14.0, 0.6, 1.0), (px - 4.5 - 6.75, cy + sgn * 1.8, 0.0))
