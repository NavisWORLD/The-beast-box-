export const CADENCE_MS: number;
export const FRESH_MS: number;
export const MAX_PENDING: number;
export const SAMPLE_SCHEMA: string;
export const BATCH_SCHEMA: string;
export const FEED_OFF_SCHEMA: string;
export const RETENTION_SCHEMA: string;
export const RETENTION_KEY: string;
export function absentChannel(source?: string, status?: string): SensorChannel;
export function measuredChannel(name: string, value: number, source: string, quality?: number): SensorChannel;
export function soundChannel(micOn: boolean, level: number | null): SensorChannel;
export function pulseChannel(reading: PulseReading | null): SensorChannel;
export function faceForSample(cameraOn: boolean, proxies: FaceProxies | null, pulse: FacePulseEstimate | null): FaceRecord | null;
export const feelingsLink: (face: {present: boolean; scale: number; x: number; y: number; blink: number} | null, pulse?: {bpm: number; sqi: number} | null) => Feelings | null;

export interface SensorChannel { label: 'MEASURED' | 'ABSENT'; value: number | null; status: string; source: string; quality: number | null }
export interface PulseReading { valid: boolean; bpm: number | null; quality: number | null; source: string }
export interface FaceProxies { facePresent: number; faceScale: number; faceX: number; faceY: number; faceBlink: number }
export interface FacePulseEstimate { bpm: number; sqi: number }
export interface FaceRecord { schema: string; heartbeat_label: string; face: {present: boolean; scale: number; x: number; y: number; blink: number}; pulse: {bpm: number; sqi: number} | null }
export interface Feelings { label: string; words: string[]; joy: number; curiosity: number; fear: number; calm: number; mischief: number; confused: null }
export interface SensorSample { schema: string; surface_id: string; session_id: string; consent_epoch: number; source_seq: number; captured_at_ms: number; channels: Record<string, SensorChannel>; face: FaceRecord | null }
export interface SensorBatch { schema: string; retention_consent: true; nonce: string; samples: SensorSample[] }
export interface FeedOff { schema: string; retention_consent: true; session_id: string; consent_epoch: number }
export interface RetentionRecord { accepted: boolean; epoch: number; at?: number }
export type SensorBody = SensorBatch | FeedOff;
export interface Validated { ok: boolean; code?: string; body?: SensorBody; sample?: SensorSample }

export function readRetention(store: {getItem(key: string): string | null} | null): RetentionRecord;
export function writeRetention(store: {setItem(key: string, value: string): void}, record: {accepted: boolean; epoch: number; at: number}): void;
export function validateSample(raw: unknown): Validated;
export function validateBatch(body: unknown): Validated;

export interface SensorReading {
  at: number;
  brightness?: number | null;
  hue?: number | null;
  frameMotion?: number | null;
  deviceMotion?: number | null;
  sound?: number | null;
  face?: FaceProxies | null;
  facePulse?: FacePulseEstimate | null;
  pulse?: PulseReading | null;
}
export interface SensoriumSession {
  setEnabled(value: boolean): void;
  setElected(value: boolean): void;
  setLease(value: 'ambient' | 'fingertip' | null): void;
  setPermission(kind: 'camera' | 'mic' | 'motion', value: string): void;
  setHidden(value: boolean): void;
  setReading(reading: SensorReading | null): void;
  grantRetention(at: number, epoch?: number, seq?: number): void;
  revokeRetention(): void;
  tick(at: number): SensorSample | null;
  flush(): Promise<{ok?: boolean; receipts?: unknown[]} | undefined>;
  arm(schedule: (ms: number, tick: () => void) => unknown): unknown;
  disarm(): void;
  beginCapture(): boolean;
  pending(): SensorSample[];
  feedOff(): FeedOff | null;
  lastFeelings(): Feelings | null;
  backpressure(): boolean;
  disclosure(): {pending: number; committed: boolean};
}
export function createSensoriumSession(options?: {
  now?: () => number;
  sessionId?: string;
  surfaceId?: string;
  post?: (body: SensorBody) => Promise<{ok?: boolean; receipts?: unknown[]}>;
  onChat?: () => void;
}): SensoriumSession;
