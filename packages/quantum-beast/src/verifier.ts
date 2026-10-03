import {validCreature,type CreatureProfile} from './canonical/creature-profile';

export const MAX_BYTES=524288,MAX_EVENTS=512;
export type PublicState={schema:'dyn12-public-v1';mode:'unavailable'|'approved_projection';values:number[];source_sha256:string|null};
export type Progress={trust:number;bond:number;evolution_stage:number};
export type EventKind='message'|'action'|'memory';
export type EventPayload={text:string}|{action:'hover'|'orbit'|'perch'|'rest'}|{summary:string;source_ref:string};
export type LineageEvent={generation:number;parent:string;proposal_id:string;kind:EventKind;payload:EventPayload;hash:string};
export type Snapshot={format:'QBEAST1';version:1;profile:CreatureProfile;public_state:PublicState;progress:Progress;events:LineageEvent[];generation:number;lineage_head:string;digest:string;signature?:{algorithm:'Ed25519';public_key:string;value:string}};
export type VerifyOptions={trustedPublicKey?:string};
export class InvalidBeast extends Error{}
export function requireCondition(condition:unknown,message:string):asserts condition{if(!condition)throw new InvalidBeast(message);}
export function exactKeys(value:unknown,names:string[],optional:string[]=[]):asserts value is Record<string,unknown>{
 requireCondition(!!value&&typeof value==='object'&&!Array.isArray(value),'Expected an object');
 const obj=value as Record<string,unknown>,keys=Object.keys(obj);
 requireCondition(names.every(k=>Object.hasOwn(obj,k))&&keys.every(k=>names.includes(k)||optional.includes(k)),'Unexpected or missing fields');
 requireCondition(Object.getPrototypeOf(obj)===Object.prototype||Object.getPrototypeOf(obj)===null,'Invalid object prototype');
}
export function boundedText(value:unknown,max:number,label='text'):asserts value is string{
 requireCondition(typeof value==='string'&&value.length>0&&value.length<=max&&!/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/u.test(value),'Invalid '+label);
}
/** An extra guard, never a replacement for the host choosing public material. */
export function publicText(value:unknown,max:number):asserts value is string{
 boundedText(value,max);
 requireCondition(!/(?:api[_ -]?key|password|credential|authorization|biometric|owner[_ -]?memory|private[_ -]?(?:key|state)|-----BEGIN|\bBearer\s|\bsk-[a-z0-9_-]{8,})/i.test(value),'Potential private material; host must choose a safe public summary');
}
const HEX=/^[a-f0-9]{64}$/;
export function hex(value:unknown):asserts value is string{requireCondition(typeof value==='string'&&HEX.test(value),'Invalid SHA-256');}
export function canonical(value:unknown):string{
 if(value===null)return 'null';
 if(typeof value==='string'||typeof value==='boolean')return JSON.stringify(value);
 if(typeof value==='number'){requireCondition(Number.isFinite(value)&&(!Number.isInteger(value)||Number.isSafeInteger(value)),'Invalid number');return JSON.stringify(value);}
 if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';
 requireCondition(!!value&&typeof value==='object','Non-JSON value');
 const obj=value as Record<string,unknown>;
 return '{'+Object.keys(obj).filter(k=>obj[k]!==undefined).sort().map(k=>JSON.stringify(k)+':'+canonical(obj[k])).join(',')+'}';
}
export async function hashObject(value:unknown):Promise<string>{
 const raw=new TextEncoder().encode('QBEAST1\0'+canonical(value));
 const digest=await globalThis.crypto.subtle.digest('SHA-256',raw);
 return Array.from(new Uint8Array(digest),x=>x.toString(16).padStart(2,'0')).join('');
}
export function unsignedPayload(snapshot:Snapshot){const {digest:_digest,signature:_signature,...rest}=snapshot;return rest;}
export function validatePayload(kind:unknown,payload:unknown):asserts payload is EventPayload{
 if(kind==='message'){exactKeys(payload,['text']);publicText(payload.text,1024);}
 else if(kind==='action'){exactKeys(payload,['action']);requireCondition(typeof payload.action==='string'&&['hover','orbit','perch','rest'].includes(payload.action),'Action outside decorative allowlist');}
 else if(kind==='memory'){exactKeys(payload,['summary','source_ref']);publicText(payload.summary,256);publicText(payload.source_ref,96);}
 else throw new InvalidBeast('Unsupported event kind');
}
function validateFields(snapshot:unknown):asserts snapshot is Snapshot{
 exactKeys(snapshot,['format','version','profile','public_state','progress','events','generation','lineage_head','digest'],['signature']);
 requireCondition(snapshot.format==='QBEAST1'&&snapshot.version===1,'Unsupported QBEAST format/version');
 requireCondition(validCreature(snapshot.profile),'Forged or malformed canonical Genesis profile');
 publicText((snapshot.profile as CreatureProfile).seed,64);
 // Require canonical bounded strings; UTF-8 bytes are checked at the file edge.
 const p=snapshot.public_state;exactKeys(p,['schema','mode','values','source_sha256']);
 requireCondition(p.schema==='dyn12-public-v1'&&['unavailable','approved_projection'].includes(String(p.mode)),'Invalid public projection');
 requireCondition(Array.isArray(p.values)&&p.values.length===12&&p.values.every(x=>typeof x==='number'&&Number.isFinite(x)&&x>=-127.996&&x<=127.996),'Invalid dyn12 width or range');
 if(p.mode==='unavailable')requireCondition(p.source_sha256===null&&p.values.every(x=>x===0),'Unavailable state cannot claim measurements');
 else hex(p.source_sha256);
 const progress=snapshot.progress;exactKeys(progress,['trust','bond','evolution_stage']);
 requireCondition(Number.isInteger(progress.trust)&&Number(progress.trust)>=0&&Number(progress.trust)<=100&&Number.isInteger(progress.bond)&&Number(progress.bond)>=0&&Number(progress.bond)<=100&&Number.isInteger(progress.evolution_stage)&&Number(progress.evolution_stage)>=0&&Number(progress.evolution_stage)<=2,'Invalid host progress');
 requireCondition(Array.isArray(snapshot.events)&&snapshot.events.length<=MAX_EVENTS,'Lineage capacity exceeded; use an explicitly versioned archival format');
 requireCondition(Number.isSafeInteger(snapshot.generation)&&snapshot.generation===snapshot.events.length,'Generation mismatch');
 hex(snapshot.lineage_head);hex(snapshot.digest);
 if(snapshot.signature!==undefined){const s=snapshot.signature;exactKeys(s,['algorithm','public_key','value']);requireCondition(s.algorithm==='Ed25519','Unsupported signature algorithm');hex(s.public_key);requireCondition(typeof s.value==='string'&&/^[a-f0-9]{128}$/.test(s.value),'Invalid Ed25519 signature');}
}
export async function genesisHead(snapshot:Pick<Snapshot,'profile'|'public_state'|'progress'>){
 return hashObject({domain:'genesis',profile:snapshot.profile,public_state:snapshot.public_state,progress:snapshot.progress});
}
export async function checkIntegrity(snapshot:unknown):Promise<Snapshot>{
 validateFields(snapshot);
 let parent=await genesisHead(snapshot);const proposals=new Set<string>();
 for(let i=0;i<snapshot.events.length;i++){
  const event=snapshot.events[i];exactKeys(event,['generation','parent','proposal_id','kind','payload','hash']);
  requireCondition(event.generation===i+1&&event.parent===parent,'Broken lineage order');hex(event.proposal_id);hex(event.hash);validatePayload(event.kind,event.payload);
  requireCondition(!proposals.has(event.proposal_id),'Replayed event');proposals.add(event.proposal_id);
  const {hash:_hash,...payload}=event;
  requireCondition(await hashObject({domain:'event',...payload})===event.hash,'Lineage event digest mismatch');parent=event.hash;
 }
 requireCondition(snapshot.lineage_head===parent,'Lineage head mismatch');
 requireCondition(await hashObject(unsignedPayload(snapshot))===snapshot.digest,'Snapshot digest mismatch');
 requireCondition(new TextEncoder().encode(canonical(snapshot)).length<=MAX_BYTES,'Snapshot too large');
 return structuredClone(snapshot);
}
export async function verifySnapshot(snapshot:unknown,options:VerifyOptions={}){
 const safe=await checkIntegrity(snapshot);
 let signature:'absent'|'valid_untrusted'|'trusted'='absent';
 if(safe.signature){
  const raw=(str:string)=>Uint8Array.from(str.match(/../g)!,x=>parseInt(x,16));
  const key=await crypto.subtle.importKey('raw',raw(safe.signature.public_key),{name:'Ed25519'},false,['verify']);
  requireCondition(await crypto.subtle.verify('Ed25519',key,raw(safe.signature.value),new TextEncoder().encode(safe.digest)),'Invalid source signature');
  signature='valid_untrusted';
  if(options.trustedPublicKey){requireCondition(options.trustedPublicKey===safe.signature.public_key,'Signing key does not match host trust anchor');signature='trusted';}
 }else requireCondition(!options.trustedPublicKey,'A trusted signature was required');
 const privileged=safe.public_state.mode!=='unavailable'||Object.values(safe.progress).some(x=>x!==0);
 requireCondition(!privileged||signature==='trusted','Nonzero progress or measured projection requires a host-pinned signing key');
 return {integrity:true as const,stats_verified:true as const,signature,creature_id:safe.profile.id,lineage_head:safe.lineage_head,digest:safe.digest,events:safe.events.length,authority:false as const};
}
export async function createSnapshot(profile:CreatureProfile,options:{publicState?:PublicState;progress?:Progress}={}):Promise<Snapshot>{
 requireCondition(validCreature(profile),'Invalid canonical creature profile');
 const snapshot:Snapshot={format:'QBEAST1',version:1,profile:structuredClone(profile),
  public_state:structuredClone(options.publicState??{schema:'dyn12-public-v1',mode:'unavailable',values:Array(12).fill(0),source_sha256:null}),
  progress:structuredClone(options.progress??{trust:0,bond:0,evolution_stage:0}),events:[],generation:0,lineage_head:'0'.repeat(64),digest:'0'.repeat(64)};
 validateFields(snapshot);snapshot.lineage_head=await genesisHead(snapshot);snapshot.digest=await hashObject(unsignedPayload(snapshot));return snapshot;
}
/** Reject duplicate keys before JSON.parse, including escaped aliases. No ZIP parser. */
export function parseStrictJson(text:string):unknown{
 requireCondition(typeof text==='string'&&new TextEncoder().encode(text).length<=MAX_BYTES,'Input exceeds byte limit');
 let i=0;const ws=()=>{while(/[\t\n\r ]/.test(text[i]??'X'))i++;};
 const str=():string=>{const start=i++;requireCondition(text[start]==='"','Expected JSON string');while(i<text.length){if(text[i]==='\\'){i+=2;continue;}if(text[i++]==='"')return JSON.parse(text.slice(start,i));}throw new InvalidBeast('Unterminated string');};
 const visit=(depth:number):void=>{
  requireCondition(depth<=16,'JSON nesting limit exceeded');ws();const c=text[i];
  if(c==='"'){str();return;}
  if(c==='{'||c==='['){i++;ws();const close=c==='{'?'}':']';if(text[i]===close){i++;return;}const seen=new Set<string>();let count=0;
   for(;;){requireCondition(++count<=2048,'JSON collection too large');if(c==='{'){ws();const key=str();requireCondition(!seen.has(key)&&!['__proto__','prototype','constructor'].includes(key),'Duplicate or forbidden JSON key');seen.add(key);ws();requireCondition(text[i++]===':','Expected colon');}visit(depth+1);ws();if(text[i]===close){i++;break;}requireCondition(text[i++ ]===',','Expected comma');}return;
  }
  const match=/^(?:null|true|false|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(text.slice(i));requireCondition(match,'Invalid JSON token');i+=match[0].length;
 };
 visit(0);ws();requireCondition(i===text.length,'Trailing JSON data');return JSON.parse(text);
}
export async function parseSnapshot(text:string,options:VerifyOptions={}):Promise<Snapshot>{const snapshot=parseStrictJson(text);await verifySnapshot(snapshot,options);return snapshot as Snapshot;}
export async function serializeSnapshot(snapshot:Snapshot,options:VerifyOptions={}):Promise<string>{await verifySnapshot(snapshot,options);return canonical(snapshot)+'\n';}
