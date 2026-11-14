import { useRef, useState } from "react";
import { gsap, prefersReducedMotion, useGSAP, useReveal } from "../../lib/motion";
import { BookOpenCheck, Church, Clock, Landmark, Languages, Users, UtensilsCrossed, X } from "lucide-react";
import type { CountryInfo } from "../../data/types";
import TimelineTab from "./TimelineTab";
import FoodTab from "./FoodTab";
import ReligionTab from "./ReligionTab";
import LanguageTab from "./LanguageTab";
import BuildingsTab from "./BuildingsTab";
import FiguresTab from "./FiguresTab";
import QuizTab from "./QuizTab";

const tabs = [
  { id: "timeline", label: "時間線", icon: Clock },
  { id: "food", label: "美食", icon: UtensilsCrossed },
  { id: "religion", label: "宗教", icon: Church },
  { id: "language", label: "語言", icon: Languages },
  { id: "buildings", label: "建築", icon: Landmark },
  { id: "figures", label: "人物", icon: Users },
  { id: "quiz", label: "測驗", icon: BookOpenCheck },
] as const;

type TabId = (typeof tabs)[number]["id"];

export default function CountryPanel({ country, onClose }: { country: CountryInfo; onClose: () => void }) {
  const [tab, setTab] = useState<TabId>("timeline");
  const panelRef = useRef<HTMLElement>(null);
  const headerRef = useRef<HTMLElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const navRef = useRef<HTMLElement>(null);
  const pillRef = useRef<HTMLSpanElement>(null);

  // 面板進場：桌機由右滑入、手機由下滑入
  useGSAP(
    () => {
      if (prefersReducedMotion()) return;
      const mm = gsap.matchMedia();
      mm.add("(min-width: 1024px)", () => {
        gsap.fromTo(panelRef.current, { x: 60, autoAlpha: 0 }, { x: 0, autoAlpha: 1, duration: 0.7, ease: "expo.out" });
      });
      mm.add("(max-width: 1023px)", () => {
        gsap.fromTo(panelRef.current, { yPercent: 100 }, { yPercent: 0, duration: 0.6, ease: "expo.out" });
      });
      gsap.fromTo(headerRef.current!.children, { y: 14, autoAlpha: 0 }, { y: 0, autoAlpha: 1, stagger: 0.07, delay: 0.15, clearProps: "all" });
    },
    { scope: panelRef },
  );

  // 分頁內容依序出現
  useReveal(contentRef, [tab], { stagger: ":scope > * > *", y: 14, each: 0.05, duration: 0.5 });

  // 分頁指示膠囊滑動
  useGSAP(
    () => {
      const btn = navRef.current?.querySelector<HTMLElement>(`[data-tab="${tab}"]`);
      if (!btn || !pillRef.current) return;
      gsap.to(pillRef.current, {
        x: btn.offsetLeft,
        width: btn.offsetWidth,
        duration: pillRef.current.dataset.ready ? 0.45 : 0,
        ease: "power3.inOut",
      });
      pillRef.current.dataset.ready = "1";
      btn.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
    },
    { dependencies: [tab] },
  );

  const close = () => {
    if (prefersReducedMotion() || !panelRef.current) return onClose();
    const desktop = window.matchMedia("(min-width: 1024px)").matches;
    gsap.to(panelRef.current, {
      ...(desktop ? { x: 60, autoAlpha: 0 } : { yPercent: 100 }),
      duration: 0.35,
      ease: "power2.in",
      onComplete: onClose,
    });
  };

  return (
    <aside
      ref={panelRef}
      className="glass absolute z-30 flex flex-col shadow-2xl max-lg:inset-x-0 max-lg:bottom-0 max-lg:h-[62%] max-lg:rounded-t-3xl lg:top-4 lg:right-4 lg:bottom-4 lg:w-[420px] lg:rounded-3xl"
      aria-label={`${country.name}歷史資料`}
    >
      <header ref={headerRef} className="relative shrink-0 px-5 pt-5 pb-3">
        <button onClick={close} className="icon-btn absolute top-4 right-4 z-10 !size-8" aria-label="關閉">
          <X className="size-4" />
        </button>
        <div className="flex items-center gap-3">
          <span className="text-4xl leading-none drop-shadow">{country.flag}</span>
          <div className="min-w-0">
            <h2 className="font-serif text-2xl font-bold text-white">{country.name}</h2>
            <p className="text-xs text-mute">
              {country.englishName}・{country.continent}・首都 {country.capital}
            </p>
          </div>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-ink/85">{country.summary}</p>
      </header>

      <nav ref={navRef} className="scroll-thin relative flex shrink-0 gap-1 overflow-x-auto border-y border-white/10 px-3 py-2" role="tablist">
        <span ref={pillRef} className="absolute top-2 left-0 h-[calc(100%-1rem)] w-0 rounded-full bg-glow" aria-hidden="true" />
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            data-tab={id}
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={`relative z-10 flex shrink-0 items-center gap-1 rounded-full px-2.5 py-1.5 text-[13px] transition-colors duration-300 ${
              tab === id ? "text-deep-950 font-medium" : "text-mute hover:text-ink"
            }`}
          >
            <Icon className="size-3.5" />
            {label}
          </button>
        ))}
      </nav>

      <div ref={contentRef} className="scroll-thin min-h-0 flex-1 overflow-y-auto px-5 py-4">
        {tab === "timeline" && <TimelineTab events={country.timeline} />}
        {tab === "food" && <FoodTab foods={country.foods} />}
        {tab === "religion" && <ReligionTab religions={country.religions} />}
        {tab === "language" && <LanguageTab languages={country.languages} />}
        {tab === "buildings" && <BuildingsTab iso={country.iso} />}
        {tab === "figures" && <FiguresTab iso={country.iso} />}
        {tab === "quiz" && <QuizTab country={country} />}
      </div>
    </aside>
  );
}
