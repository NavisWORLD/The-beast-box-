// Cory's 12D Cosmic Synapse math -> procedural texture fields (seeded per creature).
// node cst_textures.mjs <seed> <outdir>   writes float fields as PPM/PGM; cst_textures_png.py turns them into maps.
import {createCSTState,stepCSTState,lorenzStep,seededRng} from '../../lib/physics/cst-integrator.mjs';
import fs from 'node:fs';
const seed=process.argv[2]||'res_nyxbean',out=process.argv[3]||'.';const N=512;
const R=seededRng('tex:'+seed);
const F=()=>new Float32Array(N*N);
// 1) Lorenz trails: density (nebula wisps / fur clumps) + flow direction (fur comb direction)
const dens=F(),fx=F(),fy=F();
for(let w=0;w<6;w++){const S=createCSTState(seed+':'+w);const L=S.L;let px=null,py=null;
 for(let i=0;i<60000;i++){lorenzStep(L,.004,{arousal:S.ch.arousal,qe:S.ch.quantum_entropy});
  const x=((L.x/48+.5)+w*.17)%1,y=(L.z/52)%1;const ix=(x*N)|0,iy=(y*N)|0;if(ix<0||iy<0||ix>=N||iy>=N){px=null;continue;}
  const k=iy*N+ix;dens[k]+=1;if(px!==null){fx[k]+=x-px;fy[k]+=y-py;}px=x;py=y;}}
// 2) coherence field: a grid of CST cells, each integrated from its own seed; coherence + chaos sampled after settling
const G=24,coh=new Float32Array(G*G),cha=new Float32Array(G*G);
for(let j=0;j<G;j++)for(let i=0;i<G;i++){const S=createCSTState(`${seed}:c${i},${j}`,{emotion:{valence:.4+R()*.4,arousal:R()}});for(let t=0;t<240;t++)stepCSTState(S,1/60);coh[j*G+i]=S.ch.coherence;cha[j*G+i]=S.ch.chaos;}
// 3) Hebbian star clustering: points wire together (Hebbian weight grows with proximity), clusters pull in
const S0=createCSTState(seed+':stars');const P=[];for(let i=0;i<260;i++)P.push({x:R(),y:R(),w:.2+R()*.8});
const eta=.6*S0.hebb;
for(let it=0;it<30;it++)for(const a of P){let ax=0,ay=0,ws=0;for(const b of P){if(a===b)continue;const d=Math.hypot(a.x-b.x,a.y-b.y);if(d>.12)continue;const h=eta*a.w*b.w*(1-d/.12);ax+=(b.x-a.x)*h;ay+=(b.y-a.y)*h;ws+=h;}
 a.x+=ax*.08;a.y+=ay*.08;a.w=Math.min(1.5,a.w+ws*.01);}
const wr=(name,arr,n)=>{const m=arr.reduce((a,b)=>b>a?b:a,0)||1;const b=Buffer.alloc(n*n);for(let i=0;i<n*n;i++)b[i]=Math.min(255,arr[i]/m*255);fs.writeFileSync(`${out}/${name}.pgm`,Buffer.concat([Buffer.from(`P5 ${n} ${n} 255\n`),b]));};
const dl=dens.map(v=>Math.log1p(v));wr('lorenz_density',dl,N);
const fl=Buffer.alloc(N*N*3);for(let i=0;i<N*N;i++){const l=Math.hypot(fx[i],fy[i])||1;fl[i*3]=(fx[i]/l*.5+.5)*255;fl[i*3+1]=(fy[i]/l*.5+.5)*255;fl[i*3+2]=128;}
fs.writeFileSync(`${out}/lorenz_flow.ppm`,Buffer.concat([Buffer.from(`P6 ${N} ${N} 255\n`),fl]));
wr('coherence',coh,G);wr('chaos',cha,G);
fs.writeFileSync(`${out}/hebb_stars.json`,JSON.stringify(P));
console.log('cst fields',seed,'hebb',S0.hebb.toFixed(3));
