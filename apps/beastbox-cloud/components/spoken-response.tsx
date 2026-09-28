'use client';
import {useEffect,useRef,useState} from 'react';
import {Volume2,VolumeX} from 'lucide-react';

/** Optional browser speech synthesis. Nothing is recorded or auto-played. */
export default function SpokenResponse({text}:{text:string}){
 const [speaking,setSpeaking]=useState(false),[error,setError]=useState('');
 const current=useRef<SpeechSynthesisUtterance|null>(null);
 useEffect(()=>()=>{if(current.current&&typeof window!=='undefined'&&'speechSynthesis' in window){
  window.speechSynthesis.cancel();current.current=null;
 }},[]);
 function toggle(){
  if(typeof window==='undefined'||!('speechSynthesis' in window)||!('SpeechSynthesisUtterance' in window)){
   setError('Read aloud is unsupported by this browser.');return;
  }
  if(speaking){window.speechSynthesis.cancel();current.current=null;setSpeaking(false);return;}
  if(!text.trim())return;
  setError('');
  const utterance=new SpeechSynthesisUtterance(text.slice(0,650));
  utterance.lang='en-US';utterance.rate=1;utterance.pitch=1;
  utterance.onend=()=>{if(current.current===utterance){current.current=null;setSpeaking(false);}};
  utterance.onerror=()=>{if(current.current===utterance){
   current.current=null;setSpeaking(false);setError('Speech playback stopped or unavailable.');
  }};
  current.current=utterance;
  try{window.speechSynthesis.cancel();window.speechSynthesis.speak(utterance);setSpeaking(true);}
  catch{current.current=null;setSpeaking(false);setError('Speech playback requires a supported device.');}
 }
 return <span className="spoken-response">
  <button type="button" className="outline-action" onClick={toggle} aria-label={speaking?'Stop reading reply aloud':'Read reply aloud'}>
   {speaking?<VolumeX size={14}/>:<Volume2 size={14}/>} {speaking?'Stop voice':'Read aloud'}
  </button>
  {error?<small role="status">{error}</small>:null}
 </span>;
}
