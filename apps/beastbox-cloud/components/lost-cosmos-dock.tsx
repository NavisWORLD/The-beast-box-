'use client';
import { useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import type { CreatureProfile } from '../lib/creature-profile';
import { modeFor } from '../lib/companion/gba-dock.mjs';
import css from './lost-cosmos-dock.module.css';
import SolSparkPlayer from './sol-spark-player';
import {useBeastSession} from './beast-session';

type WindowEmu = Window & {
  EJS_player?: string;
  EJS_core?: string;
  EJS_gameUrl?: string;
  EJS_pathtodata?: string;
  EJS_startOnLoaded?: boolean;
  EJS_color?: string;
  EJS_volume?: number;
  EJS_emulator?: { setVolume?: (value: number) => void; gameManager?: { FS?: { writeFile: (path: string, data: Uint8Array) => void }; simulateInput?: (player: number, index: number, value: number) => void } };
};

export default function LostCosmosDock({ creature }: { creature?: CreatureProfile | null }) {
  const pathname = usePathname() || '/';
  const {session}=useBeastSession();
  const spark=!!creature&&!!session?.beast?.qbeast&&session.beast.qbeast.profile.id===creature.id;
  const mode = modeFor(pathname);
  const [expanded, setExpanded] = useState(false);
  const [closed, setClosed] = useState(false);
  const [booted, setBooted] = useState(false);
  const [note, setNote] = useState('Lost Cosmos V11.2 Spark is ready.');
  const [narrow, setNarrow] = useState(false);
  const [tucked, setTucked] = useState(false);
  const pinned = useRef(false);
  const pillWidth = useRef(250);
  const shell = useRef<HTMLElement>(null);
  const volume = useRef(0.28);
  const shown = mode === 'mini' || mode === 'full';
  const wide = mode === 'mini' && expanded && !closed;
  // On phones the mini player is a collapsed pill so it stays clear of page buttons.
  const pill = mode === 'mini' && !closed && !wide && narrow;
  const connectedName = creature?.name || 'Spark Beast';
  const readyText = `V11.2 Spark is ready for ${connectedName}. The cartridge stays mounted while you move around Beast Box.`;

  useEffect(() => {
    const host = window as WindowEmu;
    host.EJS_emulator?.setVolume?.(shown && !closed ? volume.current : 0);
  }, [shown, closed]);

  // Tell the beast music engine when the cartridge is audible so "Game audio" focus can duck the web music.
  useEffect(() => {
    window.dispatchEvent(new CustomEvent('beastbox:gba-running', { detail: booted && shown && !closed }));
  }, [booted, shown, closed]);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 760px)');
    const apply = () => setNarrow(media.matches);
    apply();
    media.addEventListener('change', apply);
    return () => media.removeEventListener('change', apply);
  }, []);

  // Avoid-rects: if the pill would sit on a visible page control, tuck it into a
  // small edge tab. Tapping the tab brings the pill back until the next scroll.
  useEffect(() => {
    if (!pill) { setTucked(false); return; }
    let frame = 0;
    const measure = () => {
      frame = 0;
      if (pinned.current) return;
      const node = shell.current;
      if (node && !node.classList.contains(css.tucked)) pillWidth.current = node.getBoundingClientRect().width || pillWidth.current;
      const width = window.innerWidth, height = window.innerHeight;
      const box = { left: width - 8 - pillWidth.current, top: height - 8 - 40, right: width - 8, bottom: height - 8 };
      const gap = 6;
      const controls = document.querySelectorAll<HTMLElement>('main a, main button, main input, main textarea, main select, [data-critical-control]');
      let hit = false;
      for (const element of controls) {
        if (element.closest('[data-lost-cosmos-dock], [data-companion-overlay]')) continue;
        const rect = element.getBoundingClientRect();
        if (rect.width < 1 || rect.height < 1 || rect.bottom < 0 || rect.top > height) continue;
        if (rect.left < box.right + gap && rect.right + gap > box.left && rect.top < box.bottom + gap && rect.bottom + gap > box.top) { hit = true; break; }
      }
      setTucked(hit);
    };
    const schedule = () => { if (!frame) frame = window.requestAnimationFrame(measure); };
    const onScroll = () => { pinned.current = false; schedule(); };
    schedule();
    const settle = window.setTimeout(schedule, 900);
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', schedule);
    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      window.clearTimeout(settle);
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', schedule);
    };
  }, [pill, pathname]);

  useEffect(() => {
    function onVolume(event: Event) {
      const value = Number((event as CustomEvent).detail);
      if (!Number.isFinite(value)) return;
      volume.current = Math.max(0, Math.min(1, value));
      const host = window as WindowEmu;
      if (modeFor(window.location.pathname) !== 'parked') host.EJS_emulator?.setVolume?.(volume.current);
    }
    window.addEventListener('beastbox:gba-volume', onVolume);
    return () => window.removeEventListener('beastbox:gba-volume', onVolume);
  }, []);

  useEffect(() => {
    function onSave() {
      const host = window as WindowEmu;
      const fs = host.EJS_emulator?.gameManager?.FS;
      if (!fs) {
        setNote('SRAM is ready. Start the cartridge, then use its save menu if live injection is unavailable.');
        return;
      }
      setNote('Cartridge core is running. Load the downloaded .sav from the emulator menu to place this Beast in the cage.');
    }
    window.addEventListener('beastbox:lcx1-ready', onSave);
    return () => window.removeEventListener('beastbox:lcx1-ready', onSave);
  }, []);

  function play() {
    if (booted) return;
    const host = window as WindowEmu;
    host.EJS_player = '#lost-cosmos-screen';
    host.EJS_core = 'gba';
    host.EJS_gameUrl = '/api/gba-rom';
    host.EJS_pathtodata = 'https://cdn.emulatorjs.org/stable/data/';
    host.EJS_startOnLoaded = true;
    host.EJS_color = '#68e5ee';
    host.EJS_volume = shown && !closed ? volume.current : 0;
    const script = document.createElement('script');
    script.src = 'https://cdn.emulatorjs.org/stable/data/loader.js';
    script.async = true;
    script.onerror = () => setNote('The emulator script did not load. The V11.2 ROM route is still available at /api/gba-rom.');
    document.body.appendChild(script);
    setBooted(true);
    setNote(`Playing V11.2 Spark with ${connectedName}. The emulator remains mounted when this dock is minimized or closed.`);
  }

  const state = mode === 'full' ? 'full' : closed ? 'closed' : wide ? 'expanded' : 'mini';
  const className = [css.dock, mode === 'full' ? css.full : '', wide ? css.wide : '', mode === 'mini' && closed ? css.closed : '', mode === 'parked' ? css.parked : '', pill ? css.pill : '', pill && tucked ? css.tucked : ''].filter(Boolean).join(' ');
  return <aside ref={shell} className={className} data-dock-pill={pill ? (tucked ? 'tucked' : 'pill') : undefined} data-cosmos-mode={mode} data-rom-source="/api/gba-rom" aria-hidden={shown ? undefined : true} aria-label={`Lost Cosmos cartridge connected to ${connectedName}`}
    data-lost-cosmos-dock="true" data-dock-state={state} data-creature-id={creature?.id || 'fallback'}>
    {mode === 'mini' && closed ? <button type="button" className={css.launcher} onClick={() => setClosed(false)}
      aria-label="Open Lost Cosmos player"><span>🎮</span><strong>LOST COSMOS</strong><small>Open</small></button> : null}
    <div className={css.bar}>
      {pill && tucked ? <button type="button" className={css.tab} onClick={() => { pinned.current = true; setTucked(false); }}
        aria-label="Show Lost Cosmos player">🎮</button> : null}
      <strong>LOST COSMOS</strong>
      <span title={connectedName}>V11.2 Spark · {connectedName}</span>
      <div className={css.actions}>
        <a href="/spark/index.html" className={css.generate}>Generate Beast</a>
        {mode === 'mini' ? <button type="button" onClick={() => setExpanded((value) => !value)}
          aria-label={wide ? 'Minimize Lost Cosmos player' : 'Expand Lost Cosmos player'}>{wide ? 'Mini' : 'Expand'}</button> : null}
        {mode === 'mini' ? <button type="button" className={css.close} onClick={() => { setExpanded(false); setClosed(true); }}
          aria-label="Close Lost Cosmos player">×</button> : null}
      </div>
    </div>
    <div className={css.screen}>
      {spark?<SolSparkPlayer compact active={shown&&!closed}/>:<div id="lost-cosmos-screen" className={css.game} /> }
      {!spark && !booted && shown ? <div className={css.poster}>
        <p>{readyText}</p>
        <button type="button" onClick={play}>Play V11.2 Spark</button>
      </div> : null}
    </div>
    {shown && booted && mode !== 'full' ? <p className={css.status}>{note}</p> : null}
  </aside>;
}
