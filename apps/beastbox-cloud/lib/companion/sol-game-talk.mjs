/** Browser companion talk beside the native cartridge, using the existing guest brain. */
import { askBeast, guestSafeContext } from './ask-beast.mjs';
import { buildChatContext } from './context.mjs';
import { rememberExchange } from './adventure.mjs';

export function gameBeastKey(session) {
  const beast = session?.beast;
  return beast?.qbeast?.profile?.id && beast.seed
    ? `${beast.qbeast.profile.id}:${beast.seed}` : '';
}

export async function askGameBeast({ session, saying, fetchImpl, signal }) {
  if (!gameBeastKey(session)) throw new Error('Choose your Spark Beast first.');
  const text = String(saying || '').trim();
  if (!text || text.length > 280 || /[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(text)) {
    throw new Error('Use a message of 1–280 characters.');
  }
  // The cartridge owns its actual location and earned progression. Do not
  // describe a browser trail as the native location, or send stored memories.
  const context = guestSafeContext(buildChatContext({ session, sensors: null, sensorLog: [] }));
  context.location = 'Lost COSMOS';
  context.nearby = [];
  const result = await askBeast({
    context, saying: text, audience: 'guest',
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
