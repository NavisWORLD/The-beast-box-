/**
 * Data-driven names and labels for the Look Closer page. Names and buttons come from
 * lib/look-closer-labels.json (the page imports it and passes it as `labels`); the honest attribution caption comes from creature-dimensional.mjs
 * unless a label set supplies its own, and a replacement caption must still say what the model is not.
 * A null entry means "use the live name" (the active Beast) or the built-in attribution.
 */
import {dimensionalAttribution} from './creature-dimensional.mjs';

export const LOOK_SUBJECT_IDS = Object.freeze(['workshop', 'moonwraith', 'dragonling']);
const KIND = {moonwraith: 'moonwraith-artistic', dragonling: 'dragonling-artistic'};
/** A replacement caption keeps the honesty wording: artistic representation, and not a measured quantum phenotype. */
export function captionKeepsHonesty(text) {
  return typeof text === 'string' && /artistic/i.test(text) && /not (?:a )?(?:newly )?measured quantum phenotype/i.test(text);
}
export function lookSubjectLabels(id, {activeName = '', profileName = '', labels = {subjects: {}}} = {}) {
  const e = (labels.subjects || {})[id] || {};
  const live = activeName || profileName || 'companion';
  const attribution = KIND[id] ? dimensionalAttribution(KIND[id]) : null;
  const custom = attribution && e.caption && captionKeepsHonesty(e.caption) ? e.caption : null;
  const headingName = e.headingName || (id === 'workshop' ? (activeName || 'your beast') : 'Zeref');
  const stageName = e.stageName || (id === 'workshop' ? live : 'Zeref');
  return {
    id,
    button: e.button || (id === 'workshop' ? (activeName || 'Your beast') : id),
    headingName,
    stageName,
    caption: custom || (attribution ? attribution.label : null),
    attributionKind: attribution ? KIND[id] : null,
    explainName: e.headingName || 'Zeref',
  };
}
