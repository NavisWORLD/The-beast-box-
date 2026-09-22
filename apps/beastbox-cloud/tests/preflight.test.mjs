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
 assert.match(proxy,/const POST_ALLOW=new Set\(\['chat','chat-start','context','connections','bio','observations','models','azure-read'\]\)/);
 assert.match(proxy,/endpoint==='azure-read'/);
 assert.match(proxy,/read_confirmed!==true/);
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


test('senses is a Settings-only control and cannot cover the chat composer',()=>{
 const live=read('components/live-senses.tsx');
 const studio=read('components/studio.tsx');
 assert.match(live,/visible:boolean/);
 assert.match(live,/onActivity:\(camera:boolean,speech:boolean\)=>void/);
 assert.match(live,/position:visible\?'relative':'absolute'/);
 assert.match(live,/visibility:visible\?'visible':'hidden'/);
 assert.doesNotMatch(live,/position:'fixed'|right:12,bottom:/);
 assert.match(studio,/<LiveSenses visible=\{page==='SETTINGS'\}/);
 assert.match(studio,/aria-label="Open sensing settings"/);
 // Mounted unconditionally at the content root; navigation must not recreate video.
 const mount=studio.indexOf('<LiveSenses visible=');
 assert.ok(mount>0 && mount<studio.indexOf("page==='BRAIN'?"));
 assert.match(studio,/aria-label="Stage file or photo locally"/);
 assert.match(studio,/Images and PDFs are locally staged only/);
});


test('model selection is owner-only, local verified, remote explicitly charged and durable',()=>{
 const bff=read('app/api/bridge/[endpoint]/route.ts');
 const bridge=read('bridge/owner_bridge.py');
 const ui=read('components/model-switcher.tsx');
 const studio=read('components/studio.tsx');
 assert.match(bff,/endpoint==='models'/);
 assert.match(bff,/Same-origin owner action required/);
 assert.match(bff,/Remote model activation requires explicit usage approval/);
 assert.match(bridge,/self\.chat_jobs\.run_when_idle/);
 assert.match(bridge,/def _model_catalog/);
 assert.match(bridge,/def _model_action/);
 assert.match(bridge,/not self\.app\.profile\.remote/);
 assert.match(ui,/Choose your brain/);
 assert.match(ui,/I explicitly approve this provider/);
 assert.match(ui,/choice==='local'/);
 assert.doesNotMatch(ui,/localStorage|sessionStorage|document\.cookie/);
 assert.match(studio,/<ModelSwitcher backendReachable=\{bridge\}/);
 assert.match(studio,/deadline=Date\.now\(\)\+660_000/);
 assert.match(studio,/typeof state\.error==='string'/);
});


test('correct Ollama Cloud model ID via owner-only key-preserving metadata update',()=>{
 const bff=read('app/api/bridge/[endpoint]/route.ts');
 const bridge=read('bridge/owner_bridge.py');
 const cloud=read('components/cloud-connections.tsx');
 const switcher=read('components/model-switcher.tsx');
 assert.match(bff,/action==='update_model'/);
 assert.match(bff,/action,model,provider/);
 assert.match(bff,/Same-origin owner action required/);
 assert.match(bridge,/self\.vault\.update_model/);
 assert.match(bridge,/Switch to local model in Brain Bay before editing/);
 assert.match(bridge,/gpt-oss:120b/);
 assert.match(cloud,/Save model ID \(keep encrypted key\)/);
 assert.match(cloud,/gpt-oss:120b/);
 assert.match(cloud,/direct API/i);
 assert.match(switcher,/direct API/i);
 assert.match(bridge,/saved\["config"\]\["model"\]\.endswith\("-cloud"\)/);
 assert.match(read('../../beastbox/cloud_connection_checks.py'),/MODEL_ID_MODE_MISMATCH/);
 assert.match(read('../../beastbox/cloud_connection_checks.py'),/MODEL_LISTED_AUTH_UNVERIFIED/);
 assert.doesNotMatch(cloud,/localStorage|sessionStorage/);
});


test('five-world surface does not replace the existing durable owner workstation',()=>{
 const ui=read('components/studio.tsx');
 const scene=read('components/cosmos-world.tsx');
 const css=read('app/globals.css');
 assert.match(ui,/COSMOS WORLD/);
 assert.match(ui,/<CosmosWorld connected=\{connected\}/);
 assert.match(scene,/const WORLDS:/);
 assert.match(scene,/WORLDS\.map/);
 assert.match(scene,/ILLUSTRATIVE GRAPHICS/);
 assert.match(scene,/webglcontextlost/);
 assert.match(scene,/ResizeObserver/);
 assert.match(scene,/prefers-reduced-motion/);
 assert.match(scene,/cancelAnimationFrame/);
 assert.match(css,/pointer-events:none!important/);
 assert.doesNotMatch(scene,/fetch\(|localStorage|sessionStorage|navigator\.mediaDevices/);
});
test('remote model grant is inspected before chat and recovery stays owner initiated',()=>{
 const ui=read('components/studio.tsx');
 const backend=read('bridge/owner_bridge.py');
 assert.match(ui,/reapproval_required:catalog\.reapproval_required===true/);
 assert.match(ui,/modelGate!==null&&!needsGrant/);
 assert.match(ui,/if\(!connected\|\|busy\|\|!prompt\.trim\(\)\)return/);
 assert.match(ui,/Use local model · no cloud charge/);
 assert.match(ui,/Review cloud model/);
 assert.match(ui,/if\(result\.no_paid_inference!==true\)/);
 assert.match(backend,/self\.app\.authority\.grant\("cloud"\)/);
 assert.match(backend,/reapproval_required/);
 assert.doesNotMatch(ui,/spend_approved:true.*choice:'local'/);
});

test('workstation has one main landmark and attachment input has an explicit name',()=>{
 const studio=read('components/studio.tsx');
 const login=studio.match(/<main className="login-screen"/g)||[];
 const shell=studio.match(/<main className="main-shell"/g)||[];
 assert.equal(login.length,1);
 assert.equal(shell.length,1);
 assert.match(studio,/aria-label="Choose files or photos to stage locally"/);
 assert.match(read('app/globals.css'),/Accessible contrast and touch affordances/);
});

test('Azure account-key mode and one-document retrieval do not grant ambient chat access',()=>{
 const connections=read('components/cloud-connections.tsx');
 const ui=read('components/studio.tsx');
 const backend=read('bridge/owner_bridge.py');
 const vault=read('../../beastbox/cloud_connections.py');
 const azure=read('../../beastbox/azure_read.py');
 assert.match(connections,/Storage account access key/);
 assert.match(connections,/read_confirmed:true/);
 assert.match(connections,/Stage for next chat/);
 assert.match(ui,/onAzureText=\{stageAzureText\}/);
 assert.match(backend,/read_owner_text/);
 assert.match(backend,/run_when_idle\(lambda: self\._azure_read_action\(data\)\)/);
 assert.match(vault,/auth_mode/);
 assert.match(azure,/MAX_CONTEXT_BYTES = 12_000/);
 assert.doesNotMatch(azure,/upload_blob|delete_blob|submit\(/);
});
