import {createHmac} from 'node:crypto';
import {bridgeConfigured,safeJson} from '@/lib/security';
import PUBLIC_PIN from '@/lib/rawrphos-public-pin.json';
// Growing Zeref (Cory, 2026-10-31): the always-learning side branch, served on its own bridge door
// (/api/guest-growing). It is NOT the pin: every reply says so, and a reply carrying the pin's sha is refused.
export const runtime='nodejs';
export const dynamic='force-dynamic';
const GROWING_LABEL='Growing Zeref · not the pin';
const MAX_PROMPT=1800,MAX_BODY=8000;
// RECORDED origin spark pulse from the bridge (beastbox/spark_pulse.py); anything malformed is ABSENT (null).
function sparkPulseOf(r:Record<string,unknown>){const s=r.sensorium as Record<string,unknown>|undefined;const p=s&&typeof s==='object'?s.spark_pulse as Record<string,unknown>|null:null;
 if(!p||typeof p!=='object'||p.label!=='RECORDED'||!Number.isInteger(p.beat)||typeof p.pulse_sha256!=='string'||!/^[a-f0-9]{64}$/.test(p.pulse_sha256)||
  typeof p.question_pair!=='string'||!/^x[01]y[01]$/.test(p.question_pair)||typeof p.recorded_win_rate!=='number')return null;
 return {label:'RECORDED',beat:p.beat,pulse_sha256:p.pulse_sha256,glow:typeof p.glow==='number'?p.glow:null,question_pair:p.question_pair,
  recorded_win_rate:p.recorded_win_rate,at_utc:typeof p.at_utc==='string'?p.at_utc.slice(0,40):null,applies_to:'growing Zeref only (never the pin)'};}
export async function POST(request:Request){
 if(request.headers.get('origin')!==new URL(request.url).origin)return safeJson(403,{error:'Same-origin guest request required'});
 if(!request.headers.get('content-type')?.toLowerCase().startsWith('application/json'))return safeJson(415,{error:'JSON required'});
 let item:Record<string,unknown>;
 try{const raw=await request.text();if(raw.length>MAX_BODY)return safeJson(413,{error:'Too large'});item=JSON.parse(raw);}catch{return safeJson(400,{error:'Invalid JSON'});}
 if(!item||typeof item!=='object'||Array.isArray(item)||Object.keys(item).join(',')!=='text')return safeJson(400,{error:'Only a message is accepted'});
 if(typeof item.text!=='string'||item.text.trim().length<1||item.text.length>MAX_PROMPT||/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(item.text))
  return safeJson(400,{error:'Message must contain 1–1800 characters'});
 if(!bridgeConfigured())return safeJson(503,{error:'Model host is not configured'});
 const secret=process.env.BEASTBOX_CLOUD_AUTH_SECRET;
 if(!secret||secret.length<32)return safeJson(503,{error:'Guest identity signing unavailable'});
 const forwarded=request.headers.get('x-vercel-forwarded-for')||request.headers.get('x-forwarded-for')||'unknown';
 const identity=createHmac('sha256',secret).update(forwarded.slice(0,256)).digest('hex');
 try{
  const res=await fetch(new URL('/api/guest-growing',process.env.BEASTBOX_CLOUD_BRIDGE_URL!),{method:'POST',redirect:'error',cache:'no-store',
   headers:{Authorization:'Bearer '+process.env.BEASTBOX_CLOUD_BRIDGE_TOKEN!,'Content-Type':'application/json'},
   body:JSON.stringify({text:item.text.trim(),guest_identity:identity}),signal:AbortSignal.timeout(55_000)});
  const raw=await res.text();if(raw.length>16000)return safeJson(502,{error:'Response too large'});
  const r=JSON.parse(raw) as Record<string,unknown>;
  if(!res.ok)return safeJson([400,403,429,503].includes(res.status)?res.status:502,{error:typeof r.error==='string'&&r.error.length<128?r.error:'Growing Zeref unavailable',label:GROWING_LABEL});
  if(r.schema!=='beastbox-guest-growing-v1'||r.model!=='rawrphos-native'||r.is_public_pin!==false||r.label!==GROWING_LABEL||
     typeof r.checkpoint_sha256!=='string'||r.checkpoint_sha256===PUBLIC_PIN.checkpoint_sha256||typeof r.reply!=='string'||r.reply.length>6000||
     typeof r.tag!=='string'||!/^zeref-growing-\d{3,}$/.test(r.tag))
   return safeJson(502,{error:'Unverified growing model response'});
  return safeJson(200,{label:GROWING_LABEL,is_public_pin:false,gated:false,model:'rawrphos-native',tag:r.tag,step:r.step,
   checkpoint_sha256:r.checkpoint_sha256,reply:r.reply,hebbian:r.hebbian===true,guest_stateless:true,sensorium:{spark_pulse:sparkPulseOf(r)}});
 }catch{return safeJson(502,{error:'Growing Zeref unavailable or timed out',label:GROWING_LABEL});}
}
