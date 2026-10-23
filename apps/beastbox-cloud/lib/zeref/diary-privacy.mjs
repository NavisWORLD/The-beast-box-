// Public diary filter (Oct 23 2026, Emeth's audit): a diary line is shown publicly only if nothing marks it private.
// Never show Cory's private lines: entries flagged private/owner/visibility!=public, lines quoting or naming the keeper,
// and anything that looks like contact details or secrets are dropped (fail closed).
const PRIVATE_RX=/\b(cory|zerefs?\s*cosmos|private|secret|password|passcode|token|api[_ -]?key|diary of cory|my (mom|dad|wife|girlfriend|boyfriend|address|phone))\b|[\w.+-]+@[\w-]+\.[\w.]+|\+?\d[\d\s().-]{7,}\d/i;
export function isPublicDiaryEntry(e){
 if(!e||typeof e!=='object')return false;
 if(e.private===true||e.owner_only===true||(e.visibility&&e.visibility!=='public'))return false;
 const t=e.thought;if(!t||typeof t.text!=='string'||!t.text.trim())return false;
 if(t.private===true||t.by==='owner'||t.by==='cory'||t.by==='keeper')return false;
 return !PRIVATE_RX.test(t.text);
}
export function publicDiaryEntries(list){return Array.isArray(list)?list.filter(isPublicDiaryEntry):[];}
/** Plain-language source for a diary line. */
export function diarySourceLabel(by){if(!by||by==='deterministic-template')return 'a written template (no model)';return /rawrph/i.test(by)?'his own words from the RAWRPHØS model, unedited':'his own words, unedited';}
