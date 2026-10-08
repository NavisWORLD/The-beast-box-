/** Browser companion talk beside the native cartridge, using the existing guest brain. */
import { askBeast, guestSafeContext } from './ask-beast.mjs';
import { buildChatContext } from './context.mjs';
import { rememberExchange } from './adventure.mjs';

export function gameBeastKey(session) {
  const beast = session?.beast;
  return beast?.qbeast?.profile?.id && beast.seed
    ? `${beast.qbeast.profile.id}:${beast.seed}` : '';
}

/**
 * A verified, opt-in optical measurement; not object recognition or native
 * player/world state. Never send raw pixels or invent enemies, items, position.
 */
export function gameObservationLine(observation) {
 if (observation?.status !== 'observed' || observation.source !== 'native-emulator-display') return '';
 const numeric = value => Number.isFinite(value) && value >= 0 && value <= 100 ? Math.round(value) : null;
 const brightness=numeric(observation.brightness),contrast=numeric(observation.contrast),change=numeric(observation.frameChange);
 if ([brightness,contrast,change].some(x=>x===null) || !['red','green','blue','mixed'].includes(observation.dominant)) return '';
 return 'Observed native game screen pixels on request: brightness '+brightness+'/100, contrast '+contrast+'/100, dominant colors '+observation.dominant+', frame-change '+change+'/100. This does NOT identify objects, enemies, map location, or actions.';
}


/** Explicit opt-in for sharing only a bounded existing local memory summary.
 * Guest chat remains stateless regardless of the toggle. Native ROM state,
 * QBEAST signing authority and raw game pixels never enter the model prompt.
 */
export function gameChatContext(session,{model='guest',shareMemories=false}={}){
 const source=buildChatContext({session,sensors:null,sensorLog:[]});
 const context=guestSafeContext(source);
 context.location='Lost COSMOS';context.nearby=[];
 if(model==='connected' && shareMemories===true){
  context.memories=(Array.isArray(source.memories)?source.memories:[])
   .filter(x=>typeof x==='string' && x.trim())
   .slice(-4).map(x=>x.replace(/[\u0000-\u001f\u007f]/g,' ').slice(0,140));
 }
 return context;
}

export async function askGameBeast({ session, saying, fetchImpl, signal, model = 'guest', observation = null, shareMemories = false }) {
  if (!gameBeastKey(session)) throw new Error('Choose your Spark Beast first.');
  const text = String(saying || '').trim();
  if (!text || text.length > 280 || /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(text)) {
    throw new Error('Use a message of 1–280 characters.');
  }
  // The cartridge owns its actual location and earned progression. Do not
  // describe a browser trail as the native location, or send stored memories.
  const context = gameChatContext(session,{model,shareMemories});
  const optics = gameObservationLine(observation);
  const question = optics ? text+'\n'+optics : text;
  const result = await askBeast({
    context, saying: question, audience: model === 'connected' ? undefined : 'guest',
    fetchImpl: async (url, init) => {
      const response = await fetchImpl(url, { ...init, signal });
      if (response.ok === false) throw new Error('Guest model unavailable. Please try again later.');
      return response;
    },
  });
  if (signal?.aborted) return { reply: '', label: 'Request canceled.', canceled: true };
  return result;
}

/** Late replies cannot rename, adopt, evolve, or update a different QBEAST. */
export function rememberGameReply(session, expectedKey, saying, result) {
  if (!expectedKey || gameBeastKey(session) !== expectedKey || result?.canceled || !result?.reply?.trim()) {
    return { applied: false };
  }
  return { applied: true, ...rememberExchange(session, saying, result.reply) };
}
