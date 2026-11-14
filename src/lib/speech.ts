// 以瀏覽器內建語音朗讀問候語
const langCodes: [RegExp, string][] = [
  [/台語|臺語|閩南/, "nan-TW"],
  [/客家/, "hak-TW"],
  [/粵/, "zh-HK"],
  [/華語|中文|漢語|普通話|國語/, "zh-TW"],
  [/日/, "ja-JP"],
  [/韓/, "ko-KR"],
  [/印地/, "hi-IN"],
  [/泰/, "th-TH"],
  [/越南/, "vi-VN"],
  [/高棉/, "km-KH"],
  [/印尼/, "id-ID"],
  [/土耳其/, "tr-TR"],
  [/波斯/, "fa-IR"],
  [/阿拉伯/, "ar-SA"],
  [/蒙古/, "mn-MN"],
  [/英/, "en-GB"],
  [/法/, "fr-FR"],
  [/德/, "de-DE"],
  [/義大利/, "it-IT"],
  [/希臘/, "el-GR"],
  [/西班牙/, "es-ES"],
  [/加泰隆尼亞/, "ca-ES"],
  [/俄/, "ru-RU"],
  [/葡萄牙/, "pt-BR"],
  [/阿姆哈拉/, "am-ET"],
  [/南非荷蘭|阿非利卡/, "af-ZA"],
  [/祖魯/, "zu-ZA"],
  [/坦米爾/, "ta-IN"],
  [/孟加拉/, "bn-IN"],
];

export function langCodeFor(name: string): string | null {
  for (const [re, code] of langCodes) if (re.test(name)) return code;
  return null;
}

export function canSpeak(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

export function speak(text: string, lang: string) {
  if (!canSpeak()) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang;
  u.rate = 0.9;
  const voice = window.speechSynthesis
    .getVoices()
    .find((v) => v.lang.toLowerCase().startsWith(lang.slice(0, 2).toLowerCase()));
  if (voice) u.voice = voice;
  window.speechSynthesis.speak(u);
}
