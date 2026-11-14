import { Link } from "react-router-dom";
import { figures, groups } from "../../data/figures";
import { formatYear } from "../../lib/format";

export default function FiguresTab({ iso }: { iso: string }) {
  const list = figures.filter((f) => f.iso === iso).sort((a, b) => a.born - b.born);
  if (!list.length)
    return (
      <div className="py-10 text-center text-sm text-mute">
        關係圖中還沒有這個國家的人物。
        <br />
        <Link to="/figures" className="mt-2 inline-block text-glow hover:underline">
          前往人物關係圖 →
        </Link>
      </div>
    );
  return (
    <ul className="space-y-2">
      {list.map((f) => {
        const g = groups.find((x) => x.id === f.group);
        return (
          <li key={f.id}>
            <Link
              to={`/figures?focus=${f.id}`}
              className="flex items-start gap-3 rounded-2xl border border-white/10 bg-white/[0.04] p-3 transition hover:border-glow/40"
            >
              <span
                className="grid size-10 shrink-0 place-items-center rounded-full font-serif text-lg font-bold text-deep-950"
                style={{ background: g?.color }}
              >
                {f.name[0]}
              </span>
              <div className="min-w-0">
                <div className="font-medium text-white">
                  {f.name}
                  <span className="ml-2 text-xs font-normal text-mute">
                    {formatYear(f.born)} – {formatYear(f.died)}
                  </span>
                </div>
                <div className="text-xs text-glow/80">{f.role}</div>
                <p className="mt-1 line-clamp-2 text-sm text-mute">{f.bio}</p>
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
