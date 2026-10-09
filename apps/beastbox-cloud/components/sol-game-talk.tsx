'use client';
import { useEffect, useId, useRef, useState } from 'react';
import { useBeastSession } from './beast-session';
import { care } from '../lib/companion/adventure.mjs';
import { shownName } from '../lib/companion/session.mjs';
import { useBeastAudio } from './use-beast-audio';
import { askGameBeast, gameBeastKey, rememberGameReply } from '../lib/companion/sol-game-talk.mjs';

export default function SolGameTalk({ active = true, observeGame }: { active?: boolean; observeGame?: () => Promise<any | null> }) {
  const { ready, session, change } = useBeastSession();
  const [open, setOpen] = useState(false), [text, setText] = useState('');
  const [busy, setBusy] = useState(false), [status, setStatus] = useState('');
  const [model, setModel] = useState<'guest'|'connected'>('guest');
  const [includeGameView, setIncludeGameView] = useState(false);
  const [viewStatus, setViewStatus] = useState('');
  const [lastReply, setLastReply] = useState('');
  const { audio, state: audioState } = useBeastAudio();
  const request = useRef<{ sequence: number; controller?: AbortController }>({ sequence: 0 });
  const key = gameBeastKey(session), currentKey = useRef(key);
  currentKey.current = key;
  const panelId = useId(), name = shownName(session?.beast);

  function cancel() {
    request.current.sequence++;
    request.current.controller?.abort();
    request.current.controller = undefined;
    setBusy(false);
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) window.speechSynthesis.cancel();
  }
  // A different QBEAST must not inherit the previous creature's draft or reply.
  // Minimizing or temporarily hiding this player is NOT an identity change.
  useEffect(() => {
    cancel(); setOpen(false); setStatus(''); setText(''); setLastReply(''); setViewStatus('');
    return () => { request.current.sequence++; request.current.controller?.abort(); };
  }, [key]);
  // Cancel in-flight calls while the game surface is inactive, but keep the
  // draft, completed reply, model choice and open state for instant restore.
  useEffect(() => {
    if (!active) cancel();
  }, [active]);

  async function send(event: React.FormEvent) {
    event.preventDefault();
    const saying = text.trim();
    if (!saying || busy || !key || !active) return;
    const controller = new AbortController(), sequence = ++request.current.sequence, expectedKey = key;
    request.current.controller = controller;
    setBusy(true); setStatus(model==='connected'?'Asking the connected Brain Bay…':'Asking the RAWRPHØS guest brain…');
    const timeout = setTimeout(() => controller.abort(), 60000);
    try {
      const observation=includeGameView&&observeGame?await observeGame():null;
      if(sequence!==request.current.sequence||currentKey.current!==expectedKey)return;
      if(includeGameView)setViewStatus(observation?.status==='observed'
        ? 'Native pixels sampled (brightness/contrast/color only). No enemy or map detection.'
        : 'Live framebuffer unavailable. No vision data was supplied.');
      const result = await askGameBeast({ session, saying, model, observation, fetchImpl: fetch, signal: controller.signal });
      if (sequence !== request.current.sequence || currentKey.current !== expectedKey) return;
      if (controller.signal.aborted) { setStatus('The model request timed out. Your game and Beast are still here.'); return; }
      if (!result.reply) { setStatus(String(result.label).slice(0, 240)); return; }
      const saved=await change(draft => { rememberGameReply(draft, expectedKey, saying, result); });
      if(!saved.ok){setStatus(saved.reason||'The reply arrived but could not be saved. Your cartridge is still running.');setLastReply(result.reply);return;}
      setText(''); setLastReply(result.reply); setStatus((result.label||'Model reply')+' · reply saved with this Beast on this device. Tap HEAR REPLY for iPhone voice.');
    } catch (error) {
      if (sequence === request.current.sequence) setStatus(error instanceof Error ? error.message : 'The guest model could not answer.');
    } finally {
      clearTimeout(timeout);
      if (sequence === request.current.sequence) { setBusy(false); request.current.controller = undefined; }
    }
  }
  async function inspectGame(){
    if(!observeGame)return;
    setViewStatus('Looking at the actual native display…');
    const observation=await observeGame();
    setViewStatus(observation?.status==='observed'
      ? 'Observed game pixels: brightness '+observation.brightness+'/100, contrast '+observation.contrast+'/100, '+observation.dominant+' color, frame change '+observation.frameChange+'/100. No object recognition.'
      : 'No readable native frame available. The Beast will not invent what it sees.');
  }
  function speakReply(){
    if(!lastReply || typeof window==='undefined')return;
    if(audioState.sparkMuted){setStatus('Unmute Beast Box sound before using the device voice.');return;}
    if(!('speechSynthesis' in window)||!('SpeechSynthesisUtterance' in window)){setStatus('Speech playback is not supported by this browser. The text reply is still available.');return;}
    // Both audio unlock and Web Speech scheduling must begin in this *trusted tap*
    // on Safari. A queued utterance is not proof that the speaker played.
    audio.unlock();
    const speech=window.speechSynthesis;
    speech.cancel();
    try{speech.resume();}catch{/* Some browsers do not expose resume. */}
    const line=new SpeechSynthesisUtterance(lastReply.slice(0,520));
    line.lang='en-US';line.pitch=1.18;line.rate=1.04;line.volume=Math.max(0,Math.min(0.8,audioState.volume));
    line.onstart=()=>setStatus('Device voice started · the connected model supplied the text.');
    line.onend=()=>setStatus('Device voice finished. The game and your Beast are still running.');
    line.onerror=()=>setStatus('Safari speech could not play. Text is saved; check iPhone Silent Mode, media volume and Bluetooth output.');
    try{speech.speak(line);setStatus('Starting device voice… If this stays silent, check iPhone sound output.');}
    catch{setStatus('Device voice could not start. The model reply remains available as text.');}
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
      <p style={{ fontSize: 12, color: '#b0c4df', lineHeight: 1.5 }}>Same QBEAST. Use RAWRPHØS guest, or your authenticated connected Brain Bay if available. Native cartridge CHAT remains local authored dialogue; this panel is real model-backed text.</p>
      <label style={{display:'grid',gap:4,fontSize:12,marginBottom:8}}>Talking brain
       <select value={model} onChange={event=>setModel(event.target.value==='connected'?'connected':'guest')} style={{minHeight:44,fontSize:16,padding:8,background:'#15253d',color:'#eef7ff'}}>
        <option value="guest">RAWRPHØS · guest</option>
        <option value="connected">My connected Brain Bay · authenticated</option>
       </select>
      </label>
      <label style={{display:'flex',alignItems:'center',gap:8,fontSize:12,lineHeight:1.5,marginBottom:8}}>
       <input type="checkbox" checked={includeGameView} onChange={event=>setIncludeGameView(event.target.checked)}/>
       Include fresh native pixel signals with each model message (not screenshots or object recognition)
      </label>
      <button type="button" style={button} disabled={!observeGame||busy} onClick={()=>void inspectGame()}>👁️ LOOK AT GAME</button>
      <p role="status" style={{fontSize:11,color:'#aaddeb'}}>{viewStatus}</p>
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
          {lastReply ? <button type="button" style={button} onClick={speakReply} disabled={audioState.sparkMuted}>🔊 HEAR REPLY</button> : null}
        </div>
      </form>
      <p role="status" style={{ fontSize: 12, color: '#9cdfea' }}>{status}</p>
    </section> : null}
  </div>;
}
