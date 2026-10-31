/**
 * TWO MINDS, ONE VOICE (Cory, 2026-10-31). Zeref answers from two drafts:
 *  - the GATED mind: the reviewed public pin (changes only through the unchanged promotion gate),
 *  - the GROWING mind: the always-learning zeref-growing-NNN side branch (NOT GATED).
 * This pure chooser picks ONE draft deterministically (no clock, no Math.random, no extra inference).
 * Score = a well-formed, non-repeating answer that shares words with what the keeper said. Ties go to the gated mind.
 * The growing mind never changes the pin; this only decides which draft is spoken.
 */
export const ONE_VOICE_SCHEMA='zeref-one-voice/v1';
export const ONE_VOICE_RULE='Both minds draft; the clearer on-topic draft is spoken (ties go to the gated mind). Deterministic, no extra model.';
const STOP=new Set('the a an and or but to of in on at is are was were be it i you me my your we he she they this that what how why who do does did for with as so not no yes'.split(' '));
const words=s=>String(s||'').toLowerCase().match(/[a-z0-9']+/g)||[];
/** The keeper's last line inside a framed prompt (falls back to the whole text). */
export function keeperLine(prompt){
 const lines=String(prompt||'').split('\n').filter(l=>/^Keeper:\s*/.test(l));
 return lines.length?lines[lines.length-1].replace(/^Keeper:\s*/,''):String(prompt||'');
}
export function draftScore(reply,prompt){
 const w=words(reply);if(!w.length)return -1e9;
 const uniq=new Set(w).size/w.length;               // 1 = no repeats; looping drafts fall
 const ask=new Set(words(keeperLine(prompt)).filter(x=>!STOP.has(x)&&x.length>2));
 const overlap=[...new Set(w)].filter(x=>ask.has(x)).length;
 const len=Math.min(w.length,40);
 const tooShort=w.length<3?10:0;
 return Math.round((len*0.25+overlap*3+uniq*10-tooShort)*1000)/1000;
}
/** gated / growing: {reply} or null. Returns {reply, chosen, scores}. */
export function chooseOneVoice(prompt,gated,growing){
 const g=gated&&typeof gated.reply==='string'&&gated.reply.trim()?gated.reply.trim():null;
 const r=growing&&typeof growing.reply==='string'&&growing.reply.trim()?growing.reply.trim():null;
 const sg=g===null?null:draftScore(g,prompt),sr=r===null?null:draftScore(r,prompt);
 if(g===null&&r===null)return {reply:null,chosen:null,scores:{gated:sg,growing:sr}};
 const chosen=g===null?'growing':r===null?'gated':sr>sg?'growing':'gated';
 return {reply:chosen==='gated'?g:r,chosen,scores:{gated:sg,growing:sr}};
}
