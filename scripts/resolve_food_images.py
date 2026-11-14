"""為 public/data/profile/*.json 的美食補上維基百科代表照片（Wikimedia Commons，含作者與授權）。

用法：python3 scripts/resolve_food_images.py
"""
import glob
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "TimeloreEducational/1.0 (non-commercial history learning site)"}
BAD = re.compile(r"(map|flag|logo|icon|coat_of_arms|locator|\.svg|\.gif|diagram|chart)", re.I)


def get_json(url, tries=6):
    for i in range(tries):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(4 * (i + 1))
                continue
            raise
        except Exception:
            time.sleep(2 * (i + 1))
    raise RuntimeError(url)


def chunks(xs, n):
    for i in range(0, len(xs), n):
        yield xs[i : i + n]


def strip_html(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "public/data/profile/*.json")))
    profiles = {f: json.load(open(f)) for f in files}
    titles = sorted({it["wiki"] for p in profiles.values() for it in p.get("food", {}).get("ranking", []) if it.get("wiki")})
    print(len(titles), "titles")

    # 1) 條目 → 主圖（縮圖網址與檔名）
    page_img = {}
    for batch in chunks(titles, 40):
        q = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "redirects": 1, "prop": "pageimages",
            "piprop": "thumbnail|name", "pithumbsize": 900, "titles": "|".join(batch),
        })
        d = get_json(q)
        alias = {}
        for n in d["query"].get("normalized", []) + d["query"].get("redirects", []):
            alias[n["from"]] = n["to"]
        found = {p["title"]: p for p in d["query"]["pages"].values()}
        for t in batch:
            tt = alias.get(t, t)
            tt = alias.get(tt, tt)
            p = found.get(tt)
            if p and p.get("thumbnail") and p.get("pageimage") and not BAD.search(p["pageimage"]):
                page_img[t] = (p["thumbnail"]["source"].split("?")[0], p["pageimage"])
        time.sleep(1.2)
    print(len(page_img), "with images")

    # 2) 檔案 → 作者與授權
    meta = {}
    names = sorted({v[1] for v in page_img.values()})
    for batch in chunks(names, 40):
        q = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "prop": "imageinfo", "iiprop": "extmetadata|url",
            "titles": "|".join("File:" + n for n in batch),
        })
        try:
            d = get_json(q)
        except RuntimeError:
            continue
        for p in d["query"]["pages"].values():
            info = (p.get("imageinfo") or [{}])[0]
            em = info.get("extmetadata", {})
            name = p["title"].removeprefix("File:").replace(" ", "_")
            artist = strip_html(em.get("Artist", {}).get("value"))[:60]
            lic = strip_html(em.get("LicenseShortName", {}).get("value"))
            meta[name] = (artist, lic, info.get("descriptionurl"))
        time.sleep(1.2)

    # 3) 寫回
    n_img = 0
    for f, p in profiles.items():
        for it in p.get("food", {}).get("ranking", []):
            hit = page_img.get(it.get("wiki", ""))
            if not hit:
                for k in ("image", "imagePage", "imageCredit"):
                    it.pop(k, None)
                continue
            url, name = hit
            artist, lic, page = meta.get(name.replace(" ", "_"), ("", "", None))
            it["image"] = url
            it["imagePage"] = page or f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(name)}"
            parts = [x for x in (artist, lic) if x]
            it["imageCredit"] = "・".join(parts + ["Wikimedia Commons"])
            n_img += 1
        json.dump(p, open(f, "w"), ensure_ascii=False, indent=1)
    print(n_img, "food items with photos")


if __name__ == "__main__":
    main()
