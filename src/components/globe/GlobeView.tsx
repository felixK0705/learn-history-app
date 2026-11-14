import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import Globe, { type GlobeInstance } from "globe.gl";
import { AdditiveBlending, Color, Mesh, MeshPhongMaterial, ShaderMaterial, SphereGeometry, TextureLoader } from "three";
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

const defaultAlt = () => (window.innerWidth < 640 ? 3.6 : window.innerWidth < 1024 ? 2.9 : 2.45);

/** 依鏡頭高度決定顯示多少國家標籤（依人口排序），避免畫面雜亂 */
const labelLimit = (alt: number) => (alt > 2.2 ? 0 : alt > 1.6 ? 25 : alt > 1.2 ? 70 : alt > 0.9 ? 140 : 999);

const GlobeView = forwardRef<GlobeHandle, Props>(function GlobeView(
  { selectedIso, visited, autoRotate, showLandmarks, onSelectCountry, onHoverCountry, onSelectBuilding, onReady },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeInstance | null>(null);
  const hoverRef = useRef<GeoFeature | null>(null);
  const selectedRef = useRef<string | null>(selectedIso);
  const labelEls = useRef(new Map<string, HTMLDivElement>());
  const limitRef = useRef(labelLimit(defaultAlt()));

  const cb = useRef({ onSelectCountry, onHoverCountry, onSelectBuilding, onReady });
  cb.current = { onSelectCountry, onHoverCountry, onSelectBuilding, onReady };

  const applyLabelVisibility = () => {
    const limit = limitRef.current;
    labelEls.current.forEach((div, iso) => {
      const c = countryByIso.get(iso);
      const show = !!c && (c.rank < limit || iso === selectedRef.current);
      div.classList.toggle("zoom-hidden", !show);
    });
  };

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
      .polygonStrokeColor((f) => ((f as GeoFeature).properties.iso_a3 === selectedRef.current ? "rgba(255,255,255,0.7)" : "rgba(0,0,0,0)"))
      .polygonsTransitionDuration(250)
      .onPolygonHover((f) => {
        hoverRef.current = (f as GeoFeature) ?? null;
        el.style.cursor = f ? "pointer" : "grab";
        g.polygonCapColor(capColor);
        const iso = f ? (f as GeoFeature).properties.iso_a3 : null;
        cb.current.onHoverCountry(iso ? countryByIso.get(iso)?.zh ?? (f as GeoFeature).properties.name : null);
      })
      .onPolygonClick((f) => cb.current.onSelectCountry((f as GeoFeature).properties.iso_a3))
      .htmlTransitionDuration(0)
      .htmlElementVisibilityModifier((elem, visible) => {
        elem.style.opacity = visible ? "" : "0";
        elem.style.pointerEvents = visible ? "" : "none";
      })
      .onGlobeReady(() => cb.current.onReady?.());

    g.pointOfView({ lat: 15, lng: 20, altitude: defaultAlt() });
    g.renderer().setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    const controls = g.controls();
    controls.autoRotateSpeed = 0.35;
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 150;
    controls.maxDistance = 650;
    controls.addEventListener("change", () => {
      const limit = labelLimit(g.pointOfView().altitude);
      if (limit !== limitRef.current) {
        limitRef.current = limit;
        applyLabelVisibility();
      }
    });

    // 海面反光（依海洋遮罩）與緩慢轉動的雲層，呈現參考圖中光滑明亮的地球
    const loader = new TextureLoader();
    const mat = g.globeMaterial() as MeshPhongMaterial;
    loader.load("/textures/earth-water.png", (tex) => {
      mat.specularMap = tex;
      mat.specular = new Color("#a9d8ff");
      mat.shininess = 18;
      mat.needsUpdate = true;
    });
    let raf = 0;
    loader.load("/textures/clouds-painted.png", (tex) => {
      if (disposed) return;
      const clouds = new Mesh(
        new SphereGeometry(g.getGlobeRadius() * 1.006, 96, 64),
        new MeshPhongMaterial({ map: tex, transparent: true, opacity: 0.72, depthWrite: false }),
      );
      g.scene().add(clouds);
      const spin = () => {
        clouds.rotation.y += 0.00025;
        raf = requestAnimationFrame(spin);
      };
      spin();
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
    g.htmlElementsData(markers)
      .htmlLat("lat")
      .htmlLng("lng")
      .htmlAltitude((m) => ((m as Marker).kind === "country" ? 0.02 : 0.012))
      .htmlElement((m) => {
        const marker = m as Marker;
        const div = document.createElement("div");
        if (marker.kind === "country") {
          const c = countryByIso.get(marker.iso)!;
          div.className = "country-label";
          const dot = document.createElement("span");
          dot.className = "dot";
          div.append(dot, c.zh);
          div.title = c.en;
          // globe.gl 會延遲建立元素，建立當下就套用縮放層級的顯示規則
          if (!(c.rank < limitRef.current || c.iso === selectedRef.current)) div.classList.add("zoom-hidden");
          if (c.iso === selectedRef.current) div.classList.add("is-active");
          div.onclick = (e) => {
            e.stopPropagation();
            cb.current.onSelectCountry(c.iso);
          };
          labelEls.current.set(c.iso, div);
        } else {
          div.className = "landmark-pin";
          div.title = marker.b.name;
          div.setAttribute("aria-label", marker.b.name);
          div.onclick = (e) => {
            e.stopPropagation();
            cb.current.onSelectBuilding(marker.b);
          };
        }
        return div;
      });
    applyLabelVisibility();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showLandmarks]);

  useEffect(() => {
    labelEls.current.forEach((div, iso) => {
      div.classList.toggle("visited", visited.includes(iso));
      div.classList.toggle("is-active", iso === selectedIso);
    });
  }, [visited, selectedIso, showLandmarks]);

  useEffect(() => {
    selectedRef.current = selectedIso;
    applyLabelVisibility();
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
