import { lazy, Suspense, useEffect, useMemo, useRef, useState } from "react";
import { gsap, prefersReducedMotion, useGSAP, useReveal } from "../lib/motion";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Globe2,
  Landmark,
  PanelRightClose,
  PanelRightOpen,
  Pause,
  Play,
  RotateCcw,
  Search,
} from "lucide-react";
import { buildings } from "../data/buildings";
import { buildingDetails } from "../data/buildingDetails";
import { countryByIso } from "../data/world";
import Flag from "../components/ui/Flag";
import views from "../data/buildingViews.json";
import type { BuildingView } from "../components/buildings/ModelViewer";

const ModelViewer = lazy(() => import("../components/buildings/ModelViewer"));

const sorted = [...buildings].sort((a, b) => a.sortYear - b.sortYear);

function eraLabel(y: number) {
  if (y < -500) return "上古";
  if (y < 500) return "古典時代";
  if (y < 1500) return "中世紀";
  if (y < 1800) return "近世";
  return "近現代";
}

const TABS = [
  { key: "overview", label: "概覽" },
  { key: "parts", label: "建築特色" },
  { key: "history", label: "歷史" },
  { key: "stats", label: "數據" },
] as const;
type TabKey = (typeof TABS)[number]["key"];

/** 照片背景上的面板：深色半透明＋模糊，確保文字在任何背景下都清楚 */
const PANEL =
  "border border-white/15 bg-[#071d4f]/94 shadow-[0_24px_60px_-20px_rgba(0,10,40,0.7),inset_0_1px_0_rgba(255,255,255,0.18)]";

export default function BuildingsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const current = sorted.find((b) => b.id === id) ?? sorted[0];
  const idx = sorted.indexOf(current);
  const detail = buildingDetails[current.id];
  const country = countryByIso.get(current.iso);

  const [q, setQ] = useState("");
  const [pickerOpen, setPickerOpen] = useState(false);
  const [autoRotate, setAutoRotate] = useState(false);
  const [resetToken, setResetToken] = useState(0);
  const [infoOpen, setInfoOpen] = useState(() => typeof window === "undefined" || window.innerWidth >= 1024);
  const [tab, setTab] = useState<TabKey>("overview");
  const [wide, setWide] = useState(() => window.innerWidth >= 1024);

  const titleRef = useRef<HTMLDivElement>(null);
  const infoRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const pickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const on = () => setWide(window.innerWidth >= 1024);
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, []);
  useEffect(() => setTab("overview"), [current.id]);
  useEffect(() => {
    if (!pickerOpen) return;
    const close = (e: MouseEvent) => {
      if (!pickerRef.current?.contains(e.target as Node)) setPickerOpen(false);
    };
    window.addEventListener("pointerdown", close);
    return () => window.removeEventListener("pointerdown", close);
  }, [pickerOpen]);

  useReveal(titleRef, [current.id], { stagger: ":scope > *", y: 14, each: 0.07, duration: 0.6 });
  useReveal(infoRef, [current.id, tab, infoOpen], { stagger: "[data-reveal]", y: 10, each: 0.04, duration: 0.45 });
  useGSAP(() => {
    if (prefersReducedMotion() || !stageRef.current) return;
    gsap.fromTo(stageRef.current, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.8, ease: "power2.out" });
  }, { dependencies: [current.id] });

  const list = useMemo(() => {
    const s = q.trim().toLowerCase();
    return s ? sorted.filter((b) => `${b.name}${b.englishName}${b.location}${b.style}`.toLowerCase().includes(s)) : sorted;
  }, [q]);

  const go = (offset: number) => navigate(`/buildings/${sorted[(idx + offset + sorted.length) % sorted.length].id}`);
  // 右側資訊面板打開時，把建築往左移到可見區域中央
  const shift = wide && infoOpen ? -200 : 0;

  return (
    <div className="absolute inset-0 overflow-hidden">
      {/* 3D 場景：滿版 */}
      <div ref={stageRef} className="absolute inset-0">
        <Suspense fallback={null}>
          <ModelViewer
            url={`/models/${current.model}`}
            view={(views as unknown as Record<string, BuildingView>)[current.id]}
            shift={shift}
            autoRotate={autoRotate}
            resetToken={resetToken}
          />
        </Suspense>
      </div>
      {/* 上方暗角：讓標題在亮天空上也清楚 */}
      <div className="pointer-events-none absolute inset-x-0 top-0 h-56 bg-gradient-to-b from-[#041640]/70 to-transparent" />

      {/* 左上：標題＋建築選單 */}
      <div className="absolute top-[78px] left-5 z-20 max-w-[min(520px,calc(100%-2.5rem))] md:top-[84px] md:left-7">
        <div ref={titleRef}>
          <p className="text-[12px] font-medium tracking-[0.14em] text-white/80 [text-shadow:0_1px_6px_rgba(0,20,60,0.8)]">
            {current.era}・{current.location}
          </p>
          <h2 className="mt-1 text-3xl font-semibold tracking-tight text-white [text-shadow:0_2px_14px_rgba(0,20,60,0.75)] md:text-[40px]">
            {current.name}
          </h2>
          <p className="text-sm text-white/80 [text-shadow:0_1px_6px_rgba(0,20,60,0.8)]">{current.englishName}</p>
        </div>

        <div ref={pickerRef} className="relative mt-4 inline-block">
          <button
            onClick={() => setPickerOpen((v) => !v)}
            className={`${PANEL} flex h-10 items-center gap-2 rounded-full pr-3 pl-4 text-sm text-white transition hover:bg-[#0a2766]/85`}
            aria-expanded={pickerOpen}
          >
            <Landmark className="size-4 text-glow" />
            全部建築
            <span className="text-white/55">{sorted.length}</span>
            <ChevronDown className={`size-4 text-white/70 transition ${pickerOpen ? "rotate-180" : ""}`} />
          </button>

          {pickerOpen && (
            <div className={`${PANEL} absolute top-12 left-0 flex max-h-[min(70vh,560px)] w-[300px] flex-col overflow-hidden rounded-2xl`}>
              <label className="m-3 mb-1 flex h-9 items-center gap-2 rounded-full border border-white/15 bg-white/8 px-3">
                <Search className="size-4 text-white/60" />
                <input
                  autoFocus
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  placeholder="搜尋建築或地點…"
                  className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-white/45"
                />
              </label>
              <ul className="scroll-thin min-h-0 flex-1 overflow-y-auto px-2 pb-2">
                {list.map((b, i) => {
                  const showEra = !q && (i === 0 || eraLabel(list[i - 1].sortYear) !== eraLabel(b.sortYear));
                  const active = b.id === current.id;
                  return (
                    <li key={b.id}>
                      {showEra && <div className="px-2 pt-3 pb-1 text-[11px] font-medium tracking-[0.16em] text-white/50">{eraLabel(b.sortYear)}</div>}
                      <Link
                        to={`/buildings/${b.id}`}
                        onClick={() => setPickerOpen(false)}
                        className={`flex items-center gap-3 rounded-xl px-3 py-2 transition ${active ? "bg-white text-deep-800" : "text-white hover:bg-white/10"}`}
                      >
                        <Flag iso2={countryByIso.get(b.iso)?.iso2} className="text-[15px]" />
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-sm font-medium">{b.name}</span>
                          <span className={`block truncate text-[11.5px] ${active ? "text-deep-800/65" : "text-white/60"}`}>{b.era}</span>
                        </span>
                      </Link>
                    </li>
                  );
                })}
                {list.length === 0 && <li className="py-8 text-center text-sm text-white/60">找不到符合的建築</li>}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* 左下：檢視控制 */}
      <div className={`${PANEL} absolute bottom-5 left-5 z-10 flex items-center gap-1 rounded-full p-1.5 md:bottom-7 md:left-7`}>
        <CtrlBtn label="上一個建築" onClick={() => go(-1)}>
          <ChevronLeft className="size-4" />
        </CtrlBtn>
        <span className="min-w-12 text-center font-mono text-xs text-white/75">
          {idx + 1} / {sorted.length}
        </span>
        <CtrlBtn label="下一個建築" onClick={() => go(1)}>
          <ChevronRight className="size-4" />
        </CtrlBtn>
        <span className="mx-1 h-5 w-px bg-white/20" />
        <CtrlBtn label={autoRotate ? "停止環繞" : "自動環繞"} onClick={() => setAutoRotate((v) => !v)}>
          {autoRotate ? <Pause className="size-4" /> : <Play className="size-4" />}
        </CtrlBtn>
        <CtrlBtn label="重設視角" onClick={() => setResetToken((t) => t + 1)}>
          <RotateCcw className="size-4" />
        </CtrlBtn>
        {!infoOpen && (
          <CtrlBtn label="顯示建築資訊" onClick={() => setInfoOpen(true)}>
            <PanelRightOpen className="size-4" />
          </CtrlBtn>
        )}
      </div>

      {/* 右側：建築資訊 */}
      {infoOpen && (
        <aside
          ref={infoRef}
          className={`${PANEL} absolute top-[78px] right-4 bottom-4 z-20 flex w-[min(380px,calc(100%-2rem))] flex-col overflow-hidden rounded-[24px]`}
        >
          <div className="flex items-start gap-3 px-5 pt-5">
            <div className="min-w-0 flex-1" data-reveal>
              <div className="flex items-center gap-2 text-[12px] text-white/65">
                <Flag iso2={country?.iso2} className="text-[13px]" />
                {country?.zh}・{current.style}
              </div>
              <h3 className="mt-1 truncate text-xl font-semibold text-white">{current.name}</h3>
            </div>
            <button
              onClick={() => setInfoOpen(false)}
              className="grid size-9 shrink-0 place-items-center rounded-full text-white/75 transition hover:bg-white/10 hover:text-white"
              aria-label="收合建築資訊"
              title="收合建築資訊"
            >
              <PanelRightClose className="size-4" />
            </button>
          </div>

          {/* 分頁 */}
          <div className="mx-5 mt-4 grid grid-cols-4 rounded-full border border-white/12 bg-white/6 p-1" role="tablist">
            {TABS.map((t) => (
              <button
                key={t.key}
                role="tab"
                aria-selected={tab === t.key}
                onClick={() => setTab(t.key)}
                className={`rounded-full py-1.5 text-[12.5px] font-medium transition ${
                  tab === t.key ? "bg-white text-deep-800 shadow" : "text-white/75 hover:text-white"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 pt-4 pb-5 text-[14px] leading-relaxed text-white/90">
            {tab === "overview" && (
              <>
                <p data-reveal>{detail?.overview ?? current.description}</p>
                {detail?.architecture && (
                  <section data-reveal className="mt-5">
                    <h4 className="mb-1.5 text-[12px] font-semibold tracking-[0.14em] text-glow">建築工法</h4>
                    <p className="text-white/85">{detail.architecture}</p>
                  </section>
                )}
                <section data-reveal className="mt-5">
                  <h4 className="mb-2 text-[12px] font-semibold tracking-[0.14em] text-glow">重點</h4>
                  <ul className="space-y-2">
                    {current.facts.map((f) => (
                      <li key={f} className="flex gap-2.5 text-white/85">
                        <span className="mt-[9px] size-1.5 shrink-0 rounded-full bg-glow" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </section>
                {detail?.visit && (
                  <section data-reveal className="mt-5 rounded-2xl border border-white/12 bg-white/6 p-3.5">
                    <h4 className="mb-1 text-[12px] font-semibold tracking-[0.14em] text-white/70">今日現況</h4>
                    <p className="text-[13.5px] text-white/85">{detail.visit}</p>
                  </section>
                )}
                {country && (
                  <Link data-reveal to={`/?country=${current.iso}`} className="mt-5 inline-flex items-center gap-1.5 text-sm font-medium text-glow hover:underline">
                    <Globe2 className="size-4" /> 探索{country.zh}的歷史
                  </Link>
                )}
              </>
            )}

            {tab === "parts" && (
              <ol className="space-y-3">
                {(detail?.parts ?? []).map((p, i) => (
                  <li key={p.name} data-reveal className="rounded-2xl border border-white/12 bg-white/6 p-3.5">
                    <div className="flex items-center gap-2.5">
                      <span className="grid size-6 shrink-0 place-items-center rounded-full bg-white text-[11px] font-semibold text-deep-800">{i + 1}</span>
                      <h4 className="font-semibold text-white">{p.name}</h4>
                    </div>
                    <p className="mt-1.5 text-[13.5px] text-white/80">{p.description}</p>
                  </li>
                ))}
              </ol>
            )}

            {tab === "history" && (
              <ol className="relative ml-1.5 border-l border-white/20">
                {(detail?.history ?? []).map((e) => (
                  <li key={e.year + e.text} data-reveal className="relative pb-4 pl-5 last:pb-0">
                    <span className="absolute top-[7px] -left-[5px] size-[9px] rounded-full border-2 border-[#071d4f] bg-glow" />
                    <div className="text-[12.5px] font-semibold text-glow">{e.year}</div>
                    <p className="text-[13.5px] text-white/85">{e.text}</p>
                  </li>
                ))}
              </ol>
            )}

            {tab === "stats" && (
              <dl className="grid grid-cols-2 gap-2.5">
                {(detail?.stats ?? []).map((s) => (
                  <div key={s.label} data-reveal className="rounded-2xl border border-white/12 bg-white/6 p-3">
                    <dt className="text-[11.5px] text-white/60">{s.label}</dt>
                    <dd className="mt-0.5 text-[13.5px] leading-snug font-medium text-white">{s.value}</dd>
                  </div>
                ))}
              </dl>
            )}
          </div>
        </aside>
      )}
    </div>
  );
}

function CtrlBtn({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      title={label}
      className="grid size-9 place-items-center rounded-full text-white/85 transition hover:bg-white/12 hover:text-white"
    >
      {children}
    </button>
  );
}
