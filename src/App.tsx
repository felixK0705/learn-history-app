import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { gsap, prefersReducedMotion, useGSAP } from "./lib/motion";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { BookOpen, Globe2, Landmark, Languages, Network, Search } from "lucide-react";
import { LANGS, setLang, useLang, useT, type Tr } from "./lib/i18n";
import CommandPalette from "./components/CommandPalette";
import Logo from "./components/Logo";
import GlobalChat from "./components/ai/GlobalChat";

const GlobePage = lazy(() => import("./pages/GlobePage"));
const FiguresPage = lazy(() => import("./pages/FiguresPage"));
const BuildingsPage = lazy(() => import("./pages/BuildingsPage"));
const StoriesPage = lazy(() => import("./pages/StoriesPage"));

const nav: { to: string; label: Tr; icon: typeof Globe2 }[] = [
  { to: "/", label: { "zh-TW": "地球", en: "Globe", ja: "地球" }, icon: Globe2 },
  { to: "/figures", label: { "zh-TW": "人物關係", en: "Figures", ja: "人物相関" }, icon: Network },
  { to: "/buildings", label: { "zh-TW": "建築 3D", en: "3D Buildings", ja: "3D 建築" }, icon: Landmark },
  { to: "/stories", label: { "zh-TW": "歷史故事", en: "Stories", ja: "歴史物語" }, icon: BookOpen },
];

/** 語言切換：地球圖示下拉選單（繁體中文／English／日本語） */
function LanguageMenu() {
  const lang = useLang();
  const t = useT();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);
  const label = t({ "zh-TW": "切換語言", en: "Language", ja: "言語を切り替え" });
  return (
    <div ref={ref} className="relative ml-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex h-9 items-center gap-1.5 rounded-full px-2.5 text-white transition hover:bg-white/10"
        aria-label={label}
        aria-expanded={open}
        title={label}
      >
        <Languages className="size-[18px]" strokeWidth={2.4} />
        <span className="text-[12px] font-semibold">{lang === "zh-TW" ? "繁" : lang === "en" ? "EN" : "日"}</span>
      </button>
      {open && (
        <div className="absolute top-11 right-0 z-50 w-36 overflow-hidden rounded-2xl border border-white/20 bg-[#113650]/97 p-1 shadow-[0_18px_40px_-16px_rgba(0,20,40,0.7)]">
          {LANGS.map((l) => (
            <button
              key={l.code}
              lang={l.code}
              onClick={() => {
                setLang(l.code);
                setOpen(false);
              }}
              className={`block w-full rounded-xl px-3 py-2 text-left text-sm transition ${l.code === lang ? "bg-white text-deep-800 font-semibold" : "text-white/85 hover:bg-white/10"}`}
            >
              {l.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function Loading() {
  const t = useT();
  const spinner = useRef<HTMLDivElement>(null);
  useGSAP(() => {
    gsap.to(spinner.current, { rotation: 360, duration: 0.9, repeat: -1, ease: "none" });
  });
  return (
    <div className="grid h-full place-items-center">
      <div className="flex flex-col items-center gap-3 text-mute">
        <div ref={spinner} className="size-10 rounded-full border-2 border-white/15 border-t-glow" />
        <span className="text-sm">{t({ "zh-TW": "載入中…", en: "Loading…", ja: "読み込み中…" })}</span>
      </div>
    </div>
  );
}

export default function App() {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const t = useT();
  const location = useLocation();
  const pageRef = useRef<HTMLDivElement>(null);
  const shellRef = useRef<HTMLDivElement>(null);

  // 首次進入：外框與導覽依序浮現
  useGSAP(
    () => {
      if (prefersReducedMotion()) return;
      gsap
        .timeline()
        .fromTo(
          shellRef.current,
          { autoAlpha: 0 },
          { autoAlpha: 1, duration: 0.8, ease: "power2.out" },
        )
        .fromTo(
          "[data-intro]",
          { y: -10, autoAlpha: 0 },
          { y: 0, autoAlpha: 1, stagger: 0.06, duration: 0.5, clearProps: "transform" },
          0.35,
        );
    },
    { scope: shellRef },
  );

  // 換頁轉場
  useGSAP(
    () => {
      if (prefersReducedMotion() || !pageRef.current) return;
      gsap.fromTo(pageRef.current, { autoAlpha: 0, y: 14 }, { autoAlpha: 1, y: 0, duration: 0.6, ease: "power3.out" });
    },
    { dependencies: [location.pathname] },
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="h-full">
      {/* 主畫面：滿版亮藍舞台 */}
      <div
        ref={shellRef}
        className="stage relative flex h-full overflow-hidden"
      >
        {/* 左側浮動膠囊導覽（半透明玻璃），垂直置中、不佔整排 */}
        <aside className="absolute top-1/2 left-4 z-40 hidden -translate-y-1/2 md:block">
          <nav
            className="flex flex-col items-center gap-3 rounded-full border border-white/25 bg-[linear-gradient(180deg,rgba(255,255,255,0.22),rgba(255,255,255,0.1))] p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.4),0_18px_40px_-16px_rgba(0,20,40,0.6)]"
            aria-label={t({ "zh-TW": "主要導覽", en: "Main navigation", ja: "メインナビゲーション" })}
          >
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                aria-label={t(label)}
                className={({ isActive }) =>
                  `group relative grid size-12 place-items-center rounded-full transition ${
                    isActive
                      ? "bg-white/25 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.55),0_6px_16px_-6px_rgba(0,20,40,0.5)]"
                      : "text-white/75 hover:bg-white/10 hover:text-white"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon className="size-[22px]" strokeWidth={isActive ? 2.2 : 1.9} />
                    <span className="pointer-events-none absolute left-16 rounded-full border border-white/20 bg-[#113650]/95 px-3 py-1 text-xs font-semibold whitespace-nowrap text-white opacity-0 shadow-lg transition group-hover:opacity-100 group-focus-visible:opacity-100">
                      {t(label)}
                    </span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        </aside>

        <div className="relative flex min-w-0 flex-1 flex-col">
          {/* 頂部列：透明疊在畫面上，地球與 3D 場景延伸到最上方 */}
          <header className="pointer-events-none absolute inset-x-0 top-0 z-30 flex h-[62px] items-center pr-5 pl-5 md:pr-7 md:pl-6 [&>*]:pointer-events-auto">
            <NavLink to="/" data-intro className="flex items-center gap-3">
              <Logo className="size-8" />
              <span className="font-[Montserrat,sans-serif] text-[24px] leading-none font-extrabold tracking-[0.01em] uppercase">Timelore</span>
            </NavLink>
            <div data-intro id="header-meta" className="ml-auto flex items-center gap-8 font-[Montserrat,Noto_Sans_TC,sans-serif] text-[13px] font-medium tracking-[0.04em] text-white/90 uppercase" />
            <button
              data-intro
              onClick={() => setPaletteOpen(true)}
              className="ml-9 grid size-9 place-items-center rounded-full text-white transition hover:bg-white/10"
              aria-label={t({ "zh-TW": "搜尋（Ctrl K）", en: "Search (Ctrl K)", ja: "検索（Ctrl K）" })}
              title={t({ "zh-TW": "搜尋（Ctrl K）", en: "Search (Ctrl K)", ja: "検索（Ctrl K）" })}
            >
              <Search className="size-[18px]" strokeWidth={2.6} />
            </button>
            <div data-intro>
              <LanguageMenu />
            </div>
            <div data-intro id="header-menu" className="ml-6 flex items-center" />
          </header>

          <main className="relative min-h-0 flex-1">
            <div ref={pageRef} className="absolute inset-x-0 top-0 bottom-14 md:bottom-0">
              <Suspense fallback={<Loading />}>
                <Routes location={location}>
                  <Route path="/" element={<GlobePage />} />
                  <Route path="/figures" element={<FiguresPage />} />
                  <Route path="/buildings" element={<BuildingsPage />} />
                  <Route path="/buildings/:id" element={<BuildingsPage />} />
                  <Route path="/stories" element={<StoriesPage />} />
                  <Route path="*" element={<GlobePage />} />
                </Routes>
              </Suspense>
            </div>
          </main>
        </div>

        {/* 手機底部導覽 */}
        <nav className="absolute inset-x-0 bottom-0 z-40 flex h-14 items-stretch border-t border-white/10 bg-[#16405f]/95 md:hidden" aria-label={t({ "zh-TW": "主要導覽", en: "Main navigation", ja: "メインナビゲーション" })}>
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex flex-1 flex-col items-center justify-center gap-0.5 text-[11px] ${isActive ? "text-white" : "text-white/55"}`
              }
            >
              <Icon className="size-5" />
              {t(label)}
            </NavLink>
          ))}
        </nav>
      </div>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
      <GlobalChat />
    </div>
  );
}
