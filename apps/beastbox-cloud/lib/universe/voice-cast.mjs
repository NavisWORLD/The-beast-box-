// Who can speak in the living world, and the roadster voice sequencing. Pure helpers: no DOM, no clock, no random source; every pick comes from
// creature-voices.mjs (seeded). A creature only speaks when it is really on screen: the five artist residents, and the ACTIVE beast when it is one
// of the named characters (Kitten, Zeref, Zeref64) or has a species line. Nothing is shown for a creature that is not there.
import {RESIDENT_LIFE_KEY} from './sprite-life.mjs';
import {creatureVoice,speciesVoice,VOICES} from './creature-voices.mjs';
/** Display name -> voice key for the named characters that can be the active beast. */
export const BEAST_VOICE_KEY=Object.freeze({kitten:'kitten',zeref:'zeref',zeref64:'zeref64'});
/** 'Zeref · Nightcat Dragon' -> 'zeref'; 'Zeref64' -> 'zeref64'; an own-named beast ('Duskscale') -> null. */
export function beastVoiceKey(name){const first=String(name||'').split(/\s+·\s+/)[0].toLowerCase().replace(/[^a-z0-9]/g,'');return BEAST_VOICE_KEY[first]||null;}
/** Species key ('nebula' or 'NEBULA') that has species lines, else null. */
export function speciesVoiceKey(family){const k=String(family||'').toUpperCase();return VOICES.species_optional?.[k]&&k[0]!=='_'?k:null;}
/** The speakers, in a fixed order: residents (art order of `residentNames`), then the active beast when it has a voice. */
export function voiceCast(residentNames,beastName,family){
 const out=[];for(const n of residentNames||[]){const key=RESIDENT_LIFE_KEY[n];if(key)out.push({name:n,key,species:null,beast:false});}
 const bk=beastVoiceKey(beastName),sk=speciesVoiceKey(family);
 if(bk||sk)out.push({name:String(beastName||'Your beast').split(/\s+·\s+/)[0],key:bk,species:sk,beast:true});
 return out;
}
/** A speaker's line for a category. Residents and named characters use their own pool; a beast with a species alternates its character line and its species idle line. */
export function castLine(sp,cat,seed,n=0){
 if(!sp)return null;
 const own=sp.key?creatureVoice(sp.key,cat,seed,n):null;
 const spc=sp.species&&(cat==='idle'||cat==='tap')?speciesVoice(sp.species,cat,seed,n):null;
 const c=[own,spc].filter(Boolean);return c.length?c[n%c.length]:null;
}
/**
 * Roadster voice sequencer (pure state machine, time comes only from dt). Emits a category once per event:
 *  board (storm > night > board) when the car is entered; other_rides ~6 s later if a resident is close (the {other} name is that resident);
 *  cruise once after 10 s of real driving at speed; stop after a real drive when the car is parked.
 * `step` returns {cat,other?} or null.
 */
export function createRoadsterVoice(){
 let was=false,fast=false,since=0,drive=0,cruised=false,otherDone=false,near=null;
 return {step(dt,{wantCar,carV=0,storming=0,night=false,nearResident=null}){
  if(!wantCar){was=false;fast=false;since=0;drive=0;cruised=false;otherDone=false;near=null;return null;}
  if(!was){was=true;since=0;drive=0;cruised=false;otherDone=false;near=nearResident;return {cat:storming>.6?'storm':night?'night':'board'};}
  since+=dt;const v=Math.abs(carV);
  if(v>2){fast=true;drive+=dt;}
  if(!otherDone&&near&&since>=6){otherDone=true;return {cat:'other_rides',other:near};}
  if(!cruised&&drive>=10){cruised=true;return {cat:'cruise'};}
  if(fast&&v<.3){fast=false;drive=0;cruised=false;return {cat:'stop'};}
  return null;}};
}
