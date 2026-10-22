// Geyser Jelly sound (PR 3/4): event-only Web Audio. Nothing plays until an event fires (no ambient loop);
// the context is created lazily on the first event and respects the site mute event.
export function createGeyserSound(){
  let ctx:AudioContext|null=null,muted=false;
  const onMute=(e:any)=>{muted=!!(e?.detail?.muted??e?.detail);};if(typeof window!=='undefined')window.addEventListener('beastbox:spark-mute',onMute);
  const ac=()=>{if(muted)return null;try{if(!ctx){const C=(window as any).AudioContext||(window as any).webkitAudioContext;if(!C)return null;ctx=new C();}if(ctx!.state==='suspended')void ctx!.resume();return ctx;}catch{return null;}};
  const noise=(c:AudioContext,sec:number)=>{const b=c.createBuffer(1,Math.max(1,Math.floor(c.sampleRate*sec)),c.sampleRate);const d=b.getChannelData(0);for(let i=0;i<d.length;i++)d[i]=Math.random()*2-1;const s=c.createBufferSource();s.buffer=b;return s;};
  const env=(c:AudioContext,g:GainNode,a:number,peak:number,rel:number)=>{const t=c.currentTime;g.gain.setValueAtTime(0.0001,t);g.gain.exponentialRampToValueAtTime(peak,t+a);g.gain.exponentialRampToValueAtTime(0.0001,t+a+rel);};
  const play:Record<string,(c:AudioContext)=>void>={
    geyser:c=>{const n=noise(c,2.2),f=c.createBiquadFilter(),g=c.createGain();f.type='bandpass';f.frequency.setValueAtTime(300,c.currentTime);f.frequency.exponentialRampToValueAtTime(1800,c.currentTime+.6);n.connect(f).connect(g).connect(c.destination);env(c,g,.08,.35,2);n.start();},
    erupt:c=>{const n=noise(c,3),f=c.createBiquadFilter(),g=c.createGain();f.type='lowpass';f.frequency.value=180;n.connect(f).connect(g).connect(c.destination);env(c,g,.2,.6,2.6);n.start();const o=c.createOscillator(),og=c.createGain();o.frequency.value=38;o.connect(og).connect(c.destination);env(c,og,.2,.25,2.2);o.start();o.stop(c.currentTime+2.6);},
    tremor:c=>{const o=c.createOscillator(),g=c.createGain();o.type='sawtooth';o.frequency.value=29;const f=c.createBiquadFilter();f.type='lowpass';f.frequency.value=90;o.connect(f).connect(g).connect(c.destination);env(c,g,.1,.4,2.2);o.start();o.stop(c.currentTime+2.5);},
    blow:c=>{const n=noise(c,1),f=c.createBiquadFilter(),g=c.createGain();f.type='highpass';f.frequency.value=900;n.connect(f).connect(g).connect(c.destination);env(c,g,.05,.12,.8);n.start();},
    breach:c=>{const o=c.createOscillator(),g=c.createGain();o.type='sine';o.frequency.setValueAtTime(140,c.currentTime);o.frequency.exponentialRampToValueAtTime(70,c.currentTime+1.8);o.connect(g).connect(c.destination);env(c,g,.3,.22,1.6);o.start();o.stop(c.currentTime+2.1);},
    splash:c=>{const n=noise(c,1.2),f=c.createBiquadFilter(),g=c.createGain();f.type='lowpass';f.frequency.value=1200;n.connect(f).connect(g).connect(c.destination);env(c,g,.02,.45,1);n.start();},
    castoff:c=>{for(const [fr,dl] of [[146.8,0],[110,.55]] as const){const o=c.createOscillator(),g=c.createGain();o.type='sawtooth';o.frequency.value=fr;const f=c.createBiquadFilter();f.type='lowpass';f.frequency.value=700;o.connect(f).connect(g).connect(c.destination);const t=c.currentTime+dl;g.gain.setValueAtTime(.0001,t);g.gain.exponentialRampToValueAtTime(.18,t+.05);g.gain.exponentialRampToValueAtTime(.0001,t+.5);o.start(t);o.stop(t+.55);}},
  };
  return {event(name:string){const f=play[name];if(!f)return;const c=ac();if(!c)return;try{f(c);}catch{}},
    dispose(){if(typeof window!=='undefined')window.removeEventListener('beastbox:spark-mute',onMute);try{void ctx?.close();}catch{}ctx=null;}};
}
