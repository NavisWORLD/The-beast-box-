import { blit, renderBeast, SPRITE } from "./draw.mjs";
import { buildGenome, bucketTraits } from "./genome.mjs";
import { bluetoothNote, connectMuse } from "./muse.mjs";
import { buildQbeast, serializeQbeast } from "./qbeast.mjs";
import { PROFILES, simulateStable } from "./signal.mjs";
import { Voice } from "./voice.mjs";

const LIVE = "https://navisworld.github.io/Cosmic-synapse-the-living-universe-sim-engine-/";
const STORE = "spark-beasts-bestiary-v1";
const SCALE = 4;

const $ = (id) => document.getElementById(id);
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

let runs = [];
let byKey = new Map();
let current = null;
let muse = null;
let voiceOn = false;
let audioCtx = null;
let audioOut = null;
let stage = 2;
let drift = false;
const target = { focus: 30, calm: 30, spark: 20 };
const felt = { focus: 30, calm: 30, spark: 20 };
let runtime = null;
let cache = {};
let bestiary = [];

function expand(row) {
  const counts = {};
  for (const part of row.c.split(",")) {
    const [k, v] = part.split(":");
    counts[k] = Number(v);
  }
  return {
    key: row.k, backend: row.b, job_id: row.j, pub_index: row.p, num_bits: row.n,
    shots: row.s, counts, counts_sha256: row.h,
  };
}

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function readTraits() {
  return {
    focus: Number($("focus").value),
    calm: Number($("calm").value),
    spark: Number($("spark").value),
  };
}

function showTraits(traits) {
  for (const key of ["focus", "calm", "spark"]) {
    $(key).value = traits[key];
    $(`v${key}`).textContent = String(traits[key]);
    target[key] = traits[key];
  }
  const b = bucketTraits(traits, 10);
  $("bucket").textContent = `Seed bucket 10: focus ${b.focus}, calm ${b.calm}, spark ${b.spark}`;
}

function selectedRun() {
  const key = $("run").value;
  return byKey.get(key) || runs[0];
}

function fillRunSelect(list) {
  const sel = $("run");
  const prev = sel.value;
  sel.replaceChildren();
  for (const run of list) {
    const opt = document.createElement("option");
    opt.value = run.key;
    opt.textContent = `${run.key} · ${run.num_bits}-bit · ${run.shots} shots`;
    sel.append(opt);
  }
  if (byKey.has(prev)) sel.value = prev;
}

function searchRuns() {
  const q = $("q").value.trim().toLowerCase();
  const list = q ? runs.filter((run) => run.key.toLowerCase().includes(q)).slice(0, 40) : runs.slice(0, 12);
  fillRunSelect(list.length ? list : runs.slice(0, 12));
}

function surpriseRun() {
  const traits = bucketTraits(readTraits(), 10);
  const n = Number.parseInt(buildGenome(traits, runs[0]).seed.slice(0, 8), 16);
  const run = runs[n % runs.length];
  fillRunSelect([run, ...runs.slice(0, 8).filter((item) => item.key !== run.key)]);
  $("run").value = run.key;
}

function paintStage(canvas, gen, which, eye = "open") {
  const ctx = canvas.getContext("2d");
  canvas.width = SPRITE * 2;
  canvas.height = SPRITE * 2;
  blit(ctx, renderBeast(gen, which, eye), 0, 0, 2);
}

function cacheEyes(gen) {
  cache = {};
  for (const which of [1, 2, 3]) {
    cache[which] = {};
    for (const eye of ["open", "sleepy", "closed", "sparkle"]) cache[which][eye] = renderBeast(gen, which, eye);
  }
}

function adopt(entry, announce = true) {
  const run = byKey.get(entry.run);
  if (!run) return;
  const gen = buildGenome(entry.traits, run, entry.user || null, 10);
  current = { entry, gen, run };
  stage = 2;
  cacheEyes(gen);
  showTraits(entry.traits);
  $("nameplate").textContent = `${gen.names[2]} · stage II`;
  $("meta").textContent = `${gen.temperament} ${gen.element} ${gen.body} from ${gen.island}. Pose ${gen.pose}, ${gen.ears} ears, ${gen.wings} wings, ${gen.tail} tail.`;
  $("quantum").textContent = `${run.backend} job ${run.job_id} pub ${run.pub_index}. ${run.num_bits}-bit recorded counts, SHA-256 ${run.counts_sha256.slice(0, 12)}…. Top outcome ${gen.quantum.top_state}.`;
  $("seed").textContent = gen.seed;
  for (const which of [1, 2, 3]) {
    paintStage($(`st${which}`), gen, which);
    $(`nm${which}`).textContent = gen.names[which];
  }
  resetRuntime();
  if (announce) say("neutral");
  drawBestiary();
}

function resetRuntime() {
  const be = current.gen.behavior;
  runtime = {
    rnd: mulberry32(be.prng_seed),
    phase: 0, aphase: 0, bphase: 0,
    nextBlink: 1, blinkUntil: -1,
    mood: "neutral", lastSay: -99, T: 0, utt: 0, talk: null,
  };
  felt.focus = target.focus; felt.calm = target.calm; felt.spark = target.spark;
}

function say(mood) {
  if (!current) return;
  const gen = current.gen;
  const lines = {
    calm: "The island is quiet.",
    focus: "Watching the signal.",
    spark: "Little lights!",
    neutral: `${gen.names[stage]} is here.`,
  };
  const drv = drive();
  const u = Voice.utterance(gen.voice, stage, mood, runtime.utt++, drv);
  $("bubble").hidden = false;
  $("bubble").textContent = u.text;
  const line = $("line");
  line.textContent = lines[mood] || lines.neutral;
  runtime.talk = { u, t0: runtime.T };
  runtime.bubbleUntil = runtime.T + Math.max(2.4, u.dur + 0.8);
  if (voiceOn && audioCtx && audioOut) Voice.schedule(audioCtx, audioOut, audioCtx.currentTime + 0.03, gen.voice, u);
}

function drive() {
  const be = current.gen.behavior;
  const out = {};
  for (const key of ["focus", "calm", "spark"]) {
    const feltV = felt[key];
    const thr = be.thresholds[key];
    out[key] = (0.3 * feltV / 100 + 0.7 * Math.max(0, Math.min(1, (feltV - thr) / (100 - thr)))) * be.sensitivity[key];
  }
  return out;
}

function tick(dt) {
  if (!current || !runtime) return;
  const be = current.gen.behavior;
  runtime.T += dt;
  if (drift && !reduceMotion) {
    for (const key of ["focus", "calm", "spark"]) {
      target[key] = Math.max(0, Math.min(100, target[key] + Math.sin(runtime.T * 0.3 + key.length) * 8 * dt));
    }
    showTraits({ focus: Math.round(target.focus), calm: Math.round(target.calm), spark: Math.round(target.spark) });
  }
  const kf = 1 - Math.exp(-dt / be.latency_s);
  for (const key of ["focus", "calm", "spark"]) felt[key] += (target[key] - felt[key]) * kf;
  const drv = drive();
  let mood = "neutral";
  let best = 0.25;
  for (const key of ["focus", "calm", "spark"]) if (drv[key] > best) { best = drv[key]; mood = key; }
  if (mood !== runtime.mood && runtime.T - runtime.lastSay > 2.2 && runtime.rnd() < 0.35 + 0.4 * be.chattiness) {
    runtime.mood = mood;
    say(mood);
  }
  runtime.mood = mood;
  const tempo = be.tempo_hz * (1 + 1.1 * Math.min(1, drv.spark) - 0.4 * Math.min(1, drv.calm));
  runtime.phase += (reduceMotion ? 0.15 : 2 * Math.PI * tempo) * dt;
  const amp = reduceMotion ? 0 : be.amplitude_px * (1 + Math.min(1, drv.spark));
  let dx = 0; let dy = 0;
  const ph = runtime.phase;
  if (be.gait === "hop") dy = -amp * 2 * Math.abs(Math.sin(ph / 2));
  else if (be.gait === "sway" || be.gait === "scuttle") dx = amp * Math.sin(ph);
  else if (be.gait === "float") dy = amp * Math.sin(ph * 0.5) - 2;
  else if (be.gait === "wobble" || be.gait === "pulse") dx = Math.sin(ph) * amp * 0.6;
  else dy = -amp * (0.5 - 0.5 * Math.cos(ph));
  let eye = "open";
  if (runtime.T > runtime.nextBlink) {
    runtime.blinkUntil = runtime.T + 0.12;
    runtime.nextBlink = runtime.T + be.blink_mean_s * (0.6 + runtime.rnd());
  }
  if (runtime.T < runtime.blinkUntil) eye = "closed";
  else if (drv.calm > 0.45) eye = "sleepy";
  else if (drv.spark > 0.55) eye = "sparkle";
  if (runtime.bubbleUntil && runtime.T > runtime.bubbleUntil) $("bubble").hidden = true;
  const view = $("view");
  const ctx = view.getContext("2d");
  const pix = cache[stage][eye] || cache[stage].open;
  blit(ctx, pix, 36 + dx * SCALE, 28 + dy * SCALE, SCALE);
  $("mood").textContent = `${runtime.mood} · ${be.gait} · hears ${be.reacts_most_to}`;
}

function spark(from = "sliders") {
  const traits = from === "profile" ? simulateStable($("profile").value) : bucketTraits(readTraits(), 10);
  const user = $("keeper").value.trim();
  if (user && !/^[A-Za-z0-9 ._-]{1,24}$/.test(user)) {
    $("status").textContent = "Keeper name must be a short public label, or leave it blank.";
    return;
  }
  const run = selectedRun();
  const entry = { traits: { focus: traits.focus, calm: traits.calm, spark: traits.spark }, run: run.key, user: user || null };
  bestiary = [entry, ...bestiary.filter((item) => item.run !== entry.run || item.user !== entry.user || item.traits.focus !== entry.traits.focus)].slice(0, 24);
  try { localStorage.setItem(STORE, JSON.stringify(bestiary)); } catch { /* storage may be blocked; the beast still exists in this tab */ }
  adopt(entry);
  $("status").textContent = "Sparked on this device. Nothing was uploaded.";
}

function drawBestiary() {
  const grid = $("bestiary");
  grid.replaceChildren();
  const cards = bestiary.length ? bestiary : starterEntries();
  for (const entry of cards) {
    const run = byKey.get(entry.run);
    if (!run) continue;
    const gen = buildGenome(entry.traits, run, entry.user || null, 10);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "beast-card";
    const canvas = document.createElement("canvas");
    paintStage(canvas, gen, 2);
    const label = document.createElement("span");
    label.textContent = `${gen.names[2]} · ${gen.island}`;
    btn.append(canvas, label);
    btn.addEventListener("click", () => adopt(entry));
    grid.append(btn);
  }
}

function starterEntries() {
  const profiles = ["serene", "focused", "sparky", "balanced", "dreamy", "steady", "restless", "mock"];
  const keys = [
    "ibm_marrakesh:d93d8pgoamcc73dc3afg",
    "ibm_kingston:d93jnlq47v0s73823aj0",
    "ibm_fez:da55afc3jnrc73agsvv0#pub1",
    "ibm_fez:da55afc3jnrc73agsvv0#pub2",
  ];
  const one = runs.find((run) => run.num_bits === 1);
  const twelve = runs.find((run) => run.num_bits === 12);
  const picked = [...keys, one && one.key, twelve && twelve.key].filter((key) => byKey.has(key));
  return profiles.map((profile, i) => ({
    traits: (({ focus, calm, spark }) => ({ focus, calm, spark }))(simulateStable(profile)),
    run: picked[i % picked.length],
    user: null,
  }));
}

function download() {
  if (!current) return;
  const text = serializeQbeast(buildQbeast(current.gen));
  const blob = new Blob([text], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${current.gen.names[2]}.qbeast`;
  a.click();
  URL.revokeObjectURL(a.href);
  $("status").textContent = "Downloaded a QBEAST1 file. The game rebuilds its companion from the seed. The memory note is the spark card.";
}

function enableVoice() {
  if (!audioCtx) {
    audioCtx = new AudioContext();
    audioOut = Voice.master(audioCtx);
  }
  void audioCtx.resume();
  voiceOn = !voiceOn;
  $("voice").textContent = voiceOn ? "Voice on" : "Voice off";
  $("voice").classList.toggle("on", voiceOn);
  if (voiceOn) say(runtime ? runtime.mood : "neutral");
}

async function museClick() {
  if (!$("consent").checked) {
    $("status").textContent = "Check the consent box before connecting a headband.";
    return;
  }
  try {
    if (muse) muse.stop();
    muse = await connectMuse((traits) => {
      showTraits(traits);
      $("status").textContent = "Muse traits updated on this device. Raw samples were discarded.";
    });
    $("status").textContent = `Connected to ${muse.name}. Reading derived traits from AF7 only.`;
  } catch (err) {
    $("status").textContent = err && err.message ? err.message : "Muse connection was cancelled.";
  }
}

function loop(prev) {
  const now = performance.now();
  const dt = Math.min(0.05, (now - prev) / 1000);
  tick(dt || 0.016);
  requestAnimationFrame(() => loop(now));
}

async function main() {
  const note = bluetoothNote();
  if (note) $("btnote").textContent = note;
  for (const key of Object.keys(PROFILES)) {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = key;
    $("profile").append(opt);
  }
  $("profile").value = "balanced";
  const table = await fetch("/spark/runs.json").then((res) => res.json());
  runs = table.runs.map(expand);
  byKey = new Map(runs.map((run) => [run.key, run]));
  $("totals").textContent = `${table.totals.entries} recorded distributions from ${table.totals.unique_jobs} IBM jobs.`;
  try { bestiary = JSON.parse(localStorage.getItem(STORE) || "[]"); } catch { bestiary = []; }
  if (!Array.isArray(bestiary)) bestiary = [];
  fillRunSelect(runs.filter((run) => run.num_bits >= 5).slice(0, 12));
  showTraits(simulateStable("balanced"));
  drawBestiary();
  adopt(starterEntries()[0], false);
  $("spark").addEventListener("click", () => spark("sliders"));
  $("use-profile").addEventListener("click", () => { showTraits(simulateStable($("profile").value)); spark("profile"); });
  $("surprise").addEventListener("click", surpriseRun);
  $("q").addEventListener("input", searchRuns);
  $("download").addEventListener("click", download);
  $("voice").addEventListener("click", enableVoice);
  $("drift").addEventListener("click", () => { drift = !drift; $("drift").classList.toggle("on", drift); });
  $("muse").addEventListener("click", () => { void museClick(); });
  $("stop-muse").addEventListener("click", () => { if (muse) muse.stop(); muse = null; $("status").textContent = "Muse disconnected. Samples cleared."; });
  for (const key of ["focus", "calm", "spark"]) $(key).addEventListener("input", () => showTraits(readTraits()));
  for (const which of [1, 2, 3]) {
    $(`pick${which}`).addEventListener("click", () => {
      stage = which;
      if (current) $("nameplate").textContent = `${current.gen.names[which]} · stage ${"I".repeat(which)}`;
    });
  }
  requestAnimationFrame((now) => loop(now));
}

main().catch((err) => {
  $("status").textContent = err && err.message ? err.message : "Spark Beasts could not start.";
});
