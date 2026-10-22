// Pure mapping from tiny-universe/v1 engine data to view labels (names from Emeth's Tiny Universe bible).
// No bodies are invented here: every label is a function of an engine field.
import {sha256Hex} from './sha256.mjs';
export const BIOMES={ember:'Ember world',paper:'Paper sea',jelly:'Jelly-geyser ocean',sunflower:'Sunflower ring',moss:'Crystal moss',glacier:'Glacier'};
export function biomeOf(p){const t=p.temperature_k,w=p.water;
 if(t>700)return w>=0.6?'paper':'ember';
 if(t<240)return 'glacier';
 if(w>=0.6)return 'jelly';if(w>=0.3)return 'sunflower';return 'moss';}
export function starClass(s){if(s.remnant==='neutron_star')return 'the Clenched Heart';if(s.remnant==='black_hole')return 'the Quiet Door';
 return s.mass_solar<1?'Ember star':s.mass_solar<=8?'Lantern star':'Storm-crowned star';}
export function lifeStage(l){if(l.stage)return l.stage;const c=l.complexity_norm??(1-Math.exp(-l.complexity/2));return c<0.3?'Glimmer':c<0.6?'Drifters':c<0.9?'Choirs':'Dreamers';}
/** First life world (earliest life[].born, then id) gets the placeholder name Hearth. */
export function hearthOf(u){const l=[...u.life].sort((a,b)=>a.born-b.born||a.id.localeCompare(b.id))[0];return l?l.planet:null;}
/** Home (golden cage) = Hearth if life exists, else the most habitable planet. */
export function homeOf(u){const h=hearthOf(u);if(h)return h;const p=[...u.planets].sort((a,b)=>b.habitability-a.habitability||a.id.localeCompare(b.id))[0];return p?p.id:null;}
/** Entangled pairs: a seed-keyed shuffle of planet ids, paired in order. Derived from the IBM seed only. */
export function entangledPairs(u){if(u.pairs)return u.pairs.map(p=>[p.a,p.b,p]);const ids=u.planets.map(p=>p.id).sort();for(let i=ids.length-1;i>0;i--){const j=parseInt(sha256Hex(u.seed+':pair:'+i).slice(0,8),16)%(i+1);[ids[i],ids[j]]=[ids[j],ids[i]];}
 const out=[];for(let i=0;i+1<ids.length;i+=2)out.push([ids[i],ids[i+1]]);return out;}
/** Zeref's perch: the home planet's star, unless it died, then the brightest living star. */
export function zerefStar(u){const home=u.planets.find(p=>p.id===homeOf(u));const s=home&&u.stars.find(x=>x.id===home.star);if(s&&!s.remnant)return s.id;
 const alive=u.stars.filter(x=>!x.remnant).sort((a,b)=>b.luminosity-a.luminosity);return (alive[0]||u.stars[0])?.id??null;}
export const GENESIS_LABEL='Seeded from recorded IBM hardware (ibm_marrakesh)';
export const GROWTH_LABEL='Growth: SIMULATED (Rigetti Bell simulator)';
export const ZEREF_LINES={abiogenesis:'New life. Zeref\u2019s tail curls happy.',storm:'A storm. Zeref puffs up, then waits.',supernova:'A star let go. Zeref goes very still.'};
export const ATLAS_BIOME={ember:'ember_world',paper:'paper_sea',jelly:'jelly_geyser',sunflower:'sunflower_ring',moss:'crystal_moss',glacier:'glacier'};
export function planetFrame(u,p){const v=parseInt(sha256Hex(u.seed+p.id).slice(0,8),16)%4;const h=p.habitability;const st=h<0.0001?'barren':h<0.3?'waking':'living';return ATLAS_BIOME[biomeOf(p)]+'.v'+v+'.'+st;}
export function starFrame(s,tick){if(s.remnant)return (s.remnant==='black_hole'?'quiet_door':'clenched_heart')+'.f'+(tick%4);const c=s.mass_solar<1?'ember_star':s.mass_solar<=8?'lantern_star':'storm_crowned';const L=Math.log10(Math.max(1e-9,s.luminosity));return c+'.lum'+(L<0?0:L<=2?1:2);}
export function threadFrame(p,t){const e=Math.abs(p.sim_E??p.E);return {key:'thread.e'+Math.min(3,Math.floor(e*4))+'.f'+(t%4),alpha:Math.min(1,Math.max(0.2,e))};}
export function hearthFrame(u,p){return p.id===homeOf(u)&&biomeOf(p)==='glacier'?'hearth.'+(u.life.some(l=>l.planet===p.id)?'living':'waking'):null;}
export function stormPhase(s,tick){if(s.lifetime<=1)return tick-s.born<1?'peak':'fade';const q=(tick-s.born)/Math.max(s.lifetime,1);return q<0.15?'spawn':q>=0.75?'fade':'peak';}
export function lifeFrame(l){return lifeStage(l).toLowerCase()+'.m'+(l.traits.motility>=0.5?1:0)+'.s'+(l.traits.sociality>=0.5?1:0)+(l.scarred||l.scars>0?'.scar':'');}
export function stormFrame(s,tick){return 'storm.'+stormPhase(s,tick)+'.v'+(parseInt(sha256Hex(s.id).slice(0,8),16)%2);}
