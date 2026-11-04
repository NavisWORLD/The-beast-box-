export const FACE_KEYS: readonly string[];
export const FACE_HONESTY: string;
export interface FaceProxies {
  facePresent: number; faceScale: number; faceX: number; faceY: number; faceBlink: number;
  eye: number; faceGreen: number;
}
export function faceProxies(px: ArrayLike<number>, w: number, h: number, prevEye?: number | null): FaceProxies;
