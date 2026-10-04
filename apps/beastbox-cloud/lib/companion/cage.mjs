/**
 * Cage bridge. .qbeast is QBEAST1 (Living Universe / Spark Beasts).
 * .lcx1 is the Synapse OS mailbox (magic LCX1) inside a Lost Cosmos SRAM save,
 * with an LCG1 growth record so earned experience can ride along.
 */

import { beastProfile, buildGrowth, buildMailbox, buildSave, parseMailbox, parseSave } from "./lcx1.mjs";
import { buildQbeast, loadQbeast, readLearning, serializeQbeast, withLearning } from "./qpack/qbeast.mjs";
import { exportMind, importMind } from "./learn.mjs";
import { stageFromXp } from "./session.mjs";

export function traitsOf(genome) {
  const traits = genome?.inputs?.traits || {};
  return {
    focus: traits.focus | 0,
    calm: traits.calm | 0,
    spark: traits.spark | 0,
  };
}

export function cageProfile(genome) {
  const traits = traitsOf(genome);
  const family = ["nebula", "aurora", "void", "plasma", "memory", "signal", "starlight"][
    (genome.seed.charCodeAt(0) || 1) % 7
  ];
  return beastProfile({
    seed: genome.seed.slice(0, 64),
    familyName: family,
    hue: 0,
    ...traits,
  });
}

export function growthFor(genome, xp = 0) {
  const profile = cageProfile(genome);
  const kept = Math.max(0, Math.floor(xp));
  return buildGrowth({
    publicId: profile.publicId,
    layer: Math.min(999, Math.floor(kept / 1000)),
    points: kept % 1000,
    grown: kept > 0,
  });
}

export function exportQbeast(genome, mind, xp = 0, notes = []) {
  const snapshot = withLearning(buildQbeast(genome), {
    ...exportMind(mind),
    xp: Math.max(0, Math.floor(xp)),
    stage: stageFromXp(xp),
    genome,
    notes,
  });
  return serializeQbeast(snapshot);
}

export function importQbeast(text) {
  const loaded = loadQbeast(text);
  const snapshot = JSON.parse(text);
  const learning = readLearning(snapshot);
  return {
    card: loaded.card,
    snapshot,
    mind: learning ? importMind(learning) : null,
    xp: Number(learning?.xp) || 0,
    genome: learning?.genome || null,
    notes: Array.isArray(learning?.notes) ? learning.notes : [],
  };
}

export function exportLcx1(genome, xp = 0) {
  const profile = cageProfile(genome);
  const sav = buildSave(profile);
  const grown = growthFor(genome, xp);
  const out = sav.slice();
  out.set(grown, 25476);
  return out;
}

export function importLcx1(bytes) {
  const data = bytes.length === 644 ? { ...parseMailbox(bytes), growth: null } : parseSave(bytes);
  const xp = data.growth ? data.growth.layer * 1000 + data.growth.points : 0;
  return { ...data, xp, stage: stageFromXp(xp) };
}

export function bytesToHex(bytes) {
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}
