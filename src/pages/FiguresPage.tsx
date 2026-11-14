import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import ForceGraph2D, { type ForceGraphMethods, type LinkObject, type NodeObject } from "react-force-graph-2d";
import { Globe2, Maximize2, Search, SlidersHorizontal, X } from "lucide-react";
import { figures, groups, relationColors, relations, type Figure, type RelationType } from "../data/figures";
import { countryByIso } from "../data/countries";
import { formatYear } from "../lib/format";
import { useReveal } from "../lib/motion";

type GNode = NodeObject<Figure & { color: string }>;
type GLink = LinkObject<GNode, { type: RelationType; label: string }>;

const groupColor = new Map(groups.map((g) => [g.id, g.color]));
const relationTypes = Object.keys(relationColors) as RelationType[];
const figureById = new Map(figures.map((f) => [f.id, f]));

function endId(end: GLink["source"]): string {
  return typeof end === "object" ? String((end as GNode).id) : String(end);
}

export default function FiguresPage() {
  const [params, setParams] = useSearchParams();
  const focusId = params.get("focus");
  const wrapRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<ForceGraphMethods<GNode, GLink> | undefined>(undefined);
  const [size, setSize] = useState({ w: 800, h: 600 });
  const [activeGroups, setActiveGroups] = useState<Set<string>>(() => new Set(groups.map((g) => g.id)));
  const [activeTypes, setActiveTypes] = useState<Set<RelationType>>(() => new Set(relationTypes));
  const [hoverId, setHoverId] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const asideRef = useRef<HTMLElement>(null);
  const detailRef = useRef<HTMLElement>(null);
  const hitsRef = useRef<HTMLUListElement>(null);
  const filtersRef = useRef<HTMLDivElement>(null);

  // 若從其他頁面帶入人物，確保其群組顯示
  useEffect(() => {
    const f = focusId ? figureById.get(focusId) : null;
    if (f && !activeGroups.has(f.group)) setActiveGroups((s) => new Set(s).add(f.group));
  }, [focusId, activeGroups]);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: el.clientHeight }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const data = useMemo(() => {
    const nodes: GNode[] = figures
      .filter((f) => activeGroups.has(f.group))
      .map((f) => ({ ...f, color: groupColor.get(f.group) ?? "#fff" }));
    const ids = new Set(nodes.map((n) => n.id));
    const links: GLink[] = relations
      .filter((r) => activeTypes.has(r.type) && ids.has(r.source) && ids.has(r.target))
      .map((r) => ({ ...r }));
    return { nodes, links };
  }, [activeGroups, activeTypes]);

  const neighbors = useMemo(() => {
    const m = new Map<string, Set<string>>();
    relations.forEach((r) => {
      if (!m.has(r.source)) m.set(r.source, new Set());
      if (!m.has(r.target)) m.set(r.target, new Set());
      m.get(r.source)!.add(r.target);
      m.get(r.target)!.add(r.source);
    });
    return m;
  }, []);

  const highlightId = hoverId ?? focusId;
  const isLit = useCallback(
    (id: string) => !highlightId || id === highlightId || neighbors.get(highlightId)?.has(id),
    [highlightId, neighbors],
  );

  const searchHits = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return figures.filter((f) => `${f.name}${f.englishName}${f.role}`.toLowerCase().includes(q)).slice(0, 8);
  }, [query]);

  const focusNode = useCallback(
    (id: string | null) => {
      if (!id) {
        setParams({}, { replace: true });
        return;
      }
      setParams({ focus: id }, { replace: true });
    },
    [setParams],
  );

  // 聚焦時將鏡頭移到人物
  useEffect(() => {
    if (!focusId) return;
    const t = setTimeout(() => {
      const n = data.nodes.find((x) => x.id === focusId);
      if (n && n.x != null && n.y != null) {
        fgRef.current?.centerAt(n.x, n.y, 800);
        fgRef.current?.zoom(2.4, 800);
      }
    }, 350);
    return () => clearTimeout(t);
  }, [focusId, data]);

  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    fg.d3Force("charge")?.strength(-160);
    (fg.d3Force("link") as unknown as { distance?: (d: number) => void })?.distance?.(55);
  }, [data]);

  const selected = focusId ? figureById.get(focusId) : null;
  const selectedRelations = useMemo(
    () => (focusId ? relations.filter((r) => r.source === focusId || r.target === focusId) : []),
    [focusId],
  );

  useReveal(asideRef, [], { stagger: ":scope > *, :scope section > div > *", y: 14, each: 0.025, duration: 0.5 });
  useReveal(detailRef, [selected?.id], { stagger: ":scope > div > *, :scope li", x: 24, y: 0, each: 0.04, duration: 0.5 });
  useReveal(hitsRef, [searchHits.length > 0], { y: -8, duration: 0.3 });
  useReveal(filtersRef, [filtersOpen], { y: -12, duration: 0.35 });

  const toggle = <T,>(set: Set<T>, v: T) => {
    const s = new Set(set);
    if (s.has(v)) s.delete(v);
    else s.add(v);
    return s;
  };

  const filters = (
    <>
      <section>
        <h3 className="mb-2 text-xs tracking-widest text-mute">時代群組</h3>
        <div className="flex flex-wrap gap-1.5">
          {groups.map((g) => (
            <button
              key={g.id}
              className={`chip ${activeGroups.has(g.id) ? "chip-on" : "opacity-60"}`}
              onClick={() => setActiveGroups((s) => toggle(s, g.id))}
            >
              <span className="size-2 rounded-full" style={{ background: g.color }} />
              {g.name}
            </button>
          ))}
        </div>
        <div className="mt-2 flex gap-3 text-[11px]">
          <button className="text-glow hover:underline" onClick={() => setActiveGroups(new Set(groups.map((g) => g.id)))}>
            全選
          </button>
          <button className="text-mute hover:underline" onClick={() => setActiveGroups(new Set())}>
            全不選
          </button>
        </div>
      </section>
      <section className="mt-5">
        <h3 className="mb-2 text-xs tracking-widest text-mute">關係類型</h3>
        <div className="flex flex-wrap gap-1.5">
          {relationTypes.map((t) => (
            <button
              key={t}
              className={`chip ${activeTypes.has(t) ? "chip-on" : "opacity-60"}`}
              onClick={() => setActiveTypes((s) => toggle(s, t))}
            >
              <span className="h-0.5 w-3 rounded" style={{ background: relationColors[t] }} />
              {t}
            </button>
          ))}
        </div>
      </section>
    </>
  );

  return (
    <div className="absolute inset-0 flex">
      {/* 左側控制面板 */}
      <aside ref={asideRef} className="scroll-thin relative z-10 hidden w-72 shrink-0 overflow-y-auto border-r border-white/10 bg-deep-950/30 p-5 lg:block">
        <h1 className="font-serif text-2xl font-bold">歷史人物關係圖</h1>
        <p className="mt-1 text-sm text-mute">
          {figures.length} 位人物、{relations.length} 條關係。滑過人物可看到與其相連的人，點擊查看詳細介紹。
        </p>
        <div className="mt-5">{filters}</div>
      </aside>

      <div ref={wrapRef} className="relative min-w-0 flex-1">
        <ForceGraph2D<GNode, GLink>
          ref={fgRef}
          width={size.w}
          height={size.h}
          graphData={data}
          backgroundColor="rgba(0,0,0,0)"
          cooldownTicks={120}
          onEngineStop={() => {
            if (!focusId) fgRef.current?.zoomToFit(600, 60);
          }}
          nodeRelSize={6}
          nodeLabel={(n) => `${n.name}（${n.role}）`}
          onNodeHover={(n) => {
            setHoverId(n ? String(n.id) : null);
            if (wrapRef.current) wrapRef.current.style.cursor = n ? "pointer" : "grab";
          }}
          onNodeClick={(n) => focusNode(String(n.id))}
          onBackgroundClick={() => focusNode(null)}
          linkColor={(l) => {
            const lit = !highlightId || endId(l.source) === highlightId || endId(l.target) === highlightId;
            return lit ? relationColors[l.type] : "rgba(255,255,255,0.05)";
          }}
          linkWidth={(l) =>
            highlightId && (endId(l.source) === highlightId || endId(l.target) === highlightId) ? 2.5 : 1.2
          }
          linkLineDash={(l) => (l.type === "影響" ? [3, 3] : null)}
          linkDirectionalParticles={(l) => (l.type === "師徒" || l.type === "影響" ? 2 : 0)}
          linkDirectionalParticleWidth={2}
          linkDirectionalParticleColor={(l) => relationColors[l.type]}
          nodeCanvasObject={(node, ctx, scale) => {
            const id = String(node.id);
            const lit = isLit(id);
            const isFocus = id === highlightId;
            const r = isFocus ? 9 : 7;
            const x = node.x ?? 0;
            const y = node.y ?? 0;
            ctx.globalAlpha = lit ? 1 : 0.15;
            if (isFocus) {
              ctx.beginPath();
              ctx.arc(x, y, r + 5, 0, 2 * Math.PI);
              ctx.fillStyle = `${node.color}40`;
              ctx.fill();
            }
            ctx.beginPath();
            ctx.arc(x, y, r, 0, 2 * Math.PI);
            ctx.fillStyle = node.color;
            ctx.fill();
            ctx.lineWidth = 1.5 / scale;
            ctx.strokeStyle = "rgba(255,255,255,0.85)";
            ctx.stroke();
            ctx.fillStyle = "#031033";
            ctx.font = `bold ${r}px "Noto Serif TC", serif`;
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(node.name[0], x, y + 0.5);
            if (scale > 1.1 || isFocus || (highlightId && lit)) {
              const fs = Math.max(11 / scale, 3.2);
              ctx.font = `500 ${fs}px "Noto Sans TC", sans-serif`;
              ctx.fillStyle = "rgba(232,243,255,0.95)";
              ctx.fillText(node.name, x, y + r + fs * 0.9);
            }
            ctx.globalAlpha = 1;
          }}
          nodePointerAreaPaint={(node, color, ctx) => {
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(node.x ?? 0, node.y ?? 0, 10, 0, 2 * Math.PI);
            ctx.fill();
          }}
        />

        {/* 搜尋 */}
        <div className="absolute top-4 left-4 z-10 w-[min(280px,calc(100%-6rem))]">
          <label className="glass flex h-10 items-center gap-2 rounded-full px-3">
            <Search className="size-4 text-mute" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜尋人物…"
              className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-mute/70"
            />
          </label>
          {searchHits.length > 0 && (
            <ul ref={hitsRef} className="glass mt-2 overflow-hidden rounded-2xl p-1">
              {searchHits.map((f) => (
                <li key={f.id}>
                  <button
                    className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm hover:bg-white/10"
                    onClick={() => {
                      focusNode(f.id);
                      setQuery("");
                    }}
                  >
                    <span className="size-2 rounded-full" style={{ background: groupColor.get(f.group) }} />
                    {f.name}
                    <span className="ml-auto truncate text-xs text-mute">{f.role}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="absolute top-4 right-4 z-10 flex gap-2">
          <button className="icon-btn lg:hidden" onClick={() => setFiltersOpen((v) => !v)} aria-label="篩選">
            <SlidersHorizontal className="size-4" />
          </button>
          <button className="icon-btn" onClick={() => fgRef.current?.zoomToFit(600, 60)} aria-label="顯示全部" title="顯示全部">
            <Maximize2 className="size-4" />
          </button>
        </div>

        {filtersOpen && (
          <div ref={filtersRef} className="glass absolute inset-x-4 top-16 z-20 rounded-2xl p-4 lg:hidden">{filters}</div>
        )}

        {/* 人物詳細 */}
        {selected && (
          <aside
            ref={detailRef}
            className="glass absolute z-20 flex flex-col rounded-3xl shadow-2xl max-md:inset-x-3 max-md:bottom-3 max-md:max-h-[55%] md:top-4 md:right-4 md:bottom-4 md:w-[340px]"
          >
            <div className="relative shrink-0 p-5 pb-3">
              <button className="icon-btn absolute top-4 right-4 !size-8" onClick={() => focusNode(null)} aria-label="關閉">
                <X className="size-4" />
              </button>
              <div className="flex items-center gap-3">
                <span
                  className="grid size-14 shrink-0 place-items-center rounded-full font-serif text-2xl font-bold text-deep-950"
                  style={{ background: groupColor.get(selected.group) }}
                >
                  {selected.name[0]}
                </span>
                <div className="min-w-0 pr-8">
                  <h2 className="font-serif text-xl font-bold">{selected.name}</h2>
                  <p className="truncate text-xs text-mute">{selected.englishName}</p>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5 text-xs">
                <span className="chip !cursor-default">{selected.role}</span>
                <span className="chip !cursor-default">
                  {formatYear(selected.born)} – {formatYear(selected.died)}
                </span>
                <span className="chip !cursor-default">{groups.find((g) => g.id === selected.group)?.name}</span>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-ink/85">{selected.bio}</p>
              {countryByIso.has(selected.iso) && (
                <Link to={`/?country=${selected.iso}`} className="mt-3 inline-flex items-center gap-1.5 text-sm text-glow hover:underline">
                  <Globe2 className="size-4" />
                  在地球上看{countryByIso.get(selected.iso)!.name}的歷史
                </Link>
              )}
            </div>
            <div className="scroll-thin min-h-0 flex-1 overflow-y-auto border-t border-white/10 p-5 pt-3">
              <h3 className="mb-2 text-xs tracking-widest text-mute">關係（{selectedRelations.length}）</h3>
              <ul className="space-y-1.5">
                {selectedRelations.map((r) => {
                  const otherId = r.source === selected.id ? r.target : r.source;
                  const other = figureById.get(otherId)!;
                  return (
                    <li key={`${r.source}-${r.target}`}>
                      <button
                        onClick={() => focusNode(otherId)}
                        className="flex w-full items-start gap-3 rounded-xl px-2 py-2 text-left transition hover:bg-white/[0.06]"
                      >
                        <span
                          className="mt-0.5 shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium text-deep-950"
                          style={{ background: relationColors[r.type] }}
                        >
                          {r.type}
                        </span>
                        <span className="min-w-0">
                          <span className="block text-sm text-white">{other.name}</span>
                          <span className="block text-xs text-mute">{r.label}</span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
