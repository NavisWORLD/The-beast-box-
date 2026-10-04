'use client';
import { useEffect, useRef } from 'react';

export default function WeightGrid({ weights, steps }: { weights: number[][] | undefined; steps: number }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const node = canvas.current;
    const ctx = node?.getContext('2d');
    if (!node || !ctx) return;
    const grid = weights && weights.length === 16 ? weights : Array.from({ length: 16 }, () => Array(16).fill(0));
    ctx.clearRect(0, 0, node.width, node.height);
    const cell = node.width / 16;
    for (let y = 0; y < 16; y++) {
      for (let x = 0; x < 16; x++) {
        const value = Math.max(-4, Math.min(4, Number(grid[y]?.[x]) || 0));
        const mag = Math.abs(value) / 4;
        ctx.fillStyle = value >= 0 ? `rgba(104,229,238,${0.12 + mag * 0.88})` : `rgba(172,140,255,${0.12 + mag * 0.88})`;
        ctx.fillRect(x * cell + 1, y * cell + 1, cell - 2, cell - 2);
      }
    }
  }, [weights, steps]);
  return <canvas ref={canvas} width={160} height={160} role="img" aria-label={`Hebbian weight matrix after ${steps} learning steps. This is pattern memory, not a conscious model.`} style={{ width: 160, height: 160, imageRendering: 'pixelated', borderRadius: 12 }} />;
}
