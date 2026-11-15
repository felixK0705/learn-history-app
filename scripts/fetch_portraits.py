"""為人物關係圖抓取維基百科肖像（多為公有領域畫像），輸出 src/data/portraits.json"""
import json, os, re, time, urllib.parse, urllib.request, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "TimeloreEducational/1.0 (non-commercial history learning site)"}
src = open(os.path.join(ROOT, "src/data/figures.ts"), encoding="utf-8").read()
people = re.findall(r'\{ id: "([^"]+)", name: "[^"]+", englishName: "([^"]+)"', src)
# 維基條目名稱需特別指定者
TITLE = {
    "brutus": "Marcus Junius Brutus", "crassus": "Marcus Licinius Crassus", "pompey": "Pompey",
    "zhangliang": "Zhang Liang (Western Han)", "xunzi": "Xunzi (philosopher)", "wellington": "Arthur Wellesley, 1st Duke of Wellington",
    "liubang": "Emperor Gaozu of Han", "qinshihuang": "Qin Shi Huang", "laozi": "Laozi", "augustus": "Augustus",
    "verrocchio": "Andrea del Verrocchio", "julius2": "Pope Julius II", "lorenzo": "Lorenzo de' Medici",
}


def get(url, tries=6):
    for i in range(tries):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(4 * (i + 1)); continue
            raise
        except Exception:
            time.sleep(2 * (i + 1))
    raise RuntimeError(url)


titles = {pid: TITLE.get(pid, en) for pid, en in people}
out = {}
items = list(titles.items())
for k in range(0, len(items), 40):
    batch = items[k : k + 40]
    q = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "redirects": 1, "prop": "pageimages",
        "piprop": "thumbnail|name", "pithumbsize": 320, "titles": "|".join(t for _, t in batch)})
    d = get(q)
    alias = {n["from"]: n["to"] for n in d["query"].get("normalized", []) + d["query"].get("redirects", [])}
    pages = {p["title"]: p for p in d["query"]["pages"].values()}
    names = {}
    for pid, t in batch:
        t2 = alias.get(alias.get(t, t), alias.get(t, t))
        p = pages.get(t2)
        if p and p.get("thumbnail") and not re.search(r"(map|flag|svg|signature|seal|coat)", p.get("pageimage", ""), re.I):
            out[pid] = {"src": p["thumbnail"]["source"].split("?")[0], "file": p["pageimage"], "page": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(t2.replace(' ', '_'))}"}
            names[p["pageimage"]] = pid
    time.sleep(1.2)
    if names:
        q = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "format": "json", "prop": "imageinfo", "iiprop": "extmetadata",
            "titles": "|".join("File:" + n for n in names)})
        d = get(q)
        for p in d["query"]["pages"].values():
            em = (p.get("imageinfo") or [{}])[0].get("extmetadata", {})
            fname = p["title"].removeprefix("File:").replace(" ", "_")
            pid = names.get(fname)
            if not pid:
                continue
            artist = html.unescape(re.sub(r"<[^>]+>", "", em.get("Artist", {}).get("value", ""))).strip()[:50]
            lic = html.unescape(re.sub(r"<[^>]+>", "", em.get("LicenseShortName", {}).get("value", ""))).strip()
            out[pid]["credit"] = "・".join(x for x in (artist, lic, "Wikimedia Commons") if x)
        time.sleep(1.2)
json.dump(out, open(os.path.join(ROOT, "src/data/portraits.json"), "w"), ensure_ascii=False, indent=1)
print(len(out), "/", len(people), "missing:", [pid for pid, _ in people if pid not in out])
