'use client';

import { useEffect, useRef, useState, type CSSProperties, type KeyboardEvent } from 'react';
import { createPortal } from 'react-dom';
import { Coffee, Github, Heart, Volume2, VolumeX, X } from 'lucide-react';
import { SUPPORT_PORTALS, SUPPORT_TIERS, type SupportGroup, type SupportTier } from '../lib/support-tiers';
import { createSupportAudio } from '../lib/support-audio.mjs';
import { shownName } from '../lib/companion/session.mjs';
import { useCompanion } from './companion-provider';
import { useBeastSession } from './beast-session';
import { useBeastAudio } from './use-beast-audio';
import SupportMascot from './support-mascot';
import SupportTierCard from './support-tier-card';

const SOUND_KEY = 'beastbox-support-sound-v1';
const QUIPS = ['✨ MORE STARDUST!!', '🌌 hehe… cosmic snacks', '💫 that tickles my orbit!',
  '🐉 tiny dragon noises intensify', '⚛️ spark accepted. science unaffected.'];

export default function CosmicSupportWidget() {
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [group, setGroup] = useState<SupportGroup>('monthly');
  const [soundOn, setSoundOn] = useState(true);
  const [beastLine, setBeastLine] = useState('psst… got any stardust?');
  const [reaction, setReaction] = useState<string | null>(null);
  const [burst, setBurst] = useState(0);
  const launcherRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const quipRef = useRef(0);
  const soundRef = useRef(true);
  const playerRef = useRef<ReturnType<typeof createSupportAudio> | null>(null);
  const { audio, state: audioState } = useBeastAudio();
  // Read existing identity only. Support never writes, adopts or evolves a Beast.
  const { profile } = useCompanion();
  const { ready, session } = useBeastSession();
  const name = ready && session?.beast ? shownName(session.beast) : profile?.name;
  const audible = soundOn && !audioState.sparkMuted;

  useEffect(() => {
    setMounted(true);
    try {
      soundRef.current = localStorage.getItem(SOUND_KEY) !== 'false';
      setSoundOn(soundRef.current);
    } catch { /* a UI preference is optional */ }
    playerRef.current = createSupportAudio(audio, { enabled: () => soundRef.current });
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
      playerRef.current?.dispose(); playerRef.current = null;
    };
  }, [audio]);

  useEffect(() => {
    if (audioState.hidden || audioState.sparkMuted) playerRef.current?.stop();
  }, [audioState.hidden, audioState.sparkMuted]);
  useEffect(() => { if (open) closeRef.current?.focus(); }, [open]);

  const react = (line: string, id = 'beast') => {
    setBeastLine(line); setReaction(id); setBurst(value => value + 1);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setReaction(null), 900);
  };
  const chirp = (tier = SUPPORT_TIERS[0]) => {
    if (!soundRef.current || audio.getSnapshot().sparkMuted) return;
    // Only explicit click/key/touch activations call this function.
    audio.unlock(); void playerRef.current?.play(tier.sound);
  };
  const openPanel = () => { setOpen(true); react('✨ oh! a visitor!'); chirp(); };
  const closePanel = () => {
    setOpen(false); react('🌙 back to orbit…'); playerRef.current?.stop();
    requestAnimationFrame(() => launcherRef.current?.focus());
  };
  const toggleSound = () => {
    const next = !audible;
    soundRef.current = next; setSoundOn(next);
    try { localStorage.setItem(SOUND_KEY, String(next)); } catch { /* optional */ }
    if (next) { audio.sparkUnmute(); chirp(); setBeastLine('🔊 tiny chirps enabled!'); }
    else { playerRef.current?.stop(); setBeastLine('🔇 stealth Beast mode'); }
  };
  const meet = (tier: SupportTier) => {
    react(tier.interactionLines[quipRef.current++ % tier.interactionLines.length], tier.id); chirp(tier);
  };
  const depart = (tier?: SupportTier, portal = 'cosmic fuel') => {
    // A link is a departure, not a payment receipt. Reserved success copy is
    // never used without a future server-verified payment signal.
    react(`Opening ${portal} portal…${tier ? ` ${tier.name} is waving goodbye.` : ''}`, tier?.id); chirp(tier);
  };
  const petBeast = () => { react(QUIPS[quipRef.current++ % QUIPS.length]); chirp(SUPPORT_TIERS[4]); };
  const selectTab = (next: SupportGroup) => { setGroup(next); setReaction(null); };
  const tabKeys = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    let next = index;
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') next = 1 - index;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = 1;
    else return;
    event.preventDefault(); selectTab(next === 0 ? 'monthly' : 'once'); tabRefs.current[next]?.focus();
  };

  if (!mounted) return null;
  // The landing artwork creates a stacking context. Mount alongside the existing
  // game dock so its controls cannot intercept this panel's checkout buttons.
  return createPortal(
    <aside className={`cosmic-support ${open ? 'is-open' : ''} ${audioState.hidden ? 'is-paused' : ''}`} aria-label="Support Beast Box">
      {!open ? <button ref={launcherRef} type="button" className="cosmic-support-launcher" onClick={openPanel}
        aria-expanded="false" aria-controls="living-support-shrine" aria-label="Open Feed the Beast support panel">
        <span className="support-beast-shell" aria-hidden="true"><SupportMascot reacting={reaction === 'beast'}/></span>
        <span className="support-launcher-copy"><small>THE BEAST HAS NOTICED YOU</small><strong>Feed the Beast</strong><em>Support the tiny universe.</em></span>
        <Heart className="support-launcher-heart" size={18} aria-hidden="true"/>
      </button> : <section id="living-support-shrine" className="cosmic-support-panel" role="dialog" aria-modal="false"
        aria-labelledby="support-title" onKeyDown={event => { if (event.key === 'Escape') { event.preventDefault(); closePanel(); } }}>
        <div className="support-shrine-topbar">
          <span className="support-room-plaque">NAVISWORLD / SECRET ROOM</span>
          <div className="support-panel-tools">
            <button type="button" className="support-sound" onClick={toggleSound} aria-pressed={audible}
              aria-label={audible ? 'Mute Beast sounds' : 'Enable Beast sounds'} title={audible ? 'Mute Beast sounds' : 'Enable Beast sounds'}>
              {audible ? <Volume2 size={18} aria-hidden="true"/> : <VolumeX size={18} aria-hidden="true"/>}
            </button>
            <button ref={closeRef} type="button" className="support-close" onClick={closePanel} aria-label="Close support panel"><X size={20} aria-hidden="true"/></button>
          </div>
        </div>
        <div className="support-shrine-scroll">
          <header className="support-shrine-header">
            <button type="button" className="support-beast-pet" onClick={petBeast} aria-label="Sprinkle stardust on the Beast">
              <SupportMascot reacting={reaction === 'beast'}/>
              {reaction === 'beast' && burst > 0 && <span key={burst} className="support-stardust-burst" aria-hidden="true">
                {Array.from({length:12},(_,i)=><i key={i} style={{'--i':i} as CSSProperties}>✦</i>)}
              </span>}
            </button>
            <div><p className="support-kicker">THE LIVING SUPPORT SHRINE</p><h2 id="support-title">Feed the Beast</h2>
              <p className="support-copy">Support the tiny universe.<br/>Encourage bad ideas.</p>
              {name && <p className="support-active-name">{String(name).slice(0,32)} found the secret room.</p>}
            </div>
          </header>
          <div className="support-beast-bubble" role="status" aria-live="polite" aria-atomic="true"><span data-support-transmission>{beastLine}</span></div>
          <p className="support-workshop-copy">This workshop runs on stardust, code, and alarming persistence. Hosting, compute, games, experiments, prototype goblins. You get the idea.</p>
          <div className="support-tabs" role="tablist" aria-label="Choose a support rhythm">
            {(['monthly','once'] as const).map((tab,i)=><button key={tab} type="button" ref={el => { tabRefs.current[i] = el; }}
              role="tab" id={`support-tab-${tab}`} aria-selected={group === tab} aria-controls={`support-tiers-${tab}`}
              tabIndex={group === tab ? 0 : -1} onClick={() => selectTab(tab)} onKeyDown={event => tabKeys(event,i)}>
              {tab === 'monthly' ? 'Monthly Companions' : 'One-Time Fuel'}
            </button>)}
          </div>
          {(['monthly','once'] as const).map(tab=><div key={tab} role="tabpanel" id={`support-tiers-${tab}`}
            aria-labelledby={`support-tab-${tab}`} hidden={group !== tab} className="support-tier-grid">
            {group === tab && SUPPORT_TIERS.filter(tier=>tier.group === tab).map(tier=><SupportTierCard key={tier.id} tier={tier}
              reacting={reaction === tier.id} burst={burst} onMeet={meet} onDepart={depart}/>)}
          </div>)}
          <p className="support-checkout-note">Each option opens its own Stripe checkout in a new tab. Monthly support is recurring; one-time fuel is a single payment.</p>
          <div className="support-other-portals">
            <a href={SUPPORT_PORTALS.sponsors} target="_blank" rel="noopener noreferrer" onClick={()=>depart(undefined,'GitHub Sponsors')}><Github size={17} aria-hidden="true"/>GitHub Sponsors</a>
            <a href={SUPPORT_PORTALS.coffee} target="_blank" rel="noopener noreferrer" onClick={()=>depart(undefined,'cosmic coffee')}><Coffee size={17} aria-hidden="true"/>Buy Me a Coffee</a>
          </div>
          <p className="support-honesty">Support is optional. Curiosity is free. The Beast remains suspiciously hungry.</p>
          <p className="support-boundary">Voluntary support provides no equity, ownership, investment returns, or guaranteed feature delivery. Petting, sounds and stardust are cosmetic. Payment never changes creature identity or scientific results.</p>
          <span className="support-sticker" aria-hidden="true">MODEL ≠ BEAST · NULL RESULTS LIVE HERE TOO</span>
        </div>
      </section>}
    </aside>, document.body
  );
}
