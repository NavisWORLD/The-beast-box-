/** Presentation and replay adapters for the existing published Spark registry.
 * No new identities, model assignments, quantum jobs or progress are created here.
 */
import {buildGenome,canonicalJson} from './genome.mjs';
import {buildQbeast} from './qbeast.mjs';
import {validateRun} from './runs.mjs';
import {selectSpark,saveSparkSession} from './identity.mjs';

const recipe=(name,file,job,traits,user,id,seed,body)=>Object.freeze({name,file,run:job+':bell-xx',traits:Object.freeze(traits),user,id,seed,body});
export const CREATURE_RECIPES=Object.freeze([
 recipe('Zeref','ibm-zeref-heart-sound-20261010.json','db4q484vf2bc73cuuuag',{focus:80,calm:20,spark:100},'Zeref-heart-15','bb-deada969','8e2e927e2cfaf489cb7c10172836286bb08869cfff0c2508b5c6371e052e54ed','dragonling'),
 recipe('Wraith','ibm-wraith-20261010.json','db4rg5klf4us73c34tqg',{focus:42,calm:54,spark:71},'WraithGlyphVideoAudio-17','bb-4a61a8d5','385f040c4f5ce01904176448585007de206cd0f92ec34f61f7e08de72256bc85','moth'),
 recipe('Mr Bone Pig','ibm-mr-bone-pig-20261010.json','db4pa784qg6s73c2g5vg',{focus:75,calm:55,spark:84},'BonePigPhoto-24','bb-62603ee3','28a3f13ee58a62a78bf2b03143f2d88210ad037e325870e947037f2a0331222c','pup'),
 recipe('Lumenwisp','ibm-lumenwisp-20261010.json','db4sba4lf4us73c36910',{focus:36,calm:82,spark:46},'Lumenwisp-Generation2','bb-983f386b','4ced51bdaae978a93970996759131f610a1be5bf9c3c5dd12b16849fbc16a0e2','pup'),
 recipe('Umbralet','ibm-real-song-cst12-umbralet-20261009.json','db4og3slf4us73c319h0',{focus:80,calm:20,spark:100},'Music12D-5','bb-1e1759f3','f67c3ba56f42fe7777a905745fa7b64f50aa0950859a8ddd829603a6bd33c4fd','dragonling'),
 recipe('Magmascale','ibm-third-final-reality-probe-20261009.json','db4nlt2mb58s7389er6g',{focus:80,calm:20,spark:100},'Final-gen3-11','bb-e9850e96','98d38e4ca857ffbd878a57eb8f6b8dc5be199b1e9f565dc56945579bc9d5e358','dragonling'),
 recipe('Pistonwyrm','ibm-second-final-reality-probe-20261009.json','db4n37g4qg6s73c2de00',{focus:75,calm:20,spark:95},'Final-gen2-2','bb-d41e5bd4','e0126de4ff158eca0966e7627917001d5d355ca7139ec64375f2343cb954623a','dragonling'),
 recipe('Umbrascale','ibm-final-live-reality-probe-20261009.json','db4m3bslf4us73c2ui9g',{focus:80,calm:20,spark:100},'Ethereal-live-19','bb-8546076e','3b2c070e58d9ff433a3fdf06aa4dc4a5d9ce55511d8c5933f562f395ac880abc','dragonling'),
 recipe('Duskscale','ibm-marrakesh-reality-probe-20261009.json','db4l2uclf4us73c2td10',{focus:80,calm:20,spark:100},'Ethereal-dragon-21','bb-bea717c9','bee3707fa173a6cdf20b79fe79874c6689b9b5e20642139af813132eb937f3a3','dragonling'),
 recipe('Zeref-Nightcat-Dragon','ibm-zeref-nightcat-dragon-20261010.json','db4tc8kvf2bc73cv3np0',{focus:72,calm:55,spark:53},'Zeref-Nightcat-Dragon','bb-f740d771','6c94f1ff03c7ced766b1b0281db3c93816814bbd276c10c6cda8b1cdce8c1398','serpent'),
 recipe('Umbrascale-Starseed','ibm-umbrascale-starseed-20261010.json','db4tdtkvf2bc73cv3qng',{focus:72,calm:56,spark:55},'Umbrascale-Starseed','bb-b396edfe','4895a7212c332b0501f40a5784321aac79e07bdb7f9242ef3602c47e80968eb7','serpent'),
 recipe('Pistonwyrm-Gearseed','ibm-pistonwyrm-gearseed-20261010.json','db4te084qg6s73c2m3lg',{focus:73,calm:57,spark:56},'Pistonwyrm-Gearseed','bb-4c633cb5','226bd3cafa2614315a4b538d6dcb26afe118800538fae7152c5fc2d13aa3fcad','pup'),
 recipe('Heartflare-Moonfire','ibm-heartflare-moonfire-20261010.json','db4te4g4qg6s73c2m470',{focus:73,calm:58,spark:55},'Heartflare-Moonfire','bb-5f6b911b','847950fde92c19fd85b591fc7932c3ba3fb586547eb0d4c0e6ba52564fc19531','biped'),
 recipe('Moonwraith-Cassette-Kit','ibm-moonwraith-cassette-kit-20261010.json','db4te7slf4us73c3888g',{focus:72,calm:56,spark:52},'Moonwraith-Cassette-Kit','bb-c190e914','1ea83dd020ec994e4a8d569fac2a18d86e6701d538a1f7289def97e77fb2ec6a','moth')
]);

export function registeredCreatures(runs=[]){
 const byKey=new Map();
 for(const run of runs){
  const old=byKey.get(run?.key);
  if(old&&canonicalJson(old)!==canonicalJson(run))throw Error('Conflicting recorded creature source.');
  validateRun(run);byKey.set(run.key,run);
 }
 return CREATURE_RECIPES.flatMap(spec=>{
  const run=byKey.get(spec.run);if(!run)return [];
  const genome=buildGenome(spec.traits,run,spec.user,10),snapshot=buildQbeast(genome);
  if(genome.seed!==spec.seed||snapshot.profile.id!==spec.id||genome.body!==spec.body)throw Error('The registered creature no longer reproduces from its original source: '+spec.name);
  return [{...spec,genome,snapshot,source:run,entry:{traits:spec.traits,run:spec.run,user:spec.user}}];
 });
}

/** Caller holds the same Web Lock used by the existing Spark generator. */
export function selectRegisteredCreature(storage,id,runs){
 if(!CREATURE_RECIPES.some(spec=>spec.id===id))throw Error('This creature is not registered.');
 const item=registeredCreatures(runs).find(spec=>spec.id===id);
 if(!item)throw Error('The original recorded creature source is unavailable. No substitute was selected.');
 const session=selectSpark(storage,item.genome);
 // First selection receives the established display alias; a keeper's rename survives.
 if(!session.beast.displayName||Object.values(item.genome.names).includes(session.beast.displayName)){
  session.beast.displayName=item.name;saveSparkSession(storage,session);
 }
 return session;
}

export function creatureVisual({id='',genome=null}={}){
 if(id==='bb-7f9c2a03')return {renderer:'moonwraith-rig',accent:'moonwraith',body:'cat',label:'Moonwraith display persona · established cat rig'};
 const accent=id==='bb-4a61a8d5'?'wraith':id==='bb-62603ee3'?'bone-pig':'native';
 return {renderer:'native-sprite',accent,body:genome?.body||'unknown',label:accent==='wraith'?'Wraith · translucent native moth presentation':accent==='bone-pig'?'Mr Bone Pig · native pup with pig presentation':'Original recorded-genome sprite'};
}
