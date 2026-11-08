// Seeded sha256 stream for the Genesis look. Presentation only. Unseeded draws are not used.
import {sha256Hex} from '../universe/sha256.mjs';

/** Unit float in [0,1) from a labelled sha256 key. */
export function stream01(key:string){
 const h=sha256Hex(String(key));
 return parseInt(h.slice(0,8),16)/4294967296;
}
/** Spatial value in [0,1) broken by one seeded phase. Not a second height field. */
export function seededNoise(seed:string,x:number,z:number){
 const p=stream01(seed+':noise');
 const s=Math.sin(x*12.9898+z*78.233+p*43.758)*43758.5453;
 return s-Math.floor(s);
}
