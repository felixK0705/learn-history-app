import { Volume2 } from "lucide-react";
import type { Language } from "../../data/types";
import { canSpeak, langCodeFor, speak } from "../../lib/speech";

const statusStyle: Record<Language["status"], string> = {
  官方: "bg-glow/20 text-glow",
  通用: "bg-emerald-400/15 text-emerald-300",
  地區: "bg-amber-300/15 text-amber-200",
  少數: "bg-white/10 text-mute",
};

export default function LanguageTab({ languages }: { languages: Language[] }) {
  const speechOk = canSpeak();
  return (
    <ul className="space-y-3">
      {languages.map((l) => {
        const code = langCodeFor(l.name);
        return (
          <li key={l.name} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
            <div className="flex items-center gap-2">
              <h4 className="font-medium text-white">{l.name}</h4>
              <span className={`rounded-full px-2 py-0.5 text-[10px] ${statusStyle[l.status]}`}>{l.status}</span>
              <span className="ml-auto text-[11px] text-mute">{l.family}</span>
            </div>
            <div className="mt-3 flex items-center gap-3 rounded-xl bg-deep-950/40 px-4 py-3">
              <div className="min-w-0 flex-1">
                <div className="text-2xl text-white">{l.greeting}</div>
                {l.pronunciation && <div className="mt-0.5 text-xs text-mute italic">{l.pronunciation}</div>}
              </div>
              {speechOk && code && (
                <button
                  className="icon-btn shrink-0"
                  onClick={() => speak(l.greeting, code)}
                  aria-label={`朗讀 ${l.greeting}`}
                  title="朗讀問候語（使用瀏覽器語音）"
                >
                  <Volume2 className="size-4" />
                </button>
              )}
            </div>
            <p className="mt-3 text-sm leading-relaxed text-mute">{l.description}</p>
          </li>
        );
      })}
    </ul>
  );
}
