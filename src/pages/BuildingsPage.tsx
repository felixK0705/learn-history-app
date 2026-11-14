import { lazy, Suspense, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, Globe2, Info, Pause, Play, RotateCcw, Search } from "lucide-react";
import { buildings } from "../data/buildings";
import { countryByIso } from "../data/countries";

const ModelViewer = lazy(() => import("../components/buildings/ModelViewer"));

const sorted = [...buildings].sort((a, b) => a.sortYear - b.sortYear);

function eraLabel(y: number) {
  if (y < -500) return "上古";
  if (y < 500) return "古典時代";
  if (y < 1500) return "中世紀";
  if (y < 1800) return "近世";
  return "近現代";
}

export default function BuildingsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const current = sorted.find((b) => b.id === id) ?? sorted[0];
  const idx = sorted.indexOf(current);
  const [q, setQ] = useState("");
  const [autoRotate, setAutoRotate] = useState(true);
  const [resetToken, setResetToken] = useState(0);
  const [infoOpen, setInfoOpen] = useState(true);

  const list = useMemo(() => {
    const s = q.trim().toLowerCase();
    return s
      ? sorted.filter((b) => `${b.name}${b.englishName}${b.location}${b.style}`.toLowerCase().includes(s))
      : sorted;
  }, [q]);

  const go = (offset: number) => navigate(`/buildings/${sorted[(idx + offset + sorted.length) % sorted.length].id}`);
  const country = countryByIso.get(current.iso);

  return (
    <div className="absolute inset-0 flex">
      {/* 建築清單 */}
      <aside className="relative z-10 hidden w-72 shrink-0 flex-col border-r border-white/10 bg-deep-950/30 lg:flex">
        <div className="p-5 pb-3">
          <h1 className="font-serif text-2xl font-bold">歷史建築 3D</h1>
          <p className="mt-1 text-sm text-mute">依年代排列，拖曳旋轉、滾輪縮放、右鍵平移。</p>
          <label className="mt-4 flex h-10 items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3">
            <Search className="size-4 text-mute" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="搜尋建築或地點…"
              className="min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-mute/70"
            />
          </label>
        </div>
        <ul className="scroll-thin min-h-0 flex-1 overflow-y-auto px-3 pb-4">
          {list.map((b, i) => {
            const showEra = i === 0 || eraLabel(list[i - 1].sortYear) !== eraLabel(b.sortYear);
            const active = b.id === current.id;
            return (
              <li key={b.id}>
                {showEra && !q && (
                  <div className="px-2 pt-4 pb-1 text-[11px] tracking-[0.3em] text-glow/80">{eraLabel(b.sortYear)}</div>
                )}
                <Link
                  to={`/buildings/${b.id}`}
                  className={`flex items-center gap-3 rounded-xl px-3 py-2 transition ${
                    active ? "bg-white/12 text-white" : "text-ink/80 hover:bg-white/[0.06]"
                  }`}
                >
                  <span className={`size-1.5 shrink-0 rounded-full ${active ? "bg-amber-300" : "bg-white/25"}`} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm">{b.name}</span>
                    <span className="block truncate text-[11px] text-mute">{b.era}</span>
                  </span>
                  <span className="text-base">{countryByIso.get(b.iso)?.flag}</span>
                </Link>
              </li>
            );
          })}
          {list.length === 0 && <li className="py-8 text-center text-sm text-mute">找不到符合的建築</li>}
        </ul>
      </aside>

      {/* 3D 舞台 */}
      <div className="relative min-w-0 flex-1">
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-deep-950/60 to-transparent" />
        <Suspense fallback={null}>
          <ModelViewer url={`/models/${current.model}`} autoRotate={autoRotate} resetToken={resetToken} />
        </Suspense>

        {/* 標題 */}
        <div className="pointer-events-none absolute top-5 left-5 right-24 animate-fade-in md:top-8 md:left-8" key={current.id}>
          <p className="text-xs tracking-[0.3em] text-amber-200">
            {current.era}・{current.location}
          </p>
          <h2 className="mt-2 font-serif text-3xl font-bold text-white drop-shadow md:text-4xl">{current.name}</h2>
          <p className="mt-1 text-sm text-mute">{current.englishName}</p>
        </div>

        {/* 工具列 */}
        <div className="absolute top-5 right-5 z-10 flex flex-col gap-2 md:top-8 md:right-8">
          <button className="icon-btn" onClick={() => setAutoRotate((v) => !v)} aria-label={autoRotate ? "停止旋轉" : "自動旋轉"} title={autoRotate ? "停止旋轉" : "自動旋轉"}>
            {autoRotate ? <Pause className="size-4" /> : <Play className="size-4" />}
          </button>
          <button className="icon-btn" onClick={() => setResetToken((t) => t + 1)} aria-label="重設視角" title="重設視角">
            <RotateCcw className="size-4" />
          </button>
          <button
            className={`icon-btn ${infoOpen ? "!border-glow/50" : ""}`}
            onClick={() => setInfoOpen((v) => !v)}
            aria-label="建築資訊"
            title="建築資訊"
          >
            <Info className="size-4" />
          </button>
        </div>

        {/* 資訊卡 */}
        {infoOpen && (
          <div
            key={`info-${current.id}`}
            className="glass scroll-thin absolute bottom-20 left-4 z-10 max-h-[45%] w-[min(calc(100%-2rem),380px)] animate-fade-in overflow-y-auto rounded-2xl p-5 md:bottom-8 md:left-8"
          >
            <div className="flex flex-wrap gap-1.5">
              <span className="chip !cursor-default">{current.style}</span>
              {country && <span className="chip !cursor-default">{country.flag} {country.name}</span>}
            </div>
            <p className="mt-3 text-sm leading-relaxed text-ink/90">{current.description}</p>
            <h3 className="mt-4 text-xs tracking-widest text-mute">你知道嗎？</h3>
            <ul className="mt-2 space-y-2">
              {current.facts.map((f) => (
                <li key={f} className="flex gap-2 text-sm leading-relaxed text-mute">
                  <span className="mt-2 size-1 shrink-0 rounded-full bg-amber-300" />
                  {f}
                </li>
              ))}
            </ul>
            {country && (
              <Link to={`/?country=${current.iso}`} className="mt-4 inline-flex items-center gap-1.5 text-sm text-glow hover:underline">
                <Globe2 className="size-4" /> 探索{country.name}的歷史
              </Link>
            )}
          </div>
        )}

        {/* 上一個 / 下一個 */}
        <div className="absolute right-4 bottom-20 z-10 flex items-center gap-2 md:right-8 md:bottom-8">
          <button className="icon-btn" onClick={() => go(-1)} aria-label="上一個建築">
            <ChevronLeft className="size-4" />
          </button>
          <span className="min-w-14 text-center font-mono text-xs text-mute">
            {idx + 1} / {sorted.length}
          </span>
          <button className="icon-btn" onClick={() => go(1)} aria-label="下一個建築">
            <ChevronRight className="size-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
