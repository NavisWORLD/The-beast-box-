'use client';
import { useEffect, useRef, useState } from 'react';
import PixelBeast from './pixel-beast';
import { useUniverseMotion } from './use-universe-motion';
import { buildCatalogCreatureRig, poseCatalogCreature } from '../lib/creature-catalog-3d.mjs';

type Props = {
  genome: any;
  stage?: number;
  emotion?: any;
  actorPoseRef?: React.MutableRefObject<any>;
  lookAtRef?: React.MutableRefObject<{ x: number; z: number } | null>;
  turntable?: boolean;
  turntableAngle?: number | null;
  speaking?: boolean;
  quality?: 'auto' | 'low';
  className?: string;
  label?: string;
};

/**
 * True 3D catalogue creature renderer (Three.js + Verlet secondary motion + elemental fluid particles).
 * Supports full 360° drag rotation or turntable presets, and falls back cleanly to PixelBeast if WebGL is unavailable.
 */
export default function Creature3DCanvas({
  genome,
  stage = 1,
  emotion = null,
  actorPoseRef,
  lookAtRef,
  turntable = false,
  turntableAngle = null,
  speaking = false,
  quality = 'auto',
  className = '',
  label = '3D catalogue creature',
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const emotionRef = useRef(emotion);
  emotionRef.current = emotion;
  const speakingRef = useRef(speaking);
  speakingRef.current = speaking;
  const rotRef = useRef({ turntable, angle: turntableAngle });
  rotRef.current = { turntable, angle: turntableAngle };
  const yawRef = useRef(0);
  const dragRef = useRef<{ x: number; yaw: number } | null>(null);
  const { reduced } = useUniverseMotion();
  const [ready, setReady] = useState(false);
  const [fallback, setFallback] = useState(false);

  useEffect(() => {
    const el = canvasRef.current;
    if (!el || !genome || fallback || typeof window === 'undefined' || typeof window.WebGLRenderingContext === 'undefined') {
      return;
    }
    let disposed = false;
    let raf = 0;
    let cleanup = () => {};

    void (async () => {
      try {
        const THREE = await import('three');
        if (disposed) return;
        const renderer = new THREE.WebGLRenderer({ canvas: el, alpha: true, antialias: quality !== 'low', powerPreference: 'low-power' });
        renderer.setPixelRatio(Math.min(quality === 'low' ? 1 : 1.5, window.devicePixelRatio || 1));
        renderer.outputColorSpace = THREE.SRGBColorSpace;

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 30);
        camera.position.set(0, 0.72, 2.55);
        camera.lookAt(0, 0.48, 0);

        scene.add(new THREE.AmbientLight(0xd8e8ff, 1.45));
        const key = new THREE.DirectionalLight(0xfff4e0, 1.55);
        key.position.set(1.8, 2.6, 2.8);
        scene.add(key);
        const rim = new THREE.PointLight(0x88e5ff, 8, 8);
        rim.position.set(-1.8, 1.2, -2.0);
        scene.add(rim);

        const rig = buildCatalogCreatureRig(THREE, genome, { stage, quality });
        scene.add(rig.root);

        const resize = () => {
          if (disposed) return;
          const r = el.getBoundingClientRect();
          const w = Math.max(1, Math.floor(r.width || 180));
          const h = Math.max(1, Math.floor(r.height || 180));
          renderer.setSize(w, h, false);
          camera.aspect = w / h;
          camera.updateProjectionMatrix();
        };
        resize();
        const ro = new ResizeObserver(resize);
        ro.observe(el);

        const onLost = (ev: Event) => {
          ev.preventDefault();
          cancelAnimationFrame(raf);
          if (!disposed) {
            setReady(false);
            setFallback(true);
          }
        };
        el.addEventListener('webglcontextlost', onLost);

        const onDown = (e: PointerEvent) => {
          dragRef.current = { x: e.clientX, yaw: yawRef.current };
        };
        const onMove = (e: PointerEvent) => {
          if (!dragRef.current) return;
          const w = el.getBoundingClientRect().width || 180;
          yawRef.current = dragRef.current.yaw + ((e.clientX - dragRef.current.x) / w) * Math.PI * 2;
        };
        const onUp = () => {
          dragRef.current = null;
        };
        el.addEventListener('pointerdown', onDown);
        window.addEventListener('pointermove', onMove);
        window.addEventListener('pointerup', onUp);

        let prev = performance.now();
        let time = 0;
        let rendered = false;

        const tick = (now: number) => {
          if (disposed) return;
          const dt = Math.min(0.05, Math.max(0.001, (now - prev) / 1000));
          prev = now;
          time += dt;

          const ap = actorPoseRef?.current || null;
          poseCatalogCreature(rig, {
            actorPose: ap,
            emotion: emotionRef.current,
            dt,
            time,
            lookAt: lookAtRef?.current || null,
            speaking: speakingRef.current,
            reduced,
          });

          if (!dragRef.current) {
            if (rotRef.current.turntable && !reduced) {
              yawRef.current = (yawRef.current + dt * 0.85) % (Math.PI * 2);
            } else if (typeof rotRef.current.angle === 'number') {
              yawRef.current = (rotRef.current.angle * Math.PI) / 180;
            } else if (ap && typeof ap.heading === 'number') {
              yawRef.current = ap.heading * 0.35;
            }
          }
          rig.root.rotation.y = yawRef.current;

          try {
            renderer.render(scene, camera);
            if (!rendered) {
              rendered = true;
              setReady(true);
            }
          } catch {
            cancelAnimationFrame(raf);
            if (!disposed) {
              setReady(false);
              setFallback(true);
            }
            return;
          }

          if (!reduced || dragRef.current) {
            raf = requestAnimationFrame(tick);
          }
        };

        raf = requestAnimationFrame(tick);
        cleanup = () => {
          cancelAnimationFrame(raf);
          ro.disconnect();
          el.removeEventListener('webglcontextlost', onLost);
          el.removeEventListener('pointerdown', onDown);
          window.removeEventListener('pointermove', onMove);
          window.removeEventListener('pointerup', onUp);
          rig.dispose();
          renderer.dispose();
        };
      } catch {
        if (!disposed) {
          setReady(false);
          setFallback(true);
        }
      }
    })();

    return () => {
      disposed = true;
      cleanup();
    };
  }, [genome?.seed, genome?.body, stage, quality, reduced, fallback]); // eslint-disable-line react-hooks/exhaustive-deps

  const dom = emotion?.dominant || 'curiosity';
  return (
    <div
      className={'creature-3d-canvas ' + className}
      data-creature-3d={ready && !fallback ? 'ready' : 'fallback'}
      data-creature-body={genome?.body || 'pup'}
      data-creature-island={genome?.island || 'Eridoria Prime'}
      aria-label={label}
      style={{ position: 'relative', width: '100%', height: '100%' }}
    >
      {!fallback ? (
        <canvas
          ref={canvasRef}
          aria-hidden="true"
          style={{
            width: '100%',
            height: '100%',
            display: 'block',
            opacity: ready ? 1 : 0,
            transition: 'opacity 180ms ease',
          }}
        />
      ) : null}
      {(!ready || fallback) && genome ? (
        <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
          <PixelBeast
            genome={genome}
            stage={stage}
            publicSpark
            pose={dom === 'fear' ? 'emote' : dom === 'joy' || dom === 'mischief' ? 'react' : 'idle'}
            emote={dom === 'fear' ? 'sleep' : dom === 'joy' ? 'spark' : 'watch'}
            label={label}
          />
        </div>
      ) : null}
    </div>
  );
}
