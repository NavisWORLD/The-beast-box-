'use client';
// A calm fallback if a page throws while rendering. The technical message stays in the console, not on the page.
import {useEffect} from 'react';
export default function RouteError({error,reset}:{error:Error&{digest?:string};reset:()=>void}){
 useEffect(()=>{console.error(error);},[error]);
 return <main data-route-error role="alert" style={{minHeight:'50vh',display:'grid',placeContent:'center',textAlign:'center',gap:12,padding:24}}>
  <h1 style={{fontSize:24,margin:0}}>That didn’t load.</h1>
  <p style={{margin:0,opacity:.8}}>Your beast is still here.</p>
  <p style={{margin:0}}><button type="button" onClick={()=>reset()} style={{padding:'10px 18px',borderRadius:10,border:'1px solid #6b5bd6',background:'#121833',color:'#fff',font:'inherit',cursor:'pointer'}}>Tap to try again</button></p>
 </main>;
}
