import {isOwner,safeJson} from '@/lib/security';
export const runtime='nodejs';
export const dynamic='force-dynamic';

// Intentionally fixed destination. This is NOT a model-controlled fetch, URL
// reader, crawler, proxy, network tool, or credential-bearing request.
const WIKIPEDIA='https://en.wikipedia.org/w/api.php';
const MAX_BYTES=48_000;
const trimText=(s:string,max:number)=>s.replace(/<[^>]*>/g,' ').replace(/&(?:amp|lt|gt|quot|#39|nbsp);/g,m=>
  ({'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&#39;':"'",'&nbsp;':' '}[m]||' ')).replace(/\s+/g,' ').trim().slice(0,max);

export async function POST(request:Request){
  if(!await isOwner())return safeJson(401,{error:'Owner authentication required'});
  if(request.headers.get('origin')!==new URL(request.url).origin)
    return safeJson(403,{error:'Same-origin owner request required'});
  if(!request.headers.get('content-type')?.toLowerCase().startsWith('application/json'))
    return safeJson(415,{error:'JSON required'});
  if(Number(request.headers.get('content-length')||0)>512)return safeJson(413,{error:'Query too large'});
  let body:string;
  try{body=await request.text();}catch{return safeJson(400,{error:'Invalid request'});}
  if(body.length>512)return safeJson(413,{error:'Query too large'});
  let data:unknown;
  try{data=JSON.parse(body);}catch{return safeJson(400,{error:'Invalid JSON'});}
  if(!data||typeof data!=='object'||Array.isArray(data))
    return safeJson(400,{error:'Expected owner search query'});
  const item=data as Record<string,unknown>;
  if(Object.keys(item).sort().join(',')!=='query,search_confirmed'||item.search_confirmed!==true||
     typeof item.query!=='string'||item.query.trim().length<2||item.query.length>120||
     /[\x00-\x1f\x7f]/.test(item.query))
    return safeJson(400,{error:'A bounded, explicitly approved search query is required'});
  const query=item.query.trim();
  const url=new URL(WIKIPEDIA);
  for(const [k,v] of Object.entries({action:'query',list:'search',format:'json',utf8:'1',
    srnamespace:'0',srlimit:'3',srprop:'snippet',srsearch:query}))url.searchParams.set(k,v);
  try{
    const response=await fetch(url,{redirect:'error',cache:'no-store',signal:AbortSignal.timeout(6000),
      headers:{accept:'application/json','user-agent':'BeastBoxCOSMOS/0.7 (+https://github.com/NavisWORLD/The-beast-box-)'}});
    if(!response.ok||!response.headers.get('content-type')?.toLowerCase().includes('application/json'))
      return safeJson(502,{error:'Public Wikipedia search unavailable; no model call occurred'});
    if(Number(response.headers.get('content-length')||0)>MAX_BYTES)
      return safeJson(502,{error:'Public search response exceeded limit'});
    if(!response.body)return safeJson(502,{error:'Empty public search response'});
    const reader=response.body.getReader();
    const chunks:Uint8Array[]=[];let total=0;
    try{
      while(true){const {done,value}=await reader.read();if(done)break;
        total+=value.byteLength;
        if(total>MAX_BYTES){await reader.cancel();return safeJson(502,{error:'Public search response exceeded limit'});}
        chunks.push(value);
      }
    }finally{reader.releaseLock();}
    const bytes=new Uint8Array(total);let at=0;for(const c of chunks){bytes.set(c,at);at+=c.length;}
    const parsed:unknown=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
    if(!parsed||typeof parsed!=='object'||Array.isArray(parsed))
      return safeJson(502,{error:'Invalid public search response'});
    const search=(parsed as {query?:{search?:unknown}}).query?.search;
    if(!Array.isArray(search))return safeJson(502,{error:'Invalid public search results'});
    const results=search.slice(0,3).flatMap((entry:unknown)=>{
      if(!entry||typeof entry!=='object'||Array.isArray(entry))return [];
      const row=entry as Record<string,unknown>;
      if(typeof row.title!=='string'||typeof row.snippet!=='string'||row.title.length>160)return [];
      const title=trimText(row.title,120),snippet=trimText(row.snippet,360);
      if(!title||!snippet)return [];
      return [{title,snippet,url:'https://en.wikipedia.org/wiki/'+encodeURIComponent(row.title.replace(/ /g,'_'))}];
    });
    return new Response(JSON.stringify({schema:'cosmos-public-web-lookup-v1',source:'Wikipedia',
      retrieved_at:new Date().toISOString(),results,model_invoked:false,persisted:false}),{
        status:200,headers:{'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
  }catch{
    return safeJson(502,{error:'Public Wikipedia search failed or timed out; no model call occurred'});
  }
}
