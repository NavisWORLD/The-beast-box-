'use client';
import { useRef, useState } from 'react';
import Link from 'next/link';
import { care, nameBeast, talkAndGrow, train } from '../lib/companion/adventure.mjs';
import { exportLcx1, exportQbeast, importLcx1, importQbeast } from '../lib/companion/cage.mjs';
import { adoptBeast, stageFromXp, shownName } from '../lib/companion/session.mjs';
import { buildGenome } from '../lib/companion/spark/genome.mjs';
import runs from '../lib/companion/spark/runs.json';
import { useBeastSession } from './beast-session';
import PixelBeast from './pixel-beast';
import {serializeQbeast} from '../public/spark/qbeast.mjs';
import {replaySpark,selectSpark,withSparkLock} from '../public/spark/identity.mjs';
import {loadSparkRuns} from '../public/spark/runs.mjs';
import WeightGrid from './weight-grid';
import css from './beast-care-deck.module.css';

const recorded = runs as Array<{ key: string; backend: string; job_id: string; pub_index: number; num_bits: number; shots: number; counts: Record<string, number> }>;

function download(bytes: BlobPart, name: string, type: string) {
  const url = URL.createObjectURL(new Blob([bytes], { type }));
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function BeastCareDeck({ chat = true, sprite = true }: { chat?: boolean; sprite?: boolean }) {
  const { ready, session, change } = useBeastSession();
  const [name, setName] = useState('');
  const [line, setLine] = useState('');
  const [status, setStatus] = useState('');
  const [hits, setHits] = useState(0);
  const [round, setRound] = useState(0);
  const started = useRef(0);
  const file = useRef<HTMLInputElement>(null);
  const beast = session?.beast;
  const mind = session?.mind;

  function meet() {
    if(beast?.qbeast){window.location.href='/spark/index.html';return;}
    const run = recorded[0];
    const genome = buildGenome({ focus: 40, calm: 40, spark: 20 }, run, null);
    change((draft) => { adoptBeast(draft, genome, name || 'Moss'); }, {allowUnsignedAdoption:true});
    setStatus('A spark beast is on this device. Pattern memory starts empty.');
  }

  function act(kind: 'pet' | 'feed' | 'rest') {
    change((draft) => { care(draft, kind); });
  }

  function spark() {
    if (!started.current) started.current = performance.now();
    const phase = ((performance.now() - started.current) / 900) % 1;
    const hit = phase > 0.35 && phase < 0.65;
    const nextHits = hits + (hit ? 1 : 0);
    const nextRound = round + 1;
    if (nextRound >= 6) {
      change((draft) => { train(draft, nextHits, 6); });
      setHits(0);
      setRound(0);
      started.current = 0;
      setStatus(hit ? 'Spark landed. Experience was earned from the hits.' : 'Round finished. Experience follows the hits, not a random prize.');
      return;
    }
    setHits(nextHits);
    setRound(nextRound);
  }

  function speak(event: React.FormEvent) {
    event.preventDefault();
    const text = line.trim();
    if (!text) return;
    change((draft) => { talkAndGrow(draft, text); });
    setLine('');
    setStatus('On-device pattern memory answered. This is not a language model.');
  }

  function saveQbeast() {
    if (!beast) return;
    const notes = (session?.chat || []).map((turn: { role: string; text: string }) => `${turn.role}: ${turn.text}`);
    const text = beast.qbeast?serializeQbeast(beast.qbeast):exportQbeast(beast.genome, session?.mind, beast.xp, notes);
    download(text, `${shownName(beast)}.qbeast`, 'application/json');
    setStatus(beast.qbeast?'Exported this exact verified Spark identity. Care and pattern chat remain in this browser.':'Exported a QBEAST1 file with pattern memory and this chat. Host progress stays zero so the file verifies without a signing key.');
  }

  function saveLcx1() {
    if (!beast) return;
    if(beast.qbeast){window.location.href='/sol-game';return;}
    download(exportLcx1(beast.genome, beast.xp), `${shownName(beast)}.sav`, 'application/octet-stream');
    window.dispatchEvent(new CustomEvent('beastbox:lcx1-ready'));
    setStatus('Exported an LCX1 mailbox inside a Lost Cosmos SRAM save, with LCG1 growth for the earned experience.');
  }

  async function onImport(list: FileList | null) {
    const item = list?.[0];
    if (!item) return;
    try {
      if(item.size>524288)throw Error('Choose a public creature file under 512 KB.');
      const bytes = new Uint8Array(await item.arrayBuffer());
      const head = String.fromCharCode(...bytes.subarray(0, 4));
      const mailbox = bytes.length > 24836 ? String.fromCharCode(...bytes.subarray(24832, 24836)) : '';
      if (head === 'LCX1' || mailbox === 'LCX1') {
        if(beast?.qbeast){window.location.assign('/sol-game');return;}
        const cage = importLcx1(bytes);
        const genome = buildGenome({ focus: cage.focus, calm: cage.calm, spark: cage.spark }, recorded[0], null);
        change((draft) => {
          adoptBeast(draft, genome, cage.callsign || 'Beast');
          if (draft.beast) {
            draft.beast.xp = cage.xp;
            draft.beast.stage = stageFromXp(cage.xp);
          }
        }, {allowUnsignedAdoption:true});
        setStatus(`Imported LCX1 traits. Experience ${cage.xp}, stage ${stageFromXp(cage.xp)}. The sprite was rebuilt from those traits and a recorded quantum run.`);
        return;
      }
      const text=new TextDecoder().decode(bytes),snapshot=JSON.parse(text);
      if(snapshot.events?.[0]?.payload?.source_ref==='public:spark-beasts'){
        const runs=await loadSparkRuns();
        const replay=replaySpark(text,new Map(runs.map(run=>[run.key,run])));
        await withSparkLock(()=>selectSpark(localStorage,replay.gen,{snapshot:replay.snapshot}));
        window.dispatchEvent(new Event('beastbox:spark-session'));
        window.dispatchEvent(new CustomEvent('beastbox:genesis-selected',{detail:replay.snapshot.profile}));
        setStatus('Restored the exact Spark identity and its saved care state.');return;
      }
      const imported = importQbeast(text);
      const run = recorded.find((entry) => entry.key === imported.card.run) || recorded[0];
      const genome = buildGenome(imported.card.traits, run, null);
      change((draft) => {
        adoptBeast(draft, genome, imported.card.name);
        if (draft.beast) {
          draft.beast.xp = imported.xp;
          draft.beast.stage = stageFromXp(imported.xp);
        }
        if (imported.mind) draft.mind = imported.mind;
        if (imported.notes?.length) {
          draft.chat = imported.notes.slice(-80).map((note: string) => {
            const you = note.startsWith('you:');
            return { role: you ? 'you' : 'beast', text: note.replace(/^(you|beast):\s*/, '') };
          });
        }
      }, {allowUnsignedAdoption:true});
      setStatus('Imported the .qbeast file. Pattern weights and notes came back from the public memory events.');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'That cage file could not be read.');
    }
  }

  const phase = started.current ? ((performance.now() - started.current) / 900) % 1 : 0;
  return <section className={css.deck} aria-label="Shared beast care">
    <span className={css.flag}>ON THIS DEVICE · SHARED CARE</span>
    <h2>Name it. Feed it. <em>Let it learn.</em></h2>
    <p className={css.lede}>{beast?.qbeast?'Care XP and bond follow this exact QBEAST. Native evolution is earned in LOST COSMOS.':'Stage 2 arrives at 40 XP and stage 3 at 120 XP.'} {beast?.qbeast?'Bond, chat, and pattern weights stay in this browser. The .qbeast preserves the verified identity.':'Bond, chat, and pattern weights stay in this browser and in the .qbeast export.'} The RAWRPHØS guest panel above is a separate stateless model. These Hebbian weights are the on-device substrate. A selected Brain Bay model is not trained by the pet dragon.</p>
    {!ready || !session ? <p className={css.note}>Opening the local save…</p> : <div className={css.grid}>
      {sprite ? <div className={css.stage}>
        {beast ? <PixelBeast publicSpark={!!beast.qbeast} genome={beast.genome} stage={beast.stage} pose={beast.mood === 'sleep' ? 'emote' : beast.mood === 'evolve' ? 'emote' : 'idle'} emote={beast.mood === 'sleep' ? 'sleep' : beast.mood === 'evolve' ? 'evolve' : beast.mood === 'happy' ? 'happy' : 'watch'} label={`${shownName(beast)}, stage ${beast.stage}, ${beast.mood}`} /> : <p className={css.note}>No beast in this save yet.</p>}
        <span className={css.caption}>{beast ? shownName(beast).toUpperCase() : 'WAITING'}</span>
      </div> : null}
      <div className={css.panel}>
        <div className={css.stats}>
          <span>{beast ? shownName(beast) : 'Unnamed'}</span>
          <span>XP {beast?.xp || 0}</span>
          <span>Stage {beast?.stage || 1}</span>
          <span>Bond {beast?.bond || 0}</span>
          <span>Energy {beast?.energy ?? 0}</span>
          <span>Mind steps {mind?.steps || 0}</span>
        </div>
        <form onSubmit={(event) => { event.preventDefault(); change((draft) => { const named = nameBeast(draft, name); setStatus(named.ok ? `Named ${named.name}.` : 'Meet a beast before naming it.'); }); }}>
          <input aria-label="Beast name" value={name} maxLength={24} onChange={(event) => setName(event.target.value)} placeholder="A public name" />
          <button type="submit">Save name</button>
          <button type="button" onClick={meet}>Meet a spark beast</button>
        </form>
        <div className={css.row}>
          <button type="button" onClick={() => act('feed')}>Feed</button>
          <button type="button" onClick={() => act('pet')}>Pet</button>
          <button type="button" onClick={() => act('rest')}>Rest</button>
          <button type="button" onClick={spark}>Spark {round}/6</button>
        </div>
        <div className={css.bar} aria-hidden="true"><i /><b style={{ left: `${phase * 100}%` }} /></div>
        <p className={css.note}>Press Spark while the gold mark sits in the bright window. Six presses. Hits add experience.</p>
        {chat ? <form onSubmit={speak}>
          <label htmlFor="care-talk">Talk to the on-device mind</label>
          <textarea id="care-talk" value={line} maxLength={400} onChange={(event) => setLine(event.target.value)} placeholder="sunflower code is marigold" />
          <button className={css.primary} type="submit">Learn this phrase</button>
        </form> : null}
        {chat && session.chat.length ? <div className={css.reply} role="status"><strong>Pattern memory, not a model.</strong><p>{session.chat[session.chat.length - 1]?.text}</p></div> : null}
        <div className={css.weights}>
          <WeightGrid weights={mind?.weights} steps={mind?.steps || 0} />
          <p className={css.note}>Cyan cells grew from word pairs you typed. Violet cells are the other direction. Nothing here is sent to a server until you export a file yourself.</p>
        </div>
        <div className={css.row}>
          <button type="button" onClick={saveQbeast} disabled={!beast}>Download .qbeast</button>
          <button type="button" onClick={saveLcx1} disabled={!beast}>Download LCX1 save</button>
          <button type="button" onClick={() => file.current?.click()}>Import cage</button>
          <Link href="/beast-cage/play">Adventure with this beast</Link>
          <Link href="/beast-cage/go">Open the field</Link>
        </div>
        <input ref={file} type="file" accept=".qbeast,.json,.sav,.lcx1,application/json" hidden onChange={(event) => void onImport(event.target.files)} />
        <p className={css.note} role="status">{status}</p>
      </div>
    </div>}
  </section>;
}
