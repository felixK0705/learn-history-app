// POST /api/explain  { text, country?, question? } → { answer }
import { generate, HttpError, postHandler, str } from "./_gemini.js";

export default postHandler(async (body) => {
  const text = str(body.text, 2000);
  if (!text) throw new HttpError(400, "請先選取要解釋的文字");
  const country = str(body.country, 80);
  const question = str(body.question, 1000);

  const prompt =
    `請詳細解釋以下文字的歷史背景、重要性和相關細節${country ? `（這段文字出自「${country}」的歷史介紹）` : ""}：\n\n` +
    `「${text}」\n\n` +
    (question
      ? `使用者特別想知道：${question}\n`
      : "請依序說明：1. 這段文字在講什麼；2. 歷史背景與前因；3. 重要性與後續影響；4. 值得一提的相關細節或人物。\n") +
    "篇幅約 250–400 字。";

  const answer = await generate({ contents: [{ role: "user", parts: [{ text: prompt }] }] });
  return { answer };
});
