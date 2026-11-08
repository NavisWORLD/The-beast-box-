// Browser capture for one app-shell sensorium. Derived numbers leave the device.
// Raw frames, waveforms, and transcripts do not. No speech recognizer and no model.
import {analyzeFrame, analyzeAudio} from '../companion/field-perception.mjs';
import {faceProxies} from '../companion/face-channel.mjs';
import {feelingsFromFace} from '../companion/emotion.mjs';
import {FacePulse} from '../bio/face-pulse.mjs';
import {analysePpg} from '../bio/ppg.mjs';
import {claimSensorLease, releaseForSensorium, releaseSensorLease} from '../environment/share-stream';
import {CADENCE_MS, createSensoriumSession, readRetention, type SensoriumSession, type SensorReading} from './sample.mjs';

const W = 32;
const H = 24;
type Lease = 'ambient' | 'fingertip';
type Stop = () => void;

function storedSeq(epoch: number): number {
  const saved = sessionStorage.getItem('beastbox-sensorium-seq') || '';
  const [savedEpoch, savedSeq] = saved.split(':');
  const seq = Number(savedSeq);
  if (Number(savedEpoch) !== epoch || !Number.isInteger(seq) || seq < 0) return 0;
  return seq;
}

function rememberSeq(epoch: number, seq: number) {
  sessionStorage.setItem('beastbox-sensorium-seq', epoch + ':' + seq);
}

function sessionId(): string {
  const key = 'beastbox-sensorium-session';
  const saved = sessionStorage.getItem(key);
  if (saved && /^s[a-f0-9]{16}$/.test(saved)) return saved;
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  const id = 's' + [...bytes].map((byte) => byte.toString(16).padStart(2, '0')).join('');
  sessionStorage.setItem(key, id);
  return id;
}

function presenceLine(sample: ReturnType<SensoriumSession['tick']>): string {
  if (!sample) return 'Senses on';
  // feelingsFromFace reads the face estimate. Its default parameter is typed as null.
  const felt = sample.face ? feelingsFromFace(sample.face.face, sample.face.pulse as null) : null;
  const word = (name: string, label: string) => `${label} ${sample.channels[name]?.label === 'MEASURED' ? 'on' : 'absent'}`;
  return [
    word('brightness', 'light'),
    word('hue', 'hue'),
    word('frame_motion', 'motion'),
    word('sound', 'sound'),
    word('pulse_bpm', 'pulse'),
    felt ? 'face estimate' : 'face absent',
  ].join(' · ');
}

export function createBrowserSensorium(options: {
  enabled: boolean;
  post: (body: unknown) => Promise<{ok?: boolean}>;
  onLine?: (line: string) => void;
}) {
  let stopped = false;
  let session: SensoriumSession | null = null;
  let timer = 0;
  const stops: Stop[] = [];
  let elected = true;
  let lockRelease: (() => void) | null = null;
  let motionLevel: number | null = null;

  function stopTracks() {
    stops.splice(0).forEach((stop) => { try { stop(); } catch { /* already stopped */ } });
    if (timer) window.clearInterval(timer);
    timer = 0;
  }

  async function openMedia(lease: Lease, target: SensoriumSession) {
    const videoMode = lease === 'fingertip' ? {ideal: 'environment' as const} : {ideal: 'user' as const};
    let video: MediaStream | null = null;
    let audio: MediaStream | null = null;
    try {
      video = await navigator.mediaDevices.getUserMedia({video:{facingMode: videoMode, width: {ideal: 320}, height: {ideal: 240}}});
      target.setPermission('camera', 'granted');
    } catch (error) {
      target.setPermission('camera', /NotAllowed|Permission|Security/i.test(String((error as Error)?.name || error)) ? 'denied' : 'ended');
    }
    try {
      audio = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation: true, noiseSuppression: true}});
      target.setPermission('mic', 'granted');
    } catch (error) {
      target.setPermission('mic', /NotAllowed|Permission|Security/i.test(String((error as Error)?.name || error)) ? 'denied' : 'ended');
    }
    const tracks = [...(video?.getTracks() ?? []), ...(audio?.getTracks() ?? [])];
    if (!tracks.length) return;
    const stream = new MediaStream(tracks);
    const videoTrack = video?.getVideoTracks()[0];
    const audioTrack = audio?.getAudioTracks()[0];
    if (videoTrack) videoTrack.onended = () => target.setPermission('camera', 'ended');
    if (audioTrack) audioTrack.onended = () => target.setPermission('mic', 'ended');
    const element = document.createElement('video');
    element.muted = true;
    element.playsInline = true;
    element.srcObject = stream;
    await element.play().catch(() => {});
    const canvas = document.createElement('canvas');
    canvas.width = W;
    canvas.height = H;
    const context = canvas.getContext('2d', {willReadFrequently: true});
    const pulse = new FacePulse();
    let prevEye: number | null = null;
    let gray: Float32Array | null = null;
    const ppgT: number[] = [];
    const ppgV: number[] = [];
    const ppgG: number[] = [];
    let meter: {ctx: AudioContext; analyser: AnalyserNode; buf: Float32Array<ArrayBuffer>} | null = null;
    if (audio) {
      const Ctx = window.AudioContext || (window as unknown as {webkitAudioContext?: typeof AudioContext}).webkitAudioContext;
      if (Ctx) {
        const ctx = new Ctx();
        const analyser = ctx.createAnalyser();
        analyser.fftSize = 2048;
        ctx.createMediaStreamSource(audio).connect(analyser);
        const samples = new ArrayBuffer(analyser.fftSize * 4);
        meter = {ctx, analyser, buf: new Float32Array(samples)};
        stops.push(() => { void ctx.close(); });
      }
    }
    const motion = await listenMotion(target);
    stops.push(motion);
    stops.push(() => {
      stream.getTracks().forEach((track) => { try { track.stop(); } catch { /* already stopped */ } });
      element.srcObject = null;
    });
    timer = window.setInterval(() => {
      if (!session || stopped || !elected) return;
      const at = Date.now();
      const reading: SensorReading = {at, brightness: null, hue: null, frameMotion: null, deviceMotion: motionLevel, sound: null, face: null, facePulse: null, pulse: null};
      if (context && element.videoWidth && lease === 'ambient') {
        context.drawImage(element, 0, 0, W, H);
        const frame = context.getImageData(0, 0, W, H).data;
        const seen = analyzeFrame(frame, gray, W, H);
        gray = seen.gray;
        reading.brightness = seen.brightness;
        reading.hue = seen.hue;
        reading.frameMotion = seen.motion;
        const proxies = faceProxies(frame, W, H, prevEye);
        prevEye = proxies.eye;
        reading.face = proxies;
        if (proxies.facePresent && proxies.faceGreen > 0) pulse.push(performance.now(), proxies.faceGreen);
        reading.facePulse = pulse.estimate();
        context.clearRect(0, 0, W, H);
      } else if (context && element.videoWidth && lease === 'fingertip') {
        context.drawImage(element, 0, 0, 8, 6);
        const data = context.getImageData(0, 0, 8, 6).data;
        let red = 0;
        let green = 0;
        const pixels = data.length / 4;
        for (let i = 0; i < data.length; i += 4) { red += data[i]; green += data[i + 1]; }
        ppgT.push(at);
        ppgV.push(red / pixels);
        ppgG.push(green / pixels);
        if (ppgT.length > 900) { ppgT.shift(); ppgV.shift(); ppgG.shift(); }
        const analysed = analysePpg({t: ppgT, v: ppgV, g: ppgG});
        reading.pulse = analysed.valid ? {valid: true, bpm: analysed.bpm, quality: analysed.sqi, source: 'fingertip_ppg'} : {valid: false, bpm: null, quality: analysed.sqi, source: 'fingertip_ppg'};
        context.clearRect(0, 0, 8, 6);
      }
      if (meter) {
        meter.analyser.getFloatTimeDomainData(meter.buf);
        reading.sound = analyzeAudio(meter.buf, meter.ctx.sampleRate || 48000).loudness;
        meter.buf.fill(0);
      }
      session.setReading(reading);
      const sample = session.tick(at);
      if (sample) rememberSeq(sample.consent_epoch, sample.source_seq);
      options.onLine?.(presenceLine(sample));
      if (session.pending().length >= 4 || session.backpressure()) void session.flush().catch(() => {});
    }, CADENCE_MS);
  }

  async function listenMotion(target: SensoriumSession): Promise<Stop> {
    try {
      const motionEvent = DeviceMotionEvent as typeof DeviceMotionEvent & {requestPermission?: () => Promise<string>};
      if (!motionEvent) throw new Error('unavailable');
      if (typeof motionEvent.requestPermission === 'function' && await motionEvent.requestPermission() !== 'granted') {
        target.setPermission('motion', 'denied');
        return () => {};
      }
      const onMotion = (event: DeviceMotionEvent) => {
        const acceleration = event.acceleration;
        const gravity = event.accelerationIncludingGravity;
        const magnitude = acceleration && acceleration.x !== null
          ? Math.hypot(acceleration.x || 0, acceleration.y || 0, acceleration.z || 0)
          : gravity && gravity.x !== null ? Math.abs(Math.hypot(gravity.x || 0, gravity.y || 0, gravity.z || 0) - 9.81) : null;
        if (magnitude !== null) motionLevel = Math.min(1, magnitude / 8);
      };
      window.addEventListener('devicemotion', onMotion);
      target.setPermission('motion', 'granted');
      return () => {
        window.removeEventListener('devicemotion', onMotion);
        motionLevel = null;
      };
    } catch {
      target.setPermission('motion', 'ended');
      return () => {};
    }
  }

  async function elect() {
    const locks = navigator.locks;
    if (!locks) { elected = true; return; }
    let settled = false;
    await new Promise<void>((resolve) => {
      const timer = window.setTimeout(() => {
        if (settled) return;
        settled = true;
        elected = false;
        resolve();
      }, 1000);
      void locks.request('beastbox-sensorium', {mode: 'exclusive', ifAvailable: true}, (lock) => {
        if (settled) return Promise.resolve();
        settled = true;
        window.clearTimeout(timer);
        if (!lock) {
          elected = false;
          resolve();
          return Promise.resolve();
        }
        elected = true;
        return new Promise<void>((release) => {
          lockRelease = release;
          resolve();
        });
      });
    });
  }

  return {
    async start(lease: Lease = 'ambient') {
      if (!options.enabled || stopped) return false;
      releaseForSensorium();
      if (!claimSensorLease('sensorium')) return false;
      const kept = readRetention(localStorage);
      if (!kept.accepted) { releaseSensorLease('sensorium'); return false; }
      await elect();
      if (!elected) { releaseSensorLease('sensorium'); return false; }
      session = createSensoriumSession({
        now: () => Date.now(),
        sessionId: sessionId(),
        surfaceId: 'app-shell',
        post: options.post,
      });
      session.setEnabled(true);
      session.setElected(true);
      session.setLease(lease);
      const epoch = kept.epoch || undefined;
      session.grantRetention(Date.now(), epoch, epoch ? storedSeq(epoch) : 0);
      if (!session.beginCapture()) { releaseSensorLease('sensorium'); return false; }
      const hidden = () => {
        session?.setHidden(document.visibilityState !== 'visible');
        const sample = session?.tick(Date.now());
        if (sample) rememberSeq(sample.consent_epoch, sample.source_seq);
        options.onLine?.(presenceLine(sample ?? null));
        void session?.flush().catch(() => {});
      };
      const leaving = () => session?.setHidden(true);
      document.addEventListener('visibilitychange', hidden);
      window.addEventListener('pagehide', leaving);
      stops.push(() => {
        document.removeEventListener('visibilitychange', hidden);
        window.removeEventListener('pagehide', leaving);
      });
      // Consent turns the indicator on before a permission prompt resolves.
      // A prompt that never returns leaves the channels ABSENT.
      void openMedia(lease, session);
      return true;
    },
    async stop(revoke = true) {
      stopped = true;
      if (revoke) session?.revokeRetention();
      const epoch = session?.feedOff()?.consent_epoch;
      try { await session?.flush(); } catch { /* the feed stays pending on this device */ }
      stopTracks();
      releaseSensorLease('sensorium');
      lockRelease?.();
      return epoch ?? 0;
    },
    line() { return 'Senses on'; },
  };
}
