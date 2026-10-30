// Port of Cosmo's flashes/verify.py (25 checks) plus the signal rules, the limiter and the wiring.
import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {FLASH_PACK as P} from '../lib/universe/flashes-data.mjs';
import {FLASH_LABEL,stormCount,lightningRate,limitFlashes,strikesInMinute,strikesNear,lightningAt,shimmerAt,nebulaRamp,skyFlashEnvelope,boltPath} from '../lib/universe/flashes.mjs';
import {tierSettings} from '../lib/universe/post-tiers.mjs';
const rd=p=>readFileSync(new URL('../'+p,import.meta.url),'utf8');const T=['LOW','MED','HIGH','GOD'];
test('pack wording: no Math.random, no real-physics claim, no live quantum, no AI wording, SEEDED, four tiers',()=>{const txt=JSON.stringify(P).toLowerCase();
 assert.ok(!txt.replace(/(no|never) math\.random/g,'').includes('math.random'));assert.ok(!txt.replace(/not real physics/g,'').includes('real physics'));assert.ok(!txt.includes('live quantum'));assert.doesNotMatch(txt,/\bai\b/);
 assert.match(P.label,/^SEEDED/);assert.deepEqual(Object.keys(P.tiers).sort(),[...T].sort());assert.match(FLASH_LABEL,/ABSENT/);
 for(const f of ['lib/universe/flashes.mjs','lib/universe/flashes-three.ts'])assert.doesNotMatch(rd(f),/Math\.random/);});
test('safety: <= 3 flashes/s, gap >= 0.334 s, large-area delta <= 0.1, reduced-motion fallback, ABSENT = no flash for every kind',()=>{const S=P.safety;
 assert.ok(S.max_flashes_per_s<=3&&S.min_gap_s>=1/3);assert.ok(S.sky_flash_max_delta_lum<=.1);assert.match(S.reduced_motion,/reduced/);assert.match(S.ABSENT,/no flash/);
 for(const k of ['lightning','spark_shimmer','star_flares_booms'])assert.match(P[k].signal,/ABSENT/);});
test('lightning: sky flash capped and decays, not red-dominant, rate range, no second light',()=>{const L=P.lightning;assert.ok(L.sky_flash.add_lum_max<=P.safety.sky_flash_max_delta_lum&&L.sky_flash.decay_s>.2);
 const c=L.sky_flash.colour.linear;assert.ok(c[0]<=.5*(c[0]+c[1]+c[2]));assert.ok(L.rate_per_min.cap/60<=3&&L.rate_per_min.base>0&&L.rate_per_min.base<=2);assert.match(L.thunder_light,/no extra light/);});
test('bloom interaction matches the live p1post thresholds; shimmer never blooms',()=>{for(const t of T){const th=tierSettings(t).bloom.threshold,b=P.lightning.bloom_interaction[t];
 assert.equal(b.p1post_threshold,th);assert.ok(b.sky_flash_peak_scene_lum_max<th);assert.ok(b.bolt_peak<=1.5*th+1e-4);}
 assert.ok(P.spark_shimmer.burst.peak_lum<Math.min(...T.map(t=>tierSettings(t).bloom.threshold)));});
test('seeded schedule sane, nebula ramp from kit visuals, tiers monotone',()=>{const sc=P.sample_schedule_storms3_60s;assert.deepEqual(sc,[...sc].sort((a,b)=>a-b));assert.ok(sc.every(x=>x>=0&&x<=60));
 const N=P.star_flares_booms.nebula_ramp;assert.equal(N.cool_blue.hex,'#1C6CC1');assert.equal(N.violet.hex,'#A65ECB');assert.equal(N.magenta_gold.hex,'#E4A187');
 for(let i=1;i<T.length;i++)for(const k of ['lightning','bolts','shimmer_particles','star_flares','boom_ring','max_concurrent'])assert.ok(P.tiers[T[i]][k]>=P.tiers[T[i-1]][k],T[i]+' '+k);
 assert.deepEqual(nebulaRamp(0),N.magenta_gold.linear);assert.deepEqual(nebulaRamp(1),N.cool_blue.linear);});
test('ABSENT and calm mean nothing flashes',()=>{assert.equal(stormCount(null),null);assert.equal(stormCount({storm:.1}),0);assert.equal(stormCount({storm:.9}),3);assert.equal(lightningRate(null),0);assert.equal(lightningRate(0),0);
 for(let t=0;t<600;t+=.5){const a=lightningAt('s','p',t,null,'MED');assert.equal(a.sky+a.bolt+a.glow,0);assert.equal(a.label,'ABSENT');const z=lightningAt('s','p',t,0,'MED');assert.equal(z.sky+z.bolt,0);}
 assert.equal(shimmerAt(null,null,'MED').on,false);assert.equal(shimmerAt(null,null,'MED').label,'ABSENT');});
test('rate = min(cap, 1.45 x storms); deterministic; the limiter holds 3/s and 0.34 s over a long storm',()=>{assert.ok(Math.abs(lightningRate(3)-P.lightning.rate_per_min.base*3)<1e-9);assert.equal(lightningRate(100),12);
 assert.deepEqual(strikesInMinute('s','p',7,3),strikesInMinute('s','p',7,3));const all=[];for(let T0=0;T0<60;T0++)all.push(...strikesNear('s','p',T0*60+59.9,100).filter(x=>x>=T0*60));
 const L=limitFlashes(all);for(let i=1;i<L.length;i++)assert.ok(L[i]-L[i-1]>=P.safety.min_gap_s-1e-9);for(const t of L)assert.ok(L.filter(x=>x<=t&&t-x<1).length<=3);
 assert.deepEqual(limitFlashes([0,.1,.2,.5,.9,1.3]),[0,.5,.9,1.3]);});
test('sky flash never exceeds +0.08; bolt capped per tier; reduced motion = soft glow only',()=>{let hit=false;for(let t=0;t<1800;t+=.02){const a=lightningAt('s','p',t,3,'GOD');assert.ok(a.sky<=.08+1e-9);assert.ok(a.bolt<=P.lightning.bolt.brightness_cap_by_tier.GOD+1e-9);if(a.sky>0)hit=true;
  const r=lightningAt('s','p',t,3,'GOD',true);assert.equal(r.sky,0);assert.equal(r.bolt,0);assert.ok(r.glow<=.25);}assert.ok(hit,'a long storm does flash');
 assert.equal(lightningAt('s','p',1000,3,'LOW').bolt,0);assert.equal(skyFlashEnvelope(-1),0);assert.equal(boltPath(.3).length,P.lightning.bolt.segments+1);});
test('shimmer: at most one burst a second of spark ticks, none on LOW, below bloom',()=>{let b=null,bursts=new Set();for(let k=0;k<40;k+=.25){const s=shimmerAt(k,b,'HIGH');b=s.burstTick;if(s.on)bursts.add(s.burstTick);assert.ok(s.level<P.spark_shimmer.burst.peak_lum+1e-9);}
 assert.ok(bursts.size<=10&&bursts.size>0);assert.equal(shimmerAt(10,null,'LOW').on,false);});
test('wired into the world on the engine clock with no added light',()=>{const w=rd('components/living-world.tsx'),v=rd('lib/universe/flashes-three.ts');assert.match(w,/addFlashes\(THREE,scene/);assert.match(w,/gxFlash\.update\(\{engineT:field\?/);
 assert.doesNotMatch(v,/new THREE\.\w*Light\(/);assert.match(v,/sky_flash_max_delta_lum/);});
