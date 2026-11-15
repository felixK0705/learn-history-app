import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import Globe, { type GlobeInstance } from "globe.gl";
import { AdditiveBlending, Color, Mesh, MeshPhongMaterial, ShaderMaterial, SphereGeometry, TextureLoader } from "three";
import { CSS2DRenderer } from "three/examples/jsm/renderers/CSS2DRenderer.js";
import { countries, countryByIso } from "../../data/world";
import { buildings, type Building } from "../../data/buildings";

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
  visited: string[];
  autoRotate: boolean;
  showLandmarks: boolean;
  onSelectCountry: (iso: string) => void;
  onHoverCountry: (name: string | null) => void;
  onSelectBuilding: (b: Building) => void;
  onReady?: () => void;
}

// 關閉 CSS2DRenderer 依距離每格重排標籤疊放順序（重疊標籤會前後跳動，看起來像在閃），改由人口排名固定順序
Object.defineProperty(CSS2DRenderer.prototype, "sortObjects", { get: () => false, set: () => {}, configurable: true });

const defaultAlt = () => (window.innerWidth < 640 ? 3.6 : window.innerWidth < 1024 ? 2.9 : 2.45);

/** 依鏡頭高度決定顯示多少國家標籤（依人口排序），避免畫面雜亂 */


const GlobeView = forwardRef<GlobeHandle, Props>(function GlobeView(
  { selectedIso, visited, autoRotate, showLandmarks, onSelectCountry, onHoverCountry, onSelectBuilding, onReady },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeInstance | null>(null);
  const hoverRef = useRef<GeoFeature | null>(null);
  const selectedRef = useRef<string | null>(selectedIso);
  const labelEls = useRef(new Map<string, HTMLDivElement>());
  /** 每個標籤在地球上的單位方向向量（建立時算一次，之後每格只做內積） */
  const labelVecs = useRef(new Map<HTMLDivElement, { x: number; y: number; z: number }>());


  const cb = useRef({ onSelectCountry, onHoverCountry, onSelectBuilding, onReady });
  cb.current = { onSelectCountry, onHoverCountry, onSelectBuilding, onReady };



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

    const capColor = (f: object) => {
      const feat = f as GeoFeature;
      if (feat.properties.iso_a3 === selectedRef.current) return "rgba(255, 255, 255, 0.36)";
      if (feat === hoverRef.current) return "rgba(255, 255, 255, 0.22)";
      return "rgba(0,0,0,0)";
    };

    const g = new Globe(el, { rendererConfig: { antialias: true, alpha: true } })
      .backgroundColor("rgba(0,0,0,0)")
      .globeImageUrl("/textures/earth-painted.jpg")
      .bumpImageUrl("/textures/earth-topology.png")
      .showAtmosphere(true)
      .atmosphereColor("#e2f8ff")
      .atmosphereAltitude(0.3)
      .polygonAltitude((f) => ((f as GeoFeature).properties.iso_a3 === selectedRef.current ? 0.018 : 0.005))
      .polygonCapColor(capColor)
      .polygonSideColor(() => "rgba(255, 255, 255, 0.06)")
      // 國界線：清楚可見的白色細線，選取的國家更亮
      .polygonStrokeColor((f) => ((f as GeoFeature).properties.iso_a3 === selectedRef.current ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.55)"))
      .polygonsTransitionDuration(0)
      .onPolygonHover((f) => {
        hoverRef.current = (f as GeoFeature) ?? null;
        el.style.cursor = f ? "pointer" : "grab";
        g.polygonCapColor(capColor);
        const iso = f ? (f as GeoFeature).properties.iso_a3 : null;
        cb.current.onHoverCountry(iso ? countryByIso.get(iso)?.zh ?? (f as GeoFeature).properties.name : null);
      })
      .onPolygonClick((f) => cb.current.onSelectCountry((f as GeoFeature).properties.iso_a3))
      .htmlTransitionDuration(0)
      // 可見度由下方的逐格淡入淡出計算接管，避免標籤在球體邊緣反覆閃爍
      .htmlElementVisibilityModifier(() => {})
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
    const tick = () => {
      if (clouds) clouds.rotation.y += 0.00025;
      const cam = g.camera().position;
      const d = cam.length();
      const horizon = g.getGlobeRadius() / d;
      labelVecs.current.forEach((u, div) => {
        const dot = (u.x * cam.x + u.y * cam.y + u.z * cam.z) / d;
        const o = Math.min(1, Math.max(0, (dot - horizon - 0.1) / 0.15));
        const v = o.toFixed(2);
        if (div.style.opacity !== v) {
          div.style.opacity = v;
          div.style.pointerEvents = o > 0.5 ? "" : "none";
        }
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    fetch("/data/countries.json")
      .then((r) => r.json())
      .then((geo: { features: GeoFeature[] }) => {
        if (!disposed) g.polygonsData(geo.features.filter((f) => f.properties.iso_a3 !== "ATA"));
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

  // HTML 標籤（國家＋地標）
  useEffect(() => {
    const g = globeRef.current;
    if (!g) return;
    type Marker = { kind: "country"; iso: string; lat: number; lng: number } | { kind: "building"; b: Building; lat: number; lng: number };
    const markers: Marker[] = countries.map((c) => ({ kind: "country", iso: c.iso, lat: c.pos[0], lng: c.pos[1] }));
    if (showLandmarks) buildings.forEach((b) => markers.push({ kind: "building", b, lat: b.position[0], lng: b.position[1] }));
    labelEls.current.clear();
    labelVecs.current.clear();
    g.htmlElementsData(markers)
      .htmlLat("lat")
      .htmlLng("lng")
      .htmlAltitude((m) => ((m as Marker).kind === "country" ? 0.02 : 0.012))
      .htmlElement((m) => {
        const marker = m as Marker;
        const div = document.createElement("div");
        div.style.opacity = "0";
        const p = g.getCoords(marker.lat, marker.lng, 0);
        const len = Math.hypot(p.x, p.y, p.z) || 1;
        labelVecs.current.set(div, { x: p.x / len, y: p.y / len, z: p.z / len });
        if (marker.kind === "country") {
          const c = countryByIso.get(marker.iso)!;
          div.className = "country-label";
          const dot = document.createElement("span");
          dot.className = "dot";
          div.append(dot, c.zh);
          div.title = c.en;
          // globe.gl 會延遲建立元素，建立當下就套用縮放層級的顯示規則
          div.style.zIndex = String(2000 - c.rank);
          if (c.iso === selectedRef.current) div.classList.add("is-active");
          div.onclick = (e) => {
            e.stopPropagation();
            cb.current.onSelectCountry(c.iso);
          };
          labelEls.current.set(c.iso, div);
        } else {
          // 建築標記：建築圖示＋名稱，一看就知道是可點開的 3D 建築
          div.className = "landmark-pin";
          div.innerHTML =
            '<svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 22h18M6 18v-7M10 18v-7M14 18v-7M18 18v-7M12 2l8 5H4z"/></svg>';
          div.append(marker.b.name);
          div.title = `${marker.b.name}（點擊觀看 3D 模型）`;
          div.setAttribute("aria-label", marker.b.name);
          div.onclick = (e) => {
            e.stopPropagation();
            cb.current.onSelectBuilding(marker.b);
          };
        }
        return div;
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showLandmarks]);

  useEffect(() => {
    labelEls.current.forEach((div, iso) => {
      div.classList.toggle("visited", visited.includes(iso));
      div.classList.toggle("is-active", iso === selectedIso);
      // 選取的國家疊在最上層
      div.style.zIndex = iso === selectedIso ? "3000" : String(2000 - (countryByIso.get(iso)?.rank ?? 999));
    });
  }, [visited, selectedIso, showLandmarks]);

  useEffect(() => {
    selectedRef.current = selectedIso;
    const g = globeRef.current;
    if (!g) return;
    g.polygonCapColor(g.polygonCapColor());
    g.polygonStrokeColor(g.polygonStrokeColor());
    g.polygonAltitude(g.polygonAltitude());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIso]);

  useEffect(() => {
    const g = globeRef.current;
    if (g) g.controls().autoRotate = autoRotate;
  }, [autoRotate]);

  return <div ref={containerRef} className="absolute inset-0 cursor-grab active:cursor-grabbing" />;
});

export default GlobeView;
