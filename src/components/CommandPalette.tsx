import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Globe2, Landmark, Search, User } from "lucide-react";
import { CONTINENT, countries, countryName } from "../data/world";
import { useReveal } from "../lib/motion";
import { useBuildings, useFigures } from "../data/localized";
import { useLang, useT, type Tr } from "../lib/i18n";

interface Item {
  kind: "country" | "figure" | "building";
  id: string;
  title: string;
  subtitle: string;
  keywords: string;
  to: string;
}

const kindMeta: Record<Item["kind"], { label: Tr; icon: typeof Globe2 }> = {
  country: { label: { "zh-TW": "國家", en: "Country", ja: "国" }, icon: Globe2 },
  figure: { label: { "zh-TW": "人物", en: "Person", ja: "人物" }, icon: User },
  building: { label: { "zh-TW": "建築", en: "Building", ja: "建築" }, icon: Landmark },
};
const byRank = [...countries].sort((a, b) => a.rank - b.rank);

export default function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  useReveal(backdropRef, [open], { y: 0, duration: 0.25 });
  useReveal(dialogRef, [open], { y: -12, scale: 0.97, duration: 0.4 });
  const navigate = useNavigate();
  const lang = useLang();
  const t = useT();
  const { figures } = useFigures();
  const buildings = useBuildings();

  // 中文、英文與目前語言的名稱都能搜到；台／臺異體字也能搜到
  const allItems = useMemo<Item[]>(
    () => [
      ...byRank.map((c) => {
        const name = countryName(c, lang);
        return {
          kind: "country" as const,
          id: c.iso,
          title: name,
          subtitle: lang === "en" ? t(CONTINENT[c.continent]) : `${c.en}・${t(CONTINENT[c.continent])}`,
          keywords: `${name} ${c.zh} ${c.zh.replace(/台/g, "臺")} ${c.en} ${c.iso}`.toLowerCase(),
          to: `/?country=${c.iso}`,
        };
      }),
      ...figures.map((f) => ({
        kind: "figure" as const,
        id: f.id,
        title: f.name,
        subtitle: lang === "en" ? f.role : `${f.englishName}・${f.role}`,
        keywords: `${f.name} ${f.englishName} ${f.role}`.toLowerCase(),
        to: `/figures?focus=${f.id}`,
      })),
      ...buildings.map((b) => ({
        kind: "building" as const,
        id: b.id,
        title: b.name,
        subtitle: lang === "en" ? b.location : `${b.englishName}・${b.location}`,
        keywords: `${b.name} ${b.englishName} ${b.location}`.toLowerCase(),
        to: `/buildings/${b.id}`,
      })),
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [lang, figures, buildings],
  );

  const results = useMemo(() => {
    const s = q.trim().toLowerCase();
    const list = s ? allItems.filter((i) => i.keywords.includes(s)) : allItems.filter((i) => i.kind === "country");
    return list.slice(0, 40);
  }, [q, allItems]);

  useEffect(() => {
    if (open) {
      setQ("");
      setActive(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  useEffect(() => setActive(0), [q]);

  if (!open) return null;

  const go = (item: Item) => {
    navigate(item.to);
    onClose();
  };

  return (
    <div ref={backdropRef} className="fixed inset-0 z-[100] flex items-start justify-center bg-deep-950/60 p-4 pt-[12vh] backdrop-blur-sm" onClick={onClose}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-label={t({ "zh-TW": "搜尋", en: "Search", ja: "検索" })}
        className="glass w-full max-w-xl overflow-hidden rounded-2xl shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-white/10 px-4">
          <Search className="size-4 text-mute" />
          <input
            ref={inputRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") onClose();
              if (e.key === "ArrowDown") {
                e.preventDefault();
                setActive((a) => Math.min(a + 1, results.length - 1));
              }
              if (e.key === "ArrowUp") {
                e.preventDefault();
                setActive((a) => Math.max(a - 1, 0));
              }
              if (e.key === "Enter" && results[active]) go(results[active]);
            }}
            placeholder={t({ "zh-TW": "輸入國家、歷史人物或建築名稱…", en: "Search countries, historical figures or buildings…", ja: "国・歴史上の人物・建築を検索…" })}
            className="h-14 flex-1 bg-transparent text-base text-ink outline-none placeholder:text-mute/70"
          />
          <kbd className="rounded border border-white/15 px-1.5 text-[10px] text-mute">Esc</kbd>
        </div>
        <ul className="scroll-thin max-h-[50vh] overflow-y-auto p-2">
          {results.length === 0 && <li className="px-3 py-8 text-center text-sm text-mute">{t({ "zh-TW": `找不到「${q}」相關結果`, en: `No results for "${q}"`, ja: `「${q}」に一致する結果はありません` })}</li>}
          {results.map((item, i) => {
            const Icon = kindMeta[item.kind].icon;
            return (
              <li key={`${item.kind}-${item.id}`}>
                <button
                  onMouseEnter={() => setActive(i)}
                  onClick={() => go(item)}
                  className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition ${
                    i === active ? "bg-white/10" : ""
                  }`}
                >
                  <Icon className="size-4 shrink-0 text-glow" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm text-ink">{item.title}</span>
                    <span className="block truncate text-xs text-mute">{item.subtitle}</span>
                  </span>
                  <span className="text-[10px] text-mute">{t(kindMeta[item.kind].label)}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
