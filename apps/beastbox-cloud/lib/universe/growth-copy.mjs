// Growth nodes UI copy (PR 3). Emeth's words, verbatim: GROWTH_LABELS (site_labels.json growth_nodes), LW_LINES.zoom_growth / growth_nodes / one_cage.
// Everything shown is DERIVED from growthNodeState (stage, generation, scarred, drive); this module only picks and fills text. Pure: no Math.random, no clock.
// Honesty: placement is SEEDED, growth is SIMULATED. Never "recorded growth", never "live quantum".
import {LW_LINES} from './living-world-lines.mjs';
import {lwStream} from './living-world.mjs';
import {NODE_STAGES,HOME_WORLD_LABEL} from './seeded-growth-nodes.mjs';
import {GROWTH_LABELS} from './growth-labels-data.mjs';
export {GROWTH_LABELS,HOME_WORLD_LABEL};
/** UI stage words (Emeth's note in site_labels.json). */
export const STAGE_WORDS=Object.freeze({sprout:'Sprout',tuft:'Tuft',full:'Full',bloom:'Bloom',gold:'Gold',shed:'Shed'});
/** Drive thresholds for Emeth's fast_tick / slow_tick lines (growthDrive is clamped 0.1..1.6, neutral 0.5 + sim_E). */
export const FAST_DRIVE=1.3,SLOW_DRIVE=0.3;
const pick=(arr,key)=>arr[Math.floor(lwStream(key)()*arr.length)%arr.length];
const cap1=s=>s.charAt(0).toUpperCase()+s.slice(1);
/** The stage most nodes are in (ties: the earlier life stage). null when there are no nodes. */
export function dominantStage(nodes){
 const c={};for(const n of nodes||[])if(NODE_STAGES.includes(n.stage))c[n.stage]=(c[n.stage]||0)+1;
 let best=null;for(const s of NODE_STAGES)if(c[s]&&(best==null||c[s]>c[best]))best=s;return best;
}
/** Emeth key for a stage: a node in its second life or later that is back at sprout/tuft reads as 'renewal'. */
export function growthKey(stage,nodes){
 if(!stage)return null;
 if((stage==='sprout'||stage==='tuft')&&(nodes||[]).some(n=>n.stage===stage&&(n.generation||0)>=1))return 'renewal';
 return stage;
}
/** Short derived planet words for the {planet} slot: 'the home world' for the planet the beast lives on, else 'planet <id tail>'. */
export function planetWords(planetId,homePlanetId){
 if(planetId&&planetId===homePlanetId)return 'the home world';
 const t=String(planetId||'').split('-').pop();return t?'planet '+t:'this planet';
}
/** zoom_growth line for the zoom-in toast. {planet} is filled by code from the node state; sentences start capitalised. */
export function growthZoomLine(nodes,planetWordsText,seed,n=0){
 const key=growthKey(dominantStage(nodes),nodes);const pool=key&&LW_LINES.zoom_growth?.[key];if(!pool)return null;
 const t=Array.isArray(pool)?pick(pool,`${seed}:zoomgrowth:${key}:${n}`):pool;
 return cap1(t.split('{planet}').join(planetWordsText||'this planet'));
}
/** growth_nodes line keyed by what the nodes are doing. {beast} = the active beast's name. Scarred beats stage; fast/slow tick only when the SIMULATED drive is extreme. */
export function growthNoteKey(nodes){
 if(!nodes||!nodes.length)return null;
 const st=dominantStage(nodes);if(!st)return null;
 if(nodes.some(n=>n.scarred&&n.stage===st))return 'scarred';
 return growthKey(st,nodes);
}
export function growthDriveKey(nodes){
 if(!nodes||!nodes.length)return null;const d=nodes[0].drive;return typeof d!=='number'?null:d>=FAST_DRIVE?'fast_tick':d<=SLOW_DRIVE?'slow_tick':null;
}
export function growthNoteLine(key,beast,seed,n=0){
 const pool=key&&LW_LINES.growth_nodes?.[key];if(!Array.isArray(pool))return null;
 return pick(pool,`${seed}:growthnote:${key}:${n}`).split('{beast}').join(beast||'Your beast');
}
/** HUD chip: "Growth nodes · SEEDED" plus the derived stage word. The explainer is Emeth's, verbatim. */
export function growthChip(nodes){
 const st=dominantStage(nodes);if(!st)return null;
 const home=(nodes||[]).some(n=>n.home_exception);
 return {text:`${GROWTH_LABELS.label} · ${STAGE_WORDS[st]}`,stage:st,explainer:GROWTH_LABELS.explainer,homeText:home?HOME_WORLD_LABEL:null};
}
/** One-cage lines for the site menu (Emeth). */
export const ONE_CAGE=Object.freeze({footer:LW_LINES.one_cage.footer,menu_hint:LW_LINES.one_cage.menu_hint,honesty:LW_LINES.one_cage.honesty});
