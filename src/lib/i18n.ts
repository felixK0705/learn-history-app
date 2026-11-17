import { useSyncExternalStore } from "react";

/** 介面語言：繁體中文、英文、日文（與原版相同，選擇存在 localStorage） */
export type Lang = "zh-TW" | "en" | "ja";
export const LANGS: { code: Lang; name: string }[] = [
  { code: "zh-TW", name: "繁體中文" },
  { code: "en", name: "English" },
  { code: "ja", name: "日本語" },
];

const KEY = "appLanguage";
function initial(): Lang {
  try {
    const v = localStorage.getItem(KEY);
    if (v === "zh-TW" || v === "en" || v === "ja") return v;
  } catch {
    /* 無法使用 localStorage 時用預設值 */
  }
  return "zh-TW";
}

let current: Lang = initial();
const listeners = new Set<() => void>();
document.documentElement.lang = current;

export function getLang(): Lang {
  return current;
}

export function setLang(lang: Lang) {
  if (lang === current) return;
  current = lang;
  document.documentElement.lang = lang;
  try {
    localStorage.setItem(KEY, lang);
  } catch {
    /* 忽略 */
  }
  listeners.forEach((l) => l());
}

function subscribe(l: () => void) {
  listeners.add(l);
  return () => listeners.delete(l);
}

export function useLang(): Lang {
  return useSyncExternalStore(subscribe, getLang);
}

/** 依語言挑選字串：tr({ "zh-TW": "地球", en: "Globe", ja: "地球" }) */
export type Tr = Record<Lang, string>;
export function pick(t: Tr, lang: Lang = current): string {
  return t[lang];
}

/** 元件內使用：const t = useT(); t({ "zh-TW": "…", en: "…", ja: "…" }) */
export function useT() {
  const lang = useLang();
  return (t: Tr) => t[lang];
}

/** 載入資料檔的語言子目錄（中文在根目錄） */
export function langDir(lang: Lang): string {
  return lang === "zh-TW" ? "" : `${lang}/`;
}
