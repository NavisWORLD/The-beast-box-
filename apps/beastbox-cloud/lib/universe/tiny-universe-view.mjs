// Pure mapping from tiny-universe/v1 engine data to view labels (names from Emeth's Tiny Universe bible).
// No bodies are invented here: every label is a function of an engine field.
import {sha256Hex} from './sha256.mjs';
export const BIOMES={ember:'Ember world',paper:'Paper sea',jelly:'Jelly-geyser ocean',sunflower:'Sunflower ring',moss:'Crystal moss',glacier:'Glacier'};
export function biomeOf(p){const t=p.temperature_k,w=p.water;
 if(t>700)return w>=0.5?'paper':'ember';
 if(t<240)return 'glacier';
 if(w>0.66)return 'jelly';if(w>=0.33)return 'sunflower';return 'moss';}
export function starClass(s){if(s.remnant==='neutron_star')return 'the Clenched Heart';if(s.remnant==='black_hole')return 'the Quiet Door';
 return s.mass_solar<1?'Ember star':s.mass_solar<=8?'Lantern star':'Storm-crowned star';}
export function lifeStage(l){const c=l.complexity;return c<0.3?'Glimmer':c<0.6?'Drifters':c<0.9?'Choirs':'Dreamers';}
/** First life world (earliest life[].born, then id) gets the placeholder name Hearth. */
export function hearthOf(u){const l=[...u.life].sort((a,b)=>a.born-b.born||a.id.localeCompare(b.id))[0];return l?l.planet:null;}
/** Home (golden cage) = Hearth if life exists, else the most habitable planet. */
export function homeOf(u){const h=hearthOf(u);if(h)return h;const p=[...u.planets].sort((a,b)=>b.habitability-a.habitability||a.id.localeCompare(b.id))[0];return p?p.id:null;}
/** Entangled pairs: a seed-keyed shuffle of planet ids, paired in order. Derived from the IBM seed only. */
export function entangledPairs(u){const ids=u.planets.map(p=>p.id).sort();for(let i=ids.length-1;i>0;i--){const j=parseInt(sha256Hex(u.seed+':pair:'+i).slice(0,8),16)%(i+1);[ids[i],ids[j]]=[ids[j],ids[i]];}
 const out=[];for(let i=0;i+1<ids.length;i+=2)out.push([ids[i],ids[i+1]]);return out;}
/** Zeref's perch: the home planet's star, unless it died, then the brightest living star. */
export function zerefStar(u){const home=u.planets.find(p=>p.id===homeOf(u));const s=home&&u.stars.find(x=>x.id===home.star);if(s&&!s.remnant)return s.id;
 const alive=u.stars.filter(x=>!x.remnant).sort((a,b)=>b.luminosity-a.luminosity);return (alive[0]||u.stars[0])?.id??null;}
export const GENESIS_LABEL='Seeded from recorded IBM hardware (ibm_marrakesh)';
export const GROWTH_LABEL='Growth: SIMULATED (Rigetti Bell simulator)';
export const ZEREF_LINES={abiogenesis:'New life. Zeref\u2019s tail curls happy.',storm:'A storm. Zeref puffs up, then waits.',supernova:'A star let go. Zeref goes very still.'};
