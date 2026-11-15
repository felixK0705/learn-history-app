import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Box, Dices, Landmark, Menu, Pause, Play, RotateCcw, X } from "lucide-react";
import HeaderSlot from "../components/HeaderSlot";
import GlobeView, { type GlobeHandle } from "../components/globe/GlobeView";
import CountryPanel from "../components/country/CountryPanel";
import StarField from "../components/StarField";
import { gsap, prefersReducedMotion, useGSAP, useReveal } from "../lib/motion";
import { countries, countryByIso } from "../data/world";
import type { Building } from "../data/buildings";
import { useVisited } from "../lib/progress";

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
  const [menuOpen, setMenuOpen] = useState(false);
  const { visited, markVisited } = useVisited();

  const shiftRef = useRef<HTMLDivElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);
  const globeWrapRef = useRef<HTMLDivElement>(null);
  const placeholderRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const buildingRef = useRef<HTMLDivElement>(null);
  const noticeRef = useRef<HTMLDivElement>(null);

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
      .fromTo(glowRef.current, { scale: 0.3, autoAlpha: 0 }, { scale: 1, autoAlpha: 1, duration: 1.6, ease: "power2.out" }, 0);
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

  useReveal(menuRef, [menuOpen], { stagger: ":scope > *", y: -8, each: 0.03, duration: 0.35 });
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
        setNotice("這個地區目前沒有收錄歷史資料");
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
    globe.current?.flyTo(selected.pos[0], selected.pos[1], window.innerWidth < 640 ? 2.2 : 1.6);
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


  return (
    <div className="absolute inset-0 overflow-hidden">
      <StarField />
      <div ref={shiftRef} className="absolute inset-0">
      {/* 地球後方光暈 */}
      <div ref={glowRef} className="pointer-events-none absolute top-1/2 left-1/2 size-[64vmin] -translate-1/2 rounded-full bg-[radial-gradient(circle,rgba(170,230,255,0.55)_0%,rgba(110,200,255,0.25)_45%,transparent_70%)] blur-[30px]" />
      <div ref={globeWrapRef} className="absolute inset-0">
        {/* 地球右上緣的光斑（參考圖） */}
        <div
          className={`pointer-events-none absolute top-[calc(50%-9vmin)] left-[calc(50%+22.5vmin)] z-10 size-[7vmin] -translate-1/2 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.95)_0%,rgba(190,235,255,0.5)_25%,transparent_65%)] mix-blend-screen transition-opacity duration-500 ${
            selected ? "opacity-0" : ""
          }`}
        />
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
          <div ref={placeholderRef} className="size-[46vmin] rounded-full bg-white/10" />
        </div>
      )}


      {/* 頂部列：探索進度文字與圓形選單（參考圖右上角） */}
      <HeaderSlot slot="header-meta">
        <span className="hidden sm:inline">
          已探索 {visited.length} / {countries.length}
        </span>
      </HeaderSlot>
      <HeaderSlot slot="header-menu">
        <button
          onClick={() => setMenuOpen((v) => !v)}
          className={`grid size-[42px] place-items-center rounded-full border transition ${
            menuOpen ? "border-white bg-white text-deep-800" : "border-white/15 bg-[#0a2f7d]/55 text-white hover:bg-[#0a2f7d]/80"
          }`}
          aria-label="地球設定"
          aria-expanded={menuOpen}
        >
          {menuOpen ? <X className="size-4" /> : <Menu className="size-4" />}
        </button>
      </HeaderSlot>

      {menuOpen && (
        <div ref={menuRef} className="glass absolute top-3 right-4 z-40 w-56 rounded-2xl p-1.5 shadow-2xl md:right-6">
          {[
            { icon: autoRotate ? Pause : Play, label: autoRotate ? "停止自轉" : "開始自轉", run: () => setAutoRotate((v) => !v) },
            { icon: Landmark, label: showLandmarks ? "隱藏建築光點" : "顯示建築光點", run: () => setShowLandmarks((v) => !v) },
            { icon: Dices, label: "隨機探索一個國家", run: randomCountry },
            {
              icon: RotateCcw,
              label: "重設視角",
              run: () => {
                select(null);
                globe.current?.reset();
              },
            },
          ].map(({ icon: Icon, label, run }) => (
            <button
              key={label}
              onClick={() => {
                run();
                setMenuOpen(false);
              }}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm text-white/90 transition hover:bg-white/10"
            >
              <Icon className="size-4 text-white/70" />
              {label}
            </button>
          ))}
        </div>
      )}

      {/* 滑過國家名稱 */}
      {hoverName && !selected && (
        <div className="pointer-events-none absolute bottom-6 left-1/2 z-10 -translate-x-1/2 text-[11px] font-semibold tracking-[0.3em] text-white/80 uppercase max-md:hidden">
          {hoverName}
        </div>
      )}

      {/* 地標資訊卡 */}
      {building && (
        <div ref={buildingRef} className="glass absolute bottom-20 left-1/2 z-30 w-[min(92%,360px)] -translate-x-1/2 rounded-2xl p-4 shadow-2xl md:bottom-6">
          <button className="absolute top-3 right-3 text-mute hover:text-ink" onClick={() => setBuilding(null)} aria-label="關閉">
            <X className="size-4" />
          </button>
          <p className="text-[11px] tracking-wider text-glow">
            {building.era}・{building.location}
          </p>
          <h3 className="mt-1 text-lg font-semibold">{building.name}</h3>
          <p className="mt-1.5 line-clamp-3 text-sm leading-relaxed text-mute">{building.description}</p>
          <Link
            to={`/buildings/${building.id}`}
            className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-white px-3.5 py-1.5 text-sm font-semibold text-deep-800 transition hover:bg-white/90"
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
