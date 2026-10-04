/** Read only the approved public, derived recorded-count tables. */
export function expandRun(row){return {key:row.k,backend:row.b,job_id:row.j,pub_index:row.p,num_bits:row.n,shots:row.s,counts:Object.fromEntries(row.c.split(',').map(part=>{const [k,v]=part.split(':');return [k,Number(v)]})),counts_sha256:row.h};}
export async function loadSparkRuns(){
 const index=await fetch('/spark/user-seeds-20261004.json',{cache:'force-cache'}).then(r=>{if(!r.ok)throw Error('Recorded seed index unavailable.');return r.json()});
 const paths=['/spark/runs.json',...(index.shards||[])];
 if(paths.some(path=>!/^\/spark\/[a-z0-9-]+\.json$/.test(path)))throw Error('Unapproved recorded seed path.');
 const tables=await Promise.all(paths.map(path=>fetch(path,{cache:'force-cache'}).then(r=>{if(!r.ok)throw Error('Recorded seed table unavailable.');return r.json()})));
 return [...new Map(tables.flatMap(t=>(t.runs||[]).map(expandRun)).map(r=>[r.key,r])).values()];
}
