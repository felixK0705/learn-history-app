import indexData from "./countryIndex.json";
import { langDir, type Lang, type Tr } from "../lib/i18n";

export interface CountryMeta {
  iso: string;
  iso2: string;
  en: string;
  zh: string;
  continent: "亞洲" | "歐洲" | "非洲" | "北美洲" | "南美洲" | "大洋洲";
  /** 標籤位置 [緯度, 經度] */
  pos: [number, number];
  /** 是否有國界形狀（小島國只有標籤） */
  shape: boolean;
  /** 時間線事件數 */
  events: number;
  /** 依人口排序的標籤優先順序（0 最優先） */
  rank: number;
}

export interface HistoryEvent {
  year: string;
  title: string;
  description: string;
  era: string;
}

export interface RankedItem {
  name: string;
  percent: number;
  description: string;
}

export interface LanguageItem extends RankedItem {
  greeting?: string;
  pronunciation?: string;
}

export interface FoodItem {
  name: string;
  localName?: string;
  description: string;
  history: string;
  wiki?: string;
  image?: string;
  imagePage?: string;
  imageCredit?: string;
}

export interface CountryProfile {
  iso: string;
  capital: string;
  summary: string;
  religion: { ranking: RankedItem[]; background: string };
  language: { official: string; ranking: LanguageItem[]; history: string };
  food: { ranking: FoodItem[] };
}

export const countries = (indexData as CountryMeta[]).slice().sort((a, b) => a.zh.localeCompare(b.zh, "zh-Hant"));
export const countryByIso = new Map(countries.map((c) => [c.iso, c]));

/** ISO alpha-2 → 國旗 emoji */
export function flagOf(iso2: string): string {
  if (!/^[A-Z]{2}$/.test(iso2)) return "🏳️";
  return String.fromCodePoint(...[...iso2].map((ch) => 0x1f1e6 + ch.charCodeAt(0) - 65));
}

const cache = new Map<string, Promise<unknown>>();

function load<T>(url: string): Promise<T> {
  if (!cache.has(url)) {
    cache.set(
      url,
      fetch(url).then((r) => {
        if (!r.ok) throw new Error(`${r.status} ${url}`);
        return r.json();
      }),
    );
  }
  return cache.get(url) as Promise<T>;
}

export const loadHistory = (iso: string, lang: Lang) => load<{ iso: string; events: HistoryEvent[] }>(`/data/history/${langDir(lang)}${iso}.json`);
export const loadProfile = (iso: string, lang: Lang) => load<CountryProfile>(`/data/profile/${langDir(lang)}${iso}.json`);

const jaRegion = new Intl.DisplayNames(["ja"], { type: "region" });
const JA_FIX: Record<string, string> = { COD: "コンゴ民主共和国", COG: "コンゴ共和国", MMR: "ミャンマー", PSE: "パレスチナ" };
/** 國名：中文用資料檔、英文用 Natural Earth 名稱、日文用瀏覽器內建的地區名稱 */
export function countryName(c: CountryMeta, lang: Lang): string {
  if (lang === "zh-TW") return c.zh;
  if (lang === "en") return c.en;
  if (JA_FIX[c.iso]) return JA_FIX[c.iso];
  try {
    const n = jaRegion.of(c.iso2);
    if (n && n !== c.iso2) return n;
  } catch {
    /* 沒有 ISO2 代碼的地區 */
  }
  return c.en;
}

export const CONTINENT: Record<CountryMeta["continent"], Tr> = {
  亞洲: { "zh-TW": "亞洲", en: "Asia", ja: "アジア" },
  歐洲: { "zh-TW": "歐洲", en: "Europe", ja: "ヨーロッパ" },
  非洲: { "zh-TW": "非洲", en: "Africa", ja: "アフリカ" },
  北美洲: { "zh-TW": "北美洲", en: "North America", ja: "北アメリカ" },
  南美洲: { "zh-TW": "南美洲", en: "South America", ja: "南アメリカ" },
  大洋洲: { "zh-TW": "大洋洲", en: "Oceania", ja: "オセアニア" },
};

/** 時間軸分期 */
export const ERA: Record<string, Tr> = {
  上古: { "zh-TW": "上古", en: "Ancient", ja: "古代" },
  中世紀: { "zh-TW": "中世紀", en: "Medieval", ja: "中世" },
  近世: { "zh-TW": "近世", en: "Early Modern", ja: "近世" },
  近代: { "zh-TW": "近代", en: "Modern", ja: "近代" },
  當代: { "zh-TW": "當代", en: "Contemporary", ja: "現代" },
};
