// Opt-in Open Field perception experiences: numeric summaries only (no images, no audio).
import {createHash,randomUUID} from 'node:crypto';
import {safeJson} from '@/lib/security';
import {storageConfig,putBlob} from '@/lib/cosmos/azure-blob.mjs';
import {isNumericExperience,PERCEPTION_SCHEMA} from '@/lib/companion/field-perception.mjs';
export const runtime='nodejs';
export const dynamic='force-dynamic';
const hits=new Map<string,number[]>();
export async function POST(request:Request){
 if(request.headers.get('origin')!==new URL(request.url).origin)return safeJson(403,{error:'Same-origin request required'});
 const raw=await request.text();if(raw.length>20000)return safeJson(413,{error:'Too large'});
 let body:any;try{body=JSON.parse(raw);}catch{return safeJson(400,{error:'Invalid JSON'});}
 if(!body||body.consent!==true||!Array.isArray(body.experiences)||Object.keys(body).sort().join(',')!=='consent,experiences')return safeJson(400,{error:'Explicit opt-in consent and numeric experiences required'});
 const ex=body.experiences.slice(0,120);
 if(!ex.length||!ex.every(isNumericExperience))return safeJson(422,{error:'Only numeric perception summaries are accepted'});
 const fwd=(request.headers.get('x-forwarded-for')||'').split(',')[0].trim();
 const client=createHash('sha256').update('perc:'+fwd).digest('hex').slice(0,24),now=Date.now();
 const recent=(hits.get(client)||[]).filter(t=>now-t<3600e3);if(recent.length>=6)return safeJson(429,{error:'Limit reached; try later.'});
 recent.push(now);hits.set(client,recent);if(hits.size>5000)hits.clear();
 const cfg=storageConfig();if(!cfg)return safeJson(503,{error:'Shared intake not configured. Experiences stay on your device.'});
 const id=randomUUID(),name=`zeref-perception/pending/${new Date().toISOString().slice(0,10)}/${id}.json`;
 const record={schema:PERCEPTION_SCHEMA,id,experiences:ex,consent:'explicit-opt-in',contains:'numeric summaries only (no images, no audio)',review_status:'PENDING_REVIEW',received_at:new Date().toISOString()};
 try{const etag=await putBlob(cfg,name,JSON.stringify(record),{contentType:'application/json',ifNoneMatch:'*'});if(!etag)throw 0;}catch{return safeJson(502,{error:'Could not store. Experiences stay on your device.'});}
 return safeJson(201,{ok:true,id,count:ex.length});
}
