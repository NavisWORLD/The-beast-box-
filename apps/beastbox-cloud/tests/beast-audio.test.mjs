import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { buildGenome } from "../lib/companion/spark/genome.mjs";
import { buildMoveset } from "../lib/companion/beast-moves.mjs";
import { buildMaster, motifContour, musicParams, renderLoop, renderSfx, SFX_KINDS, sfxSpec, themeEvents } from "../lib/companion/beast-audio.mjs";
import { createBeastAudio, MUSIC_STORAGE_KEY } from "../lib/companion/beast-audio-engine.mjs";

const read = (path) => readFileSync(new URL("../" + path, import.meta.url), "utf8");
const runs = JSON.parse(read("lib/companion/spark/runs.json"));
const sceneFor = (index) => {
  const moves = buildMoveset(buildGenome({ focus: 40, calm: 40, spark: 20 }, runs[index % runs.length], null));
  return { seedKey: moves.key, element: moves.element, temperament: moves.temperament };
};

// ---- a recording fake of the WebAudio surface the synth uses
function fakeParam(value = 0) {
  const p = { value, events: [] };
  for (const name of ["setValueAtTime", "exponentialRampToValueAtTime", "linearRampToValueAtTime", "setTargetAtTime", "cancelScheduledValues"]) {
    p[name] = (...args) => { p.events.push([name, ...args]); if (name === "setValueAtTime" || name === "setTargetAtTime") p.value = args[0]; return p; };
  }
  return p;
}
function fakeContext(log) {
  const node = (kind, extra = {}) => { const n = { kind, connect: (to) => { (n.out ||= []).push(to); return to; }, disconnect() {}, ...extra }; log.push(n); return n; };
  const ctx = {
    currentTime: 0, sampleRate: 8000, state: "running", destination: { kind: "destination" },
    createGain: () => node("gain", { gain: fakeParam(1) }),
    createOscillator: () => node("osc", { type: "sine", frequency: fakeParam(440), detune: fakeParam(0), start() {}, stop() {} }),
    createBiquadFilter: () => node("filter", { type: "lowpass", frequency: fakeParam(350), Q: fakeParam(1) }),
    createBufferSource: () => node("source", { buffer: null, start() {}, stop() {} }),
    createBuffer: (ch, len, rate) => ({ length: len, sampleRate: rate, data: new Float32Array(len), getChannelData() { return this.data; } }),
    createDynamicsCompressor: () => node("compressor", { threshold: fakeParam(-24), knee: fakeParam(30), ratio: fakeParam(12), attack: fakeParam(0.003), release: fakeParam(0.25) }),
    resume: async () => {}, close: async () => {},
  };
  return ctx;
}
function engine(storage = null) {
  const log = [];
  let made = 0;
  const audio = createBeastAudio({ createContext: () => { made++; return fakeContext(log); }, storage });
  return { audio, log, made: () => made };
}
const memoryStorage = () => { const m = new Map(); return { getItem: (k) => m.get(k) ?? null, setItem: (k, v) => m.set(k, String(v)) }; };

test("the same beast seed gives the same music parameters and theme", () => {
  const scene = sceneFor(0);
  assert.deepEqual(musicParams(scene), musicParams(scene));
  assert.deepEqual(themeEvents(musicParams(scene)), themeEvents(musicParams(scene)));
});

test("different beasts get a different key, scale, tempo or timbre", () => {
  const seen = new Set();
  for (let i = 0; i < 6; i++) {
    const p = musicParams(sceneFor(i));
    seen.add(JSON.stringify([p.root, p.scaleName, p.bpm, p.timbre]));
    assert.ok(p.bpm >= 60 && p.bpm <= 100, `calm tempo stays chill (${p.bpm})`);
    assert.ok(p.battleBpm > p.bpm, "battle layer is more intense");
  }
  assert.ok(seen.size >= 5, `expected distinct music params, got ${seen.size}`);
  const a = musicParams({ seedKey: "alpha", element: "ember" });
  const b = musicParams({ seedKey: "beta", element: "frost" });
  assert.notDeepEqual([a.root, a.bpm, a.timbre], [b.root, b.bpm, b.timbre]);
});

test("the base theme stays recognizable: the motif contour is identical across seeds", () => {
  const ref = motifContour(musicParams({ seedKey: "alpha", element: "ember" }));
  assert.ok(ref.length >= 8);
  for (let i = 0; i < 6; i++) assert.deepEqual(motifContour(musicParams(sceneFor(i))), ref);
});

test("the theme has a calm layer and a battle layer", () => {
  const events = themeEvents(musicParams(sceneFor(1)));
  const parts = new Set(events.map((e) => e.part));
  for (const part of ["pad", "bass", "arp", "lead", "kick", "snare", "hat"]) assert.ok(parts.has(part), part);
  assert.ok(events.some((e) => e.layer === "battle") && events.some((e) => e.layer === "calm"));
});

test("every move style and game event has a deterministic, element-tied SFX", () => {
  for (const kind of ["charge", "beam", "slash", "burst", "quake", "hit", "crit", "faint", "flee", "levelup", "blip", "confirm"]) assert.ok(SFX_KINDS.includes(kind), kind);
  for (const kind of SFX_KINDS) {
    assert.deepEqual(sfxSpec(kind, "ember", "seed-a"), sfxSpec(kind, "ember", "seed-a"));
    assert.notDeepEqual(sfxSpec(kind, "ember", "seed-a"), sfxSpec(kind, "ember", "seed-b"));
  }
  assert.equal(sfxSpec("burst", "ember", "s").noiseColor, "crackle");
  assert.equal(sfxSpec("beam", "frost", "s").noiseColor, "glass");
  assert.notEqual(sfxSpec("slash", "ember", "s").wave, sfxSpec("slash", "frost", "s").wave);
});

test("SFX and music go through a compressor/limiter before the speakers", () => {
  const log = [];
  const ctx = fakeContext(log);
  const master = buildMaster(ctx);
  assert.equal(master.comp.kind, "compressor");
  assert.ok(master.comp.threshold.value < 0 && master.comp.ratio.value >= 8);
  assert.ok(master.ceiling.gain.value < 1);
  assert.ok(master.comp.out.includes(master.ceiling) && master.ceiling.out.includes(ctx.destination));
  for (const kind of SFX_KINDS) renderSfx(ctx, master.sfx, sfxSpec(kind, "spark", "k"), 0);
  renderLoop(ctx, master, musicParams(sceneFor(0)), 0, 1, 16);
  // nothing but the ceiling reaches the destination directly
  assert.deepEqual(log.filter((n) => (n.out || []).includes(ctx.destination)).map((n) => n), [master.ceiling]);
});

test("nothing is created or heard before the first user gesture", () => {
  const { audio, log, made } = engine();
  audio.setScene({ id: "habitat", ...sceneFor(0), enabled: true });
  assert.equal(audio.sfx("hit"), false);
  assert.equal(audio.attack({ style: "beam", chargeMs: 500, strikeMs: 400 }), false);
  assert.equal(audio.output(), null);
  audio.tick();
  assert.equal(made(), 0);
  assert.equal(log.length, 0);
  assert.equal(audio.getSnapshot().playing, false);
  audio.unlock();
  assert.equal(made(), 1);
  assert.equal(audio.getSnapshot().playing, true);
  assert.ok(audio.stats().notes > 0, "theme notes scheduled after the gesture");
  assert.equal(audio.sfx("hit"), true);
});

test("the site-wide Spark mute silences music and SFX until unmuted", () => {
  const { audio } = engine();
  audio.unlock();
  audio.setScene({ id: "habitat", ...sceneFor(0), enabled: true });
  audio.sparkMute();
  assert.equal(audio.sfx("confirm"), false);
  assert.equal(audio.output(), null);
  assert.equal(audio.getSnapshot().playing, false);
  const before = audio.stats().notes;
  audio.tick();
  assert.equal(audio.stats().notes, before);
  audio.setMusic(true); // the Music switch alone does not override the Spark mute
  assert.equal(audio.getSnapshot().playing, false);
  audio.sparkUnmute();
  assert.equal(audio.getSnapshot().playing, true);
  assert.equal(audio.sfx("confirm"), true);
});

test("the per-cage Sound toggle and the Music switch both stop the theme", () => {
  const storage = memoryStorage();
  const { audio } = engine(storage);
  audio.unlock();
  audio.setScene({ id: "habitat", ...sceneFor(2), enabled: false });
  assert.equal(audio.getSnapshot().playing, false);
  assert.equal(audio.stats().notes, 0);
  audio.setSceneEnabled(true);
  assert.equal(audio.getSnapshot().playing, true);
  audio.setMusic(false);
  assert.equal(audio.getSnapshot().playing, false);
  assert.equal(JSON.parse(storage.getItem(MUSIC_STORAGE_KEY)).musicOn, false);
  // Music off still lets SFX through (they follow the Sound toggle in the components).
  assert.equal(audio.sfx("blip"), true);
  const again = engine(storage).audio;
  assert.equal(again.getSnapshot().musicOn, false, "music preference persists");
});

test("the web music ducks while the GBA game runs in Game audio focus", () => {
  const { audio } = engine();
  audio.unlock();
  audio.setVolume(0.6);
  audio.setScene({ id: "field", ...sceneFor(3), enabled: true });
  const full = audio.stats().musicGain;
  audio.setGameRunning(true);
  const ducked = audio.stats().musicGain;
  assert.ok(ducked < full * 0.3, `ducked ${ducked} vs ${full}`);
  audio.setFocus("beast");
  assert.ok(audio.stats().musicGain > ducked);
  audio.setFocus("game");
  audio.setGameRunning(false);
  assert.equal(audio.stats().musicGain, full);
});

test("attacks bring in the battle layer", () => {
  const { audio } = engine();
  audio.unlock();
  audio.setScene({ id: "habitat", ...sceneFor(4), enabled: true });
  assert.equal(audio.getSnapshot().battle, 0);
  assert.equal(audio.attack({ style: "quake", chargeMs: 600, strikeMs: 500, crit: true }, { element: "ember", seedKey: "x" }), true);
  assert.equal(audio.getSnapshot().battle, 1);
  assert.equal(audio.stats().sfx, 3);
});

test("audio sources stay procedural and the Music control is in the sound UI", () => {
  for (const file of ["lib/companion/beast-audio.mjs", "lib/companion/beast-audio-engine.mjs"]) {
    const src = read(file);
    assert.doesNotMatch(src, /Math\.random/);
    assert.doesNotMatch(src, /getUserMedia|decodeAudioData|"[^"]*\.(mp3|wav|ogg)"|fetch\(/);
  }
  const arena = read("components/spark-beast-arena.tsx");
  assert.match(arena, /Music on/);
  assert.match(arena, /aria-label="Beast music volume"/);
  assert.match(arena, /music\.attack\(/);
  const go = read("components/beast-go.tsx");
  assert.match(go, /Audio focus: /);
  assert.match(go, /Game audio/);
  assert.match(go, /aria-label="Beast music volume"/);
  assert.match(read("components/lost-cosmos-dock.tsx"), /beastbox:gba-running/);
  assert.match(read("components/companion-provider.tsx"), /beastbox:spark-unmute/);
});


test("browser audio unlock surface includes iPhone touch and click gestures", () => {
  const engine = read("lib/companion/beast-audio-engine.mjs");
  assert.match(engine, /"touchstart"/);
  assert.match(engine, /"touchend"/);
  assert.match(engine, /"click"/);
});

test("site mute persists and volume reaches the shared SFX bus",()=>{
 const storage=memoryStorage(),{audio,log}=engine(storage);
 audio.unlock();audio.setScene({id:"site",...sceneFor(1),enabled:true});
 audio.setVolume(0.3);
 const output=audio.output();
 assert.ok(output && output.dest.gain.events.some(e=>e[0]==="setTargetAtTime"&&Math.abs(e[1]-0.27)<1e-9));
 audio.sparkMute();
 assert.equal(storage.getItem("beastbox-site-sound-v1"),"off");
 assert.equal(audio.sfx("blip"),false);
 audio.sparkUnmute();
 assert.equal(storage.getItem("beastbox-site-sound-v1"),"on");
 audio.setHidden(true);
 assert.equal(audio.output(),null,"hidden app should not provide audio");
 assert.equal(audio.sfx("blip"),false,"hidden app must not chirp");
 audio.setHidden(false);
 assert.equal(audio.sfx("blip"),true);
});
test("cross-page sound dock and one-context creature voice",()=>{
 const dock=read("components/site-sound-dock.tsx"),css=read("components/site-sound-dock.module.css");
 const sprite=read("components/spark-beast-companion.tsx");
 assert.match(read("app/layout.tsx"),/<SiteSoundDock\/>/);
 assert.match(dock,/Beast Box music, creature and effect volume/);
 assert.match(dock,/spark-mute/);
 assert.match(css,/safe-area-inset-bottom/);
 assert.match(sprite,/getBeastAudio\(\)/);
 assert.doesNotMatch(sprite,/new AC\(\)/);
 assert.match(read("public/spark/app.mjs"),/beastbox-site-sound-v1/);
});

test("Safari UI can distinguish configured audio from the actual context readiness", () => {
  const {audio} = engine();
  const before = audio.getSnapshot();
  assert.equal(before.contextState,"locked");
  assert.equal(before.unlocked,false);
  audio.unlock();
  assert.equal(audio.getSnapshot().contextState,"running");
  assert.equal(audio.getSnapshot().unlocked,true);
  audio.sparkMute();
  assert.equal(audio.getSnapshot().sparkMuted,true);
});
