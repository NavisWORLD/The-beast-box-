'use client';
import { useEffect, useRef, useState } from 'react';
import { catalogRoster, STAGE_MARK } from '../lib/companion/field-roster.mjs';
import { expandCompactRun } from '../lib/companion/spark-machine.mjs';
import { blit, renderBeast, SPRITE } from '../public/spark/draw.mjs';
import css from './spark-field.module.css';

type StageCard = { stage: number; mark: string; name: string };
type CreatureCard = { kind: string; body: string; island: string; stages: StageCard[]; genome: { seed: string; names: Record<number, string> } };
type RareCard = { kind: string; key: string; num_bits: number; name: string; body: string; genome: { seed: string; names: Record<number, string> } };
type Catalog = {
  creatures: CreatureCard[];
  charlet: CreatureCard & { name: string };
  rares: RareCard[];
};

type Choice = { name: string; genome: { seed: string; names: Record<number, string> } };

export default function SparkFieldRoster({ onChoose }: { onChoose: (choice: Choice) => void }) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [stage, setStage] = useState<1 | 2 | 3>(1);
  const [error, setError] = useState('');
  const [picked, setPicked] = useState<Choice | null>(null);
  const sprite = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const response = await fetch('/spark/runs.json', { cache: 'force-cache' });
      if (!response.ok) throw new Error('Recorded roster table unavailable');
      const table = await response.json() as { runs?: Record<string, unknown>[] };
      const runs = (table.runs || []).map((row) => expandCompactRun(row));
      if (!cancelled) setCatalog(catalogRoster(runs) as unknown as Catalog);
    })().catch((err) => {
      if (!cancelled) setError(err instanceof Error ? err.message : 'Roster unavailable');
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const genome = picked?.genome;
    const canvas = sprite.current;
    if (!genome || !canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const scale = 3;
    canvas.width = SPRITE * scale;
    canvas.height = SPRITE * scale;
    blit(ctx, renderBeast(genome, stage, 'open'), 0, 0, scale);
  }, [picked, stage]);

  return <section className={css.block} aria-label="Spark Beast roster">
    <h3>Roster</h3>
    <p>Every Spark Beast body, stages I, II, and III, Charlet, and the 12 rares from recorded 12-bit runs.</p>
    <div className={css.stages} role="group" aria-label="Evolution stage">
      {([1, 2, 3] as const).map((value) => <button key={value} type="button" aria-pressed={stage === value} onClick={() => setStage(value)}>Stage {STAGE_MARK[value]}</button>)}
    </div>
    {error ? <p role="status">{error}</p> : null}
    {!catalog && !error ? <p>Loading the recorded roster…</p> : null}
    {catalog ? <>
      <canvas ref={sprite} data-roster-sprite="true" className={css.sprite} aria-label={picked ? `${picked.name} stage ${STAGE_MARK[stage]}` : 'Choose a Spark Beast'} />
      <div className={css.list}>
        {catalog.creatures.map((creature) => {
          const shown = creature.stages.find((item) => item.stage === stage) || creature.stages[0];
          return <button key={creature.body} type="button" onClick={() => { const choice = { name: shown.name, genome: creature.genome }; setPicked(choice); onChoose(choice); }}>{creature.body} · Stage {shown.mark} · {shown.name}</button>;
        })}
        <button type="button" onClick={() => { const shown = catalog.charlet.stages.find((item) => item.stage === stage) || catalog.charlet.stages[0]; const choice = { name: stage === 1 ? catalog.charlet.name : shown.name, genome: catalog.charlet.genome }; setPicked(choice); onChoose(choice); }}>Charlet · Stage {STAGE_MARK[stage]} · {stage === 1 ? catalog.charlet.name : catalog.charlet.stages.find((item) => item.stage === stage)?.name}</button>
        {catalog.rares.map((rare) => <button key={rare.key} type="button" onClick={() => { const choice = { name: rare.name, genome: rare.genome }; setPicked(choice); onChoose(choice); }}>Rare · {rare.name}</button>)}
      </div>
    </> : null}
  </section>;
}
