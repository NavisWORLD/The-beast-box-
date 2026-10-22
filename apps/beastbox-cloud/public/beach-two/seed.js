// Quantum seed stream: stream = SHA-256(outcomes || counter), consumed strictly in order.
// outcomes = the recorded IBM CHSH outcome string (UTF-8 "0"/"1"), counter = 8-byte big-endian.
// Only RECORDED_IBM_HARDWARE receipts are accepted. Nothing here (or anywhere in the toy) calls the built-in PRNG.
const K=new Uint32Array([0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]);
const W=new Uint32Array(64);
function compress(st,b,o){for(let i=0;i<16;i++)W[i]=(b[o+4*i]<<24|b[o+4*i+1]<<16|b[o+4*i+2]<<8|b[o+4*i+3])>>>0;
 for(let i=16;i<64;i++){const x=W[i-15],y=W[i-2];const s0=(x>>>7|x<<25)^(x>>>18|x<<14)^(x>>>3),s1=(y>>>17|y<<15)^(y>>>19|y<<13)^(y>>>10);W[i]=(W[i-16]+s0+W[i-7]+s1)>>>0;}
 let a=st[0],bb=st[1],c=st[2],d=st[3],e=st[4],f=st[5],g=st[6],h=st[7];
 for(let i=0;i<64;i++){const S1=(e>>>6|e<<26)^(e>>>11|e<<21)^(e>>>25|e<<7),ch=(e&f)^(~e&g),t1=(h+S1+ch+K[i]+W[i])>>>0,S0=(a>>>2|a<<30)^(a>>>13|a<<19)^(a>>>22|a<<10),mj=(a&bb)^(a&c)^(bb&c),t2=(S0+mj)>>>0;h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=bb;bb=a;a=(t1+t2)>>>0;}
 st[0]=st[0]+a>>>0;st[1]=st[1]+bb>>>0;st[2]=st[2]+c>>>0;st[3]=st[3]+d>>>0;st[4]=st[4]+e>>>0;st[5]=st[5]+f>>>0;st[6]=st[6]+g>>>0;st[7]=st[7]+h>>>0;}
const IV=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
export function sha256Hex(bytes){const st=new Uint32Array(IV);const n=bytes.length,full=Math.floor(n/64)*64;for(let o=0;o<full;o+=64)compress(st,bytes,o);
 const rem=n-full,padLen=rem<56?64:128,t=new Uint8Array(padLen);t.set(bytes.subarray(full));t[rem]=0x80;const bits=n*8;
 for(let i=0;i<8;i++)t[padLen-1-i]=Math.floor(bits/2**(8*i))&255;for(let o=0;o<padLen;o+=64)compress(st,t,o);return [...st].map(x=>x.toString(16).padStart(8,'0')).join('');}
export class SeedStream{
 constructor(outcomes){this.bytes=new TextEncoder().encode(outcomes);const n=this.bytes.length;this.full=Math.floor(n/64)*64;
  this.mid=new Uint32Array(IV);for(let o=0;o<this.full;o+=64)compress(this.mid,this.bytes,o);this.tail=this.bytes.subarray(this.full);this.reset();}
 reset(){this.counter=0;this.buf=new Uint32Array(8);this.idx=8;this.drawn=0;}
 block(){const rem=this.tail.length+8,n=this.bytes.length+8,padLen=rem<56?64:128,t=new Uint8Array(padLen);t.set(this.tail);
  let c=this.counter;for(let i=7;i>=0;i--){t[this.tail.length+i]=c&255;c=Math.floor(c/256);}t[rem]=0x80;const bits=n*8;
  for(let i=0;i<8;i++)t[padLen-1-i]=Math.floor(bits/2**(8*i))&255;const st=new Uint32Array(this.mid);for(let o=0;o<padLen;o+=64)compress(st,t,o);this.buf=st;this.idx=0;this.counter++;}
 u32(){if(this.idx>=8)this.block();this.drawn++;return this.buf[this.idx++];}
 next(){return this.u32()/4294967296;}             // [0,1)
 range(a,b){return a+(b-a)*this.next();}
 chance(p){return this.next()<p;}
 angle(){return this.next()*Math.PI*2;}
}
export const SEEDS=[{file:'alien-injection-001',job:'dba11mvi0auc7391bpbg'},{file:'second-coming-iii',job:'db98qos24mrc7383l7f0'},{file:'second-coming-ii',job:'db98b8k24mrc7383km4g'},{file:'second-coming-i',job:'db97pngc77vs73811img'}];
export async function loadSeed(entry){
 try{const r=await fetch('./seeds/'+entry.file+'.json',{cache:'force-cache'});if(!r.ok)throw 0;const d=await r.json();
  if(d.source_class!=='RECORDED_IBM_HARDWARE'||d.job_id!==entry.job||typeof d.outcomes!=='string'||!/^[01]+$/.test(d.outcomes))throw 0;
  const bytes=new TextEncoder().encode(d.outcomes);const mine=sha256Hex(bytes);
  let web=mine;if(crypto?.subtle){const h=await crypto.subtle.digest('SHA-256',bytes);web=[...new Uint8Array(h)].map(x=>x.toString(16).padStart(2,'0')).join('');}
  if(mine!==d.outcomes_sha256||web!==d.outcomes_sha256||d.outcomes.length!==2*d.rounds)throw 0;
  return {...d,ok:true,stream:new SeedStream(d.outcomes)};
 }catch{return {...entry,ok:false};}
}
