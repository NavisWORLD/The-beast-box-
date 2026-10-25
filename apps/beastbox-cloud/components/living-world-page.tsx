'use client';
import {beastDisplayName} from '../lib/companion/beast-name.mjs';
import dynamic from 'next/dynamic';
import {useBeastSession} from './beast-session';
const LivingWorld=dynamic(()=>import('./living-world'),{ssr:false,loading:()=><WorldLoading/>});
function WorldLoading(){return <div role="status" aria-live="polite" data-lw-loading style={{position:'fixed',inset:0,display:'grid',placeItems:'center',background:'#05030f',color:'#d9ccff',font:'600 15px system-ui,sans-serif',zIndex:2147483000}}>Opening your tiny world…</div>;}
export default function LivingWorldPage(){const {session,ready}=useBeastSession();if(!ready)return <WorldLoading/>;const b=session?.beast?.qbeast?.profile?.id?session.beast:null;
 return <LivingWorld genome={b?.genome||null} beastKey={b?.qbeast?.profile?.id||null} beastName={beastDisplayName(b)} onClose={()=>{location.href='/beast-cage';}}/>;}
