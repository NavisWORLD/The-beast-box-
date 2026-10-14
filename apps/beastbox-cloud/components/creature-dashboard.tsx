'use client';
import GrowInCosmos from './grow-in-cosmos';
import {shownName} from '../lib/companion/session.mjs';
import type {CosmosProfile} from '../public/spark/cosmos-profile.mjs';

/** Every saved creature automatically gets its own dashboard: its folder, brain
 * state and growth loop. Everything here is read from the creature's own saved
 * record on this device. Cloud growth stays one explicit tap (GrowInCosmos);
 * nothing is written to the cloud until the player taps it. */
export default function CreatureDashboard({beast,cosmosProfile}:{beast:any;cosmosProfile:CosmosProfile|null}){
 if(!beast?.qbeast?.profile?.id)return null;
 const id=beast.qbeast.profile.id,name=shownName(beast),g=beast.localGrowth||{};
 const steps=Array.isArray(g.memory_steps)?g.memory_steps.length:Number(g.memory_steps)||0;
 return <section className="creature-dashboard" id="my-creature" data-creature-dashboard={id} aria-labelledby="creature-dashboard-title">
  <h2 id="creature-dashboard-title">✦ {name}&apos;s home base</h2>
  <p className="creature-dashboard-lede">Made automatically for {name}. Lives on this device until you choose cloud growth.</p>
  <details open><summary>📁 Folder</summary>
   <p>Saved on this device as <code>{id}</code>.</p>
   <p data-advanced-only>Cloud folder (only after you opt in): <code>cosmos/beasts/{id}/</code></p>
  </details>
  <details><summary>🧠 Brain state</summary>
   <ul><li>Mood: {beast.mood||g.mood||'calm'}</li><li>XP {Number(beast.xp)||0} · Bond {Number(beast.bond)||0} · Energy {Number(beast.energy)||0}</li>
    <li>Memories learned: {steps}</li><li data-advanced-only>Local model: {typeof g.model==='string'?g.model:g.model?.name||'browser-local'} · stage {beast.stage||1}</li></ul>
  </details>
  <details><summary>🌱 Growth loop</summary>
   <p>{name} grows here every time you play, feed and talk. To keep growing while you&apos;re away, tap once below.</p>
   <GrowInCosmos profile={cosmosProfile}/>
  </details>
 </section>;
}
