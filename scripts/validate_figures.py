"""驗證 src/data/figures.ts：關係端點存在、無重複／自環，並印出人物數、關係數、關係數統計與群組人數"""
import re, sys, statistics, collections
import os
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src/data/figures.ts")
src = open(path, encoding="utf-8").read()
figs = re.findall(r'\{ id: "([^"]+)", name: "([^"]+)", englishName: "([^"]+)",.*?group: "([^"]+)"', src)
groups = re.findall(r'\{ id: "([^"]+)", name: "([^"]+)", color: "([^"]+)" \}', src)
rels = re.findall(r'\{ source: "([^"]+)", target: "([^"]+)", type: "([^"]+)", label: "([^"]+)" \}', src)
ids = [f[0] for f in figs]
idset = set(ids)
errs = []
for i, c in collections.Counter(ids).items():
    if c > 1: errs.append(f"重複人物 id: {i}")
gids = {g[0] for g in groups}
for f in figs:
    if f[3] not in gids: errs.append(f"未知群組 {f[3]} ({f[0]})")
cols = collections.Counter(g[2].lower() for g in groups)
for c, n in cols.items():
    if n > 1: errs.append(f"重複群組顏色 {c}")
types = {"師徒","親屬","盟友","敵對","君臣","影響","戀人"}
pairs = collections.Counter()
deg = collections.Counter()
for s, t, ty, lb in rels:
    if s not in idset: errs.append(f"關係來源不存在: {s} -> {t}")
    if t not in idset: errs.append(f"關係目標不存在: {s} -> {t}")
    if s == t: errs.append(f"自己連自己: {s}")
    if ty not in types: errs.append(f"未知關係類型 {ty}")
    pairs[frozenset((s, t))] += 1
    deg[s] += 1; deg[t] += 1
for p, c in pairs.items():
    if c > 1: errs.append(f"重複關係: {' <-> '.join(sorted(p))} x{c}")
ds = [deg[i] for i in ids]
print("人物數:", len(ids))
print("關係數:", len(rels))
print("每人關係數 最小值:", min(ds), " 中位數:", statistics.median(ds), " 最大值:", max(ds))
print("群組人數:")
gc = collections.Counter(f[3] for f in figs)
for g in groups: print(f"  {g[1]}（{g[0]}）: {gc[g[0]]}")
low = sorted((deg[i], i) for i in ids if deg[i] < 6)
if low: print("少於 6 條關係:", ", ".join(f"{i}={d}" for d, i in low))
if len(sys.argv) > 2:
    for i in sys.argv[2].split(","): print(i, deg[i])
print("錯誤:" if errs else "檢查通過：無錯誤")
for e in errs: print("  ", e)
sys.exit(1 if errs else 0)
