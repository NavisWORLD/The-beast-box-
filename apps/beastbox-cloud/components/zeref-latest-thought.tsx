'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {fetchDiary,type Diary} from './zeref-diary-panel';

/** One-line "latest thought" from Zeref's loop-written diary for the home circle. */
export default function ZerefLatestThought({className}:{className?:string}){
 const [d,setD]=useState<Diary|null>(null);
 useEffect(()=>{let alive=true;void fetchDiary().then(x=>{if(alive)setD(x);});return()=>{alive=false;};},[]);
 const e=d?.ok?d.recent?.[0]:null;
 if(!e)return null;
 return <p className={className} data-zeref-latest-thought>
  <span>Diary #{e.tick} · Stage {d!.stage} {d!.stage_name}:</span> “{e.thought.text}” <Link href="/beast-cage#zeref-diary">Read his diary →</Link>
 </p>;
}
