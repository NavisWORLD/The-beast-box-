import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=path=>readFileSync(new URL('../'+path,import.meta.url),'utf8');
test('V2 marker establishes no scientific, identity or owner-access claims',()=>{
 const route=read('app/api/genesis-3d-release/route.ts');
 assert.match(route,/cosmic-genesis-v2-3d-20261002/);
 assert.match(route,/verified_physical_quantum_hardware:false/);
 assert.match(route,/claims_consciousness:false/);
 assert.match(route,/real_owner_telemetry_in_public_route:false/);
 assert.match(route,/server_side_identity_storage:false/);
 assert.doesNotMatch(route,/fetch\(|getUserMedia\(|process\.env|password|secret/i);
});
test('owner companion no longer resets emergency stop from stale sensor flags',()=>{
 const dock=read('components/cosmic-companion-dock.tsx');
 assert.match(dock,/stoppedRef\.current=true/);
 assert.match(dock,/if\(stoppedRef\.current\)return/);
 assert.match(dock,/profile=\{cosmeticProfile\}/);
 assert.doesNotMatch(dock,/if\(camera\|\|speech\)setStopped\(false\)/);
});
