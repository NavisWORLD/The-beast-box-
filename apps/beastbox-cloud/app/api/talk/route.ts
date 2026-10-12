import {bridgeConfigured,isOwner,safeJson} from '@/lib/security';
export const runtime='nodejs';
export const dynamic='force-dynamic';

/**
 * Public "which brains exist" check for Talk to Beast. Reports configuration
 * only (booleans, never URLs, tokens or provider output) and spends no model
 * quota. A configured host still has to prove itself with a real reply.
 */
export async function GET(){
 const owner=await isOwner();
 const secret=process.env.BEASTBOX_CLOUD_AUTH_SECRET;
 const guestHost=bridgeConfigured()&&!!secret&&secret.length>=32;
 return safeJson(200,{
  schema:'beastbox-talk-routes-v1',
  routes:{
   'connected-brain-bay':{configured:owner&&bridgeConfigured(),cost:'configured owner provider',model:'your paired Brain Bay provider'},
   'guest-rawrphos':{configured:guestHost,cost:'free',quota:'per-visitor daily limit',model:'rawrphos-native 14K'},
   'local-ollama':{configured:'browser',cost:'free on your own computer',model:'your installed Ollama model'},
   'hf-byok':{configured:'browser',cost:'billed to your own Hugging Face key',model:'your chosen Hugging Face model'}
  },
  default:guestHost?'guest-rawrphos':'local-ollama',
  owner
 });
}
