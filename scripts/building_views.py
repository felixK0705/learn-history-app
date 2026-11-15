"""把 blender 模組的 CAMERA（Blender 座標）轉成網頁 three.js 用的 buildingViews.json 項目"""
import ast, json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
views_path = ROOT / "src/data/buildingViews.json"
views = json.loads(views_path.read_text())
for bid in sys.argv[1:]:
    src = (ROOT / "blender/buildings" / (bid.replace("-", "_") + ".py")).read_text()
    cam = next(ast.literal_eval(n.value) for n in ast.parse(src).body
               if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "CAMERA")
    (tx, ty, tz), az, el, dist, lens = cam
    a, e = math.radians(az), math.radians(el)
    lx, ly, lz = tx + math.sin(a) * math.cos(e) * dist, ty - math.cos(a) * math.cos(e) * dist, tz + math.sin(e) * dist
    views[bid] = {
        "target": [round(tx, 2), round(tz, 2), round(-ty, 2)],
        "position": [round(lx, 2), round(lz, 2), round(-ly, 2)],
        "hfov": round(math.degrees(2 * math.atan(18 / lens)), 2),
    }
views_path.write_text(json.dumps(views, indent=1, ensure_ascii=False) + "\n")
print("ok", sys.argv[1:])
