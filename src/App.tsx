import { lazy, Suspense, useEffect, useState } from "react";
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
  return (
    <div className="grid h-full place-items-center">
      <div className="flex flex-col items-center gap-3 text-mute">
        <div className="size-10 animate-spin rounded-full border-2 border-white/15 border-t-glow" />
        <span className="text-sm">載入中…</span>
      </div>
    </div>
  );
}

export default function App() {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const location = useLocation();

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
    <div className="h-full p-0 md:p-6 lg:p-8">
      {/* 主舞台：參考設計中帶陰影的圓角深藍卡片 */}
      <div className="stage relative flex h-full overflow-hidden shadow-[0_40px_80px_-30px_rgba(6,40,120,0.65)] md:rounded-[28px]">
        {/* 左側細導覽列 */}
        <aside className="relative z-30 hidden w-16 shrink-0 flex-col items-center border-r border-white/10 bg-deep-950/35 py-5 md:flex">
          <Logo className="size-9" />
          <nav className="mt-auto mb-auto flex flex-col items-center gap-5" aria-label="主要導覽">
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                aria-label={label}
                className={({ isActive }) =>
                  `group relative grid size-10 place-items-center rounded-full transition ${
                    isActive ? "bg-white/10 text-ink" : "text-mute hover:text-ink"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon className="size-[18px]" />
                    <span
                      className={`absolute -left-[13px] h-6 w-0.5 rounded-full bg-glow transition ${
                        isActive ? "opacity-100" : "opacity-0"
                      }`}
                    />
                    <span className="pointer-events-none absolute left-12 rounded-md bg-deep-950/90 px-2 py-1 text-xs whitespace-nowrap opacity-0 transition group-hover:opacity-100">
                      {label}
                    </span>
                  </>
                )}
              </NavLink>
            ))}
          </nav>
          <div className="flex flex-col items-center gap-2 text-mute/60">
            {[0, 1, 2].map((i) => (
              <span key={i} className="size-1 rounded-full bg-current" />
            ))}
          </div>
        </aside>

        <div className="relative flex min-w-0 flex-1 flex-col">
          {/* 頂部列 */}
          <header className="relative z-30 flex h-16 shrink-0 items-center gap-3 border-b border-white/10 px-4 md:px-6">
            <NavLink to="/" className="flex items-center gap-2.5">
              <Logo className="size-8 md:hidden" />
              <span className="text-lg font-bold tracking-[0.12em] uppercase">Timelore</span>
            </NavLink>

            <nav className="ml-6 hidden items-center gap-1 lg:flex">
              {nav.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === "/"}
                  className={({ isActive }) =>
                    `rounded-full px-3.5 py-1.5 text-sm transition ${
                      isActive ? "bg-white/10 text-ink" : "text-mute hover:text-ink"
                    }`
                  }
                >
                  {label}
                </NavLink>
              ))}
            </nav>

            <button
              onClick={() => setPaletteOpen(true)}
              className="ml-auto flex h-9 items-center gap-2 rounded-full border border-white/10 bg-white/5 pr-2 pl-3 text-sm text-mute transition hover:bg-white/10 hover:text-ink"
            >
              <Search className="size-4" />
              <span className="hidden sm:inline">搜尋國家、人物、建築</span>
              <kbd className="hidden rounded border border-white/15 px-1.5 text-[10px] sm:inline">Ctrl K</kbd>
            </button>
          </header>

          <main className="relative min-h-0 flex-1">
            <div className="absolute inset-x-0 top-0 bottom-14 md:bottom-0">
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

          {/* 手機底部導覽 */}
          <nav className="glass absolute inset-x-0 bottom-0 z-40 flex h-14 items-stretch md:hidden" aria-label="主要導覽">
            {nav.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex flex-1 flex-col items-center justify-center gap-0.5 text-[11px] ${
                    isActive ? "text-glow" : "text-mute"
                  }`
                }
              >
                <Icon className="size-5" />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}
