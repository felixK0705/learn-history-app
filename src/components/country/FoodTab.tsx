import { useState } from "react";
import type { Dish } from "../../data/types";

export default function FoodTab({ foods }: { foods: Dish[] }) {
  const [flipped, setFlipped] = useState<number | null>(null);
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-1">
      {foods.map((f, i) => (
        <button
          key={f.name}
          onClick={() => setFlipped(flipped === i ? null : i)}
          className="group rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-left transition hover:border-glow/40 hover:bg-white/[0.07]"
        >
          <div className="flex items-start gap-3">
            <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-white/10 text-3xl transition group-hover:scale-110">
              {f.emoji}
            </span>
            <div className="min-w-0">
              <h4 className="font-medium text-white">
                {f.name}
                {f.localName && <span className="ml-2 text-xs font-normal text-mute">{f.localName}</span>}
              </h4>
              <p className="mt-1 text-sm leading-relaxed text-mute">{f.description}</p>
            </div>
          </div>
          <div className={`grid transition-all duration-300 ${flipped === i ? "mt-3 grid-rows-[1fr]" : "grid-rows-[0fr]"}`}>
            <p className="overflow-hidden rounded-xl bg-amber-300/10 text-sm leading-relaxed text-amber-100/90">
              <span className="block p-3">📜 {f.history}</span>
            </p>
          </div>
          <span className="mt-2 block text-[11px] text-glow/80">{flipped === i ? "收起" : "點擊看歷史小故事"}</span>
        </button>
      ))}
    </div>
  );
}
