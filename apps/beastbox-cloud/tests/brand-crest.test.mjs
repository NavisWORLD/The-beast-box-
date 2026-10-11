import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { join } from 'node:path';
const root = new URL('..', import.meta.url).pathname;
const read = (p) => readFileSync(join(root, p), 'utf8');
const walk = (dir) => readdirSync(join(root, dir)).flatMap((n) => { const p = join(dir, n); return statSync(join(root, p)).isDirectory() ? walk(p) : [p]; });
const png = (p) => { const b = readFileSync(join(root, p)); assert.equal(b.toString('ascii', 1, 4), 'PNG', p); return [b.readUInt32BE(16), b.readUInt32BE(20)]; };

test('the spoked ✺ brand mark is gone from every site surface', () => {
  const files = [...walk('app'), ...walk('components'), ...walk('public/spark')].filter((f) => /\.(tsx?|css|html|mjs)$/.test(f));
  const hits = files.filter((f) => read(f).includes('✺'));
  assert.deepEqual(hits, []);
  assert.doesNotMatch(read('app/globals.css'), /\.brand-mark\{[^}]*linear-gradient\(145deg,#d8c6ff,#7663c4\)/);
});

test('one crest source: Cosmic Forge Dragon SVGs and every raster size exist', () => {
  const full = read('public/brand/cosmic-forge-dragon.svg'), small = read('public/brand/cosmic-forge-dragon-small.svg');
  assert.match(full, /Cosmic Forge Dragon/); assert.match(small, /aria-label="Beast Box"/);
  for (const [f, s] of [['cosmic-forge-dragon-16', 16], ['cosmic-forge-dragon-32', 32], ['apple-touch-icon-180', 180], ['cosmic-forge-dragon-192', 192], ['cosmic-forge-dragon-512', 512], ['cosmic-forge-dragon-1024', 1024], ['cosmic-forge-dragon-maskable-192', 192], ['cosmic-forge-dragon-maskable-512', 512]])
    assert.deepEqual(png(`public/brand/${f}.png`), [s, s], f);
  assert.deepEqual(png('public/apple-touch-icon.png'), [180, 180]);
  const ico = readFileSync(join(root, 'public/favicon.ico')); assert.equal(ico.readUInt16LE(2), 1); assert.ok(ico.readUInt16LE(4) >= 2, 'favicon.ico carries 16 and 32');
  assert.equal(existsSync(join(root, 'app/apple-icon.tsx')), false, 'no second generated apple icon competing with the crest');
});

test('favicon, apple icon, manifest and headers all point at the crest', () => {
  const brand = read('lib/brand.ts'), layout = read('app/layout.tsx'), manifest = read('app/manifest.ts');
  assert.match(brand, /BRAND_ICON_VERSION = '\d+'/);
  assert.match(layout, /BRAND_ICONS\.favicon/); assert.match(layout, /BRAND_ICONS\.apple180/); assert.match(layout, /BRAND_CREST_SMALL_SVG/);
  for (const k of ['png192', 'png512', 'maskable192', 'maskable512']) assert.match(manifest, new RegExp(`BRAND_ICONS\\.${k}`));
  assert.match(manifest, /purpose: 'maskable'/);
  const crest = read('components/brand-crest.tsx'); assert.match(crest, /alt=\{decorative \? '' : BRAND_NAME\}/);
  for (const f of ['app/page.tsx', 'app/privacy/page.tsx', 'app/next/page.tsx', 'app/sol-game/page.tsx', 'app/research/page.tsx', 'components/universe-room-nav.tsx', 'components/beast-cage-portal.tsx', 'components/studio.tsx'])
    assert.match(read(f), /<BrandCrest /, f);
  const spark = read('public/spark/index.html');
  assert.match(spark, /class="spark-mark" src="\/brand\/cosmic-forge-dragon-small\.svg\?v=/);
  assert.match(spark, /rel="apple-touch-icon" href="\/apple-touch-icon\.png/);
});
