/**
 * Local idle-life adapter over the existing classical behavior core.
 * One creature in, one behavior state out. No second scheduler, store, or network path.
 */
import {createHash} from 'node:crypto';
import {createBehavior, stepBehavior, validateBehavior} from './behavior.mjs';
import {ARTIST_RESIDENTS, ARTIST_ORIGIN} from './artist-residents.mjs';

export const IDLE_ORIGIN_ARTIST = 'ARTIST_CLASSICAL_LOCAL';
export const IDLE_ORIGIN_RECORDED = 'RECORDED_GENESIS_SEED';
export const TICK_MS = 8000;
export const MAX_CATCHUP_TICKS = 24;

const SEED_RE = /^[a-f0-9]{16,128}$/i;
const ARTIST_BY_ID = new Map(ARTIST_RESIDENTS.map(resident => [resident.id, resident]));

export function classicalArtistSeed(id) {
  return createHash('sha256').update('artist-classical:' + id).digest('hex');
}

function artistLabel(resident) {
  const name = resident?.name || 'Resident';
  return `${name} · ${ARTIST_ORIGIN} · artist-drawn · no quantum seed · deterministic local initialization`;
}

function recordedLabel() {
  return 'The recorded seed influences behavior. Displaying it is not a fresh quantum run.';
}

function classify(creature) {
  if (!creature || typeof creature !== 'object') return null;
  const artist = ARTIST_BY_ID.get(creature.id);
  if (artist) {
    return {
      origin: IDLE_ORIGIN_ARTIST,
      seed: classicalArtistSeed(artist.id),
      name: typeof creature.name === 'string' && creature.name ? creature.name : artist.name,
      label: artistLabel(artist),
    };
  }
  const seed = creature.genome?.seed;
  if (typeof seed === 'string' && SEED_RE.test(seed)) {
    return {
      origin: IDLE_ORIGIN_RECORDED,
      seed,
      name: typeof creature.name === 'string' ? creature.name : '',
      label: recordedLabel(),
    };
  }
  return null;
}

function beastFor(creature) {
  const info = classify(creature);
  const traits = creature && typeof creature.traits === 'object' && creature.traits ? creature.traits : {};
  const energy = creature && creature.energy != null ? creature.energy : 80;
  return {genome: {seed: info ? info.seed : '', inputs: {traits}}, energy};
}

function clockAt(life) {
  const at = life?.lifeClock?.lastAt;
  return typeof at === 'number' && Number.isFinite(at) ? at : 0;
}

function eventIdOk(eventId) {
  return typeof eventId === 'string' && eventId.length >= 8 && eventId.length <= 120;
}

export function createIdleLife(creature, now = 0) {
  const info = classify(creature);
  if (!info) return {ok: false, reason: 'NO_AUTHORIZED_INITIALIZER'};
  const behavior = createBehavior(beastFor(creature));
  const life = {
    ...behavior,
    idleOrigin: info.origin,
    idleLabel: info.label,
    creatureId: creature.id,
    creatureName: info.name,
    lifeClock: {lastAt: typeof now === 'number' && Number.isFinite(now) ? now : 0},
    appliedEventIds: [],
    remoteConsent: false,
    remoteStatus: 'LOCAL_ONLY',
  };
  return {ok: true, life};
}

export function applyIdleTick(life, creature, environment, eventId) {
  if (!eventIdOk(eventId)) return {ok: false, reason: 'BAD_EVENT_ID', life};
  const applied = Array.isArray(life?.appliedEventIds) ? life.appliedEventIds : [];
  if (applied.includes(eventId)) return {ok: true, duplicate: true, life};
  const beast = beastFor(creature);
  const next = stepBehavior(life, beast, environment || {}).state;
  if (!life || next.seed !== life.seed || next.tick !== life.tick + 1) {
    return {ok: false, reason: 'BEHAVIOR_REJECTED', life};
  }
  next.idleOrigin = life.idleOrigin;
  next.idleLabel = life.idleLabel;
  next.creatureId = life.creatureId;
  next.creatureName = life.creatureName;
  next.remoteConsent = life.remoteConsent;
  next.remoteStatus = life.remoteStatus;
  next.lifeClock = {lastAt: clockAt(life)};
  next.appliedEventIds = [...applied, eventId].slice(-48);
  if (Array.isArray(next.events) && next.events.length) next.events.at(-1).eventId = eventId;
  return {ok: true, duplicate: false, life: next};
}

function remoteAfter(life, consent) {
  if (life.idleOrigin === IDLE_ORIGIN_ARTIST) {
    return {remoteConsent: false, remoteStatus: 'LOCAL_ONLY'};
  }
  if (consent === true && life.idleOrigin === IDLE_ORIGIN_RECORDED) {
    return {remoteConsent: true, remoteStatus: 'DEFER_EXISTING_WORKER'};
  }
  if (consent === false && life.remoteConsent === true) {
    return {remoteConsent: false, remoteStatus: 'BLOCKED_NO_CONSENT'};
  }
  return {
    remoteConsent: consent === false ? false : Boolean(life.remoteConsent),
    remoteStatus: 'LOCAL_ONLY',
  };
}

export function catchUpIdleLife(life, creature, {now, environment, consent} = {}) {
  const baseAt = clockAt(life);
  const at = typeof now === 'number' && Number.isFinite(now) ? now : baseAt;
  const elapsed = Math.max(0, at - baseAt);
  const rawTicks = Math.floor(elapsed / TICK_MS);
  const steps = Math.min(MAX_CATCHUP_TICKS, rawTicks);
  const omitted = Math.max(0, rawTicks - steps);
  const startingTick = Number.isSafeInteger(life?.tick) ? life.tick : 0;
  const creatureId = life?.creatureId ?? creature?.id;
  let current = life;
  let applied = 0;
  for (let i = 0; i < steps; i++) {
    const result = applyIdleTick(current, creature, environment || {}, `life:${creatureId}:${startingTick + i}`);
    if (!result.ok || result.duplicate) continue;
    current = result.life;
    applied += 1;
  }
  if (current === life) current = structuredClone(life);
  current.lifeClock = {lastAt: baseAt + steps * TICK_MS};
  const remote = remoteAfter(current, consent);
  current.remoteConsent = remote.remoteConsent;
  current.remoteStatus = remote.remoteStatus;
  return {ok: true, life: current, applied, omitted, remoteStatus: current.remoteStatus};
}

export function commitIdleLife(current, proposed) {
  if (!proposed || proposed.baseTick !== current?.tick) {
    return {ok: false, reason: 'STALE_WRITE', life: current};
  }
  return {ok: true, life: proposed.life};
}

function idsChecked(creature, info, persisted) {
  if (!persisted || persisted.creatureId !== creature.id) return false;
  if (persisted.idleOrigin !== info.origin || persisted.seed !== info.seed) return false;
  if (typeof persisted.idleLabel !== 'string' || typeof persisted.creatureName !== 'string') return false;
  if (typeof persisted.remoteConsent !== 'boolean' || typeof persisted.remoteStatus !== 'string') return false;
  const at = persisted.lifeClock?.lastAt;
  if (typeof at !== 'number' || !Number.isFinite(at)) return false;
  if (!Array.isArray(persisted.appliedEventIds) || persisted.appliedEventIds.length > 48) return false;
  return persisted.appliedEventIds.every(eventIdOk);
}

export function recoverIdleLife(creature, persisted) {
  const info = classify(creature);
  if (!info) return {ok: false, reason: 'NO_AUTHORIZED_INITIALIZER'};
  const checked = validateBehavior(persisted, beastFor(creature));
  if (checked !== persisted || !idsChecked(creature, info, persisted)) {
    const reset = createIdleLife(creature, clockAt(persisted));
    return {ok: true, reason: 'RECOVERED', life: reset.life};
  }
  return {ok: true, life: persisted};
}

export function replayIdleLife(creature, script) {
  const created = createIdleLife(creature, 0);
  if (!created.ok) return created;
  let life = created.life;
  for (const step of Array.isArray(script) ? script : []) {
    life = applyIdleTick(life, creature, step?.environment || {}, step?.eventId).life;
  }
  return {ok: true, life};
}

/** Stamp a trusted local clock on an existing behavior without simulating the unknown past. */
export function stampIdleClock(behavior, now, creatureId) {
  if (!behavior || typeof behavior !== 'object') return behavior;
  const at = typeof now === 'number' && Number.isFinite(now) ? now : 0;
  behavior.lifeClock = {lastAt: at};
  if (creatureId && !behavior.creatureId) behavior.creatureId = creatureId;
  if (!behavior.idleOrigin && SEED_RE.test(behavior.seed || '')) behavior.idleOrigin = IDLE_ORIGIN_RECORDED;
  if (!Array.isArray(behavior.appliedEventIds)) behavior.appliedEventIds = [];
  if (typeof behavior.remoteConsent !== 'boolean') behavior.remoteConsent = false;
  if (typeof behavior.remoteStatus !== 'string') behavior.remoteStatus = 'LOCAL_ONLY';
  return behavior;
}

/**
 * Bounded catch-up for a behavior that already belongs to one recorded creature.
 * The first observation only stores the clock. Later gaps replay the existing rules.
 * consent true defers to the existing growth worker and does not run a provider here.
 */
export function catchUpRecordedBehavior(behavior, creatureId, environment, now, consent = false) {
  if (!behavior || !SEED_RE.test(behavior.seed || '')) return {ok: false, reason: 'NO_BEHAVIOR', life: behavior};
  const id = creatureId || behavior.creatureId || 'recorded';
  const at = typeof now === 'number' && Number.isFinite(now) ? now : 0;
  if (!behavior.lifeClock || typeof behavior.lifeClock.lastAt !== 'number') {
    const life = stampIdleClock(structuredClone(behavior), at, id);
    return {ok: true, life, applied: 0, omitted: 0, remoteStatus: life.remoteStatus, primed: true};
  }
  const seeded = behavior.idleOrigin ? behavior : stampIdleClock(structuredClone(behavior), behavior.lifeClock.lastAt, id);
  const creature = {id, name: seeded.creatureName || '', genome: {seed: seeded.seed}, energy: seeded.energy};
  return {...catchUpIdleLife(seeded, creature, {now: at, environment, consent: consent === true}), primed: false};
}

export function describeIdleSource(life) {
  const described = {
    origin: life?.idleOrigin ?? null,
    label: typeof life?.idleLabel === 'string' ? life.idleLabel : '',
    quantumHardware: false,
    freshQuantumRun: false,
    provider: null,
  };
  if (life?.idleOrigin === IDLE_ORIGIN_RECORDED) {
    described.seedClass = 'recorded-seed';
    described.execution = 'classical-behavior-rules';
  }
  return described;
}
