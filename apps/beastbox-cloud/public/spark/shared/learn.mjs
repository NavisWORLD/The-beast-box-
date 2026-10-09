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
// Same browser mind, now with a read path for bounded co-occurrence memory.
// Inspired by Cory Davis's Genesis/QC67 research, pinned in docs/BEAST_AWAKENS_HF_INTEGRATION.md.
// This is classical associative learning, not model retraining or new quantum input.
export const ASSOCIATION_SCHEMA = 'beastbox-associations-v1';
export const ASSOCIATION_LIMITS = Object.freeze({concepts:128,links:384,vocab:256,tokens:128});
const STOP = new Set('about after again also because been being could from have into just like more only other some that their them then there these they this through what when where which while with would your'.split(' '));
const safeWord = word => /^[a-z0-9][a-z0-9']{1,15}$/.test(word) && !['constructor','prototype','__proto__'].includes(word) && isKidSafe(word);
const finite = (n,max=1e6) => typeof n==='number' && Number.isFinite(n) ? Math.max(0,Math.min(max,n)) : 0;
const rounded = n => Math.round(n*1000)/1000;
const emptyAssociations = () => ({schema:ASSOCIATION_SCHEMA,observations:0,concepts:{},links:{}});
function trimMap(map,limit,score=n=>n){
 const entries=Object.entries(map).sort((a,b)=>score(b[1])-score(a[1])||a[0].localeCompare(b[0],'en')).slice(0,limit);
 return Object.fromEntries(entries);
}
function associationTokens(text){return [...new Set(tokenize(text).filter(w=>w.length>=4&&!STOP.has(w)))].slice(0,12);}
function importAssociations(raw){
 const a=emptyAssociations();if(raw?.schema!==ASSOCIATION_SCHEMA)return a;
 a.observations=Math.floor(finite(raw.observations));
 if(raw.concepts&&typeof raw.concepts==='object'&&!Array.isArray(raw.concepts))for(const [w,n] of Object.entries(raw.concepts).slice(0,4096))if(safeWord(w)&&finite(n,8)>0)a.concepts[w]=rounded(finite(n,8));
 a.concepts=trimMap(a.concepts,ASSOCIATION_LIMITS.concepts);
 if(raw.links&&typeof raw.links==='object'&&!Array.isArray(raw.links))for(const [key,n] of Object.entries(raw.links).slice(0,4096)){
  const words=key.split('|');if(words.length===2&&words[0]<words[1]&&words.every(w=>safeWord(w)&&Object.hasOwn(a.concepts,w))&&finite(n,8)>0)a.links[key]=rounded(finite(n,8));
 }
 a.links=trimMap(a.links,ASSOCIATION_LIMITS.links);return a;
}
function learnAssociations(mind,text,{seed=''}={}){
 const a=importAssociations(mind.associations),words=associationTokens(text);if(!words.length)return;
 // A domain-separated deterministic draw from this existing genesis and event count.
 // Never rereads a seed pool, requests hardware, or claims fresh measurement.
 const rate=rounded(.4+fnv(`beastbox:association:v1:${seed}:${a.observations}`)/4294967296);
 for(const w of words)a.concepts[w]=rounded(Math.min(8,(a.concepts[w]||0)+rate));
 for(let i=0;i<words.length;i++)for(let j=i+1;j<words.length;j++){
  const key=[words[i],words[j]].sort().join('|');a.links[key]=rounded(Math.min(8,(a.links[key]||0)+rate));
 }
 a.observations=Math.min(1e6,a.observations+1);
 if(a.observations%5===0)for(const bag of [a.concepts,a.links])for(const key of Object.keys(bag)){
  bag[key]=rounded(bag[key]*.995);if(bag[key]<.05)delete bag[key];
 }
 a.concepts=trimMap(a.concepts,ASSOCIATION_LIMITS.concepts);
 a.links=trimMap(Object.fromEntries(Object.entries(a.links).filter(([k])=>k.split('|').every(w=>Object.hasOwn(a.concepts,w)))),ASSOCIATION_LIMITS.links);
 mind.associations=a;
}

/** Real persisted graph weights plus the pre-existing Hebbian matrix, read before learning this turn. */
export function recallAssociations(mind,text,limit=3){
 if(!mind)return [];const a=importAssociations(mind.associations),queries=associationTokens(text),scores=new Map();
 for(const [key,strength] of Object.entries(a.links)){
  const [left,right]=key.split('|');
  for(const [cue,word] of [[left,right],[right,left]])if(queries.includes(cue)&&!queries.includes(word)){
   const prior=scores.get(word)||{word,association:0,matrix:0,cues:[]};
   prior.association+=strength;prior.cues.push(cue);
   const x=features(cue),y=features(word);let signal=0;
   for(let r=0;r<DIM;r++)for(let c=0;c<DIM;c++)signal+=x[r]*finite(mind.weights?.[r]?.[c],CLIP)*y[c];
   prior.matrix+=Math.max(0,Math.min(4,signal));scores.set(word,prior);
  }
 }
 return [...scores.values()].map(h=>({...h,association:rounded(h.association),matrix:rounded(h.matrix),score:rounded(h.association+h.matrix*.1),cues:[...new Set(h.cues)]})).sort((a,b)=>b.score-a.score||a.word.localeCompare(b.word,'en')).slice(0,Math.max(0,Math.min(12,Math.floor(limit)||0)));
}

const BLOCKED = /\b(?:porn|nude|nudes|sex|sexual|xxx|suicide|kys|nigger|faggot|retard)\b/i;

export function createMind() {
  return {
    schema: MIND_SCHEMA,
    dim: DIM,
    steps: 0,
    tokenCount: 0,
    vocab: {},
    next: {},
    associations: emptyAssociations(),
    weights: Array.from({ length: DIM }, () => Array.from({ length: DIM }, () => 0)),
  };
}

export function isKidSafe(text) {
  return !BLOCKED.test(String(text || ""));
}

export function tokenize(text) {
  return String(text || "").slice(0,4096)
    .toLowerCase()
    .replace(/[^a-z0-9'\s]/g, " ")
    .split(/\s+/)
    .map((word) => word.replace(/^'+|'+$/g, ""))
    .filter(safeWord).slice(0,ASSOCIATION_LIMITS.tokens);
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

export function observeText(mind, text, options={}) {
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
  mind.steps=Math.min(1e6,mind.steps);mind.tokenCount=Math.min(1e6,mind.tokenCount);
  mind.vocab=trimMap(mind.vocab,ASSOCIATION_LIMITS.vocab,row=>row.count);
  mind.next=trimMap(Object.fromEntries(Object.entries(mind.next).filter(([w])=>Object.hasOwn(mind.vocab,w)).map(([w,bag])=>[w,trimMap(Object.fromEntries(Object.entries(bag).filter(([v])=>Object.hasOwn(mind.vocab,v))),12)])),ASSOCIATION_LIMITS.vocab,bag=>Object.values(bag).reduce((a,b)=>a+b,0));
  learnAssociations(mind,text,options);
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
  const recalled=recallAssociations(mind,text);
  if(recalled.length)return `${name} remembers links from "${recalled[0].cues.join(', ')}": ${recalled.map(h=>h.word).join(', ')}. Learned on this device; pattern memory, not a model answer.`;
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
    associations: mind.associations,
  };
}

export function importMind(raw) {
  const mind = createMind();
  if (!raw || raw.schema !== MIND_SCHEMA || raw.dim !== DIM) return mind;
  mind.steps = Math.floor(finite(raw.steps));
  mind.tokenCount = Math.floor(finite(raw.tokenCount));
  if(raw.vocab&&typeof raw.vocab==='object'&&!Array.isArray(raw.vocab))for(const [word,row] of Object.entries(raw.vocab).slice(0,4096))if(safeWord(word)&&finite(row?.count)>0)mind.vocab[word]={count:Math.floor(finite(row.count))};
  mind.vocab=trimMap(mind.vocab,ASSOCIATION_LIMITS.vocab,row=>row.count);
  if(raw.next&&typeof raw.next==='object'&&!Array.isArray(raw.next))for(const [word,bag] of Object.entries(raw.next).slice(0,4096))if(safeWord(word)&&Object.hasOwn(mind.vocab,word)&&bag&&typeof bag==='object'&&!Array.isArray(bag)){
   mind.next[word]=trimMap(Object.fromEntries(Object.entries(bag).slice(0,4096).filter(([w,n])=>safeWord(w)&&Object.hasOwn(mind.vocab,w)&&finite(n)>0).map(([w,n])=>[w,Math.floor(finite(n))])),12);
  }
  mind.associations=importAssociations(raw.associations);
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
