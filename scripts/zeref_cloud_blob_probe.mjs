#!/usr/bin/env node
/**
 * Authorized, synthetic Azure Blob connectivity probe. Uses the production
 * REST client but only verification/zeref-cloud/<run>-<attempt>/<nonce>.json.
 * No container creation, creature writes, provider jobs, or model calls.
 * Credentials are environment-only. Output contains no URLs or secret values.
 */
import {createHash,randomUUID} from 'node:crypto';
import {mkdirSync,writeFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
import {storageConfig,getBlob,putBlob,deleteBlob} from '../apps/beastbox-cloud/lib/cosmos/azure-blob.mjs';

const APPROVAL='YES_ISOLATED_CREATE_READ_DELETE';
const hash=text=>createHash('sha256').update(text).digest('hex');
const present=value=>!!String(value||'').trim();
function safeError(error){
 return {http_status:Number.isInteger(error?.status)?error.status:null,
  azure_code:/^[A-Za-z][A-Za-z0-9]{0,79}$/.test(error?.code||'')?error.code:null};
}

function validateConfiguration(cfg,now,expectedContainer='beast-cosmos'){
 if(!cfg)return 'STORAGE_CONFIGURATION_INVALID';
 let url;try{url=new URL(cfg.containerUrl);}catch{return 'STORAGE_CONFIGURATION_INVALID';}
 // Precise but credential-free diagnostics: NEVER echo a URL, path, SAS field or account name.
 if(url.protocol!=='https:'||url.username||url.password||url.port||url.search||url.hash||
   !/^[a-z0-9]{3,24}\.blob\.core\.windows\.net$/.test(url.hostname))return 'AZURE_HTTPS_BLOB_ENDPOINT_REQUIRED';
 if(url.pathname==='/'||!url.pathname)return 'AZURE_CONTAINER_PATH_MISSING';
 if(!/^\/[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])$/.test(url.pathname))return 'AZURE_CONTAINER_PATH_INVALID';
 if(url.pathname!==`/${expectedContainer}`)return 'AZURE_CONTAINER_NAME_MISMATCH';
 if(cfg.mode==='sas'){
  const sas=new URLSearchParams(cfg.sas);
  if(sas.has('ss')||sas.has('srt'))return 'ACCOUNT_SAS_NOT_CONTAINER_SCOPED';
  if(sas.get('sr')!=='c'||!sas.get('sig')||['comp','restype','snapshot','versionid'].some(k=>sas.has(k)))return 'CONTAINER_SAS_REQUIRED';
  const permission=sas.get('sp')||'';
  if(!permission.includes('r')||!permission.includes('d')||!/[cw]/.test(permission))return 'SAS_READ_CREATE_DELETE_REQUIRED';
  const expiry=Date.parse(sas.get('se')||'');
  if(!Number.isFinite(expiry)||expiry<=now.getTime())return 'SAS_EXPIRED_OR_INVALID';
  if(sas.has('st')&&(!Number.isFinite(Date.parse(sas.get('st')))||Date.parse(sas.get('st'))>now.getTime()))return 'SAS_NOT_YET_VALID';
 }else if(cfg.mode==='key'){
  if(url.hostname!==cfg.account+'.blob.core.windows.net'||
    !/^[A-Za-z0-9+/]+={0,2}$/.test(cfg.key)||Buffer.from(cfg.key,'base64').length<32)return 'ACCOUNT_KEY_CONFIGURATION_INVALID';
 }else return 'STORAGE_CONFIGURATION_INVALID';
 return null;
}

export async function runBlobVerification({env=process.env,now=new Date()}={}){
 const receipt={schema:'zeref-isolated-blob-verification/v1',status:'BLOCKED',at:now.toISOString(),
  credentials:{AZURE_STORAGE_CONNECTION_STRING:present(env.AZURE_STORAGE_CONNECTION_STRING),
   AZURE_STORAGE_CONTAINER_SAS_URL:present(env.AZURE_STORAGE_CONTAINER_SAS_URL)},
  provider_jobs_submitted:0,model_calls:0,production_objects_touched:0,
  write:{attempted:false,acknowledged:false},readback:{sha256_matches:false},
  cleanup:{attempted:false,confirmed_absent:false}};
 const block=reason=>({...receipt,reason});
 if(env.BEASTBOX_BLOB_PROBE_APPROVAL!==APPROVAL)return block('ISOLATED_TEST_APPROVAL_REQUIRED');
 const run=String(env.GITHUB_RUN_ID||''),attempt=String(env.GITHUB_RUN_ATTEMPT||'');
 if(!/^[1-9][0-9]{0,19}$/.test(run)||!/^[1-9][0-9]{0,4}$/.test(attempt))return block('NUMERIC_RUN_ID_REQUIRED');
 if(!Object.values(receipt.credentials).some(Boolean))return block('STORAGE_CREDENTIAL_MISSING');
 const cfg=storageConfig(env),invalid=validateConfiguration(cfg,now,String(env.AZURE_STORAGE_CONTAINER||'beast-cosmos').trim());
 if(invalid)return block(invalid);
 receipt.credential_mode=cfg.mode;
 const name=`verification/zeref-cloud/${run}-${attempt}/${randomUUID()}.json`;
 receipt.object_name=name;
 const payload=JSON.stringify({schema:'zeref-synthetic-blob-test/v1',run_id:run,attempt,
  nonce:randomUUID(),content:'synthetic verification only; no creature or owner data'})+'\n';
 receipt.payload_sha256=hash(payload);receipt.payload_bytes=Buffer.byteLength(payload);
 try{
  if(await getBlob(cfg,name))return block('PREEXISTING_OBJECT_REFUSED');
 }catch(error){return {...block('READ_PREFLIGHT_REJECTED'),error:safeError(error)};}
 let collision=false;
 try{
  receipt.write.attempted=true;
  try{
   const etag=await putBlob(cfg,name,payload,{ifNoneMatch:'*'});
   receipt.write.acknowledged=true;receipt.write.etag_received=!!etag;
  }catch(error){
   collision=error?.status===409||error?.status===412;
   receipt.status=collision?'BLOCKED':'FAILED';receipt.reason=collision?'CREATE_CONFLICT':'WRITE_NOT_ACKNOWLEDGED';
   receipt.error=safeError(error);
  }
  if(receipt.write.acknowledged){
   const stored=await getBlob(cfg,name);
   receipt.readback.sha256_matches=!!stored&&hash(stored.text)===receipt.payload_sha256;
   receipt.readback.bytes_match=!!stored&&stored.text===payload;
   receipt.status=receipt.readback.sha256_matches&&receipt.readback.bytes_match?'PASSED':'FAILED';
   if(receipt.status==='FAILED')receipt.reason='READBACK_MISMATCH';
  }
 }catch(error){receipt.status='FAILED';receipt.reason='READBACK_REJECTED';receipt.error=safeError(error);}
 finally{
  // A create conflict belongs to someone else. Never delete it. For uncertain
  // acknowledgements, first reconcile the exact synthetic bytes and the etag.
  if(collision)receipt.cleanup.reason='CREATE_CONFLICT_NOT_OWNED';
  else{
   receipt.cleanup.attempted=true;
   try{
    const current=await getBlob(cfg,name);
    if(!current)receipt.cleanup.confirmed_absent=true;
    else if(current.text!==payload||!current.etag){
     receipt.cleanup.reason='OBJECT_CHANGED_REFUSING_DELETE';receipt.status='CLEANUP_FAILED';
    }else{
     await deleteBlob(cfg,name,{ifMatch:current.etag});
     receipt.cleanup.delete_acknowledged=true;
     receipt.cleanup.confirmed_absent=(await getBlob(cfg,name))===null;
     if(!receipt.cleanup.confirmed_absent){receipt.status='CLEANUP_FAILED';receipt.cleanup.reason='OBJECT_STILL_PRESENT';}
    }
   }catch(error){receipt.status='CLEANUP_FAILED';receipt.cleanup.reason='CLEANUP_REJECTED';receipt.cleanup.error=safeError(error);}
  }
 }
 return receipt;
}

if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 let receipt;
 try{receipt=await runBlobVerification();}
 catch{receipt={schema:'zeref-isolated-blob-verification/v1',status:'FAILED',reason:'UNEXPECTED_LOCAL_ERROR',provider_jobs_submitted:0,model_calls:0};}
 const output=process.argv[2]||'build/zeref-cloud-verification/receipt.json';
 mkdirSync(dirname(output),{recursive:true});
 writeFileSync(output,JSON.stringify(receipt,null,2)+'\n',{mode:0o600});
 console.log('ZEREF_CLOUD_BLOB_RECEIPT='+JSON.stringify(receipt));
 process.exitCode=receipt.status==='PASSED'?0:1;
}
