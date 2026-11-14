import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Box, Dices, Landmark, Minus, Pause, Play, Plus, RotateCcw, X } from "lucide-react";
import GlobeView, { type GlobeHandle } from "../components/globe/GlobeView";
import CountryPanel from "../components/country/CountryPanel";
import StarField from "../components/StarField";
import { gsap, prefersReducedMotion, useGSAP, useReveal } from "../lib/motion";
import { countries, countryByIso } from "../data/countries";
import { buildings, type Building } from "../data/buildings";
import { figures } from "../data/figures";
import { useVisited } from "../lib/progress";
import type { CountryInfo } from "../data/types";

const continents: CountryInfo["continent"][] = ["亞洲", "歐洲", "非洲", "北美洲", "南美洲", "大洋洲"];

export default function GlobePage() {
  const [params, setParams] = useSearchParams();
  const selectedIso = params.get("country");
  const selected = selectedIso ? countryByIso.get(selectedIso) ?? null : null;

  const globe = useRef<GlobeHandle>(null);
  const [ready, setReady] = useState(false);
  const [hoverName, setHoverName] = useState<string | null>(null);
  const [autoRotate, setAutoRotate] = useState(true);
  const [showLandmarks, setShowLandmarks] = useState(true);
  const [building, setBuilding] = useState<Building | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [continent, setContinent] = useState<CountryInfo["continent"] | null>(null);
  const { visited, markVisited } = useVisited();

  const shiftRef = useRef<HTMLDivElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);
  const globeWrapRef = useRef<HTMLDivElement>(null);
  const placeholderRef = useRef<HTMLDivElement>(null);
  const heroRef = useRef<HTMLElement>(null);
  const continentRef = useRef<HTMLDivElement>(null);
  const buildingRef = useRef<HTMLDivElement>(null);
  const noticeRef = useRef<HTMLDivElement>(null);
  const controlsRef = useRef<HTMLDivElement>(null);

  // 載入中的地球呼吸效果
  useGSAP(() => {
    if (!placeholderRef.current) return;
    gsap.to(placeholderRef.current, { scale: 1.06, opacity: 0.5, duration: 1.2, repeat: -1, yoyo: true, ease: "sine.inOut" });
  }, { dependencies: [ready] });

  // 地球就緒時放大淡入、光暈綻放
  useGSAP(() => {
    if (!ready || prefersReducedMotion()) return;
    const tl = gsap.timeline();
    tl.fromTo(globeWrapRef.current, { scale: 0.75, autoAlpha: 0 }, { scale: 1, autoAlpha: 1, duration: 1.4, ease: "expo.out" })
      .fromTo(glowRef.current, { scale: 0.3, autoAlpha: 0 }, { scale: 1, autoAlpha: 1, duration: 1.6, ease: "power2.out" }, 0)
      .fromTo(
        controlsRef.current?.children ?? [],
        { x: 24, autoAlpha: 0 },
        { x: 0, autoAlpha: 1, stagger: 0.06, duration: 0.5, clearProps: "transform" },
        0.5,
      );
  }, { dependencies: [ready] });

  // 選取國家時，地球讓位給資訊面板
  useGSAP(() => {
    const desktop = window.matchMedia("(min-width: 1024px)").matches;
    gsap.to(shiftRef.current, {
      x: selected && desktop ? -210 : 0,
      yPercent: selected && !desktop ? -22 : 0,
      duration: 1,
      ease: "expo.out",
      overwrite: true,
    });
  }, { dependencies: [!!selected] });

  useReveal(heroRef, [!!selected], { stagger: ":scope > *", y: 24, each: 0.1, duration: 0.8, delay: 0.2 });
  useReveal(continentRef, [continent], { stagger: ":scope > *", y: 8, scale: 0.9, each: 0.03, duration: 0.35 });
  useReveal(buildingRef, [building?.id], { y: 24, duration: 0.5 });
  useReveal(noticeRef, [notice], { y: -16, duration: 0.4 });

  const select = useCallback(
    (iso: string | null) => {
      setBuilding(null);
      if (!iso) {
        setParams({}, { replace: true });
        return;
      }
      if (!countryByIso.has(iso)) {
        setNotice("這個國家的內容還在整理中，先看看亮起標籤的國家吧！");
        return;
      }
      setParams({ country: iso });
    },
    [setParams],
  );

  // 選取後飛到該國
  useEffect(() => {
    if (!selected || !ready) return;
    markVisited(selected.iso);
    globe.current?.flyTo(selected.labelPos[0], selected.labelPos[1], window.innerWidth < 640 ? 2.2 : 1.6);
  }, [selected, ready, markVisited]);

  useEffect(() => {
    if (!notice) return;
    const t = setTimeout(() => setNotice(null), 2600);
    return () => clearTimeout(t);
  }, [notice]);

  const randomCountry = () => {
    const pool = countries.filter((c) => c.iso !== selectedIso);
    const unvisited = pool.filter((c) => !visited.includes(c.iso));
    const list = unvisited.length ? unvisited : pool;
    select(list[Math.floor(Math.random() * list.length)].iso);
  };

  const continentList = useMemo(
    () => (continent ? countries.filter((c) => c.continent === continent) : []),
    [continent],
  );

  return (
    <div className="absolute inset-0 overflow-hidden">
      <StarField />
      <div ref={shiftRef} className="absolute inset-0">
      {/* 地球後方光暈 */}
      <div ref={glowRef} className="pointer-events-none absolute top-1/2 left-1/2 size-[70vmin] -translate-1/2 rounded-full bg-glow/25 blur-[90px]" />
      <div ref={globeWrapRef} className="absolute inset-0">
        <GlobeView
          ref={globe}
          selectedIso={selectedIso}
          visited={visited}
          autoRotate={autoRotate && !selected}
          showLandmarks={showLandmarks}
          onSelectCountry={select}
          onHoverCountry={setHoverName}
          onSelectBuilding={(b) => {
            setBuilding(b);
            globe.current?.flyTo(b.position[0], b.position[1], 1.3);
          }}
          onReady={() => setReady(true)}
        />
      </div>
      </div>

      {!ready && (
        <div className="pointer-events-none absolute inset-0 grid place-items-center">
          <div ref={placeholderRef} className="size-[42vmin] rounded-full bg-gradient-to-br from-sky-300/30 to-deep-700/30" />
        </div>
      )}

      {/* 左上：介紹與進度 */}
      {!selected && (
        <section ref={heroRef} className="pointer-events-none absolute top-6 left-5 z-10 max-w-xs md:top-10 md:left-10">
          <p className="text-xs tracking-[0.4em] text-glow">EXPLORE WORLD HISTORY</p>
          <h1 className="mt-3 font-serif text-3xl leading-tight font-bold text-white drop-shadow md:text-5xl">
            轉動地球，
            <br />
            穿越千年
          </h1>
          <p className="mt-4 hidden text-sm leading-relaxed text-mute sm:block">
            點擊發光的國家標籤，閱讀重大歷史時間線，認識當地美食、宗教與語言；黃色光點是可 360° 觀看的歷史建築。
          </p>
          <dl className="mt-6 hidden grid-cols-3 gap-3 sm:grid">
            {[
              [countries.length, "國家"],
              [figures.length, "人物"],
              [buildings.length, "建築"],
            ].map(([n, l]) => (
              <div key={l} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 backdrop-blur">
                <dt className="text-[11px] text-mute">{l}</dt>
                <dd className="text-xl font-semibold text-white">{n}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-4 hidden sm:block">
            <div className="flex justify-between text-[11px] text-mute">
              <span>探索進度</span>
              <span>
                {visited.length} / {countries.length}
              </span>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-glow to-amber-300 transition-[width] duration-700"
                style={{ width: `${(visited.length / countries.length) * 100}%` }}
              />
            </div>
          </div>
        </section>
      )}

      {/* 左下：洲別快速前往 */}
      {!selected && (
        <div className="absolute bottom-5 left-5 z-10 max-w-[calc(100%-7rem)] md:left-10">
          {continent && (
            <div ref={continentRef} className="glass mb-2 flex max-w-md flex-wrap gap-1.5 rounded-2xl p-2">
              {continentList.map((c) => (
                <button key={c.iso} className="chip" onClick={() => select(c.iso)}>
                  <span>{c.flag}</span>
                  {c.name}
                  {visited.includes(c.iso) && <span className="size-1.5 rounded-full bg-amber-300" />}
                </button>
              ))}
            </div>
          )}
          <div className="scroll-thin flex gap-1.5 overflow-x-auto md:flex-wrap">
            {continents.map((ct) => (
              <button
                key={ct}
                className={`chip shrink-0 ${continent === ct ? "chip-on" : ""}`}
                onClick={() => setContinent((v) => (v === ct ? null : ct))}
              >
                {ct}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 滑過國家名稱 */}
      {hoverName && !selected && (
        <div className="pointer-events-none absolute top-6 left-1/2 z-10 -translate-x-1/2 rounded-full border border-white/15 bg-deep-950/60 px-4 py-1.5 text-sm backdrop-blur max-md:hidden">
          {hoverName}
        </div>
      )}

      {/* 右下：地球控制 */}
      <div
        ref={controlsRef}
        className={`absolute right-5 bottom-5 z-20 flex flex-col gap-2 transition-all duration-500 ${
          selected ? "lg:right-[452px] max-lg:opacity-0 max-lg:pointer-events-none" : ""
        }`}
      >
        <button className="icon-btn max-md:hidden" onClick={() => globe.current?.zoom(0.7)} aria-label="放大" title="放大">
          <Plus className="size-4" />
        </button>
        <button className="icon-btn max-md:hidden" onClick={() => globe.current?.zoom(1.4)} aria-label="縮小" title="縮小">
          <Minus className="size-4" />
        </button>
        <button
          className="icon-btn"
          onClick={() => setAutoRotate((v) => !v)}
          aria-label={autoRotate ? "停止自轉" : "開始自轉"}
          title={autoRotate ? "停止自轉" : "開始自轉"}
        >
          {autoRotate ? <Pause className="size-4" /> : <Play className="size-4" />}
        </button>
        <button
          className={`icon-btn ${showLandmarks ? "!border-amber-300/50 !text-amber-200" : ""}`}
          onClick={() => setShowLandmarks((v) => !v)}
          aria-label="顯示歷史建築"
          title="顯示歷史建築"
        >
          <Landmark className="size-4" />
        </button>
        <button className="icon-btn" onClick={randomCountry} aria-label="隨機探索" title="隨機探索一個國家">
          <Dices className="size-4" />
        </button>
        <button
          className="icon-btn"
          onClick={() => {
            select(null);
            globe.current?.reset();
          }}
          aria-label="重設視角"
          title="重設視角"
        >
          <RotateCcw className="size-4" />
        </button>
      </div>

      {/* 地標資訊卡 */}
      {building && (
        <div ref={buildingRef} className="glass absolute bottom-20 left-1/2 z-30 w-[min(92%,360px)] -translate-x-1/2 rounded-2xl p-4 shadow-2xl md:bottom-6">
          <button className="absolute top-3 right-3 text-mute hover:text-ink" onClick={() => setBuilding(null)} aria-label="關閉">
            <X className="size-4" />
          </button>
          <p className="text-[11px] text-amber-200">
            {building.era}・{building.location}
          </p>
          <h3 className="mt-1 font-serif text-lg font-bold">{building.name}</h3>
          <p className="mt-1.5 line-clamp-3 text-sm leading-relaxed text-mute">{building.description}</p>
          <Link
            to={`/buildings/${building.id}`}
            className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-glow/90 px-3.5 py-1.5 text-sm font-medium text-deep-950 transition hover:bg-glow"
          >
            <Box className="size-4" /> 觀看 3D 模型
          </Link>
        </div>
      )}

      {notice && (
        <div ref={noticeRef} className="glass absolute top-6 left-1/2 z-40 -translate-x-1/2 rounded-full px-4 py-2 text-sm">
          {notice}
        </div>
      )}

      {selected && <CountryPanel key={selected.iso} country={selected} onClose={() => select(null)} />}
    </div>
  );
}
