"""檢查翻譯檔與中文原檔結構一致：同樣的鍵、同樣長度的陣列、數字與不翻譯欄位不變，翻譯欄位不得殘留中文（英文版）或須含假名（日文版長句）。
用法：python3 scripts/check_i18n.py <zh.json> <譯文.json> <en|ja> [保留欄位,...]"""
import json, re, sys

HAN = re.compile(r"[一-鿿]")
KANA = re.compile(r"[぀-ヿ]")
zh_path, tr_path, lang = sys.argv[1:4]
keep = set(sys.argv[4].split(",")) if len(sys.argv) > 4 else set()
errors = []

def walk(a, b, path):
    if isinstance(a, dict):
        if not isinstance(b, dict) or set(a) != set(b):
            errors.append(f"{path}: 鍵不同 {sorted(set(a) ^ set(b if isinstance(b, dict) else {}))}")
            return
        for k in a:
            walk(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b):
            errors.append(f"{path}: 陣列長度不同")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]")
    elif isinstance(a, str):
        key = path.rsplit(".", 1)[-1].split("[")[0]
        if not isinstance(b, str):
            errors.append(f"{path}: 型別不同")
        elif key in keep:
            if a != b:
                errors.append(f"{path}: 不可翻譯的欄位被改動")
        elif HAN.search(a):
            if not b.strip():
                errors.append(f"{path}: 空字串")
            elif lang == "en" and HAN.search(b):
                errors.append(f"{path}: 英文版仍有中文：{b[:40]}")
            elif lang == "ja" and len(a) > 25 and not KANA.search(b):
                errors.append(f"{path}: 日文版沒有假名，可能沒翻：{b[:40]}")
    elif a != b:
        errors.append(f"{path}: 數值被改動")

walk(json.load(open(zh_path)), json.load(open(tr_path)), "")
print("\n".join(errors[:30]) if errors else "OK")
sys.exit(1 if errors else 0)
