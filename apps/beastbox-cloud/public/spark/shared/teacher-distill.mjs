/**
 * Teacher distillation (Cory's design, 2026-10-16).
 *
 * Talk-to-Beast "brains" other than RAWRPHØS are TEACHERS. They never become the
 * Beast's voice: RAWRPHØS still produces the Beast's own reply, and the teacher's
 * answer is shown separately, provider-labeled. Each (prompt, teacher reply,
 * provider) pair is a distillation CANDIDATE:
 *  - stored on THIS device by default (never shared across visitors);
 *  - sent to shared training ONLY if the visitor explicitly opts in (off by default),
 *    after secret/PII filtering, rate limiting and provenance labeling;
 *  - training consumes only APPROVED pairs, style-filtered toward Zeref's persona,
 *    behind the same chat gates. Teachers inform knowledge, not personality.
 */
export const TEACHER_ROUTES=Object.freeze(["shared-ollama","local-ollama","hf-byok","connected-brain-bay"]);
export const PAIRS_KEY="beastbox-teacher-pairs-v1";
export const CONTRIBUTE_KEY="beastbox-teacher-contribute-v1";
export const MAX_LOCAL_PAIRS=200;
export const MAX_PROMPT=400,MAX_REPLY=600;
export const isTeacherRoute=route=>TEACHER_ROUTES.includes(route);

// Secrets / PII: any match means the pair is NOT contributable (kept local only).
const BLOCK=[
 /\bhf_[A-Za-z0-9]{10,}/, /\bsk-[A-Za-z0-9_-]{10,}/, /\bgh[pousr]_[A-Za-z0-9]{10,}/, /\bxai-[A-Za-z0-9]{10,}/,
 /\bAKIA[0-9A-Z]{12,}/, /-----BEGIN [A-Z ]*PRIVATE KEY-----/, /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/,
 /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/,               // email
 /(?:\+?\d[\s().-]?){9,}\d/,                                       // phone / long digit runs (cards, ids)
 /\b\d{3}-\d{2}-\d{4}\b/,                                          // SSN-like
 /\b(?:password|passwd|api[_ -]?key|secret|token)\s*[:=]/i,
 /https?:\/\/\S*[?&](?:key|token|sig|signature|password)=/i,
 /\b\d{1,5}\s+[A-Za-z0-9 .]{2,30}\s(?:street|st|avenue|ave|road|rd|lane|ln|drive|dr|blvd)\b/i, // street address
];
const CTRL=/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/;
export function clean(value,max){return typeof value==="string"?value.replace(/\s+/g," ").trim().slice(0,max):"";}
export function screenText(text){
 const s=String(text||"");
 if(!s.trim())return {ok:false,reason:"empty"};
 if(CTRL.test(s))return {ok:false,reason:"control characters"};
 for(const re of BLOCK)if(re.test(s))return {ok:false,reason:"possible secret or personal info"};
 return {ok:true};
}
export function makePair({prompt,reply,route,model,beast}){
 const p=clean(prompt,MAX_PROMPT),r=clean(reply,MAX_REPLY);
 if(!p||!r||!isTeacherRoute(route))return null;
 return {schema:"beastbox-teacher-pair-v1",prompt:p,teacher_reply:r,provider:route,model:clean(model,150)||null,
  beast:clean(beast,60)||null,role:"TEACHER_NOT_BEAST_VOICE",at:Date.now(),contributed:false};
}
export function readPairs(storage){try{const rows=JSON.parse(storage?.getItem(PAIRS_KEY)||"[]");return Array.isArray(rows)?rows.filter(r=>r&&r.schema==="beastbox-teacher-pair-v1").slice(-MAX_LOCAL_PAIRS):[];}catch{return [];}}
export function writePairs(storage,rows){try{storage?.setItem(PAIRS_KEY,JSON.stringify(rows.slice(-MAX_LOCAL_PAIRS)));return true;}catch{return false;}}
export function rememberPair(storage,pair){if(!pair)return readPairs(storage);const rows=[...readPairs(storage),pair];writePairs(storage,rows);return rows;}
export function readContribute(storage){try{return storage?.getItem(CONTRIBUTE_KEY)==="yes";}catch{return false;}}
export function writeContribute(storage,on){try{if(on)storage?.setItem(CONTRIBUTE_KEY,"yes");else storage?.removeItem(CONTRIBUTE_KEY);}catch{/* private mode */}}
/** Body for POST /api/teacher-pairs, or null when the pair must stay on-device. */
export function contributionBody(pair){
 if(!pair)return null;
 const a=screenText(pair.prompt),b=screenText(pair.teacher_reply);
 if(!a.ok||!b.ok)return null;
 return {consent:true,prompt:pair.prompt,teacher_reply:pair.teacher_reply,provider:pair.provider,model:pair.model};
}

// ---- Persona style filter (shared by the server and mirrored in training) ----
const ASSISTANTISM=/\b(as an ai|language model|i am an ai|i'm an ai|ai assistant|openai|chatgpt|llama|qwen|mistral|anthropic|claude|gemini|i cannot browse|my training data)\b/i;
const GAME=/ACTION:|\b(UP|DOWN|LEFT|RIGHT|WAIT)\b/;
/** Keep teacher KNOWLEDGE, drop teacher PERSONALITY: short, plain, no self-identity. */
export function personaStyle(reply){
 let s=String(reply||"").replace(/```[\s\S]*?```/g," ").replace(/[*_#>`]/g,"").replace(/\s+/g," ").trim();
 if(!s||ASSISTANTISM.test(s)||GAME.test(s))return null;
 const sentences=s.match(/[^.!?]+[.!?]+/g)||[s];
 s=sentences.slice(0,2).map(x=>x.trim()).join(" ");
 if(s.length>160)s=s.slice(0,157).replace(/\s+\S*$/,"")+"…";
 return s.length>=2?s:null;
}
