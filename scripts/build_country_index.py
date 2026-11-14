"""從舊專案的歷史資料建立國家索引與時間線資料檔。

輸入：舊專案 backend/fastapi/history_data（路徑由第一個參數指定）
輸出：public/data/history/{ISO3}.json、src/data/countryIndex.json
"""
import glob
import json
import os
import sys

SRC = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
geo = json.load(open(os.path.join(ROOT, "public/data/countries.json"), encoding="utf-8", errors="replace"))
zh = json.load(open(os.path.join(ROOT, "scripts/out/zh-names.json")))
a2 = json.load(open(os.path.join(ROOT, "scripts/out/a2.json")))
pop = {f["properties"]["iso_a3"]: f["properties"].get("pop_est") or 0 for f in geo["features"]}

name_to_iso = {f["properties"]["name"]: f["properties"]["iso_a3"] for f in geo["features"]}
shapes = {f["properties"]["iso_a3"]: f for f in geo["features"]}
manual = {
    "Saudi_Arabia": "SAU", "North Korea": "PRK", "South Korea": "KOR", "East Timor": "TLS", "Laos": "LAO",
    "North Macedonia": "MKD", "Bosnia and Herzegovina": "BIH", "Czechia": "CZE", "Dominican Republic": "DOM",
    "Côte d'Ivoire": "CIV", "Republic of the Congo": "COG", "Central African Republic": "CAF",
    "Democratic Republic of the Congo": "COD", "São Tomé and Príncipe": "STP", "Equatorial Guinea": "GNQ",
    "Eswatini": "SWZ", "South Sudan": "SSD", "Western Sahara": "ESH", "Solomon Islands": "SLB", "Kiribati": "KIR",
    "Federated States of Micronesia": "FSM", "Marshall Islands": "MHL", "Palau": "PLW", "Nauru": "NRU", "Tuvalu": "TUV",
    "Singapore": "SGP", "Maldives": "MDV", "Malta": "MLT", "Bahrain": "BHR", "Monaco": "MCO", "Liechtenstein": "LIE",
    "San Marino": "SMR", "Vatican City": "VAT", "Andorra": "AND", "Barbados": "BRB", "Mauritius": "MUS",
    "Seychelles": "SYC", "Comoros": "COM", "Cape Verde": "CPV", "Samoa": "WSM", "Tonga": "TON", "Saint Lucia": "LCA",
    "Grenada": "GRD", "Saint Vincent and the Grenadines": "VCT", "Antigua and Barbuda": "ATG", "Dominica": "DMA",
    "Saint Kitts and Nevis": "KNA", "Kosovo": "XKX", "Somaliland": "SOL", "N. Cyprus": "CYN",
}
# 無國界形狀或標籤需手動定位的國家 [lat, lng]
points = {
    "SGP": [1.35, 103.82], "MDV": [3.2, 73.5], "MLT": [35.94, 14.38], "BHR": [26.04, 50.55], "MCO": [43.74, 7.42],
    "LIE": [47.16, 9.55], "SMR": [43.94, 12.46], "VAT": [41.903, 12.455], "AND": [42.55, 1.6], "BRB": [13.19, -59.54],
    "MUS": [-20.28, 57.55], "SYC": [-4.68, 55.5], "COM": [-11.88, 43.87], "CPV": [16.0, -23.6], "WSM": [-13.76, -172.1],
    "TON": [-21.18, -175.2], "LCA": [13.91, -60.98], "GRD": [12.12, -61.68], "VCT": [12.98, -61.29], "ATG": [17.36, -61.8],
    "DMA": [15.42, -61.37], "KNA": [17.26, -62.7], "KIR": [1.87, -157.36], "FSM": [6.92, 158.16], "MHL": [7.1, 171.18],
    "PLW": [7.5, 134.6], "NRU": [-0.53, 166.93], "TUV": [-8.52, 179.2], "STP": [0.19, 6.61],
    "USA": [39.8, -98.5], "CAN": [56.0, -96.0], "RUS": [61.5, 100.0], "FRA": [46.5, 2.5], "FJI": [-17.7, 178.0],
    "NOR": [61.5, 9.0], "CHL": [-33.0, -70.8], "IDN": [-2.0, 117.0], "JPN": [36.5, 138.5], "ITA": [42.5, 12.6],
    "VNM": [16.5, 106.5], "LAO": [18.5, 103.0], "NZL": [-41.5, 172.5], "GRL": [72.0, -40.0], "MYS": [3.5, 102.0],
    "PHL": [12.5, 122.5], "GBR": [53.0, -1.8], "HRV": [45.3, 16.0], "ARG": [-35.0, -65.0], "AUS": [-25.0, 134.0],
}
continent_zh = {"Asia": "亞洲", "Europe": "歐洲", "Africa": "非洲", "North_America": "北美洲", "Central_America_Caribbean": "北美洲",
                "South_America": "南美洲", "Oceania": "大洋洲"}
cat_zh = {"Ancient": "上古", "Classical": "古典", "Medieval": "中世紀", "Early Modern": "近世", "Modern": "近代", "Contemporary": "當代",
          "Prehistoric": "上古", "Late Antiquity": "上古", "Colonial": "近世", "Independence": "近代", "Revolutionary": "近代",
          "Post-Independence": "當代", "Authoritarian": "當代", "Military Coups": "當代", "Democratic Transition": "當代",
          "Security Crisis": "當代", "Culture": "", "Science": "", "Religion": ""}


def bbox_center(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    # 取面積最大的多邊形
    def area(ring):
        return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:]))) / 2
    best = max(polys, key=lambda p: area(p[0]))
    xs = [p[0] for p in best[0]]
    ys = [p[1] for p in best[0]]
    return [round((min(ys) + max(ys)) / 2, 3), round((min(xs) + max(xs)) / 2, 3)]


os.makedirs(os.path.join(ROOT, "public/data/history"), exist_ok=True)
index = []
for path in sorted(glob.glob(os.path.join(SRC, "continents/**/*.json"), recursive=True)):
    d = json.load(open(path))
    en = d["country"]
    iso = manual.get(en) or name_to_iso.get(en)
    if not iso or iso == "-99":
        print("skip", en)
        continue
    cont = os.path.relpath(path, os.path.join(SRC, "continents")).split(os.sep)[0]
    events = d["languages"].get("zh-TW", [])
    pos = points.get(iso) or (bbox_center(shapes[iso]["geometry"]) if iso in shapes else None)
    if pos is None:
        print("no position", en, iso)
        continue
    out = []
    last = "上古"
    for e in events:
        # 未對應的主題型分類（文化、科學、宗教）沿用前一則事件的時代
        era = cat_zh.get(e.get("category"), "") or last
        last = era
        out.append({"year": e["year"], "title": e["title"], "description": e["description"], "era": era})
    json.dump({"iso": iso, "events": out}, open(os.path.join(ROOT, f"public/data/history/{iso}.json"), "w"), ensure_ascii=False)
    index.append({
        "iso": iso, "en": en.replace("_", " "), "zh": zh.get(iso, en), "continent": continent_zh[cont],
        "iso2": a2.get(iso, ""), "pos": pos, "shape": iso in shapes, "events": len(out), "pop": int(pop.get(iso, 0)),
    })
# 標籤優先順序：人口越多越先顯示
for rank, c in enumerate(sorted(index, key=lambda c: -c["pop"])):
    c["rank"] = rank
    del c["pop"]
json.dump(sorted(index, key=lambda c: c["iso"]), open(os.path.join(ROOT, "src/data/countryIndex.json"), "w"), ensure_ascii=False, separators=(",", ":"))
print(len(index), "countries", sum(c["events"] for c in index), "events")
