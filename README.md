# Timelore

互動式世界歷史學習網站：轉動 3D 地球、點選國家，閱讀重大歷史時間線、美食、宗教與語言，並探索歷史人物關係圖與歷史建築 3D 模型。

## 功能

- **3D 地球**：拖曳旋轉、滾輪／雙指縮放、自動旋轉；國家標籤與歷史建築光點；洲別快速前往、隨機探索、探索進度
- **國家面板**：時間線（可依類別篩選）、美食、宗教比例圖、語言（瀏覽器語音朗讀問候語）、建築、人物、小測驗
- **人物關係圖**：73 位人物、87 條關係，可依時代與關係類型篩選、搜尋與聚焦
- **建築 3D**：10 座以 Blender 自製的 low-poly 立體模型
- **全站搜尋**：`Ctrl / ⌘ + K`

## 技術

React 19 · TypeScript · Vite · Tailwind CSS 4 · GSAP · globe.gl · react-force-graph-2d · React Three Fiber · Lucide icons

## 開發

```bash
npm install
npm run dev
```

```bash
npm run build
```

## 重新產生 3D 模型

模型由 `blender/` 中的 Python 腳本以 Blender（bpy）程式化建模並輸出 GLB 到 `public/models/`。

```bash
python -m venv .venv && .venv/bin/pip install bpy==5.3.0
```

```bash
.venv/bin/python blender/build.py
```

指定模型或輸出預覽圖：

```bash
.venv/bin/python blender/build.py eiffel taj-mahal --preview previews
```

## 資料

國家、人物與建築資料位於 `src/data/`，皆為繁體中文。
