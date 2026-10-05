import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {buildGenome} from '../public/spark/genome.mjs';
import {buildQbeast, loadQbeast, serializeQbeast} from '../public/spark/qbeast.mjs';
import {renderBeast} from '../public/spark/draw.mjs';

const root = new URL('../../../', import.meta.url);
const read = (path) => readFileSync(new URL(path, root), 'utf8');

function expand(row) {
  const counts = {};
  for (const part of row.c.split(',')) {
    const [key, value] = part.split(':');
    counts[key] = Number(value);
  }
  return {key: row.k, backend: row.b, job_id: row.j, pub_index: row.p, num_bits: row.n, shots: row.s, counts, counts_sha256: row.h};
}

test('browser spark matches the Python golden genome and QBEAST1 bytes', () => {
  const table = JSON.parse(read('apps/beastbox-cloud/public/spark/runs.json'));
  const by = new Map(table.runs.map((row) => [row.k, expand(row)]));
  const cases = JSON.parse(read('spark-beasts/golden/case.json'));
  assert.equal(table.totals.entries, 5580);
  for (const item of cases) {
    const genome = buildGenome(item.traits, by.get(item.run), item.user);
    assert.deepEqual(genome, item.genome);
    const text = serializeQbeast(buildQbeast(genome));
    assert.equal(text, item.qbeast);
    const loaded = loadQbeast(text);
    assert.equal(loaded.card.name, genome.names[2]);
    const again = buildGenome(loaded.card.traits, by.get(loaded.card.run), loaded.card.user_id);
    assert.equal(again.seed, genome.seed);
    const pix = renderBeast(genome, 2, 'open');
    assert.equal(pix.length, 64 * 64 * 4);
    assert.ok([...pix].some((value, index) => index % 4 === 3 && value === 255));
  }
});

test('public spark page states the honesty boundary and links the game', () => {
  const html = read('apps/beastbox-cloud/public/spark/index.html');
  assert.match(html, /not live quantum computation, entanglement or quantum advantage/);
  assert.match(html, /not a medical device/);
  assert.match(html, /not conscious/);
  assert.match(html, /id="lost-cosmos" href="\/sol-game"/);
  assert.doesNotMatch(html,/Play in Living Universe|SIM_EARTH|Pocket Reality/);
  assert.match(html, /Download \.qbeast/);
  assert.match(html, /SOUND READY/);
  assert.match(html, /<button[^>]*id="music"[^>]*>[^<]*MUSIC ON<\/button>/);
  assert.match(html, /id="music-volume"/);
  for (const href of ['/', '/beast-cage', '/beast-cage/go', '/sol-game']) assert.ok(html.includes(`href="${href}"`), href);
  for (const target of ['#habitat', '#seed-lab', '#bestiary-section']) assert.ok(html.includes(`data-jump="${target}"`), target);
  const app = read('apps/beastbox-cloud/public/spark/app.mjs');
  assert.match(app, /SOUND_KEY='spark-beast-sound-v2'/);
  assert.match(app, /getBeastAudio/);
  assert.match(app, /beastAudio\.setScene/);
  assert.match(app, /function wirePageNavigation/);
  assert.match(app, /history\.replaceState/);
  assert.match(app, /window\.addEventListener\('pointerdown',unlockPreferredSound/);
  assert.match(app, /window\.addEventListener\('touchstart',unlockPreferredSound/);
  assert.match(app, /window\.addEventListener\('click',unlockPreferredSound/);
  assert.match(app, /soundWanted=readSoundWanted\(\)/);
  const sync = read('apps/beastbox-cloud/scripts/sync-spark-shared.mjs');
  assert.match(sync, /'beast-audio'/);
  assert.match(sync, /'beast-audio-engine'/);
  assert.match(read('apps/beastbox-cloud/app/page.tsx'), /href="\/spark\/index.html"/);
  assert.match(read('apps/beastbox-cloud/next.config.ts'), /source: '\/spark'/);
});
