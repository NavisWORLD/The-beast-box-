/**
 * RAWRPHØS native dyn12, in the browser.
 *
 * This is the published 14K checkpoint's own architecture
 * (models/rawrphos/architecture/model.py): tied embeddings, RMSNorm,
 * rotary attention, gated 12D-state affinity, and the Dyn12 transition.
 * It is not a substitute model. Weights stay in the released
 * model.safetensors and are refused unless their SHA-256 matches.
 */

export const MODEL_ID = "rawrphos-native";
export const TRAINING_STEPS = 14000;
export const PARAMETER_COUNT = 3909956;
export const MODEL_SHA256 = "4e45850bfe7b3e2be1d5b12e1956286e1f3f8cfde7b01b70212ad75fbc8610a5";
export const TOKENIZER_SHA256 = "f704e9b75e816cc4ef203bc6c4afeeb966cbc11f369fb3b5f4d81c1505c8619c";
export const CONFIG_SHA256 = "2c235032f96a32d6e05b96ebec36ac879edd5dce80298df0682e777768b40650";
export const TOKENIZER_METADATA_SHA256 = "29c704d725bf6fe2e4c868e63dc29b1f299044542325a81f2bf08607b55889d2";
export const RELEASE_TAG = "rawrphos-native-conversation-step-00014000-run-35951509482";
export const ARCHIVE_SHA256 = "3875bc47e8b9d2024b4dae7889bf326f269c5a73955d2d3fc27936ba6794239c";

const D = 256;
const HEADS = 4;
const HD = 64;
const LAYERS = 6;
const VOCAB = 4096;
const STATE = 12;
const DT = 0.1;
const BOS = 1;
const EOS = 2;
const UNK = 3;
const SPECIAL = new Set([0, 1, 2, 3]);

const BYTE_TO_UNI = new Array(256);
const UNI_TO_BYTE = new Map();
(() => {
  const bs = [];
  for (let i = 33; i <= 126; i++) bs.push(i);
  for (let i = 161; i <= 172; i++) bs.push(i);
  for (let i = 174; i <= 255; i++) bs.push(i);
  const cs = bs.slice();
  let n = 0;
  const seen = new Set(bs);
  for (let b = 0; b < 256; b++) {
    if (!seen.has(b)) {
      bs.push(b);
      cs.push(256 + n);
      n += 1;
    }
  }
  for (let i = 0; i < bs.length; i++) {
    const ch = String.fromCharCode(cs[i]);
    BYTE_TO_UNI[bs[i]] = ch;
    UNI_TO_BYTE.set(ch, bs[i]);
  }
})();

const GPT2_RE = /'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+/gu;

function erf(x) {
  const sign = x < 0 ? -1 : 1;
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const p = 0.3275911;
  const ax = Math.abs(x);
  const t = 1 / (1 + p * ax);
  const y = 1 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-ax * ax);
  return sign * y;
}

export async function sha256Hex(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function assertSha(name, actual, expected) {
  if (actual !== expected) {
    throw new Error(`${name} SHA-256 mismatch: got ${actual}, expected ${expected}`);
  }
}

export function loadTokenizer(tokenizerJson) {
  const model = tokenizerJson.model;
  if (!model || model.type !== "BPE" || model.byte_fallback) {
    throw new Error("tokenizer is not the pinned byte-level BPE");
  }
  const vocab = new Map(Object.entries(model.vocab));
  if (vocab.size !== VOCAB) throw new Error("tokenizer vocab size is not 4096");
  for (const [token, id] of [["<|pad|>", 0], ["<|bos|>", 1], ["<|eos|>", 2], ["<|unk|>", 3]]) {
    if (vocab.get(token) !== id) throw new Error("special-token mismatch");
  }
  const idToToken = new Array(VOCAB);
  for (const [token, id] of vocab) idToToken[id] = token;
  const merges = new Map();
  model.merges.forEach((pair, rank) => {
    if (!Array.isArray(pair) || pair.length !== 2) throw new Error("invalid BPE merge");
    merges.set(pair[0] + "\u0000" + pair[1], rank);
  });

  function bpe(token) {
    const parts = [...token];
    if (parts.length < 2) return parts;
    while (parts.length > 1) {
      let bestRank = Infinity;
      let bestI = -1;
      for (let i = 0; i < parts.length - 1; i++) {
        const rank = merges.get(parts[i] + "\u0000" + parts[i + 1]);
        if (rank !== undefined && rank < bestRank) {
          bestRank = rank;
          bestI = i;
        }
      }
      if (bestI < 0) break;
      parts.splice(bestI, 2, parts[bestI] + parts[bestI + 1]);
    }
    return parts;
  }

  function encode(text, addBos = false) {
    if (typeof text !== "string") throw new Error("tokenizer input must be text");
    new TextEncoder().encode(text);
    const ids = addBos ? [BOS] : [];
    const parts = text.match(GPT2_RE) || [];
    for (const part of parts) {
      const bytes = new TextEncoder().encode(part);
      let chars = "";
      for (const b of bytes) chars += BYTE_TO_UNI[b];
      for (const piece of bpe(chars)) {
        const id = vocab.get(piece);
        ids.push(id === undefined ? UNK : id);
      }
    }
    return ids;
  }

  function decode(ids) {
    let text = "";
    for (const id of ids) {
      if (!Number.isInteger(id) || id < 0 || id >= VOCAB) throw new Error("invalid token id");
      if (SPECIAL.has(id)) continue;
      text += idToToken[id];
    }
    const bytes = new Uint8Array(text.length);
    for (let i = 0; i < text.length; i++) {
      const b = UNI_TO_BYTE.get(text[i]);
      if (b === undefined) throw new Error("byte-level decode missed a character");
      bytes[i] = b;
    }
    return new TextDecoder("utf-8", { fatal: false }).decode(bytes);
  }

  return { encode, decode, vocabSize: VOCAB, bosId: BOS, eosId: EOS };
}

function parseSafetensors(buffer) {
  const view = new DataView(buffer);
  if (buffer.byteLength < 8) throw new Error("safetensors too small");
  const headerLen = Number(view.getBigUint64(0, true));
  if (!Number.isSafeInteger(headerLen) || headerLen <= 0 || 8 + headerLen > buffer.byteLength) {
    throw new Error("unsafe safetensors header");
  }
  const header = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 8, headerLen)));
  const dataStart = 8 + headerLen;
  const tensors = {};
  for (const [name, meta] of Object.entries(header)) {
    if (name === "__metadata__") continue;
    if (!meta || meta.dtype !== "F32" || !Array.isArray(meta.shape) || !Array.isArray(meta.data_offsets)) {
      throw new Error("unexpected tensor " + name);
    }
    const [start, end] = meta.data_offsets;
    if (start % 4 || end % 4 || start < 0 || end < start || dataStart + end > buffer.byteLength) {
      throw new Error("bad tensor offsets " + name);
    }
    const count = (end - start) / 4;
    const expected = meta.shape.reduce((a, b) => a * b, 1) || 1;
    if (count !== expected) throw new Error("shape/byte mismatch " + name);
    const src = new Uint8Array(buffer, dataStart + start, end - start);
    const copy = new ArrayBuffer(end - start);
    new Uint8Array(copy).set(src);
    tensors[name] = { data: new Float32Array(copy), shape: meta.shape };
  }
  return tensors;
}

function need(tensors, name, shape) {
  const t = tensors[name];
  if (!t) throw new Error("missing tensor " + name);
  if (shape.length !== t.shape.length || shape.some((n, i) => n !== t.shape[i])) {
    throw new Error(`shape mismatch ${name}: ${t.shape}`);
  }
  return t.data;
}

export function loadWeights(buffer) {
  const tensors = parseSafetensors(buffer);
  const blocks = [];
  for (let i = 0; i < LAYERS; i++) {
    const p = `blocks.${i}.`;
    const block = {
      n1: need(tensors, p + "n1.weight", [D]),
      n2: need(tensors, p + "n2.weight", [D]),
      gate: need(tensors, p + "attn.gate_logit", [])[0],
      logSigma: need(tensors, p + "attn.log_sigma", [])[0],
      qkvW: need(tensors, p + "attn.qkv.weight", [3 * D, D]),
      qkvB: need(tensors, p + "attn.qkv.bias", [3 * D]),
      projW: need(tensors, p + "attn.proj.weight", [D, D]),
      projB: need(tensors, p + "attn.proj.bias", [D]),
      ffn0W: need(tensors, p + "ffn.0.weight", [414, D]),
      ffn0B: need(tensors, p + "ffn.0.bias", [414]),
      ffn2W: need(tensors, p + "ffn.2.weight", [D, 414]),
      ffn2B: need(tensors, p + "ffn.2.bias", [D]),
    };
    if (i < LAYERS - 1) {
      block.k = need(tensors, p + "transition.k", [STATE]);
      block.gamma = need(tensors, p + "transition.gamma", [STATE]);
    }
    blocks.push(block);
  }
  return {
    token: need(tensors, "token.weight", [VOCAB, D]),
    stateW: need(tensors, "state_init.weight", [STATE, D]),
    stateB: need(tensors, "state_init.bias", [STATE]),
    norm: need(tensors, "norm.weight", [D]),
    blocks,
  };
}

function gemm(outRows, outCols, x, xCols, w, bias) {
  const y = new Float64Array(outRows * outCols);
  for (let r = 0; r < outRows; r++) {
    const x0 = r * xCols;
    for (let c = 0; c < outCols; c++) {
      const w0 = c * xCols;
      let s = bias ? bias[c] : 0;
      for (let k = 0; k < xCols; k++) s += x[x0 + k] * w[w0 + k];
      y[r * outCols + c] = s;
    }
  }
  return y;
}

function rmsnorm(x, rows, weight) {
  const y = new Float64Array(rows * D);
  for (let r = 0; r < rows; r++) {
    let sq = 0;
    const o = r * D;
    for (let i = 0; i < D; i++) sq += x[o + i] * x[o + i];
    const scale = 1 / Math.sqrt(sq / D + 1e-6);
    for (let i = 0; i < D; i++) y[o + i] = x[o + i] * scale * weight[i];
  }
  return y;
}

function gelu(x) {
  const y = new Float64Array(x.length);
  const s = Math.SQRT1_2;
  for (let i = 0; i < x.length; i++) y[i] = 0.5 * x[i] * (1 + erf(x[i] * s));
  return y;
}

function rope(q, rows, positions) {
  const freq = new Float64Array(HD / 2);
  for (let i = 0; i < freq.length; i++) freq[i] = 10000 ** (-(2 * i) / HD);
  const y = new Float64Array(q.length);
  for (let r = 0; r < rows; r++) {
    for (let h = 0; h < HEADS; h++) {
      const base = (r * HEADS + h) * HD;
      for (let i = 0; i < HD / 2; i++) {
        const ang = positions[r] * freq[i];
        const cos = Math.cos(ang);
        const sin = Math.sin(ang);
        const a = q[base + 2 * i];
        const b = q[base + 2 * i + 1];
        y[base + 2 * i] = a * cos - b * sin;
        y[base + 2 * i + 1] = a * sin + b * cos;
      }
    }
  }
  return y;
}

function splitQkv(qkv, rows) {
  const q = new Float64Array(rows * HEADS * HD);
  const k = new Float64Array(rows * HEADS * HD);
  const v = new Float64Array(rows * HEADS * HD);
  for (let r = 0; r < rows; r++) {
    q.set(qkv.subarray(r * 3 * D, r * 3 * D + D), r * D);
    k.set(qkv.subarray(r * 3 * D + D, r * 3 * D + 2 * D), r * D);
    v.set(qkv.subarray(r * 3 * D + 2 * D, r * 3 * D + 3 * D), r * D);
  }
  return [q, k, v];
}

function concatSeq(a, aRows, b, bRows, width) {
  const y = new Float64Array((aRows + bRows) * width);
  y.set(a.subarray(0, aRows * width), 0);
  y.set(b.subarray(0, bRows * width), aRows * width);
  return y;
}

function softmaxRows(scores, rows, cols, allowed) {
  const y = new Float64Array(scores.length);
  for (let h = 0; h < HEADS; h++) {
    for (let r = 0; r < rows; r++) {
      let max = -Infinity;
      const base = (h * rows + r) * cols;
      for (let c = 0; c < cols; c++) {
        if (!allowed[r * cols + c]) continue;
        const v = scores[base + c];
        if (v > max) max = v;
      }
      let sum = 0;
      for (let c = 0; c < cols; c++) {
        if (!allowed[r * cols + c]) {
          y[base + c] = 0;
          continue;
        }
        const e = Math.exp(scores[base + c] - max);
        y[base + c] = e;
        sum += e;
      }
      for (let c = 0; c < cols; c++) if (allowed[r * cols + c]) y[base + c] /= sum;
    }
  }
  return y;
}

function forward(weights, ids, cache) {
  const rows = ids.length;
  if (!rows) throw new Error("empty token chunk");
  const start = cache ? cache.layers[0].rows : 0;
  if (start + rows > 2048) throw new Error("context limit exceeded");
  const x0 = new Float64Array(rows * D);
  for (let r = 0; r < rows; r++) {
    const id = ids[r];
    if (!Number.isInteger(id) || id < 0 || id >= VOCAB) throw new Error("token outside vocabulary");
    x0.set(weights.token.subarray(id * D, (id + 1) * D), r * D);
  }
  let x = x0;
  let state = gemm(rows, STATE, x, D, weights.stateW, weights.stateB);
  for (let i = 0; i < state.length; i++) state[i] = Math.tanh(state[i]);

  const layers = [];
  for (let li = 0; li < LAYERS; li++) {
    const block = weights.blocks[li];
    const h = rmsnorm(x, rows, block.n1);
    const qkv = gemm(rows, 3 * D, h, D, block.qkvW, block.qkvB);
    let [q, k, v] = splitQkv(qkv, rows);
    const positions = Array.from({ length: rows }, (_, i) => start + i);
    q = rope(q, rows, positions);
    k = rope(k, rows, positions);
    let stAll = state;
    if (cache) {
      const past = cache.layers[li];
      k = concatSeq(past.k, past.rows, k, rows, D);
      v = concatSeq(past.v, past.rows, v, rows, D);
      stAll = concatSeq(past.state, past.rows, state, rows, STATE);
    }
    const seq = (cache ? cache.layers[li].rows : 0) + rows;
    const allowed = new Uint8Array(rows * seq);
    for (let r = 0; r < rows; r++) {
      const limit = start + r;
      for (let c = 0; c <= limit; c++) allowed[r * seq + c] = 1;
    }
    const scores = new Float64Array(HEADS * rows * seq);
    const scale = 1 / Math.sqrt(HD);
    for (let head = 0; head < HEADS; head++) {
      for (let r = 0; r < rows; r++) {
        const qBase = (r * HEADS + head) * HD;
        const o = (head * rows + r) * seq;
        for (let c = 0; c < seq; c++) {
          if (!allowed[r * seq + c]) continue;
          const kBase = (c * HEADS + head) * HD;
          let s = 0;
          for (let i = 0; i < HD; i++) s += q[qBase + i] * k[kBase + i];
          scores[o + c] = s * scale;
        }
      }
    }
    const standard = softmaxRows(scores, rows, seq, allowed);
    const g = 1 / (1 + Math.exp(-block.gate));
    const sigma = Math.min(1e3, Math.max(1e-4, Math.exp(block.logSigma)));
    const affScores = new Float64Array(rows * seq);
    const inv = 1 / (2 * sigma * sigma);
    for (let r = 0; r < rows; r++) {
      let qsq = 0;
      const qs = r * STATE;
      for (let i = 0; i < STATE; i++) qsq += state[qs + i] * state[qs + i];
      for (let c = 0; c < seq; c++) {
        if (!allowed[r * seq + c]) continue;
        let ksq = 0;
        let dot = 0;
        const ks = c * STATE;
        for (let i = 0; i < STATE; i++) {
          ksq += stAll[ks + i] * stAll[ks + i];
          dot += state[qs + i] * stAll[ks + i];
        }
        affScores[r * seq + c] = -Math.max(qsq + ksq - 2 * dot, 0) * inv;
      }
    }
    const affinity = new Float64Array(rows * seq);
    for (let r = 0; r < rows; r++) {
      let max = -Infinity;
      for (let c = 0; c < seq; c++) if (allowed[r * seq + c] && affScores[r * seq + c] > max) max = affScores[r * seq + c];
      let sum = 0;
      for (let c = 0; c < seq; c++) {
        if (!allowed[r * seq + c]) continue;
        const e = Math.exp(affScores[r * seq + c] - max);
        affinity[r * seq + c] = e;
        sum += e;
      }
      for (let c = 0; c < seq; c++) if (allowed[r * seq + c]) affinity[r * seq + c] /= sum;
    }
    const mixed = new Float64Array(HEADS * rows * seq);
    for (let head = 0; head < HEADS; head++) {
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < seq; c++) {
          const i = (head * rows + r) * seq + c;
          mixed[i] = (1 - g) * standard[i] + g * affinity[r * seq + c];
        }
      }
    }
    const omega = new Float64Array(rows);
    for (let r = 0; r < rows; r++) {
      let count = 0;
      for (let c = 0; c < seq; c++) count += allowed[r * seq + c];
      let entropy = 0;
      for (let c = 0; c < seq; c++) {
        let mean = 0;
        for (let head = 0; head < HEADS; head++) mean += mixed[(head * rows + r) * seq + c];
        mean /= HEADS;
        if (mean > 0) entropy -= mean * Math.log(Math.max(mean, 1e-30));
      }
      omega[r] = count > 1 ? entropy / Math.max(Math.log(count), 1e-6) : 0;
    }
    const yHeads = new Float64Array(rows * D);
    for (let r = 0; r < rows; r++) {
      for (let head = 0; head < HEADS; head++) {
        const dest = (r * HEADS + head) * HD;
        for (let c = 0; c < seq; c++) {
          const w = mixed[(head * rows + r) * seq + c];
          if (!w) continue;
          const vBase = (c * HEADS + head) * HD;
          for (let i = 0; i < HD; i++) yHeads[dest + i] += w * v[vBase + i];
        }
      }
    }
    const proj = gemm(rows, D, yHeads, D, block.projW, block.projB);
    const x2 = new Float64Array(rows * D);
    for (let i = 0; i < x2.length; i++) x2[i] = x[i] + proj[i];
    x = x2;
    if (li < LAYERS - 1) {
      const next = new Float64Array(rows * STATE);
      for (let r = 0; r < rows; r++) {
        for (let i = 0; i < STATE; i++) {
          const s = state[r * STATE + i];
          next[r * STATE + i] = Math.tanh(s + DT * (block.k[i] * omega[r] - block.gamma[i] * s));
        }
      }
      state = next;
    }
    const n2 = rmsnorm(x, rows, block.n2);
    const hid = gelu(gemm(rows, 414, n2, D, block.ffn0W, block.ffn0B));
    const up = gemm(rows, D, hid, 414, block.ffn2W, block.ffn2B);
    const x3 = new Float64Array(rows * D);
    for (let i = 0; i < x3.length; i++) x3[i] = x[i] + up[i];
    x = x3;
    layers.push({ k, v, state: stAll, rows: seq });
  }
  const n = rmsnorm(x, rows, weights.norm);
  const logits = gemm(rows, VOCAB, n, D, weights.token, null);
  return { logits, cache: { layers } };
}

export function createGreedySession(weights, ids, eosId = EOS) {
  if (!Array.isArray(ids) || !ids.length) throw new Error("generation accepts one nonempty prompt");
  let cache = null;
  const context = ids.slice();
  const generated = [];
  return {
    get generated() { return generated.slice(); },
    step() {
      const chunk = cache ? [context[context.length - 1]] : context;
      const out = forward(weights, chunk, cache);
      cache = out.cache;
      const row = (chunk.length - 1) * VOCAB;
      let best = 0;
      let bestV = -Infinity;
      for (let i = 0; i < VOCAB; i++) {
        const v = out.logits[row + i];
        if (v > bestV) {
          bestV = v;
          best = i;
        }
      }
      generated.push(best);
      context.push(best);
      return { token: best, done: best === eosId };
    },
  };
}

export function greedyGenerate(weights, ids, maxNew, eosId = EOS, shouldStop = () => false) {
  if (!Number.isInteger(maxNew) || maxNew < 1 || maxNew > 64) throw new Error("invalid token budget");
  const session = createGreedySession(weights, ids, eosId);
  const generated = [];
  for (let step = 0; step < maxNew; step++) {
    if (shouldStop()) break;
    const item = session.step();
    generated.push(item.token);
    if (item.done) break;
  }
  return generated;
}

export async function loadPinnedRelease(weightsHref, options = {}) {
  const onProgress = options.onProgress || (() => {});
  const base = globalThis.document?.baseURI || import.meta.url;
  const root = new URL(weightsHref.endsWith("/") ? weightsHref : `${weightsHref}/`, base);
  async function fetchHashed(name, expected) {
    const response = await fetch(new URL(name, root));
    if (!response.ok) throw new Error("missing " + name);
    const total = Number(response.headers.get("content-length") || 0);
    const reader = response.body && response.body.getReader ? response.body.getReader() : null;
    let buffer;
    if (!reader) {
      buffer = await response.arrayBuffer();
      onProgress(name, buffer.byteLength, buffer.byteLength);
    } else {
      const chunks = [];
      let got = 0;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
        got += value.byteLength;
        onProgress(name, got, total);
      }
      const out = new Uint8Array(got);
      let offset = 0;
      for (const chunk of chunks) {
        out.set(chunk, offset);
        offset += chunk.byteLength;
      }
      buffer = out.buffer;
    }
    assertSha(name, await sha256Hex(buffer), expected);
    return buffer;
  }
  const [modelBuf, tokBuf, configBuf, metaBuf] = await Promise.all([
    fetchHashed("model.safetensors", MODEL_SHA256),
    fetchHashed("tokenizer.json", TOKENIZER_SHA256),
    fetchHashed("config.json", CONFIG_SHA256),
    fetchHashed("tokenizer-metadata.json", TOKENIZER_METADATA_SHA256),
  ]);
  const config = JSON.parse(new TextDecoder().decode(configBuf));
  if (config.attention_mode !== "dyn12" || config.d_model !== D || config.n_layers !== LAYERS || config.vocab_size !== VOCAB || config.state_dim !== STATE) {
    throw new Error("config is not the pinned dyn12 RAWRPHOS architecture");
  }
  const meta = JSON.parse(new TextDecoder().decode(metaBuf));
  if (meta.sha256 !== TOKENIZER_SHA256 || meta.vocab_size !== VOCAB || meta.schema !== "rawrphos-byte-bpe-v1") {
    throw new Error("tokenizer metadata does not match the pinned release");
  }
  return {
    weights: loadWeights(modelBuf),
    tokenizer: loadTokenizer(JSON.parse(new TextDecoder().decode(tokBuf))),
    config,
  };
}
