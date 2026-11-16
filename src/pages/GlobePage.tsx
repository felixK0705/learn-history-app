import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Dices, Menu, Pause, Play, RotateCcw, X } from "lucide-react";
import HeaderSlot from "../components/HeaderSlot";
import GlobeView, { type GlobeHandle } from "../components/globe/GlobeView";
import CountryPanel from "../components/country/CountryPanel";
import { gsap, prefersReducedMotion, useGSAP, useReveal } from "../lib/motion";
import { countries, countryByIso } from "../data/world";
import { useVisited } from "../lib/progress";

export default function GlobePage() {
  const [params, setParams] = useSearchParams();
  const selectedIso = params.get("country");
  const selected = selectedIso ? countryByIso.get(selectedIso) ?? null : null;

  const globe = useRef<GlobeHandle>(null);
  const [ready, setReady] = useState(false);
  const [autoRotate, setAutoRotate] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const { visited, markVisited } = useVisited();

  const shiftRef = useRef<HTMLDivElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);
  const globeWrapRef = useRef<HTMLDivElement>(null);
  const placeholderRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const noticeRef = useRef<HTMLDivElement>(null);

  // 載入中的地球呼吸效果
  useGSAP(() => {
    if (!placeholderRef.current) return;
    gsap.to(placeholderRef.current, { scale: 1.06, opacity: 0.5, duration: 1.2, repeat: -1, yoyo: true, ease: "sine.inOut" });
  }, { dependencies: [ready] });

  // 地球就緒時放大淡入、光暈綻放
  useGSAP(() => {
    if (!ready) return;
    if (prefersReducedMotion()) {
      gsap.set([globeWrapRef.current, glowRef.current], { autoAlpha: 1 });
      return;
    }
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
      duration: 0.7,
      ease: "power3.out",
      overwrite: true,
    });
  }, { dependencies: [!!selected] });

  useReveal(menuRef, [menuOpen], { stagger: ":scope > *", y: -8, each: 0.03, duration: 0.35 });
  useReveal(noticeRef, [notice], { y: -16, duration: 0.4 });

  const select = useCallback(
    (iso: string | null) => {
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
      <div ref={shiftRef} className="absolute inset-0">
      {/* 地球後方光暈 */}
      <div ref={glowRef} className="invisible pointer-events-none absolute top-1/2 left-1/2 size-[64vmin] -translate-1/2 rounded-full bg-[radial-gradient(circle,rgba(200,230,248,0.5)_0%,rgba(150,200,230,0.22)_45%,transparent_70%)]" />
      <div ref={globeWrapRef} className="invisible absolute inset-0">
        <GlobeView
          ref={globe}
          selectedIso={selectedIso}
          autoRotate={autoRotate && !selected}
          onSelectCountry={select}
          onReady={() => setReady(true)}
        />
      </div>
      </div>

      {!ready && (
        <div className="pointer-events-none absolute inset-0 grid place-items-center">
          <div ref={placeholderRef} className="size-[46vmin] rounded-full bg-white/10" />
        </div>
      )}


      {/* 頂部列：圓形選單 */}
      <HeaderSlot slot="header-menu">
        <button
          onClick={() => setMenuOpen((v) => !v)}
          className={`grid size-[42px] place-items-center rounded-full border transition ${
            menuOpen ? "border-white bg-white text-deep-800" : "border-white/15 bg-[#174a68]/55 text-white hover:bg-[#174a68]/80"
          }`}
          aria-label="地球設定"
          aria-expanded={menuOpen}
        >
          {menuOpen ? <X className="size-4" /> : <Menu className="size-4" />}
        </button>
      </HeaderSlot>

      {menuOpen && (
        <div ref={menuRef} className="glass absolute top-[66px] right-4 z-40 w-56 rounded-2xl p-1.5 shadow-2xl md:right-6">
          {[
            { icon: autoRotate ? Pause : Play, label: autoRotate ? "停止自轉" : "開始自轉", run: () => setAutoRotate((v) => !v) },
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

      {notice && (
        <div ref={noticeRef} className="glass absolute top-6 left-1/2 z-40 -translate-x-1/2 rounded-full px-4 py-2 text-sm">
          {notice}
        </div>
      )}

      {selected && <CountryPanel key={selected.iso} country={selected} onClose={() => select(null)} />}
    </div>
  );
}
