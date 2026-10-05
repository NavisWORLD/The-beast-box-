/*
 * Beast Box device bridge, injected by the Android app after each page load on the configured origin.
 *
 * Page -> phone: every ~1.5 s the live creature is reported to window.BeastBoxNative.reportState(json).
 *   Source order: window.BeastBoxDevice.getState() if the web app defines it (preferred, explicit API),
 *   else the Spark Beasts local store (localStorage "spark-beasts-v1", active beast).
 * Phone -> page: BLE commands arrive via window.__beastBoxDevice.receive(json).
 *   A "beastbox:command" CustomEvent is always dispatched on window. If the page defines
 *   window.BeastBoxDevice.onCommand(cmd) and it returns true, nothing else happens. Otherwise a
 *   best-effort Spark Beasts adapter presses the matching care control (documented in README).
 */
(function () {
  'use strict';
  if (window.__beastBoxDevice || !window.BeastBoxNative) return;
  var NATIVE = window.BeastBoxNative;
  var STORE_KEY = 'spark-beasts-v1';
  var lastSent = '';

  function num(v, lo, hi, dflt) {
    var n = Number(v);
    if (!isFinite(n)) return dflt;
    return Math.max(lo, Math.min(hi, Math.round(n)));
  }

  function fromPageHook() {
    try {
      var hook = window.BeastBoxDevice;
      if (hook && typeof hook.getState === 'function') return hook.getState() || null;
    } catch (e) { /* page hook failed; fall through */ }
    return null;
  }

  function fromSparkStore() {
    try {
      var raw = window.localStorage.getItem(STORE_KEY);
      if (!raw) return null;
      var store = JSON.parse(raw);
      var beast = store && store.beasts && store.active ? store.beasts[store.active] : null;
      if (!beast) return null;
      return {
        displayName: beast.displayName || '',
        species: beast.name || '',
        stage: beast.stage || 1,
        xp: beast.xp || 0,
        bond: beast.bond || 0,
        energy: beast.energy
      };
    } catch (e) { return null; }
  }

  function snapshot() {
    var s = fromPageHook() || fromSparkStore();
    if (!s) return { displayName: '', species: '', stage: 0, xp: 0, bond: 0, energy: null };
    return {
      displayName: String(s.displayName || s.name || '').slice(0, 32),
      species: String(s.species || '').slice(0, 32),
      stage: num(s.stage, 0, 3, 1),
      xp: num(s.xp, 0, 1e9, 0),
      bond: num(s.bond, 0, 100, 0),
      energy: s.energy == null ? null : num(s.energy, 0, 100, 0)
    };
  }

  function report(force) {
    var json = JSON.stringify(snapshot());
    if (!force && json === lastSent) return;
    lastSent = json;
    try { NATIVE.reportState(json); } catch (e) { /* bridge gone */ }
  }

  function click(id) {
    var el = document.getElementById(id);
    if (!el || el.disabled) return false;
    el.click();
    return true;
  }

  // Spark Beasts has no feed/attack buttons; these map onto its nearest care actions.
  var SPARK_ADAPTER = {
    feed: function () { return click('act-rest'); },
    play: function () { return click('act-play'); },
    attack: function () { return click('act-focus'); },
    talk: function (cmd) {
      var input = document.getElementById('chat-input');
      var form = document.getElementById('chat-form');
      if (!input || !form) return false;
      input.value = (cmd.text || 'Hi from a Beast Box device!').slice(0, 120);
      if (typeof form.requestSubmit === 'function') form.requestSubmit();
      else form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
      return true;
    }
  };

  function receive(json) {
    var cmd;
    try { cmd = JSON.parse(json); } catch (e) { return false; }
    if (!cmd || !cmd.command) return false;
    try { window.dispatchEvent(new CustomEvent('beastbox:command', { detail: cmd })); } catch (e) {}
    var handled = false;
    try {
      var hook = window.BeastBoxDevice;
      if (hook && typeof hook.onCommand === 'function') handled = hook.onCommand(cmd) === true;
    } catch (e) {}
    if (!handled && SPARK_ADAPTER[cmd.command]) handled = SPARK_ADAPTER[cmd.command](cmd);
    try { NATIVE.log('command ' + cmd.command + ' from ' + cmd.source + (handled ? ' applied' : ' not applied')); } catch (e) {}
    setTimeout(function () { report(true); }, 400);
    return handled;
  }

  window.__beastBoxDevice = { receive: receive, report: report, version: 1 };
  window.addEventListener('storage', function () { report(false); });
  setInterval(function () { report(false); }, 1500);
  report(true);
})();
