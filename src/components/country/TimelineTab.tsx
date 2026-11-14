import { useMemo, useState } from "react";
import type { TimelineEvent } from "../../data/types";

const catColors: Record<TimelineEvent["category"], string> = {
  政治: "bg-sky-400",
  戰爭: "bg-rose-400",
  文化: "bg-violet-400",
  科技: "bg-cyan-300",
  宗教: "bg-amber-300",
  經濟: "bg-emerald-400",
};

export default function TimelineTab({ events }: { events: TimelineEvent[] }) {
  const [cat, setCat] = useState<TimelineEvent["category"] | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const sorted = useMemo(() => [...events].sort((a, b) => a.sortYear - b.sortYear), [events]);
  const cats = useMemo(() => [...new Set(sorted.map((e) => e.category))], [sorted]);
  const list = cat ? sorted.filter((e) => e.category === cat) : sorted;

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-1.5">
        <button className={`chip ${cat === null ? "chip-on" : ""}`} onClick={() => setCat(null)}>
          全部 {sorted.length}
        </button>
        {cats.map((c) => (
          <button key={c} className={`chip ${cat === c ? "chip-on" : ""}`} onClick={() => setCat(cat === c ? null : c)}>
            <span className={`size-1.5 rounded-full ${catColors[c]}`} />
            {c}
          </button>
        ))}
      </div>

      <ol className="relative ml-2 border-l border-white/15">
        {list.map((e, i) => {
          const isOpen = open === i;
          return (
            <li key={`${e.year}-${e.title}`} className="relative pb-5 pl-5 last:pb-0">
              <span
                className={`absolute top-1.5 -left-[5px] size-[9px] rounded-full ring-4 ring-deep-950/70 ${catColors[e.category]}`}
              />
              <button className="w-full text-left" onClick={() => setOpen(isOpen ? null : i)} aria-expanded={isOpen}>
                <div className="flex items-baseline gap-2">
                  <span className="font-mono text-xs text-glow">{e.year}</span>
                  <span className="text-[10px] text-mute">{e.category}</span>
                </div>
                <h4 className="mt-0.5 font-medium text-white">{e.title}</h4>
                <p className={`mt-1 text-sm leading-relaxed text-mute ${isOpen ? "" : "line-clamp-2"}`}>{e.description}</p>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
