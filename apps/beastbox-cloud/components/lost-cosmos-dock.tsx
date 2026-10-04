'use client';
import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
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

export default function LostCosmosDock() {
  const pathname = usePathname() || '/';
  const mode = modeFor(pathname);
  const [expanded, setExpanded] = useState(false);
  const [booted, setBooted] = useState(false);
  const [note, setNote] = useState('Lost Cosmos V11.2 Spark is ready. The cartridge stays loaded when you change pages.');
  const shown = mode === 'mini';
  const wide = shown && expanded;

  useEffect(() => {
    const host = window as WindowEmu;
    host.EJS_emulator?.setVolume?.(shown ? 0.35 : 0);
  }, [shown]);

  useEffect(() => {
    function onSave() {
      const host = window as WindowEmu;
      const fs = host.EJS_emulator?.gameManager?.FS;
      if (!fs) {
        setNote('The SRAM download is ready. Start the cartridge, then use its save menu if live injection is unavailable.');
        return;
      }
      setNote('Cartridge core is running. Load the downloaded .sav from the emulator save menu to place this beast in the cage.');
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
    host.EJS_volume = shown ? 0.35 : 0;
    const script = document.createElement('script');
    script.src = 'https://cdn.emulatorjs.org/stable/data/loader.js';
    script.async = true;
    script.onerror = () => setNote('The emulator script did not load. The V11.2 ROM route is still available at /api/gba-rom.');
    document.body.appendChild(script);
    setBooted(true);
    setNote('Playing Lost Cosmos V11.2 Spark. This screen stays mounted, including while it is parked off the owner workstation.');
  }

  const className = [css.dock, wide ? css.wide : '', shown ? '' : css.parked].filter(Boolean).join(' ');
  return <aside className={className} aria-hidden={shown ? undefined : true} aria-label="Lost Cosmos cartridge">
    <div className={css.bar}>
      <strong>LOST COSMOS</strong>
      <span>{wide ? 'Play area' : 'Mini player'}</span>
      {shown ? <button type="button" onClick={() => setExpanded((value) => !value)}>{wide ? 'Mini' : 'Expand'}</button> : null}
    </div>
    <div className={css.screen}>
      <div id="lost-cosmos-screen" />
      {!booted && shown ? <div className={css.poster}>
        <p>{note}</p>
        <button type="button" onClick={play}>Play V11.2 Spark</button>
      </div> : null}
    </div>
    {shown && booted ? <p className={css.poster} style={{ position: 'relative', padding: 10 }}>{note}</p> : null}
  </aside>;
}
