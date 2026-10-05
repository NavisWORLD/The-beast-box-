// The gadget's Python port of beast-moves.mjs must pick the same moves as the browser.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

import { APP_LIB, ROOT, genomes, python } from './helpers.mjs';

test('Python moves match beast-moves.mjs exactly', async () => {
  const { buildMoveset, pickAttack } = await import(pathToFileURL(join(APP_LIB, 'beast-moves.mjs')).href);
  const cases = [...genomes, null, { element: 'ember', temperament: 'Fierce', seed: 'x' }, {}];
  const script = [
    'import json, sys',
    'from beastbox_musegadget.moves import build_moveset, pick_attack',
    'cases = json.load(sys.stdin)',
    'out = []',
    'for g in cases:',
    '    m = build_moveset(g)',
    '    out.append({"set": m, "picks": [pick_attack(m, n, t) for t in ("tap", "timer", "chat") for n in range(12)]})',
    'print(json.dumps(out))',
  ].join('\n');
  const res = await python(['-c', script], { env: { ...process.env, PYTHONPATH: ROOT }, input: JSON.stringify(cases) });
  const fromPython = JSON.parse(res.stdout);
  cases.forEach((genome, i) => {
    const set = buildMoveset(genome);
    assert.deepEqual(fromPython[i].set, JSON.parse(JSON.stringify(set)), `moveset ${i}`);
    const picks = ['tap', 'timer', 'chat'].flatMap((t) => Array.from({ length: 12 }, (_, n) => pickAttack(set, n, t)));
    assert.deepEqual(fromPython[i].picks, JSON.parse(JSON.stringify(picks)), `picks ${i}`);
  });
});
