import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import Globe, { type GlobeInstance } from "globe.gl";
import { geoContains } from "d3-geo";
import { AdditiveBlending, Color, Mesh, MeshPhongMaterial, ShaderMaterial, SphereGeometry, TextureLoader, Vector3 } from "three";
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


  const cb = useRef({ onSelectCountry, onReady });
  cb.current = { onSelectCountry, onReady };



  useImperativeHandle(ref, () => ({
    flyTo: (lat, lng, altitude = 1.7) => globeRef.current?.pointOfView({ lat, lng, altitude }, 1400),
    zoom: (factor) => {
      const g = globeRef.current;
      if (!g) return;
      const pov = g.pointOfView();
      g.pointOfView({ altitude: Math.min(4.5, Math.max(0.5, pov.altitude * factor)) }, 450);
    },
    reset: () => globeRef.current?.pointOfView({ lat: 15, lng: 20, altitude: defaultAlt() }, 1200),
  }));

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    let disposed = false;

    const g = new Globe(el, { rendererConfig: { antialias: true, alpha: true } })
      .backgroundColor("rgba(0,0,0,0)")
      // 國界已畫進貼圖（scripts/draw_borders.py），不再為每個國家建立 3D 物件，縮放旋轉才順
      .globeImageUrl("/textures/earth-map.jpg")
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
      .htmlTransitionDuration(0)
      .onGlobeReady(() => cb.current.onReady?.());

    g.pointOfView({ lat: 15, lng: 20, altitude: defaultAlt() });
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
    loader.load("/textures/earth-water.png", (tex) => {
      mat.specularMap = tex;
      mat.specular = new Color("#7fa6d6");
      mat.shininess = 18;
      mat.needsUpdate = true;
    });
    let clouds: Mesh | null = null;
    loader.load("/textures/clouds-painted.png", (tex) => {
      if (disposed) return;
      clouds = new Mesh(
        new SphereGeometry(g.getGlobeRadius() * 1.006, 96, 64),
        new MeshPhongMaterial({ map: tex, transparent: true, opacity: 0.72, depthWrite: false }),
      );
      g.scene().add(clouds);
    });

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
    g.scene().add(rim);

    globeRef.current = g;

    // 每格一次：雲層緩慢轉動＋標籤依與視線的夾角平滑淡出（背面隱藏，邊緣不會忽亮忽滅）
    let raf = 0;
    // 標籤避讓：互相重疊時只顯示人口較多的國家（放大後空間變大，就會出現更多國名）
    // 每 10 格重算一次；已顯示的標籤有優先權，避免來回切換
    const shown = new Set<HTMLDivElement>();
    const widths = new Map<HTMLDivElement, number>();
    const v3 = new Vector3();
    let frame = 0;
    let scale = 1;
    // 標籤離地平線（地球邊緣）的相對距離：0 = 剛好在邊緣、1 = 正對鏡頭；放大縮小都一致
    const margin = (dot: number, horizon: number) => (dot - horizon) / (1 - horizon);
    const declutter = (cam: Vector3, horizon: number, d: number) => {
      const w = el.clientWidth;
      const h = el.clientHeight;
      const R = g.getGlobeRadius() * 1.02;
      const items: { div: HTMLDivElement; x: number; y: number; w: number; pri: number }[] = [];
      labelVecs.current.forEach((u, div) => {
        if (margin((u.x * cam.x + u.y * cam.y + u.z * cam.z) / d, horizon) < 0.12) return;
        v3.set(u.x * R, u.y * R, u.z * R).project(g.camera());
        let bw = widths.get(div);
        if (!bw) widths.set(div, (bw = div.offsetWidth || 60));
        const rank = Number(div.dataset.rank);
        const pri = div.classList.contains("is-active") ? -1e4 : rank - (shown.has(div) ? 40 : 0);
        items.push({ div, x: (v3.x + 1) * w * 0.5, y: (1 - v3.y) * h * 0.5, w: bw * scale, pri });
      });
      items.sort((a, b) => a.pri - b.pri);
      const boxes: number[][] = [];
      shown.clear();
      for (const it of items) {
        const b = [it.x - it.w / 2 - 6, it.y - 10 * scale, it.x + it.w / 2 + 6, it.y + 10 * scale];
        if (boxes.some((o) => b[0] < o[2] && b[2] > o[0] && b[1] < o[3] && b[3] > o[1])) continue;
        boxes.push(b);
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
      if (frame++ % 10 === 0) declutter(cam, horizon, d);
      labelVecs.current.forEach((u, div) => {
        const dot = (u.x * cam.x + u.y * cam.y + u.z * cam.z) / d;
        const o = shown.has(div) ? Math.min(1, Math.max(0, (margin(dot, horizon) - 0.12) / 0.15)) : 0;
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
    g.htmlElementsData(countries)
      .htmlLat((d) => (d as (typeof countries)[number]).pos[0])
      .htmlLng((d) => (d as (typeof countries)[number]).pos[1])
      .htmlAltitude(0.02)
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
    selectedRef.current = selectedIso;
    const g = globeRef.current;
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
