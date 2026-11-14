import { Component, Suspense, useEffect, useRef, useState, type ReactNode } from "react";
import { Canvas } from "@react-three/fiber";
import {
  Bounds,
  Center,
  ContactShadows,
  Environment,
  Lightformer,
  OrbitControls,
  useBounds,
  useGLTF,
  useProgress,
} from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";

function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  useEffect(() => {
    scene.traverse((o) => {
      const mesh = o as unknown as { isMesh?: boolean; castShadow: boolean; receiveShadow: boolean };
      if (mesh.isMesh) {
        mesh.castShadow = true;
        mesh.receiveShadow = true;
      }
    });
  }, [scene]);
  return <primitive object={scene} />;
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
    <Canvas shadows dpr={[1, 2]} camera={{ position: [9, 8, 11], fov: 40 }} gl={{ antialias: true, alpha: true }}>
      <ambientLight intensity={0.5} />
      <directionalLight position={[8, 12, 6]} intensity={2.2} castShadow shadow-mapSize={[1024, 1024]} />
      <directionalLight position={[-6, 4, -4]} intensity={0.6} color="#9cd7ff" />
      <Environment resolution={256}>
        <Lightformer form="rect" intensity={2} position={[0, 5, -9]} scale={[10, 5, 1]} />
        <Lightformer form="rect" intensity={1.2} color="#bde7ff" position={[-6, 2, 2]} rotation-y={Math.PI / 2} scale={[8, 4, 1]} />
        <Lightformer form="ring" intensity={1.5} position={[5, 5, 5]} scale={3} />
      </Environment>

      <ModelErrorBoundary resetKey={url} onError={() => setFailedUrl(url)}>
      <Suspense fallback={null}>
        <Bounds fit clip observe margin={1.1} maxDuration={0.8}>
          <Refit token={`${url}#${resetToken}`} />
          <Center top key={url}>
            <Model url={url} />
          </Center>
        </Bounds>
        <ContactShadows position={[0, 0, 0]} opacity={0.45} scale={40} blur={2.4} far={20} color="#021038" />
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
