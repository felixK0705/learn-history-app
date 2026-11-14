import { Orbit } from "lucide-react";

/** 網站標誌：Lucide Orbit 圖示 */
export default function Logo({ className = "" }: { className?: string }) {
  return <Orbit className={`text-white ${className}`} strokeWidth={2.2} aria-hidden="true" />;
}
