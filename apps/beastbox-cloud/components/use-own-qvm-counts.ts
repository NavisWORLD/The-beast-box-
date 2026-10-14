'use client';
import {useEffect,useState} from 'react';
import {ownReceiptPath} from '../lib/pocket-sand.mjs';
import {validateRecordedQvmStimulus} from '../lib/companion/recorded-qvm-stimulus.mjs';
/** Loads ONLY the Beast's own mapped, validated Azure simulator receipt counts; otherwise null. */
export function useOwnQvmCounts(path:string|null):Record<string,number>|null{
 const own=ownReceiptPath(path);const [counts,setCounts]=useState<Record<string,number>|null>(null);
 useEffect(()=>{setCounts(null);if(!own)return;let live=true;
  fetch(own).then(r=>r.ok?r.json():null).then(j=>{if(!live||!j)return;try{setCounts(validateRecordedQvmStimulus(j).counts);}catch{}}).catch(()=>{});
  return()=>{live=false;};},[own]);
 return counts;
}
