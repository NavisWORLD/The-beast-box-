/** Bridge → native cartridge import. Reads the exact QBEAST the bridge already
 * saved on this device and passes it through the existing identity-checked
 * handoff (no new identity, no seed invention). A visiting Beast never writes
 * journeys into the active session Beast. */
import {createGameHandoff} from './game-handoff.mjs';
export const NO_CARD='This Beast was born in the bridge and has no cartridge card yet, so the Game Boy cartridge cannot verify it. Spark Beasts play here directly; bridge Beasts can use the web Synapse share under Advanced settings.';
export const PUBLIC_KEY='beastbox-quantum-beast-public-v1';
export function importIdFromSearch(search){const id=new URLSearchParams(search||'').get('import');return id&&/^[A-Za-z0-9_-]{4,80}$/.test(id)?id:null;}
export function readImportedBeast(storage,id){
 const raws=[storage.getItem(PUBLIC_KEY+'-creature-'+id),storage.getItem(PUBLIC_KEY)].filter(Boolean);
 for(const raw of raws){
  let text;try{text=JSON.parse(raw).text;}catch{continue;}
  if(typeof text!=='string')continue;
  const qbeast=JSON.parse(text);if(qbeast?.profile?.id!==id)continue;
  const beast={qbeast,seed:qbeast.profile.seed,displayName:qbeast.profile.name||'Beast',visiting:true};
  try{createGameHandoff(beast);}catch{throw Error(NO_CARD);}// the cartridge must verify this exact identity
  return beast;
 }
 throw Error('That Beast is not saved on this device yet. Open it in the bridge first.');
}
