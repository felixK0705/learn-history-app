import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, LoaderCircle, Search, Sparkles, UserRound, X } from "lucide-react";
import { gsap, prefersReducedMotion, useGSAP, useReveal } from "../../lib/motion";
import { AiError, postAi } from "../../lib/ai";
import { findPortrait, findPortraits } from "../../lib/wikiImage";

export type AiRelType = "敵對" | "盟友" | "師徒" | "親屬" | "君臣" | "影響" | "戀人";
export type AiNode = { id: string; name: string; group: string; val: number; description: string };
export type AiLink = { source: string; target: string; label: string; type: AiRelType };
export type AiGraph = { introduction: string; nodes: AiNode[]; links: AiLink[] };

/** 與館藏人物關係圖一致的配色 */
const AI_REL_COLORS: Record<AiRelType, string> = {
  師徒: "#7dd3fc",
  親屬: "#fbbf24",
  盟友: "#4ade80",
  敵對: "#f87171",
  君臣: "#c084fc",
  影響: "#94a3b8",
  戀人: "#f472b6",
};

const PANEL =
  "border border-white/15 bg-[#071d4f]/78 shadow-[0_24px_60px_-20px_rgba(0,10,40,0.7),inset_0_1px_0_rgba(255,255,255,0.18)] backdrop-blur-xl";

/** 勢力／陣營配色（柔和亮色，與主題協調） */
const GROUP_COLORS = ["#38bdf8", "#f472b6", "#fbbf24", "#34d399", "#a78bfa", "#fb923c"];

const EXAMPLES = ["諸葛亮", "凱撒", "拿破崙", "武則天", "織田信長", "伊莉莎白一世"];

const W = 1000;
const H = 720;
const CX = W / 2;
const CY = H / 2;

type Pt = { x: number; y: number };

/** 主角置中；與主角直接相連者在內圈，其他人在外圈；同勢力相鄰 */
function layout(g: AiGraph): Map<string, Pt> {
  const pos = new Map<string, Pt>();
  const center = g.nodes[0]?.id;
  if (!center) return pos;
  pos.set(center, { x: CX, y: CY });
  const direct = new Set(g.links.flatMap((l) => (l.source === center ? [l.target] : l.target === center ? [l.source] : [])));
  const others = g.nodes.slice(1);
  const order = [...others].sort((a, b) => a.group.localeCompare(b.group, "zh-Hant") || b.val - a.val);
  const inner = order.filter((n) => direct.has(n.id));
  const outer = order.filter((n) => !direct.has(n.id));
  // 人數少時全部放同一圈
  const rings = outer.length && inner.length >= 4 ? [inner, outer] : [[...inner, ...outer]];
  rings.forEach((ring, ri) => {
    const rx = rings.length === 1 ? 340 : ri === 0 ? 255 : 400;
    const ry = rings.length === 1 ? 255 : ri === 0 ? 195 : 300;
    const offset = -Math.PI / 2 + (ri === 1 ? Math.PI / ring.length : 0);
    ring.forEach((n, i) => {
      const a = offset + (i / ring.length) * Math.PI * 2;
      pos.set(n.id, { x: CX + Math.cos(a) * rx, y: CY + Math.sin(a) * ry });
    });
  });
  return pos;
}

/** 周邊人物之間的連線稍微彎曲，避免全部穿過中心 */
function path(a: Pt, b: Pt, bend: number) {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const cx = mx - dy * bend;
  const cy = my + dx * bend;
  return { d: `M${a.x},${a.y} Q${cx},${cy} ${b.x},${b.y}`, mid: { x: 0.25 * a.x + 0.5 * cx + 0.25 * b.x, y: 0.25 * a.y + 0.5 * cy + 0.25 * b.y } };
}

const radius = (n: AiNode, isCenter: boolean) => (isCenter ? 52 : 22 + Math.min(10, Math.max(1, n.val)) * 1.2);

export default function AiRelationshipGraph({ initialQuery = "" }: { initialQuery?: string }) {
  const [query, setQuery] = useState(initialQuery);
  const [graph, setGraph] = useState<AiGraph | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<AiError | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const ctl = useRef<AbortController | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const sideRef = useRef<HTMLDivElement>(null);
  const examplesRef = useRef<HTMLDivElement>(null);

  const run = async (name: string) => {
    const q = name.trim();
    if (!q) return;
    setQuery(q);
    ctl.current?.abort();
    const c = new AbortController();
    ctl.current = c;
    setLoading(true);
    setError(null);
    setPicked(null);
    try {
      const g = await postAi<AiGraph>("relationships", { name: q }, c.signal);
      if (c.signal.aborted) return;
      if (!g.nodes?.length) throw new AiError(`找不到「${q}」的人物關係資料`);
      setGraph(g);
    } catch (e) {
      if (c.signal.aborted) return;
      setError(e instanceof AiError ? e : new AiError("查詢失敗，請稍後再試。"));
    } finally {
      if (ctl.current === c) setLoading(false);
    }
  };

  const [portraits, setPortraits] = useState<Record<string, string>>({});
  useEffect(() => {
    if (!graph) return;
    let alive = true;
    setPortraits({});
    // 先以條目名稱一次批次查詢；查不到的再個別搜尋
    findPortraits(graph.nodes.map((n) => n.name)).then((byName) => {
      if (!alive) return;
      const found: Record<string, string> = {};
      graph.nodes.forEach((n) => byName[n.name] && (found[n.id] = byName[n.name]));
      setPortraits(found);
      graph.nodes
        .filter((n) => !found[n.id])
        .forEach((n) =>
          findPortrait(n.name).then((src) => {
            if (alive && src) setPortraits((m) => ({ ...m, [n.id]: src }));
          }),
        );
    });
    return () => {
      alive = false;
    };
  }, [graph]);
  const groupColor = useMemo(() => {
    const m = new Map<string, string>();
    (graph?.nodes ?? []).forEach((n) => {
      if (!m.has(n.group)) m.set(n.group, GROUP_COLORS[m.size % GROUP_COLORS.length]);
    });
    return m;
  }, [graph]);
  const pos = useMemo(() => (graph ? layout(graph) : new Map<string, Pt>()), [graph]);
  const byId = useMemo(() => new Map(graph?.nodes.map((n) => [n.id, n]) ?? []), [graph]);
  const center = graph?.nodes[0];
  const key = hover ?? picked;
  const lit = useMemo(() => {
    if (!key || !graph) return null;
    const s = new Set([key]);
    graph.links.forEach((l) => (l.source === key ? s.add(l.target) : l.target === key && s.add(l.source)));
    return s;
  }, [key, graph]);
  const pickedNode = picked ? byId.get(picked) : null;
  const pickedLinks = graph && picked ? graph.links.filter((l) => l.source === picked || l.target === picked) : [];
  const types = useMemo(() => [...new Set(graph?.links.map((l) => l.type) ?? [])], [graph]);

  // 圖形進場：連線描繪、節點彈出
  useGSAP(
    () => {
      if (!graph || prefersReducedMotion() || !svgRef.current) return;
      const tl = gsap.timeline();
      tl.fromTo(svgRef.current.querySelectorAll("[data-node]"), { scale: 0, autoAlpha: 0, transformOrigin: "50% 50%" }, { scale: 1, autoAlpha: 1, duration: 0.55, stagger: 0.04, ease: "back.out(1.7)" });
      svgRef.current.querySelectorAll<SVGPathElement>("[data-link]").forEach((p) => {
        const len = p.getTotalLength();
        tl.fromTo(p, { strokeDasharray: len, strokeDashoffset: len }, { strokeDashoffset: 0, duration: 0.8, ease: "power2.out", clearProps: "strokeDasharray,strokeDashoffset" }, 0.25);
      });
      tl.fromTo(svgRef.current.querySelectorAll("[data-label]"), { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.4, stagger: 0.02 }, 0.7);
    },
    { dependencies: [graph] },
  );
  useReveal(sideRef, [graph, picked], { stagger: "[data-reveal]", y: 10, each: 0.05 });
  useReveal(examplesRef, [], { stagger: "button", y: 8, each: 0.04, delay: 0.1 });

  return (
    <div className="absolute inset-0 flex flex-col gap-3 p-3 md:p-4">
      {/* 搜尋列 */}
      <form
        className={`${PANEL} mx-auto flex w-full max-w-[640px] shrink-0 items-center gap-2 rounded-full py-1.5 pr-1.5 pl-4`}
        onSubmit={(e) => {
          e.preventDefault();
          run(query);
        }}
      >
        <Sparkles className="size-4 shrink-0 text-glow" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="輸入任何歷史人物，例如：曹操、克麗奧佩脫拉…"
          maxLength={60}
          className="min-w-0 flex-1 bg-transparent text-[14px] text-white outline-none placeholder:text-white/45"
          aria-label="要查詢的歷史人物"
        />
        <button
          type="submit"
          disabled={!query.trim() || loading}
          className="flex h-9 shrink-0 items-center gap-1.5 rounded-full bg-white px-4 text-[13px] font-semibold text-deep-800 transition hover:bg-glow disabled:bg-white/25 disabled:text-white/60"
        >
          {loading ? <LoaderCircle className="size-4 animate-spin" /> : <Search className="size-4" />}
          {loading ? "生成中" : "AI 查詢"}
        </button>
      </form>

      <div className="flex min-h-0 flex-1 flex-col gap-3 lg:flex-row">
        {/* 圖 */}
        <div className="relative min-h-[300px] flex-1 overflow-hidden">
          {!graph && !loading && !error && (
            <div className="absolute inset-0 grid place-items-center p-6 text-center">
              <div>
                <span className="mx-auto grid size-14 place-items-center rounded-full bg-white/10 ring-1 ring-white/20">
                  <UserRound className="size-7 text-glow" />
                </span>
                <p className="mt-4 text-lg font-bold">AI 查詢任意人物</p>
                <p className="mx-auto mt-1.5 max-w-sm text-[13.5px] leading-relaxed text-white/70">輸入任何一位歷史人物，AI 會整理出與他最相關的 10–15 位人物與彼此的關係。</p>
                <div ref={examplesRef} className="mt-5 flex flex-wrap justify-center gap-2">
                  {EXAMPLES.map((n) => (
                    <button key={n} onClick={() => run(n)} className="chip text-[13px]">
                      {n}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {loading && (
            <div className="absolute inset-0 z-10 grid place-items-center bg-[#071d4f]/50 backdrop-blur-[2px]">
              <div className="flex flex-col items-center gap-3 text-[14px] text-white/85">
                <LoaderCircle className="size-9 animate-spin text-glow" />
                AI 正在整理「{query}」的人物關係…
              </div>
            </div>
          )}

          {error && !loading && (
            <div className="absolute inset-0 z-10 grid place-items-center p-6">
              <div className="max-w-sm rounded-2xl border border-amber-300/35 bg-[#071d4f]/90 p-5 text-center">
                <AlertTriangle className="mx-auto size-7 text-amber-300" />
                <p className="mt-2 text-[14px] leading-relaxed text-amber-50">{error.message}</p>
                {!error.disabled && (
                  <button onClick={() => run(query)} className="mt-3 rounded-full bg-white px-4 py-1.5 text-[13px] font-semibold text-deep-800 hover:bg-glow">
                    再試一次
                  </button>
                )}
              </div>
            </div>
          )}

          {graph && (
            <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet" className="absolute inset-0 size-full select-none" onClick={(e) => e.target === e.currentTarget && setPicked(null)}>
              <defs>
                <radialGradient id="ai-disc" cx="50%" cy="30%" r="75%">
                  <stop offset="0%" stopColor="#ffffff" />
                  <stop offset="100%" stopColor="#d6ecff" />
                </radialGradient>
                <radialGradient id="ai-center" cx="50%" cy="35%" r="70%">
                  <stop offset="0%" stopColor="#ffffff" />
                  <stop offset="100%" stopColor="#a6e1ff" />
                </radialGradient>
              </defs>
              <circle cx={CX} cy={CY} r={250} fill="none" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 8" />
              {/* 連線 */}
              {graph.links.map((l, i) => {
                const a = pos.get(l.source);
                const b = pos.get(l.target);
                if (!a || !b) return null;
                const touchesCenter = l.source === center?.id || l.target === center?.id;
                const { d } = path(a, b, touchesCenter ? 0 : 0.18);
                const on = !lit || (lit.has(l.source) && lit.has(l.target) && (l.source === key || l.target === key));
                return <path key={i} data-link d={d} fill="none" stroke={lit && on ? AI_REL_COLORS[l.type] : "#ffffff"} strokeWidth={on && lit ? 2.5 : 1.5} strokeOpacity={lit ? (on ? 0.95 : 0.08) : 0.45} strokeLinecap="round" className="transition-[stroke-opacity]" />;
              })}
              {/* 連線標籤 */}
              {graph.links.map((l, i) => {
                const a = pos.get(l.source);
                const b = pos.get(l.target);
                if (!a || !b) return null;
                const touchesCenter = l.source === center?.id || l.target === center?.id;
                const { mid } = path(a, b, touchesCenter ? 0 : 0.18);
                // 與主角的連線：標籤放在靠外側，避開中央大圓
                const p = touchesCenter ? { x: a.x + (b.x - a.x) * (l.source === center?.id ? 0.6 : 0.4), y: a.y + (b.y - a.y) * (l.source === center?.id ? 0.6 : 0.4) } : mid;
                const focusEdge = lit && (l.source === key || l.target === key);
                // 預設只標示與主角的關係；滑過或點選人物時才顯示他的其他關係，避免標籤擠成一團
                const show = lit ? focusEdge : touchesCenter;
                if (!show) return null;
                const w = l.label.length * 12 + 26;
                return (
                  <g key={i} data-label transform={`translate(${p.x},${p.y})`} className="pointer-events-none">
                    <rect x={-w / 2} y={-10.5} width={w} height={21} rx={10.5} fill="#ffffff" fillOpacity={0.95} />
                    <circle cx={-w / 2 + 10} cy={0} r={3.5} fill={AI_REL_COLORS[l.type]} />
                    <text x={6} textAnchor="middle" dy={4.2} fontSize={11.5} fontWeight={700} fill="#0b3282">
                      {l.label}
                    </text>
                  </g>
                );
              })}
              {/* 節點 */}
              {graph.nodes.map((n, i) => {
                const p = pos.get(n.id);
                if (!p) return null;
                const isCenter = i === 0;
                const r = radius(n, isCenter);
                const dim = lit && !lit.has(n.id);
                return (
                  <g
                    key={n.id}
                    transform={`translate(${p.x},${p.y})`}
                    className="cursor-pointer"
                    opacity={dim ? 0.25 : 1}
                    onPointerEnter={() => setHover(n.id)}
                    onPointerLeave={() => setHover(null)}
                    onClick={() => setPicked((v) => (v === n.id ? null : n.id))}
                  >
                    <g data-node>
                      <clipPath id={`ai-clip-${i}`}>
                        <circle r={r - 2} />
                      </clipPath>
                      {(isCenter || picked === n.id) && <circle r={r + 7} fill="none" stroke="#ffffff" strokeOpacity={0.55} strokeWidth={2} />}
                      <circle r={r + 3} fill="none" stroke={groupColor.get(n.group) ?? "#fff"} strokeWidth={2.5} />
                      <circle r={r} fill="url(#ai-disc)" />
                      {portraits[n.id] ? (
                        <image href={portraits[n.id]} x={-(r - 2)} y={-(r - 2)} width={(r - 2) * 2} height={(r - 2) * 2} preserveAspectRatio="xMidYMin slice" clipPath={`url(#ai-clip-${i})`} />
                      ) : (
                        <text textAnchor="middle" dy={isCenter ? 10 : 6} fontSize={isCenter ? 28 : 17} fontWeight={700} fill="#0b3a8f">
                          {n.name.slice(0, 1)}
                        </text>
                      )}
                      <text textAnchor="middle" y={r + 18} fontSize={isCenter ? 18 : 14} fontWeight={700} fill="#fff" stroke="rgba(6,25,74,0.55)" strokeWidth={3} paintOrder="stroke">
                        {n.name}
                      </text>
                      {n.description && (
                        <text textAnchor="middle" y={r + (isCenter ? 36 : 33)} fontSize={11} fill="rgba(255,255,255,0.78)" stroke="rgba(6,25,74,0.5)" strokeWidth={2.5} paintOrder="stroke">
                          {n.description}
                        </text>
                      )}
                    </g>
                  </g>
                );
              })}
            </svg>
          )}

          {graph && types.length > 0 && (
            <div className="pointer-events-none absolute bottom-3 left-3 flex max-w-[calc(100%-1.5rem)] flex-wrap items-center gap-x-3 gap-y-1 rounded-2xl bg-[#06194a]/80 px-3 py-2 text-[11.5px] text-white/85">
              {[...groupColor].map(([g, c]) => (
                <span key={g} className="flex items-center gap-1.5">
                  <span className="size-2.5 rounded-full" style={{ background: c }} />
                  {g}
                </span>
              ))}
              <span className="h-3 w-px bg-white/25" />
              {types.map((t) => (
                <span key={t} className="flex items-center gap-1.5">
                  <span className="h-[3px] w-4 rounded-full" style={{ background: AI_REL_COLORS[t] }} />
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* 簡介／人物詳情 */}
        {graph && center && (
          <aside ref={sideRef} className={`${PANEL} scroll-thin flex shrink-0 flex-col self-start overflow-y-auto rounded-[22px] p-5 max-lg:max-h-[38%] lg:max-h-full lg:w-[290px]`}>
            {portraits[(pickedNode ?? center).id] && (
              <img src={portraits[(pickedNode ?? center).id]} alt="" className="mb-4 h-36 w-full rounded-2xl object-cover object-top" />
            )}
            {pickedNode ? (
              <>
                <div data-reveal className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-[11px] font-semibold tracking-[0.12em] text-glow uppercase">{pickedNode.group}</p>
                    <h3 className="mt-1 text-xl font-bold">{pickedNode.name}</h3>
                    {pickedNode.description && <p className="mt-0.5 text-[13px] text-white/70">{pickedNode.description}</p>}
                  </div>
                  <button onClick={() => setPicked(null)} className="grid size-8 shrink-0 place-items-center rounded-full text-white/70 hover:bg-white/10 hover:text-white" aria-label="返回簡介" title="返回簡介">
                    <X className="size-4" />
                  </button>
                </div>
                <ul className="mt-4 space-y-2">
                  {pickedLinks.map((l, i) => {
                    const other = byId.get(l.source === pickedNode.id ? l.target : l.source);
                    return (
                      <li key={i} data-reveal className="flex items-center gap-2.5 rounded-xl border border-white/10 bg-white/6 px-3 py-2 text-[13.5px]">
                        <span className="size-2.5 shrink-0 rounded-full" style={{ background: AI_REL_COLORS[l.type] }} />
                        <span className="font-semibold">{other?.name}</span>
                        <span className="ml-auto text-right text-white/75">{l.label}</span>
                      </li>
                    );
                  })}
                </ul>
                {pickedNode.id !== center.id && (
                  <button data-reveal onClick={() => run(pickedNode.name)} className="mt-4 flex items-center justify-center gap-1.5 rounded-full bg-white px-4 py-2 text-[13px] font-semibold text-deep-800 hover:bg-glow">
                    <Sparkles className="size-4" />
                    以「{pickedNode.name}」為中心查詢
                  </button>
                )}
              </>
            ) : (
              <>
                <p data-reveal className="text-[11px] font-semibold tracking-[0.12em] text-glow uppercase">
                  AI 人物簡介
                </p>
                <h3 data-reveal className="mt-1 text-xl font-bold">
                  {center.name}
                </h3>
                {center.description && (
                  <p data-reveal className="mt-0.5 text-[13px] text-white/70">
                    {center.description}
                  </p>
                )}
                <p data-reveal className="mt-3 text-[14px] leading-[1.8] text-white/90">
                  {graph.introduction || "（AI 沒有提供簡介）"}
                </p>
                <p data-reveal className="mt-4 text-[12px] leading-relaxed text-white/55">
                  點選圖中人物查看關係；內容由 AI 生成，可能有誤。
                </p>
              </>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}
