/**
 * One place for every number the typed-text, library and brain-context code
 * shares. Nothing here is a claim about understanding; these are byte/char caps.
 *
 * What the live brain really reads (measured from the pinned checkpoint,
 * `accepted-checkpoint/config.json` of release zeref-006-cycle-44-e60c84cd4673):
 *   max_seq_len = 2048 tokens, byte-level BPE vocab 4096 (about 2.84 characters
 *   per token on English text, measured with the checkpoint's own tokenizer).
 * The free guest path asks for at most 64 new tokens, so the prompt must fit in
 * 2048 - 64 = 1984 tokens. That is about 5,600 characters at the very best, but
 * the model was trained on short windows, so we send at most BRAIN_PROMPT_CHARS.
 */
/** What a person may TYPE in one message (the UI and API accept this much). */
export const MAX_TYPED_CHARS = 8000;
export const BRAIN = Object.freeze({
  contextTokens: 2048,
  outputTokens: 64,
  promptTokenBudget: 1984,
  charsPerToken: 2.84,
  /** Most characters of one framed prompt (identity + library passages + your words) sent per turn. */
  promptChars: 1800,
  /** The old guest limit. Still used as a safe fallback if an older bridge rejects the larger prompt. */
  legacyPromptChars: 700,
});
/** Per-file and library caps (owner uploads only). */
export const MAX_FILE_BYTES = 20 * 1024 * 1024;
export const MAX_DOC_CHARS = 4_000_000;
export const MAX_LIBRARY_CHARS = 16_000_000;
export const MAX_DOCS = 40;
export const CHUNK_TARGET = 700;
export const CHUNK_MAX = 1000;
export const MAX_APPEND_CHUNKS = 300;
export const MAX_APPEND_BYTES = 1_500_000;
export const MAX_TITLE = 120;
export const ALLOWED_KINDS = Object.freeze(['txt', 'md', 'pdf', 'epub', 'paste']);
/** Passages that may join one chat turn. */
export const LIBRARY_PASSAGES = 3;
export const PASSAGE_CHARS = 420;

export function readBudgetNote(read, total) {
  const r = Math.max(0, Math.round(read)), t = Math.max(r, Math.round(total));
  return r >= t ? `Zeref read all ${t.toLocaleString('en-US')} characters of your message this turn.`
    : `Zeref read ${r.toLocaleString('en-US')} of ${t.toLocaleString('en-US')} characters this turn. The rest was left out, picked by keyword match to your question, not by understanding.`;
}
