// Look Closer light rig (Cosmo's open_stage_look pack, LIGHT_RIGS): key / fill / rim / hemisphere for the creature, chosen by time of day.
// SEEDED look data. It follows the camera, so the creature always has the same three-light look. The time of day is the device's own local hour
// (a plain clock reading); where the engine has a real sun for the page, that wins.
import {OPEN_STAGE_RIG} from './open-stage-rig-data.mjs';
export const STAGE_TIMES=Object.freeze(['day','dusk','twilight','night']);
/** local hour (0..24) -> 'day' | 'dusk' | 'twilight' | 'night' */
export function stageTimeOfHour(hour){const h=((Number(hour)%24)+24)%24;if(!Number.isFinite(h))return 'day';if(h>=7.5&&h<17.5)return 'day';if(h>=17.5&&h<19)return 'dusk';if(h>=19&&h<20)return 'twilight';if(h>=6.5&&h<7.5)return 'dusk';return 'night';}
/** the rig for a class ('thin'|'mid'|'thick') and time; the home pocket world is 'thick'. */
/** ambient readability floor by time (skypack night_floor_note tint [0.62,0.76,1.0]); a character must never go black on a phone. SEEDED start values. */
export const STAGE_FLOOR=Object.freeze({colour:'#9EC2FF',day:0.2,dusk:0.6,twilight:1.0,night:1.6});
export function stageRig(cls='thick',time='day'){const c=OPEN_STAGE_RIG.rigs[cls]||OPEN_STAGE_RIG.rigs.thick;const r=c[time]||c.day;
 return {...r,floor:STAGE_FLOOR[c[time]?time:'day'],hemi:{...r.hemi,i:Math.max(r.hemi.i,OPEN_STAGE_RIG.night_floor_hemisphere_min)}};}
/** camera-relative direction (az 0 = from the camera, + toward camera-right, +-180 = from behind; el above the horizon) -> unit vector, camera looking down -z */
export function dirFromCam(az,el){const a=az*Math.PI/180,e=el*Math.PI/180;return [Math.sin(a)*Math.cos(e),Math.sin(e),Math.cos(a)*Math.cos(e)];}
