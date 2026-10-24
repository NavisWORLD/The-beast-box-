/** Real Next.js routes + real isolated Azure Blob, synthetic private worlds only.
 * Run after `npm run build`. No provider inference or quantum submission occurs.
 */
import assert from 'node:assert/strict';
import {randomBytes,randomUUID,createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {once} from 'node:events';
import {storageConfig} from '../lib/cosmos/azure-blob.mjs';
import {azurePrivateIO} from '../lib/cosmos/private-memory.mjs';
import {PRIVATE_COOKIE,issueCredential,verifyCredential} from '../lib/cosmos/private-owner.mjs';
import {buildGenome} from '../public/spark/genome.mjs';
import {expandRun} from '../public/spark/runs.mjs';
import {buildQbeast,serializeQbeast} from '../public/spark/qbeast.mjs';
import {publicProfileFromBeast} from '../public/spark/cosmos-profile.mjs';
import {seededStream} from '../lib/seeded-stream.mjs';const __rs=seededStream('scripts/private-cosmos-http-probe.mjs');

const out=process.argv[2]||'build/private-cosmos',cfg=storageConfig();mkdirSync(out,{recursive:true});
const report={schema:'private-cosmos-http-acceptance/v1',status:'BLOCKED_EXTERNAL',checks:[],cleanup:false,physicalDevice:false};
if(!cfg||process.env.BEASTBOX_PRIVATE_PROBE_APPROVAL!=='YES_ISOLATED_PRIVATE_TEST'){writeFileSync(out+'/http-report.json',JSON.stringify(report,null,2));process.exit(2);}
const io=azurePrivateIO(cfg),scope='integration-tests/issue-323/http-'+randomUUID(),secret=randomBytes(48).toString('hex');
const port=30000+Math.floor(__rs()*20000),origin='http://127.0.0.1:'+port;let server,check='start production Next.js';
const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function start(){
 server=spawn(process.execPath,['node_modules/next/dist/bin/next','start','--hostname','127.0.0.1','--port',String(port)],{stdio:'ignore',env:{...process.env,BEASTBOX_PRIVATE_MEMORY_ENABLED:'true',BEASTBOX_CLOUD_AUTH_SECRET:secret,BEASTBOX_PRIVATE_MEMORY_PREFIX:scope,NEXT_TELEMETRY_DISABLED:'1'}});
 for(let i=0;i<200;i++){if(server.exitCode!==null)throw Error('SERVER_EXITED');try{const r=await fetch(origin+'/api/cosmos/private/session',{signal:AbortSignal.timeout(500)});if(r.ok)return;}catch{}await pause(150);}throw Error('SERVER_UNAVAILABLE');
}
async function stop(){if(server&&server.exitCode===null){const closed=once(server,'close');server.kill('SIGTERM');await closed;}}
async function api(path,{cookie='',method='GET',body,requestOrigin=origin}={}){
 const claim=cookie?verifyCredential(secret,cookie.split('=').slice(1).join('=')):null;if(body!==undefined&&claim)body={expectedOwner:claim.subject,...body};
 const response=await fetch(origin+'/api/cosmos/private/'+path,{method,headers:{...(cookie?{Cookie:cookie}:{}),...(body===undefined?{}:{Origin:requestOrigin,'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(30000)});
 const data=await response.json();report.lastOperation={path,method,status:response.status,apiStatus:data.status||null,cookieIssued:response.headers.has('set-cookie')};return {response,status:response.status,data};
}
const pass=()=>report.checks.push({name:check,status:'PASSED'});
function creature(){const run=expandRun(JSON.parse(readFileSync('public/spark/ibm-zeref-heart-sound-20261010.json')).runs[0]),genome=buildGenome({focus:80,calm:20,spark:100},run,'P-'+randomBytes(10).toString('hex'),10),snapshot=buildQbeast(genome);return {profile:publicProfileFromBeast({genome,qbeast:snapshot,displayName:'Same Name'}),qbeastText:serializeQbeast(snapshot),eventId:randomUUID()};}
function cookieOf(result){const header=result.response.headers.get('set-cookie');assert.ok(header&&/HttpOnly/i.test(header)&&/SameSite=strict/i.test(header)&&/Secure/i.test(header));return header.split(';')[0];}
try{
 await start();check='anonymous local default and explicit cloud consent';const anonymous=await api('session');assert.equal(anonymous.data.configured,true);assert.equal(anonymous.data.authorized,false);assert.equal(anonymous.response.headers.get('set-cookie'),null);assert.equal((await api('beasts')).status,401);assert.equal((await api('session',{method:'POST',body:{}})).status,403);pass();
 check='two securely issued owners create distinct canonical creatures with identical names';const a=await api('session',{method:'POST',body:{consent:true}}),b=await api('session',{method:'POST',body:{consent:true}});assert.equal(a.status,200);assert.equal(b.status,200);const ca=cookieOf(a),cb=cookieOf(b);assert.notEqual(a.data.owner,b.data.owner);
 const inputA=creature(),inputB=creature();assert.notEqual(inputA.profile.id,inputB.profile.id);const idA=inputA.profile.id,idB=inputB.profile.id;const createdA=await api('beasts',{cookie:ca,method:'POST',body:inputA}),createdB=await api('beasts',{cookie:cb,method:'POST',body:inputB});assert.equal(createdA.status,200);assert.equal(createdB.status,200);assert.equal(createdA.data.record.profile.name,'Same Name');assert.equal(createdB.data.record.profile.name,'Same Name');report.identities={a:idA,b:idB,genesisA:hash(createdA.data.record.quantumGenesis),genesisB:hash(createdB.data.record.quantumGenesis)};pass();
 check='cross-account reads, updates, simulator control and deletion fail closed';for(const request of [{},{method:'PUT',body:{action:{kind:'memory',text:'unauthorized'},eventId:randomUUID(),version:1}},{method:'PUT',body:{action:{kind:'growth-consent',enabled:true,schedule:true},eventId:randomUUID(),version:1}},{method:'DELETE',body:{}}])assert.equal((await api('beasts/'+idA,{cookie:cb,...request})).status,404);pass();
 check='client owner claims, foreign origins, forged credentials and expired credentials are rejected';assert.equal((await api('session',{method:'POST',body:{consent:true,userId:a.data.owner}})).status,403);assert.equal((await api('session',{method:'POST',body:{consent:true},requestOrigin:'https://untrusted.invalid'})).status,403);assert.equal((await api('beasts',{cookie:ca+'x'})).status,401);assert.equal((await api('beasts',{cookie:PRIVATE_COOKIE+'='+issueCredential(secret,{now:1}).token})).status,401);pass();
 check='private conversation writes are idempotent and never leak across creatures';const event=randomUUID(),body={action:{kind:'conversation',role:'you',text:'ISOLATED SYNTHETIC PRIVATE CONVERSATION A'},eventId:event,version:1};let changed=await api('beasts/'+idA,{cookie:ca,method:'PUT',body});assert.equal(changed.status,200);assert.equal((await api('beasts/'+idA,{cookie:ca,method:'PUT',body})).data.record.conversations.length,1);assert.equal((await api('beasts/'+idA,{cookie:ca,method:'PUT',body:{...body,action:{...body.action,text:'changed'}}})).status,409);assert.equal((await api('beasts/'+idB,{cookie:cb})).data.record.conversations.length,0);
 const another=creature();assert.equal((await api('beasts',{cookie:ca,method:'POST',body:another})).status,200);assert.equal((await api('beasts/'+another.profile.id,{cookie:ca})).data.record.conversations.length,0);pass();
 check='completed chat has explicit per-creature consent and two-turn atomic idempotence';
 const atomic={expectedSeed:createdA.data.record.identity.seed,eventId:randomUUID(),version:changed.data.version,action:{kind:'conversation-exchange',text:'PRIVATE USER FIXTURE',reply:'MODEL PROTOCOL FIXTURE ONLY',provider:'guest-rawrphos',model:'native-fixture',clientAt:Date.now()}};
 assert.equal((await api('beasts/'+idA,{cookie:ca,method:'PUT',body:atomic})).status,403);
 changed=await api('beasts/'+idA,{cookie:ca,method:'PUT',body:{action:{kind:'chat-consent',enabled:true},eventId:randomUUID(),version:changed.data.version}});assert.equal(changed.status,200);atomic.version=changed.data.version;atomic.expectedSeed=createdA.data.record.identity.seed;
 changed=await api('beasts/'+idA,{cookie:ca,method:'PUT',body:atomic});assert.equal(changed.status,200);assert.equal(changed.data.record.conversations.length,3);assert.equal(changed.data.record.conversations.at(-1).eligibleForTraining,false);
 const replay=await api('beasts/'+idA,{cookie:ca,method:'PUT',body:atomic});assert.equal(replay.data.version,changed.data.version);assert.equal(replay.data.record.conversations.length,3);
 assert.equal((await api('beasts/'+idB,{cookie:cb})).data.record.conversations.length,0);assert.equal((await api('beasts/'+another.profile.id,{cookie:ca})).data.record.conversations.length,0);pass();
 check='owner changes between read and write cannot disclose an old conversation into the new account';const bTwin=await api('beasts',{cookie:cb,method:'POST',body:inputA});assert.equal(bTwin.status,200);const beforeTwin=hash(bTwin.data.record);for(const request of [{method:'PUT',body:{...atomic,version:bTwin.data.version,expectedOwner:a.data.owner}},{method:'DELETE',body:{expectedOwner:a.data.owner}}])assert.equal((await api('beasts/'+idA,{cookie:cb,...request})).status,409);assert.equal(hash((await api('beasts/'+idA,{cookie:cb})).data.record),beforeTwin);pass();
 check='stale and simultaneous conditional writes cannot overwrite one another';assert.equal((await api('beasts/'+idA,{cookie:ca,method:'PUT',body:{...body,eventId:randomUUID()}})).status,409);const concurrent=await Promise.all([0,1].map(i=>api('beasts/'+idA,{cookie:ca,method:'PUT',body:{action:{kind:'memory',text:'CONCURRENT SYNTHETIC '+i},eventId:randomUUID(),version:changed.data.version}})));assert.equal(concurrent.filter(x=>x.status===200).length,1);assert.ok(concurrent.some(x=>[409,412].includes(x.status)));pass();
 check='explicit one-use device pairing restores only the issued private owner';const paired=await api('pair',{cookie:ca,method:'POST',body:{action:'issue'}});assert.equal(paired.status,200);assert.equal((await api('pair',{method:'POST',body:{action:'redeem',pairCode:paired.data.pairCode}})).status,403);const redeemed=await api('pair',{method:'POST',body:{action:'redeem',consent:true,pairCode:paired.data.pairCode}});assert.equal(redeemed.status,200);const cc=cookieOf(redeemed);assert.equal((await api('beasts/'+idA,{cookie:cc})).data.record.owner,a.data.owner);assert.equal((await api('beasts/'+idB,{cookie:cc})).status,404);assert.equal((await api('pair',{method:'POST',body:{action:'redeem',consent:true,pairCode:paired.data.pairCode}})).status,403);pass();
 check='actual Azure state survives a production server restart with the same credential';const before=(await api('beasts/'+idA,{cookie:cc})).data;await stop();await start();const after=await api('beasts/'+idA,{cookie:cc});assert.equal(after.status,200);assert.equal(hash(after.data.record),hash(before.record));pass();
 check='corrupt cloud checkpoint fails closed and explicit recovery advances its version';const base=scope+'/users/'+a.data.owner+'/beasts/'+idA,head=JSON.parse((await io.get(base+'/head.json')).text),path=base+'/commits/'+head.eventId+'.json',commit=await io.get(path);await io.put(path,'{"corrupt":"SYNTHETIC TEST ONLY"}',{ifMatch:commit.etag});assert.equal((await api('beasts/'+idA,{cookie:ca})).status,422);changed=await api('beasts/'+idA,{cookie:ca,method:'PUT',body:{action:{kind:'recover'},eventId:randomUUID(),version:head.sequence}});assert.equal(changed.status,200);assert.ok(changed.data.version>head.sequence);assert.equal(changed.data.record.growth.optedIn,false);pass();
 check='reset retains immutable genesis while deletion removes all private commit history';const reset=await api('beasts/'+idA,{cookie:ca,method:'PUT',body:{action:{kind:'reset'},eventId:randomUUID(),version:changed.data.version}});assert.equal(reset.status,200);assert.equal(reset.data.record.conversations.length,0);assert.equal(reset.data.record.sync.conversationConsent,false);assert.equal(hash(reset.data.record.quantumGenesis),report.identities.genesisA);assert.equal((await api('beasts/'+idA,{cookie:ca,method:'DELETE',body:{}})).status,200);assert.equal((await api('beasts/'+idA,{cookie:ca})).status,410);assert.equal((await io.list(base+'/commits/')).length,0);assert.equal((await api('beasts/'+idB,{cookie:cb})).status,200);pass();
 check='revocation invalidates all paired credentials and erases private data';assert.equal((await api('session',{cookie:ca,method:'DELETE',body:{}})).status,200);assert.equal((await api('beasts',{cookie:cc})).status,403);assert.equal((await api('session',{cookie:cb,method:'DELETE',body:{}})).status,200);assert.equal((await api('beasts',{cookie:cb})).status,403);pass();
 report.status='PASSED';
}catch(error){report.status='FAILED';report.failedCheck=check;report.failureClass=error?.code||error?.name||'HTTP_ACCEPTANCE_FAILED';}
finally{
 await stop();try{for(const name of await io.list(scope+'/')){const blob=await io.get(name);if(blob)await io.delete(name,{ifMatch:blob.etag});}assert.equal((await io.list(scope+'/')).length,0);report.cleanup=true;}catch{report.cleanupError='ISOLATED_CLEANUP_FAILED';}
 writeFileSync(out+'/http-report.json',JSON.stringify(report,null,2));console.log(JSON.stringify({status:report.status,checks:report.checks.length,cleanup:report.cleanup,failedCheck:report.failedCheck||null}));
}
if(report.status!=='PASSED'||!report.cleanup)process.exitCode=1;
