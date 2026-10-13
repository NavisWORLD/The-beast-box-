import {createHash} from 'node:crypto';
import {cookies} from 'next/headers';
import {privateBody,privatePrecondition,privateConfig,privateContext,privateError,privateJson,privateStore} from '@/lib/cosmos/private-api';
import {CREDENTIAL_AGE,PRIVATE_COOKIE,issueCredential,verifyCredential} from '@/lib/cosmos/private-owner.mjs';
export const runtime='nodejs';export const dynamic='force-dynamic';
const digest=(value:string)=>createHash('sha256').update(value).digest('hex');
export async function POST(req:Request){try{
 const body=await privateBody(req),config=privateConfig();if(!config)throw Object.assign(Error('UNCONFIGURED'),{status:503});
 const store=privateStore(config.cfg);
 if(body.action==='issue'){
  const {subject}=await privateContext();privatePrecondition(subject,body);const issued=issueCredential(config.secret,{subject,kind:'pair',age:300}),claim=verifyCredential(config.secret,issued.token,{kind:'pair'})!;
  const blob=await store.assertOwner(subject),account=JSON.parse(blob.text);
  await store.io.put(store.ownerPath(subject),JSON.stringify({...account,pair:{nonceHash:digest(claim.nonce),expiry:claim.expiry,consumed:false}}),{ifMatch:blob.etag});
  return privateJson({ok:true,pairCode:issued.token,expiresAt:claim.expiry,singleUse:true});
 }
 if(body.action!=='redeem'||body.consent!==true)throw Object.assign(Error('PAIRING_CONSENT_REQUIRED'),{status:403});
 const claim=verifyCredential(config.secret,body.pairCode,{kind:'pair'});if(!claim)throw Object.assign(Error('INVALID_OR_EXPIRED_PAIR_CODE'),{status:403});
 const path=store.ownerPath(claim.subject),blob=await store.assertOwner(claim.subject);
 const account=JSON.parse(blob.text),record=account.pair;if(!record||record.consumed||record.nonceHash!==digest(claim.nonce)||record.expiry!==claim.expiry)throw Object.assign(Error('PAIR_CODE_CONSUMED'),{status:403});
 await store.io.put(path,JSON.stringify({...account,pair:{...record,consumed:true}}),{ifMatch:blob.etag});const issued=issueCredential(config.secret,{subject:claim.subject});
 (await cookies()).set(PRIVATE_COOKIE,issued.token,{httpOnly:true,secure:process.env.NODE_ENV==='production',sameSite:'strict',path:'/',maxAge:CREDENTIAL_AGE});return privateJson({ok:true,authorized:true});
 }catch(error){return privateError(error);}}
