"""從 Poly Haven（CC0）下載建模所需的 1K PBR 材質到 blender/textures/<id>/"""
import json
import os
import sys
import time
import urllib.request

UA = {"User-Agent": "TimeloreEducational/1.0"}
ROOT = os.path.join(os.path.dirname(__file__), "textures")
MAPS = {"Diffuse": "diff", "nor_gl": "nor", "arm": "arm"}


def get(url):
    for i in range(5):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        except Exception:
            time.sleep(2 * (i + 1))
    raise RuntimeError(url)


def fetch(asset, res="1k", only=None):
    out = os.path.join(ROOT, asset)
    os.makedirs(out, exist_ok=True)
    files = json.loads(get(f"https://api.polyhaven.com/files/{asset}"))
    for key, short in MAPS.items():
        if only and short not in only:
            continue
        path = os.path.join(out, f"{short}.jpg")
        if os.path.exists(path):
            continue
        open(path, "wb").write(get(files[key][res]["jpg"]["url"]))
    print("ok", asset)


if __name__ == "__main__":
    only = None
    args = sys.argv[1:]
    if args and args[0] == "--diff-only":
        only, args = {"diff"}, args[1:]
    for a in args:
        fetch(a, only=only)
