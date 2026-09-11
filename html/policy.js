(() => {
  const nativeFetch = window.fetch.bind(window);
  const allowed = (input) => {
    const raw = typeof input === 'string' ? input : input?.url;
    const u = new URL(raw, location.href);
    if (u.origin === location.origin) return true;
    if (u.protocol === 'https:') return true;
    return u.protocol === 'http:' && (u.hostname === 'localhost' || u.hostname === '127.0.0.1' || u.hostname === '::1');
  };
  window.fetch = (input, init) => {
    if (!allowed(input)) return Promise.reject(new TypeError('Beast Box browser policy rejected a non-HTTPS/non-loopback endpoint'));
    return nativeFetch(input, init);
  };
})();
