export const VISION_WIDTH: number;
export const VISION_HEIGHT: number;
export type VisionFace = { detected: boolean; x: number; y: number; size: number; confidence: number; method: string };
export type VisionSurface = { detected: boolean; y: number; floorPct: number; tilt: number; confidence: number; kind: string };
export type VisionFrameResult = {
  light: number;
  lightDelta: number;
  lighting: 'dark' | 'normal' | 'bright';
  motion: number;
  motionX: number;
  motionY: number;
  face: VisionFace;
  surface: VisionSurface;
  mode: 'not-ar-on-device';
};
export function createVisionState(opts?: { width?: number; height?: number }): any;
export function analyzeRgbaFrame(rgba: Uint8ClampedArray | number[], state?: any, opts?: { hwFace?: any }): VisionFrameResult;
export function sampleVideoFrame(video: HTMLVideoElement | null, canvas: HTMLCanvasElement | null, state?: any): VisionFrameResult;
export function visionReaction(vision: VisionFrameResult | null, emotion?: any, opts?: { worldWidth?: number; name?: string }): {
  action: 'idle' | 'look' | 'approach' | 'flee';
  cue: string | null;
  lookAt: { x: number; z: number } | null;
  target: { x: number; z: number } | null;
  summary: string;
  noticeLine: string;
};
