import { useRef, useState } from "react";
import { Library, Sparkles } from "lucide-react";
import HeaderSlot from "../HeaderSlot";
import AiRelationshipGraph from "./AiRelationshipGraph";
import { gsap, prefersReducedMotion, useGSAP } from "../../lib/motion";

/**
 * 人物關係頁的「館藏人物 / AI 查詢任意人物」切換。
 * 切換鈕放在頂部列；AI 模式時以全頁覆蓋層顯示 AiRelationshipGraph，
 * 不影響原本館藏人物圖的任何邏輯（切回時原圖狀態保留）。
 */
export default function AiFiguresMode() {
  const [ai, setAi] = useState(false);
  const layerRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      if (!ai || prefersReducedMotion() || !layerRef.current) return;
      gsap.fromTo(layerRef.current, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.45, ease: "power2.out" });
    },
    { dependencies: [ai] },
  );

  const btn = (on: boolean) =>
    `flex h-8 items-center gap-1.5 whitespace-nowrap rounded-full px-3 text-[12.5px] max-sm:px-2.5 max-sm:text-[12px] font-semibold normal-case tracking-normal transition ${
      on ? "bg-white text-deep-800 shadow-[0_4px_12px_-4px_rgba(5,25,40,0.6)]" : "text-white/75 hover:text-white"
    }`;

  return (
    <>
      <HeaderSlot slot="header-meta">
        <div className="glass-soft flex rounded-full p-0.5" role="tablist" aria-label="人物關係模式">
          <button role="tab" aria-selected={!ai} onClick={() => setAi(false)} className={btn(!ai)}>
            <Library className="size-3.5 max-sm:hidden" />
            <span className="sm:hidden">館藏</span>
            <span className="max-sm:hidden">館藏人物</span>
          </button>
          <button role="tab" aria-selected={ai} onClick={() => setAi(true)} className={btn(ai)}>
            <Sparkles className="size-3.5 max-sm:hidden" />
            <span className="sm:hidden">AI 查詢</span>
            <span className="max-sm:hidden">AI 查詢任意人物</span>
          </button>
        </div>
      </HeaderSlot>
      {ai && (
        <div ref={layerRef} className="stage absolute inset-0 z-40">
          <AiRelationshipGraph />
        </div>
      )}
    </>
  );
}
