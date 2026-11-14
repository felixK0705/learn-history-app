import { type RefObject } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(useGSAP);
gsap.defaults({ ease: "power3.out", duration: 0.6 });
// 低效能裝置掉幀時讓動畫照實際時間前進，避免停在半途
gsap.ticker.lagSmoothing(0);

export const prefersReducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

type RevealOptions = {
  /** 子元素選擇器；設定後會依序錯開出現 */
  stagger?: string;
  y?: number;
  x?: number;
  scale?: number;
  delay?: number;
  duration?: number;
  each?: number;
};

/** 元素（或其子元素）淡入上移，deps 改變時重播 */
export function useReveal<T extends HTMLElement>(
  ref: RefObject<T | null>,
  deps: unknown[] = [],
  { stagger, y = 16, x = 0, scale = 1, delay = 0, duration = 0.6, each = 0.06 }: RevealOptions = {},
) {
  useGSAP(
    () => {
      const el = ref.current;
      if (!el || prefersReducedMotion()) return;
      const targets = stagger ? el.querySelectorAll(stagger) : el;
      gsap.fromTo(
        targets,
        { autoAlpha: 0, y, x, scale },
        {
          autoAlpha: 1,
          y: 0,
          x: 0,
          scale: 1,
          delay,
          duration,
          stagger: stagger ? each : 0,
          clearProps: "opacity,visibility,transform",
        },
      );
    },
    { scope: ref, dependencies: deps, revertOnUpdate: true },
  );
}

export { gsap, useGSAP };
