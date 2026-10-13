import {privateBody,privateContext,privateError,privateJson} from '@/lib/cosmos/private-api';
import {verifyPrivateGenesis} from '@/lib/cosmos/private-genesis.mjs';
export const runtime='nodejs';export const dynamic='force-dynamic';
export async function POST(req:Request){try{const body=await privateBody(req);const {store,subject}=await privateContext();const verified=verifyPrivateGenesis(body.qbeastText,body.profile?.name);if(verified.profile.id!==body.profile?.id)throw Object.assign(Error('QBEAST_PROFILE_MISMATCH'),{status:409});const result=await store.create(subject,verified.profile,body.eventId,verified);return privateJson({ok:true,record:result.record,version:result.version});}catch(error){return privateError(error);}}

export async function GET(){try{const {store,subject}=await privateContext();const account=JSON.parse((await store.assertOwner(subject)).text),beasts=[];for(const id of account.beasts||[]){try{const item=await store.read(subject,id);beasts.push({id,name:item.record.profile.name});}catch(error:any){if(![404,410].includes(error?.status))throw error;}}return privateJson({ok:true,beasts});}catch(error){return privateError(error);}}
