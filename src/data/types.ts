// 共用資料型別

export interface TimelineEvent {
  /** 顯示用年份，例如 "西元前 221 年"、"1949 年" */
  year: string;
  /** 排序用數值年份（西元前為負數） */
  sortYear: number;
  title: string;
  description: string;
  /** 分類：政治、戰爭、文化、科技、宗教、經濟 */
  category: "政治" | "戰爭" | "文化" | "科技" | "宗教" | "經濟";
}

export interface Dish {
  name: string;
  /** 原文名稱（可選），例如 "Sushi" 或 "寿司" */
  localName?: string;
  emoji: string;
  description: string;
  /** 與歷史的關聯小知識 */
  history: string;
}

export interface Religion {
  name: string;
  /** 約略人口比例 0–100 */
  percent: number;
  description: string;
}

export interface Language {
  name: string;
  /** 官方 / 通用 / 地區 / 少數 */
  status: "官方" | "通用" | "地區" | "少數";
  /** 問候語 */
  greeting: string;
  /** 問候語讀音（羅馬拼音） */
  pronunciation?: string;
  /** 語系 */
  family: string;
  description: string;
}

export interface CountryInfo {
  /** ISO 3166-1 alpha-3，需與 public/data/countries.json 的 iso_a3 相同 */
  iso: string;
  name: string;
  englishName: string;
  flag: string;
  capital: string;
  /** 標籤顯示位置 [緯度, 經度] */
  labelPos: [number, number];
  continent: "亞洲" | "歐洲" | "非洲" | "北美洲" | "南美洲" | "大洋洲";
  /** 一句話介紹 */
  summary: string;
  timeline: TimelineEvent[];
  foods: Dish[];
  religions: Religion[];
  languages: Language[];
}
