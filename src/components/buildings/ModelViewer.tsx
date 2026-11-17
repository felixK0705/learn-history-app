import { Component, Suspense, useEffect, useRef, useState, type ReactNode } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Environment, OrbitControls, useGLTF, useProgress } from "@react-three/drei";
import { Box3, DirectionalLight, Fog, MathUtils, PerspectiveCamera, Raycaster, Sphere, Vector3 } from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { useT } from "../../lib/i18n";

/** 依模型實際大小設定太陽光與陰影範圍（模型從百公尺到兩公里不等） */
function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  const sun = useRef<DirectionalLight>(null);
  useEffect(() => {
    scene.traverse((o) => {
      const mesh = o as unknown as { isMesh?: boolean; castShadow: boolean; receiveShadow: boolean };
      if (mesh.isMesh) {
        mesh.castShadow = true;
        mesh.receiveShadow = true;
      }
    });
    const light = sun.current;
    if (!light) return;
    const sphere = new Box3().setFromObject(scene).getBoundingSphere(new Sphere());
    const r = Math.max(sphere.radius, 1);
    light.position.copy(sphere.center).add(new Vector3(r * 0.7, r * 1.1, r * 0.5));
    light.target.position.copy(sphere.center);
    light.target.updateMatrixWorld();
    const cam = light.shadow.camera;
    cam.left = -r;
    cam.right = r;
    cam.top = r;
    cam.bottom = -r;
    cam.near = r * 0.1;
    cam.far = r * 4;
    cam.updateProjectionMatrix();
    light.shadow.bias = -0.0004;
    light.shadow.normalBias = r * 0.0008;
  }, [scene]);
  return (
    <>
      <primitive object={scene} />
      <directionalLight ref={sun} intensity={2.4} color="#fff4e2" castShadow shadow-mapSize={[4096, 4096]} />
    </>
  );
}

class ModelErrorBoundary extends Component<
  { children: ReactNode; resetKey: string; onError: () => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onError();
  }
  componentDidUpdate(prev: { resetKey: string }) {
    if (prev.resetKey !== this.props.resetKey && this.state.failed) this.setState({ failed: false });
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

export interface BuildingView {
  target: [number, number, number];
  position: [number, number, number];
  hfov: number;
}

/** 依實景照片的拍攝位置擺放相機（與 Blender 比對圖同一個視角），並限制可環視的範圍，避免看到地景邊緣 */
function ViewRig({ view, token, shift, controls }: { view: BuildingView; token: string; shift: number; controls: React.RefObject<OrbitControlsImpl | null> }) {
  const { camera, size, scene } = useThree();
  useEffect(() => {
    const cam = camera as PerspectiveCamera;
    const t = new Vector3(...view.target);
    const p = new Vector3(...view.position);
    const dist = p.distanceTo(t);
    const shiftW = size.width + Math.abs(shift) * 2;
    const aspect = shiftW / Math.max(size.height, 1);
    const h = MathUtils.degToRad(view.hfov);
    // Blender 以水平視角為準；網頁較窄時改以垂直方向保留同樣的畫面高度
    cam.fov = MathUtils.radToDeg(2 * Math.atan(Math.tan(h / 2) / Math.max(aspect, 1.5)));
    cam.near = Math.max(0.05, dist * 0.002);
    cam.far = dist * 20;
    // 往後退一些，讓建築完整入鏡；仰角至少 15°，一律從斜上方看，不從下往上看
    const dir = p.clone().sub(t).normalize();
    const minY = Math.sin(MathUtils.degToRad(15));
    if (dir.y < minY) {
      const flat = Math.hypot(dir.x, dir.z) || 1;
      const k = Math.cos(Math.asin(minY)) / flat;
      dir.set(dir.x * k, minY, dir.z * k);
    }
    cam.position.copy(t).addScaledVector(dir, dist * 1.25);
    // 桌機左側有建築清單，把畫面中心往右移，建築不會被清單遮住
    if (shift) cam.setViewOffset(shiftW, size.height, shift > 0 ? 0 : -shift * 2, 0, size.width, size.height);
    else cam.clearViewOffset();
    cam.updateProjectionMatrix();
    const c = controls.current;
    if (!c) return;
    c.target.copy(t);
    // 可 360 度環繞；可縮小到看見整個場景，但不能鑽到地面下
    c.minAzimuthAngle = -Infinity;
    c.maxAzimuthAngle = Infinity;
    c.minPolarAngle = 0.05;
    c.maxPolarAngle = MathUtils.degToRad(78);
    c.minDistance = dist * 0.15;
    c.maxDistance = dist * 4;
    // 遠處地景淡入天空色，縮小時不會看到地面邊緣的硬邊
    scene.fog = new Fog("#c9d5e2", dist * 6, dist * 16);
    c.update();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, shift, size.width, size.height]);
  return null;
}

/** 相機移動後往下打射線找地形高度，相機一律保持在地面（含山坡、建築）上方，不會鑽進地底 */
function GroundClamp({ token }: { token: string }) {
  const { camera, scene, controls } = useThree();
  const last = useRef(new Vector3(Infinity, 0, 0));
  const ray = useRef(new Raycaster());
  const down = useRef(new Vector3(0, -1, 0));
  useFrame(() => {
    const c = controls as unknown as OrbitControlsImpl | null;
    if (!c || camera.position.distanceToSquared(last.current) < 1e-6) return;
    const dist = camera.position.distanceTo(c.target);
    const from = camera.position.clone();
    from.y += dist * 4;
    ray.current.set(from, down.current);
    ray.current.far = dist * 8;
    const hit = ray.current.intersectObjects(scene.children, true).find((h) => (h.object as { isMesh?: boolean }).isMesh);
    const minY = hit ? hit.point.y + Math.max(dist * 0.06, 1) : -Infinity;
    if (camera.position.y < minY) {
      camera.position.y = minY;
      camera.lookAt(c.target);
    }
    last.current.copy(camera.position);
  });
  useEffect(() => {
    last.current.set(Infinity, 0, 0);
  }, [token]);
  return null;
}

/** Canvas 外的 DOM 載入進度與錯誤提示 */
function Overlay({ failed }: { failed: boolean }) {
  const { active, progress } = useProgress();
  const t = useT();
  if (failed)
    return (
      <div className="pointer-events-none absolute inset-0 grid place-items-center">
        <p className="w-60 text-center text-sm text-mute">{t({ "zh-TW": "模型載入失敗，請檢查網路連線後重新整理。", en: "Failed to load the model. Check your connection and reload.", ja: "モデルを読み込めませんでした。ネットワークを確認して再読み込みしてください。" })}</p>
      </div>
    );
  if (!active) return null;
  return (
    <div className="pointer-events-none absolute inset-0 grid place-items-center">
      <div className="flex w-44 flex-col items-center gap-2 text-mute">
        <div className="h-1 w-full overflow-hidden rounded-full bg-white/15">
          <div className="h-full bg-glow transition-[width]" style={{ width: `${progress}%` }} />
        </div>
        <span className="text-xs">{t({ "zh-TW": "模型載入中", en: "Loading model", ja: "モデルを読み込み中" })} {progress.toFixed(0)}%</span>
      </div>
    </div>
  );
}

export default function ModelViewer({
  url,
  view,
  shift = 0,
  autoRotate,
  resetToken,
}: {
  url: string;
  view: BuildingView;
  /** 畫面中心水平位移（像素，正值往右），避開側邊面板 */
  shift?: number;
  autoRotate: boolean;
  resetToken: number;
}) {
  const controls = useRef<OrbitControlsImpl>(null);
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  return (
    <>
    <Overlay failed={failedUrl === url} />
    <Canvas shadows dpr={[1, 2]} camera={{ position: [9, 7, 11], fov: 35, near: 0.5, far: 30000 }} gl={{ antialias: true, alpha: true }}>
      <Environment files="/hdri/sky.hdr" environmentIntensity={0.85} background />
      <hemisphereLight args={["#dff1ff", "#7a6a55", 0.35]} />

      <ModelErrorBoundary resetKey={url} onError={() => setFailedUrl(url)}>
      <Suspense fallback={null}>
        <Model key={url} url={url} />
        <ViewRig view={view} shift={shift} token={`${url}#${resetToken}`} controls={controls} />
        <GroundClamp token={`${url}#${resetToken}`} />
      </Suspense>
      </ModelErrorBoundary>

      <OrbitControls
        ref={controls}
        makeDefault
        autoRotate={autoRotate}
        autoRotateSpeed={0.4}
        enableDamping
      />
    </Canvas>
    </>
  );
}
