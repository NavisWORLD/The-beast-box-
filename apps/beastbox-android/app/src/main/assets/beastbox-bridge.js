/*
 * Beast Box Android bridge, injected after each trusted page load.
 *
 * Current Spark v0.2:
 * - reports the active QBEAST/care state from the explicit BeastBoxDevice hook first;
 * - falls back to beastbox-companion-session-v1 when the hook is unavailable;
 * - routes BLE feed/play/attack/talk into the current Spark controls;
 * - never exposes Bluetooth control to page JavaScript.
 */
(function () {
  'use strict';
  if (window.__beastBoxDevice || !window.BeastBoxNative) return;
  var NATIVE = window.BeastBoxNative;
  var SESSION_KEY = 'beastbox-companion-session-v1';
  var LEGACY_KEY = 'spark-beasts-v1';
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
    } catch (e) {}
    return null;
  }

  function fromCurrentSession() {
    try {
      var raw = window.localStorage.getItem(SESSION_KEY);
      if (!raw) return null;
      var session = JSON.parse(raw);
      var beast = session && session.beast;
      if (!beast) return null;
      var genome = beast.genome || {};
      var names = genome.names || {};
      var stage = num(beast.nativeStage || beast.stage, 1, 3, 1);
      return {
        displayName: beast.displayName || names[stage] || names[1] || '',
        species: names[stage] || names[1] || beast.displayName || '',
        stage: stage,
        xp: beast.xp || 0,
        bond: beast.bond || 0,
        energy: beast.energy
      };
    } catch (e) { return null; }
  }

  function fromLegacyStore() {
    try {
      var raw = window.localStorage.getItem(LEGACY_KEY);
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
    var s = fromPageHook() || fromCurrentSession() || fromLegacyStore();
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
    try { NATIVE.reportState(json); } catch (e) {}
  }

  function click(id) {
    var el = document.getElementById(id);
    if (!el || el.disabled) return false;
    el.click();
    return true;
  }

  function talk(cmd) {
    var open = document.getElementById('talk');
    var input = document.getElementById('talk-text') || document.getElementById('chat-input');
    var form = document.getElementById('talk-form') || document.getElementById('chat-form');
    if ((!input || !form) && open) {
      open.click();
      input = document.getElementById('talk-text') || document.getElementById('chat-input');
      form = document.getElementById('talk-form') || document.getElementById('chat-form');
    }
    if (!input || !form) return false;
    input.value = String(cmd.text || 'Hi from a Beast Box device!').slice(0, 120);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    if (typeof form.requestSubmit === 'function') form.requestSubmit();
    else form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    return true;
  }

  var SPARK_ADAPTER = {
    feed: function () { return click('care') || click('rest') || click('act-rest'); },
    play: function () { return click('play') || click('act-play'); },
    attack: function () { return click('train') || click('act-focus'); },
    talk: talk
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
    setTimeout(function () { report(true); }, 450);
    return handled;
  }

  window.__beastBoxDevice = { receive: receive, report: report, version: 2 };
  window.addEventListener('storage', function () { report(false); });
  window.addEventListener('beastbox:spark-selected', function () { report(true); });
  window.addEventListener('beastbox:session-changed', function () { report(true); });
  setInterval(function () { report(false); }, 1500);
  report(true);
})();
