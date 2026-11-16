import { useRef, useState } from "react";
import {
  AlertTriangle,
  Castle,
  Crown,
  Factory,
  LoaderCircle,
  Palette,
  Pyramid,
  Rocket,
  Route,
  Ship,
  Sparkles,
  Swords,
  Tent,
  TrainFront,
  Flag,
  type LucideIcon,
} from "lucide-react";
import { gsap, prefersReducedMotion, useGSAP, useReveal } from "../lib/motion";
import { AiError, postAi } from "../lib/ai";
import StoryPlayer, { type Story } from "../components/ai/StoryPlayer";
import { findImage } from "../lib/wikiImage";

const TOPICS: { title: string; blurb: string; era: string; icon: LucideIcon }[] = [
  { title: "古埃及金字塔的建造", blurb: "四千五百年前，數萬名工匠如何把巨石堆成吉薩大金字塔？", era: "前 2600 年", icon: Pyramid },
  { title: "秦始皇統一六國", blurb: "從戰國七雄到第一個大一統帝國，書同文、車同軌。", era: "前 221 年", icon: Crown },
  { title: "羅馬帝國的興衰", blurb: "從共和到帝國，再到西羅馬的崩潰，一個千年帝國的起落。", era: "前 27–476 年", icon: Castle },
  { title: "絲路", blurb: "絲綢、香料、宗教與思想，沿著駝隊在歐亞大陸間流動。", era: "前 2 世紀起", icon: Route },
  { title: "蒙古帝國的擴張", blurb: "成吉思汗與子孫建立了史上陸地面積最大的連續帝國。", era: "13 世紀", icon: Tent },
  { title: "文藝復興", blurb: "佛羅倫斯的藝術家與學者，重新點燃古典文明的光芒。", era: "14–16 世紀", icon: Palette },
  { title: "大航海時代", blurb: "哥倫布、達伽馬、麥哲倫揚帆出海，世界從此連成一體。", era: "15–17 世紀", icon: Ship },
  { title: "法國大革命", blurb: "攻占巴士底獄、人權宣言、斷頭台與拿破崙的崛起。", era: "1789 年", icon: Flag },
  { title: "工業革命", blurb: "蒸汽機轟鳴，工廠林立，人類的生活方式被徹底改寫。", era: "18–19 世紀", icon: Factory },
  { title: "明治維新", blurb: "黑船來航後，日本在短短數十年間走向現代化。", era: "1868 年", icon: TrainFront },
  { title: "第二次世界大戰", blurb: "人類史上規模最大的戰爭，如何爆發、如何結束？", era: "1939–1945 年", icon: Swords },
  { title: "阿波羅登月", blurb: "1969 年，阿姆斯壯在月球留下人類的第一個腳印。", era: "1969 年", icon: Rocket },
];

type Phase = { kind: "idle" } | { kind: "loading"; topic: string; step: "write" | "images" } | { kind: "error"; topic: string; error: AiError } | { kind: "play"; story: Story };

export default function StoriesPage() {
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [input, setInput] = useState("");
  const listRef = useRef<HTMLDivElement>(null);
  const loadRef = useRef<HTMLDivElement>(null);
  const ctl = useRef<AbortController | null>(null);

  useReveal(listRef, [phase.kind === "idle" || phase.kind === "error"], { stagger: "[data-reveal]", y: 18, each: 0.04 });

  useGSAP(
    () => {
      if (phase.kind !== "loading" || !loadRef.current || prefersReducedMotion()) return;
      gsap.fromTo(loadRef.current, { autoAlpha: 0, scale: 0.96 }, { autoAlpha: 1, scale: 1, duration: 0.5 });
    },
    { dependencies: [phase.kind] },
  );

  const start = async (topic: string) => {
    const t = topic.trim();
    if (!t) return;
    ctl.current?.abort();
    const c = new AbortController();
    ctl.current = c;
    setPhase({ kind: "loading", topic: t, step: "write" });
    try {
      const story = await postAi<Story>("story", { topic: t }, c.signal);
      if (c.signal.aborted) return;
      setPhase({ kind: "loading", topic: t, step: "images" });
      const images = await Promise.all(story.slides.map((s) => findImage(s.imageQuery)));
      if (c.signal.aborted) return;
      setPhase({ kind: "play", story: { ...story, slides: story.slides.map((s, i) => ({ ...s, image: images[i] })) } });
    } catch (e) {
      if (c.signal.aborted) return;
      setPhase({ kind: "error", topic: t, error: e instanceof AiError ? e : new AiError("產生故事時發生錯誤，請稍後再試。") });
    }
  };

  const cancel = () => {
    ctl.current?.abort();
    setPhase({ kind: "idle" });
  };

  if (phase.kind === "play") return <StoryPlayer story={phase.story} onExit={() => setPhase({ kind: "idle" })} />;

  return (
    <div className="scroll-thin absolute inset-0 overflow-y-auto">
      <div ref={listRef} className="mx-auto max-w-6xl px-4 pt-[86px] pb-28 md:px-8 md:pt-[100px]">
        <h1 data-reveal className="text-[28px] leading-tight font-bold md:text-[34px]">
          歷史故事
        </h1>

        <form
          data-reveal
          onSubmit={(e) => {
            e.preventDefault();
            start(input);
          }}
          className="mt-6 flex max-w-2xl items-center gap-2 rounded-full border border-white/15 bg-[#071d4f]/78 py-1.5 pr-1.5 pl-5 shadow-[0_24px_60px_-20px_rgba(0,10,40,0.7),inset_0_1px_0_rgba(255,255,255,0.18)] backdrop-blur-xl focus-within:border-white/35"
        >
          <Sparkles className="size-4 shrink-0 text-glow" />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            maxLength={80}
            placeholder="輸入主題"
            className="min-w-0 flex-1 bg-transparent text-[15px] text-white outline-none placeholder:text-white/45"
            aria-label="故事主題"
          />
          <button type="submit" disabled={!input.trim()} className="h-10 shrink-0 rounded-full bg-white px-5 text-[14px] font-semibold text-deep-800 transition hover:bg-glow disabled:bg-white/25 disabled:text-white/60">
            生成故事
          </button>
        </form>

        {phase.kind === "error" && (
          <div data-reveal className="mt-5 flex max-w-2xl gap-3 rounded-2xl border border-amber-300/35 bg-[#071d4f]/85 p-4 backdrop-blur-xl">
            <AlertTriangle className="mt-0.5 size-5 shrink-0 text-amber-300" />
            <div className="min-w-0 flex-1">
              <p className="text-[14px] font-semibold text-amber-50">無法產生「{phase.topic}」的故事</p>
              <p className="mt-1 text-[13.5px] leading-relaxed text-amber-50/85">{phase.error.message}</p>
            </div>
            {!phase.error.disabled && (
              <button onClick={() => start(phase.topic)} className="h-8 shrink-0 self-center rounded-full bg-white px-3.5 text-[13px] font-semibold text-deep-800 hover:bg-glow">
                再試一次
              </button>
            )}
          </div>
        )}

        <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {TOPICS.map(({ title, blurb, era, icon: Icon }) => (
            <button
              key={title}
              data-reveal
              onClick={() => start(title)}
              className="group flex flex-col rounded-[22px] border border-white/15 bg-[#071d4f]/70 p-5 text-left shadow-[0_18px_40px_-22px_rgba(0,10,40,0.8),inset_0_1px_0_rgba(255,255,255,0.15)] backdrop-blur-xl transition hover:-translate-y-0.5 hover:border-white/35 hover:bg-[#0a2766]/85"
            >
              <div className="flex items-center justify-between">
                <span className="grid size-10 place-items-center rounded-2xl bg-white/12 ring-1 ring-white/20 transition group-hover:bg-white group-hover:text-deep-800">
                  <Icon className="size-5" />
                </span>
                <span className="text-[11.5px] font-semibold text-white/60">{era}</span>
              </div>
              <h3 className="mt-4 text-[16.5px] font-bold">{title}</h3>
              <p className="mt-1.5 text-[13px] leading-relaxed text-white/72">{blurb}</p>
            </button>
          ))}
        </div>
      </div>

      {phase.kind === "loading" && (
        <div className="absolute inset-0 z-20 grid place-items-center bg-[#041640]/70 p-6 backdrop-blur-md">
          <div ref={loadRef} className="w-full max-w-sm rounded-[26px] border border-white/15 bg-[#071d4f]/90 p-6 text-center">
            <LoaderCircle className="mx-auto size-10 animate-spin text-glow" />
            <p className="mt-4 text-[17px] font-bold">「{phase.topic}」</p>
            <ol className="mt-4 space-y-2 text-left text-[14px]">
              <li className={`flex items-center gap-2 ${phase.step === "write" ? "text-white" : "text-white/50"}`}>
                <span className={`size-2 rounded-full ${phase.step === "write" ? "animate-pulse bg-glow" : "bg-white/40"}`} />
                AI 正在撰寫故事…
              </li>
              <li className={`flex items-center gap-2 ${phase.step === "images" ? "text-white" : "text-white/50"}`}>
                <span className={`size-2 rounded-full ${phase.step === "images" ? "animate-pulse bg-glow" : "bg-white/25"}`} />
                正在尋找歷史圖片…
              </li>
            </ol>
            <button onClick={cancel} className="mt-5 rounded-full border border-white/25 px-4 py-1.5 text-[13px] text-white/85 hover:bg-white/10">
              取消
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
