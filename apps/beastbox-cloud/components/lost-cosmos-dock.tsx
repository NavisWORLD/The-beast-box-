'use client';
import { useEffect, useRef, useState } from 'react';
import type React from 'react';
import { usePathname } from 'next/navigation';
import type { CreatureProfile } from '../lib/creature-profile';
import { modeFor } from '../lib/companion/gba-dock.mjs';
import css from './lost-cosmos-dock.module.css';
import SolSparkPlayer from './sol-spark-player';
import {useBeastSession} from './beast-session';
import {shownName} from '../lib/companion/session.mjs';

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
  const [nativeOwned,setNativeOwned]=useState(pathname==='/sol-game');
  const [expanded, setExpanded] = useState(false);
  const [closed, setClosed] = useState(false);
  const [booted, setBooted] = useState(false);
  // Fresh game visits show the same player and Beast chooser before a cartridge exists.
  // An already booted legacy cartridge retains its owner through navigation.
  useEffect(()=>{if(session?.beast?.qbeast||pathname==='/sol-game'&&!booted)setNativeOwned(true);},[session?.beast?.qbeast,pathname,booted]);
  const [note, setNote] = useState('Lost Cosmos V11.2 Spark is ready.');
  const [narrow, setNarrow] = useState(false);
  const [tucked, setTucked] = useState(false);
  // Desktop: the preview card collapses to the same pill when it would cover a page control.
  const [crowded, setCrowded] = useState(false);
  const cardSize = useRef({ width: 284, height: 230 });
  const pinned = useRef(false);
  const pillWidth = useRef(250);
  const shell = useRef<HTMLElement>(null);
  const volume = useRef(0.28);
  const shown = mode === 'mini' || mode === 'full';
  const wide = mode === 'mini' && expanded && !closed;
  // On phones the mini player is a collapsed pill so it stays clear of page buttons.
  const floating = mode === 'mini' && !closed && !wide;
  const pill = floating && (narrow || crowded);
  const connectedName = spark ? shownName(session.beast) : creature?.name || 'Spark Beast';
  const readyText = `V11.2 Spark is ready for ${connectedName}. The cartridge stays mounted while you move around Beast Box.`;

  useEffect(() => {
    const host = window as WindowEmu;
    host.EJS_emulator?.setVolume?.(shown && !closed ? volume.current : 0);
  }, [shown, closed]);

  // Tell the beast music engine when the cartridge is audible so "Game audio" focus can duck the web music.
  useEffect(() => {
    window.dispatchEvent(new CustomEvent('beastbox:gba-running', { detail: booted && shown && !closed }));
  }, [booted, shown, closed]);

  // A full-screen player must not cover the page's own nav ([data-page-nav]).
  // Start the fixed player just below it, and follow it when the page scrolls.
  const [navClear, setNavClear] = useState<number | null>(null);
  useEffect(() => {
    if (!nativeOwned || mode !== 'full') { setNavClear(null); return; }
    let frame = 0;
    const first = document.querySelector<HTMLElement>('main [data-page-nav]');
    const current = first?.querySelector<HTMLElement>('[aria-current]');
    // The nav is one scrollable row on phones; keep the current page in view.
    if (first && current && first.scrollWidth > first.clientWidth) first.scrollLeft = Math.max(0, current.offsetLeft - (first.clientWidth - current.offsetWidth) / 2);
    const measure = () => {
      frame = 0;
      const nav = document.querySelector<HTMLElement>('main [data-page-nav]');
      if (!nav) { setNavClear(null); return; }
      const bottom = nav.getBoundingClientRect().bottom;
      setNavClear(bottom > 0 ? Math.round(bottom + 8) : null);
    };
    const schedule = () => { if (!frame) frame = window.requestAnimationFrame(measure); };
    schedule();
    const settle = window.setTimeout(schedule, 600);
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      window.clearTimeout(settle);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
    };
  }, [nativeOwned, mode, pathname]);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 760px)');
    const apply = () => setNarrow(media.matches);
    apply();
    media.addEventListener('change', apply);
    return () => media.removeEventListener('change', apply);
  }, []);

  // Avoid-rects: if the player would sit on a visible page control, shrink it. On phones the
  // pill tucks into a small edge tab; on desktop the preview card first collapses to the pill,
  // then tucks too if the pill still covers something. Tapping the tab restores it until the next scroll.
  useEffect(() => {
    if (!floating) { setTucked(false); setCrowded(false); return; }
    let frame = 0;
    const covers = (boxWidth: number, boxHeight: number) => {
      const width = window.innerWidth, height = window.innerHeight, gap = 6, inset = narrow ? 8 : 14;
      const box = { left: width - inset - boxWidth, top: height - inset - boxHeight, right: width - inset, bottom: height - inset };
      const controls = document.querySelectorAll<HTMLElement>('main a, main button, main input, main textarea, main select, [data-critical-control]');
      for (const element of controls) {
        if (element.closest('[data-lost-cosmos-dock], [data-companion-overlay]')) continue;
        const rect = element.getBoundingClientRect();
        if (rect.width < 1 || rect.height < 1 || rect.bottom < 0 || rect.top > height) continue;
        if (rect.left < box.right + gap && rect.right + gap > box.left && rect.top < box.bottom + gap && rect.bottom + gap > box.top) return true;
      }
      return false;
    };
    const measure = () => {
      frame = 0;
      if (pinned.current) return;
      const node = shell.current;
      if (node && !node.classList.contains(css.tucked)) {
        const rect = node.getBoundingClientRect();
        if (node.classList.contains(css.pill)) pillWidth.current = rect.width || pillWidth.current;
        else if (rect.width && rect.height) cardSize.current = { width: rect.width, height: rect.height };
      }
      const cardHit = !narrow && covers(cardSize.current.width, cardSize.current.height);
      setCrowded(cardHit);
      setTucked((narrow || cardHit) && covers(pillWidth.current, 40));
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
  }, [floating, narrow, pathname]);

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
  if(nativeOwned)return <aside className={css.sparkDock} style={navClear!==null?({'--nav-clear':`${navClear}px`} as React.CSSProperties):undefined} aria-label={`Lost Cosmos cartridge connected to ${connectedName}`} data-lost-cosmos-dock="true" data-cosmos-mode={mode} data-dock-state="native" data-rom-source="/api/gba-rom" data-creature-id={session?.beast?.qbeast?.profile.id||''}>
    <SolSparkPlayer stage={mode==='full'} />
  </aside>;
  return <aside ref={shell} className={className} data-dock-pill={pill ? (tucked ? 'tucked' : 'pill') : undefined} data-cosmos-mode={mode} data-rom-source="/api/gba-rom" aria-hidden={shown ? undefined : true} aria-label={`Lost Cosmos cartridge connected to ${connectedName}`}
    data-lost-cosmos-dock="true" data-dock-state={state} data-creature-id={creature?.id || 'fallback'}>
    {mode === 'mini' && closed ? <button type="button" className={css.launcher} onClick={() => setClosed(false)}
      aria-label="Open Lost Cosmos player"><span>🎮</span><strong>LOST COSMOS</strong><small>Open</small></button> : null}
    <div className={css.bar}>
      {pill && tucked ? <button type="button" className={css.tab} onClick={() => { pinned.current = true; setTucked(false); setCrowded(false); }}
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
      <div id="lost-cosmos-screen" className={css.game} />
      {!spark && !booted && shown ? <div className={css.poster}>
        <p>{readyText}</p>
        <button type="button" onClick={play}>Play V11.2 Spark</button>
      </div> : null}
    </div>
    {shown && booted && mode !== 'full' ? <p className={css.status}>{note}</p> : null}
  </aside>;
}
