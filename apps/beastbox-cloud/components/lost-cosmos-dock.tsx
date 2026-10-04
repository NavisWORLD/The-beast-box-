'use client';
import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import type { CreatureProfile } from '../lib/creature-profile';
import css from './lost-cosmos-dock.module.css';

const MINI = new Set(['/beast-cage', '/beast-cage/talk', '/beast-cage/guest', '/beast-cage/play']);
type WindowEmu = Window & {
  EJS_player?: string;
  EJS_core?: string;
  EJS_gameUrl?: string;
  EJS_pathtodata?: string;
  EJS_startOnLoaded?: boolean;
  EJS_color?: string;
  EJS_volume?: number;
  EJS_emulator?: { setVolume?: (value: number) => void; gameManager?: { FS?: { writeFile: (path: string, data: Uint8Array) => void } } };
};

function modeFor(path: string) {
  if (path.startsWith('/workspace')) return 'parked';
  if (MINI.has(path)) return 'mini';
  return 'parked';
}

export default function LostCosmosDock({ creature }: { creature?: CreatureProfile | null }) {
  const pathname = usePathname() || '/';
  const mode = modeFor(pathname);
  const [expanded, setExpanded] = useState(false);
  const [closed, setClosed] = useState(false);
  const [booted, setBooted] = useState(false);
  const [note, setNote] = useState('Lost Cosmos V11.2 Spark is ready.');
  const shown = mode === 'mini';
  const wide = shown && expanded && !closed;
  const connectedName = creature?.name || 'Spark Beast';
  const readyText = `V11.2 Spark is ready for ${connectedName}. The cartridge stays mounted while you move around Beast Box.`;

  useEffect(() => {
    const host = window as WindowEmu;
    host.EJS_emulator?.setVolume?.(shown && !closed ? 0.28 : 0);
  }, [shown, closed]);

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
    host.EJS_volume = shown && !closed ? 0.28 : 0;
    const script = document.createElement('script');
    script.src = 'https://cdn.emulatorjs.org/stable/data/loader.js';
    script.async = true;
    script.onerror = () => setNote('The emulator script did not load. The V11.2 ROM route is still available at /api/gba-rom.');
    document.body.appendChild(script);
    setBooted(true);
    setNote(`Playing V11.2 Spark with ${connectedName}. The emulator remains mounted when this dock is minimized or closed.`);
  }

  const state = closed ? 'closed' : wide ? 'expanded' : 'mini';
  const className = [css.dock, wide ? css.wide : '', closed ? css.closed : '', shown ? '' : css.parked].filter(Boolean).join(' ');
  return <aside className={className} aria-hidden={shown ? undefined : true} aria-label={`Lost Cosmos cartridge connected to ${connectedName}`}
    data-lost-cosmos-dock="true" data-dock-state={state} data-creature-id={creature?.id || 'fallback'}>
    {shown && closed ? <button type="button" className={css.launcher} onClick={() => setClosed(false)}
      aria-label="Open Lost Cosmos player"><span>🎮</span><strong>LOST COSMOS</strong><small>Open</small></button> : null}
    <div className={css.bar}>
      <strong>LOST COSMOS</strong>
      <span title={connectedName}>{wide ? `Connected · ${connectedName}` : connectedName}</span>
      <div className={css.actions}>
        <a href="/spark/index.html" className={css.generate}>Generate Beast</a>
        {shown ? <button type="button" onClick={() => setExpanded((value) => !value)}
          aria-label={wide ? 'Minimize Lost Cosmos player' : 'Expand Lost Cosmos player'}>{wide ? 'Mini' : 'Expand'}</button> : null}
        {shown ? <button type="button" className={css.close} onClick={() => { setExpanded(false); setClosed(true); }}
          aria-label="Close Lost Cosmos player">×</button> : null}
      </div>
    </div>
    <div className={css.screen}>
      <div id="lost-cosmos-screen" />
      {!booted && shown ? <div className={css.poster}>
        <p>{readyText}</p>
        <button type="button" onClick={play}>Play V11.2 Spark</button>
      </div> : null}
    </div>
    {shown && booted ? <p className={css.status}>{note}</p> : null}
  </aside>;
}
