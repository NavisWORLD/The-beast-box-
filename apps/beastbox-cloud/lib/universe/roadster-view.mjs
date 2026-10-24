/**
 * Roadster · SEEDED: view-only helpers for Cosmo's roadster pack (public/universe/livingworld/roadster/).
 * The roadster is a VISUAL swap for the spawned-in traveler. It adds no physics: the traveler's existing walkOn/stepMover motion drives it,
 * and these functions only turn that real speed into wheel spin, body bob, lamp and underglow numbers. Cosmo's numbers are SIMULATED
 * suggestions (hand-tuned, not measured); nothing here was measured on a device. No clock, no Math.random: time `t` is passed in.
 * Pack provenance: roadster.glb / roadster_rig.json / roadster_palette.json by Cosmo (see README_cosmo.md beside them).
 */
export const ROADSTER_LABEL = 'Roadster · SEEDED';
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

/** Body variant: 0 = cherry (fixed default, always the first), 1..3 = seeded from a seeded stream value r in [0,1). Cherry stays the most common look. */
export function bodyVariantIndex(r) { const v = Number.isFinite(r) ? r : 0; return v < 0.4 ? 0 : 1 + Math.min(2, Math.floor((v - 0.4) / 0.2)); }

/** Wheel spin (rad/s) from forward speed (m/s) and wheel radius (m): omega = v / r. */
export function wheelOmega(v, r = 0.32) { return v / Math.max(0.05, r); }

/** Ackermann steering angle (rad) from a steer input in [-1,1]; max 28 deg. */
export function steerAngle(input) { return clamp(input, -1, 1) * (28 * Math.PI / 180); }

/** Driving state from speed (m/s): 'idle' below 0.15, else 'drive' (boost is not wired: no second motion system). */
export function driveState(v) { return Math.abs(v) < 0.15 ? 'idle' : 'drive'; }

/** Body bob (m) at time t (s) for speed v (m/s), from the rig's drive and idle numbers. reduced = prefers-reduced-motion: no bob. */
export function bodyBob(v, t, reduced = false) {
  if (reduced) return 0;
  const sp = Math.abs(v);
  if (driveState(v) === 'idle') return 0.004 * Math.sin(t * Math.PI * 2 * 0.5);
  const amp = 0.008 + 0.006 * clamp(sp / 6, 0, 1), hz = Math.min(3.5, 1.2 + 0.25 * sp);
  return amp * Math.sin(t * Math.PI * 2 * hz);
}

/** Headlamp strength (linear) and colour hex from state and whether it is night (0..1). Colours reuse the landscape lamp ramp. */
export function headlamp(state, night, t) {
  const drive = state === 'drive';
  const base = drive ? 1.0 : 0.55, amp = drive ? 0.05 : 0.08, hz = drive ? 0.0 : 0.35;
  const k = 0.35 + 0.65 * clamp(night, 0, 1); // dimmer by day, full at night
  return { intensity: (base + amp * Math.sin(t * Math.PI * 2 * hz)) * k, hex: drive ? '#FFD9A0' : '#FFBE6E' };
}

/** Underglow colour and pulse (0..1) by state: idle = wonder, drive = curious (cage mood colours). */
export function underglow(state, t) {
  const drive = state === 'drive';
  const period = drive ? 1.1 : 2.4, lo = drive ? 0.5 : 0.35, hi = drive ? 1.0 : 0.7;
  return { hex: drive ? '#5fe7ff' : '#b48cff', pulse: lo + (hi - lo) * (0.5 + 0.5 * Math.sin(t * Math.PI * 2 / period)) };
}
