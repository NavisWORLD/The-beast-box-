'use client';
import {useEffect,useState} from 'react';
type P={label:string;beat:number;pulse_sha256:string;glow:number;question_pair:string;recorded_win_rate:number;honesty:string;at_utc:string};
export function ZerefSparkPulse(){
 const [p,setP]=useState<P|null>(null);
 useEffect(()=>{let on=true;const f=()=>fetch('/api/zeref/spark-pulse',{cache:'no-store'}).then(x=>x.ok?x.json():null).then(j=>{if(on)setP(j);}).catch(()=>{});
  f();const id=setInterval(f,10000);return()=>{on=false;clearInterval(id);};},[]);
 if(!p)return null;
 const a=0.35+0.65*p.glow;
 return <div data-spark-pulse style={{border:'2px solid #fcd34d',borderRadius:12,padding:10,margin:'0 0 10px',background:'#1a1033',color:'#fef3c7',overflowWrap:'anywhere',boxShadow:`0 0 ${Math.round(8+20*p.glow)}px rgba(252,211,77,${a})`}}>
  <div style={{fontSize:12,fontWeight:700}}>✨ Origin spark pulse <span data-label style={{fontSize:10,border:'1px solid #fcd34d',borderRadius:6,padding:'0 4px'}}>{p.label}</span></div>
  <div style={{fontSize:14,margin:'4px 0'}}>Beat #{p.beat.toLocaleString('en-US')} · {p.question_pair} · recorded win {(p.recorded_win_rate*100).toFixed(1)}%</div>
  <div style={{fontSize:11,opacity:.8,fontFamily:'monospace'}}>{p.pulse_sha256.slice(0,16)}…</div>
  <div style={{fontSize:11,opacity:.75}}>{p.honesty}</div>
 </div>;
}
