export const FACE_PULSE_RULES: Readonly<Record<string, number>>;
export declare class FacePulse {
  constructor();
  push(t: number, green: number): void;
  estimate(): { bpm: number; sqi: number; beats: number } | null;
  reset(): void;
}
