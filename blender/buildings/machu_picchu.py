"""machu-picchu 馬丘比丘（印加古城，約 1450 年）寫實模型（公尺；+Y 北，城區主廣場高程定為 0）

- 地形：古城位於南北向山脊頂（約 360 × 170 m），東西兩側陡降至約 -420 m 的烏魯班巴河谷；
  北側經鞍部接瓦伊納比丘（Huayna Picchu，比城區高約 300 m 的尖峰，岩壁稜角分明、以 ridged noise 做出岩脊與斷崖），
  瓦伊納比丘向東延伸出巨大的陡壁山稜；西北另有一座較低的尖峰
- 城區：外圍為層層農業梯田（每階約 2.6 m 高、3.2 m 寬，灰色石砌擋土牆＋綠色草面），頂部分為
  中央大草坪廣場、西側神殿區（兩層台＋拴日石小丘）、東側住居區（密集的無頂石屋，兩端山牆三角）、南側梯田區
- 植被：山體為深綠雲霧林（程式樹冠貼圖），坡度過陡處露出灰色花崗岩（依面法線＋雜訊分配材質、平滑著色只用於林面）
- 背景：外環遠山（半徑 750–1250 m），越遠越偏藍灰，表現霧氣層次

註：舊版「深色岩壁在算圖中變成淺灰色方塊」的原因是材質指派邏輯——城區網格中凡是陡面（span>1.3 或 nz<0.5）
一律指派成淺灰色砌石牆貼圖（stone_wall_04），山坡懸崖因此變成淺灰方塊；深色 cliff 材質只在幾乎不存在的條件下才會被選到。
與 UV、法線或 GLB 材質槽無關。本版改為：岩壁依坡度另用花崗岩貼圖，砌石牆只用在梯田擋土牆與石屋。
"""

import math
import os

from mathutils import Matrix, Vector, noise

from lib import TAU, TEX
from buildings.kinkakuji import GEN, AsiaBuilder, _cloud, _save_maps, gen_canopy

# (目標點, 方位角, 仰角, 距離, 焦距)：參考照自南側守衛屋上方俯瞰古城，瓦伊納比丘居中
CAMERA = ((0.0, 330.0, 30.0), 3.5, 12.0, 640.0, 28)

# 城區外輪廓：圓角矩形（中心、半寬、半深、圓角半徑）
CX, CY, CA, CB, CR = 0.0, 20.0, 85.0, 180.0, 55.0
STEP_W, STEP_H, N_TERR = 3.2, 2.6, 15


def city_sdf(x, y):
    qx = abs(x - CX) - (CA - CR)
    qy = abs(y - CY) - (CB - CR)
    return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - CR


def rrect(a, b, r, z, n_arc=8):
    """圓角矩形頂點（逆時針）"""
    pts = []
    for k, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        a0 = k * math.pi / 2
        for i in range(n_arc + 1):
            t = a0 + (math.pi / 2) * i / n_arc
            pts.append((CX + sx * (a - r) + r * math.cos(t), CY + sy * (b - r) + r * math.sin(t), z))
    return pts


def _n(x, y, s, z=0.0):
    return noise.noise(Vector((x / s, y / s, z)))


def _ridged(x, y, s, z=0.0, oct_=3):
    v, a, f = 0.0, 1.0, 1.0
    for _ in range(oct_):
        v += a * (1 - abs(noise.noise(Vector((x * f / s, y * f / s, z + 3.1 * f))))) ** 2
        a *= 0.5
        f *= 2.1
    return v


def natural(x, y):
    # 山脊縱剖面
    if y > 200:
        E = -0.55 * (y - 200)
    elif y < -160:
        E = max(-0.82 * (-160 - y), 0.9 * (-300 - y) - 20)
    else:
        E = 0.0
    xc = 0.06 * max(0.0, y - 150)
    u = abs(x - xc) - CA
    if u > 0:
        g = 0.82 * u if u < 45 else 37 + 1.6 * (u - 45)
        g += 18 * max(0.0, _n(x, y, 90.0, 1.0)) * min(1.0, u / 60)
        E -= g
    h = E
    # 瓦伊納比丘：陡峭尖峰＋岩脊（ridged noise）＋岩層斷崖
    px, py = 15.0, 600.0
    r = math.hypot(x - px, (y - py) / 1.2)
    if r < 260:
        t = 1 - r / 235.0
        base = 330.0 * max(0.0, t) ** 0.95 - 60 + 12 * t
        rid = _ridged(x, y, 70.0, 5.0)
        ang = math.atan2(y - py, x - px)
        flute = (1 - abs(math.sin(ang * 5 + 0.7 * _n(x, y, 60.0, 9.0) * 3))) ** 3  # 放射狀稜脊
        hp = base + (28 * rid + 22 * flute) * min(1.0, max(0.0, t) * 2.5) - 20
        # 岩層：輕微量化造成斷崖帶
        q = hp / 22.0
        hp = 22.0 * (math.floor(q) + min(1.0, (q - math.floor(q)) * 1.6)) * 0.55 + hp * 0.45
        h = max(h, hp)
    # 東側巨大陡壁山稜（自峰頂向東南東下降）
    ax, ay, bx, by = 15.0, 600.0, 480.0, 430.0
    L2 = (bx - ax) ** 2 + (by - ay) ** 2
    t = max(0.0, min(1.0, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / L2))
    qx, qy = ax + (bx - ax) * t, ay + (by - ay) * t
    side = (x - qx) * (by - ay) - (y - qy) * (bx - ax)   # >0：南側（面向相機）
    q = math.hypot(x - qx, y - qy)
    crest = 230.0 * (1 - t) ** 0.9 - 70 + 25 * _ridged(x, y, 60.0, 2.0)
    hr = crest - q * (3.2 if side > 0 else 1.3)
    h = max(h, hr)
    # 西北較低尖峰
    r2 = math.hypot(x + 190, (y - 340) * 1.1)
    if r2 < 160:
        t2 = 1 - r2 / 125.0
        hl = 150.0 * max(0.0, t2) ** 1.1 - 60 + 20 * _ridged(x, y, 45.0, 7.0) * max(0.0, t2)
        h = max(h, hl)
    # 一般起伏
    h += 6 * _n(x, y, 40.0, 3.3) + 3 * _n(x, y, 15.0, 4.4)
    return max(h, -420.0 + 8 * _n(x, y, 50.0))


def height(x, y):
    h = natural(x, y)
    d = city_sdf(x, y)
    if d < N_TERR * STEP_W + 2:
        cap = -STEP_H * (math.floor(max(0.0, d) / STEP_W) + 1) - 0.8
        h = min(h, cap)
    return h


def bake_terrain(name, Hg, step, N=2048, seed=4):
    """把地形依坡度烘成俯視色貼圖：緩坡為深綠雲霧林（樹冠斑點）、陡坡露出灰色花崗岩（含苔斑），
    山溝較暗、稜線較亮。Hg[i, j] 為網格高程（i 沿 x、j 沿 y）。貼圖第 0 列對應 y 最大處。"""
    import numpy as np
    from PIL import Image, ImageFilter

    out = os.path.join(GEN, name)
    if os.path.exists(os.path.join(out, "diff.jpg")):
        return out
    rng = np.random.default_rng(seed)
    img = Image.fromarray(np.ascontiguousarray(Hg.T[::-1]).astype(np.float32), mode="F")   # 列=y（上大）、行=x
    H = np.asarray(img.resize((N, N), Image.Resampling.BICUBIC), dtype=float)
    px = step * (Hg.shape[0] - 1) / N
    gy, gx = np.gradient(H, px)
    nz = 1.0 / np.sqrt(1 + gx * gx + gy * gy)
    hi = Image.fromarray(H.astype(np.float32), mode="F")
    blur = np.asarray(hi.resize((N // 24, N // 24), Image.Resampling.BOX).resize((N, N), Image.Resampling.BICUBIC), dtype=float)
    cav = np.clip((H - blur) / 12.0, -1, 1)          # 稜線 +、山溝 -
    n1 = _cloud(rng, N, 96, 1.0) + _cloud(rng, N, 24, 0.5)
    rock = np.clip((0.5 + n1 * 0.35 - nz) * 7.0 + cav * 0.8, 0, 1)
    moss = np.clip(_cloud(rng, N, 16, 1.6) + 0.1, 0, 1) * (1 - np.clip((0.3 - nz) * 6, 0, 1))
    # 林：深綠＋樹冠斑點
    can = Image.open(os.path.join(gen_canopy("andes_deep3", (40, 70, 32), seed=12), "diff.jpg")).convert("RGB").resize((96, 96))
    reps = N // 96 + 1
    ct = np.tile(np.asarray(can, dtype=float), (reps, reps, 1))[:N, :N]
    ct = ct / ct.reshape(-1, 3).mean(0)[None, None]
    tone = 1 + _cloud(rng, N, 128, 0.35)
    forest = np.array((38, 64, 30), float)[None, None] * ct * tone[..., None]
    forest = forest * (1 + 0.15 * np.clip(_cloud(rng, N, 64, 1.0), 0, 1))[..., None] + np.array((10, 14, 4))[None, None] * np.clip(cav, 0, 1)[..., None] * 3
    # 岩：灰色花崗岩，帶縱向流痕與苔
    rk = Image.open(os.path.join(TEX, "rock_face_03", "diff.jpg")).convert("L").resize((160, 160))
    reps = N // 160 + 1
    rt = np.tile(np.asarray(rk, dtype=float), (reps, reps))[:N, :N]
    rt = rt / rt.mean()
    grey = np.array((108, 108, 102), float)[None, None] * (0.75 + 0.25 * rt)[..., None] * (1 + _cloud(rng, N, 8, 0.25))[..., None]
    grey = grey * (1 - 0.35 * np.clip(-n1, 0, 1))[..., None]
    mossc = np.array((58, 76, 40), float)[None, None]
    rockc = grey * (1 - 0.5 * moss[..., None]) + mossc * 0.5 * moss[..., None]
    col = forest * (1 - rock[..., None]) + rockc * rock[..., None]
    col = col * (1 + 0.45 * cav)[..., None]
    _save_maps(out, col, None)
    return out


class AndesBuilder(AsiaBuilder):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.planar = {}

    def _uv(self):
        super()._uv()
        uv = self.bm.loops.layers.uv.verify()
        for f in self.bm.faces:
            if f.material_index in self.planar:
                X0, Y0, W, Hh = self.planar[f.material_index]
                for l in f.loops:
                    c = l.vert.co
                    l[uv].uv = ((c.x - X0) / W, (c.y - Y0) / Hh)

    def block(self, mi, x0, x1, y0, y1, z0, z1, top=None, bottom=False):
        vs = [self.V(p) for p in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                  (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        fs = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        if bottom:
            fs.append((0, 3, 2, 1))
        for f in fs:
            self.face([vs[i] for i in f], mi)
        self.face([vs[i] for i in (4, 5, 6, 7)], top if top is not None else mi)

    def slab(self, pts, z0, z1, side, top):
        """多邊形（逆時針）擠出：側面 side、頂面 top"""
        bot = [self.V((x, y, z0)) for x, y, _ in pts]
        tp = [self.V((x, y, z1)) for x, y, _ in pts]
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            self.face([bot[i], bot[j], tp[j], tp[i]], side)
        self.face(tp, top)


def machu_picchu(path):
    b = AndesBuilder("MachuPicchu", seed=9)
    rng = b.rng
    grass = b.ptex("grass", "grass_ground", tile=5.0, tint="#5b8a2a", rough=0.95, normal=0.6)
    lawn = b.ptex("lawn", "grass_ground", tile=4.0, tint="#7cb03c", rough=0.95, normal=0.4)
    wall = b.ptex("wall", "stone_wall_04", tile=2.6, tint="#827f76", rough=0.9, normal=1.0)
    wall_d = b.ptex("wall_d", "stone_wall_04", tile=2.6, tint="#6f6c64", rough=0.9, normal=1.0)
    forest = b.gtex("forest", gen_canopy("andes_deep3", (40, 70, 32), seed=12), tile=22.0, rough=0.95, normal=1.0)
    rock_s = b.ptex("rock_s", "rock_04", tile=3.0, tint="#8e8b82", rough=0.9, normal=1.0)
    hz = []
    for k, (col, em) in enumerate((("#3a5a50", 0.04), ("#4f6f72", 0.12), ("#6c8792", 0.22), ("#8ea3b0", 0.34))):
        mi = b.color(f"haze{k}", col, rough=0.95)
        bs = b.mats[mi].node_tree.nodes["Principled BSDF"]
        bs.inputs["Emission Color"].default_value = bs.inputs["Base Color"].default_value
        bs.inputs["Emission Strength"].default_value = em
        hz.append(mi)
    thatch = b.ptex("thatch", "grass_ground", tile=1.5, tint="#a08a5a", rough=1.0, normal=0.6)
    shadow = b.color("shadow", "#2a2722", rough=1.0)

    # ---------------- 主地形（圓盤範圍網格；陡面為花崗岩、其餘為林）
    OX, OY, RMAX = 0.0, 180.0, 760.0
    STEP = 6.0
    x0, x1, y0, y1 = OX - RMAX, OX + RMAX, OY - RMAX, OY + RMAX
    nx, ny = int((x1 - x0) / STEP), int((y1 - y0) / STEP)
    H = {}
    verts = {}

    def hv(i, j):
        if (i, j) not in H:
            x, y = x0 + i * STEP, y0 + j * STEP
            H[(i, j)] = height(x, y)
        return H[(i, j)]

    def vv(i, j):
        if (i, j) not in verts:
            verts[(i, j)] = b.V((x0 + i * STEP, y0 + j * STEP, hv(i, j)))
        return verts[(i, j)]

    import numpy as np
    Hg = np.array([[hv(i, j) for j in range(ny + 1)] for i in range(nx + 1)])   # [i(x), j(y)]
    terr = b.gtex("terrain", bake_terrain("mp_terrain4", Hg, STEP), tile=1.0, rough=0.95, normal=0.0)
    b.planar[terr] = (x0, y0, x1 - x0, y1 - y0)
    for i in range(nx):
        for j in range(ny):
            cx, cy = x0 + (i + 0.5) * STEP, y0 + (j + 0.5) * STEP
            if math.hypot(cx - OX, cy - OY) > RMAX:
                continue
            if city_sdf(cx, cy) < -3:
                continue  # 城區頂面由梯田幾何負責
            b.face([vv(i, j), vv(i + 1, j), vv(i + 1, j + 1), vv(i, j + 1)], terr, smooth=True)

    # ---------------- 外環遠山（越遠越偏藍灰：霧氣層次）
    NA, NRr = 180, 18
    r_in, r_out = RMAX - 12, 1250.0
    ring = []
    for ia in range(NA):
        a = TAU * ia / NA
        row = []
        for jr in range(NRr + 1):
            r = r_in + (r_out - r_in) * jr / NRr
            x, y = OX + r * math.cos(a), OY + r * math.sin(a)
            if jr == 0:
                z = height(x, y) - 2.0
            else:
                tt = jr / NRr
                pk = 120 + 420 * _ridged(x, y, 240.0, 11.0) + 180 * _n(x, y, 400.0, 12.0)
                z = -420 + (pk + 420) * min(1.0, max(0.0, tt - 0.1) * 1.6) ** 1.1 - 260 * max(0.0, tt - 0.8)
                z = max(z, height(x, y) - 2.0) if jr == 1 else z
            row.append(b.V((x, y, z)))
        ring.append(row)
    for ia in range(NA):
        ib = (ia + 1) % NA
        for jr in range(NRr):
            r = r_in + (r_out - r_in) * (jr + 0.5) / NRr
            mi = forest if r < 860 else hz[min(3, int((r - 860) / 100))]
            b.face([ring[ia][jr], ring[ia][jr + 1], ring[ib][jr + 1], ring[ib][jr]], mi, smooth=True)

    # ---------------- 梯田（同心圓角矩形層層下降）
    for k in range(N_TERR, 0, -1):
        d = k * STEP_W
        z = -STEP_H * k
        pts = rrect(CA + d, CB + d, CR + d, z, n_arc=8)
        jit = [(x + 0.6 * _n(x, y, 20.0, k), y + 0.6 * _n(x, y, 20.0, k + 50), zz) for x, y, zz in pts]
        b.slab(jit, z - 9.0, z, wall_d if k % 3 == 0 else wall, grass)
    # 城區頂台（z=0）
    b.slab(rrect(CA, CB, CR, 0.0, n_arc=8), -9.0, 0.0, wall, grass)

    # ---------------- 城內：中央大廣場、西側神殿區、東側住居區、南側農業梯田
    b.block(lawn, -20, 22, 0, 120, -0.3, 0.05)                    # 大廣場（草坪）
    # 西側神殿區：兩層台
    b.block(wall, -80, -24, -40, 165, -1.0, 3.0, top=grass)
    b.block(wall, -78, -34, 15, 150, 2.0, 6.0, top=grass)
    # 拴日石小丘（Intihuatana）：小階台堆疊
    for k in range(6):
        s = 16 - k * 2.4
        b.block(wall, -52 - s, -52 + s, 172 - s * 0.8, 172 + s * 0.8, -1.0 + 3.0 * k, 3.0 + 3.0 * k, top=grass)
    b.block(rock_s, -53.0, -51.0, 171.0, 173.0, 18.0, 19.8)
    # 東側住居區：向東、向北逐階下降
    for ix, (xa, xb) in enumerate(((26, 44), (44, 62), (62, 80))):
        for iy, (ya, yb) in enumerate(((-60, -10), (-10, 40), (40, 90), (90, 140), (140, 185))):
            zt = 5.0 - 1.4 * ix - 0.6 * iy
            b.block(wall, xa, xb, ya, yb, -1.0, zt, top=grass)
    # 南側城內農業梯田（向南升高）
    for j in range(4):
        yb = -55 - 18 * j
        b.block(wall if j % 2 else wall_d, -62 + 3 * j, 62 - 3 * j, -150, yb, -1.0, 1.1 * (j + 1), top=grass)

    # ---------------- 石屋（無頂、兩端山牆三角）
    def top_z(x, y):
        if -80 < x < -24 and -40 < y < 165:
            return 6.0 if (-78 < x < -34 and 15 < y < 150) else 3.0
        if 26 < x < 80 and -60 < y < 185:
            ix = min(2, int((x - 26) // 18))
            iy = min(4, int((y + 60) // 50))
            return 5.0 - 1.4 * ix - 0.6 * iy
        return 0.0

    occupied = []

    def house(x, y, w, d, rot90=False, roof=False):
        if any(abs(x - ox) < (w + ow) / 2 + 1.0 and abs(y - oy) < (d + od) / 2 + 1.0 for ox, oy, ow, od in occupied):
            return False
        z0 = top_z(x, y) - 0.3
        hw = rng.uniform(2.6, 3.4)
        t = 0.6
        mi = wall if rng.random() < 0.75 else wall_d
        W, D = (d, w) if rot90 else (w, d)   # 世界座標寬（x）、深（y）
        occupied.append((x, y, W, D))
        gx = not rot90   # 山牆在 x 兩端（長軸沿 x）
        # 四面牆
        b.block(mi, x - W / 2, x + W / 2, y - D / 2, y - D / 2 + t, z0, z0 + hw)
        b.block(mi, x - W / 2, x + W / 2, y + D / 2 - t, y + D / 2, z0, z0 + hw)
        b.block(mi, x - W / 2, x - W / 2 + t, y - D / 2 + t, y + D / 2 - t, z0, z0 + hw)
        b.block(mi, x + W / 2 - t, x + W / 2, y - D / 2 + t, y + D / 2 - t, z0, z0 + hw)
        gh = (D if gx else W) * 0.45
        for s in (-1, 1):
            if gx:
                b.tri_prism(mi, t, D, gh, (x + s * (W / 2 - t / 2), y, z0 + hw))
            else:
                b.tri_prism(mi, t, W, gh, (x, y + s * (D / 2 - t / 2), z0 + hw), rot_z=math.pi / 2)
        # 門洞（暗面貼在長牆外側）
        if gx:
            b.block(shadow, x - 0.5, x + 0.5, y - D / 2 - 0.03, y - D / 2 + 0.02, z0 + 0.3, z0 + 2.0)
        else:
            b.block(shadow, x - W / 2 - 0.03, x - W / 2 + 0.02, y - 0.5, y + 0.5, z0 + 0.3, z0 + 2.0)
        if roof:
            if gx:
                b.tri_prism(thatch, D + 1.2, W + 0.8, gh + 0.5, (x, y, z0 + hw - 0.2), rot_z=math.pi / 2)
            else:
                b.tri_prism(thatch, W + 1.2, D + 0.8, gh + 0.5, (x, y, z0 + hw - 0.2))
        return True

    # 東側住居區：成排密集
    for gy in range(-55, 182, 8):
        for gx in range(29, 80, 10):
            if rng.random() < 0.85:
                house(gx + rng.uniform(-0.8, 0.8), gy + rng.uniform(-0.6, 0.6), rng.uniform(6.5, 9.0), rng.uniform(4.2, 5.4),
                      rot90=rng.random() < 0.25)
    # 西側神殿區
    for gy in range(-35, 162, 9):
        for gx in range(-76, -26, 11):
            if rng.random() < 0.7 and not (-60 < gx < -40 and 160 < gy):
                house(gx + rng.uniform(-1, 1), gy + rng.uniform(-1, 1), rng.uniform(7.0, 10.5), rng.uniform(4.5, 6.0),
                      rot90=rng.random() < 0.3)
    # 廣場南北兩端與南區
    for gx in range(-16, 22, 9):
        for gy in (-30, -18, 130, 141):
            if rng.random() < 0.8:
                house(gx + rng.uniform(-1, 1), gy + rng.uniform(-1, 1), rng.uniform(6.5, 8.5), rng.uniform(4.3, 5.2))
    # 守衛屋與梯田上的茅頂小屋（復原屋頂）
    house(30.0, -150.0, 7.0, 4.8, roof=True)
    house(-40.0, -100.0, 6.5, 4.5, roof=True)
    # 採石場散石（城中央南側）
    for _ in range(26):
        x, y = rng.uniform(-18, 20), rng.uniform(-14, -2)
        s = rng.uniform(0.8, 2.2)
        b.rock(rock_s, (s * 1.4, s, s * 0.7), (x, y, -0.3), rot=(0, 0, rng.uniform(0, TAU)), seed=rng.randint(0, 99), round_=0.4)

    b.export_glb(path)
