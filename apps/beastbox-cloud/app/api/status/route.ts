import { bridgeConfigured, isOwner, ownerConfigured, safeJson } from '@/lib/security';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

type ProbeState = 'OWNER_LOGIN_REQUIRED'|'BRIDGE_SETTINGS_MISSING'|'BRIDGE_UNREACHABLE'|'BRIDGE_AUTH_REJECTED'|'BRIDGE_BAD_RESPONSE'|'REFERENCE_ONLY'|'MODEL_PROFILE_CONFIGURED_NOT_ATTESTED';
function result(owner:boolean, state:ProbeState, reachable=false, providerKind?:string) {
  return safeJson(200,{
    application:'BEAST BOX // COSMIC CHAOS', owner, ownerConfigured:ownerConfigured(),
    bridgeSettingsConfigured:owner && bridgeConfigured(), backendReachable:owner && reachable,
    backendStatus:state,
    // Provider profile existence is never evidence of successful inference.
    inference:state==='REFERENCE_ONLY'?'DETERMINISTIC_REFERENCE_ONLY':state==='MODEL_PROFILE_CONFIGURED_NOT_ATTESTED'?'MODEL_PROFILE_CONFIGURED_NOT_ATTESTED':'UNAVAILABLE',
    providerKind:owner && reachable?providerKind||'UNKNOWN':undefined,
    attachments:'LOCAL_STAGING_ONLY',
    persistence:owner && reachable?'RUNTIME_READ_VERIFIED_RESTART_NOT_ATTESTED':'UNAVAILABLE',
    surface:'PRIVATE_PREVIEW',backendKind:'SEPARATE_DURABLE_RUNTIME_REQUIRED'
  });
}
async function getHostJson(endpoint:'orbit'|'provider'):Promise<{status:number,data:Record<string,unknown>|null}> {
  const root=process.env.BEASTBOX_CLOUD_BRIDGE_URL!;
  const url=new URL('/api/'+endpoint,root.endsWith('/')?root:root+'/');
  const reply=await fetch(url,{
    method:'GET',cache:'no-store',redirect:'error',
    headers:{Authorization:'Bearer '+process.env.BEASTBOX_CLOUD_BRIDGE_TOKEN!},
    signal:AbortSignal.timeout(5_000),
  });
  if(!reply.ok) return {status:reply.status,data:null};
  if(Number(reply.headers.get('content-length')||0)>128_000) return {status:502,data:null};
  const raw=await reply.text();
  if(raw.length>128_000) return {status:502,data:null};
  let value:unknown;
  try {value=JSON.parse(raw);} catch {return {status:502,data:null};}
  if(!value||typeof value!=='object'||Array.isArray(value))return {status:502,data:null};
  return {status:reply.status,data:value as Record<string,unknown>};
}
export async function GET() {
  const owner=await isOwner();
  if(!owner)return result(false,'OWNER_LOGIN_REQUIRED');
  if(!bridgeConfigured())return result(true,'BRIDGE_SETTINGS_MISSING');
  try {
    const orbit=await getHostJson('orbit');
    if(orbit.status===401||orbit.status===403)return result(true,'BRIDGE_AUTH_REJECTED');
    if(orbit.status!==200)return result(true,'BRIDGE_BAD_RESPONSE');
    const runtime=orbit.data?.runtime;
    if(!runtime||typeof runtime!=='object'||Array.isArray(runtime)||typeof (runtime as Record<string,unknown>).system_id!=='string')return result(true,'BRIDGE_BAD_RESPONSE');
    const provider=await getHostJson('provider');
    if(provider.status===401||provider.status===403)return result(true,'BRIDGE_AUTH_REJECTED');
    if(provider.status!==200)return result(true,'BRIDGE_BAD_RESPONSE');
    const profile=provider.data?.profile;
    if(!profile||typeof profile!=='object'||Array.isArray(profile))return result(true,'BRIDGE_BAD_RESPONSE');
    const kind=(profile as Record<string,unknown>).kind;
    if(typeof kind!=='string')return result(true,'BRIDGE_BAD_RESPONSE');
    return result(true,kind==='reference'?'REFERENCE_ONLY':'MODEL_PROFILE_CONFIGURED_NOT_ATTESTED',true,kind);
  }catch {
    // Do not leak bridge URL, bearer, internal TLS details or provider output.
    return result(true,'BRIDGE_UNREACHABLE');
  }
}
