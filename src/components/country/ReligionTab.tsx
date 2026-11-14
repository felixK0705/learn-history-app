import { useState } from "react";
import type { Religion } from "../../data/types";

const palette = ["#5cc8ff", "#fbbf24", "#a78bfa", "#34d399", "#f472b6", "#94a3b8"];

export default function ReligionTab({ religions }: { religions: Religion[] }) {
  const [active, setActive] = useState(0);
  const total = religions.reduce((s, r) => s + r.percent, 0) || 1;
  const R = 52;
  const C = 2 * Math.PI * R;
  let offset = 0;

  return (
    <div>
      <div className="flex items-center gap-5">
        <svg viewBox="0 0 140 140" className="size-36 shrink-0 -rotate-90" role="img" aria-label="宗教人口比例圓餅圖">
          <circle cx="70" cy="70" r={R} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="18" />
          {religions.map((r, i) => {
            const len = (r.percent / total) * C;
            const seg = (
              <circle
                key={r.name}
                cx="70"
                cy="70"
                r={R}
                fill="none"
                stroke={palette[i % palette.length]}
                strokeWidth={i === active ? 22 : 16}
                strokeDasharray={`${Math.max(len - 2, 0)} ${C}`}
                strokeDashoffset={-offset}
                className="cursor-pointer transition-all duration-300"
                onMouseEnter={() => setActive(i)}
                onClick={() => setActive(i)}
              />
            );
            offset += len;
            return seg;
          })}
        </svg>
        <div className="min-w-0">
          <div className="text-4xl font-semibold" style={{ color: palette[active % palette.length] }}>
            {religions[active]?.percent}%
          </div>
          <div className="mt-1 text-white">{religions[active]?.name}</div>
          <div className="mt-1 text-[11px] text-mute">約略人口比例</div>
        </div>
      </div>

      <ul className="mt-5 space-y-2">
        {religions.map((r, i) => (
          <li key={r.name}>
            <button
              onClick={() => setActive(i)}
              className={`w-full rounded-xl border p-3 text-left transition ${
                i === active ? "border-white/20 bg-white/[0.07]" : "border-transparent hover:bg-white/[0.04]"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="size-2.5 rounded-full" style={{ background: palette[i % palette.length] }} />
                <span className="font-medium text-white">{r.name}</span>
                <span className="ml-auto font-mono text-sm text-mute">{r.percent}%</span>
              </div>
              <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/10">
                <div className="h-full rounded-full" style={{ width: `${r.percent}%`, background: palette[i % palette.length] }} />
              </div>
              {i === active && <p className="mt-2 text-sm leading-relaxed text-mute">{r.description}</p>}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
