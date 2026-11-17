import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import Globe, { type GlobeInstance } from "globe.gl";
import { geoArea, geoContains } from "d3-geo";
import { AdditiveBlending, BufferAttribute, BufferGeometry, Color, Mesh, MeshPhongMaterial, PerspectiveCamera, Points, PointsMaterial, ShaderMaterial, SphereGeometry, SRGBColorSpace, type Texture, TextureLoader } from "three";
import { CSS2DRenderer } from "three/examples/jsm/renderers/CSS2DRenderer.js";
import { countries, countryByIso, countryName } from "../../data/world";
import { getLang, useLang, type Lang } from "../../lib/i18n";

interface GeoFeature {
  type: string;
  properties: { name: string; iso_a3: string };
  geometry: unknown;
}

export interface GlobeHandle {
  flyTo: (lat: number, lng: number, altitude?: number) => void;
  zoom: (factor: number) => void;
  reset: () => void;
}

interface Props {
  selectedIso: string | null;
  autoRotate: boolean;
  onSelectCountry: (iso: string) => void;
  onReady?: () => void;
}

// 關閉 CSS2DRenderer 依距離每格重排標籤疊放順序（重疊標籤會前後跳動，看起來像在閃），改由人口排名固定順序
Object.defineProperty(CSS2DRenderer.prototype, "sortObjects", { get: () => false, set: () => {}, configurable: true });

/** 地球上空間有限，長國名用常見簡稱 */
const SHORT: Record<Lang, Record<string, string>> = {
  "zh-TW": {
    ARE: "阿聯", ATG: "安地卡", TTO: "千里達", COD: "剛果（金）", CAF: "中非",
    BIH: "波赫", KNA: "聖克里斯多福", VCT: "聖文森", STP: "聖多美", PNG: "巴紐",
  },
  en: {
    COD: "DR Congo", COG: "Congo", DOM: "Dominican Rep.", PNG: "Papua New Guinea", ARE: "UAE", BIH: "Bosnia",
    CAF: "C. African Rep.", TTO: "Trinidad", GNQ: "Eq. Guinea", STP: "São Tomé", ATG: "Antigua",
    KNA: "St. Kitts", VCT: "St. Vincent", FSM: "Micronesia", USA: "United States",
  },
  ja: {
    COD: "コンゴ民主", COG: "コンゴ", ARE: "UAE", BIH: "ボスニア", CAF: "中央アフリカ", TTO: "トリニダード",
    STP: "サントメ", ATG: "アンティグア", KNA: "セントクリストファー", VCT: "セントビンセント", FSM: "ミクロネシア",
    PNG: "パプアニューギニア", PSE: "パレスチナ",
  },
};
const labelText = (c: (typeof countries)[number], lang: Lang) => SHORT[lang][c.iso] ?? countryName(c, lang);

// 窄視角鏡頭（15°）從遠處看：透視變形小，旋轉時國名幾乎只水平移動、不會上下飄。
// 以下高度仍用原本 50° 視角時的數值設定，再換算成遠距離鏡頭的實際高度，畫面大小不變
const FOV = 15;
const K = Math.tan((25 * Math.PI) / 180) / Math.tan(((FOV / 2) * Math.PI) / 180);
const toAlt = (a: number) => (1 + a) * K - 1;
const fromAlt = (a: number) => (1 + a) / K - 1;

// d3 依環繞方向計算面積，方向相反時會得到「地球減去該國」的面積，取較小者
const sphereArea = (f: unknown) => {
  const a = geoArea(f as never);
  return Math.min(a, 4 * Math.PI - a);
};

const defaultAlt = () => toAlt(window.innerWidth < 640 ? 3.6 : window.innerWidth < 1024 ? 2.9 : 2.45);

const GlobeView = forwardRef<GlobeHandle, Props>(function GlobeView(
  { selectedIso, autoRotate, onSelectCountry, onReady },
  ref,
) {
  const lang = useLang();
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeInstance | null>(null);
  const features = useRef<GeoFeature[]>([]);
  const selectedRef = useRef<string | null>(selectedIso);
  const autoRotateRef = useRef(autoRotate);
  const labelEls = useRef(new Map<string, HTMLDivElement>());
  /** 每個標籤在地球上的單位方向向量（建立時算一次，之後每格只做內積） */
  const labelVecs = useRef(new Map<HTMLDivElement, { x: number; y: number; z: number }>());
  /** 標籤與所屬國家、人口排名，供避讓計算 */
  const labelPos = useRef<{ div: HTMLDivElement; iso: string; rank: number }[]>([]);
  /** 各國面積（球面度），國名避讓時面積大的國家優先顯示 */
  const areaByIso = useRef(new Map<string, number>());
  /** 可以用細線把國名拉到旁邊的小國：沒有國界形狀的島國、微型國家，以及面積很小的國家 */
  const leaderOk = useRef(new Set(countries.filter((c) => !c.shape).map((c) => c.iso)));


  const cb = useRef({ onSelectCountry, onReady });
  cb.current = { onSelectCountry, onReady };



  useImperativeHandle(ref, () => ({
    flyTo: (lat, lng, altitude = 1.7) => globeRef.current?.pointOfView({ lat, lng, altitude: toAlt(altitude) }, 900),
    zoom: (factor) => {
      const g = globeRef.current;
      if (!g) return;
      const pov = g.pointOfView();
      g.pointOfView({ altitude: toAlt(Math.min(4.5, Math.max(0.5, fromAlt(pov.altitude) * factor))) }, 450);
    },
    reset: () => globeRef.current?.pointOfView({ lat: 0, lng: 20, altitude: defaultAlt() }, 1200),
  }));

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    let disposed = false;

    const g = new Globe(el, { animateIn: false, rendererConfig: { antialias: true, alpha: true } })
      .backgroundColor("rgba(0,0,0,0)")
      // 國界已畫進貼圖（scripts/draw_borders.py），不再為每個國家建立 3D 物件，縮放旋轉才順
      .showAtmosphere(true)
      .atmosphereColor("#e2f8ff")
      .atmosphereAltitude(0.3)
      // 只有選取的國家才建立多邊形（亮色高光）
      .polygonAltitude(0.012)
      .polygonCapColor(() => "rgba(255, 255, 255, 0.32)")
      .polygonSideColor(() => "rgba(255, 255, 255, 0.08)")
      .polygonStrokeColor(() => "rgba(255,255,255,0.95)")
      .polygonsTransitionDuration(0)
      .onPolygonClick((f) => cb.current.onSelectCountry((f as GeoFeature).properties.iso_a3))
      // 點地球任一處：用經緯度找出所在國家
      .onGlobeClick(({ lat, lng }) => {
        const hit = features.current.find((f) => geoContains(f as never, [lng, lat]));
        if (hit) cb.current.onSelectCountry(hit.properties.iso_a3);
      })
      .htmlTransitionDuration(0);

    g.pointOfView({ lat: 0, lng: 20, altitude: defaultAlt() });
    g.renderer().setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    const controls = g.controls();
    controls.autoRotateSpeed = 0.35;
    // 套件依鏡頭高度調整拖曳／縮放速度；鏡頭拉遠後要換回等效高度，拖動手感才跟原本一樣
    // 自轉中若被拖斜（例如去看北極），放開 3 秒後慢慢轉回正對赤道：自轉時國名才只水平移動、不會上下飄
    let levelTimer = 0;
    controls.addEventListener("start", () => clearTimeout(levelTimer));
    controls.addEventListener("end", () => {
      clearTimeout(levelTimer);
      levelTimer = window.setTimeout(() => {
        const pov = g.pointOfView();
        if (!controls.autoRotate || Math.abs(pov.lat) <= 1) return;
        // 轉回期間先暫停自轉，避免與轉回動畫互相拉扯
        controls.autoRotate = false;
        g.pointOfView({ lat: 0, lng: pov.lng, altitude: pov.altitude }, 1500);
        levelTimer = window.setTimeout(() => (controls.autoRotate = autoRotateRef.current), 1600);
      }, 3000);
    });
    controls.addEventListener("change", () => {
      const a = fromAlt(g.pointOfView().altitude);
      controls.rotateSpeed = a * 0.3;
      controls.zoomSpeed = Math.sqrt(a) * 0.7;
    });
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 150 * K;
    controls.maxDistance = 650 * K;


    // 海面反光（依海洋遮罩）與緩慢轉動的雲層，呈現參考圖中光滑明亮的地球
    const loader = new TextureLoader();
    const mat = g.globeMaterial() as MeshPhongMaterial;
    let clouds: Mesh | null = null;

    // 玻璃珠般的邊緣反光（菲涅耳效果），重現參考圖地球亮白的外緣
    const rim = new Mesh(
      new SphereGeometry(g.getGlobeRadius() * 1.012, 96, 64),
      new ShaderMaterial({
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
        uniforms: { tint: { value: new Color("#bfeeff") } },
        vertexShader: `
          varying vec3 vN; varying vec3 vV;
          void main() {
            vec4 mv = modelViewMatrix * vec4(position, 1.0);
            vN = normalize(normalMatrix * normal);
            vV = normalize(-mv.xyz);
            gl_Position = projectionMatrix * mv;
          }`,
        fragmentShader: `
          uniform vec3 tint; varying vec3 vN; varying vec3 vV;
          void main() {
            float f = pow(1.0 - max(dot(vN, vV), 0.0), 3.2);
            gl_FragColor = vec4(tint * f * 1.25, f);
          }`,
      }),
    );
    // 背景星空放進 3D 場景：旋轉、拖動地球時星星跟著一起轉
    const starPos = new Float32Array(900 * 3);
    for (let i = 0; i < 900; i++) {
      const u = Math.random() * 2 - 1;
      const t = Math.random() * Math.PI * 2;
      const r = Math.sqrt(1 - u * u) * 12000;
      starPos.set([r * Math.cos(t), u * 12000, r * Math.sin(t)], i * 3);
    }
    const starGeo = new BufferGeometry();
    starGeo.setAttribute("position", new BufferAttribute(starPos, 3));
    const stars = new Points(starGeo, new PointsMaterial({ color: "#ffffff", size: 1.6, sizeAttenuation: false, transparent: true, opacity: 0.75, depthWrite: false }));
    g.scene().add(stars);
    const cam = g.camera() as PerspectiveCamera;
    cam.fov = FOV;
    // 鏡頭離地球至少 150*K，近裁切面設大一點，深度精度才夠分出地球與緊貼的雲層（否則出現細線閃爍）
    cam.near = 100;
    cam.far = 30000;
    cam.updateProjectionMatrix();

    // 地球、海面反光、雲層三張貼圖都載入完成後才一起顯示，避免先出現一顆空的玻璃球
    const load = (url: string) => new Promise<Texture>((ok, fail) => loader.load(url, ok, undefined, fail));
    Promise.all(["/textures/earth-map.jpg", "/textures/earth-water.png", "/textures/clouds-painted.png"].map(load)).then(([earth, water, cloud]) => {
      if (disposed) return;
      earth.colorSpace = cloud.colorSpace = SRGBColorSpace;
      earth.anisotropy = g.renderer().capabilities.getMaxAnisotropy();
      mat.map = earth;
      mat.color = new Color("#ffffff");
      mat.specularMap = water;
      mat.specular = new Color("#7fa6d6");
      mat.shininess = 18;
      mat.needsUpdate = true;
      clouds = new Mesh(
        new SphereGeometry(g.getGlobeRadius() * 1.006, 96, 64),
        new MeshPhongMaterial({ map: cloud, transparent: true, opacity: 0.45, depthWrite: false }),
      );
      g.scene().add(clouds, rim);
      cb.current.onReady?.();
    });

    globeRef.current = g;

    // 每格一次：雲層緩慢轉動＋標籤依與視線的夾角平滑淡出（背面隱藏，邊緣不會忽亮忽滅）
    let raf = 0;
    // 標籤避讓：每 6 格依國名在畫面上的實際位置檢查，重疊時保留面積較大的國家（選取的國家永遠優先）。
    // 鏡頭是遠距窄視角，旋轉時地球中間的國名幾乎是整體平移、相對位置不變，所以不會閃動
    const hidden = new Set<HTMLDivElement>();
    let frame = 0;
    let scale = 1;
    // 標籤離地平線（地球邊緣）的相對距離：0 = 剛好在邊緣、1 = 正對鏡頭；放大縮小都一致
    const margin = (dot: number, horizon: number) => (dot - horizon) / (1 - horizon);
    const priority = (it: { div: HTMLDivElement; iso: string; rank: number }) =>
      it.div.classList.contains("is-active") ? Infinity : (areaByIso.current.get(it.iso) ?? 0) - it.rank * 1e-9;
    // 國名放不下時依序改放在國家的上、下、右、左側，都放不下才隱藏
    const offset = new Map<HTMLDivElement, number>();
    const seen = new Set<HTMLDivElement>();
    const hiddenAt = new Map<HTMLDivElement, number>();
    // 以國名寬、高的倍數表示位移：正中、上、下、右、左
    const OFFSETS = [[0, 0], [0, -1], [0, 1], [0.5, 0], [-0.5, 0]];
    // 小島國、微型國家：上面都放不下時，把國名拉到旁邊空白處並以細線連回國家位置（8 個方向 × 2 種距離）
    const D = Math.SQRT1_2;
    const LEADERS = [26, 52, 84].flatMap((gap) => [[1, 0], [-1, 0], [D, -D], [D, D], [-D, -D], [-D, D], [0, -1], [0, 1]].map(([x, y]) => [x, y, gap]));
    const shift = (k: number, w: number, h: number) => {
      if (k < OFFSETS.length) return [OFFSETS[k][0] * (w + 12), OFFSETS[k][1] * h];
      const [ux, uy, gap] = LEADERS[k - OFFSETS.length];
      return [ux * (gap + w / 2), uy * (gap + h / 2)];
    };
    // 引線線段：國名框邊緣上最靠近國家位置的點 → 國家位置
    const leaderSeg = (b: number[], ax: number, ay: number) => [Math.min(Math.max(ax, b[0]), b[2]), Math.min(Math.max(ay, b[1]), b[3]), ax, ay];
    const crosses = (a: number[], b: number[]) => {
      const o = (px: number, py: number, qx: number, qy: number, rx: number, ry: number) => Math.sign((qx - px) * (ry - py) - (qy - py) * (rx - px));
      return o(a[0], a[1], a[2], a[3], b[0], b[1]) * o(a[0], a[1], a[2], a[3], b[2], b[3]) < 0 && o(b[0], b[1], b[2], b[3], a[0], a[1]) * o(b[0], b[1], b[2], b[3], a[2], a[3]) < 0;
    };
    const place = (div: HTMLDivElement, k: number, w: number, h: number) => {
      const [ox, oy] = shift(k, w, h);
      div.style.marginLeft = `${ox}px`;
      div.style.marginTop = `${oy}px`;
      const line = div.querySelector<HTMLElement>(".label-leader");
      if (!line) return;
      if (k < OFFSETS.length) {
        line.style.display = "none";
        return;
      }
      // 從國名框邊緣畫到國家位置（國名框內的座標）
      const ax = w / 2 - ox;
      const ay = h / 2 - oy;
      const ex = Math.min(Math.max(ax, 0), w);
      const ey = Math.min(Math.max(ay, 0), h);
      line.style.display = "block";
      line.style.left = `${ex}px`;
      line.style.top = `${ey}px`;
      line.style.width = `${Math.max(0, Math.hypot(ax - ex, ay - ey) - 1)}px`;
      line.style.transform = `rotate(${Math.atan2(ay - ey, ax - ex)}rad)`;
    };
    const declutter = (d: number, horizon: number) => {
      const cam = g.camera().position;
      const boxes: number[][] = [];
      // 已畫出的引線（畫面座標線段），新的引線不能與它們交叉、也不能穿過其他國名
      const lines: number[][] = [];
      // 地球在畫面上的圓：拉線的國名只能放在地球範圍內，不會飄到太空
      const rect = el.getBoundingClientRect();
      const gcx = rect.left + rect.width / 2;
      const gcy = rect.top + rect.height / 2;
      const gr = ((rect.height / 2) * (horizon / Math.sqrt(1 - horizon * horizon))) / Math.tan(((FOV / 2) * Math.PI) / 180) - 8;
      const inDisk = (x: number, y: number) => (x - gcx) ** 2 + (y - gcy) ** 2 < gr * gr;
      // 小國的實際位置（畫面座標）：任何國名都不能蓋住，否則看不出引線指向哪個島
      const anchors = new Map<HTMLDivElement, number[]>();
      for (const it of labelPos.current) {
        if (!leaderOk.current.has(it.iso)) continue;
        const u = labelVecs.current.get(it.div);
        if (!u || (u.x * cam.x + u.y * cam.y + u.z * cam.z) / d < horizon) continue;
        const r = it.div.getBoundingClientRect();
        const [px, py] = shift(offset.get(it.div) ?? 0, r.width, r.height);
        anchors.set(it.div, [r.left - px + r.width / 2, r.top - py + r.height / 2]);
      }
      const wasHidden = new Set(hidden);
      const now = performance.now();
      hidden.clear();
      for (const it of [...labelPos.current].sort((a, b) => priority(b) - priority(a))) {
        const u = labelVecs.current.get(it.div);
        // 已轉到地球邊緣外淡出的不算
        if (!u || margin((u.x * cam.x + u.y * cam.y + u.z * cam.z) / d, horizon) < 0.4) continue;
        const r = it.div.getBoundingClientRect();
        const prev = offset.get(it.div) ?? 0;
        const [px, py] = shift(prev, r.width, r.height);
        const bx = r.left - px;
        const by = r.top - py;
        // 緩衝：已顯示的國名要明顯疊進去才換位置或隱藏，已隱藏的要留出空隙才重新顯示，擦邊時不會來回閃
        const pad = wasHidden.has(it.div) ? 12 : 2;
        const free = (k: number) => {
          const [ox, oy] = shift(k, r.width, r.height);
          const b = [bx + ox, by + oy, bx + ox + r.width, by + oy + r.height];
          const p = k === prev ? pad : 6;
          if (boxes.some((o) => b[0] - p < o[2] && b[2] + p > o[0] && b[1] - p / 2 < o[3] && b[3] + p / 2 > o[1])) return null;
          for (const [div, [x, y]] of anchors) if (div !== it.div && x > b[0] - 4 && x < b[2] + 4 && y > b[1] - 3 && y < b[3] + 3) return null;
          if (k >= OFFSETS.length) {
            if (!inDisk(b[0], b[1]) || !inDisk(b[2], b[1]) || !inDisk(b[0], b[3]) || !inDisk(b[2], b[3])) return null;
            const seg = leaderSeg(b, bx + r.width / 2, by + r.height / 2);
            if (lines.some((l) => crosses(l, seg))) return null;
            for (let i = 1; i < 8; i++) {
              const x = seg[0] + ((seg[2] - seg[0]) * i) / 8;
              const y = seg[1] + ((seg[3] - seg[1]) * i) / 8;
              if (boxes.some((o) => x > o[0] - 5 && x < o[2] + 5 && y > o[1] - 4 && y < o[3] + 4)) return null;
            }
          }
          return b;
        };
        let pick = prev;
        let box = free(prev);
        // 只有原本隱藏的國名才換位置（淡入時直接出現在新位置）；正在顯示的國名被擋住就淡出，畫面上不會看到國名跳動
        // 換位置前至少要先隱藏 0.8 秒（淡出完成），否則看起來像國名在跳
        const settled = !seen.has(it.div) || (wasHidden.has(it.div) && now - (hiddenAt.get(it.div) ?? 0) > 800);
        const tries = OFFSETS.length + (leaderOk.current.has(it.iso) ? LEADERS.length : 0);
        if (settled) for (let k = 0; !box && k < tries; k++) if (k !== prev && (box = free(k))) pick = k;
        seen.add(it.div);
        if (!box) {
          if (!wasHidden.has(it.div)) hiddenAt.set(it.div, now);
          hidden.add(it.div);
          continue;
        }
        boxes.push(box);
        if (pick >= OFFSETS.length) lines.push(leaderSeg(box, bx + r.width / 2, by + r.height / 2));
        // 拉線的國名每次都重算（放大時字變大，線要跟著接到框邊）
        if (pick !== prev || pick >= OFFSETS.length) {
          offset.set(it.div, pick);
          place(it.div, pick, r.width, r.height);
        }
      }
    };
    const tick = () => {
      if (clouds) clouds.rotation.y += 0.00025;
      const cam = g.camera().position;
      const d = cam.length();
      const horizon = g.getGlobeRadius() / d;
      // 放大時國名跟著變大（最多 1.35 倍），近看比較好讀
      const s = Math.min(1.35, Math.max(1, 1 + (2.45 - fromAlt(d / g.getGlobeRadius() - 1)) * 0.18));
      if (Math.abs(s - scale) > 0.01) el.style.setProperty("--label-scale", String((scale = s)));
      if (frame++ % 6 === 0) declutter(d, horizon);
      labelVecs.current.forEach((u, div) => {
        const dot = (u.x * cam.x + u.y * cam.y + u.z * cam.z) / d;
        const o = hidden.has(div) ? 0 : Math.min(1, Math.max(0, (margin(dot, horizon) - 0.4) / 0.15));
        const v = o.toFixed(2);
        if (div.style.opacity !== v) div.style.opacity = v;
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    const showSelected = () => g.polygonsData(features.current.filter((f) => f.properties.iso_a3 === selectedRef.current));
    fetch("/data/countries.json")
      .then((r) => r.json())
      .then((geo: { features: GeoFeature[] }) => {
        if (disposed) return;
        features.current = geo.features.filter((f) => f.properties.iso_a3 !== "ATA");
        for (const f of features.current) areaByIso.current.set(f.properties.iso_a3, (areaByIso.current.get(f.properties.iso_a3) ?? 0) + sphereArea(f));
        // 約 1.2 萬平方公里以下（如千里達、黎巴嫩、盧森堡）
        areaByIso.current.forEach((a, iso) => a < 1.2e4 * ((4 * Math.PI) / 510e6) && leaderOk.current.add(iso));
        showSelected();
      })
      .catch(() => {});

    const ro = new ResizeObserver(() => {
      g.width(el.clientWidth);
      g.height(el.clientHeight);
    });
    ro.observe(el);

    return () => {
      disposed = true;
      clearTimeout(levelTimer);
      cancelAnimationFrame(raf);
      ro.disconnect();
      g._destructor?.();
      el.replaceChildren();
      globeRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 國家名稱標籤
  useEffect(() => {
    const g = globeRef.current;
    if (!g) return;
    labelEls.current.clear();
    labelVecs.current.clear();
    labelPos.current = [];
    g.htmlElementsData(countries)
      .htmlLat((d) => (d as (typeof countries)[number]).pos[0])
      .htmlLng((d) => (d as (typeof countries)[number]).pos[1])
      .htmlAltitude(0)
      .htmlElement((d) => {
        const c = d as (typeof countries)[number];
        const div = document.createElement("div");
        div.className = "country-label";
        // 文字與引線分開，換語言只改文字
        const text = document.createElement("span");
        const line = document.createElement("span");
        line.className = "label-leader";
        div.append(text, line);
        div.style.opacity = "0";
        div.style.zIndex = String(2000 - c.rank);
        div.dataset.rank = String(c.rank);
        const p = g.getCoords(c.pos[0], c.pos[1], 0);
        const len = Math.hypot(p.x, p.y, p.z) || 1;
        labelVecs.current.set(div, { x: p.x / len, y: p.y / len, z: p.z / len });
        labelPos.current.push({ div, iso: c.iso, rank: c.rank });
        text.textContent = labelText(c, getLang());
        div.title = c.en;
        if (c.iso === selectedRef.current) div.classList.add("is-active");
        labelEls.current.set(c.iso, div);
        return div;
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 切換語言時更新國名文字；寬度改變後由避讓重新判斷
  useEffect(() => {
    labelEls.current.forEach((div, iso) => {
      const c = countryByIso.get(iso);
      if (c) div.firstChild!.textContent = labelText(c, lang);
    });
  }, [lang]);

  useEffect(() => {
    labelEls.current.forEach((div, iso) => {
      div.classList.toggle("is-active", iso === selectedIso);
      // 選取的國家疊在最上層
      div.style.zIndex = iso === selectedIso ? "3000" : String(2000 - (countryByIso.get(iso)?.rank ?? 999));
    });
  }, [selectedIso]);

  useEffect(() => {
    const g = globeRef.current;
    // 關閉國家面板、恢復自轉時轉回正對赤道，自轉中國名只水平移動、不會上下飄
    if (g && selectedRef.current && !selectedIso) g.pointOfView({ lat: 0, lng: g.pointOfView().lng }, 1000);
    selectedRef.current = selectedIso;
    if (!g) return;
    g.polygonsData(features.current.filter((f) => f.properties.iso_a3 === selectedIso));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIso]);

  useEffect(() => {
    const g = globeRef.current;
    autoRotateRef.current = autoRotate;
    if (g) g.controls().autoRotate = autoRotate;
  }, [autoRotate]);

  return <div ref={containerRef} className="absolute inset-0 cursor-grab active:cursor-grabbing" />;
});

export default GlobeView;
