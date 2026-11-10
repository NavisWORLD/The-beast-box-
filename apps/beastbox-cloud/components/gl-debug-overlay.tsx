'use client';
import {useEffect,useState} from 'react';
import {glDebugEnabled,installGlDebug,pageGlDebug,type GlDebugSnap} from '@/lib/three/gl-debug';
/** Visible only for ?gldebug=1. The flag check happens before any canvas patch. */
export default function GlDebugOverlay(){
 const [snap,setSnap]=useState<GlDebugSnap|null>(null);
 const [copied,setCopied]=useState(false);
 useEffect(()=>{
  if(!glDebugEnabled())return;
  installGlDebug();
  const read=()=>setSnap(pageGlDebug()?.snapshot()??null);
  read();
  const id=setInterval(read,500);
  return ()=>clearInterval(id);
 },[]);
 if(!snap)return null;
 const text=JSON.stringify(snap,null,2);
 const copy=()=>{const done=()=>setCopied(true);try{navigator.clipboard.writeText(text).then(done).catch(()=>{});}catch{}};
 return <aside data-gldebug="1" style={{position:'fixed',left:8,bottom:8,zIndex:80,maxWidth:'min(420px,92vw)',maxHeight:'46vh',overflow:'auto',padding:'8px 10px',borderRadius:8,background:'rgba(0,0,0,.82)',color:'#d8ffe8',font:'12px/1.35 ui-monospace,monospace'}}>
  <p style={{margin:'0 0 6px'}}>WebGL receipt. Live contexts {snap.live}. This panel only reads.</p>
  <ul style={{margin:'0 0 6px',paddingLeft:16}}>
   {snap.views.map(v=><li key={v.id}>{v.view} #{v.id} {v.disposed?'disposed':v.lost?'lost':'live'} {v.renderer||'renderer unknown'}</li>)}
  </ul>
  <button type="button" onClick={copy} style={{marginBottom:6}}>Copy receipt</button>
  {copied?<span> copied</span>:null}
  <textarea readOnly value={text} aria-label="WebGL debug receipt" style={{display:'block',width:'100%',height:120,background:'#111',color:'#d8ffe8',border:'1px solid #345',font:'11px/1.3 ui-monospace,monospace'}}/>
 </aside>;
}
