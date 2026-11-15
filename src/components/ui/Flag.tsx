import "flag-icons/css/flag-icons.min.css";

/** 國旗圖示（SVG）：Windows 不支援國旗 emoji，改用圖片確保所有瀏覽器都看得到 */
export default function Flag({ iso2, className = "" }: { iso2?: string; className?: string }) {
  if (!iso2 || !/^[A-Za-z]{2}$/.test(iso2)) return null;
  return (
    <span
      aria-hidden="true"
      className={`fi fi-${iso2.toLowerCase()} inline-block shrink-0 overflow-hidden rounded-[3px] bg-cover shadow-[0_0_0_1px_rgba(255,255,255,0.25)] ${className}`}
      style={{ width: "1.35em", height: "1em", lineHeight: 1 }}
    />
  );
}
