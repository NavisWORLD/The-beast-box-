/* Lost Cosmos seeded creature voice — WebAudio, no network, deterministic per seed.
 * Voice params come from the genome (beastgen/voice.py). An utterance is derived from
 * (voice.prng_seed, utterance index, felt signal drive), so the same beast + same moment =
 * same babble. The same code renders live (AudioContext) and offline (OfflineAudioContext)
 * for the demo-video soundtrack and the WAV samples. */
"use strict";
const Voice = (() => {
  function mul(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296}}
  const STAGE_PITCH = {1:1.28, 2:1.0, 3:0.8}, STAGE_RATE = {1:1.12, 2:1.0, 3:0.9};
  const VL = {a:"a", e:"e", i:"i", o:"o", u:"u", ee:"ee", aw:"aw", "ü":"u"};
  const GLIDE = {chirp:6, coo:-2.5, growl:-3, trill:0, beep:0, purr:-1};   // semitones within a syllable
  const END = {spark:"!", calm:"~", focus:".", neutral:"?"};
  // drive: {focus,calm,spark} in ~0..1.5 (the beast's own felt drive, from its genome sensitivity)
  function utterance(v, stage, mood, idx, drive){
    const r = mul((v.prng_seed ^ Math.imul(idx + 1, 0x9E3779B1)) >>> 0);
    // the current mood sets a floor for its channel, so a calm line is clearly calm even right after the mood flips
    const fl = ch => (mood === ch ? 0.65 : 0);
    const dc = Math.min(1.2, Math.max(fl("calm"), drive.calm||0)), ds = Math.min(1.2, Math.max(fl("spark"), drive.spark||0)),
          df = Math.min(1.2, Math.max(fl("focus"), drive.focus||0));
    const rate = v.speed_sps * STAGE_RATE[stage] * (1 + 0.38*ds - 0.32*dc + 0.08*df);
    const pitch = v.base_pitch_hz * STAGE_PITCH[stage] * (1 + 0.24*ds - 0.10*dc);
    const gain = v.gain * (1 - 0.45*dc + 0.1*ds);
    const jump = v.jump_semitones * (1 + 0.8*ds - 0.45*dc - 0.3*df);
    const [lo, hi] = v.phrase_syllables;
    const n = lo + Math.floor(r()*(hi - lo + 1)) + (ds > 0.6 ? 1 : 0) - (dc > 0.7 && lo > 2 ? 1 : 0);
    const contour = ds > 0.6 ? "bounce" : v.contour;
    const syl = []; let t = 0; const words = [];
    for (let i = 0; i < n; i++){
      const long = v.rhythm[(idx + i) % v.rhythm.length] === 1;
      const dur = (long ? 1.65 : 1.0) / rate * (0.9 + 0.2*r());
      const u = n > 1 ? i/(n-1) : 0;
      let semi = contour === "rise" ? jump*u : contour === "fall" ? jump*(1-u) : contour === "arch" ? jump*Math.sin(Math.PI*u) : (i % 2) * jump;
      semi += (r() - 0.5) * (1.5 + 3*ds);
      if (v.style === "beep") semi = Math.round(semi / 2) * 2;
      const f0 = pitch * Math.pow(2, semi/12);
      const f1 = f0 * Math.pow(2, (GLIDE[v.style] * (ds > 0.5 ? 1.4 : 1) * (i === n-1 && mood === "spark" ? 1.6 : 1)) / 12);
      const vi = (idx + i) % v.vowel_formants.length;
      const vf = v.vowel_formants[vi];
      // mix the beast's own formants (timbre) with the vowel's (colour)
      const F = [0.5*v.formants_hz[0] + 0.5*vf[0], 0.5*v.formants_hz[1] + 0.5*vf[1]];
      const amp = gain * (long ? 1 : 0.85) * (0.9 + 0.2*r());
      syl.push({t, dur, f0, f1, F, amp});
      const cons = v.consonants[(idx + i*3) % v.consonants.length];
      let vw = VL[v.vowels[vi]] || "a"; if (long) vw = vw + vw.slice(-1);
      words.push(cons + vw);
      t += dur + (0.22 + 0.25*dc - 0.08*ds) / rate * (0.7 + 0.6*r());
    }
    let text = words.join(r() < 0.5 ? "-" : " ");
    text = text[0].toUpperCase() + text.slice(1) + (END[mood] || "!");
    if (mood === "spark" && r() < 0.6) text += "!";
    return {syl, text, dur: t, style: v.style};
  }
  let NOISE = new WeakMap();
  function noiseBuf(ac){
    if (NOISE.has(ac)) return NOISE.get(ac);
    const b = ac.createBuffer(1, ac.sampleRate, ac.sampleRate), d = b.getChannelData(0), r = mul(0xC0FFEE);
    for (let i = 0; i < d.length; i++) d[i] = r()*2 - 1;
    NOISE.set(ac, b); return b;
  }
  function master(ac){   // gain -> fixed tanh soft-clip (deterministic; no adaptive compressor)
    const g = ac.createGain(); g.gain.value = 0.4;
    const ws = ac.createWaveShaper(), c = new Float32Array(2049);
    for (let i = 0; i < c.length; i++){ const x = (i/1024 - 1)*3; c[i] = Math.tanh(x)/Math.tanh(3); }
    ws.curve = c; g.connect(ws); ws.connect(ac.destination); return g;
  }
  // schedule one utterance at absolute context time t0
  function schedule(ac, out, t0, v, u){
    for (const s of u.syl){
      const ts = t0 + s.t, te = ts + s.dur;
      const osc = ac.createOscillator(); osc.type = v.wave;
      osc.frequency.setValueAtTime(s.f0, ts);
      osc.frequency.exponentialRampToValueAtTime(Math.max(40, s.f1), te);
      if (v.vibrato_hz > 0.05){
        const lfo = ac.createOscillator(); lfo.frequency.value = v.vibrato_hz;
        const lg = ac.createGain(); lg.gain.value = s.f0 * (Math.pow(2, v.vibrato_cents/1200) - 1);
        lfo.connect(lg); lg.connect(osc.frequency); lfo.start(ts); lfo.stop(te + 0.03);
      }
      const env = ac.createGain();
      const att = Math.min(0.025, s.dur*0.25), rel = Math.min(0.06, s.dur*0.35);
      env.gain.setValueAtTime(0, ts); env.gain.linearRampToValueAtTime(s.amp, ts + att);
      env.gain.setValueAtTime(s.amp, te - rel); env.gain.linearRampToValueAtTime(0, te);
      let src = osc;
      if (v.am_hz > 0){   // purr / growl flutter
        const am = ac.createGain(); am.gain.value = 0.55;
        const lfo = ac.createOscillator(); lfo.type = "triangle"; lfo.frequency.value = v.am_hz;
        const lg = ac.createGain(); lg.gain.value = 0.45; lfo.connect(lg); lg.connect(am.gain); lfo.start(ts); lfo.stop(te + 0.03);
        osc.connect(am); src = am;
      }
      const dry = ac.createBiquadFilter(); dry.type = "lowpass"; dry.frequency.value = 900 + 3200*v.brightness;
      const dg = ac.createGain(); dg.gain.value = 0.45;
      const b1 = ac.createBiquadFilter(); b1.type = "bandpass"; b1.frequency.value = s.F[0]; b1.Q.value = v.formant_q;
      const g1 = ac.createGain(); g1.gain.value = 1.6;
      const b2 = ac.createBiquadFilter(); b2.type = "bandpass"; b2.frequency.value = s.F[1]; b2.Q.value = v.formant_q;
      const g2 = ac.createGain(); g2.gain.value = 0.5 + 0.9*v.brightness;
      src.connect(dry); dry.connect(dg); dg.connect(env);
      src.connect(b1); b1.connect(g1); g1.connect(env);
      src.connect(b2); b2.connect(g2); g2.connect(env);
      if (v.breath > 0.005){
        const nz = ac.createBufferSource(); nz.buffer = noiseBuf(ac); nz.loop = true;
        const nb = ac.createBiquadFilter(); nb.type = "bandpass"; nb.frequency.value = s.F[1]; nb.Q.value = 1.2;
        const ng = ac.createGain(); ng.gain.value = v.breath * 0.6;
        nz.connect(nb); nb.connect(ng); ng.connect(env); nz.start(ts, (s.t*7919) % 0.9); nz.stop(te + 0.02);
      }
      env.connect(out);
      osc.start(ts); osc.stop(te + 0.03);
    }
  }
  function wav(buf){
    const ch = buf.getChannelData(0), n = ch.length, sr = buf.sampleRate;
    const ab = new ArrayBuffer(44 + n*2), dv = new DataView(ab);
    const w = (o, s) => { for (let i = 0; i < s.length; i++) dv.setUint8(o+i, s.charCodeAt(i)); };
    w(0,"RIFF"); dv.setUint32(4, 36 + n*2, true); w(8,"WAVE"); w(12,"fmt "); dv.setUint32(16,16,true); dv.setUint16(20,1,true);
    dv.setUint16(22,1,true); dv.setUint32(24,sr,true); dv.setUint32(28,sr*2,true); dv.setUint16(32,2,true); dv.setUint16(34,16,true);
    w(36,"data"); dv.setUint32(40, n*2, true);
    for (let i = 0; i < n; i++){ const x = Math.max(-1, Math.min(1, ch[i])); dv.setInt16(44 + i*2, Math.round(x*32767), true); }
    let s = ""; const by = new Uint8Array(ab); for (let i = 0; i < by.length; i += 0x8000) s += String.fromCharCode.apply(null, by.subarray(i, i + 0x8000));
    return btoa(s);
  }
  // events: [{t, v, u}] -> base64 16-bit mono WAV of `seconds`
  async function renderWav(events, seconds, sr = 44100){
    const ac = new OfflineAudioContext(1, Math.ceil(seconds*sr), sr);
    const out = master(ac);
    for (const e of events) schedule(ac, out, e.t, e.v, e.u);
    const buf = await ac.startRendering();
    return wav(buf);
  }
  return {utterance, schedule, master, renderWav};
})();

export { Voice };
