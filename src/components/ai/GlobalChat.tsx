import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { AlertTriangle, ArrowUp, Bot, Eraser, MapPin, Quote, Sparkles, X } from "lucide-react";
import { gsap, prefersReducedMotion, useGSAP } from "../../lib/motion";
import { clearChat, closeChat, sendChat, setChatContext, toggleChat, useChat } from "../../lib/ai";
import { countryByIso, countryName } from "../../data/world";
import { useBuildings, useFigures } from "../../data/localized";
import { useLang, useT } from "../../lib/i18n";
import Markdown from "./Markdown";

const PANEL =
  "border border-white/15 bg-[#113650]/97 shadow-[0_24px_60px_-20px_rgba(4,18,30,0.75),inset_0_1px_0_rgba(255,255,255,0.18)]";

/** 依目前網址推出「使用者在看什麼」，作為對話情境（情境給模型看用中文，標籤依介面語言） */
function useAiContext(): { label: string; context: string; country?: string } {
  const { pathname, search } = useLocation();
  const lang = useLang();
  const t = useT();
  const { figures } = useFigures();
  const buildings = useBuildings();
  return useMemo(() => {
    const q = new URLSearchParams(search);
    if (pathname.startsWith("/figures")) {
      const f = figures.find((x) => x.id === q.get("focus"));
      return f
        ? { label: f.name, context: `人物關係頁，正在查看歷史人物「${f.name}」（${f.role}）` }
        : { label: t({ "zh-TW": "人物關係", en: "Figures", ja: "人物相関" }), context: "人物關係頁" };
    }
    if (pathname.startsWith("/buildings")) {
      const id = pathname.split("/")[2];
      const b = buildings.find((x) => x.id === id);
      return b
        ? { label: b.name, context: `建築 3D 頁，正在查看「${b.name}」（${b.location}，${b.era}）` }
        : { label: t({ "zh-TW": "建築 3D", en: "3D Buildings", ja: "3D 建築" }), context: "建築 3D 頁" };
    }
    if (pathname.startsWith("/stories")) return { label: t({ "zh-TW": "歷史故事", en: "Stories", ja: "歴史物語" }), context: "歷史故事頁" };
    const c = countryByIso.get(q.get("country") ?? "");
    return c
      ? { label: countryName(c, lang), context: `地球頁，正在查看「${c.zh}」（${c.en}）的歷史與文化`, country: countryName(c, lang) }
      : { label: t({ "zh-TW": "地球", en: "Globe", ja: "地球" }), context: "地球首頁（世界地圖）" };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, search, lang, figures, buildings]);
}

/** 桌機上避開各頁右側資訊面板，讓浮動按鈕不遮住面板內容 */
function useFabShift() {
  const { pathname, search } = useLocation();
  const q = new URLSearchParams(search);
  if (pathname === "/" && q.get("country")) return "lg:right-[472px]";
  if (pathname.startsWith("/figures") && q.get("focus")) return "md:right-[332px]";
  if (pathname.startsWith("/buildings")) return "lg:right-[412px]";
  return "md:right-5";
}

const SUGGESTIONS = {
  "zh-TW": ["文藝復興為什麼從義大利開始？", "絲路對東西方交流有什麼影響？", "第一次世界大戰的導火線是什麼？"],
  en: ["Why did the Renaissance begin in Italy?", "How did the Silk Road shape East–West exchange?", "What sparked the First World War?"],
  ja: ["ルネサンスはなぜイタリアで始まったのか？", "シルクロードは東西交流にどんな影響を与えたか？", "第一次世界大戦の引き金は何だったのか？"],
};

export default function GlobalChat() {
  const { open, pending, messages } = useChat();
  const { label, context, country } = useAiContext();
  const lang = useLang();
  const t = useT();
  const fabShift = useFabShift();
  const { pathname, search } = useLocation();
  const [input, setInput] = useState("");
  const panelRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const dotsRef = useRef<HTMLDivElement>(null);
  const fabRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => setChatContext(context), [context]);

  // 開啟動畫
  useGSAP(
    () => {
      if (!open || !panelRef.current) return;
      inputRef.current?.focus({ preventScroll: true });
      if (prefersReducedMotion()) return;
      gsap.fromTo(panelRef.current, { autoAlpha: 0, y: 24, scale: 0.96 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.45, ease: "expo.out" });
    },
    { dependencies: [open] },
  );

  // 新訊息淡入並捲到底
  useGSAP(
    () => {
      const list = listRef.current;
      if (!list) return;
      list.scrollTo({ top: list.scrollHeight, behavior: prefersReducedMotion() ? "auto" : "smooth" });
      const last = list.querySelector("[data-msg]:last-of-type");
      if (last && !prefersReducedMotion()) gsap.fromTo(last, { autoAlpha: 0, y: 10 }, { autoAlpha: 1, y: 0, duration: 0.4, clearProps: "all" });
    },
    { dependencies: [messages.length, open] },
  );

  // 載入中三點跳動
  useGSAP(
    () => {
      if (!pending || !dotsRef.current) return;
      gsap.fromTo(dotsRef.current.children, { y: 0, opacity: 0.35 }, { y: -4, opacity: 1, duration: 0.4, stagger: 0.14, repeat: -1, yoyo: true, ease: "sine.inOut" });
    },
    { dependencies: [pending] },
  );

  // 浮動按鈕呼吸光暈
  useGSAP(() => {
    if (prefersReducedMotion() || !fabRef.current) return;
    gsap.fromTo(fabRef.current, { autoAlpha: 0, scale: 0.6 }, { autoAlpha: 1, scale: 1, delay: 0.8, duration: 0.6, ease: "back.out(1.8)" });
  });

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && closeChat();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const submit = (text = input) => {
    if (!text.trim() || pending) return;
    sendChat(text);
    setInput("");
  };

  return (
    <>
      <button
        ref={fabRef}
        onClick={toggleChat}
        className={`fixed right-4 bottom-[4.5rem] z-50 grid size-13 place-items-center rounded-full border border-white/30 bg-[linear-gradient(145deg,#4fa3cf,#1d5a80)] text-white shadow-[0_14px_30px_-10px_rgba(5,25,40,0.8),inset_0_1px_0_rgba(255,255,255,0.5)] transition hover:scale-105 hover:brightness-110 md:bottom-5 ${fabShift} ${open ? "max-sm:hidden" : ""} ${pathname === "/" && search.includes("country=") ? "max-lg:hidden" : ""}`}
        aria-label={open ? t({ "zh-TW": "關閉 AI 助理", en: "Close AI assistant", ja: "AI アシスタントを閉じる" }) : t({ "zh-TW": "開啟 AI 歷史助理", en: "Open AI history assistant", ja: "AI 歴史アシスタントを開く" })}
        title={t({ "zh-TW": "AI 歷史助理", en: "AI history assistant", ja: "AI 歴史アシスタント" })}
      >
        {open ? <X className="size-6" /> : <Sparkles className="size-6" strokeWidth={2} />}
      </button>

      {open && (
        <div
          ref={panelRef}
          role="dialog"
          aria-label={t({ "zh-TW": "AI 歷史助理", en: "AI history assistant", ja: "AI 歴史アシスタント" })}
          className={`${PANEL} fixed z-50 flex flex-col overflow-hidden rounded-[26px] text-white max-sm:inset-2 max-sm:bottom-[4.25rem] sm:right-5 sm:bottom-[5.5rem] sm:h-[min(620px,calc(100dvh-8rem))] sm:w-[400px] md:bottom-20`}
        >
          <header className="flex shrink-0 items-center gap-3 border-b border-white/10 px-4 py-3">
            <span className="grid size-9 place-items-center rounded-full bg-white/12 ring-1 ring-white/20">
              <Bot className="size-5" />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[15px] leading-tight font-bold">{t({ "zh-TW": "AI 歷史助理", en: "AI history assistant", ja: "AI 歴史アシスタント" })}</p>
              <p className="mt-0.5 flex items-center gap-1 truncate text-[11.5px] text-white/65">
                <MapPin className="size-3 shrink-0" />
                {t({ "zh-TW": "目前位置：", en: "Viewing: ", ja: "現在地：" })}
                {label}
              </p>
            </div>
            <button
              onClick={clearChat}
              disabled={!messages.length}
              className="grid size-8 place-items-center rounded-full text-white/75 transition hover:bg-white/10 hover:text-white disabled:opacity-35"
              aria-label={t({ "zh-TW": "清除對話", en: "Clear chat", ja: "会話を消去" })}
              title={t({ "zh-TW": "清除對話", en: "Clear chat", ja: "会話を消去" })}
            >
              <Eraser className="size-4" />
            </button>
            <button onClick={closeChat} className="grid size-8 place-items-center rounded-full text-white/75 transition hover:bg-white/10 hover:text-white" aria-label={t({ "zh-TW": "關閉對話視窗", en: "Close chat", ja: "チャットを閉じる" })} title={t({ "zh-TW": "關閉", en: "Close", ja: "閉じる" })}>
              <X className="size-[18px]" />
            </button>
          </header>

          <div ref={listRef} className="scroll-thin min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {!messages.length && (
              <div className="py-4 text-center">
                <Sparkles className="mx-auto size-8 text-glow" />
                <p className="mt-3 text-[15px] font-semibold">{t({ "zh-TW": "問我任何歷史問題", en: "Ask me anything about history", ja: "歴史について何でも聞いてください" })}</p>
                <div className="mt-4 flex flex-col gap-2">
                  {(country
                    ? [t({ "zh-TW": `${country}歷史上最重要的轉折是什麼？`, en: `What were the key turning points in the history of ${country}?`, ja: `${country}の歴史で最も重要な転換点は何か？` }), ...SUGGESTIONS[lang].slice(0, 2)]
                    : SUGGESTIONS[lang]
                  ).map((s) => (
                    <button
                      key={s}
                      onClick={() => submit(s)}
                      className="rounded-2xl border border-white/15 bg-white/6 px-3.5 py-2 text-left text-[13px] text-white/90 transition hover:bg-white/12"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m) =>
              m.role === "user" ? (
                <div key={m.id} data-msg className="flex justify-end">
                  {m.kind === "quote" ? (
                    <div className="max-w-[88%] rounded-2xl rounded-br-md bg-white/92 px-3.5 py-2.5 text-[13.5px] leading-relaxed text-deep-950">
                      <p className="mb-1 flex items-center gap-1 text-[11.5px] font-semibold text-deep-700">
                        <Quote className="size-3" />
                        {t({ "zh-TW": "請解釋這段文字", en: "Explain this passage", ja: "この文章を解説して" })}
                      </p>
                      <p className="line-clamp-5 border-l-2 border-deep-600/40 pl-2 text-deep-900">{m.content}</p>
                    </div>
                  ) : (
                    <p className="max-w-[85%] rounded-2xl rounded-br-md bg-white/92 px-3.5 py-2.5 text-[14px] leading-relaxed whitespace-pre-wrap text-deep-950">{m.content}</p>
                  )}
                </div>
              ) : m.kind === "error" ? (
                <div key={m.id} data-msg className="flex gap-2 rounded-2xl border border-amber-300/35 bg-amber-400/12 px-3.5 py-3 text-[13.5px] leading-relaxed text-amber-50">
                  <AlertTriangle className="mt-0.5 size-4 shrink-0 text-amber-300" />
                  <span>{m.content}</span>
                </div>
              ) : (
                <div key={m.id} data-msg className="max-w-[94%] rounded-2xl rounded-bl-md border border-white/12 bg-white/7 px-3.5 py-2.5 text-[14px] leading-[1.7] text-white/92">
                  <Markdown text={m.content} />
                </div>
              ),
            )}

            {pending && (
              <div className="flex items-center gap-2 text-[13px] text-white/70" aria-live="polite">
                <div ref={dotsRef} className="flex gap-1 rounded-2xl rounded-bl-md border border-white/12 bg-white/7 px-3.5 py-3">
                  <span className="size-1.5 rounded-full bg-white" />
                  <span className="size-1.5 rounded-full bg-white" />
                  <span className="size-1.5 rounded-full bg-white" />
                </div>
                {t({ "zh-TW": "AI 思考中…", en: "Thinking…", ja: "AI が考え中…" })}
              </div>
            )}
          </div>

          <form
            className="shrink-0 border-t border-white/10 p-3"
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
          >
            <div className="flex items-end gap-2 rounded-[20px] border border-white/15 bg-white/8 py-1.5 pr-1.5 pl-3.5 focus-within:border-white/35">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                    e.preventDefault();
                    submit();
                  }
                }}
                rows={1}
                maxLength={2000}
                placeholder={messages.length ? t({ "zh-TW": "繼續追問…", en: "Ask a follow-up…", ja: "続けて質問…" }) : t({ "zh-TW": "輸入你的歷史問題…", en: "Type a history question…", ja: "歴史の質問を入力…" })}
                className="max-h-28 min-h-[36px] flex-1 resize-none bg-transparent py-1.5 text-[14px] leading-relaxed text-white outline-none placeholder:text-white/45"
                aria-label={t({ "zh-TW": "輸入問題", en: "Your question", ja: "質問を入力" })}
              />
              <button
                type="submit"
                disabled={!input.trim() || pending}
                className="grid size-9 shrink-0 place-items-center rounded-full bg-white text-deep-800 transition hover:bg-glow disabled:bg-white/20 disabled:text-white/50"
                aria-label={t({ "zh-TW": "送出", en: "Send", ja: "送信" })}
                title={t({ "zh-TW": "送出（Enter）", en: "Send (Enter)", ja: "送信（Enter）" })}
              >
                <ArrowUp className="size-[18px]" strokeWidth={2.6} />
              </button>
            </div>
            <p className="mt-1.5 text-center text-[10.5px] text-white/45">{t({ "zh-TW": "AI 回答可能有誤，重要史實請再查證", en: "AI answers can be wrong — double-check important facts", ja: "AI の回答には誤りが含まれることがあります。重要な史実は確認してください" })}</p>
          </form>
        </div>
      )}
    </>
  );
}
