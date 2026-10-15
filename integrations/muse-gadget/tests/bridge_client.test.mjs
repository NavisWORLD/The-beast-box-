// End to end: the real browser client module and the real Beast Box session
// functions (apps/beastbox-cloud/lib/companion, imported read-only) linked to
// the real Python bridge, driven by the same `muse-command` the SDK runs.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

import { BeastBoxBridge, createSessionHandler, parseSse } from '../browser/beastbox-bridge-client.mjs';
import { APP_LIB, genomes, memoryStorage, python, startBridge } from './helpers.mjs';

const lib = (name) => import(pathToFileURL(join(APP_LIB, name)).href);

test('parseSse splits events and keeps the partial tail', () => {
  const [events, rest] = parseSse(': ping\n\nevent: command\ndata: {"a":1}\n\nevent: comm');
  assert.deepEqual(events, [{ event: 'command', data: '{"a":1}' }]);
  assert.equal(rest, 'event: comm');
});

test('a Muse command changes the live browser beast and its state flows back', async (t) => {
  const { createSession, exportSession, importSession, adoptBeast, shownName } = await lib('session.mjs');
  const { care, train, talkAndGrow } = await lib('adventure.mjs');
  const { buildMoveset, pickAttack } = await lib('beast-moves.mjs');

  // The browser's beast: the fixture genome, 36 xp, one feed away from evolving.
  let current = createSession();
  adoptBeast(current, genomes[0], '');
  Object.assign(current.beast, { xp: 36, bond: 11, energy: 72 });
  // Like BeastSessionProvider.change(): a copied draft, applied asynchronously.
  const change = (mutate) => setTimeout(() => { const draft = importSession(exportSession(current)); mutate(draft); current = draft; }, 0);
  const attacks = [];
  const statuses = [];

  const gadget = await startBridge();
  t.after(() => gadget.child.kill());
  const bridge = new BeastBoxBridge({ url: gadget.url, storage: memoryStorage() });

  // Tap Pair: the browser shows a code; Cory runs `musegadget-beastbox link CODE` on the gadget.
  const { code, expiresIn } = await bridge.startPairing({ label: 'Cory laptop' });
  assert.match(code, /^[A-Z2-9]{4}-[A-Z2-9]{4}$/);
  assert.equal(expiresIn, 600);
  const linking = bridge.waitForLink({ intervalMs: 100 });
  const linked = await python(['-m', 'beastbox_musegadget', 'link', code], { env: gadget.env });
  assert.equal(linked.code, 0, linked.stderr);
  assert.match(linked.stdout, /Linked Cory laptop/);
  await linking;
  assert.equal(bridge.linked, true);

  const handler = createSessionHandler({
    change, getSession: () => current, care, train, talkAndGrow, shownName, buildMoveset, pickAttack,
    onAttack: (move) => attacks.push(move.name), onStatus: (s) => statuses.push(s),
  });
  bridge.connect(handler, { retryMs: 100 });
  t.after(() => bridge.disconnect());
  for (let i = 0; i < 100 && bridge.status !== 'connected'; i += 1) await new Promise((r) => setTimeout(r, 50));
  assert.equal(bridge.status, 'connected');

  const muse = async (name, params = {}) => {
    const out = await python(['-m', 'beastbox_musegadget', 'muse-command', name], { env: gadget.env, input: JSON.stringify(params) });
    return JSON.parse(out.stdout);
  };

  const status = await muse('beastbox.status');
  assert.equal(status.ok, true, JSON.stringify(status));
  assert.match(status.payload.source, /^live browser beast/);
  assert.equal(status.payload.result.name, 'Rimecoil');
  assert.equal(status.payload.result.species, 'serpent');

  const fed = await muse('beastbox.feed', { food: 'star berries' });
  assert.equal(fed.ok, true, JSON.stringify(fed));
  assert.equal(current.beast.xp, 42, 'the browser beast itself was fed');
  assert.equal(current.beast.stage, 2);
  assert.equal(shownName(current.beast), 'Glacecoil');
  assert.equal(fed.payload.beast.name, 'Glacecoil', 'state flowed back to Muse');
  assert.equal(fed.payload.result.evolved, true);

  const played = await muse('beastbox.play', { game: 'train', hits: 6 });
  assert.equal(played.payload.result.score, 6);
  assert.equal(current.train.rounds, 1);

  const talk = await muse('beastbox.talk', { message: 'hello from Muse' });
  assert.equal(talk.ok, true, JSON.stringify(talk));
  assert.equal(typeof talk.payload.result.reply, 'string');
  assert.ok(current.chat.some((turn) => turn.role === 'you' && turn.text === 'hello from Muse'));

  const attack = await muse('beastbox.attack', { move: 'beam' });
  assert.equal(attack.payload.result.move.name, 'Rime Lance');
  assert.equal(attack.payload.result.animated, true);
  assert.deepEqual(attacks, ['Rime Lance']);

  const moves = await muse('beastbox.moves');
  assert.deepEqual(moves.payload.result.moves.map((m) => m.name), buildMoveset(current.beast.genome).moves.map((m) => m.name));

  const lost = await muse('beastbox.lost_cosmos');
  assert.equal(lost.payload.result.available, false);

  // Revoke from the browser: the token stops working and the gadget forgets the link.
  await bridge.revoke();
  assert.equal(bridge.linked, false);
  const links = await python(['-m', 'beastbox_musegadget', 'links'], { env: gadget.env });
  assert.match(links.stdout, /No linked browsers/);
  const after = await muse('beastbox.status');
  assert.equal(after.ok, false, 'no live beast and no gadget copy left');
  assert.ok(statuses.includes('connected'));
});

test('a wrong code links nothing', async (t) => {
  const gadget = await startBridge();
  t.after(() => gadget.child.kill());
  const bridge = new BeastBoxBridge({ url: gadget.url, storage: memoryStorage() });
  await bridge.startPairing();
  const out = await python(['-m', 'beastbox_musegadget', 'link', 'AAAA-2222'], { env: gadget.env });
  assert.equal(out.code, 1);
  assert.match(out.stderr, /unknown, used or expired/);
  assert.equal(bridge.linked, false);
});
