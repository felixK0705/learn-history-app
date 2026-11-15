// 維基百科配圖：前端直接呼叫 MediaWiki API（origin=* 允許跨來源）
const imageCache = new Map<string, Promise<string | null>>();

/** 以英文維基百科搜尋關鍵字，取第一個有大圖（非 SVG）的條目縮圖 */
export function findImage(query: string): Promise<string | null> {
  const q = query.trim();
  if (!q) return Promise.resolve(null);
  let p = imageCache.get(q);
  if (!p) {
    const url =
      "https://en.wikipedia.org/w/api.php?action=query&format=json&origin=*&generator=search&gsrnamespace=0&gsrlimit=6" +
      `&gsrsearch=${encodeURIComponent(q)}&prop=pageimages&piprop=thumbnail&pithumbsize=1600`;
    p = fetch(url, { signal: AbortSignal.timeout(8000) })
      .then((r) => (r.ok ? r.json() : null))
      .then((d: { query?: { pages?: Record<string, { index?: number; thumbnail?: { source: string; width: number; height: number } }> } } | null) => {
        const pages = Object.values(d?.query?.pages ?? {}).sort((a, b) => (a.index ?? 99) - (b.index ?? 99));
        const hit = pages.find((pg) => pg.thumbnail && !/\.svg/i.test(pg.thumbnail.source) && pg.thumbnail.width >= 500);
        return hit?.thumbnail?.source ?? null;
      })
      .catch(() => null);
    imageCache.set(q, p);
  }
  return p;
}


const portraitCache = new Map<string, Promise<string | null>>();

/** 以中文維基百科搜尋人名，取條目代表圖（人物肖像）縮圖 */
export function findPortrait(name: string): Promise<string | null> {
  const q = name.trim();
  if (!q) return Promise.resolve(null);
  let p = portraitCache.get(q);
  if (!p) {
    const url =
      "https://zh.wikipedia.org/w/api.php?action=query&format=json&origin=*&generator=search&gsrnamespace=0&gsrlimit=1" +
      `&gsrsearch=${encodeURIComponent(q)}&prop=pageimages&piprop=thumbnail&pithumbsize=240`;
    p = fetch(url, { signal: AbortSignal.timeout(8000) })
      .then((r) => (r.ok ? r.json() : null))
      .then((d: { query?: { pages?: Record<string, { thumbnail?: { source: string } }> } } | null) => {
        const pg = Object.values(d?.query?.pages ?? {})[0];
        const src = pg?.thumbnail?.source;
        return src && !/\.svg/i.test(src) ? src : null;
      })
      .catch(() => null);
    portraitCache.set(q, p);
  }
  return p;
}

/** 一次查詢多位人物的中文維基百科代表圖（以條目名稱精確比對，比搜尋準確，也只需一次請求） */
export async function findPortraits(names: string[]): Promise<Record<string, string>> {
  const uniq = [...new Set(names.map((n) => n.trim()).filter(Boolean))].slice(0, 50);
  if (!uniq.length) return {};
  const url =
    "https://zh.wikipedia.org/w/api.php?action=query&format=json&origin=*&redirects=1&prop=pageimages&piprop=thumbnail&pithumbsize=240" +
    `&titles=${encodeURIComponent(uniq.join("|"))}`;
  try {
    const r = await fetch(url, { signal: AbortSignal.timeout(9000) });
    if (!r.ok) return {};
    const d: {
      query?: {
        normalized?: { from: string; to: string }[];
        redirects?: { from: string; to: string }[];
        pages?: Record<string, { title: string; thumbnail?: { source: string } }>;
      };
    } = await r.json();
    const byTitle = new Map(Object.values(d.query?.pages ?? {}).map((p) => [p.title, p.thumbnail?.source]));
    const norm = new Map((d.query?.normalized ?? []).map((x) => [x.from, x.to]));
    const redir = new Map((d.query?.redirects ?? []).map((x) => [x.from, x.to]));
    const out: Record<string, string> = {};
    for (const n of uniq) {
      let t = norm.get(n) ?? n;
      t = redir.get(t) ?? t;
      const src = byTitle.get(t);
      if (src && !/\.svg/i.test(src)) out[n] = src;
    }
    return out;
  } catch {
    return {};
  }
}
