import { canonicalJson } from "./genome.mjs";
import { sha256Hex } from "./sha.mjs";

export const QVM_SOURCE_SHA = "7ef23c00005a2053d1fc830985330f4db322b3bf6144fd79fd1561d14c425599";
export const QVM_SOURCE_CLASS = "NEW_AZURE_CLOUD_QVM_SIMULATION_NOT_QPU";
export const QVM_TARGET = "rigetti.sim.qvm";
const PHASE_ORDER = { history_a: 0, history_b: 1, future_held_out: 2 };

function finiteCount(value) {
  const n = Number(value);
  return Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0;
}

export function expandQvmReceipt(receipt) {
  if (!receipt || receipt.public_rows_sha256 !== QVM_SOURCE_SHA) throw new Error("Rigetti QVM receipt digest is not the pinned public source.");
  if (receipt.source_class !== QVM_SOURCE_CLASS) throw new Error("Rigetti source class changed.");
  if (receipt.completed_provider_jobs !== 24 || receipt.scenarios !== 8) throw new Error("Rigetti QVM receipt is incomplete.");
  const out = [];
  for (const row of receipt.scenario_records || []) {
    if (!Number.isInteger(row.scenario) || !Array.isArray(row.batches) || row.batches.length !== 3) throw new Error("Rigetti QVM scenario shape changed.");
    for (let index = 0; index < row.batches.length; index++) {
      const batch = row.batches[index];
      if (batch.target !== QVM_TARGET || !(batch.phase in PHASE_ORDER)) throw new Error("Unexpected Rigetti QVM target or phase.");
      const counts = Object.fromEntries(["00", "01", "10", "11"].map((key) => [key, finiteCount(batch.counts?.[key])]));
      const shots = Object.values(counts).reduce((sum, value) => sum + value, 0);
      if (shots !== batch.shots) throw new Error("Rigetti QVM shot total changed.");
      out.push({
        key: `rigetti-qvm:s${row.scenario}:${batch.phase}:${batch.job_id}`,
        backend: QVM_TARGET,
        job_id: batch.job_id,
        pub_index: (row.scenario - 1) * 3 + index,
        num_bits: 2,
        shots: batch.shots,
        counts,
        counts_sha256: sha256Hex(canonicalJson(counts)),
        qvm: {
          source_sha256: QVM_SOURCE_SHA,
          source_class: QVM_SOURCE_CLASS,
          scenario: row.scenario,
          theta_rad: row.theta_rad,
          phase: batch.phase,
          phase_index: PHASE_ORDER[batch.phase],
          source: batch.source,
        },
      });
    }
  }
  if (out.length !== 24 || new Set(out.map((row) => row.job_id)).size !== 24) throw new Error("Rigetti QVM job inventory changed.");
  return out;
}

export function growthFromQvmBatch(run) {
  const shots = Math.max(1, Number(run?.shots) || 1);
  const counts = run?.counts || {};
  const probabilities = ["00", "01", "10", "11"].map((key) => Math.max(0, Number(counts[key]) || 0) / shots);
  const entropy = -probabilities.reduce((sum, p) => sum + (p > 0 ? p * Math.log2(p) : 0), 0) / 2;
  const p00 = probabilities[0], p11 = probabilities[3];
  const balance = 1 - Math.min(1, Math.abs(p00 - p11));
  const delta = Math.max(0.05, Math.min(0.18, 0.07 + entropy * 0.05 + balance * 0.04 + p11 * 0.02));
  return {
    delta,
    entropy: Math.max(0, Math.min(1, entropy)),
    p00,
    p11,
    signal: Math.max(-1, Math.min(1, p11 - p00)),
  };
}

export function scenarioRuns(runs, scenario) {
  return (runs || [])
    .filter((row) => row?.qvm?.scenario === scenario)
    .slice()
    .sort((a, b) => (a.qvm?.phase_index ?? 99) - (b.qvm?.phase_index ?? 99));
}
