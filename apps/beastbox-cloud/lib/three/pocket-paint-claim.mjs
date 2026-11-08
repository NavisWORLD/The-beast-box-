/** Newest cage-pocket tab paints. Older pocket tabs park until this one closes
 * or the person claims the page. The living world never joins this channel.
 * The id and stamp live in sessionStorage so an effect restart does not mint a
 * newer claim and steal the painter (that left a cleared black canvas). */
const CHANNEL = 'beastbox-pocket-paint';
const ID_KEY = 'beastbox-pocket-paint-id';
const STAMP_KEY = 'beastbox-pocket-paint-stamp';

function read(store, key) {
  try { return store?.getItem(key) ?? null; } catch { return null; }
}
function write(store, key, value) {
  try { store?.setItem(key, String(value)); } catch { /* private mode */ }
}
function mintId(now) {
  const tick = typeof performance !== 'undefined' ? Math.floor(performance.now()) : 0;
  return `p${now.toString(36)}-${tick.toString(36)}`;
}

export function createPocketPaintClaim(options = {}) {
  const store = options.storage || globalThis.sessionStorage;
  const now = options.now || (() => Date.now());
  const onChange = options.onChange;
  const id = read(store, ID_KEY) || mintId(now());
  write(store, ID_KEY, id);
  let stamp = Number(read(store, STAMP_KEY));
  if (!Number.isFinite(stamp) || stamp <= 0) stamp = now();
  write(store, STAMP_KEY, stamp);
  const peers = new Map([[id, stamp]]);
  let lead = true;
  let lastHeard = now();
  let channel = null;
  let heart = 0;

  const tell = kind => {
    try { channel?.postMessage({role: 'pocket', id, stamp, kind}); } catch { /* channel closed */ }
  };
  const elect = () => {
    let bestId = id;
    let bestStamp = stamp;
    for (const [pid, pst] of peers) {
      if (pst > bestStamp || (pst === bestStamp && pid > bestId)) { bestId = pid; bestStamp = pst; }
    }
    const next = bestId === id;
    if (next !== lead) { lead = next; onChange?.(lead); }
  };
  const note = msg => {
    if (!msg || msg.role !== 'pocket' || !msg.id || msg.id === id) return;
    lastHeard = now();
    if (msg.kind === 'release') { peers.delete(msg.id); elect(); return; }
    peers.set(msg.id, Number(msg.stamp) || 0);
    elect();
  };
  try {
    channel = new BroadcastChannel(CHANNEL);
    channel.onmessage = event => note(event.data);
  } catch { channel = null; }

  const claim = fresh => {
    if (fresh) {
      stamp = Math.max(now(), stamp + 1);
      write(store, STAMP_KEY, stamp);
    }
    peers.set(id, stamp);
    lastHeard = now();
    tell('claim');
    elect();
  };
  claim(false);
  heart = setInterval(() => {
    if (lead) tell('claim');
    else if (now() - lastHeard > 1500) {
      for (const pid of [...peers.keys()]) if (pid !== id) peers.delete(pid);
      elect();
    }
  }, 400);
  heart.unref?.();

  return {
    leads: () => lead,
    claim: () => claim(true),
    close() {
      clearInterval(heart);
      tell('release');
      try { channel?.close(); } catch { /* already closed */ }
      channel = null;
    }
  };
}
