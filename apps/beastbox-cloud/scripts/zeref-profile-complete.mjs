#!/usr/bin/env node
/**
 * One-time completion of the public cosmos profile for bb-deada969 (Zeref).
 *
 * Why this exists: the registered profile for this beast is a stub carrying
 * only schema, id, name and provenance kind/backend (written by an early
 * mirror). Registration is create-only, so the stub can never be repaired
 * through the public route, and the growth loop's genesis validation rejects
 * it ("Not a public cosmos profile"), so this beast never ticks.
 *
 * This script writes the completed cosmos-beast-public/v1 profile from facts
 * already on record, and nothing else:
 *   - identity and genome traits: lib/companion/zeref-genome.ts
 *     (Cinder Drift, ember dragonling, flame ears/tail, bat wings, stripes)
 *   - provenance: the recorded genome-birth run on ibm_fez
 *     (job db4q484vf2bc73cuuuag, bell-xx counts digest on record) and the
 *     genome seed the beast id itself is derived from
 *   - game stats: the beast's own recorded stats from its QBEAST1 birth file
 *     (public/spark/zeref-live-20261010/qbeast.json, game.stats)
 * Stats were delegated to Emeth by the owner on 2026-10-27; the recorded
 * birth stats were used, not invented.
 *
 * Safety: the profile is validated with the repo's own validator and its
 * genesis identity is computed before anything is written. If a state.json
 * already exists whose identity block does not match this profile's genesis,
 * the script writes nothing and stops. This script never ticks the beast;
 * the scheduled diary loop does the ticking.
 */
import {createHash} from 'node:crypto';
import {storageConfig,getBlob,putBlob} from '../lib/cosmos/azure-blob.mjs';
import {validatePublicProfile} from '../public/spark/cosmos-profile.mjs';
import {genesisForBeast} from '../lib/zeref/zeref-diary.mjs';

const PROFILE={
 schema:'cosmos-beast-public/v1',
 id:'bb-deada969',
 name:'Zeref',
 provenance:{
  kind:'recorded-quantum-genome',
  backend:'ibm_fez',
  job_id:'db4q484vf2bc73cuuuag',
  counts_sha256:'151c96aed2079f274a3b3b0bf725d5f27b8bda0d83164c335d1b203bc5dd0bdc',
  seed:'8e2e927e2cfaf489cb7c10172836286bb08869cfff0c2508b5c6371e052e54ed'
 },
 traits:{
  island:'Cinder Drift',element:'ember',body:'dragonling',ears:'flame',
  tail:'flame',wings:'bat',pattern:'stripes',eye_style:'round',mouth:'open',
  stats:{hp:44,energy:63,signal:33,memory:44,resonance:42,agility:44,
   chaos:47,stability:68,curiosity:52,evolution:63}
 }
};

const cfg=storageConfig();
if(!cfg){console.log('COSMOS storage not configured (set AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_CONTAINER_SAS_URL); nothing written.');process.exit(0);}
const v=validatePublicProfile(PROFILE);
if(!v.ok){console.error('STOP: completed profile does not validate: '+v.error);process.exit(1);}
const genesis=genesisForBeast(PROFILE);
const base='beasts/'+PROFILE.id;
const cur=await getBlob(cfg,base+'/profile.json');
let registeredAt=null;
if(cur){
 let p=null;try{p=JSON.parse(cur.text);}catch{}
 registeredAt=p?.registered_at||null;
 console.log('current profile: present, sha256 '+createHash('sha256').update(cur.text).digest('hex').slice(0,16)
  +(p?(', fields: '+JSON.stringify({prov:Object.keys(p.provenance||{}),stats:Object.keys(p.traits?.stats||{})})):', unparseable'));
}else{
 console.log('current profile: absent');
}
const st=await getBlob(cfg,base+'/state.json');
if(st){
 const state=JSON.parse(st.text);
 if(JSON.stringify(state.identity)!==JSON.stringify(genesis.identity)){
  console.log('STOP: an existing state identity does not match this profile genesis. Nothing written.');
  console.log('existing identity: '+JSON.stringify(state.identity).slice(0,300));
  console.log('candidate identity: '+JSON.stringify(genesis.identity).slice(0,300));
  process.exit(1);
 }
 console.log('existing state identity matches this genesis; completion is safe.');
}
await putBlob(cfg,base+'/profile.json',JSON.stringify({...v.profile,registered_at:registeredAt||new Date().toISOString()},null,1)+'\n');
const back=await getBlob(cfg,base+'/profile.json');
const v2=back?validatePublicProfile(JSON.parse(back.text)):{ok:false};
console.log('PROFILE_COMPLETED '+JSON.stringify({id:PROFILE.id,valid:v2.ok,
 identity_digest:genesis.identity.recorded_digest.slice(0,16),
 signals:genesis.signals,
 sha256:createHash('sha256').update(back.text).digest('hex')}));
