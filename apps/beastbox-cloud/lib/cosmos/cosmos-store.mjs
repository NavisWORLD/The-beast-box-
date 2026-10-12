/**
 * Per-beast cosmos folders in Azure Blob Storage:
 *   beasts/<id>/profile.json   public profile (create-only; identity never rewritten)
 *   beasts/<id>/state.json     loop state (mutable fields only)
 *   beasts/<id>/diary.jsonl    append-only, hash-chained entries
 *   beasts/<id>/latest.json    summary the page reads
 *   beasts/<id>/runs/<tick>.json  simulator receipt for that tick (job id, counts or real error)
 *   cosmos/cursor.json         round-robin position of the scheduled loop
 * Server/CI only.
 */
import {ensureContainer,getBlob,listBlobs,putBlob} from './azure-blob.mjs';
import {validatePublicProfile,cosmosIdFor} from '../../public/spark/cosmos-profile.mjs';
import {genesisForBeast,planGrowthCircuit,stepDiary,summarize,verifyChain} from '../zeref/zeref-diary.mjs';

export const MAX_REGISTERED=2000;
export const DEFAULT_BATCH=6;
const dir=id=>`beasts/${id}`;
const J=o=>JSON.stringify(o,null,1)+'\n';

export async function registerBeast(cfg,raw){
 const v=validatePublicProfile(raw);if(!v.ok)return {ok:false,status:400,error:v.error};
 const p=v.profile;
 await ensureContainer(cfg);
 const existing=await getBlob(cfg,dir(p.id)+'/profile.json');
 if(existing)return {ok:true,status:200,registered:true,already:true,id:p.id};
 const count=(await listBlobs(cfg,'beasts/',{max:MAX_REGISTERED*8})).filter(n=>n.endsWith('/profile.json')).length;
 if(count>=MAX_REGISTERED)return {ok:false,status:503,error:'The cosmos is full for now (free-tier cap).'};
 try{await putBlob(cfg,dir(p.id)+'/profile.json',J({...p,registered_at:new Date().toISOString()}),{ifNoneMatch:'*'});}
 catch(e){if(e.status===409||e.status===412)return {ok:true,status:200,registered:true,already:true,id:p.id};throw e;}
 return {ok:true,status:201,registered:true,already:false,id:p.id};
}

export async function readBeast(cfg,rawId,{limit=12}={}){
 const id=cosmosIdFor(rawId);if(!id)return {ok:false,status:400,error:'Invalid beast id.'};
 const prof=await getBlob(cfg,dir(id)+'/profile.json');
 if(!prof)return {ok:true,registered:false,id};
 const latest=await getBlob(cfg,dir(id)+'/latest.json');
 let profile;try{profile=JSON.parse(prof.text);}catch{profile=null;}
 const pub=profile?{id:profile.id,name:profile.name,provenance:{kind:profile.provenance?.kind,backend:profile.provenance?.backend||null},registered_at:profile.registered_at}:null;
 if(!latest)return {ok:true,registered:true,id,profile:pub,diary:null};
 let diary=null;try{diary=JSON.parse(latest.text);}catch{}
 if(diary?.recent)diary.recent=diary.recent.slice(0,limit);
 return {ok:true,registered:true,id,profile:pub,diary};
}

export async function listRegistered(cfg){
 const names=await listBlobs(cfg,'beasts/',{max:MAX_REGISTERED*8});
 return [...new Set(names.filter(n=>/^beasts\/[^/]+\/profile\.json$/.test(n)).map(n=>n.split('/')[1]))].sort();
}

async function loadBeast(cfg,id){
 const prof=await getBlob(cfg,dir(id)+'/profile.json');if(!prof)throw Error('profile missing');
 const profile=JSON.parse(prof.text);
 const genesis=genesisForBeast(profile);
 const st=await getBlob(cfg,dir(id)+'/state.json');
 const log=await getBlob(cfg,dir(id)+'/diary.jsonl');
 const state=st?JSON.parse(st.text):genesis;
 if(JSON.stringify(state.identity)!==JSON.stringify(genesis.identity))throw Error('identity block changed; refusing to tick');
 const entries=log?log.text.split('\n').filter(Boolean).map(l=>JSON.parse(l)):[];
 const chain=verifyChain(entries,state.identity);
 if(!chain.ok)throw Error('diary chain invalid at tick '+chain.tick);
 if(chain.tick!==state.tick||(chain.head??null)!==state.last_entry_hash)throw Error('state does not match diary head');
 return {profile,state,entries,etags:{state:st?.etag||null,log:log?.etag||null}};
}

/** Round-robin batch: returns plans for up to `batch` registered beasts (Zeref is handled by its own repo diary). */
export async function planBatch(cfg,{batch=DEFAULT_BATCH,skip=[]}={}){
 const ids=(await listRegistered(cfg)).filter(id=>!skip.includes(id));
 if(!ids.length)return {cursor:0,plans:[],skipped:[]};
 const cur=await getBlob(cfg,'cosmos/cursor.json');
 let start=0;try{start=Math.max(0,Number(JSON.parse(cur?.text||'{}').next)||0)%ids.length;}catch{}
 const pick=[];for(let i=0;i<Math.min(batch,ids.length);i++)pick.push(ids[(start+i)%ids.length]);
 const plans=[],skipped=[];
 for(const id of pick){
  try{const {state}=await loadBeast(cfg,id);plans.push({beast_id:id,...planGrowthCircuit(state)});}
  catch(e){skipped.push({beast_id:id,error:String(e.message||e).slice(0,160)});}
 }
 return {cursor:{start,next:(start+pick.length)%ids.length,etag:cur?.etag||null},plans,skipped};
}

/** Apply one tick per planned beast with its simulator receipt (or the real failure). */
export async function applyBatch(cfg,plan,receipts,{now=new Date().toISOString()}={}){
 const byName=new Map((receipts||[]).map(r=>[r.job_name||r.plan_job_name,r]));
 const done=[];
 for(const pl of plan.plans){
  try{
   const {state,entries,etags}=await loadBeast(cfg,pl.beast_id);
   const expected=planGrowthCircuit(state);
   let growth=byName.get(expected.job_name)||{ok:false,error:'simulator step produced no receipt for this beast'};
   if(growth.ok&&growth.job_name!==expected.job_name)growth={ok:false,job_id:growth.job_id,error:'receipt is for a different tick; counts ignored'};
   const {state:next,entry}=stepDiary(state,{now,growth});
   const base=dir(pl.beast_id);
   // append-only: new log = old bytes + one line, guarded by the old etag
   const oldLog=entries.map(e=>JSON.stringify(e)).join('\n');
   await putBlob(cfg,base+'/diary.jsonl',(oldLog?oldLog+'\n':'')+JSON.stringify(entry)+'\n',etags.log?{ifMatch:etags.log}:{ifNoneMatch:'*'});
   await putBlob(cfg,base+'/state.json',J(next),etags.state?{ifMatch:etags.state}:{ifNoneMatch:'*'});
   await putBlob(cfg,base+'/latest.json',J({...summarize(next,[...entries,entry]),generated_at:now}));
   await putBlob(cfg,`${base}/runs/${String(entry.tick).padStart(6,'0')}.json`,J({tick:entry.tick,at:now,receipt:{ok:!!growth.ok,target:growth.target||null,job_id:growth.job_id||null,shots:growth.shots||null,counts:growth.ok?growth.counts:null,error:growth.ok?null:growth.error||null}}));
   done.push({beast_id:pl.beast_id,tick:entry.tick,growth:entry.growth_source.kind,job:entry.growth_source.job_id,new_cells:entry.learning.new_cells,hash:entry.hash.slice(0,16)});
  }catch(e){done.push({beast_id:pl.beast_id,error:String(e.message||e).slice(0,160)});}
 }
 await putBlob(cfg,'cosmos/cursor.json',J({next:plan.cursor.next,updated_at:now}));
 return done;
}

/** Mirror Zeref's repo diary into his storage folder (he is the first registered beast). */
export async function mirrorZeref(cfg,{profile,stateText,logText,latestText}){
 await ensureContainer(cfg);
 const base=dir(profile.id);
 if(!await getBlob(cfg,base+'/profile.json'))await putBlob(cfg,base+'/profile.json',J({...profile,registered_at:new Date().toISOString(),note:'first registered beast; canonical diary also on the zeref-diary branch'}),{ifNoneMatch:'*'}).catch(()=>{});
 await putBlob(cfg,base+'/state.json',stateText);
 await putBlob(cfg,base+'/diary.jsonl',logText,{contentType:'application/x-ndjson'});
 await putBlob(cfg,base+'/latest.json',latestText);
}
