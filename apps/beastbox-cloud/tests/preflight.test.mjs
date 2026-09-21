import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read = p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('no credentials stored in app',()=>{
 const env=read('.env.example');
 for(const key of ['BEASTBOX_OWNER_PASSWORD','BEASTBOX_CLOUD_AUTH_SECRET','BEASTBOX_CLOUD_BRIDGE_URL','BEASTBOX_CLOUD_BRIDGE_TOKEN']) assert.match(env,new RegExp('^'+key+'=$','m'));
 assert.doesNotMatch(read('lib/security.ts'), /TYPESAFE_API_KEY|sk-proj-/);
});
test('backend unavailable fails closed',()=>{
 const proxy=read('app/api/bridge/[endpoint]/route.ts');
 assert.match(proxy,/if \(!bridgeConfigured\(\)\) return safeJson\(503/);
 assert.match(proxy,/redirect:'error'/);
 assert.match(proxy,/No model call was performed/);
});
test('auth uses HMAC cookie and server verification',()=>{
 const auth=read('lib/security.ts');
 assert.match(auth,/createHmac\('sha256'/);
 assert.match(auth,/httpOnly: true/);
 assert.match(auth,/sameSite: 'strict'/);
 assert.match(read('app/api/bridge/[endpoint]/route.ts'),/if \(!await isOwner\(\)\)/);
});
test('images and PDFs stay local until real storage',()=>{
 const ui=read('components/studio.tsx');
 assert.match(ui,/Images and PDFs are locally staged only/);
 assert.match(ui,/No response is simulated/);
});
test('proxy excludes arbitrary tools and filesystem',()=>{
 const proxy=read('app/api/bridge/[endpoint]/route.ts');
 assert.match(proxy,/const POST_ALLOW=new Set\(\['chat','chat-start','context','connections','bio','observations'\]\)/);
 assert.doesNotMatch(proxy,/['"]workspace\/write['"]/);
});

test('authenticated status probes actual durable runtime rather than treating env vars as reachability',()=>{
 const source=read('app/api/status/route.ts');
 assert.match(source,/const owner=await isOwner\(\)/);
 assert.match(source,/if\(!bridgeConfigured\(\)\)return result\(true,'BRIDGE_SETTINGS_MISSING'\)/);
 assert.match(source,/getHostJson\('orbit'\)/);
 assert.match(source,/getHostJson\('provider'\)/);
 assert.match(source,/AbortSignal\.timeout\(5_000\)/);
 assert.match(source,/BRIDGE_AUTH_REJECTED/);
 assert.match(source,/MODEL_PROFILE_CONFIGURED_NOT_ATTESTED/);
 assert.doesNotMatch(source,/BEASTBOX_CLOUD_BRIDGE_TOKEN.*(console|JSON\.stringify)/);
 const studio=read('components/studio.tsx');
 assert.match(studio,/status\.backendReachable===true/);
 assert.match(studio,/BRIDGE_SETTINGS_MISSING/);
});

test('BYOK provider credentials are owner-only, same-origin and never browser-persisted',()=>{
 const bff=read('app/api/bridge/[endpoint]/route.ts');
 const ui=read('components/cloud-connections.tsx');
 assert.match(bff,/Same-origin owner action required/);
 assert.match(bff,/Explicit model-spending approval required/);
 assert.match(bff,/if \(!await isOwner\(\)\)/);
 assert.doesNotMatch(ui,/localStorage|sessionStorage|document\.cookie/);
 assert.match(ui,/type="password"/);
 assert.match(ui,/HOST_KEY_REQUIRED/);
 assert.match(ui,/single-owner|Single-owner/);
 assert.match(ui,/ollama_cloud/);
 assert.match(ui,/ibm_quantum/);
 assert.match(ui,/azure_blob/);
});

test('bio requires owner, same-origin consent, and no implicit device or durable grant',()=>{
 const proxy=read('app/api/bridge/[endpoint]/route.ts');
 const ui=read('components/bio-panel.tsx');
 assert.match(proxy,/endpoint==='connections'\|\|endpoint==='bio'/);
 assert.match(proxy,/Invalid or unconsented bio submission/);
 assert.match(proxy,/persist_confirmed/);
 assert.match(ui,/BEASTBOX_BIO_INGEST_ENABLED=yes/);
 assert.match(ui,/BEASTBOX_BIO_PERSIST_ENABLED=yes/);
 assert.match(ui,/Preview without saving/);
 assert.doesNotMatch(ui,/getUserMedia\(|navigator\.bluetooth|localStorage|sessionStorage/);
});


test('device sensing is gesture-only, local and cannot silently persist media',()=>{
 const ui=read('components/device-panel.tsx');
 const studio=read('components/studio.tsx');
 assert.match(ui,/getUserMedia\(\{video:/);
 assert.match(ui,/getUserMedia\(\{audio:/);
 assert.match(ui,/aria-label="Local camera preview"/);
 assert.match(ui,/visibilitychange/);
 assert.match(ui,/getFloatTimeDomainData/);
 assert.match(ui,/getImageData/);
 assert.match(ui,/I choose to draft these numeric summaries/);
 assert.match(ui,/Add to chat draft \(do not send yet\)/);
 assert.match(ui,/stopCamera\(\);stopMic\(\)/);
 assert.doesNotMatch(ui,/fetch\(|sendBeacon\(|MediaRecorder|toDataURL\(|toBlob\(|localStorage|sessionStorage/);
 assert.match(studio,/<DevicePanel canSend=\{connected\}/);
 assert.match(studio,/setPrompt\(previous=>\[previous.trim\(\),summary\]/);
 assert.match(studio,/setPage\('BRAIN'\)/);
});

test('bio previews are separate from retention and model requests',()=>{
 const ui=read('components/bio-panel.tsx');
 assert.match(ui,/action:'preview'\|'persist'/);
 assert.match(ui,/persist_enabled/);
 assert.match(ui,/remote_enabled/);
 assert.match(ui,/No new memory or model request/);
 assert.match(ui,/Preview without saving/);
});


test('slow real CPU chat uses one idempotent job with short same-origin polls',()=>{
 const proxy=read('app/api/bridge/[endpoint]/route.ts');
 const ui=read('components/studio.tsx');
 const bridge=read('bridge/owner_bridge.py');
 const jobs=read('../../beastbox/chat_jobs.py');
 assert.match(proxy,/chat-start/);
 assert.match(proxy,/chat-job/);
 assert.match(proxy,/endpoint==='chat-start'/);
 assert.match(proxy,/Same-origin owner action required/);
 assert.match(proxy,/incoming\.searchParams\.get\('id'\)/);
 assert.match(ui,/crypto\.randomUUID\(\)/);
 assert.match(ui,/bridge\/chat-start/);
 assert.match(ui,/bridge\/chat-job\?id=/);
 assert.doesNotMatch(ui,/api\('bridge\/chat',/);
 assert.match(bridge,/self\.chat_jobs\.start\(data\)/);
 assert.match(bridge,/self\.chat_jobs\.get\(query\["id"\]\[0\]\)/);
 assert.match(jobs,/self\._active/);
 assert.match(jobs,/self\._requests/);
 assert.match(jobs,/Check conversation before retrying/);
});


test('owner-live senses use real local classifier and explicit browser speech consent',()=>{
 const live=read('components/live-senses.tsx');
 const vision=read('lib/vision-classifier.ts');
 const studio=read('components/studio.tsx');
 assert.match(vision,/import\('@mediapipe\/tasks-vision'\)/);
 assert.match(vision,/efficientnet_lite0\.tflite/);
 assert.match(vision,/runningMode:'IMAGE'/);
 assert.match(live,/navigator\.mediaDevices\.getUserMedia\(\{video:/);
 assert.match(live,/webkitSpeechRecognition/);
 assert.match(live,/allowBrowserSpeech/);
 assert.match(live,/browser speech recognition, including possible off-device audio processing/);
 assert.match(live,/visibilitychange/);
 assert.match(live,/pagehide/);
 assert.match(live,/setInterval\(tick,12000\)/);
 assert.match(live,/Stop vision/);
 assert.match(live,/Stop speech/);
 assert.match(live,/setIncludeInChat/);
 assert.match(studio,/onContext=\{updateLiveContext\}/);
 assert.match(studio,/Owner-approved unverified device observations/);
 assert.doesNotMatch(live,/MediaRecorder|toDataURL\(|toBlob\(|localStorage|sessionStorage/);
});

test('durable device text requires same-origin owner permission and explicit retention',()=>{
 const live=read('components/live-senses.tsx');
 const bff=read('app/api/bridge/[endpoint]/route.ts');
 const bridge=read('bridge/owner_bridge.py');
 const validator=read('../../beastbox/device_observations.py');
 assert.match(bff,/endpoint==='observations'/);
 assert.match(bff,/Same-origin owner action required/);
 assert.match(bff,/Owner consent and bounded observation batch required/);
 assert.match(live,/persist_confirmed:true/);
 assert.match(live,/onDraft/);
 assert.match(bridge,/self\.device_memory_enabled/);
 assert.match(bridge,/store_external_memory/);
 assert.match(validator,/raw_media_transmitted/);
 assert.match(validator,/MAX_BATCH = 8/);
});
