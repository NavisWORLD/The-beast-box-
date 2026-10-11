import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
const root = new URL('..', import.meta.url).pathname;
const read = (p) => readFileSync(join(root, p), 'utf8');

// Browser evidence (390x844 and 390x664): the nav stays visible, the full game
// screen is inside the viewport and the controls sit below it. These checks
// keep the pieces of that fix from drifting apart.
test('/sol-game nav is one marked row the player can measure', () => {
  const page = read('app/sol-game/page.tsx');
  assert.match(page, /<nav data-page-nav aria-label="Beast Box journey"/);
  assert.match(page, /flexWrap:'nowrap',overflowX:'auto'/);
});

test('the full-screen player starts below the page nav and minimized still wins', () => {
  const dock = read('components/lost-cosmos-dock.tsx');
  assert.match(dock, /querySelector<HTMLElement>\('main \[data-page-nav\]'\)/);
  assert.match(dock, /'--nav-clear'/);
  const css = read('components/lost-cosmos-dock.module.css');
  const full = css.indexOf('.sparkDock[data-cosmos-mode=full]{top:var(--nav-clear,8px)}');
  const minimized = css.indexOf('.sparkDock:has([data-player-mode=minimized])');
  assert.ok(full > 0 && minimized > full, 'minimized rule must come after the nav-clear rule');
});
