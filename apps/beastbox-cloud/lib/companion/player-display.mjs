/** Layout owns no cartridge state. Fullscreen reality comes from the browser. */
export function createPlayerDisplay({ document: doc, shell, changed, release }) {
  let mode = 'normal', intent = 'normal', generation = 0, disposed = false;
  const set = next => { if (!disposed && mode !== next) { mode = next; changed(next); } };
  const ownsFullscreen = () => doc.fullscreenElement === shell;
  const sync = () => {
    release();
    if (ownsFullscreen()) set('fullscreen');
    else if (mode === 'fullscreen') set(intent === 'minimized' ? 'minimized' : 'normal');
  };
  doc.addEventListener('fullscreenchange', sync);
  async function exit(next = 'normal') {
    intent = next; const request = ++generation; release();
    if (ownsFullscreen()) {
      try { await doc.exitFullscreen(); } catch { /* Reflect the actual browser, never a pretend exit. */ }
    }
    if (!disposed && request === generation) set(ownsFullscreen() ? 'fullscreen' : next);
  }
  return {
    get mode() { return mode; },
    async expand() {
      if (disposed) return;
      intent = 'expanded'; release(); const request = ++generation;
      try {
        if (typeof shell.requestFullscreen !== 'function' || doc.fullscreenEnabled === false) throw new Error('unavailable');
        await shell.requestFullscreen();
      } catch { /* Mobile element fullscreen may be unavailable: use the shell's CSS surface. */ }
      if (disposed || request !== generation) {
        if (ownsFullscreen() && (disposed || intent !== 'expanded')) { try { await doc.exitFullscreen(); } catch { sync(); } }
        return;
      }
      set(ownsFullscreen() ? 'fullscreen' : 'immersive');
    },
    normal: () => exit('normal'),
    minimize: () => exit('minimized'),
    restore: () => exit('normal'),
    dispose() {
      disposed = true; generation++; release(); doc.removeEventListener('fullscreenchange', sync);
      if (ownsFullscreen()) void doc.exitFullscreen().catch(() => undefined);
    },
  };
}
