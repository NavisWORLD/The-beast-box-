export const FACE_BIO_SCHEMA: string;
export const FACE_BIO_SOURCE: string;
export const FACE_BIO_HONESTY: string;
export interface FaceEstimates {
  schema: string; source: string; heartbeat_label: 'ESTIMATE'; honesty: string;
  face: { present: boolean; scale: number; x: number; y: number; blink: number };
  pulse: { bpm: number; sqi: number } | null;
  raw_audio_published: false; raw_video_published: false; raw_frames_in_packet: false;
}
export function buildFaceEstimates(input: { face?: Record<string, number>; pulse?: { bpm: number; sqi: number } | null }): FaceEstimates;
export function validateFaceEstimates(o: unknown): { ok: boolean; errors: string[] };
