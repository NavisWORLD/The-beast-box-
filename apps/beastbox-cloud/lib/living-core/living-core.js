import {buildLineOverlay,buildAccessoryOverlay,buildHornMeshes} from './overlay.js';
// living-core.js — reusable "Living Core" builder for Beast Box sprites.
// sprite -> signed depth field -> CST-driven particles + cached marching-cubes body,
// with eye / lid / tail / whisker rigs from auto-detected regions, a star-dust birth,
// idle bit-trading with the surrounding dust, contact shadow and env light pickup.
// CST math ported from apps/beastbox-cloud/lib/physics/cst-integrator.mjs.
const LORENZ={sigma:10,rho:28,beta:8/3},GAIN={lorenzRho:.30,lorenzQ:2.0,hebbCoh:.20};
const clamp=(x,a=0,b=1)=>x<a?a:x>b?b:x;
function makeCST(){const S={L:{x:.12,y:.25,z:.35},hebb:.3,coh:.6,arousal:.45,qe:.5};
 S.step=dt=>{const L=S.L,rho=LORENZ.rho*(1+GAIN.lorenzRho*(S.arousal-.5));
  const dx=LORENZ.sigma*(L.y-L.x)+GAIN.lorenzQ*(S.qe-.5),dy=L.x*(rho-L.z)-L.y,dz=L.x*L.y-LORENZ.beta*L.z;
  L.x+=dx*dt;L.y+=dy*dt;L.z+=dz*dt;const chaos=clamp(Math.hypot(dx,dy,dz)/400);
  S.coh=clamp(clamp(1-chaos*.8)+GAIN.hebbCoh*(S.hebb-.25));S.hebb=clamp(S.hebb+dt*(.5*S.coh*(1-S.hebb)-.2*S.hebb));S.arousal+=((S.arT??.45)-S.arousal)*dt*.8;};return S;}
// CST flow field: Lorenz-phase-modulated curl-like swirl (used for birth + star dust)
export function cstFlow(x,y,z,t,S,out){const a=S.L.x*.04,b=S.L.y*.04,c=(S.L.z-25)*.04;
 out[0]=Math.sin(y*.55+t*.4+a)-Math.cos(z*.47+b)*.8-x*.05;out[1]=Math.sin(z*.5+t*.33+b)*.7-Math.cos(x*.52+c)*.6-y*.05;out[2]=Math.sin(x*.45+t*.37+c)-Math.cos(y*.6+a)*.8-z*.05;return out;}
// Danny Phantom motion constants (cosmo-study/research/danny_phantom_motion.md §2)
// Beast Box Motion Bible BB constants (cosmo-study/research/beastbox_motion_bible.md §1, master reference)
export const BB={holdExpression:12/24,holdStrong:16/24,holdEntry:18/24,anticipate:4/24,snapIn:3/24,overshoot:2/24,settle:5/24,squashHit:.82,stretchLeap:1.18,
 idleBreathHz:.35,idleBobHz:.55,idleBobAmp:.02,hopAir:10/24,landSettle:6/24,ringForm:4/24,ringSweep:10/24,ringSparkle:8/24,
 // livingCore.morph (§4.1): ghost ring + digivolve data/wireframe reform, ~2.0s
 morphCharge:.4,morphRewrite:.9,morphBurst:.2,morphReveal:.5};
export const DP={anticipate:4/24,snapIn:3/24,overshoot:2/24,settle:5/24,holdExpression:12/24,holdStrong:16/24,squashHit:.82,stretchLeap:1.18,
 ringForm:4/24,ringSweep:10/24,ringSparkle:8/24,ringTotal:18/24,blinkMin:2.5,blinkMax:4.5,blinkDur:.11,calmTailHz:.4,happyTailHz:2.2,happyTailAmp:1.6,headTiltDeg:4};
export function cubicBezier(x1,y1,x2,y2){return x=>{if(x<=0)return 0;if(x>=1)return 1;let t=x;for(let i=0;i<6;i++){const cx=3*x1*t*(1-t)**2+3*x2*t*t*(1-t)+t**3-x;const d=3*x1*(1-t)**2+6*(x2-x1)*t*(1-t)+3*(1-x2)*t*t;if(Math.abs(d)<1e-6)break;t=Math.min(1,Math.max(0,t-cx/d));}return 3*y1*t*(1-t)**2+3*y2*t*t*(1-t)+t**3;};}
export const EASE={snapOut:cubicBezier(.15,.85,.25,1),snapIn:cubicBezier(.55,0,.85,.45),cushion:cubicBezier(.33,0,.2,1),ghost:cubicBezier(.2,.8,.2,1)};
// overshootSettle spring (ω≈14, ζ≈0.55): unit step response
const springStep=(t,w=14,z=.55)=>{const wd=w*Math.sqrt(1-z*z);return 1-Math.exp(-z*w*t)*(Math.cos(wd*t)+z/Math.sqrt(1-z*z)*Math.sin(wd*t));};
// hop timeline: anticipate -> snap/leap (stretch) -> land squash (snapIn) -> spring overshoot+settle -> moving hold
const T_AIR=BB.hopAir*1.35; // bible hopAir 0.417s, x1.35 for the kitten's 1-unit leap height
function hopPose(h){const a=DP.anticipate,l=a+T_AIR,s=l+DP.snapIn;
 if(h<a){const e=EASE.cushion(h/a);return {y:-.06*e,sy:1-.10*e,phase:0};}
 if(h<l){const u=(h-a)/T_AIR;const y=Math.sin(Math.PI*u);const st=u<.5?1+(DP.stretchLeap-1)*(1-EASE.snapOut(u*2))*1+(DP.stretchLeap-1)*0:1+(DP.stretchLeap-1)*.5*EASE.snapIn((u-.5)*2);return {y,sy:u<.08?.9+(DP.stretchLeap-.9)*(u/.08):st,phase:1};}
 if(h<s){const e=EASE.snapIn((h-l)/DP.snapIn);return {y:0,sy:1+(DP.squashHit-1)*e,phase:2};}
 const r=springStep(h-s);return {y:0,sy:DP.squashHit+(1-DP.squashHit)*r,phase:3};}
function rng(seed){let a=seed>>>0||1;return()=>{a^=a<<13;a>>>=0;a^=a>>>17;a^=a<<5;a>>>=0;return a/4294967296;};}

let o_bridge=1.6;async function loadSprite(src,targetH,smooth=true,attach=true){const img=new Image();img.src=src;await img.decode();
 const c0=document.createElement('canvas');c0.width=img.width;c0.height=img.height;const x0=c0.getContext('2d');x0.drawImage(img,0,0);
 const d0=x0.getImageData(0,0,img.width,img.height).data;let x1=1e9,y1=1e9,x2=-1,y2=-1;
 for(let y=0;y<img.height;y++)for(let x=0;x<img.width;x++)if(d0[(y*img.width+x)*4+3]>128){x1=Math.min(x1,x);y1=Math.min(y1,y);x2=Math.max(x2,x);y2=Math.max(y2,y);}
 const bw=x2-x1+1,bh=y2-y1+1,down=bh>targetH*1.3,s=down?targetH/bh:Math.max(1,Math.round(targetH/bh)),pad=8;const W=Math.round(bw*s)+pad*2,H=Math.round(bh*s)+pad*2;
 const cv=document.createElement('canvas');cv.width=W;cv.height=H;const cx=cv.getContext('2d');cx.imageSmoothingEnabled=down;cx.imageSmoothingQuality='high';cx.drawImage(img,x1,y1,bw,bh,pad,pad,bw*s,bh*s);
 const im=cx.getImageData(0,0,W,H),D=im.data;
 if(s>=2&&smooth){ // smooth the enlarged silhouette: bilinear alpha, thresholded -> rounded edges instead of stair steps
  const c2=document.createElement('canvas');c2.width=W;c2.height=H;const g2=c2.getContext('2d');g2.imageSmoothingEnabled=true;g2.imageSmoothingQuality='high';g2.drawImage(img,x1,y1,bw,bh,pad,pad,bw*s,bh*s);
  const SA=g2.getImageData(0,0,W,H).data;const na=new Uint8Array(W*H);for(let k=0;k<W*H;k++)na[k]=SA[k*4+3]>128?1:0;
  for(let it=0;it<s;it++)for(let y=1;y<H-1;y++)for(let x=1;x<W-1;x++){const k=y*W+x;if(na[k]&&D[k*4+3]<128){for(const q of [k-1,k+1,k-W,k+W])if(D[q*4+3]>=128){D[k*4]=D[q*4];D[k*4+1]=D[q*4+1];D[k*4+2]=D[q*4+2];D[k*4+3]=254;break;}}}
  for(let k=0;k<W*H;k++)if(!na[k])D[k*4+3]=0;}
 const attached=[];
 if(attach){const A=new Uint8Array(W*H);for(let k=0;k<W*H;k++)A[k]=D[k*4+3]>128?1:0;const lab=new Int32Array(W*H).fill(-1);const comps=[];
  for(let k=0;k<W*H;k++){if(!A[k]||lab[k]>=0)continue;const id=comps.length,list=[k];lab[k]=id;for(let i=0;i<list.length;i++){const q=list[i],x=q%W;for(const r of [q-1,q+1,q-W,q+W]){if(r<0||r>=W*H||(r===q-1&&x===0)||(r===q+1&&x===W-1))continue;if(A[r]&&lab[r]<0){lab[r]=id;list.push(r);}}}comps.push(list);}
  comps.sort((a,b)=>b.length-a.length);const main=new Set(comps[0]||[]);const edge=(comps[0]||[]).filter(q=>!A[q-1]||!A[q+1]||!A[q-W]||!A[q+W]);
  for(const cp of comps.slice(1)){if(cp.length<Math.max(30,4*s*s))continue;let best=1e9,bc=0,bm=0;const ce=cp.filter((q,i)=>i%2===0);
   for(const c of ce){const cx_=c%W,cy_=(c/W)|0;for(let i=0;i<edge.length;i+=2){const m=edge[i];const d=(m%W-cx_)**2+(((m/W)|0)-cy_)**2;if(d<best){best=d;bc=c;bm=m;}}}
   const d=Math.sqrt(best),ov=1.6*s;if(d<=ov)continue;const f=(d-ov)/d;const dx=Math.round((bm%W-bc%W)*f),dy=Math.round((((bm/W)|0)-((bc/W)|0))*f);
   const buf=cp.map(q=>[q,D[q*4],D[q*4+1],D[q*4+2],D[q*4+3]]);for(const q of cp)D[q*4+3]=0;
   for(const [q,r,g,b,a] of buf){const x=q%W+dx,y=((q/W)|0)+dy;if(x<0||y<0||x>=W||y>=H)continue;const k=(y*W+x)*4;D[k]=r;D[k+1]=g;D[k+2]=b;D[k+3]=a;}// blend: stamp a tapered bridge from the moved part into the head so the depth field fuses them
   {const ax=bc%W+dx,ay=((bc/W)|0)+dy,bx=bm%W,by=(bm/W)|0;const k0=bc*4;const col=[buf[0][1],buf[0][2],buf[0][3]];const rr=Math.max(2,s*(o_bridge??1.6));
    for(let u=0;u<=1;u+=.05){const cx_=ax+(bx-ax)*(u+.35),cy_=ay+(by-ay)*(u+.35);const r=rr*(1.25-.35*u);for(let yy=-r;yy<=r;yy++)for(let xx=-r;xx<=r;xx++){if(xx*xx+yy*yy>r*r)continue;const X=Math.round(cx_+xx),Y=Math.round(cy_+yy);if(X<0||Y<0||X>=W||Y>=H)continue;const k=(Y*W+X)*4;if(D[k+3]<128){D[k]=col[0];D[k+1]=col[1];D[k+2]=col[2];D[k+3]=255;}}}}
   attached.push({px:cp.length,dx,dy});}}
 const toL=(x,y)=>[(x-x1)*s+pad,(y-y1)*s+pad];
 return {W,H,D,scale:s,toL,attached};}

export async function buildLivingCore({THREE,MarchingCubes,src,opts={}}){
 const o=Object.assign({eyeTop:.62,targetH:200,eye:'auto',eyeMinR:0.055,furBlack:false,whiskers:'auto',irisColor:null,hatSway:true,seed:7},opts);
 const R0=rng(o.seed);const S=makeCST();
 o_bridge=o.bridge??1.6;const {W,H,D,scale:SPX,toL,attached}=await loadSprite(src,o.targetH,o.smooth!==false,o.attachParts!==false);
 const A=new Uint8Array(W*H);for(let k=0;k<W*H;k++)A[k]=D[k*4+3]>128?1:0;
 // wings: saturated blue-violet lateral regions -> lifted out of the body into separate membrane sheets
 if(o.wings&&o.wings.excludeSrc)o.wings.exclude=o.wings.excludeSrc.map(e=>{const [a,b]=toL(e.cx,e.cy),[c]=toL(e.cx+e.rx,e.cy),[,d]=toL(e.cx,e.cy+e.ry);return {cx:a,cy:b,rx:Math.abs(c-a),ry:Math.abs(d-b)};});
 let fillMs=0,icicleCount=0;const wingPx=[];const wingLeft=new Uint8Array(W*H);let wcx=0,wn0=0;for(let k=0;k<W*H;k++)if(A[k]){wcx+=k%W;wn0++;}wcx/=wn0||1;
 if(o.wings){const WG=new Uint8Array(W*H);let ax1=W,ax2=0;for(let k=0;k<W*H;k++)if(A[k]){const x=k%W;ax1=Math.min(ax1,x);ax2=Math.max(ax2,x);}const bwA=ax2-ax1;
  for(let k=0;k<W*H;k++){if(!A[k])continue;const x=k%W,y=(k/W)|0,r=D[k*4]/255,g=D[k*4+1]/255,b=D[k*4+2]/255;if(!(o.wings.exclude||[]).some(e=>((x-e.cx)/e.rx)**2+((y-e.cy)/e.ry)**2<=1)&&Math.abs(x-wcx)>bwA*o.wings.inner&&y>H*o.wings.y1&&y<H*o.wings.y2&&b>.28&&b-g>.08&&(Math.abs(x-wcx)>bwA*o.wings.outer||b>.5))WG[k]=1;}
  // grow into the wing's own dark veins within the lateral band
  for(let it=0;it<3;it++){const n2=new Uint8Array(WG);for(let y=1;y<H-1;y++)for(let x=1;x<W-1;x++){const k=y*W+x;if(!WG[k]&&A[k]&&!(o.wings.exclude||[]).some(e=>((x-e.cx)/e.rx)**2+((y-e.cy)/e.ry)**2<=1)&&Math.abs(x-wcx)>bwA*o.wings.outer&&(WG[k-1]||WG[k+1]||WG[k-W]||WG[k+W]))n2[k]=1;}WG.set(n2);}
  for(let k=0;k<W*H;k++){if(!WG[k]&&A[k]){const x=k%W,b=D[k*4+2]/255,g=D[k*4+1]/255;if(Math.abs(x-wcx)>bwA*.17&&b>.3&&b-g>.1&&(D[k*4]+D[k*4+1]+D[k*4+2])/765<.6)wingLeft[k]=1;}}
  for(let k=0;k<W*H;k++)if(WG[k]){wingPx.push([k%W,(k/W)|0,D[k*4],D[k*4+1],D[k*4+2]]);A[k]=0;D[k*4+3]=0;}
  {const r=o.wings.fillR??6;const box=(src,er)=>{const S=new Int32Array((W+1)*(H+1));for(let y=0;y<H;y++){let row=0;for(let x=0;x<W;x++){row+=src[y*W+x];S[(y+1)*(W+1)+x+1]=S[y*(W+1)+x+1]+row;}}const out=new Uint8Array(W*H);for(let y=0;y<H;y++){const y0=Math.max(0,y-r),y1=Math.min(H,y+r+1);for(let x=0;x<W;x++){const x0=Math.max(0,x-r),x1=Math.min(W,x+r+1);const sm=S[y1*(W+1)+x1]-S[y0*(W+1)+x1]-S[y1*(W+1)+x0]+S[y0*(W+1)+x0];out[y*W+x]=er?(sm===(2*r+1)*(2*r+1)?1:0):(sm>0?1:0);}}return out;};const t0=performance.now();const cl=box(box(A,0),1);for(let k=0;k<W*H;k++)if(cl[k]&&!A[k]&&WG[k]){A[k]=1;D[k*4+3]=255;wingLeft[k]=1;}fillMs=performance.now()-t0;}}
 let trimEdges=0;const blur=(src,r)=>{const t=new Float32Array(W*H),q=new Float32Array(W*H);for(let y=0;y<H;y++)for(let x=0;x<W;x++){let s=0;for(let i=-r;i<=r;i++)s+=src[y*W+Math.min(W-1,Math.max(0,x+i))];t[y*W+x]=s/(2*r+1);}
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){let s=0;for(let i=-r;i<=r;i++)s+=t[Math.min(H-1,Math.max(0,y+i))*W+x];q[y*W+x]=s/(2*r+1);}return q;};
 function chamfer(inside){const d=new Float32Array(W*H);for(let k=0;k<W*H;k++)d[k]=(A[k]===inside)?1e4:0;
  for(let pass=0;pass<2;pass++){const fw=pass==0,s=fw?-1:1;for(let yy=0;yy<H;yy++){const y=fw?yy:H-1-yy;for(let xx=0;xx<W;xx++){const x=fw?xx:W-1-xx,k=y*W+x;if(!d[k])continue;
   for(const [a,b,c] of [[s,0,1],[0,s,1],[s,s,1.414],[-s,s,1.414]]){const X=x+a,Y=y+b;const v=(X<0||Y<0||X>=W||Y>=H)?(inside?0:1e4):d[Y*W+X];if(v+c<d[k])d[k]=v+c;}}}}return d;}
 const dIn=chamfer(1),dOut=chamfer(0);
 // ---- signed depth field ----
 let hF=new Float32Array(W*H);for(let k=0;k<W*H;k++)hF[k]=A[k]?3.1*Math.sqrt(dIn[k]+.5)*(H/216)**.5:-dOut[k];
 // ---- shaped-part body: smooth-union SDF of authored primitives -> per-pixel front depth ----
 let NT=null,NF=null,sdfInfo=null,sdf3=null,ZH=null,ZC=null,H0=null,FB=null;if(o.sdfParts){const SP=o.sdfParts,sc=toL(1,0)[0]-toL(0,0)[0],K=(SP.k??18)*sc;
  const parts=SP.parts.map(p=>{if(p.type==='cap'){const pts=p.pts.map(q=>{const [x,y]=toL(q[0],q[1]);return [x,y,(q[2]??0)*sc];});return {type:'cap',pts,r:p.r.map(v=>v*sc),k:(p.k??SP.k??18)*sc};}const [x,y]=toL(p.c[0],p.c[1]);return {type:'ell',sub:!!p.sub,c:[x,y,(p.c[2]??0)*sc],r:p.r.map(v=>v*sc),k:(p.k??SP.k??18)*sc};});
  const smin=(a,b,k)=>{const h=Math.max(k-Math.abs(a-b),0)/k;return Math.min(a,b)-h*h*k*.25;};
  const dEll=(p,P)=>{const qx=(P[0]-p.c[0])/p.r[0],qy=(P[1]-p.c[1])/p.r[1],qz=(P[2]-p.c[2])/p.r[2];const l=Math.hypot(qx,qy,qz);return (l-1)*Math.min(...p.r);};
  const dCap=(p,P)=>{let best=1e9;for(let i=0;i<p.pts.length-1;i++){const a=p.pts[i],b=p.pts[i+1];const ab=[b[0]-a[0],b[1]-a[1],b[2]-a[2]],ap=[P[0]-a[0],P[1]-a[1],P[2]-a[2]];const L2=ab[0]**2+ab[1]**2+ab[2]**2;const t=Math.max(0,Math.min(1,(ap[0]*ab[0]+ap[1]*ab[1]+ap[2]*ab[2])/L2));const d=Math.hypot(ap[0]-ab[0]*t,ap[1]-ab[1]*t,ap[2]-ab[2]*t);const u=(i+t)/(p.pts.length-1);const r=p.r[0]+(p.r[1]-p.r[0])*u;best=Math.min(best,d-r);}return best;};
  const sdf=P=>{let d=1e9;for(const p of parts){if(p.sub)continue;const dp=p.type==='cap'?dCap(p,P):dEll(p,P);d=d>1e8?dp:smin(d,dp,p.k);}for(const p of parts){if(!p.sub)continue;const dp=dEll(p,P);d=-smin(-d,dp,p.k);}return d;};
  sdf3=sdf;ZH=new Float32Array(W*H);ZC=new Float32Array(W*H);FB=new Uint8Array(W*H);let hit=0,fb=0;const zMax=(RES_GUESS=>RES_GUESS)(Math.max(W,H)*.6);
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(!A[k])continue;let lo=-zMax,hi=zMax,inside=false;
   // find any inside sample along z
   let zin=null;for(let z=-zMax;z<=zMax;z+=zMax/12){if(sdf([x,y,z])<0){zin=z;break;}}
   if(zin===null){hF[k]=Math.min(hF[k],SP.fallback??4);ZH[k]=hF[k];ZC[k]=0;FB[k]=1;fb++;continue;}
   lo=zin;hi=zMax;for(let i=0;i<14;i++){const m=(lo+hi)/2;if(sdf([x,y,m])<0)lo=m;else hi=m;}const zf=Math.max(.5,lo);let a2=-zMax,b2=zin;for(let i=0;i<14;i++){const m=(a2+b2)/2;if(sdf([x,y,m])<0)b2=m;else a2=m;}hF[k]=zf;ZH[k]=Math.max(.5,(zf-b2)/2);ZC[k]=(zf+b2)/2;hit++;}
  if(SP.noFallback){NF=new Uint8Array(W*H);for(const e of SP.noFallback){const [ex,ey]=toL(e.cx,e.cy),[ex2]=toL(e.cx+e.rx,0),[,ey2]=toL(0,e.cy+e.ry);const rx=Math.abs(ex2-ex),ry=Math.abs(ey2-ey);for(let y=0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(FB[k]&&((x-ex)/rx)**2+((y-ey)/ry)**2<=1)NF[k]=1;}}}
  if(SP.noTrim){NT=new Uint8Array(W*H);for(const e of SP.noTrim){const [ex,ey]=toL(e.cx,e.cy),[ex2]=toL(e.cx+e.rx,0),[,ey2]=toL(0,e.cy+e.ry);const rx=Math.abs(ex2-ex),ry=Math.abs(ey2-ey);for(let y=0;y<H;y++)for(let x=0;x<W;x++)if(((x-ex)/rx)**2+((y-ey)/ry)**2<=1)NT[y*W+x]=1;}}
  sdfInfo={hit,fallback:fb,parts:parts.length};}

 const BR=Math.max(2,Math.round(SPX*.9));hF=blur(blur(hF,BR),BR);
 if(o.sdfParts)H0=new Float32Array(hF);
 const lum=k=>(D[k*4]*.3+D[k*4+1]*.55+D[k*4+2]*.15)/255;
 // outline ink -> creases
 const OL=new Float32Array(W*H);for(let k=0;k<W*H;k++)if(A[k]&&lum(k)<(o.inkLum??.07)&&dIn[k]>1.5)OL[k]=1;
 const OLb=blur(blur(OL,o.creaseBlur??1),o.creaseBlur??1);for(let k=0;k<W*H;k++)if(A[k])hF[k]-=(o.creaseK??2.2)*OLb[k];
 // separate depth lobes (limbs, horns, ears): each gets its own rounded profile + a groove where it meets the body
 if(o.lobes)for(const L of o.lobes){const [cx,cy]=toL(L.cx,L.cy),[x2]=toL(L.cx+L.rx,0),[,y2]=toL(0,L.cy+L.ry),rx=Math.abs(x2-cx),ry=Math.abs(y2-cy);const M=new Uint8Array(W*H);for(let y=0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(A[k]&&((x-cx)/rx)**2+((y-cy)/ry)**2<=1)M[k]=1;}
  const d=new Float32Array(W*H);for(let k=0;k<W*H;k++)d[k]=M[k]?1e4:0;for(let y=0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(!M[k])continue;if(x>0)d[k]=Math.min(d[k],d[k-1]+1);if(y>0)d[k]=Math.min(d[k],d[k-W]+1);if(x>0&&y>0)d[k]=Math.min(d[k],d[k-W-1]+1.414);if(x<W-1&&y>0)d[k]=Math.min(d[k],d[k-W+1]+1.414);}
  for(let y=H-1;y>=0;y--)for(let x=W-1;x>=0;x--){const k=y*W+x;if(!M[k])continue;if(x<W-1)d[k]=Math.min(d[k],d[k+1]+1);if(y<H-1)d[k]=Math.min(d[k],d[k+W]+1);if(x<W-1&&y<H-1)d[k]=Math.min(d[k],d[k+W+1]+1.414);if(x>0&&y<H-1)d[k]=Math.min(d[k],d[k+W-1]+1.414);}
  for(let k=0;k<W*H;k++)if(M[k]){const y=(k/W)|0;hF[k]=(L.k??3.1)*Math.sqrt(d[k]+.5)*(H/216)**.5+(L.z??0);if(L.ridges)hF[k]-=L.ridges*(.5+.5*Math.cos((y-cy)/ry*Math.PI*(L.rings??4)))*Math.min(1,d[k]/2);if(L.tip)hF[k]+=L.tip*Math.max(0,(cy-y)/ry);}}
 if(o.smoothH){const m=blur(blur(hF,o.smoothH),o.smoothH);for(let k=0;k<W*H;k++)if(A[k])hF[k]=hF[k]*.3+m[k]*.7;}
 const C=new Float32Array(W*H*3),has=new Uint8Array(A);for(let k=0;k<W*H;k++){if(OL[k]||wingLeft[k])has[k]=0;if(o.edgeRecolor&&dIn[k]<o.edgeRecolor&&!(lum(k)>.72))has[k]=0;C[k*3]=D[k*4]/255;C[k*3+1]=D[k*4+1]/255;C[k*3+2]=D[k*4+2]/255;}
 for(let it=0;it<(o.edgeRecolor?Math.ceil(o.edgeRecolor)+10:10);it++){const nh=new Uint8Array(has);for(let y=1;y<H-1;y++)for(let x=1;x<W-1;x++){const k=y*W+x;if(has[k])continue;for(const q of [k-1,k+1,k-W,k+W])if(has[q]){C[k*3]=C[q*3];C[k*3+1]=C[q*3+1];C[k*3+2]=C[q*3+2];nh[k]=1;break;}}has.set(nh);}
 // ---- region detection ----
 let bx1=W,by1=H,bx2=0,by2=0,cxm=0,cym=0,cn=0,hx=0,hn=0;for(let y=0;y<H;y++)for(let x=0;x<W;x++)if(A[y*W+x]&&dIn[y*W+x]>3){bx1=Math.min(bx1,x);bx2=Math.max(bx2,x);by1=Math.min(by1,y);by2=Math.max(by2,y);cxm+=x;cym+=y;cn++;}
 cxm/=cn;cym/=cn;const BH=by2-by1;
 const eyeRule=o.eye==='purple'?(r,g,b)=>b>.45&&b>g*1.25&&(r+b)>.85:(r,g,b)=>(r*.3+g*.55+b*.15)>.62&&Math.max(r,g,b)-Math.min(r,g,b)<.35;
 const cand=[];for(let y=by1;y<by1+BH*o.eyeTop;y++)for(let x=0;x<W;x++){const k=y*W+x;if(A[k]&&dIn[k]>1&&eyeRule(D[k*4]/255,D[k*4+1]/255,D[k*4+2]/255))cand.push([x,y]);}
 // cluster candidates (grid-hash union within 5px)
 const lab=new Int32Array(cand.length).fill(-1);const clusters=[];const gk=(x,y)=>((x/5)|0)+','+((y/5)|0);const grid=new Map();cand.forEach((p,i)=>{const k=gk(p[0],p[1]);(grid.get(k)||grid.set(k,[]).get(k)).push(i);});
 for(let i=0;i<cand.length;i++){if(lab[i]>=0)continue;const cl=[];const st=[i];lab[i]=clusters.length;while(st.length){const j=st.pop();cl.push(cand[j]);const [x,y]=cand[j];
   for(let a=-1;a<=1;a++)for(let b=-1;b<=1;b++){for(const q of grid.get(((x/5|0)+a)+','+((y/5|0)+b))||[]){if(lab[q]<0&&Math.abs(cand[q][0]-x)<=5&&Math.abs(cand[q][1]-y)<=5){lab[q]=clusters.length;st.push(q);}}}}clusters.push(cl);}
 clusters.sort((a,b)=>b.length-a.length);const eyes=[];
 for(const cl of clusters.slice(0,2)){if(cl.length<Math.max(6,clusters[0].length*.5))continue;let x=0,y=0;for(const p of cl){x+=p[0];y+=p[1];}x/=cl.length;y/=cl.length;
  const r=Math.sqrt(cl.length/Math.PI)*1.2;eyes.push({x,y,r:Math.max(o.eyeMinR*BH,r),n:cl.length});}
 if(o.eyes){eyes.length=0;for(const e of o.eyes){const [x,y]=toL(e.x+.5,e.y+.5);eyes.push({x,y,r:e.r*SPX,n:-1});}}
 if(o.eyeShift)for(const e of eyes){e.x+=o.eyeShift[0]*e.r;e.y+=o.eyeShift[1]*e.r;}
 // eye size from the sprite's pixels: scan 16 rays from each centre until fur-like colour or outline ink
 for(const e of eyes){const g=e.r;let fr=0,fg=0,fb=0,fn=0;for(let i=0;i<24;i++){const a=i/24*6.283,x=Math.round(e.x+Math.cos(a)*g*3),y=Math.round(e.y+Math.sin(a)*g*3);if(x<0||y<0||x>=W||y>=H)continue;const k=(y*W+x)*4;if(D[k+3]<128)continue;fr+=D[k];fg+=D[k+1];fb+=D[k+2];fn++;}
  if(!fn)continue;fr/=fn;fg/=fn;fb/=fn;const ds=[];for(let i=0;i<16;i++){const a=i/16*6.283;let d=1,run=0;for(;d<g*3.2;d+=.5){const x=Math.round(e.x+Math.cos(a)*d),y=Math.round(e.y+Math.sin(a)*d);if(x<0||y<0||x>=W||y>=H)break;const k=(y*W+x)*4;
   const fur=D[k+3]<128||Math.hypot(D[k]-fr,D[k+1]-fg,D[k+2]-fb)<34||(D[k]+D[k+1]+D[k+2])<40;run=fur?run+1:0;if(run>=3){d-=1;break;}}ds.push(d);}
  ds.sort((a,b)=>a-b);const m=ds[8];e.rRaw=e.r;e.rScan=Math.min(g*1.6,Math.max(g*.5,m));e.r=o.eyeFixed?g:e.rScan;}
 for(const e of eyes)for(const f of eyes)if(e!==f)e.r=Math.min(e.r,Math.hypot(e.x-f.x,e.y-f.y)*.5);
 eyes.sort((a,b)=>a.x-b.x);
 if(o.creaseFaceOnly&&eyes.length){for(let y=0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(!A[k])continue;const d=Math.min(...eyes.map(E=>Math.hypot(x-E.x,y-E.y)/E.r));const w=clamp((d-3)/1.5);hF[k]+=(o.creaseK??2.2)*OLb[k]*w;}}
 let hcx=0,hcn=0;for(let y=by1;y<by1+BH*.5;y++)for(let x=0;x<W;x++)if(A[y*W+x]&&dIn[y*W+x]>3){hcx+=x;hcn++;}hcx/=hcn;
 const ex=eyes.length?eyes.reduce((s,e)=>s+e.x,0)/eyes.length:hcx,ey=eyes.length?eyes.reduce((s,e)=>s+e.y,0)/eyes.length:by1+BH*.35;
 const eR=eyes.length?eyes[0].r:BH*.05;
 const frontal=(o.frontal!==undefined)?o.frontal:eyes.length===2||Math.abs(ex-hcx)<W*.06;const dir=frontal?0:Math.sign(ex-hcx); // -1: face looks screen-left
 // tail: thin pixels in the lower body, on the side opposite the face
 const thin=Math.max(4,BH*.035)*(o.tailThin??1);const tailM=new Uint8Array(W*H);let tcnt=0,TB=null;
 // local-width map: max of dIn within a radius -> appendages are pixels whose neighbourhood never gets thick
 const mr=Math.round(thin*1.3);const mx1=new Float32Array(W*H),dMax=new Float32Array(W*H);
 for(let y=0;y<H;y++)for(let x=0;x<W;x++){let m=0;for(let i=-mr;i<=mr;i++){const X=x+i;if(X>=0&&X<W)m=Math.max(m,dIn[y*W+X]);}mx1[y*W+x]=m;}
 for(let y=0;y<H;y++)for(let x=0;x<W;x++){let m=0;for(let i=-mr;i<=mr;i++){const Y=y+i;if(Y>=0&&Y<H)m=Math.max(m,mx1[Y*W+x]);}dMax[y*W+x]=m;}
 for(let y=by1+BH*.55|0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(A[k]&&dMax[k]<thin*1.25&&(o.tailSide?Math.sign(x-cxm)===o.tailSide:(dir===0?true:Math.sign(x-cxm)===-dir))&&Math.abs(x-cxm)>W*(o.tailMinX??.12)){tailM[k]=1;tcnt++;}}
 if(o.tailRegion){tailM.fill(0);tcnt=0;const [ex,ey]=toL(o.tailRegion.cx,o.tailRegion.cy),[ex2]=toL(o.tailRegion.cx+o.tailRegion.rx,0),[,ey2]=toL(0,o.tailRegion.cy+o.tailRegion.ry);const rx=Math.abs(ex2-ex),ry=Math.abs(ey2-ey);for(let y=0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(A[k]&&((x-ex)/rx)**2+((y-ey)/ry)**2<=1){tailM[k]=1;tcnt++;}}}
 const tailMd=blur(tailM,o.tailRegion?(o.tailFeather??8):3);for(let k=0;k<W*H;k++)tailM[k]=(A[k]&&tailMd[k]>.35)?1:0;
 if(o.tailBase){TB=toL(o.tailBase[0],o.tailBase[1]).map(v=>Math.round(v));}else if(tcnt>BH*1.5){let best=1e9;for(let y=0;y<H;y++)for(let x=0;x<W;x++)if(tailM[y*W+x]){const d=Math.hypot(x-cxm,y-cym);if(d<best){best=d;TB=[x,y];}}}
 // ---- colour treatment ----
 for(const e of eyes)for(let y=0;y<H;y++)for(let x=0;x<W;x++){if(Math.hypot(x-e.x,y-e.y)<e.r*1.25){const k=(y*W+x)*3;if(o.eyeFill&&Math.hypot(x-e.x,y-e.y)<e.r*1.02){C[k]=.05;C[k+1]=.02;C[k+2]=.09;continue;}if(o.eyeDarken!==false&&(C[k]+C[k+1]+C[k+2]>.75)||(o.eye==='purple'&&C[k+2]>.4)){C[k]=.05;C[k+1]=.02;C[k+2]=.09;}}}
 if(o.eyeFillFur)for(const e of eyes){let r=0,g=0,b=0,n=0;for(let i=0;i<48;i++){const a=i/48*6.283;const X=Math.min(W-1,Math.max(0,Math.round(e.x+Math.cos(a)*e.r*(o.eyeFillR??1.35)*1.15))),Y=Math.min(H-1,Math.max(0,Math.round(e.y+Math.sin(a)*e.r*(o.eyeFillR??1.35)*1.15))),q=(Y*W+X)*3;if(!A[Y*W+X])continue;r+=C[q];g+=C[q+1];b+=C[q+2];n++;}if(!n)continue;r/=n;g/=n;b/=n;for(let y=0;y<H;y++)for(let x=0;x<W;x++){const dd=Math.hypot(x-e.x,y-e.y)/e.r;const FR=o.eyeFillR??1.35;if(dd<FR){const k=(y*W+x)*3,w=clamp((FR-dd)/.25);C[k]=C[k]*(1-w)+r*w;C[k+1]=C[k+1]*(1-w)+g*w;C[k+2]=C[k+2]*(1-w)+b*w;}}}
 if(o.furStreak)for(const F of o.furStreak){const [cx,cy]=toL(F.cx,F.cy),[x2]=toL(F.cx+F.rx,0),[,y2]=toL(0,F.cy+F.ry),rx=Math.abs(x2-cx),ry=Math.abs(y2-cy);for(let y=0;y<H;y++)for(let x=0;x<W;x++){const q=((x-cx)/rx)**2+((y-cy)/ry)**2;if(q<1&&A[y*W+x]){const h=Math.sin(x*12.9898+Math.floor(y/3)*78.233)*43758.5453;const n=h-Math.floor(h);const st=.5+.5*Math.sin((x+Math.sin(y*.35)*1.5)*2.2);const v=1+(F.k??.5)*((st*.7+n*.3)-.5)*2*clamp((1-q)/.3);const k=(y*W+x)*3;for(let i=0;i<3;i++)C[k+i]=Math.min(.98,C[k+i]*v);}}}
 if(o.regionGain)for(const G of o.regionGain){const [cx,cy]=toL(G.cx,G.cy),[x2]=toL(G.cx+G.rx,0),[,y2]=toL(0,G.cy+G.ry),rx=Math.abs(x2-cx),ry=Math.abs(y2-cy);for(let y=0;y<H;y++)for(let x=0;x<W;x++){const q=((x-cx)/rx)**2+((y-cy)/ry)**2;if(q<1){const w=clamp((1-q)/.35),k=(y*W+x)*3,g=1+(G.g-1)*w;for(let i=0;i<3;i++)C[k+i]=Math.min(.98,C[k+i]*g);}}}
 if(o.whiten)for(let k=0;k<W*H;k++){const r=C[k*3],g=C[k*3+1],b=C[k*3+2],mx=Math.max(r,g,b),mn=Math.min(r,g,b),l=(r+g+b)/3;if(l>.42&&(mx-mn)<.16+(b>r?.08:0)){const w=o.whiten*clamp((l-.42)/.2),t=Math.min(.96,l*1.25+.08);C[k*3]=r+(t-r)*w;C[k*3+1]=g+(t-g)*w;C[k*3+2]=b+(t*1.02-b)*w;}}
 if(o.eyeSocket)for(const e of eyes)for(let y=0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(!A[k])continue;const dx=(x-e.x)/(e.r*(o.eyeAspect?.[0]??1)),dy=(y-e.y)/(e.r*(o.eyeAspect?.[1]??1));hF[k]-=o.eyeSocket*Math.exp(-(dx*dx+dy*dy)*1.2);}
 if(o.eyeFlat)for(const e of eyes){const ax=e.r*(o.eyeAspect?.[0]??1)*o.eyeFlat,ay=e.r*(o.eyeAspect?.[1]??1)*o.eyeFlat;const h0=hF[Math.round(e.y)*W+Math.round(e.x)];for(let y=0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(!A[k])continue;const q=Math.hypot((x-e.x)/ax,(y-e.y)/ay);if(q<1.4){const w=clamp((1.4-q)/.4);hF[k]=hF[k]*(1-w)+Math.min(hF[k],h0-(o.eyeFlatDrop??.5))*w;}}}
 if(o.knit){const K=o.knit;const p=K.p??22;for(let k=0;k<W*H;k++){if(!A[k])continue;const r=C[k*3],g=C[k*3+1],b=C[k*3+2];if(!(b-g>.12&&b>r*.9))continue;const x=k%W,y=(k/W)|0,m=((x%p)+p)%p,u=m/p,col=Math.floor(x/p);
   const bulge=Math.sin(u*Math.PI);const tw=(col%2?1:-1);const rope=Math.abs(Math.cos(((y/(p*.9))+tw*(u-.5)*.9)*Math.PI));const gro=u<.08||u>.92?-1:0;const rw=K.rope??.45,cr=Math.pow(rope,K.sharp??1);hF[k]+=(K.amp??2)*((1-rw)*bulge+rw*cr-.5+gro*.5);}}
 if(o.trimSmooth){const T=new Uint8Array(W*H);for(let k=0;k<W*H;k++){if(!A[k])continue;const r=C[k*3],g=C[k*3+1],b=C[k*3+2];if(b-g>.15&&b>.35)T[k]=1;}
  const Tb=blur(T,1),rr=o.trimSmooth,C0=new Float32Array(C);let ne=0;
  for(let y=rr;y<H-rr;y++)for(let x=rr;x<W-rr;x++){const k=y*W+x;if(!A[k])continue;const t=Tb[k];if(t<.15||t>.85)continue;
   let ar=0,ag=0,ab=0,an=0,br=0,bg2=0,bb=0,bn=0;for(let dy=-rr;dy<=rr;dy++)for(let dx=-rr;dx<=rr;dx++){const q=k+dy*W+dx;if(!A[q])continue;if(T[q]&&Tb[q]>.6){ar+=C0[q*3];ag+=C0[q*3+1];ab+=C0[q*3+2];an++;}else if(!T[q]&&Tb[q]<.4){br+=C0[q*3];bg2+=C0[q*3+1];bb+=C0[q*3+2];bn++;}}
   if(!an||!bn)continue;const s2=t*t*(3-2*t);C[k*3]=br/bn+(ar/an-br/bn)*s2;C[k*3+1]=bg2/bn+(ag/an-bg2/bn)*s2;C[k*3+2]=bb/bn+(ab/an-bb/bn)*s2;ne++;}
  if(o.trimGlow)for(let k=0;k<W*H;k++)if(T[k]&&Tb[k]>.5){const g=1+(o.trimGlow-1)*Tb[k];C[k*3]*=g;C[k*3+1]*=g;C[k*3+2]*=g;}
  trimEdges=ne;}
 if(o.colorSmooth){const r=o.colorSmooth,keep=o.colorSmoothKeep??.25;const skipC=k=>o.colorSmoothSkipPurple&&(C[k*3+2]-C[k*3+1]>.12);const ch=[0,1,2].map(i=>{const a=new Float32Array(W*H),m=new Float32Array(W*H);for(let k=0;k<W*H;k++){const ok=A[k]&&!skipC(k);m[k]=ok?1:0;a[k]=ok?C[k*3+i]:0;}return [blur(blur(a,r),r),blur(blur(m,r),r)];});
  const sk2=new Uint8Array(W*H);for(let k=0;k<W*H;k++)sk2[k]=skipC(k)?1:0;for(let k=0;k<W*H;k++){if(!A[k]||sk2[k])continue;let near=1e9;for(const e of eyes)near=Math.min(near,Math.hypot(k%W-e.x,((k/W)|0)-e.y)/e.r);const w=near<1.6?0:(1-keep);for(let i=0;i<3;i++){const [a,m]=ch[i];C[k*3+i]=C[k*3+i]*(1-w)+(a[k]/Math.max(1e-3,m[k]))*w;}}}
 if(o.paint)for(const Pn of o.paint){const [cx,cy]=toL(Pn.cx,Pn.cy),[x2]=toL(Pn.cx+Pn.rx,0),[,y2]=toL(0,Pn.cy+Pn.ry),rx=Math.abs(x2-cx),ry=Math.abs(y2-cy);const pc=new THREE.Color(Pn.color);for(let y=0;y<H;y++)for(let x=0;x<W;x++){const q=((x-cx)/rx)**2+((y-cy)/ry)**2;if(q<1){const w=(Pn.a??.7)*(Pn.flat?Math.min(1,(1-q)*6):(1-q)**1.5),k=(y*W+x)*3;C[k]+=(pc.r-C[k])*w;C[k+1]+=(pc.g-C[k+1])*w;C[k+2]+=(pc.b-C[k+2])*w;}}}
 if(o.furBlack)for(let k=0;k<W*H;k++){const r=C[k*3],g=C[k*3+1],b=C[k*3+2],l=r*.3+g*.55+b*.15;if(l<.32){const m=.35;C[k*3]=(l+(r-l)*.35)*m;C[k*3+1]=(l+(g-l)*.35)*m;C[k*3+2]=(l+(b-l)*.35)*m;}}
 // ---- small-sprite colour softening: blur within colour regions (edge-preserving), heavy blur in a mouth box ----
 if((SPX>=2&&o.regionBlur!==false)||o.regionBlur===true){const r=Math.max(2,Math.round(Math.max(SPX,1)*(o.regionR??1.2))),C2=new Float32Array(C);
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(!A[k])continue;let sr=0,sg=0,sb=0,sw=0;const c0=[C[k*3],C[k*3+1],C[k*3+2]];
   for(let j=-r;j<=r;j+=2)for(let i=-r;i<=r;i+=2){const X=x+i,Y=y+j;if(X<0||Y<0||X>=W||Y>=H)continue;const q=Y*W+X;if(!A[q])continue;const d=Math.abs(C[q*3]-c0[0])+Math.abs(C[q*3+1]-c0[1])+Math.abs(C[q*3+2]-c0[2]);const w=Math.exp(-d*d/.02)*Math.exp(-(i*i+j*j)/(r*r));sr+=C[q*3]*w;sg+=C[q*3+1]*w;sb+=C[q*3+2]*w;sw+=w;}
   C2[k*3]=sr/sw;C2[k*3+1]=sg/sw;C2[k*3+2]=sb/sw;}C.set(C2);
  // anti-alias colour region boundaries (crest steps)
  const aa=Math.max(1,Math.round(SPX*(o.colorAA??.6)));const ch=[0,1,2].map(c=>{const a=new Float32Array(W*H);for(let k=0;k<W*H;k++)a[k]=C[k*3+c];return blur(a,aa);});for(let k=0;k<W*H;k++)if(A[k])for(let c=0;c<3;c++)C[k*3+c]=ch[c][k];}
 if(o.mouth){const [mx1,my1]=toL(o.mouth.x,o.mouth.y),[mx2,my2]=toL(o.mouth.x+o.mouth.w,o.mouth.y+o.mouth.h);const r=Math.round(SPX*1.5),C2=new Float32Array(C);
  for(let y=my1|0;y<my2;y++)for(let x=mx1|0;x<mx2;x++){const k=y*W+x;if(!A[k])continue;let sr=0,sg=0,sb=0,sw=0;for(let j=-r;j<=r;j++)for(let i=-r;i<=r;i++){const q=(y+j)*W+x+i;if(q<0||q>=W*H||!A[q])continue;sr+=C[q*3];sg+=C[q*3+1];sb+=C[q*3+2];sw++;}C2[k*3]=sr/sw;C2[k*3+1]=sg/sw;C2[k*3+2]=sb/sw;}
  C.set(C2);for(let y=my1|0;y<my2;y++)for(let x=mx1|0;x<mx2;x++){const k=y*W+x;if(A[k])hF[k]-=1.2*Math.sin(Math.PI*(x-mx1)/(mx2-mx1))*Math.exp(-((y-(my1+my2)/2)**2)/(2*(SPX*1.2)**2));}}
 // ---- authored features (source-pixel coords from the reference art) ----
 const F=o.features||{};
 if(F.moon){const [mx,my]=toL(F.moon.x,F.moon.y),mr=F.moon.r*SPX;for(let y=0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(!A[k]||Math.hypot(x-mx,y-my)>mr)continue;if(lum(k)>.5){C[k*3]=1.9;C[k*3+1]=1.75;C[k*3+2]=2.3;hF[k]+=1;}}}
 if(F.collar){const [x1c,yc]=toL(F.collar.x1,F.collar.y),[x2c]=toL(F.collar.x2,F.collar.y),hc=F.collar.h*SPX;for(let y=0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(!A[k]||x<x1c||x>x2c)continue;const dy=Math.abs(y-yc);if(dy<hc){const w=1-dy/hc;
   C[k*3]=.20;C[k*3+1]=.15;C[k*3+2]=.32;if(((x-x1c)/(hc*1.6)|0)%2===0&&dy<hc*.35){C[k*3]=.55;C[k*3+1]=.5;C[k*3+2]=.75;}hF[k]+=2.4*Math.sqrt(w);}}}
 if(F.horns){for(let y=0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(!A[k])continue;const r=D[k*4]/255,g=D[k*4+1]/255,b=D[k*4+2]/255,l=(r+g+b)/3;if(l>.55&&Math.max(r,g,b)-Math.min(r,g,b)<.22&&y<by1+BH*F.horns.yMax&&Math.abs(x-cxm)>(bx2-bx1)*F.horns.xMin){
   const tip=clamp((by1+BH*F.horns.yMax-y)/(BH*F.horns.yMax));C[k*3]=.38+.5*tip;C[k*3+1]=.33+.5*tip;C[k*3+2]=.48+.48*tip;hF[k]+=1.5;}}}
 if(F.pads){const PM=new Float32Array(W*H);for(let y=by1+BH*F.pads.yMin|0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(!A[k])continue;const r=D[k*4]/255,g=D[k*4+1]/255,b=D[k*4+2]/255;if(r>.55&&b>.6&&g>.4)PM[k]=1;}
  const PB=blur(blur(PM,3),3);for(let k=0;k<W*H;k++){if(!A[k])continue;const w=clamp((PB[k]-.25)/.3);if(w>0){C[k*3]=C[k*3]*(1-w)+.86*w;C[k*3+1]=C[k*3+1]*(1-w)+.66*w;C[k*3+2]=C[k*3+2]*(1-w)+.9*w;hF[k]+=1.8*w;}}}
 // ---- horns: crease where horn colour meets the head + slimmer, pointier horn volume ----
 if(o.horn){const isH=k=>{const r=D[k*4]/255,g=D[k*4+1]/255,b=D[k*4+2]/255;return A[k]&&r>o.horn.r&&g<o.horn.g&&b<o.horn.b;};const HM=new Float32Array(W*H);for(let k=0;k<W*H;k++)HM[k]=isH(k)?1:0;
  for(let k=0;k<W*H;k++)if(((k/W)|0)>by1+BH*.45)HM[k]=0;const HMb=blur(HM,Math.max(2,SPX));for(let k=0;k<W*H;k++){if(!A[k])continue;const edge=HMb[k]*(1-HMb[k])*4;const h0=hF[k];hF[k]-=edge*(o.horn.crease??4);if(HM[k])hF[k]*=.72;if(h0>1.5)hF[k]=Math.max(hF[k],1.5);}}
 if(o.anatomy){const an=o.anatomy,bw=bx2-bx1;const g2a=(x,y,cx,cy,rx,ry)=>Math.exp(-((x-cx)**2/(2*rx*rx)+(y-cy)**2/(2*ry*ry)));
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(!A[k])continue;const fy=(y-by1)/BH;let e=0;
   e-=(an.neckK??4)*Math.exp(-((fy-an.neckY)**2)/(2*.035*.035));                                    // neck groove
   for(const sd of [-1,1]){e+=(an.shK??4.5)*g2a(x,y,cxm+sd*bw*.24,by1+BH*an.shoulderY,bw*.13,BH*.06);   // shoulders
    e+=(an.hK??5.5)*g2a(x,y,cxm+sd*bw*.22,by1+BH*an.haunchY,bw*.15,BH*.07);}                          // haunches
   e-=2.5*g2a(x,y,cxm,by1+BH*((an.shoulderY+an.haunchY)/2),bw*.08,BH*.12);                           // belly/flank separation
   hF[k]+=e;}}
 // ---- face sculpt (relative to detected eyes / facing) ----
 const g2=(x,y,cx,cy,r)=>Math.exp(-((x-cx)**2+(y-cy)**2)/(2*r*r));
 const fdx=dir===0?0:dir; const mz=[ex+fdx*eR*1.85,ey+eR*(frontal?1.6:1.33)];
 if(eyes.length){for(let y=0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(hF[k]<0)continue;let e=0;
  if(frontal){e+=6*g2(x,y,mz[0]-eR*.42,mz[1],eR*.4)+6*g2(x,y,mz[0]+eR*.42,mz[1],eR*.4)+3*g2(x,y,mz[0],mz[1]-eR*.35,eR*.25);}
  else{e+=5*g2(x,y,ex+fdx*eR*1.6,ey+eR*1.35,eR*.46)+5*g2(x,y,ex+fdx*eR*2.0,ey+eR*1.3,eR*.46); // pad lobes
   e-=2.2*Math.exp(-((Math.hypot(x-mz[0],y-mz[1])-eR*.85)**2)/(2*(eR*.12)**2));                // crease outlining the pad
   e+=9.5*g2(x,y,ex+fdx*eR*1.4,ey+eR*1.2,eR*.85);e+=1.8*g2(x,y,ex+fdx*eR*1.9,ey+eR*1.0,eR*.65);e-=1.8*g2(x,y,ex+fdx*eR*1.65,ey+eR*1.8,eR*.22);
   e+=5.5*g2(x,y,ex-fdx*eR*.3,ey+eR*1.7,eR*.9);}
  for(const E of eyes){const d=Math.hypot(x-E.x,y-E.y);e+=3.5*g2(x,y,E.x,E.y-E.r*1.3,E.r*.65);e-=5.5*Math.exp(-((d-E.r*1.05)**2)/(2*(E.r*.22)**2));if(d<E.r)e+=2.6*Math.sqrt(1-(d/E.r)**2)-2.0;}
  hF[k]+=e;}
  // nose: dark violet-rose tint at the pad top
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){const w=g2(x,y,mz[0]+fdx*eR*.15,mz[1]-eR*.45,eR*.18);if(w>.3){const k=(y*W+x)*3;C[k]=C[k]*(1-w)+.20*w;C[k+1]=C[k+1]*(1-w)+.06*w;C[k+2]=C[k+2]*(1-w)+.14*w;}}}
 // bilinear sampling: nearest-pixel lookups at ~2.2px/cell aliased into stair-step ripples on the marching-cubes surface
 const BF=o.backFill?o.backFill.map(b=>{const [x,y]=toL(b.cx,b.cy),[x2,y2]=toL(b.cx+b.rx,b.cy+b.ry);const cc=new THREE.Color(b.color);return {x,y,rx:Math.abs(x2-x),ry:Math.abs(y2-y),c:[cc.r,cc.g,cc.b],blend:(b.blend??6)*(toL(1,0)[0]-toL(0,0)[0]),f:(b.front??0)*(toL(1,0)[0]-toL(0,0)[0])};}):null;
const hAt=(x,y)=>{if(x<0||y<0||x>W-1||y>H-1)return -50;const x0=Math.floor(x),y0=Math.floor(y),x1=Math.min(W-1,x0+1),y1=Math.min(H-1,y0+1),fx=x-x0,fy=y-y0;return (hF[y0*W+x0]*(1-fx)+hF[y0*W+x1]*fx)*(1-fy)+(hF[y1*W+x0]*(1-fx)+hF[y1*W+x1]*fx)*fy;};
let DLT=null;if(sdf3&&o.sdfParts.true3D){DLT=new Float32Array(W*H);for(let k=0;k<W*H;k++)DLT[k]=A[k]&&!FB[k]?hF[k]-H0[k]:0;const r=o.sdfParts.deltaBlur??3;DLT=blur(blur(DLT,r),r);if(o.sdfParts.deltaMaxPos!=null)for(let k=0;k<W*H;k++)DLT[k]=Math.min(DLT[k],o.sdfParts.deltaMaxPos);}
const nAt=(x,y)=>{const d=3,hx=(hAt(x+d,y)-hAt(x-d,y))/(2*d),hy=(hAt(x,y+d)-hAt(x,y-d))/(2*d);const v=new THREE.Vector3(-hx,hy,1);if(v.z/v.length()<.3){v.z=.3*Math.hypot(v.x,v.y)/Math.sqrt(1-.09);}return v.normalize();};
const M2Ws=(px,py,pz)=>{const h=hAt(px,py);return M2W(px,py,h).add(nAt(px,py).multiplyScalar((pz-h)/cellPx/(RES/2)));};
 const cAt=(x,y)=>{x=Math.min(W-1,Math.max(0,Math.round(x)));y=Math.min(H-1,Math.max(0,Math.round(y)));const k=(y*W+x)*3;return [C[k],C[k+1],C[k+2]];};
 // ---- particles ----
 const STEP=2,SC=0.045,PX=SC/STEP;const parts=[];
 for(let y=0;y<H;y+=STEP)for(let x=0;x<W;x+=STEP){if(!A[y*W+x])continue;if(NF&&NF[y*W+x])continue;if(o.eyeNoBits&&eyes.some(E=>Math.hypot(x-E.x,y-E.y)<E.r*o.eyeNoBits))continue;const k=(y*W+x)*3;const c=[D[k/3*4]/255,D[k/3*4+1]/255,D[k/3*4+2]/255];const h=Math.max(1,ZH?ZH[y*W+x]:hAt(x,y));
  const n=Math.max(1,Math.round(h/STEP));const eye=eyes.some(E=>Math.hypot(x-E.x,y-E.y)<E.r*.9);
  for(let z=-n;z<=n;z++){if(Math.abs(z)<n-1&&((x+y+z)&3))continue;const sh=z>=0?1:.55;parts.push({x,y,z:(ZC?ZC[y*W+x]:0)+z*h/n,c:[c[0]*sh,c[1]*sh,c[2]*sh],eye:eye&&z===n,tail:!!tailM[y*W+x],top:y<by1+BH*.3});}}
 const N=parts.length;const rest=new Float32Array(N*3),pos=new Float32Array(N*3),vel=new Float32Array(N*3),cols=new Float32Array(N*3),seed=new Float32Array(N),glowA=new Float32Array(N);
 const L2W=(px,py,pz)=>[(px-W/2)*PX,(H/2-py)*PX,pz*PX];
 parts.forEach((p,n)=>{const w=L2W(p.x,p.y,p.z);rest.set(w,n*3);cols.set(p.c,n*3);seed[n]=R0();});pos.set(rest);
 const footY=(H/2-by2-3)*PX;
 const group=new THREE.Group();
 const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.BufferAttribute(pos,3));geo.setAttribute('color',new THREE.BufferAttribute(cols,3));geo.setAttribute('glow',new THREE.BufferAttribute(glowA,1));
 const pmat=new THREE.ShaderMaterial({transparent:true,depthWrite:true,vertexColors:true,uniforms:{uRim:{value:new THREE.Color(o.rim?.[1]||'#3f99ff')},uCharge:{value:0},uBand:{value:new THREE.Vector3(0,0,0)},uSize:{value:SC*1.55*innerHeight*.85},uFade:{value:1},uFloor:{value:new THREE.Color(0x4a2aa8).multiplyScalar(o.floorK??1)}},
  vertexShader:`attribute float glow;varying vec3 vC;varying float vG;uniform float uSize;uniform vec3 uBand;uniform float uCharge;void main(){vC=color;vG=glow;bool inb=position.y>uBand.x&&position.y<uBand.y;if((uBand.z==1.&&inb)||(uBand.z==2.&&!inb)){gl_Position=vec4(2.,2.,2.,1.);gl_PointSize=0.;return;}float edge=uCharge*.8+(uBand.z>0.?max(1.-abs(position.y-uBand.x)*8.,1.-abs(position.y-uBand.y)*8.):0.);vG=max(vG,edge*1.4);vec4 mv=modelViewMatrix*vec4(position,1.);gl_Position=projectionMatrix*mv;gl_PointSize=min(uSize*(1.+glow*.6)/-mv.z,40.)*smoothstep(.35,1.1,-mv.z);/* near-lens cap + fade */}`,
  fragmentShader:`varying vec3 vC;varying float vG;uniform float uFade;uniform vec3 uFloor;uniform vec3 uRim;void main(){vec2 p=gl_PointCoord*2.-1.;float r=dot(p,p);if(r>1.)discard;vec3 n=vec3(p.x,-p.y,sqrt(1.-r));
  vec3 key=normalize(vec3(.5,.6,.7));float d=max(dot(n,key),0.);float rm=pow(1.-n.z,2.);float up=clamp(-n.y,0.,1.);
  vec3 c=vC*(.35+1.4*d)+vec3(.70,.55,1.)*d*.12+uRim*rm*.55+uFloor*up*.18+vec3(.55,.4,1.)*vG*.9;gl_FragColor=vec4(c,uFade);}`});
 const points=new THREE.Points(geo,pmat);points.frustumCulled=false;group.add(points);
 // ---- cached marching-cubes body ----
 const RES=110,cellPx=(Math.max(W,H)+12)/RES,MCS=(RES/2)*cellPx*PX;const lin=v=>Math.pow(v,2.2);
 const FUR=sh=>{if(!o.furBump)return;const FB2=o.furBump;const E=FB2.regions.slice(0,3).map(r=>{const [x,y]=toL(r.cx,r.cy),[x2,y2]=toL(r.cx+r.rx,r.cy+r.ry);const c=M2W(x,y,0),e=M2W(x2,y2,0);return new THREE.Vector4(c.x,c.y,Math.abs(e.x-c.x),Math.abs(e.y-c.y));});while(E.length<3)E.push(new THREE.Vector4(9,9,.001,.001));sh.uniforms.uFE={value:E};
  sh.vertexShader='varying vec3 vFP;\n'+sh.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvFP=position;');
  sh.fragmentShader='varying vec3 vFP;uniform vec4 uFE[3];\n'+sh.fragmentShader.replace('#include <normal_fragment_maps>','#include <normal_fragment_maps>\n{float m=0.;for(int i=0;i<3;i++){m=max(m,1.-smoothstep(.65,1.,length((vFP.xy-uFE[i].xy)/uFE[i].zw)));} if(m>0.){vec2 q=vFP.xy*'+(FB2.freq??180).toFixed(1)+';float dw=cos(q.x+sin(q.y*.35)*1.6)+1.15*cos(q.x*2.3+q.y*.4+1.7);float dv=.4*sin(q.y*1.3+q.x*.7);normal=normalize(normal+vec3(dw,dv,0.)*'+(FB2.amp??.3).toFixed(3)+'*m);}}');};
 const rimBase=[new THREE.Color(o.rim?.[0]||'#6633ff'),new THREE.Color(o.rim?.[1]||'#2e73ff')];const rimU={A:{value:rimBase[0].clone()},B:{value:rimBase[1].clone()}};
 const bmat=new THREE.MeshPhysicalMaterial({vertexColors:true,roughness:o.matte?.92:.55,metalness:0,sheen:o.matte?.35:1,sheenRoughness:o.matte?.8:.3,sheenColor:new THREE.Color(o.sheen||'#a07cff'),clearcoat:o.matte?0:.3,clearcoatRoughness:.3,envMapIntensity:o.envI??.7,transparent:true,emissive:new THREE.Color(o.sss||0x000000).multiplyScalar(o.sssK??0)});
 bmat.onBeforeCompile=sh=>{sh.uniforms.uRimA=rimU.A;sh.uniforms.uRimB=rimU.B;sh.fragmentShader='uniform vec3 uRimA;uniform vec3 uRimB;\n'+sh.fragmentShader.replace('#include <emissivemap_fragment>',`#include <emissivemap_fragment>
  { vec3 V=normalize(vViewPosition); float fr=${o.rimCrisp?`smoothstep(${o.rimCrisp[0]},${o.rimCrisp[1]},1.0-clamp(abs(dot(normal,V)),0.,1.))`:'pow(1.0-clamp(abs(dot(normal,V)),0.,1.),2.6)'}; float side=clamp(normal.x*-.6+.5,0.,1.);
    totalEmissiveRadiance+=vColor*smoothstep(.95,1.4,max(vColor.r,max(vColor.g,vColor.b)))*${(o.glowBright??0).toFixed(2)}; totalEmissiveRadiance+=mix(uRimA,uRimB,side)*fr*${(o.rimK??1.25).toFixed(3)}${o.rimFront?'*smoothstep('+o.rimFront[0]+','+o.rimFront[1]+',vBZ)':''}; totalEmissiveRadiance+=uRimA*0.4*${(o.floorK??1).toFixed(3)}*clamp(-normal.y,0.,1.)*.10; }`);if(o.sheenBackFade){sh.vertexShader='varying float vBZ;\n'+sh.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvBZ=position.z;');sh.fragmentShader='varying float vBZ;\n'+sh.fragmentShader.replace('#include <lights_physical_fragment>','#include <lights_physical_fragment>\n{float bf=smoothstep('+o.sheenBackFade[0].toFixed(3)+','+o.sheenBackFade[1].toFixed(3)+',vBZ);float bk=mix('+(o.sheenBackFade[2]??.15).toFixed(2)+',1.,bf);\n#ifdef USE_SHEEN\nmaterial.sheenColor*=bk;\n#endif\nmaterial.roughness=mix(1.,material.roughness,bf);material.specularColor*=bk;material.specularF90*=bk;\n#ifdef USE_CLEARCOAT\nmaterial.clearcoat*=bk;\n#endif\n}').replace('#include <opaque_fragment>',''+(o.backDark?'outgoingLight*=mix('+o.backDark[2].toFixed(2)+',1.,smoothstep('+o.backDark[0].toFixed(3)+','+o.backDark[1].toFixed(3)+',vBZ));\n':'')+'#include <opaque_fragment>');}FUR(sh);};
 const MC=new MarchingCubes(RES,bmat,false,true,400000);MC.isolation=0;
 {const f=MC.field,pal=MC.palette;for(let cz=0;cz<RES;cz++)for(let cy=0;cy<RES;cy++)for(let cx=0;cx<RES;cx++){
   const px=W/2+(cx-RES/2)*cellPx,py=H/2-(cy-RES/2)*cellPx,pz=(cz-RES/2)*cellPx;const q=cx+cy*RES+cz*RES*RES;
   if(cx<1||cy<1||cz<1||cx>RES-2||cy>RES-2||cz>RES-2)f[q]=-1;else if(sdf3&&o.sdfParts.true3D){const ix=Math.min(W-1,Math.max(0,Math.round(px))),iy=Math.min(H-1,Math.max(0,Math.round(py))),kk=iy*W+ix;let v=-sdf3([px,py,pz]);
    if(A[kk]&&FB[kk]&&!(NF&&NF[kk]))v=Math.max(v,hAt(px,py)-Math.abs(pz));if(A[kk]&&!FB[kk]&&pz>ZC[kk])v+=DLT[kk]*clamp((pz-ZC[kk])/Math.max(1,ZH[kk]));if(!A[kk]&&!(NT&&NT[kk]))v=Math.min(v,-(dOut[kk]||1)*(o.sdfTrim??o.sdfParts.trim??1));f[q]=v;}else f[q]=hAt(px,py)-Math.abs(pz);
   let c=cAt(px,py);const sh=pz>=0?1:(o.backShade??.6);if(BF){for(const b of BF){if(pz>=b.f)continue;const q=((px-b.x)/b.rx)**2+((py-b.y)/b.ry)**2;if(q<1){const w=Math.min(1,(b.f-pz)/b.blend)*Math.min(1,(1-q)*4);c=[c[0]+(b.c[0]-c[0])*w,c[1]+(b.c[1]-c[1])*w,c[2]+(b.c[2]-c[2])*w];break;}}}const cg=o.colorGain??1;pal[q*3]=(c[0]>1?c[0]:lin(c[0]))*sh*cg;pal[q*3+1]=(c[1]>1?c[1]:lin(c[1]))*sh*cg;pal[q*3+2]=(c[2]>1?c[2]:lin(c[2]))*sh*cg;}MC.update();}
 const bg=MC.geometry.clone();bg.setDrawRange(0,MC.count);bg.computeBoundingSphere();const tris=MC.count/3;MC.geometry.dispose();
 const bodyMesh=new THREE.Mesh(bg,bmat);const body=new THREE.Group();body.add(bodyMesh);let outl=null;if(o.outline){const om=new THREE.MeshBasicMaterial({color:new THREE.Color(o.outline.color||'#9a6aff'),side:THREE.BackSide,transparent:true,toneMapped:false});om.onBeforeCompile=sh=>{sh.vertexShader=sh.vertexShader.replace('#include <begin_vertex>','vec3 transformed=position+normalize(normal)*'+(o.outline.w??.012).toFixed(4)+';');};outl=new THREE.Mesh(bg,om);body.add(outl);}const SHELLS=[];const buildShells=()=>{if(o.furShells){const F=o.furShells;const E=F.regions.slice(0,3).map(r=>{const [x,y]=toL(r.cx,r.cy),[x2,y2]=toL(r.cx+r.rx,r.cy+r.ry);const c=M2W(x,y,0),e=M2W(x2,y2,0);return new THREE.Vector4(c.x,c.y,Math.abs(e.x-c.x),Math.abs(e.y-c.y));});while(E.length<3)E.push(new THREE.Vector4(9,9,.001,.001));const n=F.layers??8;for(let i=1;i<=n;i++){const h=i/n;const fm=new THREE.MeshLambertMaterial({vertexColors:true,color:new THREE.Color(F.tint||'#ffffff').multiplyScalar((F.bright??1.4)*(.75+.35*h)),transparent:true,opacity:F.alpha??.55,depthWrite:false});fm.userData.a=F.alpha??.55;fm.onBeforeCompile=sh=>{sh.uniforms.uFE={value:E};sh.vertexShader='varying vec3 vFP;varying float vFZ;\n'+sh.vertexShader.replace('#include <begin_vertex>','vFZ=normalize(normalMatrix*normal).z;vec3 transformed=position+normalize(normal)*'+((F.len??.02)*h).toFixed(5)+'-vec3(0.,'+((F.droop??.006)*h*h).toFixed(5)+',0.);vFP=position;');sh.fragmentShader='varying vec3 vFP;varying float vFZ;uniform vec4 uFE[3];\n'+sh.fragmentShader.replace('void main() {','void main() {'+(F.faceCam!=null?'if(vFZ<'+F.faceCam.toFixed(3)+')discard;':'')+'float m=0.;for(int i=0;i<3;i++){m=max(m,1.-smoothstep(.6,1.,length((vFP.xy-uFE[i].xy)/uFE[i].zw)));}'+(F.frontOnly?'if(vFP.z<'+F.frontOnly.toFixed(3)+')discard;':'')+'vec2 q=floor(vec2(vFP.x*'+(F.freq??220).toFixed(1)+',vFP.y*'+((F.freq??220)*.5).toFixed(1)+'+vFP.z*'+(F.freq??220).toFixed(1)+'));float nz=fract(sin(dot(q,vec2(12.9898,78.233)))*43758.5453);if(nz*m<'+h.toFixed(3)+'*0.9+0.05) discard;');};const sm=new THREE.Mesh(bg,fm);body.add(sm);SHELLS.push(sm);}}};body.visible=false;group.add(body);
 const M2W=(px,py,pz)=>new THREE.Vector3((px-W/2)/cellPx/(RES/2),(H/2-py)/cellPx/(RES/2),pz/cellPx/(RES/2));// body-local (scaled by MCS)
 // tail bend rig
 const tp=bg.attributes.position,tn=bg.attributes.normal,tailV=[];let TBL=null;
 if(TB){TBL=M2W(TB[0],TB[1],0);let tl=0;for(let y=0;y<H;y++)for(let x=0;x<W;x++)if(tailM[y*W+x])tl=Math.max(tl,Math.hypot(x-TB[0],y-TB[1]));const tlL=tl/cellPx/(RES/2);
  for(let v=0;v<bg.drawRange.count;v++){const x=tp.getX(v),y=tp.getY(v);const px=W/2+x*(RES/2)*cellPx,py=H/2-y*(RES/2)*cellPx;const md=tailMd[Math.min(H-1,Math.max(0,Math.round(py)))*W+Math.min(W-1,Math.max(0,Math.round(px)))];
   if(md>.15){const lk=o.tailLock??0;let w=clamp((Math.hypot(x-TBL.x,y-TBL.y)/(tlL*.6)-lk)/(1-lk))*clamp((md-.15)/.4);w=w*w*(3-2*w);tailV.push([v,x,y,tp.getZ(v),tn.getX(v),tn.getY(v),w]);}}}
 function bendTail(a){for(const [v,x,y,z,nx,ny,w] of tailV){const b=a*w+Math.sin(tailPh*1.3-w*4.2)*.22*w*w,c=Math.cos(b),s=Math.sin(b),dx=x-TBL.x,dy=y-TBL.y;tp.setXY(v,TBL.x+dx*c-dy*s,TBL.y+dx*s+dy*c);tp.setZ(v,z+Math.sin(b*2)*.02*w);tn.setXY(v,nx*c-ny*s,nx*s+ny*c);}if(tailV.length){tp.needsUpdate=true;tn.needsUpdate=true;}}
 // whiskers from the pad
 const WMat=new THREE.LineBasicMaterial({color:0xd9ccff,transparent:true,opacity:.85});const wantW=o.whiskers===true||(o.whiskers==='auto'&&eyes.length&&!frontal);
 if(wantW){const sides=frontal?[-1,1]:[fdx];for(const sd of sides){const rx=mz[0]+sd*(eR*(o.whiskerK??1))*(frontal?.5:0),ry=mz[1],rz=hAt(rx,ry);for(let k=0;k<3;k++){const pts=[];const ang=(k-1)*.28;
   for(let u=0;u<=12;u++){const t=u/12,L=eR*3.4*(o.whiskerL??1);pts.push(M2W(rx+sd*Math.cos(ang)*L*t,ry+Math.sin(ang)*L*t+t*t*eR*.6,rz+.3+t*2.5));}body.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),WMat));}}}
 // eyes: layered iris + glossy dome + crisp highlights + lid
 const eyeMats=[];const lids=[];const irisMs=[];
 let irisHex=o.irisColor;if(!irisHex&&eyes.length){irisHex='#8b4cff';}
 // eyelid = the creature's own fur: average non-ink colour in a ring around the eyes, plus the creature sheen
 let lr_=0,lg_=0,lb_=0,ln_=0;for(const E of eyes)for(let i=0;i<32;i++){const a=i/32*6.283,rr2=E.r*(1.5+(i%3)*.3);const c=cAt(E.x+Math.cos(a)*rr2,E.y+Math.sin(a)*rr2);if(c[0]+c[1]+c[2]<.06&&!o.furBlack)continue;lr_+=c[0];lg_+=c[1];lb_+=c[2];ln_++;}
 const furC=ln_?[lr_/ln_,lg_/ln_,lb_/ln_]:cAt(ex,ey-eR*1.6);
 const lidMat=new THREE.MeshPhysicalMaterial({color:new THREE.Color().setRGB(...furC.map(v=>lin(v))).lerp(new THREE.Color(o.sheen||'#a07cff'),o.lidLight??0),emissive:new THREE.Color(o.sheen||'#a07cff').multiplyScalar((o.lidLight??0)*.25),roughness:.55,sheen:1,sheenRoughness:.3,sheenColor:new THREE.Color(o.sheen||'#a07cff'),envMapIntensity:o.envI??.7,transparent:true});
 for(const E of eyes){const cv=document.createElement('canvas');cv.width=cv.height=256;const g=cv.getContext('2d');const base=new THREE.Color(irisHex);const hx=c=>'#'+c.getHexString();
  const lite=base.clone().lerp(new THREE.Color(1,1,1),.45),deep=base.clone().multiplyScalar(.35),dark=base.clone().multiplyScalar(.12);
  const ES=o.eyeStyle||'deep';let gr=g.createRadialGradient(128,128,10,128,128,128);if(ES==='stars'){gr.addColorStop(0,'#c890ff');gr.addColorStop(.35,'#7a2aff');gr.addColorStop(.75,'#3a0aa0');gr.addColorStop(1,'#14042e');}else if(ES==='glow'){const wh=base.clone().lerp(new THREE.Color(1,1,1),.8);gr.addColorStop(0,hx(wh));gr.addColorStop(.4,hx(lite));gr.addColorStop(.8,hx(base));gr.addColorStop(1,hx(lite));}else if(o.irisStops){o.irisStops.forEach(([p,c])=>gr.addColorStop(p,c));}else{gr.addColorStop(0,hx(dark));gr.addColorStop(.28,hx(deep));gr.addColorStop(.55,hx(base));gr.addColorStop(.8,hx(lite));gr.addColorStop(.93,hx(deep));gr.addColorStop(1,hx(dark));}
  g.fillStyle=gr;g.fillRect(0,0,256,256);g.globalAlpha=o.irisStriate??(ES==='glow'?.12:ES==='stars'?0:.35);for(let i=0;i<90;i++){const a=i/90*Math.PI*2;g.strokeStyle=i%2?'#f0e4ff':hx(dark);g.lineWidth=1.5;g.beginPath();g.moveTo(128+Math.cos(a)*40,128+Math.sin(a)*40);g.lineTo(128+Math.cos(a)*118,128+Math.sin(a)*118);g.stroke();}
  if(o.irisBottomGlow){g.globalAlpha=1;const bg=g.createRadialGradient(128,200,4,128,200,90);bg.addColorStop(0,o.irisBottomGlow);bg.addColorStop(1,'rgba(220,190,255,0)');g.fillStyle=bg;g.fillRect(0,0,256,256);}
  g.globalAlpha=ES==='stars'?0:1;g.fillStyle=ES==='glow'?hx(base.clone().multiplyScalar(.55)):'#07020c';{const pu=o.pupil||[30,44,0,0];if(o.pupilColor)g.fillStyle=o.pupilColor;g.beginPath();g.ellipse(128+pu[2],128+pu[3],ES==='glow'?7:pu[0],ES==='glow'?50:pu[1],0,0,7);g.fill();}
  if(ES==='stars'){let sd=E.x*13.7+3;const rnd=()=>{sd=(sd*16807)%2147483647;return sd/2147483647;};for(let i=0;i<140;i++){const a=rnd()*6.283,r=Math.sqrt(rnd())*118;g.globalAlpha=.4+rnd()*.6;g.fillStyle=rnd()<.2?'#e8c8ff':'#ffffff';const z=rnd()<.15?3:1.6;g.fillRect(128+Math.cos(a)*r,128+Math.sin(a)*r,z,z);}g.globalAlpha=1;}
  if(ES==='sparkle'||ES==='stars'){const star=(x,y,r)=>{g.fillStyle='#fff';g.beginPath();for(let i=0;i<8;i++){const a=i*Math.PI/4,rr=i%2?r*.22:r;g.lineTo(x+Math.cos(a)*rr,y+Math.sin(a)*rr);}g.fill();};const sk=o.sparkleK??1;star(150,100,34*sk);star(96,150,16*sk);star(170,165,9*sk);}g.fillStyle='rgba(255,230,255,.7)';g.beginPath();g.arc(90,170,9,0,7);g.fill();
  const tex=new THREE.CanvasTexture(cv);tex.colorSpace=THREE.SRGBColorSpace;const lr=E.r*1.05*(o.eyeR??1)/cellPx/(RES/2);
  const eg=new THREE.Group();if(o.eyeAspect)eg.scale.set(o.eyeAspect[0],o.eyeAspect[1],1);const eyeRimP=o.eyeRim;eg.position.copy(M2Ws(E.x,E.y,hAt(E.x,E.y)+(o.eyeLift??-1.2)));body.add(eg);if(o.eyeNormal){const nn=nAt(E.x,E.y).lerp(new THREE.Vector3(0,0,1),1-o.eyeNormal).normalize();eg.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),nn);}if(eyes.length>1&&o.gaze!==false){const gx=eyes.reduce((a,e)=>a+e.x,0)/eyes.length;eg.lookAt(M2W(gx+(o.gazeX??0),E.y,hAt(E.x,E.y)+(o.gazeDist??120)));}
  const irisM=new THREE.MeshBasicMaterial({map:tex,transparent:true,toneMapped:o.eyeToneMap??true});eg.add(new THREE.Mesh(o.eyeOuterCurve?(()=>{const R=lr*.95,gq=new THREE.RingGeometry(0,R,64,16),p=gq.attributes.position,uv=gq.attributes.uv,sd=Math.sign(E.x-ex)||1;for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),t=Math.max(0,x*sd/R);p.setZ(i,-o.eyeOuterCurve*R*t*t*(1-.3*(y/R)**2));uv.setXY(i,x/(2*R)+.5,y/(2*R)+.5);}gq.computeVertexNormals();return gq;})():o.eyeCurve?(()=>{const ca=o.eyeCurve,Rs=lr*.95/Math.sin(ca),gq=new THREE.SphereGeometry(Rs,48,16,0,Math.PI*2,0,ca);gq.rotateX(Math.PI/2);gq.translate(0,0,-Rs);const p=gq.attributes.position,uv=gq.attributes.uv;for(let i=0;i<p.count;i++)uv.setXY(i,p.getX(i)/(2*lr*.95)+.5,p.getY(i)/(2*lr*.95)+.5);uv.needsUpdate=true;return gq;})():new THREE.CircleGeometry(lr*.95,48),irisM));if(o.eyeCurve&&o.eyeBackFace)irisM.side=THREE.DoubleSide;
  const domeM=new THREE.MeshPhysicalMaterial({color:ES==='glow'?0xe8e0ff:0x1a0d33,roughness:.04,clearcoat:1,clearcoatRoughness:0,transparent:true,opacity:o.eyeDomeOp??(ES==='glow'?.1:.28),depthWrite:o.eyeDomeOp==null,envMapIntensity:1.2});
  if(ES==='glow'){const hc=document.createElement('canvas');hc.width=hc.height=64;const hg=hc.getContext('2d');const rg=hg.createRadialGradient(32,32,8,32,32,32);rg.addColorStop(0,'rgba(210,190,255,.55)');rg.addColorStop(1,'rgba(160,120,255,0)');hg.fillStyle=rg;hg.fillRect(0,0,64,64);const gh=new THREE.Mesh(new THREE.PlaneGeometry(lr*2.6,lr*2.6),new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(hc),transparent:true,blending:THREE.AdditiveBlending,depthWrite:false}));gh.position.z=lr*.05;eg.add(gh);}
  const dome=new THREE.Mesh(new THREE.SphereGeometry(lr,40,24,0,Math.PI*2,0,Math.PI/2),domeM);dome.rotation.x=Math.PI/2;dome.scale.set(1,.42,1);eg.add(dome);
  const hlM=new THREE.MeshBasicMaterial({color:0xffffff,toneMapped:false,transparent:true,depthWrite:false,map:o.eyeHLsoft?(()=>{const c=document.createElement('canvas');c.width=c.height=64;const q=c.getContext('2d');const r=q.createRadialGradient(32,32,0,32,32,32);r.addColorStop(0,'rgba(255,255,255,1)');r.addColorStop(.45,'rgba(255,255,255,.95)');r.addColorStop(.75,'rgba(255,255,255,.35)');r.addColorStop(1,'rgba(255,255,255,0)');q.fillStyle=r;q.fillRect(0,0,64,64);return new THREE.CanvasTexture(c);})():null,opacity:ES==='stars'?(o.eyeHL??.3):(o.eyeHL??1)});if(ES==='stars'){domeM.opacity=o.eyeDome??.07;domeM.color.set(0x8050ff);domeM.clearcoat=.3;domeM.roughness=.4;}const h1=new THREE.Mesh(new THREE.CircleGeometry(lr*(o.eyeHLsize??.2),32),hlM);h1.position.set(lr*(o.eyeHLpos?.[0]??.3),lr*(o.eyeHLpos?.[1]??.34),lr*.45);h1.renderOrder=5;eg.add(h1);
  const h2=new THREE.Mesh(new THREE.CircleGeometry(lr*.09,16),hlM);h2.position.set(-lr*.3,-lr*.25,lr*.42);eg.add(h2);
  const lid=new THREE.Mesh(new THREE.SphereGeometry(1,24,16),lidMat);lid.position.copy(eg.position);lid.position.z+=lr*.05;body.add(lid);lids.push({lid,y0:lid.position.y,lr,hl:[h1,h2]});
  if(eyeRimP){if((eyeRimP.t??.13)>0){const rm=new THREE.Mesh(new THREE.TorusGeometry(lr*1.0,lr*(eyeRimP.t??.13),10,48),new THREE.MeshPhysicalMaterial({color:eyeRimP.color,roughness:.6,sheen:.5,sheenColor:new THREE.Color(eyeRimP.color)}));rm.position.z=lr*.05;eg.add(rm);}if(eyeRimP.upper){const gx=eyes.reduce((a,e)=>a+e.x,0)/eyes.length,sd=E.x<gx?1:-1;const a0=Math.PI*(eyeRimP.a0??.2),a1=Math.PI*(eyeRimP.a1??.8),sh=sd*Math.PI*(eyeRimP.shift??.1);const R0=lr*1.0,th=lr*eyeRimP.upper*2,sp=new THREE.Shape(),N=24;
   for(let i=0;i<=N;i++){const u=i/N,a=a0+(a1-a0)*u+sh;const w=Math.sin(Math.PI*u)**.8*(1+.35*(sd>0?u:1-u)*0);const t=th*w*(sd>0?(.5+.5*(1-u)):(.5+.5*u));const x=Math.cos(a)*(R0+t),y=Math.sin(a)*(R0+t);i?sp.lineTo(x,y):sp.moveTo(x,y);}
   for(let i=N;i>=0;i--){const u=i/N,a=a0+(a1-a0)*u+sh;sp.lineTo(Math.cos(a)*R0,Math.sin(a)*R0);}
   const ul=new THREE.Mesh(new THREE.ShapeGeometry(sp),new THREE.MeshBasicMaterial({color:eyeRimP.lash||0x120a14,side:THREE.DoubleSide}));ul.position.z=lr*.12;eg.add(ul);}}
  irisMs.push(irisM);eyeMats.push([irisM,1],[domeM,domeM.opacity],[hlM,hlM.opacity]);}
 const setLids=b=>{for(const L of lids){L.lid.visible=b>.02;L.lid.scale.set(L.lr*1.05,L.lr*1.05*Math.max(.02,b),L.lr*(o.lidDepth??.5));L.lid.position.y=L.y0+L.lr*(1-b);if(L.hl)for(const m of L.hl)m.visible=b<.35;}};setLids(0);
 // ---- wing membranes: thin sheets with bone ridges, hinged at the root, flapping ----
 let halo=null;if(o.features?.moon){const hc=document.createElement('canvas');hc.width=hc.height=128;const g=hc.getContext('2d');const gr=g.createRadialGradient(64,64,4,64,64,64);gr.addColorStop(0,'rgba(235,225,255,.9)');gr.addColorStop(.35,'rgba(190,160,255,.35)');gr.addColorStop(1,'rgba(120,80,255,0)');g.fillStyle=gr;g.fillRect(0,0,128,128);
  const [mx,my]=toL(o.features.moon.x,o.features.moon.y);halo=new THREE.Mesh(new THREE.PlaneGeometry(1,1),new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(hc),transparent:true,blending:THREE.AdditiveBlending,depthWrite:false}));
  halo.position.copy(M2Ws(mx,my,hAt(mx,my)+(o.haloLift??3)));if(o.surfaceNormal)halo.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),nAt(mx,my));halo.userData.s=o.features.moon.r*SPX*(o.haloK??3.2)/cellPx/(RES/2);body.add(halo);}
 if(o.glowSpots){const gc=document.createElement('canvas');gc.width=gc.height=128;const g2=gc.getContext('2d');const gr2=g2.createRadialGradient(64,64,0,64,64,64);gr2.addColorStop(0,'rgba(255,255,255,1)');gr2.addColorStop(.55,'rgba(255,255,255,.85)');gr2.addColorStop(1,'rgba(255,255,255,0)');g2.fillStyle=gr2;g2.fillRect(0,0,128,128);const gt=new THREE.CanvasTexture(gc);
  for(const G of o.glowSpots){const [gx,gy]=toL(G.cx,G.cy);const m=new THREE.Mesh(new THREE.PlaneGeometry(1,1),new THREE.MeshBasicMaterial({map:gt,color:new THREE.Color(G.color),transparent:true,opacity:G.a??.6,blending:G.solid?THREE.NormalBlending:THREE.AdditiveBlending,depthWrite:false}));m.position.copy(M2Ws(gx,gy,hAt(gx,gy)+(G.lift??1)));m.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),nAt(gx,gy));const u=SPX/cellPx/(RES/2);m.scale.set(G.rx*2*u,G.ry*2*u,1);body.add(m);}}
 if(o.icicles){const I=o.icicles,IM=new Uint8Array(W*H);const [,yMin]=toL(0,I.yMin);for(let y=yMin|0;y<H;y++)for(let x=0;x<W;x++){const k=y*W+x;if(!A[k])continue;const r=D[k*4]/255,g=D[k*4+1]/255,b=D[k*4+2]/255;if(b-r>(I.blue??.07)&&b>.5)IM[k]=1;}
  const seen=new Uint8Array(W*H),icM=new THREE.MeshPhysicalMaterial({color:0xf2f6ff,roughness:.42,metalness:0,clearcoat:.6,clearcoatRoughness:.5,sheen:1,sheenColor:new THREE.Color(0xd8e4ff),emissive:0x9ab0ff,emissiveIntensity:I.glow??.35,transparent:true,opacity:.95});let nI=0;
  for(let k0=0;k0<W*H;k0++){if(!IM[k0]||seen[k0])continue;const st=[k0];seen[k0]=1;let x1=W,x2=0,y1=H,y2=0,n=0;while(st.length){const k=st.pop(),x=k%W,y=(k/W)|0;n++;x1=Math.min(x1,x);x2=Math.max(x2,x);y1=Math.min(y1,y);y2=Math.max(y2,y);for(const kk of [k-1,k+1,k-W,k+W])if(kk>=0&&kk<W*H&&IM[kk]&&!seen[kk]){seen[kk]=1;st.push(kk);}}
   const h=y2-y1+1,w=x2-x1+1;if(n<(I.minPx??12)||h<w*1.3||nI>=(I.max??40))continue;const cx=(x1+x2)/2;const top=M2W(cx,y1,hAt(cx,y1+2)+(I.lift??0)+1),bot=M2W(cx,y2,hAt(cx,y1+2)+(I.lift??0)+1.5);const len=top.distanceTo(bot),rad=Math.max(w*.42,1.2)*(I.fat??1)/cellPx/(RES/2);
   const maxW=I.maxW??6,ns=Math.max(1,Math.ceil(w/maxW));for(let j=0;j<ns&&nI<(I.max??40);j++){const sx=x1+(j+.5)*w/ns,lk=ns>1?(.55+.45*Math.abs(Math.sin(j*2.3+x1))):1;const t2=M2W(sx,y1,hAt(sx,y1+2)+(I.lift??0)+1),b2=M2W(sx,y1+(y2-y1)*lk,hAt(sx,y1+2)+(I.lift??0)+1.5);const L2=t2.distanceTo(b2),r2=Math.min(rad,Math.max((w/ns)*.42,1.2)*(I.fat??1)/cellPx/(RES/2));
   const cone=new THREE.Mesh(new THREE.ConeGeometry(r2,L2*(I.lenK??1.1),6,2),icM);cone.rotation.x=Math.PI;cone.position.copy(t2).lerp(b2,.5);body.add(cone);nI++;}}
  icicleCount=nI;}
 buildShells();const ovInfo={};{const ctx={W,H,A,C,hAt,M2W:o.surfaceNormal?M2Ws:M2W,M2Wz:M2W,cellPx,RES,lin,toL};
  if(o.lineOverlay){ovInfo.lines=0;for(const lo of [].concat(o.lineOverlay)){const L=buildLineOverlay(ctx,lo);body.add(L.group);ovInfo.lines+=L.lines;ovInfo.bridges=L.bridges;ovInfo.linePx=L.pixels;}}
  if(o.accessory){const Ac=buildAccessoryOverlay(ctx,o.accessory);body.add(Ac.mesh);ovInfo.accTris=Ac.tris;ovInfo.brimPts=Ac.brimPts;ovInfo.accPx=Ac.pixels;}
  if(o.hornMeshes){body.add(buildHornMeshes(ctx,o.hornMeshes,o.hornMeshOpts||{}));ovInfo.horns=o.hornMeshes.length;}}
 const wings=[];
 if(o.batWings){const BW=o.batWings;for(const side of BW.sides){const sd=side.sd;const [sx,sy]=toL(...side.S);const P0=L2W(sx,sy,0);const rel=q=>{const [x,y]=toL(...q);const p=L2W(x,y,0);return new THREE.Vector3(p[0]-P0[0],p[1]-P0[1],0).multiplyScalar(BW.spread??1);};
   const Wr=rel(side.Wr),tips=side.tips.map(rel),S0=new THREE.Vector3();const rim=[];const qb=(a,m,b,u)=>a.clone().multiplyScalar((1-u)**2).add(m.clone().multiplyScalar(2*u*(1-u))).add(b.clone().multiplyScalar(u*u));
   for(let i=0;i<tips.length;i++){rim.push(tips[i]);if(i<tips.length-1){const a=tips[i],b=tips[i+1],m=a.clone().lerp(b,.5).lerp(Wr,BW.scallop??.28);for(let j=1;j<6;j++)rim.push(qb(a,m,b,j/6));}}
   {const a=tips[tips.length-1],b=S0,m=a.clone().lerp(b,.5).lerp(Wr,(BW.scallop??.28)*.6);for(let j=1;j<6;j++)rim.push(qb(a,m,b,j/6));}
   const pos=[Wr.x,Wr.y,0,0,0,0],col=[],idx=[];const cin=new THREE.Color(BW.inner||'#5a2ab8'),cout=new THREE.Color(BW.outer||'#7aa8ff');const maxD=Math.max(...tips.map(t=>t.distanceTo(Wr)));const pc=v=>{const d=Math.min(1,v.distanceTo(Wr)/maxD);const cc=cin.clone().lerp(cout,Math.pow(d,BW.blueK??1)*.95);col.push(cc.r,cc.g,cc.b);};pc(Wr);pc(S0);
   for(const v of rim){pos.push(v.x,v.y,-.04*v.distanceTo(Wr));pc(v);}const nR=rim.length;for(let i=0;i<nR-1;i++)idx.push(0,2+i,2+i+1);idx.push(0,2+nR-1,1);idx.push(0,1,2);
   const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));geo.setAttribute('color',new THREE.Float32BufferAttribute(col,3));geo.setIndex(idx);geo.computeVertexNormals();
   const wm=new THREE.MeshStandardMaterial({vertexColors:true,side:THREE.DoubleSide,transparent:true,roughness:.5,emissive:new THREE.Color(BW.glow||'#3a2a90'),emissiveIntensity:BW.glowK??.35,opacity:1});const mem=new THREE.Mesh(geo,wm);
   const hinge=new THREE.Group();hinge.position.set(P0[0],P0[1],(BW.z??-1)*PX*10);hinge.add(mem);
   const bm=new THREE.MeshStandardMaterial({color:new THREE.Color(BW.bone||'#2a1850'),roughness:.4,transparent:true});const bone=(a,b,r0,r1)=>{const d=b.clone().sub(a),L=d.length();const m=new THREE.Mesh(new THREE.CylinderGeometry(r1,r0,L,8),bm);m.position.copy(a.clone().lerp(b,.5));m.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),d.normalize());hinge.add(m);};
   const br=(BW.boneR??3)*PX;bone(S0,Wr,br*1.3,br);for(const tp of tips)bone(Wr,tp,br*.9,br*.25);const claw=new THREE.Mesh(new THREE.ConeGeometry(br*.9,br*4,8),bm);claw.position.copy(Wr).add(new THREE.Vector3(0,br*2,0));hinge.add(claw);
   const extra=[bm];if(BW.stars){const sp=[],R0=()=>{rs=(rs*16807)%2147483647;return rs/2147483647;};let rs=7+sd*3+500;const P3=geo.attributes.position,I3=geo.index.array;for(let i=0;i<BW.stars;i++){const tI=Math.floor(R0()*(I3.length/3))*3;let a=R0(),b=R0();if(a+b>1){a=1-a;b=1-b;}const v=[0,1,2].map(j=>new THREE.Vector3().fromBufferAttribute(P3,I3[tI+j]));const q=v[0].clone().addScaledVector(v[1].clone().sub(v[0]),a).addScaledVector(v[2].clone().sub(v[0]),b);sp.push(q.x,q.y,q.z+.004);}
   const sg=new THREE.BufferGeometry();sg.setAttribute('position',new THREE.Float32BufferAttribute(sp,3));const smat=new THREE.PointsMaterial({color:0xf4eeff,size:BW.starSize??.035,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false});hinge.add(new THREE.Points(sg,smat));extra.push(smat);}
   group.add(hinge);wings.push({hinge,sd,wm,bat:true,extra});}}
 else if(wingPx.length){for(const sd of [-1,1]){const px=wingPx.filter(p=>Math.sign(p[0]-wcx)===sd);if(px.length<30)continue;
   let x1=W,x2=0,y1=H,y2=0;for(const p of px){x1=Math.min(x1,p[0]);x2=Math.max(x2,p[0]);y1=Math.min(y1,p[1]);y2=Math.max(y2,p[1]);}
   const tw=x2-x1+1,th=y2-y1+1,cv=document.createElement('canvas');cv.width=tw;cv.height=th;const g=cv.getContext('2d');const id=g.createImageData(tw,th);
   for(const p of px){const k=((p[1]-y1)*tw+(p[0]-x1))*4;id.data[k]=p[2];id.data[k+1]=p[3];id.data[k+2]=p[4];id.data[k+3]=255;}g.putImageData(id,0,0);
   const tex=new THREE.CanvasTexture(cv);tex.colorSpace=THREE.SRGBColorSpace;
   const rootX=sd<0?x2:x1,rootY=(y1+y2)/2;const geo2=new THREE.PlaneGeometry(tw*PX,th*PX,40,24);const pa=geo2.attributes.position;
   for(let v=0;v<pa.count;v++){const u=(pa.getX(v)/(tw*PX)+.5),w=(pa.getY(v)/(th*PX)+.5);const fromRoot=sd<0?1-u:u;const ang=Math.atan2(w-.5,fromRoot+.05);
    const ridge=Math.pow(Math.max(0,Math.cos(ang*5)),6)*.16*fromRoot+(1-Math.min(1,Math.abs(w-.5)*8))*.06;pa.setZ(v,ridge-fromRoot*fromRoot*.12);}geo2.computeVertexNormals();
   geo2.translate((x1+tw/2-rootX)*PX,0,0);
   const wm=new THREE.MeshPhysicalMaterial({map:tex,transparent:true,alphaTest:.5,side:THREE.DoubleSide,roughness:.45,sheen:1,sheenColor:new THREE.Color(o.sheen||'#a07cff'),transmission:0,emissive:new THREE.Color(0x2a1a70),emissiveIntensity:.35});
   const mesh=new THREE.Mesh(geo2,wm);const hinge=new THREE.Group();const [hx,hy,hz]=L2W(rootX,rootY+(y1+th/2-rootY),-1);hinge.position.set(hx,hy,hz);hinge.add(mesh);group.add(hinge);wings.push({hinge,sd,wm});}}

 const scv=document.createElement('canvas');scv.width=scv.height=128;{const g=scv.getContext('2d');const gr=g.createRadialGradient(64,64,0,64,64,64);gr.addColorStop(0,'rgba(0,0,0,.85)');gr.addColorStop(.5,'rgba(0,0,0,.45)');gr.addColorStop(1,'rgba(0,0,0,0)');g.fillStyle=gr;g.fillRect(0,0,128,128);}
 const shadow=new THREE.Mesh(new THREE.PlaneGeometry(1,1),new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(scv),transparent:true,depthWrite:false}));
 shadow.rotation.x=-Math.PI/2;const shW=(bx2-bx1)*PX*1.1;shadow.position.set((cxm-W/2)*PX,footY+.01,0);shadow.scale.set(shW,shW*.45,1);
 // ---- star dust: ambient motes orbiting the creature (shared with idle trading) ----
 const ND=420,dpos=new Float32Array(ND*3),dph=new Float32Array(ND);for(let i=0;i<ND;i++){const r=2.2+R0()*2.6,a=R0()*6.283,y=(R0()-.5)*4;dpos.set([Math.cos(a)*r,y,Math.sin(a)*r],i*3);dph[i]=R0()*10;}
 const dgeo=new THREE.BufferGeometry();dgeo.setAttribute('position',new THREE.BufferAttribute(dpos,3));
 const dust=new THREE.Points(dgeo,new THREE.PointsMaterial({size:.045,color:0xb8a2ff,transparent:true,opacity:.75*(o.dustK??1),depthWrite:false,blending:THREE.AdditiveBlending}));
 // ---- Going-Ghost ring sweep (bits <-> body) ----
 const ringTop=(H/2-by1+4)*PX,ringBot=footY,ringMid=(H/2-cym)*PX,ringR=(bx2-bx1)*PX*.62;let ring=null;
 const rings=[0,1].map(()=>{const m=new THREE.Mesh(new THREE.TorusGeometry(1,.022,8,96),new THREE.MeshBasicMaterial({color:o.ringColor||0xb9a6ff,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false}));m.rotation.x=Math.PI/2;m.visible=false;group.add(m);return m;});
 const NS=600,spkP=new Float32Array(NS*3).fill(-999),spkV=new Float32Array(NS*3),spkL=new Float32Array(NS),spk={i:0};const spkGeo=new THREE.BufferGeometry();spkGeo.setAttribute('position',new THREE.BufferAttribute(spkP,3));
 const spkPts=new THREE.Points(spkGeo,new THREE.PointsMaterial({size:.06,color:0xf0e8ff,transparent:true,blending:THREE.AdditiveBlending,depthWrite:false}));spkPts.frustumCulled=false;group.add(spkPts);
 const clipIn=[new THREE.Plane(new THREE.Vector3(0,-1,0),0),new THREE.Plane(new THREE.Vector3(0,1,0),0)],clipOut=[new THREE.Plane(new THREE.Vector3(0,1,0),0),new THREE.Plane(new THREE.Vector3(0,-1,0),0)];
const wireMat=new THREE.MeshBasicMaterial({color:o.dataColor||0x4fe6ff,transparent:true,opacity:.6,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide});
 wireMat.onBeforeCompile=sh=>{sh.vertexShader='varying vec3 vLP;\n'+sh.vertexShader.replace('#include <begin_vertex>','#include <begin_vertex>\nvLP=position;');
  sh.fragmentShader='varying vec3 vLP;\n'+sh.fragmentShader.replace('#include <clipping_planes_fragment>','#include <clipping_planes_fragment>\n float ly=fract(vLP.y*30.),lx=fract((vLP.x*.8+vLP.z)*12.);float dl=min(min(ly,1.-ly)*1.6,min(lx,1.-lx));if(dl>.045)discard;');};
 const wclip=[new THREE.Plane(new THREE.Vector3(0,-1,0),0),new THREE.Plane(new THREE.Vector3(0,1,0),0)];wireMat.clippingPlanes=wclip;
 const wireM=new THREE.Mesh(bg,wireMat);wireM.visible=false;wireM.scale.setScalar(1.004);body.add(wireM);
 const digiLights=[0,1].map(()=>{const m=new THREE.Mesh(new THREE.SphereGeometry(.07,12,8),new THREE.MeshBasicMaterial({color:0xffffff}));m.visible=false;group.add(m);return m;});
 let charge=0;
 // ---- emotion presets (Motion Bible §2 matrix) ----
 const EMO={calm:{tailHz:.4,tailAmp:1,bobHz:.55,bobAmp:1,breathHz:.35,blinkMin:2.5,blinkMax:4.5,lid:0,tilt:4,tiltBias:0,lean:0,tremble:0,squash:1,anger:0,hopEvery:0,arousal:.45,dust:1},
  happy:{tailHz:2.2,tailAmp:1.6,bobHz:.7,bobAmp:1.2,breathHz:.45,blinkMin:2,blinkMax:3.5,lid:.32,tilt:6,tiltBias:0,lean:3,tremble:0,squash:1,anger:0,hopEvery:2.3,arousal:.7,dust:1.6},
  curious:{tailHz:1.5,tailAmp:.5,bobHz:.55,bobAmp:.8,breathHz:.35,blinkMin:3,blinkMax:5,lid:0,tilt:3,tiltBias:16,lean:14,tremble:0,squash:1,anger:0,hopEvery:0,arousal:.6,dust:1},
  scared:{tailHz:3,tailAmp:.3,bobHz:.85,bobAmp:.5,breathHz:.9,blinkMin:1.4,blinkMax:2.4,lid:0,tilt:0,tiltBias:0,lean:-8,tremble:.014,squash:.9,anger:0,hopEvery:0,arousal:1,dust:.6},
  sleepy:{tailHz:.2,tailAmp:.6,bobHz:.28,bobAmp:3,breathHz:.22,blinkMin:3,blinkMax:6,lid:.7,tilt:8,tiltBias:-5,lean:-4,tremble:0,squash:.97,anger:0,hopEvery:0,arousal:.2,dust:.7},
  angry:{tailHz:1,tailAmp:1.4,bobHz:.85,bobAmp:.6,breathHz:.6,blinkMin:3,blinkMax:5,lid:.25,tilt:0,tiltBias:0,lean:10,tremble:.003,squash:.96,anger:1,hopEvery:0,arousal:.95,dust:1.3}};
 const P=Object.assign({},EMO.calm);let emoTgt=EMO.calm,emoName='calm',emoT=9,nextHop=1e9;
 function setEmotion(n){if(!EMO[n])return;emoTgt=EMO[n];emoName=n;emoT=0;nextHop=t+BB.anticipate+.4;}
 const dustBase=new THREE.Color(0xb8a2ff),hot=new THREE.Color('#ff3a2a');let bobPh=0,brPh=0;
 function transform(to){ring={t:0,to};morphT=to;}
 // ---- state ----
 let t=0,morph=0,morphT=0,hopT=-1,birthT=1e9,nextBlink=1.5,blinkT=-1,tailPh=0,nextTilt=1,tilt0=0,tiltTgt=0,tiltNow=0,tiltT=-1;const sparkle=new Float32Array(N);const fl=[0,0,0];
 const away=new Float32Array(N);const awayTgt=new Int32Array(N).fill(-1);const born=new Float32Array(N).fill(1);
 function birth(){birthT=0;for(let n=0;n<N;n++){/* cluster-scatter birth: particles arrive from 14 drifting clusters (glyph-like knots) instead of a uniform shell */const K=14,ci=(n*7)%K,cr=11+((ci*.618)%1)*9,ca=ci*2.39996,cb=Math.acos(2*((ci*.381+.13)%1)-1),j=.9+seed[n]*1.4,ja=seed[n]*977.1,jb=(seed[n]*7919)%1*6.2832;pos[n*3]=Math.sin(cb)*Math.cos(ca)*cr+Math.cos(ja)*Math.sin(jb)*j;pos[n*3+1]=Math.cos(cb)*cr*.55+Math.cos(jb)*j;pos[n*3+2]=-3-Math.abs(Math.sin(cb)*Math.sin(ca))*cr*.6+Math.sin(ja)*Math.sin(jb)*j;born[n]=0;}vel.fill(0);}
 let happyT=-1,scattered=false;function hop(){if(hopT>=0)return;hopT=0;scattered=false;S.arousal=1;}
 function scatter(){for(let n=0;n<N;n++)if(seed[n]<.10&&!parts[n].eye){const ci=(n*7)%14,a=ci*2.39996+seed[n]*.5,b=ci*1.7+seed[n]*.5;vel[n*3]+=Math.cos(a)*1.6;vel[n*3+1]+=1.0+Math.sin(b);vel[n*3+2]+=Math.sin(a)*1.6;sparkle[n]=1;}}
 const eyeY=L2W(0,ey,0)[1],eyeRw=eR*.9*PX;
 function step(dt){t+=dt;S.step(dt);
  emoT+=dt;const ant=emoT<BB.anticipate?Math.sin(Math.PI*emoT/BB.anticipate):0;if(emoT>=BB.anticipate){const a=1-Math.exp(-dt/((BB.snapIn+BB.settle)*.35));for(const k2 in P)P[k2]+=(emoTgt[k2]-P[k2])*a;}
  S.arT=P.arousal;if(P.hopEvery>.5&&emoTgt.hopEvery>0&&hopT<0&&!ring&&t>nextHop){hop();nextHop=t+emoTgt.hopEvery*(.8+R0()*.4);}
  bobPh+=dt*2*Math.PI*P.bobHz;brPh+=dt*2*Math.PI*P.breathHz;
  const bob=Math.sin(bobPh)*BB.idleBobAmp*P.bobAmp*(ringTop-ringBot);const breathe=1+.025*Math.sin(brPh)*(.6+.4*S.coh);if(t>=nextBlink){blinkT=0;nextBlink=t+P.blinkMin+R0()*(P.blinkMax-P.blinkMin);}let blink=0;if(blinkT>=0){blinkT+=dt;const u=blinkT/DP.blinkDur;blink=u<.4?EASE.snapIn(u/.4):u<.55?1:u<1?1-EASE.cushion((u-.55)/.45):0;if(u>=1)blinkT=-1;}
  const hap=happyT>=0?clamp(1-(happyT-DP.holdStrong)/.6):0;if(happyT>=0){happyT+=dt;if(happyT>DP.holdStrong+.6)happyT=-1;}
  tailPh+=dt*2*Math.PI*(P.tailHz+(DP.happyTailHz-P.tailHz)*hap);const sway=Math.sin(tailPh+S.L.x*.02)*.35*(P.tailAmp+(DP.happyTailAmp-P.tailAmp)*hap);
  if(t>=nextTilt){tilt0=tiltNow;tiltTgt=(R0()*2-1)*P.tilt*Math.PI/180;tiltT=0;nextTilt=t+2+R0()*2;}if(tiltT>=0){tiltT+=dt;tiltNow=tilt0+(tiltTgt-tilt0)*EASE.cushion(Math.min(1,tiltT/DP.holdExpression));}
  const fsg=dir?-dir:1;group.rotation.z=tiltNow*(1-.6*hap)+(P.tiltBias*.5+P.lean)*Math.PI/180*fsg;group.position.x=Math.sin(t*2*Math.PI*10)*P.tremble*(1+R0()*.3);
  const lidB=Math.max(blink,P.lid);rimU.A.value.copy(rimBase[0]).lerp(hot,P.anger*.85);rimU.B.value.copy(rimBase[1]).lerp(hot,P.anger*.6);for(const im of irisMs)im.color.setScalar(1+P.anger*.9);
  dust.material.color.copy(dustBase).lerp(hot,P.anger*.7);dust.material.opacity=Math.min(1,.55*P.dust);
  const k=60*(.6+.6*S.hebb),damp=Math.exp(-dt*(6+4*S.coh));let hopY=bob,sy=P.squash*(1-.05*ant);if(hopT>=0){hopT+=dt;const HP=hopPose(hopT);hopY=HP.y+bob;sy=HP.sy*P.squash;if(HP.phase>=1&&!scattered){scattered=true;scatter();}if(HP.phase===3&&happyT<0&&hopT<DP.anticipate+T_AIR+DP.snapIn+.05)happyT=0;if(hopT>DP.anticipate+T_AIR+DP.snapIn+.9)hopT=-1;}
  const sxz=1/Math.sqrt(sy);
  const lx=S.L.x*.0015,ly=S.L.y*.0015,lz=(S.L.z-25)*.0015;const ax=TB?L2W(TB[0],TB[1],0):null;
  // dust motes drift on the CST flow, tethered to their orbit shell
  for(let i=0;i<ND;i++){const p=i*3;cstFlow(dpos[p],dpos[p+1],dpos[p+2],t+dph[i],S,fl);dpos[p]+=(fl[0]*.25-dpos[p+2]*.12)*dt;dpos[p+1]+=fl[1]*.15*dt;dpos[p+2]+=(fl[2]*.25+dpos[p]*.12)*dt;
   const r=Math.hypot(dpos[p],dpos[p+2]);const want=2.2+(dph[i]%1)*2.6;dpos[p]*=1+(want-r)/r*dt*.5;dpos[p+2]*=1+(want-r)/r*dt*.5;dpos[p+1]*=1-dt*.05;}
  dgeo.attributes.position.needsUpdate=true;
  // idle trading: a few bits leave to ride a dust mote, then come home
  if(birthT>4&&hopT<0&&R0()<dt*6*(o.tradeK??1)){const n=(R0()*N)|0;if(!parts[n].eye&&away[n]<=0&&Math.abs(parts[n].z)>0){away[n]=2+R0()*2.5;awayTgt[n]=(R0()*ND)|0;}}
  const bt=birthT<1e8?(birthT+=dt):99;
  for(let n=0;n<N;n++){const p=parts[n];let rx=rest[n*3],ry=rest[n*3+1],rz=rest[n*3+2];
   ry=ry*breathe+(breathe-1)*.4;rx*=1+(breathe-1)*.5;rz*=1+(breathe-1)*1.2;
   if(p.tail&&ax){const dx=rx-ax[0],dy=ry-ax[1];const w=Math.min(1,Math.hypot(dx,dy)/1.2);const a=sway*w;rx=ax[0]+dx*Math.cos(a)-dy*Math.sin(a);ry=ax[1]+dx*Math.sin(a)+dy*Math.cos(a);rz+=Math.sin(t*3+dx*3)*.06*w;}
   if(p.top&&o.hatSway){const h=Math.max(0,ry-.8);rx+=Math.sin(t*1.7)*.05*h*h;}
   let covered=false;if(p.eye){covered=(eyeY+eyeRw-rest[n*3+1])<lidB*2.1*eyeRw;}
   ry=footY+(ry-footY)*sy;rx*=sxz;rz*=sxz;ry+=hopY;const j=(1-S.coh)*.6+.15;rx+=lx*j*Math.sin(seed[n]*50+t);ry+=ly*j*Math.cos(seed[n]*31+t);rz+=lz*j;
   let kk=k,flowW=0;
   if(born[n]<1){const start=seed[n]*1.6;if(bt<start){flowW=1;kk=0;}else{born[n]=Math.min(1,(bt-start)/1.8);kk=k*born[n]*born[n];flowW=1-born[n];}}
   if(away[n]>0){away[n]-=dt;const d=awayTgt[n]*3;const out=away[n]>1.2;if(out){rx=dpos[d];ry=dpos[d+1];rz=dpos[d+2];kk=k*.06;}else kk=k*.25;sparkle[n]=Math.max(sparkle[n],.6);}
   const s=sparkle[n];if(s>0&&away[n]<=0)kk*=(1-s)*.5;
   if(flowW>0){cstFlow(pos[n*3]*.6,pos[n*3+1]*.6,pos[n*3+2]*.6,t,S,fl);for(let a=0;a<3;a++)vel[n*3+a]+=fl[a]*1.6*flowW*dt;}
   for(let a=0;a<3;a++){const r=a==0?rx:a==1?ry:rz;const ii=n*3+a;vel[ii]+=(r-pos[ii])*kk*dt;if(s>0&&a==1&&away[n]<=0)vel[ii]-=1.2*dt*s;vel[ii]*=born[n]<1?Math.exp(-dt*2.5):damp;pos[ii]+=vel[ii]*dt;}
   if(s>0&&away[n]<=0)sparkle[n]=Math.max(0,s-dt*.9);
   const bornGlow=born[n]<1?(1-born[n]):0;glowA[n]=p.eye?(covered?0:.45):(sparkle[n]>0?sparkle[n]:-.6*bornGlow);
   if(p.eye&&covered){cols[n*3]=.17;cols[n*3+1]=.13;cols[n*3+2]=.22;}
   else if(bornGlow>0){const q=bornGlow;cols[n*3]=p.c[0]*(1-q)+.26*q;cols[n*3+1]=p.c[1]*(1-q)+.23*q;cols[n*3+2]=p.c[2]*(1-q)+.46*q;}else cols.set(p.c,n*3);}
  geo.attributes.position.needsUpdate=true;geo.attributes.glow.needsUpdate=true;geo.attributes.color.needsUpdate=true;
  let lo=0,hi=0,mode=0;
  let wlo=0,whi=0,flash=0;
  if(ring){ring.t+=dt;const rt=ring.t;const mid=ringMid+hopY;const T1=BB.morphCharge,T2=T1+BB.morphRewrite,T3=T2+BB.morphBurst,T4=T3+BB.morphReveal;
   // 1 charge: particles energize + rings form at the waist, digivice lights spin
   const ch=clamp(rt/T1);let sp=0;if(rt>T1)sp=EASE.ghost(clamp((rt-T1)/BB.morphRewrite));
   const sp2=clamp((sp-.28)/.72); // solid skin trails the data/wireframe front
   whi=mid+(ringTop-ringMid)*sp+.02;wlo=mid-(ringMid-ringBot)*sp-.02;hi=mid+(ringTop-ringMid)*sp2+.02;lo=mid-(ringMid-ringBot)*sp2-.02;if(sp2<=0){hi=lo=mid;}
   mode=ring.to>.5?1:2;charge=ch*(1-sp);
   if(rt>T2&&rt<T3)flash=Math.sin(Math.PI*(rt-T2)/BB.morphBurst);
   const fo=rt<T1?EASE.snapOut(ch):rt<T2?1:clamp(1-(rt-T2)/BB.morphBurst);for(const rg of rings){rg.material.opacity=fo;rg.visible=fo>.01;}
   rings[0].position.y=rt<T1?mid:whi;rings[1].position.y=rt<T1?mid:wlo;const sc=ringR*(rt<T1?.6+.4*EASE.snapOut(ch):1);rings[0].scale.setScalar(sc);rings[1].scale.setScalar(sc);rings[0].rotation.z=rt*9;rings[1].rotation.z=-rt*9;
   for(const [k2,L] of digiLights.entries()){L.visible=fo>.01;const a=rt*10+k2*Math.PI;const rg=rings[k2];L.position.set(Math.cos(a)*sc,rg.position.y,Math.sin(a)*sc);}
   // sparkles: spiral UP during charge, leading-edge during rewrite, burst at flash, arc DOWN on reveal
   const emit=(n,fn)=>{for(let e=0;e<n;e++){const i=spk.i++%NS;fn(i);}};
   if(rt<T1)emit(4,i=>{const a=R0()*6.283;spkP.set([Math.cos(a)*ringR*.9,ringBot+R0()*.4,Math.sin(a)*ringR*.9],i*3);spkV.set([-Math.sin(a)*1.2,1.8+R0(),Math.cos(a)*1.2],i*3);spkL[i]=.5;});
   else if(sp<1)emit(8,i=>{const a=R0()*6.283,y=R0()<.5?whi:wlo;spkP.set([Math.cos(a)*ringR,y,Math.sin(a)*ringR],i*3);spkV.set([Math.cos(a)*.6,(R0()-.5)*.8,Math.sin(a)*.6],i*3);spkL[i]=BB.ringSparkle+R0()*.25;});
   else if(rt<T3)emit(25,i=>{const a=R0()*6.283,b=R0()*3.14;spkP.set([0,mid,0],i*3);const v=2.5+R0()*2;spkV.set([Math.sin(b)*Math.cos(a)*v,Math.cos(b)*v,Math.sin(b)*Math.sin(a)*v],i*3);spkL[i]=.45;});
   else if(rt<T4)emit(3,i=>{const a=R0()*6.283;spkP.set([Math.cos(a)*ringR*.3,ringTop+.3,Math.sin(a)*ringR*.3],i*3);spkV.set([Math.cos(a)*1.4,-.5,Math.sin(a)*1.4],i*3);spkL[i]=.6;});
   if(sp>=1){mode=ring.to>.5?1:2;}
   if(rt>=T3){morph=morphT=ring.to;mode=0;}
   if(rt>T4)ring=null;}
  else{morph+=(morphT-morph)*Math.min(1,dt*3);if(Math.abs(morphT-morph)<.002)morph=morphT;}
  for(let i=0;i<NS;i++){if(spkL[i]>0){spkL[i]-=dt;for(let a=0;a<3;a++)spkP[i*3+a]+=spkV[i*3+a]*dt;spkV[i*3+1]-=.6*dt;}else spkP[i*3+1]=-999;}spkGeo.attributes.position.needsUpdate=true;
  if(mode===2)pmat.uniforms.uBand.value.set(lo,hi,mode);else pmat.uniforms.uBand.value.set(wlo,whi,mode);pmat.uniforms.uCharge.value=charge;
  wireM.visible=mode>0;if(mode>0){wclip[0].constant=whi;wclip[1].constant=-wlo;wireMat.opacity=.6;}bmat.emissiveIntensity=1;bmat.emissive.setRGB(flash*.9,flash*.8,flash);
  if(mode===1){bmat.clippingPlanes=clipIn;bmat.clipIntersection=false;clipIn[0].constant=hi;clipIn[1].constant=-lo;}else if(mode===2){bmat.clippingPlanes=clipOut;bmat.clipIntersection=true;clipOut[0].constant=-whi;clipOut[1].constant=wlo;}else bmat.clippingPlanes=null;
  for(const w of wings){if(w.bat){const BW=o.batWings,hz=(BW.hz??1.1)*(1+P.anger*.3),u=((t*hz+(w.sd>0?0:.02))%1+1)%1,dn=BW.down??.35;let a;if(u<dn)a=(BW.up??.6)+((BW.lo??-.3)-(BW.up??.6))*EASE.snapOut(u/dn);else{const v=(u-dn)/(1-dn);a=(BW.lo??-.3)+((BW.up??.6)-(BW.lo??-.3))*EASE.cushion(v)+(v<.25?-.08*Math.sin(v/.25*Math.PI):0);}
   w.hinge.rotation.y=-w.sd*a;w.hinge.rotation.z=w.sd*.12*Math.sin(u*Math.PI*2);w.hinge.scale.x=1-(u>dn?.12*Math.sin((u-dn)/(1-dn)*Math.PI):0);const wb=bt<99?clamp((bt-1.6)/1.8):1;w.wm.opacity=wb*Math.min(1,Math.max(0,(morph-.35)/.5));for(const m of w.extra)m.opacity=w.wm.opacity;w.hinge.visible=w.wm.opacity>.01&&!w.hinge.userData.hide;continue;}
   const f=Math.sin(t*2*Math.PI*(o.wings?.hz??1.1)+(w.sd>0?0:.15));w.hinge.rotation.y=w.sd*(.05+.3*f)*(1+P.anger*.3);w.hinge.rotation.z=w.sd*.08*f;w.hinge.position.y+=0;const wb=bt<99?clamp((bt-1.6)/1.8):1;w.wm.opacity=wb*Math.min(1,Math.max(0,(morph-.35)/.5));w.wm.alphaTest=wb<.99?.02:.5;w.hinge.visible=w.wm.opacity>.01&&!w.hinge.userData.hide;}
  if(halo){const hs=halo.userData.s*(1+.08*Math.sin(t*2*Math.PI*.7));halo.scale.set(hs,hs,1);halo.material.opacity=.85*(ring?0:morph)*(1+.25*P.anger);}
  body.position.y=hopY+footY*(1-sy);body.scale.set(MCS*(1+(breathe-1)*.5)*sxz,MCS*breathe*sy,MCS*(1+(breathe-1)*1.2)*sxz);if(morph>.001){bendTail(sway*.9*(o.tailAmp??1));setLids(lidB);}
  // contact shadow: shrinks + fades with hop height; fades in as the body condenses
  const bAmt=bt<99?clamp((bt-1.2)/2.5):1;const hs=1-hopY*.45;shadow.scale.set(shW*hs,shW*.45*hs,1);shadow.material.opacity=(.85-hopY*.5)*bAmt;
  // render-state
  const m=ring?(mode? (ring.to>.5?0:1):morph):morph;const bm=ring?1:m;pmat.uniforms.uFade.value=ring?1:1-m;points.visible=ring?true:(o.bitsHideFormed?m<.999:(m<.999||hopT>=0));body.visible=ring?true:m>.001;bmat.opacity=bm;if(outl)outl.material.opacity=bm*bm;for(const sm of SHELLS){sm.material.opacity=sm.material.userData.a*bm*bm;sm.visible=bm>.05;}bmat.transparent=bm<.999;bmat.depthWrite=bm>.5;const fm=ring?(ring.to>.5?clamp((ringTop-hi)<.01?1:0):(lo<=ringBot+.03?0:1)):m;WMat.opacity=.85*fm;lidMat.opacity=fm;for(const [mm,a] of eyeMats)mm.opacity=a*fm;
  return {hopY};}
 return {group,shadow,dust,step,hop,birth,points,pmat,body,footY,setMorph:v=>morphT=v,transform,setEmotion,emotions:Object.keys(EMO),forceMorph:v=>{morph=morphT=v;},hideWings:h=>{for(const w of wings)w.hinge.userData.hide=h;},
  tailProbe:()=>{if(!tailV.length)return null;let tip=tailV[0],base=tailV[0];for(const q of tailV){if(q[6]>tip[6])tip=q;if(q[6]<base[6])base=q;}body.updateMatrixWorld();const P2=v=>new THREE.Vector3(tp.getX(v),tp.getY(v),tp.getZ(v)).applyMatrix4(body.matrixWorld).toArray().map(n=>+n.toFixed(4));const piv=TBL.clone().applyMatrix4(body.matrixWorld).toArray().map(n=>+n.toFixed(4));return {piv,tip:P2(tip[0]),base:P2(base[0]),tipRest:[tip[1],tip[2]],baseRest:[base[1],base[2]]};},
  info:{attached,W,H,N,tris,eyes:eyes.map(e=>({x:+e.x.toFixed(1),y:+e.y.toFixed(1),r:+e.r.toFixed(1),n:e.n})),bb:[bx1,by1,bx2,by2],cand:cand.length,frontal,dir,tail:TB,tailVerts:tailV.length,get icicles(){return icicleCount;},get sdf(){return sdfInfo;},overlay:ovInfo,get trimEdges(){return trimEdges;},get fillMs(){return +fillMs.toFixed(1);},whiskers:!!wantW},S};}
