// Face pulse: an rPPG-style ESTIMATE from the front camera's face region.
// The skin region's green-channel mean is a light signal the pulse rides on;
// it is analysed by the SAME PPG analyser the fingertip path uses, under
// relaxed rules, and the result is an ESTIMATE by construction: it never
// wears the MEASURED label, never enters the sealed bio packet, and is
// null whenever the signal does not pass the quality gate (never invented).
import { analysePpg, PPG_RULES } from './ppg.mjs';
// min_red is a face-lit floor, not the fingertip torch floor, and the signal
// is passed without a green companion channel so the fingertip geometry check
// (red minus green) does not apply to a face. The quality gates that matter
// (SQI from agreement, coverage and regularity; beat count; bpm range) stay.
export const FACE_PULSE_RULES = Object.freeze({ ...PPG_RULES, settle_s: 1, min_duration_s: 8, min_beats: 6, min_sqi: 0.4, min_red: 40 });
const MAX_SAMPLES = 1800; // ~3 minutes at 10 samples/s; the estimate uses the tail window
export class FacePulse {
  constructor() { this.t = []; this.v = []; }
  /** One sample: time in ms (monotonic) and the face region's mean green 0..255. Non-increasing times are dropped. */
  push(t, green) {
    if (!Number.isFinite(t) || !Number.isFinite(green)) return;
    if (this.t.length && t <= this.t[this.t.length - 1]) return;
    this.t.push(t); this.v.push(green);
    if (this.t.length > MAX_SAMPLES) { this.t.splice(0, this.t.length - MAX_SAMPLES); this.v.splice(0, this.v.length - MAX_SAMPLES); }
  }
  /** {bpm, sqi, beats} when the collected signal passes the gate, else null. */
  estimate() {
    if (this.t.length < 60) return null;
    const r = analysePpg({ t: this.t, v: this.v }, FACE_PULSE_RULES);
    return r.valid ? { bpm: Math.round(r.bpm), sqi: r.sqi, beats: r.beats } : null;
  }
  reset() { this.t = []; this.v = []; }
}
