'use strict';
/** Independent controlled native policy arena — no fake game rewards. */
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const SHA=x=>crypto.createHash('sha256').update(typeof x==='string'?x:JSON.stringify(x)).digest('hex');
const ACT=['UP','DOWN','LEFT','RIGHT','A','B','WAIT'];
const TEACHER_SEQUENCE=['RIGHT','UP','LEFT','DOWN','A','B','RIGHT','RIGHT','UP','LEFT','A','DOWN','RIGHT','B'];
const parseModel=s=>{
 if(typeof s!=='string')return null;
 const match=/^ACTION: (UP|DOWN|LEFT|RIGHT|A|B|WAIT)$/.exec(s.trim());
 return match?match[1]:null;
};
const optic=o=>o&&o.status==='observed'&&o.source==='native-emulator-display'
 &&['red','green','blue','mixed'].includes(o.dominant)
 &&['brightness','contrast','frameChange'].every(k=>Number.isInteger(o[k])&&o[k]>=0&&o[k]<=100);
function teacher(o,episode,step){
 assert.ok(optic(o),'Scripted teacher requires authentic native framebuffer features');
 if(o.brightness<20)return 'A';
 if(o.frameChange<5)return 'RIGHT';
 if(o.contrast>70)return 'LEFT';
 if(o.dominant==='blue')return 'UP';
 if(o.dominant==='green')return 'DOWN';
 if(o.brightness>70)return 'B';
 return TEACHER_SEQUENCE[(episode*3+step)%TEACHER_SEQUENCE.length];
}
function seededRandom(seed){
 let x=(seed>>>0)||1;
 return ()=>{x^=x<<13;x^=x>>>17;x^=x<<5;return(x>>>0)/4294967296};
}
function opticsSignature(o){
 assert.ok(optic(o));return JSON.stringify([o.brightness,o.contrast,o.frameChange,o.dominant]);
}
function summarizeArm(episodes){
 const rows=episodes.flatMap(e=>e.rows),signatures=new Set(rows.flatMap(r=>[opticsSignature(r.before),opticsSignature(r.after)]));
 const mean=arr=>arr.length?arr.reduce((a,b)=>a+b,0)/arr.length:0;
 return {
  episodes:episodes.length,actual_native_observations:rows.length*2,
  native_controller_acks:rows.filter(r=>r.native_ack_digest!==null).length,
  model_valid_actions:rows.filter(r=>r.is_model&&r.model_valid_action).length,
  model_invalid_or_unavailable:rows.filter(r=>r.is_model&&!r.model_valid_action).length,
  scripted_teacher_matches:rows.filter(r=>r.is_model&&r.model_valid_action&&r.action===r.scripted_target).length,
  unique_observed_optical_signatures:signatures.size,
  mean_screen_feature_change:mean(rows.map(r=>Math.abs(r.after.brightness-r.before.brightness)+Math.abs(r.after.contrast-r.before.contrast)+Math.abs(r.after.frameChange-r.before.frameChange))),
  distinct_explored_game_areas:null,earned_rewards:null,dialogue_advancement:null,game_progress:null,
  native_objective_metrics_available:false,visual_motion_does_not_prove_progress:true
 };
}
module.exports={SHA,ACT,parseModel,optic,teacher,seededRandom,opticsSignature,summarizeArm};