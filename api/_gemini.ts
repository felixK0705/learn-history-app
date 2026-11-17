/**
 * Vercel Serverless Functions 共用工具：呼叫 Gemini REST API。
 * 檔名以底線開頭，Vercel 不會把它部署成獨立端點。
 * 金鑰只從環境變數 GEMINI_API_KEY 讀取，絕不寫死、也不傳給前端。
 */
import type { IncomingMessage, ServerResponse } from "node:http";

export type ApiRequest = IncomingMessage & { body?: unknown; method?: string };
export type ApiResponse = ServerResponse & {
  status: (code: number) => ApiResponse;
  json: (body: unknown) => void;
};

export const DISABLED_MESSAGE = "AI 功能尚未啟用（網站管理者需在 Vercel 設定 GEMINI_API_KEY）";

const MODEL = process.env.GEMINI_MODEL || "gemini-2.5-flash";

export const SYSTEM_PROMPT =
  "你是世界歷史學習助理，服務對象是正在學習世界歷史的使用者。" +
  "一律使用繁體中文（台灣用語）回答，不可使用簡體字。" +
  "回答要條理清楚：先給重點結論，再分點說明背景、經過與影響；適度使用 Markdown 標題、條列與粗體，但不要過長。" +
  "年代請標示西元年（西元前用「前」）。不確定的史實要說明有爭議或資料不足，不要捏造。";

export class HttpError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export type GeminiContent = { role: "user" | "model"; parts: { text: string }[] };

type GenerateOptions = {
  system?: string;
  /** 網站介面語言（zh-TW／en／ja），決定回答語言 */
  lang?: unknown;
  contents: GeminiContent[];
  json?: boolean;
  temperature?: number;
  maxOutputTokens?: number;
};

const LANG_RULE: Record<string, string> = {
  en: "OUTPUT LANGUAGE OVERRIDE: The user is reading the site in English. Write every word of your answer in natural English (for JSON, every text value in English), regardless of any earlier instruction to use Chinese.",
  ja: "出力言語の指定：ユーザーはサイトを日本語で閲覧しています。それ以前の「繁體中文で回答」という指示に関係なく、回答はすべて自然な日本語で書くこと（JSON の場合は全テキスト値を日本語に）。",
};

/** 呼叫 Gemini generateContent，回傳純文字 */
export async function generate({ system = SYSTEM_PROMPT, lang, contents, json = false, temperature = 0.7, maxOutputTokens = 4096 }: GenerateOptions): Promise<string> {
  const rule = typeof lang === "string" ? LANG_RULE[lang] : undefined;
  if (rule) {
    system = `${system}\n\n${rule}`;
    const last = contents[contents.length - 1];
    if (last?.role === "user") contents = [...contents.slice(0, -1), { role: "user", parts: [{ text: `${last.parts[0].text}\n\n(${rule})` }] }];
  }
  const key = process.env.GEMINI_API_KEY;
  if (!key) throw new HttpError(503, DISABLED_MESSAGE);

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(MODEL)}:generateContent`;
  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      // 金鑰放在標頭（等同 ?key=），避免出現在網址與記錄中
      headers: { "Content-Type": "application/json", "x-goog-api-key": key },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: system }] },
        contents,
        generationConfig: {
          temperature,
          maxOutputTokens,
          ...(json ? { responseMimeType: "application/json" } : {}),
          // 關閉 2.5 Flash 的思考步驟，縮短回應時間
          thinkingConfig: { thinkingBudget: 0 },
        },
      }),
      signal: AbortSignal.timeout(55_000),
    });
  } catch (err) {
    console.error("Gemini fetch failed", err);
    throw new HttpError(504, "AI 服務連線逾時，請稍後再試。");
  }

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    console.error("Gemini error", res.status, detail.slice(0, 500));
    if (res.status === 429) throw new HttpError(429, "AI 使用量已達上限，請稍後再試。");
    if (res.status === 400 || res.status === 403)
      throw new HttpError(502, "AI 服務設定有誤（請確認 GEMINI_API_KEY 是否有效）。");
    throw new HttpError(502, `AI 服務暫時無法回應（${res.status}），請稍後再試。`);
  }

  const data = (await res.json()) as {
    candidates?: { content?: { parts?: { text?: string }[] }; finishReason?: string }[];
    promptFeedback?: { blockReason?: string };
  };
  const text = (data.candidates?.[0]?.content?.parts ?? []).map((p) => p.text ?? "").join("").trim();
  if (!text) {
    if (data.promptFeedback?.blockReason) throw new HttpError(422, "這個問題無法回答，請換個說法再試試。");
    throw new HttpError(502, "AI 沒有產生內容，請再試一次。");
  }
  return text;
}

/** 解析模型回傳的 JSON（容忍 ```json 包裝） */
export function parseJson(text: string): unknown {
  const cleaned = text.replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/, "").trim();
  try {
    return JSON.parse(cleaned);
  } catch {
    const start = cleaned.indexOf("{");
    const end = cleaned.lastIndexOf("}");
    if (start >= 0 && end > start) {
      try {
        return JSON.parse(cleaned.slice(start, end + 1));
      } catch {
        /* fallthrough */
      }
    }
    throw new HttpError(502, "AI 回傳的資料格式有誤，請再試一次。");
  }
}

/** 取字串並裁切長度 */
export function str(v: unknown, max = 2000): string {
  return typeof v === "string" ? v.trim().slice(0, max) : "";
}

/** 讀取 JSON body（Vercel 會自動解析 application/json；保險起見也處理字串與串流） */
async function readBody(req: ApiRequest): Promise<Record<string, unknown>> {
  if (req.body && typeof req.body === "object") return req.body as Record<string, unknown>;
  if (typeof req.body === "string") return JSON.parse(req.body || "{}");
  const chunks: Buffer[] = [];
  for await (const c of req) chunks.push(typeof c === "string" ? Buffer.from(c) : c);
  const raw = Buffer.concat(chunks).toString("utf8");
  return raw ? JSON.parse(raw) : {};
}

function send(res: ApiResponse, status: number, body: unknown) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(body));
}

/** 包裝 POST 端點：方法檢查、body 解析、錯誤轉成中文 JSON */
export function postHandler(fn: (body: Record<string, unknown>) => Promise<unknown>) {
  return async function handler(req: ApiRequest, res: ApiResponse) {
    if (req.method !== "POST") {
      res.setHeader("Allow", "POST");
      return send(res, 405, { error: "只接受 POST 請求" });
    }
    let body: Record<string, unknown>;
    try {
      body = await readBody(req);
    } catch {
      return send(res, 400, { error: "請求內容不是有效的 JSON" });
    }
    try {
      send(res, 200, await fn(body));
    } catch (err) {
      if (err instanceof HttpError) return send(res, err.status, { error: err.message, ...(err.status === 503 ? { disabled: true } : {}) });
      console.error(err);
      send(res, 500, { error: "伺服器發生錯誤，請稍後再試。" });
    }
  };
}
