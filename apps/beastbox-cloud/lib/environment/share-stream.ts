// One shared "Share my world with Zeref" session for the whole site.
// The stream lives here, not in any page. Camera and microphone are separate
// permissions. Frames stay on this device. One lease: the sensorium, this
// share session, or the surroundings panel. Two of them do not open tracks.
import {analyzeAudio} from '../companion/field-perception.mjs';

export type ShareFacing = 'user' | 'environment';
export type ShareState = 'off' | 'live' | 'resume' | 'denied' | 'unavailable';
export type SensorLease = 'sensorium' | 'share-world' | 'environment';
export const SHARE_PREF_KEY = 'beastbox-share-world-v1';
export interface SharePref { on: boolean; facing: ShareFacing }

type Store = { getItem(k: string): string | null; setItem(k: string, v: string): void } | null;
const defaultStore = (): Store => { try { return window.localStorage; } catch { return null; } };

export function readSharePref(store: Store = defaultStore()): SharePref {
  try {
    const raw = store?.getItem(SHARE_PREF_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return { on: parsed?.on === true, facing: parsed?.facing === 'environment' ? 'environment' : 'user' };
  } catch { return { on: false, facing: 'user' }; }
}
export function writeSharePref(pref: SharePref, store: Store = defaultStore()): void {
  try { store?.setItem(SHARE_PREF_KEY, JSON.stringify(pref)); } catch { /* storage full/blocked: the session still works, it just will not resume */ }
}

let lease: SensorLease | null = null;
export function sensorLeaseHolder(): SensorLease | null { return lease; }
export function claimSensorLease(id: SensorLease): boolean {
  if (lease && lease !== id) return false;
  lease = id;
  return true;
}
export function releaseSensorLease(id: SensorLease): void {
  if (lease === id) lease = null;
}
export function releaseForSensorium(): void {
  shareStream.stop();
  lease = null;
  if (typeof window !== 'undefined') window.dispatchEvent(new Event('beastbox:sensorium-lease'));
}

type Listener = (state: ShareState) => void;
type Meter = { ctx: AudioContext; analyser: AnalyserNode; buf: Float32Array<ArrayBuffer> };

class ShareStreamManager {
  state: ShareState = 'off';
  facing: ShareFacing = 'user';
  stream: MediaStream | null = null;
  video: HTMLVideoElement | null = null;
  cameraLive = false;
  micLive = false;
  private listeners = new Set<Listener>();
  private starting: Promise<boolean> | null = null;
  private meter: Meter | null = null;

  subscribe(fn: Listener): () => void { this.listeners.add(fn); fn(this.state); return () => { this.listeners.delete(fn); }; }
  private set(state: ShareState) { this.state = state; this.listeners.forEach(fn => { try { fn(state); } catch { /* a listener must never break the session */ } }); }

  /** Derived loudness, or null when the microphone is not live. Null is absence, not silence. */
  measureSound(): { loudness: number; pitchHz: number } | null {
    if (!this.micLive || !this.meter) return null;
    this.meter.analyser.getFloatTimeDomainData(this.meter.buf);
    const level = analyzeAudio(this.meter.buf, this.meter.ctx.sampleRate || 48000);
    this.meter.buf.fill(0);
    return level;
  }

  /** Start (or restart) the shared stream. Resolves true when live. A user gesture is required by the browser for the permission prompt. */
  start(facing?: ShareFacing): Promise<boolean> {
    if (lease && lease !== 'share-world') return Promise.resolve(false);
    if (this.starting) return this.starting;
    if (facing) this.facing = facing;
    this.starting = this.open().finally(() => { this.starting = null; });
    return this.starting;
  }
  private async open(): Promise<boolean> {
    this.stopTracks();
    if (!claimSensorLease('share-world')) return false;
    if (typeof window === 'undefined' || !window.isSecureContext || !navigator.mediaDevices?.getUserMedia) { this.set('unavailable'); releaseSensorLease('share-world'); return false; }
    let video: MediaStream | null = null;
    let audio: MediaStream | null = null;
    let videoError: unknown = null;
    let audioError: unknown = null;
    try {
      video = await navigator.mediaDevices.getUserMedia({video:{facingMode: { ideal: this.facing }, width: { ideal: 320 }, height: { ideal: 240 }}});
    } catch (error) { videoError = error; }
    try {
      audio = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation: true, noiseSuppression: true}});
    } catch (error) { audioError = error; }
    this.cameraLive = !!video?.getVideoTracks().length;
    this.micLive = !!audio?.getAudioTracks().length;
    if (!this.cameraLive && !this.micLive) {
      releaseSensorLease('share-world');
      const name = String((videoError as Error)?.name || (audioError as Error)?.name || videoError || audioError);
      this.set(/NotAllowed|Permission|Security/i.test(name) ? 'denied' : 'unavailable');
      return false;
    }
    const stream = new MediaStream([...(video?.getTracks() ?? []), ...(audio?.getTracks() ?? [])]);
    for (const track of stream.getTracks()) track.onended = () => this.noteEnded(track.kind);
    const element = this.video ?? document.createElement('video');
    element.muted = true; element.playsInline = true;
    if (this.cameraLive) { element.srcObject = stream; await element.play().catch(() => {}); }
    this.stream = stream; this.video = element;
    this.attachMeter(audio);
    this.set('live');
    return true;
  }
  private noteEnded(kind: string) {
    if (kind === 'video') this.cameraLive = false;
    if (kind === 'audio') { this.micLive = false; this.meter = null; }
    if (!this.cameraLive && !this.micLive) this.stop();
  }
  private attachMeter(audio: MediaStream | null) {
    this.meter = null;
    if (!audio) return;
    const Ctx = window.AudioContext || (window as unknown as {webkitAudioContext?: typeof AudioContext}).webkitAudioContext;
    if (!Ctx) { this.micLive = false; return; }
    const ctx = new Ctx();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 2048;
    ctx.createMediaStreamSource(audio).connect(analyser);
    const samples = new ArrayBuffer(analyser.fftSize * 4);
    this.meter = {ctx, analyser, buf: new Float32Array(samples)};
  }
  /** Flip between the selfie camera and the world camera, live. */
  async flip(): Promise<boolean> {
    this.facing = this.facing === 'user' ? 'environment' : 'user';
    if (this.state === 'live') return this.start(this.facing);
    return false;
  }
  private stopTracks() {
    this.stream?.getTracks().forEach(t => { try { t.stop(); } catch { /* already stopped */ } });
    this.stream = null;
    this.cameraLive = false;
    this.micLive = false;
    if (this.meter) { void this.meter.ctx.close(); this.meter = null; }
    if (this.video) this.video.srcObject = null;
  }
  stop() { this.stopTracks(); releaseSensorLease('share-world'); this.set('off'); }
  /** After a reload with the switch on: 'granted' boots the stream silently; anything else needs the one honest tap. */
  async resume(): Promise<void> {
    try {
      const status = await navigator.permissions?.query({ name: 'camera' as PermissionName });
      if (status?.state === 'granted') { const ok = await this.start(); if (!ok) this.set('resume'); return; }
    } catch { /* permissions API missing: fall through to the tap */ }
    if (this.state !== 'live') this.set('resume');
  }
}

export const shareStream = new ShareStreamManager();
