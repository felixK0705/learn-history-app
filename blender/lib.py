"""Timelore 寫實建築模型共用工具（Blender bpy / bmesh）。

- 全部以真實公尺為單位建模
- 材質使用 Poly Haven（CC0）PBR 貼圖：Base Color、Normal、ARM（AO/Roughness/Metal）
- 依世界座標做方塊投影 UV，貼圖以「每幾公尺重複一次」控制密度
"""

import math
import os
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector, noise

TAU = 2 * math.pi
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "textures")


def srgb(hex_color: str):
    h = hex_color.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i : i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def tinted_texture(tex_id: str, tint: str | None, gain: float = 1.0) -> str:
    """回傳（必要時調色後的）漫反射貼圖路徑；調色結果快取在 textures/_tinted"""
    src = os.path.join(TEX, tex_id, "diff.jpg")
    if not tint and gain == 1.0:
        return src
    out_dir = os.path.join(TEX, "_tinted")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{tex_id}_{(tint or 'none').lstrip('#')}_{gain:.2f}.jpg")
    if not os.path.exists(out):
        from PIL import Image, ImageOps

        im = Image.open(src).convert("RGB")
        if tint:
            # 先轉灰階保留明暗細節，再以目標色上色（保持貼圖質感、換成參考照的顏色）
            g = ImageOps.grayscale(im)
            mean = sum(g.getdata()) / (g.width * g.height)
            r, gg, b = (int(tint.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))

            def ch(c):
                return g.point(lambda v, c=c: max(0, min(255, int(c * (v / mean) * gain))))

            im = Image.merge("RGB", (ch(r), ch(gg), ch(b)))
        else:
            im = im.point(lambda v: max(0, min(255, int(v * gain))))
        im.save(out, quality=88)
    return out


class Builder:
    def __init__(self, name: str, seed: int = 1):
        self.name = name
        self.bm = bmesh.new()
        self.mats: list[bpy.types.Material] = []
        self.tiles: list[float] = []
        self._cache: dict[str, int] = {}
        self.rng = random.Random(seed)

    # ------------------------------------------------------------ 材質
    def tex(self, name, tex_id, tile=2.0, tint=None, gain=1.0, rough=None, metal=None, normal=1.0):
        """PBR 貼圖材質；tile 為貼圖在世界中重複的公尺數"""
        if name in self._cache:
            return self._cache[name]
        m = bpy.data.materials.new(f"{self.name}_{name}")
        m.use_nodes = True
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        img = nt.nodes.new("ShaderNodeTexImage")
        img.image = bpy.data.images.load(tinted_texture(tex_id, tint, gain), check_existing=True)
        nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
        nor_path = os.path.join(TEX, tex_id, "nor.jpg")
        if os.path.exists(nor_path) and normal > 0:
            nimg = nt.nodes.new("ShaderNodeTexImage")
            nimg.image = bpy.data.images.load(nor_path, check_existing=True)
            nimg.image.colorspace_settings.name = "Non-Color"
            nmap = nt.nodes.new("ShaderNodeNormalMap")
            nmap.inputs["Strength"].default_value = normal
            nt.links.new(nimg.outputs["Color"], nmap.inputs["Color"])
            nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
        arm_path = os.path.join(TEX, tex_id, "arm.jpg")
        if os.path.exists(arm_path) and rough is None:
            aimg = nt.nodes.new("ShaderNodeTexImage")
            aimg.image = bpy.data.images.load(arm_path, check_existing=True)
            aimg.image.colorspace_settings.name = "Non-Color"
            sep = nt.nodes.new("ShaderNodeSeparateColor")
            nt.links.new(aimg.outputs["Color"], sep.inputs["Color"])
            nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
            nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
        else:
            bsdf.inputs["Roughness"].default_value = rough if rough is not None else 0.8
        if metal is not None:
            for l in list(bsdf.inputs["Metallic"].links):
                nt.links.remove(l)
            bsdf.inputs["Metallic"].default_value = metal
        return self._register(name, m, tile)

    def color(self, name, hex_color, rough=0.7, metal=0.0, alpha=1.0):
        if name in self._cache:
            return self._cache[name]
        m = bpy.data.materials.new(f"{self.name}_{name}")
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = srgb(hex_color)
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        if alpha < 1:
            bsdf.inputs["Alpha"].default_value = alpha
            m.surface_render_method = "BLENDED"
        return self._register(name, m, 1.0)

    def _register(self, name, m, tile):
        self.mats.append(m)
        self.tiles.append(tile)
        self._cache[name] = len(self.mats) - 1
        return self._cache[name]

    def _assign(self, verts, mi, smooth=False):
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = mi
            f.smooth = smooth

    # ------------------------------------------------------------ 基本形體
    def box(self, mi, size, loc, rot=(0, 0, 0)):
        M = Matrix.LocRotScale(Vector(loc), Euler(rot), Vector(size))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)
        self._assign(r["verts"], mi)
        return r["verts"]

    def box_base(self, mi, size, base, rot=(0, 0, 0)):
        x, y, z = base
        return self.box(mi, size, (x, y, z + size[2] / 2), rot)

    def cyl(self, mi, r1, r2, h, base, seg=24, rot=(0, 0, 0), smooth=False):
        if r2 <= 1e-6:
            return self.cone(mi, r1, h, base, seg, rot, smooth)
        M = Matrix.LocRotScale(Vector(base), Euler(rot), Vector((1, 1, 1))) @ Matrix.Translation((0, 0, h / 2))
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r1, radius2=r2, depth=h, matrix=M)
        self._assign(r["verts"], mi, smooth)
        return r["verts"]

    def cone(self, mi, r, h, base, seg=16, rot=(0, 0, 0), smooth=False):
        M = Matrix.LocRotScale(Vector(base), Euler(rot), Vector((1, 1, 1)))
        ring = [self.bm.verts.new(M @ Vector((r * math.cos(TAU * i / seg), r * math.sin(TAU * i / seg), 0))) for i in range(seg)]
        apex = self.bm.verts.new(M @ Vector((0, 0, h)))
        self.bm.faces.new(list(reversed(ring)))
        for i in range(seg):
            self.bm.faces.new([ring[i], ring[(i + 1) % seg], apex])
        self._assign(ring + [apex], mi, smooth)
        return ring + [apex]

    def ico(self, mi, radius, loc, subdiv=2, scale=(1, 1, 1), smooth=True):
        M = Matrix.LocRotScale(Vector(loc), Euler((0, 0, 0)), Vector(scale))
        r = bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=radius, matrix=M)
        self._assign(r["verts"], mi, smooth)
        return r["verts"]

    def frustum(self, mi, bottom, top, h, base, rot_z=0.0, top_offset=(0, 0)):
        bx, by = bottom[0] / 2, bottom[1] / 2
        tx, ty = top[0] / 2, top[1] / 2
        ox, oy = top_offset
        M = Matrix.Translation(Vector(base)) @ Matrix.Rotation(rot_z, 4, "Z")
        pts = [(-bx, -by, 0), (bx, -by, 0), (bx, by, 0), (-bx, by, 0),
               (-tx + ox, -ty + oy, h), (tx + ox, -ty + oy, h), (tx + ox, ty + oy, h), (-tx + ox, ty + oy, h)]
        vs = [self.bm.verts.new(M @ Vector(p)) for p in pts]
        for f in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
            self.bm.faces.new([vs[i] for i in f])
        self._assign(vs, mi)
        return vs

    def prism(self, mi, pts2d, z0, h, M=None):
        """XY 平面逆時針多邊形擠出 h（可帶變換矩陣 M）"""
        M = M or Matrix.Identity(4)
        n = len(pts2d)
        bot = [self.bm.verts.new(M @ Vector((x, y, z0))) for x, y in pts2d]
        top = [self.bm.verts.new(M @ Vector((x, y, z0 + h))) for x, y in pts2d]
        self.bm.faces.new(list(reversed(bot)))
        self.bm.faces.new(top)
        for i in range(n):
            j = (i + 1) % n
            self.bm.faces.new([bot[i], bot[j], top[j], top[i]])
        self._assign(bot + top, mi)
        return bot + top

    def profile_wall(self, mi, pts_uv, depth, M):
        """立面輪廓（u 水平、v 垂直，逆時針）沿局部 Y 擠出 depth；用於拱門、山牆"""
        R = M @ Matrix.Rotation(math.pi / 2, 4, "X") @ Matrix.Translation((0, 0, -depth / 2))
        return self.prism(mi, pts_uv, 0, depth, R)

    def tri_prism(self, mi, width, depth, height, base, rot_z=0.0):
        M = Matrix.Translation(Vector(base)) @ Matrix.Rotation(rot_z, 4, "Z")
        w, d = width / 2, depth / 2
        pts = [(-w, -d, 0), (-w, d, 0), (-w, 0, height), (w, -d, 0), (w, d, 0), (w, 0, height)]
        v = [self.bm.verts.new(M @ Vector(p)) for p in pts]
        for f in [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)]:
            self.bm.faces.new([v[i] for i in f])
        self._assign(v, mi)
        return v

    def lathe(self, mi, profile, base=(0, 0, 0), seg=32, smooth=True, rot_offset=0.0, radial=None):
        """旋轉體；radial(theta) 可回傳半徑倍率（做出凹槽、稜線）"""
        bx, by, bz = base
        rings = []
        for r, z in profile:
            if r < 1e-6:
                rings.append([self.bm.verts.new((bx, by, bz + z))])
                continue
            ring = []
            for i in range(seg):
                t = rot_offset + TAU * i / seg
                rr = r * (radial(t) if radial else 1.0)
                ring.append(self.bm.verts.new((bx + rr * math.cos(t), by + rr * math.sin(t), bz + z)))
            rings.append(ring)
        if len(rings[0]) > 1:
            self.bm.faces.new(list(reversed(rings[0])))
        if len(rings[-1]) > 1:
            self.bm.faces.new(rings[-1])
        for a, b in zip(rings, rings[1:]):
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                for i in range(seg):
                    self.bm.faces.new([a[0], b[i], b[(i + 1) % seg]])
            elif len(b) == 1:
                for i in range(seg):
                    self.bm.faces.new([a[i], a[(i + 1) % seg], b[0]])
            else:
                for i in range(seg):
                    j = (i + 1) % seg
                    self.bm.faces.new([a[i], a[j], b[j], b[i]])
        allv = [v for r in rings for v in r]
        self._assign(allv, mi, smooth)
        return allv

    def ering(self, mi, inner, outer, z0, z1, seg=96, t0=0.0, t1=TAU, center=(0, 0)):
        full = abs((t1 - t0) - TAU) < 1e-6
        n = seg if full else max(2, int(seg * (t1 - t0) / TAU) + 1)
        cx, cy = center

        def ring(a, b, z):
            return [self.bm.verts.new((cx + a * math.cos(t0 + (t1 - t0) * i / (n if full else n - 1)),
                                       cy + b * math.sin(t0 + (t1 - t0) * i / (n if full else n - 1)), z)) for i in range(n)]

        ib, ob, it, ot = ring(*inner, z0), ring(*outer, z0), ring(*inner, z1), ring(*outer, z1)
        m = n if full else n - 1
        for i in range(m):
            j = (i + 1) % n
            self.bm.faces.new([ot[i], ot[j], it[j], it[i]])
            self.bm.faces.new([ib[i], ib[j], ob[j], ob[i]])
            self.bm.faces.new([ob[i], ob[j], ot[j], ot[i]])
            self.bm.faces.new([it[i], it[j], ib[j], ib[i]])
        if not full:
            self.bm.faces.new(list(reversed([ib[0], ob[0], ot[0], it[0]])))
            self.bm.faces.new([ib[-1], ob[-1], ot[-1], it[-1]])
        allv = ib + ob + it + ot
        self._assign(allv, mi)
        return allv

    def rock(self, mi, size, loc, rot=(0, 0, 0), rough=0.18, subdiv=3, seed=0, flat_bottom=True, round_=0.35):
        """不規則岩塊：細分立方體加雜訊位移（用於巨石、碎石）"""
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=subdiv, use_grid_fill=True)
        off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
        for v in bm.verts:
            p = v.co.copy()
            # 先把立方體往圓角收，再加多層雜訊
            p = p.normalized() * 0.5 * round_ + p * (1 - round_)
            n = noise.noise(p * 2.2 + off) * 0.6 + noise.noise(p * 5.0 + off) * 0.25
            p += p.normalized() * n * rough
            if flat_bottom and p.z < -0.42:
                p.z = -0.5
            v.co = p
        M = Matrix.LocRotScale(Vector(loc), Euler(rot), Vector(size))
        bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
        me = bpy.data.meshes.new("tmp_rock")
        bm.to_mesh(me)
        bm.free()
        start = len(self.bm.verts)
        self.bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        self.bm.verts.ensure_lookup_table()
        new = self.bm.verts[start:]
        self._assign(new, mi, smooth=True)
        return new

    # ------------------------------------------------------------ 建築組件
    def arch_points(self, width, spring, kind="round", seg=12):
        """拱的上緣曲線點（由左至右）；kind=round 半圓、pointed 尖拱"""
        w = width / 2
        pts = []
        if kind == "round":
            for i in range(seg + 1):
                a = math.pi - math.pi * i / seg
                pts.append((w * math.cos(a), spring + w * math.sin(a)))
        else:  # 雙心尖拱：左右兩段圓弧在頂點交會
            r = width * 0.8
            cx = -w + r
            dy = math.sqrt(r * r - cx * cx)
            a_top = math.atan2(dy, -cx)
            half = seg // 2
            left = [(cx + r * math.cos(math.pi + (a_top - math.pi) * i / half), spring + r * math.sin(math.pi + (a_top - math.pi) * i / half)) for i in range(half + 1)]
            pts = left + [(-x, y) for x, y in reversed(left[:-1])]
        return pts

    def arch_frame(self, mi, width, height, spring, opening, depth, M, kind="round"):
        """有拱形開口的牆面板：外框寬 width、高 height，開口寬 opening、起拱高 spring"""
        w = width / 2
        o = opening / 2
        arc = self.arch_points(opening, spring, kind)
        # 左柱
        self.profile_wall(mi, [(-w, 0), (-o, 0), (-o, spring), (-w, spring)], depth, M)
        # 右柱
        self.profile_wall(mi, [(o, 0), (w, 0), (w, spring), (o, spring)], depth, M)
        # 拱上方的拱肩（左右兩半，避免凹多邊形）
        mid = len(arc) // 2
        left = arc[: mid + 1]
        right = arc[mid:]
        apex = arc[mid]
        self.profile_wall(mi, [(-w, spring), (-o, spring)] + left[1:] + [(apex[0], height), (-w, height)], depth, M)
        self.profile_wall(mi, [(apex[0], apex[1])] + right[1:-1] + [(o, spring), (w, spring), (w, height), (apex[0], height)], depth, M)

    def ground_disc(self, mi, radius, edge_mi, depth=3.0, seg=96, height_fn=None, rings=24):
        """圓形地景（可帶起伏）＋側面土層，頂面中心 z=0"""
        grid = []
        for i in range(rings + 1):
            r = radius * i / rings
            row = []
            n = 1 if i == 0 else seg
            for j in range(n):
                a = TAU * j / seg
                x, y = r * math.cos(a), r * math.sin(a)
                z = height_fn(x, y) if height_fn else 0.0
                row.append(self.bm.verts.new((x, y, z)))
            grid.append(row)
        faces = []
        for j in range(seg):
            faces.append(self.bm.faces.new([grid[0][0], grid[1][j], grid[1][(j + 1) % seg]]))
        for i in range(1, rings):
            for j in range(seg):
                k = (j + 1) % seg
                faces.append(self.bm.faces.new([grid[i][j], grid[i + 1][j], grid[i + 1][k], grid[i][k]]))
        for f in faces:
            f.material_index = mi
            f.smooth = True
        edge = grid[-1]
        bottom = [self.bm.verts.new((v.co.x, v.co.y, -depth)) for v in edge]
        for j in range(seg):
            k = (j + 1) % seg
            f = self.bm.faces.new([edge[k], edge[j], bottom[j], bottom[k]])
            f.material_index = edge_mi
        f = self.bm.faces.new(list(reversed(bottom)))
        f.material_index = edge_mi

    def tree(self, x, y, z=0.0, h=8.0, kind="broad"):
        trunk = self.color("trunk", "#5a4330", rough=0.9)
        leaf = self.color("foliage", "#4f7a34", rough=0.85) if kind == "broad" else self.color("conifer", "#2f5a2c", rough=0.85)
        self.cyl(trunk, h * 0.035, h * 0.025, h * 0.45, (x, y, z), seg=7)
        if kind == "broad":
            for k in range(4):
                ox, oy = self.rng.uniform(-0.15, 0.15) * h, self.rng.uniform(-0.15, 0.15) * h
                self.rock(leaf, (h * 0.45, h * 0.45, h * 0.38), (x + ox, y + oy, z + h * (0.62 + 0.08 * k)), rough=0.35, subdiv=2, seed=self.rng.randint(0, 999), flat_bottom=False)
        elif kind == "cypress":
            self.lathe(leaf, [(0, 0), (h * 0.12, h * 0.15), (h * 0.14, h * 0.45), (h * 0.08, h * 0.85), (0, h)], (x, y, z), seg=10)
        else:
            for k in range(4):
                self.cone(leaf, h * (0.28 - k * 0.05), h * 0.38, (x, y, z + h * (0.25 + k * 0.17)), seg=9)

    def lattice(self, name, rings, mi, thickness):
        """鋼構格架：由多個截面環（點列）組成的管狀網格，三角化後套用 Wireframe 修改器（輸出時套用）"""
        bm = bmesh.new()
        vr = [[bm.verts.new(p) for p in ring] for ring in rings]
        n = len(rings[0])
        for a, c in zip(vr, vr[1:]):
            for i in range(n):
                j = (i + 1) % n
                bm.faces.new([a[i], a[j], c[j], c[i]])
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method="ALTERNATE")
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(self.mats[mi])
        obj = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(obj)
        mod = obj.modifiers.new("wire", "WIREFRAME")
        mod.thickness = thickness
        mod.use_even_offset = True
        mod.use_relative_offset = False
        mod.use_replace = True
        mod.use_boundary = True
        return obj

    def hip_roof(self, mi, w, d, h, base, overhang=1.0, upturn=0.6, rot_z=0.0, sag=0.25):
        """日式入母屋／寄棟屋頂：四角上翹、斜面微凹"""
        M = Matrix.Translation(Vector(base)) @ Matrix.Rotation(rot_z, 4, "Z")
        W, D = w / 2 + overhang, d / 2 + overhang
        ridge = max(0.0, (w - d) / 2)
        eave = [(-W, -D, upturn), (W, -D, upturn), (W, D, upturn), (-W, D, upturn)]
        mid_f = 0.55
        mid = [(x * mid_f + (0 if abs(x) < 1e-6 else (ridge * (1 - mid_f) * (1 if x > 0 else -1))), y * mid_f, h * (0.5 - sag * 0.5)) for x, y, _ in eave]
        mids = [(-W, -D), (W, -D), (W, D), (-W, D)]
        # 每邊中點（不上翹）
        edge_mid = [((a[0] + c[0]) / 2, (a[1] + c[1]) / 2, 0.0) for a, c in zip(mids, mids[1:] + mids[:1])]
        ring1 = []
        for i in range(4):
            ring1.append(eave[i])
            ring1.append(edge_mid[i])
        ring2 = []
        for i in range(4):
            ring2.append(mid[i])
            a, c = mid[i], mid[(i + 1) % 4]
            ring2.append(((a[0] + c[0]) / 2, (a[1] + c[1]) / 2, a[2] - 0.05))
        top = [(-ridge, 0, h), (ridge, 0, h)]
        v1 = [self.bm.verts.new(M @ Vector(p)) for p in ring1]
        v2 = [self.bm.verts.new(M @ Vector(p)) for p in ring2]
        t0 = self.bm.verts.new(M @ Vector(top[0]))
        t1 = self.bm.verts.new(M @ Vector(top[1])) if ridge > 1e-6 else t0
        for i in range(8):
            j = (i + 1) % 8
            self.bm.faces.new([v1[i], v1[j], v2[j], v2[i]])
        # 上段收至屋脊：索引 0..7 依序為 角、邊中點… 對應 -Y,+X,+Y,-X 邊
        tops = [t0 if ring2[i][0] < 0 else t1 for i in range(8)] if ridge > 1e-6 else [t0] * 8
        for i in range(8):
            j = (i + 1) % 8
            if tops[i] is tops[j]:
                self.bm.faces.new([v2[i], v2[j], tops[i]])
            else:
                self.bm.faces.new([v2[i], v2[j], tops[j], tops[i]])
        bot = [self.bm.verts.new(M @ Vector((x, y, z - 0.35))) for x, y, z in ring1]
        for i in range(8):
            j = (i + 1) % 8
            self.bm.faces.new([bot[j], bot[i], v1[i], v1[j]])
        self.bm.faces.new(list(reversed(bot)))
        allv = v1 + v2 + bot + [t0, t1]
        self._assign(allv, mi)
        return allv

    def scatter(self, n, r_min, r_max, avoid=None, min_dist=2.0):
        pts, tries = [], 0
        while len(pts) < n and tries < n * 80:
            tries += 1
            a = self.rng.uniform(0, TAU)
            r = math.sqrt(self.rng.uniform(r_min**2, r_max**2))
            x, y = r * math.cos(a), r * math.sin(a)
            if avoid and avoid(x, y):
                continue
            if any((x - px) ** 2 + (y - py) ** 2 < min_dist**2 for px, py in pts):
                continue
            pts.append((x, y))
        return pts

    # ------------------------------------------------------------ 輸出
    def _uv(self):
        uv = self.bm.loops.layers.uv.verify()
        for f in self.bm.faces:
            tile = self.tiles[f.material_index] if f.material_index < len(self.tiles) else 1.0
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                c = l.vert.co
                if ax == 2:
                    u, v = c.x, c.y
                elif ax == 0:
                    u, v = c.y, c.z
                else:
                    u, v = c.x, c.z
                l[uv].uv = (u / tile, v / tile)

    def build_object(self):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        self.bm.normal_update()
        self._uv()
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(obj)
        return obj

    def export(self, path):
        self.build_object()
        bpy.ops.export_scene.gltf(
            filepath=path,
            export_format="GLB",
            export_apply=True,
            export_yup=True,
            export_image_format="JPEG",
            export_jpeg_quality=82,
        )
