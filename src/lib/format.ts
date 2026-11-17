import type { Lang } from "./i18n";

/** 年份：負數為西元前 */
export function formatYear(y: number, lang: Lang = "zh-TW"): string {
  if (y >= 0) return `${y}`;
  return lang === "en" ? `${-y} BC` : lang === "ja" ? `前${-y}` : `前 ${-y}`;
}
