'use client';
import { useEffect, useRef } from 'react';
import { eyesFor } from '../lib/companion/adventure.mjs';
import { renderSprite } from '../lib/companion/spark/render.mjs';

type Pose = 'idle' | 'walk' | 'follow' | 'react' | 'emote' | string;
type Genome = { seed?: string; facing?: string };

function paint(canvas: HTMLCanvasElement, genome: Genome, stage: number, eyes: string, facing: string, dx: number, dy: number, flash: number) {
  const drawn = renderSprite({ ...genome, facing }, Math.min(3, Math.max(1, stage)), { eyes });
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const blob = new ImageData(new Uint8ClampedArray(drawn.rgba), 64, 64);
  const scratch = document.createElement('canvas');
  scratch.width = 64;
  scratch.height = 64;
  scratch.getContext('2d')?.putImageData(blob, 0, 0);
  const scale = 4;
  ctx.drawImage(scratch, 16 + dx, 8 + dy, 64 * scale, 64 * scale);
  if (flash > 0) {
    ctx.fillStyle = `rgba(184, 238, 255, ${flash})`;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
}

export default function PixelBeast({
  genome, stage = 1, pose = 'idle', emote = 'watch', facing = 'right', reduced = false, label,
}: {
  genome: Genome | null;
  stage?: number;
  pose?: Pose;
  emote?: string;
  facing?: string;
  reduced?: boolean;
  label: string;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const genomeRef = useRef(genome);
  genomeRef.current = genome;
  useEffect(() => {
    const node = canvas.current;
    const current = genomeRef.current;
    if (!node || !current) return;
    const eyes = eyesFor({ emote, pose });
    if (reduced) {
      paint(node, current, stage, eyes, facing, 0, 0, 0);
      return;
    }
    let frame = 0;
    const tick = (now: number) => {
      const live = genomeRef.current;
      if (!live) return;
      const phase = now / 280;
      const walking = pose === 'walk' || pose === 'follow';
      const dx = walking ? Math.sin(phase) * 10 : pose === 'react' ? Math.sin(phase * 3) * 3 : 0;
      const dy = pose === 'idle' || pose === 'emote' ? Math.sin(phase) * 3 : walking ? Math.abs(Math.sin(phase * 2)) * -4 : 0;
      const flash = emote === 'evolve' ? (Math.sin(phase * 2) + 1) / 5 : 0;
      paint(node, live, stage, eyesFor({ emote, pose }), facing, dx, dy, flash);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [genome?.seed, stage, pose, emote, facing, reduced]);
  return <canvas ref={canvas} width={288} height={288} role="img" aria-label={label} style={{ width: '100%', height: 'auto', imageRendering: 'pixelated', background: 'transparent' }} />;
}
