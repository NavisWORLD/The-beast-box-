import { ImageResponse } from 'next/og';
export const size = { width: 180, height: 180 };
export const contentType = 'image/png';
export default function AppleIcon() {
  return new ImageResponse(
    <div style={{ width: '100%', height: '100%', background: '#080b19', borderRadius: 36, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ width: 130, height: 130, borderRadius: '50%', border: '8px solid #a98aff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#77e7ef', fontSize: 95, fontWeight: 800 }}>B</div>
    </div>,
    size
  );
}
