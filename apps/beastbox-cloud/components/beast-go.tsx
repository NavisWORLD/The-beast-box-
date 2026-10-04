'use client';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { care, goTo, PLACES, placeById, rememberExchange, talkAndGrow } from '../lib/companion/adventure.mjs';
import { askBeast, guestSafeContext } from '../lib/companion/ask-beast.mjs';
import { buildChatContext } from '../lib/companion/context.mjs';
import { BAG, focusBeast, GBA_KEYS, hudCard, keyboardLegend, pressCartridge, QUICK, sheetGesture, sparkVisualState } from '../lib/companion/go-hud.mjs';
import { adoptBeast, shownName } from '../lib/companion/session.mjs';
import { buildGenome } from '../lib/companion/spark/genome.mjs';
import runs from '../lib/companion/spark/runs.json';
import { generateCreature, type CreatureProfile } from '../lib/creature-profile';
import { useCompanion } from './companion-provider';
import { useBeastSession } from './beast-session';
import SparkBeastCompanion from './spark-beast-companion';
import SparkFieldRoster from './spark-field-roster';
import SparkMachine from './spark-machine';
import SparkWanderer from './spark-wanderer';
import css from './beast-go.module.css';

const recorded = runs as Array<{ key: string; backend: string; job_id: string; pub_index: number; num_bits: number; shots: number; counts: Record<string, number> }>;
type SheetId = 'menu' | 'bag' | 'beasts' | 'talk' | 'map' | 'settings' | null;
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
  const drag = useRef<{ y: number; id: number } | null>(null);
  const beast = session?.beast;
  const card = hudCard(beast);
  const place = placeById(trail.place);

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
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setSheet(null);
        return;
      }
      const target = event.target;
      if (target instanceof HTMLElement && target.closest('textarea, input')) return;
      if (GAME_KEYS.has(event.key)) event.preventDefault();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  function toggle(next: SheetId) {
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

  function hold(button: string, event: React.PointerEvent<HTMLButtonElement>) {
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    pressCartridge(button, true, window);
    const release = () => {
      pressCartridge(button, false, window);
      event.currentTarget.removeEventListener('pointerup', release);
      event.currentTarget.removeEventListener('pointercancel', release);
    };
    event.currentTarget.addEventListener('pointerup', release);
    event.currentTarget.addEventListener('pointercancel', release);
  }

  function meet() {
    const genome = buildGenome({ focus: 40, calm: 40, spark: 20 }, recorded[0], null);
    change((draft) => { adoptBeast(draft, genome, 'Moss'); });
  }

  function useItem(kind: 'feed' | 'pet' | 'rest' | 'spark') {
    change((draft) => { care(draft, kind); });
  }

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const saying = text.trim();
    if (!saying || busy || !session) return;
    setBusy(true);
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
      change((draft) => { local = talkAndGrow(draft, saying).reply || ''; });
      setAnswer(local);
      setLabel(`${result.label} Local pattern reply is separate and is not a model answer.`);
    } else if (result.reply) {
      const line = result.reply;
      change((draft) => { rememberExchange(draft, saying, line); });
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
    change((draft) => { adoptBeast(draft, genome, name); });
  }

  function toggleSound() {
    const next = !sound;
    setSound(next);
    window.dispatchEvent(new CustomEvent('beastbox:gba-volume', { detail: next ? 0.35 : 0 }));
  }

  return <main className={css.field} data-go-screen="true">
    <h1 className={css.sr}>Lost Cosmos field</h1>
    {guestMode ? <p className={css.guestNote} data-guest-play="true">Guest-safe play · no owner memory or authority.</p> : null}
    <Link className={css.exit} href="/beast-cage" aria-label="Back to Beast Cage">×</Link>
    <div className={css.card}>
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
    </div>
    {touch && !sheet ? <div className={css.pad} aria-label="Touch controls">
      {(['up', 'left', 'right', 'down'] as const).map((button) => <button key={button} type="button" aria-label={GBA_KEYS[button].label} onPointerDown={(event) => hold(button, event)}>{GBA_KEYS[button].label}</button>)}
    </div> : null}
    {touch && !sheet ? <div className={css.actions} aria-label="Touch buttons">
      <button type="button" aria-label="L" onPointerDown={(event) => hold('l', event)}>L</button>
      <button type="button" aria-label="R" onPointerDown={(event) => hold('r', event)}>R</button>
      <button type="button" className={css.a} aria-label="A" onPointerDown={(event) => hold('a', event)}>A</button>
      <button type="button" aria-label="B" onPointerDown={(event) => hold('b', event)}>B</button>
      <button type="button" className={css.wide} aria-label="Start" onPointerDown={(event) => hold('start', event)}>Start</button>
    </div> : null}
    <div className={css.chrome} onPointerDown={onPointerDown} onPointerUp={onPointerUp}>
      <button type="button" className={css.handle} aria-label="Swipe up for the menu" onClick={() => toggle('menu')}><i /></button>
      <div className={css.quick} role="toolbar" aria-label="Field shortcuts">
        {QUICK.map((item) => <button key={item.id} type="button" aria-pressed={sheet === item.id} onClick={() => toggle(item.id as SheetId)}>{item.label}</button>)}
      </div>
      <button type="button" className={css.orb} aria-label="Main menu" aria-expanded={sheet === 'menu'} onClick={() => toggle('menu')}>Menu</button>
    </div>
    <section className={`${css.sheet} ${sheet ? css.open : ''}`} role="dialog" aria-modal="false" aria-hidden={sheet ? undefined : true} aria-label={sheet ? `${sheet} sheet` : 'Closed sheet'}>
      <button type="button" className={css.handle} aria-label="Swipe down to close" onPointerDown={onPointerDown} onPointerUp={onPointerUp} onClick={() => setSheet(null)}><i /></button>
      {sheet === 'menu' ? <>
        <h2>Field menu</h2>
        <div className={`${css.list} ${css.menuGrid}`}>
          {QUICK.map((item) => <button key={item.id} type="button" onClick={() => setSheet(item.id as SheetId)}>{item.label}</button>)}
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
          {(session?.bestiary || []).map((item: { seed: string; name?: string }) => <button key={item.seed} type="button" aria-pressed={beast?.seed === item.seed} onClick={() => change((draft) => { focusBeast(draft, item.seed); })}>{item.name || 'Beast'}{beast?.seed === item.seed ? ' · with you' : ''}</button>)}
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
          {PLACES.map((spot) => <button key={spot.id} type="button" aria-pressed={trail.place === spot.id} onClick={() => setTrail(goTo(trail, spot.id))}>{spot.name}</button>)}
        </div>
        <p>Nearby: {place.nearby.join(', ')}.</p>
      </> : null}
      {sheet === 'settings' ? <>
        <h2>Settings</h2>
        <div className={css.row}>
          <button type="button" aria-pressed={sound} onClick={toggleSound}>Sound {sound ? 'on' : 'off'}</button>
          <button type="button" aria-pressed={touch} onClick={() => setTouch((value) => !value)}>Touch controls {touch ? 'on' : 'off'}</button>
        </div>
        <p>Sound and touch controls only affect this game screen. Owner settings stay separate.</p>
        <div className={css.list}>
          {keyboardLegend().map(([key, action]) => <p key={key} className={css.copy}>{key}: {action}</p>)}
        </div>
        <div className={css.row}>
          <Link href="/beast-cage">Cage</Link>
          <Link href="/beast-cage/play">Adventure</Link>
          <Link href="/workspace">Owner deck</Link>
        </div>
      </> : null}
    </section>
  </main>;
}
