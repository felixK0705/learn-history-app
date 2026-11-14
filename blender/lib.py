"""Timelore 建築模型共用建模工具（Blender bpy / bmesh）。

所有幾何直接寫入同一個 bmesh，並以 material_index 區分材質，
最後輸出為單一 mesh 物件，讓 GLB 檔案小、繪製呼叫少。
"""

import math
import random

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

TAU = 2 * math.pi


def srgb(hex_color: str):
    """#rrggbb → 線性色彩空間 RGBA"""
    h = hex_color.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i : i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1.0)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


class Builder:
    def __init__(self, name: str, seed: int = 1):
        self.name = name
        self.bm = bmesh.new()
        self.mats: list[bpy.types.Material] = []
        self._mat_cache: dict[str, bpy.types.Material] = {}
        self.rng = random.Random(seed)
        self.extra_objects: list[bpy.types.Object] = []

    # ---------- 材質 ----------
    def mat(self, name: str, color: str, rough: float = 0.85, metal: float = 0.0) -> int:
        if name not in self._mat_cache:
            m = bpy.data.materials.new(f"{self.name}_{name}")
            m.use_nodes = True
            bsdf = m.node_tree.nodes.get("Principled BSDF")
            bsdf.inputs["Base Color"].default_value = srgb(color)
            bsdf.inputs["Roughness"].default_value = rough
            bsdf.inputs["Metallic"].default_value = metal
            m.diffuse_color = srgb(color)
            self._mat_cache[name] = m
            self.mats.append(m)
        return self.mats.index(self._mat_cache[name])

    def _assign(self, verts, mi: int, smooth: bool = False):
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = mi
            f.smooth = smooth

    # ---------- 基本形體 ----------
    def box(self, mi, size, loc, rot=(0, 0, 0)):
        """以中心點 loc 建立長方體"""
        M = Matrix.LocRotScale(Vector(loc), Euler(rot), Vector(size))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)
        self._assign(r["verts"], mi)
        return r["verts"]

    def box_base(self, mi, size, base, rot=(0, 0, 0)):
        """以底面中心 base 建立長方體"""
        x, y, z = base
        return self.box(mi, size, (x, y, z + size[2] / 2), rot)

    def cyl(self, mi, r1, r2, h, base, seg=16, rot=(0, 0, 0), smooth=False):
        """底面中心為 base 的圓柱／圓錐（r2=0 為圓錐）"""
        if r2 <= 1e-6:
            return self.cone(mi, r1, h, base, seg=seg, rot=rot, smooth=smooth)
        M = Matrix.LocRotScale(Vector(base), Euler(rot), Vector((1, 1, 1))) @ Matrix.Translation((0, 0, h / 2))
        r = bmesh.ops.create_cone(
            self.bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r1, radius2=r2, depth=h, matrix=M
        )
        self._assign(r["verts"], mi, smooth)
        return r["verts"]

    def cone(self, mi, r, h, base, seg=16, rot=(0, 0, 0), smooth=False):
        """尖頂圓錐／角錐（頂點只有一個，避免退化面）"""
        M = Matrix.LocRotScale(Vector(base), Euler(rot), Vector((1, 1, 1)))
        ring = [self.bm.verts.new(M @ Vector((r * math.cos(TAU * i / seg), r * math.sin(TAU * i / seg), 0))) for i in range(seg)]
        apex = self.bm.verts.new(M @ Vector((0, 0, h)))
        self.bm.faces.new(list(reversed(ring)))
        for i in range(seg):
            self.bm.faces.new([ring[i], ring[(i + 1) % seg], apex])
        self._assign(ring + [apex], mi, smooth)
        return ring + [apex]

    def ico(self, mi, radius, loc, subdiv=1, scale=(1, 1, 1), smooth=False):
        M = Matrix.LocRotScale(Vector(loc), Euler((0, 0, 0)), Vector(scale))
        r = bmesh.ops.create_icosphere(self.bm, subdivisions=subdiv, radius=radius, matrix=M)
        self._assign(r["verts"], mi, smooth)
        return r["verts"]

    def frustum(self, mi, bottom, top, h, base, rot_z=0.0):
        """矩形截頭錐體：bottom/top 為 (寬, 深)"""
        bx, by = bottom[0] / 2, bottom[1] / 2
        tx, ty = top[0] / 2, top[1] / 2
        M = Matrix.Translation(Vector(base)) @ Matrix.Rotation(rot_z, 4, "Z")
        pts = [(-bx, -by, 0), (bx, -by, 0), (bx, by, 0), (-bx, by, 0), (-tx, -ty, h), (tx, -ty, h), (tx, ty, h), (-tx, ty, h)]
        vs = [self.bm.verts.new(M @ Vector(p)) for p in pts]
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        for f in faces:
            self.bm.faces.new([vs[i] for i in f])
        self._assign(vs, mi)
        return vs

    def prism(self, mi, pts2d, z0, h, offset=(0, 0, 0), rot_z=0.0):
        """將逆時針 2D 多邊形擠出成柱體"""
        M = Matrix.Translation(Vector(offset)) @ Matrix.Rotation(rot_z, 4, "Z")
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

    def tri_prism(self, mi, width, depth, height, base, rot_z=0.0):
        """三角柱（山牆／屋脊），沿 X 方向延伸 width，截面寬 depth、高 height"""
        M = Matrix.Translation(Vector(base)) @ Matrix.Rotation(rot_z, 4, "Z")
        w, d = width / 2, depth / 2
        pts = [(-w, -d, 0), (-w, d, 0), (-w, 0, height), (w, -d, 0), (w, d, 0), (w, 0, height)]
        v = [self.bm.verts.new(M @ Vector(p)) for p in pts]
        for f in [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)]:
            self.bm.faces.new([v[i] for i in f])
        self._assign(v, mi)
        return v

    def lathe(self, mi, profile, base=(0, 0, 0), seg=24, smooth=True, rot_offset=0.0):
        """旋轉體：profile 為由下到上的 (半徑, 高度)"""
        bx, by, bz = base
        rings = []
        for r, z in profile:
            if r < 1e-5:
                rings.append([self.bm.verts.new((bx, by, bz + z))])
            else:
                rings.append(
                    [
                        self.bm.verts.new(
                            (
                                bx + r * math.cos(rot_offset + 2 * math.pi * i / seg),
                                by + r * math.sin(rot_offset + 2 * math.pi * i / seg),
                                bz + z,
                            )
                        )
                        for i in range(seg)
                    ]
                )
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

    def ering(self, mi, inner, outer, z0, z1, seg=72, t0=0.0, t1=2 * math.pi, center=(0, 0)):
        """橢圓環柱體：inner/outer 為 (a, b) 半軸，可指定角度範圍"""
        full = abs((t1 - t0) - 2 * math.pi) < 1e-6
        n = seg if full else max(2, int(seg * (t1 - t0) / (2 * math.pi)) + 1)
        cx, cy = center

        def ring(a, b, z):
            out = []
            for i in range(n):
                t = t0 + (t1 - t0) * i / (n if full else n - 1)
                out.append(self.bm.verts.new((cx + a * math.cos(t), cy + b * math.sin(t), z)))
            return out

        ib, ob = ring(*inner, z0), ring(*outer, z0)
        it, ot = ring(*inner, z1), ring(*outer, z1)
        m = n if full else n - 1
        for i in range(m):
            j = (i + 1) % n
            self.bm.faces.new([ot[i], ot[j], it[j], it[i]])  # 頂
            self.bm.faces.new([ib[i], ib[j], ob[j], ob[i]])  # 底
            self.bm.faces.new([ob[i], ob[j], ot[j], ot[i]])  # 外
            self.bm.faces.new([it[i], it[j], ib[j], ib[i]])  # 內
        if not full:
            for k in (0, n - 1):
                f = [ib[k], ob[k], ot[k], it[k]]
                self.bm.faces.new(f if k == n - 1 else list(reversed(f)))
        allv = ib + ob + it + ot
        self._assign(allv, mi)
        return allv

    # ---------- 常用組件 ----------
    def plinth(self, radius, top_mi, side_mi, depth=1.2, seg=64):
        """圓形展示地台，頂面在 z=-0.01（讓貼地物件不會與頂面重疊閃爍）"""
        self.cyl(side_mi, radius * 0.97, radius, depth - 0.08, (0, 0, -depth), seg=seg)
        self.cyl(top_mi, radius, radius, 0.07, (0, 0, -0.08), seg=seg)

    def tree_cone(self, x, y, z=0.0, h=1.6, r=0.5, leaf=None, trunk=None):
        leaf = leaf if leaf is not None else self.mat("leaf", "#3f7d3a")
        trunk = trunk if trunk is not None else self.mat("trunk", "#6b4a2b")
        self.cyl(trunk, 0.08, 0.06, h * 0.25, (x, y, z), seg=6)
        self.cyl(leaf, r, 0.0, h * 0.55, (x, y, z + h * 0.2), seg=7)
        self.cyl(leaf, r * 0.75, 0.0, h * 0.5, (x, y, z + h * 0.45), seg=7)

    def tree_round(self, x, y, z=0.0, h=1.4, r=0.6, leaf=None, trunk=None):
        leaf = leaf if leaf is not None else self.mat("leaf_round", "#4f8f3f")
        trunk = trunk if trunk is not None else self.mat("trunk", "#6b4a2b")
        self.cyl(trunk, 0.09, 0.07, h * 0.5, (x, y, z), seg=6)
        self.ico(leaf, r, (x, y, z + h * 0.5 + r * 0.6), subdiv=1, scale=(1, 1, 0.85))

    def palm(self, x, y, z=0.0, h=2.0):
        trunk = self.mat("palm_trunk", "#8a6a45")
        leaf = self.mat("palm_leaf", "#5c9a3e")
        lean = self.rng.uniform(-0.15, 0.15)
        self.cyl(trunk, 0.09, 0.06, h, (x, y, z), seg=6, rot=(lean, lean * 0.5, 0))
        top = Vector((x + math.sin(lean * 0.5) * h, y - math.sin(lean) * h, z + h))
        for k in range(6):
            a = k * math.pi / 3 + self.rng.uniform(-0.2, 0.2)
            self.box(leaf, (1.1, 0.22, 0.04), (top.x + math.cos(a) * 0.5, top.y + math.sin(a) * 0.5, top.z - 0.12), rot=(0, 0.35, a))

    def scatter(self, n, r_min, r_max, avoid=None):
        """在環形區域內隨機取點；avoid(x, y) 回傳 True 表示略過"""
        pts = []
        tries = 0
        while len(pts) < n and tries < n * 50:
            tries += 1
            a = self.rng.uniform(0, 2 * math.pi)
            r = math.sqrt(self.rng.uniform(r_min**2, r_max**2))
            x, y = r * math.cos(a), r * math.sin(a)
            if avoid and avoid(x, y):
                continue
            if any((x - px) ** 2 + (y - py) ** 2 < 0.8 for px, py in pts):
                continue
            pts.append((x, y))
        return pts

    # ---------- 輸出 ----------
    def build_object(self):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        obj = bpy.data.objects.new(self.name, me)
        bpy.context.scene.collection.objects.link(obj)
        return obj

    def export(self, path: str):
        self.build_object()
        bpy.ops.export_scene.gltf(
            filepath=path,
            export_format="GLB",
            export_apply=True,
            export_yup=True,
            export_draco_mesh_compression_enable=False,
        )
