/**
 * Sealed spark machine. A pull chooses one recorded run, including the public
 * generator shards. Nothing about the beast is listed before the pull returns.
 */

import { buildGenome } from "../../public/spark/genome.mjs";

export function expandCompactRun(row) {
  const counts = {};
  for (const part of String(row?.c || "").split(",")) {
    if (!part) continue;
    const [key, value] = part.split(":");
    if (key) counts[key] = Number(value) || 0;
  }
  return {
    key: String(row?.k || ""),
    backend: String(row?.b || ""),
    job_id: String(row?.j || ""),
    pub_index: Number(row?.p) || 0,
    num_bits: Number(row?.n) || 0,
    shots: Number(row?.s) || 0,
    counts,
    counts_sha256: String(row?.h || ""),
  };
}

export function mergeSeedTables(tables) {
  const byKey = new Map();
  for (const table of tables || []) {
    for (const row of table?.runs || []) {
      const run = expandCompactRun(row);
      if (!run.key || !Object.keys(run.counts).length) continue;
      if (!byKey.has(run.key)) byKey.set(run.key, run);
    }
  }
  return [...byKey.values()];
}

export function companionHash(text) {
  let out = 2166136261;
  for (const byte of new TextEncoder().encode(String(text))) {
    out ^= byte;
    out = Math.imul(out, 16777619);
  }
  return out >>> 0;
}

/** Same filter the Spark portrait uses: recorded runs of at least 2 bits. */
export function portraitRuns(runs) {
  const usable = (runs || []).filter((run) => run.num_bits >= 2 && Object.keys(run.counts || {}).length > 0);
  return [...new Map(usable.map((run) => [run.key, run])).values()];
}

export function portraitRun(profile, runs) {
  const table = portraitRuns(runs);
  if (!table.length || !profile?.id || !profile?.seed) return null;
  return table[companionHash(profile.id + "|" + profile.seed) % table.length];
}

export function profileTraits(profile) {
  const stats = profile?.game?.stats || {};
  const temperament = profile?.temperament || {};
  const clamp = (value) => Math.max(0, Math.min(100, Math.round(value)));
  return {
    focus: clamp(((stats.signal || 0) + (stats.memory || 0) + (stats.stability || 0)) / 3),
    calm: clamp(((stats.stability || 0) + (stats.memory || 0) + (temperament.caution || 0)) / 3),
    spark: clamp(((stats.energy || 0) + (stats.resonance || 0) + (temperament.playfulness || 0)) / 3),
  };
}

export function bytesToSeed(bytes) {
  const hex = [...bytes].map((value) => Number(value).toString(16).padStart(2, "0")).join("");
  return hex.slice(0, 32);
}

export function sealedMachine() {
  return { sealed: true, names: [], keys: [] };
}

export async function loadRecordedRuns(fetchImpl) {
  const indexResponse = await fetchImpl("/spark/user-seeds-20261004.json", { cache: "force-cache" });
  const index = await indexResponse.json();
  const shards = Array.isArray(index?.shards) ? index.shards : [];
  const paths = ["/spark/runs.json", ...shards];
  const tables = [];
  for (const path of paths) {
    const response = await fetchImpl(path, { cache: "force-cache" });
    tables.push(await response.json());
  }
  return mergeSeedTables(tables);
}

export function revealRecordedBeast(profile, runs) {
  const run = portraitRun(profile, runs);
  if (!run) return { ok: false, reason: "no recorded runs" };
  const genome = buildGenome(profileTraits(profile), run, null, 10);
  return {
    ok: true,
    sealed: false,
    name: genome.names[2] || genome.names[1],
    genome,
    runKey: run.key,
    num_bits: run.num_bits,
  };
}
