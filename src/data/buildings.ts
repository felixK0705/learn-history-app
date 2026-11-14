export interface Building {
  id: string;
  name: string;
  englishName: string;
  /** 對應國家 ISO alpha-3 */
  iso: string;
  location: string;
  era: string;
  /** 排序用年份（西元前為負數） */
  sortYear: number;
  style: string;
  model: string;
  /** [緯度, 經度] */
  position: [number, number];
  description: string;
  facts: string[];
}

export const buildings: Building[] = [
  {
    id: "giza",
    position: [29.979, 31.134],
    name: "吉薩金字塔群",
    englishName: "Giza Pyramids",
    iso: "EGY",
    location: "埃及・吉薩",
    era: "約西元前 2560 年",
    sortYear: -2560,
    style: "古埃及陵墓建築",
    model: "giza.glb",
    description:
      "古埃及第四王朝法老古夫、卡夫拉與孟卡拉的陵墓，是古代世界七大奇蹟中唯一仍大致完整保存的一座。",
    facts: [
      "古夫金字塔原高約 146 公尺，在近四千年間都是世界最高的人造建築。",
      "使用約 230 萬塊石灰岩與花崗岩石塊。",
      "四面幾乎精準對齊東南西北四個方位。",
      "前方的獅身人面像長約 73 公尺，以整塊石灰岩基岩雕成。",
    ],
  },
  {
    id: "stonehenge",
    position: [51.179, -1.826],
    name: "巨石陣",
    englishName: "Stonehenge",
    iso: "GBR",
    location: "英國・威爾特郡",
    era: "約西元前 3000–2000 年",
    sortYear: -2500,
    style: "新石器時代巨石建築",
    model: "stonehenge.glb",
    description:
      "由巨大立石圍成的環狀遺跡，石塊排列與夏至日出、冬至日落方向對齊，用途可能與祭祀、曆法與喪葬有關。",
    facts: [
      "部分「青石」來自約 240 公里外的威爾斯普雷塞利山。",
      "最大的砂岩巨石重約 25 公噸。",
      "1986 年列入聯合國教科文組織世界遺產。",
    ],
  },
  {
    id: "parthenon",
    position: [37.972, 23.727],
    name: "帕德嫩神廟",
    englishName: "Parthenon",
    iso: "GRC",
    location: "希臘・雅典衛城",
    era: "西元前 447–432 年",
    sortYear: -447,
    style: "古希臘多立克柱式",
    model: "parthenon.glb",
    description:
      "供奉雅典守護女神雅典娜的神廟，於伯里克利時代興建，是古典希臘建築與民主雅典黃金時代的象徵。",
    facts: [
      "柱子微微向內傾斜且中段略粗（收分），以修正視覺錯覺。",
      "1687 年威尼斯軍隊砲擊時，存放於內的火藥爆炸，使建築嚴重受損。",
      "部分雕刻現藏於倫敦大英博物館，歸還爭議持續至今。",
    ],
  },
  {
    id: "great-wall",
    position: [40.432, 116.57],
    name: "萬里長城",
    englishName: "Great Wall of China",
    iso: "CHN",
    location: "中國・北方",
    era: "西元前 7 世紀–明代",
    sortYear: -221,
    style: "古代軍事防禦工程",
    model: "great-wall.glb",
    description:
      "歷代王朝為抵禦北方遊牧民族而修築的防禦工事，秦始皇統一後連接各國長城，今日所見多為明代重修。",
    facts: [
      "2012 年中國官方公布歷代長城總長約 21,196 公里。",
      "「在太空中肉眼可見長城」是常見的誤解。",
      "沿線設有烽火台，以煙火快速傳遞軍情。",
    ],
  },
  {
    id: "chichen-itza",
    position: [20.684, -88.568],
    name: "奇琴伊察・庫庫爾坎金字塔",
    englishName: "Chichen Itza",
    iso: "MEX",
    location: "墨西哥・猶加敦半島",
    era: "約西元 9–12 世紀",
    sortYear: 900,
    style: "馬雅–托爾特克建築",
    model: "chichen-itza.glb",
    description:
      "馬雅古城奇琴伊察的核心建築，是一座階梯金字塔，也是一部巨大的石造曆法。",
    facts: [
      "四面階梯各 91 階，加上頂部平台共 365 階，對應一年天數。",
      "春分、秋分時，陽光在階梯側面投下如羽蛇蜿蜒而下的影子。",
      "在金字塔前拍手，回音聽起來像格查爾鳥的鳴叫。",
    ],
  },
  {
    id: "colosseum",
    position: [41.89, 12.492],
    name: "羅馬競技場",
    englishName: "Colosseum",
    iso: "ITA",
    location: "義大利・羅馬",
    era: "西元 70–80 年",
    sortYear: 80,
    style: "古羅馬建築",
    model: "colosseum.glb",
    description:
      "弗拉維王朝興建的巨大橢圓形圓形劇場，用於角鬥士競技、猛獸表演與公共慶典，是古羅馬工程技術的代表。",
    facts: [
      "估計可容納約 5 萬至 8 萬名觀眾。",
      "地下設有複雜的通道與升降機關，可讓猛獸突然出現在場上。",
      "大量使用羅馬混凝土與拱券結構。",
    ],
  },
  {
    id: "angkor-wat",
    position: [13.412, 103.867],
    name: "吳哥窟",
    englishName: "Angkor Wat",
    iso: "KHM",
    location: "柬埔寨・暹粒",
    era: "12 世紀上半葉",
    sortYear: 1113,
    style: "高棉建築",
    model: "angkor-wat.glb",
    description:
      "高棉帝國國王蘇利耶跋摩二世興建，原供奉印度教毗濕奴，後轉為佛教寺院，是世界最大的宗教建築群之一。",
    facts: [
      "五座蓮花蓓蕾狀的寶塔象徵宇宙中心須彌山。",
      "迴廊浮雕描繪〈攪拌乳海〉等印度史詩場景。",
      "吳哥窟圖案出現在柬埔寨國旗上。",
    ],
  },
  {
    id: "himeji",
    position: [34.839, 134.694],
    name: "姬路城",
    englishName: "Himeji Castle",
    iso: "JPN",
    location: "日本・兵庫縣姬路市",
    era: "1609 年完成現存天守",
    sortYear: 1609,
    style: "日本城郭建築",
    model: "himeji.glb",
    description:
      "因白色外牆宛如展翅白鷺而別名「白鷺城」，是日本現存最完整的古城之一，躲過了戰火與地震。",
    facts: [
      "1993 年與法隆寺一同成為日本首批世界遺產。",
      "城內迷宮般的通道設計用來迷惑入侵者。",
      "二戰空襲時燃燒彈落在天守卻未爆炸。",
    ],
  },
  {
    id: "taj-mahal",
    position: [27.175, 78.042],
    name: "泰姬瑪哈陵",
    englishName: "Taj Mahal",
    iso: "IND",
    location: "印度・阿格拉",
    era: "1632–1653 年",
    sortYear: 1632,
    style: "蒙兀兒建築",
    model: "taj-mahal.glb",
    description:
      "蒙兀兒皇帝沙賈汗為紀念愛妻慕塔芝・瑪哈所建的白色大理石陵墓，融合波斯、伊斯蘭與印度建築風格。",
    facts: [
      "動員約兩萬名工匠，花費約 20 年完成。",
      "大理石上鑲嵌了來自各地的寶石。",
      "四座宣禮塔略向外傾，以防地震時倒向主陵。",
    ],
  },
  {
    id: "eiffel",
    position: [48.858, 2.294],
    name: "艾菲爾鐵塔",
    englishName: "Eiffel Tower",
    iso: "FRA",
    location: "法國・巴黎",
    era: "1887–1889 年",
    sortYear: 1889,
    style: "鍛鐵結構",
    model: "eiffel.glb",
    description:
      "為 1889 年巴黎世界博覽會暨法國大革命一百週年而建，起初飽受藝術家批評，如今成為法國最具代表性的地標。",
    facts: [
      "由約 18,000 個鐵件、250 萬顆鉚釘組成。",
      "夏天受熱膨脹，塔頂可能升高十多公分。",
      "原本只預計保留 20 年，因可作無線電天線而免於拆除。",
    ],
  },
];
