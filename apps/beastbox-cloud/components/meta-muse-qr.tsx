'use client';
import { useMemo } from 'react';
import { encode } from 'uqr';

/** Client-side QR code rendered as SVG rects (no innerHTML, no network). */
export default function MetaMuseQr({ value, label, size = 196 }: { value: string; label: string; size?: number }) {
  const qr = useMemo(() => encode(value, { ecc: 'M', border: 2 }), [value]);
  const path = useMemo(() => {
    let d = '';
    qr.data.forEach((row, y) => row.forEach((on, x) => { if (on) d += `M${x} ${y}h1v1h-1z`; }));
    return d;
  }, [qr]);
  return <svg role="img" aria-label={label} width={size} height={size} viewBox={`0 0 ${qr.size} ${qr.size}`} shapeRendering="crispEdges" style={{ background: '#fff', borderRadius: 10, display: 'block' }} data-meta-muse-qr="true">
    <path d={path} fill="#080b17" />
  </svg>;
}
