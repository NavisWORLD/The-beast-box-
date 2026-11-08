/** Resolves true once `el` intersects the viewport. A cancel resolves false.
 * Heavy WebGL on /beast-cage was starting while its canvas was still below the fold.
 * On SwiftShader those frames ran for seconds and starved the OPEN GAME navigation.
 * A zero-size box does not count as shown. `timeoutMs` settles true anyway so a
 * page with no intersection (or a bridge that never arrives) cannot stay black. */
export function whenShown(el, options = {}) {
  let observer = null;
  let resize = null;
  let timer = 0;
  let settle = null;
  const timeoutMs = Number(options.timeoutMs) || 0;
  const promise = new Promise(resolve => {
    settle = value => {
      settle = null;
      if (observer) { observer.disconnect(); observer = null; }
      if (resize) { resize.disconnect(); resize = null; }
      if (timer) { clearTimeout(timer); timer = 0; }
      resolve(value);
    };
    try {
      if (!el || typeof IntersectionObserver !== 'function') { settle(true); return; }
      const visible = () => {
        const box = el.getBoundingClientRect?.();
        const height = window.innerHeight || 0;
        return !!(box && box.width > 2 && box.height > 2 && box.bottom > 0 && box.top < height);
      };
      if (visible()) { settle(true); return; }
      observer = new IntersectionObserver(entries => {
        if (!settle || !entries.some(entry => entry.isIntersecting)) return;
        settle(true);
      }, { threshold: 0.01 });
      observer.observe(el);
      if (typeof ResizeObserver === 'function') {
        resize = new ResizeObserver(() => { if (settle && visible()) settle(true); });
        resize.observe(el);
      }
      if (timeoutMs > 0) timer = setTimeout(() => { if (settle) settle(true); }, timeoutMs);
    } catch {
      if (settle) settle(true);
    }
  });
  return {
    promise,
    cancel() {
      if (timer) { clearTimeout(timer); timer = 0; }
      if (observer) { observer.disconnect(); observer = null; }
      if (resize) { resize.disconnect(); resize = null; }
      if (settle) settle(false);
    }
  };
}
