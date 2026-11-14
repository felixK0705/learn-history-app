import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import Globe, { type GlobeInstance } from "globe.gl";
import { countries, countryByIso } from "../../data/countries";
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

const defaultAlt = () => (window.innerWidth < 640 ? 3.6 : window.innerWidth < 1024 ? 2.8 : 2.3);

const GlobeView = forwardRef<GlobeHandle, Props>(function GlobeView(
  { selectedIso, visited, autoRotate, showLandmarks, onSelectCountry, onHoverCountry, onSelectBuilding, onReady },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const globeRef = useRef<GlobeInstance | null>(null);
  const hoverRef = useRef<GeoFeature | null>(null);
  const selectedRef = useRef<string | null>(selectedIso);
  const labelEls = useRef(new Map<string, HTMLDivElement>());

  // 用 ref 保存最新的 callback，避免重新建立地球
  const cb = useRef({ onSelectCountry, onHoverCountry, onSelectBuilding, onReady });
  cb.current = { onSelectCountry, onHoverCountry, onSelectBuilding, onReady };

  useImperativeHandle(ref, () => ({
    flyTo: (lat, lng, altitude = 1.7) => globeRef.current?.pointOfView({ lat, lng, altitude }, 1400),
    zoom: (factor) => {
      const g = globeRef.current;
      if (!g) return;
      const pov = g.pointOfView();
      g.pointOfView({ altitude: Math.min(4.5, Math.max(0.6, pov.altitude * factor)) }, 450);
    },
    reset: () => globeRef.current?.pointOfView({ lat: 15, lng: 20, altitude: defaultAlt() }, 1200),
  }));

  // 初始化
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    let disposed = false;

    const capColor = (f: object) => {
      const feat = f as GeoFeature;
      const iso = feat.properties.iso_a3;
      const has = countryByIso.has(iso);
      if (iso === selectedRef.current) return "rgba(92, 200, 255, 0.55)";
      if (feat === hoverRef.current) return has ? "rgba(92, 200, 255, 0.38)" : "rgba(255,255,255,0.12)";
      return has ? "rgba(92, 200, 255, 0.10)" : "rgba(0,0,0,0)";
    };

    const g = new Globe(el, { rendererConfig: { antialias: true, alpha: true } })
      .backgroundColor("rgba(0,0,0,0)")
      .globeImageUrl("/textures/earth_daymap.jpg")
      .showAtmosphere(true)
      .atmosphereColor("#7cc7ff")
      .atmosphereAltitude(0.22)
      .polygonAltitude((f) => ((f as GeoFeature).properties.iso_a3 === selectedRef.current ? 0.02 : 0.006))
      .polygonCapColor(capColor)
      .polygonSideColor(() => "rgba(92, 200, 255, 0.15)")
      .polygonStrokeColor((f) =>
        countryByIso.has((f as GeoFeature).properties.iso_a3) ? "rgba(190, 235, 255, 0.55)" : "rgba(255,255,255,0.12)",
      )
      .polygonsTransitionDuration(250)
      .onPolygonHover((f) => {
        hoverRef.current = (f as GeoFeature) ?? null;
        el.style.cursor = f ? "pointer" : "grab";
        g.polygonCapColor(capColor);
        cb.current.onHoverCountry(f ? (f as GeoFeature).properties.name : null);
      })
      .onPolygonClick((f) => {
        const iso = (f as GeoFeature).properties.iso_a3;
        cb.current.onSelectCountry(iso);
      })
      .htmlTransitionDuration(0)
      .htmlElementVisibilityModifier((elem, visible) => {
        elem.style.opacity = visible ? "1" : "0";
        elem.style.pointerEvents = visible ? "auto" : "none";
      })
      .onGlobeReady(() => cb.current.onReady?.());

    g.pointOfView({ lat: 15, lng: 20, altitude: defaultAlt() });

    const renderer = g.renderer();
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    const controls = g.controls();
    controls.autoRotateSpeed = 0.35;
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 160;
    controls.maxDistance = 650;

    // 讓地球稍微變亮、更有光澤
    const mat = g.globeMaterial() as unknown as { shininess?: number };
    if ("shininess" in mat) mat.shininess = 12;

    globeRef.current = g;

    fetch("/data/countries.json")
      .then((r) => r.json())
      .then((geo: { features: GeoFeature[] }) => {
        if (disposed) return;
        g.polygonsData(geo.features.filter((f) => f.properties.iso_a3 !== "ATA"));
      })
      .catch(() => {});

    const ro = new ResizeObserver(() => {
      g.width(el.clientWidth);
      g.height(el.clientHeight);
    });
    ro.observe(el);

    return () => {
      disposed = true;
      ro.disconnect();
      g._destructor?.();
      el.replaceChildren();
      globeRef.current = null;
    };
  }, []);

  // HTML 標籤（國家 + 地標）
  useEffect(() => {
    const g = globeRef.current;
    if (!g) return;
    type Marker = { kind: "country"; iso: string; lat: number; lng: number } | { kind: "building"; b: Building; lat: number; lng: number };
    const markers: Marker[] = countries.map((c) => ({ kind: "country", iso: c.iso, lat: c.labelPos[0], lng: c.labelPos[1] }));
    if (showLandmarks) {
      buildings.forEach((b) => markers.push({ kind: "building", b, lat: b.position[0], lng: b.position[1] }));
    }
    labelEls.current.clear();
    g.htmlElementsData(markers)
      .htmlLat("lat")
      .htmlLng("lng")
      .htmlAltitude((m) => ((m as Marker).kind === "country" ? 0.025 : 0.012))
      .htmlElement((m) => {
        const marker = m as Marker;
        const div = document.createElement("div");
        if (marker.kind === "country") {
          const c = countryByIso.get(marker.iso)!;
          div.className = "country-label";
          const dot = document.createElement("span");
          dot.className = "dot";
          div.append(dot, c.name);
          div.title = c.englishName;
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
  }, [showLandmarks]);

  // 標籤狀態（已探索 / 選取中）
  useEffect(() => {
    labelEls.current.forEach((div, iso) => {
      div.classList.toggle("visited", visited.includes(iso));
      div.classList.toggle("is-active", iso === selectedIso);
    });
  }, [visited, selectedIso, showLandmarks]);

  // 選取國家時更新多邊形
  useEffect(() => {
    selectedRef.current = selectedIso;
    const g = globeRef.current;
    if (!g) return;
    g.polygonCapColor(g.polygonCapColor());
    g.polygonAltitude(g.polygonAltitude());
  }, [selectedIso]);

  useEffect(() => {
    const g = globeRef.current;
    if (g) g.controls().autoRotate = autoRotate;
  }, [autoRotate]);

  return <div ref={containerRef} className="absolute inset-0 cursor-grab active:cursor-grabbing" />;
});

export default GlobeView;
