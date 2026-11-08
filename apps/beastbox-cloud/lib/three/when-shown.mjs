/** Resolves true once `el` intersects the viewport. A cancel resolves false.
 * Heavy WebGL on /beast-cage was starting while its canvas was still below the fold.
 * On SwiftShader those frames ran for seconds and starved the OPEN GAME navigation. */
export function whenShown(el) {
  let observer = null;
  let settle = null;
  const promise = new Promise(resolve => {
    settle = value => { settle = null; resolve(value); };
    try {
      if (!el || typeof IntersectionObserver !== 'function') { settle(true); return; }
      const box = el.getBoundingClientRect?.();
      const height = window.innerHeight || 0;
      if (box && box.width > 2 && box.height > 2 && box.bottom > 0 && box.top < height) { settle(true); return; }
      observer = new IntersectionObserver(entries => {
        if (!settle || !entries.some(entry => entry.isIntersecting)) return;
        observer.disconnect();
        observer = null;
        settle(true);
      }, { threshold: 0.01 });
      observer.observe(el);
    } catch {
      if (settle) settle(true);
    }
  });
  return {
    promise,
    cancel() {
      if (observer) { observer.disconnect(); observer = null; }
      if (settle) settle(false);
    }
  };
}
