import { useCallback, useSyncExternalStore } from "react";

const KEY = "timelore:visited";
const listeners = new Set<() => void>();

function read(): string[] {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}

let cache = read();

function write(next: string[]) {
  cache = next;
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    /* 私密模式等情況下忽略 */
  }
  listeners.forEach((l) => l());
}

/** 記錄使用者探索過的國家（存在瀏覽器本機） */
export function useVisited() {
  const visited = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => cache,
  );
  const markVisited = useCallback((iso: string) => {
    if (!cache.includes(iso)) write([...cache, iso]);
  }, []);
  return { visited, markVisited };
}
