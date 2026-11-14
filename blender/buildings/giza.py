"""giza 寫實模型（尺寸依實測資料，公尺）

座標：以古夫金字塔中心為原點，+X 東、+Y 北（依經緯度換算）。
- 古夫：底 230.3 m、原高 146.6 m、現高 138.5 m
- 卡夫拉：底 215.3 m、原高 143.5 m、現高 136.4 m，頂端保留原始石灰岩外殼，地勢高約 10 m
- 孟卡拉：底 102.2 × 104.6 m、原高 65.5 m、現高 61 m
- 獅身人面像：長 73 m、寬 19 m、高 20 m，面向正東，位於鑿出的圍坑中
"""

import math

from mathutils import Vector, noise

from lib import TAU, Builder

# ---------------------------------------------------------------------- 共用：頂點色（風化色差）


class Painter:
    """在 bmesh 上以頂點色（每個面角）做色差；材質以 Multiply 混入貼圖，glTF 輸出為 COLOR_0"""

    def __init__(self, b):
        self.b = b
        self.cl = b.bm.loops.layers.color.new("Col")
        self.mark = b.bm.faces.layers.int.new("painted")

    def faces_of(self, verts):
        return {f for v in verts for f in v.link_faces}

    def paint(self, faces, fn):
        """fn(face, vert_co) -> (r, g, b)"""
        cl, mk = self.cl, self.mark
        for f in faces:
            f[mk] = 1
            for l in f.loops:
                c = fn(f, l.vert.co)
                l[cl] = (min(1.0, max(0.0, c[0])), min(1.0, max(0.0, c[1])), min(1.0, max(0.0, c[2])), 1.0)

    def pv(self, verts, fn):
        self.paint(self.faces_of(verts), fn)

    def finish(self):
        cl, mk = self.cl, self.mark
        for f in self.b.bm.faces:
            if not f[mk]:
                for l in f.loops:
                    l[cl] = (1.0, 1.0, 1.0, 1.0)
        self.b.bm.faces.layers.int.remove(mk)
        for m in self.b.mats:
            nt = m.node_tree
            bsdf = nt.nodes["Principled BSDF"]
            links = bsdf.inputs["Base Color"].links
            vc = nt.nodes.new("ShaderNodeVertexColor")
            vc.layer_name = "Col"
            if links:
                src = links[0].from_socket
                mix = nt.nodes.new("ShaderNodeMix")
                mix.data_type = "RGBA"
                mix.blend_type = "MULTIPLY"
                mix.inputs["Factor"].default_value = 1.0
                nt.links.new(src, mix.inputs[6])
                nt.links.new(vc.outputs["Color"], mix.inputs[7])
                nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
            else:
                nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])


def n2(x, y, s, seed=0.0):
    return noise.noise(Vector((x * s + seed, y * s - seed * 0.7, seed * 0.31)))


def fbm(x, y, s, octaves=4, seed=0.0):
    t, a, f = 0.0, 1.0, s
    for i in range(octaves):
        t += a * n2(x, y, f, seed + i * 17.3)
        a *= 0.5
        f *= 2.03
    return t


def smooth(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------- 主體
def giza(path):
    b = Builder("Giza", seed=3)
    P = Painter(b)
    sand = b.tex("sand", "sand_01", tile=23.0, tint="#efcd93", normal=0)
    stone = b.tex("stone", "rock_04", tile=3.0, tint="#d9c39c", normal=1.4)
    rockm = stone  # 岩盤與露頭共用同一貼圖，以頂點色區分（減少 GLB 大小）
    side = b.color("soil_side", "#b08e5e", rough=0.95)
    granite = b.color("granite", "#6e5a52", rough=0.6)
    rng = b.rng

    # ------------------------------------------------------------ 地形高度
    KH = (0.0, 0.0, 230.3, 230.3)
    KF = (-328.0, -344.0, 215.3, 215.3)
    MK = (-569.0, -743.0, 102.2, 104.6)
    SPH = (330.0, -432.0)

    def trend(x, y):
        # 高原往東南緩降，東側為下降到尼羅河谷的崖坡
        return -0.017 * (x + 0.35 * y) - 14.0 * smooth(250, 520, x) - 4.0 * smooth(-900, -1300, y)

    pads = []  # (cx, cy, hx, hy, z, ramp)

    def pad(cx, cy, hx, hy, ramp=70.0):
        z = trend(cx, cy)
        pads.append((cx, cy, hx, hy, z, ramp))
        return z

    zKH = pad(KH[0], KH[1], 130, 130, 90)
    zKF = pad(KF[0], KF[1], 122, 122, 90) + 3.0
    pads[-1] = (*pads[-1][:4], zKF, 90)
    zMK = pad(MK[0], MK[1], 62, 64, 70)

    sx, sy = SPH
    floor_z = trend(sx, sy) - 8.5  # 獅身像圍坑地面

    def hollow(x, y):
        """獅身像圍坑（硬邊，由岩壁遮住過渡）與東側神廟低地"""
        lx, ly = x - sx, y - sy
        if -55 < lx < 46 and -26 < ly < 26:
            return True
        return False

    def mound(x, y):
        # 金字塔底部的碎石與沙堆
        t = 0.0
        for cx, cy, w, d, h in ((KH[0], KH[1], 115.2, 115.2, 4.5), (KF[0], KF[1], 107.7, 107.7, 4.0), (MK[0], MK[1], 51.1, 52.3, 3.5)):
            e = max(abs(x - cx) - w, abs(y - cy) - d)
            if -10 < e < 45:
                t += h * math.exp(-((e - 6) / 11.0) ** 2)
        return t

    def height(x, y):
        z = trend(x, y)
        # 沙丘與岩質起伏（遠離遺址處較明顯）
        dunes = 7.0 * fbm(x, y, 0.0028, 3, 1.1) + 2.2 * abs(fbm(x, y, 0.009, 2, 4.2)) + 0.8 * n2(x, y, 0.03, 6.0) + 0.3 * n2(x, y, 0.07, 8.0)
        w = 1.0
        for cx, cy, hx, hy, pz, ramp in pads:
            e = max(abs(x - cx) - hx, abs(y - cy) - hy)
            k = smooth(0, ramp, e)
            z = z * k + pz * (1 - k) if e < ramp else z
            w = min(w, smooth(0, ramp * 2.2, e))
        # 獅身像周圍：坑內地面、東側神廟區低地
        lx, ly = x - sx, y - sy
        if hollow(x, y):
            return floor_z
        east = smooth(70, 30, abs(ly + 15)) * smooth(30, 50, lx) * smooth(230, 130, lx)
        z = z * (1 - east) + (floor_z + 0.3) * east
        w = min(w, 1 - east)
        dw = min(1.0, max(0.0, (math.hypot(lx, ly) - 70) / 120))
        w = min(w, dw)
        return z + dunes * (0.25 + 0.75 * w) + mound(x, y)

    # ------------------------------------------------------------ 地形網格（核心區 10 m 格，外圍漸疏；裁成圓盤）
    CX, CY, RAD = -170.0, -380.0, 1250.0

    def axis(c0, c1, lo, hi, step=10.0):
        xs = [c0 + i * step for i in range(int((c1 - c0) / step) + 1)]
        s = step
        x = xs[-1]
        while x < hi:
            s *= 1.22
            x += s
            xs.append(x)
        s, x, pre = step, xs[0], []
        while x > lo:
            s *= 1.22
            x -= s
            pre.append(x)
        return list(reversed(pre)) + xs

    gx = axis(-720.0, 480.0, CX - RAD - 10, CX + RAD + 10, 12.0)
    gy = axis(-960.0, 180.0, CY - RAD - 10, CY + RAD + 10, 12.0)
    grid = {}
    for i, x in enumerate(gx):
        for j, y in enumerate(gy):
            d = math.hypot(x - CX, y - CY)
            grid[(i, j)] = (x, y, d)
    vmap = {}

    def gv(i, j):
        if (i, j) not in vmap:
            x, y, d = grid[(i, j)]
            if d > RAD:
                x, y = CX + (x - CX) * RAD / d, CY + (y - CY) * RAD / d
            vmap[(i, j)] = b.bm.verts.new((x, y, height(x, y)))
        return vmap[(i, j)]

    tfaces = []
    for i in range(len(gx) - 1):
        for j in range(len(gy) - 1):
            ds = [grid[(i, j)][2], grid[(i + 1, j)][2], grid[(i + 1, j + 1)][2], grid[(i, j + 1)][2]]
            if min(ds) > RAD:
                continue
            vs = [gv(i, j), gv(i + 1, j), gv(i + 1, j + 1), gv(i, j + 1)]
            if (vs[0].co - vs[2].co).length < 0.5 or (vs[1].co - vs[3].co).length < 0.5:
                continue
            try:
                f = b.bm.faces.new(vs)
            except ValueError:
                continue
            f.material_index = sand
            f.smooth = True
            tfaces.append(f)
    tset = set(tfaces)
    edge_faces = []
    for f in tfaces:
        for e in f.edges:
            if sum(1 for lf in e.link_faces if lf in tset) == 1:
                v1, v2 = e.verts
                b1 = b.bm.verts.new((v1.co.x, v1.co.y, -60))
                b2 = b.bm.verts.new((v2.co.x, v2.co.y, -60))
                sf = b.bm.faces.new([v1, v2, b2, b1])
                sf.material_index = side
                edge_faces.append(sf)

    def sand_col(f, co):
        x, y = co.x, co.y
        a = fbm(x, y, 0.004, 3, 2.0)
        r = 0.88 + 0.08 * a + 0.04 * n2(x, y, 0.05, 3.0)
        # 碎石／岩盤露頭的較暗灰褐斑塊
        g = max(0.0, fbm(x, y, 0.008, 3, 9.0) - 0.15)
        near = 0.0
        for cx, cy, w, d, _ in ((KH[0], KH[1], 115, 115, 0), (KF[0], KF[1], 108, 108, 0), (MK[0], MK[1], 52, 53, 0)):
            e = max(abs(x - cx) - w, abs(y - cy) - d)
            near = max(near, math.exp(-max(0.0, e) / 25.0))
        dark = min(0.35, g * 0.6 + near * 0.18)
        return (r * (1 - dark * 0.8), r * (0.985 - dark * 0.95), r * (0.92 - dark * 1.0))

    P.paint(tfaces, sand_col)
    P.paint(edge_faces, lambda f, co: (1, 1, 1))

    # ------------------------------------------------------------ 逐層石階金字塔
    def step_pyramid(cx, cy, z0, bx, by, H, H_now, course, seg, amp, seed, casing_from=None, inset=0.8,
                     tone=(1.0, 0.96, 0.9), base_dark=None):
        hx0, hy0 = bx / 2, by / 2
        slope_x, slope_y = hx0 / H, hy0 / H
        zs = [-3.0]
        z = 0.0
        while z < H_now - 0.3:
            zs.append(z)
            z += course * rng.uniform(0.75, 1.25)
        zs.append(H_now)
        top_z = H_now
        if casing_from is not None:
            zs = [zz for zz in zs if zz < casing_from + 6] + [casing_from + 6]
        n = len(zs)
        # 周長取樣（四邊各 seg 段），記錄外法線
        per = []
        for s in range(4):
            for j in range(seg):
                t = 0.5 - 0.5 * math.cos(math.pi * j / seg)  # 角落附近取樣較密（稜線崩缺）
                per.append((s, t))

        def base_pt(s, t, hx, hy):
            corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
            a, c = corners[s], corners[(s + 1) % 4]
            return a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t

        normals = [(0, -1), (1, 0), (0, 1), (-1, 0)]
        sideL = [bx, by, bx, by]

        def erosion(k, s, t):
            z = zs[k]
            px, py = base_pt(s, t, hx0, hy0)
            e = amp * (0.55 + 0.45 * fbm(px, py + z * 2.0, 0.035, 2, seed))
            e += amp * 0.9 * max(0.0, fbm(px * 0.7, z, 0.06, 2, seed + 5)) ** 2 * 3
            dc = min(t, 1 - t) * sideL[s]
            e += amp * 3.2 * max(0.0, 1 - dc / 14.0) ** 1.5 * (0.5 + 0.9 * rng.random())
            return e

        tread = course / max(slope_x, 1e-3) * slope_x * 0 + course * slope_x  # 每層退縮量
        D = [[0.0] * len(per) for _ in range(n)]
        for k in range(n - 1, -1, -1):
            for q, (s, t) in enumerate(per):
                d = erosion(k, s, t) + rng.uniform(0, 0.7) * tread + (tread * rng.uniform(0.8, 2.0) if rng.random() < 0.07 else 0)
                if k < n - 1:
                    d = min(d, D[k + 1][q] + tread * 0.92)
                if k == 0:
                    d = min(d, 0.6)
                D[k][q] = d

        rings = []
        for k in range(n):
            z = zs[k]
            hx = hx0 - slope_x * max(z, 0) - inset
            hy = hy0 - slope_y * max(z, 0) - inset
            if z < 0:
                hx, hy = hx0 - inset + 0.3, hy0 - inset + 0.3
            A, B = [], []
            ztop = zs[k + 1] if k < n - 1 else z
            for q, (s, t) in enumerate(per):
                px, py = base_pt(s, t, hx, hy)
                d = D[k][q]
                nx, ny = normals[s]
                if t == 0:  # 角點：沿對角線內收
                    pnx, pny = normals[(s - 1) % 4]
                    px -= (nx + pnx) * d * 0.75
                    py -= (ny + pny) * d * 0.75
                else:
                    px -= nx * d
                    py -= ny * d
                A.append(Vector((cx + px, cy + py, z0 + z)))
                B.append(Vector((cx + px, cy + py, z0 + ztop)))
            rings.append((A, B))
        allf = []
        vrings = []
        for k, (A, B) in enumerate(rings):
            va = [b.bm.verts.new(p) for p in A]
            vb = [b.bm.verts.new(p) for p in B] if k < n - 1 else None
            vrings.append((va, vb))
        m = len(per)
        course_tone = [rng.uniform(0.86, 1.0) for _ in range(n)]
        riser, treadf = [], []
        for k in range(n - 1):
            va, vb = vrings[k]
            vn = vrings[k + 1][0]
            for q in range(m):
                r = (q + 1) % m
                f = b.bm.faces.new([va[q], va[r], vb[r], vb[q]])
                f.material_index = stone
                riser.append((f, k))
                f = b.bm.faces.new([vb[q], vb[r], vn[r], vn[q]])
                f.material_index = stone
                treadf.append((f, k))
        cap = b.bm.faces.new(vrings[-1][0])
        cap.material_index = stone
        treadf.append((cap, n - 1))

        def col(k, co, top):
            x, y, z = co.x - cx, co.y - cy, co.z - z0
            blot = fbm(x + z * 0.5, y - z * 0.3, 0.025, 3, seed + 2)
            v = course_tone[k] * (0.9 + 0.1 * blot) * (0.94 + 0.06 * n2(x, z, 0.3, seed))
            grey = max(0.0, fbm(x, z, 0.012, 2, seed + 9)) * 0.25
            r, g, bb = tone
            r, g, bb = r * v, g * v, bb * v
            r, g, bb = r * (1 - grey) + v * 0.92 * grey, g * (1 - grey) + v * 0.9 * grey, bb * (1 - grey) + v * 0.88 * grey
            if top:  # 階面積沙、較亮偏黃
                r, g, bb = r * 1.04, g * 1.0, bb * 0.92
            if base_dark and z < base_dark[0]:
                c = base_dark[1]
                kk = 1 - z / base_dark[0]
                r, g, bb = r * (1 - kk) + c[0] * kk, g * (1 - kk) + c[1] * kk, bb * (1 - kk) + c[2] * kk
            return (r, g, bb)

        ring_of = {}
        for k, (va, vb) in enumerate(vrings):
            for v in va:
                ring_of[v] = 0
            for v in vb or []:
                ring_of[v] = 1
        cl, mk = P.cl, P.mark
        vr = {v: rng.uniform(0.8, 1.08) for v in ring_of}
        # 每層石階：豎面下緣（接縫陰影）較暗、階面內側積塵較暗
        for faces, top in ((riser, False), (treadf, True)):
            for f, k in faces:
                f[mk] = 1
                for l in f.loops:
                    r, g, bb = col(k, l.vert.co, top)
                    if top:
                        fac = 0.8 if ring_of.get(l.vert) == 0 and k < n - 1 else 1.0
                    else:
                        fac = 0.68 if ring_of.get(l.vert) == 0 else 1.0
                    fac *= vr.get(l.vert, 1.0)
                    l[cl] = (min(1, r * fac), min(1, g * fac), min(1, bb * fac), 1.0)

        # 卡夫拉頂部原始外殼（平滑、偏亮），下緣不規則
        if casing_from is not None:
            V = 10
            zl = [casing_from + 5.0 * fbm(s * 9.0 + t * 9.0, 0, 0.9, 2, seed + 3) + 2.0 * math.sin(t * TAU * 2 + s) + rng.uniform(-1.2, 1.2) for s, t in per]
            ztop = H_now
            cring = []
            for vv in range(V + 1):
                ring = []
                for q, (s, t) in enumerate(per):
                    z = zl[q] + (ztop - zl[q]) * vv / V
                    hx, hy = hx0 - slope_x * z, hy0 - slope_y * z
                    px, py = base_pt(s, t, hx, hy)
                    ring.append(b.bm.verts.new((cx + px, cy + py, z0 + z)))
                cring.append(ring)
            cf = []
            for vv in range(V):
                for q in range(m):
                    r = (q + 1) % m
                    cf.append(b.bm.faces.new([cring[vv][q], cring[vv][r], cring[vv + 1][r], cring[vv + 1][q]]))
            cf.append(b.bm.faces.new(cring[-1]))
            # 外殼下緣的厚度（往內收到核心石階）
            lip = []
            for q, (s, t) in enumerate(per):
                z = zl[q]
                hx, hy = hx0 - slope_x * z - inset - 1.0, hy0 - slope_y * z - inset - 1.0
                px, py = base_pt(s, t, hx, hy)
                lip.append(b.bm.verts.new((cx + px, cy + py, z0 + z)))
            for q in range(m):
                r = (q + 1) % m
                cf.append(b.bm.faces.new([lip[q], lip[r], cring[0][r], cring[0][q]]))
            for f in cf:
                f.material_index = stone

            def ccol(f, co):
                x, y, z = co.x - cx, co.y - cy, co.z - z0
                v = 0.92 + 0.05 * fbm(x, z, 0.08, 2, 4)
                streak = 0.1 * max(0.0, fbm(x * 0.2 + y * 0.2, z * 0.02, 0.15, 2, 7))
                return (v * (0.97 - streak), v * (0.93 - streak), v * (0.85 - streak * 1.2))

            P.paint(cf, ccol)

    # 古夫（外殼全失，露出逐層石階；頂部約 10 m 平台）
    step_pyramid(KH[0], KH[1], zKH, KH[2], KH[3], 146.6, 138.5, 1.4, 12, 1.0, 1.0, tone=(0.95, 0.86, 0.72))
    # 卡夫拉（底座為削平岩盤，頂部保留外殼）
    step_pyramid(KF[0], KF[1], zKF, KF[2], KF[3], 143.5, 136.4, 1.35, 12, 0.9, 2.0, casing_from=98.0, inset=1.2,
                 tone=(0.92, 0.86, 0.76))
    # 孟卡拉（底部殘留紅色花崗岩外殼）
    step_pyramid(MK[0], MK[1], zMK, MK[2], MK[3], 65.5, 61.0, 1.1, 10, 0.9, 3.0, tone=(0.95, 0.83, 0.66),
                 base_dark=(9.0, (0.62, 0.5, 0.45)))

    # 古夫的三座王后金字塔（G1-a/b/c，東側由北而南，已嚴重崩毀）
    for k, (qx, qy, qb, qh, now) in enumerate([(168, -12, 49.5, 30.2, 19.0), (163, -64, 49.0, 30.0, 17.5), (158, -113, 46.3, 29.6, 21.5)]):
        z = trend(qx, qy)
        step_pyramid(qx, qy, z, qb, qb, qh, now, 1.4, 6, 1.4, 10.0 + k, tone=(0.93, 0.86, 0.75))
    # 孟卡拉的三座王后金字塔（G3-a 為真金字塔，G3-b/c 為四層階梯）
    z = trend(-522, -846)
    step_pyramid(-522, -846, z, 44.3, 44.3, 28.4, 21.5, 1.2, 6, 1.3, 20.0, tone=(0.92, 0.84, 0.72))
    for k, qx in enumerate((-580, -636)):
        qy, base = -846, 33.0
        z = trend(qx, qy)
        tiers = 4
        zt = z
        for t_ in range(tiers - (1 if k == 0 else 0)):
            w = base - t_ * 7.6 - rng.uniform(0, 1.5)
            h = 4.4 if t_ else 4.4 + 0.0
            # 每層為近乎垂直、略內傾的粗石牆（以石階金字塔函式做出塊石粗糙感）
            step_pyramid(qx, qy, zt, w, w * 0.96, h * 7.0, h, 0.75, 6, 1.1, 30.0 + k * 4 + t_, inset=0.0,
                         tone=(0.88 - 0.02 * t_, 0.8 - 0.02 * t_, 0.68 - 0.02 * t_))
            zt += h

    # ------------------------------------------------------------ 馬斯塔巴墓群（南北向長方、外牆內傾）
    def mastaba(x, y, w, d, h):
        z = height(x, y) - 1.2
        vs = b.frustum(stone, (w, d), (w - h * 0.45, d - h * 0.45), h + 1.2, (x, y, z), rot_z=rng.uniform(-0.01, 0.01))
        tone = rng.uniform(0.8, 0.95)
        P.pv(vs, lambda f, co: (tone * (0.98 + 0.03 * n2(co.x, co.z, 0.5)), tone * 0.9, tone * 0.78))

    for gx0, gy0, ni, nj in ((-175, -40, 7, 9), (205, -130, 4, 7)):
        for i in range(ni):
            for j in range(nj):
                if rng.random() < 0.22:
                    continue
                x = gx0 - i * 34 if gx0 < 0 else gx0 + i * 30
                y = gy0 + j * 30 + rng.uniform(-3, 3)
                mastaba(x, y, rng.uniform(9, 13), rng.uniform(18, 26), rng.uniform(2.5, 6.5))

    # ------------------------------------------------------------ 神廟、參道
    def ruin(x, y, w, d, h, rot=0.0):
        z = height(x, y) - 1.0
        vs = b.box_base(stone, (w, d, h + 1.0), (x, y, z), rot=(0, 0, rot))
        P.pv(vs, lambda f, co: (0.86, 0.79, 0.68))

    # 卡夫拉祭廟（東側）
    for dx, dy, w, d, h in ((0, 0, 50, 56, 4.5), (-38, 0, 20, 70, 6), (34, 0, 18, 30, 5)):
        ruin(KF[0] + 107.7 + 32 + dx, KF[1] + dy, w, d, h)
    # 孟卡拉祭廟
    ruin(MK[0] + 51 + 30, MK[1], 40, 48, 3.5)
    # 卡夫拉參道：祭廟 → 河谷神廟（沿地形分段）
    p0 = Vector((KF[0] + 107.7 + 58, KF[1] - 6))
    p1 = Vector((sx + 52, sy - 52))
    N = 40
    for i in range(N):
        a = p0.lerp(p1, i / N)
        c = p0.lerp(p1, (i + 1) / N)
        mid = (a + c) / 2
        L = (c - a).length + 0.4
        ang = math.atan2(c.y - a.y, c.x - a.x)
        z = min(height(a.x, a.y), height(c.x, c.y)) - 1.0
        vs = b.box_base(stone, (L, 6.0, 2.4), (mid.x, mid.y, z), rot=(0, 0, ang))
        P.pv(vs, lambda f, co: (0.88, 0.81, 0.7))
    # 河谷神廟與獅身像神廟（巨大石灰岩塊、花崗岩柱廳）
    ruin(sx + 58, sy - 50, 45, 45, 10.5)
    ruin(sx + 55, sy + 8, 46, 40, 6.5)
    b.box_base(granite, (20, 12, 0.6), (sx + 58, sy - 50, floor_z + 10.5 - 0.5))

    # ------------------------------------------------------------ 獅身人面像
    build_sphinx(b, P, stone, rockm, sx, sy, floor_z, height)

    # ------------------------------------------------------------ 碎石、岩塊
    def debris(x, y, size, mi=stone, tone=(0.85, 0.78, 0.66), subdiv=1):
        """低面數碎石：抖動的二十面體"""
        z = height(x, y)
        sc = (size * rng.uniform(0.8, 1.4), size * rng.uniform(0.8, 1.3), size * rng.uniform(0.4, 0.75))
        vs = b.ico(mi, 0.5, (x, y, z + sc[2] * 0.15), subdiv=1, scale=sc, smooth=False)
        for v in vs:
            v.co.x += rng.uniform(-0.18, 0.18) * sc[0]
            v.co.y += rng.uniform(-0.18, 0.18) * sc[1]
            v.co.z += rng.uniform(-0.12, 0.12) * sc[2]
        t = rng.uniform(0.85, 1.05)
        P.pv(vs, lambda f, co: (tone[0] * t, tone[1] * t, tone[2] * t))

    # 金字塔腳下散落的石塊
    for cx, cy, w, d, cnt in ((KH[0], KH[1], 115.2, 115.2, 170), (KF[0], KF[1], 107.7, 107.7, 150), (MK[0], MK[1], 51.1, 52.3, 110)):
        for _ in range(cnt):
            s = rng.randrange(4)
            t = rng.uniform(-1.05, 1.05)
            off = rng.uniform(0, 1) ** 2 * 30 + 1
            if s == 0:
                x, y = cx + t * w, cy - d - off
            elif s == 1:
                x, y = cx + w + off, cy + t * d
            elif s == 2:
                x, y = cx + t * w, cy + d + off
            else:
                x, y = cx - w - off, cy + t * d
            debris(x, y, rng.uniform(0.6, 2.2) * (1.6 if off < 6 else 1.0))
    # 沙漠中散布的碎石與露頭（近南側，參考照前景）
    for _ in range(650):
        a = rng.uniform(0, TAU)
        r = math.sqrt(rng.uniform(0, 1)) * RAD * 0.95
        x, y = CX + r * math.cos(a), CY + r * math.sin(a)
        if any(max(abs(x - cx) - hx - 6, abs(y - cy) - hy - 6) < 0 for cx, cy, hx, hy, _, _ in pads):
            continue
        if abs(x - sx) < 110 and abs(y - sy) < 90:
            continue
        debris(x, y, rng.uniform(0.4, 1.6), tone=(0.82, 0.74, 0.62), subdiv=1)
    # 低矮岩脊（灰褐石灰岩露頭）
    for _ in range(26):
        a = rng.uniform(0, TAU)
        r = rng.uniform(380, 1150)
        x, y = CX + r * math.cos(a), CY + r * math.sin(a)
        if any(max(abs(x - cx) - hx - 25, abs(y - cy) - hy - 25) < 0 for cx, cy, hx, hy, _, _ in pads):
            continue
        if abs(x - sx) < 140 and abs(y - sy) < 120:
            continue
        L = rng.uniform(25, 80)
        z = height(x, y)
        vs = b.rock(rockm, (L, L * rng.uniform(0.2, 0.4), rng.uniform(3, 6)), (x, y, z - 1.5), rot=(0, 0, rng.uniform(0, TAU)),
                    rough=0.55, subdiv=2, seed=rng.randint(0, 9999), round_=0.1)
        P.pv(vs, lambda f, co: (0.74 + 0.08 * n2(co.x, co.y, 0.2), 0.64 + 0.07 * n2(co.x, co.y, 0.2), 0.5))

    P.finish()
    b.export(path)


# ---------------------------------------------------------------------- 獅身人面像
def loft(b, mi, sections, cap_start=True, cap_end=True):
    """以等點數的封閉截面依序相連；回傳頂點"""
    vr = [[b.bm.verts.new(p) for p in sec] for sec in sections]
    n = len(sections[0])
    faces = []
    for a, c in zip(vr, vr[1:]):
        for i in range(n):
            j = (i + 1) % n
            faces.append(b.bm.faces.new([a[i], a[j], c[j], c[i]]))
    if cap_start:
        faces.append(b.bm.faces.new(list(reversed(vr[0]))))
    if cap_end:
        faces.append(b.bm.faces.new(vr[-1]))
    for f in faces:
        f.material_index = mi
        f.smooth = True
    return [v for r in vr for v in r], faces


def build_sphinx(b, P, stone, rockm, sx, sy, fz, height):
    """面向 +X（東）。局部座標：x 前後、y 左右、z 自坑底起算"""
    rng = b.rng

    def W(x, y, z):
        return Vector((sx + x, sy + y, fz + z))

    def section(x, hw, h, n=20, bottom=-1.0, squ=2.6):
        """圓角矩形（超橢圓）截面，底部埋入地面"""
        pts = []
        for i in range(n):
            a = TAU * i / n
            c, s = math.cos(a), math.sin(a)
            yy = hw * math.copysign(abs(c) ** (2 / squ), c)
            zz = (h / 2) * math.copysign(abs(s) ** (2 / squ), s) + h / 2
            zz = max(zz, bottom)
            pts.append((x, yy, zz))
        return pts

    def erode(co_local):
        x, y, z = co_local
        # 水平風化層紋：較軟岩層被侵蝕成凹槽
        g = 0.28 * (0.5 + 0.5 * math.sin(z * TAU / 1.7 + 1.5 * noise.noise(Vector((x * 0.08, y * 0.08, z * 0.1)))))
        g += 0.12 * noise.noise(Vector((x * 0.4, y * 0.4, z * 0.4)))
        return g

    # 身體（臀 → 胸），長約 56 m
    prof = [(-46, 4.5, 6.0), (-44, 7.2, 9.0), (-40, 8.6, 11.0), (-34, 9.3, 12.0), (-27, 9.0, 11.6), (-18, 8.4, 11.2),
            (-8, 8.4, 11.6), (0, 8.9, 12.4), (5, 9.2, 13.0), (9, 8.8, 13.2), (11, 7.6, 12.6), (12, 5.5, 11.0)]
    secs = []
    for x, hw, h in prof:
        sec = []
        for (px, py, pz) in section(x, hw, h):
            r = erode((px, py, pz))
            k = 1 - r / max(hw, 1.0)
            sec.append(W(px, py * k, pz - (r * 0.5 if pz > h * 0.8 else 0)))
        secs.append(sec)
    vs, fs = loft(b, stone, secs)

    def body_col(f, co):
        z = co.z - fz
        n = noise.noise(Vector(((co.x - sx) * 0.2, (co.y - sy) * 0.2, z * 0.3)))
        band = 0.06 * math.sin(z * TAU / 1.7)
        if z < 3.0:  # 下段的後世修補石塊，較淺黃
            return (0.98 + 0.02 * n, 0.9 + 0.03 * n, 0.74)
        v = 0.9 + 0.05 * n + band
        return (v * 1.0, v * 0.82, v * 0.62)

    P.paint(fs, body_col)
    # 尾巴（沿右臀側盤繞）
    tail = []
    for i in range(10):
        t = i / 9
        tail.append((-44 + t * 10, -8.2 - 0.6 * math.sin(t * math.pi), 0.8 + 0.3 * t))
    for i in range(9):
        a, c = Vector(tail[i]), Vector(tail[i + 1])
        vs = b.cyl(stone, 0.55, 0.5, (c - a).length, tuple(W(*a)), seg=8, rot=(0, math.pi / 2, math.atan2(c.y - a.y, c.x - a.x)))
        P.pv(vs, body_col)

    # 前爪（長約 15 m），兩爪間為圖特摩斯四世的夢境石碑
    for side in (-1, 1):
        cy = side * 4.6
        secs = []
        for x, hw, h in ((9, 2.0, 3.6), (14, 1.9, 2.9), (20, 1.8, 2.5), (25, 1.8, 2.3), (27.0, 1.5, 2.0), (27.8, 0.9, 1.4)):
            secs.append([W(px, py + cy, pz) for (px, py, pz) in section(x, hw, h, n=14, squ=3.0)])
        vs, fs = loft(b, stone, secs)
        P.paint(fs, lambda f, co: (0.97, 0.88, 0.72))
        # 腳趾
        for k in range(4):
            vs = b.rock(stone, (1.4, 0.8, 0.9), tuple(W(27.6, cy + (k - 1.5) * 0.85, 0.45)), rough=0.05, subdiv=1, seed=k + 40 + side)
            P.pv(vs, lambda f, co: (0.95, 0.86, 0.7))
    vs = b.box_base(b.color("stela", "#5e504c", rough=0.5), (0.7, 4.0, 3.6), tuple(W(11.8, 0, 0)))
    # 頸
    neck = [section(x, hw, h) for x, hw, h in ((4, 4.0, 15.0), (8, 3.8, 15.5), (10.5, 3.4, 15.0))]
    vs, fs = loft(b, stone, [[W(*p) for p in s] for s in neck])
    P.paint(fs, body_col)

    # 頭巾（nemes）：以水平截面堆疊，下段兩側垂片張開至肩
    def nemes_sec(z, hw_back, hw_front, x_back, x_front, n=24):
        xc, hd = (x_back + x_front) / 2, (x_front - x_back) / 2
        pts = []
        for i in range(n):
            a = TAU * i / n
            c, s = math.cos(a), math.sin(a)
            hw = hw_front if c > 0 else hw_back
            xx = xc + hd * math.copysign(abs(c) ** (2 / 3.2), c)
            yy = hw * math.copysign(abs(s) ** (2 / 3.2), s)
            pts.append(W(xx, yy, z))
        return pts

    levels = [(11.0, 6.4, 5.6, 1.5, 11.0), (12.5, 6.1, 5.4, 1.8, 11.2), (14.0, 5.0, 4.8, 2.4, 11.3), (15.5, 4.1, 4.0, 2.8, 11.2),
              (17.0, 3.7, 3.6, 3.1, 11.0), (18.5, 3.5, 3.3, 3.4, 10.8), (19.4, 3.1, 2.8, 3.8, 10.4), (20.0, 2.2, 1.8, 4.6, 9.6)]
    secs = [nemes_sec(*lv) for lv in levels]
    vs, fs = loft(b, stone, secs)

    def head_col(f, co):
        z = co.z - fz
        n = noise.noise(Vector(((co.x - sx) * 0.5, (co.y - sy) * 0.5, z * 0.5)))
        # 頭巾上殘存的條紋
        stripe = 0.05 * (1 if math.sin(z * TAU / 0.9) > 0 else -1)
        v = 0.86 + 0.05 * n + stripe
        return (v, v * 0.84, v * 0.68)

    P.paint(fs, head_col)
    # 臉：自頭巾前方突出（寬 4.1 m、高約 5 m），鼻已缺損
    face = []
    for z, hw, xf in ((12.4, 1.2, 12.0), (13.0, 1.7, 12.6), (14.0, 2.05, 12.9), (15.2, 2.1, 13.0), (16.4, 2.1, 13.1),
                      (17.4, 2.05, 13.1), (18.3, 1.9, 12.7), (18.9, 1.5, 12.0)):
        sec = []
        n = 16
        for i in range(n):
            a = TAU * i / n
            c, s = math.cos(a), math.sin(a)
            xx = 10.6 + (xf - 10.6) * (0.5 + 0.5 * c) ** 0.6 if c > -1 else 10.6
            yy = hw * s * (0.85 + 0.15 * abs(c))
            sec.append(W(xx, yy, z))
        face.append(sec)
    vs, fs = loft(b, stone, face)

    def face_col(f, co):
        z = co.z - fz
        y = co.y - sy
        x = co.x - sx
        v = 0.9 + 0.04 * noise.noise(Vector((x, y, z)))
        # 眼窩、口部陰影
        if 16.3 < z < 17.0 and 0.5 < abs(y) < 1.5 and x > 12.6:
            v *= 0.62
        if 14.3 < z < 14.6 and abs(y) < 0.9 and x > 12.6:
            v *= 0.7
        return (v, v * 0.83, v * 0.66)

    P.paint(fs, face_col)
    # 眉骨、殘鼻、耳
    vs = b.box(stone, (0.5, 3.6, 0.35), tuple(W(13.05, 0, 17.25)))
    P.pv(vs, face_col)
    vs = b.frustum(stone, (0.9, 0.9), (0.4, 0.5), 0.5, tuple(W(13.0, 0, 15.2)), rot_z=0)
    P.pv(vs, face_col)
    for s in (-1, 1):
        vs = b.rock(stone, (1.0, 0.5, 1.6), tuple(W(11.0, s * 2.35, 16.2)), rough=0.05, subdiv=1, seed=60 + s)
        P.pv(vs, face_col)

    # 圍坑岩壁（北、南、西側），頂與周圍高原同高
    def cliff(x0, x1, y0, y1):
        cxl, cyl = (x0 + x1) / 2, (y0 + y1) / 2
        top = max(height(sx + cxl + dx, sy + cyl + dy) for dx in (-(x1 - x0) / 2, 0, (x1 - x0) / 2) for dy in (-(y1 - y0) / 2, (y1 - y0) / 2))
        hgt = top - fz + 3.0
        vs = b.rock(rockm, (x1 - x0, y1 - y0, hgt + 2.0), tuple(W(cxl, cyl, hgt / 2 - 2.5)), rough=0.06, subdiv=4,
                    seed=rng.randint(0, 999), round_=0.06)

        def col(f, co):
            z = co.z - fz
            v = 0.86 + 0.06 * math.sin(z * TAU / 1.4) + 0.05 * noise.noise(Vector((co.x * 0.2, co.y * 0.2, z * 0.3)))
            return (v, v * 0.86, v * 0.7)

        P.pv(vs, col)

    cliff(-66, 34, 22.0, 40)
    cliff(-66, 34, -40, -22.0)
    cliff(-68, -51.5, -30, 30)
