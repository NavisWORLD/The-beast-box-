/** Zeref (RAWRPHOS lineage, bb-deada969) cloud memory in his per-beast Azure folder:
 *   beasts/bb-deada969/profile.json           who he is (create-only)
 *   beasts/bb-deada969/model.json             current public RAWRPHOS pin (step, sha)
 *   beasts/bb-deada969/experiences/<tag>.json approved training cycles (create-only, from public releases)
 *   beasts/bb-deada969/lessons/<date>/<id>.json approved teacher lessons (create-only, provenance-labeled)
 * The diary Zeref identity bb-7f9c2a03 is intentionally NOT written here. */
import {ensureContainer,getBlob,putBlob,listBlobs} from './azure-blob.mjs';
export const ZEREF_RAWRPHOS_ID='bb-deada969';
export const ZEREF_DIR=`beasts/${ZEREF_RAWRPHOS_ID}`;
const J=v=>JSON.stringify(v,null,1);
async function createOnly(cfg,name,value){if(await getBlob(cfg,name))return false;await putBlob(cfg,name,J(value),{ifNoneMatch:'*'}).catch(()=>null);return true;}
export async function storeLesson(cfg,record){
 const date=String(record.received_at||new Date().toISOString()).slice(0,10);
 return createOnly(cfg,`${ZEREF_DIR}/lessons/${date}/${record.id}.json`,{...record,beast_id:ZEREF_RAWRPHOS_ID,
  kind:'APPROVED_TEACHER_LESSON',teacher_is_not_zeref_voice:true});
}
export async function syncZerefCloud(cfg,{pin,releases}){
 await ensureContainer(cfg);
 const profileNew=await createOnly(cfg,`${ZEREF_DIR}/profile.json`,{id:ZEREF_RAWRPHOS_ID,name:'Zeref',
  kind:'Spark-Born beast; mind = RAWRPHOS (custom transformer)',provenance:{kind:'recorded-ibm-hardware',backend:'ibm',job_id:'db4q484vf2bc73cuuuag'},
  registered_at:new Date().toISOString(),note:'RAWRPHOS training lineage identity; diary identity bb-7f9c2a03 is separate and untouched.'});
 await putBlob(cfg,`${ZEREF_DIR}/model.json`,J({model_id:pin.model_id,training_steps:pin.training_steps,checkpoint_sha256:pin.checkpoint_sha256,
  release_tag:pin.promotion?.release_tag||null,updated_at:new Date().toISOString(),source:'lib/rawrphos-public-pin.json (reviewed promotion PR)'}));
 let added=0;
 for(const r of releases){if(!/^zeref-006-cycle-\d+-[0-9a-f]{12}$/.test(r.tag_name))continue;
  if(await createOnly(cfg,`${ZEREF_DIR}/experiences/${r.tag_name}.json`,{tag:r.tag_name,published_at:r.published_at,url:r.html_url,
   kind:'APPROVED_TRAINING_CYCLE',note:'CPU training on real native-game observations; batch order from recorded Rigetti SIMULATOR counts (SIMULATED).',production_promoted:false}))added++;}
 const lessons=(await listBlobs(cfg,`${ZEREF_DIR}/lessons/`,{max:2000})).length;
 const experiences=(await listBlobs(cfg,`${ZEREF_DIR}/experiences/`,{max:2000})).length;
 return {profile_created:profileNew,experiences_added:added,experiences,lessons,model_step:pin.training_steps};
}
