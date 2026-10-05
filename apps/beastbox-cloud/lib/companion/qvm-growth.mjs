import { grantXp } from "./session.mjs";

function count(batch,key){return Math.max(0,Number(batch?.counts?.[key])||0);}
function ratio11(batch){const shots=Math.max(1,Number(batch?.shots)||0);return count(batch,"11")/shots;}
function clamp(n,a,b){return Math.max(a,Math.min(b,n));}

export function deriveQvmGrowth(scenario){
  const batches=Array.isArray(scenario?.batches)?scenario.batches:[];
  const histories=batches.filter((row)=>row?.phase==="history_a"||row?.phase==="history_b");
  if(histories.length!==2)return {ok:false,reason:"historical QVM batches unavailable"};
  const [a,b]=histories;
  const pa=ratio11(a),pb=ratio11(b),mean=(pa+pb)/2,delta=Math.abs(pa-pb);
  const xp=clamp(10+Math.round(mean*12+(1-delta)*3),8,24);
  const bond=clamp(1+Math.round((1-delta)*2),1,3);
  const resonance=Math.round(mean*100);
  return {
    ok:true,scenario:Number(scenario.scenario)||0,theta_rad:Number(scenario.theta_rad)||0,
    xp,bond,resonance,stability:Math.round((1-delta)*100),
    jobs:[a.job_id,b.job_id],program_sha256:a.program_sha256||"",
    source:"ARCHIVED_AZURE_RIGETTI_QVM_SIMULATOR"
  };
}

export function nextQvmGrowth(session,receipt){
  if(!session?.beast)return {ok:false,reason:"no beast"};
  const scenarios=Array.isArray(receipt?.scenario_records)?receipt.scenario_records:[];
  const used=new Set((session.beast.qvm_growth||[]).map((row)=>Number(row.scenario)));
  const scenario=scenarios.find((row)=>!used.has(Number(row.scenario)));
  if(!scenario)return {ok:false,complete:true,reason:"all archived scenarios processed"};
  const pulse=deriveQvmGrowth(scenario);
  if(!pulse.ok)return pulse;
  const result=grantXp(session,pulse.xp,"qvm");
  session.beast.bond=Math.min(100,(session.beast.bond||0)+pulse.bond);
  session.beast.mood=result.evolved?"evolve":"spark";
  session.mood=session.beast.mood;
  session.beast.qvm_growth=[...(session.beast.qvm_growth||[]),{
    scenario:pulse.scenario,theta_rad:pulse.theta_rad,xp:pulse.xp,bond:pulse.bond,
    resonance:pulse.resonance,stability:pulse.stability,jobs:pulse.jobs,
    program_sha256:pulse.program_sha256,source:pulse.source
  }];
  return {...pulse,...result,used:session.beast.qvm_growth.length,total:scenarios.length};
}
