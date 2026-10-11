import {DIARY_LABELS,DIARY_SCHEMA,entryHash,genesisState,summarize} from '@/lib/zeref/zeref-diary.mjs';

export const revalidate=120;
const SOURCE='https://raw.githubusercontent.com/NavisWORLD/The-beast-box-/zeref-diary/zeref/latest.json';

/**
 * Zeref's diary, written by the scheduled loop on the data-only `zeref-diary`
 * branch. Public, read-only, cached ~2 min. Each recent entry's hash is
 * re-checked here; if the branch is unreachable the genesis state is returned
 * with ok:false (never an invented entry).
 */
export async function GET(){
 const headers={'Cache-Control':'public, s-maxage=120, stale-while-revalidate=600'};
 try{
  const res=await fetch(SOURCE,{next:{revalidate:120},signal:AbortSignal.timeout(6000)});
  if(!res.ok)throw new Error('diary http '+res.status);
  const data=await res.json();
  if(data?.schema!==DIARY_SCHEMA||data?.identity?.beast_id!==genesisState().identity.beast_id||!Array.isArray(data.recent))throw new Error('diary shape');
  const recent=data.recent.slice(0,12);
  const verified=recent.every((e:any)=>typeof e?.hash==='string'&&entryHash(e)===e.hash);
  return Response.json({ok:true,source:'zeref-diary branch (GitHub Actions loop)',verified,...data,recent,labels:DIARY_LABELS},{headers});
 }catch(error){
  return Response.json({ok:false,source:'genesis (loop output unreachable)',reason:error instanceof Error?error.message:'unavailable',verified:false,...summarize(genesisState(),[])},{headers});
 }
}
