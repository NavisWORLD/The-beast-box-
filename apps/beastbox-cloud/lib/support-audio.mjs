/** Tiny support voices on the EXISTING Beast SFX bus. No context or autoplay here.
 * @param {ReturnType<import('./companion/beast-audio-engine.mjs').createBeastAudio>} audio
 * @param {{enabled?: () => boolean}} options
 */
export function createSupportAudio(audio, { enabled = () => true } = {}) {
  const voices = new Set();
  let epoch = 0;
  let disposed = false;
  const audible = () => {
    const state = audio.getSnapshot();
    return !disposed && enabled() && state.unlocked && !state.sparkMuted && !state.hidden;
  };
  const stop = () => {
    epoch++;
    for (const voice of voices) {
      try { voice.osc.stop(); } catch { /* already ended */ }
      voice.osc.disconnect();
      voice.gain.disconnect();
    }
    voices.clear();
  };
  return {
    async play(spec) {
      if (!audible()) return false;
      const request = ++epoch;
      try {
        const output = audio.output();
        if (!output) return false;
        const { ctx, dest } = output;
        if (ctx.state === 'suspended') await ctx.resume();
        if (ctx.state !== 'running' || request !== epoch || !audible()) return false;
        // One short reaction at a time. Repeated taps cannot accumulate voices.
        for (const voice of voices) {
          try { voice.osc.stop(); } catch { /* optional sound */ }
          voice.osc.disconnect(); voice.gain.disconnect();
        }
        voices.clear();
        const now = ctx.currentTime + 0.01;
        const duration = Math.max(0.05, Math.min(0.4, spec.duration));
        const spacing = Math.max(0.03, Math.min(0.1, spec.spacing));
        for (const [index, frequency] of spec.notes.slice(0, 4).entries()) {
          if (!Number.isFinite(frequency) || frequency <= 0) continue;
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          const voice = { osc, gain };
          voices.add(voice);
          const start = now + index * spacing, end = start + duration;
          osc.type = spec.wave === 'triangle' ? 'triangle' : 'sine';
          osc.frequency.setValueAtTime(frequency, start);
          osc.frequency.exponentialRampToValueAtTime(frequency * Math.max(0.5, Math.min(1.3, spec.bend)), end);
          gain.gain.setValueAtTime(0.0001, start);
          gain.gain.exponentialRampToValueAtTime(0.026, start + 0.015);
          gain.gain.exponentialRampToValueAtTime(0.0001, end);
          osc.connect(gain); gain.connect(dest);
          osc.onended = () => { voices.delete(voice); osc.disconnect(); gain.disconnect(); };
          osc.start(start); osc.stop(end + 0.015);
        }
        return true;
      } catch { stop(); return false; } // audio refusal never blocks checkout
    },
    stop,
    dispose() { stop(); disposed = true; }, // never close the shared game context
  };
}
