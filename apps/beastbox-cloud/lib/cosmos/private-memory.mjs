/** Server-only private worlds backed by the existing Azure Blob client.
 * A create-only full commit and one ETag-protected head are the transaction.
 * An orphan commit never changes live state; the same event can resume safely.
 */
import {createHash,randomUUID} from 'node:crypto';
import {canonicalJson} from '../../public/spark/genome.mjs';
import {validatePublicProfile,cosmosIdFor} from '../../public/spark/cosmos-profile.mjs';
import {checkedSpark} from '../../public/spark/identity.mjs';
import {createGameHandoff} from '../companion/game-handoff.mjs';
import {verifyWorkerReceipt} from './private-qvm.mjs';
import {countsFeatures} from '../zeref/zeref-diary.mjs';
import {validSubject} from './private-owner.mjs';
import {getBlob,putBlob,listBlobs,deleteBlob} from './azure-blob.mjs';
export const PRIVATE_SCHEMA='private-cosmos/v1';
export const LIMITS=Object.freeze({users:100,beasts:4,commits:256,bytes:262144,conversations:64,memory:128,events:64});
const hash=value=>createHash('sha256').update(canonicalJson(value)).digest('hex');
const fail=(code,status=400)=>Object.assign(Error(code),{code,status});
const eventId=value=>typeof value==='string'&&/^[A-Za-z0-9_-]{8,96}$/.test(value)?value:null;
const json=value=>canonicalJson(value)+'\n';
const clone=value=>JSON.parse(JSON.stringify(value));
function parse(blob){try{if(!blob||blob.text.length>LIMITS.bytes*2)throw Error();return JSON.parse(blob.text);}catch{throw fail('CORRUPT_RECORD',422);}}
export function azurePrivateIO(cfg){return {get:name=>getBlob(cfg,name),put:(name,text,options)=>putBlob(cfg,name,text,options),list:prefix=>listBlobs(cfg,prefix,{max:3000}),delete:(name,options)=>deleteBlob(cfg,name,options)};}
function empty(profile,owner){return {schema:PRIVATE_SCHEMA,owner,beastId:profile.id,profile,identity:{qbeastId:profile.id,seed:profile.provenance.seed,provenance:profile.provenance,authority:'PRIVATE_MEMORY_ONLY',genesisValidation:'CLIENT_CLAIM_UNVERIFIED'},memory:[],conversations:[],personalityState:{source:'bounded classical interaction rules',curiosity:50,trust:0,engagement:0},sensorHistory:[],quantumGenesis:{source:profile.provenance,verification:'CLIENT_CLAIM_UNVERIFIED',freshHardwareJob:false},simulationReceipts:[],learningEvents:[],evolutionHistory:[],gameCheckpoints:[],model:{provider:null,model:null},growth:{optedIn:false,schedule:false,tick:0,status:'OFF',jobs:0,lastAttempt:null},sync:{version:1,recentEvents:{},migrations:[],conversationConsent:false}};}
function append(rows,value,max){return [...rows,value].slice(-max);}
function text(value,max=2000){if(typeof value!=='string'||!value.trim()||value.length>max||/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(value))throw fail('INVALID_TEXT');return value;}
function apply(record,action,at,event){
 const next=clone(record);
 switch(action?.kind){
  case 'memory':next.memory=append(next.memory,{text:text(action.text),at,source:'OWNER_AUTHORIZED_IMPORT_UNVERIFIED'},LIMITS.memory);break;
  case 'conversation':if(!['you','beast'].includes(action.role))throw fail('INVALID_ROLE');next.conversations=append(next.conversations,{role:action.role,text:text(action.text,6000),at,source:'OWNER_AUTHORIZED_IMPORT_UNVERIFIED',model:typeof action.model==='string'?action.model.slice(0,150):null},LIMITS.conversations);next.personalityState.engagement=Math.min(100,next.personalityState.engagement+1);break;
  case 'chat-consent':if(typeof action.enabled!=='boolean')throw fail('INVALID_CHAT_CONSENT');next.sync.conversationConsent=action.enabled;break;
  case 'conversation-exchange':{
   if(next.sync.conversationConsent!==true)throw fail('CONVERSATION_NOT_OPTED_IN',403);
   if(!['guest-rawrphos','local-ollama','hf-byok','connected-brain-bay'].includes(action.provider))throw fail('INVALID_MODEL');
   const saying=text(action.text,400),reply=text(action.reply,6000),model=action.model==null?null:text(action.model,150);
   if(action.clientAt!==undefined&&(!Number.isSafeInteger(action.clientAt)||action.clientAt<0))throw fail('INVALID_CLIENT_TIMESTAMP');
   // The owner imports a completed exchange. Client text cannot attest a world
   // event or provider execution, and never enters a training dataset here.
   const meta={at,clientAt:action.clientAt??null,provider:action.provider,model,source:'OWNER_AUTHORIZED_IMPORT_UNVERIFIED',validation:'unverified',eligibleForTraining:false};
   next.conversations=[...next.conversations,{...meta,id:event+'-you',role:'you',text:saying},{...meta,id:event+'-beast',role:'beast',text:reply}].slice(-LIMITS.conversations);
   next.personalityState.engagement=Math.min(100,next.personalityState.engagement+1);break;
  }
  case 'name':{const p=validatePublicProfile({...next.profile,name:action.name});if(!p.ok)throw fail('INVALID_NAME');next.profile=p.profile;break;}
  case 'model':if(!['guest-rawrphos','local-ollama','hf-byok','connected-brain-bay'].includes(action.provider)||typeof action.model!=='string'||! /^[a-zA-Z0-9_./: -]{1,150}$/.test(action.model))throw fail('INVALID_MODEL');next.model={provider:action.provider,model:action.model};break;
  case 'game-checkpoint':{
   if(typeof next.identity.qbeastText!=='string')throw fail('QBEAST_ASSOCIATION_REQUIRED',409);
   const {snapshot}=checkedSpark(next.identity.qbeastText);
   createGameHandoff({qbeast:snapshot,seed:snapshot.profile.seed,genome:{seed:snapshot.profile.seed},game:{native_save:action.nativeSave}});
   next.gameCheckpoints=append(next.gameCheckpoints,{nativeSave:action.nativeSave,at,source:'CRC_IDENTITY_CHECKED_UNSIGNED_BATTERY',objectiveProgress:'not inferred'},2);break;
  }
  case 'sensor':{const value=action.amplitude;if(action.consent!==true||!Number.isFinite(value)||value<0||value>1)throw fail('SENSOR_CONSENT_OR_VALUE_INVALID');next.sensorHistory=append(next.sensorHistory,{at,amplitude:value,source:'CLIENT_MIC_AMPLITUDE_UNVERIFIED'},LIMITS.events);break;}
  case 'experience':if(!action.observation||!['MOVE_UP','MOVE_DOWN','MOVE_LEFT','MOVE_RIGHT','ACTION_A','ACTION_B','START','SELECT','WAIT'].includes(action.action))throw fail('INVALID_EXPERIENCE');next.learningEvents=append(next.learningEvents,{at,action:action.action,observation:text(JSON.stringify(action.observation),2000),source:'CLIENT_OBSERVATION_UNVERIFIED',validation:'unverified',eligibleForTraining:false},LIMITS.events);break;
  case 'growth-consent':if(typeof action.enabled!=='boolean'||typeof action.schedule!=='boolean')throw fail('INVALID_GROWTH_CONSENT');next.growth.optedIn=action.enabled;next.growth.schedule=action.enabled&&action.schedule;next.growth.status=action.enabled?'READY':'OFF';if(!action.enabled)next.growth.pending=null;break;
  case 'simulation-request':if(!next.growth.optedIn)throw fail('GROWTH_NOT_OPTED_IN',403);if(next.growth.pending)throw fail('SIMULATION_ALREADY_QUEUED',409);next.growth.status='QUEUED';next.growth.pending={eventId:event,requestedAt:at};break;
  case 'reset':{const reset=empty(next.profile,next.owner);reset.identity=next.identity;reset.quantumGenesis=next.quantumGenesis;reset.sync={...next.sync,conversationConsent:false};reset.simulationReceipts=next.simulationReceipts;reset.evolutionHistory=next.evolutionHistory;reset.gameCheckpoints=next.gameCheckpoints;reset.growth={...next.growth,optedIn:false,schedule:false,status:'OFF'};return reset;}
  default:throw fail('UNSUPPORTED_MEMORY_ACTION');
 }
 return next;
}
export class PrivateCosmos{
 constructor(io,{scope='',limits={}}={}){if(!io?.get||!io?.put||scope&&!/^[a-zA-Z0-9/_-]{1,100}$/.test(scope)||scope.includes('..'))throw fail('INVALID_STORE');this.io=io;this.scope=scope?scope.replace(/\/$/,'')+'/':'';this.limits={...LIMITS,...limits};}
 path(owner,id){if(!validSubject(owner)||!cosmosIdFor(id)||cosmosIdFor(id)!==id)throw fail('INVALID_NAMESPACE',403);return this.scope+'users/'+owner+'/beasts/'+id;}
 ownerPath(owner){if(!validSubject(owner))throw fail('INVALID_OWNER',403);return this.scope+'users/'+owner+'/authorization.json';}
 async assertOwner(owner){const row=await this.io.get(this.ownerPath(owner));if(!row||parse(row).active!==true)throw fail('OWNER_REVOKED_OR_UNKNOWN',403);return row;}
 async ownerStatus(owner){const row=await this.io.get(this.ownerPath(owner));if(!row)throw fail('OWNER_REVOKED_OR_UNKNOWN',403);const account=parse(row);if(account.id!==owner||typeof account.active!=='boolean')throw fail('CORRUPT_OWNER',422);return {active:account.active,erasurePending:!account.active&&account.erasure?.status!=='COMPLETE'};}
 async assertWritable(owner,id){await this.assertOwner(owner);const row=await this.io.get(this.path(owner,id)+'/head.json');if(!row)throw fail('PRIVATE_BEAST_NOT_FOUND',404);if(parse(row).deleted)throw fail('PRIVATE_BEAST_DELETED',410);}
 async markErasurePending(owner){
  for(let attempt=0;attempt<4;attempt++){const row=await this.io.get(this.ownerPath(owner));if(!row)return;const account=parse(row);if(account.active)return;
   try{await this.io.put(this.ownerPath(owner),json({...account,erasure:{...account.erasure,status:'PENDING'}}),{ifMatch:row.etag});return;}catch(error){if(error.status!==412||attempt===3)throw error;}}
 }
 async cleanupIfClosed(owner,id,path){
  if(!path.startsWith(this.path(owner,id)+'/'))throw fail('INVALID_NAMESPACE',403);
  try{await this.assertWritable(owner,id);return false;}catch(error){if(![403,404,410].includes(error.status))throw error;}
  try{const row=await this.io.get(path);if(row)await this.io.delete(path,{ifMatch:row.etag});}catch(error){await this.markErasurePending(owner).catch(()=>{});throw error;}return true;
 }
 async putAuxiliary(owner,id,path,value,options){
  if(!path.startsWith(this.path(owner,id)+'/'))throw fail('INVALID_NAMESPACE',403);
  // A writer that loses an erase race must clean its own late object. Writes
  // that pass this fence preceded the tombstone and are covered by its purge.
  try{await this.io.put(path,value,options);await this.assertWritable(owner,id);return await this.io.get(path);}catch(error){await this.cleanupIfClosed(owner,id,path);throw error;}
 }
 async admit(owner){const path=this.ownerPath(owner),existing=await this.io.get(path);if(existing){if(!parse(existing).active)throw fail('OWNER_REVOKED',403);return;}
  const budget=this.scope+'private-system/admission.json';
  for(let attempt=0;attempt<4;attempt++){const row=await this.io.get(budget),state=row?parse(row):{subjects:[]};if(!Array.isArray(state.subjects))throw fail('CORRUPT_ADMISSION',422);if(state.subjects.includes(owner))break;if(state.subjects.length>=this.limits.users)throw fail('PRIVATE_USER_CAP',429);try{await this.io.put(budget,json({subjects:[...state.subjects,owner]}),row?{ifMatch:row.etag}:{ifNoneMatch:'*'});break;}catch(error){if(error.status!==412||attempt===3)throw error;}}
  try{await this.io.put(path,json({schema:'private-owner/v1',id:owner,active:true,beasts:[],createdAt:new Date().toISOString()}),{ifNoneMatch:'*'});}catch(error){if(error.status!==412)throw error;await this.assertOwner(owner);}
 }
 async read(owner,id){await this.assertOwner(owner);const base=this.path(owner,id),blob=await this.io.get(base+'/head.json');if(!blob)throw fail('PRIVATE_BEAST_NOT_FOUND',404);const head=parse(blob);if(head.deleted)throw fail('PRIVATE_BEAST_DELETED',410);const commit=await this.io.get(base+'/commits/'+head.eventId+'.json');const doc=parse(commit),{hash:checksum,...unsigned}=doc;if(hash(unsigned)!==checksum||checksum!==head.hash||doc.owner!==owner||doc.beastId!==id||doc.sequence!==head.sequence||doc.record?.owner!==owner||doc.record?.beastId!==id||doc.record?.schema!==PRIVATE_SCHEMA)throw fail('CORRUPT_PRIVATE_COMMIT',422);return {record:doc.record,version:head.sequence,etag:blob.etag,head,commit:doc};}
 async create(owner,raw,id,{qbeastText=null,quantumGenesis=null}={}){await this.assertOwner(owner);const v=validatePublicProfile(raw);if(!v.ok)throw fail('INVALID_PRIVATE_PROFILE');if(!eventId(id))throw fail('INVALID_EVENT_ID');const profile=v.profile,base=this.path(owner,profile.id),auth=await this.io.get(this.ownerPath(owner)),account=parse(auth);if(!account.beasts.includes(profile.id)){if(account.beasts.length>=this.limits.beasts)throw fail('PRIVATE_CREATURE_CAP',429);await this.io.put(this.ownerPath(owner),json({...account,beasts:[...account.beasts,profile.id]}),{ifMatch:auth.etag});}
  if(await this.io.get(base+'/head.json')){const old=await this.read(owner,profile.id);if(hash(old.record.identity.provenance)!==hash(profile.provenance))throw fail('IMMUTABLE_IDENTITY_CONFLICT',409);return old;}
  const record=empty(profile,owner);if(quantumGenesis)record.quantumGenesis=quantumGenesis;if(qbeastText){const {snapshot}=checkedSpark(qbeastText);if(snapshot.profile.id!==profile.id||snapshot.profile.seed!==profile.provenance.seed)throw fail('QBEAST_PROFILE_MISMATCH',409);record.identity.qbeastText=qbeastText;record.identity.genesisValidation='QBEAST_INTEGRITY_VALID_PROVIDER_CLAIM_UNVERIFIED';}
  return this.commit(owner,profile.id,record,{kind:'create',profile,qbeastText},id,null);
 }
 async update(owner,id,action,event,expectedVersion){if(!eventId(event))throw fail('INVALID_EVENT_ID');const old=await this.read(owner,id),digest=hash(action);const already=old.record.sync.recentEvents[event];if(already){if(already!==digest)throw fail('EVENT_ID_REUSED',409);return old;}if(old.version!==expectedVersion)throw fail('STALE_VERSION',409);const next=apply(old.record,action,new Date().toISOString(),event);return this.commit(owner,id,next,action,event,old);}
 async commit(owner,id,record,action,event,old,{rebasePrepared=false}={}){const base=this.path(owner,id),digest=hash(action),sequence=(old?.version||0)+1,parentHash=old?.head.hash||null;if(sequence>this.limits.commits)throw fail('PRIVATE_COMMIT_CAP',429);let storageEvent=event,path=base+'/commits/'+storageEvent+'.json',existing=await this.io.get(path),doc;
  if(existing&&rebasePrepared){const prepared=parse(existing),{hash:checksum,...unsigned}=prepared;if(prepared.inputHash!==digest||prepared.owner!==owner||prepared.beastId!==id)throw fail('PREPARED_COMMIT_CONFLICT',409);if(hash(unsigned)!==checksum)throw fail('CORRUPT_PREPARED_COMMIT',422);
   if(prepared.parentHash!==parentHash){storageEvent='qvm-rebase-'+hash({event,parentHash});path=base+'/commits/'+storageEvent+'.json';existing=await this.io.get(path);}}
  if(existing){doc=parse(existing);if(doc.inputHash!==digest||doc.owner!==owner||doc.beastId!==id||doc.parentHash!==parentHash||doc.sequence!==sequence)throw fail('PREPARED_COMMIT_CONFLICT',409);const {hash:checksum,...unsigned}=doc;if(hash(unsigned)!==checksum)throw fail('CORRUPT_PREPARED_COMMIT',422);}
  else{record.sync.version=sequence;record.sync.recentEvents={...record.sync.recentEvents,[event]:digest};const unsigned={schema:'private-commit/v1',owner,beastId:id,eventId:storageEvent,inputHash:digest,parentHash,sequence,record};doc={...unsigned,hash:hash(unsigned)};const serialized=json(doc);if(Buffer.byteLength(serialized)>this.limits.bytes)throw fail('PRIVATE_RECORD_CAP',413);
   try{await this.io.put(path,serialized,{ifNoneMatch:'*'});}catch(error){await this.cleanupIfClosed(owner,id,path);throw error;}}
  // Revocation may race a prepared write. Check authority again before exposing it.
  try{await this.assertOwner(owner);await this.io.put(base+'/head.json',json({eventId:storageEvent,hash:doc.hash,sequence,previous:old?{eventId:old.head.eventId,hash:old.head.hash,sequence:old.head.sequence}:null}),old?{ifMatch:old.etag}:{ifNoneMatch:'*'});}
  catch(error){
   const current=await this.io.get(base+'/head.json').catch(()=>null);
   const account=await this.io.get(this.ownerPath(owner)).catch(()=>null);
   if(account&&parse(account).active===true&&current&&parse(current).hash===doc.hash)return this.read(owner,id);
   // Leave transient transport failures prepared for retry. Terminal revocation,
   // deletion or CAS conflicts remove this candidate only if it is not live.
   if(error.status===412||error.status===403){try{const candidate=await this.io.get(path);if(candidate)await this.io.delete(path,{ifMatch:candidate.etag});}catch(cleanupError){await this.markErasurePending(owner).catch(()=>{});throw cleanupError;}}
   throw error;
  }
  return this.read(owner,id);
 }
 async applyQvm(owner,id,plan,receipt,event,version,secret){
  const old=await this.read(owner,id);
  if(!old.record.growth.optedIn)throw fail('QVM_CANCELLED',403);
  if(!verifyWorkerReceipt(secret,receipt,plan))throw fail('QVM_RECEIPT_SIGNATURE_FAILED',403);
  const digest=hash({kind:'trusted-qvm-receipt',receipt});if(old.record.sync.recentEvents[event]===digest)return old;
  if(plan.owner!==owner||plan.beast_id!==id||plan.tick!==old.record.growth.tick+1||event!==plan.event_id)throw fail('QVM_RECEIPT_BINDING_FAILED',403);
  if(old.version!==version)throw fail('STALE_VERSION',409);
  const next=clone(old.record);next.growth.pending=null;next.growth.lastAttempt=receipt.startedAt;next.simulationReceipts=append(next.simulationReceipts,receipt,LIMITS.events);
  const feature=receipt.status==='RIGETTI_QVM_REMOTE'?countsFeatures(receipt.counts,receipt.shots):null;
  if(feature){next.growth.tick=plan.tick;next.growth.jobs++;next.growth.lastCompleted=receipt.completedAt;next.growth.status='RIGETTI_QVM_REMOTE';next.personalityState.curiosity=Math.max(0,Math.min(100,next.personalityState.curiosity+Math.round((feature.p0-.5)*4)));const signals={...next.profile.traits.stats,...next.growth.signals};for(const [name,p] of [['energy',feature.p0],['signal',feature.p1],['resonance',feature.p2]])signals[name]=Math.max(0,Math.min(100,(signals[name]??50)+(p-.5)*4));next.growth.signals=signals;}
  else next.growth.status='BLOCKED_EXTERNAL';
  const ledger=this.path(owner,id)+'/simulation-receipts/'+event+'.json';
  try{const saved=await this.io.get(ledger);if(saved){if(parse(saved).receipt_hash!==receipt.receipt_hash)throw fail('QVM_LEDGER_CONFLICT',409);await this.assertWritable(owner,id);}else await this.putAuxiliary(owner,id,ledger,json(receipt),{ifNoneMatch:'*'});
   return await this.commit(owner,id,next,{kind:'trusted-qvm-receipt',receipt},event,old,{rebasePrepared:true});
  }catch(error){await this.cleanupIfClosed(owner,id,ledger);throw error;}
 }
 async recover(owner,id){
  await this.assertOwner(owner);const base=this.path(owner,id),blob=await this.io.get(base+'/head.json'),head=parse(blob),previous=head.previous;
  if(head.deleted||!previous?.eventId||!eventId(previous.eventId))throw fail('NO_PRIOR_COMMITTED_CHECKPOINT',409);
  const doc=parse(await this.io.get(base+'/commits/'+previous.eventId+'.json')),{hash:checksum,...unsigned}=doc;
  if(checksum!==previous.hash||hash(unsigned)!==checksum||doc.owner!==owner||doc.beastId!==id||doc.sequence!==previous.sequence)throw fail('PRIOR_CHECKPOINT_CORRUPT',422);
  const record=clone(doc.record);record.growth={...record.growth,optedIn:false,schedule:false,status:'OFF'};
  record.sync.migrations=append(record.sync.migrations,{kind:'explicit-corruption-recovery',checkpointHash:checksum,at:new Date().toISOString()},LIMITS.events);
  return this.commit(owner,id,record,{kind:'recover',checkpointHash:checksum},'recovery-'+randomUUID(),{head,etag:blob.etag,version:head.sequence});
 }
 async remove(owner,id){
  await this.assertOwner(owner);const base=this.path(owner,id),blob=await this.io.get(base+'/head.json');if(!blob)throw fail('PRIVATE_BEAST_NOT_FOUND',404);const head=parse(blob);
  if(!head.deleted)await this.io.put(base+'/head.json',json({deleted:true,sequence:Number.isSafeInteger(head.sequence)?head.sequence+1:1}),{ifMatch:blob.etag});
  for(const name of await this.io.list(base+'/')){if(name.endsWith('/head.json'))continue;const row=await this.io.get(name);if(row)await this.io.delete(name,{ifMatch:row.etag});}return {deleted:true};
 }
 async revoke(owner){
  const row=await this.io.get(this.ownerPath(owner));if(!row)throw fail('OWNER_REVOKED_OR_UNKNOWN',403);const account=parse(row);if(account.id!==owner||typeof account.active!=='boolean')throw fail('CORRUPT_OWNER',422);
  const pending={...account,active:false,pair:null,revokedAt:account.revokedAt||new Date().toISOString(),erasure:{status:'PENDING'}};
  await this.io.put(this.ownerPath(owner),json(pending),{ifMatch:row.etag});
  // Keep opaque tombstones for all admitted creatures. A concurrently prepared
  // first commit must never recreate its head after account revocation.
  for(const id of account.beasts||[]){const path=this.path(owner,id)+'/head.json',head=await this.io.get(path);try{await this.io.put(path,json({deleted:true,revoked:true}),head?{ifMatch:head.etag}:{ifNoneMatch:'*'});}catch(error){if(error.status!==412)throw error;const current=await this.io.get(path);if(current)await this.io.put(path,json({deleted:true,revoked:true}),{ifMatch:current.etag});}}
  const prefix=this.scope+'users/'+owner+'/beasts/';for(const name of await this.io.list(prefix)){if(name.endsWith('/head.json'))continue;const blob=await this.io.get(name);if(blob)await this.io.delete(name,{ifMatch:blob.etag});}
  const latest=await this.io.get(this.ownerPath(owner));if(!latest)throw fail('OWNER_REVOKED_OR_UNKNOWN',403);const closed=parse(latest);if(closed.active)throw fail('OWNER_ERASURE_CONFLICT',409);
  // Capture authorization before the absence check: a failed late-write
  // cleanup advances this ETag and prevents a false COMPLETE acknowledgement.
  if((await this.io.list(prefix)).some(name=>!name.endsWith('/head.json')))throw fail('PRIVATE_ERASURE_PENDING',502);
  await this.io.put(this.ownerPath(owner),json({...closed,erasure:{status:'COMPLETE',completedAt:new Date().toISOString()}}),{ifMatch:latest.etag});return {revoked:true};
 }
}
