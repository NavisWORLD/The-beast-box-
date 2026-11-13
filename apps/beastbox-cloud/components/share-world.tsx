'use client';
// "Share my world with Zeref": ONE site-wide share session, mounted in the app
// shell so it survives navigation. The switch is persisted; the shared stream
// is owned by lib/environment/share-stream (never by a page), analysed on this
// device into numbers (field perception + the face channel), and the little
// selfie preview stays pinned here so the keeper always sees what Zeref sees.
// Raw video and audio never leave the device; a reload may still need one tap
// to resume (browser law), and the card says so when that is the case.
import { useEffect, useRef, useState } from 'react';
import { analyzeFrame, experience, notice, LOG_KEY } from '../lib/companion/field-perception.mjs';
import { faceProxies } from '../lib/companion/face-channel.mjs';
import { FacePulse } from '../lib/bio/face-pulse.mjs';
import { buildFaceEstimates } from '../lib/bio/face-estimates.mjs';
import { readSharePref, shareStream, writeSharePref, type ShareFacing, type ShareState } from '../lib/environment/share-stream';

const W = 32, H = 24, MAX_LOG = 300;
function readLog(): any[] { try { const v = JSON.parse(localStorage.getItem(LOG_KEY) || '[]'); return Array.isArray(v) ? v.slice(-MAX_LOG) : []; } catch { return []; } }

export default function ShareWorld() {
  const [state, setState] = useState<ShareState>('off');
  const [facing, setFacing] = useState<ShareFacing>('user');
  const [line, setLine] = useState('');
  const [estLine, setEstLine] = useState('');
  const pip = useRef<HTMLDivElement | null>(null);
  const scratch = useRef<HTMLCanvasElement | null>(null);
  const gray = useRef<Float32Array | null>(null);
  const prev = useRef<any>(null);
  const prevEye = useRef<number | null>(null);
  const pulse = useRef<FacePulse | null>(null);
  const lastLog = useRef(0);

  useEffect(() => {
    const pref = readSharePref();
    shareStream.facing = pref.facing;
    setFacing(pref.facing);
    const unsub = shareStream.subscribe(s => setState(s));
    if (pref.on) void shareStream.resume();
    const kill = () => { shareStream.stop(); writeSharePref({ on: false, facing: shareStream.facing }); };
    window.addEventListener('beastbox:master-privacy-stop', kill);
    return () => { unsub(); window.removeEventListener('beastbox:master-privacy-stop', kill); };
  }, []);

  // Pin the shared preview while live: the keeper sees exactly what Zeref sees.
  useEffect(() => {
    if (state === 'live' && pip.current && shareStream.video) {
      const v = shareStream.video;
      v.style.width = '96px'; v.style.height = '72px'; v.style.borderRadius = '8px'; v.style.background = '#000';
      v.style.transform = shareStream.facing === 'user' ? 'scaleX(-1)' : '';
      if (v.parentNode !== pip.current) pip.current.appendChild(v);
    }
  }, [state, facing]);

  // The sampling loops: perception twice a second, the face channel ten times
  // a second (the pulse estimate needs the denser green series). Numbers only.
  useEffect(() => {
    if (state !== 'live') return;
    if (!scratch.current) { const c = document.createElement('canvas'); c.width = W; c.height = H; scratch.current = c; }
    if (!pulse.current) pulse.current = new FacePulse();
    const g = scratch.current.getContext('2d', { willReadFrequently: true });
    if (!g) return;
    const sampleFrame = () => {
      const v = shareStream.video;
      if (!v || !v.videoWidth) return null;
      g.drawImage(v, 0, 0, W, H);
      return g.getImageData(0, 0, W, H).data;
    };
    const faceTick = window.setInterval(() => {
      if (shareStream.facing !== 'user') return;
      const data = sampleFrame(); if (!data) return;
      const fp = faceProxies(data, W, H, prevEye.current);
      prevEye.current = fp.eye;
      if (fp.facePresent && fp.faceGreen > 0) pulse.current?.push(performance.now(), fp.faceGreen);
    }, 100);
    const tick = window.setInterval(() => {
      const data = sampleFrame();
      const heard = shareStream.measureSound();
      if (!data && !heard) return;
      const f = data ? analyzeFrame(data, gray.current, W, H) : null;
      if (f) gray.current = f.gray;
      const fp = data && shareStream.facing === 'user' ? faceProxies(data, W, H, prevEye.current) : null;
      const cur: any = { brightness: f?.brightness, hue: f?.hue, motion: f?.motion, gazeX: f?.gazeX, gazeY: f?.gazeY };
      if (heard) { cur.loudness = heard.loudness; cur.pitchHz = heard.pitchHz; }
      if (fp) { cur.facePresent = fp.facePresent; cur.faceScale = fp.faceScale; cur.faceX = fp.faceX; cur.faceY = fp.faceY; cur.faceBlink = fp.faceBlink; }
      const n = notice(cur, prev.current); prev.current = cur;
      const now = Date.now();
      if ((n || now - lastLog.current > 20000) && f) {
        lastLog.current = now;
        const record = experience(cur, now) as {loudness?: number; pitchHz?: number};
        if (!heard) { delete record.loudness; delete record.pitchHz; }
        const log = [...readLog(), record].slice(-MAX_LOG);
        try { localStorage.setItem(LOG_KEY, JSON.stringify(log)); } catch { /* full/blocked: sharing still works */ }
      }
      const est = buildFaceEstimates({ face: fp ? { facePresent: fp.facePresent, faceScale: fp.faceScale, faceX: fp.faceX, faceY: fp.faceY, faceBlink: fp.faceBlink } : undefined, pulse: pulse.current?.estimate() || null });
      const soundLine = heard ? `sound ${heard.loudness}` : 'sound absent';
      setLine(`light ${f ? cur.brightness : 'absent'} · motion ${f ? cur.motion : 'absent'} · ${soundLine}${fp ? ` · face ${fp.facePresent ? 'present' : 'not seen'} (estimate)` : ''}`);
      setEstLine(est.pulse ? `pulse ≈ ${est.pulse.bpm} bpm (estimate, face channel)` : '');
    }, 500);
    return () => { window.clearInterval(faceTick); window.clearInterval(tick); };
  }, [state]);

  async function toggle() {
    if (state === 'live') { shareStream.stop(); writeSharePref({ on: false, facing: shareStream.facing }); return; }
    writeSharePref({ on: true, facing });
    await shareStream.start(facing);
    if (shareStream.state !== 'live') writeSharePref({ on: true, facing }); // the wish stays saved; the state line says why it is not live yet
  }
  async function flip() {
    const next: ShareFacing = facing === 'user' ? 'environment' : 'user';
    setFacing(next); shareStream.facing = next;
    writeSharePref({ on: state === 'live', facing: next });
    if (state === 'live') await shareStream.start(next);
  }

  const status = state === 'live' ? 'Sharing is on. Zeref reads this room as numbers only; no images or audio leave this device.'
    : state === 'resume' ? 'Sharing was on. Your browser needs one tap after a reload to let the camera back in.'
    : state === 'denied' ? 'Camera permission was not given, so sharing is off.'
    : state === 'unavailable' ? 'This browser cannot share a camera here (needs a secure page).'
    : 'Off. Turn it on once and it stays on across the whole site.';
  return <aside id="share-world-card" data-share-world data-share-state={state} style={{ position: 'fixed', left: 10, bottom: 10, zIndex: 40, maxWidth: 240, padding: 10, border: '1px solid #3b3f78', borderRadius: 12, background: 'rgba(13,18,48,.92)', color: '#e8ecff', font: '12px system-ui', pointerEvents: 'none' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, pointerEvents: 'auto' }}>
      <button type="button" role="switch" aria-checked={state === 'live'} data-share-toggle onClick={() => void toggle()}>{state === 'live' ? 'Sharing ✓' : 'Share my world with Zeref'}</button>
      {state === 'live' ? <button type="button" data-share-flip onClick={() => void flip()} title="Flip camera">🔄 {facing === 'user' ? 'front' : 'rear'}</button> : null}
    </div>
    <div ref={pip} data-share-pip style={{ marginTop: state === 'live' ? 8 : 0, pointerEvents: 'auto' }} />
    <p style={{ margin: '6px 0 0', opacity: .85 }}>{status}</p>
    {state === 'live' && line ? <p style={{ margin: '4px 0 0' }}><small>{line}{estLine ? <><br />{estLine}</> : null}</small></p> : null}
  </aside>;
}
