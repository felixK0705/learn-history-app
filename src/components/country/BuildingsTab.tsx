import { Link } from "react-router-dom";
import { Box } from "lucide-react";
import { buildings } from "../../data/buildings";

export default function BuildingsTab({ iso }: { iso: string }) {
  const list = buildings.filter((b) => b.iso === iso).sort((a, b) => a.sortYear - b.sortYear);
  if (!list.length)
    return (
      <div className="py-10 text-center text-sm text-mute">
        這個國家的建築 3D 模型還在製作中。
        <br />
        <Link to="/buildings" className="mt-2 inline-block text-glow hover:underline">
          看看其他國家的建築 →
        </Link>
      </div>
    );
  return (
    <ul className="space-y-3">
      {list.map((b) => (
        <li key={b.id}>
          <Link
            to={`/buildings/${b.id}`}
            className="group block rounded-2xl border border-white/10 bg-gradient-to-br from-white/[0.07] to-transparent p-4 transition hover:border-glow/40"
          >
            <div className="flex items-center gap-2 text-[11px] text-amber-200">
              {b.era}
              <span className="text-mute">・{b.style}</span>
            </div>
            <h4 className="mt-1 font-serif text-lg font-bold text-white">{b.name}</h4>
            <p className="mt-1 line-clamp-2 text-sm text-mute">{b.description}</p>
            <span className="mt-3 inline-flex items-center gap-1.5 text-sm text-glow">
              <Box className="size-4 transition group-hover:rotate-12" /> 進入 3D 檢視
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
