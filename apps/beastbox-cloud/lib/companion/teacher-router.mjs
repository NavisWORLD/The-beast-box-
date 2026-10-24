import {seededStream} from '../seeded-stream.mjs';
/** Picks which Ollama teacher answers a message (Cory, 2026-10-16). Pure + testable. */
export function messageKind(text){
 const t=String(text||"");
 if(/```|\b(code|function|javascript|python|bug|error|regex|sql)\b/i.test(t))return "code";
 if(/\b(math|calculate|equation|\d+\s*[-+*/^]\s*\d+|physics|quantum|science|why|how does)\b/i.test(t))return "reasoning";
 if(t.length>220)return "long";
 return "chat";
}
const PREFS={code:[/coder|code/i,/qwen/i,/gpt-oss/i],reasoning:[/gpt-oss:120b|deepseek|kimi|qwen3/i,/gpt-oss/i],long:[/gpt-oss:120b|kimi|deepseek|glm/i,/gpt-oss/i],chat:[/gpt-oss:20b|gemma|llama|mini|small/i,/gpt-oss/i]};
/** Returns {kind, order, explored}: best match first, ~15% exploration, then fallbacks. */
export function pickTeachers(text,available,{preferred="",fallback="gpt-oss:20b",random=seededStream("lib/companion/teacher-router.mjs")}={}){
 const kind=messageKind(text);
 const pref=String(preferred).split(/[\s,]+/).filter(Boolean);
 let pool=[...new Set((available||[]).filter(Boolean))];
 if(pref.length){const allowed=pool.filter(m=>pref.includes(m));pool=allowed.length?allowed:pref;}
 if(!pool.length)pool=[fallback];
 const score=m=>{const i=PREFS[kind].findIndex(re=>re.test(m));return i<0?99:i;};
 const ranked=[...pool].sort((a,b)=>score(a)-score(b)||a.localeCompare(b));
 let explored=false;
 if(ranked.length>1&&random()<0.15){const j=1+Math.floor(random()*(ranked.length-1));[ranked[0],ranked[j]]=[ranked[j],ranked[0]];explored=true;}
 if(!ranked.includes(fallback))ranked.push(fallback);
 return {kind,order:ranked,explored};
}
