// Visual Life Pass: authored text only. Every line comes from visual_life_labels.json (via the generated data file); this module fills {placeholders} with ENGINE numbers.
// A line whose placeholder has no real number is dropped (receipt() returns null): no number, no claim.
import {VL_DATA} from './visual-life-labels-data.mjs';
export const VL_TEXT=VL_DATA;
/** Output labels the code stands behind. SIMULATED = stepped by the world loop. SEEDED = placement or look from the seeded stream. */
export const VL_OUTPUT_LABELS=Object.freeze({foam:'SIMULATED',caustics:'SIMULATED',glitter:'SIMULATED',haze_fog:'SIMULATED',boom:'SIMULATED',storm:'SIMULATED',growth:'SIMULATED',landscape_placement:'SEEDED',below_waterline_forms:'SEEDED',palette:'SEEDED'});
const fmt=(v)=>typeof v==='number'?(Math.abs(v)>=10?v.toFixed(0):v.toFixed(2)):String(v);
/** receipt('foam',{wind:.42}) -> 'Foam drifts with wind 0.42'; null if the line is unknown or any placeholder is missing / not finite. */
export function receipt(key,vals={}){
 const line=VL_TEXT.hud_receipts?.[key];if(!line)return null;let ok=true;
 const out=line.replace(/\{(\w+)\}/g,(m,k)=>{const v=vals[k];if(v==null||(typeof v==='number'&&!Number.isFinite(v))){ok=false;return m;}return fmt(v);});
 return ok?out:null;
}
/** Chip text: the receipt plus the honesty label of its output. */
export const receiptChip=(key,out,vals)=>{const r=receipt(key,vals);return r?r+' · '+VL_OUTPUT_LABELS[out]:null;};
