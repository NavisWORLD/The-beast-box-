// Regenerate Tiny Universe samples: genesis, tick 200, and the first tick (searched in order) with live storms on a life world if any, else any storm.
import {readFileSync,writeFileSync} from 'node:fs';import {genesis,grow} from '../lib/universe/tiny-universe.mjs';import {seededGrowthNodes,growthNodesAt} from '../lib/universe/seeded-growth-nodes.mjs';
const shard=JSON.parse(readFileSync(new URL('../public/spark/ibm-marrakesh-reality-probe-20261009.json',import.meta.url),'utf8'));
const out=(n,u)=>writeFileSync(new URL('../public/universe/'+n,import.meta.url),JSON.stringify(u,null,1)+'\n');
const g=genesis(shard);out('tiny-universe-genesis.json',g);out('tiny-universe-tick200-sample.json',grow(g,200));
let u=g,firstStorm=null,lifeStorm=null;for(let t=1;t<=2000&&!lifeStorm;t++){u=grow(u,1);if(u.storms.length&&!firstStorm)firstStorm=u;if(u.storms.some(s=>u.life.some(l=>l.planet===s.planet)))lifeStorm=u;}
const pick=lifeStorm||firstStorm;if(!pick)throw new Error('no storm in 2000 ticks');out('tiny-universe-storm-sample.json',pick);console.log('storm sample tick',pick.tick,'storms',pick.storms.length,'life-storm',!!lifeStorm);
// Growth sample: the first tick (searched in order) where any seeded growth node reaches 'bloom' on the recorded genesis. The only planet with
// habitability above 0 is below 0.25, so its nodes come from the SEEDED home-world exception (carried as home_exception, recorded habitability unchanged).
{let v=g,hit=null;for(let t=1;t<=600&&!hit;t++){v=grow(v,1);if(growthNodesAt(v,v.tick).some(n=>n.stage==='bloom'))hit=v;}
 if(!hit)throw new Error('no growth node reached bloom in 600 ticks');
 out('tiny-universe-growth-sample.json',{note:'Placement is SEEDED (home world exception, recorded habitability unchanged), the growth drive is SIMULATED, genesis is RECORDED.',universe:hit,growth_nodes:growthNodesAt(hit,hit.tick)});console.log('growth sample tick',hit.tick,'nodes',growthNodesAt(hit,hit.tick).length);}
