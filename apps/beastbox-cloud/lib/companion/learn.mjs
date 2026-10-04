/**
 * On-device pattern companion.
 *
 * A fixed Hebbian matrix plus word-to-word counts. Each accepted exchange
 * updates weights in the browser. This is not a conscious system and it does
 * not claim understanding. Optional local Ollama text is only extra wording;
 * the weights still move from the exchange itself.
 */

export const MIND_SCHEMA = "beastbox-hebbian-mind-v1";
export const DIM = 16;
const ETA = 0.15;
const CLIP = 4;

const BLOCKED = /\b(?:porn|nude|nudes|sex|sexual|xxx|suicide|kys|nigger|faggot|retard)\b/i;

export function createMind() {
  return {
    schema: MIND_SCHEMA,
    dim: DIM,
    steps: 0,
    tokenCount: 0,
    vocab: {},
    next: {},
    weights: Array.from({ length: DIM }, () => Array.from({ length: DIM }, () => 0)),
  };
}

export function isKidSafe(text) {
  return !BLOCKED.test(String(text || ""));
}

export function tokenize(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^a-z0-9'\s]/g, " ")
    .split(/\s+/)
    .map((word) => word.replace(/^'+|'+$/g, ""))
    .filter((word) => word.length >= 2 && word.length <= 16);
}

function fnv(text) {
  let h = 2166136261;
  for (const byte of new TextEncoder().encode(text)) h = Math.imul(h ^ byte, 16777619) >>> 0;
  return h >>> 0;
}

export function features(token) {
  const vector = Array.from({ length: DIM }, () => 0);
  let h = fnv(token);
  for (let i = 0; i < 3; i++) {
    vector[h % DIM] += 1;
    h = Math.imul(h ^ 0x9e3779b9, 16777619) >>> 0;
  }
  let norm = 0;
  for (const value of vector) norm += value * value;
  norm = Math.sqrt(norm) || 1;
  return vector.map((value) => value / norm);
}

function clip(value) {
  return Math.max(-CLIP, Math.min(CLIP, Math.round(value * 10000) / 10000));
}

export function observeText(mind, text) {
  if (!isKidSafe(text)) return { mind, learned: false, reason: "blocked" };
  const tokens = tokenize(text);
  if (!tokens.length) return { mind, learned: false, reason: "empty" };
  for (const token of tokens) {
    const row = mind.vocab[token] || { count: 0 };
    row.count += 1;
    mind.vocab[token] = row;
    mind.tokenCount += 1;
  }
  for (let i = 0; i < tokens.length - 1; i++) {
    const left = tokens[i];
    const right = tokens[i + 1];
    const bag = mind.next[left] || {};
    bag[right] = (bag[right] || 0) + 1;
    mind.next[left] = bag;
    const a = features(left);
    const b = features(right);
    for (let r = 0; r < DIM; r++) {
      if (!a[r]) continue;
      for (let c = 0; c < DIM; c++) {
        if (!b[c]) continue;
        mind.weights[r][c] = clip(mind.weights[r][c] + ETA * a[r] * b[c]);
      }
    }
  }
  if (tokens.length === 1) {
    const a = features(tokens[0]);
    for (let r = 0; r < DIM; r++) {
      if (!a[r]) continue;
      mind.weights[r][r] = clip(mind.weights[r][r] + ETA * a[r]);
    }
  }
  mind.steps += 1;
  return { mind, learned: true, tokens };
}

export function weightSum(mind) {
  let sum = 0;
  for (const row of mind.weights) for (const value of row) sum += Math.abs(value);
  return Math.round(sum * 10000) / 10000;
}

export function topLink(mind, token) {
  const bag = mind.next[token];
  if (!bag) return null;
  let best = null;
  let score = 0;
  for (const [word, count] of Object.entries(bag)) {
    if (count > score) {
      best = word;
      score = count;
    }
  }
  return best ? { word: best, count: score } : null;
}

export function replyFromMind(mind, text, name = "Beast") {
  if (!isKidSafe(text)) {
    return `${name} skips unkind or grown-up words. Those are not stored.`;
  }
  const tokens = tokenize(text);
  if (!tokens.length) return `${name} is listening. Try a short phrase.`;
  const last = tokens[tokens.length - 1];
  const link = topLink(mind, last) || topLink(mind, tokens[0]);
  if (link) {
    return `${name} links "${last}" with "${link.word}" (${link.count}). Pattern memory only. I am not conscious.`;
  }
  const known = tokens.filter((token) => mind.vocab[token]);
  if (known.length) {
    return `${name} has seen ${known[0]} ${mind.vocab[known[0]].count} time${mind.vocab[known[0]].count === 1 ? "" : "s"}. Say what comes next and the weights will move.`;
  }
  return `${name} has no link for that yet. Repeat a pair of words and the Hebbian matrix updates on this device.`;
}

export function exportMind(mind) {
  return {
    schema: MIND_SCHEMA,
    dim: DIM,
    steps: mind.steps,
    tokenCount: mind.tokenCount,
    vocab: mind.vocab,
    next: mind.next,
    weights: mind.weights,
  };
}

export function importMind(raw) {
  const mind = createMind();
  if (!raw || raw.schema !== MIND_SCHEMA || raw.dim !== DIM) return mind;
  mind.steps = Number(raw.steps) || 0;
  mind.tokenCount = Number(raw.tokenCount) || 0;
  mind.vocab = raw.vocab && typeof raw.vocab === "object" ? raw.vocab : {};
  mind.next = raw.next && typeof raw.next === "object" ? raw.next : {};
  if (Array.isArray(raw.weights) && raw.weights.length === DIM) {
    mind.weights = raw.weights.map((row) => Array.from({ length: DIM }, (_, i) => clip(Number(row?.[i]) || 0)));
  }
  return mind;
}

export function memoryDb() {
  const bag = new Map();
  return {
    async get(key) {
      return bag.has(key) ? JSON.parse(JSON.stringify(bag.get(key))) : null;
    },
    async set(key, value) {
      bag.set(key, JSON.parse(JSON.stringify(value)));
    },
  };
}

export async function saveMind(db, mind) {
  await db.set("mind", exportMind(mind));
}

export async function loadMind(db) {
  return importMind(await db.get("mind"));
}

export function openIndexedDb(factory = globalThis.indexedDB) {
  return new Promise((resolve, reject) => {
    if (!factory) {
      reject(new Error("IndexedDB is unavailable"));
      return;
    }
    const request = factory.open("beastbox-companion-v1", 1);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains("kv")) db.createObjectStore("kv");
    };
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const db = request.result;
      const op = (mode, fn) => new Promise((ok, fail) => {
        const tx = db.transaction("kv", mode);
        const store = tx.objectStore("kv");
        const result = fn(store);
        result.onsuccess = () => ok(result.result);
        result.onerror = () => fail(result.error);
      });
      resolve({
        async get(key) {
          const value = await op("readonly", (store) => store.get(key));
          return value ?? null;
        },
        async set(key, value) {
          await op("readwrite", (store) => store.put(value, key));
        },
      });
    };
  });
}
