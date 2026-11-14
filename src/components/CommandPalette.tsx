import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Globe2, Landmark, Search, User } from "lucide-react";
import { countries } from "../data/countries";
import { figures } from "../data/figures";
import { buildings } from "../data/buildings";

interface Item {
  kind: "country" | "figure" | "building";
  id: string;
  title: string;
  subtitle: string;
  keywords: string;
  to: string;
}

const kindMeta = {
  country: { label: "國家", icon: Globe2 },
  figure: { label: "人物", icon: User },
  building: { label: "建築", icon: Landmark },
} as const;

const allItems: Item[] = [
  ...countries.map((c) => ({
    kind: "country" as const,
    id: c.iso,
    title: `${c.flag} ${c.name}`,
    subtitle: `${c.englishName}・${c.capital}`,
    keywords: `${c.name} ${c.englishName} ${c.capital} ${c.iso}`.toLowerCase(),
    to: `/?country=${c.iso}`,
  })),
  ...figures.map((f) => ({
    kind: "figure" as const,
    id: f.id,
    title: f.name,
    subtitle: `${f.englishName}・${f.role}`,
    keywords: `${f.name} ${f.englishName} ${f.role}`.toLowerCase(),
    to: `/figures?focus=${f.id}`,
  })),
  ...buildings.map((b) => ({
    kind: "building" as const,
    id: b.id,
    title: b.name,
    subtitle: `${b.englishName}・${b.location}`,
    keywords: `${b.name} ${b.englishName} ${b.location}`.toLowerCase(),
    to: `/buildings/${b.id}`,
  })),
];

export default function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const results = useMemo(() => {
    const s = q.trim().toLowerCase();
    const list = s ? allItems.filter((i) => i.keywords.includes(s)) : allItems.filter((i) => i.kind === "country");
    return list.slice(0, 40);
  }, [q]);

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
    <div className="fixed inset-0 z-[100] flex items-start justify-center bg-deep-950/60 p-4 pt-[12vh] backdrop-blur-sm" onClick={onClose}>
      <div
        role="dialog"
        aria-label="搜尋"
        className="glass w-full max-w-xl animate-fade-in overflow-hidden rounded-2xl shadow-2xl"
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
            placeholder="輸入國家、歷史人物或建築名稱…"
            className="h-14 flex-1 bg-transparent text-base text-ink outline-none placeholder:text-mute/70"
          />
          <kbd className="rounded border border-white/15 px-1.5 text-[10px] text-mute">Esc</kbd>
        </div>
        <ul className="scroll-thin max-h-[50vh] overflow-y-auto p-2">
          {results.length === 0 && <li className="px-3 py-8 text-center text-sm text-mute">找不到「{q}」相關結果</li>}
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
                  <span className="text-[10px] text-mute">{kindMeta[item.kind].label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
