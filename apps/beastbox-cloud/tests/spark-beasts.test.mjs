import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import {buildGenome} from '../public/spark/genome.mjs';
import {buildQbeast, loadQbeast, serializeQbeast} from '../public/spark/qbeast.mjs';
import {renderBeast} from '../public/spark/draw.mjs';
import {catalogForms,CORE_RECIPES,RARE_KEYS} from '../public/spark/roster.mjs';

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
  assert.match(read('apps/beastbox-cloud/app/page.tsx'), /href="\/spark\/index.html"/);
  assert.match(read('apps/beastbox-cloud/next.config.ts'), /source: '\/spark'/);
});

test('public bestiary always exposes the complete core and rare visual catalog',()=>{
 const table=JSON.parse(read('apps/beastbox-cloud/public/spark/runs.json'));
 const by=new Map(table.runs.map(row=>[row.k,expand(row)]));
 const forms=catalogForms(by);
 assert.equal(CORE_RECIPES.length,11);
 assert.equal(RARE_KEYS.length,12);
 assert.equal(forms.length,48);
 assert.equal(forms.filter(row=>row.rare).length,12);
 assert.equal(new Set(forms.filter(row=>!row.rare&&row.label!=='Charlet line').map(row=>row.body)).size,11);
 assert.equal(forms.some(row=>row.name==='Charlet'),true);
 assert.deepEqual([...new Set(forms.filter(row=>!row.rare&&row.label!=='Charlet line').map(row=>row.stage))].sort(),[1,2,3]);
 const app=read('apps/beastbox-cloud/public/spark/app.mjs');
 const html=read('apps/beastbox-cloud/public/spark/index.html');
 assert.match(app,/catalogForms\(byKey\)/);
 assert.match(app,/catalog-count/);
 assert.match(html,/id="catalog"/);
 assert.match(html,/11 body families/);
 assert.match(html,/12 recorded rare forms/);
});
