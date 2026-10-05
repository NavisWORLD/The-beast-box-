'use client';
import { useEffect, useRef, useState } from 'react';
import { catalogRoster, STAGE_MARK } from '../lib/companion/field-roster.mjs';
import { expandCompactRun } from '../lib/companion/spark-machine.mjs';
import { blit, renderBeast, SPRITE } from '../public/spark/draw.mjs';
import css from './spark-field.module.css';

type StageCard = { stage: number; mark: string; name: string };
type Genome = { seed: string; names: Record<number, string>; [key: string]: unknown };
type CreatureCard = { kind: string; body: string; island: string; stages: StageCard[]; genome: Genome };
type RareCard = { kind: string; key: string; num_bits: number; name: string; body: string; genome: Genome };
type Catalog = {
  creatures: CreatureCard[];
  charlet: CreatureCard & { name: string };
  rares: RareCard[];
};
type Choice = { name: string; genome: Genome };

function RosterCard({ genome, stage, name, detail, rare = false, onChoose }:{
  genome: Genome; stage: 1|2|3; name: string; detail: string; rare?: boolean; onChoose:()=>void;
}){
  const canvas=useRef<HTMLCanvasElement>(null);
  useEffect(()=>{
    const node=canvas.current;
    if(!node)return;
    const ctx=node.getContext('2d');
    if(!ctx)return;
    const scale=3;
    node.width=SPRITE*scale;node.height=SPRITE*scale;
    blit(ctx,renderBeast(genome,stage,'open'),0,0,scale);
  },[genome,stage]);
  return <button type="button" className={css.rosterCard} data-roster-card={rare?'rare':'core'} onClick={onChoose}>
    <canvas ref={canvas} className={css.rosterCanvas} aria-label={`${name} stage ${STAGE_MARK[stage]} sprite`}/>
    <strong>{name}</strong><span>{detail}</span>{rare?<small>RARE · RECORDED 12-BIT SEED</small>:null}
  </button>;
}

export default function SparkFieldRoster({ onChoose }: { onChoose: (choice: Choice) => void }) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [stage, setStage] = useState<1 | 2 | 3>(1);
  const [error, setError] = useState('');

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

  return <section className={css.block} aria-label="Spark Beast roster">
    <div className={css.rosterHead}><div><h3>All Spark Beasts</h3><p>Every core body family, all three visual stages, Charlet, and the 12 recorded rare forms.</p></div>
      <div className={css.stages} role="group" aria-label="Evolution stage preview">
        {([1,2,3] as const).map(value=><button key={value} type="button" aria-pressed={stage===value} onClick={()=>setStage(value)}>Stage {STAGE_MARK[value]}</button>)}
      </div>
    </div>
    <p className={css.previewNote}>Stage buttons preview art only. Earned evolution still comes from game progression.</p>
    {error?<p role="status">{error}</p>:null}
    {!catalog&&!error?<p>Loading the recorded roster…</p>:null}
    {catalog?<>
      <div className={css.rosterGrid} aria-label="Core Spark Beast families">
        {catalog.creatures.map(creature=>{
          const shown=creature.stages.find(item=>item.stage===stage)||creature.stages[0];
          return <RosterCard key={creature.body} genome={creature.genome} stage={stage} name={shown.name}
            detail={`${creature.body} · ${creature.island}`}
            onChoose={()=>onChoose({name:shown.name,genome:creature.genome})}/>;
        })}
        {(()=>{
          const shown=catalog.charlet.stages.find(item=>item.stage===stage)||catalog.charlet.stages[0];
          const name=stage===1?catalog.charlet.name:shown.name;
          return <RosterCard genome={catalog.charlet.genome} stage={stage} name={name}
            detail="Charlet line · Cinder Drift" onChoose={()=>onChoose({name,genome:catalog.charlet.genome})}/>;
        })()}
      </div>
      <h4 className={css.rareTitle}>Recorded rare forms · 12</h4>
      <div className={css.rosterGrid} aria-label="Rare Spark Beasts">
        {catalog.rares.map(rare=>{
          const name=rare.genome.names?.[stage]||rare.name;
          return <RosterCard key={rare.key} genome={rare.genome} stage={stage} name={name}
            detail={`${rare.body} · ${rare.key.split(':')[0]}`} rare
            onChoose={()=>onChoose({name,genome:rare.genome})}/>;
        })}
      </div>
    </>:null}
  </section>;
}
