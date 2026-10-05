// Runtime engine for Beast Box music + SFX. Stateful, but every side effect
// goes through injected hooks so tests can drive it with a fake AudioContext.
//
// Gates (all must pass before anything is heard):
//  - unlocked: a real user gesture happened (browser autoplay rules);
//  - not sparkMuted: the site-wide Spark mute (beastbox:spark-mute);
//  - music: musicOn and the current scene's own Sound toggle (scene.enabled).
// While the GBA emulator is running, "Game audio" focus ducks the web music.
import { buildMaster, LOOP_BEATS, musicParams, renderNote, renderSfx, sfxSpec, themeEvents } from "./beast-audio.mjs";

export const MUSIC_STORAGE_KEY = "beastbox-music-v1";
const DUCK = 0.12;

export function createBeastAudio({ createContext = null, storage = null, setTimer = null, clearTimer = null } = {}) {
  let prefs = { musicOn: true, volume: 0.5, focus: "game" };
  try {
    const raw = storage && storage.getItem(MUSIC_STORAGE_KEY);
    if (raw) {
      const saved = JSON.parse(raw);
      prefs = {
        musicOn: saved.musicOn !== false,
        volume: Number.isFinite(saved.volume) ? Math.max(0, Math.min(1, saved.volume)) : 0.5,
        focus: saved.focus === "beast" ? "beast" : "game",
      };
    }
  } catch { /* storage unavailable: defaults */ }
  const state = { unlocked: false, sparkMuted: false, hidden: false, gameRunning: false, battle: 0, scene: null, ...prefs };
  let ctx = null, master = null, timer = null, loopStart = 0, nextIndex = 0, loopCount = 0, params = null, events = [];
  let battleUntil = 0;
  const listeners = new Set();
  const stats = { contexts: 0, notes: 0, sfx: 0 };

  const save = () => { try { storage && storage.setItem(MUSIC_STORAGE_KEY, JSON.stringify({ musicOn: state.musicOn, volume: state.volume, focus: state.focus })); } catch { /* optional */ } };
  const snapshot = () => ({ ...state, scene: state.scene ? { ...state.scene } : null, playing: Boolean(timer) });
  let cached = snapshot();
  const emit = () => { cached = snapshot(); for (const fn of listeners) fn(); };

  const musicAudible = () => state.unlocked && !state.sparkMuted && !state.hidden && state.musicOn && Boolean(state.scene && state.scene.enabled);
  const sfxAudible = () => state.unlocked && !state.sparkMuted;

  function ensureContext() {
    if (!sfxAudible() || !createContext) return null;
    if (!ctx) {
      try {
        ctx = createContext();
        if (!ctx) return null;
        stats.contexts++;
        master = buildMaster(ctx);
      } catch { ctx = null; master = null; return null; } // no audio device: stay silent
    }
    if (ctx.state === "suspended" && typeof ctx.resume === "function") { try { void ctx.resume(); } catch { /* resumes on next gesture */ } }
    return ctx;
  }
  function musicLevel() {
    return state.volume * (state.gameRunning && state.focus === "game" ? DUCK : 1);
  }
  function applyLevels(ramp = 0.4) {
    if (!ctx || !master) return;
    const t = ctx.currentTime;
    const target = musicAudible() ? musicLevel() : 0;
    master.music.gain.cancelScheduledValues(t);
    master.music.gain.setTargetAtTime(Math.max(0, target), t, ramp / 3);
    master.battle.gain.cancelScheduledValues(t);
    master.battle.gain.setTargetAtTime(state.battle, t, state.battle ? 0.15 : 0.6);
  }
  function tick(lookahead = 0.35) {
    if (!ctx || !master || !params || !musicAudible()) return;
    const spb = 60 / params.bpm;
    const horizon = ctx.currentTime + lookahead;
    if (state.battle && ctx.currentTime > battleUntil) { state.battle = 0; applyLevels(); emit(); }
    for (let guard = 0; guard < 400; guard++) {
      if (nextIndex >= events.length) { nextIndex = 0; loopCount++; }
      const ev = events[nextIndex];
      const when = loopStart + (loopCount * LOOP_BEATS + ev.t) * spb;
      if (when > horizon) break;
      if (when >= ctx.currentTime - 0.05) {
        try { renderNote(ctx, ev.layer === "battle" ? master.battle : master.calm, ev, params, when, spb); stats.notes++; } catch { /* skip one note */ }
      }
      nextIndex++;
    }
  }
  function startMusic() {
    if (!musicAudible() || timer) { applyLevels(); return; }
    if (!ensureContext()) return;
    params = musicParams(state.scene);
    events = themeEvents(params).slice().sort((a, b) => a.t - b.t);
    loopStart = ctx.currentTime + 0.08; nextIndex = 0; loopCount = 0;
    master.music.gain.setValueAtTime(0, ctx.currentTime);
    applyLevels(1.2);
    tick();
    timer = setTimer ? setTimer(() => tick(), 120) : null;
    if (!setTimer) timer = -1; // test mode: caller drives tick()
  }
  function stopMusic() {
    if (timer && timer !== -1 && clearTimer) clearTimer(timer);
    timer = null;
    applyLevels(0.25);
  }
  function refresh() {
    if (musicAudible()) {
      const same = params && state.scene && params.seedKey === String(state.scene.seedKey) && params.element === state.scene.element;
      if (timer && !same) stopMusic();
      startMusic();
    } else stopMusic();
    emit();
  }

  return {
    /** Called from a real user gesture. */
    unlock() { if (state.unlocked) { ensureContext(); return; } state.unlocked = true; ensureContext(); refresh(); },
    setScene(scene) {
      const next = scene ? { seedKey: String(scene.seedKey || "spark-fallback"), element: scene.element || "spark", temperament: scene.temperament || "Curious", enabled: scene.enabled !== false, id: scene.id || "scene" } : null;
      state.scene = next; refresh();
    },
    clearScene(id) { if (!state.scene || !id || state.scene.id === id) { state.scene = null; refresh(); } },
    setSceneEnabled(enabled) { if (state.scene) { state.scene.enabled = Boolean(enabled); refresh(); } },
    setMusic(on) { state.musicOn = Boolean(on); save(); refresh(); },
    setVolume(v) { state.volume = Math.max(0, Math.min(1, Number(v) || 0)); save(); applyLevels(0.15); emit(); },
    setFocus(focus) { state.focus = focus === "beast" ? "beast" : "game"; save(); applyLevels(); emit(); },
    setGameRunning(running) { state.gameRunning = Boolean(running); applyLevels(); emit(); },
    /** Page hidden (tab in background): stop the music loop; SFX stay gated by their callers. */
    setHidden(hidden) { state.hidden = Boolean(hidden); refresh(); },
    sparkMute() { state.sparkMuted = true; stopMusic(); emit(); },
    sparkUnmute() { state.sparkMuted = false; refresh(); },
    /** Fade the battle layer in for `seconds`. */
    battle(seconds = 3) {
      if (!musicAudible() || !ctx) return;
      state.battle = 1; battleUntil = ctx.currentTime + seconds; applyLevels(); emit();
    },
    /** Play one SFX. Returns false when gated (no gesture yet, or muted). */
    sfx(kind, { element = "spark", seedKey = "spark-fallback", delay = 0 } = {}) {
      if (!ensureContext()) return false;
      try { renderSfx(ctx, master.sfx, sfxSpec(kind, element, seedKey), ctx.currentTime + 0.01 + Math.max(0, delay)); } catch { return false; }
      stats.sfx++;
      return true;
    },
    /** Charge, strike, impact (+crit) for a seeded move, with the battle layer. */
    attack(move, { element = "spark", seedKey = "spark-fallback" } = {}) {
      if (!move || !ensureContext()) return false;
      const charge = (move.chargeMs || 600) / 1000;
      this.sfx("charge", { element, seedKey });
      this.sfx(move.style || "burst", { element, seedKey, delay: charge });
      this.sfx(move.crit ? "crit" : "hit", { element, seedKey, delay: charge + 0.12 });
      this.battle(charge + (move.strikeMs || 500) / 1000 + 2.5);
      return true;
    },
    /** The live context and SFX bus, or null when gated. */
    output() { return ensureContext() ? { ctx, dest: master.sfx } : null; },
    tick,
    subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    getSnapshot() { return cached; },
    stats() { return { ...stats, musicGain: master ? master.music.gain.value : 0 }; },
    dispose() { stopMusic(); try { ctx && ctx.close && ctx.close(); } catch { /* closed */ } ctx = null; master = null; },
  };
}

let shared = null;
/** Browser singleton, unlocked by the first pointer/key gesture and muted by beastbox:spark-mute. */
export function getBeastAudio() {
  if (shared) return shared;
  if (typeof window === "undefined") return createBeastAudio();
  const AC = window.AudioContext || window.webkitAudioContext;
  shared = createBeastAudio({
    createContext: AC ? () => new AC() : null,
    storage: (() => { try { return window.localStorage; } catch { return null; } })(),
    setTimer: (fn, ms) => window.setInterval(fn, ms),
    clearTimer: (id) => window.clearInterval(id),
  });
  const unlock = () => { try { shared.unlock(); } catch { /* audio is optional */ } };
  for (const type of ["pointerdown", "touchstart", "touchend", "click", "keydown"]) window.addEventListener(type, unlock, { capture: true, passive: true });
  window.addEventListener("beastbox:spark-mute", () => shared.sparkMute());
  window.addEventListener("beastbox:spark-unmute", () => shared.sparkUnmute());
  window.addEventListener("beastbox:gba-running", (event) => shared.setGameRunning(Boolean(event.detail)));
  document.addEventListener("visibilitychange", () => shared.setHidden(document.hidden));
  return shared;
}
