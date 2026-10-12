/**
 * Minimal Azure Blob Storage client (REST, SharedKey or container SAS) for the
 * per-beast cosmos folders. Server/CI only: never import from client code.
 *
 * Configuration (env, never logged):
 *   AZURE_STORAGE_CONNECTION_STRING  "DefaultEndpointsProtocol=https;AccountName=..;AccountKey=..;EndpointSuffix=core.windows.net"
 *     or
 *   AZURE_STORAGE_CONTAINER_SAS_URL  "https://<account>.blob.core.windows.net/<container>?sv=..&sig=.." (read/write/list/create)
 *   AZURE_STORAGE_CONTAINER          container name for the connection-string form (default "beast-cosmos")
 */
import {createHmac} from 'node:crypto';

const VERSION='2021-08-06';

export function storageConfig(env=process.env){
 const sas=String(env.AZURE_STORAGE_CONTAINER_SAS_URL||'').trim();
 if(sas){
  try{const u=new URL(sas);if(!u.search)return null;return {mode:'sas',containerUrl:u.origin+u.pathname.replace(/\/$/,''),sas:u.search.slice(1)};}catch{return null;}
 }
 const cs=String(env.AZURE_STORAGE_CONNECTION_STRING||'').trim();
 if(!cs)return null;
 const kv=Object.fromEntries(cs.split(';').filter(Boolean).map(p=>{const i=p.indexOf('=');return [p.slice(0,i).trim(),p.slice(i+1).trim()];}));
 if(!kv.AccountName||!kv.AccountKey)return null;
 const container=String(env.AZURE_STORAGE_CONTAINER||'beast-cosmos').trim();
 if(!/^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])$/.test(container))return null;
 const endpoint=(kv.BlobEndpoint||`${kv.DefaultEndpointsProtocol||'https'}://${kv.AccountName}.blob.${kv.EndpointSuffix||'core.windows.net'}`).replace(/\/$/,'');
 return {mode:'key',account:kv.AccountName,key:kv.AccountKey,containerUrl:endpoint+'/'+container,container};
}

function sign(cfg,method,url,headers){
 const u=new URL(url);
 const h=Object.fromEntries(Object.entries(headers).map(([k,v])=>[k.toLowerCase(),String(v)]));
 const canonHeaders=Object.keys(h).filter(k=>k.startsWith('x-ms-')).sort().map(k=>`${k}:${h[k].trim()}\n`).join('');
 // CanonicalizedResource = /<account><encoded URI path> (path-style emulator URLs keep their account segment).
 const canonResource=`/${cfg.account}${u.pathname}`+
  [...u.searchParams.keys()].map(k=>k.toLowerCase()).sort().filter((k,i,a)=>a.indexOf(k)===i)
   .map(k=>`\n${k}:${u.searchParams.getAll(k).sort().join(',')}`).join('');
 const len=h['content-length']&&h['content-length']!=='0'?h['content-length']:'';
 const sts=[method,h['content-encoding']||'',h['content-language']||'',len,h['content-md5']||'',h['content-type']||'','',
  h['if-modified-since']||'',h['if-match']||'',h['if-none-match']||'',h['if-unmodified-since']||'',h['range']||'',canonHeaders+canonResource].join('\n');
 return `SharedKey ${cfg.account}:${createHmac('sha256',Buffer.from(cfg.key,'base64')).update(sts,'utf8').digest('base64')}`;
}

/** Blob names are fixed to beasts/<id>/... and cosmos/... by callers; still encode each segment. */
function blobUrl(cfg,name,query=''){
 const path=name.split('/').map(encodeURIComponent).join('/');
 const q=[query,cfg.mode==='sas'?cfg.sas:''].filter(Boolean).join('&');
 return `${cfg.containerUrl}${path?'/'+path:''}${q?'?'+q:''}`;
}

async function call(cfg,method,name,{query='',body=null,headers={},timeoutMs=15000}={}){
 const url=blobUrl(cfg,name,query);
 const h={'x-ms-version':VERSION,'x-ms-date':new Date().toUTCString(),...headers};
 if(body!=null)h['Content-Length']=String(Buffer.byteLength(body));
 else if(method==='PUT')h['Content-Length']='0';
 if(cfg.mode==='key')h.Authorization=sign(cfg,method,url,h);
 const res=await fetch(url,{method,headers:h,body:body??undefined,signal:AbortSignal.timeout(timeoutMs),cache:'no-store',redirect:'error'});
 return res;
}

/** Sanitised error text: status + Azure error code only (no URLs, no SAS). */
async function fail(res,what){
 const text=await res.text().catch(()=>'');
 const code=/<Code>([^<]{1,80})<\/Code>/.exec(text)?.[1]||res.headers.get('x-ms-error-code')||'';
 const e=new Error(`storage ${what} failed: HTTP ${res.status}${code?' '+code:''}`);e.status=res.status;e.code=code;return e;
}

export async function ensureContainer(cfg){
 if(cfg.mode==='sas')return true;
 const res=await call(cfg,'PUT','',{query:'restype=container'});
 if(res.ok||res.status===409)return true;
 throw await fail(res,'create container');
}

/** -> {text,etag} | null when missing. */
export async function getBlob(cfg,name){
 const res=await call(cfg,'GET',name);
 if(res.status===404)return null;
 if(!res.ok)throw await fail(res,'read');
 return {text:await res.text(),etag:res.headers.get('etag')};
}

/** Write a block blob. ifNoneMatch:'*' = create only; ifMatch:etag = optimistic update. Returns etag; throws on conflict (status 409/412). */
export async function putBlob(cfg,name,text,{contentType='application/json; charset=utf-8',ifNoneMatch,ifMatch}={}){
 const headers={'x-ms-blob-type':'BlockBlob','Content-Type':contentType};
 if(ifNoneMatch)headers['If-None-Match']=ifNoneMatch;
 if(ifMatch)headers['If-Match']=ifMatch;
 const res=await call(cfg,'PUT',name,{body:text,headers});
 if(!res.ok)throw await fail(res,'write');
 return res.headers.get('etag');
}

/** Conditional cleanup only. An etag is required so a changed object is never deleted. */
export async function deleteBlob(cfg,name,{ifMatch}={}){
 if(typeof ifMatch!=='string'||!ifMatch)throw Error('Storage delete requires an etag.');
 const res=await call(cfg,'DELETE',name,{headers:{'If-Match':ifMatch}});
 if(res.status===404)return false;
 if(!res.ok)throw await fail(res,'delete');
 return true;
}

/** All blob names under a prefix (follows continuation markers, bounded). */
export async function listBlobs(cfg,prefix,{max=5000}={}){
 const names=[];let marker='';
 for(let page=0;page<20&&names.length<max;page++){
  const q=`restype=container&comp=list&prefix=${encodeURIComponent(prefix)}&maxresults=1000${marker?'&marker='+encodeURIComponent(marker):''}`;
  const res=await call(cfg,'GET','',{query:q});
  if(!res.ok)throw await fail(res,'list');
  const xml=await res.text();
  for(const m of xml.matchAll(/<Name>([^<]+)<\/Name>/g))names.push(m[1].replace(/&amp;/g,'&'));
  marker=/<NextMarker>([^<]*)<\/NextMarker>/.exec(xml)?.[1]||'';
  if(!marker)break;
 }
 return names.slice(0,max);
}
