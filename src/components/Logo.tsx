import { Orbit } from "lucide-react";

/** 網站標誌：Lucide Orbit 圖示 */
export default function Logo({ className = "" }: { className?: string }) {
  return (
    <span
      className={`grid place-items-center rounded-full bg-gradient-to-br from-sky-200 to-glow text-deep-900 shadow-[0_0_18px_rgba(92,200,255,0.55)] ${className}`}
      aria-hidden="true"
    >
      <Orbit className="size-[60%]" strokeWidth={2.2} />
    </span>
  );
}
