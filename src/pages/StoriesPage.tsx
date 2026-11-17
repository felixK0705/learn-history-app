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
import { pick, useLang, useT, type Lang } from "../lib/i18n";
import StoryPlayer, { type Story } from "../components/ai/StoryPlayer";
import { findImage } from "../lib/wikiImage";

type L3 = Record<Lang, string>;
const TOPICS: { title: L3; blurb: L3; era: L3; icon: LucideIcon }[] = [
  {
    title: { "zh-TW": "古埃及金字塔的建造", en: "Building the Pyramids of Egypt", ja: "古代エジプトのピラミッド建設" },
    blurb: { "zh-TW": "四千五百年前，數萬名工匠如何把巨石堆成吉薩大金字塔？", en: "4,500 years ago, how did tens of thousands of workers stack giant stones into the Great Pyramid of Giza?", ja: "4500年前、数万人の職人はどのように巨石を積み上げてギザの大ピラミッドを築いたのか？" },
    era: { "zh-TW": "前 2600 年", en: "c. 2600 BC", ja: "前2600年" },
    icon: Pyramid,
  },
  {
    title: { "zh-TW": "秦始皇統一六國", en: "Qin Shi Huang Unifies China", ja: "始皇帝の中国統一" },
    blurb: { "zh-TW": "從戰國七雄到第一個大一統帝國，書同文、車同軌。", en: "From the Seven Warring States to the first unified empire — one script, one axle width.", ja: "戦国七雄から最初の統一帝国へ。文字と車軸の幅まで統一された。" },
    era: { "zh-TW": "前 221 年", en: "221 BC", ja: "前221年" },
    icon: Crown,
  },
  {
    title: { "zh-TW": "羅馬帝國的興衰", en: "Rise and Fall of the Roman Empire", ja: "ローマ帝国の興亡" },
    blurb: { "zh-TW": "從共和到帝國，再到西羅馬的崩潰，一個千年帝國的起落。", en: "From republic to empire to the collapse of the West — the rise and fall of a thousand-year power.", ja: "共和政から帝政、そして西ローマの崩壊まで。千年帝国の栄枯盛衰。" },
    era: { "zh-TW": "前 27–476 年", en: "27 BC – AD 476", ja: "前27〜476年" },
    icon: Castle,
  },
  {
    title: { "zh-TW": "絲路", en: "The Silk Road", ja: "シルクロード" },
    blurb: { "zh-TW": "絲綢、香料、宗教與思想，沿著駝隊在歐亞大陸間流動。", en: "Silk, spices, faiths and ideas travelled across Eurasia with the camel caravans.", ja: "絹、香辛料、宗教、思想がキャラバンとともにユーラシアを行き交った。" },
    era: { "zh-TW": "前 2 世紀起", en: "From the 2nd century BC", ja: "前2世紀から" },
    icon: Route,
  },
  {
    title: { "zh-TW": "蒙古帝國的擴張", en: "The Mongol Conquests", ja: "モンゴル帝国の拡大" },
    blurb: { "zh-TW": "成吉思汗與子孫建立了史上陸地面積最大的連續帝國。", en: "Genghis Khan and his heirs built the largest contiguous land empire in history.", ja: "チンギス・ハンとその子孫は史上最大の陸続きの帝国を築いた。" },
    era: { "zh-TW": "13 世紀", en: "13th century", ja: "13世紀" },
    icon: Tent,
  },
  {
    title: { "zh-TW": "文藝復興", en: "The Renaissance", ja: "ルネサンス" },
    blurb: { "zh-TW": "佛羅倫斯的藝術家與學者，重新點燃古典文明的光芒。", en: "Florence's artists and scholars rekindled the light of classical civilization.", ja: "フィレンツェの芸術家と学者が古典文明の輝きをよみがえらせた。" },
    era: { "zh-TW": "14–16 世紀", en: "14th–16th centuries", ja: "14〜16世紀" },
    icon: Palette,
  },
  {
    title: { "zh-TW": "大航海時代", en: "The Age of Exploration", ja: "大航海時代" },
    blurb: { "zh-TW": "哥倫布、達伽馬、麥哲倫揚帆出海，世界從此連成一體。", en: "Columbus, da Gama and Magellan set sail, and the world became connected.", ja: "コロンブス、ヴァスコ・ダ・ガマ、マゼランが海へ乗り出し、世界は一つにつながった。" },
    era: { "zh-TW": "15–17 世紀", en: "15th–17th centuries", ja: "15〜17世紀" },
    icon: Ship,
  },
  {
    title: { "zh-TW": "法國大革命", en: "The French Revolution", ja: "フランス革命" },
    blurb: { "zh-TW": "攻占巴士底獄、人權宣言、斷頭台與拿破崙的崛起。", en: "The storming of the Bastille, the Rights of Man, the guillotine and the rise of Napoleon.", ja: "バスティーユ襲撃、人権宣言、ギロチン、そしてナポレオンの台頭。" },
    era: { "zh-TW": "1789 年", en: "1789", ja: "1789年" },
    icon: Flag,
  },
  {
    title: { "zh-TW": "工業革命", en: "The Industrial Revolution", ja: "産業革命" },
    blurb: { "zh-TW": "蒸汽機轟鳴，工廠林立，人類的生活方式被徹底改寫。", en: "Steam engines roared, factories rose, and the way people lived was rewritten.", ja: "蒸気機関がうなり、工場が立ち並び、人々の暮らしは根本から変わった。" },
    era: { "zh-TW": "18–19 世紀", en: "18th–19th centuries", ja: "18〜19世紀" },
    icon: Factory,
  },
  {
    title: { "zh-TW": "明治維新", en: "The Meiji Restoration", ja: "明治維新" },
    blurb: { "zh-TW": "黑船來航後，日本在短短數十年間走向現代化。", en: "After the Black Ships arrived, Japan modernized within a few decades.", ja: "黒船来航ののち、日本はわずか数十年で近代化を遂げた。" },
    era: { "zh-TW": "1868 年", en: "1868", ja: "1868年" },
    icon: TrainFront,
  },
  {
    title: { "zh-TW": "第二次世界大戰", en: "World War II", ja: "第二次世界大戦" },
    blurb: { "zh-TW": "人類史上規模最大的戰爭，如何爆發、如何結束？", en: "How did the largest war in human history begin, and how did it end?", ja: "人類史上最大の戦争はどのように始まり、どのように終わったのか？" },
    era: { "zh-TW": "1939–1945 年", en: "1939–1945", ja: "1939〜1945年" },
    icon: Swords,
  },
  {
    title: { "zh-TW": "阿波羅登月", en: "The Apollo Moon Landing", ja: "アポロ月面着陸" },
    blurb: { "zh-TW": "1969 年，阿姆斯壯在月球留下人類的第一個腳印。", en: "In 1969, Neil Armstrong left humanity's first footprint on the Moon.", ja: "1969年、アームストロングが月面に人類最初の足跡を残した。" },
    era: { "zh-TW": "1969 年", en: "1969", ja: "1969年" },
    icon: Rocket,
  },
];

type Phase = { kind: "idle" } | { kind: "loading"; topic: string; step: "write" | "images" } | { kind: "error"; topic: string; error: AiError } | { kind: "play"; story: Story };

export default function StoriesPage() {
  const lang = useLang();
  const tr = useT();
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
      setPhase({ kind: "error", topic: t, error: e instanceof AiError ? e : new AiError(pick({ "zh-TW": "產生故事時發生錯誤，請稍後再試。", en: "Something went wrong while creating the story. Please try again.", ja: "物語の作成中にエラーが発生しました。もう一度お試しください。" })) });
    }
  };

  const cancel = () => {
    ctl.current?.abort();
    setPhase({ kind: "idle" });
  };

  if (phase.kind === "play") return <StoryPlayer story={phase.story} onExit={() => setPhase({ kind: "idle" })} />;

  return (
    <div className="scroll-thin absolute inset-0 overflow-y-auto">
      <div ref={listRef} className="mx-auto max-w-6xl px-4 pt-[86px] pb-28 md:pt-[100px] md:pr-8 md:pl-[104px]">
        <h1 data-reveal className="text-[28px] leading-tight font-bold md:text-[34px]">
          {tr({ "zh-TW": "歷史故事", en: "History stories", ja: "歴史物語" })}
        </h1>

        <form
          data-reveal
          onSubmit={(e) => {
            e.preventDefault();
            start(input);
          }}
          className="mt-6 flex max-w-2xl items-center gap-2 rounded-full border border-white/15 bg-[#113650]/78 py-1.5 pr-1.5 pl-5 shadow-[0_24px_60px_-20px_rgba(4,18,30,0.7),inset_0_1px_0_rgba(255,255,255,0.18)] backdrop-blur-xl focus-within:border-white/35"
        >
          <Sparkles className="size-4 shrink-0 text-glow" />
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            maxLength={80}
            placeholder={tr({ "zh-TW": "輸入主題", en: "Enter a topic", ja: "テーマを入力" })}
            className="min-w-0 flex-1 bg-transparent text-[15px] text-white outline-none placeholder:text-white/45"
            aria-label={tr({ "zh-TW": "故事主題", en: "Story topic", ja: "物語のテーマ" })}
          />
          <button type="submit" disabled={!input.trim()} className="h-10 shrink-0 rounded-full bg-white px-5 text-[14px] font-semibold text-deep-800 transition hover:bg-glow disabled:bg-white/25 disabled:text-white/60">
            {tr({ "zh-TW": "生成故事", en: "Create story", ja: "物語を作成" })}
          </button>
        </form>

        {phase.kind === "error" && (
          <div data-reveal className="mt-5 flex max-w-2xl gap-3 rounded-2xl border border-amber-300/35 bg-[#113650]/85 p-4 backdrop-blur-xl">
            <AlertTriangle className="mt-0.5 size-5 shrink-0 text-amber-300" />
            <div className="min-w-0 flex-1">
              <p className="text-[14px] font-semibold text-amber-50">{tr({ "zh-TW": `無法產生「${phase.topic}」的故事`, en: `Couldn't create a story about "${phase.topic}"`, ja: `「${phase.topic}」の物語を作成できませんでした` })}</p>
              <p className="mt-1 text-[13.5px] leading-relaxed text-amber-50/85">{phase.error.message}</p>
            </div>
            {!phase.error.disabled && (
              <button onClick={() => start(phase.topic)} className="h-8 shrink-0 self-center rounded-full bg-white px-3.5 text-[13px] font-semibold text-deep-800 hover:bg-glow">
                {tr({ "zh-TW": "再試一次", en: "Try again", ja: "再試行" })}
              </button>
            )}
          </div>
        )}

        <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {TOPICS.map(({ title, blurb, era, icon: Icon }) => (
            <button
              key={title["zh-TW"]}
              data-reveal
              onClick={() => start(title[lang])}
              className="group flex flex-col rounded-[22px] border border-white/15 bg-[#113650]/70 p-5 text-left shadow-[0_18px_40px_-22px_rgba(4,18,30,0.8),inset_0_1px_0_rgba(255,255,255,0.15)] backdrop-blur-xl transition hover:-translate-y-0.5 hover:border-white/35 hover:bg-[#174560]/85"
            >
              <div className="flex items-center justify-between">
                <span className="grid size-10 place-items-center rounded-2xl bg-white/12 ring-1 ring-white/20 transition group-hover:bg-white group-hover:text-deep-800">
                  <Icon className="size-5" />
                </span>
                <span className="text-[11.5px] font-semibold text-white/60">{era[lang]}</span>
              </div>
              <h3 className="mt-4 text-[16.5px] font-bold">{title[lang]}</h3>
              <p className="mt-1.5 text-[13px] leading-relaxed text-white/72">{blurb[lang]}</p>
            </button>
          ))}
        </div>
      </div>

      {phase.kind === "loading" && (
        <div className="absolute inset-0 z-20 grid place-items-center bg-[#0c2a40]/70 p-6 backdrop-blur-md">
          <div ref={loadRef} className="w-full max-w-sm rounded-[26px] border border-white/15 bg-[#113650]/90 p-6 text-center">
            <LoaderCircle className="mx-auto size-10 animate-spin text-glow" />
            <p className="mt-4 text-[17px] font-bold">「{phase.topic}」</p>
            <ol className="mt-4 space-y-2 text-left text-[14px]">
              <li className={`flex items-center gap-2 ${phase.step === "write" ? "text-white" : "text-white/50"}`}>
                <span className={`size-2 rounded-full ${phase.step === "write" ? "animate-pulse bg-glow" : "bg-white/40"}`} />
                {tr({ "zh-TW": "AI 正在撰寫故事…", en: "AI is writing the story…", ja: "AI が物語を執筆中…" })}
              </li>
              <li className={`flex items-center gap-2 ${phase.step === "images" ? "text-white" : "text-white/50"}`}>
                <span className={`size-2 rounded-full ${phase.step === "images" ? "animate-pulse bg-glow" : "bg-white/25"}`} />
                {tr({ "zh-TW": "正在尋找歷史圖片…", en: "Finding historical images…", ja: "歴史画像を検索中…" })}
              </li>
            </ol>
            <button onClick={cancel} className="mt-5 rounded-full border border-white/25 px-4 py-1.5 text-[13px] text-white/85 hover:bg-white/10">
              {tr({ "zh-TW": "取消", en: "Cancel", ja: "キャンセル" })}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
