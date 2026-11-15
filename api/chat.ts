// POST /api/chat  { messages: [{ role, content }], context?: string } → { answer }
import { generate, HttpError, postHandler, str, SYSTEM_PROMPT, type GeminiContent } from "./_gemini.js";

export default postHandler(async (body) => {
  const raw = Array.isArray(body.messages) ? body.messages : [];
  const contents: GeminiContent[] = raw
    .slice(-20)
    .map((m) => {
      const msg = (m ?? {}) as { role?: unknown; content?: unknown };
      const text = str(msg.content, 4000);
      return { role: msg.role === "assistant" || msg.role === "model" ? "model" : "user", parts: [{ text }] } as GeminiContent;
    })
    .filter((c) => c.parts[0].text);
  // Gemini 要求對話從 user 開始
  while (contents.length && contents[0].role !== "user") contents.shift();
  if (!contents.length || contents[contents.length - 1].role !== "user") throw new HttpError(400, "請輸入問題");

  const context = str(body.context, 1500);
  const system = context ? `${SYSTEM_PROMPT}\n\n目前情境（使用者在網站上的位置）：${context}。若問題與此情境相關，請結合它回答。` : SYSTEM_PROMPT;
  const answer = await generate({ system, contents });
  return { answer };
});
