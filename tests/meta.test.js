const test = require('node:test');
const assert = require('node:assert');
const Meta = require('../js/meta.js');

function memStorage() {
  const m = {};
  return { getItem: (k) => (k in m ? m[k] : null), setItem: (k, v) => (m[k] = String(v)) };
}
const rng = () => 0.3;

test('load gives defaults with three distinct missions', () => {
  const s = Meta.load(memStorage(), rng);
  assert.strictEqual(s.best, 0);
  assert.strictEqual(s.missions.length, 3);
  assert.strictEqual(new Set(s.missions.map((m) => m.kind)).size, 3);
});

test('corrupt storage falls back to defaults', () => {
  const st = memStorage();
  st.setItem(Meta.KEY, '{not json');
  const s = Meta.load(st, rng);
  assert.strictEqual(s.coins, 0);
});

test('persist + load round trip', () => {
  const st = memStorage();
  const s = Meta.load(st, rng);
  s.coins = 77;
  Meta.persist(st, s);
  assert.strictEqual(Meta.load(st, rng).coins, 77);
});

test('applyRun updates best and coins', () => {
  const s = Meta.load(memStorage(), rng);
  const r = Meta.applyRun(s, { score: 40, gems: 5, nearMisses: 0, bestCombo: 3, feverCount: 0 }, rng);
  assert.strictEqual(s.best, 40);
  assert.ok(r.coins >= 15);
  assert.strictEqual(r.newBest, false); // first run is not celebrated as "new best"
  const r2 = Meta.applyRun(s, { score: 41, gems: 0, nearMisses: 0, bestCombo: 0, feverCount: 0 }, rng);
  assert.strictEqual(r2.newBest, true);
});

test('levels', () => {
  assert.strictEqual(Meta.levelFromXp(0), 1);
  assert.strictEqual(Meta.levelFromXp(49), 1);
  assert.strictEqual(Meta.levelFromXp(50), 2);
  assert.strictEqual(Meta.levelFromXp(150), 3);
  const p = Meta.levelProgress(75);
  assert.deepStrictEqual(p, { level: 2, into: 25, need: 100 });
});

test('daily streak', () => {
  const s = Meta.defaultSave();
  const day = 24 * 3600 * 1000;
  const t0 = new Date(2026, 0, 1, 12).getTime();
  assert.strictEqual(Meta.checkDaily(s, t0), 10);
  assert.strictEqual(Meta.checkDaily(s, t0 + 1000), 0);
  assert.strictEqual(Meta.checkDaily(s, t0 + day), 15);
  assert.strictEqual(s.streak, 2);
  assert.strictEqual(Meta.checkDaily(s, t0 + 3 * day), 10);
  assert.strictEqual(s.streak, 1);
});

test('buy skin', () => {
  const s = Meta.defaultSave();
  assert.strictEqual(Meta.buySkin(s, 'sakura'), false);
  s.coins = 100;
  assert.strictEqual(Meta.buySkin(s, 'sakura'), true);
  assert.strictEqual(s.coins, 40);
  assert.strictEqual(s.skin, 'sakura');
  assert.strictEqual(Meta.buySkin(s, 'neon'), true);
  assert.strictEqual(s.coins, 40);
});

test('missions complete and refill', () => {
  const s = Meta.load(memStorage(), rng);
  const before = s.missions.map((m) => m.kind);
  const run = { score: 1000, gems: 100, nearMisses: 100, bestCombo: 100, feverCount: 10 };
  const r = Meta.applyRun(s, run, rng);
  assert.ok(r.completed.length >= 1);
  assert.strictEqual(s.missions.length, 3);
  assert.ok(before.length === 3);
});
