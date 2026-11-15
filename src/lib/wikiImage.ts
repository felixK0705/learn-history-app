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

