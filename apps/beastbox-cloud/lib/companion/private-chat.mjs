/** Optional private conversation adapter. The model and ownership are separate.
 * It never provisions a world, uploads automatically, calls a model or sends an
 * owner ID as authority. The existing API validates its HttpOnly credential.
 */
const routes=['guest-rawrphos','local-ollama','hf-byok','connected-brain-bay'];
const ownerPattern=/^u_[a-f0-9]{32}$/;
function identity(beast){const id=beast?.qbeast?.profile?.id,seed=beast?.genome?.seed||beast?.seed;if(!/^[a-z0-9][a-z0-9_-]{5,63}$/.test(id||'')||typeof seed!=='string')throw Error('Choose a canonical saved Beast first.');return {id,seed};}
async function api(fetchImpl,path,{body,signal}={}){
 const response=await fetchImpl('/api/cosmos/private/'+path,{method:body?'PUT':'GET',credentials:'same-origin',cache:'no-store',signal,headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});
 const raw=await response.text();if(raw.length>300000)throw Error('Private memory response exceeded its limit.');let value;try{value=JSON.parse(raw);}catch{throw Error('Private memory sent an unreadable response.');}
 if(!response.ok||value.ok===false)throw Error(typeof value.status==='string'?value.status:'Private cloud memory is unavailable.');return value;
}
export async function loadPrivateChat(beast,{fetchImpl=globalThis.fetch,signal,expectedOwner}={}){
 const {id,seed}=identity(beast),auth=await api(fetchImpl,'session',{signal});
 if(auth.authorized!==true||!ownerPattern.test(auth.owner||''))throw Error('Enable this Beast’s private memory in Settings, or pair your own device first.');
 if(expectedOwner&&auth.owner!==expectedOwner)throw Error('Private ownership changed. Restore this device’s own conversation first.');
 const result=await api(fetchImpl,'beasts/'+encodeURIComponent(id),{signal}),record=result.record;
 if(record?.owner!==auth.owner||record.beastId!==id||record.identity?.qbeastId!==id||record.profile?.provenance?.seed!==seed||!Number.isSafeInteger(result.version))throw Error('Private conversation belongs to another owner or creature.');
 const rows=Array.isArray(record.conversations)?record.conversations.filter(row=>['you','beast'].includes(row?.role)&&typeof row.text==='string'&&row.text.length<=6000).slice(-64).map(row=>({role:row.role,text:row.text,model:typeof row.model==='string'?row.model:undefined,route:routes.includes(row.provider)?row.provider:undefined,at:typeof row.clientAt==='number'?row.clientAt:Date.parse(row.at)||undefined,id:typeof row.id==='string'?row.id:undefined})):[];
 return {owner:auth.owner,id,seed,version:result.version,consented:record.sync?.conversationConsent===true,rows};
}
export async function savePrivateExchange(beast,exchange,{fetchImpl=globalThis.fetch,signal,expectedOwner}={}){
 if(!expectedOwner)throw Error('Restore or select your own private conversation before saving.');
 const state=await loadPrivateChat(beast,{fetchImpl,signal,expectedOwner});if(!state.consented)throw Error('Private conversation storage is off in Settings. This exchange remains on the selected device or tab.');
 if(!/^[A-Za-z0-9_-]{8,96}$/.test(exchange?.eventId||'')||!routes.includes(exchange.provider)||typeof exchange.text!=='string'||!exchange.text.trim()||exchange.text.length>400||typeof exchange.reply!=='string'||!exchange.reply.trim()||exchange.reply.length>6000)throw Error('Only a bounded completed conversation can be saved.');
 const result=await api(fetchImpl,'beasts/'+encodeURIComponent(state.id),{signal,body:{eventId:exchange.eventId,version:state.version,action:{kind:'conversation-exchange',text:exchange.text,reply:exchange.reply,provider:exchange.provider,model:exchange.model,clientAt:exchange.at}}});
 if(result.record?.owner!==state.owner||result.record?.beastId!==state.id)throw Error('Private conversation acknowledgement changed identity.');return {owner:state.owner,id:state.id,version:result.version};
}
export function mergePrivateChat(local,remote){
 const result=[],seen=new Set();for(const row of [...remote,...local]){const id=row.id||JSON.stringify([row.role,row.text,row.at,row.model]);if(seen.has(id))continue;seen.add(id);result.push(row);}return result.slice(-24);
}
