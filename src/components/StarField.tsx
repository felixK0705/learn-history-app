import { useMemo, useRef } from "react";
import { gsap, prefersReducedMotion, useGSAP } from "../lib/motion";

/** 背景漂浮光點（以 GSAP 製作閃爍與緩慢漂移） */
export default function StarField({ count = 70 }: { count?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const stars = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => {
        const r = (n: number) => {
          const x = Math.sin(i * 9301 + n * 49297) * 233280;
          return x - Math.floor(x);
        };
        const big = r(3) >= 0.9;
        return { left: r(1) * 100, top: r(2) * 100, size: big ? 3 + r(4) * 4 : 1 + r(4) * 1.5, big };
      }),
    [count],
  );

  useGSAP(
    () => {
      if (prefersReducedMotion()) return;
      gsap.utils.toArray<HTMLElement>(".star").forEach((el) => {
        gsap.fromTo(
          el,
          { opacity: gsap.utils.random(0.1, 0.4) },
          {
            opacity: gsap.utils.random(0.6, 1),
            duration: gsap.utils.random(1.5, 4),
            repeat: -1,
            yoyo: true,
            ease: "sine.inOut",
            delay: gsap.utils.random(0, 3),
          },
        );
      });
      gsap.utils.toArray<HTMLElement>(".star-big").forEach((el) => {
        gsap.to(el, {
          x: gsap.utils.random(-30, 30),
          y: gsap.utils.random(-30, 30),
          duration: gsap.utils.random(8, 14),
          repeat: -1,
          yoyo: true,
          ease: "sine.inOut",
        });
      });
    },
    { scope: ref },
  );

  return (
    <div ref={ref} className="pointer-events-none absolute inset-0" aria-hidden="true">
      {stars.map((s, i) => (
        <span
          key={i}
          className={`absolute rounded-full bg-white ${s.big ? "star-big opacity-30 blur-[1px]" : "star opacity-50"}`}
          style={{ left: `${s.left}%`, top: `${s.top}%`, width: s.size, height: s.size }}
        />
      ))}
    </div>
  );
}
