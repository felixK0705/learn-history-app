export default function Logo({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="logo-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#bdf0ff" />
          <stop offset="1" stopColor="#5cc8ff" />
        </linearGradient>
      </defs>
      <circle cx="20" cy="20" r="15" fill="none" stroke="url(#logo-g)" strokeWidth="1.5" opacity=".55" />
      <path d="M8 26c5-11 14-17 26-17-9 3-15 9-18 21" fill="none" stroke="url(#logo-g)" strokeWidth="2.6" strokeLinecap="round" />
      <path d="M12 31c3-7 8-12 15-14" fill="none" stroke="#e8f3ff" strokeWidth="1.6" strokeLinecap="round" opacity=".8" />
    </svg>
  );
}
