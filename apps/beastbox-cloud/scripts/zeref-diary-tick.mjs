#!/usr/bin/env node
/**
 * One tick of Zeref's forever loop. Usage:
 *   node scripts/zeref-diary-tick.mjs <diary-dir> --plan <out.json>           (write next growth circuit)
 *   node scripts/zeref-diary-tick.mjs <diary-dir> [--now ISO] [--care N] [--qvm result.json]
 * Reads <dir>/state.json + <dir>/diary.jsonl (creating genesis if absent),
 * verifies the hash chain, appends exactly one entry and rewrites state.json
 * and latest.json. Existing diary lines are never rewritten (append-only).
 *
 * Optional model phrasing (off by default): only when the repository owner
 * sets ZEREF_DIARY_MODEL (a Hugging Face router chat model id) AND
 * ZEREF_DIARY_MODEL_BILLING_APPROVED=yes AND provides HF_TOKEN. The model only
 * rephrases the already-computed facts; on any failure the deterministic
 * template line is kept and the entry says so. Never a faked model response.
 */
import {appendFileSync,existsSync,mkdirSync,readFileSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {genesisState,planGrowthCircuit,stepDiary,summarize,verifyChain} from '../lib/zeref/zeref-diary.mjs';

const args=process.argv.slice(2);
const dir=args[0];
if(!dir){console.error('usage: zeref-diary-tick.mjs <dir> [--now ISO] [--care N]');process.exit(2);}
const opt=k=>{const i=args.indexOf(k);return i>0?args[i+1]:undefined;};
const now=opt('--now')||new Date().toISOString();
const care=Number(opt('--care')||0);
mkdirSync(dir,{recursive:true});
const statePath=join(dir,'state.json'),logPath=join(dir,'diary.jsonl'),latestPath=join(dir,'latest.json');

const entries=existsSync(logPath)?readFileSync(logPath,'utf8').split('\n').filter(Boolean).map(l=>JSON.parse(l)):[];
const state=existsSync(statePath)?JSON.parse(readFileSync(statePath,'utf8')):genesisState();
const genesis=genesisState();
if(JSON.stringify(state.identity)!==JSON.stringify(genesis.identity))throw Error('Identity block changed: refusing to tick.');
const chain=verifyChain(entries,state.identity);
if(!chain.ok)throw Error('Diary chain invalid at tick '+chain.tick+': '+chain.reason);
if(chain.tick!==state.tick||(chain.head??null)!==state.last_entry_hash)throw Error('state.json does not match the diary head.');

async function modelThought(entry){
 const model=process.env.ZEREF_DIARY_MODEL,approved=process.env.ZEREF_DIARY_MODEL_BILLING_APPROVED==='yes',token=process.env.HF_TOKEN;
 if(!model||!approved||!token)return {thought:null,note:'model-not-configured'};
 const facts={mood:entry.mood,place:entry.place,new_combos:entry.new_combo_count,stage_name:entry.stage_name,grew:entry.grew,signals:entry.signals,local_hour:entry.hour_local};
 try{
  const res=await fetch('https://router.huggingface.co/v1/chat/completions',{method:'POST',signal:AbortSignal.timeout(20000),
   headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},
   body:JSON.stringify({model,max_tokens:70,temperature:.7,messages:[
    {role:'system',content:'You write one short, cute first-person diary line (max 30 words) for Zeref, a black moon-cat dragon game companion exploring a pocket dimension. Use only the given facts. No claims of consciousness or real quantum links.'},
    {role:'user',content:JSON.stringify(facts)}]})});
  if(!res.ok)return {thought:null,note:'model-http-'+res.status};
  const data=await res.json();const text=String(data?.choices?.[0]?.message?.content||'').replace(/\s+/g,' ').trim();
  if(!text)return {thought:null,note:'model-empty'};
  return {thought:{text,by:'huggingface-router:'+model},note:'model-ok'};
 }catch(e){return {thought:null,note:'model-error'};}
}

const planOut=opt('--plan');
if(planOut){writeFileSync(planOut,JSON.stringify(planGrowthCircuit(state),null,1)+'\n');console.log('ZEREF_GROWTH_PLAN '+JSON.stringify({tick:state.tick+1}));process.exit(0);}
// Growth source: the simulator receipt written by scripts/zeref_diary_qvm.py (success or real failure).
let growth=null;const qvmPath=opt('--qvm');
if(qvmPath){
 if(existsSync(qvmPath)){
  try{growth=JSON.parse(readFileSync(qvmPath,'utf8'));}catch{growth={ok:false,error:'simulator receipt unreadable'};}
  const plan=planGrowthCircuit(state);
  if(growth?.ok&&growth.job_name!==plan.job_name)growth={ok:false,job_id:growth.job_id,error:'simulator receipt is for a different tick; counts ignored'};
 }else growth={ok:false,error:'simulator step produced no receipt'};
}
let {state:next,entry}=stepDiary(state,{now,care,growth});
const {thought,note}=await modelThought(entry);
if(thought)({state:next,entry}=stepDiary(state,{now,care,thought,growth}));
appendFileSync(logPath,JSON.stringify(entry)+'\n');
writeFileSync(statePath,JSON.stringify(next,null,1)+'\n');
writeFileSync(latestPath,JSON.stringify({...summarize(next,[...entries,entry]),generated_at:now,thought_source_note:note},null,1)+'\n');
console.log('ZEREF_DIARY_TICK '+JSON.stringify({tick:entry.tick,at:entry.at,mood:entry.mood,place:entry.place,new_combos:entry.new_combo_count,xp:entry.xp,stage:entry.stage_name,thought_by:entry.thought.by,note,growth:entry.growth_source.kind,job:entry.growth_source.job_id,hash:entry.hash.slice(0,16)}));
