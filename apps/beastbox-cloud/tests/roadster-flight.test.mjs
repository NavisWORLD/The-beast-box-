import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {FLIGHT,ATMO,FLIGHT_LABEL,gravityAt,circularSpeed,escapeSpeed,airDensity,orbitEnergy,skyFade,liftOff,stepFlight,flightInfo,landingAssist,ascentAssist,orbitElements,len,norm} from '../lib/universe/roadster-flight.mjs';
const R=FLIGHT.R;
const run=(S,inp,secs,dt=1/60,ground)=>{const n=Math.round(secs/dt);for(let i=0;i<n;i++){stepFlight(S,typeof inp==='function'?inp(S,i*dt):inp,dt,ground);}return S;};
test('label is honest: SIMULATED',()=>{assert.equal(FLIGHT_LABEL,'Roadster flight · SIMULATED');});
test('gravity falls as 1/r^2, escape speed is sqrt(2) times circular speed',()=>{
 assert.ok(Math.abs(gravityAt(R)-FLIGHT.g0)<1e-12);assert.ok(Math.abs(gravityAt(2*R)-FLIGHT.g0/4)<1e-12);
 for(const r of [R,12,40,500])assert.ok(Math.abs(escapeSpeed(r)/circularSpeed(r)-Math.SQRT2)<1e-9);});
test('air thins out with height and is exactly the same curve every call',()=>{
 assert.equal(airDensity(0),1);assert.ok(airDensity(ATMO.H)<.37&&airDensity(ATMO.H)>.36);assert.ok(airDensity(20*ATMO.H)<1e-8);
 assert.equal(skyFade(0),1);assert.equal(skyFade(40),0);assert.ok(skyFade(1)>0&&skyFade(1)<1);});
test('a vacuum circular orbit stays circular for three laps (leapfrog keeps the energy)',()=>{
 const r=R+30;const S={p:[r,0,0],v:[0,0,circularSpeed(r)],fwd:[0,0,1],up:[1,0,0],t:0,throttle:0};const T=2*Math.PI*r/circularSpeed(r);
 let lo=1e9,hi=0;const n=Math.round(3*T*60);for(let i=0;i<n;i++){stepFlight(S,{},1/60);const l=len(S.p);lo=Math.min(lo,l);hi=Math.max(hi,l);}
 assert.ok(hi-lo<r*.01,'radius drift '+(hi-lo));assert.ok(Math.abs(orbitEnergy(S.p,S.v))<Math.abs(-FLIGHT.g0*R*R/r)*.5+1);});
test('no drag in vacuum: coasting keeps its speed (nothing slows you down but gravity)',()=>{
 const S={p:[0,0,R+300],v:[40,0,0],fwd:[1,0,0],up:[0,1,0],t:0,throttle:0};const e0=orbitEnergy(S.p,S.v);run(S,{},20);
 assert.ok(Math.abs(orbitEnergy(S.p,S.v)-e0)<.5,'energy moved '+(orbitEnergy(S.p,S.v)-e0));});
test('lift off from the ground, climb through the air and reach space under constant thrust',()=>{
 const S=liftOff([0,0,R+FLIGHT.hullR],[0,0,1],[1,0,0],0);const hist=[];
 run(S,{thrust:1,pitch:0,level:0},8,1/60);const info=flightInfo(S);
 assert.ok(info.alt>8,'alt '+info.alt);assert.ok(info.inSpace,'should be out of the air');});
test('there is no speed, distance or size cap: keep thrusting and you pass escape speed and keep going',()=>{
 const S=liftOff([0,0,R+FLIGHT.hullR],[0,0,1],[1,0,0],0);run(S,{thrust:1,level:0,pitch:.05},25);
 const i=flightInfo(S);assert.ok(i.energy>0&&i.escaping,'energy '+i.energy);assert.ok(i.speed>escapeSpeed(i.r),'speed vs escape');
 const p0=len(S.p);run(S,{thrust:1,level:0},60);assert.ok(len(S.p)>p0*3);assert.ok(flightInfo(S).speed>flightInfo(S).escape);});
test('the planet is solid: dropped from height with no thrust you never end up inside it',()=>{
 const S={p:[0,R+10,0],v:[0,0,0],fwd:[0,0,1],up:[0,1,0],t:0,throttle:0};let min=1e9;for(let i=0;i<60*20;i++){stepFlight(S,{},1/60);min=Math.min(min,len(S.p));}
 assert.ok(min>=R+FLIGHT.hullR-1e-6,'min r '+min);});
test('bumpy ground: the contact radius follows a terrain function',()=>{
 const g=n=>R+.4*Math.sin(n[0]*9);
 const S2={p:[.3,R+4,0],v:[0,0,0],fwd:[0,0,1],up:[0,1,0],t:0,throttle:0};let ok=true;for(let i=0;i<60*10;i++){stepFlight(S2,{},1/60,g);if(len(S2.p)<g(norm(S2.p))+FLIGHT.hullR-1e-6)ok=false;}assert.ok(ok);});
test('pitch, yaw and roll turn the nose without changing the frame handedness',()=>{
 const S=liftOff([0,0,R+.12],[0,0,1],[1,0,0],0);run(S,{pitch:1,yaw:.5,roll:1,level:0},3);
 assert.ok(Math.abs(len(S.fwd)-1)<1e-9&&Math.abs(len(S.up)-1)<1e-9&&Math.abs(S.fwd[0]*S.up[0]+S.fwd[1]*S.up[1]+S.fwd[2]*S.up[2])<1e-9);});
test('the Land assist brings you home softly from orbit height and from a fast dive',()=>{
 for(const [p,v] of [[[0,0,R+20],[0,0,0]],[[0,0,R+25],[-.8,0,-1.8]],[[0,0,R+25],[1.5,0,3]],[[R+40,0,0],[0,0,0]],[[R+30,0,0],[0,circularSpeed(R+30),0]]]){
  const n=norm(p);const S={p:[...p],v:[...v],fwd:norm([v[0]||1,v[1]||0,v[2]||0]),up:n,t:0,throttle:0};let landedAt=null,maxTouch=0;
  for(let i=0;i<60*120&&landedAt===null;i++){stepFlight(S,landingAssist(S),1/60);if(S.touch>maxTouch)maxTouch=S.touch;if(S.landed&&S.t>1)landedAt=S.t;}
  assert.ok(landedAt!==null,'did not land from '+JSON.stringify(p)+' r='+len(S.p)+' v='+len(S.v));assert.ok(maxTouch<FLIGHT.landV*1.6,'touchdown '+maxTouch);}});
test('deterministic: the same inputs give bit-identical states',()=>{
 const mk=()=>{const S=liftOff([0,0,R+.12],[0,0,1],[1,0,0],3);return run(S,(s,t)=>({thrust:t<6?1:0,pitch:Math.sin(t),yaw:Math.cos(t)*.3,roll:0}),12);};
 assert.deepEqual(mk(),mk());});
test('module reads no clock and no Math.random',()=>{const s=readFileSync(new URL('../lib/universe/roadster-flight.mjs',import.meta.url),'utf8').replace(/\/\*[\s\S]*?\*\//g,'');assert.ok(!/Math\.random|Date\.|performance\./.test(s));});
test('orbitElements: a circular orbit has e~0 and periapsis = apoapsis = r; an escape path is open',()=>{
 const r=R+30,S={p:[r,0,0],v:[0,circularSpeed(r),0]};const el=orbitElements(S);assert.ok(el.e<1e-6&&Math.abs(el.peri-r)<1e-6&&Math.abs(el.apo-r)<1e-6&&el.bound);
 const open=orbitElements({p:[r,0,0],v:[0,escapeSpeed(r)*1.1,0]});assert.ok(!open.bound&&open.apo===Infinity);});
test('Exit to orbit: the gravity-turn autopilot climbs from the ground and ends in a bound orbit clear of the air',()=>{
 for(const vg of [0,2,4]){
  const S=liftOff([0,0,R+FLIGHT.hullR],[0,0,1],[1,0,0],vg);let done=false,steps=0;
  for(let i=0;i<60*120&&!done;i++){const I=ascentAssist(S,R);stepFlight(S,I,1/60);done=I.done;steps++;}
  const el=orbitElements(S);
  assert.ok(done,'autopilot finished (vg='+vg+')');assert.ok(el.bound&&el.peri>R+ATMO.H*2,'bound orbit above the air: peri='+el.peri.toFixed(2)+' vg='+vg);
  assert.ok(steps/60<100,'within 100 s');}});
