import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ChevronDown, Globe2, Minus, Plus, Scan, Search, X } from "lucide-react";
import { figures, groups, REL_TYPE, relationColors, relations, type RelationType } from "../data/figures";
import { countryByIso, countryName } from "../data/world";
import { useFigures } from "../data/localized";
import { useLang, useT } from "../lib/i18n";
import { formatYear } from "../lib/format";
import { gsap, prefersReducedMotion, useGSAP, useReveal } from "../lib/motion";
import portraitData from "../data/portraits.json";
import AiFiguresMode from "../components/ai/AiFiguresMode";

const portraits = portraitData as Record<string, { src: string; page: string; credit?: string }>;

/*
 * 人物關係圖
 * - 總覽：九個時代群組如星座般由左（古代）到右（近代）沿弧線排列，群內以葉序（向日葵）排列
 * - 聚焦：點選人物後轉為同心圓：本人在中央、直接關係人物環繞，連線上標示關係類型
 */

type Pt = { x: number; y: number };
const figureById = new Map(figures.map((f) => [f.id, f]));
const groupById = new Map(groups.map((g) => [g.id, g]));
const relationTypes = Object.keys(relationColors) as RelationType[];

const neighbors = (() => {
  const m = new Map<string, { id: string; type: RelationType; ri: number }[]>();
  relations.forEach((r, ri) => {
    if (!m.has(r.source)) m.set(r.source, []);
    if (!m.has(r.target)) m.set(r.target, []);
    m.get(r.source)!.push({ id: r.target, type: r.type, ri });
    m.get(r.target)!.push({ id: r.source, type: r.type, ri });
  });
  return m;
})();

// ---------- 總覽版面（固定座標系 1600 × 900） ----------
const W = 2000;
const H = 1340;

function medianBorn(gid: string) {
  const ys = figures.filter((f) => f.group === gid).map((f) => f.born).sort((a, b) => a - b);
  return ys[Math.floor(ys.length / 2)] ?? 0;
}
const groupOrder = [...groups].sort((a, b) => medianBorn(a.id) - medianBorn(b.id));
// 依年代由左至右、由上而下排成網格（每列 COLS 個時代）
const COLS = 5;
const ROWS = Math.ceil(groups.length / COLS);
const groupCenters = new Map<string, Pt>(
  groupOrder.map((g, i) => {
    const col = i % COLS;
    const row = Math.floor(i / COLS);
    return [g.id, { x: (W / COLS) * (col + 0.5), y: (H / ROWS) * (row + 0.42) }];
  }),
);
const degree = new Map(figures.map((f) => [f.id, relations.filter((r) => r.source === f.id || r.target === f.id).length]));
const nodeR = (id: string) => 13 + Math.min(degree.get(id) ?? 0, 8) * 1.6;
const overview = new Map<string, Pt>();
groupOrder.forEach((g) => {
  const c = groupCenters.get(g.id)!;
  figures
    .filter((f) => f.group === g.id)
    .sort((a, b) => a.born - b.born)
    .forEach((f, k) => {
      const r = 30 * Math.sqrt(k + 0.4);
      const a = k * 2.39996;
      overview.set(f.id, { x: c.x + r * Math.cos(a), y: c.y + r * Math.sin(a) });
    });
});


function egoLayout(center: string): Map<string, Pt> {
  const out = new Map<string, Pt>();
  const cx = W / 2 - 120;
  const cy = H / 2;
  out.set(center, { x: cx, y: cy });
  // 只顯示直接相關的人物，圍成一圈；人數多時圈加大，避免重疊
  const ring = [...new Set((neighbors.get(center) ?? []).map((n) => n.id))];
  const R = Math.max(300, (ring.length * 95) / (2 * Math.PI));
  ring.forEach((id, i) => {
    const a = -Math.PI / 2 + (i / ring.length) * Math.PI * 2;
    out.set(id, { x: cx + Math.cos(a) * R, y: cy + Math.sin(a) * R });
  });
  // 其他人移到畫面外（淡出）
  figures.forEach((f) => {
    if (out.has(f.id)) return;
    const p = overview.get(f.id)!;
    const dx = p.x - cx;
    const dy = p.y - cy;
    const d = Math.hypot(dx, dy) || 1;
    out.set(f.id, { x: cx + (dx / d) * 1600, y: cy + (dy / d) * 1100 });
  });
  return out;
}

function curve(a: Pt, b: Pt, bend = 0.16) {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  return {
    d: `M${a.x},${a.y} Q${mx - dy * bend},${my + dx * bend} ${b.x},${b.y}`,
    mid: { x: mx - dy * bend * 0.5, y: my + dx * bend * 0.5 },
  };
}

export default function FiguresPage() {
  const [params, setParams] = useSearchParams();
  const lang = useLang();
  const t = useT();
  // 顯示文字依語言替換；版面座標仍以原始資料計算
  const loc = useFigures();
  const fig = useMemo(() => new Map(loc.figures.map((f) => [f.id, f])), [loc]);
  const gName = useMemo(() => new Map(loc.groups.map((g) => [g.id, g.name])), [loc]);
  const focusId = params.get("focus");
  const focus = focusId ? fig.get(focusId) ?? null : null;
  const [hover, setHover] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [types, setTypes] = useState<Set<RelationType>>(() => new Set(relationTypes));

  // 版面切換：以 GSAP 補間每個節點的位置
  const [pos, setPos] = useState<Map<string, Pt>>(overview);
  const posRef = useRef(pos);
  posRef.current = pos;
  const target = useMemo(() => (focusId && figureById.has(focusId) ? egoLayout(focusId) : overview), [focusId]);

  useGSAP(
    () => {
      const from = new Map(posRef.current);
      if (prefersReducedMotion()) {
        setPos(target);
        return;
      }
      const st = { t: 0 };
      gsap.to(st, {
        t: 1,
        duration: 1.1,
        ease: "expo.inOut",
        onUpdate: () => {
          const m = new Map<string, Pt>();
          target.forEach((p, id) => {
            const f = from.get(id) ?? p;
            m.set(id, { x: f.x + (p.x - f.x) * st.t, y: f.y + (p.y - f.y) * st.t });
          });
          setPos(m);
        },
      });
    },
    { dependencies: [target] },
  );

  // 平移與縮放
  const svgRef = useRef<SVGSVGElement>(null);
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const viewRef = useRef(view);
  viewRef.current = view;
  const viewTo = useCallback((v: { x: number; y: number; k: number }) => {
    const st = { ...viewRef.current };
    gsap.to(st, { ...v, duration: 0.9, ease: "power3.inOut", onUpdate: () => setView({ ...st }) });
  }, []);
  useEffect(() => {
    if (!focusId) return;
    // 聚焦時放大到關係圈約佔畫面高度的三分之二，圓心留在右側面板左邊
    const n = new Set((neighbors.get(focusId) ?? []).map((x) => x.id)).size;
    const R = Math.max(300, (n * 95) / (2 * Math.PI));
    const k = Math.min(1.8, (H * 0.36) / R);
    viewTo({ x: 120 * k - 120, y: 0, k });
  }, [focusId, viewTo]);
  const drag = useRef<{ x: number; y: number; vx: number; vy: number; moved: boolean } | null>(null);

  const key = hover ?? focusId;
  const lit = useMemo(() => (key ? new Set([key, ...(neighbors.get(key) ?? []).map((n) => n.id)]) : null), [key]);

  const hits = useMemo(() => {
    const s = query.trim().toLowerCase();
    if (!s) return [];
    return loc.figures.filter((f) => `${f.name}${f.englishName}${f.role}`.toLowerCase().includes(s)).slice(0, 7);
  }, [query, loc]);

  const select = (id: string | null) => setParams(id ? { focus: id } : {}, { replace: true });

  const asideRef = useRef<HTMLElement>(null);
  const detailRef = useRef<HTMLElement>(null);
  useReveal(asideRef, [], { stagger: "[data-reveal]", y: 12, each: 0.03, duration: 0.6 });
  useReveal(detailRef, [focusId], { stagger: "[data-reveal]", x: 20, y: 0, each: 0.04, duration: 0.55 });

  const egoMode = !!focus;

  return (
    <div className="absolute inset-0 overflow-hidden">
      <AiFiguresMode />
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        className="absolute inset-x-0 top-[62px] h-[calc(100%-62px)] w-full cursor-grab touch-none select-none active:cursor-grabbing"
        onWheel={(e) => {
          const k = Math.min(3, Math.max(0.6, view.k * (e.deltaY < 0 ? 1.1 : 0.9)));
          setView((v) => ({ ...v, k }));
        }}
        onPointerDown={(e) => {
          drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y, moved: false };
        }}
        onPointerMove={(e) => {
          const d = drag.current;
          if (!d || !svgRef.current) return;
          const scale = W / svgRef.current.clientWidth;
          if (Math.hypot(e.clientX - d.x, e.clientY - d.y) > 3) d.moved = true;
          setView((v) => ({ ...v, x: d.vx + (e.clientX - d.x) * scale, y: d.vy + (e.clientY - d.y) * scale }));
        }}
        onPointerUp={(e) => {
          const d = drag.current;
          drag.current = null;
          if (d && !d.moved && e.target === svgRef.current) select(null);
        }}
      >
        <defs>
          <clipPath id="node-clip" clipPathUnits="objectBoundingBox">
            <circle cx="0.5" cy="0.5" r="0.5" />
          </clipPath>
          <radialGradient id="star-glow">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.9" />
            <stop offset="45%" stopColor="#bfe9ff" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#bfe9ff" stopOpacity="0" />
          </radialGradient>
        </defs>
        <g transform={`translate(${W / 2 + view.x} ${H / 2 + view.y}) scale(${view.k}) translate(${-W / 2} ${-H / 2})`}>
          {/* 星座名稱與年代（總覽） */}
          {!egoMode &&
            groupOrder.map((g) => {
              const c = groupCenters.get(g.id)!;
              const members = figures.filter((f) => f.group === g.id);
              const yrs = members.map((m) => m.born);
              const faded = lit && !members.some((m) => lit.has(m.id));
              return (
                <g key={g.id} opacity={faded ? 0.3 : 1} className="transition-opacity duration-500">
                  <circle cx={c.x} cy={c.y} r={135} fill="url(#star-glow)" opacity={0.16} />
                  <text x={c.x} y={c.y + 142} textAnchor="middle" fill="#ffffff" fontSize={15} fontWeight={600} letterSpacing="0.02em">
                    {gName.get(g.id)}
                  </text>
                  <text x={c.x} y={c.y + 161} textAnchor="middle" fill="rgba(255,255,255,0.5)" fontSize={11}>
                    {formatYear(Math.min(...yrs), lang)} – {formatYear(Math.max(...yrs), lang)}
                  </text>
                </g>
              );
            })}

          {/* 關係連線（曲線） */}
          {relations
            .filter((r) => types.has(r.type))
            .map((r) => {
              const a = pos.get(r.source);
              const b = pos.get(r.target);
              if (!a || !b) return null;
              const on = !!key && (r.source === key || r.target === key);
              const { d, mid } = curve(a, b);
              return (
                <g key={`${r.source}-${r.target}`}>
                  <path
                    d={d}
                    fill="none"
                    stroke={relationColors[r.type]}
                    strokeOpacity={on ? 0.95 : key ? 0.05 : 0.38}
                    strokeWidth={on ? 2.6 : 1.3}
                    strokeDasharray={r.type === "影響" ? "4 5" : undefined}
                    strokeLinecap="round"
                  />
                  {egoMode && on && hover !== null && (
                    <g transform={`translate(${mid.x} ${mid.y})`}>
                      {(() => {
                        const label = t(REL_TYPE[r.type]);
                        const w = 26 + label.length * (lang === "en" ? 8 : 14);
                        return (
                          <>
                            <rect x={-w / 2} y={-14} width={w} height={28} rx={14} fill="#ffffff" />
                            <circle cx={-w / 2 + 14} cy={0} r={4.5} fill={relationColors[r.type]} />
                            <text x={7} y={5} textAnchor="middle" fontSize={14} fontWeight={600} fill="#1d5a80">
                              {label}
                            </text>
                          </>
                        );
                      })()}
                    </g>
                  )}
                </g>
              );
            })}

          {/* 人物（發光星點） */}
          {figures.map((f) => {
            const p = pos.get(f.id);
            if (!p) return null;
            const g = groupById.get(f.group)!;
            const isFocus = f.id === focusId;
            const inRing = egoMode && !!lit?.has(f.id);
            const dim = lit && !lit.has(f.id);
            const r = isFocus ? 58 : inRing ? 32 : nodeR(f.id);
            const showName = isFocus || inRing || f.id === hover || (!!lit && lit.has(f.id)) || view.k > 1.4;
            return (
              <g
                key={f.id}
                transform={`translate(${p.x} ${p.y})`}
                opacity={dim ? (egoMode ? 0 : 0.25) : 1}
                className="cursor-pointer transition-opacity duration-300"
                onPointerEnter={() => setHover(f.id)}
                onPointerLeave={() => setHover(null)}
                onPointerUp={(e) => {
                  e.stopPropagation();
                  if (!drag.current?.moved) select(f.id);
                  drag.current = null;
                }}
              >
                <circle r={r * 1.9} fill="url(#star-glow)" opacity={isFocus ? 0.6 : 0.3} />
                <circle r={r + (isFocus ? 4 : 2.5)} fill={g.color} />
                <circle r={r} fill="#dbe9ff" />
                {portraits[f.id] ? (
                  <image href={portraits[f.id].src} x={-r} y={-r} width={r * 2} height={r * 2} preserveAspectRatio="xMidYMin slice" clipPath="url(#node-clip)" />
                ) : (
                  <text textAnchor="middle" y={r * 0.36} fontWeight={600} fill="#1d5a80" fontSize={r * 0.95}>
                    {(fig.get(f.id)?.name ?? f.name)[0]}
                  </text>
                )}
                {showName && (
                  <text
                    textAnchor="middle"
                    y={r + (isFocus ? 30 : 20)}
                    fill="#ffffff"
                    fontSize={isFocus ? 21 : inRing ? 16 : 14}
                    fontWeight={isFocus ? 600 : 500}
                    style={{ paintOrder: "stroke", stroke: "rgba(11,58,150,0.9)", strokeWidth: 4, strokeLinejoin: "round" }}
                  >
                    {fig.get(f.id)?.name ?? f.name}
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      {/* 左側：搜尋、時代星座、關係類型 */}
      <aside ref={asideRef} className="absolute top-[78px] left-4 z-20 w-[min(300px,calc(100%-2rem))] md:left-[104px]">
        <div className="rounded-2xl border border-white/15 bg-[#0f3049]/85 p-3 shadow-[0_20px_50px_-20px_rgba(4,18,30,0.7)] backdrop-blur-xl">
        <div className="flex items-center justify-between gap-2 px-1">
          <h1 className="text-[17px] font-semibold tracking-tight">{t({ "zh-TW": "人物關係", en: "Historical figures", ja: "人物相関図" })}</h1>
          <span className="text-[11.5px] text-white/60 tabular-nums">
            {t({ "zh-TW": `${figures.length} 人・${relations.length} 條關係`, en: `${figures.length} people · ${relations.length} links`, ja: `${figures.length} 人・${relations.length} 件の関係` })}
          </span>
        </div>
        <label className="mt-2.5 flex h-9 items-center gap-2 rounded-full border border-white/15 bg-white/8 px-3.5">
          <Search className="size-[15px] text-white/55" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t({ "zh-TW": "搜尋人物", en: "Search people", ja: "人物を検索" })} className="min-w-0 flex-1 bg-transparent text-[13px] outline-none placeholder:text-white/40" />
        </label>
        {hits.length > 0 && (
          <ul className="mt-2 space-y-0.5">
            {hits.map((f) => (
              <li key={f.id}>
                <button
                  onClick={() => {
                    select(f.id);
                    setQuery("");
                  }}
                  className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-[13px] hover:bg-white/10"
                >
                  <span className="size-2 rounded-full" style={{ background: groupById.get(f.group)?.color }} />
                  {f.name}
                  <span className="ml-auto truncate text-[11px] text-white/50">{f.role}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <button
          onClick={() => setFiltersOpen((v) => !v)}
          className="mt-2 flex w-full items-center justify-between rounded-xl px-2 py-1.5 text-[12.5px] text-white/80 hover:bg-white/8"
          aria-expanded={filtersOpen}
        >
          {t({ "zh-TW": "時代與關係篩選", en: "Filter by era and relation", ja: "時代と関係で絞り込む" })}
          <ChevronDown className={`size-4 transition ${filtersOpen ? "rotate-180" : ""}`} />
        </button>
        {filtersOpen && (
        <div className="scroll-thin max-h-[60vh] overflow-y-auto px-1 pb-1">
        <p className="eyebrow mt-3 mb-2">
          {t({ "zh-TW": "時代星座", en: "Eras", ja: "時代" })}
        </p>
        <ul className="space-y-0.5">
          {groupOrder.map((g) => (
            <li key={g.id}>
              <button
                onClick={() => {
                  select(null);
                  const c = groupCenters.get(g.id)!;
                  viewTo({ x: (W / 2 - c.x) * 2.2, y: (H / 2 - c.y) * 2.2, k: 2.2 });
                }}
                className="flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left text-[13px] transition hover:bg-white/10"
              >
                <span className="size-2.5 rounded-full ring-2 ring-white/30" style={{ background: g.color }} />
                <span className="flex-1">{gName.get(g.id)}</span>
                <span className="text-[11px] text-white/45 tabular-nums">{figures.filter((f) => f.group === g.id).length}</span>
              </button>
            </li>
          ))}
        </ul>
        <p className="eyebrow mt-4 mb-2">
          {t({ "zh-TW": "關係類型", en: "Relation types", ja: "関係の種類" })}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {relationTypes.map((rt) => (
            <button
              key={rt}
              onClick={() =>
                setTypes((s) => {
                  const n = new Set(s);
                  if (n.has(rt)) n.delete(rt);
                  else n.add(rt);
                  return n;
                })
              }
              className={`chip ${types.has(rt) ? "chip-on" : ""}`}
            >
              <span className="size-2 rounded-full" style={{ background: relationColors[rt] }} />
              {t(REL_TYPE[rt])}
            </button>
          ))}
        </div>
        </div>
        )}
        </div>
      </aside>

      {/* 縮放控制 */}
      <div className="absolute bottom-5 left-1/2 z-20 flex -translate-x-1/2 gap-2">
        <button className="icon-btn" onClick={() => setView((v) => ({ ...v, k: Math.min(3, v.k * 1.25) }))} aria-label={t({ "zh-TW": "放大", en: "Zoom in", ja: "拡大" })}>
          <Plus className="size-4" />
        </button>
        <button className="icon-btn" onClick={() => setView((v) => ({ ...v, k: Math.max(0.6, v.k / 1.25) }))} aria-label={t({ "zh-TW": "縮小", en: "Zoom out", ja: "縮小" })}>
          <Minus className="size-4" />
        </button>
        <button
          className="icon-btn"
          onClick={() => {
            select(null);
            viewTo({ x: 0, y: 0, k: 1 });
          }}
          aria-label={t({ "zh-TW": "顯示全部", en: "Show all", ja: "全体を表示" })}
        >
          <Scan className="size-4" />
        </button>
      </div>

      {/* 右側：人物詳細 */}
      {focus && (
        <aside
          ref={detailRef}
          className="absolute top-[78px] right-4 bottom-4 z-20 flex w-[300px] flex-col overflow-hidden rounded-[24px] border border-white/15 bg-[#0f3049]/88 shadow-[0_24px_60px_-20px_rgba(4,18,30,0.75)] backdrop-blur-xl max-md:inset-x-3 max-md:top-auto max-md:max-h-[55%] max-md:w-auto"
        >
          <button onClick={() => select(null)} className="absolute top-3 right-3 z-30 grid size-8 place-items-center rounded-full bg-[#0f3049]/80 text-white/90 ring-1 ring-white/25 hover:bg-[#174560]" aria-label={t({ "zh-TW": "關閉", en: "Close", ja: "閉じる" })} title={t({ "zh-TW": "關閉", en: "Close", ja: "閉じる" })}>
            <X className="size-4" />
          </button>
          {portraits[focus.id] && (
            <figure className="relative h-40 shrink-0 overflow-hidden">
              <img src={portraits[focus.id].src} alt={focus.name} className="size-full object-cover object-top" />
              <div className="absolute inset-0 bg-[linear-gradient(180deg,transparent_45%,rgba(13,42,64,0.95))]" />
              {portraits[focus.id].credit && (
                <a href={portraits[focus.id].page} target="_blank" rel="noreferrer" className="absolute right-3 bottom-2 max-w-[80%] truncate text-[10px] text-white/60 hover:text-white">
                  {portraits[focus.id].credit}
                </a>
              )}
            </figure>
          )}
          <div className="relative shrink-0 px-5 pt-4 pb-3">
            <p data-reveal className="eyebrow">
              {gName.get(focus.group)}
            </p>
            <h2 data-reveal className="mt-1 text-[28px] leading-tight font-semibold tracking-tight">
              {focus.name}
            </h2>
            {lang !== "en" && (
              <p data-reveal className="text-[13px] text-white/55">
                {focus.englishName}
              </p>
            )}
            <div data-reveal className="mt-3 flex flex-wrap gap-1.5">
              <span className="chip">{focus.role}</span>
              <span className="chip tabular-nums">
                {formatYear(focus.born, lang)} – {formatYear(focus.died, lang)}
              </span>
            </div>
            <p data-reveal className="mt-4 text-[13.5px] leading-relaxed text-white/85">
              {focus.bio}
            </p>
            {countryByIso.has(focus.iso) && (
              <Link data-reveal to={`/?country=${focus.iso}`} className="mt-3 inline-flex items-center gap-1.5 text-[13px] text-white/80 hover:text-white">
                <Globe2 className="size-4" />
                {(() => {
                  const n = countryName(countryByIso.get(focus.iso)!, lang);
                  return t({ "zh-TW": `在地球上看${n}的歷史`, en: `See the history of ${n} on the globe`, ja: `地球で${n}の歴史を見る` });
                })()}
              </Link>
            )}
          </div>
          <div className="scroll-thin min-h-0 flex-1 overflow-y-auto border-t border-white/10 px-4 py-4">
            <p data-reveal className="eyebrow mb-2 px-2">
              {(() => {
                const n = (neighbors.get(focus.id) ?? []).length;
                return t({ "zh-TW": `關係（${n}）`, en: `Relations (${n})`, ja: `関係（${n}）` });
              })()}
            </p>
            <ul className="space-y-1">
              {(neighbors.get(focus.id) ?? []).map((n) => {
                const o = fig.get(n.id)!;
                return (
                  <li key={n.id} data-reveal>
                    <button
                      onClick={() => select(n.id)}
                      onPointerEnter={() => setHover(n.id)}
                      onPointerLeave={() => setHover(null)}
                      className="flex w-full items-start gap-3 rounded-2xl px-2 py-2.5 text-left transition hover:bg-white/10"
                    >
                      <span className="mt-0.5 inline-flex shrink-0 items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[10.5px] font-semibold text-deep-800">
                        <span className="size-1.5 rounded-full" style={{ background: relationColors[n.type] }} />
                        {t(REL_TYPE[n.type])}
                      </span>
                      <span className="min-w-0">
                        <span className="block text-[14px] font-medium">{o.name}</span>
                        <span className="block text-[12px] leading-snug text-white/60">{loc.relations[n.ri].label}</span>
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
  );
}
