import { useMemo, useState } from "react";
import { Check, RefreshCw, X } from "lucide-react";
import type { CountryInfo, TimelineEvent } from "../../data/types";
import { countries as allCountries } from "../../data/countries";

interface Question {
  prompt: string;
  options: string[];
  answer: number;
  explain: string;
}

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function buildQuiz(country: CountryInfo): Question[] {
  const events = country.timeline;
  const qs: Question[] = [];

  // 題型一：哪件事比較早？
  for (let k = 0; k < 3 && events.length >= 2; k++) {
    const [a, b] = shuffle(events).slice(0, 2) as [TimelineEvent, TimelineEvent];
    if (a.sortYear === b.sortYear) continue;
    const earlier = a.sortYear < b.sortYear ? 0 : 1;
    qs.push({
      prompt: "下列哪一件事比較早發生？",
      options: [a.title, b.title],
      answer: earlier,
      explain: `${a.title}（${a.year}）；${b.title}（${b.year}）`,
    });
  }

  // 題型二：這件事發生在何時？
  shuffle(events)
    .slice(0, 2)
    .forEach((e) => {
      const others = shuffle(events.filter((x) => x.year !== e.year)).slice(0, 3);
      const opts = shuffle([e, ...others]);
      qs.push({
        prompt: `「${e.title}」發生在什麼時候？`,
        options: opts.map((o) => o.year),
        answer: opts.indexOf(e),
        explain: e.description,
      });
    });

  // 題型三：哪一道是這個國家的美食？
  if (country.foods.length) {
    const f = shuffle(country.foods)[0];
    const decoys = shuffle(allCountries.filter((c) => c.iso !== country.iso).flatMap((c) => c.foods)).slice(0, 3);
    const opts = shuffle([f, ...decoys]);
    qs.push({
      prompt: `下列哪一道是${country.name}的代表美食？`,
      options: opts.map((o) => `${o.emoji} ${o.name}`),
      answer: opts.indexOf(f),
      explain: f.history,
    });
  }

  return shuffle(qs);
}

export default function QuizTab({ country }: { country: CountryInfo }) {
  const [seed, setSeed] = useState(0);
  const quiz = useMemo(() => (seed >= 0 ? buildQuiz(country) : []), [country, seed]);
  const [idx, setIdx] = useState(0);
  const [picked, setPicked] = useState<number | null>(null);
  const [score, setScore] = useState(0);

  const restart = () => {
    setSeed((s) => s + 1);
    setIdx(0);
    setPicked(null);
    setScore(0);
  };

  if (idx >= quiz.length) {
    const ratio = score / quiz.length;
    return (
      <div className="py-8 text-center">
        <div className="text-5xl">{ratio === 1 ? "🏆" : ratio >= 0.6 ? "🎉" : "📚"}</div>
        <p className="mt-4 text-lg text-white">
          答對 {score} / {quiz.length} 題
        </p>
        <p className="mt-1 text-sm text-mute">
          {ratio === 1 ? `你已經是${country.name}歷史通了！` : "回到時間線再複習一下，然後再挑戰一次吧。"}
        </p>
        <button onClick={restart} className="mt-6 inline-flex items-center gap-2 rounded-full bg-glow px-4 py-2 text-sm font-medium text-deep-950">
          <RefreshCw className="size-4" /> 再玩一次
        </button>
      </div>
    );
  }

  const q = quiz[idx];
  return (
    <div>
      <div className="flex items-center justify-between text-xs text-mute">
        <span>
          第 {idx + 1} / {quiz.length} 題
        </span>
        <span>得分 {score}</span>
      </div>
      <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/10">
        <div className="h-full bg-glow transition-[width]" style={{ width: `${(idx / quiz.length) * 100}%` }} />
      </div>
      <h4 className="mt-5 text-base leading-relaxed font-medium text-white">{q.prompt}</h4>
      <ul className="mt-4 space-y-2">
        {q.options.map((o, i) => {
          const state = picked === null ? "idle" : i === q.answer ? "right" : i === picked ? "wrong" : "dim";
          return (
            <li key={i}>
              <button
                disabled={picked !== null}
                onClick={() => {
                  setPicked(i);
                  if (i === q.answer) setScore((s) => s + 1);
                }}
                className={`flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-left text-sm leading-relaxed transition ${
                  state === "idle"
                    ? "border-white/10 bg-white/[0.04] hover:border-glow/50"
                    : state === "right"
                      ? "border-emerald-400/60 bg-emerald-400/15 text-white"
                      : state === "wrong"
                        ? "border-rose-400/60 bg-rose-400/15 text-white"
                        : "border-white/5 opacity-50"
                }`}
              >
                <span className="mt-0.5 font-mono text-xs text-mute">{String.fromCharCode(65 + i)}</span>
                <span className="flex-1">{o}</span>
                {state === "right" && <Check className="size-4 text-emerald-300" />}
                {state === "wrong" && <X className="size-4 text-rose-300" />}
              </button>
            </li>
          );
        })}
      </ul>
      {picked !== null && (
        <div className="mt-4 animate-fade-in">
          <p className="rounded-xl bg-white/[0.05] p-3 text-sm leading-relaxed text-mute">💡 {q.explain}</p>
          <button
            onClick={() => {
              setIdx((n) => n + 1);
              setPicked(null);
            }}
            className="mt-3 w-full rounded-full bg-glow py-2 text-sm font-medium text-deep-950"
          >
            {idx + 1 === quiz.length ? "看結果" : "下一題"}
          </button>
        </div>
      )}
    </div>
  );
}
