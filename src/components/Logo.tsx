/** Timelore 標誌：簡潔的地球經緯線，代表「探索世界的歷史」 */
export default function Logo({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true" fill="none">
      <circle cx="16" cy="16" r="14" fill="white" />
      <circle cx="16" cy="16" r="9.5" stroke="#1a4f72" strokeWidth="1.8" />
      <ellipse cx="16" cy="16" rx="4" ry="9.5" stroke="#1a4f72" strokeWidth="1.8" />
      <path d="M6.8 13h18.4M6.8 19h18.4" stroke="#1a4f72" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}
