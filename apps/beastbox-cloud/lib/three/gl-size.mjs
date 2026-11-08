/** Pixel size of an element. A WebGL drawing buffer of 0 is a black frame and a
 * zero-size framebuffer warning, so callers wait for a real box before setSize. */
export function boxOf(el) {
  const rect = el?.getBoundingClientRect?.();
  const width = rect?.width || 0;
  const height = rect?.height || 0;
  return {ok: width > 2 && height > 2, width, height};
}

/** Resolves when `el` has a non-zero layout, or when `timeoutMs` elapses.
 * The timeout result can be `{ok:false}` so the caller can fall back instead of
 * constructing a renderer on an empty canvas. */
export function whenLaidOut(el, timeoutMs = 4000) {
  const first = boxOf(el);
  if (!el) return Promise.resolve({ok: false, width: 0, height: 0});
  if (first.ok) return Promise.resolve(first);
  return new Promise(resolve => {
    let observer = null;
    let timer = 0;
    const finish = value => {
      if (observer) { observer.disconnect(); observer = null; }
      if (timer) { clearTimeout(timer); timer = 0; }
      resolve(value);
    };
    if (typeof ResizeObserver === 'function') {
      observer = new ResizeObserver(() => {
        const box = boxOf(el);
        if (box.ok) finish(box);
      });
      try { observer.observe(el); } catch { /* not a node */ }
    }
    timer = setTimeout(() => finish(boxOf(el)), timeoutMs);
  });
}
