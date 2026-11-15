"""motherland 伏爾加格勒「祖國母親在召喚」雕像寫實模型（公尺）

- 位於馬馬耶夫崗頂；女性人像高 52 m（至頭頂），右手高舉 33 m 長劍，連劍總高約 85 m
- 姿態：大步向前、左臂向前側伸展張開手掌、頭轉向左側呼喊；長裙與披肩在身後被風吹起
- 預力混凝土外表為淡灰白色；立於約 2 m 高的長方形混凝土基座
- 雕塑以 metaball（隱式曲面）組合人體與衣褶後轉成網格，劍為獨立的稜角幾何
- 地面為山崗頂的草坪（略呈圓丘）與基座周邊步道

座標：雕像面向 -Y（前方），+X 為她的左側；基座頂面中心 z = 2。參考照由正前方偏右手側的坡下仰拍。
"""

import math

import bmesh
import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

from lib import Builder

CAMERA = ((2, 0, 42), -14, -20, 98, 28)

BASE_Z = 2.0
K = 1.6    # metaball 半徑 → 實際表面半徑的換算（stiffness 2、threshold 0.45：(1-x²)³·s = t）


def build_figure(b, mi):
    """以 metaball 組合人像，轉成網格後併入 Builder 的 bmesh"""
    mb = bpy.data.metaballs.new("figure")
    mb.resolution = 0.42
    mb.render_resolution = 0.42
    mb.threshold = 0.45
    obj = bpy.data.objects.new("figure", mb)
    bpy.context.scene.collection.objects.link(obj)

    def ball(c, r, stiff=2.0):
        e = mb.elements.new()
        e.type = "BALL"
        e.co = Vector(c)
        e.radius = r * K
        e.stiffness = stiff

    def cap(p0, p1, r, stiff=2.0):
        p0, p1 = Vector(p0), Vector(p1)
        d = p1 - p0
        e = mb.elements.new()
        e.type = "CAPSULE"
        e.co = (p0 + p1) / 2
        e.radius = r * K
        e.size_x = d.length / 2 if d.length > 1e-6 else 0.0
        e.rotation = Vector((1, 0, 0)).rotation_difference(d.normalized()) if d.length > 1e-6 else Quaternion()
        e.stiffness = stiff

    def ell(c, size, rot=(0, 0, 0), stiff=2.0, r=1.0):
        e = mb.elements.new()
        e.type = "ELLIPSOID"
        e.co = Vector(c)
        e.radius = r * K
        e.size_x, e.size_y, e.size_z = size
        e.rotation = Euler(rot).to_quaternion()
        e.stiffness = stiff

    Z = BASE_Z
    # ---------------- 軀幹
    ell((0, -0.3, Z + 37.5), (5.6, 3.7, 5.8))
    ell((0, 0.3, Z + 31.5), (4.4, 3.4, 4.0))
    ell((0, 0.8, Z + 26.5), (5.8, 4.3, 4.4))
    for sx in (-1, 1):
        ball((sx * 2.3, -3.0, Z + 38.2), 1.9, stiff=1.6)
        ball((sx * 5.8, 0.0, Z + 42.3), 2.3)
    # 頸、頭（轉向左側、微仰）、髮髻
    cap((0, -0.4, Z + 42.5), (0.4, -0.9, Z + 46.2), 1.55)
    face = Vector((math.sin(math.radians(28)), -math.cos(math.radians(28)), 0.12)).normalized()
    hc = Vector((0.6, -1.0, Z + 49.0))
    ell(hc, (2.5, 2.9, 3.4), rot=(math.radians(-8), 0, math.radians(28)))
    ball(hc + face * 2.75 + Vector((0, 0, -0.1)), 0.55, stiff=1.4)        # 鼻
    ball(hc + face * 2.2 + Vector((0, 0, -1.9)), 1.05, stiff=1.6)         # 下巴（張口呼喊）
    ball(hc - face * 2.0 + Vector((0, 0, 0.6)), 1.9, stiff=1.6)           # 後腦／髮髻
    ell(hc - face * 1.0 + Vector((0, 0, 2.2)), (2.4, 2.4, 1.0), stiff=1.4)  # 頭頂頭髮
    for k in range(5):                                                    # 飄起的髮束
        cap(hc - face * 1.6 + Vector((0, 0, 1.0 - k * 0.6)), hc - face * (4.0 + k * 0.6) + Vector((-1.2, 0.8, 0.2 - k * 0.8)), 0.55, stiff=1.4)
    # ---------------- 右臂（高舉握劍）
    sh_r = Vector((-5.8, 0.0, Z + 42.3))
    el_r = Vector((-8.6, 1.8, Z + 51.5))
    wr_r = Vector((-10.2, 2.8, Z + 58.8))
    cap(sh_r, el_r, 2.0)
    cap(el_r, wr_r, 1.6)
    ball(wr_r + Vector((-0.2, 0.2, 1.4)), 1.75)                            # 拳
    # ---------------- 左臂（向前側伸展，手掌張開）
    sh_l = Vector((5.8, 0.0, Z + 42.3))
    el_l = Vector((12.0, -3.0, Z + 43.4))
    wr_l = Vector((17.6, -6.8, Z + 44.2))
    cap(sh_l, el_l, 1.9)
    cap(el_l, wr_l, 1.5)
    palm_c = wr_l + Vector((1.3, -0.9, 0.0))
    ell(palm_c, (1.5, 0.55, 1.25), rot=(0, 0, math.radians(-35)))
    fdir = Vector((0.82, -0.55, 0.0)).normalized()
    side = Vector((0, 0, 1)).cross(fdir).normalized()
    for k, (spread, L) in enumerate(((-0.55, 2.2), (-0.18, 2.7), (0.12, 2.9), (0.4, 2.6), (0.7, 2.1))):
        base = palm_c + fdir * 1.2 + Vector((0, 0, 0.9 - k * 0.45))
        d = (fdir + Vector((0, 0, spread * 0.6)) + side * spread * 0.2).normalized()
        cap(base, base + d * L, 0.36 if k else 0.42, stiff=1.6)
    cap(palm_c + Vector((0, 0, -0.9)), palm_c + Vector((0.4, -1.6, -1.9)), 0.45, stiff=1.6)   # 拇指
    # ---------------- 腿（左腿前跨、右腿後蹬）：大多藏在裙內，只露出膝蓋起伏與腳
    cap((2.6, -0.8, Z + 24.0), (3.0, -5.0, Z + 14.0), 2.6)
    cap((3.0, -5.0, Z + 14.0), (3.1, -6.0, Z + 3.0), 1.8)
    cap((3.0, -6.6, Z + 1.0), (3.2, -10.2, Z + 0.7), 1.1)
    cap((-2.6, 1.2, Z + 24.0), (-3.0, 3.4, Z + 13.0), 2.5)
    cap((-3.0, 3.4, Z + 13.0), (-3.3, 5.6, Z + 3.0), 1.7)
    cap((-3.3, 5.8, Z + 1.4), (-3.4, 3.4, Z + 0.6), 1.0)
    # ---------------- 長裙：一圈垂直衣褶（上窄下寬、身後被風吹起），褶間形成直向凹凸
    ell((0.0, 1.0, Z + 20.0), (5.2, 4.2, 6.5), stiff=1.8)
    n_f = 14
    for k in range(n_f):
        t = math.tau * k / n_f
        ct, st = math.cos(t), math.sin(t)
        back = max(0.0, st)                       # +Y 為身後
        top = Vector((ct * 4.6, 0.8 + st * 3.6, Z + 26.0))
        bot = Vector((ct * (7.4 + 0.8 * back), 1.6 + st * (6.2 + 3.5 * back) + 1.8 * back, Z + 1.4 + 1.5 * back))
        if st < -0.5 and ct > 0:                  # 左腿前跨處，下擺被腿撐向前
            bot += Vector((0.0, -1.6, 0.0))
        cap(top, bot, 1.5 + 0.5 * (k % 2), stiff=1.7)
    # 身後被風吹起的大片裙擺（扁長橢球形成大衣褶）
    for c, size, rot in (((-1.5, 10.5, Z + 9.0), (5.0, 1.8, 6.5), (0.35, 0, -0.2)),
                         ((3.0, 11.0, Z + 13.0), (4.0, 1.6, 6.0), (0.45, 0, 0.3)),
                         ((0.5, 8.0, Z + 20.0), (4.5, 1.8, 5.0), (0.5, 0, 0)),
                         ((5.0, 9.0, Z + 5.0), (3.0, 1.8, 4.0), (0.3, 0, 0.4))):
        ell(c, size, rot=rot, stiff=1.6)
    # 披肩：從右肩垂到右臀側，形成一大片衣褶
    cap((-5.6, 0.8, Z + 40.5), (-7.6, 1.6, Z + 31.0), 2.0, stiff=1.7)
    ell((-7.6, 1.8, Z + 28.5), (2.4, 3.0, 4.5), rot=(0.2, -0.15, 0), stiff=1.6)
    cap((-7.0, 2.4, Z + 30.0), (-8.4, 5.0, Z + 20.0), 1.5, stiff=1.6)
    cap((5.0, 1.5, Z + 41.0), (2.0, 4.5, Z + 34.0), 1.4, stiff=1.6)
    cap((-4.6, -2.4, Z + 40.6), (3.4, -3.0, Z + 30.5), 1.0, stiff=1.6)     # 胸前斜披衣帶

    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    bpy.data.objects.remove(obj)
    bpy.data.metaballs.remove(mb)
    b.bm.verts.ensure_lookup_table()
    start_f = len(b.bm.faces)
    b.bm.from_mesh(me)
    bpy.data.meshes.remove(me)
    b.bm.faces.ensure_lookup_table()
    for f in b.bm.faces[start_f:]:
        f.material_index = mi
        f.smooth = True
    return wr_r + Vector((-0.2, 0.2, 1.4))


def sword(b, mi, fist, tip):
    """長劍：握柄＋護手＋菱形斷面的錐形劍身"""
    fist, tip = Vector(fist), Vector(tip)
    d = (tip - fist).normalized()
    q = d.to_track_quat("Z", "Y")
    R = q.to_matrix().to_4x4()

    def place(verts, M):
        bmesh.ops.transform(b.bm, matrix=M, verts=verts)

    L = (tip - fist).length
    # 握柄（拳內）
    vs = b.cyl(mi, 0.45, 0.45, 4.6, (0, 0, 0), seg=8)
    place(vs, Matrix.Translation(fist - d * 2.4) @ R)
    # 護手
    vs = b.box(mi, (6.0, 1.1, 0.9), (0, 0, 0))
    place(vs, Matrix.Translation(fist + d * 2.4) @ R)
    # 劍身（菱形斷面，底寬 1.9 m → 尖端）
    g = fist + d * 2.75
    Lb = (tip - g).length
    ring0 = [Vector((1.3, 0, 0)), Vector((0, 0.32, 0)), Vector((-1.3, 0, 0)), Vector((0, -0.32, 0))]
    ring1 = [p * 0.55 + Vector((0, 0, Lb * 0.86)) for p in ring0]
    M = Matrix.Translation(g) @ R
    v0 = [b.bm.verts.new(M @ p) for p in ring0]
    v1 = [b.bm.verts.new(M @ p) for p in ring1]
    vt = b.bm.verts.new(M @ Vector((0, 0, Lb)))
    faces = [b.bm.faces.new(list(reversed(v0)))]
    for i in range(4):
        j = (i + 1) % 4
        faces.append(b.bm.faces.new([v0[i], v0[j], v1[j], v1[i]]))
        faces.append(b.bm.faces.new([v1[i], v1[j], vt]))
    for f in faces:
        f.material_index = mi
        f.smooth = False
    _ = L


def motherland(path):
    b = Builder("Motherland", seed=5)
    concrete = b.tex("concrete", "plastered_wall_04", tile=7.0, tint="#cdc8bb", rough=0.85, normal=0.6)
    steel = b.tex("sword", "plastered_wall_04", tile=4.0, tint="#cbc6ba", rough=0.6, normal=0.3)
    base_c = b.tex("base", "white_sandstone_blocks_02", tile=3.0, tint="#cdc8bc", rough=0.8, normal=0.4)
    path_c = b.tex("path", "gravel_floor", tile=2.5, tint="#a8a296", rough=0.9, normal=0.3)
    grass = b.tex("grass", "grass_ground", tile=6.0, tint="#6b8a3c", gain=0.95, rough=0.95, normal=0.3)
    soil = b.color("soil", "#6b5a45", rough=0.95)

    # ---------------------------------------------------------------- 山崗頂草坪
    b.ground_disc(grass, 200, soil, depth=30, rings=24, seg=96, height_fn=lambda x, y: -0.00042 * (x * x + y * y))
    # 基座：兩層混凝土板
    b.box_base(path_c, (34.0, 30.0, 0.35), (0, 0.5, -0.1))
    b.box_base(base_c, (22.0, 17.0, 0.6), (0, 0.5, 0.0))
    b.box_base(base_c, (19.0, 14.5, BASE_Z - 0.6), (0, 0.5, 0.6))
    # 通往雕像的步道（前方蜿蜒小徑以直線近似）
    for k in range(1):
        y = -18.0 - k * 14.0
        b.box_base(path_c, (5.0, 14.2, 0.3), (-1.0 - k * 1.2, y, -0.00042 * y * y - 0.2), rot=(0.0, 0, 0.08))

    fist = build_figure(b, concrete)
    sword(b, steel, fist, (11.5, 7.5, 85.0))
    b.export(path)
