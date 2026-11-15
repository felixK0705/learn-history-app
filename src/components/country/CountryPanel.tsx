import { useEffect, useMemo, useRef, useState } from "react";
import { Search, Volume2, X } from "lucide-react";
import { gsap, prefersReducedMotion, useGSAP, useReveal } from "../../lib/motion";
import Flag from "../ui/Flag";
import { loadHistory, loadProfile, type CountryMeta, type CountryProfile, type HistoryEvent } from "../../data/world";
import { canSpeak, langCodeFor, speak } from "../../lib/speech";

const tabs = [
  { id: "history", label: "歷史" },
  { id: "religion", label: "宗教" },
  { id: "language", label: "語言" },
  { id: "food", label: "美食" },
] as const;
type TabId = (typeof tabs)[number]["id"];

export default function CountryPanel({ country, onClose }: { country: CountryMeta; onClose: () => void }) {
  const [tab, setTab] = useState<TabId>("history");
  const [events, setEvents] = useState<HistoryEvent[] | null>(null);
  const [profile, setProfile] = useState<CountryProfile | null | undefined>(undefined);
  const panelRef = useRef<HTMLElement>(null);
  const headerRef = useRef<HTMLElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const navRef = useRef<HTMLDivElement>(null);
  const pillRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    let alive = true;
    loadHistory(country.iso).then((d) => alive && setEvents(d.events)).catch(() => alive && setEvents([]));
    loadProfile(country.iso).then((d) => alive && setProfile(d)).catch(() => alive && setProfile(null));
    return () => {
      alive = false;
    };
  }, [country.iso]);

  useGSAP(
    () => {
      if (prefersReducedMotion()) return;
      const desktop = window.matchMedia("(min-width: 1024px)").matches;
      gsap.fromTo(
        panelRef.current,
        desktop ? { x: 48, autoAlpha: 0, scale: 0.98 } : { yPercent: 100 },
        desktop ? { x: 0, autoAlpha: 1, scale: 1, duration: 0.8, ease: "expo.out" } : { yPercent: 0, duration: 0.7, ease: "expo.out" },
      );
      gsap.fromTo(headerRef.current!.children, { y: 12, autoAlpha: 0 }, { y: 0, autoAlpha: 1, stagger: 0.06, delay: 0.15, duration: 0.6, clearProps: "all" });
    },
    { scope: panelRef },
  );

  useReveal(contentRef, [tab, !!events, profile === undefined], { stagger: "[data-reveal]", y: 12, each: 0.035, duration: 0.5 });

  // 分段控制的白色滑塊
  useGSAP(
    () => {
      const btn = navRef.current?.querySelector<HTMLElement>(`[data-tab="${tab}"]`);
      if (!btn || !pillRef.current) return;
      gsap.to(pillRef.current, {
        x: btn.offsetLeft,
        width: btn.offsetWidth,
        duration: pillRef.current.dataset.ready ? 0.5 : 0,
        ease: "power3.inOut",
      });
      pillRef.current.dataset.ready = "1";
    },
    { dependencies: [tab] },
  );

  const close = () => {
    if (prefersReducedMotion() || !panelRef.current) return onClose();
    const desktop = window.matchMedia("(min-width: 1024px)").matches;
    gsap.to(panelRef.current, { ...(desktop ? { x: 48, autoAlpha: 0 } : { yPercent: 100 }), duration: 0.35, ease: "power2.in", onComplete: onClose });
  };

  return (
    <aside
      ref={panelRef}
      className="absolute z-30 flex flex-col overflow-hidden border border-white/15 bg-[#06194a]/88 shadow-[0_30px_70px_-25px_rgba(0,10,40,0.8),inset_0_1px_0_rgba(255,255,255,0.18)] backdrop-blur-2xl max-lg:inset-x-2 max-lg:bottom-2 max-lg:h-[64%] max-lg:rounded-[28px] lg:top-4 lg:right-4 lg:bottom-4 lg:w-[440px] lg:rounded-[32px]"
      aria-label={`${country.zh}的歷史與文化`}
    >
      <header ref={headerRef} className="shrink-0 px-6 pt-6 pb-4">
        <div className="flex items-start justify-between gap-3">
          <p className="eyebrow pt-1">
            {country.continent}
            {profile?.capital ? ` · ${profile.capital}` : ""}
          </p>
          <button onClick={close} className="glass-soft -mt-1 -mr-1 grid size-9 place-items-center rounded-full text-white/80 transition hover:bg-white/20 hover:text-white" aria-label="關閉">
            <X className="size-4" />
          </button>
        </div>
        <div className="mt-1 flex items-center gap-3">
          <h2 className="text-[30px] leading-tight font-semibold tracking-tight">{country.zh}</h2>
          <Flag iso2={country.iso2} className="text-[22px]" />
        </div>
        <p className="text-[13px] text-white/55">{country.en}</p>
        {profile?.summary && <p className="mt-3 text-[13.5px] leading-relaxed text-white/85">{profile.summary}</p>}
      </header>

      <div className="shrink-0 px-4 pb-3">
        <div ref={navRef} className="glass-soft relative flex rounded-full p-1" role="tablist">
          <span ref={pillRef} className="absolute top-1 bottom-1 left-0 w-0 rounded-full bg-white shadow-[0_2px_10px_rgba(0,30,90,0.25)]" aria-hidden="true" />
          {tabs.map(({ id, label }) => (
            <button
              key={id}
              data-tab={id}
              role="tab"
              aria-selected={tab === id}
              onClick={() => setTab(id)}
              className={`relative z-10 flex-1 rounded-full px-2 py-1.5 text-[13px] font-medium whitespace-nowrap transition-colors duration-300 ${
                tab === id ? "text-deep-800" : "text-white/70 hover:text-white"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div ref={contentRef} className="scroll-thin min-h-0 flex-1 overflow-y-auto px-6 pt-1 pb-6">
        {tab === "history" && <HistoryTab events={events} />}
        {tab === "religion" && <RankingTab profile={profile} kind="religion" />}
        {tab === "language" && <RankingTab profile={profile} kind="language" />}
        {tab === "food" && <FoodTab profile={profile} />}
      </div>
    </aside>
  );
}

function Skeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="space-y-3" aria-label="載入中">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-16 animate-pulse rounded-2xl bg-white/10" />
      ))}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return <p className="py-10 text-center text-sm text-white/60">{text}</p>;
}

const ERA_ORDER = ["上古", "中世紀", "近世", "近代", "當代"];
/** 每個時代一個辨識色，時間軸、總覽條與標題都用同一色 */
const ERA_COLOR: Record<string, string> = { 上古: "#fbbf24", 中世紀: "#c084fc", 近世: "#34d399", 近代: "#fb7185", 當代: "#38bdf8" };

function HistoryTab({ events }: { events: HistoryEvent[] | null }) {
  const [era, setEra] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  const counts = useMemo(() => {
    const m = new Map<string, number>();
    (events ?? []).forEach((e) => m.set(e.era, (m.get(e.era) ?? 0) + 1));
    return ERA_ORDER.filter((e) => m.has(e)).map((e) => ({ era: e, n: m.get(e)! }));
  }, [events]);
  const total = counts.reduce((s, c) => s + c.n, 0) || 1;

  const groups = useMemo(() => {
    const s = q.trim();
    const list = (events ?? []).filter((e) => (!era || e.era === era) && (!s || e.title.includes(s) || e.description.includes(s) || e.year.includes(s)));
    return ERA_ORDER.map((name) => ({ name, items: list.filter((e) => e.era === name) })).filter((g) => g.items.length);
  }, [events, era, q]);

  if (!events) return <Skeleton />;
  if (!events.length) return <Empty text="這個國家的歷史資料整理中。" />;
  return (
    <div>
      {/* 時代總覽：依事件數比例分段、各時代不同顏色，點擊篩選 */}
      <div data-reveal className="flex gap-1">
        {counts.map((c) => {
          const on = era === null || era === c.era;
          return (
            <button
              key={c.era}
              onClick={() => setEra(era === c.era ? null : c.era)}
              style={{ flexGrow: Math.max(c.n / total, 0.12), flexBasis: 0 }}
              className={`min-w-0 text-left transition-opacity ${on ? "opacity-100" : "opacity-35 hover:opacity-70"}`}
              aria-pressed={era === c.era}
            >
              <span className="block h-2 rounded-full" style={{ background: ERA_COLOR[c.era] }} />
              <span className="mt-1.5 block truncate text-[11.5px] font-semibold" style={{ color: ERA_COLOR[c.era] }}>
                {c.era}
              </span>
              <span className="block text-[10.5px] text-white/55 tabular-nums">{c.n} 則</span>
            </button>
          );
        })}
      </div>

      <div data-reveal className="mt-4 flex h-9 items-center gap-2 rounded-full border border-white/15 bg-white/8 px-3.5">
        <Search className="size-[15px] text-white/60" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={`搜尋 ${events.length} 則事件`}
          className="min-w-0 flex-1 bg-transparent text-[13px] text-white outline-none placeholder:text-white/45"
        />
        {(q || era) && (
          <button onClick={() => { setQ(""); setEra(null); }} className="text-[11px] text-white/70 hover:text-white">
            清除
          </button>
        )}
      </div>

      {groups.map((g) => {
        const color = ERA_COLOR[g.name];
        return (
          <section key={g.name} className="mt-5">
            <header className="sticky top-0 z-10 -mx-6 mb-2 flex items-center gap-2.5 bg-[#06194a] px-6 py-2.5">
              <span className="rounded-full px-2.5 py-0.5 text-[13px] font-bold text-[#06194a]" style={{ background: color }}>
                {g.name}
              </span>
              <span className="text-[12px] text-white/70 tabular-nums">
                {g.items[0].year.replace(/年$/, "")} – {g.items[g.items.length - 1].year.replace(/年$/, "")}・{g.items.length} 則
              </span>
            </header>
            {/* 時間軸：左欄年份、中間軸線與節點、右欄事件 */}
            <ol>
              {g.items.map((e, i) => {
                const key = `${e.year}-${e.title}`;
                const isOpen = open === key;
                const last = i === g.items.length - 1;
                return (
                  <li key={key} data-reveal={i < 8 ? "" : undefined} className="grid grid-cols-[74px_18px_1fr] gap-x-2">
                    <div className="pt-[1px] text-right text-[12.5px] leading-tight font-bold tabular-nums" style={{ color }}>
                      {e.year}
                    </div>
                    <div className="relative flex justify-center">
                      {!last && <span className="absolute top-3 bottom-0 w-[2px] rounded-full" style={{ background: `${color}55` }} />}
                      <span
                        className="relative z-[1] mt-[3px] size-[11px] rounded-full border-2"
                        style={{ borderColor: color, background: isOpen ? color : "#06194a" }}
                      />
                    </div>
                    <button className="block pb-5 text-left" onClick={() => setOpen(isOpen ? null : key)} aria-expanded={isOpen}>
                      <span className="block text-[15px] leading-snug font-semibold text-white">{e.title}</span>
                      <span className={`mt-1 block text-[13px] leading-[1.7] text-white/75 ${isOpen ? "" : "line-clamp-2"}`}>{e.description}</span>
                    </button>
                  </li>
                );
              })}
            </ol>
          </section>
        );
      })}
      {!groups.length && <Empty text="找不到符合的事件" />}
    </div>
  );
}

/** 圓餅圖色票（已用色盲檢查工具驗證，深色面板上可區分），依排名固定順序，第 7 項起併入「其他」灰色 */
const PIE_COLORS = ["#0284c7", "#d97706", "#ec4899", "#8b5cf6", "#059669", "#ea580c"];
const OTHER_COLOR = "#64748b";

function Donut({ items, title }: { items: { name: string; percent: number }[]; title: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const top = items.slice(0, 6).map((it, i) => ({ ...it, color: PIE_COLORS[i] }));
  const used = top.reduce((s, it) => s + it.percent, 0);
  const rest = Math.max(0, 100 - used);
  const slices = rest >= 0.5 ? [...top, { name: "其他／未統計", percent: rest, color: OTHER_COLOR }] : top;
  const sum = slices.reduce((s, it) => s + it.percent, 0) || 1;
  const R = 62, r = 40, C = 80;
  let acc = 0;
  const arc = (a0: number, a1: number) => {
    const p = (a: number, rad: number) => [C + rad * Math.sin(a), C - rad * Math.cos(a)];
    const large = a1 - a0 > Math.PI ? 1 : 0;
    const [x0, y0] = p(a0, R), [x1, y1] = p(a1, R), [x2, y2] = p(a1, r), [x3, y3] = p(a0, r);
    return `M${x0} ${y0}A${R} ${R} 0 ${large} 1 ${x1} ${y1}L${x2} ${y2}A${r} ${r} 0 ${large} 0 ${x3} ${y3}Z`;
  };
  const shown = hover !== null ? slices[hover] : slices[0];
  return (
    <div data-reveal className="mb-4 flex items-center gap-4 rounded-2xl border border-white/12 bg-white/6 p-4">
      <svg viewBox="0 0 160 160" className="size-[150px] shrink-0" role="img" aria-label={`${title}比例圓餅圖`}>
        {slices.map((sl, i) => {
          const a0 = (acc / sum) * Math.PI * 2;
          acc += sl.percent;
          const a1 = (acc / sum) * Math.PI * 2;
          const full = a1 - a0 >= Math.PI * 2 - 1e-3;
          return full ? (
            <circle key={sl.name} cx={C} cy={C} r={(R + r) / 2} fill="none" stroke={sl.color} strokeWidth={R - r} />
          ) : (
            <path
              key={sl.name}
              d={arc(a0, a1)}
              fill={sl.color}
              stroke="#06194a"
              strokeWidth={2}
              opacity={hover === null || hover === i ? 1 : 0.4}
              onPointerEnter={() => setHover(i)}
              onPointerLeave={() => setHover(null)}
            >
              <title>{`${sl.name} ${sl.percent}%`}</title>
            </path>
          );
        })}
        <text x={C} y={C - 2} textAnchor="middle" className="fill-white text-[22px] font-bold">{shown.percent}%</text>
        <text x={C} y={C + 16} textAnchor="middle" className="fill-white/70 text-[10px]">
          {shown.name.length > 7 ? shown.name.slice(0, 7) + "…" : shown.name}
        </text>
      </svg>
      <ul className="min-w-0 flex-1 space-y-1.5">
        {slices.map((sl, i) => (
          <li
            key={sl.name}
            className="flex items-center gap-2 text-[12.5px]"
            onPointerEnter={() => setHover(i)}
            onPointerLeave={() => setHover(null)}
          >
            <span className="size-2.5 shrink-0 rounded-[3px]" style={{ background: sl.color }} />
            <span className="min-w-0 flex-1 truncate text-white/85">{sl.name}</span>
            <span className="font-semibold text-white tabular-nums">{sl.percent}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RankingTab({ profile, kind }: { profile: CountryProfile | null | undefined; kind: "religion" | "language" }) {
  const speechOk = canSpeak();
  if (profile === undefined) return <Skeleton rows={4} />;
  if (!profile) return <Empty text="資料整理中。" />;
  const data = kind === "religion" ? profile.religion : profile.language;
  const ranking = data.ranking;
  const max = Math.max(...ranking.map((r) => r.percent), 1);
  const note = kind === "religion" ? profile.religion.background : profile.language.history;
  return (
    <div>
      {kind === "language" && (
        <p data-reveal className="mb-4 text-[13.5px] leading-relaxed text-white/85">
          {profile.language.official}
        </p>
      )}
      <Donut items={ranking} title={kind === "religion" ? "宗教" : "語言"} />
      <p data-reveal className="eyebrow mb-2">
        {kind === "religion" ? "信仰排名" : "使用人口排名"}
      </p>
      <ol className="space-y-2">
        {ranking.map((r, i) => {
          const greet = kind === "language" ? (r as CountryProfile["language"]["ranking"][number]) : null;
          const code = greet ? langCodeFor(r.name) : null;
          return (
            <li key={r.name} data-reveal className="glass-soft rounded-2xl px-4 py-3">
              <div className="flex items-baseline gap-3">
                <span className="grid size-6 shrink-0 place-items-center rounded-full text-[12px] font-bold text-white tabular-nums" style={{ background: PIE_COLORS[i] ?? OTHER_COLOR }}>{i + 1}</span>
                <span className="min-w-0 flex-1 text-[14.5px] font-medium">{r.name}</span>
                <span className="text-[15px] font-semibold tabular-nums">{r.percent}%</span>
              </div>
              <div className="mt-2 ml-8 h-1 overflow-hidden rounded-full bg-white/12">
                <div className="h-full rounded-full" style={{ width: `${(r.percent / max) * 100}%`, background: PIE_COLORS[i] ?? OTHER_COLOR }} />
              </div>
              <p className="mt-2 ml-8 text-[12.5px] leading-relaxed text-white/70">{r.description}</p>
              {greet?.greeting && (
                <div className="mt-2 ml-8 flex items-center gap-2">
                  <span className="text-[15px]">{greet.greeting}</span>
                  {greet.pronunciation && <span className="text-xs text-white/55 italic">{greet.pronunciation}</span>}
                  {speechOk && code && (
                    <button onClick={() => speak(greet.greeting!, code)} className="ml-auto grid size-7 place-items-center rounded-full bg-white/10 text-white/80 hover:bg-white/20" aria-label={`朗讀 ${greet.greeting}`}>
                      <Volume2 className="size-3.5" />
                    </button>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ol>
      <div data-reveal className="mt-5">
        <p className="eyebrow mb-2">{kind === "religion" ? "信仰背景" : "語言的歷史"}</p>
        <p className="text-[13.5px] leading-relaxed text-white/85">{note}</p>
      </div>
    </div>
  );
}

function FoodTab({ profile }: { profile: CountryProfile | null | undefined }) {
  if (profile === undefined) return <Skeleton rows={3} />;
  if (!profile) return <Empty text="資料整理中。" />;
  return (
    <ol className="space-y-4">
      {profile.food.ranking.map((f, i) => (
        <li key={f.name} data-reveal className="glass-soft overflow-hidden rounded-3xl">
          {f.image ? (
            <figure className="relative aspect-[16/10] bg-white/5">
              <img src={f.image} alt={f.name} loading="lazy" className="size-full object-cover" />
              <span className="glass absolute top-3 left-3 grid size-9 place-items-center rounded-full text-sm font-semibold">{i + 1}</span>
            </figure>
          ) : null}
          <div className="px-4 pt-3 pb-4">
            <div className="flex items-baseline gap-2">
              {!f.image && <span className="text-lg font-light text-white/50 tabular-nums">{i + 1}</span>}
              <h4 className="text-[15.5px] font-semibold">{f.name}</h4>
              {f.localName && <span className="truncate text-xs text-white/55">{f.localName}</span>}
            </div>
            <p className="mt-1.5 text-[13px] leading-relaxed text-white/80">{f.description}</p>
            <p className="mt-2 text-[12.5px] leading-relaxed text-white/62">{f.history}</p>
            {f.imageCredit && (
              <p className="mt-2 text-[10.5px] text-white/40">
                圖片：
                {f.imagePage ? (
                  <a href={f.imagePage} target="_blank" rel="noreferrer" className="underline-offset-2 hover:underline">
                    {f.imageCredit}
                  </a>
                ) : (
                  f.imageCredit
                )}
              </p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

