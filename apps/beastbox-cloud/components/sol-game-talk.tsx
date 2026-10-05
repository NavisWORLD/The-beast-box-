'use client';
import { useEffect, useId, useRef, useState } from 'react';
import { useBeastSession } from './beast-session';
import { care } from '../lib/companion/adventure.mjs';
import { shownName } from '../lib/companion/session.mjs';
import { askGameBeast, gameBeastKey, rememberGameReply } from '../lib/companion/sol-game-talk.mjs';

export default function SolGameTalk({ active = true }: { active?: boolean }) {
  const { ready, session, change } = useBeastSession();
  const [open, setOpen] = useState(false), [text, setText] = useState('');
  const [busy, setBusy] = useState(false), [status, setStatus] = useState('');
  const request = useRef<{ sequence: number; controller?: AbortController }>({ sequence: 0 });
  const key = gameBeastKey(session), currentKey = useRef(key);
  currentKey.current = key;
  const panelId = useId(), name = shownName(session?.beast);

  function cancel() {
    request.current.sequence++;
    request.current.controller?.abort();
    request.current.controller = undefined;
    setBusy(false);
  }
  useEffect(() => {
    cancel(); setOpen(false); setStatus(''); setText('');
    return () => { request.current.sequence++; request.current.controller?.abort(); };
  }, [key, active]);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const saying = text.trim();
    if (!saying || busy || !key || !active) return;
    const controller = new AbortController(), sequence = ++request.current.sequence, expectedKey = key;
    request.current.controller = controller;
    setBusy(true); setStatus('RAWRPHØS is answering…');
    const timeout = setTimeout(() => controller.abort(), 60000);
    try {
      const result = await askGameBeast({ session, saying, fetchImpl: fetch, signal: controller.signal });
      if (sequence !== request.current.sequence || currentKey.current !== expectedKey) return;
      if (controller.signal.aborted) { setStatus('The model request timed out. Your game and Beast are still here.'); return; }
      if (!result.reply) { setStatus(String(result.label).slice(0, 240)); return; }
      change(draft => { rememberGameReply(draft, expectedKey, saying, result); });
      setText(''); setStatus('RAWRPHØS guest model · reply saved with this Beast on your device.');
    } catch (error) {
      if (sequence === request.current.sequence) setStatus(error instanceof Error ? error.message : 'The guest model could not answer.');
    } finally {
      clearTimeout(timeout);
      if (sequence === request.current.sequence) { setBusy(false); request.current.controller = undefined; }
    }
  }
  function careFor(kind: string) {
    change(draft => { if (gameBeastKey(draft) === key) care(draft, kind); });
  }

  if (!ready || !key || !active) return null;
  const button = { minHeight: 44, padding: '9px 12px', border: '1px solid #53718e', borderRadius: 8, background: '#14304a', color: '#b8efff', cursor: 'pointer' };
  return <div data-spark-game-talk data-creature-id={session.beast.qbeast.profile.id} style={{ padding: 10, minWidth: 0, overflowWrap: 'anywhere' }}>
    <button type="button" style={button} aria-expanded={open} aria-controls={panelId} onClick={() => { if (open) cancel(); setOpen(!open); }}>
      {open ? 'CLOSE TALK' : `TALK TO ${name.toUpperCase()} 💬`}
    </button>
    {open ? <section id={panelId} aria-label={`Talk to ${name}`} style={{ marginTop: 10, padding: 12, background: '#0c192d', border: '1px solid #355570', borderRadius: 10 }}>
      <strong>{name} · same Beast, same Cage</strong>
      <p style={{ fontSize: 12, color: '#b0c4df', lineHeight: 1.5 }}>RAWRPHØS guest model. Send your message and this Beast’s game stats. Chat stays on this device. Native CHAT uses local game dialogue.</p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <button type="button" style={button} onClick={() => careFor('pet')}>PET</button>
        <button type="button" style={button} onClick={() => careFor('rest')}>REST</button>
        <a href="/beast-cage" style={{ color: '#b8efff', padding: 8 }}>BEAST CAGE · CARE</a>
      </div>
      <p data-game-care style={{ fontSize: 12 }}>Care XP {session.beast.xp} · Bond {session.beast.bond} · Energy {session.beast.energy}. Native evolution is earned in the cartridge.</p>
      <div aria-label="This Beast’s recent chat" aria-live="polite" style={{ maxHeight: 180, overflowY: 'auto', fontSize: 13, lineHeight: 1.5 }}>
        {(session.chat || []).slice(-6).map((turn: { role: string; text: string }, i: number) => <p key={i} style={{ margin: '8px 0', whiteSpace: 'pre-wrap' }}><strong>{turn.role === 'you' ? 'You' : name}: </strong>{turn.text}</p>)}
      </div>
      <form onSubmit={send} style={{ marginTop: 12, display: 'grid', gap: 8, minWidth: 0 }}>
        <label htmlFor={panelId + '-message'}>Say something to {name}</label>
        <textarea id={panelId + '-message'} aria-label={`Message to ${name}`} value={text} onChange={event => setText(event.target.value)} maxLength={280} rows={2} disabled={busy} style={{ boxSizing: 'border-box', width: '100%', minWidth: 0, padding: 10, fontSize: 16, borderRadius: 8, background: '#081224', color: '#eef5ff', border: '1px solid #53718e', resize: 'vertical' }} />
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button type="submit" style={button} disabled={busy || !text.trim()}>{busy ? 'ANSWERING…' : 'SEND TO MODEL'}</button>
          {busy ? <button type="button" style={button} onClick={() => { cancel(); setStatus('Request canceled.'); }}>CANCEL</button> : null}
        </div>
      </form>
      <p role="status" style={{ fontSize: 12, color: '#9cdfea' }}>{status}</p>
    </section> : null}
  </div>;
}
