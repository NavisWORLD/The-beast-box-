/**
 * Bounded research controller. RAWRPHØS proposes at most one primitive button.
 * Only an explicitly consenting host can execute it. No tool/model authority,
 * object recognition, native save mutation, or fabricated fallback action.
 */
import {askGameBeast,gameBeastKey,gameObservationLine} from './sol-game-talk.mjs';

const ACTIONS=Object.freeze({UP:'up',DOWN:'down',LEFT:'left',RIGHT:'right',A:'a',B:'b',WAIT:null});
export const MAX_GUIDED_STEPS=3;
export const GUIDED_BUTTON_MS=125;

export function parseModelGameAction(reply) {
 if(typeof reply!=='string'||reply.length>96)return {ok:false,reason:'Model did not produce a bounded action line.'};
 // Reject preambles, multimodal payloads, multiple commands, and instructions.
 const match=/^ACTION: (UP|DOWN|LEFT|RIGHT|A|B|WAIT)$/.exec(reply.trim());
 if(!match)return {ok:false,reason:'The model response was not a valid single ACTION instruction.'};
 return {ok:true,command:match[1],button:ACTIONS[match[1]]};
}

export async function proposeGuidedGameAction({
 session,observation,fetchImpl,signal,model='guest',
}) {
 const identity=gameBeastKey(session);
 if(!identity)return {ok:false,reason:'A canonical QBEAST must be selected first.'};
 const optical=gameObservationLine(observation);
 if(!optical)return {ok:false,reason:'No freshly measured native-screen pixels; no action was submitted.'};
 if(signal?.aborted)return {ok:false,reason:'Canceled before model request.'};
 const question='Experimental game control: propose exactly ONE safe next key. Respond with only ACTION: UP, DOWN, LEFT, RIGHT, A, B, or WAIT. Use the supplied numerical native display observation. Do not pretend you recognize objects or map positions.';
 const result=await askGameBeast({
  session,saying:question,observation,model,shareMemories:false,fetchImpl,signal
 });
 if(signal?.aborted)return {ok:false,reason:'Canceled while the model was responding.'};
 if(!result.reply)return {ok:false,reason:result.label||'Model unavailable; no substitute action.'};
 const parsed=parseModelGameAction(result.reply);
 return {...parsed,identity,actual_model_output:result.reply,label:result.label,
  source:'native-pixel-signals-and-model-text',screen:optical};
}
