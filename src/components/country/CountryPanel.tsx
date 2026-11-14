import { useState } from "react";
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

  return (
    <aside
      className="glass absolute z-30 flex animate-slide-in flex-col shadow-2xl max-lg:inset-x-0 max-lg:bottom-0 max-lg:h-[62%] max-lg:rounded-t-3xl lg:top-4 lg:right-4 lg:bottom-4 lg:w-[420px] lg:rounded-3xl"
      aria-label={`${country.name}歷史資料`}
    >
      <header className="relative shrink-0 px-5 pt-5 pb-3">
        <button onClick={onClose} className="icon-btn absolute top-4 right-4 !size-8" aria-label="關閉">
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

      <nav className="scroll-thin flex shrink-0 gap-1 overflow-x-auto border-y border-white/10 px-3 py-2" role="tablist">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={`flex shrink-0 items-center gap-1 rounded-full px-2.5 py-1.5 text-[13px] transition ${
              tab === id ? "bg-glow text-deep-950 font-medium" : "text-mute hover:bg-white/10 hover:text-ink"
            }`}
          >
            <Icon className="size-3.5" />
            {label}
          </button>
        ))}
      </nav>

      <div key={tab} className="scroll-thin min-h-0 flex-1 animate-fade-in overflow-y-auto px-5 py-4">
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
