import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('web app manifest and iOS metadata exist without caching private owner data',()=>{
  assert.match(read('app/manifest.ts'),/display: 'standalone'/);
  assert.match(read('app/manifest.ts'),/start_url: '\/'/);
  assert.match(read('app/layout.tsx'),/appleWebApp/);
  assert.doesNotMatch(read('components/install-app.tsx'),/navigator\.serviceWorker\.register|localStorage/);
});
test('owner activation is restricted to verified bounded operations and master stop',()=>{
  const proxy=read('app/api/bridge/[endpoint]/route.ts');
  assert.match(proxy,/endpoint==='activation'\|\|endpoint==='authority'/);
  assert.match(proxy,/Number\(input.max_tasks\)>3/);
  assert.match(proxy,/input.wall_seconds>8/);
  assert.match(proxy,/Cloud activation cannot grant tools/);
  assert.match(proxy,/input.action!=='master_stop'/);
  assert.match(proxy,/Same-origin owner action required/);
});
