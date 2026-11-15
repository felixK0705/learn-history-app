"""產生 Timelore 寫實建築 GLB 模型。

需求：Blender Python 模組（pip install bpy==5.3.0）、Pillow，以及先執行
    python blender/fetch_textures.py <材質 id...>   # 下載 Poly Haven CC0 材質

用法：
    python blender/build.py                         # 全部
    python blender/build.py parthenon colosseum     # 指定
    python blender/build.py --preview DIR [--ref DIR]   # 另以 Cycles 輸出預覽；--ref 會與參考照並排
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import importlib  # noqa: E402

from lib import HERE, reset_scene  # noqa: E402

# 每座建築一個模組：blender/buildings/<模組>.py，內含同名函式
_IDS = ["stonehenge", "giza", "parthenon", "chichen-itza", "angkor-wat", "colosseum", "great-wall", "taj-mahal", "himeji", "eiffel",
        "kremlin", "kinkakuji", "forbidden-city", "pisa", "louvre", "machu-picchu", "christ-redeemer", "statue-of-liberty", "sphinx", "sydney-opera", "moai", "callanish", "hagia-sophia", "rushmore", "deoksugung", "blue-mosque", "motherland", "wat-pho", "tikal", "belem-tower", "florence-duomo", "neuschwanstein"]
MODELS = {i: (lambda mod: (lambda path: getattr(importlib.import_module(f"buildings.{mod}"), mod)(path)))(i.replace("-", "_")) for i in _IDS}

# 預覽相機：目標點、方位角（度，0 = 從 -Y 往 +Y 看）、仰角、距離（公尺）、焦距；盡量對應參考照的拍攝角度
CAMS = {
    "stonehenge": ((0, 0, 3.2), 215, 1.5, 48, 32),
    "giza": ((-458.7, -658.8, 54.2), 334.5, -1.0, 700.0, 78),
    "parthenon": ((0, 0, 9), 222, 4, 92, 28),
    "chichen-itza": ((0, 0, 12), 150, 8, 110, 35),
    "angkor-wat": ((-11.7, 9.8, 4.18), 259.25, -0.37, 430.0, 65),
    "colosseum": ((0, 0, 22), 120, 6, 230, 35),
    "great-wall": ((0.0, 582.18, 34.85), 0.0, 14.0, 600.0, 30.0),
    "taj-mahal": ((0, 0, 32), 180, 4, 240, 40),
    "himeji": ((5.8, -7.4, 40.3), -22.9, -14.0, 160, 50),
    "eiffel": ((0, 0, 140), 180, 5, 620, 40),
}

OUT = os.path.join(HERE, "..", "public", "models")


def render_preview(name, png_path, ref_dir=None):
    scene = bpy.context.scene
    # 建築模組可自帶 CAMERA 常數（目標點、方位角、仰角、距離、焦距），優先於 CAMS
    mod = importlib.import_module(f"buildings.{name.replace('-', '_')}")
    target, az, el, dist, lens = getattr(mod, "CAMERA", None) or CAMS.get(name, ((0, 0, 10), 200, 8, 120, 35))
    t = Vector(target)
    a, e = math.radians(az), math.radians(el)
    loc = t + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = lens
    cam_data.clip_end = dist * 10
    cam = bpy.data.objects.new("cam", cam_data)
    cam.location = loc
    cam.rotation_euler = (t - loc).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(cam)
    scene.camera = cam

    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    nt = world.node_tree
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(os.path.join(HERE, "hdri", "sky_1k.hdr"))
    nt.links.new(env.outputs["Color"], nt.nodes["Background"].inputs["Color"])
    nt.nodes["Background"].inputs["Strength"].default_value = 1.0
    scene.world = world

    sun_data = bpy.data.lights.new("sun", "SUN")
    sun_data.energy = 4.0
    sun_data.angle = math.radians(1.5)
    sun = bpy.data.objects.new("sun", sun_data)
    sun.rotation_euler = (math.radians(42), 0, math.radians(az + 35))
    scene.collection.objects.link(sun)

    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.cycles.device = "CPU"
    scene.view_settings.view_transform = "AgX"
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    scene.view_settings.exposure = -0.35
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 750
    scene.render.filepath = png_path
    bpy.ops.render.render(write_still=True)

    if ref_dir and os.path.exists(os.path.join(ref_dir, f"{name}.jpg")):
        from PIL import Image

        ref = Image.open(os.path.join(ref_dir, f"{name}.jpg")).convert("RGB")
        ref.thumbnail((1000, 750))
        ren = Image.open(png_path).convert("RGB")
        side = Image.new("RGB", (2000, 750), "white")
        side.paste(ref, (0, 0))
        side.paste(ren, (1000, 0))
        side.save(png_path.replace(".png", "_compare.jpg"), quality=85)


def main():
    args = sys.argv[1:]
    preview_dir = ref_dir = None
    if "--preview" in args:
        i = args.index("--preview")
        preview_dir = args[i + 1]
        del args[i : i + 2]
    if "--ref" in args:
        i = args.index("--ref")
        ref_dir = args[i + 1]
        del args[i : i + 2]
    names = args or list(MODELS)
    os.makedirs(OUT, exist_ok=True)
    for name in names:
        reset_scene()
        path = os.path.abspath(os.path.join(OUT, f"{name}.glb"))
        MODELS[name](path)
        size = os.path.getsize(path) / 1024 / 1024
        tris = sum(len(p.vertices) - 2 for o in bpy.context.scene.objects if o.type == "MESH" for p in o.data.polygons)
        print(f"[ok] {name}: {size:.1f} MB, ~{tris} tris", flush=True)
        if preview_dir:
            os.makedirs(preview_dir, exist_ok=True)
            render_preview(name, os.path.join(os.path.abspath(preview_dir), f"{name}.png"), ref_dir)


if __name__ == "__main__":
    main()
