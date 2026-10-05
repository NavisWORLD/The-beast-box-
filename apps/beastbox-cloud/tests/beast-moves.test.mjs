import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { buildGenome } from "../lib/companion/spark/genome.mjs";
import { buildMoveset, nextAttackDelay, pickAttack, roamAt, roarFor, seedKeyFor, STYLES, TRIGGERS } from "../lib/companion/beast-moves.mjs";

const read = (path) => readFileSync(new URL("../" + path, import.meta.url), "utf8");
const runs = JSON.parse(read("lib/companion/spark/runs.json"));
const genomeFor = (index, traits = { focus: 40, calm: 40, spark: 20 }) => buildGenome(traits, runs[index % runs.length], null);
const sequence = (moveset, trigger, count = 24) => Array.from({ length: count }, (_, n) => pickAttack(moveset, n, trigger).name);

test("the attack picker replays the same moves from the same recorded seed", () => {
  const genome = genomeFor(0);
  const a = buildMoveset(genome);
  const b = buildMoveset(structuredClone(genome));
  assert.deepEqual(a, b);
  for (const trigger of TRIGGERS) assert.deepEqual(sequence(a, trigger), sequence(b, trigger));
  assert.deepEqual(pickAttack(a, 7, "tap"), pickAttack(b, 7, "tap"));
  assert.equal(nextAttackDelay(a, 3), nextAttackDelay(b, 3));
  assert.deepEqual(roamAt(a, 12.5), roamAt(b, 12.5));
  assert.deepEqual(roarFor(genome, a.moves[0]), roarFor(genome, b.moves[0]));
});

test("different recorded seeds give different beasts different fights", () => {
  const keys = new Set();
  const fights = new Set();
  for (let i = 0; i < Math.min(runs.length, 6); i++) {
    const moveset = buildMoveset(genomeFor(i, { focus: 20 + i * 10, calm: 30, spark: 70 - i * 8 }));
    keys.add(moveset.key);
    fights.add(sequence(moveset, "timer", 16).join(",") + "|" + moveset.moves.map((m) => m.hue).join(","));
  }
  assert.ok(keys.size >= 2, "seed keys should differ across recorded runs");
  assert.ok(fights.size >= 2, "move order or looks should differ across recorded runs");
  const ember = buildMoveset({ seed: "s1", element: "ember", temperament: "Fierce", quantum: { top_state: "01" } });
  const frost = buildMoveset({ seed: "s1", element: "frost", temperament: "Fierce", quantum: { top_state: "01" } });
  assert.notDeepEqual(ember.moves.map((m) => m.name), frost.moves.map((m) => m.name));
});

test("moves cover every effect style, stay in bounds, and follow the temperament bias", () => {
  const moveset = buildMoveset({ seed: "bias", element: "machine", temperament: "Fierce", quantum: { top_state: "1100", counts_sha256: "x" }, stats: { 2: { atk: 90, spd: 40, spark: 80 } } });
  assert.deepEqual([...new Set(moveset.moves.map((m) => m.style))].sort(), [...STYLES].sort());
  const counts = {};
  for (let n = 0; n < 600; n++) {
    const move = pickAttack(moveset, n, "timer");
    counts[move.style] = (counts[move.style] || 0) + 1;
    assert.ok(move.shake >= 0 && move.shake <= 16);
    assert.ok(move.chargeMs >= 300 && move.chargeMs <= 1000);
    assert.ok(move.hue >= 0 && move.hue < 360);
    assert.equal(typeof move.crit, "boolean");
  }
  assert.ok(counts.slash > counts.beam, "a Fierce beast favours slashes");
  for (let n = 0; n < 50; n++) {
    const d = nextAttackDelay(moveset, n);
    assert.ok(d >= 5500 && d <= 12500, String(d));
    const p = roamAt(moveset, n * 0.7);
    assert.ok(Math.abs(p.x) <= 1 && Math.abs(p.y) <= 1 && Math.abs(p.facing) === 1);
  }
  const roar = roarFor({ voice: { base_pitch_hz: 260, formants_hz: [800, 1600] } }, moveset.moves[0]);
  assert.ok(roar.startHz > 0 && roar.peakHz > roar.startHz && roar.endHz > 0 && roar.seconds > 0.4 && roar.gain <= 0.6);
  assert.equal(pickAttack({ moves: [] }, 0, "tap"), null);
  assert.equal(pickAttack(moveset, 2, "nonsense").trigger, "timer");
  assert.equal(seedKeyFor(null), "spark-fallback");
});

test("the habitat beast is seeded, honest, muted until a tap, and respects reduced motion", () => {
  const lib = read("lib/companion/beast-moves.mjs");
  const arena = read("components/spark-beast-arena.tsx");
  assert.doesNotMatch(lib, /Math\.random/);
  assert.doesNotMatch(arena, /Math\.random/);
  assert.match(arena, /useState\(false\),soundRef/);
  assert.match(arena, /prefers-reduced-motion: reduce/);
  assert.match(arena, /attack\('tap'\)/);
  assert.match(arena, /attack\('timer'\)/);
  assert.match(arena, /attack\('chat'\)/);
  assert.match(arena, /data-move-toast="true"/);
  assert.match(arena, /no live quantum link/);
  assert.match(arena, /aria-pressed=\{sound\}/);
  assert.match(arena, /<SparkBeastCompanion /);
  assert.match(read("components/beast-cage-portal.tsx"), /<SparkBeastArena /);
  assert.doesNotMatch(arena, /getUserMedia|\/api\/bridge|Authorization/);
});

test("the field screen fits the cartridge in a safe area and keeps our touch pad", () => {
  const dock = read("components/lost-cosmos-dock.tsx");
  const css = read("components/lost-cosmos-dock.module.css");
  const go = read("components/beast-go.tsx");
  assert.match(css, /\.full :global\(\.ejs_virtualGamepad_parent\)\{display:none!important\}/);
  assert.match(css, /aspect-ratio:3\/2/);
  assert.match(css, /var\(--go-safe-top/);
  assert.match(css, /var\(--go-safe-bottom/);
  assert.match(go, /--go-safe-top/);
  assert.match(go, /aria-label="Touch controls"/);
  assert.match(go, /aria-expanded=\{guestOpen\}/);
  assert.match(dock, /data-dock-pill=/);
  assert.match(dock, /Show Lost Cosmos player/);
  const roamer = read("components/companion-provider.module.css");
  assert.match(roamer, /\.shell\[data-anchored="true"\] \.toolbar/);
});
