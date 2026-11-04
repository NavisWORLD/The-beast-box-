// One shared "Share my world with Zeref" session for the whole site.
// Until now every page opened its own camera stream and unmounting killed it,
// so sharing never survived navigation and never really "saved". This manager
// owns ONE stream at app-shell level: the persisted switch (localStorage)
// says whether sharing is on, and the stream lives here, not in any page.
// Frames are analysed on-device by the surfaces that subscribe; the stream
// itself is never recorded or uploaded anywhere. Browser permission law still
// applies: after a reload the browser may require one fresh tap, and the
// shell says so honestly instead of pretending the switch stayed on.
export type ShareFacing = 'user' | 'environment';
export type ShareState = 'off' | 'live' | 'resume' | 'denied' | 'unavailable';
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

type Listener = (state: ShareState) => void;

class ShareStreamManager {
  state: ShareState = 'off';
  facing: ShareFacing = 'user';
  stream: MediaStream | null = null;
  video: HTMLVideoElement | null = null;
  private listeners = new Set<Listener>();
  private starting: Promise<boolean> | null = null;

  subscribe(fn: Listener): () => void { this.listeners.add(fn); fn(this.state); return () => { this.listeners.delete(fn); }; }
  private set(state: ShareState) { this.state = state; this.listeners.forEach(fn => { try { fn(state); } catch { /* a listener must never break the session */ } }); }

  /** Start (or restart) the shared stream. Resolves true when live. A user gesture is required by the browser for the permission prompt. */
  start(facing?: ShareFacing): Promise<boolean> {
    if (this.starting) return this.starting;
    if (facing) this.facing = facing;
    this.starting = this.open().finally(() => { this.starting = null; });
    return this.starting;
  }
  private async open(): Promise<boolean> {
    this.stopTracks();
    if (typeof window === 'undefined' || !window.isSecureContext || !navigator.mediaDevices?.getUserMedia) { this.set('unavailable'); return false; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: this.facing }, width: { ideal: 320 }, height: { ideal: 240 } },
        audio: { echoCancellation: true, noiseSuppression: true },
      });
      const video = this.video ?? document.createElement('video');
      video.muted = true; video.playsInline = true; video.srcObject = stream;
      await video.play().catch(() => {});
      this.stream = stream; this.video = video;
      this.set('live');
      return true;
    } catch (error) {
      const name = String((error as Error)?.name || error);
      this.set(/NotAllowed|Permission|Security/i.test(name) ? 'denied' : 'unavailable');
      return false;
    }
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
    if (this.video) this.video.srcObject = null;
  }
  stop() { this.stopTracks(); this.set('off'); }
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
