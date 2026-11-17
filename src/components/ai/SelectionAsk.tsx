import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Sparkles } from "lucide-react";
import { gsap, prefersReducedMotion, useGSAP } from "../../lib/motion";
import { askExplain } from "../../lib/ai";
import { useT } from "../../lib/i18n";

/**
 * 選取文字問 AI：放在任何容器內（作為子元素），
 * 使用者在該容器裡反白文字時，於選取處上方浮出「問 AI」按鈕。
 * 本元件只渲染一個隱藏的定位點，以其父元素作為偵測範圍，不影響容器版面。
 */
export default function SelectionAsk({ country }: { country?: string }) {
  const t = useT();
  const markerRef = useRef<HTMLSpanElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const [sel, setSel] = useState<{ text: string; x: number; y: number; below: boolean } | null>(null);

  useEffect(() => {
    const scope = markerRef.current?.parentElement;
    if (!scope) return;
    let raf = 0;

    const read = () => {
      const s = window.getSelection();
      if (!s || s.isCollapsed || !s.rangeCount) return setSel(null);
      const range = s.getRangeAt(0);
      if (!scope.contains(range.commonAncestorContainer)) return setSel(null);
      const text = s.toString().replace(/\s+/g, " ").trim();
      if (text.length < 2) return setSel(null);
      const rects = Array.from(range.getClientRects()).filter((r) => r.width > 0 || r.height > 0);
      const first = rects[0] ?? range.getBoundingClientRect();
      const box = range.getBoundingClientRect();
      const below = first.top < 70; // 太靠近頂部時改放在下方
      setSel({
        text,
        x: Math.min(window.innerWidth - 60, Math.max(60, below ? box.left + box.width / 2 : first.left + first.width / 2)),
        y: below ? box.bottom + 10 : first.top - 10,
        below,
      });
    };
    const schedule = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(read);
    };
    // selectionchange 在拖曳時會一直觸發；放開滑鼠／手指後再讀一次確保位置正確
    document.addEventListener("selectionchange", schedule);
    document.addEventListener("pointerup", schedule);
    window.addEventListener("resize", schedule);
    window.addEventListener("scroll", schedule, true);
    return () => {
      cancelAnimationFrame(raf);
      document.removeEventListener("selectionchange", schedule);
      document.removeEventListener("pointerup", schedule);
      window.removeEventListener("resize", schedule);
      window.removeEventListener("scroll", schedule, true);
    };
  }, []);

  const visible = !!sel;
  useGSAP(
    () => {
      if (!visible || !btnRef.current || prefersReducedMotion()) return;
      gsap.fromTo(btnRef.current, { autoAlpha: 0, scale: 0.8 }, { autoAlpha: 1, scale: 1, duration: 0.25, ease: "back.out(2)" });
    },
    { dependencies: [visible] },
  );

  return (
    <>
      <span ref={markerRef} hidden />
      {sel &&
        createPortal(
          <div
            className="fixed z-[60]"
            style={{ left: sel.x, top: sel.y, transform: `translate(-50%, ${sel.below ? "0" : "-100%"})` }}
          >
          <button
            ref={btnRef}
            type="button"
            // 避免點擊時取消選取
            onPointerDown={(e) => e.preventDefault()}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => {
              askExplain(sel.text, country);
              window.getSelection()?.removeAllRanges();
              setSel(null);
            }}
            className="flex items-center gap-1.5 rounded-full border border-white/40 bg-[linear-gradient(145deg,#4fa3cf,#1d5a80)] px-3.5 py-1.5 text-[13px] font-semibold whitespace-nowrap text-white shadow-[0_10px_24px_-8px_rgba(5,22,36,0.85),inset_0_1px_0_rgba(255,255,255,0.45)] hover:brightness-110"
            aria-label={t({ "zh-TW": "請 AI 解釋選取的文字", en: "Ask AI to explain the selection", ja: "選択した文章を AI に解説してもらう" })}
          >
            <Sparkles className="size-3.5" />
            {t({ "zh-TW": "問 AI", en: "Ask AI", ja: "AI に聞く" })}
          </button>
          </div>,
          document.body,
        )}
    </>
  );
}
