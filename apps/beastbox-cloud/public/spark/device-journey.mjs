/** Portable local state, never a signed QBEAST or a cartridge admission. */
import {canonicalJson,buildGenome} from './genome.mjs';
import {serializeQbeast} from './qbeast.mjs';
import {replaySpark,selectSpark,saveSparkSession,readSparkSession,SESSION_KEY,QBEAST_KEY,PROFILE_KEY} from './identity.mjs';
import {exportSession,importSession} from './shared/session.mjs';
import {validateBehavior} from './shared/behavior.mjs';
import {loadSparkRuns} from './runs.mjs';

export const DEVICE_JOURNEY_SCHEMA='beastbox-device-journey-v1';
export const DEVICE_JOURNEY_LIMIT=2*1024*1024;
export async function loadDeviceJourneyRuns(){
 return loadSparkRuns({includeQvm:true});
}
const clone=value=>JSON.parse(JSON.stringify(value));
const object=value=>!!value&&typeof value==='object'&&!Array.isArray(value);
const integer=(value,max=1_000_000_000,min=0)=>Number.isSafeInteger(value)&&value>=min&&value<=max;
const fail=message=>{throw Error(`Device journey: ${message}`);};
const allowed=(value,keys)=>{if(!object(value)||Object.keys(value).some(key=>!keys.includes(key)))fail('unexpected session fields.');};
function bounded(value,depth=0){
 if(depth>16)fail('data is nested too deeply.');
 if(typeof value==='number'&&!Number.isFinite(value))fail('non-finite state.');
 if(typeof value==='string'&&value.length>65536)fail('a text field is too large.');
 if(Array.isArray(value)){if(value.length>8192)fail('a collection is too large.');for(const item of value)bounded(item,depth+1);}
 else if(object(value)){if(Object.keys(value).length>2048)fail('a record is too large.');for(const [key,item] of Object.entries(value)){if(['__proto__','constructor','prototype'].includes(key)||key.length>128)fail('unsafe record key.');bounded(item,depth+1);}}
}
function mindBounds(mind){
 allowed(mind,['schema','dim','steps','tokenCount','vocab','next','weights','associations']);
 if(mind.schema!=='beastbox-hebbian-mind-v1'||mind.dim!==16||!integer(mind.steps)||!integer(mind.tokenCount))fail('pattern memory counters are invalid.');
 if(!Array.isArray(mind.weights)||mind.weights.length!==16||mind.weights.some(row=>!Array.isArray(row)||row.length!==16||row.some(v=>!Number.isFinite(v)||v< -4||v>4)))fail('pattern memory must be a bounded 16×16 matrix.');
 if(!object(mind.vocab)||!object(mind.next)||Object.keys(mind.vocab).length>1024||Object.keys(mind.next).length>1024)fail('pattern vocabulary exceeds 1024 words.');
 const word=key=>/^[a-z0-9'][a-z0-9']{1,15}$/.test(key)&&!['__proto__','constructor','prototype'].includes(key);
 for(const [key,row] of Object.entries(mind.vocab)){if(!word(key)||!object(row)||Object.keys(row).some(k=>k!=='count')||!integer(row.count))fail('invalid word count.');}
 let links=0;for(const [key,bag] of Object.entries(mind.next)){if(!word(key)||!object(bag))fail('invalid word links.');for(const [next,count] of Object.entries(bag)){if(!word(next)||!integer(count))fail('invalid word link count.');links++;}}
 if(links>8192)fail('pattern links exceed 8192 pairs.');
}
function nativeBounds(native){
 if(!native)return;
 allowed(native,['status','nativeStage','game','applied','retained']);
 if(native.status!==undefined&&native.status!=='unsigned-unverified')fail('native artifact claims authority.');
 if(!integer(native.nativeStage,3,1)||!object(native.game)||!Array.isArray(native.applied)||native.applied.length>64||native.applied.some(v=>typeof v!=='string'||v.length>80))fail('invalid retained native artifact.');
 allowed(native.game,['game_xp','game_level','game_stage','discovered','inventory','beacons','echoes','flags','native_save']);
 if(native.game.native_save!==undefined&&(typeof native.game.native_save!=='string'||native.game.native_save.length!==43692||!/^[A-Za-z0-9+/]{43691}=$/.test(native.game.native_save)))fail('native save must be a 32768-byte base64 artifact.');
 if(native.retained!==undefined){if(!Array.isArray(native.retained)||native.retained.length>8||native.retained.some(item=>item?.retained!==undefined))fail('native artifact archive exceeds eight records.');for(const item of native.retained)nativeBounds(item);}
}
function nativeArchive(incoming,host){
 const primary={status:'unsigned-unverified',nativeStage:incoming.nativeStage??1,game:clone(incoming.game||incoming.localGrowth?.game||{}),applied:clone(incoming.localGrowth?.applied||[])};
 const imported=incoming.journeyNative,existing=host.journeyNative;
 const candidates=[primary,...[imported,existing].flatMap(item=>item?[{status:'unsigned-unverified',nativeStage:item.nativeStage,game:item.game,applied:item.applied},...(item.retained||[])]:[])];
 const unique=new Map();for(const item of candidates){if(Object.keys(item.game).length||item.nativeStage>1)unique.set(canonicalJson(item),clone(item));}
 const records=[...unique.values()];if(records.length>9)fail('native artifact archive is full; keep both original journeys before importing.');
 const main=records.shift()||primary;return {...main,retained:records};
}
function validateSession(raw,replay,byKey){
 allowed(raw,['schema','tab','beast','bestiary','chat','mind','emulator','train','mood','pet']);
 if(raw.schema!=='beastbox-companion-session-v1'||!object(raw.beast))fail('no companion session.');
 const b=raw.beast;
 allowed(b,['id','seed','genome','displayName','xp','bond','energy','stage','mood','qbeast','nativeStage','qbeastProgress','localGrowth','game','behavior','journeyNative']);
 if(b.seed!==replay.gen.seed||canonicalJson(b.genome)!==canonicalJson(replay.gen)||canonicalJson(b.qbeast)!==canonicalJson(replay.snapshot))fail('session and recorded identity disagree.');
 if(typeof b.displayName!=='string'||b.displayName.length>24||!integer(b.xp)||!integer(b.bond,100)||!Number.isFinite(b.energy)||b.energy<0||b.energy>100||!integer(b.stage,3,1)||!integer(b.nativeStage??1,3,1))fail('care state is outside its bounds.');
 if(typeof b.mood!=='string'||b.mood.length>24||typeof raw.mood!=='string'||raw.mood.length>24)fail('invalid mood.');
 if(!Array.isArray(raw.chat)||raw.chat.length>80||raw.chat.some(t=>!object(t)||!['you','beast'].includes(t.role)||typeof t.text!=='string'||t.text.length>400||Object.keys(t).some(k=>!['role','text'].includes(k))))fail('chat exceeds 80 bounded turns.');
 if(!Array.isArray(raw.bestiary)||raw.bestiary.length>128)fail('bestiary exceeds 128 entries.');
 for(const item of raw.bestiary){
  allowed(item,['seed','name','island','body','genome']);if(typeof item.seed!=='string'||item.seed.length>80||typeof item.name!=='string'||item.name.length>80)fail('invalid bestiary entry.');
  const source=byKey.get(item.genome?.inputs?.quantum_run);if(!source)fail('bestiary recorded recipe is unavailable.');
  const genome=buildGenome(item.genome.inputs.traits,source,item.genome.inputs.user_id,10);if(genome.seed!==item.seed||genome.seed!==item.genome.seed)fail('bestiary recipe does not reproduce its seed.');
  // Old legacy renderer metadata may differ; reconstruct visuals from the same verified recipe.
  item.genome=genome;item.body=genome.body;item.island=genome.island;
 }
 if(raw.mind.associations){
  const a=raw.mind.associations;allowed(a,['schema','observations','concepts','links']);
  if(a.schema!=='beastbox-associations-v1'||!integer(a.observations,1e6)||!object(a.concepts)||Object.keys(a.concepts).length>128||!object(a.links)||Object.keys(a.links).length>384)fail('association memory exceeds its bounds.');
  for(const [key,v] of Object.entries(a.concepts))if(!/^[a-z0-9][a-z0-9']{1,15}$/.test(key)||!Number.isFinite(v)||v<=0||v>8)fail('invalid association concept.');
  for(const [key,v] of Object.entries(a.links)){const words=key.split('|');if(words.length!==2||words[0]>=words[1]||!words.every(w=>Object.hasOwn(a.concepts,w))||!Number.isFinite(v)||v<=0||v>8)fail('invalid association link.');}
 }
 mindBounds(raw.mind);allowed(raw.train,['score','rounds']);if(!integer(raw.train.score)||!integer(raw.train.rounds))fail('invalid training counters.');
 allowed(raw.emulator,['mounted','ticks','booted']);if(!integer(raw.emulator.ticks))fail('invalid emulator counter.');
 if(raw.pet){allowed(raw.pet,['model','steps','learned','source','modelWeightsTrained']);if(raw.pet.modelWeightsTrained!==false||typeof raw.pet.model!=='string'||raw.pet.model.length>128||!integer(raw.pet.steps))fail('invalid local model activity.');}
 if(b.localGrowth){allowed(b.localGrowth,['schema','status','signature','qbeast_id','seed','xp','bond','energy','stage','mood','train','memory_steps','game','applied','model','note']);if(b.localGrowth.status!=='unsigned-local'||b.localGrowth.signature!=='none'||b.localGrowth.qbeast_id!==replay.snapshot.profile.id||b.localGrowth.seed!==replay.gen.seed)fail('local growth claims another identity or authority.');if(b.localGrowth.model)allowed(b.localGrowth.model,['provider','swapped']);}
 nativeBounds({nativeStage:b.nativeStage??1,game:b.game||b.localGrowth?.game||{},applied:b.localGrowth?.applied||[]});nativeBounds(b.journeyNative);
 if(b.behavior){
  allowed(b.behavior,['schema','seed','tick','energy','curiosity','preferences','position','lastAction','memory','events','lastFeedback']);
  for(const e of b.behavior.events||[]){allowed(e,['tick','kind','place','action','input','scores','result']);allowed(e.result,['energy','curiosity','position']);}
  if(canonicalJson(validateBehavior(b.behavior,b))!==canonicalJson(b.behavior))fail('behavior snapshot violates its current core bounds.');
 }
 const session=importSession(clone(raw));
 if(b.behavior&&canonicalJson(session.beast.behavior)!==canonicalJson(b.behavior))fail('behavior import changed its snapshot.');
 return session;
}
export function readDeviceJourney(text,byKey){
 if(typeof text!=='string'||new TextEncoder().encode(text).length>DEVICE_JOURNEY_LIMIT)fail('choose a file under 2 MiB.');
 let file;try{file=JSON.parse(text);}catch{fail('invalid JSON.');}
 allowed(file,['schema','status','signature','qbeast','session']);
 if(file.schema!==DEVICE_JOURNEY_SCHEMA||file.status!=='unsigned-device-journey'||file.signature!=='none')fail('only unsigned device journeys are supported.');
 bounded(file);
 const replay=replaySpark(serializeQbeast(file.qbeast),byKey);
 const session=validateSession(file.session,replay,byKey);
 return {...replay,session};
}
export function serializeDeviceJourney(session,byKey){
 if(!session?.beast?.qbeast)fail('choose a verified Spark identity first.');
 const file={schema:DEVICE_JOURNEY_SCHEMA,status:'unsigned-device-journey',signature:'none',qbeast:clone(session.beast.qbeast),session:clone(exportSession(session))};
 const text=JSON.stringify(file,null,2)+'\n';readDeviceJourney(text,byKey);return text;
}
/** Caller holds the existing Spark Web Lock. Import is a deliberate local restore. */
export function restoreDeviceJourney(storage,journey){
 const prior=readSparkSession(storage);
 const incoming=clone(exportSession(journey.session)),b=incoming.beast;
 const ids=[journey.snapshot.profile.id,prior.beast?.qbeast?.profile.id].filter(Boolean);
 const keys=[SESSION_KEY,QBEAST_KEY,PROFILE_KEY,...ids.flatMap(id=>[QBEAST_KEY+'-creature-'+id,SESSION_KEY+'-creature-'+id])];
 const before=new Map(keys.map(key=>[key,storage.getItem(key)]));
 try{
  selectSpark(storage,journey.gen,{snapshot:journey.snapshot});
  const selected=readSparkSession(storage),host=selected.beast;
  b.journeyNative=nativeArchive(b,host);nativeBounds(b.journeyNative);
  b.nativeStage=host.nativeStage||1;b.stage=b.nativeStage;b.game=clone(host.game||host.localGrowth?.game||{});
  if(b.localGrowth){b.localGrowth.game=clone(b.game);b.localGrowth.applied=clone(host.localGrowth?.applied||[]);b.localGrowth.stage=b.stage;}
  b.qbeast=host.qbeast;b.genome=journey.gen;
  const session=importSession(incoming);saveSparkSession(storage,session);
  const restored=readSparkSession(storage);
  if(canonicalJson(exportSession(restored))!==canonicalJson(exportSession(session)))fail('save could not be read back.');
  return restored;
 }catch(error){
  // Restore both identity and care after any failed write in the import transaction.
  for(const [key,value] of before)try{value===null?storage.removeItem(key):storage.setItem(key,value);}catch{}
  throw error;
 }
}
export function retainedNativeBytes(beast){
 const artifact=beast?.journeyNative,text=artifact?.game?.native_save||artifact?.retained?.find(item=>item.game.native_save)?.game.native_save;if(!text)return null;
 nativeBounds(beast.journeyNative);
 return Uint8Array.from(atob(text),char=>char.charCodeAt(0));
}
