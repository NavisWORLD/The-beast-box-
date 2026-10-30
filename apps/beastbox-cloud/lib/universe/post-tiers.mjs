// P1 quality tiers (LOW / MED / HIGH / GOD). Values come only from Cosmo's p1post pack (SEEDED); nothing here is hand-tuned.
// Auto-detect from device hints, plus a manual override remembered per device. Pure except for the storage the caller passes in.
import {P1POST} from './data/p1post.mjs';
export const TIERS=Object.freeze(['LOW','MED','HIGH','GOD']);
export const QUALITY_KEY='beastbox.quality.v1';
export const DEFAULT_TIER='MED';
/** Pick a tier from device hints: {phone, cores, memoryGB, dpr, reducedMotion, softGL}. MED is the phone default; GOD is desktop-class only. */
export function autoTier(h={}){
  if(h.softGL)return 'LOW';
  if(h.reducedMotion)return 'LOW';
  const cores=+h.cores||4,mem=+h.memoryGB||4;
  if(h.phone)return (cores<=4||mem<=3)?'LOW':'MED';
  if(cores>=8&&mem>=8)return 'GOD';
  if(cores>=6)return 'HIGH';
  return 'MED';
}
export function readTierOverride(storage){try{const v=storage?.getItem(QUALITY_KEY);return TIERS.includes(v)?v:null;}catch{return null;}}
export function writeTierOverride(storage,tier){try{if(tier&&TIERS.includes(tier))storage?.setItem(QUALITY_KEY,tier);else storage?.removeItem(QUALITY_KEY);}catch{}return TIERS.includes(tier)?tier:null;}
/** The tier in force: a saved override wins, else auto. */
export function activeTier(storage,hints){return readTierOverride(storage)||autoTier(hints);}
/** Next tier when the chip is tapped (LOW -> MED -> HIGH -> GOD -> LOW). */
export function nextTier(t){const i=TIERS.indexOf(t);return TIERS[(i+1)%TIERS.length];}
/** The pack settings for a tier (a frozen copy of the pack entry). */
export function tierSettings(t){return P1POST.tiers[TIERS.includes(t)?t:DEFAULT_TIER];}
export function qualityLabel(t){return `Quality: ${TIERS.includes(t)?t:DEFAULT_TIER}`;}
/** Bloom threshold in the units UnrealBloomPass sees (scene luminance before exposure): pack threshold is after exposure. */
export function bloomThresholdPreExposure(t){const s=tierSettings(t);return s.bloom.threshold/(s.optics.exposure||1);}
