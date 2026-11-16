import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import Globe, { type GlobeInstance } from "globe.gl";
import { geoContains } from "d3-geo";
import { AdditiveBlending, BufferAttribute, BufferGeometry, Color, Mesh, MeshPhongMaterial, PerspectiveCamera, Points, PointsMaterial, ShaderMaterial, SphereGeometry, SRGBColorSpace, type Texture, TextureLoader } from "three";
import { CSS2DRenderer } from "three/examples/jsm/renderers/CSS2DRenderer.js";
import { countries, countryByIso } from "../../data/world";

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
const SHORT: Record<string, string> = {
  ARE: "阿聯", ATG: "安地卡", TTO: "千里達", COD: "剛果（金）", CAF: "中非",
  BIH: "波赫", KNA: "聖克里斯多福", VCT: "聖文森", STP: "聖多美", PNG: "巴紐",
};

const defaultAlt = () => (window.innerWidth < 640 ? 3.6 : window.innerWidth < 1024 ? 2.9 : 2.45);

const GlobeView = forwardRef<GlobeHandle, Props>(function GlobeView(
  { selectedIso, autoRotate, onSelectCountry, onReady },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeInstance | null>(null);
  const features = useRef<GeoFeature[]>([]);
  const selectedRef = useRef<string | null>(selectedIso);
  const labelEls = useRef(new Map<string, HTMLDivElement>());
  /** 每個標籤在地球上的單位方向向量（建立時算一次，之後每格只做內積） */
  const labelVecs = useRef(new Map<HTMLDivElement, { x: number; y: number; z: number }>());
  /** 標籤的經緯度、人口排名與寬度，供避讓計算 */
  const labelPos = useRef<{ div: HTMLDivElement; lat: number; lng: number; rank: number; w: number }[]>([]);


  const cb = useRef({ onSelectCountry, onReady });
  cb.current = { onSelectCountry, onReady };



  useImperativeHandle(ref, () => ({
    flyTo: (lat, lng, altitude = 1.7) => globeRef.current?.pointOfView({ lat, lng, altitude }, 900),
    zoom: (factor) => {
      const g = globeRef.current;
      if (!g) return;
      const pov = g.pointOfView();
      g.pointOfView({ altitude: Math.min(4.5, Math.max(0.5, pov.altitude * factor)) }, 450);
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
      .bumpImageUrl("/textures/earth-topology.png")
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
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 150;
    controls.maxDistance = 650;


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
      const r = Math.sqrt(1 - u * u) * 1800;
      starPos.set([r * Math.cos(t), u * 1800, r * Math.sin(t)], i * 3);
    }
    const starGeo = new BufferGeometry();
    starGeo.setAttribute("position", new BufferAttribute(starPos, 3));
    const stars = new Points(starGeo, new PointsMaterial({ color: "#ffffff", size: 1.6, sizeAttenuation: false, transparent: true, opacity: 0.75, depthWrite: false }));
    g.scene().add(stars);
    const cam = g.camera() as PerspectiveCamera;
    cam.far = Math.max(cam.far, 4000);
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
    // 標籤避讓：國名互相重疊時只顯示人口較多的國家。以地表上的經緯度距離計算，
    // 只隨縮放改變、旋轉時完全不變，國名不會轉一轉就忽然出現或消失
    const shown = new Set<HTMLDivElement>();
    let frame = 0;
    let scale = 1;
    let lastD = 0;
    let lastSel: string | null = null;
    let measured = false;
    // 標籤離地平線（地球邊緣）的相對距離：0 = 剛好在邊緣、1 = 正對鏡頭；放大縮小都一致
    const margin = (dot: number, horizon: number) => (dot - horizon) / (1 - horizon);
    const declutter = (d: number) => {
      const R = g.getGlobeRadius();
      const cam = g.camera() as PerspectiveCamera;
      // 地球正中央每弧度約佔多少螢幕像素
      const pxPerRad = (R * el.clientHeight) / 2 / Math.tan((cam.fov * Math.PI) / 360) / (d - R);
      const items = [...labelPos.current].sort((a, b) =>
        a.div.classList.contains("is-active") ? -1 : b.div.classList.contains("is-active") ? 1 : a.rank - b.rank,
      );
      const placed: typeof items = [];
      shown.clear();
      measured = items.length > 0; // 標籤尚未建立時下次再算
      for (const it of items) {
        it.w ||= it.div.offsetWidth;
        if (!it.w) measured = false;
        const hit = placed.some((o) => {
          const dx = Math.abs(((((it.lng - o.lng + 540) % 360) - 180) * Math.PI) / 180) * Math.cos((it.lat * Math.PI) / 180) * pxPerRad;
          const dy = (Math.abs(it.lat - o.lat) * Math.PI * pxPerRad) / 180;
          return dx < (((it.w || 60) + (o.w || 60)) / 2) * scale * 1.35 + 10 && dy < 30 * scale;
        });
        if (hit) continue;
        placed.push(it);
        shown.add(it.div);
      }
    };
    const tick = () => {
      if (clouds) clouds.rotation.y += 0.00025;
      const cam = g.camera().position;
      const d = cam.length();
      const horizon = g.getGlobeRadius() / d;
      // 放大時國名跟著變大（最多 1.35 倍），近看比較好讀
      const s = Math.min(1.35, Math.max(1, 1 + (2.45 - (d / g.getGlobeRadius() - 1)) * 0.18));
      if (Math.abs(s - scale) > 0.01) el.style.setProperty("--label-scale", String((scale = s)));
      // 縮放超過 3% 才重新計算（標籤寬度還沒量到時每 10 格重試）
      if (Math.abs(d - lastD) / d > 0.03 || (!measured && frame % 10 === 0) || lastSel !== selectedRef.current) {
        lastSel = selectedRef.current;
        declutter((lastD = d));
      }
      frame++;
      labelVecs.current.forEach((u, div) => {
        const dot = (u.x * cam.x + u.y * cam.y + u.z * cam.z) / d;
        const o = shown.has(div) ? Math.min(1, Math.max(0, (margin(dot, horizon) - 0.4) / 0.15)) : 0;
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
        div.style.opacity = "0";
        div.style.zIndex = String(2000 - c.rank);
        div.dataset.rank = String(c.rank);
        const p = g.getCoords(c.pos[0], c.pos[1], 0);
        const len = Math.hypot(p.x, p.y, p.z) || 1;
        labelVecs.current.set(div, { x: p.x / len, y: p.y / len, z: p.z / len });
        labelPos.current.push({ div, lat: c.pos[0], lng: c.pos[1], rank: c.rank, w: 0 });
        div.textContent = SHORT[c.iso] ?? c.zh;
        div.title = c.en;
        if (c.iso === selectedRef.current) div.classList.add("is-active");
        labelEls.current.set(c.iso, div);
        return div;
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    if (g) g.controls().autoRotate = autoRotate;
  }, [autoRotate]);

  return <div ref={containerRef} className="absolute inset-0 cursor-grab active:cursor-grabbing" />;
});

export default GlobeView;
