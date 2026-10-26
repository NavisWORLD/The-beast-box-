// Beast Box ⇄ Muse gadget bridge client. Standalone ES module, no dependencies.
//
// Flow: the Muse app pairs with the Linux gadget over Bluetooth (the browser
// cannot advertise Bluetooth). The gadget runs a small bridge server. This
// module links one browser tab's beast to that bridge with a one-time short
// code, then carries Muse commands (feed, play, talk, attack, ...) to the live
// beast and its state back.
//
// A community gadget built on Meta's open source Muse Gadget SDK; not made or
// endorsed by Meta. Beasts are game companions, not conscious beings; their
// recorded IBM counts are a fixed seed, not a live quantum link.
//
//   const bridge = new BeastBoxBridge({ url: 'http://beastbox-pi.local:8787' });
//   const { code } = await bridge.startPairing({ label: 'Cory laptop' });
//   showCode(code);                       // user runs `musegadget-beastbox link CODE` or tells Muse the code
//   await bridge.waitForLink();
//   bridge.connect(createSessionHandler({ ... }));

export const STORAGE_KEY = 'beastbox-muse-bridge-v1';
export const ACTIONS = ['status', 'feed', 'play', 'talk', 'attack', 'moves', 'lost_cosmos'];

const sleep = (ms, signal) => new Promise((resolve, reject) => {
  const timer = setTimeout(resolve, ms);
  signal?.addEventListener('abort', () => { clearTimeout(timer); reject(new DOMException('aborted', 'AbortError')); }, { once: true });
});

/** Split a text/event-stream buffer into complete events; returns [events, rest]. */
export function parseSse(buffer) {
  const events = [];
  const blocks = buffer.replace(/\r\n/g, '\n').split('\n\n');
  const rest = blocks.pop() ?? '';
  for (const block of blocks) {
    let event = 'message';
    const data = [];
    for (const line of block.split('\n')) {
      if (line.startsWith(':')) continue;
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''));
    }
    if (data.length) events.push({ event, data: data.join('\n') });
  }
  return [events, rest];
}

export class BridgeHttpError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

export class BeastBoxBridge {
  constructor({ url, storage = globalThis.localStorage, fetch: fetchImpl = globalThis.fetch?.bind(globalThis), storageKey = STORAGE_KEY } = {}) {
    if (!url) throw new Error('BeastBoxBridge needs the gadget bridge url');
    this.url = String(url).replace(/\/+$/, '');
    this.storage = storage;
    this.fetch = fetchImpl;
    this.storageKey = storageKey;
    this.pending = null;
    this.controller = null;
    this.status = this.linked ? 'linked' : 'unlinked';
  }

  _read() {
    try { return JSON.parse(this.storage?.getItem(this.storageKey) || 'null'); } catch { return null; }
  }

  _write(value) {
    try {
      if (value) this.storage?.setItem(this.storageKey, JSON.stringify(value));
      else this.storage?.removeItem(this.storageKey);
    } catch { /* private browsing */ }
  }

  get linked() {
    const saved = this._read();
    return !!(saved && saved.url === this.url && saved.token);
  }

  get linkId() { return this._read()?.linkId || null; }

  async _call(method, path, body, token) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await this.fetch(this.url + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    let data = {};
    try { data = await response.json(); } catch { /* empty */ }
    if (!response.ok) throw new BridgeHttpError(response.status, data.error || `bridge answered HTTP ${response.status}`);
    return data;
  }

  /** Ask the gadget for a one-time code to show to the user. */
  async startPairing({ label = 'Beast Box browser' } = {}) {
    const data = await this._call('POST', '/v1/pair/start', { label });
    this.pending = { pairId: data.pair_id, secret: data.poll_secret, expiresAt: Date.now() + data.expires_in * 1000 };
    return { code: data.code, expiresIn: data.expires_in };
  }

  /** Wait until the gadget approves the code; stores the link token. */
  async waitForLink({ signal, intervalMs = 1500 } = {}) {
    if (!this.pending) throw new Error('call startPairing() first');
    const { pairId, secret, expiresAt } = this.pending;
    while (Date.now() < expiresAt) {
      const data = await this._call('POST', '/v1/pair/claim', { pair_id: pairId, poll_secret: secret });
      if (data.status === 'linked') {
        this._write({ url: this.url, token: data.token, linkId: data.link_id });
        this.pending = null;
        this.status = 'linked';
        return { linkId: data.link_id };
      }
      await sleep(intervalMs, signal);
    }
    this.pending = null;
    throw new BridgeHttpError(410, 'the pairing code expired; tap Pair again');
  }

  async pushState(state) {
    const saved = this._read();
    if (!saved?.token) return;
    await this._call('POST', '/v1/state', { state }, saved.token);
  }

  /**
   * Keep a live stream open and answer commands until disconnect() or revoke.
   * handler: { handle(command) -> {ok, result, state} , getState() -> state, onStatus?(status, detail) }
   */
  connect(handler, { retryMs = 2000, maxRetryMs = 30000 } = {}) {
    this.disconnect();
    const controller = new AbortController();
    this.controller = controller;
    const setStatus = (status, detail) => { this.status = status; handler.onStatus?.(status, detail); };
    const loop = async () => {
      let delay = retryMs;
      while (!controller.signal.aborted) {
        const saved = this._read();
        if (!saved?.token) { setStatus('unlinked'); return; }
        try {
          setStatus('connecting');
          const response = await this.fetch(this.url + '/v1/events', {
            headers: { Authorization: `Bearer ${saved.token}`, Accept: 'text/event-stream' },
            signal: controller.signal,
          });
          if (response.status === 401) { this._write(null); setStatus('revoked'); return; }
          if (!response.ok || !response.body) throw new BridgeHttpError(response.status, 'stream refused');
          const state = await handler.getState?.();
          if (state) await this.pushState(state).catch(() => undefined);
          setStatus('connected');
          delay = retryMs;
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          for (;;) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const [events, rest] = parseSse(buffer);
            buffer = rest;
            for (const item of events) {
              if (item.event !== 'command') continue;
              let command;
              try { command = JSON.parse(item.data); } catch { continue; }
              await this._answer(handler, command, saved.token);
            }
          }
        } catch (error) {
          if (controller.signal.aborted) break;
          setStatus('offline', error instanceof Error ? error.message : String(error));
        }
        if (controller.signal.aborted) break;
        await sleep(delay, controller.signal).catch(() => undefined);
        delay = Math.min(maxRetryMs, delay * 2);
      }
      setStatus(this.linked ? 'linked' : 'unlinked');
    };
    this.done = loop();
    return this.done;
  }

  async _answer(handler, command, token) {
    let reply;
    try {
      if (!ACTIONS.includes(command.action)) throw new Error(`unknown action ${command.action}`);
      reply = await handler.handle(command);
    } catch (error) {
      reply = { ok: false, error: error instanceof Error ? error.message : String(error) };
    }
    const body = { id: command.id, ok: reply?.ok !== false, result: reply?.result ?? null, state: reply?.state ?? null, error: reply?.error ?? null };
    await this._call('POST', '/v1/results', body, token).catch(() => undefined);
  }

  disconnect() {
    this.controller?.abort();
    this.controller = null;
  }

  /** Revoke this browser's link on the gadget and forget the token. */
  async revoke() {
    const saved = this._read();
    this.disconnect();
    if (saved?.token) await this._call('POST', '/v1/revoke', {}, saved.token).catch(() => undefined);
    this._write(null);
    this.status = 'unlinked';
  }
}

/** The beast summary the gadget shows to Muse. */
export function summarizeBeast(session, shownName = (b) => b?.displayName || 'Beast') {
  const beast = session?.beast;
  if (!beast) return { name: null, adopted: false };
  const genome = beast.genome || {};
  const stage = Number(beast.stage) || 1;
  const xp = Number(beast.xp) || 0;
  return {
    name: shownName(beast),
    species: genome.body || 'unknown',
    island: genome.island || null,
    element: genome.element || null,
    temperament: genome.temperament || null,
    mood: beast.mood || session.mood || 'idle',
    stage,
    stats: { xp, next_stage_xp: stage >= 3 ? null : [0, 40, 120][stage], bond: Number(beast.bond) || 0, energy: Number(beast.energy ?? 100), combat: (genome.stats && (genome.stats[stage] || genome.stats[String(stage)])) || {} },
    honesty: 'A game companion, not a conscious being. Recorded IBM counts are a fixed seed, not a live quantum link.',
  };
}

/**
 * Map bridge commands onto the Beast Box session functions, injected so this
 * module never imports app code. All of them are optional except change/getSession.
 *   change(mutate)            the BeastSessionProvider's change()
 *   getSession()              returns the current session
 *   care(draft, kind)         adventure.mjs care: 'feed' | 'pet' | 'rest' | 'spark'
 *   train(draft, hits, total) adventure.mjs train
 *   talkAndGrow(draft, text)  adventure.mjs talkAndGrow -> { reply }
 *   shownName(beast)          session.mjs shownName
 *   buildMoveset(genome), pickAttack(moveset, n, trigger)   beast-moves.mjs
 *   onAttack(move)            play the attack animation (e.g. dispatch a CustomEvent)
 *   lostCosmos()              Lost Cosmos progress object, or null
 */
export function createSessionHandler(deps) {
  const { change, getSession, care, train, talkAndGrow, shownName, buildMoveset, pickAttack, onAttack, lostCosmos, onStatus } = deps;
  let attacks = 0;
  const summary = (session) => summarizeBeast(session, shownName);

  async function mutate(fn) {
    let out;
    let snap;
    let done = false;
    change((draft) => { out = fn(draft); snap = summary(draft); done = true; });
    for (let i = 0; !done && i < 100; i += 1) await sleep(20);
    if (!done) throw new Error('the beast did not update');
    return { result: out, state: snap };
  }

  function need(fn, name) {
    if (typeof fn !== 'function') throw new Error(`${name} is not wired in this page`);
    return fn;
  }

  return {
    onStatus,
    getState: () => summary(getSession()),
    async handle({ action, args = {} }) {
      const session = getSession();
      if (!session?.beast) return { ok: false, error: 'no beast adopted in this browser yet', state: summary(session) };
      switch (action) {
        case 'status':
          return { ok: true, result: summary(session), state: summary(session) };
        case 'feed':
          return { ok: true, ...(await mutate((d) => ({ ...need(care, 'care')(d, 'feed'), food: String(args.food || 'a snack').slice(0, 60) }))) };
        case 'play': {
          const game = String(args.game || 'spark').toLowerCase();
          if (game === 'train') return { ok: true, ...(await mutate((d) => need(train, 'train')(d, Number(args.hits ?? 3), 6))) };
          if (game !== 'spark' && game !== 'pet') return { ok: false, error: 'game must be spark, pet or train' };
          return { ok: true, ...(await mutate((d) => need(care, 'care')(d, game))) };
        }
        case 'talk': {
          const text = String(args.message || '').trim();
          if (!text) return { ok: false, error: 'message is required' };
          return { ok: true, ...(await mutate((d) => need(talkAndGrow, 'talkAndGrow')(d, text))) };
        }
        case 'moves': {
          const set = need(buildMoveset, 'buildMoveset')(session.beast.genome);
          return { ok: true, result: { element: set.element, temperament: set.temperament, moves: set.moves.map(({ id, name, style, power }) => ({ id, name, style, power })) }, state: summary(session) };
        }
        case 'attack': {
          const set = need(buildMoveset, 'buildMoveset')(session.beast.genome);
          const wanted = String(args.move || '').toLowerCase();
          const chosen = set.moves.find((m) => [m.id, m.name, m.style].some((v) => v.toLowerCase() === wanted))
            || need(pickAttack, 'pickAttack')(set, attacks, 'chat');
          attacks += 1;
          onAttack?.(chosen);
          return { ok: true, result: { move: { id: chosen.id, name: chosen.name, style: chosen.style, power: chosen.power }, crit: !!chosen.crit, animated: typeof onAttack === 'function' }, state: summary(session) };
        }
        case 'lost_cosmos': {
          const progress = typeof lostCosmos === 'function' ? await lostCosmos() : null;
          return { ok: true, result: progress || { available: false, note: 'This page does not expose Lost Cosmos progress yet.' }, state: summary(session) };
        }
        default:
          return { ok: false, error: `unknown action ${action}` };
      }
    },
  };
}
