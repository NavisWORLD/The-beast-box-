import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');
test('existing app gains install metadata without changing authenticated backend paths',()=>{
  assert.match(read('app/manifest.ts'),/display: 'standalone'/);
  assert.match(read('app/layout.tsx'),/appleWebApp/);
  assert.match(read('app/layout.tsx'),/manifest: '\/manifest.webmanifest'/);
  assert.doesNotMatch(read('components/install-app.tsx'),/navigator\.serviceWorker\.register|localStorage/);
  const studio=read('components/studio.tsx');
  assert.match(studio,/SubstrateSignals events=\{trace\}/);
  assert.match(studio,/<InstallApp\/>/);
  assert.doesNotMatch(studio,/ActivationDeck/);
});
test('signals are derived only from real trace events',()=>{
  assert.match(read('components/substrate-signals.tsx'),/substrate-signal-v1/);
  assert.doesNotMatch(read('components/substrate-signals.tsx'),/Math\.random|fake|mockSignals/);
});
