import { useEffect, useState } from "react";
import { useLang, type Lang } from "../lib/i18n";
import { buildings as zhBuildings, type Building } from "./buildings";
import { buildingDetails as zhDetails, type BuildingDetail } from "./buildingDetails";
import { figures as zhFigures, groups as zhGroups, relations as zhRelations, type Figure, type Relation } from "./figures";

/** 建築與人物的英文／日文翻譯（scripts 依中文原檔產生，結構與中文相同），切換語言時才載入 */
type BuildingTr = Pick<Building, "name" | "location" | "era" | "style" | "description" | "facts"> & { detail: BuildingDetail };
type FigureTr = { figures: Record<string, Pick<Figure, "name" | "role" | "bio">>; groups: Record<string, string>; relations: string[] };

const loaders = {
  buildings: { en: () => import("./i18n/buildings.en.json"), ja: () => import("./i18n/buildings.ja.json") },
  figures: { en: () => import("./i18n/figures.en.json"), ja: () => import("./i18n/figures.ja.json") },
};
const cache = new Map<string, unknown>();

function useTr<T>(kind: keyof typeof loaders, lang: Lang): T | null {
  const key = `${kind}.${lang}`;
  const [, force] = useState(0);
  useEffect(() => {
    if (lang === "zh-TW" || cache.has(key)) return;
    let alive = true;
    loaders[kind][lang]().then((m) => {
      cache.set(key, m.default);
      if (alive) force((n) => n + 1);
    });
    return () => {
      alive = false;
    };
  }, [kind, lang, key]);
  return lang === "zh-TW" ? null : ((cache.get(key) as T | undefined) ?? null);
}

export interface LocalBuilding extends Building {
  detail?: BuildingDetail;
}

export function useBuildings(): LocalBuilding[] {
  const tr = useTr<Record<string, BuildingTr>>("buildings", useLang());
  if (!tr) return zhBuildings.map((b) => ({ ...b, detail: zhDetails[b.id] }));
  return zhBuildings.map((b) => {
    const t = tr[b.id];
    return t ? { ...b, ...t } : { ...b, detail: zhDetails[b.id] };
  });
}

export function useFigures(): { figures: Figure[]; groups: typeof zhGroups; relations: Relation[] } {
  const tr = useTr<FigureTr>("figures", useLang());
  if (!tr) return { figures: zhFigures, groups: zhGroups, relations: zhRelations };
  return {
    figures: zhFigures.map((f) => ({ ...f, ...tr.figures[f.id] })),
    groups: zhGroups.map((g) => ({ ...g, name: tr.groups[g.id] ?? g.name })),
    relations: zhRelations.map((r, i) => ({ ...r, label: tr.relations[i] ?? r.label })),
  };
}
