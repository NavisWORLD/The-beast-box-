/** The ONE light rig (P1). DERIVED from oneSunAt() output (`os`: {day, elevationDeg, sky}) and the pack tier exposure.
 * FIX_NOTES_43c74d3 values (sun 3.03 x day once, hemi .6 x day + .15).
 * Never a second clock or night factor: `day` is the one-sun value the view already computed. */
export function lightRigFor(os, exposure = 0.85) {
  const day = Math.min(1, Math.max(0, +os?.day || 0));
  const z = os?.sky?.zenith || [0, 0, 0], h = os?.sky?.horizon || [0, 0, 0];
  return {label: 'DERIVED', sunIntensity: 3.03 * day, hemiIntensity: .6 * day + .15, hemiColor: [0, 1, 2].map(i => (z[i] + h[i]) / 2), exposure, sunElevationDeg: +os?.elevationDeg || 0};
}
