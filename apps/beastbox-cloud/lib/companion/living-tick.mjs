/**
 * LIVING TICK — bounded scheduler over the existing behavior core.
 *
 * This module does NOT introduce a second behavior engine, dashboard, or
 * creature state store. It only plans and applies a bounded number of steps
 * through the existing `advanceCreature()` / `stepBehavior()` contract in
 * behavior.mjs, with:
 *
 * - one living epoch bound to the creature's genesis seed + QBEAST id
 * - elapsed-time catch-up with explicit caps (no invented adventures)
 * - idempotent plans keyed to the behavior tick they were planned from
 * - classical-only provenance labeling (never hardware, never a fresh QVM run)
 *
 * Pure except for the step application itself, which mutates the passed
 * session exactly the way the existing callers do. Storage stays with the
 * caller (use updateDeviceSession for conditional writes).
 */
import {advanceCreature} from './behavior.mjs';

export const LIVING_TICK_SCHEMA='beastbox-living-tick-v1';
/** Provenance marker attached to living-tick plans. Classical rules only. */
export const LIVING_SOURCE='classical-behavior-tick';
export const LIVING_DEFAULTS=Object.freeze({maxSteps:8,maxCatchUpMs:120000,intervalMs:15000});

const fnv=text=>{let h=2166136261;for(const c of String(text))h=Math.imul(h^c.charCodeAt(0),16777619);return (h>>>0).toString(16).padStart(8,'0');};
const seedOf=beast=>String(beast?.genome?.seed||beast?.seed||'');
const idOf=beast=>String(beast?.qbeast?.profile?.id||beast?.id||'unclaimed');

/** Domain-separated epoch binding this living record to one creature lineage. */
export function livingEpochFor(beast){
 return fnv(`beastbox:living-tick:v1:${seedOf(beast)}:${idOf(beast)}`);
}

export function freshLivingTick(beast,nowIso=null){
 const at=nowIso||new Date().toISOString();
 return {
  schema:LIVING_TICK_SCHEMA,
  epoch:livingEpochFor(beast),
  source:LIVING_SOURCE,
  behaviorTick:Number.isSafeInteger(beast?.behavior?.tick)?beast.behavior.tick:0,
  lastTrustedAt:at,
  accumulatedMs:0,
 };
}

/** Reject foreign or corrupted living records; never mix lineages. */
export function validateLivingTick(living,beast){
 const epoch=livingEpochFor(beast);
 const ok=living?.schema===LIVING_TICK_SCHEMA
  &&living.epoch===epoch
  &&living.source===LIVING_SOURCE
  &&Number.isSafeInteger(living.behaviorTick)&&living.behaviorTick>=0
  &&Number.isSafeInteger(living.accumulatedMs)&&living.accumulatedMs>=0
  &&Number.isFinite(Date.parse(living.lastTrustedAt));
 return ok?living:freshLivingTick(beast);
}

/**
 * Plan a bounded number of behavior steps for the elapsed wall-clock time.
 * Pure: no storage writes, no behavior mutation. Catch-up is capped so a
 * long absence produces at most maxSteps ordinary steps — never a backlog
 * of invented conversations, quests, or sensor readings.
 */
export function planLivingSteps(living,beast,{nowIso=null,maxSteps=LIVING_DEFAULTS.maxSteps,maxCatchUpMs=LIVING_DEFAULTS.maxCatchUpMs,intervalMs=LIVING_DEFAULTS.intervalMs}={}){
 const valid=validateLivingTick(living,beast);
 const nowMs=Date.parse(nowIso||new Date().toISOString());
 if(!Number.isFinite(nowMs))throw Error('living-tick: invalid now timestamp');
 const lastMs=Date.parse(valid.lastTrustedAt);
 const rawElapsed=nowMs-lastMs;
 if(rawElapsed<=0)return {epoch:valid.epoch,source:LIVING_SOURCE,baseTick:valid.behaviorTick,baseAt:valid.lastTrustedAt,targetAt:new Date(nowMs).toISOString(),steps:0,capped:false,reason:'no-elapsed-time'};
 const elapsed=Math.min(rawElapsed,Math.max(0,maxCatchUpMs));
 const steps=Math.min(Math.max(0,maxSteps),Math.floor(elapsed/Math.max(1,intervalMs)));
 return {
  epoch:valid.epoch,
  source:LIVING_SOURCE,
  baseTick:valid.behaviorTick,
  baseAt:valid.lastTrustedAt,
  targetAt:new Date(nowMs).toISOString(),
  steps,
  capped:rawElapsed>elapsed||steps<Math.floor(elapsed/Math.max(1,intervalMs)),
  reason:steps===0?'interval-not-reached':'elapsed-time',
 };
}

/**
 * Apply a plan through the existing behavior core. Idempotent: a plan only
 * applies when the session's behavior tick still matches the tick it was
 * planned from, so duplicate delivery applies zero steps.
 *
 * environmentFactory(session, stepIndex) must be deterministic for replay.
 * Returns the next living record alongside the step count.
 */
export function applyLivingSteps(session,living,plan,{environmentFactory=null}={}){
 const beast=session?.beast;
 if(!beast)return {ok:false,reason:'no beast'};
 const valid=validateLivingTick(living,beast);
 if(!plan||plan.epoch!==valid.epoch||plan.source!==LIVING_SOURCE)return {ok:false,reason:'plan-epoch-mismatch'};
 const currentTick=Number.isSafeInteger(beast?.behavior?.tick)?beast.behavior.tick:0;
 if(currentTick!==plan.baseTick||valid.behaviorTick!==plan.baseTick)return {ok:true,stepsApplied:0,behaviorTick:currentTick,duplicate:true,living:valid};
 let applied=0;
 for(let i=0;i<plan.steps;i++){
  const env=typeof environmentFactory==='function'?environmentFactory(session,i):{};
  const result=advanceCreature(session,env);
  if(!result?.ok)break;
  applied++;
 }
 const next={
  ...valid,
  behaviorTick:Number.isSafeInteger(beast?.behavior?.tick)?beast.behavior.tick:plan.baseTick,
  lastTrustedAt:plan.targetAt,
  accumulatedMs:0,
 };
 return {ok:true,stepsApplied:applied,behaviorTick:next.behaviorTick,duplicate:false,living:next};
}
