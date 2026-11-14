import indexData from "./countryIndex.json";

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

export const loadHistory = (iso: string) => load<{ iso: string; events: HistoryEvent[] }>(`/data/history/${iso}.json`);
export const loadProfile = (iso: string) => load<CountryProfile>(`/data/profile/${iso}.json`);
