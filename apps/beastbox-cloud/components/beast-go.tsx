'use client';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { care, goTo, PLACES, placeById, rememberExchange, talkAndGrow } from '../lib/companion/adventure.mjs';
import { askBeast, guestSafeContext } from '../lib/companion/ask-beast.mjs';
import { buildChatContext } from '../lib/companion/context.mjs';
import { BAG, focusBeast, GBA_KEYS, gamepadButtons, hudCard, keyboardLegend, pressCartridge, QUICK, sheetGesture, sparkVisualState } from '../lib/companion/go-hud.mjs';
import { adoptBeast, shownName } from '../lib/companion/session.mjs';
import { buildGenome } from '../lib/companion/spark/genome.mjs';
import runs from '../lib/companion/spark/runs.json';
import { generateCreature, type CreatureProfile } from '../lib/creature-profile';
import { seedKeyFor } from '../lib/companion/beast-moves.mjs';
import { useBeastAudio } from './use-beast-audio';
import { useCompanion } from './companion-provider';
import { useBeastSession } from './beast-session';
import SparkBeastCompanion from './spark-beast-companion';
import SparkFieldRoster from './spark-field-roster';
import SparkMachine from './spark-machine';
import SparkWanderer from './spark-wanderer';
import MetaMusePanel from './meta-muse-panel';
import css from './beast-go.module.css';
import GbaControls, {controllerInput as normalizedControllerInput} from './gba-controls';

const recorded = runs as Array<{ key: string; backend: string; job_id: string; pub_index: number; num_bits: number; shots: number; counts: Record<string, number> }>;
type SheetId = 'menu' | 'bag' | 'beasts' | 'talk' | 'map' | 'settings' | 'metamuse' | null;
const GAME_KEYS = new Set(['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'z', 'x', 'Z', 'X', 'Enter', 'v', 'V', 'q', 'Q', 'e', 'E']);

export default function BeastGo() {
  const { profile, selectProfile } = useCompanion();
  const { ready, session, trail, sensorLog, change, setTrail } = useBeastSession();
  const [sheet, setSheet] = useState<SheetId>(null);
  const [touch, setTouch] = useState(false);
  const [sound, setSound] = useState(true);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState('');
  const [guestMode, setGuestMode] = useState(true);
  const [label, setLabel] = useState('Guests play with a beast saved in this browser. No owner authority and no private memory. Talk uses the guest-safe brain.');
  const [guestOpen, setGuestOpen] = useState(false);
  const drag = useRef<{ y: number; id: number } | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const deckRef = useRef<HTMLDivElement>(null);
  const beast = session?.beast;
  const nativePlayer = Boolean(beast?.qbeast);
  const card = hudCard(beast);
  const place = placeById(trail.place);
  // Seeded field theme + menu SFX. Silent until a gesture; this screen's Sound switch gates it too.
  const { audio: music, state: musicState } = useBeastAudio();
  const genomeNow = (beast as { genome?: { element?: string; temperament?: string } } | undefined)?.genome;
  const fieldSeed = genomeNow ? seedKeyFor(genomeNow) : `profile:${profile?.seed || 'sparkbeast'}`;
  const fieldElement = genomeNow?.element || 'spark';
  const fieldTemper = genomeNow?.temperament || 'Curious';
  function sfx(kind: string) {
    if (sound) music.sfx(kind, { element: fieldElement, seedKey: fieldSeed });
  }
  useEffect(() => {
    music.setScene({ id: 'field', seedKey: fieldSeed, element: fieldElement, temperament: fieldTemper, enabled: sound });
  }, [music, fieldSeed, fieldElement, fieldTemper, sound]);
  useEffect(() => () => music.clearScene('field'), [music]);
  const stageNow = Number(card.stage) || 0;
  const lastStage = useRef<number | null>(null);
  useEffect(() => {
    if (lastStage.current !== null && stageNow > lastStage.current && sound) music.sfx('levelup', { element: fieldElement, seedKey: fieldSeed });
    lastStage.current = stageNow;
  }, [stageNow, sound, music, fieldElement, fieldSeed]);

  useEffect(() => {
    let cancelled = false;
    void fetch('/api/status', { cache: 'no-store', credentials: 'same-origin' })
      .then((response) => response.json())
      .then((status) => {
        if (cancelled) return;
        const kind = typeof status?.providerKind === 'string' ? status.providerKind : '';
        const ownerBrain = status?.owner === true && status?.backendReachable === true && Boolean(kind) && kind !== 'UNKNOWN' && kind !== 'reference';
        setGuestMode(!ownerBrain);
        if (ownerBrain) setLabel('Type to your beast. Brain Bay answers when it is connected.');
      })
      .catch(() => { if (!cancelled) setGuestMode(true); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const media = window.matchMedia('(pointer: coarse)');
    const apply = () => setTouch(media.matches);
    apply();
    media.addEventListener('change', apply);
    return () => media.removeEventListener('change', apply);
  }, []);

  useEffect(() => {
    // #meta-muse (owner deck, Brain Bay) opens the Pair with Meta Muse sheet.
    const open = () => { if (window.location.hash === '#meta-muse') setSheet('metamuse'); };
    open();
    window.addEventListener('hashchange', open);
    return () => window.removeEventListener('hashchange', open);
  }, []);

  useEffect(() => {
    if (nativePlayer) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape' && event.type === 'keydown') {
        setSheet(null);
        return;
      }
      const target = event.target;
      if (target instanceof HTMLElement && target.closest('textarea, input')) return;
      if (!GAME_KEYS.has(event.key)) return;
      if (!event.isTrusted) return;
      event.preventDefault();
      if (event.type === 'keydown' && event.repeat) return;
      const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
      const entry = Object.entries(GBA_KEYS).find(([, spec]) => {
        const mapped = spec.key.length === 1 ? spec.key.toLowerCase() : spec.key;
        return mapped === key;
      });
      if (!entry) return;
      window.dispatchEvent(new CustomEvent('beastbox:gba-input', {
        detail: { button: entry[0], down: event.type === 'keydown' },
      }));
    }
    window.addEventListener('keydown', onKey);
    window.addEventListener('keyup', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('keyup', onKey);
    };
  }, [nativePlayer]);

  useEffect(() => {
    if (nativePlayer) return;
    if (typeof navigator.getGamepads !== 'function') return;
    let frame = 0;
    let active = new Set<string>();
    const pads = () => Array.from(navigator.getGamepads()).filter((pad): pad is Gamepad => pad !== null && pad.connected !== false);
    const releaseAll = () => {
      for (const button of active) controllerInput(button, false);
      active.clear();
    };
    const poll = () => {
      frame = 0;
      if (document.hidden) { releaseAll(); return; }
      const connected = pads();
      if (!connected.length) { releaseAll(); return; }
      const next = new Set<string>();
      for (const pad of connected) for (const button of gamepadButtons(pad)) next.add(button);
      for (const button of next) if (!active.has(button)) controllerInput(button, true);
      for (const button of active) if (!next.has(button)) controllerInput(button, false);
      active = next;
      frame = window.requestAnimationFrame(poll);
    };
    const start = () => { if (!frame) frame = window.requestAnimationFrame(poll); };
    const stop = () => { if (frame) window.cancelAnimationFrame(frame); frame = 0; releaseAll(); };
    const reconnect = () => { stop(); if (pads().length) start(); };
    const visibility = () => { if (document.hidden) stop(); else if (pads().length) start(); };
    window.addEventListener('gamepadconnected', start);
    window.addEventListener('gamepaddisconnected', reconnect);
    document.addEventListener('visibilitychange', visibility);
    if (pads().length) start();
    return () => {
      stop();
      window.removeEventListener('gamepadconnected', start);
      window.removeEventListener('gamepaddisconnected', reconnect);
      document.removeEventListener('visibilitychange', visibility);
    };
  }, [nativePlayer]);

  // Publish the safe game area (between the portrait card and the bottom HUD /
  // touch pad) so the full-screen cartridge never sits under the field chrome.
  useEffect(() => {
    const root = document.documentElement;
    let frame = 0;
    const measure = () => {
      frame = 0;
      if (sheet) return; // keep the last area while a sheet is open so the game does not jump
      const height = window.innerHeight;
      const card = cardRef.current?.getBoundingClientRect();
      const deck = deckRef.current?.getBoundingClientRect();
      const top = Math.max(0, Math.round((card ? card.bottom : 0) + 8));
      const ceiling = deck && deck.height > 0 ? deck.top : height;
      const bottom = Math.max(0, Math.round(height - ceiling + (deck ? 4 : 0)));
      root.style.setProperty('--go-safe-top', `${top}px`);
      root.style.setProperty('--go-safe-bottom', `${bottom}px`);
    };
    const schedule = () => { if (!frame) frame = window.requestAnimationFrame(measure); };
    schedule();
    const observer = typeof ResizeObserver === 'function' ? new ResizeObserver(schedule) : null;
    for (const node of [cardRef.current, deckRef.current]) if (node && observer) observer.observe(node);
    window.addEventListener('resize', schedule);
    window.visualViewport?.addEventListener('resize', schedule);
    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      observer?.disconnect();
      window.removeEventListener('resize', schedule);
      window.visualViewport?.removeEventListener('resize', schedule);
    };
  }, [sheet, touch, guestMode]);

  useEffect(() => () => {
    document.documentElement.style.removeProperty('--go-safe-top');
    document.documentElement.style.removeProperty('--go-safe-bottom');
  }, []);

  function toggle(next: SheetId) {
    sfx('blip');
    setSheet((current) => current === next ? null : next);
  }

  function onPointerDown(event: React.PointerEvent<HTMLElement>) {
    drag.current = { y: event.clientY, id: event.pointerId };
  }

  function onPointerUp(event: React.PointerEvent<HTMLElement>) {
    if (!drag.current || drag.current.id !== event.pointerId) return;
    const action = sheetGesture(drag.current.y, event.clientY, Boolean(sheet));
    drag.current = null;
    if (action === 'open') setSheet('menu');
    if (action === 'close') setSheet(null);
  }

  function controllerInput(button: string, down: boolean) {
    // Cross-origin LOST COSMOS core and local fallback share one normalized deck.
    return normalizedControllerInput(button, down);
  }

  function meet() {
    const genome = buildGenome({ focus: 40, calm: 40, spark: 20 }, recorded[0], null);
    change((draft) => { adoptBeast(draft, genome, 'Moss'); },{allowUnsignedAdoption:true});
  }

  function useItem(kind: 'feed' | 'pet' | 'rest' | 'spark') {
    sfx('confirm');
    change((draft) => { care(draft, kind); });
  }

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const saying = text.trim();
    if (!saying || busy || !session) return;
    setBusy(true);
    sfx('confirm');
    setText('');
    const raw = buildChatContext({ session, trail, sensors: null, sensorLog });
    const context = guestMode ? guestSafeContext(raw) : raw;
    const result = await askBeast({
      context,
      saying,
      audience: guestMode ? 'guest' : undefined,
      fetchImpl: (input: string, init?: RequestInit) => fetch(input, init),
    });
    if (!result.reply && !result.pending) {
      let local = '';
      const saved=await change((draft) => { local = talkAndGrow(draft, saying).reply || ''; });
      if(!saved.ok){setLabel(saved.reason||'The exchange could not be saved.');setBusy(false);return;}
      setAnswer(local);
      setLabel(`${result.label} Local pattern reply is separate and is not a model answer.`);
    } else if (result.reply) {
      const line = result.reply;
      const saved=await change((draft) => { rememberExchange(draft, saying, line); });
      if(!saved.ok){setLabel(saved.reason||'The exchange could not be saved.');setBusy(false);return;}
      setAnswer(line);
      setLabel(result.label);
    } else {
      setAnswer('');
      setLabel(result.label);
    }
    setBusy(false);
  }

  function keepLocal(genome: { seed: string; names?: Record<number, string> }, name: string, nextProfile?: CreatureProfile) {
    const seed = String(nextProfile ? nextProfile.seed : genome.seed).replace(/[^a-zA-Z0-9]/g, '').slice(0, 32) || 'sparkbeast';
    selectProfile(nextProfile || generateCreature(seed, profile?.baseLook ?? 'nebula'));
    change((draft) => { adoptBeast(draft, genome, name); },{allowUnsignedAdoption:true});
  }

  function toggleSound() {
    const next = !sound;
    setSound(next);
    window.dispatchEvent(new CustomEvent('beastbox:gba-volume', { detail: next ? (musicState.focus === 'beast' ? 0.06 : 0.35) : 0 }));
    if (next) { music.sparkUnmute(); music.unlock(); music.sfx('confirm', { element: fieldElement, seedKey: fieldSeed }); }
  }

  // Audio focus: "Game audio" ducks the beast music while the cartridge runs;
  // "Beast music" turns the cartridge down instead. Both stay behind the Sound switch.
  function toggleFocus() {
    const next = musicState.focus === 'beast' ? 'game' : 'beast';
    music.setFocus(next);
    window.dispatchEvent(new CustomEvent('beastbox:gba-volume', { detail: sound ? (next === 'beast' ? 0.06 : 0.35) : 0 }));
    sfx('blip');
  }

  return <main className={css.field} data-go-screen="true">
    <h1 className={css.sr}>Lost Cosmos field</h1>
    {guestMode && guestOpen ? <p className={css.guestNote} data-guest-play="true" id="go-guest-note">Guests play with a beast saved in this browser. No owner authority and no private memory. Talk uses the guest-safe brain.</p> : null}
    <div className={css.card} ref={cardRef}>
      <span className={css.portrait}>
        <SparkBeastCompanion profile={profile} fallbackLook={profile?.baseLook ?? 'nebula'} compact state={sparkVisualState(card.mood)} className={css.spark} label={`${profile?.name || 'Spark Beast'} portrait`} />
      </span>
      <button type="button" className={css.identity} onClick={() => toggle('beasts')}>
        <span className={css.meta}>
          <strong>{ready ? (profile?.name || 'Spark Beast') : 'Loading save'}</strong>
          <span>Lv {card.stage} · {card.mood}</span>
          <span className={css.xp} role="meter" aria-label={`Experience ${card.xp}`} aria-valuemin={0} aria-valuemax={card.goal || card.xp || 1} aria-valuenow={card.xp}><i style={{ width: `${Math.round(card.ratio * 100)}%` }} /></span>
        </span>
      </button>
      {guestMode ? <button type="button" className={css.guestChip} data-guest-play="true" aria-expanded={guestOpen} aria-controls="go-guest-note"
        aria-label={guestOpen ? 'Hide the guest play note' : 'Show the guest play note'} onClick={() => setGuestOpen((value) => !value)}>Guest {guestOpen ? '▴' : 'ⓘ'}</button> : null}
    </div>
    {!nativePlayer && touch && !sheet ? <div className={css.handheld} ref={deckRef}>
      <GbaControls shoulders onMenu={() => toggle('menu')} />
    </div> : <div className={css.screenMenu} onPointerDown={onPointerDown} onPointerUp={onPointerUp}>
      <button type="button" className={css.handle} aria-label="Swipe up for the menu" onClick={() => toggle('menu')}><i /></button>
      <button type="button" aria-label="Main menu" aria-expanded={sheet === 'menu'} onClick={() => toggle('menu')}>☰</button>
    </div>}
    <section className={`${css.sheet} ${sheet ? css.open : ''}`} role="dialog" aria-modal="false" aria-hidden={sheet ? undefined : true} aria-label={sheet ? `${sheet} sheet` : 'Closed sheet'}>
      <div className={css.sheetHead}>
        <button type="button" className={css.handle} aria-label="Swipe down to close" onPointerDown={onPointerDown} onPointerUp={onPointerUp} onClick={() => setSheet(null)}><i /></button>
        <button type="button" className={css.sheetClose} aria-label="Close field menu" onClick={() => setSheet(null)}>×</button>
      </div>
      {sheet === 'menu' ? <>
        <h2>Field menu</h2>
        <div className={css.list}>
          {QUICK.map((item) => <button key={item.id} type="button" onClick={() => { sfx('confirm'); setSheet(item.id as SheetId); }}>{item.label}</button>)}
          <button type="button" data-meta-muse-entry="menu" onClick={() => { sfx('confirm'); setSheet('metamuse'); }}>Pair with Meta Muse</button>
        </div>
      </> : null}
      {sheet === 'bag' ? <>
        <h2>Bag</h2>
        <p>Care items use the same save as the cage. Feed, pet, rest, and spark change energy, bond, and experience.</p>
        {beast ? <div className={css.row}>{BAG.map((item) => <button key={item.id} type="button" onClick={() => useItem(item.kind)}>{item.label}</button>)}</div> : <button className={css.send} type="button" onClick={meet}>Meet a spark beast</button>}
        <p>Energy {beast?.energy ?? 0} · Bond {beast?.bond || 0} · XP {card.xp}</p>
      </> : null}
      {sheet === 'beasts' ? <>
        <h2>Beasts</h2>
        <p>{profile ? `${profile.name} · ${profile.family} is the Spark Beast game profile on this browser.` : 'Customize chooses the Spark Beast. This portrait uses that same profile, including the preview when none is saved yet.'}</p>
        <div className={css.row}><Link href="/beast-cage#customize">Customize this Beast</Link></div>
        <div className={css.list}>
          {(session?.bestiary || []).map((item: { seed: string; name?: string }) => <button key={item.seed} type="button" aria-pressed={beast?.seed === item.seed} onClick={() => { sfx('confirm'); change((draft) => { focusBeast(draft, item.seed); },{allowUnsignedAdoption:true}); }}>{item.name || 'Beast'}{beast?.seed === item.seed ? ' · with you' : ''}</button>)}
        </div>
        {!session?.bestiary?.length ? <button className={css.send} type="button" onClick={meet}>Meet a spark beast</button> : null}
        <SparkFieldRoster onChoose={(choice) => keepLocal(choice.genome, choice.name)} />
        <SparkMachine onReveal={(result) => keepLocal(result.genome, result.name, result.profile)} />
      </> : null}
      {sheet === 'talk' ? <>
        <h2>Talk</h2>
        <SparkWanderer profile={profile} pulse={answer} thinking={busy} />
        <div className={css.reply} role="status">
          <strong>{label}</strong>
          <p>{busy ? 'Waiting for a verified reply…' : answer || 'Type to your beast. If Brain Bay or the RAWRPHØS guest host is quiet, the on-device pattern memory answers and says so.'}</p>
        </div>
        <form onSubmit={(event) => void send(event)}>
          <label htmlFor="go-talk">Message</label>
          <textarea id="go-talk" value={text} maxLength={400} disabled={busy || !beast} autoFocus onChange={(event) => setText(event.target.value)} placeholder={beast ? `Say something to ${shownName(beast)}` : 'Meet a beast in the bag first'} />
          <button className={css.send} type="submit" disabled={busy || !text.trim() || !beast}>{busy ? 'Waiting…' : 'Send'}</button>
        </form>
      </> : null}
      {sheet === 'map' ? <>
        <h2>Map</h2>
        <p>Lost Cosmos on this cartridge is the world. These field notes share the care trail with Adventure. You are near {place.name}.</p>
        <div className={css.list}>
          {PLACES.map((spot) => <button key={spot.id} type="button" aria-pressed={trail.place === spot.id} onClick={() => { sfx('blip'); setTrail(goTo(trail, spot.id)); }}>{spot.name}</button>)}
        </div>
        <p>Nearby: {place.nearby.join(', ')}.</p>
      </> : null}
      {sheet === 'settings' ? <>
        <h2>Settings</h2>
        <div className={css.row}>
          <button type="button" aria-pressed={sound} onClick={toggleSound}>Sound {sound ? 'on' : 'off'}</button>
          <button type="button" aria-pressed={touch} onClick={() => setTouch((value) => !value)}>Touch controls {touch ? 'on' : 'off'}</button>
        </div>
        <div className={css.row} data-beast-music="true">
          <button type="button" aria-pressed={musicState.musicOn} onClick={() => { music.unlock(); music.setMusic(!musicState.musicOn); }}>Music {musicState.musicOn ? 'on' : 'off'}</button>
          <button type="button" aria-pressed={musicState.focus === 'beast'} onClick={toggleFocus}>Audio focus: {musicState.focus === 'beast' ? 'Beast music' : 'Game audio'}</button>
          <label className={css.copy}>Music volume <input type="range" min={0} max={100} step={5} value={Math.round(musicState.volume * 100)} aria-label="Beast music volume" onChange={(event) => music.setVolume(Number(event.target.value) / 100)} /></label>
        </div>
        <p>These switches stay on this field screen. Brain Bay, Model Bay, and owner settings are left as they are. On a phone the touch pad walks the cartridge. On desktop the same actions work from the keyboard, and standard browser Gamepad API controllers feed the exact same cartridge input path when connected.</p>
        <div className={css.list}>
          {keyboardLegend().map(([key, action]) => <p key={key} className={css.copy}>{key}: {action}</p>)}
        </div>
        <div className={css.row}>
          <Link href="/beast-cage">Cage</Link>
          <Link href="/beast-cage/play">Adventure</Link>
          <Link href="/workspace">Owner deck</Link>
        </div>
        <div className={css.row}>
          <button type="button" data-meta-muse-entry="settings" onClick={() => { sfx('confirm'); setSheet('metamuse'); }}>Pair with Meta Muse</button>
        </div>
      </> : null}
      {sheet === 'metamuse' ? <MetaMusePanel /> : null}
    </section>
  </main>;
}
