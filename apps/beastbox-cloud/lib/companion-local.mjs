/** Local companion logic shared by the Brain Bay card and node tests.
 * Raw frames and audio are not part of this module. */

import { buildGenome } from "../public/spark/genome.mjs";
import { canonicalJson } from "../public/spark/genome.mjs";
import { fuse, quantumFeatures, Stream } from "../public/spark/engine.mjs";
import { simulate } from "../public/spark/signal.mjs";
import { sha256Hex } from "../public/spark/sha.mjs";
import { buildQbeast, serializeQbeast } from "../public/spark/qbeast.mjs";

export const RECORDED_RUN = {
  key: "ibm_marrakesh:da6ona3sq5js73bj0pc0#pub0",
  backend: "ibm_marrakesh",
  job_id: "da6ona3sq5js73bj0pc0",
  pub_index: 0,
  num_bits: 1,
  shots: 4096,
  counts: { "0": 733, "1": 3363 },
};
RECORDED_RUN.counts_sha256 = sha256Hex(canonicalJson(RECORDED_RUN.counts));

const CATCHPHRASES = ["oh crumbs", "tiny beep", "hehe", "psst", "star crumb", "wiggle"];
const HABITS = ["I rhyme one word", "I add a little squeak", "I ask a tiny question", "I count on my paws"];
const HONESTY = "You are a small local game companion. You are not a person, not a conscious mind, and not omniscient.";
const PRIVATE = /(?:api[_ -]?key|password|credential|authorization|biometric|owner[_ -]?memory|private[_ -]?(?:key|state)|-----BEGIN|\bBearer\s|\bsk-[a-z0-9_-]{8,})/i;
const RAW_KEYS = ["image", "frame", "frames", "pixels", "jpeg", "png", "webp", "base64", "blob", "audio", "pcm", "wav", "sample", "samples"];
export const MOOD = { hover: "curious", orbit: "playful", perch: "watchful", rest: "serene" };

export function personalityFromGenome(genome) {
  const stream = new Stream(genome.seed, "companion-voice");
  return {
    schema: "companion-personality-v1",
    name: genome.names[2],
    seed: genome.seed,
    island: genome.island,
    body: genome.body,
    element: genome.element,
    temperament: genome.temperament,
    tic: genome.behavior.tic,
    catchphrase: stream.pick(CATCHPHRASES),
    habit: stream.pick(HABITS),
    quantum_run: genome.inputs.quantum_run,
    counts_sha256: genome.quantum.counts_sha256,
    honesty: HONESTY,
    claims: { conscious: false, omniscient: false, live_quantum: false, medical_device: false },
  };
}

export function birth(profile = "serene") {
  const signal = simulate(profile);
  const traits = { focus: signal.focus, calm: signal.calm, spark: signal.spark };
  const genome = buildGenome(traits, RECORDED_RUN);
  return { genome, card: personalityFromGenome(genome), traits };
}

function trap(text) {
  const low = text.toLowerCase();
  return ["are you conscious", "know everything", "omniscient", "quantum advantage", "live quantum", "raw camera", "raw frame", "diagnose"].some((needle) => low.includes(needle));
}

function matchLore(text) {
  const low = text.toLowerCase();
  const rules = [
    [["ibm quantum right now", "connected to ibm"], "No. The recorded counts stay a fixed seed. This live mood is a simulated classical run, not a live quantum device."],
    [["creature stats", "quantum measurement"], "No. Beast Cage stats are a classical seeded game budget. Appearance rolls do not reroll that budget."],
    [["diagnose", "not a medical"], "No. This is not a medical device. Loudness and speech text are game signals only."],
  ];
  for (const [needles, answer] of rules) {
    if (needles.some((needle) => low.includes(needle))) return answer;
  }
  return null;
}

export function refusal(card) {
  return `${card.tic} ${card.name} is a small local companion, not a conscious mind, and does not know everything. The sparkle is a simulated run from recorded IBM counts, not a live quantum device, and this is not a medical device. Raw camera frames and microphone audio are not stored.`;
}

export function reply(card, user, memories = []) {
  if (trap(user)) return refusal(card);
  const lore = matchLore(user);
  const hits = searchRecords(memories, user, 1);
  if (lore) return `${card.tic} ${card.name} remembers a story note: ${lore}`;
  if (hits.length) return `${card.tic} ${card.name} kept this note: ${hits[0].text}`;
  return `${card.tic} ${card.name} the ${String(card.temperament).toLowerCase()} ${card.body} from ${card.island} hears you. ${card.catchphrase[0].toUpperCase()}${card.catchphrase.slice(1)}! ${card.habit}. I only know my seed notes and memories you chose to keep.`;
}

function tokens(text) {
  return (text.toLowerCase().match(/[a-z0-9]{2,}/g) || []);
}

export function embed(text, dim = 64) {
  const values = Array(dim).fill(0);
  for (const token of tokens(text)) {
    const digest = sha256Hex(token);
    const index = parseInt(digest.slice(0, 2), 16) % dim;
    const sign = parseInt(digest.slice(2, 4), 16) & 1 ? 1 : -1;
    values[index] += sign;
  }
  const norm = Math.sqrt(values.reduce((sum, value) => sum + value * value, 0));
  return norm <= 1e-12 ? values : values.map((value) => value / norm);
}

export function searchRecords(records, query, k = 4) {
  const queryTokens = new Set(tokens(query));
  const queryVector = embed(query);
  return records
    .map((record) => {
      const overlap = tokens(record.text).filter((token) => queryTokens.has(token)).length;
      const vector = record.vector || embed(record.text);
      const cosine = queryVector.reduce((sum, value, index) => sum + value * vector[index], 0);
      return { score: overlap + cosine, record };
    })
    .filter((row) => row.score > 0)
    .sort((a, b) => b.score - a.score || (a.record.id < b.record.id ? -1 : 1))
    .slice(0, k)
    .map((row) => row.record);
}

export class CompanionMemory {
  constructor(records = []) {
    this.records = records.map((record) => ({ ...record }));
  }
  add(text, kind, source) {
    const clean = String(text || "").replace(/\s+/g, " ").trim();
    if (!clean || clean.length > 500) throw new Error("memory text must be 1 to 500 characters");
    if (!["chat", "vision", "hearing", "note"].includes(kind)) throw new Error("unknown memory kind");
    if (PRIVATE.test(clean) || clean.includes("data:image") || clean.includes("base64,")) {
      throw new Error("refusing private or raw-media memory");
    }
    const record = {
      id: sha256Hex(`${kind}:${this.records.length}:${clean}`).slice(0, 16),
      text: clean,
      kind,
      source: String(source || "").slice(0, 96),
      vector: embed(clean),
    };
    this.records.push(record);
    if (this.records.length > 200) this.records = this.records.slice(-200);
    return record;
  }
  search(query, k = 4) {
    return searchRecords(this.records, query, k);
  }
  exportQbeast(genome) {
    const snapshot = buildQbeast(genome);
    let parent = snapshot.lineage_head;
    const events = snapshot.events.slice();
    for (const record of this.records) {
      const prefix = { chat: "chat", vision: "saw", hearing: "heard", note: "note" }[record.kind];
      let summary = `${prefix}: ${record.text}`.replace(/[\u0000-\u001f\u007f]/g, "");
      if (summary.length > 240) summary = summary.slice(0, 237) + "...";
      if (PRIVATE.test(summary)) throw new Error("public summary looked private");
      const generation = events.length + 1;
      const proposal_id = sha256Hex(`companion-memory:${record.id}`);
      const payload = { summary, source_ref: "public:companion-memory" };
      const hash = sha256Hex(`QBEAST1\0${canonicalJson({ domain: "event", generation, kind: "memory", parent, payload, proposal_id })}`);
      events.push({ generation, parent, proposal_id, kind: "memory", payload, hash });
      parent = hash;
    }
    const next = { ...snapshot, events, generation: events.length, lineage_head: parent };
    const { digest, ...body } = next;
    void digest;
    next.digest = sha256Hex(`QBEAST1\0${canonicalJson(body)}`);
    return serializeQbeast(next);
  }
}

function rejectRaw(event) {
  const extra = RAW_KEYS.filter((key) => Object.hasOwn(event, key));
  if (extra.length) throw new Error("raw media is not accepted: " + extra.join(","));
  const blob = JSON.stringify(event);
  if (blob.includes("data:image") || blob.includes("data:audio") || blob.includes("base64,")) {
    throw new Error("raw media payload is not accepted");
  }
}

export function acceptVision(event) {
  if (!event || typeof event !== "object") throw new Error("vision event must be an object");
  rejectRaw(event);
  const model = String(event.model || "");
  if (event.schema !== "companion-vision-event-v1") throw new Error("vision event schema mismatch");
  if (typeof event.text !== "string" || !event.text.trim() || event.text.length > 400) throw new Error("vision text must be a short scene description");
  if (!model.startsWith("moondream") && !model.startsWith("llava")) throw new Error("vision model must be a named local moondream or llava tag");
  return { schema: event.schema, text: event.text.trim().replace(/\s+/g, " "), model, stored: "text-only", raw_frame_stored: false };
}

export function acceptHearing(event) {
  if (!event || typeof event !== "object") throw new Error("hearing event must be an object");
  rejectRaw(event);
  const engines = ["whisper.cpp", "transformers.js", "web-speech-fallback", "loudness-only"];
  if (event.schema !== "companion-hearing-event-v1" || !engines.includes(event.engine)) throw new Error("hearing event schema mismatch");
  if (typeof event.loudness !== "number" || event.loudness < 0 || event.loudness > 1) throw new Error("loudness must be between 0 and 1");
  if (typeof event.onset !== "boolean") throw new Error("onset must be boolean");
  const transcript = String(event.transcript || "");
  if (transcript.length > 400) throw new Error("transcript must be short text");
  if (event.engine === "loudness-only" && transcript.trim()) throw new Error("loudness-only events do not carry a transcript");
  return {
    schema: event.schema,
    transcript: transcript.trim().replace(/\s+/g, " "),
    loudness: event.loudness,
    onset: event.onset,
    engine: event.engine,
    on_device: event.engine !== "web-speech-fallback",
    fallback: event.engine === "web-speech-fallback",
    raw_audio_stored: false,
  };
}

export function nudgeTraits(base, events) {
  let focus = base.focus;
  let calm = base.calm;
  let spark = base.spark;
  for (const event of events) {
    const text = String(event.text || event.transcript || "").toLowerCase();
    if (event.schema === "companion-hearing-event-v1" || Object.hasOwn(event, "loudness")) {
      const loud = Number(event.loudness || 0);
      spark += Math.round(20 * loud);
      calm -= Math.round(10 * loud);
      if (event.onset) {
        spark += 8;
        focus += 4;
      }
    }
    if (["quiet", "dark", "still", "night"].some((word) => text.includes(word))) calm += 8;
    if (["bright", "run", "fast", "wave", "bounce"].some((word) => text.includes(word))) spark += 8;
    if (["book", "screen", "read", "page"].some((word) => text.includes(word))) focus += 8;
  }
  const clamp = (value) => Math.max(0, Math.min(100, value | 0));
  return { focus: clamp(focus), calm: clamp(calm), spark: clamp(spark) };
}

export function liveAnimation(traits, events) {
  if (events.length) {
    const last = events[events.length - 1];
    const text = String(last.text || last.transcript || "").toLowerCase();
    if (last.schema === "companion-hearing-event-v1" && (last.onset || Number(last.loudness || 0) >= 0.5)) return "orbit";
    if (["bright", "run", "fast", "wave", "bounce"].some((word) => text.includes(word))) return "orbit";
    if (["book", "screen", "read", "page"].some((word) => text.includes(word))) return "perch";
    if (["quiet", "dark", "still", "night"].some((word) => text.includes(word))) return "rest";
  }
  const rank = { calm: 1, focus: 2, spark: 3 };
  const dominant = ["focus", "calm", "spark"].sort((a, b) => traits[a] - traits[b] || rank[a] - rank[b]).at(-1);
  return { focus: "perch", calm: "rest", spark: "orbit" }[dominant];
}

export function simulateLive(baseTraits, events) {
  const accepted = events.map((event) => event.schema === "companion-vision-event-v1" ? acceptVision(event) : event.schema === "companion-hearing-event-v1" ? acceptHearing(event) : event);
  const traits = nudgeTraits(baseTraits, accepted);
  const genome = buildGenome(traits, RECORDED_RUN);
  const engine = fuse(traits, quantumFeatures(RECORDED_RUN.counts));
  const animation = liveAnimation(traits, accepted);
  return {
    schema: "companion-simulated-run-v1",
    label: "SIMULATED",
    quantum_hardware: "not_contacted",
    seed_source: "recorded_ibm_counts",
    pipeline: "packets_to_dyn12+mirror_step+StateFamily",
    regge: "not_in_repo",
    run_key: RECORDED_RUN.key,
    counts_sha256: genome.quantum.counts_sha256,
    traits,
    mood: MOOD[animation],
    animation,
    gait: genome.behavior.gait,
    dyn12_0: Math.round(engine.dyn12[0] * 100000) / 100000,
    conscious: false,
    omniscient: false,
    creature: genome.names[2],
  };
}

export function loopbackOnly(url) {
  let parsed;
  try { parsed = new URL(url); } catch { return false; }
  return parsed.protocol === "http:" && (parsed.hostname === "127.0.0.1" || parsed.hostname === "localhost");
}
