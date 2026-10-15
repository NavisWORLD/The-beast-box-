import type {TalkState} from './beast-talk-panel';

/**
 * Kid-friendly scene captions for the Talk page habitat. The animation shows
 * what the page is doing (waiting, thinking, replied) — never model emotions
 * or awareness. Keys must stay in sync with TalkState.
 */
export const SCENE_CAPTION:Record<TalkState,string>={
 idle:'Waiting for your message',
 thinking:'Asking your Beast’s teacher…',
 listening:'Listening…',
 speaking:'Reading the reply aloud',
 replied:'Reply received ✓',
 offline:'Teacher offline · no made-up reply',
};
