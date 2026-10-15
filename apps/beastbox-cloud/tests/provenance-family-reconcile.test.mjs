// Adopted from PR #344 (Cursor agent "Cosmic Finisher": provenance-labels + explainer only),
// reconciled with family-explain (#345): both vocabularies must make the same honesty claims.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {friendlyKind,PROVENANCE_KINDS} from '../lib/provenance-labels.mjs';
const fam=readFileSync(new URL('../lib/companion/family-explain.mjs',import.meta.url),'utf8');
test('Rigetti is a simulator in both vocabularies',()=>{assert.match(friendlyKind('rigetti-qvm-simulated'),/simulat/i);assert.match(fam,/simulator, not a quantum chip/);});
test('artist-drawn means no quantum seed in both',()=>{assert.match(friendlyKind('artist-drawn'),/no quantum seed/);assert.match(fam,/artist-drawn · no quantum seed/);});
test('IBM counts are recorded/historical, never live hardware claims',()=>{assert.match(friendlyKind('recorded-ibm-hardware'),/Recorded.*historical/);assert.match(fam,/RECORDED_IBM_HARDWARE/);});
test('the local growth rule is not hardware and not a simulator job in both',()=>{assert.match(friendlyKind('deterministic-fallback'),/no simulator job/);assert.match(fam,/not hardware and not a remote simulator job/);assert.ok(PROVENANCE_KINDS.includes('local-classical-qvm-inspired'));});
test('grow-in-cosmos mounts the explainer for genesis and growth',()=>{const g=readFileSync(new URL('../components/grow-in-cosmos.tsx',import.meta.url),'utf8');assert.match(g,/variant="genesis"/);assert.match(g,/variant="growth"/);});
