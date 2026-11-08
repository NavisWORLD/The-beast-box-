'use client';
// One app-shell sensorium. It stays dark unless the lived backbone flag is on
// and the owner agrees to keep derived numbers. Closing a page does not stop it;
// Stop does. This consent is not the older surroundings record.
import {useEffect, useRef, useState} from 'react';
import {createBrowserSensorium} from '../lib/sensorium/runtime';
import {readRetention, writeRetention} from '../lib/sensorium/sample.mjs';

type Status = {enabled?: boolean};
type Runtime = ReturnType<typeof createBrowserSensorium>;

async function postSample(body: unknown) {
  const response = await fetch('/api/zeref/sensorium', {
    method: 'POST',
    credentials: 'same-origin',
    cache: 'no-store',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error('not admitted');
  const data = await response.json().catch(() => ({}));
  return {ok: data?.admitted !== false && data?.enabled !== false};
}

export default function SensoriumProvider() {
  const [status, setStatus] = useState<Status | null>(null);
  const [running, setRunning] = useState(false);
  const [line, setLine] = useState('Senses on');
  const runtimeRef = useRef<Runtime | null>(null);

  useEffect(() => {
    let live = true;
    fetch('/api/zeref/sensorium', {cache: 'no-store', credentials: 'same-origin'})
      .then((response) => response.json())
      .then((body) => { if (live) setStatus(body?.enabled === true ? body : {enabled: false}); })
      .catch(() => { if (live) setStatus({enabled: false}); });
    return () => { live = false; };
  }, []);

  useEffect(() => () => { void runtimeRef.current?.stop(false); }, []);

  if (status?.enabled !== true) return null;
  const accepted = typeof window !== 'undefined' && readRetention(window.localStorage).accepted;

  async function start(lease: 'ambient' | 'fingertip') {
    writeRetention(window.localStorage, {accepted: true, epoch: Math.max(1, readRetention(window.localStorage).epoch || 1), at: Date.now()});
    const next = createBrowserSensorium({enabled: true, post: postSample, onLine: setLine});
    runtimeRef.current = next;
    const ok = await next.start(lease);
    if (!ok) runtimeRef.current = null;
    setRunning(ok);
  }
  async function stop() {
    const current = runtimeRef.current;
    runtimeRef.current = null;
    const epoch = await current?.stop(true);
    writeRetention(window.localStorage, {accepted: false, epoch: (epoch || 0) + 1, at: Date.now()});
    setRunning(false);
  }

  return <aside data-sensorium style={{position: 'fixed', right: 10, top: 10, zIndex: 40, maxWidth: 220, padding: 10, border: '1px solid #3b3f78', borderRadius: 12, background: 'rgba(13,18,48,.92)', color: '#e8ecff', font: '12px system-ui'}}>
    {running ? <>
      <p data-sensorium-indicator style={{margin: 0}}>Senses on</p>
      <p style={{margin: '4px 0 8px', opacity: .8}}>{line}</p>
      <button type="button" data-sensorium-stop onClick={() => void stop()} style={{minHeight: 44}}>Stop senses</button>
    </> : <>
      <p style={{margin: '0 0 6px'}}>Keep derived sense numbers</p>
      <p style={{margin: '0 0 8px', opacity: .8}}>Brightness, hue, motion, sound, pulse and face presence. Numbers only. They are kept. Stopping later does not erase what was already kept.</p>
      <button type="button" data-sensorium-consent onClick={() => void start('ambient')} style={{minHeight: 44}} disabled={accepted && running}>Keep them</button>
      <button type="button" data-sensorium-fingertip onClick={() => void start('fingertip')} style={{minHeight: 44, marginLeft: 8}}>Fingertip pulse</button>
    </>}
  </aside>;
}
