// POST /api/story  { topic } → { title, slides: [{ caption, narration, imageQuery }] }
import { generate, HttpError, parseJson, postHandler, str } from "./_gemini.js";

export default postHandler(async (body) => {
  const topic = str(body.topic, 80);
  if (!topic) throw new HttpError(400, "請輸入故事主題");

  const prompt = `請以「${topic}」為主題，製作一段給一般大眾觀看的歷史故事投影片，像紀錄片旁白一樣有畫面感。

回傳 JSON，格式如下：
{
  "title": "故事標題（繁體中文，8–16 字）",
  "slides": [
    {
      "caption": "這張投影片的小標題（繁體中文，4–12 字，可含年代）",
      "narration": "旁白（繁體中文，2–3 句，約 50–90 字，適合朗讀）",
      "imageQuery": "用來在英文維基百科搜尋配圖的英文關鍵字（具體的地點、建築、文物、人物或事件名稱，2–5 個英文單字）"
    }
  ]
}

規則：
- slides 共 3–5 張，依時間或因果順序排列，有開場與結尾。
- 內容須符合史實，不要捏造。
- imageQuery 必須是英文、具體且容易在維基百科找到對應條目的名稱（例如 "Great Pyramid of Giza"、"Battle of Actium"），不要用抽象詞。
- 只回傳 JSON。`;

  const text = await generate({ contents: [{ role: "user", parts: [{ text: prompt }] }], json: true, temperature: 0.7, lang: body.lang });
  const data = (parseJson(text) ?? {}) as { title?: unknown; slides?: unknown };

  const slides = (Array.isArray(data.slides) ? data.slides : [])
    .map((s) => {
      const o = (s ?? {}) as Record<string, unknown>;
      return {
        caption: str(o.caption, 40),
        narration: str(o.narration, 400),
        imageQuery: str(o.imageQuery, 100) || topic,
      };
    })
    .filter((s) => s.narration)
    .slice(0, 5);
  if (slides.length < 2) throw new HttpError(502, "AI 產生的故事內容不完整，請再試一次。");

  return { title: str(data.title, 40) || topic, slides: slides.map((s, i) => ({ ...s, caption: s.caption || `第 ${i + 1} 幕` })) };
});
