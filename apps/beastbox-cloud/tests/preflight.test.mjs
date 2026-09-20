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
 assert.match(proxy,/const POST_ALLOW=new Set\(\['chat','context'\]\)/);
 assert.doesNotMatch(proxy,/['"]workspace\/write['"]/);
});
