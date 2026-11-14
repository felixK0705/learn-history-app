// 產生 ISO alpha-3 → 繁體中文國名對照（scripts/out/zh-names.json）
import fs from "node:fs";
import countries from "i18n-iso-countries";
import zh from "i18n-iso-countries/langs/zh.json" with { type: "json" };
import { tify } from "chinese-conv";

countries.registerLocale(zh);
const out = {};
for (const a3 of Object.keys(countries.getAlpha3Codes())) {
  const name = countries.getName(a3, "zh");
  if (name) out[a3] = tify(name);
}
// 台灣慣用譯名修正
Object.assign(out, {
  TWN: "台灣", KOR: "韓國", PRK: "北韓", USA: "美國", GBR: "英國", RUS: "俄羅斯", ITA: "義大利", AUS: "澳洲",
  NZL: "紐西蘭", SAU: "沙烏地阿拉伯", KHM: "柬埔寨", LAO: "寮國", IDN: "印尼", MYS: "馬來西亞", SGP: "新加坡",
  IRN: "伊朗", IRQ: "伊拉克", JOR: "約旦", YEM: "葉門", ARE: "阿拉伯聯合大公國", QAT: "卡達", OMN: "阿曼",
  KAZ: "哈薩克", UZB: "烏茲別克", TKM: "土庫曼", KGZ: "吉爾吉斯", TJK: "塔吉克", AFG: "阿富汗", PAK: "巴基斯坦",
  BGD: "孟加拉", NPL: "尼泊爾", BTN: "不丹", LKA: "斯里蘭卡", MDV: "馬爾地夫", MMR: "緬甸", PHL: "菲律賓",
  TLS: "東帝汶", PNG: "巴布亞紐幾內亞", SLB: "索羅門群島", VUT: "萬那杜", FJI: "斐濟", WSM: "薩摩亞", TON: "東加",
  KIR: "吉里巴斯", FSM: "密克羅尼西亞", MHL: "馬紹爾群島", PLW: "帛琉", NRU: "諾魯", TUV: "吐瓦魯",
  CZE: "捷克", SVK: "斯洛伐克", SVN: "斯洛維尼亞", HRV: "克羅埃西亞", SRB: "塞爾維亞", BIH: "波士尼亞與赫塞哥維納",
  MNE: "蒙特內哥羅", MKD: "北馬其頓", ALB: "阿爾巴尼亞", ROU: "羅馬尼亞", BGR: "保加利亞", MDA: "摩爾多瓦",
  UKR: "烏克蘭", BLR: "白俄羅斯", LTU: "立陶宛", LVA: "拉脫維亞", EST: "愛沙尼亞", GEO: "喬治亞", ARM: "亞美尼亞",
  AZE: "亞塞拜然", CYP: "賽普勒斯", MLT: "馬爾他", LUX: "盧森堡", LIE: "列支敦斯登", AND: "安道爾", MCO: "摩納哥",
  SMR: "聖馬利諾", VAT: "梵蒂岡", ISL: "冰島", IRL: "愛爾蘭", NOR: "挪威", SWE: "瑞典", FIN: "芬蘭", DNK: "丹麥",
  NLD: "荷蘭", BEL: "比利時", CHE: "瑞士", AUT: "奧地利", POL: "波蘭", HUN: "匈牙利", PRT: "葡萄牙", ESP: "西班牙",
  GRC: "希臘", TUR: "土耳其", ISR: "以色列", PSE: "巴勒斯坦", LBN: "黎巴嫩", SYR: "敘利亞", KWT: "科威特", BHR: "巴林",
  EGY: "埃及", LBY: "利比亞", TUN: "突尼西亞", DZA: "阿爾及利亞", MAR: "摩洛哥", ESH: "西撒哈拉", MRT: "茅利塔尼亞",
  MLI: "馬利", NER: "尼日", TCD: "查德", SDN: "蘇丹", SSD: "南蘇丹", ETH: "衣索比亞", ERI: "厄利垂亞", DJI: "吉布地",
  SOM: "索馬利亞", KEN: "肯亞", UGA: "烏干達", RWA: "盧安達", BDI: "蒲隆地", TZA: "坦尚尼亞", MOZ: "莫三比克",
  MWI: "馬拉威", ZMB: "尚比亞", ZWE: "辛巴威", BWA: "波札那", NAM: "納米比亞", ZAF: "南非", LSO: "賴索托",
  SWZ: "史瓦帝尼", MDG: "馬達加斯加", MUS: "模里西斯", SYC: "塞席爾", COM: "葛摩", AGO: "安哥拉", COD: "剛果民主共和國",
  COG: "剛果共和國", GAB: "加彭", GNQ: "赤道幾內亞", CMR: "喀麥隆", CAF: "中非共和國", NGA: "奈及利亞", BEN: "貝南",
  TGO: "多哥", GHA: "迦納", CIV: "象牙海岸", LBR: "賴比瑞亞", SLE: "獅子山", GIN: "幾內亞", GNB: "幾內亞比索",
  SEN: "塞內加爾", GMB: "甘比亞", CPV: "維德角", BFA: "布吉納法索", STP: "聖多美普林西比", MEX: "墨西哥",
  GTM: "瓜地馬拉", BLZ: "貝里斯", HND: "宏都拉斯", SLV: "薩爾瓦多", NIC: "尼加拉瓜", CRI: "哥斯大黎加", PAN: "巴拿馬",
  CUB: "古巴", JAM: "牙買加", HTI: "海地", DOM: "多明尼加", BHS: "巴哈馬", BRB: "巴貝多", TTO: "千里達及托巴哥",
  GRD: "格瑞那達", LCA: "聖露西亞", VCT: "聖文森及格瑞那丁", ATG: "安地卡及巴布達", DMA: "多米尼克",
  KNA: "聖克里斯多福及尼維斯", COL: "哥倫比亞", VEN: "委內瑞拉", GUY: "蓋亞那", SUR: "蘇利南", ECU: "厄瓜多",
  PER: "秘魯", BOL: "玻利維亞", BRA: "巴西", PRY: "巴拉圭", URY: "烏拉圭", ARG: "阿根廷", CHL: "智利", CAN: "加拿大",
  GRL: "格陵蘭", MNG: "蒙古", CHN: "中國", JPN: "日本", IND: "印度", THA: "泰國", VNM: "越南", BRN: "汶萊",
  DEU: "德國", FRA: "法國", SAU2: undefined,
});
delete out.SAU2;
fs.mkdirSync("scripts/out", { recursive: true });
fs.writeFileSync("scripts/out/zh-names.json", JSON.stringify(out, null, 0));
console.log(Object.keys(out).length);

// ISO alpha-3 → alpha-2（用於國旗 emoji）
const a2 = {};
for (const [a3, code] of Object.entries(countries.getAlpha3Codes())) a2[a3] = code;
fs.writeFileSync("scripts/out/a2.json", JSON.stringify(a2));
