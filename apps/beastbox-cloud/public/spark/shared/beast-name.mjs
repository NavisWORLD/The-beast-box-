// ONE source of truth for the active beast's display name (Oct 23 2026, Emeth's first-visitor audit).
// Order: the saved active Spark Beast (its own chosen name, else its genome name for its current stage, else its QBEAST
// profile name), then the seeded Beast Cage companion this device was given, then a neutral phrase. Never a hardcoded name.
export const SESSION_KEY='beastbox-companion-session-v1';
export const COMPANION_KEY='beastbox-active-creature-v1';
const clean=(v)=>typeof v==='string'&&v.trim()?v.trim().slice(0,32):null;
export function beastDisplayName(beast){if(!beast)return null;const n=beast.genome?.names||{};
 return clean(beast.displayName)||clean(n[String(beast.stage)])||clean(n[beast.stage])||clean(beast.qbeast?.profile?.name)||clean(n['1'])||clean(n[1])||null;}
function readJson(storage,key){try{const raw=storage?.getItem(key);return raw?JSON.parse(raw):null;}catch{return null;}}
export function readActiveBeast(storage){const s=readJson(storage,SESSION_KEY);return s?.beast||null;}
/** {name, source:'saved'|'seeded'|null}. 'seeded' = the device's seeded Beast Cage companion (no saved Spark Beast yet). */
export function activeBeastName(storage){const b=beastDisplayName(readActiveBeast(storage));if(b)return {name:b,source:'saved'};
 const c=readJson(storage,COMPANION_KEY);const cn=clean(c?.name);return cn?{name:cn,source:'seeded'}:{name:null,source:null};}
export function nameOr(n,fallback='your beast'){return n||fallback;}
/** Emeth's site_labels.json templates: {beast} becomes the active beast name. */
export function fillBeast(t,name){return String(t||'').split('{beast}').join(nameOr(name));}
