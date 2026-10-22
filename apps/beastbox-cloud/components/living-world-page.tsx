'use client';
import dynamic from 'next/dynamic';
import {useBeastSession} from './beast-session';
const LivingWorld=dynamic(()=>import('./living-world'),{ssr:false});
export default function LivingWorldPage(){const {session}=useBeastSession();const b=session?.beast?.qbeast?.profile?.id?session.beast:null;
 return <LivingWorld genome={b?.genome||null} beastKey={b?.qbeast?.profile?.id||null} beastName={b?.displayName||null} onClose={()=>{location.href='/beast-cage';}}/>;}
