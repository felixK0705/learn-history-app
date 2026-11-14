import { Component, Suspense, useEffect, useRef, useState, type ReactNode } from "react";
import { Canvas } from "@react-three/fiber";
import { Bounds, Center, Environment, OrbitControls, useBounds, useGLTF, useProgress } from "@react-three/drei";
import { Box3, DirectionalLight, Sphere, Vector3 } from "three";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";

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

/** 切換模型或按重設時重新框選 */
function Refit({ token }: { token: string }) {
  const bounds = useBounds();
  useEffect(() => {
    const t = setTimeout(() => bounds.refresh().clip().fit(), 50);
    return () => clearTimeout(t);
  }, [token, bounds]);
  return null;
}

/** Canvas 外的 DOM 載入進度與錯誤提示 */
function Overlay({ failed }: { failed: boolean }) {
  const { active, progress } = useProgress();
  if (failed)
    return (
      <div className="pointer-events-none absolute inset-0 grid place-items-center">
        <p className="w-60 text-center text-sm text-mute">模型載入失敗，請檢查網路連線後重新整理。</p>
      </div>
    );
  if (!active) return null;
  return (
    <div className="pointer-events-none absolute inset-0 grid place-items-center">
      <div className="flex w-44 flex-col items-center gap-2 text-mute">
        <div className="h-1 w-full overflow-hidden rounded-full bg-white/15">
          <div className="h-full bg-glow transition-[width]" style={{ width: `${progress}%` }} />
        </div>
        <span className="text-xs">模型載入中 {progress.toFixed(0)}%</span>
      </div>
    </div>
  );
}

export default function ModelViewer({
  url,
  autoRotate,
  resetToken,
}: {
  url: string;
  autoRotate: boolean;
  resetToken: number;
}) {
  const controls = useRef<OrbitControlsImpl>(null);
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  return (
    <>
    <Overlay failed={failedUrl === url} />
    <Canvas shadows dpr={[1, 2]} camera={{ position: [9, 7, 11], fov: 35, near: 0.5, far: 30000 }} gl={{ antialias: true, alpha: true }}>
      <Environment files="/hdri/sky.hdr" environmentIntensity={0.85} />
      <hemisphereLight args={["#dff1ff", "#7a6a55", 0.35]} />

      <ModelErrorBoundary resetKey={url} onError={() => setFailedUrl(url)}>
      <Suspense fallback={null}>
        <Bounds fit clip observe margin={0.9} maxDuration={0.8}>
          <Refit token={`${url}#${resetToken}`} />
          <Center top key={url}>
            <Model url={url} />
          </Center>
        </Bounds>
      </Suspense>
      </ModelErrorBoundary>

      <OrbitControls
        ref={controls}
        makeDefault
        autoRotate={autoRotate}
        autoRotateSpeed={0.8}
        enableDamping
        minPolarAngle={0.1}
        maxPolarAngle={Math.PI / 2.05}
      />
    </Canvas>
    </>
  );
}
