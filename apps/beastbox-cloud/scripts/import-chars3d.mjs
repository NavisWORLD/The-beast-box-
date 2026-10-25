#!/usr/bin/env node
/**
 * Copy Cosmo's light chars3d pack into public/creatures3d/custom/ and write the slot manifest.
 * Usage: node scripts/import-chars3d.mjs <chars3d-dir>
 * Deterministic: no clock, no random. Each rig json gets the slot schema, id, honesty line and format tag added;
 * everything else in it is copied untouched. Zeref's own art is not in the pack and is never touched here.
 */
import {readFileSync, writeFileSync, mkdirSync, copyFileSync, statSync} from 'node:fs';
import {join, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
const src = process.argv[2];
if (!src) { console.error('usage: node scripts/import-chars3d.mjs <chars3d-dir>'); process.exit(2); }
const out = join(dirname(fileURLToPath(import.meta.url)), '..', 'public', 'creatures3d', 'custom');
mkdirSync(out, {recursive: true});
// slot id -> pack key. The art-* ids are the world residents (lib/companion/artist-residents.mjs).
const MAP = {
  'art-kairo': 'kairo', 'art-frostmitt': 'frost', 'art-nyxbean': 'kittenref', 'art-velvetcoil': 'velvetcoil', 'art-shardhowl': 'shardhowl',
  'kitten': 'kitten', 'zeref64': 'zeref64', 'wisp_nebula': 'wisp_nebula', 'wisp_aurora': 'wisp_aurora', 'wisp_starlight': 'wisp_starlight',
};
const HONESTY = 'Artistic 3D model by Cosmo. SEEDED procedural build (seed from the recorded IBM ibm_marrakesh run, not live quantum input). Motion amplitudes are SIMULATED. Not a measured quantum phenotype.';
const report = JSON.parse(readFileSync(join(src, 'tri_report.json'), 'utf8'));
const species = JSON.parse(readFileSync(join(src, 'wisp_species.json'), 'utf8')).species;
const models = {};
for (const [id, key] of Object.entries(MAP)) {
  const glbSrc = join(src, key, key + '.glb');
  const rig = JSON.parse(readFileSync(join(src, key, key + '_rig.json'), 'utf8'));
  copyFileSync(glbSrc, join(out, id + '.glb'));
  const bytes = statSync(glbSrc).size;
  const sha = createHash('sha256').update(readFileSync(glbSrc)).digest('hex');
  if (report[key] && report[key].bytes !== bytes) throw new Error(key + ': size differs from tri_report.json');
  writeFileSync(join(out, id + '.rig.json'), JSON.stringify({schema: 'beastbox-creature-model-slot-v1', id, rig_format: 'chars3d-node-rig-v1', forward: '+Z', honesty: HONESTY, ...rig, glb: id + '.glb'}, null, 1) + '\n');
  const e = {glb: id + '.glb', rig: id + '.rig.json', tier: 'light', bytes, tris: report[key].tris, sha256: sha};
  if (key.startsWith('wisp_')) {
    const fam = key.slice(5);
    e.variants = Object.fromEntries(Object.entries(species).filter(([, v]) => v.family === fam).map(([name, v]) => [name, {glow_hex: v.glow_hex, materials: v.materials, action_multipliers: v.action_multipliers}]));
  }
  models[id] = e;
}
writeFileSync(join(out, 'manifest.json'), JSON.stringify({schema: 'beastbox-creature-model-slot-v1', _note: 'Delivered light GLB plus rig json per creature id (Cosmo chars3d v1, validator 0 errors). SEEDED, not a measured quantum phenotype. Not tested on a real phone. The sprite or sculpted body stays the fallback.', models}, null, 1) + '\n');
console.log('wrote', Object.keys(models).length, 'models');
