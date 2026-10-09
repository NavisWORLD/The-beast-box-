'use client';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { eyesFor, followStep, goTo, placeById, reactionFor, rememberExchange, talkAndGrow } from '../lib/companion/adventure.mjs';
import { chooseBrain, fallbackAfterFailure, guestBody, interpretModelResult, ownerChatBody } from '../lib/companion/brain.mjs';
import { buildChatContext, renderContextPrompt } from '../lib/companion/context.mjs';
import { replyFromMind } from '../lib/companion/learn.mjs';
import { readCameraFrame, readMicSample, readSignal } from '../lib/companion/sensors.mjs';
import { shownName } from '../lib/companion/session.mjs';
import { MuseLink, mockTraits } from '../lib/companion/spark/muse.mjs';
import BeastCareDeck from './beast-care-deck';
import { useBeastSession } from './beast-session';
import PixelBeast from './pixel-beast';
import css from './beast-adventure.module.css';

type Sensors = {
  camera: ReturnType<typeof readCameraFrame>;
  mic: ReturnType<typeof readMicSample>;
  signal: ReturnType<typeof readSignal>;
};

const OFF: Sensors = {
  camera: readCameraFrame(null, null),
  mic: readMicSample(null, null),
  signal: readSignal({ enabled: false }),
};

type Job = { state?: string; error?: string; result?: { result?: { response?: string } }; response?: string };

export default function BeastAdventure() {
  const { ready, session, trail, sensorLog, change, setTrail, noteSensor } = useBeastSession();
  const [sensors, setSensors] = useState<Sensors>(OFF);
  const [cameraOn, setCameraOn] = useState(false);
  const [micOn, setMicOn] = useState(false);
  const [signalMode, setSignalMode] = useState<'off' | 'simulated' | 'muse'>('off');
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState('');
  const [label, setLabel] = useState('No message yet.');
  const [reduced, setReduced] = useState(false);
  const video = useRef<HTMLVideoElement>(null);
  const cameraStream = useRef<MediaStream | null>(null);
  const micStream = useRef<MediaStream | null>(null);
  const audio = useRef<AudioContext | null>(null);
  const previousFrame = useRef<Uint8ClampedArray | null>(null);
  const previousLoud = useRef(0);
  const micTimer = useRef<number | null>(null);
  const museStop = useRef<null | (() => void)>(null);
  const sensorsRef = useRef(sensors);
  sensorsRef.current = sensors;

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const apply = () => setReduced(media.matches);
    apply();
    media.addEventListener('change', apply);
    return () => media.removeEventListener('change', apply);
  }, []);

  useEffect(() => {
    if (reduced || !trail.moving) return;
    const timer = window.setInterval(() => setTrail(followStep(trail)), 180);
    return () => window.clearInterval(timer);
  }, [trail, setTrail, reduced]);

  useEffect(() => () => {
    if (micTimer.current !== null) window.clearInterval(micTimer.current);
    cameraStream.current?.getTracks().forEach((track) => track.stop());
    micStream.current?.getTracks().forEach((track) => track.stop());
    void audio.current?.close().catch(() => undefined);
    museStop.current?.();
  }, []);

  useEffect(() => {
    if (!cameraOn && !micOn && signalMode === 'off') return;
    const timer = window.setInterval(() => {
      const next = { ...sensorsRef.current };
      if (cameraOn && video.current && video.current.readyState >= 2) {
        const scratch = document.createElement('canvas');
        scratch.width = 16;
        scratch.height = 16;
        const ctx = scratch.getContext('2d', { willReadFrequently: true });
        if (ctx) {
          ctx.drawImage(video.current, 0, 0, 16, 16);
          const frame = ctx.getImageData(0, 0, 16, 16).data;
          next.camera = readCameraFrame(previousFrame.current, frame);
          previousFrame.current = new Uint8ClampedArray(frame);
        }
      }
      setSensors(next);
    }, 400);
    return () => window.clearInterval(timer);
  }, [cameraOn, micOn, signalMode]);

  const beast = session?.beast;
  const reaction = reactionFor({
    genome: beast?.genome,
    beast,
    trail,
    sensors,
  });
  const place = placeById(trail.place);

  async function toggleCamera() {
    if (cameraOn) {
      cameraStream.current?.getTracks().forEach((track) => track.stop());
      cameraStream.current = null;
      if (video.current) video.current.srcObject = null;
      previousFrame.current = null;
      setCameraOn(false);
      setSensors((current) => ({ ...current, camera: readCameraFrame(null, null) }));
      noteSensor('camera off');
      return;
    }
    try {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) throw new Error('Camera needs a secure page.');
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false });
      cameraStream.current = stream;
      if (video.current) {
        video.current.srcObject = stream;
        await video.current.play();
      }
      setCameraOn(true);
      noteSensor('camera on');
    } catch {
      setCameraOn(false);
      setSensors((current) => ({ ...current, camera: readCameraFrame(null, null) }));
      noteSensor('camera permission denied');
      setLabel('Camera stayed off. Permission was denied or the browser has no camera.');
    }
  }

  async function toggleMic() {
    if (micOn) {
      if (micTimer.current !== null) window.clearInterval(micTimer.current);
      micTimer.current = null;
      micStream.current?.getTracks().forEach((track) => track.stop());
      micStream.current = null;
      void audio.current?.close().catch(() => undefined);
      audio.current = null;
      setMicOn(false);
      setSensors((current) => ({ ...current, mic: readMicSample(null, null) }));
      noteSensor('mic off');
      return;
    }
    try {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) throw new Error('Microphone needs a secure page.');
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true }, video: false });
      micStream.current = stream;
      const ctx = new AudioContext();
      audio.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const node = ctx.createAnalyser();
      node.fftSize = 1024;
      source.connect(node);
      const silent = ctx.createGain();
      silent.gain.value = 0;
      node.connect(silent);
      silent.connect(ctx.destination);
      await ctx.resume();
      micTimer.current = window.setInterval(() => {
        if (!audio.current || audio.current.state === 'closed') return;
        const data = new Float32Array(node.fftSize);
        node.getFloatTimeDomainData(data);
        const rms = Math.sqrt(data.reduce((sum, value) => sum + value * value, 0) / data.length);
        const reading = readMicSample(rms, previousLoud.current);
        previousLoud.current = reading.loudness;
        setSensors((current) => ({ ...current, mic: reading }));
        if (reading.onset) noteSensor('mic onset');
      }, 250);
      setMicOn(true);
      noteSensor('mic on');
    } catch {
      setMicOn(false);
      setSensors((current) => ({ ...current, mic: readMicSample(null, null) }));
      noteSensor('mic permission denied');
      setLabel('Microphone stayed off. Permission was denied or the browser has no mic.');
    }
  }

  async function toggleSignal(mode: 'off' | 'simulated' | 'muse') {
    museStop.current?.();
    museStop.current = null;
    if (mode === 'off' || signalMode === mode) {
      setSignalMode('off');
      setSensors((current) => ({ ...current, signal: readSignal({ enabled: false }) }));
      noteSensor('headband off');
      return;
    }
    if (mode === 'simulated') {
      setSignalMode('simulated');
      const reading = readSignal({ enabled: true, simulated: mockTraits() });
      setSensors((current) => ({ ...current, signal: reading }));
      noteSensor('simulated headband on');
      return;
    }
    try {
      const link = new MuseLink((traits: { focus: number; calm: number; spark: number }) => {
        setSensors((current) => ({ ...current, signal: readSignal({ museTraits: traits }) }));
      });
      await link.connect();
      museStop.current = () => { void link.stop(); };
      setSignalMode('muse');
      noteSensor(`Muse connected: ${link.device?.name || 'Muse'}`);
    } catch (error) {
      setSignalMode('off');
      setSensors((current) => ({ ...current, signal: readSignal({ enabled: false }) }));
      setLabel(error instanceof Error ? error.message : 'Muse did not connect. The simulated headband stays off until you choose it.');
    }
  }

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const saying = text.trim();
    if (!saying || busy || !session) return;
    setBusy(true);
    setText('');
    const context = buildChatContext({ session, trail, sensors, sensorLog });
    const prompt = renderContextPrompt(context, saying, 700);
    let route = chooseBrain({ ownerReady: false, guestReady: false });
    try {
      const status = await fetch('/api/status', { cache: 'no-store', credentials: 'same-origin' }).then((response) => response.json());
      route = chooseBrain({
        ownerReady: status?.owner === true && status?.backendReachable === true,
        providerKind: typeof status?.providerKind === 'string' ? status.providerKind : '',
        guestReady: false,
      });
    } catch {
      route = chooseBrain({});
    }
    let spoken = '';
    let spokenLabel = route.label;
    let ownerPending = false;
    if (route.route === 'owner-bridge') {
      const requestId = crypto.randomUUID();
      const started = await fetch('/api/bridge/chat-start', {
        method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ownerChatBody(renderContextPrompt(context, saying, 4000), requestId)),
      });
      const job = await started.json() as Job & { job_id?: string };
      if (started.ok && typeof job.job_id === 'string') {
        let state: Job = job;
        const deadline = Date.now() + 40_000;
        while (state.state === 'running' && Date.now() < deadline) {
          await new Promise((resolve) => setTimeout(resolve, 2000));
          const polled = await fetch('/api/bridge/chat-job?id=' + encodeURIComponent(job.job_id), { cache: 'no-store', credentials: 'same-origin' });
          state = await polled.json() as Job;
        }
        if (state.state === 'running') {
          ownerPending = true;
          spokenLabel = 'Brain Bay is still running. No substitute reply was invented.';
        } else {
          const read = interpretModelResult('owner-bridge', state);
          if (read.ok && read.reply) {
            spoken = read.reply;
            spokenLabel = route.label;
          } else spokenLabel = fallbackAfterFailure(read.reason).failure;
        }
      } else spokenLabel = fallbackAfterFailure(typeof job.error === 'string' ? job.error : 'Brain Bay did not start a chat').failure;
    }
    if (!spoken && !ownerPending) {
      const guestRoute = chooseBrain({ guestReady: true });
      const guest = await fetch('/api/guest', {
        method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(guestBody(prompt)),
      });
      const payload = await guest.json();
      const read = interpretModelResult('guest-rawrphos', payload);
      if (read.ok && read.reply) {
        spoken = read.reply;
        spokenLabel = guestRoute.label;
      } else if (route.route !== 'owner-bridge') spokenLabel = fallbackAfterFailure(read.reason).failure;
    }
    if (!spoken && !ownerPending) {
      let local = '';
      const saved=await change((draft) => { local = talkAndGrow(draft, saying).reply || ''; });
      if(!saved.ok){setLabel(saved.reason||'The exchange could not be saved.');setBusy(false);return;}
      spoken = local;
      spokenLabel = `${spokenLabel} Local pattern reply is separate and is not a model answer.`;
    } else if (spoken) {
      const line = spoken;
      const saved=await change((draft) => { rememberExchange(draft, saying, line); });
      if(!saved.ok){setLabel(saved.reason||'The exchange could not be saved.');setBusy(false);return;}
    }
    setAnswer(spoken);
    setLabel(spokenLabel);
    setBusy(false);
  }

  return <main className={css.page}>
    <header className={css.top}>
      <Link href="/beast-cage">✦ BEAST CAGE</Link>
      <Link href="/workspace#brain-bay">BRAIN BAY ↗</Link>
    </header>
    <div className={css.layout}>
      <section className={css.map} aria-label="Adventure trail">
        {['grove', 'shore', 'observatory', 'nest'].map((id) => {
          const spot = placeById(id);
          return <button key={id} type="button" className={css.place} style={{ left: `${spot.x}%`, top: `${spot.y}%` }} aria-pressed={trail.place === id} onClick={() => setTrail(goTo(trail, id))}>{spot.name}</button>;
        })}
        <div className={css.beast} style={{ left: `${trail.beast.x}%`, top: `${trail.beast.y}%` }}>
          {beast ? <PixelBeast publicSpark={!!beast?.qbeast} genome={{ ...beast.genome, facing: trail.facing }} stage={beast.stage} pose={reaction.pose === 'emote' ? 'emote' : reaction.pose} emote={reaction.emote} facing={trail.facing} reduced={reduced} label={`${shownName(beast)} ${reaction.pose}, ${reaction.reason}`} /> : null}
        </div>
        <p className={css.emote} style={{ left: `${trail.beast.x}%`, top: `${trail.beast.y}%` }}>{beast ? reaction.reason : 'Meet a spark beast in the care deck.'}</p>
        <video ref={video} muted playsInline style={{ position: 'absolute', width: 1, height: 1, opacity: 0 }} aria-hidden="true" />
      </section>
      <section className={css.side} aria-label="Adventure talk">
        <span className={css.label}>{place.name}</span>
        <p className={css.note}>Nearby: {place.nearby.join(', ')}. {ready && beast ? `${shownName(beast)} · stage ${beast.stage} · ${beast.mood} · ${beast.xp} XP` : 'The care deck below can meet a beast.'}</p>
        <div className={css.sensors} role="group" aria-label="Optional sensors">
          <button type="button" className={cameraOn ? css.on : ''} aria-pressed={cameraOn} onClick={() => void toggleCamera()}>Camera {cameraOn ? 'on' : 'off'}</button>
          <button type="button" className={micOn ? css.on : ''} aria-pressed={micOn} onClick={() => void toggleMic()}>Mic {micOn ? 'on' : 'off'}</button>
          <button type="button" className={signalMode === 'simulated' ? css.on : ''} aria-pressed={signalMode === 'simulated'} onClick={() => void toggleSignal('simulated')}>Simulated signal {signalMode === 'simulated' ? 'on' : 'off'}</button>
          <button type="button" className={signalMode === 'muse' ? css.on : ''} aria-pressed={signalMode === 'muse'} onClick={() => void toggleSignal('muse')}>Muse {signalMode === 'muse' ? 'on' : 'off'}</button>
        </div>
        <p className={css.note}>Each sensor starts off. Seeing is motion and brightness. Hearing is loudness and onset. The simulated headband is labeled and does not replace a Muse.</p>
        <div className={css.chat} role="status">
          <strong>{label}</strong>
          <p>{busy ? 'Waiting for a verified reply…' : answer || 'Type to your beast. If Brain Bay or the RAWRPHØS guest host is quiet, the on-device pattern memory answers and says so.'}</p>
        </div>
        <form onSubmit={(event) => void send(event)}>
          <label htmlFor="adventure-talk">Talk on the trail</label>
          <textarea id="adventure-talk" value={text} maxLength={400} disabled={busy || !beast} onChange={(event) => setText(event.target.value)} placeholder={beast ? 'What do you see here?' : 'Meet a beast first'} />
          <button className={css.send} type="submit" disabled={busy || !text.trim() || !beast}>{busy ? 'Waiting…' : 'Send'}</button>
        </form>
        <p className={css.note}>Eyes: {eyesFor(reaction)}. Pose: {reaction.pose}. This movement comes from spark traits, care needs, and the sensors that are actually on.</p>
      </section>
    </div>
    <BeastCareDeck chat={false} sprite={false} />
  </main>;
}
