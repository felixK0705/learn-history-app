import { useMemo } from "react";

/** 背景漂浮光點（參考設計中的星點與光斑） */
export default function StarField({ count = 70 }: { count?: number }) {
  const stars = useMemo(
    () =>
      Array.from({ length: count }, (_, i) => {
        // 以固定種子產生，避免每次渲染跳動
        const r = (n: number) => {
          const x = Math.sin(i * 9301 + n * 49297) * 233280;
          return x - Math.floor(x);
        };
        return {
          left: r(1) * 100,
          top: r(2) * 100,
          size: r(3) < 0.9 ? 1 + r(4) * 1.5 : 3 + r(4) * 4,
          delay: r(5) * 4,
          duration: 3 + r(6) * 4,
        };
      }),
    [count],
  );
  return (
    <div className="pointer-events-none absolute inset-0" aria-hidden="true">
      {stars.map((s, i) => (
        <span
          key={i}
          className="absolute animate-twinkle rounded-full bg-white"
          style={{
            left: `${s.left}%`,
            top: `${s.top}%`,
            width: s.size,
            height: s.size,
            animationDelay: `${s.delay}s`,
            animationDuration: `${s.duration}s`,
            opacity: s.size > 3 ? 0.35 : undefined,
            filter: s.size > 3 ? "blur(1px)" : undefined,
          }}
        />
      ))}
    </div>
  );
}
