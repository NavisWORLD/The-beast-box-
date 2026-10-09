'use client';
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { care, nameBeast, talkAndGrow, train } from '../lib/companion/adventure.mjs';
import { exportLcx1, exportQbeast, importLcx1, importQbeast } from '../lib/companion/cage.mjs';
import { adoptBeast, beastIdentity, exportSession, importSession, recordCreatureExperience, stageFromXp, shownName } from '../lib/companion/session.mjs';
import { buildGenome } from '../lib/companion/spark/genome.mjs';
import { canonicalJson } from '../public/spark/genome.mjs';
import runs from '../lib/companion/spark/runs.json';
import { useBeastSession } from './beast-session';
import PixelBeast from './pixel-beast';
import { serializeQbeast } from '../public/spark/qbeast.mjs';
import { replaySpark, selectSpark, withSparkLock, SESSION_KEY } from '../public/spark/identity.mjs';
import { DEVICE_JOURNEY_SCHEMA, DEVICE_JOURNEY_LIMIT, loadDeviceJourneyRuns, readDeviceJourney, serializeDeviceJourney, restoreDeviceJourney, retainedNativeBytes } from '../public/spark/device-journey.mjs';
import WeightGrid from './weight-grid';
import { useUniverseMotion } from './use-universe-motion';
import { visualStateFromBeast } from '../lib/companion/creature-visual-state.mjs';
import css from './beast-care-deck.module.css';

const recorded = runs as Array<{ key: string; backend: string; job_id: string; pub_index: number; num_bits: number; shots: number; counts: Record<string, number> }>;
type Reaction = 'pet' | 'feed' | 'rest' | 'train' | 'name' | 'talk' | 'save';

function download(bytes: BlobPart, name: string, type: string) {
  const url = URL.createObjectURL(new Blob([bytes], { type }));
  const link = document.createElement('a');
  link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function savedHere(session: any) {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return !!raw && canonicalJson(exportSession(importSession(JSON.parse(raw)))) === canonicalJson(exportSession(session));
  } catch { return false; }
}
function selected() {
  window.dispatchEvent(new Event('beastbox:spark-selected'));
  window.dispatchEvent(new Event('beastbox:spark-session'));
}

export default function BeastCareDeck({ chat = true, sprite = true }: { chat?: boolean; sprite?: boolean }) {
  const { ready, session, change, storageStatus } = useBeastSession();
  const { reduced } = useUniverseMotion();
  const router = useRouter();
  const [name, setName] = useState('');
  const [line, setLine] = useState('');
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [hits, setHits] = useState(0);
  const [round, setRound] = useState(0);
  const started = useRef(0);
  const marker = useRef<HTMLElement>(null);
  const file = useRef<HTMLInputElement>(null);
  const beast = session?.beast;
  const mind = session?.mind;
  const id = beastIdentity(beast);
  const visual = visualStateFromBeast(beast);
  const pose = visual === 'observing' ? 'walk' : visual === 'listening' ? 'react' : ['sleeping', 'celebrating', 'thinking', 'remembering'].includes(visual) ? 'emote' : 'idle';
  const emote = visual === 'sleeping' ? 'sleep' : visual === 'celebrating' ? 'happy' : visual === 'thinking' || visual === 'remembering' ? 'think' : 'watch';
  const named = !!beast?.displayName && !Object.values(beast.genome?.names || {}).includes(beast.displayName);
  const petted = (beast?.bond || 0) >= 3;
  const trained = (session?.train?.rounds || 0) > 0;

  useEffect(() => {
    setSaved(!!session && savedHere(session));
    const check = () => setSaved(!!session && savedHere(session));
    window.addEventListener('storage', check); window.addEventListener('beastbox:session-changed', check);
    return () => { window.removeEventListener('storage', check); window.removeEventListener('beastbox:session-changed', check); };
  }, [session]);
  useEffect(() => { setRound(0); setHits(0); started.current = 0; }, [id]);
  useEffect(() => {
    if (!round) { if (marker.current) marker.current.style.left = '0%'; return; }
    let frame = 0;
    const draw = () => {
      const phase = ((performance.now() - started.current) / 900) % 1;
      if (marker.current) { marker.current.style.left = `${phase * 100}%`; marker.current.dataset.phase = phase.toFixed(4); }
      frame = requestAnimationFrame(draw);
    };
    frame = requestAnimationFrame(draw); return () => cancelAnimationFrame(frame);
  }, [round]);

  function reaction(action: Reaction) {
    if (id) window.dispatchEvent(new CustomEvent('beastbox:creature-reaction', { detail: { id, action } }));
  }
  async function commit(mutate: (draft: any) => void, action?: Reaction, message?: string, options: {allowUnsignedAdoption?:boolean}={}) {
    if (busy) return false; setBusy(true);
    try {
      const result: any = await change(mutate,options);
      if (result?.ok === false) throw Error(result.reason || 'This device could not save the change.');
      if (action) reaction(action); if (message) setStatus(message); return true;
    } catch (error) {
      setSaved(false); setStatus(error instanceof Error ? error.message : 'This device could not save the change.'); return false;
    } finally { setBusy(false); }
  }
  async function meet() {
    if (beast?.qbeast) { router.push('/spark/index.html'); return; }
    const genome = buildGenome({ focus: 40, calm: 40, spark: 20 }, recorded[0], null);
    await commit(draft => { adoptBeast(draft, genome, name || 'Moss'); }, undefined, 'Your companion is ready. Give it a name and a gentle pet.',{allowUnsignedAdoption:true});
  }
  async function rename(event: React.FormEvent) {
    event.preventDefault(); const clean = name.replace(/[^\w .'-]/g, '').trim().slice(0, 24);
    if (!beast || !clean) { setStatus(beast ? 'Choose a name of up to 24 characters.' : 'Meet a beast before naming it.'); return; }
    if (await commit(draft => { nameBeast(draft, clean); }, 'name', `Named ${clean}. Saved on this device.`)) setName('');
  }
  async function act(kind: 'pet' | 'feed' | 'rest') {
    await commit(draft => { care(draft, kind); }, kind, kind === 'pet' ? 'A soft pet. Your bond grew.' : kind === 'feed' ? 'A snack and a little energy.' : 'A quiet moment to recover.');
  }
  async function spark() {
    if (!beast || busy) return;
    if (!started.current) started.current = performance.now();
    const phase = ((performance.now() - started.current) / 900) % 1;
    const hit = phase > 0.35 && phase < 0.65;
    const nextHits = hits + (hit ? 1 : 0), nextRound = round + 1; reaction('train');
    if (nextRound >= 6) {
      const ok = await commit(draft => { train(draft, nextHits, 6); }, undefined, `Training complete · ${nextHits}/6 hits. Experience follows your timing.`);
      if (ok) { setHits(0); setRound(0); started.current = 0; } return;
    }
    setHits(nextHits); setRound(nextRound);
  }
  async function speak(event: React.FormEvent) {
    event.preventDefault(); const text = line.trim(); if (!text || !beast) return;
    if (await commit(draft => { talkAndGrow(draft, text); }, 'talk', 'Your local pattern memory kept the exchange.')) setLine('');
  }
  async function save() {
    if (!beast) return;
    await commit(draft => { recordCreatureExperience(draft, {kind:'save',place:draft.beast.behavior?.events?.at(-1)?.place||'grove'}); }, 'save', 'Saved on this device. Download a device journey to carry care and memory elsewhere.');
  }
  function saveQbeast() {
    if (!beast) return;
    const notes = (session?.chat || []).map((turn: { role: string; text: string }) => `${turn.role}: ${turn.text}`);
    download(beast.qbeast ? serializeQbeast(beast.qbeast) : exportQbeast(beast.genome, mind, beast.xp, notes), `${shownName(beast)}.qbeast`, 'application/json');
    setStatus(beast.qbeast ? 'Downloaded this exact verified identity. Use a device journey to carry care, memory and behavior.' : 'Downloaded QBEAST1 with public pattern memory and chat. Host progress stays unsigned.');
  }
  async function saveJourney() {
    try {
      const entries = await loadDeviceJourneyRuns();
      const text = serializeDeviceJourney(session, new Map(entries.map(run => [run.key, run])));
      download(text, `${shownName(beast)}.beastjourney`, 'application/json');
      setStatus('Device journey downloaded: your name, care, memory and behavior, plus the same QBEAST. Unsigned local state.');
    } catch (error) { setStatus(error instanceof Error ? error.message : 'The journey could not be downloaded.'); }
  }
  function saveLcx1() {
    if (!beast) return; if (beast.qbeast) { router.push('/sol-game'); return; }
    download(exportLcx1(beast.genome, beast.xp), `${shownName(beast)}.sav`, 'application/octet-stream');
    window.dispatchEvent(new CustomEvent('beastbox:lcx1-ready'));
    setStatus('Downloaded an LCX1 mailbox and its earned local growth inside a Lost COSMOS SRAM save.');
  }
  function saveRetainedNative() {
    try {
      const bytes = retainedNativeBytes(beast); if (bytes) download(bytes, `${shownName(beast)}-unverified-native.sav`, 'application/octet-stream');
      setStatus('Retained native save downloaded. Restore it through LOST COSMOS; this unsigned file did not grant a native stage.');
    } catch (error) { setStatus(error instanceof Error ? error.message : 'Native artifact could not be read.'); }
  }
  async function onImport(list: FileList | null) {
    const item = list?.[0]; if (!item) return;
    try {
      if (item.size > DEVICE_JOURNEY_LIMIT) throw Error('Choose a device journey under 2 MiB or a creature file under 512 KB.');
      const bytes = new Uint8Array(await item.arrayBuffer()), head = String.fromCharCode(...bytes.subarray(0, 4));
      const mailbox = bytes.length > 24836 ? String.fromCharCode(...bytes.subarray(24832, 24836)) : '';
      if (head === 'LCX1' || mailbox === 'LCX1') {
        if (beast?.qbeast) { router.push('/sol-game'); return; }
        const cage = importLcx1(bytes), genome = buildGenome({ focus: cage.focus, calm: cage.calm, spark: cage.spark }, recorded[0], null);
        await commit(draft => { adoptBeast(draft, genome, cage.callsign || 'Beast'); draft.beast.xp = cage.xp; draft.beast.stage = stageFromXp(cage.xp); }, undefined, `Imported LCX1 traits and ${cage.xp} local XP.`,{allowUnsignedAdoption:true}); return;
      }
      const text = new TextDecoder().decode(bytes), snapshot = JSON.parse(text);
      if (snapshot.schema === DEVICE_JOURNEY_SCHEMA) {
        const entries = await loadDeviceJourneyRuns(), journey = readDeviceJourney(text, new Map(entries.map(run => [run.key, run])));
        await withSparkLock(() => restoreDeviceJourney(localStorage, journey)); selected();
        window.dispatchEvent(new CustomEvent('beastbox:genesis-selected', { detail: journey.snapshot.profile }));
        setStatus('Device journey restored on this device. Native artifacts remain unsigned; current cartridge progress stays with the host.'); return;
      }
      if (item.size > 524288) throw Error('Choose a public creature file under 512 KB.');
      if (snapshot.events?.[0]?.payload?.source_ref === 'public:spark-beasts') {
        const entries = await loadDeviceJourneyRuns(), replay = replaySpark(text, new Map(entries.map(run => [run.key, run])));
        await withSparkLock(() => selectSpark(localStorage, replay.gen, { snapshot: replay.snapshot })); selected();
        window.dispatchEvent(new CustomEvent('beastbox:genesis-selected', { detail: replay.snapshot.profile }));
        setStatus('Restored the exact Spark identity and its care already saved on this device.'); return;
      }
      const imported = importQbeast(text), run = recorded.find(entry => entry.key === imported.card.run) || recorded[0], genome = buildGenome(imported.card.traits, run, null);
      await commit(draft => {
        adoptBeast(draft, genome, imported.card.name); draft.beast.xp = imported.xp; draft.beast.stage = stageFromXp(imported.xp);
        if (imported.mind) draft.mind = imported.mind;
        if (imported.notes?.length) draft.chat = imported.notes.slice(-80).map((note: string) => ({ role: note.startsWith('you:') ? 'you' : 'beast', text: note.replace(/^(you|beast):\s*/, '') }));
      }, undefined, 'Imported the .qbeast file with its public pattern weights and notes.',{allowUnsignedAdoption:true});
    } catch (error) { setStatus(error instanceof Error ? error.message : 'That companion file could not be read.'); }
    finally { if (file.current) file.current.value = ''; }
  }

  return <section className={css.deck} aria-label="Shared beast care" data-care-deck data-creature-id={id || ''}>
    <span className={css.flag}>YOUR LITTLE COMPANION</span>
    <h2>A name. A soft pet. <em>A shared journey.</em></h2>
    <p className={css.lede}>Start with a name, then pet and train together. Your beast keeps its care, memory and small discoveries on this device.</p>
    {!ready || !session ? <p className={css.note}>{ready ? storageStatus : 'Opening the local save…'}</p> : <div className={`${css.grid} ${!sprite ? css.withoutSprite : ''}`}>
      {sprite ? <div className={css.stage}>
        {beast ? <PixelBeast publicSpark={!!beast.qbeast} genome={beast.genome} stage={beast.qbeast ? beast.nativeStage || 1 : beast.stage} pose={pose} emote={emote} reduced={reduced} label={`${shownName(beast)}, stage ${beast.stage}, ${visual}`} /> : <p className={css.note}>Your companion is waiting.</p>}
        <span className={css.caption}>{beast ? shownName(beast) : 'MEET YOUR BEAST'}</span>
      </div> : null}
      <div className={css.panel}>
        <ol className={css.steps} aria-label="First minute together">
          {[['Name', named], ['Pet', petted], ['Train', trained], ['Save', saved]].map(([label, done], index) => <li key={String(label)} data-complete={String(done)}><span>{done ? '✓' : index + 1}</span>{label}</li>)}
        </ol>
        <form onSubmit={event => void rename(event)}>
          <label className={css.nameLabel}>A name for your beast<input aria-label="Beast name" value={name} maxLength={24} onChange={event => setName(event.target.value)} placeholder={beast ? shownName(beast) : 'A little name'} /></label>
          <button type="submit" disabled={!beast || busy}>Name</button><button type="button" onClick={() => void meet()} disabled={busy}>Meet a spark beast</button>
        </form>
        <div className={css.row}>
          <button className={css.primary} type="button" onClick={() => void act('pet')} disabled={!beast || busy}>Pet</button>
          <button type="button" onClick={() => void spark()} disabled={!beast || busy}>Train · {round}/6</button>
          <button type="button" onClick={() => void save()} disabled={!beast || busy}>Save on this device</button>
          <button type="button" onClick={() => void act('feed')} disabled={!beast || busy}>Feed</button><button type="button" onClick={() => void act('rest')} disabled={!beast || busy}>Rest</button>
        </div>
        <div className={css.training} hidden={!round}>
          <div className={css.bar} aria-hidden="true"><i /><b ref={marker} data-training-marker /></div>
          <p className={css.note}>Tap Train in the bright window. Six taps, 900 ms per pass. {hits} hits so far.</p>
        </div>
        <p className={css.saved} data-care-saved={saved ? 'true' : 'false'}>{saved ? '✓ Saved on this device' : 'Local save has not been verified'} <span>· Care XP {beast?.xp || 0} · Bond {beast?.bond || 0} · Energy {Math.round(beast?.energy ?? 0)}</span></p>
        {chat ? <form onSubmit={event => void speak(event)}>
          <label htmlFor="care-talk">Tell your companion something</label><textarea id="care-talk" value={line} maxLength={400} onChange={event => setLine(event.target.value)} placeholder="A short phrase to remember…" />
          <button type="submit" disabled={!beast || busy}>Learn this phrase</button>
        </form> : null}
        {chat && session.chat.length ? <div className={css.reply} role="status"><strong>Local pattern companion</strong><p>{session.chat[session.chat.length - 1]?.text}</p></div> : null}
        <p className={css.note} role="status" data-care-status>{status}</p>
        <div className={css.row}><Link href="/beast-cage/play">Adventure together</Link><Link href="/beast-cage/go">Open the field</Link></div>
        <details className={css.details}>
          <summary>Carry your beast · files and native game</summary>
          <p className={css.note}>A device journey carries unsigned care, chat, pattern memory and behavior with the same verified identity. A .qbeast carries that exact identity. Native evolution is earned through LOST COSMOS.</p>
          <div className={css.row}>
            <button type="button" onClick={() => void saveJourney()} disabled={!beast?.qbeast}>Download device journey</button><button type="button" onClick={saveQbeast} disabled={!beast}>Download .qbeast</button>
            <button type="button" onClick={saveLcx1} disabled={!beast}>Download LCX1 save</button><button type="button" onClick={() => file.current?.click()}>Import cage or journey</button>
          </div>
          {beast?.journeyNative ? <p className={css.note}>Retained native data is unsigned and unverified. {(beast.journeyNative.game?.native_save || beast.journeyNative.retained?.some((item: any) => item.game?.native_save)) ? <button type="button" onClick={saveRetainedNative}>Download retained native .sav</button> : null} <Link href="/sol-game">Restore through LOST COSMOS →</Link></p> : null}
        </details>
        <details className={css.details}>
          <summary>See local memory and the recorded recipe</summary>
          <div className={css.stats}><span>Stage {beast?.stage || 1}</span><span>Mind steps {mind?.steps || 0}</span><span>Behavior ticks {beast?.behavior?.tick || 0}</span></div>
          <div className={css.weights}><WeightGrid weights={mind?.weights} steps={mind?.steps || 0} /><p className={css.note}>Word pairs grow these on-device Hebbian weights. This is pattern memory. The RAWRPHØS guest panel and selected Brain Bay model keep their own weights.</p></div>
          <p className={css.note}>{beast?.qbeast ? `QBEAST ${id} · Care XP does not grant native evolution.` : 'Legacy local stages arrive at 40 and 120 XP.'} Recorded seed {beast?.seed}. A selected model is not trained by this companion.</p>
        </details>
        {petted && trained && saved ? <button type="button" className={css.support} onClick={() => window.dispatchEvent(new Event('beastbox:open-support'))}>Keep this little world growing · optional support</button> : null}
        <input ref={file} type="file" accept=".beastjourney,.qbeast,.json,.sav,.lcx1,application/json" hidden onChange={event => void onImport(event.target.files)} />
      </div>
    </div>}
  </section>;
}
