'use client';

import { useEffect, useRef, useState } from 'react';
import { Coffee, Github, Heart, Sparkles, Volume2, VolumeX, X, Zap } from 'lucide-react';

const STRIPE_URL = 'https://buy.stripe.com/3cIbJ27zN7kO8mN97pa7C01';
const SPONSORS_URL = 'https://github.com/sponsors/NavisWORLD';
const COFFEE_URL = 'https://buymeacoffee.com/Cosmic_syanpse';

export default function CosmicSupportWidget() {
  const [open, setOpen] = useState(false);
  const [soundOn, setSoundOn] = useState(true);
  const [reacting, setReacting] = useState(false);
  const [beastLine, setBeastLine] = useState('psst… got any stardust?');
  const audioContextRef = useRef<AudioContext | null>(null);
  const reactionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const react = (line: string) => {
    setBeastLine(line);
    setReacting(true);
    if (reactionTimerRef.current) clearTimeout(reactionTimerRef.current);
    reactionTimerRef.current = setTimeout(() => setReacting(false), 850);
  };

  const playBeastChirp = (kind: 'open' | 'close' | 'fuel' = 'open', force = false) => {
    if ((!soundOn && !force) || typeof window === 'undefined' || !window.AudioContext) return;

    try {
      const ctx = audioContextRef.current ?? new window.AudioContext();
      audioContextRef.current = ctx;
      if (ctx.state === 'suspended') void ctx.resume();

      const now = ctx.currentTime;
      const notes =
        kind === 'fuel'
          ? [523.25, 783.99, 1046.5]
          : kind === 'close'
            ? [659.25, 493.88]
            : [587.33, 783.99, 987.77];

      notes.forEach((frequency, index) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        const start = now + index * 0.055;
        const stop = start + 0.13;

        osc.type = index % 2 === 0 ? 'sine' : 'triangle';
        osc.frequency.setValueAtTime(frequency, start);
        osc.frequency.exponentialRampToValueAtTime(frequency * 1.035, stop);

        gain.gain.setValueAtTime(0.0001, start);
        gain.gain.exponentialRampToValueAtTime(0.045, start + 0.018);
        gain.gain.exponentialRampToValueAtTime(0.0001, stop);

        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(start);
        osc.stop(stop + 0.02);
      });
    } catch {
      // Sound is optional. Browsers may decline AudioContext creation.
    }
  };

  const togglePanel = () => {
    const next = !open;
    setOpen(next);
    react(next ? '✨ oh! a visitor!' : '🌙 back to orbit…');
    playBeastChirp(next ? 'open' : 'close');
  };

  const supportClick = (kind: 'stripe' | 'github' | 'coffee') => {
    const line =
      kind === 'stripe'
        ? '⚡ COSMIC FUEL DETECTED!'
        : kind === 'github'
          ? '💖 a new constellation friend!'
          : '☕ tiny cosmic coffee acquired!';
    react(line);
    playBeastChirp('fuel');
  };

  const toggleSound = () => {
    const next = !soundOn;
    setSoundOn(next);
    setBeastLine(next ? '🔊 chirps enabled!' : '🔇 stealth Beast mode');
    if (next) playBeastChirp('open', true);
  };

  useEffect(() => {
    return () => {
      if (reactionTimerRef.current) clearTimeout(reactionTimerRef.current);
      const ctx = audioContextRef.current;
      if (ctx && ctx.state !== 'closed') void ctx.close();
    };
  }, []);

  return (
    <aside className={`cosmic-support ${open ? 'is-open' : ''}`} aria-label="Support Beast Box">
      {!open ? (
        <button
          type="button"
          className="cosmic-support-launcher"
          onClick={togglePanel}
          aria-expanded="false"
          aria-label="Open Feed the Beast support panel"
        >
          <span className={`support-beast-shell ${reacting ? 'is-reacting' : ''}`} aria-hidden="true">
            <img className="support-beast-img" src="/cosmic-creature.svg" alt="" />
            <span className="support-beast-glow" />
            <span className="support-beast-spark">✦</span>
          </span>
          <span className="support-launcher-copy">
            <small>THE BEAST HAS NOTICED YOU</small>
            <strong>Feed the Beast</strong>
            <em>{beastLine}</em>
          </span>
          <Heart className="support-launcher-heart" size={18} aria-hidden="true" />
        </button>
      ) : (
        <div className="cosmic-support-panel">
          <div className="support-constellation" aria-hidden="true">
            <i/><i/><i/><i/><i/>
          </div>

          <div className="support-panel-tools">
            <button
              type="button"
              className="support-sound"
              onClick={toggleSound}
              aria-label={soundOn ? 'Mute Beast sounds' : 'Enable Beast sounds'}
              aria-pressed={soundOn}
              title={soundOn ? 'Mute Beast sounds' : 'Enable Beast sounds'}
            >
              {soundOn ? <Volume2 size={16}/> : <VolumeX size={16}/>}
            </button>
            <button
              type="button"
              className="support-close"
              onClick={togglePanel}
              aria-label="Close support panel"
            >
              <X size={17}/>
            </button>
          </div>

          <div className="support-beast-stage" aria-label="Cosmic Beast support companion">
            <span className={`support-beast-shell support-beast-large ${reacting ? 'is-reacting' : ''}`}>
              <img className="support-beast-img" src="/cosmic-creature.svg" alt="A smiling purple cosmic Beast" />
              <span className="support-beast-glow" aria-hidden="true" />
              <span className="support-beast-spark" aria-hidden="true">✦</span>
            </span>
            <div className="support-beast-bubble" aria-live="polite">
              <small>BEAST TRANSMISSION</small>
              <strong>{beastLine}</strong>
            </div>
          </div>

          <p className="support-kicker"><Sparkles size={14}/> FUEL THE LIVING COSMOS</p>
          <h2>Keep the strange little universe alive.</h2>
          <p className="support-copy">
            Beast Box is open source. Support helps cover hosting, compute, storage, hardware
            prototypes, documentation, experiments, and the time it takes to keep shipping.
          </p>

          <div className="support-fuel" aria-label="Ways support helps">
            <span>✦ hosting + storage</span>
            <span>⚛ compute + experiments</span>
            <span>🐉 creature + game work</span>
          </div>

          <a
            className="support-primary"
            href={STRIPE_URL}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => supportClick('stripe')}
          >
            Direct Cosmic Fuel via Stripe <Zap size={18}/>
          </a>

          <a
            className="support-secondary"
            href={SPONSORS_URL}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => supportClick('github')}
          >
            Sponsor the COSMOS on GitHub <Github size={17}/>
          </a>

          <a
            className="support-secondary support-coffee"
            href={COFFEE_URL}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => supportClick('coffee')}
          >
            Send a Cosmic Coffee <Coffee size={17}/>
          </a>

          <p className="support-honesty">
            Support is optional. Curiosity is free. The Beast remains suspiciously hungry.
            No fake counters, scarcity, equity, or promised returns.
          </p>
        </div>
      )}
    </aside>
  );
}
