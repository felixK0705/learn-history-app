// POST /api/relationships  { name } → { introduction, nodes, links }
import { generate, HttpError, parseJson, postHandler, str } from "./_gemini.js";

const TYPES = ["敵對", "盟友", "師徒", "親屬", "君臣", "影響", "戀人"] as const;
type RelType = (typeof TYPES)[number];

const TYPE_ALIASES: Record<string, RelType> = {
  hostile: "敵對", enemy: "敵對", rival: "敵對", 敵人: "敵對", 對手: "敵對", 衝突: "敵對",
  ally: "盟友", friend: "盟友", 朋友: "盟友", 同盟: "盟友", 友好: "盟友",
  mentor: "師徒", teacher: "師徒", student: "師徒", 師生: "師徒",
  family: "親屬", 家人: "親屬", 家族: "親屬", 父子: "親屬", 母子: "親屬", 兄弟: "親屬", 夫妻: "親屬",
  subordinate: "君臣", 部下: "君臣", 上下級: "君臣", 主從: "君臣",
  influence: "影響", neutral: "影響", 中性: "影響",
  lover: "戀人", 情人: "戀人", 愛人: "戀人",
};

function normType(v: unknown): RelType {
  const s = str(v, 20);
  if ((TYPES as readonly string[]).includes(s)) return s as RelType;
  return TYPE_ALIASES[s.toLowerCase()] ?? TYPE_ALIASES[s] ?? "影響";
}

const norm = (s: string) => s.replace(/[\s·・．.\-_'"「」]/g, "").toLowerCase();

export default postHandler(async (body) => {
  const name = str(body.name, 60);
  if (!name) throw new HttpError(400, "請輸入人物名稱");

  const prompt = `請使用繁體中文生成關於歷史人物「${name}」的人物關係圖資料。
請找出與「${name}」關係最密切的重要歷史人物，連同「${name}」本人共 10–15 人，並定義他們之間的關係。

回傳 JSON，格式如下：
{
  "introduction": "「${name}」的生平簡介，約 100–150 字",
  "nodes": [
    { "id": "英文或拼音的唯一識別碼", "name": "人物名稱（繁體中文）", "group": "所屬勢力或類別，如：魏國、蜀國、羅馬共和派", "val": 1到10的重要性整數, "description": "2–8 字的身分描述，如：蜀漢丞相" }
  ],
  "links": [
    { "source": "人物 id", "target": "人物 id", "label": "2–6 字的關係描述，如：結拜兄弟、殺父仇人", "type": "敵對、盟友、師徒、親屬、君臣、影響、戀人 七者之一" }
  ]
}

規則：
- nodes 的第一個必須是「${name}」本人，val 為 10。
- 每個其他人物至少要有一條連線；大多數連線應與「${name}」相連，也可加入其他人物彼此之間的重要關係。
- links 的 source、target 必須使用 nodes 中存在的 id。
- 只能是真實存在的歷史人物，不要捏造。若「${name}」不是可辨識的歷史人物，回傳 {"introduction": "", "nodes": [], "links": []}。
- 所有文字必須是繁體中文。只回傳 JSON。
- type 欄位一律填上述七個中文值之一（即使被要求以其他語言輸出也不翻譯 type）。`;

  const text = await generate({ contents: [{ role: "user", parts: [{ text: prompt }] }], json: true, temperature: 0.4, maxOutputTokens: 6144, lang: body.lang });
  const data = (parseJson(text) ?? {}) as { introduction?: unknown; nodes?: unknown; links?: unknown };

  // ── 清理節點：去除重複 id 與重複姓名 ──
  const nodes: { id: string; name: string; group: string; val: number; description: string }[] = [];
  const idMap = new Map<string, string>(); // 原始 id / 姓名 → 保留下來的 id
  for (const n of Array.isArray(data.nodes) ? data.nodes : []) {
    const o = (n ?? {}) as Record<string, unknown>;
    const nodeName = str(o.name, 40);
    let id = str(o.id, 60) || nodeName;
    if (!nodeName || !id) continue;
    const key = norm(nodeName);
    const existing = idMap.get(`name:${key}`) ?? idMap.get(`id:${id}`);
    if (existing) {
      idMap.set(`id:${id}`, existing);
      continue;
    }
    if (nodes.some((x) => x.id === id)) id = `${id}_${nodes.length}`;
    const val = Math.round(Number(o.val));
    nodes.push({
      id,
      name: nodeName,
      group: str(o.group, 30) || "其他",
      val: Number.isFinite(val) ? Math.min(10, Math.max(1, val)) : 5,
      description: str(o.description, 40),
    });
    idMap.set(`id:${str(o.id, 60) || nodeName}`, id);
    idMap.set(`name:${key}`, id);
    if (nodes.length >= 15) break;
  }
  if (!nodes.length) throw new HttpError(404, `找不到「${name}」的人物關係資料，請確認名稱或換個寫法。`);

  // 主角放第一個
  const target = norm(name);
  const ci = nodes.findIndex((n) => norm(n.name) === target || norm(n.name).includes(target) || target.includes(norm(n.name)));
  if (ci > 0) nodes.unshift(...nodes.splice(ci, 1));
  nodes[0].val = 10;

  // ── 清理連線：端點必須存在、不可自連、同一對人物只保留一條 ──
  const resolve = (v: unknown) => {
    const s = str(v, 60);
    return idMap.get(`id:${s}`) ?? idMap.get(`name:${norm(s)}`);
  };
  const seen = new Set<string>();
  const links: { source: string; target: string; label: string; type: RelType }[] = [];
  for (const l of Array.isArray(data.links) ? data.links : []) {
    const o = (l ?? {}) as Record<string, unknown>;
    const source = resolve(o.source);
    const tgt = resolve(o.target);
    if (!source || !tgt || source === tgt) continue;
    const pair = [source, tgt].sort().join("\u0000");
    if (seen.has(pair)) continue;
    seen.add(pair);
    const type = normType(o.type);
    links.push({ source, target: tgt, label: str(o.label, 20) || type, type });
  }

  // 沒有任何連線的人物，補一條與主角的「影響」關係，避免孤立節點
  const center = nodes[0].id;
  for (const n of nodes.slice(1)) {
    if (!links.some((l) => l.source === n.id || l.target === n.id)) {
      links.push({ source: center, target: n.id, label: "相關人物", type: "影響" });
    }
  }

  return { introduction: str(data.introduction, 1200), nodes, links };
});
