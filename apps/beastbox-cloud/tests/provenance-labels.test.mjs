import test from 'node:test';
import assert from 'node:assert/strict';
import {PROVENANCE_KINDS,friendlyKind,formatGenesisReceipt,formatGrowthReceipt,formatTeacherAttribution} from '../lib/provenance-labels.mjs';

test('kind vocabulary is closed and simulator kinds never read as hardware',()=>{
 assert.ok(PROVENANCE_KINDS.includes('rigetti-qvm-simulated'));
 assert.ok(PROVENANCE_KINDS.includes('deterministic-fallback'));
 assert.match(friendlyKind('rigetti-qvm-simulated'),/simulated/);
 assert.doesNotMatch(friendlyKind('rigetti-qvm-simulated'),/hardware/i);
 assert.match(friendlyKind('artist-drawn'),/no quantum seed/);
});

test('genesis receipts separate recorded sheets from classical seeds without inventing fields',()=>{
 const recorded=formatGenesisReceipt({genome:{seed:'ab'.repeat(32),quantum:{backend:'ibm_marrakesh',job_id:'db4te7slf4us73c3888g',counts_sha256:'00'.repeat(32)}}});
 assert.equal(recorded.advanced.kind,'recorded-quantum-genome');
 assert.equal(recorded.advanced.job_id,'db4te7slf4us73c3888g');
 assert.match(recorded.friendly,/recorded quantum count sheet/);
 assert.match(recorded.friendly,/not from live hardware today/);
 const classical=formatGenesisReceipt({genome:{seed:'cd'.repeat(32)}});
 assert.equal(classical.advanced.kind,'classical-seed');
 assert.equal(classical.advanced.job_id,null);
 assert.match(classical.friendly,/no quantum hardware involved/);
 const artist=formatGenesisReceipt({provenance:{kind:'artist-drawn'}});
 assert.match(artist.friendly,/no quantum seed/);
 assert.equal(artist.advanced.job_id,null);
});

test('growth receipts keep simulator, queued, blocked, and fallback distinct',()=>{
 const sim=formatGrowthReceipt({kind:'rigetti-qvm-simulated',provider:'azure-quantum/rigetti',target:'rigetti.sim.qvm',job_id:'job-1',shots:256,counts_sha256:'11'.repeat(32)});
 assert.equal(sim.advanced.simulated,true);
 assert.match(sim.friendly,/simulator job/);
 assert.match(sim.friendly,/Simulated counts, not hardware/);
 const queued=formatGrowthReceipt({kind:'QUEUED'});
 assert.match(queued.friendly,/No simulator job is claimed/);
 const blocked=formatGrowthReceipt({kind:'BLOCKED_EXTERNAL',error:'quota exhausted'});
 assert.match(blocked.friendly,/could not be reached/);
 const fallback=formatGrowthReceipt({kind:'deterministic-fallback',error:'offline'});
 assert.equal(fallback.advanced.simulated,false);
 assert.match(fallback.friendly,/honest fallback step/);
});

test('teacher attribution unifies friendly and technical identity without claiming training',()=>{
 const pending=formatTeacherAttribution({route:'guest-rawrphos'});
 assert.match(pending.friendly,/Beast Box free host/);
 assert.equal(pending.advanced.model,null);
 assert.equal(pending.advanced.verified_at,null);
 const verified=formatTeacherAttribution({route:'guest-rawrphos',model:'rawrphos-native · 14K',verifiedAt:'2026-10-14T12:00:00.000Z'});
 assert.equal(verified.advanced.teacher,'RAWRPHØS guest');
 assert.match(verified.friendly,/voiced this reply/);
 assert.doesNotMatch(verified.friendly,/train|learned|absorbed/i);
 const ollama=formatTeacherAttribution({route:'local-ollama',model:'zeref'});
 assert.match(ollama.friendly,/My local Ollama/);
});
