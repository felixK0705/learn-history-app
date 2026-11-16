import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowLeft, Pause, Play, RotateCcw, SkipBack, SkipForward, Volume2, VolumeX, LayoutGrid } from "lucide-react";
import { gsap, prefersReducedMotion, useGSAP } from "../../lib/motion";
import { canSpeak } from "../../lib/speech";

export type StorySlide = { caption: string; narration: string; imageQuery: string; image?: string | null };
export type Story = { title: string; slides: StorySlide[] };

const PANEL =
  "border border-white/15 bg-[#071d4f]/78 shadow-[0_24px_60px_-20px_rgba(0,10,40,0.7),inset_0_1px_0_rgba(255,255,255,0.18)] backdrop-blur-xl";

/** 找不到圖片時使用的漸層背景 */
const GRADIENTS = [
  "radial-gradient(120% 90% at 20% 10%, #2a8fd4 0%, #11449a 45%, #041640 100%)",
  "radial-gradient(120% 90% at 80% 20%, #7c5cd6 0%, #23307f 50%, #050f33 100%)",
  "radial-gradient(120% 90% at 30% 80%, #c98a3a 0%, #6b3b2a 45%, #140a1f 100%)",
  "radial-gradient(120% 90% at 70% 70%, #1fa58f 0%, #0f4f6b 50%, #04142e 100%)",
  "radial-gradient(120% 90% at 50% 0%, #d0566b 0%, #5a2a6e 50%, #0b0b2a 100%)",
];

// ───────── 語音朗讀 ─────────
function zhVoice() {
  const voices = window.speechSynthesis.getVoices();
  return voices.find((v) => v.lang === "zh-TW") ?? voices.find((v) => /zh[-_](TW|Hant)/i.test(v.lang)) ?? voices.find((v) => v.lang.toLowerCase().startsWith("zh"));
}

/** 依句切開分段朗讀（避免 Chrome 長句被截斷），全部唸完後呼叫 onDone */
function speakAll(text: string, onDone: (failed: boolean) => void, keep: SpeechSynthesisUtterance[]) {
  const synth = window.speechSynthesis;
  synth.cancel();
  const parts = text.match(/[^。！？!?；;]+[。！？!?；;]?/g)?.map((s) => s.trim()).filter(Boolean) ?? [text];
  const voice = zhVoice();
  keep.length = 0;
  parts.forEach((part, i) => {
    const u = new SpeechSynthesisUtterance(part);
    u.lang = "zh-TW";
    u.rate = 0.9;
    if (voice) u.voice = voice;
    if (i === parts.length - 1) u.onend = () => onDone(false);
    u.onerror = (e) => {
      if (e.error !== "interrupted" && e.error !== "canceled") onDone(true);
    };
    keep.push(u); // 保留參照，避免被回收後不觸發 onend
    synth.speak(u);
  });
}

const speakSeconds = (t: string) => t.length / 4.2 + 1;
const readSeconds = (t: string) => Math.max(6, t.length / 6 + 2);

export default function StoryPlayer({ story, onExit }: { story: Story; onExit: () => void }) {
  const total = story.slides.length;
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [ended, setEnded] = useState(false);
  const [muted, setMuted] = useState(() => !canSpeak());
  const rootRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const fillRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const utterances = useRef<SpeechSynthesisUtterance[]>([]);
  const slide = story.slides[index];

  const go = useCallback(
    (i: number) => {
      if (i >= total) {
        setEnded(true);
        setPlaying(false);
        return;
      }
      setEnded(false);
      setIndex(Math.max(0, i));
    },
    [total],
  );

  // 播放：朗讀（或依字數計時）完成後自動下一張
  useEffect(() => {
    if (!playing || ended) return;
    let done = false;
    const timers: number[] = [];
    const startedAt = performance.now();
    const useVoice = !muted && canSpeak();
    const secs = useVoice ? speakSeconds(slide.narration) : readSeconds(slide.narration);
    // 朗讀失敗（例如系統沒有中文語音）時，改以閱讀時間計時，避免投影片一閃而過
    const next = (failed = false) => {
      if (done) return;
      done = true;
      const elapsed = performance.now() - startedAt;
      const minMs = failed ? readSeconds(slide.narration) * 1000 : 4000;
      timers.push(window.setTimeout(() => go(index + 1), Math.max(900, minMs - elapsed)));
    };
    if (useVoice) {
      speakAll(slide.narration, next, utterances.current);
      // 保險：某些瀏覽器沒有語音或不觸發 onend 時仍會前進
      timers.push(window.setTimeout(() => next(), (secs * 1.8 + 4) * 1000));
    } else {
      timers.push(window.setTimeout(() => next(), secs * 1000));
    }
    const fill = fillRefs.current[index];
    const tween = fill ? gsap.fromTo(fill, { scaleX: 0 }, { scaleX: 1, duration: secs, ease: "none" }) : null;
    return () => {
      done = true;
      timers.forEach(clearTimeout);
      tween?.kill();
      if (canSpeak()) window.speechSynthesis.cancel();
    };
  }, [index, playing, muted, ended, slide.narration, go]);

  // 進度條：已播完的填滿、之後的清空
  useEffect(() => {
    fillRefs.current.forEach((el, i) => {
      if (!el) return;
      if (i < index || (ended && i === index)) gsap.set(el, { scaleX: 1 });
      else if (i > index) gsap.set(el, { scaleX: 0 });
    });
  }, [index, ended]);

  useEffect(() => () => void (canSpeak() && window.speechSynthesis.cancel()), []);

  // 圖片交叉淡入＋Ken Burns 緩慢放大
  useGSAP(
    () => {
      const layers = gsap.utils.toArray<HTMLElement>("[data-layer]");
      layers.forEach((el, i) => {
        const on = i === index;
        gsap.to(el, { autoAlpha: on ? 1 : 0, duration: prefersReducedMotion() ? 0 : 1.2, ease: "power2.inOut", overwrite: "auto" });
        if (on && !prefersReducedMotion()) {
          const img = el.querySelector("[data-kb]");
          const dir = i % 2 ? 1 : -1;
          gsap.fromTo(img, { scale: 1.02, xPercent: 0, yPercent: 0 }, { scale: 1.16, xPercent: 2.5 * dir, yPercent: -1.5, duration: 22, ease: "none", overwrite: true });
        }
      });
    },
    { scope: rootRef, dependencies: [index] },
  );

  // 字幕淡入
  useGSAP(
    () => {
      if (!textRef.current || prefersReducedMotion()) return;
      gsap.fromTo(textRef.current.querySelectorAll("[data-t]"), { autoAlpha: 0, y: 18 }, { autoAlpha: 1, y: 0, duration: 0.8, stagger: 0.15, delay: 0.3, ease: "power3.out" });
    },
    { dependencies: [index] },
  );

  useGSAP(
    () => {
      if (!ended || !endRef.current || prefersReducedMotion()) return;
      gsap.fromTo(endRef.current.children, { autoAlpha: 0, y: 20 }, { autoAlpha: 1, y: 0, stagger: 0.1, duration: 0.6 });
    },
    { dependencies: [ended] },
  );

  // 鍵盤：← → 換頁、空白鍵播放／暫停、Esc 離開
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.closest("input,textarea")) return;
      if (e.key === "ArrowRight") go(index + 1);
      else if (e.key === "ArrowLeft") go(index - 1);
      else if (e.key === " ") {
        e.preventDefault();
        setPlaying((p) => !p);
      } else if (e.key === "Escape") onExit();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [index, go, onExit]);

  const replay = () => {
    setEnded(false);
    setIndex(0);
    setPlaying(true);
  };

  const ctrl = "grid size-11 place-items-center rounded-full text-white transition hover:bg-white/15 disabled:opacity-35";

  return (
    <div ref={rootRef} className="absolute inset-0 overflow-hidden bg-[#020c24] text-white">
      {/* 背景圖層 */}
      {story.slides.map((s, i) => (
        <div key={i} data-layer className="invisible absolute inset-0 opacity-0">
          {s.image ? (
            <img data-kb src={s.image} alt={s.caption} className="size-full object-cover will-change-transform" />
          ) : (
            <div data-kb className="size-full will-change-transform" style={{ background: GRADIENTS[i % GRADIENTS.length] }} />
          )}
        </div>
      ))}
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(2,12,36,0.75)_0%,rgba(2,12,36,0.1)_22%,rgba(2,12,36,0.15)_50%,rgba(2,12,36,0.92)_100%)]" />

      {/* 頂部：返回、標題、進度 */}
      <div className="absolute inset-x-0 top-0 z-10 px-4 pt-[74px] md:px-6">
        <div className="flex gap-1.5" aria-label={`第 ${index + 1} 張，共 ${total} 張`}>
          {story.slides.map((_, i) => (
            <button key={i} onClick={() => go(i)} className="group h-4 flex-1 py-1.5" aria-label={`跳到第 ${i + 1} 張`}>
              <span className="block h-1 overflow-hidden rounded-full bg-white/25 group-hover:bg-white/40">
                <span
                  ref={(el) => {
                    fillRefs.current[i] = el;
                  }}
                  className="block h-full origin-left scale-x-0 rounded-full bg-white"
                />
              </span>
            </button>
          ))}
        </div>
        <div className="mt-2 flex items-center gap-3">
          <button onClick={onExit} className="grid size-9 shrink-0 place-items-center rounded-full bg-[#071d4f]/70 ring-1 ring-white/20 hover:bg-[#0a2766]" aria-label="返回主題列表" title="返回主題列表">
            <ArrowLeft className="size-[18px]" />
          </button>
          <p className="min-w-0 truncate text-[15px] font-bold [text-shadow:0_2px_8px_rgba(0,0,0,0.6)]">{story.title}</p>
          <span className="ml-auto shrink-0 rounded-full bg-[#071d4f]/70 px-2.5 py-1 text-[12px] font-semibold tabular-nums ring-1 ring-white/20">
            {index + 1} / {total}
          </span>
        </div>
      </div>

      {/* 字幕與控制 */}
      {!ended && (
        <div className="absolute inset-x-0 bottom-0 z-10 px-4 pb-4 md:px-8 md:pb-6">
          <div ref={textRef} className={`${PANEL} mx-auto max-w-3xl rounded-[26px] px-5 pt-4 pb-3 md:px-7 md:pt-5`}>
            <p data-t className="text-[12px] font-semibold tracking-[0.14em] text-glow">
              第 {index + 1} 幕
            </p>
            <h2 data-t className="mt-1 text-[22px] leading-tight font-bold md:text-[28px]">
              {slide.caption}
            </h2>
            <p data-t className="mt-2.5 text-[15px] leading-[1.85] text-white/92 md:text-[16.5px]">
              {slide.narration}
            </p>
            <div className="mt-3 flex items-center justify-center gap-1 border-t border-white/10 pt-2.5">
              <button onClick={() => go(index - 1)} disabled={index === 0} className={ctrl} aria-label="上一張" title="上一張（←）">
                <SkipBack className="size-5" />
              </button>
              <button onClick={() => setPlaying((p) => !p)} className="grid size-12 place-items-center rounded-full bg-white text-deep-800 transition hover:bg-glow" aria-label={playing ? "暫停" : "播放"} title={playing ? "暫停（空白鍵）" : "播放（空白鍵）"}>
                {playing ? <Pause className="size-5" fill="currentColor" /> : <Play className="size-5 translate-x-px" fill="currentColor" />}
              </button>
              <button onClick={() => go(index + 1)} className={ctrl} aria-label="下一張" title="下一張（→）">
                <SkipForward className="size-5" />
              </button>
              <button
                onClick={() => setMuted((m) => !m)}
                disabled={!canSpeak()}
                className={`${ctrl} ml-2`}
                aria-label={muted ? "開啟語音朗讀" : "靜音"}
                title={canSpeak() ? (muted ? "開啟語音朗讀" : "靜音") : "此瀏覽器不支援語音朗讀"}
              >
                {muted ? <VolumeX className="size-5" /> : <Volume2 className="size-5" />}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 結束畫面 */}
      {ended && (
        <div className="absolute inset-0 z-20 grid place-items-center bg-[#020c24]/70 p-6 backdrop-blur-sm">
          <div ref={endRef} className="text-center">
            <p className="text-[13px] font-semibold tracking-[0.2em] text-glow">THE END</p>
            <h2 className="mt-2 text-3xl font-bold md:text-4xl">{story.title}</h2>
            <p className="mt-2 text-[15px] text-white/75">故事結束，共 {total} 幕</p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <button onClick={replay} className="flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-[14px] font-semibold text-deep-800 hover:bg-glow">
                <RotateCcw className="size-4" />
                重新播放
              </button>
              <button onClick={onExit} className="flex items-center gap-2 rounded-full border border-white/30 bg-white/10 px-5 py-2.5 text-[14px] font-semibold hover:bg-white/20">
                <LayoutGrid className="size-4" />
                選擇其他主題
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
