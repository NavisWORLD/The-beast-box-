/**
 * The minimal beast snapshot a paired browser shares with the Meta Muse connector.
 * Only game fields are copied: no chat history, pattern-memory weights, sensors,
 * owner memory, or profile data beyond the beast itself.
 */
export const SNAPSHOT_SCHEMA = "beastbox-muse-snapshot-v1";
export const MAX_SNAPSHOT_BYTES = 12000;

const num = (v, lo, hi, d = 0) => (Number.isFinite(Number(v)) ? Math.max(lo, Math.min(hi, Number(v))) : d);
const str = (v, max) => (typeof v === "string" ? v.slice(0, max) : "");

function pickGenome(g) {
  if (!g || typeof g !== "object") return null;
  const q = g.quantum && typeof g.quantum === "object" ? g.quantum : {};
  const stats = {};
  for (const stage of ["1", "2", "3"]) {
    const s = g.stats && g.stats[stage];
    if (s && typeof s === "object") stats[stage] = { hp: num(s.hp, 0, 999), atk: num(s.atk, 0, 999), def: num(s.def, 0, 999), spd: num(s.spd, 0, 999), spark: num(s.spark, 0, 999) };
  }
  const names = {};
  for (const stage of ["1", "2", "3"]) if (g.names && typeof g.names[stage] === "string") names[stage] = str(g.names[stage], 32);
  return {
    seed: str(g.seed, 96),
    element: str(g.element, 24),
    body: str(g.body, 32),
    island: str(g.island, 48),
    temperament: str(g.temperament, 24),
    glow: num(g.glow, 0, 360),
    stats,
    names,
    quantum: {
      backend: str(q.backend, 48),
      job_id: str(q.job_id, 64),
      top_state: str(q.top_state, 64),
      counts_sha256: str(q.counts_sha256, 64),
      num_bits: num(q.num_bits, 0, 64),
      shots: num(q.shots, 0, 1e7),
    },
  };
}

/** Build the snapshot from the shared care save (exportSession output) and trail. */
export function minimalSnapshot(session, trail, now = Date.now()) {
  const b = session && session.beast;
  const beast = b ? {
    seed: str(b.seed, 96),
    displayName: str(b.displayName, 24),
    xp: num(b.xp, 0, 1e7),
    bond: num(b.bond, 0, 100),
    energy: num(b.energy, 0, 100),
    stage: num(b.stage, 1, 3, 1),
    mood: str(b.mood, 24) || "idle",
    nativeStage: b.nativeStage ? num(b.nativeStage, 1, 3, 1) : null,
    qbeast: b.qbeast && (b.qbeast.profile || b.qbeast.profileId)
      ? { profileId: str(b.qbeast.profile ? b.qbeast.profile.id : b.qbeast.profileId, 64), profileName: str(b.qbeast.profile ? b.qbeast.profile.name : b.qbeast.profileName, 48) }
      : null,
    genome: pickGenome(b.genome),
  } : null;
  return {
    schema: SNAPSHOT_SCHEMA,
    beast,
    bestiaryCount: Array.isArray(session && session.bestiary) ? Math.min(999, session.bestiary.length) : 0,
    train: { rounds: num(session && session.train && session.train.rounds, 0, 1e6), score: num(session && session.train && session.train.score, 0, 1e7) },
    emulator: { booted: Boolean(session && session.emulator && session.emulator.booted), ticks: num(session && session.emulator && session.emulator.ticks, 0, 1e9) },
    place: str(trail && trail.place, 32),
    syncedAt: new Date(now).toISOString(),
  };
}

/** Server-side validation: re-pick every field so nothing extra is stored. */
export function validateSnapshot(raw, now = Date.now()) {
  if (!raw || typeof raw !== "object" || raw.schema !== SNAPSHOT_SCHEMA) return null;
  if (JSON.stringify(raw).length > MAX_SNAPSHOT_BYTES) return null;
  const safe = minimalSnapshot({ beast: raw.beast, bestiary: Array.from({ length: num(raw.bestiaryCount, 0, 999) }), train: raw.train, emulator: raw.emulator }, { place: raw.place }, now);
  return safe;
}
