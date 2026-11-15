import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { gsap, prefersReducedMotion, useGSAP } from "./lib/motion";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { Globe2, Landmark, Network, Search } from "lucide-react";
import CommandPalette from "./components/CommandPalette";
import Logo from "./components/Logo";

const GlobePage = lazy(() => import("./pages/GlobePage"));
const FiguresPage = lazy(() => import("./pages/FiguresPage"));
const BuildingsPage = lazy(() => import("./pages/BuildingsPage"));

const nav = [
  { to: "/", label: "地球", icon: Globe2 },
  { to: "/figures", label: "人物關係", icon: Network },
  { to: "/buildings", label: "建築 3D", icon: Landmark },
];

function Loading() {
  const spinner = useRef<HTMLDivElement>(null);
  useGSAP(() => {
    gsap.to(spinner.current, { rotation: 360, duration: 0.9, repeat: -1, ease: "none" });
  });
  return (
    <div className="grid h-full place-items-center">
      <div className="flex flex-col items-center gap-3 text-mute">
        <div ref={spinner} className="size-10 rounded-full border-2 border-white/15 border-t-glow" />
        <span className="text-sm">載入中…</span>
      </div>
    </div>
  );
}

export default function App() {
  const [paletteOpen, setPaletteOpen] = useState(false);
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
        {/* 左側深色細條（寬約卡片 4.8%）：logo 在頂端、圓點導覽在 43% 高度 */}
        <aside className="relative z-30 hidden w-16 shrink-0 flex-col items-center bg-[linear-gradient(90deg,#082560_0%,#0a2c72_75%,rgba(10,44,114,0.85)_100%)] md:flex">
          <NavLink to="/" data-intro className="grid h-[62px] w-full place-items-center" aria-label="Timelore 首頁">
            <Logo className="size-10" />
          </NavLink>
          <nav className="absolute top-[36%] flex flex-col items-center gap-3" aria-label="主要導覽">
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                aria-label={label}
                className={({ isActive }) =>
                  `group relative grid size-11 place-items-center rounded-2xl transition ${
                    isActive
                      ? "bg-white/18 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.45),0_6px_16px_-6px_rgba(0,20,80,0.6)]"
                      : "text-white/60 hover:bg-white/10 hover:text-white"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon className="size-[21px]" strokeWidth={isActive ? 2.2 : 1.9} />
                    <span className={`absolute -left-[10px] h-5 w-[3px] rounded-full bg-white transition ${isActive ? "opacity-100" : "opacity-0"}`} />
                    <span className="pointer-events-none absolute left-14 rounded-full bg-white px-3 py-1 text-xs font-semibold whitespace-nowrap text-deep-800 opacity-0 shadow-lg transition group-hover:opacity-100 group-focus-visible:opacity-100">
                      {label}
                    </span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>
        </aside>

        <div className="relative flex min-w-0 flex-1 flex-col">
          {/* 頂部列（高約卡片 8%） */}
          <header className="relative z-30 flex h-[62px] shrink-0 items-center border-b border-white/[0.1] pr-5 pl-5 md:pr-7 md:pl-2">
            <NavLink to="/" data-intro className="flex items-center gap-3">
              <Logo className="size-8 md:hidden" />
              <span className="font-[Montserrat,sans-serif] text-[24px] leading-none font-extrabold tracking-[0.01em] uppercase">Timelore</span>
            </NavLink>
            <div data-intro id="header-meta" className="ml-auto flex items-center gap-8 font-[Montserrat,Noto_Sans_TC,sans-serif] text-[13px] font-medium tracking-[0.04em] text-white/90 uppercase" />
            <button
              data-intro
              onClick={() => setPaletteOpen(true)}
              className="ml-9 grid size-9 place-items-center rounded-full text-white transition hover:bg-white/10"
              aria-label="搜尋（Ctrl K）"
              title="搜尋（Ctrl K）"
            >
              <Search className="size-[18px]" strokeWidth={2.6} />
            </button>
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
                  <Route path="*" element={<GlobePage />} />
                </Routes>
              </Suspense>
            </div>
          </main>
        </div>

        {/* 手機底部導覽 */}
        <nav className="absolute inset-x-0 bottom-0 z-40 flex h-14 items-stretch border-t border-white/10 bg-[#0a3591]/80 backdrop-blur-xl md:hidden" aria-label="主要導覽">
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
              {label}
            </NavLink>
          ))}
        </nav>
      </div>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}
