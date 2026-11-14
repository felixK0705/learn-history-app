export type RelationType = "師徒" | "親屬" | "盟友" | "敵對" | "君臣" | "影響" | "戀人";

export interface Figure {
  id: string;
  name: string;
  englishName: string;
  iso: string;
  born: number;
  died: number;
  role: string;
  /** 所屬群組，用於上色與篩選 */
  group: string;
  bio: string;
}

export interface Relation {
  source: string;
  target: string;
  type: RelationType;
  label: string;
}

export const relationColors: Record<RelationType, string> = {
  師徒: "#7dd3fc",
  親屬: "#fbbf24",
  盟友: "#4ade80",
  敵對: "#f87171",
  君臣: "#c084fc",
  影響: "#94a3b8",
  戀人: "#f472b6",
};

export const groups: { id: string; name: string; color: string }[] = [
  { id: "greece", name: "古希臘哲學", color: "#60a5fa" },
  { id: "rome", name: "羅馬共和末期", color: "#f97316" },
  { id: "china-ancient", name: "先秦與秦漢", color: "#ef4444" },
  { id: "three-kingdoms", name: "三國", color: "#e11d48" },
  { id: "renaissance", name: "文藝復興", color: "#a78bfa" },
  { id: "sengoku", name: "日本戰國", color: "#f43f5e" },
  { id: "science", name: "科學革命", color: "#22d3ee" },
  { id: "revolution", name: "革命與帝國", color: "#facc15" },
  { id: "modern", name: "二十世紀", color: "#34d399" },
];

export const figures: Figure[] = [
  // 古希臘
  { id: "socrates", name: "蘇格拉底", englishName: "Socrates", iso: "GRC", born: -470, died: -399, role: "哲學家", group: "greece", bio: "以對話詰問法探究真理，主張「未經檢視的人生不值得活」，最終被雅典判處飲毒芹汁而死。" },
  { id: "plato", name: "柏拉圖", englishName: "Plato", iso: "GRC", born: -428, died: -348, role: "哲學家", group: "greece", bio: "蘇格拉底的學生，創立雅典學院，提出理型論，著有《理想國》。" },
  { id: "aristotle", name: "亞里斯多德", englishName: "Aristotle", iso: "GRC", born: -384, died: -322, role: "哲學家", group: "greece", bio: "柏拉圖的學生、亞歷山大大帝的老師，著作橫跨邏輯、生物、政治與倫理學。" },
  { id: "alexander", name: "亞歷山大大帝", englishName: "Alexander the Great", iso: "GRC", born: -356, died: -323, role: "馬其頓國王", group: "greece", bio: "十年間建立橫跨希臘、埃及至印度河的帝國，開啟希臘化時代。" },
  { id: "philip2", name: "腓力二世", englishName: "Philip II of Macedon", iso: "GRC", born: -382, died: -336, role: "馬其頓國王", group: "greece", bio: "改革馬其頓軍隊、征服希臘城邦，為兒子亞歷山大的東征奠定基礎。" },
  { id: "darius3", name: "大流士三世", englishName: "Darius III", iso: "IRN", born: -380, died: -330, role: "波斯皇帝", group: "greece", bio: "阿契美尼德王朝最後一位皇帝，在高加米拉戰役敗給亞歷山大。" },

  // 羅馬
  { id: "caesar", name: "凱撒", englishName: "Julius Caesar", iso: "ITA", born: -100, died: -44, role: "羅馬將軍、獨裁官", group: "rome", bio: "征服高盧、渡過盧比孔河發動內戰，成為終身獨裁官後遇刺身亡。" },
  { id: "pompey", name: "龐培", englishName: "Pompey", iso: "ITA", born: -106, died: -48, role: "羅馬將軍", group: "rome", bio: "與凱撒、克拉蘇組成前三頭同盟，後與凱撒決裂，兵敗逃往埃及被殺。" },
  { id: "crassus", name: "克拉蘇", englishName: "Crassus", iso: "ITA", born: -115, died: -53, role: "羅馬政治家", group: "rome", bio: "羅馬首富，前三頭同盟成員，在卡萊戰役敗給帕提亞而死。" },
  { id: "brutus", name: "布魯圖斯", englishName: "Brutus", iso: "ITA", born: -85, died: -42, role: "羅馬元老", group: "rome", bio: "刺殺凱撒的主謀之一，凱撒臨死前據說說出「還有你嗎，布魯圖斯？」" },
  { id: "augustus", name: "屋大維（奧古斯都）", englishName: "Augustus", iso: "ITA", born: -63, died: 14, role: "羅馬帝國首位皇帝", group: "rome", bio: "凱撒的養子，擊敗安東尼與克麗奧佩脫拉後建立元首制，開啟羅馬和平。" },
  { id: "antony", name: "馬克・安東尼", englishName: "Mark Antony", iso: "ITA", born: -83, died: -30, role: "羅馬將軍", group: "rome", bio: "凱撒的部將，後三頭同盟成員，與克麗奧佩脫拉結盟，在亞克興海戰敗給屋大維。" },
  { id: "cleopatra", name: "克麗奧佩脫拉七世", englishName: "Cleopatra VII", iso: "EGY", born: -69, died: -30, role: "埃及女王", group: "rome", bio: "托勒密王朝最後一位法老，先後與凱撒、安東尼結盟，埃及隨其死去併入羅馬。" },

  // 先秦與秦漢
  { id: "confucius", name: "孔子", englishName: "Confucius", iso: "CHN", born: -551, died: -479, role: "思想家、教育家", group: "china-ancient", bio: "儒家創始人，主張仁與禮，有教無類，弟子整理其言行成《論語》。" },
  { id: "laozi", name: "老子", englishName: "Laozi", iso: "CHN", born: -571, died: -471, role: "思想家", group: "china-ancient", bio: "道家創始人，相傳著有《道德經》；據《史記》記載孔子曾向他問禮。（生卒年為傳統說法）" },
  { id: "mencius", name: "孟子", englishName: "Mencius", iso: "CHN", born: -372, died: -289, role: "思想家", group: "china-ancient", bio: "受業於子思的門人，發揚孔子學說，提出性善論與民貴君輕，被尊為亞聖。" },
  { id: "xunzi", name: "荀子", englishName: "Xunzi", iso: "CHN", born: -310, died: -238, role: "思想家", group: "china-ancient", bio: "戰國末期儒家，主張性惡論與禮法並重，學生有韓非與李斯。" },
  { id: "hanfei", name: "韓非", englishName: "Han Fei", iso: "CHN", born: -280, died: -233, role: "法家思想家", group: "china-ancient", bio: "集法家之大成，主張法、術、勢，深受秦王嬴政賞識，卻遭同門李斯陷害而死。" },
  { id: "lisi", name: "李斯", englishName: "Li Si", iso: "CHN", born: -284, died: -208, role: "秦朝丞相", group: "china-ancient", bio: "輔佐秦始皇統一六國，推行郡縣制與書同文，後被趙高陷害腰斬。" },
  { id: "qinshihuang", name: "秦始皇", englishName: "Qin Shi Huang", iso: "CHN", born: -259, died: -210, role: "秦朝開國皇帝", group: "china-ancient", bio: "西元前 221 年統一中國，自稱始皇帝，統一文字、度量衡與貨幣。" },
  { id: "xiangyu", name: "項羽", englishName: "Xiang Yu", iso: "CHN", born: -232, died: -202, role: "西楚霸王", group: "china-ancient", bio: "秦末起義領袖，鉅鹿之戰大破秦軍，楚漢相爭中敗給劉邦，烏江自刎。" },
  { id: "liubang", name: "劉邦", englishName: "Liu Bang", iso: "CHN", born: -256, died: -195, role: "漢朝開國皇帝", group: "china-ancient", bio: "出身平民，善於用人，擊敗項羽建立漢朝。" },
  { id: "hanxin", name: "韓信", englishName: "Han Xin", iso: "CHN", born: -231, died: -196, role: "漢初名將", group: "china-ancient", bio: "「國士無雙」，為劉邦打下半壁江山，後被呂后與蕭何設計殺害。" },
  { id: "zhangliang", name: "張良", englishName: "Zhang Liang", iso: "CHN", born: -250, died: -186, role: "漢初謀臣", group: "china-ancient", bio: "「運籌帷幄之中，決勝千里之外」，功成後急流勇退。" },

  // 三國
  { id: "caocao", name: "曹操", englishName: "Cao Cao", iso: "CHN", born: 155, died: 220, role: "魏王", group: "three-kingdoms", bio: "挾天子以令諸侯，統一北方，奠定曹魏基業，亦為傑出詩人。" },
  { id: "liubei", name: "劉備", englishName: "Liu Bei", iso: "CHN", born: 161, died: 223, role: "蜀漢昭烈帝", group: "three-kingdoms", bio: "以仁德聞名，三顧茅廬請出諸葛亮，建立蜀漢。" },
  { id: "sunquan", name: "孫權", englishName: "Sun Quan", iso: "CHN", born: 182, died: 252, role: "吳大帝", group: "three-kingdoms", bio: "繼承父兄基業據有江東，與劉備聯手在赤壁擊退曹操。" },
  { id: "zhugeliang", name: "諸葛亮", englishName: "Zhuge Liang", iso: "CHN", born: 181, died: 234, role: "蜀漢丞相", group: "three-kingdoms", bio: "提出隆中對，輔佐劉備父子，鞠躬盡瘁，死而後已。" },
  { id: "guanyu", name: "關羽", englishName: "Guan Yu", iso: "CHN", born: 160, died: 220, role: "蜀漢名將", group: "three-kingdoms", bio: "以忠義著稱，後世尊為關聖帝君，失荊州後被東吳所殺。" },
  { id: "zhouyu", name: "周瑜", englishName: "Zhou Yu", iso: "CHN", born: 175, died: 210, role: "東吳都督", group: "three-kingdoms", bio: "赤壁之戰吳軍主帥，以火攻大破曹軍。" },
  { id: "simayi", name: "司馬懿", englishName: "Sima Yi", iso: "CHN", born: 179, died: 251, role: "曹魏重臣", group: "three-kingdoms", bio: "多次抵禦諸葛亮北伐，其孫司馬炎篡魏建立晉朝。" },

  // 文藝復興
  { id: "lorenzo", name: "羅倫佐・德・麥地奇", englishName: "Lorenzo de' Medici", iso: "ITA", born: 1449, died: 1492, role: "佛羅倫斯統治者", group: "renaissance", bio: "人稱「偉大的羅倫佐」，大力贊助藝術家，使佛羅倫斯成為文藝復興中心。" },
  { id: "verrocchio", name: "維洛及奧", englishName: "Andrea del Verrocchio", iso: "ITA", born: 1435, died: 1488, role: "雕塑家、畫家", group: "renaissance", bio: "佛羅倫斯重要工作室主人，達文西曾在此當學徒。" },
  { id: "davinci", name: "達文西", englishName: "Leonardo da Vinci", iso: "ITA", born: 1452, died: 1519, role: "畫家、發明家", group: "renaissance", bio: "《蒙娜麗莎》與《最後的晚餐》作者，手稿涵蓋解剖、工程與飛行器構想。" },
  { id: "michelangelo", name: "米開朗基羅", englishName: "Michelangelo", iso: "ITA", born: 1475, died: 1564, role: "雕塑家、畫家", group: "renaissance", bio: "創作《大衛像》與西斯汀禮拜堂天頂畫，少年時曾寄居麥地奇家。" },
  { id: "raphael", name: "拉斐爾", englishName: "Raphael", iso: "ITA", born: 1483, died: 1520, role: "畫家", group: "renaissance", bio: "《雅典學院》作者，畫中將柏拉圖畫成達文西的模樣。" },
  { id: "machiavelli", name: "馬基維利", englishName: "Niccolò Machiavelli", iso: "ITA", born: 1469, died: 1527, role: "政治思想家", group: "renaissance", bio: "著有《君王論》，並將此書獻給麥地奇家族的羅倫佐二世。" },
  { id: "julius2", name: "儒略二世", englishName: "Pope Julius II", iso: "ITA", born: 1443, died: 1513, role: "教宗", group: "renaissance", bio: "「戰士教宗」，委託米開朗基羅繪製西斯汀天頂、拉斐爾繪製梵蒂岡房間壁畫。" },

  // 日本戰國
  { id: "nobunaga", name: "織田信長", englishName: "Oda Nobunaga", iso: "JPN", born: 1534, died: 1582, role: "戰國大名", group: "sengoku", bio: "以鐵砲戰術與樂市樂座推動統一，在本能寺之變中被明智光秀所害。" },
  { id: "hideyoshi", name: "豐臣秀吉", englishName: "Toyotomi Hideyoshi", iso: "JPN", born: 1537, died: 1598, role: "關白", group: "sengoku", bio: "出身農民，信長死後完成日本統一，晚年出兵朝鮮。" },
  { id: "ieyasu", name: "德川家康", englishName: "Tokugawa Ieyasu", iso: "JPN", born: 1543, died: 1616, role: "江戶幕府初代將軍", group: "sengoku", bio: "關原之戰勝利後開創延續約 260 年的江戶幕府。" },
  { id: "mitsuhide", name: "明智光秀", englishName: "Akechi Mitsuhide", iso: "JPN", born: 1528, died: 1582, role: "武將", group: "sengoku", bio: "織田家重臣，發動本能寺之變，旋即在山崎之戰敗給秀吉。" },
  { id: "yisunsin", name: "李舜臣", englishName: "Yi Sun-sin", iso: "KOR", born: 1545, died: 1598, role: "朝鮮水軍將領", group: "sengoku", bio: "在壬辰倭亂中以龜船屢敗日本水軍，於露梁海戰中陣亡。" },
  { id: "shingen", name: "武田信玄", englishName: "Takeda Shingen", iso: "JPN", born: 1521, died: 1573, role: "戰國大名", group: "sengoku", bio: "「甲斐之虎」，三方原之戰大敗德川家康。" },
  { id: "kenshin", name: "上杉謙信", englishName: "Uesugi Kenshin", iso: "JPN", born: 1530, died: 1578, role: "戰國大名", group: "sengoku", bio: "「越後之龍」，與武田信玄在川中島多次交戰。" },

  // 科學革命
  { id: "copernicus", name: "哥白尼", englishName: "Nicolaus Copernicus", iso: "POL", born: 1473, died: 1543, role: "天文學家", group: "science", bio: "提出日心說，著有《天體運行論》，掀起科學革命。" },
  { id: "galileo", name: "伽利略", englishName: "Galileo Galilei", iso: "ITA", born: 1564, died: 1642, role: "物理學家、天文學家", group: "science", bio: "改良望遠鏡觀測木星衛星，支持日心說而遭宗教裁判所審判。" },
  { id: "kepler", name: "克卜勒", englishName: "Johannes Kepler", iso: "DEU", born: 1571, died: 1630, role: "天文學家", group: "science", bio: "根據第谷的觀測資料提出行星運動三大定律。" },
  { id: "tycho", name: "第谷", englishName: "Tycho Brahe", iso: "DNK", born: 1546, died: 1601, role: "天文學家", group: "science", bio: "丹麥天文學家，留下望遠鏡發明前最精確的天文觀測紀錄。" },
  { id: "newton", name: "牛頓", englishName: "Isaac Newton", iso: "GBR", born: 1643, died: 1727, role: "物理學家、數學家", group: "science", bio: "提出萬有引力與運動三定律，發展微積分，「站在巨人的肩膀上」。" },
  { id: "leibniz", name: "萊布尼茲", englishName: "Gottfried Leibniz", iso: "DEU", born: 1646, died: 1716, role: "數學家、哲學家", group: "science", bio: "與牛頓各自獨立發明微積分，引發激烈的優先權之爭。" },
  { id: "darwin", name: "達爾文", englishName: "Charles Darwin", iso: "GBR", born: 1809, died: 1882, role: "博物學家", group: "science", bio: "搭乘小獵犬號環球考察，著《物種起源》提出天擇演化論。" },
  { id: "einstein", name: "愛因斯坦", englishName: "Albert Einstein", iso: "DEU", born: 1879, died: 1955, role: "物理學家", group: "science", bio: "提出相對論與光量子假說，1921 年獲諾貝爾物理學獎。" },

  // 革命與帝國
  { id: "washington", name: "喬治・華盛頓", englishName: "George Washington", iso: "USA", born: 1732, died: 1799, role: "美國首任總統", group: "revolution", bio: "領導大陸軍贏得獨立戰爭，兩任總統後主動卸任。" },
  { id: "lafayette", name: "拉法葉", englishName: "Marquis de Lafayette", iso: "FRA", born: 1757, died: 1834, role: "法國將軍", group: "revolution", bio: "志願投身美國獨立戰爭，與華盛頓情同父子，後參與起草《人權宣言》。" },
  { id: "jefferson", name: "湯瑪斯・傑佛遜", englishName: "Thomas Jefferson", iso: "USA", born: 1743, died: 1826, role: "美國第三任總統", group: "revolution", bio: "《獨立宣言》主要起草人，任內完成路易斯安那購地。" },
  { id: "louis16", name: "路易十六", englishName: "Louis XVI", iso: "FRA", born: 1754, died: 1793, role: "法國國王", group: "revolution", bio: "支援美國獨立戰爭使財政惡化，法國大革命中被送上斷頭台。" },
  { id: "marie", name: "瑪麗・安東尼", englishName: "Marie Antoinette", iso: "FRA", born: 1755, died: 1793, role: "法國王后", group: "revolution", bio: "奧地利公主，路易十六之妻，大革命中被處決。" },
  { id: "robespierre", name: "羅伯斯比爾", englishName: "Maximilien Robespierre", iso: "FRA", born: 1758, died: 1794, role: "雅各賓派領袖", group: "revolution", bio: "恐怖統治的核心人物，熱月政變後被處決。" },
  { id: "napoleon", name: "拿破崙", englishName: "Napoleon Bonaparte", iso: "FRA", born: 1769, died: 1821, role: "法國皇帝", group: "revolution", bio: "大革命後崛起的軍事天才，頒布《拿破崙法典》，最終敗於滑鐵盧。" },
  { id: "wellington", name: "威靈頓公爵", englishName: "Duke of Wellington", iso: "GBR", born: 1769, died: 1852, role: "英國將軍", group: "revolution", bio: "在滑鐵盧戰役中與普魯士聯軍擊敗拿破崙。" },
  { id: "alexander1", name: "亞歷山大一世", englishName: "Alexander I of Russia", iso: "RUS", born: 1777, died: 1825, role: "俄國沙皇", group: "revolution", bio: "1812 年擊退拿破崙入侵，主導維也納會議後的神聖同盟。" },
  { id: "beethoven", name: "貝多芬", englishName: "Ludwig van Beethoven", iso: "DEU", born: 1770, died: 1827, role: "作曲家", group: "revolution", bio: "原將《英雄交響曲》題獻給拿破崙，得知其稱帝後憤而劃去題詞。" },

  // 二十世紀
  { id: "sunyatsen", name: "孫中山", englishName: "Sun Yat-sen", iso: "CHN", born: 1866, died: 1925, role: "中華民國國父", group: "modern", bio: "領導推翻清朝的革命，提出三民主義，創立中國國民黨。" },
  { id: "chiangkaishek", name: "蔣中正", englishName: "Chiang Kai-shek", iso: "TWN", born: 1887, died: 1975, role: "中華民國總統", group: "modern", bio: "北伐統一、領導對日抗戰，國共內戰失利後政府遷台。" },
  { id: "maozedong", name: "毛澤東", englishName: "Mao Zedong", iso: "CHN", born: 1893, died: 1976, role: "中華人民共和國主席", group: "modern", bio: "中共領導人，1949 年建立中華人民共和國，發動大躍進與文化大革命。" },
  { id: "churchill", name: "邱吉爾", englishName: "Winston Churchill", iso: "GBR", born: 1874, died: 1965, role: "英國首相", group: "modern", bio: "二戰時帶領英國抵抗納粹德國，1953 年獲諾貝爾文學獎。" },
  { id: "fdr", name: "小羅斯福", englishName: "Franklin D. Roosevelt", iso: "USA", born: 1882, died: 1945, role: "美國總統", group: "modern", bio: "推行新政對抗經濟大蕭條，帶領美國參與二戰，唯一連任四屆的總統。" },
  { id: "stalin", name: "史達林", englishName: "Joseph Stalin", iso: "RUS", born: 1878, died: 1953, role: "蘇聯領導人", group: "modern", bio: "推動工業化與集體化，進行大清洗，帶領蘇聯擊敗納粹德國。" },
  { id: "hitler", name: "希特勒", englishName: "Adolf Hitler", iso: "DEU", born: 1889, died: 1945, role: "納粹德國元首", group: "modern", bio: "發動第二次世界大戰與猶太人大屠殺，戰敗前自殺。" },
  { id: "gandhi", name: "甘地", englishName: "Mahatma Gandhi", iso: "IND", born: 1869, died: 1948, role: "印度獨立運動領袖", group: "modern", bio: "以非暴力不合作運動爭取印度獨立，影響全球民權運動。" },
  { id: "mlk", name: "馬丁・路德・金恩", englishName: "Martin Luther King Jr.", iso: "USA", born: 1929, died: 1968, role: "民權運動領袖", group: "modern", bio: "受甘地啟發推動美國非裔民權運動，發表〈我有一個夢〉演說。" },
  { id: "mandela", name: "曼德拉", englishName: "Nelson Mandela", iso: "ZAF", born: 1918, died: 2013, role: "南非總統", group: "modern", bio: "反種族隔離鬥士，入獄 27 年後成為南非首位黑人總統。" },
];

export const relations: Relation[] = [
  // 古希臘
  { source: "socrates", target: "plato", type: "師徒", label: "蘇格拉底教導柏拉圖" },
  { source: "plato", target: "aristotle", type: "師徒", label: "亞里斯多德在雅典學院求學二十年" },
  { source: "aristotle", target: "alexander", type: "師徒", label: "受腓力二世之聘教導少年亞歷山大" },
  { source: "philip2", target: "alexander", type: "親屬", label: "父子" },
  { source: "alexander", target: "darius3", type: "敵對", label: "伊蘇斯與高加米拉戰役" },

  // 羅馬
  { source: "caesar", target: "pompey", type: "盟友", label: "前三頭同盟（後反目內戰）" },
  { source: "caesar", target: "crassus", type: "盟友", label: "前三頭同盟" },
  { source: "pompey", target: "crassus", type: "盟友", label: "前三頭同盟" },
  { source: "caesar", target: "brutus", type: "敵對", label: "布魯圖斯參與刺殺凱撒" },
  { source: "caesar", target: "augustus", type: "親屬", label: "凱撒在遺囑中收屋大維為養子" },
  { source: "caesar", target: "cleopatra", type: "戀人", label: "育有一子凱撒里昂" },
  { source: "antony", target: "cleopatra", type: "戀人", label: "政治與愛情同盟" },
  { source: "augustus", target: "antony", type: "敵對", label: "亞克興海戰" },
  { source: "caesar", target: "antony", type: "君臣", label: "安東尼是凱撒的得力部將" },
  { source: "augustus", target: "brutus", type: "敵對", label: "腓立比戰役擊敗刺殺者" },

  // 先秦秦漢
  { source: "laozi", target: "confucius", type: "影響", label: "相傳孔子曾向老子問禮" },
  { source: "confucius", target: "mencius", type: "影響", label: "孟子私淑孔子，發揚儒學" },
  { source: "xunzi", target: "hanfei", type: "師徒", label: "韓非師從荀子" },
  { source: "xunzi", target: "lisi", type: "師徒", label: "李斯師從荀子" },
  { source: "lisi", target: "hanfei", type: "敵對", label: "同門相忌，李斯陷害韓非" },
  { source: "qinshihuang", target: "lisi", type: "君臣", label: "李斯任丞相" },
  { source: "hanfei", target: "qinshihuang", type: "影響", label: "秦王讀韓非著作大為讚嘆" },
  { source: "xiangyu", target: "liubang", type: "敵對", label: "楚漢相爭、鴻門宴" },
  { source: "liubang", target: "hanxin", type: "君臣", label: "拜韓信為大將" },
  { source: "liubang", target: "zhangliang", type: "君臣", label: "張良為首席謀士" },
  { source: "xiangyu", target: "hanxin", type: "敵對", label: "韓信曾為項羽部下，後於垓下圍困項羽" },
  { source: "xiangyu", target: "qinshihuang", type: "敵對", label: "項羽見始皇出巡曰「彼可取而代也」" },

  // 三國
  { source: "liubei", target: "zhugeliang", type: "君臣", label: "三顧茅廬" },
  { source: "liubei", target: "guanyu", type: "盟友", label: "桃園結義（演義）／情同兄弟" },
  { source: "caocao", target: "liubei", type: "敵對", label: "青梅煮酒論英雄，後成死敵" },
  { source: "sunquan", target: "liubei", type: "盟友", label: "孫劉聯盟抗曹，並有姻親" },
  { source: "sunquan", target: "zhouyu", type: "君臣", label: "周瑜為東吳大都督" },
  { source: "zhouyu", target: "caocao", type: "敵對", label: "赤壁之戰" },
  { source: "zhugeliang", target: "simayi", type: "敵對", label: "北伐交鋒" },
  { source: "caocao", target: "simayi", type: "君臣", label: "司馬懿出仕曹操" },
  { source: "sunquan", target: "guanyu", type: "敵對", label: "東吳奪荊州，關羽遇害" },
  { source: "caocao", target: "guanyu", type: "敵對", label: "關羽曾短暫降曹，斬顏良後離去" },

  // 文藝復興
  { source: "verrocchio", target: "davinci", type: "師徒", label: "達文西在維洛及奧工作室當學徒" },
  { source: "lorenzo", target: "michelangelo", type: "君臣", label: "羅倫佐收留少年米開朗基羅" },
  { source: "lorenzo", target: "verrocchio", type: "君臣", label: "麥地奇家族贊助維洛及奧" },
  { source: "davinci", target: "michelangelo", type: "敵對", label: "著名的藝術競爭對手" },
  { source: "davinci", target: "raphael", type: "影響", label: "拉斐爾深受達文西畫風影響" },
  { source: "julius2", target: "michelangelo", type: "君臣", label: "委託西斯汀禮拜堂天頂畫" },
  { source: "julius2", target: "raphael", type: "君臣", label: "委託梵蒂岡拉斐爾房間壁畫" },
  { source: "michelangelo", target: "raphael", type: "敵對", label: "在梵蒂岡同時期工作、互相較勁" },
  { source: "machiavelli", target: "lorenzo", type: "影響", label: "《君王論》獻給麥地奇家族" },

  // 戰國
  { source: "nobunaga", target: "hideyoshi", type: "君臣", label: "秀吉從草鞋取起步成為重臣" },
  { source: "nobunaga", target: "ieyasu", type: "盟友", label: "清洲同盟" },
  { source: "nobunaga", target: "mitsuhide", type: "敵對", label: "本能寺之變" },
  { source: "hideyoshi", target: "mitsuhide", type: "敵對", label: "山崎之戰為主君報仇" },
  { source: "hideyoshi", target: "ieyasu", type: "君臣", label: "家康臣服於秀吉，秀吉死後奪取天下" },
  { source: "hideyoshi", target: "yisunsin", type: "敵對", label: "壬辰倭亂" },
  { source: "shingen", target: "kenshin", type: "敵對", label: "川中島之戰" },
  { source: "shingen", target: "ieyasu", type: "敵對", label: "三方原之戰" },
  { source: "nobunaga", target: "shingen", type: "敵對", label: "西上作戰對峙" },

  // 科學
  { source: "copernicus", target: "galileo", type: "影響", label: "伽利略以觀測支持日心說" },
  { source: "copernicus", target: "kepler", type: "影響", label: "克卜勒是日心說的支持者" },
  { source: "tycho", target: "kepler", type: "師徒", label: "克卜勒擔任第谷的助手並繼承其資料" },
  { source: "galileo", target: "newton", type: "影響", label: "伽利略的運動研究為牛頓力學奠基" },
  { source: "kepler", target: "newton", type: "影響", label: "萬有引力解釋了克卜勒定律" },
  { source: "newton", target: "leibniz", type: "敵對", label: "微積分發明優先權之爭" },
  { source: "newton", target: "einstein", type: "影響", label: "相對論修正了牛頓力學" },
  { source: "darwin", target: "newton", type: "影響", label: "達爾文葬於西敏寺牛頓墓旁" },

  // 革命
  { source: "washington", target: "lafayette", type: "盟友", label: "獨立戰爭並肩作戰，情同父子" },
  { source: "washington", target: "jefferson", type: "君臣", label: "傑佛遜任華盛頓政府國務卿" },
  { source: "louis16", target: "marie", type: "親屬", label: "夫妻" },
  { source: "louis16", target: "washington", type: "盟友", label: "法國援助美國獨立戰爭" },
  { source: "robespierre", target: "louis16", type: "敵對", label: "力主處決國王" },
  { source: "lafayette", target: "louis16", type: "君臣", label: "國民衛隊司令，處境兩難" },
  { source: "napoleon", target: "wellington", type: "敵對", label: "滑鐵盧戰役" },
  { source: "napoleon", target: "alexander1", type: "敵對", label: "1812 年遠征俄國" },
  { source: "napoleon", target: "beethoven", type: "影響", label: "《英雄交響曲》題獻事件" },
  { source: "jefferson", target: "lafayette", type: "盟友", label: "傑佛遜駐法期間協助拉法葉草擬《人權宣言》" },

  // 二十世紀
  { source: "sunyatsen", target: "chiangkaishek", type: "君臣", label: "蔣中正任黃埔軍校校長" },
  { source: "chiangkaishek", target: "maozedong", type: "敵對", label: "國共內戰" },
  { source: "churchill", target: "fdr", type: "盟友", label: "《大西洋憲章》" },
  { source: "churchill", target: "stalin", type: "盟友", label: "雅爾達會議" },
  { source: "fdr", target: "stalin", type: "盟友", label: "雅爾達會議" },
  { source: "churchill", target: "hitler", type: "敵對", label: "不列顛空戰" },
  { source: "stalin", target: "hitler", type: "敵對", label: "德蘇戰爭" },
  { source: "fdr", target: "chiangkaishek", type: "盟友", label: "開羅會議" },
  { source: "churchill", target: "chiangkaishek", type: "盟友", label: "開羅會議" },
  { source: "gandhi", target: "mlk", type: "影響", label: "非暴力抗爭的啟發" },
  { source: "gandhi", target: "mandela", type: "影響", label: "甘地早年在南非從事民權運動" },
  { source: "churchill", target: "gandhi", type: "敵對", label: "邱吉爾強烈反對印度獨立" },
  { source: "einstein", target: "fdr", type: "影響", label: "愛因斯坦致信羅斯福，促成曼哈頓計畫" },
  { source: "einstein", target: "hitler", type: "敵對", label: "納粹上台後愛因斯坦流亡美國" },
];
