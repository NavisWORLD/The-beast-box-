// Creature voice lines (Cosmic Emeth's creature_voices_DRAFT.json, approved by Cory Oct 24 2026).
// Pure helpers, no DOM, no clock, no unseeded randomness: every pick is lwStream(seed + key), so the same seed and event give the same line.
// These are ADDITIVE: when a creature or category has no voice line, the caller keeps the existing line (or says nothing).
// Creature behaviour is SEEDED art, not a measured quantum phenotype. No line claims recorded data.
import {lwStream} from './living-world.mjs';
import {VOICES} from './creature-voices-data.mjs';
export {VOICES};
export const VOICE_CATS=Object.freeze(['idle','move','sleep','storm','tap']);
export const ROADSTER_CATS=Object.freeze(['board','cruise','night','storm','stop','other_rides']);
/** Lines for a resident life key (kairo, frost, kittenref, velvetcoil, shardhowl, ...) and a category, or null. */
export function voicePool(key,cat){const p=VOICES.sprites?.[key]?.[cat];return Array.isArray(p)&&p.length?p:null;}
function pick(pool,seed,k){if(!pool)return null;const r=lwStream(String(seed)+':voice:'+k);return pool[Math.floor(r()*pool.length)%pool.length];}
/** One seeded line for a creature, or null so the caller can fall back to its existing line. */
export function creatureVoice(key,cat,seed,n=0){return pick(voicePool(key,cat),seed,key+':'+cat+':'+n);}
/** Roadster line with {beast} (and {other}) filled in, or null. */
export function roadsterVoice(cat,seed,n=0,{beast='Your beast',other='A friend'}={}){const p=VOICES.roadster?.[cat];const l=pick(Array.isArray(p)&&p.length?p:null,seed,'roadster:'+cat+':'+n);return l?l.replace(/\{beast\}/g,beast).replace(/\{other\}/g,other):null;}
/** Which resident speaks next and after how many seconds: both seeded by (seed, n). */
export function voiceTurn(seed,n,count){const r=lwStream(String(seed)+':voice:turn:'+n);const who=Math.floor(r()*Math.max(1,count))%Math.max(1,count);const wait=+(18+r()*22).toFixed(2);return {who,wait};}
/** Category from the resident's real state: storm > sleep > move > idle. */
export function voiceCategory({storming=0,napping=false,moving=false}={}){return storming>.6?'storm':napping?'sleep':moving?'move':'idle';}
/** Species temperament lines (idle|tap) for NEBULA, AURORA, VOID, PLASMA, MEMORY, SIGNAL, STARLIGHT. `family` may be lower case ('nebula'). Null when unknown. */
export function speciesVoice(family,cat,seed,n=0){const k=String(family||'').toUpperCase();return pick(voicePoolOf(VOICES.species_optional?.[k],cat),seed,'species:'+k+':'+cat+':'+n);}
const voicePoolOf=(o,cat)=>{const p=o?.[cat];return Array.isArray(p)&&p.length?p:null;};
/** The ocean's own kind names (fish, ray, whale, jelly, turtle, seabird) to the sea_life keys in the voice data. */
export const SEA_VOICE_KEY=Object.freeze({fish:'fish',ray:'manta ray',whale:'whale',jelly:'jellyfish',turtle:'turtle',seabird:'seabird'});
/** One seeded sea-life line for an ocean kind (or a sea_life key), or null. */
export function seaLifeVoice(kind,seed,n=0){const k=SEA_VOICE_KEY[kind]||kind;return pick(voicePoolOf(VOICES.sea_life,k),seed,'sea:'+k+':'+n);}
