import { useSyncExternalStore } from "react";

/** 後端沒有設定 GEMINI_API_KEY 時顯示的訊息 */
export const AI_DISABLED_MESSAGE = "AI 功能尚未啟用（網站管理者需在 Vercel 設定 GEMINI_API_KEY）";

export class AiError extends Error {
  status: number;
  /** true：AI 尚未啟用（沒有金鑰或找不到後端） */
  disabled: boolean;
  constructor(message: string, status = 0, disabled = false) {
    super(message);
    this.status = status;
    this.disabled = disabled;
  }
}

/** 呼叫 /api/* 端點；所有錯誤都轉成中文的 AiError */
export async function postAi<T>(path: "chat" | "explain" | "relationships" | "story", body: unknown, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") throw err;
    throw new AiError("無法連線到 AI 服務，請檢查網路後再試。");
  }

  const type = res.headers.get("content-type") ?? "";
  const data = type.includes("application/json") ? ((await res.json().catch(() => null)) as (T & { error?: string }) | null) : null;

  if (res.status === 503) throw new AiError(AI_DISABLED_MESSAGE, 503, true);
  // 找不到端點（例如本機 vite preview 沒有 /api）或回傳的不是 JSON
  if (!data) {
    if (res.status === 404 || res.status === 405 || res.ok) throw new AiError(`${AI_DISABLED_MESSAGE}。目前環境找不到 AI 服務。`, res.status, true);
    throw new AiError(`AI 服務暫時無法使用（${res.status}），請稍後再試。`, res.status);
  }
  if (!res.ok) throw new AiError(data.error || `AI 服務發生錯誤（${res.status}）`, res.status);
  return data;
}

// ───────────────────────── 全域對話狀態 ─────────────────────────

export type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  /** error：錯誤提示，不送回模型；quote：選取文字解釋請求 */
  kind?: "error" | "quote";
  disabled?: boolean;
};

type ChatState = {
  open: boolean;
  pending: boolean;
  messages: ChatMessage[];
  /** 目前所在頁面／國家，送給模型當作情境 */
  context: string;
  /** 最後一次選取解釋的國家，供追問時使用 */
  focusCountry?: string;
};

let state: ChatState = { open: false, pending: false, messages: [], context: "" };
let seq = 0;
let controller: AbortController | null = null;
const listeners = new Set<() => void>();

function set(patch: Partial<ChatState>) {
  state = { ...state, ...patch };
  listeners.forEach((l) => l());
}
const push = (m: Omit<ChatMessage, "id">) => set({ messages: [...state.messages, { ...m, id: ++seq }] });

export function useChat() {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => state,
  );
}

export const openChat = () => set({ open: true });
export const closeChat = () => set({ open: false });
export const toggleChat = () => set({ open: !state.open });
export const setChatContext = (context: string) => {
  if (context !== state.context) set({ context });
};

export function clearChat() {
  controller?.abort();
  controller = null;
  set({ messages: [], pending: false, focusCountry: undefined });
}

async function run(call: (signal: AbortSignal) => Promise<{ answer: string }>) {
  controller?.abort();
  const ctl = new AbortController();
  controller = ctl;
  set({ pending: true });
  try {
    const { answer } = await call(ctl.signal);
    if (ctl.signal.aborted) return;
    push({ role: "assistant", content: answer });
  } catch (err) {
    if (ctl.signal.aborted) return;
    const e = err instanceof AiError ? err : new AiError("發生未知錯誤，請稍後再試。");
    push({ role: "assistant", content: e.message, kind: "error", disabled: e.disabled });
  } finally {
    if (controller === ctl) {
      controller = null;
      set({ pending: false });
    }
  }
}

/** 一般提問：帶入完整對話紀錄與目前情境 */
export function sendChat(text: string) {
  const content = text.trim();
  if (!content || state.pending) return;
  push({ role: "user", content });
  const messages = state.messages
    .filter((m) => m.kind !== "error")
    .map((m) => ({ role: m.role, content: m.kind === "quote" ? `請解釋這段文字：「${m.content}」` : m.content }));
  const context = [state.context, state.focusCountry && `先前討論的國家：${state.focusCountry}`].filter(Boolean).join("；");
  return run((signal) => postAi<{ answer: string }>("chat", { messages, context: context || undefined }, signal));
}

/** 選取文字解釋：開啟對話視窗並送出 explain 請求，之後可在同一對話追問 */
export function askExplain(text: string, country?: string) {
  const quote = text.trim().slice(0, 1500);
  if (!quote) return;
  set({ open: true, focusCountry: country ?? state.focusCountry });
  push({ role: "user", content: quote, kind: "quote" });
  return run((signal) => postAi<{ answer: string }>("explain", { text: quote, country }, signal));
}
