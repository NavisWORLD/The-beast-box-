'use client';
import { useState } from 'react';
import { generateCreature, type CreatureProfile } from '../lib/creature-profile';
import { bytesToSeed, loadRecordedRuns, revealRecordedBeast, sealedMachine } from '../lib/companion/spark-machine.mjs';
import css from './spark-field.module.css';

type Genome = { seed: string; names: Record<number, string> };
type Revealed = { profile: CreatureProfile; genome: Genome; name: string };

export default function SparkMachine({ onReveal }: { onReveal: (result: Revealed) => void }) {
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const sealed = sealedMachine();

  async function pull() {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const bytes = new Uint8Array(16);
      crypto.getRandomValues(bytes);
      const seed = bytesToSeed(bytes);
      const profile = generateCreature(seed, 'nebula');
      const runs = await loadRecordedRuns((input: string, init?: RequestInit) => fetch(input, init));
      const revealed = revealRecordedBeast(profile, runs);
      if (!revealed.ok || !revealed.genome) throw new Error(revealed.reason || 'The spark machine did not return a beast');
      setName(revealed.name);
      onReveal({ profile, genome: revealed.genome as unknown as Genome, name: revealed.name });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The spark machine could not pull');
    } finally {
      setBusy(false);
    }
  }

  return <section className={css.sealed} aria-label="Spark machine" data-spark-machine={name ? 'revealed' : 'sealed'}>
    <h3>Spark machine</h3>
    {name ? <p role="status">A {name} came out of the spark machine. It is saved as this browser&apos;s beast.</p> : <p>The spark machine stays sealed. It does not show what will come out.</p>}
    <p>The pull uses recorded IBM runs, including the public generator shards. {sealed.sealed ? 'No names are listed beforehand.' : ''}</p>
    <button type="button" className={css.pull} disabled={busy} onClick={() => void pull()}>{busy ? 'Pulling…' : 'Pull the spark machine'}</button>
    {error ? <p role="status">{error}</p> : null}
  </section>;
}
