"""產生 Timelore 建築 GLB 模型。

用法（需安裝 Blender 或 pip 的 bpy 模組）：
    python blender/build.py                 # 全部
    python blender/build.py giza parthenon  # 指定
    python blender/build.py --preview DIR   # 另外以 Cycles 輸出預覽圖
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import models_ancient as A  # noqa: E402
import models_later as B  # noqa: E402
from lib import reset_scene, srgb  # noqa: E402

MODELS = {
    "stonehenge": A.stonehenge,
    "giza": A.giza,
    "parthenon": A.parthenon,
    "chichen-itza": A.chichen_itza,
    "angkor-wat": A.angkor_wat,
    "colosseum": B.colosseum,
    "great-wall": B.great_wall,
    "taj-mahal": B.taj_mahal,
    "himeji": B.himeji,
    "eiffel": B.eiffel,
}

OUT = os.path.join(os.path.dirname(__file__), "..", "public", "models")


def render_preview(png_path):
    scene = bpy.context.scene
    objs = [o for o in scene.objects if o.type == "MESH"]
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center = (lo + hi) / 2
    size = max(hi - lo)

    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 40
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    d = size * 1.25
    cam.location = center + Vector((d * 0.75, -d * 0.95, d * 0.62))
    direction = center - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    sun_data = bpy.data.lights.new("sun", "SUN")
    sun_data.energy = 3.5
    sun_data.angle = math.radians(8)
    sun = bpy.data.objects.new("sun", sun_data)
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))
    scene.collection.objects.link(sun)

    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = srgb("#1e5fc8")
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
    scene.world = world

    scene.render.engine = "CYCLES"
    scene.cycles.samples = 24
    scene.cycles.device = "CPU"
    scene.render.resolution_x = 800
    scene.render.resolution_y = 600
    scene.render.filepath = png_path
    bpy.ops.render.render(write_still=True)


def main():
    args = sys.argv[1:]
    preview_dir = None
    if "--preview" in args:
        i = args.index("--preview")
        preview_dir = args[i + 1]
        del args[i : i + 2]
    names = args or list(MODELS)
    os.makedirs(OUT, exist_ok=True)
    for name in names:
        reset_scene()
        path = os.path.abspath(os.path.join(OUT, f"{name}.glb"))
        MODELS[name](path)
        size = os.path.getsize(path) / 1024
        tris = sum(len(p.vertices) - 2 for o in bpy.context.scene.objects if o.type == "MESH" for p in o.data.polygons)
        print(f"[ok] {name}: {size:.0f} KB, ~{tris} tris")
        if preview_dir:
            os.makedirs(preview_dir, exist_ok=True)
            render_preview(os.path.join(os.path.abspath(preview_dir), f"{name}.png"))


if __name__ == "__main__":
    main()
