/** Recipe builder for the five catalogue concept creatures (kept out of concept-sprites.mjs so the
 * shared sprite adapter stays dependency-free for every PixelBeast page). */
import {buildGenome} from './genome.mjs';
import {simulateStable} from './signal.mjs';
import {CONCEPT_CATALOGUE,CONCEPT_SPRITES} from './concept-sprites.mjs';
export function conceptCatalogueTraits() { const t = simulateStable('balanced'); return { focus: t.focus, calm: t.calm, spark: t.spark }; }
/** Build verified genomes from expanded runs; entries whose seed does not reproduce are dropped. */
export function conceptCatalogueGenomes(runs = []) {
 const byKey = new Map((runs || []).map(r => [r?.key, r])), traits = conceptCatalogueTraits(), out = [];
 for (const c of CONCEPT_CATALOGUE) {
  const run = byKey.get(c.runKey), entry = CONCEPT_SPRITES.find(e => e.slug === c.slug);
  if (!run || !entry) continue;
  try { const genome = buildGenome(traits, run, null, 10); if (genome.seed === entry.seed) out.push({ slug: c.slug, key: c.runKey, name: genome.names?.[1] || c.slug, genome }); } catch {}
 }
 return out;
}
