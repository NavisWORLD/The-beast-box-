// Original procedural music and sound effects for Beast Box.
//
// Everything is synthesized at runtime with plain WebAudio nodes (oscillators,
// filters, gains and seeded noise buffers). There are no samples, recordings or
// borrowed melodies. The theme, its chords and its motif are written for this
// game. A beast's recorded seed only nudges key, scale, tempo, timbre and small
// ornaments, so every beast sounds a little different while the base theme stays
// recognizable. Nothing here uses unseeded randomness: the same seed always
// gives the same music and the same effects.

const MASK = 4294967296;

function fnv(text) {
  let out = 2166136261;
  for (const byte of new TextEncoder().encode(String(text))) { out ^= byte; out = Math.imul(out, 16777619); }
  return out >>> 0;
}
/** Seeded unit float in [0,1). */
export function unitOf(seedKey, label) {
  let h = fnv(seedKey + "|" + label);
  h ^= h >>> 16; h = Math.imul(h, 0x85ebca6b) >>> 0;
  h ^= h >>> 13; h = Math.imul(h, 0xc2b2ae35) >>> 0;
  h ^= h >>> 16;
  return (h >>> 0) / MASK;
}
/** Small seeded PRNG for noise buffers. */
export function prng(seed) {
  let s = (seed >>> 0) || 1;
  return () => { s = (Math.imul(s, 1664525) + 1013904223) >>> 0; return s / MASK; };
}
const pick = (seedKey, label, list) => list[Math.floor(unitOf(seedKey, label) * list.length) % list.length];
export const midiToHz = (m) => 440 * Math.pow(2, (m - 69) / 12);

export const SCALES = {
  dorian: [0, 2, 3, 5, 7, 9, 10],
  aeolian: [0, 2, 3, 5, 7, 8, 10],
  lydian: [0, 2, 4, 6, 7, 9, 11],
  mixolydian: [0, 2, 4, 5, 7, 9, 10],
  major: [0, 2, 4, 5, 7, 9, 11],
};
const ELEMENT_SCALES = {
  ember: ["mixolydian", "aeolian", "dorian"], frost: ["lydian", "dorian", "aeolian"], radiant: ["lydian", "major", "mixolydian"],
  umbral: ["aeolian", "dorian", "aeolian"], machine: ["dorian", "mixolydian", "aeolian"], verdant: ["major", "mixolydian", "lydian"],
  grove: ["mixolydian", "major", "dorian"], crystal: ["lydian", "dorian", "major"],
};
const ELEMENT_WAVE = {
  ember: ["sawtooth", "square", "triangle"], frost: ["sine", "triangle", "sine"], radiant: ["square", "triangle", "sine"],
  umbral: ["sawtooth", "sine", "triangle"], machine: ["square", "square", "sawtooth"], verdant: ["triangle", "sine", "triangle"],
  grove: ["triangle", "sine", "square"], crystal: ["sine", "triangle", "sine"],
};

/** Per-element sound character shared by music timbre and SFX. */
export const ELEMENT_CHARACTER = {
  ember: { noise: "crackle", grit: 0.8, bright: 0.55, partials: [1, 2, 3], wave: "sawtooth" },
  frost: { noise: "glass", grit: 0.1, bright: 0.95, partials: [1, 2.76, 5.4, 8.93], wave: "sine" },
  radiant: { noise: "hiss", grit: 0.2, bright: 0.9, partials: [1, 2, 4], wave: "square" },
  umbral: { noise: "rumble", grit: 0.5, bright: 0.25, partials: [1, 1.5, 0.5], wave: "sawtooth" },
  machine: { noise: "bits", grit: 0.7, bright: 0.7, partials: [1, 3, 5], wave: "square" },
  verdant: { noise: "rustle", grit: 0.3, bright: 0.45, partials: [1, 2, 3.01], wave: "triangle" },
  grove: { noise: "rustle", grit: 0.35, bright: 0.4, partials: [1, 1.99, 3], wave: "triangle" },
  crystal: { noise: "glass", grit: 0.15, bright: 0.85, partials: [1, 2.4, 4.13, 6.7], wave: "sine" },
  spark: { noise: "hiss", grit: 0.3, bright: 0.65, partials: [1, 2, 3], wave: "triangle" },
};
export const characterFor = (element) => ELEMENT_CHARACTER[element] || ELEMENT_CHARACTER.spark;

/**
 * Music parameters for one beast. Input is the seed key (recorded quantum
 * seed + genome identity) and element/temperament.
 */
export function musicParams({ seedKey = "spark-fallback", element = "spark", temperament = "Curious" } = {}) {
  const key = String(seedKey);
  const scaleName = pick(key, "scale", ELEMENT_SCALES[element] || ["dorian", "aeolian", "lydian"]);
  const shift = Math.floor(unitOf(key, "key") * 9) - 4; // -4..+4 semitones around A
  const calmTemper = /Serene|Dreamy|Gentle|Steadfast/.test(temperament);
  const bpm = Math.round(74 + unitOf(key, "tempo") * 16 + (calmTemper ? -4 : 4));
  const ch = characterFor(element);
  return {
    seedKey: key,
    element,
    scaleName,
    scale: SCALES[scaleName],
    root: 57 + shift,
    bpm,
    battleBpm: bpm * 2,
    arpShape: Math.floor(unitOf(key, "arp") * 3),
    ornament: Math.floor(unitOf(key, "ornament") * 8),
    timbre: {
      lead: pick(key, "lead", ELEMENT_WAVE[element] || ["triangle", "sine", "square"]),
      pad: unitOf(key, "pad") < 0.5 ? "sawtooth" : "triangle",
      detuneCents: Math.round(4 + unitOf(key, "detune") * 10),
      cutoffHz: Math.round(900 + ch.bright * 1200 + unitOf(key, "cutoff") * 500),
      vibratoHz: Math.round((4 + unitOf(key, "vib") * 2) * 10) / 10,
      grit: ch.grit,
    },
  };
}

// The base theme (original): an 8-bar progression in scale degrees and a fixed motif.
export const PROGRESSION = [0, 5, 3, 4, 0, 5, 3, 6];
// Motif per bar: [eighth-step, scale-degree above the chord root's octave, length in eighths].
export const MOTIF = [
  [[0, 4, 2], [2, 2, 1], [3, 4, 1], [4, 7, 3], [7, 6, 1]],
  [[0, 5, 2], [2, 4, 2], [4, 2, 4]],
  [[0, 3, 2], [2, 5, 1], [3, 4, 1], [4, 3, 2], [6, 2, 2]],
  [[0, 4, 3], [3, 1, 1], [4, 2, 4]],
  [[0, 4, 2], [2, 2, 1], [3, 4, 1], [4, 7, 2], [6, 9, 2]],
  [[0, 8, 2], [2, 7, 2], [4, 5, 4]],
  [[0, 3, 2], [2, 4, 2], [4, 5, 2], [6, 6, 2]],
  [[0, 7, 6], [6, 4, 2]],
];
const ARP_SHAPES = [[0, 2, 4, 7], [0, 4, 2, 4], [0, 2, 4, 2]];

function degreeToMidi(params, degree, octave = 0) {
  const s = params.scale, n = s.length;
  const o = Math.floor(degree / n), d = ((degree % n) + n) % n;
  return params.root + s[d] + 12 * (o + octave);
}

/** All note events of one 8-bar loop (32 beats). Times and durations are in beats. */
export function themeEvents(params) {
  const events = [];
  PROGRESSION.forEach((chord, bar) => {
    const t0 = bar * 4;
    // Pad: the chord triad held for the bar.
    for (const step of [0, 2, 4]) events.push({ layer: "calm", part: "pad", t: t0, dur: 4, midi: degreeToMidi(params, chord + step, -1), vel: 0.16 });
    // Bass: chord root on beats 1 and 3.
    events.push({ layer: "calm", part: "bass", t: t0, dur: 1.8, midi: degreeToMidi(params, chord, -2), vel: 0.42 });
    events.push({ layer: "calm", part: "bass", t: t0 + 2, dur: 1.6, midi: degreeToMidi(params, chord + (bar % 2 ? 4 : 0), -2), vel: 0.34 });
    // Arp: soft 8ths in the beast's arp shape.
    const shape = ARP_SHAPES[params.arpShape];
    for (let i = 0; i < 8; i++) events.push({ layer: "calm", part: "arp", t: t0 + i * 0.5, dur: 0.45, midi: degreeToMidi(params, chord + shape[i % 4], 1), vel: 0.08 + (i % 2 ? 0 : 0.03) });
    // Lead: the motif (identical in degrees for every beast).
    for (const [step, deg, len] of MOTIF[bar]) events.push({ layer: "calm", part: "lead", t: t0 + step * 0.5, dur: len * 0.5 * 0.95, midi: degreeToMidi(params, chord + deg, 0), vel: 0.2, motif: true, degree: chord + deg });
    // Seeded ornament: one grace note in a bar chosen by the seed.
    if (bar === params.ornament) events.push({ layer: "calm", part: "lead", t: t0 + 3.75, dur: 0.22, midi: degreeToMidi(params, chord + 5, 0), vel: 0.12 });
    // Battle layer: driving drums, 8th-note bass ostinato and off-beat stabs.
    for (let b = 0; b < 4; b++) {
      events.push({ layer: "battle", part: "kick", t: t0 + b, dur: 0.4, midi: 36, vel: 0.9 });
      if (b % 2) events.push({ layer: "battle", part: "snare", t: t0 + b, dur: 0.25, midi: 38, vel: 0.55 });
      events.push({ layer: "battle", part: "hat", t: t0 + b, dur: 0.06, midi: 42, vel: 0.18 });
      events.push({ layer: "battle", part: "hat", t: t0 + b + 0.5, dur: 0.05, midi: 42, vel: 0.26 });
      events.push({ layer: "battle", part: "stab", t: t0 + b + 0.5, dur: 0.2, midi: degreeToMidi(params, chord + 4, 0), vel: 0.12 });
    }
    for (let i = 0; i < 8; i++) events.push({ layer: "battle", part: "bbass", t: t0 + i * 0.5, dur: 0.4, midi: degreeToMidi(params, chord + (i % 4 === 3 ? 4 : 0), -2), vel: 0.36 });
  });
  return events;
}
export const LOOP_BEATS = PROGRESSION.length * 4;

/** The lead motif as [beat, length, scale degree]: identical for every beast (the recognizable part). */
export function motifContour(params) {
  return themeEvents(params).filter((e) => e.motif).map((e) => [e.t, e.dur, e.degree]);
}

// ---------------------------------------------------------------- SFX specs

export const SFX_KINDS = ["charge", "beam", "slash", "burst", "quake", "hit", "crit", "faint", "flee", "levelup", "blip", "confirm"];

/** Deterministic parameters for one sound effect. */
export function sfxSpec(kind, element = "spark", seedKey = "spark-fallback") {
  const k = SFX_KINDS.includes(kind) ? kind : "blip";
  const ch = characterFor(element);
  const key = `${seedKey}:${element}:${k}`;
  const u = (label) => unitOf(key, label);
  const base = {
    charge: 180, beam: 520, slash: 900, burst: 300, quake: 55, hit: 140, crit: 220, faint: 440, flee: 520, levelup: 523.25, blip: 880, confirm: 660,
  }[k] * (0.85 + u("pitch") * 0.3);
  const dur = { charge: 0.75, beam: 0.6, slash: 0.28, burst: 0.55, quake: 0.9, hit: 0.22, crit: 0.45, faint: 1.1, flee: 0.5, levelup: 0.9, blip: 0.07, confirm: 0.18 }[k];
  const sweep = { charge: 3.2, beam: 0.6, slash: 0.35, burst: 0.4, quake: 0.5, hit: 0.45, crit: 0.4, faint: 0.35, flee: 2.4, levelup: 1, blip: 1, confirm: 1.5 }[k];
  const noise = { charge: 0.25, beam: 0.15, slash: 0.85, burst: 0.7, quake: 0.9, hit: 0.6, crit: 0.65, faint: 0.05, flee: 0.3, levelup: 0, blip: 0, confirm: 0 }[k];
  return {
    kind: k,
    element,
    seedKey: String(seedKey),
    wave: ch.wave,
    freq: Math.round(base * 100) / 100,
    sweep,
    dur: Math.round(dur * (0.9 + u("dur") * 0.2) * 1000) / 1000,
    noise: Math.min(1, noise + ch.grit * 0.15),
    noiseColor: ch.noise,
    partials: ch.partials,
    bright: ch.bright,
    gain: { blip: 0.35, confirm: 0.45, levelup: 0.55, faint: 0.5, flee: 0.5 }[k] ?? 0.8,
    notes: k === "levelup" ? [0, 4, 7, 12].map((n) => n + Math.floor(u("lvl") * 3)) : k === "confirm" ? [0, 7] : k === "faint" ? [0, -3, -7, -12] : [0],
    noiseSeed: fnv(key + ":noise"),
  };
}

// ---------------------------------------------------------------- WebAudio rendering

function envGain(ctx, dest, when, attack, hold, release, peak) {
  const g = ctx.createGain();
  g.gain.setValueAtTime(0.0001, when);
  g.gain.exponentialRampToValueAtTime(Math.max(0.0002, peak), when + Math.max(0.002, attack));
  g.gain.setValueAtTime(Math.max(0.0002, peak), when + attack + hold);
  g.gain.exponentialRampToValueAtTime(0.0001, when + attack + hold + Math.max(0.01, release));
  g.connect(dest);
  return g;
}

/** Seeded noise buffer, coloured per element (crackle, glass, hiss, rumble, bits, rustle). */
export function noiseBuffer(ctx, seconds, color, seed) {
  const len = Math.max(1, Math.floor(ctx.sampleRate * seconds));
  const buffer = ctx.createBuffer(1, len, ctx.sampleRate);
  const data = buffer.getChannelData(0);
  const rnd = prng(seed);
  let last = 0;
  for (let i = 0; i < len; i++) {
    const white = rnd() * 2 - 1;
    let v = white;
    if (color === "crackle") v = rnd() < 0.012 ? (rnd() * 2 - 1) * 1.6 : white * 0.18;
    else if (color === "rumble") { last = last * 0.97 + white * 0.03; v = last * 6; }
    else if (color === "bits") v = Math.round(white * 3) / 3;
    else if (color === "rustle") { last = last * 0.6 + white * 0.4; v = last * 1.4; }
    else if (color === "glass") v = white * 0.5;
    data[i] = Math.max(-1, Math.min(1, v));
  }
  return buffer;
}

/** Schedule one SFX on any BaseAudioContext (live or offline). Returns its length in seconds. */
export function renderSfx(ctx, dest, spec, when = ctx.currentTime) {
  const out = ctx.createGain();
  out.gain.value = spec.gain;
  out.connect(dest);
  const { dur, freq } = spec;
  // Tonal body: one oscillator per note (and per element partial for bell-like elements).
  spec.notes.forEach((semi, ni) => {
    const t = when + (spec.kind === "levelup" ? ni * 0.11 : spec.kind === "confirm" ? ni * 0.07 : spec.kind === "faint" ? ni * 0.22 : 0);
    const f0 = freq * Math.pow(2, semi / 12);
    const partials = spec.noiseColor === "glass" || spec.kind === "levelup" ? spec.partials : [1];
    partials.forEach((ratio, pi) => {
      const osc = ctx.createOscillator();
      osc.type = pi === 0 ? spec.wave : "sine";
      const f = f0 * ratio;
      osc.frequency.setValueAtTime(spec.kind === "charge" ? f * 0.5 : f, t);
      const end = spec.kind === "charge" ? f * spec.sweep : f * spec.sweep;
      osc.frequency.exponentialRampToValueAtTime(Math.max(20, end), t + dur * (spec.kind === "faint" ? 0.3 : 0.95));
      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.setValueAtTime(800 + spec.bright * 6000, t);
      filter.Q.value = spec.kind === "charge" ? 6 : 1;
      const peak = (pi === 0 ? 0.55 : 0.25 / pi) * (spec.kind === "quake" ? 1.2 : 1);
      const atk = spec.kind === "charge" ? dur * 0.8 : 0.004;
      const hold = spec.kind === "beam" ? dur * 0.5 : 0.01;
      const g = envGain(ctx, out, t, atk, hold, Math.max(0.03, dur - atk - hold), peak);
      osc.connect(filter); filter.connect(g);
      osc.start(t); osc.stop(t + dur + 0.05);
    });
  });
  // Noise transient, coloured by element.
  if (spec.noise > 0.01) {
    const src = ctx.createBufferSource();
    src.buffer = noiseBuffer(ctx, dur + 0.05, spec.noiseColor, spec.noiseSeed);
    const bp = ctx.createBiquadFilter();
    bp.type = spec.kind === "quake" ? "lowpass" : spec.noiseColor === "glass" ? "highpass" : "bandpass";
    bp.frequency.setValueAtTime(spec.kind === "quake" ? 220 : spec.kind === "slash" ? 3200 : 1400 + spec.bright * 3000, when);
    if (spec.kind === "slash") bp.frequency.exponentialRampToValueAtTime(900, when + dur);
    const g = envGain(ctx, out, when, spec.kind === "charge" ? dur * 0.7 : 0.002, 0.01, Math.max(0.03, dur * 0.8), spec.noise * 0.6);
    src.connect(bp); bp.connect(g);
    src.start(when); src.stop(when + dur + 0.05);
  }
  // Sub thump for impacts.
  if (["hit", "crit", "quake", "burst"].includes(spec.kind)) {
    const sub = ctx.createOscillator();
    sub.type = "sine";
    sub.frequency.setValueAtTime(spec.kind === "quake" ? 90 : 150, when);
    sub.frequency.exponentialRampToValueAtTime(38, when + Math.min(0.4, dur));
    const g = envGain(ctx, out, when, 0.003, 0.02, Math.min(0.45, dur), spec.kind === "crit" ? 0.9 : 0.7);
    sub.connect(g); sub.start(when); sub.stop(when + dur + 0.05);
  }
  return dur + 0.1;
}

/** Schedule one theme note on any BaseAudioContext. */
export function renderNote(ctx, dest, ev, params, when, secPerBeat) {
  const dur = Math.max(0.03, ev.dur * secPerBeat);
  const tb = params.timbre;
  if (ev.part === "kick") {
    const o = ctx.createOscillator(); o.type = "sine";
    o.frequency.setValueAtTime(140, when); o.frequency.exponentialRampToValueAtTime(42, when + 0.12);
    const g = envGain(ctx, dest, when, 0.002, 0.01, 0.22, ev.vel);
    o.connect(g); o.start(when); o.stop(when + 0.3); return;
  }
  if (ev.part === "snare" || ev.part === "hat") {
    const src = ctx.createBufferSource();
    src.buffer = noiseBuffer(ctx, dur + 0.02, ev.part === "hat" && params.element === "ember" ? "crackle" : "white", fnv(params.seedKey + ev.part));
    const f = ctx.createBiquadFilter(); f.type = ev.part === "hat" ? "highpass" : "bandpass"; f.frequency.value = ev.part === "hat" ? 7000 : 1800;
    const g = envGain(ctx, dest, when, 0.001, 0.005, dur, ev.vel);
    src.connect(f); f.connect(g); src.start(when); src.stop(when + dur + 0.02); return;
  }
  const hz = midiToHz(ev.midi);
  const wave = ev.part === "lead" ? tb.lead : ev.part === "pad" ? tb.pad : ev.part === "arp" ? "triangle" : ev.part === "stab" ? "square" : "sawtooth";
  const voices = ev.part === "pad" ? [-tb.detuneCents, tb.detuneCents] : [0];
  const filter = ctx.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.setValueAtTime(ev.part === "bass" || ev.part === "bbass" ? 420 : ev.part === "pad" ? tb.cutoffHz * 0.6 : tb.cutoffHz, when);
  const attack = ev.part === "pad" ? Math.min(1.2, dur * 0.4) : ev.part === "lead" ? 0.03 : 0.006;
  const g = envGain(ctx, dest, when, attack, Math.max(0, dur - attack - 0.12), ev.part === "pad" ? 0.9 : 0.18, ev.vel);
  filter.connect(g);
  for (const cents of voices) {
    const o = ctx.createOscillator();
    o.type = wave;
    o.frequency.setValueAtTime(hz, when);
    o.detune.setValueAtTime(cents, when);
    if (ev.part === "lead") {
      const lfo = ctx.createOscillator(); lfo.frequency.value = tb.vibratoHz;
      const depth = ctx.createGain(); depth.gain.value = 6;
      lfo.connect(depth); depth.connect(o.detune);
      lfo.start(when); lfo.stop(when + dur + 1);
    }
    o.connect(filter); o.start(when); o.stop(when + dur + 1);
  }
}

/** Mastering chain: compressor/limiter so punchy SFX never clip. */
export function buildMaster(ctx, dest = ctx.destination) {
  const comp = ctx.createDynamicsCompressor();
  comp.threshold.value = -14; comp.knee.value = 6; comp.ratio.value = 12; comp.attack.value = 0.003; comp.release.value = 0.22;
  const ceiling = ctx.createGain(); ceiling.gain.value = 0.85;
  comp.connect(ceiling); ceiling.connect(dest);
  const music = ctx.createGain(), calm = ctx.createGain(), battle = ctx.createGain(), sfx = ctx.createGain();
  calm.gain.value = 1; battle.gain.value = 0; music.gain.value = 0.5; sfx.gain.value = 0.9;
  calm.connect(music); battle.connect(music); music.connect(comp); sfx.connect(comp);
  return { comp, ceiling, music, calm, battle, sfx };
}

/** Render a whole loop into any context (used by the offline demo renderer). */
export function renderLoop(ctx, master, params, start, loops = 1, battleFrom = Infinity) {
  const spb = 60 / params.bpm;
  const events = themeEvents(params);
  for (let l = 0; l < loops; l++) {
    for (const ev of events) {
      const when = start + (l * LOOP_BEATS + ev.t) * spb;
      if (ev.layer === "battle" && when < battleFrom) continue;
      renderNote(ctx, ev.layer === "battle" ? master.battle : master.calm, ev, params, when, spb);
    }
  }
  return LOOP_BEATS * spb * loops;
}
