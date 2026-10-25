/** Optional private conversation adapter. The model and ownership are separate.
 * It never provisions a world, uploads automatically, calls a model or sends an
 * owner ID as authority. The existing API validates its HttpOnly credential.
 */
const routes=['guest-rawrphos','local-ollama','hf-byok','connected-brain-bay'];
const ownerPattern=/^u_[a-f0-9]{32}$/;
function identity(beast){const id=beast?.qbeast?.profile?.id,seeds=[beast?.genome?.seed,beast?.seed,beast?.qbeast?.profile?.seed].filter(value=>value!==undefined&&value!==null),seed=seeds[0];if(!/^[a-z0-9][a-z0-9_-]{5,63}$/.test(id||'')||typeof seed!=='string'||!/^[a-f0-9]{16,128}$/i.test(seed)||seeds.some(value=>value!==seed))throw Error('Choose a canonical saved Beast with one matching seed first.');return {id,seed};}
function recordMatches(record,{owner,id,seed}){return record?.owner===owner&&record.beastId===id&&record.identity?.qbeastId===id&&record.identity?.seed===seed&&record.profile?.provenance?.seed===seed;}
function completedExchange(value){if(!/^[A-Za-z0-9_-]{8,96}$/.test(value?.eventId||'')||!routes.includes(value.provider)||typeof value.text!=='string'||!value.text.trim()||value.text.length>8000||typeof value.reply!=='string'||!value.reply.trim()||value.reply.length>6000||value.model!==undefined&&(typeof value.model!=='string'||value.model.length>150)||value.at!==undefined&&(!Number.isSafeInteger(value.at)||value.at<0))throw Error('Only a bounded completed conversation can be saved.');return Object.freeze({eventId:value.eventId,text:value.text,reply:value.reply,provider:value.provider,model:value.model,at:value.at});}
async function api(fetchImpl,path,{body,signal}={}){
 if(signal?.aborted)throw Error('Private conversation request was cancelled.');
 const response=await fetchImpl('/api/cosmos/private/'+path,{method:body?'PUT':'GET',credentials:'same-origin',cache:'no-store',signal,headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});
 const raw=await response.text();if(signal?.aborted)throw Error('Private conversation request was cancelled.');if(raw.length>300000)throw Error('Private memory response exceeded its limit.');let value;try{value=JSON.parse(raw);}catch{throw Error('Private memory sent an unreadable response.');}
 if(!response.ok||value.ok===false)throw Error(typeof value.status==='string'?value.status:'Private cloud memory is unavailable.');return value;
}
export async function loadPrivateChat(beast,{fetchImpl=globalThis.fetch,signal,expectedOwner}={}){
 const {id,seed}=identity(beast),auth=await api(fetchImpl,'session',{signal});
 if(auth.authorized!==true||!ownerPattern.test(auth.owner||''))throw Error('Enable this Beast’s private memory in Settings, or pair your own device first.');
 if(expectedOwner&&auth.owner!==expectedOwner)throw Error('Private ownership changed. Restore this device’s own conversation first.');
 const result=await api(fetchImpl,'beasts/'+encodeURIComponent(id),{signal}),record=result.record;
 if(!recordMatches(record,{owner:auth.owner,id,seed})||!Number.isSafeInteger(result.version)||result.version<1)throw Error('Private conversation belongs to another owner or creature.');
 const rows=Array.isArray(record.conversations)?record.conversations.filter(row=>['you','beast'].includes(row?.role)&&typeof row.text==='string'&&row.text.length<=6000).slice(-64).map(row=>({role:row.role,text:row.text,model:typeof row.model==='string'?row.model:undefined,route:routes.includes(row.provider)?row.provider:undefined,at:typeof row.clientAt==='number'?row.clientAt:Date.parse(row.at)||undefined,id:typeof row.id==='string'?row.id:undefined,cloudImported:true,verified:false,source:'PRIVATE_CLOUD_IMPORT_UNVERIFIED'})):[];
 return {owner:auth.owner,id,seed,version:result.version,consented:record.sync?.conversationConsent===true,rows};
}
export async function savePrivateExchange(beast,exchange,{fetchImpl=globalThis.fetch,signal,expectedOwner}={}){
 if(!ownerPattern.test(expectedOwner||''))throw Error('Restore or select your own private conversation before saving.');
 exchange=completedExchange(exchange);
 const state=await loadPrivateChat(beast,{fetchImpl,signal,expectedOwner});if(!state.consented)throw Error('Private conversation storage is off in Settings. This exchange remains on the selected device or tab.');
 const result=await api(fetchImpl,'beasts/'+encodeURIComponent(state.id),{signal,body:{expectedOwner:state.owner,expectedSeed:state.seed,eventId:exchange.eventId,version:state.version,action:{kind:'conversation-exchange',text:exchange.text,reply:exchange.reply,provider:exchange.provider,model:exchange.model,clientAt:exchange.at}}});
 if(!recordMatches(result.record,state)||!Number.isSafeInteger(result.version)||result.version<state.version)throw Error('Private conversation acknowledgement changed identity or version.');return {owner:state.owner,id:state.id,seed:state.seed,version:result.version};
}
export function mergePrivateChat(local,remote){const result=[],seen=new Set();for(const row of [...remote,...local]){const id=row.id||JSON.stringify([row.role,row.text,row.at,row.model]);if(seen.has(id))continue;seen.add(id);result.push(row);}return result.slice(-24);}

/** Bounded in-memory queue. Explicit retry retains immutable event IDs.
 * Closing/minimizing does not unmount it; a full page unload discards retry
 * metadata while the separately saved local transcript remains.
 */
export function createPrivateChatQueue({fetchImpl=globalThis.fetch,onChange=()=>{},limit=8}={}){
 const maximum=Number.isInteger(limit)&&limit>0?Math.min(limit,8):8,queues=new Map();let selected=null,running=null,lastSaved=null,disposed=false;
 function binding(value){const {id,seed}=identity(value?.beast);if(!ownerPattern.test(value?.owner||'')||typeof value.key!=='string'||!value.key||value.key.length>160)throw Error('Restore your selected private conversation before saving.');return {key:value.key,owner:value.owner,id,seed,scope:JSON.stringify([value.key,value.owner,id,seed]),beast:{qbeast:{profile:{id,seed}},genome:{seed}},enabled:value.enabled===true,consented:value.consented===true};}
 function snapshot(){const queue=queues.get(selected?.scope);return {busy:!!running&&running.scope===selected?.scope,pending:queue?.items.length||0,paused:queue?.paused===true,error:queue?.error||null,lastSavedEvent:lastSaved&&lastSaved.scope===selected?.scope?lastSaved.eventId:null};}
 function emit(){if(!disposed)onChange(snapshot());}
 function pause(){if(!running)return;const old=running;running=null;old.controller.abort();const queue=queues.get(old.scope);if(queue?.items.length)queue.paused=true;}
 async function drain(){
  if(disposed||running||!selected?.enabled||!selected.consented)return;
  const scope=selected.scope,queue=queues.get(scope);if(!queue?.items.length||queue.paused)return;
  const run={scope,controller:new AbortController()};running=run;emit();
  try{while(queue.items.length){const item=queue.items[0];await savePrivateExchange(item.beast,item.exchange,{fetchImpl,signal:run.controller.signal,expectedOwner:item.owner});
   if(disposed||running!==run||run.controller.signal.aborted||selected?.scope!==scope||!selected.enabled||!selected.consented)return;
   queue.items.shift();queue.error=null;lastSaved={scope,eventId:item.exchange.eventId};emit();
  }}catch(error){if(!disposed&&running===run){queue.paused=true;queue.error=error instanceof Error?error.message:'Private cloud write failed.';}}
  finally{if(running===run){running=null;if(!queue.items.length)queues.delete(scope);emit();}}
 }
 return {
  snapshot,
  select(value){if(disposed)return;const next=value?binding(value):null;if(running&&(!next||next.scope!==running.scope||!next.enabled||!next.consented))pause();selected=next;const queue=queues.get(next?.scope);if(next?.consented&&queue)queue.error=null;emit();void drain();},
  enqueue(value){if(disposed)throw Error('Private saving is closed.');const saved=binding(value),exchange=completedExchange(value.exchange);if(saved.scope!==selected?.scope)throw Error('Private saving no longer belongs to this owner or selection.');if(!selected.enabled||!selected.consented)throw Error('Private conversation saving is off. The completed reply stays in local storage.');
   let queue=queues.get(saved.scope);const duplicate=queue?.items.find(item=>item.exchange.eventId===exchange.eventId);if(duplicate){if(JSON.stringify(duplicate.exchange)!==JSON.stringify(exchange))throw Error('Private event ID was reused with another exchange.');return;}
   if([...queues.values()].reduce((total,item)=>total+item.items.length,0)>=maximum)throw Error('The private save queue is full. Retry pending saves first.');
   if(!queue){queue={items:[],paused:false,error:null};queues.set(saved.scope,queue);}queue.items.push({owner:saved.owner,beast:saved.beast,exchange});emit();void drain();
  },
  async retry(){if(disposed||running||!selected?.enabled||!selected.consented)return;const queue=queues.get(selected.scope);if(!queue?.items.length)return;queue.paused=false;queue.error=null;emit();await drain();},
  dispose(){disposed=true;pause();selected=null;queues.clear();},
 };
}
