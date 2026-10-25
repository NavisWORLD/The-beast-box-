#!/usr/bin/env node
/**
 * node scripts/zeref-live-tick-run.mjs <diary-clone> <live-clone> <runSeconds> [batchSeconds]
 * <diary-clone>: read-only clone of the data-only `zeref-diary` branch (this script never writes there).
 * <live-clone>:  clone of the data-only `zeref-live-tick` branch; batches are committed here (never per second).
 * Per-second state is SIMULATED; recorded diary ticks and the IBM birth spark are untouched.
 */
import {appendFileSync,existsSync,mkdirSync,readFileSync,writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
import {runLiveTickLoop} from '../lib/zeref/live-tick-run.mjs';
const [diaryDir,liveDir,runS,batchS]=process.argv.slice(2);
if(!diaryDir||!liveDir||!runS){console.error('usage: zeref-live-tick-run.mjs <diary-clone> <live-clone> <runSeconds> [batchSeconds]');process.exit(2);}
const runSeconds=Math.min(19800,Math.max(1,Number(runS)|0)),batchSeconds=Math.max(60,Number(batchS||600)|0);
const git=(cwd,...a)=>execFileSync('git',a,{cwd,stdio:['ignore','pipe','pipe']}).toString();
const stateP=join(diaryDir,'zeref','state.json'),logP=join(diaryDir,'zeref','diary.jsonl');
const liveD=join(liveDir,'live');mkdirSync(liveD,{recursive:true});
const readDiary=()=>{try{const st=JSON.parse(readFileSync(stateP,'utf8'));let recent=[];try{recent=readFileSync(logP,'utf8').split('\n').filter(Boolean).slice(-12).reverse().map(l=>JSON.parse(l));}catch{}
 return {...st,beast_id:st.identity?.beast_id,recent};}catch{return null;}};
const readHead=()=>{try{return JSON.parse(readFileSync(join(liveD,'head.json'),'utf8'));}catch{return null;}};
const io={
 readDiary,readHead,
 async refresh(){try{git(diaryDir,'pull','-q','--ff-only','origin','zeref-diary');}catch(e){console.error('diary refresh failed (continuing with last state)');}},
 writeBatch({head,snapshot,entry}){writeFileSync(join(liveD,'head.json'),JSON.stringify(head,null,1)+'\n');writeFileSync(join(liveD,'latest.json'),JSON.stringify(snapshot,null,1)+'\n');appendFileSync(join(liveD,'diary.jsonl'),JSON.stringify(entry)+'\n');},
 async commit(msg){try{git(liveDir,'add','-A');try{git(liveDir,'commit','-q','-m',msg);}catch{return true;}
  for(let i=0;i<3;i++){try{git(liveDir,'push','-q','origin','HEAD:zeref-live-tick');return true;}catch{await new Promise(r=>setTimeout(r,4000));try{git(liveDir,'pull','-q','--rebase','origin','zeref-live-tick');}catch{}}}
  return false;}catch(e){console.error('commit failed:',String(e.message).slice(0,200));return false;}}
};
const r=await runLiveTickLoop({io,clock:{now:()=>Date.now(),sleep:ms=>new Promise(res=>setTimeout(res,ms))},runSeconds,batchSeconds,log:(...a)=>console.log('[live-tick]',...a)});
console.log('LIVE_TICK_RESULT='+JSON.stringify(r));process.exit(r.ok?0:1);
