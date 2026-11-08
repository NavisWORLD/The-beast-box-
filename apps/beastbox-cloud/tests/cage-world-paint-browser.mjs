/**
 * Browser acceptance for the #859 render regression.
 * Requires the app on BEAST_BROWSER_ROOT (default http://localhost:3100)
 * and Chrome (BEAST_BROWSER_EXECUTABLE, default /usr/bin/google-chrome).
 *
 *   node --test tests/cage-world-paint-browser.mjs
 *
 * /beast-cage/world must draw non-black pixels with no data-bridge-settled.
 * The pocket must keep drawing. A second tab parks the first with a visible
 * message, and closing it lets the first tab paint again.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdirSync, writeFileSync} from 'node:fs';
import {inflateSync} from 'node:zlib';

const ROOT = process.env.BEAST_BROWSER_ROOT || 'http://localhost:3100';
const CHROME = process.env.BEAST_BROWSER_EXECUTABLE || '/usr/bin/google-chrome';
const PORT = Number(process.env.BEAST_CDP_PORT || 9333);
const OUT = process.env.BEAST_BROWSER_OUT || '/tmp/cage-world-paint';

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function serverUp() {
  try {
    const res = await fetch(ROOT + '/beast-cage/world', {redirect: 'manual'});
    return res.status > 0 && res.status < 500;
  } catch { return false; }
}

function pngNonBlack(buf) {
  let o = 8, width = 0, height = 0, color = 6;
  const idat = [];
  while (o + 8 <= buf.length) {
    const len = buf.readUInt32BE(o); o += 4;
    const type = buf.toString('ascii', o, o + 4); o += 4;
    const data = buf.subarray(o, o + len); o += len + 4;
    if (type === 'IHDR') { width = data.readUInt32BE(0); height = data.readUInt32BE(4); color = data[9]; }
    else if (type === 'IDAT') idat.push(data);
    else if (type === 'IEND') break;
  }
  const raw = inflateSync(Buffer.concat(idat));
  const bpp = color === 6 ? 4 : color === 2 ? 3 : color === 4 ? 2 : 1;
  const stride = width * bpp;
  const paeth = (a, b, c) => {
    const q = a + b - c, pa = Math.abs(q - a), pb = Math.abs(q - b), pc = Math.abs(q - c);
    return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
  };
  let nonBlack = 0, p = 0, prev = Buffer.alloc(stride);
  for (let y = 0; y < height; y++) {
    const filter = raw[p++];
    const row = Buffer.alloc(stride);
    for (let i = 0; i < stride; i++) {
      const x = raw[p++];
      const a = i >= bpp ? row[i - bpp] : 0;
      const b = prev[i];
      const c = i >= bpp ? prev[i - bpp] : 0;
      let v = x;
      if (filter === 1) v = (x + a) & 255;
      else if (filter === 2) v = (x + b) & 255;
      else if (filter === 3) v = (x + ((a + b) >> 1)) & 255;
      else if (filter === 4) v = (x + paeth(a, b, c)) & 255;
      row[i] = v;
    }
    for (let x = 0; x < width; x++) {
      const r = row[x * bpp], g = row[x * bpp + 1] || 0, b = row[x * bpp + 2] || 0;
      if (r > 18 || g > 18 || b > 18) nonBlack++;
    }
    prev = row;
  }
  return {width, height, nonBlack, total: width * height};
}

function overlaps(a, b) {
  if (!a || !b || a.width < 2 || b.width < 2 || a.height < 2 || b.height < 2) return false;
  return a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1;
}

test('world draws without a bridge, the pocket keeps painting, and the newer tab parks the older one', {timeout: 240000}, async t => {
  if (!await serverUp()) return t.skip(`no server at ${ROOT}`);
  mkdirSync(OUT, {recursive: true});
  const chrome = spawn(CHROME, [
    '--headless=new', '--disable-gpu', '--no-sandbox', '--no-first-run',
    '--use-gl=angle', '--use-angle=swiftshader',
    `--remote-debugging-port=${PORT}`, `--user-data-dir=/tmp/chrome-paint-${PORT}`,
    'about:blank'
  ], {stdio: 'ignore'});
  let browser;
  try {
    let version;
    for (let i = 0; i < 40; i++) {
      try { version = await fetch(`http://127.0.0.1:${PORT}/json/version`).then(r => r.json()); break; }
      catch { await sleep(150); }
    }
    assert.ok(version?.webSocketDebuggerUrl, 'chrome debugger');
    browser = new WebSocket(version.webSocketDebuggerUrl);
    let seq = 0; const pending = new Map();
    const send = (method, params = {}, sessionId) => {
      const id = ++seq;
      const payload = {id, method, params};
      if (sessionId) payload.sessionId = sessionId;
      browser.send(JSON.stringify(payload));
      return new Promise((resolve, reject) => pending.set(id, {resolve, reject}));
    };
    browser.addEventListener('message', ev => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id); pending.delete(msg.id);
        msg.error ? p.reject(new Error(JSON.stringify(msg.error))) : p.resolve(msg.result);
      }
    });
    await new Promise((resolve, reject) => { browser.addEventListener('open', resolve); browser.addEventListener('error', reject); });

    const DRAW = `(() => {
      const bump = function(){ try { this.canvas.__draws = (this.canvas.__draws||0)+1; } catch(e){} };
      for (const P of [window.WebGLRenderingContext, window.WebGL2RenderingContext]) {
        if (!P || P.prototype.__beastDraws) continue;
        P.prototype.__beastDraws = true;
        const de = P.prototype.drawElements, da = P.prototype.drawArrays;
        P.prototype.drawElements = function(){ bump.call(this); return de.apply(this, arguments); };
        P.prototype.drawArrays = function(){ bump.call(this); return da.apply(this, arguments); };
      }
    })();`;

    async function openPage(width, height) {
      const {targetId} = await send('Target.createTarget', {url: 'about:blank'});
      const {sessionId} = await send('Target.attachToTarget', {targetId, flatten: true});
      await send('Page.enable', {}, sessionId);
      await send('Runtime.enable', {}, sessionId);
      await send('Page.addScriptToEvaluateOnNewDocument', {source: DRAW}, sessionId);
      await send('Emulation.setDeviceMetricsOverride', {width, height, deviceScaleFactor: 1, mobile: width < 500}, sessionId);
      return {targetId, sessionId};
    }
    async function evalJson(sessionId, expression) {
      const res = await send('Runtime.evaluate', {returnByValue: true, expression}, sessionId);
      if (res.exceptionDetails) throw new Error(JSON.stringify(res.exceptionDetails));
      return res.result?.value;
    }
    async function goto(sessionId, path) {
      await send('Page.navigate', {url: ROOT + path}, sessionId);
      await sleep(400);
    }
    async function waitFor(sessionId, expression, ms) {
      const start = Date.now();
      let last;
      while (Date.now() - start < ms) {
        last = await evalJson(sessionId, expression);
        if (last) return last;
        await sleep(250);
      }
      throw new Error('timeout ' + expression + ' last=' + JSON.stringify(last));
    }
    async function shot(sessionId, name, clip) {
      const params = {format: 'png'};
      if (clip) params.clip = {...clip, scale: 1};
      const {data} = await send('Page.captureScreenshot', params, sessionId);
      const buf = Buffer.from(data, 'base64');
      writeFileSync(`${OUT}/${name}.png`, buf);
      return pngNonBlack(buf);
    }
    async function draws(sessionId, selector) {
      return evalJson(sessionId, `document.querySelector(${JSON.stringify(selector)})?.__draws || 0`);
    }

    const desktop = await openPage(1280, 800);
    await goto(desktop.sessionId, '/beast-cage/world');
    await waitFor(desktop.sessionId, `(() => {
      const host = document.querySelector('[data-living-world]');
      const loading = document.querySelector('[data-lw-loading]');
      const canvas = host?.querySelector('canvas');
      return !!(host && !loading && canvas && canvas.width > 2 && canvas.height > 2 && (canvas.__draws || 0) > 0);
    })()`, 45000);
    const worldBridge = await evalJson(desktop.sessionId, `document.querySelector('[data-bridge-settled]')`);
    assert.equal(worldBridge, null);
    const chromeOn = await evalJson(desktop.sessionId, `!!document.querySelector('[data-lw-chips]')`);
    assert.equal(chromeOn, true);
    const box = await evalJson(desktop.sessionId, `(() => { const r = document.querySelector('[data-living-world] canvas').getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height}; })()`);
    const worldPx = await shot(desktop.sessionId, 'world-1280', box);
    assert.ok(worldPx.nonBlack > 800, 'world desktop non-black ' + worldPx.nonBlack);

    const phone = await openPage(393, 852);
    await goto(phone.sessionId, '/beast-cage/world');
    await waitFor(phone.sessionId, `(() => {
      const host = document.querySelector('[data-living-world]');
      const loading = document.querySelector('[data-lw-loading]');
      const canvas = host?.querySelector('canvas');
      return !!(host && !loading && canvas && canvas.clientWidth > 2 && (canvas.__draws || 0) > 0);
    })()`, 45000);
    assert.equal(await evalJson(phone.sessionId, `document.querySelector('[data-bridge-settled]')`), null);
    assert.equal(await evalJson(phone.sessionId, `!!document.querySelector('[data-lw-chips]')`), true);
    const phoneBox = await evalJson(phone.sessionId, `(() => { const r = document.querySelector('[data-living-world] canvas').getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height}; })()`);
    const phonePx = await shot(phone.sessionId, 'world-393', phoneBox);
    assert.ok(phonePx.nonBlack > 400, 'world phone non-black ' + phonePx.nonBlack);
    await shot(phone.sessionId, 'world-393-page');
    await send('Target.closeTarget', {targetId: desktop.targetId});
    await send('Target.closeTarget', {targetId: phone.targetId});

    const pocket = await openPage(1280, 800);
    await goto(pocket.sessionId, '/beast-cage');
    await waitFor(pocket.sessionId, `!!document.querySelector('.cage-habitat-visual')`, 20000);
    await evalJson(pocket.sessionId, `document.querySelector('.cage-habitat-visual').scrollIntoView({block:'center'})`);
    await waitFor(pocket.sessionId, `document.querySelector('[data-pocket-state]')?.dataset.pocketState === 'ready'`, 45000);
    const before = await draws(pocket.sessionId, '[data-pocket-webgl="true"]');
    await sleep(30000);
    const after = await draws(pocket.sessionId, '[data-pocket-webgl="true"]');
    assert.ok(after > before, `pocket kept drawing ${before} -> ${after}`);
    assert.equal(await evalJson(pocket.sessionId, `document.querySelector('[data-pocket-parked]')`), null);
    assert.equal(await evalJson(pocket.sessionId, `document.querySelector('[data-pocket-state]')?.dataset.pocketState`), 'ready');
    const pocketBox = await evalJson(pocket.sessionId, `(() => { const r = document.querySelector('.cage-habitat-visual').getBoundingClientRect(); return {x:Math.max(0,r.x),y:Math.max(0,r.y),width:r.width,height:r.height}; })()`);
    const pocketPx = await shot(pocket.sessionId, 'pocket-1280', pocketBox);
    assert.ok(pocketPx.nonBlack > 400, 'pocket desktop non-black ' + pocketPx.nonBlack);
    await send('Target.closeTarget', {targetId: pocket.targetId});

    const narrow = await openPage(393, 852);
    await goto(narrow.sessionId, '/beast-cage');
    await waitFor(narrow.sessionId, `!!document.querySelector('.cage-habitat-visual')`, 20000);
    await evalJson(narrow.sessionId, `document.querySelector('.cage-habitat-visual').scrollIntoView({block:'center'})`);
    await waitFor(narrow.sessionId, `document.querySelector('[data-pocket-state]')?.dataset.pocketState === 'ready'`, 45000);
    await sleep(500);
    const layout = await evalJson(narrow.sessionId, `(() => {
      const box = el => { if (!el) return null; const s = getComputedStyle(el); if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity) === 0) return null; const r = el.getBoundingClientRect(); return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height}; };
      const circle = document.querySelector('.cage-habitat-visual')?.getBoundingClientRect();
      return {
        circle: circle && {left:circle.left,top:circle.top,right:circle.right,bottom:circle.bottom,width:circle.width,height:circle.height},
        menu: box(document.querySelector('[aria-label="Habitat menu"]')),
        tools: box(document.querySelector('[data-beast-arena="true"] [class*="tools"]')),
        caption: box(document.querySelector('[data-spark-beast="true"] figcaption')),
        live: box(document.querySelector('[data-pocket-dimension] [class*="live"]')),
        sand: box(document.querySelector('[data-sand-source]')),
        sprite: [...document.querySelectorAll('.cage-habitat-visual [data-beast-sprite="true"]')].map(el => { const r = el.getBoundingClientRect(); return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height}; }).find(b => b.width > 40 && b.height > 40) || null
      };
    })()`);
    await shot(narrow.sessionId, 'pocket-393-page');
    assert.equal(overlaps(layout.sand, layout.menu), false, 'sand overlaps habitat menu ' + JSON.stringify(layout));
    assert.equal(overlaps(layout.tools, layout.menu), false, 'tools overlap habitat menu ' + JSON.stringify(layout));
    assert.equal(overlaps(layout.live, layout.menu), false, 'live badge overlaps habitat menu ' + JSON.stringify(layout));
    assert.equal(overlaps(layout.caption, layout.sprite), false, 'caption overlaps the creature ' + JSON.stringify(layout));
    assert.equal(overlaps(layout.sand, layout.sprite), false, 'sand overlaps the creature ' + JSON.stringify(layout));
    assert.equal(overlaps(layout.tools, layout.sprite), false, 'tools overlap the creature ' + JSON.stringify(layout));
    assert.ok(layout.sprite && layout.sprite.width > 40, 'creature box ' + JSON.stringify(layout.sprite));
    const seedLine = await evalJson(narrow.sessionId, `(() => { const el = document.querySelector('[class*="seedLine"]'); if (!el) return ''; const s = getComputedStyle(el); if (s.display === 'none' || Number(s.opacity) === 0) return ''; return el.textContent || ''; })()`);
    assert.match(seedLine, /RECORDED on IBM hardware/);
    await send('Target.closeTarget', {targetId: narrow.targetId});

    const tabA = await openPage(1280, 800);
    await goto(tabA.sessionId, '/beast-cage');
    await waitFor(tabA.sessionId, `!!document.querySelector('.cage-habitat-visual')`, 20000);
    await evalJson(tabA.sessionId, `document.querySelector('.cage-habitat-visual').scrollIntoView({block:'center'})`);
    await waitFor(tabA.sessionId, `document.querySelector('[data-pocket-state]')?.dataset.pocketState === 'ready' && document.querySelector('[data-pocket-painter]')?.dataset.pocketPainter === 'lead'`, 45000);
    const tabB = await openPage(1280, 800);
    await goto(tabB.sessionId, '/beast-cage');
    await waitFor(tabA.sessionId, `!!document.querySelector('[data-pocket-parked="yes"]')`, 15000);
    const parkedText = await evalJson(tabA.sessionId, `document.querySelector('[data-pocket-parked="yes"]')?.textContent || ''`);
    assert.match(parkedText, /Paused/);
    const parkedBox = await evalJson(tabA.sessionId, `(() => { const r = document.querySelector('[data-pocket-parked="yes"]').getBoundingClientRect(); return {width:r.width,height:r.height}; })()`);
    assert.ok(parkedBox.width > 40 && parkedBox.height > 20, 'parked message has a box');
    await shot(tabA.sessionId, 'tab-a-parked');
    const aFrozen = await draws(tabA.sessionId, '[data-pocket-webgl="true"]');
    await sleep(1200);
    const aStill = await draws(tabA.sessionId, '[data-pocket-webgl="true"]');
    assert.equal(aStill, aFrozen, 'parked tab kept drawing');
    assert.equal(await evalJson(tabB.sessionId, `document.querySelector('[data-pocket-parked]')`), null);
    await send('Target.closeTarget', {targetId: tabB.targetId});
    await waitFor(tabA.sessionId, `!document.querySelector('[data-pocket-parked]') && document.querySelector('[data-pocket-painter]')?.dataset.pocketPainter === 'lead'`, 8000);
    const aResume = await draws(tabA.sessionId, '[data-pocket-webgl="true"]');
    await sleep(1500);
    const aPainting = await draws(tabA.sessionId, '[data-pocket-webgl="true"]');
    assert.ok(aPainting > aResume, `tab A resumed ${aResume} -> ${aPainting}`);
    await shot(tabA.sessionId, 'tab-a-resumed');
  } finally {
    try { browser?.close(); } catch { /* closed */ }
    chrome.kill('SIGKILL');
  }
});
